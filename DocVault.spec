# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec：DocVault 单文件 exe（前端产物 + FastAPI + pywebview）。"""
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = os.path.dirname(os.path.abspath(SPEC))

datas = [(os.path.join(ROOT, 'frontend', 'dist'), 'frontend/dist')]
binaries = []
hiddenimports = [
    # markdown 扩展按名字动态导入，必须显式声明
    'markdown.extensions.extra',
    'markdown.extensions.sane_lists',
    'markdown.extensions.toc',
    'markdown.extensions.codehilite',
    'markdown.extensions.admonition',
    'markdown.extensions.md_in_html',
    # uvicorn 动态选择 loop/protocol
    'uvicorn.logging',
    'uvicorn.loops.asyncio',
    'uvicorn.lifespan.on',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets.websockets_impl',
]
for pkg in ('webview', 'clr_loader', 'pythonnet'):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass  # webview 不可用时 exe 自动回退浏览器模式
for sub in ('pygments.lexers', 'pygments.formatters', 'pygments.styles'):
    hiddenimports += collect_submodules(sub)

a = Analysis(
    [os.path.join(ROOT, 'backend', 'run_app.py')],
    pathex=[os.path.join(ROOT, 'backend')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DocVault',
    console=False,
    disable_windowed_traceback=False,
    upx=False,
    icon=None,
)
