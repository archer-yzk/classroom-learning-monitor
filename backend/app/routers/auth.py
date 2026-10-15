"""密码、短信、微信、QQ登录，以及当前用户和退出登录接口。"""

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.core.password import hash_password, verify_password
from backend.app.core.session import (
    SESSION_COOKIE_NAME,
    SESSION_HOURS,
    create_session_token,
    hash_session_token,
    utc_now_without_timezone,
)
from backend.app.core.third_party import (
    QQ_DEMO_AUTHORIZATION_CODE,
    QQ_DEMO_OPENID,
    WECHAT_DEMO_AUTHORIZATION_CODE,
    WECHAT_DEMO_OPENID,
)
from backend.app.database import get_db
from backend.app.dependencies.auth import get_current_user
from backend.app.models import LoginSession, SmsVerificationCode, User
from backend.app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    QQLoginRequest,
    SmsCodeRequest,
    SmsCodeResponse,
    SmsLoginRequest,
    WeChatLoginRequest,
)


router = APIRouter(prefix="/api/auth", tags=["登录认证"])
SMS_CODE_MINUTES = 5


def create_login_session(
    user: User,
    response: Response,
    database_session: Session,
) -> None:
    """为已完成身份校验的用户创建八小时登录会话。"""

    current_time = utc_now_without_timezone()
    database_session.execute(
        delete(LoginSession).where(LoginSession.expires_at <= current_time)
    )

    session_token = create_session_token()
    database_session.add(
        LoginSession(
            user_id=user.id,
            token_hash=hash_session_token(session_token),
            expires_at=current_time + timedelta(hours=SESSION_HOURS),
        )
    )
    database_session.commit()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=SESSION_HOURS * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


@router.post("/login", response_model=LoginResponse)
def password_login(
    login_data: LoginRequest,
    response: Response,
    database_session: Session = Depends(get_db),
) -> LoginResponse:
    """校验账号密码并创建八小时有效的登录会话。"""

    user = database_session.scalar(
        select(User).where(User.username == login_data.username)
    )
    if (
        user is None
        or user.status != "active"
        or not verify_password(login_data.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    create_login_session(user, response, database_session)

    return LoginResponse(
        message="登录成功",
        user=CurrentUserResponse.model_validate(user),
    )


@router.post("/sms/send", response_model=SmsCodeResponse)
def send_sms_login_code(
    code_request: SmsCodeRequest,
    database_session: Session = Depends(get_db),
) -> SmsCodeResponse:
    """生成短信登录验证码；当前课程版本直接把模拟验证码返回页面。"""

    user = database_session.scalar(
        select(User).where(
            User.phone == code_request.phone,
            User.status == "active",
        )
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该手机号未登记或账号已被停用",
        )

    current_time = utc_now_without_timezone()
    # 每个账号只保留最新验证码，重新获取后旧验证码立即失效。
    database_session.execute(
        delete(SmsVerificationCode).where(
            SmsVerificationCode.user_id == user.id
        )
    )
    verification_code = f"{secrets.randbelow(1_000_000):06d}"
    database_session.add(
        SmsVerificationCode(
            user_id=user.id,
            code_hash=hash_password(verification_code),
            expires_at=current_time + timedelta(minutes=SMS_CODE_MINUTES),
        )
    )
    database_session.commit()

    return SmsCodeResponse(
        message="模拟短信已发送，验证码5分钟内有效",
        debug_code=verification_code,
        expires_in_seconds=SMS_CODE_MINUTES * 60,
    )


@router.post("/sms/login", response_model=LoginResponse)
def sms_code_login(
    login_data: SmsLoginRequest,
    response: Response,
    database_session: Session = Depends(get_db),
) -> LoginResponse:
    """校验手机号和短信验证码，然后建立登录会话。"""

    user = database_session.scalar(
        select(User).where(
            User.phone == login_data.phone,
            User.status == "active",
        )
    )
    current_time = utc_now_without_timezone()
    verification_code = None
    if user is not None:
        verification_code = database_session.scalar(
            select(SmsVerificationCode)
            .where(
                SmsVerificationCode.user_id == user.id,
                SmsVerificationCode.used_at.is_(None),
                SmsVerificationCode.expires_at > current_time,
            )
            .order_by(SmsVerificationCode.id.desc())
        )

    if (
        user is None
        or verification_code is None
        or not verify_password(login_data.code, verification_code.code_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或验证码错误，验证码也可能已经过期",
        )

    verification_code.used_at = current_time
    create_login_session(user, response, database_session)
    return LoginResponse(
        message="短信验证码登录成功",
        user=CurrentUserResponse.model_validate(user),
    )


@router.post("/wechat/login", response_model=LoginResponse)
def wechat_login(
    login_data: WeChatLoginRequest,
    response: Response,
    database_session: Session = Depends(get_db),
) -> LoginResponse:
    """用本地模拟微信授权码登录已绑定的测试账号。"""

    # 真实接入时，这里应调用微信接口，用临时 code 换取 openid。
    if login_data.code != WECHAT_DEMO_AUTHORIZATION_CODE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="微信授权失败，请重新授权",
        )

    user = database_session.scalar(
        select(User).where(
            User.wechat_openid == WECHAT_DEMO_OPENID,
            User.status == "active",
        )
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="微信账号未绑定或系统账号已被停用",
        )

    create_login_session(user, response, database_session)
    return LoginResponse(
        message="微信登录成功",
        user=CurrentUserResponse.model_validate(user),
    )


@router.post("/qq/login", response_model=LoginResponse)
def qq_login(
    login_data: QQLoginRequest,
    response: Response,
    database_session: Session = Depends(get_db),
) -> LoginResponse:
    """用本地模拟QQ授权码登录已绑定的测试账号。"""

    # 真实接入时，这里应调用QQ互联接口，用临时 code 换取 openid。
    if login_data.code != QQ_DEMO_AUTHORIZATION_CODE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="QQ授权失败，请重新授权",
        )

    user = database_session.scalar(
        select(User).where(
            User.qq_openid == QQ_DEMO_OPENID,
            User.status == "active",
        )
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="QQ账号未绑定或系统账号已被停用",
        )

    create_login_session(user, response, database_session)
    return LoginResponse(
        message="QQ登录成功",
        user=CurrentUserResponse.model_validate(user),
    )


@router.get("/me", response_model=CurrentUserResponse)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> CurrentUserResponse:
    """返回当前浏览器所登录的用户。"""

    return CurrentUserResponse.model_validate(current_user)


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    database_session: Session = Depends(get_db),
) -> MessageResponse:
    """删除当前登录会话和浏览器 Cookie。"""

    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        database_session.execute(
            delete(LoginSession).where(
                LoginSession.token_hash == hash_session_token(session_token)
            )
        )
        database_session.commit()

    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return MessageResponse(message="已退出登录")
