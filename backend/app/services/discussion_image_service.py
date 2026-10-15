"""课堂讨论图片的检查和本地保存。"""

from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
UPLOAD_RELATIVE_ROOT = Path("uploads") / "discussions"
UPLOAD_ABSOLUTE_ROOT = PROJECT_ROOT / "frontend" / "static" / UPLOAD_RELATIVE_ROOT
MAX_IMAGE_SIZE = 5 * 1024 * 1024


class InvalidDiscussionImageError(ValueError):
    """表示上传内容不是系统允许的真实图片格式。"""


def detect_image_extension(image_data: bytes) -> str:
    """根据文件头判断真实格式，不信任用户提供的扩展名。"""

    if image_data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if image_data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if (
        len(image_data) >= 12
        and image_data[:4] == b"RIFF"
        and image_data[8:12] == b"WEBP"
    ):
        return "webp"
    raise InvalidDiscussionImageError("只允许上传 JPEG、PNG、GIF 或 WebP 图片")


def save_discussion_image(
    session_id: int,
    image_data: bytes,
) -> tuple[Path, str]:
    """使用随机文件名保存图片，返回绝对路径和数据库相对路径。"""

    extension = detect_image_extension(image_data)
    session_directory = UPLOAD_ABSOLUTE_ROOT / str(session_id)
    session_directory.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}.{extension}"
    absolute_path = session_directory / filename
    absolute_path.write_bytes(image_data)

    relative_path = (UPLOAD_RELATIVE_ROOT / str(session_id) / filename).as_posix()
    return absolute_path, relative_path
