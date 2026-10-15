"""教师历史学情查询接口的数据格式。"""

from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.schemas.statistics import ScoreCountResponse


class HistorySnapshotResponse(BaseModel):
    """一条带有课程和课堂信息的历史统计快照。"""

    snapshot_id: int
    session_id: int
    course_name: str
    class_name: str
    topic: str
    class_start_time: datetime
    period_start: datetime
    period_end: datetime
    interval_minutes: int = Field(ge=5, le=10)
    total_students: int = Field(ge=0)
    score_counts: list[ScoreCountResponse]
    average_score: float = Field(ge=0, le=6)
    variance: float = Field(ge=0)


class HistoryQueryResponse(BaseModel):
    """历史学情组合查询结果。"""

    total: int = Field(ge=0)
    records: list[HistorySnapshotResponse]
