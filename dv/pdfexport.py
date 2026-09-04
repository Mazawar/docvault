"""Per-book PDF export via weasyprint."""
import html as H
from pathlib import Path
from . import util, sync as syncmod

DIST = syncmod.DATA / 'dist' / 'pdf'

PDF_CSS = '''
@page { size: A4; margin: 16mm 13mm 18mm 13mm;
  @bottom-center { content: counter(page); font-size: 8pt; color: #999; font-family: "Noto Sans CJK SC"; } }
@page cover { @bottom-center { content: none; } }
body { font-family: "Noto Sans CJK SC", sans-serif; font-size: 10.5pt; line-height: 1.75; color: #24292f; }
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
code { font-family: "Noto Sans Mono CJK SC", monospace; font-size: 8.5pt; }
:not(pre) > code { background: #f0f1f3; border-radius: 3pt; padding: 1pt 3pt; color: #c7254e; }
.codehilite { background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 6pt; padding: 8pt; }
a { color: #2b6cb0; text-decoration: none; }
del { color: #999; }
'''


def export_book(pid, book_id, log=print):
    from weasyprint import HTML
    man = syncmod.load_manifests()
    man = next(m for m in man if m['id'] == pid)
    book = next(b for b in man['books'] if b['id'] == book_id)
    broot = Path(book['root'])
    log(f"[{pid}/{book_id}] {len(book['articles'])} articles")

    toc, secs, assets = [], [], set()
    for i, a in enumerate(book['articles'], 1):
        tx = (broot / (a['slug'] + '.md')).read_text(encoding='utf-8', errors='ignore')
        body = util.md_to_html(tx)
        body = util.alerts(body)
        assets |= set(util.collect_urls(tx))
        for url in util.collect_urls(tx):
            f = syncmod.ASSETS / util.asset_name(url)
            if f.exists():
                body = body.replace(url, f'file://{f}')
                body = body.replace(url.replace('&', '&amp;'), f'file://{f}')
        body = util.localize_local(body, (broot / a['slug']).parent, syncmod.ASSETS,
                                   prefix='file://' + str(syncmod.ASSETS) + '/')
        secs.append(f'<section id="art-{i}">{body}</section>')
        toc.append(f'<li><a href="#art-{i}">{H.escape(a["title"])}</a></li>')
        log(f"  {i}/{len(book['articles'])} {a['title'][:40]}")

    html = ('<!DOCTYPE html><html><head><meta charset="utf-8"><style>' + PDF_CSS +
            '</style></head><body><div class="cover"><h1>' + H.escape(book['title']) +
            '</h1><p>' + H.escape(man['name']) + ' · DocVault 离线导出 · ' +
            man['updated'] + '</p></div><nav class="toc"><h1>目录</h1><ol>' +
            ''.join(toc) + '</ol></nav>' + ''.join(secs) + '</body></html>')

    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / f"{pid}__{book_id}.pdf"
    HTML(string=html, base_url=str(syncmod.DATA)).write_pdf(str(out))
    log(f"PDF -> {out} ({out.stat().st_size/1048576:.1f} MB)")
    return out
