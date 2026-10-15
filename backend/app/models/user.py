"""用户数据表模型。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class User(Base):
    """统一保存学生、教师和管理员三种角色。"""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('student', 'teacher', 'admin')",
            name="ck_users_role",
        ),
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_users_status",
        ),
        CheckConstraint(
            "age IS NULL OR (age >= 1 AND age <= 120)",
            name="ck_users_age",
        ),
        CheckConstraint(
            "role != 'student' OR "
            "(student_no IS NOT NULL AND grade IS NOT NULL "
            "AND class_name IS NOT NULL AND major IS NOT NULL)",
            name="ck_student_required_fields",
        ),
        Index("ix_users_role", "role"),
        Index("ix_users_class_name", "class_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    student_no: Mapped[str | None] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(20))
    grade: Mapped[str | None] = mapped_column(String(30))
    class_name: Mapped[str | None] = mapped_column(String(100))
    major: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)

    # 后续接入第三方认证时保存平台返回的用户唯一标识。
    wechat_openid: Mapped[str | None] = mapped_column(String(100), unique=True)
    qq_openid: Mapped[str | None] = mapped_column(String(100), unique=True)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
