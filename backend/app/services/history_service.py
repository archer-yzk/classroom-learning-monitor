"""教师历史学情查询的公共数据访问逻辑。"""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Course, CourseSession, StatisticsSnapshot


HistoryDatabaseRow = tuple[StatisticsSnapshot, CourseSession, Course]


def validate_history_time_range(
    start_time: datetime | None,
    end_time: datetime | None,
) -> None:
    """检查组合查询的开始时间不能晚于结束时间。"""

    if start_time is not None and end_time is not None and start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="开始时间不能晚于结束时间",
        )


def query_teacher_history_rows(
    database_session: Session,
    teacher_id: int,
    course_name: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[HistoryDatabaseRow]:
    """查询当前教师自己的历史快照，供页面和 Excel 导出共同使用。"""

    validate_history_time_range(start_time, end_time)

    statement = (
        select(StatisticsSnapshot, CourseSession, Course)
        .join(
            CourseSession,
            StatisticsSnapshot.session_id == CourseSession.id,
        )
        .join(Course, CourseSession.course_id == Course.id)
        .where(Course.teacher_id == teacher_id)
    )

    cleaned_course_name = course_name.strip() if course_name else ""
    if cleaned_course_name:
        statement = statement.where(Course.name.contains(cleaned_course_name))
    if start_time is not None:
        statement = statement.where(CourseSession.start_time >= start_time)
    if end_time is not None:
        statement = statement.where(CourseSession.start_time <= end_time)

    # 课程作业规模下最多返回最近 500 条，避免页面或文件一次加载过多数据。
    statement = statement.order_by(
        StatisticsSnapshot.period_start.desc(),
        StatisticsSnapshot.id.desc(),
    ).limit(500)

    return [
        (snapshot, classroom, course)
        for snapshot, classroom, course in database_session.execute(statement).all()
    ]
