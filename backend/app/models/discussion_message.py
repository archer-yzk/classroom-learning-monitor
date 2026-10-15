"""课堂讨论消息数据表模型。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class DiscussionMessage(Base):
    """保存学生或教师在某次课堂中发送的讨论消息。"""

    __tablename__ = "discussion_messages"
    __table_args__ = (
        CheckConstraint(
            "(content IS NOT NULL AND length(trim(content)) > 0) "
            "OR image_path IS NOT NULL",
            name="ck_discussion_message_content",
        ),
        Index("ix_discussion_session_id", "session_id", "id"),
        Index("ix_discussion_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("course_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content: Mapped[str | None] = mapped_column(Text)
    # 下一小步的图片消息将保存相对于静态目录的文件路径。
    image_path: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
