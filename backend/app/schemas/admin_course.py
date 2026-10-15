"""管理员课程与课堂场次管理的数据格式。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TeacherOptionResponse(BaseModel):
    """新增课程时可选择的启用教师。"""

    id: int
    username: str
    name: str


class AdminCourseCreate(BaseModel):
    """管理员新增课程时提交的数据。"""

    name: str = Field(min_length=1, max_length=100)
    teacher_id: int = Field(gt=0)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("课程名称不能为空")
        return cleaned_value

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class AdminCourseResponse(BaseModel):
    """课程及其授课教师、课堂数量。"""

    id: int
    name: str
    teacher_id: int
    teacher_name: str
    teacher_status: Literal["active", "disabled"]
    description: str | None
    status: Literal["active", "inactive"]
    session_count: int = Field(ge=0)
    active_session_count: int = Field(ge=0)


class AdminCourseListResponse(BaseModel):
    """课程列表和可选教师。"""

    total: int = Field(ge=0)
    courses: list[AdminCourseResponse]
    teachers: list[TeacherOptionResponse]


class AdminCourseSessionCreate(BaseModel):
    """创建一个课堂场次，可保存为待开始或直接开始。"""

    course_id: int = Field(gt=0)
    class_name: str = Field(min_length=1, max_length=100)
    topic: str = Field(min_length=1, max_length=200)
    start_time: datetime
    status: Literal["scheduled", "active"] = "scheduled"

    @field_validator("class_name", "topic")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("班级和课堂主题不能为空")
        return cleaned_value


class AdminCourseSessionStatusUpdate(BaseModel):
    """开始或结束课堂时提交的目标状态。"""

    status: Literal["active", "finished"]


class AdminCourseSessionResponse(BaseModel):
    """课堂场次及其课程和教师信息。"""

    id: int
    course_id: int
    course_name: str
    teacher_id: int
    teacher_name: str
    class_name: str
    topic: str
    start_time: datetime
    end_time: datetime | None
    status: Literal["scheduled", "active", "finished"]


class AdminCourseSessionListResponse(BaseModel):
    """最近的课堂场次列表。"""

    total: int = Field(ge=0)
    sessions: list[AdminCourseSessionResponse]
