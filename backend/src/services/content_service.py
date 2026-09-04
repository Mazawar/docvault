"""内容渲染服务：文章 md → 前端可展示 HTML（API 模式与离线导出共用管线）。"""
import html as H
import os
import re
from pathlib import Path
from ..core import config, util
from ..models import repository

A_PREFIX = '/a/'


def article_url(pid, bid, slug):
    """前端 hash 路由地址（离线静态模式同样有效）。"""
    return f"#/read/{pid}/{bid}/{slug}"


def _urlmap(pid, bid, articles):
    m = {}
    for a in articles:
        m[a['slug'] + '.md'] = article_url(pid, bid, a['slug'])
        if a['slug'].lower().endswith('/readme'):
            m[a['slug'][:-6] + '.md'] = article_url(pid, bid, a['slug'])
    return m


class _Linker:
    """把正文里的相对 .md 链接改写为前端路由地址。"""

    def __init__(self, root: Path, urlmap: dict):
        self.root = Path(root)
        self.urlmap = urlmap

    def __call__(self, body, cur_dir: Path):
        pat = re.compile(r'href="([^"#?]+\.md)(#[^"]*)?"')

        def rw(m):
            href, frag = m.group(1), m.group(2) or ''
            if href.startswith(('http://', 'https://', '/')):
                return m.group(0)
            try:
                target = os.path.normpath(Path(cur_dir) / href)
                rel = str(Path(target).relative_to(self.root)).replace(os.sep, '/')
                if not rel.endswith('.md'):
                    rel += '.md'
                if rel in self.urlmap:
                    return f'href="{self.urlmap[rel]}{frag}"'
            except Exception:
                pass
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


def render_article(pid, bid, slug):
    """-> 前端 article payload；文章不存在返回 None。"""
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

    body = util.md_to_html(art['body'])
    body = re.sub(r'<h1[^>]*>.*?</h1>', '', body, count=1, flags=re.S)
    body = util.alerts(body)
    body = _rewrite_remote(body)
    broot = Path(book['root'])
    body = util.localize_local(body, (broot / slug).parent, config.ASSETS)
    body = _Linker(broot, _urlmap(pid, bid, articles))(body, (broot / slug).parent)

    proj = repository.get_project(pid)
    return {
        'pid': pid, 'bid': bid, 'slug': slug,
        'title': art['title'],
        'html': body,
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
        'articles': repository.list_articles(pid, bid),
    }


def search_text(html_body):
    return util.strip_tags(html_body, 1200)
