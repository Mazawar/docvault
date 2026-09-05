"""管理接口（控制器层）：项目 CRUD / 同步 / 上传 / 笔记 / PDF / 离线包 / 任务。"""
import re
import time
from pathlib import Path
from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from ...core import config
from ...models import database, repository
from ...services import (export_service, job_service, note_service, pack_service,
                         pdf_service, sync_service)

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
    groupTitles: dict[str, dict[str, str]] = Field(default_factory=dict)


class SyncSpec(BaseModel):
    pid: str = ''


class PdfSpec(BaseModel):
    pid: str
    bid: str


class NotePdfSpec(BaseModel):
    folder: str = '我的笔记'
    name: str = ''


@router.get('/overview')
def overview():
    projects = []
    for p in repository.list_projects():
        books = repository.list_books(p['id'])
        projects.append({**p, 'books': [{'id': b['id'], 'title': b['title'], 'n': b['n']}
                                        for b in books]})
    z = export_service.latest_zip()
    pk = pack_service.latest_pack()
    return {'projects': projects,
            'pdfs': pdf_service.list_pdfs(),
            'zip': z.name if z else None,
            'zipSize': z.stat().st_size if z else 0,
            'pack': pk.name if pk else None,
            'packSize': pk.stat().st_size if pk else 0,
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


def _dir_size(p) -> int:
    if not Path(p).exists():
        return 0
    return sum(f.stat().st_size for f in Path(p).rglob('*') if f.is_file())


@router.get('/storage')
def storage():
    """缓存空间概览：各项目仓库占用 + 全局目录占用。"""
    def mb(p):
        return round(_dir_size(p) / 1048576, 1)
    items = []
    for p in repository.list_projects():
        items.append({
            'id': p['id'], 'name': p['name'], 'type': p['type'],
            'repos_mb': mb(config.REPOS / p['id']),
            'articles': sum(b['n'] for b in repository.list_books(p['id'])),
        })
    return {
        'projects': items,
        'assets': {'mb': mb(config.ASSETS),
                   'files': len(list(config.ASSETS.glob('*'))) if config.ASSETS.exists() else 0},
        'repos_mb': mb(config.REPOS),
        'db_mb': mb(config.DB),
        'notes_mb': mb(config.DATA / 'notes'),
        'uploads_mb': mb(config.UPLOADS),
        'dist_mb': mb(config.DIST),
    }


@router.post('/purge-repos')
def purge_repos(spec: SyncSpec):
    """清理某项目的仓库缓存（文章/图片保留，下次同步自动重新克隆）。"""
    if not repository.get_project(spec.pid):
        raise HTTPException(status_code=404, detail='项目不存在')
    def work(logcb):
        import shutil
        d = config.REPOS / spec.pid
        if d.exists():
            m = _dir_size(d) / 1048576
            shutil.rmtree(d, ignore_errors=True)
            logcb(f'已清理 {spec.pid} 仓库缓存 {m:.0f} MB（文章与图片保留，下次同步自动重新克隆）')
        else:
            logcb('该项目没有仓库缓存')
    job_service.start_job('清理仓库缓存', work)
    return {'ok': True}


@router.post('/purge-orphan-assets')
def purge_orphan_assets():
    """清理图床中未被任何文章/笔记引用的无效图片。"""
    def work(logcb):
        import re as _re
        from ...core import util as _util
        ref = set()
        with database.connect() as c:
            for (body,) in c.execute('SELECT body FROM articles'):
                ref |= {m.group(1) for m in _re.finditer(r'src="/a/([^"]+)"', body)}
                for u in _util.collect_urls(body):
                    ref.add(_util.asset_name(u))
        for folder, name, path in note_service.iter_notes():
            try:
                body = path.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            ref |= {m.group(1) for m in _re.finditer(r'src="/a/([^"]+)"', body)}
            for u in _util.collect_urls(body):
                ref.add(_util.asset_name(u))
        deleted, freed = 0, 0
        for f in config.ASSETS.iterdir():
            if f.name in ref or f.name.startswith('.') or not f.is_file():
                continue
            try:
                freed += f.stat().st_size
                f.unlink()
                deleted += 1
            except OSError:
                pass
        logcb(f'清理无效图片 {deleted} 个，释放 {freed / 1048576:.1f} MB（保留 {len(ref)} 个引用中）')
    job_service.start_job('清理无效图片', work)
    return {'ok': True}


@router.post('/export-pack')
def export_pack_route():
    job_service.start_job('生成资源包',
                          lambda logcb: pack_service.export_pack(False, logcb))
    return {'ok': True}


@router.post('/pdf-note')
def pdf_note(spec: NotePdfSpec):
    def work(logcb):
        if spec.name:
            pdf_service.export_note(spec.folder, spec.name, logcb)
        else:
            pdf_service.export_note_folder(spec.folder, logcb)
    job_service.start_job('导出笔记 PDF',
                          work)
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


@router.get('/projects')
def list_projects():
    return repository.list_projects()


@router.post('/projects')
def save_project(spec: ProjectSpec):
    pid = spec.id.strip().lower()
    if not PID_RE.match(pid):
        raise HTTPException(status_code=400, detail='id 需为小写字母/数字/连字符，2~40 位')
    if spec.type not in ('github', 'upload', 'notebook'):
        raise HTTPException(status_code=400, detail='type 仅支持 github/upload/notebook')
    entry = {'id': pid, 'name': spec.name.strip() or pid, 'type': spec.type,
             'repo': '', 'root': '.', 'books': {}}
    if spec.type == 'github':
        repo = spec.repo.strip()
        if not REPO_RE.match(repo):
            raise HTTPException(status_code=400, detail='repo 需为 owner/name 格式')
        entry['repo'] = repo
        entry['root'] = spec.root.strip() or '.'
        entry['books'] = {str(k): str(v) for k, v in spec.books.items() if str(k).strip()}
        entry['group_titles'] = {str(bid): {str(d): str(t) for d, t in m.items()}
                                 for bid, m in (spec.groupTitles or {}).items()}
    elif spec.type == 'notebook':
        repo = spec.repo.strip()
        if not repo:
            raise HTTPException(status_code=400, detail='请选择要导入的笔记本')
        entry['repo'] = repo
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
    running = [j for j in repository.jobs_recent(50)
               if j['status'] == 'running' and pid in j['name']]
    if running:
        raise HTTPException(status_code=409, detail='该项目有进行中的任务，请稍后再删除')
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
