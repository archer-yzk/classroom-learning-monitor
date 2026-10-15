"""教师实时学情统计接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies.auth import require_role
from backend.app.models import (
    Course,
    CourseSession,
    LearningAlert,
    StatisticsSnapshot,
    User,
)
from backend.app.schemas.statistics import (
    CurrentStatisticsResponse,
    StatisticsTrendPointResponse,
)
from backend.app.services.statistics_service import calculate_current_statistics


router = APIRouter(prefix="/api/statistics", tags=["学情统计"])


@router.get(
    "/current/{session_id}",
    response_model=CurrentStatisticsResponse,
)
def read_current_statistics(
    session_id: int,
    teacher: User = Depends(require_role("teacher")),
    database_session: Session = Depends(get_db),
) -> CurrentStatisticsResponse:
    """返回当前教师所授课堂的实时学情统计。"""

    classroom = database_session.get(CourseSession, session_id)
    if classroom is None or classroom.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课堂不存在或已经结束",
        )

    course = database_session.get(Course, classroom.course_id)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在",
        )
    if course.teacher_id != teacher.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能查看其他教师课堂的统计数据",
        )

    statistics = calculate_current_statistics(session_id, database_session)
    statistics.eligible_students = database_session.scalar(
        select(func.count(User.id)).where(
            User.role == "student",
            User.status == "active",
            User.class_name == classroom.class_name,
        )
    ) or 0
    statistics.pending_alerts = database_session.scalar(
        select(func.count(LearningAlert.id)).where(
            LearningAlert.session_id == session_id,
            LearningAlert.status == "pending",
        )
    ) or 0

    recent_snapshots = database_session.scalars(
        select(StatisticsSnapshot)
        .where(StatisticsSnapshot.session_id == session_id)
        .order_by(StatisticsSnapshot.period_end.desc())
        .limit(5)
    ).all()
    statistics.recent_periods = [
        StatisticsTrendPointResponse(
            period_end=snapshot.period_end,
            average_score=snapshot.average_score,
            total_students=snapshot.total_students,
        )
        for snapshot in reversed(recent_snapshots)
    ]
    return statistics
