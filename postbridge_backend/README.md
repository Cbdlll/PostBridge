# PostBridge Backend

PostBridge 后端是基于 Flask、Waitress、SQLite 和 Playwright 的本地 API 服务。它负责视频文件管理、账号 Cookie/Profile 管理、平台发布自动化、AI 内容任务、定时任务和桌面打包后的静态文件托管。

## 技术栈

- Python 3.10+
- Flask + Flask-CORS
- Waitress + Paste TransLogger
- SQLite
- APScheduler
- Playwright
- PyInstaller
- CustomTkinter（打包为桌面程序时的本地控制窗口）

## 目录说明

```text
postbridge_backend/
|-- ai_service/        LLM、视频生成和平台人设相关服务
|-- database/          数据库初始化脚本与开发期数据库位置
|-- rpa_service/       各平台浏览器自动化发布逻辑
|-- static/            前端构建后的静态资源，用于打包/生产访问
|-- utils/             Cookie、Profile、加密、文件、网络和通用工具
|-- app.py             Flask 应用入口
|-- cli_main.py        命令行入口
|-- conf.py            路径、Chrome 和数据库配置
|-- continue_task_api.py
|-- scheduler.py       定时校验和任务调度
|-- requirements.txt   Python 依赖
`-- app.spec           PyInstaller 配置
```

## 本地启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python app.py
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
python app.py
```

服务默认监听：

```text
http://localhost:5409
```

开发时通常配合前端 Vite 服务使用，前端请求会代理到该端口。

## 主要能力

- `/uploadSave`、`/getFiles`、`/getFile`、`/deleteFile`、`/renameFile`：视频素材上传和管理。
- `/getAccounts`、`/getValidAccounts`、`/api/startLogin`、`/api/openBrowser`：平台账号与浏览器资料管理。
- `/postVideo`、`/postVideoBatch`：手动发布和批量发布。
- `/api/create_prompt`、`/api/generate_video`、`/api/ai_task/create`：AI 内容与视频生成任务。
- `/api/tasks`、`/api/publish_tasks`：AI 任务和发布任务管理。
- `/api/config`：Chrome 路径、AI 服务等本地配置。

## 运行时数据

开发模式下，运行时数据保存在 `postbridge_backend/` 下的本地目录中，例如：

- `data/videos/`：上传或生成的视频文件。
- `data/cookies/`：导入或远程提交的 Cookie 文件。
- `data/profiles/`：浏览器用户资料。
- `database/database.db`：SQLite 数据库。
- `logs/`：运行日志。

打包运行时，数据会保存到系统应用数据目录下的 `PostBridge` 目录，具体逻辑见 `conf.py`。

这些数据通常包含账号、Cookie、视频素材、日志和 API Key，不应提交到 GitHub。

## 配置说明

- Chrome 路径优先读取 `data/app_config.json` 中的 `chrome_path`。
- Windows 下会自动尝试常见 Chrome 安装路径。
- Linux 默认回退到 `/usr/bin/google-chrome`。
- AI/视频生成服务凭据通过前端设置页或请求参数传入，避免写死在代码中。

## 打包

推荐使用根目录脚本：

```bat
..\build_exe.bat
```

手动打包前，需要先构建前端并复制到 `postbridge_backend/static/`：

```bash
cd ../postbridge_frontend
npm install
npm run build

cd ../postbridge_backend
mkdir -p static
cp -r ../postbridge_frontend/dist/* static/
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --clean --noconfirm app.spec
```

Windows 下可直接运行根目录 `build_exe.bat`，输出通常位于：

```text
postbridge_backend\dist\PostBridge.exe
```

## 开发注意事项

- 新增 API 时，保持响应结构尽量统一为 `code`、`msg`、`data`。
- 涉及浏览器自动化的逻辑应优先放在 `rpa_service/` 或 `utils/` 中。
- 涉及 AI 供应商的逻辑应优先放在 `ai_service/` 中。
- 不要提交本地数据库、Cookie、浏览器 Profile、上传视频、日志、虚拟环境和打包产物。
