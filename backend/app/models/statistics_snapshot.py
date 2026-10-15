"""周期学情统计快照表模型。"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class StatisticsSnapshot(Base):
    """保存某次课堂在一个统计周期内的学情状态快照。"""

    __tablename__ = "statistics_snapshots"
    __table_args__ = (
        CheckConstraint(
            "interval_minutes >= 5 AND interval_minutes <= 10",
            name="ck_snapshot_interval",
        ),
        CheckConstraint(
            "period_end > period_start",
            name="ck_snapshot_period",
        ),
        CheckConstraint(
            "total_students = score_1_count + score_2_count + score_3_count "
            "+ score_4_count + score_5_count + score_6_count",
            name="ck_snapshot_total_count",
        ),
        CheckConstraint(
            "average_score >= 0 AND average_score <= 6",
            name="ck_snapshot_average_score",
        ),
        CheckConstraint("variance >= 0", name="ck_snapshot_variance"),
        UniqueConstraint(
            "session_id",
            "period_start",
            "interval_minutes",
            name="uq_snapshot_session_period_interval",
        ),
        Index("ix_snapshots_session_period", "session_id", "period_start"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("course_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_students: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_1_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_2_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_3_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_4_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_5_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_6_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    variance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
