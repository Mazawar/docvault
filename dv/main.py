"""CLI: python3 -m dv.main {sync|build|pdf|export|serve}"""
import argparse, sys
from . import sync as syncmod, render, pdfexport


def main():
    ap = argparse.ArgumentParser(prog='dv')
    sub = ap.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('sync')
    s.add_argument('target', nargs='?', default='all')

    b = sub.add_parser('build')

    p = sub.add_parser('pdf')
    p.add_argument('pid')
    p.add_argument('book')

    e = sub.add_parser('export')

    v = sub.add_parser('serve')
    v.add_argument('--port', type=int, default=8787)

    a = ap.parse_args()
    if a.cmd == 'sync':
        pids = [p['id'] for p in syncmod.projects()] if a.target == 'all' else [a.target]
        for pid in pids:
            syncmod.sync_project(pid)
        render.build()
    elif a.cmd == 'build':
        render.build()
    elif a.cmd == 'pdf':
        pdfexport.export_book(a.pid, a.book)
    elif a.cmd == 'export':
        import time, zipfile
        from pathlib import Path
        out = syncmod.DATA / 'dist' / f'DocVault-offline-{time.strftime("%Y%m%d")}.zip'
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_STORED) as z:
            for root in (render.SITE, syncmod.DATA / 'dist' / 'pdf'):
                root = Path(root)
                if root.exists():
                    for f in root.rglob('*'):
                        if f.is_file():
                            z.write(f, f.relative_to(syncmod.DATA))
        print(out, f'{out.stat().st_size/1048576:.0f} MB')
    elif a.cmd == 'serve':
        import uvicorn
        uvicorn.run('dv.server:app', host='127.0.0.1', port=a.port, log_level='warning')


if __name__ == '__main__':
    main()
