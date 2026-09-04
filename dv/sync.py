"""Sync sources -> manifest + image cache."""
import json, os, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from . import util

BASE = Path(__file__).resolve().parent.parent
# DV_DATA 可把数据目录放纯沙箱盘（PRoot 下 /var/minis 桥接 App 存储会出幽灵条目）
DATA = Path(os.environ.get('DV_DATA', str(BASE / 'data')))
REPOS = DATA / 'repos'
ASSETS = DATA / 'assets'
UPLOADS = DATA / 'uploads'
MANIFESTS = DATA / 'manifest'


def projects():
    cfg = json.loads((BASE / 'projects.json').read_text(encoding='utf-8'))
    return cfg['projects']


def project(pid):
    for p in projects():
        if p['id'] == pid:
            return p
    raise KeyError(pid)


def log(msg):
    print(time.strftime('%H:%M:%S'), msg, flush=True)


def ensure_repo(p):
    dest = REPOS / p['id']
    url = f"https://github.com/{p['repo']}.git"
    if (dest / '.git').exists():
        r = subprocess.run(['git', '-C', str(dest), 'pull', '--ff-only'],
                           capture_output=True, text=True)
        log(f"[{p['id']}] pull: {(r.stdout + r.stderr).strip()[:120]}")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(['git', 'clone', '--depth', '1', url, str(dest)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-300:])
        log(f"[{p['id']}] cloned {p['repo']}")
    return dest


def discover_books(p):
    """-> [(book_id, book_title, repo_root, [rel_md_paths sorted])]"""
    root = REPOS / p['id'] / p.get('root', '.')
    books_cfg = p.get('books')
    out = []
    if books_cfg:
        for sub, title in books_cfg.items():
            bdir = root / sub
            arts = _scan(bdir, bdir)
            if arts:
                out.append((sub, title, bdir, arts))
    else:
        arts = _scan(root, root)
        out.append(('main', p['name'], root, arts))
    return out


def _scan(bdir, root):
    found = []
    for f in bdir.rglob('*.md'):
        rel = f.relative_to(root)
        if any(x.startswith('.') for x in rel.parts):
            continue
        h1 = util.h1_of(f)
        found.append((util.order_key(rel, h1), rel, h1))
    found.sort(key=lambda x: x[0])
    return [(str(r.with_suffix('')), t) for _, r, t in found]


def sync_project(pid):
    p = project(pid)
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    books = []
    if p['type'] == 'github':
        ensure_repo(p)
        for bid, btitle, broot, arts in discover_books(p):
            books.append({'id': bid, 'title': btitle, 'root': str(broot),
                          'articles': [{'slug': s, 'title': t} for s, t in arts]})
        log(f"[{pid}] {len(books)} books, "
            f"{sum(len(b['articles']) for b in books)} articles")
    elif p['type'] == 'upload':
        udir = UPLOADS / pid
        udir.mkdir(parents=True, exist_ok=True)
        arts = []
        for f in sorted(udir.glob('*.md')):
            arts.append({'slug': f.stem, 'title': util.h1_of(f)})
        books.append({'id': 'notes', 'title': '笔记', 'root': str(udir),
                      'articles': arts})
        log(f"[{pid}] {len(arts)} uploaded notes")

    # images
    urls = set()
    for b in books:
        for a in b['articles']:
            tx = (Path(b['root']) / (a['slug'] + '.md')).read_text(
                encoding='utf-8', errors='ignore')
            urls.update(util.collect_urls(tx))
    todo = [u for u in sorted(urls) if not (ASSETS / util.asset_name(u)).exists()]
    log(f"[{pid}] images: {len(urls)} total, {len(todo)} to fetch")
    ok = fail = 0
    with ThreadPoolExecutor(16) as ex:
        futs = {ex.submit(util.fetch, u, ASSETS): u for u in todo}
        for fu in as_completed(futs):
            if fu.result():
                ok += 1
            else:
                fail += 1
                log(f"  FAIL {futs[fu][:100]}")
    log(f"[{pid}] images ok={ok} fail={fail}")

    man = {'id': pid, 'name': p['name'], 'type': p['type'],
           'updated': time.strftime('%Y-%m-%d %H:%M'), 'books': books}
    (MANIFESTS / f'{pid}.json').write_text(
        json.dumps(man, ensure_ascii=False, indent=1), encoding='utf-8')
    return man


def load_manifests():
    out = []
    if MANIFESTS.exists():
        for f in sorted(MANIFESTS.glob('*.json')):
            out.append(json.loads(f.read_text(encoding='utf-8')))
    return out
