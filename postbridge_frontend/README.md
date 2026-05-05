# PostBridge Frontend

PostBridge 前端是基于 Vue 3、Vite、TypeScript 和 Element Plus 的运营控制台。它负责账号管理、视频素材管理、手动发布、任务监控、系统设置、仪表盘和 AI 创作页面。

## 技术栈

- Vue 3 + TypeScript
- Vite
- Vue Router
- Pinia
- Element Plus + Element Plus Icons
- ECharts / vue-echarts
- Axios

## 目录说明

```text
postbridge_frontend/
|-- src/
|   |-- api/          后端接口封装
|   |-- layouts/      主布局
|   |-- router/       路由配置
|   |-- utils/        前端工具
|   |-- views/        页面视图
|   |-- App.vue       应用入口组件
|   `-- main.ts       前端入口
|-- public/           公共静态资源
|-- index.html        Vite HTML 入口
|-- package.json      脚本与依赖
`-- vite.config.ts    Vite 配置与开发代理
```

## 本地开发

先启动后端服务，默认地址为 `http://localhost:5409`。然后在前端目录执行：

```bash
npm install
npm run dev
```

开发服务默认运行在：

```text
http://localhost:5173
```

`vite.config.ts` 已配置开发代理，前端会把 `/api`、`/uploadSave`、`/getFiles`、`/postVideo` 等请求转发到 `http://localhost:5409`。

## 常用脚本

```bash
npm run dev
```

启动 Vite 开发服务。

```bash
npm run build
```

执行 TypeScript 类型检查并生成生产构建，输出到 `dist/`。

```bash
npm run preview
```

本地预览生产构建。

## 页面模块

- `Dashboard.vue`：数据概览。
- `Accounts.vue`：平台账号管理、登录与状态同步。
- `VideoManager.vue`：视频素材上传、查看、重命名和删除。
- `ManualPublish.vue`：手动发布和批量发布。
- `Tasks.vue`：AI 任务与发布任务管理。
- `AICreate.vue`：AI 选题、提示词、视频生成和自动发布流程。
- `UserPersona.vue`：平台人设模板管理。
- `Settings.vue`：Chrome 路径、LLM 和视频生成服务配置。

## 构建与打包配合

桌面程序打包时，需要先生成前端静态文件，再复制到后端 `static/` 目录：

```bash
npm run build
```

根目录的 `build_exe.bat` 会自动完成前端构建、静态文件复制和后端 PyInstaller 打包。通常优先使用根目录脚本。

## 注意事项

- `node_modules/` 和 `dist/` 不应提交到仓库。
- 新增接口时，优先在 `src/api/index.ts` 中统一封装。
- 新增页面时，同时更新 `src/router/index.ts` 和主布局导航。
