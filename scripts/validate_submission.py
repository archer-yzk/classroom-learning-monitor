"""提交前质量检查：源码、文档、截图、数据库和必备报告。"""

from __future__ import annotations

import argparse
import re
import sqlite3
import struct
from pathlib import Path
from urllib.parse import unquote, urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md",
    "requirements.txt",
    "run.bat",
    "产品要求文档.pdf",
    "课堂学情监控管理系统大作业清单.pdf",
    "backend/app/main.py",
    "frontend/index.html",
    "frontend/student.html",
    "frontend/teacher.html",
    "frontend/history.html",
    "frontend/admin.html",
    "frontend/static/js/api.js",
    "database/schema.sql",
    "database/seed.sql",
    "database/classroom_monitor.db",
    "docs/用户使用手册.md",
    "docs/系统安装调试手册.md",
    "docs/自主新增业务模块说明.md",
    "docs/AI使用情况报告.md",
    "docs/提交前检查清单.md",
    "docs/全系统验收基线.md",
    "scripts/init_db.py",
    "scripts/smoke_test.py",
    "scripts/validate_submission.py",
    "scripts/package_submission.ps1",
    "tests/test_statistics.py",
)
SCREENSHOTS = (
    "01_登录页面.png",
    "02_学生学情反馈.jpg",
    "03_学生学情提醒.jpg",
    "04_学生在线讨论.jpg",
    "05_教师实时统计与图表.jpg",
    "06_教师学情预警跟进.jpg",
    "07_教师在线讨论.jpg",
    "08_历史学情查询.jpg",
    "09_管理员用户管理.jpg",
    "10_管理员统计周期.jpg",
    "11_学生移动端适配.jpg",
)
EXPECTED_TABLES = {
    "users",
    "login_sessions",
    "sms_verification_codes",
    "courses",
    "course_sessions",
    "feedback_records",
    "statistics_settings",
    "statistics_snapshots",
    "discussion_messages",
    "learning_alerts",
}
PERSONAL_INFO_PLACEHOLDERS = {
    "docs/待填写个人信息.md": ("[待填写]",),
    "docs/AI使用情况报告.md": (
        "[请填写本人姓名]",
        "[请填写本人学号]",
        "[请填写本人班级]",
        "[请本人签名]",
        "[请填写实际签字日期]",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查课程项目提交材料")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="最终打包模式：个人信息占位符也视为失败",
    )
    return parser.parse_args()


def image_dimensions(image_path: Path) -> tuple[int, int] | None:
    """不依赖第三方库读取 PNG/JPEG 尺寸。"""

    data = image_path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if not data.startswith(b"\xff\xd8"):
        return None

    offset = 2
    start_of_frame_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 2 > len(data):
            break
        segment_length = int.from_bytes(data[offset : offset + 2], "big")
        if segment_length < 2 or offset + segment_length > len(data):
            break
        if marker in start_of_frame_markers and segment_length >= 7:
            height = int.from_bytes(data[offset + 3 : offset + 5], "big")
            width = int.from_bytes(data[offset + 5 : offset + 7], "big")
            return width, height
        offset += segment_length
    return None


def validate_markdown_links(errors: list[str]) -> int:
    """检查 README 与 docs 中的本地链接和图片是否存在。"""

    markdown_paths = [PROJECT_ROOT / "README.md"]
    markdown_paths.extend(sorted((PROJECT_ROOT / "docs").glob("*.md")))
    link_count = 0
    pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for markdown_path in markdown_paths:
        content = markdown_path.read_text(encoding="utf-8")
        for raw_target in pattern.findall(content):
            target = raw_target.strip()
            if target.startswith("<") and ">" in target:
                target = target[1 : target.index(">")]
            else:
                target = target.split(maxsplit=1)[0]
            if not target or target.startswith("#"):
                continue
            split_target = urlsplit(target)
            if split_target.scheme in {"http", "https", "mailto", "tel", "data"}:
                continue
            link_count += 1
            decoded_path = unquote(split_target.path)
            resolved_target = (markdown_path.parent / decoded_path).resolve()
            if not resolved_target.is_file():
                errors.append(
                    f"Markdown 本地链接不存在：{markdown_path.relative_to(PROJECT_ROOT)} -> {target}"
                )
    return link_count


def validate_python_sources(errors: list[str]) -> int:
    """直接编译源码文本，检查语法且不生成 __pycache__。"""

    source_paths = sorted((PROJECT_ROOT / "backend").rglob("*.py"))
    source_paths.extend(sorted((PROJECT_ROOT / "scripts").rglob("*.py")))
    source_paths.extend(sorted((PROJECT_ROOT / "tests").rglob("*.py")))
    for source_path in source_paths:
        try:
            source = source_path.read_text(encoding="utf-8")
            compile(source, str(source_path), "exec")
        except (OSError, SyntaxError, UnicodeError) as error:
            errors.append(
                f"Python 源码检查失败：{source_path.relative_to(PROJECT_ROOT)} -> {error}"
            )
    return len(source_paths)


def validate_frontend_assets(errors: list[str]) -> int:
    """检查页面引用的本地 CSS、JavaScript 和静态文件。"""

    reference_count = 0
    pattern = re.compile(r'(?:src|href)="(/static/[^"?#]+)(?:[?#][^"]*)?"')
    for html_path in sorted((PROJECT_ROOT / "frontend").glob("*.html")):
        content = html_path.read_text(encoding="utf-8")
        for asset_path in pattern.findall(content):
            reference_count += 1
            resolved_asset = PROJECT_ROOT / "frontend" / "static" / asset_path.removeprefix("/static/")
            if not resolved_asset.is_file():
                errors.append(
                    f"前端静态资源不存在：{html_path.name} -> {asset_path}"
                )
    return reference_count


def validate_database(errors: list[str]) -> tuple[int, int, int]:
    database_path = PROJECT_ROOT / "database" / "classroom_monitor.db"
    if not database_path.is_file():
        return 0, 0, 0

    with sqlite3.connect(database_path) as connection:
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        database_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if quick_check != "ok":
            errors.append(f"SQLite quick_check 失败：{quick_check}")
        if foreign_key_errors:
            errors.append(f"SQLite 外键错误：{len(foreign_key_errors)} 条")
        if database_tables != EXPECTED_TABLES:
            errors.append(
                "运行数据库表不一致："
                f"缺少 {sorted(EXPECTED_TABLES - database_tables)}，"
                f"多出 {sorted(database_tables - EXPECTED_TABLES)}"
            )

        active_role_count = connection.execute(
            "SELECT COUNT(DISTINCT role) FROM users WHERE status = 'active'"
        ).fetchone()[0]
        if active_role_count != 3:
            errors.append("运行数据库必须包含学生、教师、管理员三类启用账号")
        course_count = connection.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
        classroom_count = connection.execute(
            "SELECT COUNT(*) FROM course_sessions"
        ).fetchone()[0]
        invalid_settings = connection.execute(
            "SELECT COUNT(*) FROM statistics_settings "
            "WHERE interval_minutes NOT BETWEEN 5 AND 10"
        ).fetchone()[0]
        if not course_count or not classroom_count:
            errors.append("运行数据库缺少可演示的课程或课堂")
        if invalid_settings:
            errors.append("运行数据库包含超出 5～10 分钟范围的统计周期")
    return len(database_tables), course_count, classroom_count


def main() -> None:
    args = parse_args()
    errors: list[str] = []
    warnings: list[str] = []

    for relative_path in REQUIRED_FILES:
        target = PROJECT_ROOT / relative_path
        if not target.is_file() or target.stat().st_size == 0:
            errors.append(f"缺少或为空文件：{relative_path}")

    screenshot_dimensions: list[tuple[int, int]] = []
    for file_name in SCREENSHOTS:
        image_path = PROJECT_ROOT / "截图与视频" / file_name
        if not image_path.is_file() or image_path.stat().st_size < 10_000:
            errors.append(f"截图缺失或异常小：{file_name}")
            continue
        dimensions = image_dimensions(image_path)
        if dimensions is None:
            errors.append(f"截图格式或文件头异常：{file_name}")
            continue
        screenshot_dimensions.append(dimensions)
        if dimensions[0] < 320 or dimensions[1] < 240:
            errors.append(f"截图分辨率过低：{file_name} -> {dimensions[0]}×{dimensions[1]}")

    markdown_link_count = validate_markdown_links(errors)
    python_source_count = validate_python_sources(errors)
    frontend_asset_count = validate_frontend_assets(errors)

    module_document = (PROJECT_ROOT / "docs" / "自主新增业务模块说明.md").read_text(
        encoding="utf-8"
    )
    chinese_character_count = len(re.findall(r"[\u4e00-\u9fff]", module_document))
    if chinese_character_count < 500:
        errors.append(f"自主模块说明中文字符不足 500：实际 {chinese_character_count}")

    ai_report = (PROJECT_ROOT / "docs" / "AI使用情况报告.md").read_text(
        encoding="utf-8"
    )
    prompt_count = len(re.findall(r"^### 记录 \d+", ai_report, flags=re.MULTILINE))
    issue_count = len(re.findall(r"^### 问题 \d+", ai_report, flags=re.MULTILINE))
    if prompt_count < 5:
        errors.append(f"AI 报告关键提示少于 5 条：实际 {prompt_count}")
    if issue_count < 2:
        errors.append(f"AI 报告问题修正少于 2 条：实际 {issue_count}")
    if "代表性 AI 完整输出附录" not in ai_report or "原创性声明" not in ai_report:
        errors.append("AI 报告缺少完整输出附录或原创性声明")

    placeholder_count = 0
    for relative_path, placeholders in PERSONAL_INFO_PLACEHOLDERS.items():
        content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        for placeholder in placeholders:
            occurrences = content.count(placeholder)
            placeholder_count += occurrences
            if occurrences:
                message = f"个人信息尚未填写：{relative_path} -> {placeholder}"
                (errors if args.strict else warnings).append(message)

    schema_sql = (PROJECT_ROOT / "database" / "schema.sql").read_text(
        encoding="utf-8"
    )
    schema_tables = {
        name.lower()
        for name in re.findall(
            r"CREATE TABLE IF NOT EXISTS\s+([a-z_]+)",
            schema_sql,
            flags=re.IGNORECASE,
        )
    }
    if schema_tables != EXPECTED_TABLES:
        errors.append(
            "schema.sql 表不一致："
            f"缺少 {sorted(EXPECTED_TABLES - schema_tables)}，"
            f"多出 {sorted(schema_tables - EXPECTED_TABLES)}"
        )

    database_table_count, course_count, classroom_count = validate_database(errors)

    print(f"必备文件：{len(REQUIRED_FILES)} 项")
    print(f"最终截图：{len(screenshot_dimensions)}/{len(SCREENSHOTS)} 张")
    print(f"Markdown 本地链接：{markdown_link_count} 项")
    print(f"前端静态资源引用：{frontend_asset_count} 项")
    print(f"Python 源码：{python_source_count} 个文件")
    print(f"自主模块说明中文字符：{chinese_character_count}")
    print(f"AI 报告关键提示：{prompt_count} 条")
    print(f"AI 报告问题修正：{issue_count} 条")
    print(f"建表脚本/运行数据库：{len(schema_tables)}/{database_table_count} 张业务表")
    print(f"运行数据库课程/课堂：{course_count}/{classroom_count}")

    if warnings:
        print("\n待本人完成（不影响日常检查）：")
        for warning in warnings:
            print(f"- {warning}")
    if errors:
        print("\n检查失败：")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    if args.strict:
        print("最终提交严格检查全部通过。")
    else:
        suffix = f"；另有 {placeholder_count} 处个人信息待填写" if warnings else ""
        print(f"项目质量检查全部通过{suffix}。")


if __name__ == "__main__":
    main()
