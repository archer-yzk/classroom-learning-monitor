"""学生和教师共用的课堂在线讨论接口。"""

import logging

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies.auth import get_current_user
from backend.app.models import Course, CourseSession, DiscussionMessage, User
from backend.app.schemas.discussion import (
    DiscussionMessageCreate,
    DiscussionMessageListResponse,
    DiscussionMessageResponse,
)
from backend.app.services.discussion_image_service import (
    MAX_IMAGE_SIZE,
    InvalidDiscussionImageError,
    save_discussion_image,
)


router = APIRouter(prefix="/api/discussions", tags=["在线讨论"])
LOGGER = logging.getLogger(__name__)


def get_accessible_classroom(
    session_id: int,
    current_user: User,
    database_session: Session,
) -> CourseSession:
    """确认当前用户能够进入指定的进行中课堂。"""

    classroom = database_session.get(CourseSession, session_id)
    if classroom is None or classroom.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课堂不存在或已经结束",
        )

    course = database_session.get(Course, classroom.course_id)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在",
        )

    if current_user.role == "student":
        if classroom.class_name != current_user.class_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="不能进入其他班级的讨论区",
            )
    elif current_user.role == "teacher":
        if course.teacher_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="不能进入其他教师课堂的讨论区",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理员不参与课堂讨论",
        )

    return classroom


def build_message_response(
    message: DiscussionMessage,
    sender: User,
    current_user_id: int,
) -> DiscussionMessageResponse:
    """把消息和发送人信息组合成前端需要的数据。"""

    return DiscussionMessageResponse(
        id=message.id,
        session_id=message.session_id,
        sender_id=sender.id,
        sender_name=sender.name,
        sender_role=sender.role,
        content=message.content,
        image_url=(f"/static/{message.image_path}" if message.image_path else None),
        is_mine=sender.id == current_user_id,
        created_at=message.created_at,
    )


@router.get(
    "/{session_id}/messages",
    response_model=DiscussionMessageListResponse,
)
def read_discussion_messages(
    session_id: int,
    after_id: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> DiscussionMessageListResponse:
    """读取课堂最近消息，轮询时只返回指定编号之后的新消息。"""

    get_accessible_classroom(session_id, current_user, database_session)
    statement = (
        select(DiscussionMessage, User)
        .join(User, DiscussionMessage.user_id == User.id)
        .where(DiscussionMessage.session_id == session_id)
    )

    if after_id > 0:
        rows = database_session.execute(
            statement.where(DiscussionMessage.id > after_id)
            .order_by(DiscussionMessage.id.asc())
            .limit(100)
        ).all()
    else:
        # 初次打开只取最近 100 条，再反转成从旧到新的显示顺序。
        rows = list(
            reversed(
                database_session.execute(
                    statement.order_by(DiscussionMessage.id.desc()).limit(100)
                ).all()
            )
        )

    return DiscussionMessageListResponse(
        session_id=session_id,
        messages=[
            build_message_response(message, sender, current_user.id)
            for message, sender in rows
        ],
    )


@router.post(
    "/{session_id}/messages",
    response_model=DiscussionMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_discussion_message(
    session_id: int,
    message_data: DiscussionMessageCreate,
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> DiscussionMessageResponse:
    """以当前登录用户身份保存一条文字消息。"""

    get_accessible_classroom(session_id, current_user, database_session)
    message = DiscussionMessage(
        session_id=session_id,
        user_id=current_user.id,
        content=message_data.content,
    )
    database_session.add(message)
    database_session.commit()
    database_session.refresh(message)
    return build_message_response(message, current_user, current_user.id)


@router.post(
    "/{session_id}/images",
    response_model=DiscussionMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_discussion_image_message(
    session_id: int,
    image: Annotated[UploadFile, File(description="课堂讨论图片")],
    content: Annotated[str | None, Form(max_length=500)] = None,
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> DiscussionMessageResponse:
    """保存一条图片消息，允许同时附带简短文字。"""

    get_accessible_classroom(session_id, current_user, database_session)

    try:
        # 多读 1 字节，用来判断文件是否超过上限。
        image_data = await image.read(MAX_IMAGE_SIZE + 1)
    finally:
        await image.close()

    if not image_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="请选择要上传的图片",
        )
    if len(image_data) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="图片不能超过 5 MB",
        )

    cleaned_content = content.strip() if content else None
    try:
        absolute_path, relative_path = save_discussion_image(
            session_id,
            image_data,
        )
    except InvalidDiscussionImageError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    message = DiscussionMessage(
        session_id=session_id,
        user_id=current_user.id,
        content=cleaned_content or None,
        image_path=relative_path,
    )
    try:
        database_session.add(message)
        database_session.commit()
        database_session.refresh(message)
    except SQLAlchemyError:
        database_session.rollback()
        try:
            absolute_path.unlink(missing_ok=True)
        except OSError:
            LOGGER.exception("讨论消息写入失败后无法清理图片：%s", absolute_path)
        raise

    return build_message_response(message, current_user, current_user.id)
