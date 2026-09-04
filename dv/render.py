"""Render site/: VitePress-style theme, portal, articles, search JSON."""
import html as H
import json, os, re, shutil, time
from pathlib import Path
from . import util, sync as syncmod

SITE = syncmod.DATA / 'site'
A = '/a/'

VPC = '''
:root{--bg:#ffffff;--bg-alt:#f6f6f7;--bg-soft:#f6f6f7;--divider:rgba(60,60,67,.12);
--text-1:#213547;--text-2:rgba(60,60,67,.78);--text-3:rgba(60,60,67,.56);
--brand:#3451b2;--brand-hover:#5672cd;--brand-soft:rgba(100,108,255,.14);
--code-bg:#f6f8fa;--code-border:rgba(60,60,67,.12);--inline-code:#476582;--inline-code-bg:rgba(127,127,187,.12);
--nav-h:60px;--side-w:272px;--green:#3eaf7c;--yellow:#e0a800;--red:#e53e3e;--purple:#8250df}
html.dark{--bg:#1b1b1f;--bg-alt:#202127;--bg-soft:#202127;--divider:rgba(82,82,89,.36);
--text-1:rgba(235,235,245,.86);--text-2:rgba(235,235,245,.6);--text-3:rgba(235,235,245,.38);
--brand:#a8b1ff;--brand-hover:#9e9ce6;--brand-soft:rgba(159,169,255,.14);
--code-bg:#161618;--code-border:rgba(82,82,89,.36);--inline-code:#c9cdfb;--inline-code-bg:rgba(127,127,187,.22)}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text-1);font-size:16px;line-height:1.8;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue","PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif;
-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
a{color:var(--brand);text-decoration:none}a:hover{color:var(--brand-hover)}
::selection{background:var(--brand-soft)}
#progress{position:fixed;top:0;left:0;height:2px;width:0;background:linear-gradient(90deg,var(--brand),#41d1ff);z-index:99}
.nav{position:fixed;top:0;left:0;right:0;height:var(--nav-h);display:flex;align-items:center;gap:14px;
padding:0 22px;background:color-mix(in srgb,var(--bg) 82%,transparent);backdrop-filter:saturate(1.6) blur(10px);
border-bottom:1px solid var(--divider);z-index:80}
.logo{font-size:17px;font-weight:700;color:var(--text-1);white-space:nowrap}
.logo b{color:var(--brand)}
.nav select{max-width:230px;border:1px solid var(--divider);background:var(--bg);color:var(--text-1);
border-radius:8px;padding:5px 8px;font-size:13px;outline:none}
.nav .sp{flex:1}
.searchwrap{position:relative}
#q{width:200px;border:1px solid var(--divider);background:var(--bg-alt);color:var(--text-1);border-radius:8px;
padding:6px 12px;font-size:13px;outline:none;transition:border .2s}
#q:focus{border-color:var(--brand);background:var(--bg)}
#results{position:absolute;right:0;top:40px;width:380px;max-height:64vh;overflow:auto;display:none;
background:var(--bg);border:1px solid var(--divider);border-radius:12px;box-shadow:0 12px 32px rgba(0,0,0,.14)}
#results a{display:block;padding:9px 14px;color:var(--text-1);border-bottom:1px solid var(--divider);font-size:13px}
#results a:last-child{border-bottom:none}#results a:hover{background:var(--bg-soft)}
#results .t{font-weight:600}#results .s{font-size:12px;color:var(--text-3)}
.tbtn{border:1px solid var(--divider);background:var(--bg);color:var(--text-2);border-radius:8px;
width:34px;height:30px;cursor:pointer;font-size:14px}
.tbtn:hover{color:var(--brand);border-color:var(--brand)}
.adminlink{font-size:13px;color:var(--text-3)}.adminlink:hover{color:var(--brand)}
.layout{display:flex;padding-top:var(--nav-h)}
.sidebar{width:var(--side-w);flex:none;position:sticky;top:var(--nav-h);height:calc(100vh - var(--nav-h));
overflow-y:auto;padding:20px 14px 48px;border-right:1px solid var(--divider);scrollbar-width:thin}
.sidebar details{margin:0 0 4px}
.sidebar summary{list-style:none;cursor:pointer;font-size:13px;font-weight:600;color:var(--text-1);
padding:6px 10px;border-radius:8px;display:flex;align-items:center;gap:6px}
.sidebar summary::-webkit-details-marker{display:none}
.sidebar summary::before{content:"";width:0;height:0;border-left:5px solid var(--text-3);border-top:4px solid transparent;
border-bottom:4px solid transparent;transition:transform .15s}
.sidebar details[open] summary::before{transform:rotate(90deg)}
.sidebar a{display:block;position:relative;padding:5px 12px;margin:1px 0;border-radius:8px;font-size:13.5px;
color:var(--text-2);line-height:1.5}
.sidebar a:hover{color:var(--text-1);background:var(--bg-soft)}
.sidebar a.on{color:var(--brand);font-weight:600;background:var(--brand-soft)}
.sidebar a.read::after{content:"✓";position:absolute;right:8px;color:var(--green);font-size:12px;font-weight:700}
.main{flex:1;min-width:0}
.article{max-width:784px;margin:0 auto;padding:34px 40px 90px}
.crumb{font-size:13px;color:var(--text-3);margin-bottom:14px}
.crumb a{color:var(--text-3)}.crumb a:hover{color:var(--brand)}
h1.tt{font-size:32px;font-weight:700;line-height:1.35;margin:0 0 28px;color:var(--text-1)}
.article h2{font-size:24px;margin:44px 0 16px;padding-top:24px;border-top:1px solid var(--divider)}
.article h3{font-size:19px;margin:32px 0 12px}
.article p{margin:14px 0;color:var(--text-1)}
.article li{margin:6px 0}
.article img{max-width:100%;border-radius:10px;margin:12px auto;display:block;border:1px solid var(--divider)}
.article table{border-collapse:collapse;width:100%;font-size:13.5px;margin:16px 0;display:block;overflow-x:auto}
.article th,.article td{border:1px solid var(--divider);padding:7px 12px}
.article th{background:var(--bg-soft)}
.article blockquote{margin:18px 0;padding:2px 18px;border-left:3px solid var(--brand);color:var(--text-2)}
.vp-alert{margin:18px 0;padding:14px 18px;border:1px solid var(--divider);border-left:4px solid var(--brand);
border-radius:8px;background:var(--bg-soft);color:var(--text-2);font-size:14.5px}
.vp-alert p{margin:4px 0}
.vp-alert .vp-alert-title{font-weight:700;color:var(--text-1);font-size:14px}
.vp-alert.note{border-left-color:#3b82f6}.vp-alert.tip{border-left-color:var(--green)}
.vp-alert.important{border-left-color:var(--purple)}.vp-alert.warning{border-left-color:var(--yellow)}
.vp-alert.danger{border-left-color:var(--red)}
.article :not(pre)>code{background:var(--inline-code-bg);color:var(--inline-code);border-radius:4px;
padding:2px 6px;font-size:.9em;font-family:"JetBrains Mono",ui-monospace,Consolas,monospace}
.codehilite{position:relative;background:var(--code-bg);border:1px solid var(--code-border);border-radius:10px;
padding:16px 18px;margin:18px 0;overflow-x:auto}
.codehilite pre{margin:0;font-size:13.5px;line-height:1.65}
code{font-family:"JetBrains Mono",ui-monospace,Consolas,"Noto Sans Mono CJK SC",monospace}
.copybtn{position:absolute;top:8px;right:8px;border:1px solid var(--code-border);background:var(--bg);
color:var(--text-3);border-radius:6px;font-size:11px;padding:3px 9px;cursor:pointer;opacity:0;transition:opacity .2s}
.codehilite:hover .copybtn{opacity:1}.copybtn:hover{color:var(--brand);border-color:var(--brand)}
.pager{display:flex;gap:14px;max-width:784px;margin:0 auto;padding:28px 40px 70px}
.pager a{flex:1;border:1px solid var(--divider);border-radius:12px;padding:14px 18px;transition:border .2s}
.pager a:hover{border-color:var(--brand)}
.pager a.next{text-align:right}
.pager .lab{display:block;font-size:12px;color:var(--text-3)}
.pager .ti{color:var(--text-1);font-size:14.5px;font-weight:600}
.pager a:hover .ti{color:var(--brand)}
.foot{max-width:784px;margin:0 auto;padding:0 40px 60px;color:var(--text-3);font-size:12.5px;
border-top:1px solid var(--divider);padding-top:18px}
.hero{padding:88px 24px 60px;text-align:center}
.hero h1{font-size:52px;margin:0;line-height:1.2;letter-spacing:-1px;
background:linear-gradient(120deg,var(--brand) 30%,#41d1ff);
-webkit-background-clip:text;background-clip:text;color:transparent}
.hero p{font-size:21px;color:var(--text-2);margin:22px auto 34px;max-width:640px}
.hero .btns{display:flex;gap:14px;justify-content:center;flex-wrap:wrap}
.btn{border-radius:22px;padding:9px 22px;font-size:15px;font-weight:600;cursor:pointer}
.btn.pri{background:var(--brand);color:#fff;border:1px solid var(--brand)}
.btn.pri:hover{background:var(--brand-hover);color:#fff}
.btn.alt{background:var(--bg-soft);color:var(--text-1);border:1px solid var(--divider)}
.btn.alt:hover{border-color:var(--brand);color:var(--brand)}
.feat{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;max-width:980px;margin:10px auto 40px;padding:0 24px}
.feat .f{border:1px solid var(--divider);border-radius:14px;padding:22px;background:var(--bg)}
.feat .f h3{margin:0 0 6px;font-size:16px;color:var(--text-1)}
.feat .f p{margin:0;font-size:13.5px;color:var(--text-2);line-height:1.7}
.portal{max-width:980px;margin:0 auto;padding:10px 24px 90px}
.portal h2{font-size:22px;margin:40px 0 16px;color:var(--text-1)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
.card{border:1px solid var(--divider);border-radius:16px;padding:20px 22px;background:var(--bg);transition:border .2s, transform .2s}
.card:hover{border-color:var(--brand)}
.card h3{margin:0 0 2px;font-size:17px}.card .u{color:var(--text-3);font-size:12px;margin-bottom:12px}
.card li{margin:5px 0;list-style:none}
.card ul{padding:0;margin:0}
.card a{color:var(--text-1)}.card a:hover{color:var(--brand)}
.card .cnt{color:var(--text-3);font-size:12px}
.recent li a{display:flex;justify-content:space-between;gap:10px}
.recent .when{color:var(--text-3);font-size:12px}
.mburger{display:none;align-items:center;justify-content:center}
.backdrop{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:89}
.backdrop.show{display:block}
@media(max-width:900px){
 .mburger{display:inline-flex}
 .sidebar{display:block;position:fixed;left:0;top:var(--nav-h);bottom:0;height:auto;width:280px;
  z-index:90;transform:translateX(-105%);transition:transform .25s ease;box-shadow:none}
 .sidebar.open{transform:translateX(0);box-shadow:12px 0 40px rgba(0,0,0,.25)}
 .nav{padding:0 10px;gap:8px}
 .nav select{max-width:118px;font-size:12px}
 #q{width:104px;font-size:16px}
 .adminlink .t{display:none}
 .article{padding:22px 16px 60px}
 h1.tt{font-size:25px}
 .article h2{font-size:20px;margin-top:32px;padding-top:16px}
 .hero{padding:calc(var(--nav-h) + 40px) 16px 38px}
 .hero h1{font-size:38px}.hero p{font-size:16px}
 .article,.pager,.foot{padding-left:16px;padding-right:16px}
 .pager{padding-top:20px;padding-bottom:50px;gap:10px}
 .pager .ti{font-size:13px}
}
'''


def _pyg():
    from pygments.formatters import HtmlFormatter
    light = HtmlFormatter(style='friendly').get_style_defs('.codehilite')
    dark = HtmlFormatter(style='github-dark').get_style_defs('.codehilite')

    def scope(css, prefix):
        out = []
        for rule in css.split('}'):
            rule = rule.strip()
            if not rule:
                continue
            sel, _, props = rule.partition('{')
            out.append(f'{prefix} {sel.strip()}{{{props.strip()}}}')
        return '\n'.join(out)
    return light, scope(dark, 'html.dark')


def rewrite_images(body):
    def rw(m):
        alt, url = m.group(1), m.group(2)
        if url.startswith(('http://', 'https://')):
            name = util.asset_name(url)
            if (syncmod.ASSETS / name).exists():
                url = A + name
        return f'![{alt}]({url})'
    return util.IMG_INLINE.sub(rw, body)


def rewrite_htmlimgs(body):
    def rw(m):
        url = m.group(1)
        name = util.asset_name(url)
        if (syncmod.ASSETS / name).exists():
            url = A + name
        return m.group(0).replace(m.group(1), url)
    return util.HTML_IMG.sub(rw, body)


class Linker:
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


def _sidebar(man, book, cur_slug=''):
    groups = {}
    for a2 in book['articles']:
        segs = a2['slug'].split('/')
        groups.setdefault(segs[0] if len(segs) > 1 else '', []).append(a2)
    out = ['<aside class="sidebar" id="sidebar">']
    base = f"/p/{man['id']}/{book['id']}"
    for g, arts in groups.items():
        if g:
            gshow = re.sub(r'^\d+[_.\s-]*', '', g).replace('_', ' ').replace('-', ' ').strip() or g
            out.append(f'<details open><summary>{H.escape(gshow)}</summary>')
        for a2 in arts:
            cls = ' class="on"' if a2['slug'] == cur_slug else ''
            out.append(f'<a{cls} href="{base}/{H.escape(a2["slug"])}.html">{H.escape(a2["title"])}</a>')
        if g:
            out.append('</details>')
    out.append('</aside>')
    return ''.join(out)


def _topbar(man):
    opts = []
    for m2 in syncmod.load_manifests():
        sel = ' selected' if m2['id'] == man['id'] else ''
        opts.append(f'<option value="{m2["id"]}"{sel}>{H.escape(m2["name"])}</option>')
    return ('<div id="progress"></div>'
            '<header class="nav"><button class="tbtn mburger" id="mbtn" title="目录">☰</button>'
            '<a class="logo" href="/">Doc<b>Vault</b></a>'
            f'<select onchange="location=\'/?p=\'+this.value">{"".join(opts)}</select>'
            '<span class="sp"></span>'
            '<div class="searchwrap"><input id="q" placeholder="搜索本书… Ctrl+K" autocomplete="off"/>'
            '<div id="results"></div></div>'
            '<button class="tbtn" id="themebtn" title="切换主题">🌗</button>'
            '<a class="adminlink" href="/admin" target="_blank" title="管理台（新窗口打开）">⚙<span class="t"> 管理台</span></a></header>'
            '<div class="backdrop" id="backdrop"></div>')


PAGE = ('<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width,initial-scale=1"/>'
        '<title>@@TITLE@@ · DocVault</title>'
        '<script>@@HEADJS@@</script><style>@@CSS@@</style>'
        '<style>@@PYG_L@@</style><style>@@PYG_D@@</style></head>'
        '<body data-pid="@@PID@@">@@TOPBAR@@<div class="layout">@@SIDEBAR@@'
        '<main class="main"><div class="article">'
        '<div class="crumb">@@CRUMB@@</div><h1 class="tt">@@TITLE@@</h1>@BODY@</div>'
        '<div class="pager">@@PREV@@@@NEXT@@</div>'
        '<div class="foot">DocVault · 同步于 @@UPD@@ · 源: @@SRC@@</div></main></div>'
        '<script>@@APP@@</script></body></html>')

HEADJS = ("try{var t=localStorage.dvTheme;if(t==='dark'||(!t&&matchMedia('(prefers-color-scheme: dark)').matches))"
          "document.documentElement.classList.add('dark')}catch(e){}")

PORTAL = ('<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"/>'
          '<meta name="viewport" content="width=device-width,initial-scale=1"/><title>DocVault</title>'
          '<script>' + HEADJS + '</script><style>@@CSS@@</style></head><body>'
          '<div id="progress"></div>'
          '<header class="nav"><a class="logo" href="/">Doc<b>Vault</b></a><span class="sp"></span>'
          '<button class="tbtn" id="themebtn">🌗</button><a class="adminlink" href="/admin" target="_blank">⚙ 管理台</a></header>'
          '<section class="hero"><h1>DocVault</h1>'
          '<p>多源技术文档缓存站 · 在线可更新，离线可携带 —— 看过的每一篇都被记住</p>'
          '<div class="btns"><a class="btn pri" href="#books">开始阅读</a>'
          '<a class="btn alt" href="/admin">管理资源</a></div></section>'
          '<section class="feat">'
          '<div class="f"><h3>📥 多源缓存</h3><p>GitHub 开源教程一键镜像，图片全部本地化，永不失效</p></div>'
          '<div class="f"><h3>🔍 全文搜索</h3><p>每本书独立的预构建索引，离线环境下依然即输即搜</p></div>'
          '<div class="f"><h3>✅ 阅读记忆</h3><p>自动记录已读与最近浏览，侧栏打勾，接着上次继续</p></div>'
          '<div class="f"><h3>📦 一包带走</h3><p>整站导出为一个 zip，拷进内网 nginx/python 即可开箱即用</p></div>'
          '</section>'
          '<section class="portal" id="books"><h2>📚 书架</h2><div class="cards" id="cards">@@CARDS@@</div>'
          '<h2>🕘 最近阅读</h2><div class="card recent"><ul id="recent"><li class="u" style="color:var(--text-3)">暂无记录，读一篇文章试试</li></ul></div>'
          '</section><script>@@APP@@</script></body></html>')


def _urlmap(man, book):
    m = {}
    base = f"/p/{man['id']}/{book['id']}"
    for a2 in book['articles']:
        m[a2['slug'] + '.md'] = f"{base}/{H.escape(a2['slug'])}.html"
        if a2['slug'].lower().endswith('/readme'):
            m[a2['slug'][:-6] + '.md'] = f"{base}/{H.escape(a2['slug'])}.html"
    return m


def build(manifests=None):
    global SITE
    manifests = manifests if manifests is not None else syncmod.load_manifests()
    tmp = syncmod.DATA / 'site.tmp'
    if tmp.exists():
        shutil.rmtree(tmp)
    SITE = tmp
    (SITE / 'search').mkdir(parents=True)
    (SITE / 'a').mkdir(parents=True)
    pyg_l, pyg_d = _pyg()

    for man in manifests:
        sidx = []
        for b in man['books']:
            broot = Path(b['root'])
            for a2 in b['articles']:
                tx = (broot / (a2['slug'] + '.md')).read_text(encoding='utf-8', errors='ignore')
                body = util.md_to_html(tx)
                sidx.append({'u': f"/p/{man['id']}/{b['id']}/{a2['slug']}.html",
                             't': a2['title'], 'x': util.strip_tags(body, 1200)})
        (SITE / 'search' / f"{man['id']}.json").write_text(json.dumps(sidx, ensure_ascii=False))
        print(f"[{man['id']}] search index: {len(sidx)}")

        for b in man['books']:
            broot = Path(b['root'])
            linker = Linker(broot, _urlmap(man, b))
            base = f"/p/{man['id']}/{b['id']}"
            arts = b['articles']
            lst = ''.join(f'<li><a href="{base}/{H.escape(a2["slug"])}.html">{H.escape(a2["title"])}</a></li>'
                          for a2 in arts)
            _write_page(man, b, 'index.html', f'{b["title"]} · 目录',
                        f'<p style="color:var(--text-2)">{len(arts)} 篇 · 点击左侧目录或下方列表开始</p><ol>{lst}</ol>',
                        upd=man['updated'], pyg=(pyg_l, pyg_d))
            all_local = set()
            for i, a2 in enumerate(arts):
                tx = (broot / (a2['slug'] + '.md')).read_text(encoding='utf-8', errors='ignore')
                body = util.md_to_html(tx)
                body = re.sub(r'<h1[^>]*>.*?</h1>', '', body, count=1, flags=re.S)
                body = util.alerts(body)
                body = rewrite_htmlimgs(rewrite_images(body))
                body = util.localize_local(body, (broot / a2['slug']).parent, syncmod.ASSETS)
                body = linker(body, (broot / a2['slug']).parent)
                all_local |= {m.group(1).split('/')[-1]
                              for m in re.finditer(r'src="/a/([^"]+)"', body)}
                for u in util.collect_urls(tx):
                    f = syncmod.ASSETS / util.asset_name(u)
                    if f.exists():
                        all_local.add(util.asset_name(u))
                prev_a = arts[i - 1] if i > 0 else None
                next_a = arts[i + 1] if i < len(arts) - 1 else None
                prev = (f'<a href="{base}/{H.escape(prev_a["slug"])}.html">'
                        f'<span class="lab">← 上一篇</span><span class="ti">{H.escape(prev_a["title"][:26])}</span></a>'
                        ) if prev_a else '<span></span>'
                nxt = (f'<a class="next" href="{base}/{H.escape(next_a["slug"])}.html">'
                       f'<span class="lab">下一篇 →</span><span class="ti">{H.escape(next_a["title"][:26])}</span></a>'
                       ) if next_a else '<span></span>'
                _write_page(man, b, a2['slug'] + '.html', a2['title'], body, cur=a2['slug'],
                            prev=prev, nxt=nxt, upd=man['updated'], pyg=(pyg_l, pyg_d))
            _link_assets(all_local)
            print(f"[{man['id']}] book {b['id']}: {len(arts)} pages")

    _portal(manifests)
    (SITE / 'style.css').write_text(VPC)
    real = syncmod.DATA / 'site'
    old = syncmod.DATA / 'site.old'
    if real.exists():
        os.rename(real, old)
    os.rename(tmp, real)
    shutil.rmtree(old, ignore_errors=True)
    SITE = real
    print('site ->', SITE)


def _link_assets(names):
    d = SITE / 'a'
    d.mkdir(parents=True, exist_ok=True)
    for n in names:
        src = syncmod.ASSETS / n
        dst = d / n
        if not src.exists() or dst.exists():
            continue
        shutil.copy2(src, dst)


def _write_page(man, book, fname, title, body, cur='', sidebar=None, prev='', nxt='',
                upd='', pyg=('', '')):
    path = SITE / 'p' / man['id'] / book['id'] / fname
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f"/p/{man['id']}/{book['id']}/{fname}"
    src = H.escape(man['name'])
    if man['type'] == 'github':
        p = [x for x in syncmod.projects() if x['id'] == man['id']][0]
        src = f"<a href=\"https://github.com/{p['repo']}\">{p['repo']}</a>"
    html = (PAGE.replace('@@TITLE@@', H.escape(title))
                .replace('@@HEADJS@@', HEADJS)
                .replace('@@CSS@@', VPC)
                .replace('@@PYG_L@@', pyg[0]).replace('@@PYG_D@@', pyg[1])
                .replace('@@PID@@', man['id'])
                .replace('@@TOPBAR@@', _topbar(man))
                .replace('@@SIDEBAR@@', sidebar or _sidebar(man, book, cur))
                .replace('@@CRUMB@@', f'<a href="{url.rsplit("/", 1)[0]}/index.html">{H.escape(book["title"])}</a>'
                                      f' / {H.escape(title)}')
                .replace('@BODY@', body)
                .replace('@@PREV@@', prev).replace('@@NEXT@@', nxt)
                .replace('@@UPD@@', upd or '').replace('@@SRC@@', src)
                .replace('@@APP@@', APP_JS))
    path.write_text(html, encoding='utf-8')


def _portal(manifests):
    cards = []
    for man in manifests:
        lis = []
        for b in man['books']:
            lis.append(f'<li><a href="/p/{man["id"]}/{b["id"]}/index.html">{H.escape(b["title"])} '
                       f'<span class="cnt">({len(b["articles"])})</span></a></li>')
        if man['type'] == 'upload':
            fdir = syncmod.UPLOADS / man['id'] / '_files'
            if fdir.exists():
                for f in sorted(fdir.iterdir()):
                    lis.append(f'<li><a href="/files/{man["id"]}/{H.escape(f.name)}">📎 {H.escape(f.name)}</a></li>')
        cards.append(f'<div class="card"><h3>{H.escape(man["name"])}</h3>'
                     f'<div class="u">同步: {man["updated"]} · {man["type"]}</div><ul>{"".join(lis)}</ul></div>')
    (SITE / 'index.html').write_text(
        PORTAL.replace('@@CSS@@', VPC).replace('@@CARDS@@', ''.join(cards))
              .replace('@@APP@@', APP_JS), encoding='utf-8')


APP_JS = '''
(function(){
var d=document;
/* theme */
var tb=d.getElementById('themebtn');
if(tb)tb.onclick=function(){var c=d.documentElement.classList;c.toggle('dark');
try{localStorage.dvTheme=c.contains('dark')?'dark':'light'}catch(e){}};
/* progress */
var pg=d.getElementById('progress');
d.addEventListener('scroll',function(){
 var h=d.documentElement,max=h.scrollHeight-h.clientHeight;
 if(pg)pg.style.width=(max>0?(h.scrollTop/max*100):0)+'%';
 markRead();},{passive:true});
/* copy buttons */
d.querySelectorAll('.codehilite').forEach(function(el){
 var b=d.createElement('button');b.className='copybtn';b.textContent='复制';
 b.onclick=function(){navigator.clipboard.writeText(el.innerText.replace(/\\n?复制$/,'')).then(function(){b.textContent='✓';setTimeout(function(){b.textContent='复制'},1200)})};
 el.appendChild(b)});
/* search */
var q=d.getElementById('q'),box=d.getElementById('results'),pid=d.body.dataset.pid,idx=null;
function esc(s){return (s||'').replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function snip(x,t){var i=x.toLowerCase().indexOf(t);return i<0?x.slice(0,80):'…'+x.slice(Math.max(0,i-20),i+80)+'…'}
function render(){var t=(q.value||'').trim().toLowerCase();
 if(!t||!idx){box.style.display='none';return}
 var hits=idx.filter(function(a){return (a.t+' '+a.x).toLowerCase().indexOf(t)>=0}).slice(0,20);
 box.innerHTML=hits.map(function(a){return '<a href="'+a.u+'"><div class="t">'+esc(a.t)+'</div><div class="s">'+esc(snip(a.x,t))+'</div></a>'}).join('')||'<a><div class="s">无结果</div></a>';
 box.style.display='block'}
if(q){q.addEventListener('focus',function(){if(!idx&&pid)fetch('/search/'+pid+'.json').then(function(r){return r.json()}).then(function(j){idx=j})});
 q.addEventListener('input',render);q.addEventListener('keydown',function(e){if(e.key==='Enter')render()})}
d.addEventListener('keydown',function(e){if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();if(q)q.focus()}});
d.addEventListener('click',function(e){if(box&&!box.contains(e.target)&&e.target!==q)box.style.display='none'});
/* drawer */
var mb=d.getElementById('mbtn'),bd=d.getElementById('backdrop'),sb=d.getElementById('sidebar');
function drawer(o){if(!sb)return;sb.classList.toggle('open',o);
 if(bd)bd.classList.toggle('show',o);d.body.style.overflow=o?'hidden':''}
if(mb)mb.onclick=function(){drawer(!sb.classList.contains('open'))};
if(bd)bd.onclick=function(){drawer(false)};
d.querySelectorAll('.sidebar a').forEach(function(a){
 a.addEventListener('click',function(){drawer(false)})});
/* read tracking */
var url=location.pathname, title=d.title.replace(' · DocVault','');
function store(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
function load(k,def){try{return JSON.parse(localStorage.getItem(k))||def}catch(e){return def}}
var read=load('dvRead',{}),recent=load('dvRecent',[]);
if(read[url]){var cur=d.querySelector('.sidebar a.on');if(cur)cur.classList.add('read')}
d.querySelectorAll('.sidebar a').forEach(function(a){
 if(read[new URL(a.href,location.origin).pathname])a.classList.add('read')});
var marked=false;
function markRead(){
 if(marked||!pid||d.body.querySelector('.portal'))return;
 var h=d.documentElement;
 if((h.scrollTop+h.clientHeight)/h.scrollHeight>0.82){
  marked=true;read[url]=Date.now();store('dvRead',read);
  var cur=d.querySelector('.sidebar a.on');if(cur)cur.classList.add('read');
  recent=recent.filter(function(x){return x.u!==url});
  recent.unshift({u:url,t:title,ts:Date.now()});recent=recent.slice(0,12);store('dvRecent',recent)}}
/* portal recent */
var rec=d.getElementById('recent');
if(rec){var items=load('dvRecent',[]).slice(0,8);
 rec.innerHTML=items.length?items.map(function(x){
  var t=new Date(x.ts),pad=function(n){return (n<10?'0':'')+n};
  return '<li><a href="'+x.u+'"><span>'+esc(x.t)+'</span><span class="when">'+
   t.getFullYear()+'-'+pad(t.getMonth()+1)+'-'+pad(t.getDate())+'</span></a></li>'}).join(''):
  '<li style="color:var(--text-3)">暂无记录，读一篇文章试试</li>'}
})();
'''
