"""笔记接口（控制器层）：笔记本/笔记 CRUD + 渲染。数据事实源在文件系统。"""
import time

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from ...core import config
from ...services import note_service

router = APIRouter(prefix='/api/notes', tags=['notes'])


class NoteSpec(BaseModel):
    folder: str = note_service.DEFAULT_FOLDER
    name: str
    content: str = ''
    tags: list[str] | None = None


class RenameSpec(BaseModel):
    folder: str = note_service.DEFAULT_FOLDER
    old: str
    new: str


class FolderSpec(BaseModel):
    name: str


def _load(fn, *a):
    try:
        return fn(*a)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='笔记不存在')
    except (ValueError, FileExistsError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get('/index')
def index():
    return {'folders': note_service.list_index()}


@router.get('/render/{folder}/{name}')
def render(folder: str, name: str):
    return _load(note_service.render_payload, folder, name)


@router.post('/render-preview')
def render_preview(spec: NoteSpec):
    return {'html': note_service.render_html(spec.content)}


@router.get('/content/{folder}/{name}')
def content(folder: str, name: str):
    return _load(note_service.read, folder, name)


@router.post('/save')
def save(spec: NoteSpec):
    return _load(note_service.write, spec.folder, spec.name, spec.content, spec.tags)


@router.get('/search')
def search(q: str = '', limit: int = 30):
    return note_service.search(q, limit)


@router.get('/backlinks/{folder}/{name}')
def backlinks(folder: str, name: str):
    return note_service.backlinks(folder, name)


@router.post('/daily')
def daily():
    return note_service.daily()


@router.post('/image')
async def upload_image(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail='图片超过 15MB')
    ext = '.png' if file.content_type in (None, 'application/octet-stream') else '.' + file.content_type.split('/')[-1].split('+')[0]
    if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'):
        ext = '.png'
    url = note_service.save_image(data, ext)
    return {'url': url, 'name': url.split('/')[-1]}


@router.post('/attachment')
async def upload_attachment(file: UploadFile = File(...)):
    name = file.filename.replace(' ', '_')
    d = config.UPLOADS / 'my-notes' / '_files'
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_bytes(await file.read())
    return {'url': f'/files/my-notes/{name}', 'name': name}


@router.post('/create')
def create(spec: NoteSpec):
    return _load(note_service.create, spec.folder, spec.name)


@router.post('/delete')
def delete(spec: NoteSpec):
    return _load(note_service.delete, spec.folder, spec.name) or {'ok': True}


@router.post('/rename')
def rename(spec: RenameSpec):
    return _load(note_service.rename, spec.folder, spec.old, spec.new)


@router.post('/folder')
def add_folder(spec: FolderSpec):
    note_service._folder(spec.name)
    return {'ok': True}


@router.delete('/folder/{name}')
def del_folder(name: str):
    note_service.delete_folder(name)
    return {'ok': True}
