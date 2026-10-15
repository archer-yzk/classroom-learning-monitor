"""学情预警查询接口。"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, aliased

from backend.app.database import get_db
from backend.app.core.session import utc_now_without_timezone
from backend.app.dependencies.auth import require_role
from backend.app.models import Course, CourseSession, LearningAlert, User
from backend.app.schemas.learning_alert import (
    LearningAlertResponse,
    LearningAlertResolveRequest,
    LearningAlertResolveResponse,
    StudentLearningAlertListResponse,
    StudentLearningAlertResponse,
    TeacherLearningAlertListResponse,
)


router = APIRouter(prefix="/api/teacher/learning-alerts", tags=["学情预警"])
student_router = APIRouter(
    prefix="/api/student/learning-alerts",
    tags=["学情预警"],
)


@student_router.get("", response_model=StudentLearningAlertListResponse)
def read_student_learning_alerts(
    student: User = Depends(require_role("student")),
    database_session: Session = Depends(get_db),
) -> StudentLearningAlertListResponse:
    """只返回当前登录学生自己的预警和教师处理结果。"""

    handler_user = aliased(User)
    rows = database_session.execute(
        select(
            LearningAlert,
            Course.name.label("course_name"),
            CourseSession.topic.label("topic"),
            handler_user.name.label("handler_name"),
        )
        .join(CourseSession, CourseSession.id == LearningAlert.session_id)
        .join(Course, Course.id == CourseSession.course_id)
        .outerjoin(handler_user, handler_user.id == LearningAlert.handled_by)
        .where(LearningAlert.student_id == student.id)
        .order_by(
            case((LearningAlert.status == "pending", 0), else_=1),
            LearningAlert.updated_at.desc(),
            LearningAlert.id.desc(),
        )
    ).all()

    alerts = [
        StudentLearningAlertResponse(
            id=row.LearningAlert.id,
            session_id=row.LearningAlert.session_id,
            course_name=row.course_name,
            topic=row.topic,
            latest_score=row.LearningAlert.latest_score,
            status=row.LearningAlert.status,
            teacher_note=row.LearningAlert.teacher_note,
            handler_name=row.handler_name,
            created_at=row.LearningAlert.created_at,
            updated_at=row.LearningAlert.updated_at,
            resolved_at=row.LearningAlert.resolved_at,
        )
        for row in rows
    ]
    return StudentLearningAlertListResponse(
        total=len(alerts),
        pending_count=sum(alert.status == "pending" for alert in alerts),
        alerts=alerts,
    )


@router.get("", response_model=TeacherLearningAlertListResponse)
def read_teacher_learning_alerts(
    alert_status: Literal["pending", "resolved"] | None = Query(
        default=None,
        alias="status",
    ),
    teacher: User = Depends(require_role("teacher")),
    database_session: Session = Depends(get_db),
) -> TeacherLearningAlertListResponse:
    """返回当前教师所授课程的预警，并支持按处理状态筛选。"""

    student_user = aliased(User)
    handler_user = aliased(User)
    filters = [Course.teacher_id == teacher.id]
    if alert_status is not None:
        filters.append(LearningAlert.status == alert_status)

    rows = database_session.execute(
        select(
            LearningAlert,
            Course.name.label("course_name"),
            CourseSession.topic.label("topic"),
            CourseSession.class_name.label("class_name"),
            student_user.student_no.label("student_no"),
            student_user.name.label("student_name"),
            handler_user.name.label("handler_name"),
        )
        .join(CourseSession, CourseSession.id == LearningAlert.session_id)
        .join(Course, Course.id == CourseSession.course_id)
        .join(student_user, student_user.id == LearningAlert.student_id)
        .outerjoin(handler_user, handler_user.id == LearningAlert.handled_by)
        .where(*filters)
        .order_by(
            case((LearningAlert.status == "pending", 0), else_=1),
            LearningAlert.updated_at.desc(),
            LearningAlert.id.desc(),
        )
    ).all()

    pending_count = database_session.scalar(
        select(func.count())
        .select_from(LearningAlert)
        .join(CourseSession, CourseSession.id == LearningAlert.session_id)
        .join(Course, Course.id == CourseSession.course_id)
        .where(
            Course.teacher_id == teacher.id,
            LearningAlert.status == "pending",
        )
    ) or 0

    alerts = [
        LearningAlertResponse(
            id=row.LearningAlert.id,
            session_id=row.LearningAlert.session_id,
            course_name=row.course_name,
            topic=row.topic,
            student_id=row.LearningAlert.student_id,
            student_no=row.student_no,
            student_name=row.student_name,
            class_name=row.class_name,
            latest_score=row.LearningAlert.latest_score,
            status=row.LearningAlert.status,
            teacher_note=row.LearningAlert.teacher_note,
            handled_by=row.LearningAlert.handled_by,
            handler_name=row.handler_name,
            created_at=row.LearningAlert.created_at,
            updated_at=row.LearningAlert.updated_at,
            resolved_at=row.LearningAlert.resolved_at,
        )
        for row in rows
    ]
    return TeacherLearningAlertListResponse(
        total=len(alerts),
        pending_count=pending_count,
        alerts=alerts,
    )


@router.patch("/{alert_id}", response_model=LearningAlertResolveResponse)
def resolve_teacher_learning_alert(
    alert_id: int,
    resolve_data: LearningAlertResolveRequest,
    teacher: User = Depends(require_role("teacher")),
    database_session: Session = Depends(get_db),
) -> LearningAlertResolveResponse:
    """由授课教师填写意见并完成一条待处理预警。"""

    learning_alert = database_session.scalar(
        select(LearningAlert)
        .join(CourseSession, CourseSession.id == LearningAlert.session_id)
        .join(Course, Course.id == CourseSession.course_id)
        .where(
            LearningAlert.id == alert_id,
            Course.teacher_id == teacher.id,
        )
    )
    if learning_alert is None:
        # 对不属于当前教师的记录也返回不存在，避免泄露其他课程信息。
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预警不存在或不属于当前教师课程",
        )
    if learning_alert.status == "resolved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该预警已经处理，不能重复覆盖处理意见",
        )

    resolved_at = utc_now_without_timezone()
    learning_alert.status = "resolved"
    learning_alert.teacher_note = resolve_data.teacher_note
    learning_alert.handled_by = teacher.id
    learning_alert.resolved_at = resolved_at
    database_session.commit()

    return LearningAlertResolveResponse(
        message="预警处理完成",
        id=learning_alert.id,
        status="resolved",
        teacher_note=learning_alert.teacher_note,
        handled_by=teacher.id,
        handler_name=teacher.name,
        resolved_at=resolved_at,
    )
