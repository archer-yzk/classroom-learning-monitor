"""短信验证码数据表模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class SmsVerificationCode(Base):
    """保存短信登录验证码的散列、有效期和使用状态。"""

    __tablename__ = "sms_verification_codes"
    __table_args__ = (
        Index(
            "ix_sms_codes_user_created",
            "user_id",
            "created_at",
        ),
        Index("ix_sms_codes_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # 与密码一样只保存散列，不把验证码明文写入数据库。
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
