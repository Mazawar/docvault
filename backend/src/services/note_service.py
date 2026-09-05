"""笔记服务：文件系统为事实源 data/notes/<笔记本>/<笔记>.md。

- 不走 SQLite：目录拷走即可在另一台机器完整恢复（DESIGN.md 笔记模块原则）
- 纯文本 front-matter（title/tags）由 md_to_html 前的 strip_fm 处理
- 渲染复用 util 管线（与文章同款：高亮/提示块/图片本地化重写）
"""
import hashlib
import os
import re
import shutil
import time
import urllib.parse
from pathlib import Path

from ..core import config, util
from ..models import database, repository

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


def _fm_tags(fm: str) -> list[str]:
    m = re.search(r'^tags:\s*(.+)$', fm, re.M)
    if m:
        v = m.group(1).strip()
        if v.startswith('['):
            return [x.strip() for x in v.strip('[]').split(',') if x.strip()]
        return [v] if v else []
    m2 = re.search(r'^tags:\s*\n((?:\s*-\s*.+\n?)+)', fm, re.M)
    if m2:
        return [ln.strip()[1:].strip() for ln in m2.group(1).strip().splitlines() if ln.strip()]
    return []


def _tags_of(p: Path) -> list[str]:
    try:
        _, fm = util.strip_fm(p.read_text(encoding='utf-8', errors='ignore')[:4000])
    except OSError:
        return []
    return _fm_tags(fm)


def list_index() -> list[dict]:
    """-> [{folder, notes:[{name,title,tags,updated,size}]}]，笔记本按名排序，笔记按更新时间倒序。"""
    out = []
    if not ROOT.exists():
        ROOT.mkdir(parents=True, exist_ok=True)
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith('.'):
            continue
        notes = []
        for f in d.glob('*.md'):
            st = f.stat()
            notes.append({'name': f.stem, 'title': _title_of(f), 'tags': _tags_of(f),
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
    raw = p.read_text(encoding='utf-8', errors='ignore')
    body, fm = util.strip_fm(raw)
    return {'folder': folder, 'name': name, 'title': _title_of(p),
            'fm_title': util.fm_title(fm) or '',
            'tags': _fm_tags(fm),
            'content': body,
            'updated': time.strftime('%Y-%m-%d %H:%M', time.localtime(st.st_mtime))}


def _compose_fm(title: str | None, tags: list[str] | None) -> str:
    lines = ['---']
    if title:
        lines.append(f'title: {title}')
    if tags:
        lines.append('tags: [' + ', '.join(tags) + ']')
    lines.append('---')
    return '\n'.join(lines) + '\n\n'


def write(folder: str, name: str, content: str, tags=None, title=None) -> dict:
    # 编辑器提交的 content 为正文（不含 front-matter）；title/tags 由参数管理
    if title is not None or tags is not None:
        content = util.strip_fm(content)[0]
        fm_title = title if title else ''
        fm_tags = tags if tags is not None else []
        if fm_title or fm_tags:
            content = _compose_fm(fm_title, fm_tags) + content
    p = _folder(folder) / (_safe(name) + '.md')
    tmp = p.with_suffix('.tmp')
    tmp.write_text(content, encoding='utf-8')
    os.replace(tmp, p)
    row = read(folder, name)
    try:
        repository.note_fts_upsert(folder, name, row['title'], content)
    except Exception:
        pass
    return row


def create(folder: str, name: str) -> dict:
    p = _folder(folder) / (_safe(name) + '.md')
    if p.exists():
        raise FileExistsError(f'笔记已存在: {name}')
    p.write_text(f'# {name}\n\n', encoding='utf-8')
    return read(folder, name)


def delete(folder: str, name: str):
    _note_path(folder, name).unlink()
    try:
        repository.note_fts_delete(name)
    except Exception:
        pass


def rename(folder: str, old: str, new: str) -> dict:
    src = _note_path(folder, old)
    dst = _folder(folder) / (_safe(new) + '.md')
    if dst.exists():
        raise FileExistsError(f'目标已存在: {new}')
    src.rename(dst)
    return read(folder, new)


def rename_folder(old: str, new: str) -> dict:
    src = ROOT / _safe(old)
    dst = ROOT / _safe(new)
    if not src.is_dir():
        raise FileNotFoundError(f'笔记本不存在: {old}')
    if dst.exists():
        raise FileExistsError(f'笔记本已存在: {new}')
    src.rename(dst)
    for p in sorted(dst.glob('*.md')):
        try:
            row = read(new, p.stem)
            repository.note_fts_upsert(new, p.stem, row['title'],
                                       p.read_text(encoding='utf-8', errors='ignore'))
        except Exception:
            pass
    return {'ok': True}


def delete_folder(folder: str, force: bool = False):
    d = ROOT / _safe(folder)
    if not d.is_dir():
        raise FileNotFoundError(f'笔记本不存在: {folder}')
    notes = list(d.glob('*.md'))
    if notes and not force:
        raise ValueError(f'笔记本内还有 {len(notes)} 篇笔记，请先移走或删除')
    shutil.rmtree(d, ignore_errors=True)
    for p in notes:
        repository.note_fts_delete(p.stem)
    return {'ok': True}


def _note_lookup() -> dict:
    """stem/title -> (folder, name)，供 [[双链]] 解析。"""
    lk = {}
    for folder, name, p in iter_notes():
        lk.setdefault(name.lower(), (folder, name))
        lk.setdefault(_title_of(p).lower(), (folder, name))
    return lk


def render_html(content: str) -> str:
    """与文章同款渲染管线 + [[双链]]（高亮/提示块/已缓存远程图重写）。"""
    from . import content_service
    body = util.md_to_html(content)
    body = util.alerts(body)

    lk = _note_lookup()

    def wl(m):
        inner = m.group(1)
        target, _, label = inner.partition('|')
        label = (label or target).strip()
        hit = lk.get(target.strip().lower())
        if hit:
            f, n = hit
            return (f'<a class="wikilink" href="#/notes?folder={urllib.parse.quote(f)}'
                    f'&name={urllib.parse.quote(n)}">{label}</a>')
        return f'<span class="wikilink missing">{label}</span>'

    body = re.sub(r'\[\[([^\]]+)\]\]', wl, body)
    return content_service._rewrite_remote(body)


def search(q: str, limit: int = 30) -> list[dict]:
    rows = repository.search_notes(q, limit)
    words = [w for w in re.sub(r'[^\w ]+', ' ', q).split() if w]
    out = []
    for r in rows:
        p = ROOT / r['folder'] / (r['name'] + '.md')
        raw = p.read_text(encoding='utf-8', errors='ignore') if p.exists() else ''
        text, _ = util.strip_fm(raw)
        out.append({'kind': 'note', 'pid': '__notes__', 'bid': r['folder'], 'slug': r['name'],
                    'title': r['title'], 'snip': repository._make_snip(text, words)})
    return out


def backlinks(folder: str, name: str) -> list[dict]:
    target = {name.lower()}
    p0 = ROOT / folder / (name + '.md')
    if p0.exists():
        target.add(_title_of(p0).lower())
    out = []
    for f2, n2, p in iter_notes():
        if f2 == folder and n2 == name:
            continue
        text = p.read_text(encoding='utf-8', errors='ignore')
        if any(f'[[{t}]]' in text or f'[[{t}|' in text for t in target):
            out.append({'folder': f2, 'name': n2, 'title': _title_of(p)})
    return out


def daily() -> dict:
    folder = '日记'
    name = time.strftime('%Y-%m-%d')
    p = ROOT / folder / (name + '.md')
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f'# {name}\n\n', encoding='utf-8')
    return read(folder, name)


def save_image(data: bytes, ext: str = '.png') -> str:
    name = hashlib.sha256(data).hexdigest()[:32] + ext
    (config.ASSETS).mkdir(parents=True, exist_ok=True)
    (config.ASSETS / name).write_bytes(data)
    return '/a/' + name


def render_payload(folder: str, name: str) -> dict:
    p = _note_path(folder, name)
    content = p.read_text(encoding='utf-8', errors='ignore')
    return {'folder': folder, 'name': name, 'title': _title_of(p),
            'html': render_html(content),
            'updated': time.strftime('%Y-%m-%d %H:%M', time.localtime(p.stat().st_mtime))}


def static_index() -> dict:
    return {'folders': list_index()}
