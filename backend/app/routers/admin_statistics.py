"""管理员统计周期配置接口。"""

from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.session import utc_now_without_timezone
from backend.app.database import get_db
from backend.app.dependencies.auth import require_role
from backend.app.models import CourseSession, StatisticsSetting, StatisticsSnapshot, User
from backend.app.schemas.admin_statistics import (
    DailySnapshotCountResponse,
    StatisticsSettingResponse,
    StatisticsSettingUpdate,
)
from backend.app.services.snapshot_service import get_or_create_statistics_setting


router = APIRouter(
    prefix="/api/admin/statistics-settings",
    tags=["管理员统计配置"],
)


def build_setting_response(
    setting: StatisticsSetting,
    database_session: Session,
) -> StatisticsSettingResponse:
    """组合统计周期配置和已经生成的快照状态。"""

    snapshot_count = database_session.scalar(
        select(func.count()).select_from(StatisticsSnapshot)
    ) or 0
    latest_snapshot_at = database_session.scalar(
        select(func.max(StatisticsSnapshot.created_at))
    )
    active_session_count = database_session.scalar(
        select(func.count(CourseSession.id)).where(CourseSession.status == "active")
    ) or 0
    updated_by_name = None
    if setting.updated_by is not None:
        updated_by_name = database_session.scalar(
            select(User.name).where(User.id == setting.updated_by)
        )

    today = utc_now_without_timezone().date()
    first_day = today - timedelta(days=6)
    daily_rows = database_session.execute(
        select(
            func.date(StatisticsSnapshot.created_at),
            func.count(StatisticsSnapshot.id),
        )
        .where(
            StatisticsSnapshot.created_at
            >= datetime.combine(first_day, time.min)
        )
        .group_by(func.date(StatisticsSnapshot.created_at))
    ).all()
    counts_by_day = {str(day): count for day, count in daily_rows}
    recent_daily_snapshots = [
        DailySnapshotCountResponse(
            day=first_day + timedelta(days=offset),
            count=counts_by_day.get(
                str(first_day + timedelta(days=offset)),
                0,
            ),
        )
        for offset in range(7)
    ]
    return StatisticsSettingResponse(
        interval_minutes=setting.interval_minutes,
        updated_at=setting.updated_at,
        snapshot_count=snapshot_count,
        latest_snapshot_at=latest_snapshot_at,
        active_session_count=active_session_count,
        updated_by_name=updated_by_name,
        recent_daily_snapshots=recent_daily_snapshots,
    )


@router.get("", response_model=StatisticsSettingResponse)
def read_statistics_setting(
    _administrator: User = Depends(require_role("admin")),
    database_session: Session = Depends(get_db),
) -> StatisticsSettingResponse:
    """管理员查看统计周期和快照运行状态。"""

    setting = get_or_create_statistics_setting(database_session)
    database_session.commit()
    database_session.refresh(setting)
    return build_setting_response(setting, database_session)


@router.put("", response_model=StatisticsSettingResponse)
def update_statistics_setting(
    setting_data: StatisticsSettingUpdate,
    administrator: User = Depends(require_role("admin")),
    database_session: Session = Depends(get_db),
) -> StatisticsSettingResponse:
    """管理员把统计周期修改为 5 到 10 分钟。"""

    setting = get_or_create_statistics_setting(database_session)
    setting.interval_minutes = setting_data.interval_minutes
    setting.updated_by = administrator.id
    setting.updated_at = utc_now_without_timezone()
    database_session.commit()
    database_session.refresh(setting)
    return build_setting_response(setting, database_session)
