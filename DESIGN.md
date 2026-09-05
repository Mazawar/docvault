# DocVault 设计文档

## 目标

联网时缓存学习资源（GitHub 教程 + 自上传笔记），产出**离线资源包**；内网机部署纯静态阅读站，更新 = 换包。
形态：前后端分离的 Web 应用，可打包为单文件 exe（pywebview 壳，回退浏览器）。

## 架构

```
sources ──sync──▶ SQLite(data/docvault.db) ──API──▶ Vue SPA（联机模式）
(GitHub repos     ├ articles + FTS5 全文索引          │
  + 上传笔记)     ├ assets/ 图片内容寻址缓存           └─export──▶ 离线包 zip
                  ├ uploads/                              ├ site/  前端 dist + 预渲染 JSON 树
                  └ dist/pdf                              └ pdf/   整书 PDF
内网：unzip → 任意静态服务器（无后端、无数据库、零外部依赖）；更新 = 覆盖 site/
```

## 分层

| 层 | 位置 | 职责 |
|---|---|---|
| api | `backend/src/api/` | FastAPI 路由（reading /admin）、静态托管、应用组装 |
| services | `backend/src/services/` | sync（clone/扫描/图片缓存）、content（md→HTML 管线）、pdf（weasyprint）、export（离线包）、jobs（串行队列） |
| models | `backend/src/models/` | database（连接/建表）+ repository（查询，全部 ? 参数绑定） |
| core | `backend/src/core/` | config（路径，frozen 感知）、util（markdown、SSRF 防护抓图、排序） |
| 前端 api | `frontend/src/api/` | 双模式适配：`/api/*` ↔ 离线 `d/*.json`；TS 类型契约 |
| 前端视图 | `frontend/src/views/` | Portal 书架 / Reader 阅读+侧栏+TOC / Search / Admin |

## 核心决策

1. **DB 为纲，JSON 为影**：联机时 SQLite 是唯一事实源（FTS5 全文搜索、CJK 逐字切分保证短词可搜）；离线包是预渲染 JSON 快照——静态服务器跑不了数据库，这是刻意的"一份内容、两种形态"。
2. **hash 路由 + 相对路径**：前端 `#/read/:pid/:bid/:slug*`（slug 是嵌套路径），离线包在任意子路径/静态服务器下可直达，无需 rewrite。
3. **图片内容寻址**：`assets/<sha256(url|bytes)>.<ext>`，跨项目去重；图片 URL 在渲染时重写为 `/a/<name>`。
4. **任务串行**：同步/导出/PDF 单 worker 队列，任务与日志持久化在 jobs 表，管理台轮询。
5. **安全**：SQL 全静态语句 + 参数绑定；搜索词白名单清洗防 FTS 语法注入；外链图片抓取走 SSRF 防护（协议白名单、字面私网/环回 IP 拦截、重定向校验，代理环境交由代理解析）；git 子进程仅注入代理 env。
6. **桌面壳可降级**：exe 启动本机随机端口 uvicorn → 探活 → pywebview 窗口；webview 不可用自动开浏览器，`--browser` 可强制。

## API（摘要）

- 阅读：`GET /api/index` · `GET /api/book/{pid}/{bid}` · `GET /api/article/{pid}/{bid}/{slug:path}` · `GET /api/search?q=&pid=`
- 管理：`GET /api/admin/overview` · `POST /api/admin/sync|pdf|export|upload|note` · `GET/POST/DELETE /api/admin/projects` · `GET /api/admin/download` · `GET /api/jobs`
- 静态：`/a/*` 图片缓存、`/files/{pid}/{name}` 附件、`/` 前端 dist

## 离线包结构

```
site/index.html + assets/   前端构建产物
site/d/index.json           书架
site/d/{pid}/{bid}/toc.json 书目录
site/d/{pid}/{bid}/{slug}.json  文章（预渲染 HTML + 上下篇）
site/d/search.json          全文检索索引（前端本地检索）
site/a/*                    本地化图片
pdf/*.pdf                   整书导出
```

## 笔记模块（规划中 · 独立一等模块）

**动机**：现在笔记以 `my-notes` 上传型项目的形态混在书架里（一本书），编辑器也只是管理台里的简版 textarea。
"自己写的笔记"和"缓存别人的书"是两类内容，应当并列为一等模块。

**定位**：笔记 ≠ 项目。项目 = 外部内容的只读缓存；笔记 = 自己的创作与摘录，需要完整的书写体验。

### 原则
- **文件系统为事实源**：`data/notes/<笔记本>/<笔记>.md` + 纯文本 front-matter（title/tags/created）。
  天然可 git、可拷贝、可直接作为 VitePress srcDir（呼应"自己写文章用 VitePress"的结论）；
  内存建索引供搜索，与 manifest 思路一致，不走 SQLite 正文。
- **零依赖不变**：编辑器选型不得引入 npm 之外的运行时依赖（CodeMirror 走前端构建期依赖，可用）。

### 分期
| 阶段 | 内容 |
|---|---|
| P0 可用性 ✅ **已完成 2026-09-05** | 独立路由 `/notes`：左栏笔记本+笔记列表 / 右栏编辑+实时预览分栏；新建/重命名/删除；书架与全局搜索已排除笔记（upload 型项目），离线包含预渲染笔记 |
| P1 组织 ✅ | front-matter 标签 + 标签/文本过滤；notes_fts 并入 `/api/search`（kind=note，📝 前缀） |
| P2 富输入 ✅ | 粘贴/拖拽图片进 `data/assets`（sha256 去重）；附件入 `_files`，光标处插链接 |
| P3 导出 ✅ | 单篇/整本笔记本 PDF（封面+页码目录），CLI `pdf-note` |
| P4 联动 ✅ | CLI `notes-vite dev/build`：自动脚手架+侧栏生成+笔记副本同步，构建实测 5.1s 通过 |
| P5 可选 ✅ | `[[双链]]`（解析/missing 样式）+ 反向链接面板 + 每日笔记按钮 |

### 迁移
- `my-notes` 上传项目一键迁移为 `data/notes/我的笔记/`（书=笔记本、文章=笔记），书架中该消失。
- 管理台不承担笔记编辑（职责分离定稿）：笔记统一在 `/notes` 维护，管理台只负责在线资源的维护与导出。

### 验收标准（P0）
- 笔记不出现在书架/搜索的项目列表里（或在搜索中单独标注）
- 断网、纯静态站模式下笔记可读（预渲染进离线包）
- `data/notes` 单目录拷走即可在另一台机器完整恢复

## 路线

- 增量同步（内容 hash 只重建变动文章）
- EPUB 导出
- GitLab / 任意 URL adapter
- 定时自动同步（crontab 调 CLI）
- 笔记模块 P0→P5（见上文）
