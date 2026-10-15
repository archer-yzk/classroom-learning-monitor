"""学情预警接口的数据格式。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LearningAlertResponse(BaseModel):
    """教师预警列表中的一条完整记录。"""

    id: int
    session_id: int
    course_name: str
    topic: str
    student_id: int
    student_no: str
    student_name: str
    class_name: str
    latest_score: int = Field(ge=1, le=2)
    status: Literal["pending", "resolved"]
    teacher_note: str | None
    handled_by: int | None
    handler_name: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class TeacherLearningAlertListResponse(BaseModel):
    """教师预警查询结果和待处理数量。"""

    total: int = Field(ge=0)
    pending_count: int = Field(ge=0)
    alerts: list[LearningAlertResponse]


class StudentLearningAlertResponse(BaseModel):
    """学生查看的一条本人预警记录。"""

    id: int
    session_id: int
    course_name: str
    topic: str
    latest_score: int = Field(ge=1, le=2)
    status: Literal["pending", "resolved"]
    teacher_note: str | None
    handler_name: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class StudentLearningAlertListResponse(BaseModel):
    """当前学生本人的预警列表。"""

    total: int = Field(ge=0)
    pending_count: int = Field(ge=0)
    alerts: list[StudentLearningAlertResponse]


class LearningAlertResolveRequest(BaseModel):
    """教师处理预警时填写的意见。"""

    teacher_note: str = Field(min_length=1, max_length=500)

    @field_validator("teacher_note")
    @classmethod
    def clean_teacher_note(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("教师处理意见不能为空")
        return cleaned_value


class LearningAlertResolveResponse(BaseModel):
    """一条已处理预警的结果。"""

    message: str
    id: int
    status: Literal["resolved"]
    teacher_note: str
    handled_by: int
    handler_name: str
    resolved_at: datetime
