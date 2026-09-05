"""FastAPI 应用组装：路由挂载 + 图片/附件托管 + 前端静态托管。"""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from ..core import config
from ..models import database
from .routes import admin, notes, reading

_FALLBACK_PAGE = ('<!DOCTYPE html><meta charset="utf-8"><title>DocVault</title>'
                  '<body style="font-family:sans-serif;padding:40px">'
                  '<h2>前端未构建</h2><p>请先在 frontend/ 目录执行 <code>npm install && npm run build</code>，'
                  '或使用 CLI：<code>python -m src.main sync all</code> 同步数据。</p>')


def create_app() -> FastAPI:
    config.ensure_dirs()
    database.init()
    app = FastAPI(title='DocVault', docs_url=None, redoc_url=None)
    app.include_router(reading.router)
    app.include_router(notes.router)
    app.include_router(admin.router)

    @app.get('/api/status')
    def status():
        return {'ok': True, 'app': 'DocVault'}

    config.ASSETS.mkdir(parents=True, exist_ok=True)
    app.mount('/a', StaticFiles(directory=config.ASSETS), name='assets')
    config.UPLOADS.mkdir(parents=True, exist_ok=True)

    @app.get('/files/{pid}/{name}')
    def files(pid: str, name: str):
        f = config.UPLOADS / pid / '_files' / Path(name).name
        if not f.exists():
            raise HTTPException(status_code=404, detail='file not found')
        return FileResponse(f)

    front = config.frontend_dist()
    if front:
        app.mount('/', StaticFiles(directory=front, html=True), name='spa')
    else:
        @app.get('/', response_class=HTMLResponse)
        def no_front():
            return _FALLBACK_PAGE
    return app


app = create_app()
