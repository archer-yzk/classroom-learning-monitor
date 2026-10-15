"""当前课堂学情统计计算。"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.session import utc_now_without_timezone
from backend.app.models import FeedbackRecord
from backend.app.schemas.statistics import (
    CurrentStatisticsResponse,
    ScoreCountResponse,
)
from backend.app.services.feedback_service import FEEDBACK_OPTIONS


def calculate_current_statistics(
    session_id: int,
    database_session: Session,
    *,
    submitted_before: datetime | None = None,
) -> CurrentStatisticsResponse:
    """按照每名学生最近一次反馈计算统计，可限定统计截止时间。"""

    feedback_filter = [FeedbackRecord.session_id == session_id]
    if submitted_before is not None:
        feedback_filter.append(FeedbackRecord.submitted_at < submitted_before)

    # 用提交时间决定“最近一次”，并用编号处理同一时刻的并列记录。
    # 这样导入历史数据或生成周期快照时不会错误地把最大编号当作最新时间。
    ranked_feedbacks = (
        select(
            FeedbackRecord.id.label("feedback_id"),
            func.row_number()
            .over(
                partition_by=FeedbackRecord.student_id,
                order_by=(
                    FeedbackRecord.submitted_at.desc(),
                    FeedbackRecord.id.desc(),
                ),
            )
            .label("position"),
        )
        .where(*feedback_filter)
        .subquery()
    )

    # 只让数据库返回最多六行聚合结果，避免班级人数增长后把每名学生的
    # 原始分数都传回 Python，也避免对同一个列表反复执行 count。
    score_count_rows = database_session.execute(
        select(
            FeedbackRecord.score,
            func.count(FeedbackRecord.id),
        )
        .join(
            ranked_feedbacks,
            FeedbackRecord.id == ranked_feedbacks.c.feedback_id,
        )
        .where(ranked_feedbacks.c.position == 1)
        .group_by(FeedbackRecord.score)
    ).all()
    counts_by_score = {
        score: count for score, count in score_count_rows
    }

    total_students = sum(counts_by_score.values())
    if total_students:
        raw_average = sum(
            score * count for score, count in counts_by_score.items()
        ) / total_students
        raw_variance = sum(
            count * (score - raw_average) ** 2
            for score, count in counts_by_score.items()
        ) / total_students
    else:
        raw_average = 0.0
        raw_variance = 0.0

    score_counts = []
    for score in range(6, 0, -1):
        option = FEEDBACK_OPTIONS[score]
        score_counts.append(
            ScoreCountResponse(
                score=score,
                emoji=option["emoji"],
                label=option["label"],
                count=counts_by_score.get(score, 0),
            )
        )

    return CurrentStatisticsResponse(
        session_id=session_id,
        total_students=total_students,
        average_score=round(raw_average, 2),
        variance=round(raw_variance, 2),
        score_counts=score_counts,
        calculated_at=utc_now_without_timezone(),
    )
