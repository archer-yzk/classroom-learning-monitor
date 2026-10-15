"""课堂学情监控管理系统的 FastAPI 应用入口。"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from starlette.middleware.gzip import GZipMiddleware

from backend.app.database import Base, SessionLocal, engine
from backend.app.models import User
from backend.app.routers.admin_courses import (
    classroom_router as admin_classrooms_router,
    router as admin_courses_router,
)
from backend.app.routers.admin_statistics import router as admin_statistics_router
from backend.app.routers.admin_users import router as admin_users_router
from backend.app.routers.auth import router as auth_router
from backend.app.routers.classrooms import router as classrooms_router
from backend.app.routers.discussions import router as discussions_router
from backend.app.routers.feedbacks import router as feedbacks_router
from backend.app.routers.history import router as history_router
from backend.app.routers.learning_alerts import (
    router as learning_alerts_router,
    student_router as student_learning_alerts_router,
)
from backend.app.routers.pages import router as pages_router
from backend.app.routers.statistics import router as statistics_router
from backend.app.schemas.system import HealthResponse
from backend.app.services.snapshot_service import run_snapshot_scheduler


# main.py 位于 backend/app/，向上两级就是项目根目录。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """启动数据表检查和定时快照任务，并在关闭时安全停止。"""

    Base.metadata.create_all(bind=engine)
    scheduler_task = asyncio.create_task(run_snapshot_scheduler())
    try:
        yield
    finally:
        scheduler_task.cancel()
        with suppress(asyncio.CancelledError):
            await scheduler_task


app = FastAPI(
    title="课堂学情监控管理系统",
    description="用于课堂学情反馈、统计与师生互动的课程项目",
    version="0.1.0",
    lifespan=lifespan,
)

# 压缩较大的 JSON、HTML、CSS、JavaScript 和本地 ECharts 文件，显著减少
# 首次打开教师图表页时的传输体积。
app.add_middleware(GZipMiddleware, minimum_size=500, compresslevel=6)


@app.middleware("http")
async def add_response_headers(request: Request, call_next):
    """补充浏览器安全响应头，并为不同资源设置合适的缓存策略。"""

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )

    request_path = request.url.path
    protected_pages = {"/student", "/teacher", "/teacher/history", "/admin"}
    if request_path.startswith("/api/") or request_path in protected_pages:
        # 接口包含登录状态和课堂数据，不允许浏览器或中间缓存保存。
        response.headers["Cache-Control"] = "no-store"
    elif request_path.startswith("/static/vendor/"):
        # 第三方版本化资源不会在运行时变化，可长期缓存。
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

    return response

# 将前端静态资源映射到 /static 地址。
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR / "static"),
    name="static",
)

app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(classrooms_router)
app.include_router(discussions_router)
app.include_router(feedbacks_router)
app.include_router(statistics_router)
app.include_router(history_router)
app.include_router(learning_alerts_router)
app.include_router(student_learning_alerts_router)
app.include_router(admin_courses_router)
app.include_router(admin_classrooms_router)
app.include_router(admin_statistics_router)
app.include_router(admin_users_router)


@app.get("/api/health", tags=["系统"], response_model=HealthResponse)
async def health_check() -> dict[str, str | int]:
    """确认后端和数据库是否正常运行。"""

    with SessionLocal() as database_session:
        user_count = database_session.scalar(
            select(func.count()).select_from(User)
        ) or 0

    return {
        "status": "ok",
        "message": "课堂学情监控管理系统运行正常",
        "database": "ok",
        "user_count": user_count,
    }
