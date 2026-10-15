"""周期统计快照生成和后台检查任务。"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.session import utc_now_without_timezone
from backend.app.database import SessionLocal
from backend.app.models import (
    CourseSession,
    StatisticsSetting,
    StatisticsSnapshot,
    User,
)
from backend.app.services.statistics_service import calculate_current_statistics


LOGGER = logging.getLogger(__name__)
SCHEDULER_CHECK_SECONDS = 30


def get_or_create_statistics_setting(
    database_session: Session,
) -> StatisticsSetting:
    """取得唯一统计配置；缺失时使用 5 分钟默认值创建。"""

    setting = database_session.get(StatisticsSetting, 1)
    if setting is not None:
        return setting

    administrator = database_session.scalar(
        select(User).where(User.role == "admin").order_by(User.id)
    )
    if administrator is None:
        raise RuntimeError("系统中没有管理员，无法创建统计周期配置")

    setting = StatisticsSetting(
        id=1,
        interval_minutes=5,
        updated_by=administrator.id,
    )
    database_session.add(setting)
    database_session.flush()
    return setting


def calculate_period_window(
    current_time: datetime,
    interval_minutes: int,
) -> tuple[datetime, datetime]:
    """把当前时间归入固定长度的统计窗口。"""

    aware_time = current_time.replace(tzinfo=UTC)
    interval_seconds = interval_minutes * 60
    current_timestamp = int(aware_time.timestamp())
    start_timestamp = current_timestamp - (current_timestamp % interval_seconds)
    period_start = datetime.fromtimestamp(start_timestamp, UTC).replace(tzinfo=None)
    period_end = period_start + timedelta(minutes=interval_minutes)
    return period_start, period_end


def generate_active_classroom_snapshots() -> int:
    """为全部进行中的课堂生成最近已结束周期的快照。"""

    created_count = 0
    with SessionLocal() as database_session:
        setting = get_or_create_statistics_setting(database_session)
        current_time = utc_now_without_timezone()
        current_period_start, _current_period_end = calculate_period_window(
            current_time,
            setting.interval_minutes,
        )
        period_end = current_period_start
        period_start = period_end - timedelta(minutes=setting.interval_minutes)

        active_session_ids = list(
            database_session.scalars(
                select(CourseSession.id).where(
                    CourseSession.status == "active",
                    CourseSession.start_time < period_end,
                )
            )
        )

        for session_id in active_session_ids:
            existing_snapshot = database_session.scalar(
                select(StatisticsSnapshot.id).where(
                    StatisticsSnapshot.session_id == session_id,
                    StatisticsSnapshot.period_start == period_start,
                    StatisticsSnapshot.interval_minutes == setting.interval_minutes,
                )
            )
            if existing_snapshot is not None:
                continue

            statistics = calculate_current_statistics(
                session_id,
                database_session,
                submitted_before=period_end,
            )
            counts = {
                item.score: item.count for item in statistics.score_counts
            }
            database_session.add(
                StatisticsSnapshot(
                    session_id=session_id,
                    interval_minutes=setting.interval_minutes,
                    period_start=period_start,
                    period_end=period_end,
                    total_students=statistics.total_students,
                    score_1_count=counts[1],
                    score_2_count=counts[2],
                    score_3_count=counts[3],
                    score_4_count=counts[4],
                    score_5_count=counts[5],
                    score_6_count=counts[6],
                    average_score=statistics.average_score,
                    variance=statistics.variance,
                )
            )
            created_count += 1

        database_session.commit()
    return created_count


async def run_snapshot_scheduler() -> None:
    """服务运行期间定期检查是否需要生成新快照。"""

    while True:
        try:
            created_count = await asyncio.to_thread(
                generate_active_classroom_snapshots
            )
            if created_count:
                LOGGER.info("本次定时任务新增 %s 个学情快照", created_count)
        except Exception:
            LOGGER.exception("定时学情快照生成失败")

        await asyncio.sleep(SCHEDULER_CHECK_SECONDS)
