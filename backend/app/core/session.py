"""登录会话令牌的公共工具。"""

import hashlib
import secrets
from datetime import UTC, datetime


SESSION_COOKIE_NAME = "classroom_session"
SESSION_HOURS = 8


def create_session_token() -> str:
    """生成只交给浏览器保存的随机登录令牌。"""

    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """计算令牌散列，避免数据库泄露后令牌被直接使用。"""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def utc_now_without_timezone() -> datetime:
    """返回供 SQLite 保存的无时区 UTC 时间。"""

    return datetime.now(UTC).replace(tzinfo=None)
