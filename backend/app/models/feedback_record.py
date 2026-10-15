"""学生学情反馈数据表模型。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class FeedbackRecord(Base):
    """保存学生在某次课堂中提交的一次理解程度反馈。"""

    __tablename__ = "feedback_records"
    __table_args__ = (
        CheckConstraint("score >= 1 AND score <= 6", name="ck_feedback_score"),
        Index("ix_feedback_session_time", "session_id", "submitted_at"),
        Index(
            "ix_feedback_student_session_time",
            "student_id",
            "session_id",
            "submitted_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("course_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
