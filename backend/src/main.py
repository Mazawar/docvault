"""CLI 入口：python -m src.main {serve|app|sync|build|pdf|export|import}"""
import argparse
from .core import config
from .models import database
from .services import export_service, pack_service, pdf_service, sync_service


def main():
    ap = argparse.ArgumentParser(prog='dv')
    sub = ap.add_subparsers(dest='cmd', required=True)

    v = sub.add_parser('serve', help='启动 Web 服务（浏览器访问）')
    v.add_argument('--host', default='127.0.0.1')
    v.add_argument('--port', type=int, default=config.READ_PORT)

    a = sub.add_parser('app', help='桌面窗口（pywebview，回退浏览器）')
    a.add_argument('--browser', action='store_true', help='跳过 webview 直接开浏览器')
    a.add_argument('--port', type=int, default=0)

    s = sub.add_parser('sync', help='同步项目（默认 all）')
    s.add_argument('target', nargs='?', default='all')

    b = sub.add_parser('build', help='生成离线静态站 site/')
    p = sub.add_parser('pdf', help='导出某本书 PDF')
    p.add_argument('pid')
    p.add_argument('bid')
    e = sub.add_parser('export', help='打离线包 zip')
    pk = sub.add_parser('export-pack', help='打资源包（可导回程序）')
    pk.add_argument('--with-repos', action='store_true', help='附带源仓库（导入后可联网更新）')
    ipk = sub.add_parser('import-pack', help='导入资源包')
    ipk.add_argument('pack')
    pn = sub.add_parser('pdf-note', help='导出笔记 PDF（name 省略则整本笔记本）')
    pn.add_argument('folder')
    pn.add_argument('name', nargs='?')
    vt = sub.add_parser('notes-vite', help='VitePress 联动（dev/build）')
    vt.add_argument('mode', nargs='?', default='dev', choices=['dev', 'build'])
    i = sub.add_parser('import', help='从 projects.json 重新导入项目配置')

    a2 = ap.parse_args()
    database.init()
    if a2.cmd == 'serve':
        import uvicorn
        from .api.app import app
        uvicorn.run(app, host=a2.host, port=a2.port, log_level='warning')
    elif a2.cmd == 'app':
        from .desktop import run
        run(browser=a2.browser, port=a2.port)
    elif a2.cmd == 'sync':
        sync_service.sync_all(None if a2.target == 'all' else a2.target)
    elif a2.cmd == 'build':
        export_service.build_site()
    elif a2.cmd == 'pdf':
        pdf_service.export_book(a2.pid, a2.bid)
    elif a2.cmd == 'export':
        export_service.export_zip()
    elif a2.cmd == 'export-pack':
        pack_service.export_pack(with_repos=a2.with_repos)
    elif a2.cmd == 'import-pack':
        pack_service.import_pack(a2.pack)
    elif a2.cmd == 'pdf-note':
        from .services import note_service
        if a2.name:
            pdf_service.export_note(a2.folder, a2.name)
        else:
            pdf_service.export_note_folder(a2.folder)
    elif a2.cmd == 'notes-vite':
        import sys as _sys
        from pathlib import Path as _P
        _sys.path.insert(0, str(_P(__file__).resolve().parents[2]))
        from scripts.notes_vite import run
        run(a2.mode)
    elif a2.cmd == 'import':
        n = sync_service.import_projects_json()
        print(f'imported {n} projects')


if __name__ == '__main__':
    main()
