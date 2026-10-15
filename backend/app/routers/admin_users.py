"""管理员用户查询接口。"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.password import hash_password
from backend.app.database import get_db
from backend.app.dependencies.auth import require_role
from backend.app.models import (
    Course,
    DiscussionMessage,
    FeedbackRecord,
    LoginSession,
    StatisticsSetting,
    User,
)
from backend.app.schemas.admin_user import (
    AdminUserCreate,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserStatusUpdate,
    AdminUserUpdate,
)
from backend.app.schemas.auth import MessageResponse


router = APIRouter(prefix="/api/admin/users", tags=["管理员用户管理"])


def user_has_business_records(user_id: int, database_session: Session) -> bool:
    """检查用户是否已被课堂或系统业务数据引用。"""

    reference_queries = (
        select(Course.id).where(Course.teacher_id == user_id).limit(1),
        select(FeedbackRecord.id)
        .where(FeedbackRecord.student_id == user_id)
        .limit(1),
        select(DiscussionMessage.id)
        .where(DiscussionMessage.user_id == user_id)
        .limit(1),
        select(StatisticsSetting.id)
        .where(StatisticsSetting.updated_by == user_id)
        .limit(1),
    )
    return any(
        database_session.scalar(query) is not None
        for query in reference_queries
    )


@router.get("", response_model=AdminUserListResponse)
def read_admin_users(
    role: Literal["student", "teacher", "admin"] | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=50),
    _administrator: User = Depends(require_role("admin")),
    database_session: Session = Depends(get_db),
) -> AdminUserListResponse:
    """按角色和关键词查询三类用户。"""

    filters = []
    if role is not None:
        filters.append(User.role == role)

    cleaned_keyword = keyword.strip() if keyword else ""
    if cleaned_keyword:
        # 关键词同时匹配常用身份字段，方便管理员快速定位用户。
        filters.append(
            or_(
                User.username.contains(cleaned_keyword),
                User.name.contains(cleaned_keyword),
                User.student_no.contains(cleaned_keyword),
                User.phone.contains(cleaned_keyword),
            )
        )

    total = database_session.scalar(
        select(func.count()).select_from(User).where(*filters)
    ) or 0
    users = list(
        database_session.scalars(
            select(User).where(*filters).order_by(User.id.asc())
        )
    )
    return AdminUserListResponse(total=total, users=users)


@router.post(
    "",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_user(
    user_data: AdminUserCreate,
    _administrator: User = Depends(require_role("admin")),
    database_session: Session = Depends(get_db),
) -> User:
    """创建学生、教师或管理员账号，并保存密码散列。"""

    duplicate_conditions = [
        User.username == user_data.username,
        User.phone == user_data.phone,
    ]
    if user_data.student_no:
        duplicate_conditions.append(User.student_no == user_data.student_no)

    duplicate_user = database_session.scalar(
        select(User).where(or_(*duplicate_conditions))
    )
    if duplicate_user is not None:
        if duplicate_user.username == user_data.username:
            detail = "登录账号已存在"
        elif duplicate_user.phone == user_data.phone:
            detail = "联系方式已存在"
        else:
            detail = "学号已存在"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )

    user = User(
        role=user_data.role,
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        student_no=user_data.student_no,
        name=user_data.name,
        age=user_data.age,
        gender=user_data.gender,
        grade=user_data.grade,
        class_name=user_data.class_name,
        major=user_data.major,
        phone=user_data.phone,
        status="active",
    )
    database_session.add(user)
    try:
        database_session.commit()
    except IntegrityError as error:
        # 防止两次请求几乎同时创建相同账号时绕过前面的友好检查。
        database_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="账号、学号或联系方式已存在",
        ) from error

    database_session.refresh(user)
    return user


@router.put("/{user_id}", response_model=AdminUserResponse)
def update_admin_user(
    user_id: int,
    user_data: AdminUserUpdate,
    _administrator: User = Depends(require_role("admin")),
    database_session: Session = Depends(get_db),
) -> User:
    """修改用户资料，账号角色和启用状态在本步骤中保持不变。"""

    user = database_session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if user.role == "student":
        if not all(
            (
                user_data.student_no,
                user_data.grade,
                user_data.class_name,
                user_data.major,
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="学生必须填写学号、年级、班级和专业",
            )
    else:
        # 教师和管理员不保存学生专属字段。
        user_data.student_no = None
        user_data.grade = None
        user_data.class_name = None
        user_data.major = None

    duplicate_conditions = [
        User.username == user_data.username,
        User.phone == user_data.phone,
    ]
    if user_data.student_no:
        duplicate_conditions.append(User.student_no == user_data.student_no)

    duplicate_user = database_session.scalar(
        select(User).where(
            User.id != user_id,
            or_(*duplicate_conditions),
        )
    )
    if duplicate_user is not None:
        if duplicate_user.username == user_data.username:
            detail = "登录账号已存在"
        elif duplicate_user.phone == user_data.phone:
            detail = "联系方式已存在"
        else:
            detail = "学号已存在"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )

    user.username = user_data.username
    user.student_no = user_data.student_no
    user.name = user_data.name
    user.age = user_data.age
    user.gender = user_data.gender
    user.grade = user_data.grade
    user.class_name = user_data.class_name
    user.major = user_data.major
    user.phone = user_data.phone
    if user_data.password is not None:
        user.password_hash = hash_password(user_data.password)

    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="账号、学号或联系方式已存在",
        ) from error

    database_session.refresh(user)
    return user


@router.patch("/{user_id}/status", response_model=AdminUserResponse)
def update_admin_user_status(
    user_id: int,
    status_data: AdminUserStatusUpdate,
    administrator: User = Depends(require_role("admin")),
    database_session: Session = Depends(get_db),
) -> User:
    """启用或停用账号；停用后立即清除该账号的登录会话。"""

    user = database_session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if user.id == administrator.id and status_data.status == "disabled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能停用当前登录的管理员账号",
        )

    user.status = status_data.status
    if status_data.status == "disabled":
        database_session.execute(
            delete(LoginSession).where(LoginSession.user_id == user.id)
        )
    database_session.commit()
    database_session.refresh(user)
    return user


@router.delete("/{user_id}", response_model=MessageResponse)
def delete_admin_user(
    user_id: int,
    administrator: User = Depends(require_role("admin")),
    database_session: Session = Depends(get_db),
) -> MessageResponse:
    """永久删除没有业务记录的账号。"""

    user = database_session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if user.id == administrator.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除当前登录的管理员账号",
        )

    if user_has_business_records(user.id, database_session):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该用户已有课堂或系统记录，不能删除，请改为停用",
        )

    user_label = f"{user.name}（{user.username}）"
    # 登录会话不是业务历史，删除账号时一并清理。
    database_session.execute(
        delete(LoginSession).where(LoginSession.user_id == user.id)
    )
    database_session.delete(user)
    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该用户仍有关联数据，不能删除，请改为停用",
        ) from error

    return MessageResponse(message=f"已删除用户：{user_label}")
