"""管理员统计周期配置接口的数据格式。"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class StatisticsSettingUpdate(BaseModel):
    """管理员修改统计周期时提交的数据。"""

    interval_minutes: int = Field(ge=5, le=10)


class DailySnapshotCountResponse(BaseModel):
    """最近一天的统计快照数量。"""

    day: date
    count: int = Field(ge=0)


class StatisticsSettingResponse(BaseModel):
    """统计周期配置和快照运行状态。"""

    interval_minutes: int = Field(ge=5, le=10)
    updated_at: datetime
    snapshot_count: int = Field(ge=0)
    latest_snapshot_at: datetime | None
    active_session_count: int = Field(default=0, ge=0)
    updated_by_name: str | None = None
    recent_daily_snapshots: list[DailySnapshotCountResponse] = Field(default_factory=list)
