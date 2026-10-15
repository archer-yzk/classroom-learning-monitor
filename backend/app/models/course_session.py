"""课堂场次数据表模型。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class CourseSession(Base):
    """表示某门课程面向某个班级的一次实际上课。"""

    __tablename__ = "course_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'active', 'finished')",
            name="ck_course_sessions_status",
        ),
        Index("ix_course_sessions_course_id", "course_id"),
        Index("ix_course_sessions_class_status", "class_name", "status"),
        Index("ix_course_sessions_start_time", "start_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    class_name: Mapped[str] = mapped_column(String(100), nullable=False)
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="scheduled",
        server_default="scheduled",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
