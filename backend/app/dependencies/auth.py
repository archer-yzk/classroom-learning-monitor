"""当前用户识别和角色权限检查。"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.session import (
    SESSION_COOKIE_NAME,
    hash_session_token,
    utc_now_without_timezone,
)
from backend.app.database import get_db
from backend.app.models import LoginSession, User


def get_current_user(
    request: Request,
    database_session: Session = Depends(get_db),
) -> User:
    """根据浏览器 Cookie 找到当前已登录用户。"""

    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )

    login_session = database_session.scalar(
        select(LoginSession).where(
            LoginSession.token_hash == hash_session_token(session_token)
        )
    )
    if login_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态无效，请重新登录",
        )

    if login_session.expires_at <= utc_now_without_timezone():
        database_session.delete(login_session)
        database_session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期，请重新登录",
        )

    current_user = database_session.get(User, login_session.user_id)
    if current_user is None or current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号不存在或已被停用",
        )

    return current_user


def require_role(required_role: str) -> Callable[..., User]:
    """生成一个只允许指定角色通过的权限检查。"""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此页面或功能",
            )
        return current_user

    return role_checker
