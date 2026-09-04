"""PDF 导出服务：weasyprint 引擎（Linux 服务器或已装 GTK 运行库的环境）。

Windows 下 weasyprint 需要 GTK 运行库；缺失时导出任务返回明确的安装提示，
不做任何浏览器注入或外部进程调用。
"""
import html as H
from pathlib import Path
from ..core import config, util
from ..models import repository

PDF_CSS = '''
@page { size: A4; margin: 16mm 13mm 18mm 13mm;
  @bottom-center { content: counter(page); font-size: 8pt; color: #999; font-family: "Noto Sans CJK SC"; } }
@page cover { @bottom-center { content: none; } }
body { font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif; font-size: 10.5pt; line-height: 1.75; color: #24292f; }
.cover { page: cover; page-break-after: always; text-align: center; padding-top: 90mm; }
.cover h1 { font-size: 34pt; border: none; color: #1f2328; }
.cover p { color: #777; font-size: 12pt; margin-top: 12mm; }
nav.toc { page-break-after: always; }
nav.toc h1 { page-break-before: avoid; font-size: 20pt; border: none; margin-bottom: 14pt; }
nav.toc ol { list-style: none; padding: 0; }
nav.toc li { margin: 4pt 0; font-size: 10pt; border-bottom: 1px dotted #ddd; overflow: hidden; }
nav.toc a { color: #24292f; text-decoration: none; }
nav.toc a::after { content: target-counter(attr(href), page); float: right; color: #3b82f6; font-weight: bold; }
h1 { page-break-before: always; font-size: 18pt; color: #111; border-bottom: 2.5px solid #3b82f6; padding-bottom: 6pt; }
h2 { font-size: 14pt; border-left: 5px solid #3b82f6; padding-left: 8pt; margin-top: 1.5em; }
img { max-width: 100%; display: block; margin: 8pt auto; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; margin: 8pt 0; }
th, td { border: 1px solid #d0d7de; padding: 3pt 6pt; } th { background: #f6f8fa; }
blockquote { border-left: 4px solid #fbbf24; background: #fffbeb; margin: 8pt 0; padding: 6pt 10pt; color: #555; }
.vp-alert { margin: 8pt 0; padding: 6pt 10pt; border: 1px solid #e1e4e8; border-left: 3pt solid #3b82f6;
  border-radius: 4pt; background: #f6f8fa; color: #444; font-size: 9.5pt; }
.vp-alert.tip { border-left-color: #3eaf7c; } .vp-alert.warning { border-left-color: #e0a800; }
.vp-alert.danger { border-left-color: #e53e3e; } .vp-alert.important { border-left-color: #8250df; }
.vp-alert .vp-alert-title { font-weight: bold; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; }
code { font-family: Consolas, "Noto Sans Mono CJK SC", monospace; font-size: 8.5pt; }
:not(pre) > code { background: #f0f1f3; border-radius: 3pt; padding: 1pt 3pt; color: #c7254e; }
.codehilite { background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 6pt; padding: 8pt; }
a { color: #2b6cb0; text-decoration: none; }
del { color: #999; }
'''


def build_html(pid, bid):
    """整书拼成一页 HTML（封面 + 目录 + 章节），图片走 file:// 绝对路径。"""
    book = repository.get_book(pid, bid)
    if not book:
        raise KeyError(pid, bid)
    proj = repository.get_project(pid)
    articles = repository.list_articles(pid, bid)
    broot = Path(book['root'])

    toc, secs = [], []
    for i, a in enumerate(articles, 1):
        art = repository.get_article(pid, bid, a['slug'])
        body = util.md_to_html(art['body'])
        body = util.alerts(body)
        for url in util.collect_urls(art['body']):
            f = config.ASSETS / util.asset_name(url)
            if f.exists():
                uri = f.as_uri()
                body = body.replace(url, uri)
                body = body.replace(url.replace('&', '&amp;'), uri)
        body = util.localize_local(body, (broot / a['slug']).parent, config.ASSETS,
                                   prefix=config.ASSETS.as_uri() + '/')
        secs.append(f'<section id="art-{i}">{body}</section>')
        toc.append(f'<li><a href="#art-{i}">{H.escape(a["title"])}</a></li>')
    cover_sub = f"{proj['name']} · DocVault 导出 · {proj['updated']}" if proj else 'DocVault'
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"><style>' + PDF_CSS +
            '</style></head><body><div class="cover"><h1>' + H.escape(book['title']) +
            '</h1><p>' + H.escape(cover_sub) + '</p></div><nav class="toc"><h1>目录</h1><ol>' +
            ''.join(toc) + '</ol></nav>' + ''.join(secs) + '</body></html>')


def export_book(pid, bid, logcb=print):
    try:
        from weasyprint import HTML
    except Exception as e:
        raise RuntimeError(
            'PDF 引擎 weasyprint 不可用（Windows 需安装 GTK 运行库，'
            '或在内网 Linux 服务器上使用）。详情: ' + repr(e)[:200])
    html = build_html(pid, bid)
    n = len(repository.list_articles(pid, bid))
    logcb(f'[{pid}/{bid}] {n} articles')
    out = config.PDF_DIR / f'{pid}__{bid}.pdf'
    config.PDF_DIR.mkdir(parents=True, exist_ok=True)
    HTML(string=html, base_url=str(config.DATA)).write_pdf(str(out))
    logcb(f'-> {out.name} ({out.stat().st_size / 1048576:.1f} MB)')
    return out


def list_pdfs():
    config.PDF_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(p.name for p in config.PDF_DIR.glob('*.pdf'))
