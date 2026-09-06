"""全局配置与路径：开发态锚定 backend/，打包态锚定 exe 所在目录。"""
import os
import sys
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]  # backend/dv/core/config.py -> backend/


BASE = _base_dir()
# DV_DATA 可把数据目录指到别处（沙箱/便携盘场景）
DATA = Path(os.environ.get('DV_DATA', str(BASE / 'data')))
# DV_REPOS 可把仓库缓存单独迁出（repos 是第三方源码缓存，迁出源码树可避免被
# 代码扫描/门禁工具当作项目代码，且不随项目备份膨胀）
REPOS = Path(os.environ.get('DV_REPOS', str(DATA / 'repos')))
ASSETS = DATA / 'assets'
UPLOADS = DATA / 'uploads'
DIST = DATA / 'dist'
SITE = DIST / 'site'
PDF_DIR = DIST / 'pdf'
DB = DATA / 'docvault.db'
LOG_FILE = DATA / 'docvault.log'

READ_PORT = int(os.environ.get('DV_PORT', '8787'))

_FRONTEND_CANDIDATES = (
    BASE.parent / 'frontend' / 'dist',                    # 开发态（monorepo 布局）
    DATA / 'frontend-dist',                               # 资源包导入（离线机免 npm）
    Path(getattr(sys, '_MEIPASS', '')) / 'frontend' / 'dist',  # PyInstaller 解包
)


def frontend_dist() -> Path | None:
    """已构建的前端产物目录；未构建返回 None。"""
    for p in _FRONTEND_CANDIDATES:
        if (p / 'index.html').exists():
            return p
    return None


def ensure_dirs():
    for d in (DATA, REPOS, ASSETS, UPLOADS, DIST, PDF_DIR):
        d.mkdir(parents=True, exist_ok=True)
