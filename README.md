# 课堂学情监控管理系统

一个面向课程大作业的课堂反馈与教学跟进系统。学生可用 1～6 分表情反馈理解程度并参与课堂讨论；教师可查看实时统计、ECharts 图表、历史快照、Excel 报表和学情预警；管理员可维护课程、课堂场次、三类账号和 5～10 分钟统计周期。

## 技术栈

- 后端：Python、FastAPI
- 数据库：SQLite
- ORM 与校验：SQLAlchemy、Pydantic
- 前端：HTML、CSS、原生 JavaScript
- 图表与报表：ECharts、openpyxl
- 开发与运行环境：Windows

## 快速启动（Windows）

在项目根目录打开 PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.init_db
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

也可以在依赖安装完成后双击 `run.bat`。浏览器访问：<http://127.0.0.1:8000>。

如果 PowerShell 不允许激活虚拟环境，不必修改系统策略，直接使用：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.init_db
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

## 演示账号

以下是从空库恢复时始终可用的核心演示账号：

| 角色 | 账号 | 密码 | 手机号 |
| --- | --- | --- | --- |
| 学生 | `student001` | `123456` | `13800000001` |
| 学生 | `student002` | `123456` | `13800000004` |
| 教师 | `teacher001` | `123456` | `13800000002` |
| 管理员 | `admin001` | `123456` | `13800000003` |

当前随项目保存的运行数据库已扩充到 16 个测试账号：学生 `student101`～`student109`、教师 `teacher101`～`teacher102`、管理员 `admin101` 也使用密码 `123456`；其中 `student109` 为停用状态。完整姓名、班级、手机号和当前课程数据见[当前演示数据说明](docs/当前演示数据说明.md)。

短信、微信、QQ 是课程作业的本地演示认证：短信测试验证码会直接显示在登录页；微信演示绑定 `student001`；QQ 演示绑定 `teacher001`。数据库仅保存验证码和会话令牌的散列。

## 主要功能

- 三角色账号密码、短信验证码、微信演示、QQ 演示登录。
- 学生使用六档表情随时提交当前理解程度。
- 教师端每 5 秒刷新当前统计，展示提交人数与提交率、六档人数、平均理解度、分歧程度、本课堂待处理预警、柱状图和最近五个完整周期趋势图。
- 系统按管理员设置的 5～10 分钟周期，在周期结束后生成课堂统计快照；快照只采用截止时点前每名学生的最新反馈。
- 教师按课程名称和上课时间组合查询历史，并导出 `.xlsx`。
- 学生和教师发送文字或图片消息，页面每 3 秒增量读取新消息；统一上传组件显示文件名与移除操作，自己和对方消息采用左右气泡区分，空状态与真实消息严格互斥。
- 管理员对学生、教师、管理员账号进行增删改查、条件查询和启停管理；列表保留“修改”主操作，其余操作收纳到“更多”菜单。
- 管理员可新增课程、创建待开始或进行中的课堂，并开始、结束课堂；同一教师或班级不能同时进入两个课堂。
- 自主新增“学情预警与教师跟进”：1～2 分反馈自动触发预警，教师在键盘可控的详情抽屉中填写跟进意见，学生查看处理结果；空意见会获得明确的就地提示。
- 电脑端采用固定左侧功能导航并一次展示一个模块，平板使用顶部标签，手机切换为固定底部导航。
- 界面统一为轻量 SaaS 工作台：教师实时课堂作为数据驾驶舱直接进入统计内容，预警和讨论业务页保留紧凑工作台 Banner；教师关键指标采用白底色条卡片，预警使用简表、分钟级紧凑时间和右侧详情抽屉，学生提醒卡片降低高度；管理员统计页补充真实运行状态、近 7 天快照趋势和最近配置摘要。
- 业务页面与接口均要求登录，并按角色、班级和授课课程限制数据范围。

后续页面扩展应遵循《[UI 设计规范](docs/UI设计规范.md)》，保持颜色语义、卡片、表格、状态胶囊和响应式导航一致。

## 数据库说明

- 正常运行数据库：`database/classroom_monitor.db`
- 完整建表脚本：`database/schema.sql`
- 可重复导入的演示数据：`database/seed.sql`
- Python 初始化入口：`python -m scripts.init_db`

`schema.sql` 与 `seed.sql` 已在空白 SQLite 数据库中连续导入两次验证，包含 10 张业务表、4 个基线演示账号、课堂、反馈、快照、讨论消息和学情预警。当前 `classroom_monitor.db` 保留了后续测试新增的 16 个账号、3 门课程和 3 节课堂；SQL 基线与运行数据库用途不同，提交包可同时保留。

默认数据库路径是 `database/classroom_monitor.db`。自动化测试或临时部署可设置环境变量 `CLASSROOM_MONITOR_DATABASE` 指向另一份 SQLite 文件，避免污染演示数据。

## 一键复验

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m scripts.smoke_test
.\.venv\Scripts\python.exe -m scripts.validate_submission
```

- 回归测试验证“按提交时间取最新反馈”和“只保存已结束周期快照”。
- HTTP 冒烟验收会启动临时本地服务，检查健康状态、匿名拦截、三角色登录/越权、四种认证和静态资源安全头；临时数据库会自动清理。
- 日常提交检查覆盖 26 项必备文件、11 张截图、37 个 Markdown 本地链接、35 个前端静态资源引用、60 个 Python 文件语法、10 张数据库表及演示数据基线，并明确列出尚未填写的个人信息。
- 最终交互复验覆盖反馈刷新持久化、学生到教师的数据联动、讨论上传组件与气泡方向、预警抽屉校验与焦点恢复、用户启停确认，以及 390×844 手机端横向溢出和底栏安全区。
- 最终打包会自动运行 `python -m scripts.validate_submission --strict`；姓名、学号、班级、签名日期等占位符未替换时不会生成 ZIP。

## 目录结构

```text
课堂学情监控管理系统/
├─ backend/                 FastAPI 后端、模型、接口和业务服务
├─ frontend/                HTML、CSS、原生 JavaScript、ECharts 与上传图片
├─ database/                SQLite 数据库、schema.sql、seed.sql
├─ scripts/                 数据库初始化与提交打包脚本
├─ tests/                   统计与定时快照回归测试
├─ docs/                    使用、安装、模块、AI 报告和各阶段验收记录
├─ 截图与视频/             11 张最终验收截图
├─ requirements.txt
├─ run.bat
└─ README.md
```

## 提交前个人信息

由于姓名、学号、班级、签字和提交日期属于个人信息，项目不会自动编造。请先填写 `docs/待填写个人信息.md` 和 `docs/AI使用情况报告.md` 的对应位置，然后运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package_submission.ps1 -StudentNo "你的学号" -Name "你的姓名"
```

脚本会先执行最终提交严格检查，再在 `dist` 中生成 `学号_姓名_课堂学情监控系统.zip`，并自动排除虚拟环境、缓存、临时文件和运行时 WAL 文件。

## 详细文档

- [用户使用手册](docs/用户使用手册.md)
- [当前演示数据说明](docs/当前演示数据说明.md)
- [系统安装调试手册](docs/系统安装调试手册.md)
- [自主新增模块说明](docs/自主新增业务模块说明.md)
- [AI 使用情况报告](docs/AI使用情况报告.md)
- [提交前检查清单](docs/提交前检查清单.md)
- [全系统验收基线](docs/全系统验收基线.md)

本项目按课程作业规模设计。真实短信和真实微信/QQ 开放平台接入、HTTPS、云部署、多进程扩容等未被 PRD 明确规定，属于需要自行设计的生产化内容，不作为本作业的基础需求。
