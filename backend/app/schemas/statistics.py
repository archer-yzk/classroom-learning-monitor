"""教师实时学情统计接口的数据格式。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ScoreCountResponse(BaseModel):
    """一个分数段的学生数量。"""

    score: int = Field(ge=1, le=6)
    emoji: str
    label: str
    count: int = Field(ge=0)


class StatisticsTrendPointResponse(BaseModel):
    """最近一个已完成统计周期的趋势点。"""

    period_end: datetime
    average_score: float = Field(ge=0, le=6)
    total_students: int = Field(ge=0)


class CurrentStatisticsResponse(BaseModel):
    """当前课堂的完整实时统计结果。"""

    session_id: int
    total_students: int = Field(ge=0)
    eligible_students: int = Field(default=0, ge=0)
    pending_alerts: int = Field(default=0, ge=0)
    average_score: float = Field(ge=0, le=6)
    variance: float = Field(ge=0)
    score_counts: list[ScoreCountResponse]
    recent_periods: list[StatisticsTrendPointResponse] = Field(default_factory=list)
    calculated_at: datetime
