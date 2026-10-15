"""管理员课程和课堂场次管理接口。"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from backend.app.core.session import utc_now_without_timezone
from backend.app.core.time import normalize_utc_naive
from backend.app.database import get_db
from backend.app.dependencies.auth import require_role
from backend.app.models import Course, CourseSession, User
from backend.app.schemas.admin_course import (
    AdminCourseCreate,
    AdminCourseListResponse,
    AdminCourseResponse,
    AdminCourseSessionCreate,
    AdminCourseSessionListResponse,
    AdminCourseSessionResponse,
    AdminCourseSessionStatusUpdate,
    TeacherOptionResponse,
)


router = APIRouter(prefix="/api/admin/courses", tags=["管理员课程管理"])
classroom_router = APIRouter(
    prefix="/api/admin/classrooms",
    tags=["管理员课堂管理"],
)


def get_course_teacher(
    course_id: int,
    database_session: Session,
) -> tuple[Course, User]:
    """取得课程与教师，并为不存在的课程返回友好错误。"""

    row = database_session.execute(
        select(Course, User)
        .join(User, Course.teacher_id == User.id)
        .where(Course.id == course_id)
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在",
        )
    return row


def build_session_response(
    classroom: CourseSession,
    course: Course,
    teacher: User,
) -> AdminCourseSessionResponse:
    """组合课堂场次、课程和教师信息。"""

    return AdminCourseSessionResponse(
        id=classroom.id,
        course_id=course.id,
        course_name=course.name,
        teacher_id=teacher.id,
        teacher_name=teacher.name,
        class_name=classroom.class_name,
        topic=classroom.topic,
        start_time=classroom.start_time,
        end_time=classroom.end_time,
        status=classroom.status,
    )


def ensure_course_can_start(course: Course, teacher: User) -> None:
    """只有启用课程和启用教师才能开始课堂。"""

    if course.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="课程已停用，不能开始课堂",
        )
    if teacher.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="授课教师账号已停用，不能开始课堂",
        )


def ensure_no_active_classroom_conflict(
    classroom: CourseSession,
    course: Course,
    database_session: Session,
) -> None:
    """避免同一教师或同一班级同时进入两个课堂。"""

    conflict = database_session.execute(
        select(CourseSession, Course)
        .join(Course, CourseSession.course_id == Course.id)
        .where(
            CourseSession.status == "active",
            CourseSession.id != (classroom.id or 0),
            or_(
                Course.teacher_id == course.teacher_id,
                CourseSession.class_name == classroom.class_name,
            ),
        )
        .order_by(CourseSession.start_time.desc())
    ).first()
    if conflict is None:
        return

    conflict_classroom, conflict_course = conflict
    if conflict_course.teacher_id == course.teacher_id:
        detail = (
            f"该教师已有进行中的课堂：{conflict_course.name} · "
            f"{conflict_classroom.class_name}"
        )
    else:
        detail = (
            f"{classroom.class_name}已有进行中的课堂："
            f"{conflict_course.name}"
        )
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


@router.get("", response_model=AdminCourseListResponse)
def read_admin_courses(
    _administrator: User = Depends(require_role("admin")),
    database_session: Session = Depends(get_db),
) -> AdminCourseListResponse:
    """列出全部课程、课堂数量和可选教师。"""

    session_counts = (
        select(
            CourseSession.course_id.label("course_id"),
            func.count(CourseSession.id).label("session_count"),
            func.sum(
                case((CourseSession.status == "active", 1), else_=0)
            ).label("active_session_count"),
        )
        .group_by(CourseSession.course_id)
        .subquery()
    )
    rows = database_session.execute(
        select(
            Course,
            User,
            func.coalesce(session_counts.c.session_count, 0),
            func.coalesce(session_counts.c.active_session_count, 0),
        )
        .join(User, Course.teacher_id == User.id)
        .outerjoin(session_counts, session_counts.c.course_id == Course.id)
        .order_by(Course.id.desc())
    ).all()
    courses = [
        AdminCourseResponse(
            id=course.id,
            name=course.name,
            teacher_id=teacher.id,
            teacher_name=teacher.name,
            teacher_status=teacher.status,
            description=course.description,
            status=course.status,
            session_count=session_count,
            active_session_count=active_session_count,
        )
        for course, teacher, session_count, active_session_count in rows
    ]
    teachers = [
        TeacherOptionResponse(id=teacher.id, username=teacher.username, name=teacher.name)
        for teacher in database_session.scalars(
            select(User)
            .where(User.role == "teacher", User.status == "active")
            .order_by(User.name.asc(), User.id.asc())
        )
    ]
    return AdminCourseListResponse(
        total=len(courses),
        courses=courses,
        teachers=teachers,
    )


@router.post(
    "",
    response_model=AdminCourseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_course(
    course_data: AdminCourseCreate,
    _administrator: User = Depends(require_role("admin")),
    database_session: Session = Depends(get_db),
) -> AdminCourseResponse:
    """为一名启用教师新增课程。"""

    teacher = database_session.get(User, course_data.teacher_id)
    if teacher is None or teacher.role != "teacher" or teacher.status != "active":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="请选择一个已启用的教师账号",
        )

    duplicate_course = database_session.scalar(
        select(Course).where(
            Course.teacher_id == teacher.id,
            func.lower(Course.name) == course_data.name.lower(),
        )
    )
    if duplicate_course is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该教师已经有同名课程",
        )

    course = Course(
        name=course_data.name,
        teacher_id=teacher.id,
        description=course_data.description,
        status="active",
    )
    database_session.add(course)
    database_session.commit()
    database_session.refresh(course)
    return AdminCourseResponse(
        id=course.id,
        name=course.name,
        teacher_id=teacher.id,
        teacher_name=teacher.name,
        teacher_status=teacher.status,
        description=course.description,
        status=course.status,
        session_count=0,
        active_session_count=0,
    )


@classroom_router.get("", response_model=AdminCourseSessionListResponse)
def read_admin_course_sessions(
    classroom_status: Literal["scheduled", "active", "finished"] | None = Query(
        default=None,
        alias="status",
    ),
    _administrator: User = Depends(require_role("admin")),
    database_session: Session = Depends(get_db),
) -> AdminCourseSessionListResponse:
    """列出最近 100 个课堂场次，可按状态筛选。"""

    filters = []
    if classroom_status is not None:
        filters.append(CourseSession.status == classroom_status)

    total = database_session.scalar(
        select(func.count()).select_from(CourseSession).where(*filters)
    ) or 0
    rows = database_session.execute(
        select(CourseSession, Course, User)
        .join(Course, CourseSession.course_id == Course.id)
        .join(User, Course.teacher_id == User.id)
        .where(*filters)
        .order_by(CourseSession.start_time.desc(), CourseSession.id.desc())
        .limit(100)
    ).all()
    return AdminCourseSessionListResponse(
        total=total,
        sessions=[
            build_session_response(classroom, course, teacher)
            for classroom, course, teacher in rows
        ],
    )


@classroom_router.post(
    "",
    response_model=AdminCourseSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_course_session(
    session_data: AdminCourseSessionCreate,
    _administrator: User = Depends(require_role("admin")),
    database_session: Session = Depends(get_db),
) -> AdminCourseSessionResponse:
    """为已有课程创建待开始或正在进行的课堂。"""

    course, teacher = get_course_teacher(session_data.course_id, database_session)
    ensure_course_can_start(course, teacher)
    classroom = CourseSession(
        course_id=course.id,
        class_name=session_data.class_name,
        topic=session_data.topic,
        start_time=normalize_utc_naive(session_data.start_time),
        status=session_data.status,
    )
    if classroom.status == "active":
        ensure_no_active_classroom_conflict(classroom, course, database_session)

    database_session.add(classroom)
    database_session.commit()
    database_session.refresh(classroom)
    return build_session_response(classroom, course, teacher)


@classroom_router.patch(
    "/{session_id}/status",
    response_model=AdminCourseSessionResponse,
)
def update_admin_course_session_status(
    session_id: int,
    status_data: AdminCourseSessionStatusUpdate,
    _administrator: User = Depends(require_role("admin")),
    database_session: Session = Depends(get_db),
) -> AdminCourseSessionResponse:
    """开始待上课堂，或结束正在进行的课堂。"""

    classroom = database_session.get(CourseSession, session_id)
    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课堂不存在",
        )
    course, teacher = get_course_teacher(classroom.course_id, database_session)

    if classroom.status == status_data.status:
        return build_session_response(classroom, course, teacher)

    if status_data.status == "active":
        if classroom.status != "scheduled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="只有待开始的课堂可以开始上课",
            )
        ensure_course_can_start(course, teacher)
        ensure_no_active_classroom_conflict(classroom, course, database_session)
        classroom.status = "active"
        classroom.start_time = utc_now_without_timezone()
        classroom.end_time = None
    else:
        if classroom.status != "active":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="只有进行中的课堂可以结束",
            )
        classroom.status = "finished"
        classroom.end_time = utc_now_without_timezone()

    database_session.commit()
    database_session.refresh(classroom)
    return build_session_response(classroom, course, teacher)
