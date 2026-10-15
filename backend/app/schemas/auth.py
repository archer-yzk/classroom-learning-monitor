"""登录认证相关的 Pydantic 数据格式。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    """账号密码登录时浏览器提交的数据。"""

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        """去除用户名首尾误输入的空格。"""

        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("用户名不能为空")
        return normalized_value


class SmsCodeRequest(BaseModel):
    """获取短信验证码时提交的数据。"""

    phone: str = Field(min_length=1, max_length=30)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("手机号不能为空")
        return cleaned_value


class SmsCodeResponse(BaseModel):
    """本地模拟短信的返回结果。"""

    message: str
    debug_code: str
    expires_in_seconds: int


class SmsLoginRequest(SmsCodeRequest):
    """使用手机号和六位验证码登录时提交的数据。"""

    code: str = Field(pattern=r"^\d{6}$")

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class WeChatLoginRequest(BaseModel):
    """微信授权登录时提交的临时授权码。"""

    code: str = Field(min_length=1, max_length=100)

    @field_validator("code")
    @classmethod
    def normalize_wechat_code(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("微信授权码不能为空")
        return cleaned_value


class QQLoginRequest(BaseModel):
    """QQ授权登录时提交的临时授权码。"""

    code: str = Field(min_length=1, max_length=100)

    @field_validator("code")
    @classmethod
    def normalize_qq_code(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("QQ授权码不能为空")
        return cleaned_value


class CurrentUserResponse(BaseModel):
    """允许返回给前端的当前用户基本信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    name: str


class LoginResponse(BaseModel):
    """登录成功后的返回数据。"""

    message: str
    user: CurrentUserResponse


class MessageResponse(BaseModel):
    """仅返回提示消息的通用格式。"""

    message: str
