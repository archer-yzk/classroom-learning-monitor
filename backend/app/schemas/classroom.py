"""课程与课堂场次接口的数据格式。"""

from datetime import datetime

from pydantic import BaseModel


class CurrentClassroomResponse(BaseModel):
    """学生或教师当前课堂的展示信息。"""

    session_id: int
    course_id: int
    course_name: str
    class_name: str
    topic: str
    teacher_id: int
    teacher_name: str
    start_time: datetime
    status: str
