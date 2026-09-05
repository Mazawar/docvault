"""资源包服务：程序可导回的完整数据包。

与静态站 zip（export_zip）的区别：
- 静态站 zip：只读产物，任何静态服务器可跑，无程序逻辑
- 资源包（export_pack）：导入 DocVault 程序即为完整实例——
  含 SQLite 库（项目/书/文章）、图片缓存、上传、PDF、前端产物；
  离线内网机器：clone 代码 + 导入资源包 + serve，全程无网络无 npm。

导入语义：按项目合并（同 id 覆盖、其余保留），图片/上传/PDF 跳过已有。
"""
import json
import os
import shutil
import sqlite3
import time
import zipfile
from pathlib import Path

from ..core import config
from ..models import repository

PACK_GLOB = 'DocVault-pack-*.zip'


def _snapshot_db(work: Path) -> Path:
    """SQLite backup API 取一致性快照（服务运行中导出也安全）。"""
    dst = work / 'docvault.db'
    src = sqlite3.connect(config.DB)
    dst_c = sqlite3.connect(dst)
    with dst_c:
        src.backup(dst_c)
    dst_c.close()
    src.close()
    return dst


def _add_dir(z: zipfile.ZipFile, root: Path, arc_root: str) -> int:
    if not root.exists():
        return 0
    n = 0
    for f in root.rglob('*'):
        if f.is_file():
            z.write(f, str(Path(arc_root) / f.relative_to(root)))
            n += 1
    return n


def export_pack(with_repos=False, logcb=print) -> Path:
    stamp = time.strftime('%Y%m%d')
    config.DIST.mkdir(parents=True, exist_ok=True)
    out = config.DIST / f'DocVault-pack-{stamp}.zip'
    tmp_zip = config.DIST / f'.{out.name}.tmp'
    work = config.DIST / '.packtmp'
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    logcb('快照数据库...')
    db = _snapshot_db(work)
    meta = {
        'format': 1,
        'app': 'DocVault',
        'exported': time.strftime('%Y-%m-%d %H:%M:%S'),
        'projects': [p['id'] for p in repository.list_projects()],
        'with_repos': bool(with_repos),
    }
    (work / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')

    with zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_STORED) as z:
        z.write(db, 'docvault.db')
        z.write(work / 'meta.json', 'meta.json')
        logcb('图片缓存...')
        logcb(f"assets: {_add_dir(z, config.ASSETS, 'assets')}")
        _add_dir(z, config.UPLOADS, 'uploads')
        _add_dir(z, config.PDF_DIR, 'pdf')
        front = config.frontend_dist()
        if front:
            logcb('前端产物（离线机免 npm）...')
            _add_dir(z, front, 'frontend-dist')
        if with_repos:
            logcb('源仓库（供后续联网同步）...')
            _add_dir(z, config.REPOS, 'repos')

    # 同名覆盖失败（旧包正被下载/杀软扫描）→ 落盘为带时分秒的新包，绝不让导出失败
    for i in range(3):
        try:
            os.replace(tmp_zip, out)
            break
        except PermissionError:
            if i == 2:
                out = config.DIST / f'DocVault-pack-{stamp}-{time.strftime("%H%M%S")}.zip'
                os.replace(tmp_zip, out)
                break
            time.sleep(2)
    shutil.rmtree(work, ignore_errors=True)
    # 资源包永远只保留最新一个
    packs = sorted(config.DIST.glob(PACK_GLOB))
    for old in packs[:-1]:
        try:
            old.unlink()
        except OSError:
            pass
    logcb(f'{out.name} ({out.stat().st_size / 1048576:.0f} MB)')
    return out


def latest_pack() -> Path | None:
    packs = sorted(config.DIST.glob(PACK_GLOB))
    return packs[-1] if packs else None


def _copy_tree(src: Path, dst: Path) -> int:
    if not src.exists():
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in src.rglob('*'):
        if f.is_file():
            d = dst / f.relative_to(src)
            d.parent.mkdir(parents=True, exist_ok=True)
            if not d.exists():
                shutil.copy2(f, d)
                n += 1
    return n


def import_pack(zip_path, logcb=print) -> dict:
    zip_path = Path(zip_path)
    work = config.DIST / '.importtmp'
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(work)

    meta = {}
    mf = work / 'meta.json'
    if mf.exists():
        meta = json.loads(mf.read_text(encoding='utf-8'))
    logcb(f"format={meta.get('format', '?')} 导出于 {meta.get('exported', '?')}")

    pdb = work / 'docvault.db'
    if not pdb.exists():
        shutil.rmtree(work, ignore_errors=True)
        raise RuntimeError('包内缺少 docvault.db——这不是资源包；'
                           '静态站 zip 请直接解压到静态服务器目录即可')

    con = sqlite3.connect(pdb)
    con.row_factory = sqlite3.Row
    projs = con.execute('SELECT * FROM projects ORDER BY sort, id').fetchall()
    for pr in projs:
        pid = pr['id']
        repository.delete_project(pid)
        repository.upsert_project({'id': pid, 'name': pr['name'], 'type': pr['type'],
                                   'repo': pr['repo'], 'root': pr['root'],
                                   'books': json.loads(pr['books_json'] or '{}')},
                                  sort=pr['sort'])
        books_ = []
        for b in con.execute('SELECT * FROM books WHERE pid=?', (pid,)).fetchall():
            arts = con.execute(
                'SELECT slug,title,body FROM articles WHERE pid=? AND bid=? ORDER BY ord',
                (pid, b['id'])).fetchall()
            books_.append({'id': b['id'], 'title': b['title'], 'root': b['root'],
                           'articles': [{'slug': a['slug'], 'title': a['title'],
                                         'body': a['body']} for a in arts]})
        if books_:
            repository.replace_books(pid, books_)
        repository.touch_project(pid, pr['updated'])
        logcb(f'[{pid}] {len(books_)} books / {sum(len(b["articles"]) for b in books_)} articles')

    a = _copy_tree(work / 'assets', config.ASSETS)
    logcb(f'assets +{a}')
    logcb(f"uploads +{_copy_tree(work / 'uploads', config.UPLOADS)}")
    logcb(f"pdf +{_copy_tree(work / 'pdf', config.PDF_DIR)}")
    fd = _copy_tree(work / 'frontend-dist', config.DATA / 'frontend-dist')
    if fd:
        logcb(f'frontend-dist +{fd}（离线机无需 npm build）')
    r = _copy_tree(work / 'repos', config.REPOS)
    if r:
        logcb(f'repos +{r}')
    con.close()
    shutil.rmtree(work, ignore_errors=True)
    # 管理台上传的临时 zip 用完即删（CLI 导入的用户文件不动）
    if zip_path.name.startswith('.import-'):
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass
    logcb('导入完成：serve 即为完整实例（搜索/管理/阅读记忆全可用）')
    return {'projects': [p['id'] for p in projs]}
