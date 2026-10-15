"""系统时区转换工具。

数据库统一保存无时区 UTC；只有在人机界面和报表输出时转换为北京时间。
"""

from datetime import UTC, datetime, timedelta, timezone


CHINA_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")


def normalize_utc_naive(value: datetime | None) -> datetime | None:
    """把带时区时间转成无时区 UTC；无时区值按已是 UTC 处理。"""

    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def utc_naive_to_china(value: datetime | None) -> datetime | None:
    """把数据库中的无时区 UTC 转成 Excel 可写入的无时区北京时间。"""

    if value is None:
        return None
    utc_value = normalize_utc_naive(value)
    if utc_value is None:
        return None
    return (
        utc_value.replace(tzinfo=UTC)
        .astimezone(CHINA_TIMEZONE)
        .replace(tzinfo=None)
    )


def china_now_naive() -> datetime:
    """返回不带时区信息的当前北京时间，供文件名和报表展示使用。"""

    return datetime.now(CHINA_TIMEZONE).replace(tzinfo=None)
