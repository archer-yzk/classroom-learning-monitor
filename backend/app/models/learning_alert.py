"""学情预警与教师跟进数据表模型。"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class LearningAlert(Base):
    """保存学生低分预警及教师后续处理记录。"""

    __tablename__ = "learning_alerts"
    __table_args__ = (
        CheckConstraint(
            "latest_score IN (1, 2)",
            name="ck_learning_alerts_score",
        ),
        CheckConstraint(
            "status IN ('pending', 'resolved')",
            name="ck_learning_alerts_status",
        ),
        CheckConstraint(
            "teacher_note IS NULL "
            "OR (length(trim(teacher_note)) >= 1 "
            "AND length(teacher_note) <= 500)",
            name="ck_learning_alerts_teacher_note",
        ),
        CheckConstraint(
            "(status = 'pending' "
            "AND teacher_note IS NULL "
            "AND handled_by IS NULL "
            "AND resolved_at IS NULL) "
            "OR (status = 'resolved' "
            "AND teacher_note IS NOT NULL "
            "AND handled_by IS NOT NULL "
            "AND resolved_at IS NOT NULL)",
            name="ck_learning_alerts_resolution",
        ),
        Index(
            "ix_learning_alerts_session_status",
            "session_id",
            "status",
        ),
        Index(
            "ix_learning_alerts_student_created",
            "student_id",
            "created_at",
        ),
        Index("ix_learning_alerts_handled_by", "handled_by"),
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
    latest_feedback_id: Mapped[int] = mapped_column(
        ForeignKey("feedback_records.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    latest_score: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    teacher_note: Mapped[str | None] = mapped_column(Text)
    handled_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
