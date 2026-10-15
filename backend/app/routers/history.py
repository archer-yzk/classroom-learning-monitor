"""教师历史学情组合查询接口。"""

from datetime import datetime

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.core.time import china_now_naive, normalize_utc_naive
from backend.app.database import get_db
from backend.app.dependencies.auth import require_role
from backend.app.models import StatisticsSnapshot, User
from backend.app.schemas.history import (
    HistoryQueryResponse,
    HistorySnapshotResponse,
)
from backend.app.schemas.statistics import ScoreCountResponse
from backend.app.services.excel_service import build_history_excel
from backend.app.services.feedback_service import FEEDBACK_OPTIONS
from backend.app.services.history_service import query_teacher_history_rows


router = APIRouter(prefix="/api/statistics", tags=["学情统计"])


def build_score_counts(snapshot: StatisticsSnapshot) -> list[ScoreCountResponse]:
    """把数据库中的六个计数字段整理成前端容易使用的列表。"""

    return [
        ScoreCountResponse(
            score=score,
            emoji=FEEDBACK_OPTIONS[score]["emoji"],
            label=FEEDBACK_OPTIONS[score]["label"],
            count=getattr(snapshot, f"score_{score}_count"),
        )
        for score in range(6, 0, -1)
    ]


@router.get("/history", response_model=HistoryQueryResponse)
def read_history_statistics(
    course_name: str | None = Query(default=None, max_length=100),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    teacher: User = Depends(require_role("teacher")),
    database_session: Session = Depends(get_db),
) -> HistoryQueryResponse:
    """按课程名称和实际上课时间查询当前教师自己的历史快照。"""

    start_time = normalize_utc_naive(start_time)
    end_time = normalize_utc_naive(end_time)
    rows = query_teacher_history_rows(
        database_session=database_session,
        teacher_id=teacher.id,
        course_name=course_name,
        start_time=start_time,
        end_time=end_time,
    )
    records = [
        HistorySnapshotResponse(
            snapshot_id=snapshot.id,
            session_id=classroom.id,
            course_name=course.name,
            class_name=classroom.class_name,
            topic=classroom.topic,
            class_start_time=classroom.start_time,
            period_start=snapshot.period_start,
            period_end=snapshot.period_end,
            interval_minutes=snapshot.interval_minutes,
            total_students=snapshot.total_students,
            score_counts=build_score_counts(snapshot),
            average_score=snapshot.average_score,
            variance=snapshot.variance,
        )
        for snapshot, classroom, course in rows
    ]

    return HistoryQueryResponse(total=len(records), records=records)


@router.get("/history/export", response_class=StreamingResponse)
def export_history_statistics(
    course_name: str | None = Query(default=None, max_length=100),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    teacher: User = Depends(require_role("teacher")),
    database_session: Session = Depends(get_db),
) -> StreamingResponse:
    """把当前教师的历史组合查询结果下载为 Excel 文件。"""

    start_time = normalize_utc_naive(start_time)
    end_time = normalize_utc_naive(end_time)
    rows = query_teacher_history_rows(
        database_session=database_session,
        teacher_id=teacher.id,
        course_name=course_name,
        start_time=start_time,
        end_time=end_time,
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="没有可导出的历史统计记录",
        )

    exported_at = china_now_naive()
    file_stream = build_history_excel(
        rows=rows,
        teacher_name=teacher.name,
        course_name=course_name,
        start_time=start_time,
        end_time=end_time,
        exported_at=exported_at,
    )
    filename = f"学情历史_{exported_at.strftime('%Y%m%d_%H%M%S')}.xlsx"
    encoded_filename = quote(filename)

    return StreamingResponse(
        file_stream,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f"attachment; filename=classroom_history.xlsx; "
                f"filename*=UTF-8''{encoded_filename}"
            )
        },
    )
