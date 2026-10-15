"""创建数据库表并写入最小测试数据。

运行方式：python -m scripts.init_db
"""

from datetime import timedelta

from sqlalchemy import func, select

from backend.app.core.password import hash_password
from backend.app.core.session import utc_now_without_timezone
from backend.app.core.third_party import QQ_DEMO_OPENID, WECHAT_DEMO_OPENID
from backend.app.database import Base, DATABASE_FILE, SessionLocal, engine
from backend.app.models import Course, CourseSession, StatisticsSetting, User


TEST_USERS = (
    {
        "role": "student",
        "username": "student001",
        "student_no": "20260001",
        "name": "张三",
        "age": 20,
        "gender": "男",
        "grade": "2026级",
        "class_name": "软件工程1班",
        "major": "软件工程",
        "phone": "13800000001",
    },
    {
        "role": "teacher",
        "username": "teacher001",
        "name": "李老师",
        "age": 35,
        "gender": "女",
        "phone": "13800000002",
    },
    {
        "role": "admin",
        "username": "admin001",
        "name": "系统管理员",
        "age": 30,
        "gender": "男",
        "phone": "13800000003",
    },
)


def initialize_database() -> None:
    """建立缺失的数据表，并补充尚不存在的测试账号。"""

    Base.metadata.create_all(bind=engine)

    created_user_count = 0
    created_course_count = 0
    created_session_count = 0
    created_setting_count = 0
    created_wechat_binding_count = 0
    created_qq_binding_count = 0
    with SessionLocal() as database_session:
        for user_data in TEST_USERS:
            existing_user = database_session.scalar(
                select(User).where(User.username == user_data["username"])
            )
            if existing_user is not None:
                continue

            database_session.add(
                User(
                    **user_data,
                    password_hash=hash_password("123456"),
                )
            )
            created_user_count += 1

        database_session.commit()

        student = database_session.scalar(
            select(User).where(User.username == "student001")
        )
        if student is None:
            raise RuntimeError("未找到测试学生 student001")
        if student.wechat_openid is None:
            student.wechat_openid = WECHAT_DEMO_OPENID
            created_wechat_binding_count = 1
            database_session.commit()

        teacher = database_session.scalar(
            select(User).where(User.username == "teacher001")
        )
        if teacher is None:
            raise RuntimeError("未找到测试教师 teacher001")
        if teacher.qq_openid is None:
            teacher.qq_openid = QQ_DEMO_OPENID
            created_qq_binding_count = 1
            database_session.commit()

        course = database_session.scalar(
            select(Course).where(
                Course.name == "Python 程序设计",
                Course.teacher_id == teacher.id,
            )
        )
        if course is None:
            course = Course(
                name="Python 程序设计",
                teacher_id=teacher.id,
                description="课堂学情监控管理系统测试课程",
            )
            database_session.add(course)
            database_session.flush()
            created_course_count = 1

        active_classroom = database_session.scalar(
            select(CourseSession).where(
                CourseSession.course_id == course.id,
                CourseSession.class_name == "软件工程1班",
                CourseSession.status == "active",
            )
        )
        if active_classroom is None:
            database_session.add(
                CourseSession(
                    course_id=course.id,
                    class_name="软件工程1班",
                    topic="FastAPI 基础",
                    start_time=utc_now_without_timezone() - timedelta(minutes=30),
                    status="active",
                )
            )
            created_session_count = 1

        administrator = database_session.scalar(
            select(User).where(User.username == "admin001")
        )
        if administrator is None:
            raise RuntimeError("未找到测试管理员 admin001")

        statistics_setting = database_session.get(StatisticsSetting, 1)
        if statistics_setting is None:
            statistics_setting = StatisticsSetting(
                id=1,
                interval_minutes=5,
                updated_by=administrator.id,
            )
            database_session.add(statistics_setting)
            created_setting_count = 1

        database_session.commit()

        total_user_count = database_session.scalar(
            select(func.count()).select_from(User)
        ) or 0
        total_course_count = database_session.scalar(
            select(func.count()).select_from(Course)
        ) or 0
        total_session_count = database_session.scalar(
            select(func.count()).select_from(CourseSession)
        ) or 0

    print(f"数据库位置：{DATABASE_FILE}")
    print(f"本次新增测试用户：{created_user_count} 个")
    print(f"当前用户总数：{total_user_count} 个")
    print(f"本次新增课程：{created_course_count} 门")
    print(f"当前课程总数：{total_course_count} 门")
    print(f"本次新增课堂场次：{created_session_count} 个")
    print(f"当前课堂场次总数：{total_session_count} 个")
    print(f"本次新增统计配置：{created_setting_count} 个")
    print(f"当前统计周期：{statistics_setting.interval_minutes} 分钟")
    print(f"本次新增微信测试绑定：{created_wechat_binding_count} 个")
    print("微信登录测试账号：student001")
    print(f"本次新增QQ测试绑定：{created_qq_binding_count} 个")
    print("QQ登录测试账号：teacher001")
    print("测试账号：student001、teacher001、admin001")
    print("测试密码：123456")


if __name__ == "__main__":
    initialize_database()
