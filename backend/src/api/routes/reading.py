"""阅读接口（控制器层）：书架 / 书目录 / 文章 / 全文搜索。"""
from fastapi import APIRouter, HTTPException, Query
from ...models import repository
from ...services import content_service, note_service

router = APIRouter(prefix='/api', tags=['reading'])


@router.get('/index')
def index():
    return repository.index_payload()


@router.get('/book/{pid}/{bid}')
def book(pid: str, bid: str):
    payload = content_service.book_payload(pid, bid)
    if not payload:
        raise HTTPException(status_code=404, detail='book not found')
    return payload


@router.get('/article/{pid}/{bid}/{slug:path}')
def article(pid: str, bid: str, slug: str):
    payload = content_service.render_article(pid, bid, slug)
    if not payload:
        raise HTTPException(status_code=404, detail='article not found')
    return payload


@router.get('/search')
def search(q: str = Query(''), pid: str = Query(''), limit: int = Query(60)):
    items = repository.search(q, pid=pid, limit=limit)
    for r in items:
        r['kind'] = 'article'
    if not pid:
        items += note_service.search(q, limit=max(5, limit // 6))
    return {'items': items}
