"""在临时数据库和真实本地 HTTP 服务上执行无污染冒烟验收。"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from http.cookiejar import CookieJar
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    Request,
    build_opener,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class NoRedirectHandler(HTTPRedirectHandler):
    """让冒烟测试能直接断言 303，而不是自动跟随跳转。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def find_available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temporary_socket:
        temporary_socket.bind(("127.0.0.1", 0))
        return int(temporary_socket.getsockname()[1])


def main() -> None:
    check_count = 0

    def check(condition: bool, description: str) -> None:
        nonlocal check_count
        if not condition:
            raise AssertionError(description)
        check_count += 1

    (PROJECT_ROOT / "tmp").mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="smoke-", dir=PROJECT_ROOT / "tmp") as temp_dir:
        database_path = Path(temp_dir) / "smoke.db"
        os.environ["CLASSROOM_MONITOR_DATABASE"] = str(database_path)

        # 必须在设置隔离数据库路径后再导入应用模块。
        import uvicorn

        from backend.app.database import engine
        from backend.app.main import app
        from scripts.init_db import initialize_database

        initialize_database()

        port = find_available_port()
        server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=port,
                log_level="warning",
            )
        )
        server_thread = threading.Thread(target=server.run, daemon=True)
        server_thread.start()

        base_url = f"http://127.0.0.1:{port}"
        cookie_jar = CookieJar()
        opener = build_opener(HTTPCookieProcessor(cookie_jar))
        no_redirect_opener = build_opener(NoRedirectHandler())

        def request(
            path: str,
            *,
            method: str = "GET",
            payload: dict[str, object] | None = None,
            follow_redirects: bool = True,
        ) -> tuple[int, dict[str, str], bytes]:
            data = None
            headers: dict[str, str] = {}
            if payload is not None:
                data = json.dumps(payload).encode("utf-8")
                headers["Content-Type"] = "application/json"
            http_request = Request(
                f"{base_url}{path}",
                data=data,
                headers=headers,
                method=method,
            )
            selected_opener = opener if follow_redirects else no_redirect_opener
            try:
                with selected_opener.open(http_request, timeout=5) as response:
                    response_headers = {
                        key.lower(): value for key, value in response.headers.items()
                    }
                    return response.status, response_headers, response.read()
            except HTTPError as error:
                response_headers = {
                    key.lower(): value for key, value in error.headers.items()
                }
                return error.code, response_headers, error.read()

        try:
            deadline = time.monotonic() + 10
            while True:
                try:
                    status_code, _, _ = request("/api/health")
                    if status_code == 200:
                        break
                except URLError:
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError("本地测试服务未能在 10 秒内启动")
                time.sleep(0.05)

            status_code, headers, _ = request("/", follow_redirects=False)
            check(status_code == 303, "首页应跳转到登录页")
            check(headers.get("location", "").endswith("/login"), "首页跳转地址错误")

            status_code, _, body = request("/login")
            check(status_code == 200, "登录页无法访问")
            check("课堂学情监控管理系统" in body.decode("utf-8"), "登录页内容异常")

            status_code, _, body = request("/api/health")
            health = json.loads(body)
            check(status_code == 200, "健康检查失败")
            check(health.get("database") == "ok", "数据库健康状态异常")

            for path in ("/student", "/teacher", "/teacher/history", "/admin"):
                status_code, headers, _ = request(path)
                check(status_code == 401, f"匿名访问未被拒绝：{path}")
                check(headers.get("cache-control") == "no-store", f"受保护页面缓存策略错误：{path}")

            role_pages = {
                "student001": ("student", "/student"),
                "teacher001": ("teacher", "/teacher"),
                "admin001": ("admin", "/admin"),
            }
            for username, (role, own_page) in role_pages.items():
                status_code, _, body = request(
                    "/api/auth/login",
                    method="POST",
                    payload={"username": username, "password": "123456"},
                )
                login = json.loads(body)
                check(status_code == 200, f"{username} 密码登录失败")
                check(login["user"]["role"] == role, f"{username} 角色错误")
                check(request("/api/auth/me")[0] == 200, f"{username} 会话无效")
                check(request(own_page)[0] == 200, f"{username} 角色页面失败")

                other_page = "/admin" if role != "admin" else "/student"
                check(request(other_page)[0] == 403, f"{username} 越权未被拒绝")
                check(request("/api/auth/logout", method="POST")[0] == 200, f"{username} 退出失败")
                check(request("/api/auth/me")[0] == 401, f"{username} 退出后会话仍有效")

            status_code, _, body = request(
                "/api/auth/sms/send",
                method="POST",
                payload={"phone": "13800000001"},
            )
            sms_code = json.loads(body)
            check(status_code == 200, "短信验证码生成失败")
            status_code, _, _ = request(
                "/api/auth/sms/login",
                method="POST",
                payload={
                    "phone": "13800000001",
                    "code": sms_code["debug_code"],
                },
            )
            check(status_code == 200, "短信验证码登录失败")
            request("/api/auth/logout", method="POST")

            check(
                request(
                    "/api/auth/wechat/login",
                    method="POST",
                    payload={"code": "wechat_demo_authorized"},
                )[0]
                == 200,
                "微信演示登录失败",
            )
            request("/api/auth/logout", method="POST")
            check(
                request(
                    "/api/auth/qq/login",
                    method="POST",
                    payload={"code": "qq_demo_authorized"},
                )[0]
                == 200,
                "QQ 演示登录失败",
            )

            status_code, headers, _ = request("/static/js/api.js")
            check(status_code == 200, "前端 API 工具未能加载")
            check(headers.get("x-content-type-options") == "nosniff", "静态资源安全响应头缺失")
        finally:
            server.should_exit = True
            server_thread.join(timeout=5)
            engine.dispose()
            check(not server_thread.is_alive(), "本地测试服务未能正常停止")

    print(f"HTTP 冒烟验收通过：{check_count} 项，临时数据库已自动清理。")


if __name__ == "__main__":
    main()
