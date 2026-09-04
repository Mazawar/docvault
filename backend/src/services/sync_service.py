"""同步服务：拉取仓库/扫描上传目录 → 文章入库 → 图片全局缓存。"""
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from ..core import config, util
from ..models import repository


def log(msg):
    """stdout 可能失效（后台服务/无控制台），失败静默；同时落盘日志。"""
    line = time.strftime('%H:%M:%S') + ' ' + msg
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        config.DATA.mkdir(parents=True, exist_ok=True)
        with open(config.DATA / 'sync.log', 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def _detect_proxy():
    """代理探测：环境变量优先，Windows 读系统代理设置。仅注入子进程环境。"""
    for k in ('HTTPS_PROXY', 'https_proxy', 'HTTP_PROXY', 'http_proxy'):
        if os.environ.get(k):
            return os.environ[k]
    if sys.platform == 'win32':
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r'Software\Microsoft\Windows\CurrentVersion\Internet Settings')
            enabled = winreg.QueryValueEx(k, 'ProxyEnable')[0]
            server = str(winreg.QueryValueEx(k, 'ProxyServer')[0])
            if enabled and server and '=' not in server:
                return server if '://' in server else 'http://' + server
        except Exception:
            pass
    return None


def _git_env():
    proxy = _detect_proxy()
    if not proxy:
        return None
    env = dict(os.environ)
    env['HTTPS_PROXY'] = env['https_proxy'] = proxy
    env['HTTP_PROXY'] = env['http_proxy'] = proxy
    log(f'git via proxy {proxy}')
    return env


def ensure_repo(p):
    dest = config.REPOS / p['id']
    url = f"https://github.com/{p['repo']}.git"
    env = _git_env()
    if (dest / '.git').exists():
        r = subprocess.run(['git', '-C', str(dest), 'pull', '--ff-only'],
                           capture_output=True, text=True, env=env, timeout=600)
        log(f"[{p['id']}] pull: {(r.stdout + r.stderr).strip()[:120]}")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(['git', 'clone', '--depth', '1', url, str(dest)],
                           capture_output=True, text=True, env=env, timeout=1800)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-300:])
        log(f"[{p['id']}] cloned {p['repo']}")
    return dest


def discover_books(p):
    """-> [(book_id, book_title, book_root_dir)]，文章扫描在 _scan_book 内完成。"""
    root = config.REPOS / p['id'] / (p.get('root') or '.')
    books_cfg = p.get('books') or {}
    if books_cfg:
        return [(sub, title, root / sub) for sub, title in books_cfg.items()]
    return [('main', p['name'], root)]


def _scan_dir(bdir: Path):
    """扫描目录下全部 md → [(slug, title, body)]，按 目录编号+H1编号 排序。"""
    found = []
    for f in bdir.rglob('*.md'):
        rel = f.relative_to(bdir)
        if any(x.startswith('.') for x in rel.parts):
            continue
        h1 = util.h1_of(f)
        found.append((util.order_key(rel, h1), rel.with_suffix('').as_posix(), h1, f))
    found.sort(key=lambda x: x[0])
    out = []
    for _, slug, title, f in found:
        body = f.read_text(encoding='utf-8', errors='ignore')
        out.append({'slug': slug, 'title': title, 'body': body})
    return out


def sync_project(pid):
    p = repository.get_project(pid)
    if not p:
        raise KeyError(pid)
    books_ = []
    if p['type'] == 'github':
        ensure_repo(p)
        for bid, btitle, bdir in discover_books(p):
            arts = _scan_dir(bdir)
            if arts:
                books_.append({'id': bid, 'title': btitle, 'root': bdir, 'articles': arts})
        log(f"[{pid}] {len(books_)} books, {sum(len(b['articles']) for b in books_)} articles")
    elif p['type'] == 'upload':
        udir = config.UPLOADS / pid
        udir.mkdir(parents=True, exist_ok=True)
        arts = []
        for f in sorted(udir.glob('*.md')):
            arts.append({'slug': f.stem, 'title': util.h1_of(f),
                         'body': f.read_text(encoding='utf-8', errors='ignore')})
        books_.append({'id': 'notes', 'title': '笔记', 'root': udir, 'articles': arts})
        log(f"[{pid}] {len(arts)} uploaded notes")

    repository.replace_books(pid, books_)
    _cache_images(pid, books_)
    repository.touch_project(pid)
    return repository.get_book(pid, books_[0]['id']) if books_ else None


def _cache_images(pid, books_):
    urls = set()
    for b in books_:
        for a in b['articles']:
            urls.update(util.collect_urls(a['body']))
    todo = [u for u in sorted(urls)
            if not (config.ASSETS / util.asset_name(u)).exists()]
    log(f"[{pid}] images: {len(urls)} total, {len(todo)} to fetch")
    ok = fail = 0
    with ThreadPoolExecutor(16) as ex:
        futs = {ex.submit(util.fetch, u, config.ASSETS): u for u in todo}
        for fu in as_completed(futs):
            if fu.result():
                ok += 1
            else:
                fail += 1
                log(f"  FAIL {futs[fu][:100]}")
    log(f"[{pid}] images ok={ok} fail={fail}")


def sync_targets(pid=None):
    if pid:
        return [pid]
    return [p['id'] for p in repository.list_projects()]


def sync_all(pid=None, logcb=log):
    for t in sync_targets(pid):
        logcb(f'sync {t} ...')
        sync_project(t)
        logcb(f'sync {t} done')


def import_projects_json():
    """把 backend/projects.json 重新导入 DB（upsert），返回导入数量。"""
    f = config.BASE / 'projects.json'
    cfg = json.loads(f.read_text(encoding='utf-8'))
    for i, p in enumerate(cfg.get('projects', [])):
        repository.upsert_project({'id': p['id'], 'name': p.get('name', p['id']),
                                   'type': p.get('type', 'github'), 'repo': p.get('repo', ''),
                                   'root': p.get('root', '.'), 'books': p.get('books') or {},
                                   'group_titles': p.get('groupTitles') or {}},
                                  sort=i)
    return len(cfg.get('projects', []))
