"""学生学情反馈接口的数据格式。"""

from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackOptionResponse(BaseModel):
    """一个可选择的学情表情。"""

    score: int = Field(ge=1, le=6)
    emoji: str
    label: str


class FeedbackCreate(BaseModel):
    """学生提交学情反馈时的数据。"""

    session_id: int = Field(gt=0)
    score: int = Field(ge=1, le=6)


class FeedbackResponse(BaseModel):
    """一次已经保存的学情反馈。"""

    id: int
    session_id: int
    student_id: int
    score: int = Field(ge=1, le=6)
    emoji: str
    label: str
    submitted_at: datetime


class CurrentFeedbackResponse(BaseModel):
    """学生在指定课堂中的最近一次反馈。"""

    session_id: int
    feedback: FeedbackResponse | None
