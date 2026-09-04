# DocVault

多源文档缓存站：缓存在线教程（GitHub 开源仓库）+ 自上传资源 + PDF 导出 + 内网离线包。

## 首次使用

```bash
pip install -r requirements.txt
# 1. 联网同步全部项目并构建站点
python3 -m dv.main sync all
# 2. 启动服务（阅读 + 管理台）
python3 -m dv.main serve --port 8787
#    阅读:  http://127.0.0.1:8787/
#    管理台: http://127.0.0.1:8787/admin
```

## 日常操作（管理台按钮 / CLI 二选一）

| 操作 | 管理台 | CLI |
|---|---|---|
| 同步最新 | 项目行「同步」 | `python3 -m dv.main sync all` |
| 导出某本书 PDF | 「导出 PDF」 | `python3 -m dv.main pdf javaguide main` |
| 打离线包 | 「导出离线包」 | `python3 -m dv.main export` |
| 上传资源 | 「上传资源」 | 丢文件进 `data/uploads/my-notes/` |

离线包产物：`data/dist/DocVault-offline-日期.zip`（= site/ 纯静态站 + pdf/ 全部 PDF）。

## 内网部署

```bash
unzip DocVault-offline-*.zip -d dv
# 方式一：临时
cd dv/site && python3 -m http.server 8080
# 方式二：nginx
# server { listen 80; root /opt/dv/site; index index.html; }
```

零外部依赖（无 CDN / 在线字体 / JS 库），内网机器只需任意静态文件服务器。

## 常驻服务（如鲁班猫服务器）

```ini
# /etc/systemd/system/docvault.service
[Unit]
After=network-online.target
[Service]
WorkingDirectory=/opt/docvault
ExecStart=/usr/bin/python3 -m dv.main serve --port 8787
Restart=always
[Install]
WantedBy=multi-user.target
```

定时自动同步（服务器有外网时）：`crontab: 0 4 * * * cd /opt/docvault && python3 -m dv.main sync all`

## 加新项目

编辑 `projects.json`（支持 `type:github` 与 `type:upload`），然后同步。
