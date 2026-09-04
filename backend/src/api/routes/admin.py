"""管理接口（控制器层）：项目 CRUD / 同步 / 上传 / 笔记 / PDF / 离线包 / 任务。"""
import re
import time
from pathlib import Path
from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from ...core import config
from ...models import repository
from ...services import (export_service, job_service, pack_service, pdf_service,
                         sync_service)

router = APIRouter(prefix='/api/admin', tags=['admin'])

PID_RE = re.compile(r'^[a-z0-9][a-z0-9-]{1,40}$')
REPO_RE = re.compile(r'^[\w.-]+/[\w.-]+$')


class ProjectSpec(BaseModel):
    id: str = Field(min_length=2, max_length=40)
    name: str = ''
    type: str = 'github'
    repo: str = ''
    root: str = '.'
    books: dict[str, str] = Field(default_factory=dict)


class SyncSpec(BaseModel):
    pid: str = ''


class PdfSpec(BaseModel):
    pid: str
    bid: str


class NoteSpec(BaseModel):
    name: str
    content: str = ''
    pid: str = 'my-notes'


@router.get('/overview')
def overview():
    projects = []
    for p in repository.list_projects():
        books = repository.list_books(p['id'])
        projects.append({**p, 'books': [{'id': b['id'], 'title': b['title'], 'n': b['n']}
                                        for b in books]})
    z = export_service.latest_zip()
    pk = pack_service.latest_pack()
    notes = []
    for up in [p for p in projects if p['type'] == 'upload']:
        ndir = config.UPLOADS / up['id']
        if ndir.exists():
            notes += [{'pid': up['id'], 'name': f.name, 'size': f.stat().st_size}
                      for f in sorted(ndir.glob('*.md'))]
    return {'projects': projects,
            'pdfs': pdf_service.list_pdfs(),
            'zip': z.name if z else None,
            'zipSize': z.stat().st_size if z else 0,
            'pack': pk.name if pk else None,
            'packSize': pk.stat().st_size if pk else 0,
            'notes': notes,
            'jobs': repository.jobs_recent(8)}


@router.post('/sync')
def sync(spec: SyncSpec = Body(default=SyncSpec())):
    job_service.start_job('sync-all' if not spec.pid else f'sync-{spec.pid}',
                          lambda logcb: sync_service.sync_all(spec.pid or None, logcb))
    return {'ok': True}


@router.post('/pdf')
def pdf(spec: PdfSpec):
    job_service.start_job(f'pdf-{spec.pid}-{spec.bid}',
                          lambda logcb: pdf_service.export_book(spec.pid, spec.bid, logcb))
    return {'ok': True}


@router.post('/export')
def export():
    job_service.start_job('生成静态站', lambda logcb: export_service.export_zip(logcb))
    return {'ok': True}


@router.get('/download')
def download():
    z = export_service.latest_zip()
    if not z:
        raise HTTPException(status_code=404, detail='尚未导出离线包')
    return FileResponse(z, filename=z.name)


@router.post('/export-pack')
def export_pack_route():
    job_service.start_job('生成资源包',
                          lambda logcb: pack_service.export_pack(False, logcb))
    return {'ok': True}


@router.get('/download-pack')
def download_pack():
    f = pack_service.latest_pack()
    if not f:
        raise HTTPException(status_code=404, detail='尚未导出资源包')
    return FileResponse(f, filename=f.name)


@router.post('/import-pack')
async def import_pack(file: UploadFile = File(...)):
    config.DIST.mkdir(parents=True, exist_ok=True)
    tmp = config.DIST / f'.import-{int(time.time())}.zip'
    with open(tmp, 'wb') as w:
        w.write(await file.read())
    job_service.start_job('导入资源包',
                          lambda logcb: pack_service.import_pack(tmp, logcb))
    return {'ok': True}


@router.post('/upload')
async def upload(pid: str = Form(...), files: list[UploadFile] = File(...)):
    p = repository.get_project(pid)
    if not p or p['type'] != 'upload':
        raise HTTPException(status_code=400, detail='目标必须是 upload 类型项目')
    udir = config.UPLOADS / pid
    saved = []
    for f in files:
        name = Path(f.filename or '').name
        if name.lower().endswith('.md'):
            dest = udir / name
        else:
            dest = udir / '_files' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(await f.read())
        saved.append(name)
    job_service.start_job(f'sync-{pid}', lambda logcb: sync_service.sync_all(pid, logcb))
    return {'ok': True, 'saved': saved}


@router.get('/projects')
def list_projects():
    return repository.list_projects()


@router.post('/projects')
def save_project(spec: ProjectSpec):
    pid = spec.id.strip().lower()
    if not PID_RE.match(pid):
        raise HTTPException(status_code=400, detail='id 需为小写字母/数字/连字符，2~40 位')
    if spec.type not in ('github', 'upload'):
        raise HTTPException(status_code=400, detail='type 仅支持 github/upload')
    entry = {'id': pid, 'name': spec.name.strip() or pid, 'type': spec.type,
             'repo': '', 'root': '.', 'books': {}}
    if spec.type == 'github':
        repo = spec.repo.strip()
        if not REPO_RE.match(repo):
            raise HTTPException(status_code=400, detail='repo 需为 owner/name 格式')
        entry['repo'] = repo
        entry['root'] = spec.root.strip() or '.'
        entry['books'] = {str(k): str(v) for k, v in spec.books.items() if str(k).strip()}
    else:
        (config.UPLOADS / pid).mkdir(parents=True, exist_ok=True)
    existing = [p for p in repository.list_projects() if p['id'] != pid]
    repository.upsert_project(entry, sort=len(existing))
    job_service.start_job(f'sync-{pid}', lambda logcb: sync_service.sync_all(pid, logcb))
    return {'ok': True}


@router.delete('/projects/{pid}')
def delete_project(pid: str, purge: bool = True):
    if not repository.get_project(pid):
        raise HTTPException(status_code=404, detail='project not found')
    repository.delete_project(pid)
    job_service.start_job(f'delete-{pid}', lambda logcb: _purge(pid, purge, logcb))
    return {'ok': True}


def _purge(pid, purge, logcb):
    import shutil
    if purge:
        for d in (config.REPOS / pid, config.UPLOADS / pid):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)
        for f in config.PDF_DIR.glob(f'{pid}__*.pdf'):
            f.unlink(missing_ok=True)
        logcb(f'purged {pid} data')


@router.get('/note')
def note_get(pid: str = 'my-notes', name: str = ''):
    name = Path(name).name
    p = config.UPLOADS / pid / name
    if not p.exists():
        raise HTTPException(status_code=404, detail='note not found')
    return {'name': name, 'content': p.read_text(encoding='utf-8', errors='ignore')}


@router.post('/note')
def note_save(spec: NoteSpec):
    name = Path(spec.name).name or 'untitled.md'
    if not name.endswith('.md'):
        name += '.md'
    d = config.UPLOADS / spec.pid
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(spec.content, encoding='utf-8')
    job_service.start_job(f'sync-{spec.pid}',
                          lambda logcb: sync_service.sync_all(spec.pid, logcb))
    return {'ok': True, 'name': name}
