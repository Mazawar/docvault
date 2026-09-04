# DocVault 设计文档

## 目标
自托管的多项目文档缓存站：缓存在线学习资源（GitHub 开源教程等）+ 支持自己上传资源 + 导出 PDF + 一键打离线包拷贝进内网。

## 架构

```
sources ──sync──▶ data/ ──build──▶ site/(纯静态) ──export──▶ offline.zip
(GitHub repos      ├ repos/     ├ 侧栏/搜索/portal        内网 unzip + 任意静态服务器
  + Web上传)       ├ assets/    └ search/*.json           在线: FastAPI 常驻(阅读+管理台)
                   ├ uploads/                                ├ /admin 同步/上传/导PDF/打包
                   ├ manifest/*.json                         └ / 静态站
                   └ dist/ (pdf/ offline.zip)
```

## 核心原则
1. **一份产物两种模式**：在线模式 = 静态站 + 管理壳；离线 = 同一个 site/ 拷走即用。零外部依赖（无 CDN/字体/JS 库）。
2. **图片全局缓存**：`data/assets/<sha1>.<ext>`，跨项目去重，URL 重写后内嵌。
3. **manifest 为索引**：`data/manifest/<pid>.json` 记录 books/articles/order，渲染和 PDF 都从它出发。
4. **任务串行**：同步/导出都是重活，单信号量排队，jobs.json 记录状态。

## 数据模型

projects.json（用户可编辑）:
```json
{"projects": [
  {"id":"xiaolincoding","name":"小林 coding","type":"github","repo":"xiaolincoder/CS-Base","root":".",
   "books":{"network":"图解网络","os":"图解系统","mysql":"图解MySQL","redis":"图解Redis"}},
  {"id":"javaguide","name":"JavaGuide","type":"github","repo":"Snailclimb/JavaGuide","root":"docs"},
  {"id":"my-notes","name":"我的笔记","type":"upload"}]}
```
- `type:github` → clone/pull 到 data/repos/<id>，root 为 md 根；books 省略则整库一本
- `type:upload` → data/uploads/<id>/ 下的 .md 自动成书；二进制放 _files/ 作为附件
- 书内分组：按一级子目录；文章排序：目录编号 + H1 编号（"2.3 xxx"）双级

## 模块
| 模块 | 职责 |
|---|---|
| dv/util.py | md→HTML、图片抓取缓存、URL 重写、排序键 |
| dv/sync.py | 拉仓库/上传目录 → 下载图片 → 生成 manifest |
| dv/render.py | 渲染 site/：portal、书页、文章页、搜索 JSON |
| dv/pdfexport.py | 按 book 导出 PDF（weasyprint，带页码目录） |
| dv/server.py | FastAPI：/ 静态站 + /admin 管理台 + 任务队列 |
| dv/main.py | CLI：sync / build / pdf / export / serve |

## API（/admin/api/*）
- GET status · POST sync/{pid} · POST sync-all
- POST pdf/{pid}/{book} · POST export（打离线 zip）
- POST upload（multipart，目标项目）
- GET jobs（轮询任务状态）

## 离线包用法
`unzip DocVault-offline-*.zip -d docvault && cd docvault/site && python3 -m http.server 8080`
或 nginx：`root /path/site; index index.html;`（图片用根路径 /a/，需站点跑在根路径）

## v2 路线
- SQLite FTS5 在线全文搜索（现用预构建 JSON，内网也够用）
- 增量同步（git diff 只重建变动文章）
- 更多 adapter：GitLab / 任意 URL 爬取 / HTML 镜像站
- 定时自动同步（服务器侧 crontab 调 dv/main.py）
- EPUB 导出
