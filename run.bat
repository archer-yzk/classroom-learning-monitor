@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo 未找到虚拟环境，请先按照说明创建 .venv 并安装依赖。
    pause
    exit /b 1
)

echo 正在启动课堂学情监控管理系统...
echo 正在检查并初始化数据库...
".venv\Scripts\python.exe" -m scripts.init_db
if errorlevel 1 (
    echo 数据库初始化失败，请检查上方错误信息。
    pause
    exit /b 1
)

echo 浏览器访问：http://127.0.0.1:8000
echo 同一 WiFi 下的手机访问：http://电脑的WiFi地址:8000
".venv\Scripts\python.exe" -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
