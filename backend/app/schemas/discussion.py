"""课堂在线讨论接口的数据格式。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DiscussionMessageCreate(BaseModel):
    """学生或教师发送的文字讨论内容。"""

    content: str = Field(min_length=1, max_length=500)

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        """去掉首尾空格，并阻止只输入空格的消息。"""

        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("消息内容不能为空")
        return cleaned_value


class DiscussionMessageResponse(BaseModel):
    """一条可显示在讨论区的完整消息。"""

    id: int
    session_id: int
    sender_id: int
    sender_name: str
    sender_role: Literal["student", "teacher"]
    content: str | None
    image_url: str | None
    is_mine: bool
    created_at: datetime


class DiscussionMessageListResponse(BaseModel):
    """课堂讨论消息列表。"""

    session_id: int
    messages: list[DiscussionMessageResponse]
