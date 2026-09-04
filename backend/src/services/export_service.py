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
from . import content_service


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
    _copy_assets(tmp, bodies)
    return tmp


def _promote(tmp: Path, logcb=print, strict=False) -> Path:
    """把 tmp 目录替换为正式 site/。strict=True 时占用即报错（CLI 场景），
    否则降级保留 tmp 并提示（打包场景，zip 已生成不受影响）。"""
    site = config.SITE
    if not site.exists():
        tmp.rename(site)
        return site
    old = config.DIST / 'site.old'
    if old.exists():
        shutil.rmtree(old, ignore_errors=True)
    try:
        site.rename(old)
    except OSError as e:
        if strict:
            raise RuntimeError(f'旧 site 目录被占用，无法替换（先停掉占用它的静态服务器）: {e}')
        logcb(f'提示: 旧 site 被占用，新站暂存于 {tmp}；释放占用后重命名即可生效')
        return tmp
    tmp.rename(site)
    shutil.rmtree(old, ignore_errors=True)
    return site


def build_site(logcb=print):
    """生成 data/dist/site/（纯静态）。占用阻塞时按 CLI 语义报错。"""
    tmp = _build_tmp(logcb)
    site = _promote(tmp, logcb, strict=True)
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
        for root in (tmp, config.PDF_DIR):
            if not root.exists():
                continue
            for f in Path(root).rglob('*'):
                if f.is_file():
                    z.write(f, f.relative_to(config.DIST))
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
