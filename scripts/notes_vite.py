"""VitePress 联动（P4）：把 data/notes 作为 srcDir 一键 dev/build。

- 首次运行自动生成 DATA/vitepress/.vitepress/config.mts（侧栏按笔记本结构生成）
- notes-vite dev  : npx vitepress dev（热更写作）
- notes-vite build: npx vitepress build（产物 data/vitepress/.vitepress/dist 或 vitepress/dist）
- 需要 Node.js 18+；首次 npx 会自动安装 vitepress
"""
import json
import shutil
import subprocess
import sys


def _vitepress_dir():
    from src.core import config
    return config.DATA / 'vitepress'


def _ensure_scaffold():
    from src.core import config
    from src.services import note_service
    vp = _vitepress_dir()
    (vp / '.vitepress').mkdir(parents=True, exist_ok=True)
    if not (vp / 'package.json').exists():
        (vp / 'package.json').write_text(
            json.dumps({'name': 'docvault-notes', 'private': True, 'type': 'module'},
                       ensure_ascii=False, indent=2), encoding='utf-8')
    folders = [
        {'text': f['folder'],
         'items': [{'text': n['title'], 'link': '/' + f['folder'] + '/' + n['name']}
                   for n in f['notes']]}
        for f in note_service.list_index()]
    cfg = ("import { defineConfig } from 'vitepress'\n\n"
           "export default defineConfig({\n"
           "  lang: 'zh-CN',\n"
           "  title: '我的笔记',\n"
           "  description: 'DocVault 笔记（VitePress 工作区）',\n"
           "  srcDir: 'notes',\n"
           "  themeConfig: {\n"
           "    sidebar: " + json.dumps(folders, ensure_ascii=False, indent=2) + ",\n"
           "  },\n"
           "})\n")
    (vp / '.vitepress' / 'config.mts').write_text(cfg, encoding='utf-8')
    # 同步笔记副本进工程内（模块解析需要；数据事实源仍在 DATA/notes）
    notes_src = config.DATA / 'notes'
    notes_dst = vp / 'notes'
    shutil.rmtree(notes_dst, ignore_errors=True)
    if notes_src.exists():
        shutil.copytree(notes_src, notes_dst, ignore=shutil.ignore_patterns('..*'))
    if not (vp / 'node_modules' / 'vitepress').exists():
        print('首次使用：安装 vitepress（约 1-2 分钟）...', flush=True)
        r = subprocess.run(['npm', 'install', 'vitepress', '--no-audit', '--no-fund'],
                           cwd=str(vp))
        if r.returncode != 0:
            print('vitepress 安装失败：请检查 Node.js/npm 环境。', file=sys.stderr)
            sys.exit(1)
    return vp


def run(mode='dev'):
    vp = _ensure_scaffold()
    print(f'VitePress 工作区: {vp}', flush=True)
    try:
        if mode == 'dev':
            subprocess.run(['npx', 'vitepress', 'dev', str(vp)], cwd=str(vp))
        else:
            subprocess.run(['npx', 'vitepress', 'build', str(vp)], cwd=str(vp))
            out = vp / '.vitepress' / 'dist'
            print(f'build -> {out}')
    except FileNotFoundError:
        print('需要 Node.js 环境（npx）。请先安装 Node.js 18+。', file=sys.stderr)
        sys.exit(1)
