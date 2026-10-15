"""课程与课堂场次查询接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies.auth import get_current_user
from backend.app.models import Course, CourseSession, User
from backend.app.schemas.classroom import CurrentClassroomResponse


router = APIRouter(prefix="/api/classrooms", tags=["课堂"])


@router.get("/current", response_model=CurrentClassroomResponse)
def read_current_classroom(
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> CurrentClassroomResponse:
    """按学生班级或教师身份查询当前正在进行的课堂。"""

    statement = (
        select(CourseSession, Course, User)
        .join(Course, CourseSession.course_id == Course.id)
        .join(User, Course.teacher_id == User.id)
        .where(CourseSession.status == "active")
        .order_by(CourseSession.start_time.desc())
    )

    if current_user.role == "student":
        statement = statement.where(
            CourseSession.class_name == current_user.class_name
        )
    elif current_user.role == "teacher":
        statement = statement.where(Course.teacher_id == current_user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理员不参与当前课堂",
        )

    classroom_result = database_session.execute(statement).first()
    if classroom_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="当前没有正在进行的课堂",
        )

    course_session, course, teacher = classroom_result
    return CurrentClassroomResponse(
        session_id=course_session.id,
        course_id=course.id,
        course_name=course.name,
        class_name=course_session.class_name,
        topic=course_session.topic,
        teacher_id=teacher.id,
        teacher_name=teacher.name,
        start_time=course_session.start_time,
        status=course_session.status,
    )
