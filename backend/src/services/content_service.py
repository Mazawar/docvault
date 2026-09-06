"""内容渲染服务：文章 md → 前端可展示 HTML（API 模式与离线导出共用管线）。"""
import html as H
import os
import re
import urllib.parse
from pathlib import Path
from ..core import config, util
from ..models import repository

A_PREFIX = '/a/'


def article_url(pid, bid, slug):
    """前端 hash 路由地址（离线静态模式同样有效）。"""
    return f"#/read/{pid}/{bid}/{slug}"


def _pathmap(pid):
    """项目内所有书的文章：规范化文件路径 → 前端路由地址（链接解析共用）。

    键含 .md 与无扩展名两种形式；xx/readme 额外映射为 xx.md。"""
    m = {}
    for b in repository.list_books(pid):
        broot = Path(b['root'])
        for a in repository.list_articles(pid, b['id']):
            url = article_url(pid, b['id'], a['slug'])
            rels = {a['slug'] + '.md', a['slug']}
            if a['slug'].lower().endswith('/readme'):
                rels.add(a['slug'][:-7] + '.md')
            for rel in rels:
                m[str(os.path.normpath(broot / rel))] = url
    return m


def _link_url(root, href, cur_dir, pmap):
    """链接地址 → 前端路由；解析不到返回 None。

    相对路径按文章所在目录解析；/ 开头的站内绝对路径按站点根（书根及其
    上两级）解析——VitePress 等源站常写 /guide/xxx 形式，且可能跨书。"""
    rel_path = urllib.parse.unquote(href.split('#')[0]).lstrip('/')
    if not rel_path or rel_path == '/':
        return None
    bases = [Path(cur_dir)] if cur_dir is not None else []
    bases += [Path(root), Path(root).parent, Path(root).parent.parent]
    for base in bases:
        url = pmap.get(str(os.path.normpath(base / rel_path)))
        if url:
            return url
    return None


class _Linker:
    """把正文里的相对/站内绝对链接改写为前端路由地址。"""

    def __init__(self, root: Path, pmap: dict):
        self.root = Path(root)
        self.pmap = pmap

    def __call__(self, body, cur_dir: Path):
        pat = re.compile(r'href="([^"#?]+)(#[^"]*)?"')

        def rw(m):
            href, frag = m.group(1), m.group(2) or ''
            if href.startswith(('http://', 'https://', '//', '#')):
                return m.group(0)
            url = _link_url(self.root, href, cur_dir, self.pmap)
            if url:
                return f'href="{url}{frag}"'
            return m.group(0)
        return pat.sub(rw, body)


def _rewrite_remote(body):
    """远程图片 URL → 本地缓存地址（已缓存的才替换）。"""
    def rw_md(m):
        alt, url = m.group(1), m.group(2)
        if url.startswith(('http://', 'https://')) and (config.ASSETS / util.asset_name(url)).exists():
            url = A_PREFIX + util.asset_name(url)
        return f'![{alt}]({url})'

    def rw_html(m):
        url = m.group(1)
        if (config.ASSETS / util.asset_name(url)).exists():
            return m.group(0).replace(url, A_PREFIX + util.asset_name(url))
        return m.group(0)
    body = util.IMG_INLINE.sub(rw_md, body)
    return util.HTML_IMG.sub(rw_html, body)


_MD_LINK = re.compile(r'\]\(\s*([^)#\s]+)(#[^)\s]*)?\s*(?:"[^"]*")?\s*\)')


def _link_md(body, root, pmap, cur_dir):
    """Markdown 链接里的仓库内相对/站内绝对地址（含无扩展名、跨书）→ 前端路由地址。"""
    def rw(m):
        href, frag = m.group(1), m.group(2) or ''
        if href.startswith(('http://', 'https://', '//')):
            return m.group(0)
        url = _link_url(root, href, cur_dir, pmap)
        if url:
            return f']({url}{frag})'
        return m.group(0)
    return _MD_LINK.sub(rw, body)


def _md_for_client(body, broot, slug, pmap):
    """前端 markdown-it 渲染用的正文。

    与 HTML 管线（md_to_html，离线包用）分离：这里只做「文本级」清洗——
    VitePress 方言（标题锚点/容器/围栏行高亮）转成通用 Markdown，围栏内不动；
    空行补齐、markdown="1" 等仅 Python-Markdown 需要的适配一律不做。
    """
    text, _ = util.strip_fm(body)
    text = util.strip_heading_meta(text)
    text = util.vp_containers(text)
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if re.match(r'^#\s+\S', line):
            del lines[i]  # 首个 h1 与页头标题重复
        break
    text = '\n'.join(lines)
    cur_dir = (Path(broot) / slug).parent
    text = util.outside_fences(text, _rewrite_remote)
    text = util.outside_fences(
        text, lambda t: util.localize_local(t, cur_dir, config.ASSETS))
    text = util.outside_fences(
        text, lambda t: util.localize_md_images(t, cur_dir, config.ASSETS, root=broot))
    text = util.outside_fences(
        text, lambda t: _link_md(t, broot, pmap, cur_dir))
    return text


def render_article(pid, bid, slug):
    """-> 前端 article payload；文章不存在返回 None。

    html：Python-Markdown 预渲染（离线静态包与搜索摘要用）。
    md：文本级清洗后的 Markdown（应用内由前端 markdown-it 渲染）。
    """
    art = repository.get_article(pid, bid, slug)
    if not art:
        return None
    book = repository.get_book(pid, bid)
    if not book:
        return None
    articles = repository.list_articles(pid, bid)
    idx = next((i for i, a in enumerate(articles) if a['slug'] == slug), -1)
    prev = articles[idx - 1] if idx > 0 else None
    nxt = articles[idx + 1] if 0 <= idx < len(articles) - 1 else None

    broot = Path(book['root'])
    cur_dir = (broot / slug).parent
    pmap = _pathmap(pid)

    body = util.md_to_html(art['body'])
    body = re.sub(r'<h1[^>]*>.*?</h1>', '', body, count=1, flags=re.S)
    body = util.alerts(body)
    body = _rewrite_remote(body)
    body = util.localize_local(body, cur_dir, config.ASSETS)
    body = _Linker(broot, pmap)(body, cur_dir)

    proj = repository.get_project(pid)
    return {
        'pid': pid, 'bid': bid, 'slug': slug,
        'title': art['title'],
        'html': body,
        'md': _md_for_client(art['body'], broot, slug, pmap),
        'prev': {'slug': prev['slug'], 'title': prev['title']} if prev else None,
        'next': {'slug': nxt['slug'], 'title': nxt['title']} if nxt else None,
        'updated': proj['updated'] if proj else '',
        'source': f"https://github.com/{proj['repo']}" if proj and proj.get('repo') else '',
        'pname': proj['name'] if proj else pid,
        'btitle': book['title'],
    }


def book_payload(pid, bid):
    """-> 书目录 payload（文章列表按分组前缀信息交由前端聚合）。"""
    book = repository.get_book(pid, bid)
    if not book:
        return None
    proj = repository.get_project(pid)
    return {
        'pid': pid, 'bid': bid, 'title': book['title'], 'n': book['n'],
        'pname': proj['name'] if proj else pid,
        'updated': proj['updated'] if proj else '',
        'gt': ((proj or {}).get('group_titles') or {}).get(bid, {}),
        'articles': repository.list_articles(pid, bid),
    }


def search_text(html_body):
    return util.strip_tags(html_body, 1200)
