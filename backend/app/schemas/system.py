"""系统公共接口的数据格式。"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """健康检查接口返回格式。"""

    status: str
    message: str
    database: str
    user_count: int = Field(ge=0)
