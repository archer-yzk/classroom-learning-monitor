"""学生学情反馈接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies.auth import require_role
from backend.app.models import CourseSession, FeedbackRecord, User
from backend.app.schemas.feedback import (
    CurrentFeedbackResponse,
    FeedbackCreate,
    FeedbackOptionResponse,
    FeedbackResponse,
)
from backend.app.services.feedback_service import FEEDBACK_OPTIONS, get_feedback_option
from backend.app.services.learning_alert_service import (
    create_or_update_learning_alert,
)


router = APIRouter(prefix="/api/feedbacks", tags=["学情反馈"])


def get_student_classroom(
    session_id: int,
    student: User,
    database_session: Session,
) -> CourseSession:
    """确认课堂存在、正在进行，并且属于当前学生班级。"""

    classroom = database_session.get(CourseSession, session_id)
    if classroom is None or classroom.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课堂不存在或已经结束",
        )
    if classroom.class_name != student.class_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能向其他班级的课堂提交反馈",
        )
    return classroom


def build_feedback_response(record: FeedbackRecord) -> FeedbackResponse:
    """把数据库记录转换成包含表情文字的接口数据。"""

    option = get_feedback_option(record.score)
    return FeedbackResponse(
        id=record.id,
        session_id=record.session_id,
        student_id=record.student_id,
        score=record.score,
        emoji=option["emoji"],
        label=option["label"],
        submitted_at=record.submitted_at,
    )


@router.get("/options", response_model=list[FeedbackOptionResponse])
def read_feedback_options(
    _student: User = Depends(require_role("student")),
) -> list[FeedbackOptionResponse]:
    """返回固定的六级表情选项。"""

    return [
        FeedbackOptionResponse(score=score, **option)
        for score, option in sorted(FEEDBACK_OPTIONS.items(), reverse=True)
    ]


@router.get(
    "/current/{session_id}",
    response_model=CurrentFeedbackResponse,
)
def read_current_feedback(
    session_id: int,
    student: User = Depends(require_role("student")),
    database_session: Session = Depends(get_db),
) -> CurrentFeedbackResponse:
    """读取学生在当前课堂中最近一次提交的反馈。"""

    get_student_classroom(session_id, student, database_session)
    latest_feedback = database_session.scalar(
        select(FeedbackRecord)
        .where(
            FeedbackRecord.session_id == session_id,
            FeedbackRecord.student_id == student.id,
        )
        .order_by(
            FeedbackRecord.submitted_at.desc(),
            FeedbackRecord.id.desc(),
        )
        .limit(1)
    )

    return CurrentFeedbackResponse(
        session_id=session_id,
        feedback=(
            build_feedback_response(latest_feedback)
            if latest_feedback is not None
            else None
        ),
    )


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def create_feedback(
    feedback_data: FeedbackCreate,
    student: User = Depends(require_role("student")),
    database_session: Session = Depends(get_db),
) -> FeedbackResponse:
    """保存学生的一次学情反馈。"""

    get_student_classroom(feedback_data.session_id, student, database_session)

    feedback_record = FeedbackRecord(
        session_id=feedback_data.session_id,
        student_id=student.id,
        score=feedback_data.score,
    )
    database_session.add(feedback_record)
    # 先取得反馈编号，再让预警与反馈在同一个事务中一起保存。
    database_session.flush()
    create_or_update_learning_alert(feedback_record, database_session)
    database_session.commit()
    database_session.refresh(feedback_record)

    return build_feedback_response(feedback_record)
