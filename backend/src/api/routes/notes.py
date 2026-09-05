"""笔记接口（控制器层）：笔记本/笔记 CRUD + 渲染。数据事实源在文件系统。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ...services import note_service

router = APIRouter(prefix='/api/notes', tags=['notes'])


class NoteSpec(BaseModel):
    folder: str = note_service.DEFAULT_FOLDER
    name: str
    content: str = ''


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
    return _load(note_service.write, spec.folder, spec.name, spec.content)


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
