"""SQLite 与 SQLAlchemy 的公共配置。"""

from collections.abc import Generator
import os
from pathlib import Path
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_PATH_ENV = "CLASSROOM_MONITOR_DATABASE"
configured_database_path = os.environ.get(DATABASE_PATH_ENV)
DATABASE_FILE = (
    Path(configured_database_path).expanduser().resolve()
    if configured_database_path
    else DATABASE_DIR / "classroom_monitor.db"
)

# 确保数据库目录存在。SQLite 会在首次连接时创建数据库文件。
DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite+pysqlite:///{DATABASE_FILE.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },
)


@event.listens_for(engine, "connect")
def configure_sqlite(dbapi_connection: SQLiteConnection, _connection_record: object) -> None:
    """为每个 SQLite 连接启用外键和等待锁机制。"""

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA busy_timeout = 30000")
    cursor.close()


class Base(DeclarativeBase):
    """所有 SQLAlchemy 数据表模型的共同基类。"""


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """为一次接口请求提供数据库会话，并在结束后自动关闭。"""

    database_session = SessionLocal()
    try:
        yield database_session
    finally:
        database_session.close()
