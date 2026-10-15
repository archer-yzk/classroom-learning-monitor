"""登录页和三个角色页面入口。"""

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, RedirectResponse

from backend.app.dependencies.auth import require_role
from backend.app.models import User


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIR = PROJECT_ROOT / "frontend"

router = APIRouter(include_in_schema=False)


@router.get("/")
def root_page() -> RedirectResponse:
    """把系统首页引导到登录页。"""

    return RedirectResponse(url="/login", status_code=303)


@router.get("/login")
def login_page() -> FileResponse:
    """返回公共登录页。"""

    return FileResponse(FRONTEND_DIR / "index.html")


@router.get("/student")
def student_page(
    _current_user: User = Depends(require_role("student")),
) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "student.html")


@router.get("/teacher")
def teacher_page(
    _current_user: User = Depends(require_role("teacher")),
) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "teacher.html")


@router.get("/teacher/history")
def teacher_history_page(
    _current_user: User = Depends(require_role("teacher")),
) -> FileResponse:
    """返回仅教师可以访问的历史学情页面。"""

    return FileResponse(FRONTEND_DIR / "history.html")


@router.get("/admin")
def admin_page(
    _current_user: User = Depends(require_role("admin")),
) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "admin.html")
