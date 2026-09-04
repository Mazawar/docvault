<div align="center">

# 📚 DocVault

**把值得反复读的技术文档缓存到本地 —— 联网时同步更新，离线时开箱即读**

[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009485?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3-4fc08d?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![SQLite](https://img.shields.io/badge/SQLite-003b57?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Platform](https://img.shields.io/badge/平台-Linux%20%7C%20Windows%20%7C%20macOS-6e6e6e)](#)

*为内网自我学习的同学设计 · 一个资源包，拷走就是整个图书馆*

</div>

---

## ⚠️ 免责声明

> 本项目**仅供个人学习与技术参考使用**。仓库内不含任何第三方内容本体，所缓存的文章、图片、PDF 等
> **版权归原原作者所有**，请尊重原作者的劳动成果：
>
> - 仅限个人在内网/离线环境下学习使用，**请勿用于任何商业用途或二次分发**；
> - 使用本项目缓存任何内容前，请确认已遵守原站的用户协议与 robots 约定；
> - 如原站作者要求停止缓存，请立即删除相关数据；
> - 因使用本项目产生的任何问题，由使用者自行承担。
>
> 如果某个项目/教程对你有帮助，请去**原站支持原作者**（这是本项目存在的意义）。

## ✨ 特性

- 📥 **多源缓存** — GitHub 开源教程一键镜像（自动 clone/同步），图片全部本地化（sha256 内容寻址、跨项目去重）
- ✍️ **自上传资源** — 管理台上传 Markdown 笔记与附件，即刻进站可读
- 🔍 **全文搜索** — SQLite FTS5 全文索引（联机）/ 预渲染索引（离线），中文分词友好
- 📕 **PDF 导出** — 按书导出 A4 PDF：封面 + 真实页码目录 + 代码高亮 + 图片内嵌
- 📦 **资源包导入/导出** — 数据库 + 图片 + 笔记 + PDF + 前端产物打包成一个 zip，内网机器**导入即完整实例**（无需联网、无需 npm）
- 🌐 **只读静态站** — 也可导出纯静态站，给没有安装 DocVault 的人浏览器直接看
- 🌗 **VitePress 风格** — 靛蓝主题、暗色模式、侧栏分组、页内目录、阅读进度条
- ✅ **阅读记忆** — 已读标记、最近阅读，localStorage 存储离线同样生效
- 📱 **移动端适配** — 抽屉目录、自适应导航，手机上完整可用
- 🖥 **桌面模式** — 可打包为单文件 exe（pywebview 窗口，回退浏览器）

## 🚀 快速开始（联网机）

> 出厂**不预置任何缓存内容**——要缓存什么、缓存多少，完全由你决定。
> `backend/projects.example.json` 里有一份示例配置（小林 coding / JavaGuide / advanced-java）可直接抄。

```bash
git clone https://github.com/Mazawar/docvault.git && cd docvault
pip install -r backend/requirements.txt

# 1. 声明你想缓存的项目：二选一
#    a) 编辑 backend/projects.json（参考 projects.example.json 的写法）
#    b) 启动后在管理台 #/admin 里可视化添加
cd backend
python -m src.main sync all      # 2. 同步全部项目（clone + 图片本地化 + 入库）
python -m src.main export        # 3. 打只读静态站 -> data/dist/DocVault-offline-日期.zip
python -m src.main serve         # 4. 联网自用：http://127.0.0.1:8787
```

项目配置示例（写进 `backend/projects.json`）：

```json
{
  "projects": [
    { "id": "xiaolincoding", "name": "小林 coding", "type": "github",
      "repo": "xiaolincoder/CS-Base", "root": ".",
      "books": { "network": "图解网络" },
      "groupTitles": { "network": { "1_base": "网络基础" } } },
    { "id": "my-notes", "name": "我的笔记", "type": "upload" }
  ]
}
```

打开 `http://127.0.0.1:8787` 阅读，`#/admin` 进管理台：
项目增删改（GitHub / 本地上传）、单项目或全量同步、笔记在线编辑、上传附件、导出整本书 PDF、生成/下载两种离线包。

桌面模式：`python -m src.main app`（pywebview 窗口，无 webview 环境自动回退浏览器）。

## 📦 资源包：导入 / 导出（内网迁移主线）

资源包 = **可导回程序的数据包**（SQLite 库 + 图片缓存 + 上传 + PDF + **前端产物**）。
内网机器：clone 代码 + 导入 + serve = 完整 DocVault，全程无网络、无 npm。

```bash
# 联网机（有数据的一方）
python -m src.main export-pack                 # 管理台「生成资源包」等价
python -m src.main export-pack --with-repos    # 附带源仓库，导入后可继续联网同步

# 内网机（空机器）
git clone https://github.com/Mazawar/docvault.git && cd docvault/backend
pip install -r requirements.txt                # 无外网时先在有网机器 pip download 离线装
python -m src.main import-pack DocVault-pack-xxx.zip
python -m src.main serve --port 8787           # 完整实例，直接用
```

管理台等价操作：「生成资源包 / 下载资源包 / 导入资源包」。
导入语义：按项目合并（同 id 覆盖、其余保留），图片/上传/PDF 跳过已有文件。

## 🌐 只读静态站（无需本程序）

```bash
unzip DocVault-offline-*.zip -d dv
cd dv/site && python3 -m http.server 8080
# 或 nginx: root /path/dv/site; index index.html;
```

纯静态站（Vue 前端 + 预渲染 JSON 数据树 + 本地化图片）+ `pdf/` 全部导出的 PDF。
零外部依赖（无 CDN/在线字体/JS 库），阅读、全文搜索、暗色主题、阅读记忆全部离线可用。

> **两种包怎么选**：**资源包**是程序的数据（导回 DocVault 就是完整实例）；
> **静态站**是只读产物（给没有程序的人浏览器直接看）。

## 🧭 路线图

- [x] 多项目缓存 / 图片本地化 / PDF 导出 / 资源包导入导出
- [x] VitePress 风格主题 / 暗色模式 / 阅读记忆 / 移动端适配
- [ ] **笔记模块**（独立一等模块：笔记本 + 分栏编辑器 + 标签 + 粘贴传图 + VitePress 联动，见 [DESIGN.md](DESIGN.md)）
- [ ] 增量同步（内容 hash 只重建变动文章）
- [ ] EPUB 导出 · GitLab / 任意 URL adapter · 定时自动同步

## 🛠 开发

```bash
cd frontend && npm install && npm run dev     # 前端热更 http://localhost:5173（代理 /api 到 8787）
cd backend && python -m uvicorn src.api.app:app --port 8787
scripts\build_exe.bat                          # 打 exe（Windows），产物 dist/DocVault.exe
```

目录结构：

```
backend/
  src/core       配置与通用工具（路径、md 渲染、图片抓取缓存）
  src/models     SQLite（projects/books/articles/jobs + FTS5 全文索引，全参数绑定）
  src/services   业务：sync 同步 / content 渲染 / pdf 导出 / export 静态站 / pack 资源包 / jobs 队列
  src/api        FastAPI 路由（reading /admin）与应用组装
  src/main.py    CLI（serve/app/sync/build/pdf/export/export-pack/import-pack/import）
  src/desktop.py 桌面入口（uvicorn 线程 + pywebview，回退浏览器）
frontend/src     api 请求层（双模式：API / 离线 JSON）· views · stores · router · styles
projects.json    首次启动的种子配置（之后以数据库为准，可在管理台改）
```

## 📁 数据说明

- 联机：SQLite（`backend/data/docvault.db`）是唯一事实源；`projects.json` 仅首次播种，可 `python -m src.main import` 重新导入。
- 仓库与出厂配置**不包含任何第三方内容**；缓存哪些项目、何时同步，全部由使用者自行决定与管理。
- 离线包内是预渲染的 JSON 数据树——静态服务器跑不了数据库，这是"一份内容、两种形态"：在线 DB ↔ 离线快照。
- 图片按内容寻址缓存（`data/assets/`），跨项目去重；同步时自动下载文中外链图片。
- PDF 导出用 weasyprint（Windows 需 GTK 运行库，Linux 开箱即用）；未就绪时任务会给出明确提示。

## 🙏 致谢

`projects.example.json` 中的示例项目来自这些优秀的开源教程，**感谢原作者们的无私分享**：

[小林 coding](https://xiaolincoding.com/) · [JavaGuide](https://javaguide.cn/) · [doocs/advanced-java](https://github.com/doocs/advanced-java) · 以及所有被缓存内容的原作者

---

<div align="center">

**仅供内网学习交流 · 内容版权归原作者所有 · 请支持正版与原站**

</div>
