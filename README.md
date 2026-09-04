# DocVault

多源文档缓存站：联网时把 GitHub 开源教程 / 自上传笔记缓存到本地，一键打出**离线资源包**；内网部署纯静态阅读站，以后更新只需换包。

前后端分离：FastAPI（`backend/`）+ Vue3/TS/Tailwind（`frontend/`），可打包为单文件 `DocVault.exe`（pywebview 桌面窗口，无 webview 环境时自动回退浏览器）。

## 联网机：缓存 + 打包

```bash
pip install -r backend/requirements.txt
cd backend
python -m src.main sync all        # 1. 同步全部项目（clone/pull + 图片本地化 + 入库）
python -m src.main export          # 2. 打离线包 -> data/dist/DocVault-offline-日期.zip
python -m src.main serve           # 联网自用：http://127.0.0.1:8787 （阅读 + 管理）
```

管理台（`#/admin`）可做的事：项目增删改（GitHub 仓库 / 本地上传）、单项目或全量同步、
笔记在线编辑发布、上传附件、导出某本书 PDF、打离线包并下载。

桌面模式（双击 exe 或 `python -m src.main app`）：pywebview 窗口，不可用时自动打开浏览器。

## 内网机：部署离线包

```bash
unzip DocVault-offline-*.zip -d dv
cd dv/site && python3 -m http.server 8080
# 或 nginx: root /path/dv/site; index index.html;
```

离线包 = 纯静态站（Vue 前端 + 预渲染 JSON 数据树 + 本地化图片）+ `pdf/` 全部导出的 PDF。
零外部依赖（无 CDN/在线字体/JS 库），阅读、全文搜索、暗色主题、阅读记忆全部离线可用。
以后更新：重打新包，解压覆盖 `site/` 即可。

## 开发

```bash
# 前端（热更）
cd frontend && npm install && npm run dev     # http://localhost:5173，代理 /api 到 8787
# 后端
cd backend && python -m uvicorn src.api.app:app --port 8787
# 打 exe
scripts\build_exe.bat                          # 产物 dist/DocVault.exe
```

目录结构：

```
backend/
  src/core       配置与通用工具（路径、md 渲染、图片抓取缓存）
  src/models     SQLite（projects/books/articles/jobs + FTS5 全文索引，全参数绑定）
  src/services   业务：sync 同步 / content 渲染 / pdf 导出 / export 离线包 / jobs 队列
  src/api        FastAPI 路由（reading /admin）与应用组装
  src/main.py    CLI（serve/app/sync/build/pdf/export/import）
  src/desktop.py 桌面入口（uvicorn 线程 + pywebview，回退浏览器）
frontend/src     api 请求层（双模式：API / 离线 JSON）· views · stores · router · styles
projects.json    首次启动的种子配置（之后以数据库为准，可在管理台改）
```

## 数据说明

- 联机：SQLite（`backend/data/docvault.db`）是唯一事实源；`projects.json` 仅首次播种，可 `python -m src.main import` 重新导入。
- 离线包内是预渲染的 JSON 数据树——静态服务器跑不了数据库，这是"一份内容、两种形态"：在线 DB ↔ 离线快照。
- 图片按内容寻址缓存（`data/assets/`），跨项目去重；同步时自动下载文中外链图片。
- PDF 导出用 weasyprint（Windows 需 GTK 运行库，Linux 开箱即用）；未就绪时任务会给出明确提示。
