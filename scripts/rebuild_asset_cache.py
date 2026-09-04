#!/usr/bin/env python3
"""从 v1 缓存(sha1 全名)重建 v2 缓存(sha256[:32])，再清掉残留 sha1 文件。"""
import hashlib, os, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'backend'))
from src.models import database  # noqa: E402

OLD = Path('/root/dv2/assets')
NEW = Path('/root/dv3/assets')
NEW.mkdir(exist_ok=True)

def v1_name(url):
    return hashlib.sha1(url.encode()).hexdigest()

def v2_name(url):
    return hashlib.sha256(url.encode()).hexdigest()[:32]

# 1. 从文章正文收集全部图片 URL
urls = set()
with database.connect() as c:
    for (body,) in c.execute('SELECT body FROM articles'):
        import re
        urls.update(m.group(1) for m in re.finditer(
            r'!\[[^\]]*\]\(\s*<?([^)\s>]+)>?', body))
        urls.update(m.group(1) for m in re.finditer(
            r'<img[^>]*src="(https?://[^"]+)"', body))

restored = have = no_src = 0
import urllib.parse
for u in sorted(urls):
    # dv2 文件名 = sha1(url) + 扩展名
    matches = list(OLD.glob(hashlib.sha1(u.encode()).hexdigest() + '.*'))
    if not matches:
        no_src += 1
        continue
    # v2 规则的扩展名
    ext = os.path.splitext(urllib.parse.urlparse(u).path)[1].lower()
    if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'):
        ext = '.svg' if 'svg' in u.lower() else '.png'
    dst = NEW / (v2_name(u) + ext)
    if dst.exists():
        have += 1
        continue
    shutil.copy2(matches[0], dst)
    restored += 1

print(f'URL total: {len(urls)}, restored: {restored}, already: {have}, no_src: {no_src}')

# 2. 删除 dv3 里 40 位十六进制命名的残留（sha1 时代文件）
removed = 0
for f in NEW.iterdir():
    stem = f.stem
    if len(stem) == 40 and all(ch in '0123456789abcdef' for ch in stem):
        try:
            f.unlink()
            removed += 1
        except OSError:
            pass
print(f'stale sha1 removed: {removed}')
print(f'now: {len(list(NEW.iterdir()))} files, {sum(f.stat().st_size for f in NEW.iterdir())/1048576:.0f} MB')
