"""FastAPI service: static site + admin console + job queue."""
import json, threading, time, zipfile
from pathlib import Path
from fastapi import FastAPI, File, Form, UploadFile, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from . import sync as syncmod, render, pdfexport

BASE = syncmod.BASE
SITE = render.SITE
DIST = syncmod.DATA / 'dist'
JOBS_FILE = syncmod.DATA / 'jobs.json'

for d in (syncmod.ASSETS, syncmod.UPLOADS, syncmod.MANIFESTS, SITE, DIST / 'pdf'):
    d.mkdir(parents=True, exist_ok=True)
if not (SITE / 'index.html').exists():
    (SITE / 'index.html').write_text(
        '<meta charset="utf-8"><p>尚未构建，请访问 /admin 执行同步。</p>')

app = FastAPI(title='DocVault')
JOBS, _lk, _sem = {}, threading.Lock(), threading.Semaphore(1)


def _save_jobs():
    with _lk:
        JOBS_FILE.write_text(json.dumps(
            dict(list(JOBS.items())[-50:]), ensure_ascii=False, indent=1), encoding='utf-8')


def start_job(name, fn):
    jid = time.strftime('%H%M%S') + '-' + name
    j = {'id': jid, 'name': name, 'status': 'running',
         'start': time.strftime('%H:%M:%S'), 'log': []}
    with _lk:
        JOBS[jid] = j
    _save_jobs()

    def run():
        with _sem:
            try:
                fn(j)
                j['status'] = 'done'
            except Exception as e:
                j['status'] = 'error'
                j['log'].append('ERROR: ' + repr(e)[:800])
            j['end'] = time.strftime('%H:%M:%S')
            _save_jobs()
    threading.Thread(target=run, daemon=True).start()
    return j


def do_sync(pids, j):
    for pid in pids:
        j['log'].append(f'sync {pid} ...')
        syncmod.sync_project(pid)
    j['log'].append('build site ...')
    render.build()
    j['log'].append('OK')


@app.get('/admin', response_class=HTMLResponse)
def admin():
    return (BASE / 'dv' / 'admin.html').read_text(encoding='utf-8')


@app.get('/admin/api/status')
def status():
    mans = {m['id']: m for m in syncmod.load_manifests()}
    projs = []
    for p in syncmod.projects():
        m = mans.get(p['id'], {})
        projs.append({
            'id': p['id'], 'name': p['name'], 'type': p['type'],
            'updated': m.get('updated', '-'),
            'books': [{'id': b['id'], 'title': b['title'], 'n': len(b['articles'])}
                      for b in m.get('books', [])]})
    pdfs = sorted((DIST / 'pdf').glob('*.pdf')) if (DIST / 'pdf').exists() else []
    zips = sorted(DIST.glob('DocVault-offline-*.zip')) if DIST.exists() else []
    notes = []
    ndir = syncmod.UPLOADS / 'my-notes'
    if ndir.exists():
        notes = sorted([{'name': p.name, 'size': p.stat().st_size} for p in ndir.glob('*.md')],
                       key=lambda x: x['name'])
    return {'projects': projs,
            'pdfs': [p.name for p in pdfs],
            'zip': zips[-1].name if zips else None,
            'notes': notes,
            'jobs': dict(list(JOBS.items())[-8:])}


@app.post('/admin/api/sync/{pid}')
def sync_one(pid: str):
    start_job(f'sync-{pid}', lambda j: do_sync([pid], j))
    return {'ok': True}


@app.post('/admin/api/sync-all')
def sync_all():
    pids = [p['id'] for p in syncmod.projects()]
    start_job('sync-all', lambda j: do_sync(pids, j))
    return {'ok': True}


@app.post('/admin/api/pdf/{pid}/{book}')
def pdf(pid: str, book: str):
    start_job(f'pdf-{pid}-{book}',
              lambda j: pdfexport.export_book(pid, book, log=lambda m: j['log'].append(str(m))))
    return {'ok': True}


@app.post('/admin/api/upload')
async def upload(pid: str = Form('my-notes'), files: list[UploadFile] = File(...)):
    p = syncmod.project(pid)
    udir = syncmod.UPLOADS / pid
    saved = []
    for f in files:
        name = Path(f.filename).name
        if name.lower().endswith('.md'):
            dest = udir / name
        else:
            dest = udir / '_files' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(await f.read())
        saved.append(name)
    start_job(f'sync-{pid}', lambda j: do_sync([pid], j))
    return {'ok': True, 'saved': saved}


PID_RE = __import__('re').compile(r'^[a-z0-9][a-z0-9-]{1,40}$')
REPO_RE = __import__('re').compile(r'^[\w.-]+/[\w.-]+$')


def _save_projects(projs):
    (BASE / 'projects.json').write_text(
        json.dumps({'projects': projs}, ensure_ascii=False, indent=2), encoding='utf-8')


@app.get('/admin/api/projects')
def list_projects():
    return syncmod.projects()


@app.post('/admin/api/projects')
async def project_save(spec: dict = Body(...)):
    pid = str(spec.get('id', '')).strip().lower()
    if not PID_RE.match(pid):
        return JSONResponse({'error': 'id 需为小写字母/数字/连字符，2~40 位'}, status_code=400)
    name = str(spec.get('name', '')).strip() or pid
    ptype = spec.get('type', 'github')
    if ptype not in ('github', 'upload'):
        return JSONResponse({'error': 'type 仅支持 github/upload'}, status_code=400)
    entry = {'id': pid, 'name': name, 'type': ptype}
    if ptype == 'github':
        repo = str(spec.get('repo', '')).strip()
        if not REPO_RE.match(repo):
            return JSONResponse({'error': 'repo 需为 owner/name 格式'}, status_code=400)
        entry['repo'] = repo
        entry['root'] = str(spec.get('root', '')).strip() or '.'
        books = spec.get('books') or {}
        if isinstance(books, dict) and books:
            entry['books'] = {str(k): str(v) for k, v in books.items()}
    else:
        (syncmod.UPLOADS / pid).mkdir(parents=True, exist_ok=True)
    projs = [p for p in syncmod.projects() if p['id'] != pid]
    projs.append(entry)
    _save_projects(projs)
    start_job(f'sync-{pid}', lambda j: do_sync([pid], j))
    return {'ok': True}


@app.delete('/admin/api/projects/{pid}')
def project_delete(pid: str, purge: bool = True):
    projs = syncmod.projects()
    if not any(p['id'] == pid for p in projs):
        return JSONResponse({'error': 'not found'}, status_code=404)
    _save_projects([p for p in projs if p['id'] != pid])

    def work(j):
        import shutil
        if purge:
            for d in (syncmod.REPOS / pid, syncmod.UPLOADS / pid,
                      syncmod.MANIFESTS / f'{pid}.json'):
                if d.is_dir():
                    shutil.rmtree(d, ignore_errors=True)
                elif d.exists():
                    d.unlink()
            for f in (DIST / 'pdf').glob(f'{pid}__*.pdf'):
                f.unlink(missing_ok=True)
            j['log'].append(f'purged {pid} data')
        j['log'].append('rebuild site ...')
        render.build()
        j['log'].append('OK')
    start_job(f'delete-{pid}', work)
    return {'ok': True}


@app.get('/admin/api/articles')
def articles(pid: str = '', q: str = '', limit: int = 100):
    out = []
    for m in syncmod.load_manifests():
        if pid and m['id'] != pid:
            continue
        for b in m['books']:
            for a in b['articles']:
                t, s = a['title'], a['slug']
                if q and q.lower() not in t.lower() and q.lower() not in s.lower():
                    continue
                out.append({'pid': m['id'], 'pname': m['name'], 'book': b['title'],
                            'title': t, 'url': f"/p/{m['id']}/{b['id']}/{a['slug']}.html"})
    return {'total': len(out), 'items': out[:max(1, min(limit, 500))]}


@app.get('/admin/api/note')
def note_get(name: str):
    name = Path(name).name
    p = syncmod.UPLOADS / 'my-notes' / name
    if not p.exists():
        return JSONResponse({'error': 'not found'}, status_code=404)
    return {'name': name, 'content': p.read_text(encoding='utf-8', errors='ignore')}


@app.post('/admin/api/note')
async def note_save(name: str = Form(...), content: str = Form(...)):
    name = Path(name).name or 'untitled.md'
    if not name.endswith('.md'):
        name += '.md'
    d = syncmod.UPLOADS / 'my-notes'
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(content, encoding='utf-8')
    start_job('sync-my-notes', lambda j: do_sync(['my-notes'], j))
    return {'ok': True, 'name': name}


@app.post('/admin/api/export')
def export():
    def make(j):
        stamp = time.strftime('%Y%m%d')
        out = DIST / f'DocVault-offline-{stamp}.zip'
        j['log'].append('zipping site/ + pdf/ ...')
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_STORED) as z:
            for root in (SITE, DIST / 'pdf'):
                for f in Path(root).rglob('*'):
                    if f.is_file():
                        z.write(f, f.relative_to(syncmod.DATA))
        j['log'].append(f'{out.name} {out.stat().st_size/1048576:.0f} MB')
    start_job('export', make)
    return {'ok': True}


@app.get('/admin/api/download')
def download():
    zips = sorted(DIST.glob('DocVault-offline-*.zip'))
    if not zips:
        return JSONResponse({'error': 'no zip yet'}, status_code=404)
    return FileResponse(zips[-1], filename=zips[-1].name)


@app.get('/files/{pid}/{name}')
def files(pid: str, name: str):
    return FileResponse(syncmod.UPLOADS / pid / '_files' / name)


app.mount('/files-static', StaticFiles(directory=syncmod.UPLOADS), name='files-static')
app.mount('/', StaticFiles(directory=SITE, html=True), name='site')
