"""学情预警的业务规则。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import FeedbackRecord, LearningAlert


ALERT_SCORE_THRESHOLD = 2


def create_or_update_learning_alert(
    feedback_record: FeedbackRecord,
    database_session: Session,
) -> LearningAlert | None:
    """为低分反馈创建预警，或更新同课堂已有的待处理预警。"""

    if feedback_record.score > ALERT_SCORE_THRESHOLD:
        return None

    pending_alert = database_session.scalar(
        select(LearningAlert)
        .where(
            LearningAlert.session_id == feedback_record.session_id,
            LearningAlert.student_id == feedback_record.student_id,
            LearningAlert.status == "pending",
        )
        .order_by(LearningAlert.updated_at.desc(), LearningAlert.id.desc())
        .limit(1)
    )
    if pending_alert is not None:
        # 连续低分更新同一条待处理预警，避免教师列表出现重复事项。
        pending_alert.latest_feedback_id = feedback_record.id
        pending_alert.latest_score = feedback_record.score
        return pending_alert

    learning_alert = LearningAlert(
        session_id=feedback_record.session_id,
        student_id=feedback_record.student_id,
        latest_feedback_id=feedback_record.id,
        latest_score=feedback_record.score,
        status="pending",
    )
    database_session.add(learning_alert)
    return learning_alert
