"""集中导入数据表模型，确保 SQLAlchemy 能发现这些表。"""

from backend.app.models.course import Course
from backend.app.models.course_session import CourseSession
from backend.app.models.discussion_message import DiscussionMessage
from backend.app.models.feedback_record import FeedbackRecord
from backend.app.models.learning_alert import LearningAlert
from backend.app.models.login_session import LoginSession
from backend.app.models.sms_verification_code import SmsVerificationCode
from backend.app.models.statistics_setting import StatisticsSetting
from backend.app.models.statistics_snapshot import StatisticsSnapshot
from backend.app.models.user import User

__all__ = [
    "Course",
    "CourseSession",
    "DiscussionMessage",
    "FeedbackRecord",
    "LearningAlert",
    "LoginSession",
    "SmsVerificationCode",
    "StatisticsSetting",
    "StatisticsSnapshot",
    "User",
]
