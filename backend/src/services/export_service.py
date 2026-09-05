"""离线导出服务：前端 dist + 预渲染 JSON 数据树 + 资源 → 纯静态站 → zip。

产物结构（任意静态文件服务器可跑，无需后端）：
  site/index.html        前端 SPA（hash 路由）
  site/d/index.json      书架数据
  site/d/{pid}/{bid}/toc.json        书目录
  site/d/{pid}/{bid}/{slug}.json     文章（预渲染 HTML）
  site/d/search.json     全库搜索索引（前端本地检索）
  site/a/<asset>         图片缓存

健壮性：zip 永远直接从临时目录打包——本地 site/ 被内网服务器占用时
导出照常成功，site/ 目录的替换降级为尽力而为。
"""
import json
import os
import re
import shutil
import time
import zipfile
from pathlib import Path
from ..core import config, util
from ..models import repository
from . import content_service, note_service


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')


def _copy_assets(site: Path, html_bodies):
    """收集正文引用到的 /a/ 资源 + 正文中的远程图，拷入 site/a/。"""
    adir = site / 'a'
    adir.mkdir(parents=True, exist_ok=True)
    names = set()
    for body in html_bodies:
        names |= {m.group(1) for m in re.finditer(r'src="/a/([^"]+)"', body)}
    for n in names:
        src = config.ASSETS / n
        dst = adir / n
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)


def _build_tmp(logcb=print) -> Path:
    """渲染全部内容到 data/dist/site.tmp/，返回该目录。"""
    front = config.frontend_dist()
    if not front:
        raise RuntimeError('前端未构建：请先在 frontend/ 执行 npm run build')
    tmp = config.DIST / 'site.tmp'
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    # 前端文件平铺到站点根（index.html 必须在根）
    for f in front.rglob('*'):
        if f.is_file():
            rel = f.relative_to(front)
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, tmp / rel)

    _write_json(tmp / 'd' / 'index.json', repository.index_payload())

    search_idx, bodies = [], []
    for p in repository.list_projects():
        if p['type'] == 'upload':
            continue  # 笔记走独立 /notes 模块
        for b in repository.list_books(p['id']):
            articles = repository.list_articles(p['id'], b['id'])
            _write_json(tmp / 'd' / p['id'] / b['id'] / 'toc.json',
                        content_service.book_payload(p['id'], b['id']))
            for a in articles:
                payload = content_service.render_article(p['id'], b['id'], a['slug'])
                if not payload:
                    continue
                _write_json(tmp / 'd' / p['id'] / b['id'] / (a['slug'] + '.json'), payload)
                bodies.append(payload['html'])
                search_idx.append({'pid': p['id'], 'bid': b['id'], 'slug': a['slug'],
                                   't': a['title'], 'x': content_service.search_text(payload['html'])})
            logcb(f"[{p['id']}/{b['id']}] {len(articles)} pages")
    _write_json(tmp / 'd' / 'search.json', search_idx)
    notes = note_service.static_index()
    _write_json(tmp / 'd' / 'notes' / 'index.json', notes)
    for fol in notes['folders']:
        for n in fol['notes']:
            payload = note_service.render_payload(fol['folder'], n['name'])
            _write_json(tmp / 'd' / 'notes' / fol['folder'] / (n['name'] + '.json'), payload)
            ntx = (config.DATA / 'notes' / fol['folder'] / (n['name'] + '.md')).read_text(
                encoding='utf-8', errors='ignore')
            search_idx.append({'pid': '__notes__', 'bid': fol['folder'], 'slug': n['name'],
                               't': n['title'], 'x': content_service.search_text(ntx)})
    logcb(f"[notes] {sum(len(f['notes']) for f in notes['folders'])} pages")
    _copy_assets(tmp, bodies)
    return tmp


def _promote(tmp: Path, logcb=print, strict=False) -> Path:
    """把 tmp 内容落地为正式 site/。

    首选换名替换（原子、干净）；site/ 被进程占用（如内网静态服务器的 CWD）
    导致目录无法改名时，退化为「原位清空 + 内容同步」——Windows 只锁目录
    本身，其中的文件仍可重写，因此本地预览/内网服务器都不阻塞导出。
    """
    site = config.SITE
    if not site.exists():
        tmp.rename(site)
        return site
    try:
        old = config.DIST / 'site.old'
        if old.exists():
            shutil.rmtree(old, ignore_errors=True)
        site.rename(old)
        tmp.rename(site)
        shutil.rmtree(old, ignore_errors=True)
        return site
    except OSError:
        pass
    # 原位内容同步
    for child in site.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            try:
                child.unlink()
            except OSError:
                pass
    copied = 0
    for f in tmp.rglob('*'):
        rel = f.relative_to(tmp)
        dst = site / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if f.is_file():
            shutil.copy2(f, dst)
            copied += 1
    shutil.rmtree(tmp, ignore_errors=True)
    logcb(f'提示: site 目录被占用，已原位同步 {copied} 个文件')
    return site


def build_site(logcb=print):
    """生成 data/dist/site/（纯静态）。"""
    tmp = _build_tmp(logcb)
    site = _promote(tmp, logcb)
    logcb(f'site -> {site}')
    return site


def export_zip(logcb=print):
    """打离线包：data/dist/DocVault-offline-日期.zip。zip 直接来自临时目录，
    本地 site/ 是否被占用不影响导出。"""
    tmp = _build_tmp(logcb)
    stamp = time.strftime('%Y%m%d')
    out = config.DIST / f'DocVault-offline-{stamp}.zip'
    tmp_zip = config.DIST / f'.{out.name}.tmp'
    with zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_STORED) as z:
        # 注意 arcname：站点目录在包内必须叫 site/（tmp 的实际名字是 site.tmp）
        for root, arc_root in ((tmp, 'site'), (config.PDF_DIR, 'pdf')):
            if not root.exists():
                continue
            for f in Path(root).rglob('*'):
                if f.is_file():
                    z.write(f, str(Path(arc_root) / f.relative_to(root)))
    for i in range(3):
        try:
            os.replace(tmp_zip, out)
            break
        except PermissionError:
            if i == 2:
                # 旧包被占用（如资源管理器/杀软正打开）→ 落盘为带时间的新包，绝不让导出失败
                out = config.DIST / f'DocVault-offline-{stamp}-{time.strftime("%H%M%S")}.zip'
                os.replace(tmp_zip, out)
                break
            time.sleep(2)
    # 只保留最近 3 个离线包
    zips = sorted(config.DIST.glob('DocVault-offline-*.zip'))
    for old in zips[:-3]:
        try:
            old.unlink()
        except OSError:
            pass
    _promote(tmp, logcb, strict=False)
    logcb(f'{out.name} ({out.stat().st_size / 1048576:.0f} MB)')
    return out


def latest_zip():
    zips = sorted(config.DIST.glob('DocVault-offline-*.zip'))
    return zips[-1] if zips else None
