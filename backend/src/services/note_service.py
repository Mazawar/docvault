"""笔记服务：文件系统为事实源 data/notes/<笔记本>/<笔记>.md。

- 不走 SQLite：目录拷走即可在另一台机器完整恢复（DESIGN.md 笔记模块原则）
- 纯文本 front-matter（title/tags）由 md_to_html 前的 strip_fm 处理
- 渲染复用 util 管线（与文章同款：高亮/提示块/图片本地化重写）
"""
import os
import re
import shutil
import time
from pathlib import Path

from ..core import config, util

ROOT = config.DATA / 'notes'
DEFAULT_FOLDER = '我的笔记'
ALLOWED_EXTS = ('.md',)


def _safe(name: str) -> str:
    name = Path(name).name.strip()
    if not name or name.startswith('.'):
        raise ValueError('非法名称')
    return name


def _folder(folder: str) -> Path:
    f = ROOT / _safe(folder or DEFAULT_FOLDER)
    f.mkdir(parents=True, exist_ok=True)
    return f


def _title_of(p: Path) -> str:
    try:
        text, fm = util.strip_fm(p.read_text(encoding='utf-8', errors='ignore')[:4000])
    except OSError:
        return p.stem
    t = util.fm_title(fm)
    if t:
        return t
    for line in text.splitlines():
        if line.startswith('# '):
            return line[2:].strip()
    return p.stem


def list_index() -> list[dict]:
    """-> [{folder, notes:[{name,title,updated,size}]}]，笔记本按名排序，笔记按更新时间倒序。"""
    out = []
    if not ROOT.exists():
        ROOT.mkdir(parents=True, exist_ok=True)
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith('.'):
            continue
        notes = []
        for f in d.glob('*.md'):
            st = f.stat()
            notes.append({'name': f.stem, 'title': _title_of(f),
                          'updated': time.strftime('%Y-%m-%d %H:%M', time.localtime(st.st_mtime)),
                          'ts': int(st.st_mtime), 'size': st.st_size})
        notes.sort(key=lambda x: -x['ts'])
        out.append({'folder': d.name, 'notes': notes})
    return out


def iter_notes():
    """遍历全部笔记 -> [(folder, name, path)]。"""
    if not ROOT.exists():
        return
    for d in sorted(ROOT.iterdir()):
        if d.is_dir() and not d.name.startswith('.'):
            for f in sorted(d.glob('*.md')):
                yield d.name, f.stem, f


def _note_path(folder: str, name: str) -> Path:
    p = _folder(folder) / (_safe(name) + '.md')
    if not p.exists():
        raise FileNotFoundError(f'笔记不存在: {folder}/{name}')
    return p


def read(folder: str, name: str) -> dict:
    p = _note_path(folder, name)
    st = p.stat()
    return {'folder': folder, 'name': name, 'title': _title_of(p),
            'content': p.read_text(encoding='utf-8', errors='ignore'),
            'updated': time.strftime('%Y-%m-%d %H:%M', time.localtime(st.st_mtime))}


def write(folder: str, name: str, content: str) -> dict:
    p = _folder(folder) / (_safe(name) + '.md')
    tmp = p.with_suffix('.tmp')
    tmp.write_text(content, encoding='utf-8')
    os.replace(tmp, p)
    return read(folder, name)


def create(folder: str, name: str) -> dict:
    p = _folder(folder) / (_safe(name) + '.md')
    if p.exists():
        raise FileExistsError(f'笔记已存在: {name}')
    p.write_text(f'# {name}\n\n', encoding='utf-8')
    return read(folder, name)


def delete(folder: str, name: str):
    _note_path(folder, name).unlink()


def rename(folder: str, old: str, new: str) -> dict:
    src = _note_path(folder, old)
    dst = _folder(folder) / (_safe(new) + '.md')
    if dst.exists():
        raise FileExistsError(f'目标已存在: {new}')
    src.rename(dst)
    return read(folder, new)


def delete_folder(folder: str):
    d = ROOT / _safe(folder)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def render_html(content: str) -> str:
    """与文章同款渲染管线（高亮/提示块/已缓存远程图重写）。"""
    from . import content_service
    body = util.md_to_html(content)
    body = util.alerts(body)
    return content_service._rewrite_remote(body)


def render_payload(folder: str, name: str) -> dict:
    p = _note_path(folder, name)
    content = p.read_text(encoding='utf-8', errors='ignore')
    return {'folder': folder, 'name': name, 'title': _title_of(p),
            'html': render_html(content),
            'updated': time.strftime('%Y-%m-%d %H:%M', time.localtime(p.stat().st_mtime))}


def static_index() -> dict:
    return {'folders': list_index()}
