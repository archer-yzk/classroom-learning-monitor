"""管理员用户列表接口的数据格式。"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AdminUserCreate(BaseModel):
    """管理员新增三类用户时提交的数据。"""

    role: Literal["student", "teacher", "admin"]
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    student_no: str | None = Field(default=None, max_length=30)
    name: str = Field(min_length=1, max_length=50)
    age: int = Field(ge=1, le=120)
    gender: str = Field(min_length=1, max_length=20)
    grade: str | None = Field(default=None, max_length=30)
    class_name: str | None = Field(default=None, max_length=100)
    major: str | None = Field(default=None, max_length=100)
    phone: str = Field(min_length=1, max_length=30)

    @field_validator("username", "name", "gender", "phone")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        """清理必填文字并阻止只输入空格。"""

        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("必填内容不能为空")
        return cleaned_value

    @field_validator("student_no", "grade", "class_name", "major")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        """把学生选填字段的空字符串统一转换成空值。"""

        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_role_fields(self) -> Self:
        """学生必须填写四个专属字段，其他角色不保存这些字段。"""

        student_fields = {
            "student_no": self.student_no,
            "grade": self.grade,
            "class_name": self.class_name,
            "major": self.major,
        }
        if self.role == "student":
            missing_fields = [name for name, value in student_fields.items() if not value]
            if missing_fields:
                raise ValueError("学生必须填写学号、年级、班级和专业")
        else:
            self.student_no = None
            self.grade = None
            self.class_name = None
            self.major = None
        return self


class AdminUserUpdate(BaseModel):
    """管理员修改用户资料时提交的数据，角色由原账号决定。"""

    username: str = Field(min_length=3, max_length=50)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    student_no: str | None = Field(default=None, max_length=30)
    name: str = Field(min_length=1, max_length=50)
    age: int = Field(ge=1, le=120)
    gender: str = Field(min_length=1, max_length=20)
    grade: str | None = Field(default=None, max_length=30)
    class_name: str | None = Field(default=None, max_length=100)
    major: str | None = Field(default=None, max_length=100)
    phone: str = Field(min_length=1, max_length=30)

    @field_validator("username", "name", "gender", "phone")
    @classmethod
    def clean_update_required_text(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("必填内容不能为空")
        return cleaned_value

    @field_validator("password", mode="before")
    @classmethod
    def clean_optional_password(cls, value: str | None) -> str | None:
        """空密码表示保留原密码。"""

        if value is None:
            return None
        return value if value else None

    @field_validator("student_no", "grade", "class_name", "major")
    @classmethod
    def clean_update_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class AdminUserStatusUpdate(BaseModel):
    """管理员启用或停用账号时提交的数据。"""

    status: Literal["active", "disabled"]


class AdminUserResponse(BaseModel):
    """管理员可以查看的一名用户，不包含密码等认证敏感信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Literal["student", "teacher", "admin"]
    student_no: str | None
    name: str
    age: int | None
    gender: str | None
    grade: str | None
    class_name: str | None
    major: str | None
    phone: str
    status: Literal["active", "disabled"]


class AdminUserListResponse(BaseModel):
    """管理员用户组合查询结果。"""

    total: int = Field(ge=0)
    users: list[AdminUserResponse]
