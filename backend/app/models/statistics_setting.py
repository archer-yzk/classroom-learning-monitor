"""学情统计周期配置表模型。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class StatisticsSetting(Base):
    """保存管理员配置的统计周期；系统只使用编号为 1 的配置。"""

    __tablename__ = "statistics_settings"
    __table_args__ = (
        CheckConstraint(
            "interval_minutes >= 5 AND interval_minutes <= 10",
            name="ck_statistics_interval",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    interval_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
    )
    updated_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
