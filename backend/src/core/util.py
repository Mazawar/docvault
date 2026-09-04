"""通用工具：md→html、图片抓取缓存、排序键。无包内依赖。"""
import html as H
import hashlib, ipaddress, os, re, socket, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path
import markdown
from markdown.extensions.toc import slugify_unicode

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36'}
IMG_INLINE = re.compile(r'!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?[^)]*\)')
IMG_REF = re.compile(r'!\[([^\]]*)\]\[([^\]]+)\]')
REF_DEF = re.compile(r'^\s*\[([^\]]+)\]:\s*(\S+)', re.M)
HTML_IMG = re.compile(r'<img[^>]*src="(https?://[^"]+)"')
LOCAL_IMG = re.compile(r'<img[^>]*src="(?!(?:https?:|/a/|data:|file:))([^"]+)"')
DEL = re.compile(r'~~(.+?)~~')
EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp')

MD_KW = dict(
    extensions=['extra', 'sane_lists', 'toc', 'codehilite', 'admonition', 'md_in_html'],
    extension_configs={'toc': {'slugify': slugify_unicode},
                       'codehilite': {'guess_lang': False}})


def rewrite_refdefs(t):
    defs = {m.group(1).strip().lower(): m.group(2) for m in REF_DEF.finditer(t)}
    if not defs:
        return t
    t = IMG_REF.sub(lambda m: f'![{m.group(1)}]({defs.get(m.group(2).strip().lower(), "")})'
                    if m.group(2).strip().lower() in defs else m.group(0), t)
    return REF_DEF.sub('', t)


FM = re.compile(r'\A---\s*\n(.*?)\n---\s*\n', re.S)


def strip_fm(text):
    m = FM.match(text)
    return (text[m.end():] if m else text, m.group(1) if m else '')


def fm_title(fm_block):
    m = re.search(r'^title:\s*(.+)$', fm_block, re.M)
    return m.group(1).strip().strip('\'"') if m else None


def md_to_html(text):
    text, _ = strip_fm(text)
    text = rewrite_refdefs(text)
    text = DEL.sub(r'<del>\1</del>', text)
    md = markdown.Markdown(**MD_KW)
    return md.convert(text)


ALERT = re.compile(r'<blockquote>\s*<p>\[!(NOTE|TIP|IMPORTANT|WARNING|DANGER)\]\s*(.*?)</blockquote>', re.S)
ALERT_TITLE = {'NOTE': '笔记', 'TIP': '提示', 'IMPORTANT': '重要', 'WARNING': '警告', 'DANGER': '危险'}


def alerts(html_text):
    def rw(m):
        k = m.group(1).lower()
        return (f'<div class="vp-alert {k}"><p class="vp-alert-title">{ALERT_TITLE[m.group(1)]}'
                f'</p>{m.group(2)}</div>')
    return ALERT.sub(rw, html_text)


def collect_urls(text):
    text = rewrite_refdefs(text)
    urls = [m.group(2) for m in IMG_INLINE.finditer(text)]
    urls += [m.group(1) for m in HTML_IMG.finditer(text)]
    return [u for u in urls if u.startswith(('http://', 'https://'))]


def asset_name(url):
    path = urllib.parse.urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    if ext not in EXTS:
        ext = '.svg' if 'svg' in path.lower() else '.png'
    return hashlib.sha256(url.encode()).hexdigest()[:32] + ext


def url_allowed(url):
    """SSRF 防护：仅 http(s)；字面 IP/localhost 严格拦截；
    域名在无代理时按解析出的 IP 拦私网/环回/链路本地/保留段，
    配置了系统代理时本地 DNS 可能失真（代理负责真实解析），放行交给代理。"""
    sp = urllib.parse.urlsplit(url)
    if sp.scheme not in ('http', 'https') or not sp.hostname:
        return False
    host = sp.hostname
    try:
        ip = ipaddress.ip_address(host)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast or ip.is_unspecified)
    except ValueError:
        pass
    if host.lower() in ('localhost',):
        return False
    proxies = urllib.request.getproxies()
    if proxies.get(sp.scheme) or proxies.get('http'):
        return True
    port = sp.port or (443 if sp.scheme == 'https' else 80)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(str(info[4][0]))
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            return False
    return True


class _RedirectGuard(urllib.request.HTTPRedirectHandler):
    """重定向目标逐一过 SSRF 校验。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not url_allowed(newurl):
            raise urllib.error.URLError('redirect blocked by SSRF guard')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_RedirectGuard)


def fetch(url, cache_dir):
    """Download url into cache_dir (sha256 name). Returns Path or None."""
    if not url_allowed(url):
        return None
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    f = cache_dir / asset_name(url)
    if f.exists() and f.stat().st_size > 100:
        return f
    safe = urllib.parse.quote(url, safe=':/?&=%+#@,;~')
    for _ in range(3):
        try:
            data = _OPENER.open(urllib.request.Request(safe, headers=UA), timeout=25).read()
            if len(data) > 100:
                tmp = f.with_suffix('.tmp')
                tmp.write_bytes(data)
                tmp.rename(f)
                return f
        except Exception:
            time.sleep(1)
    return None


def h1_of(p):
    text, fm = strip_fm(p.read_text(encoding='utf-8', errors='ignore')[:4000])
    t = fm_title(fm)
    if t:
        return t
    for line in text.splitlines():
        if line.startswith('# '):
            return line[2:].strip()
    return p.stem


def order_key(relpath, h1):
    """(readme-first, dir number, h1 number, name) sort key."""
    parts = Path(relpath).parts
    m = re.match(r'(\d+)', parts[0]) if len(parts) > 1 else None
    dirnum = int(m.group(1)) if m else 0
    m2 = re.match(r'(\d+(?:\.\d+)?)', h1)
    artnum = float(m2.group(1)) if m2 else 999
    prio = 0 if Path(relpath).name.upper() == 'README.MD' else 1
    return (prio, dirnum, artnum, str(relpath))


def strip_tags(html_text, limit=5000):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', html_text, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = H.unescape(re.sub(r'\s+', ' ', t))
    return t[:limit]


def localize_local(body, cur_dir, assets_dir, prefix='/a/'):
    """Rewrite in-repo relative <img src> into cached asset urls."""
    def rw(m):
        src = m.group(1)
        p = Path(os.path.normpath(Path(cur_dir) / urllib.parse.unquote(src.split('#')[0])))
        if not p.exists() or not p.is_file():
            return m.group(0)
        data = p.read_bytes()
        name = hashlib.sha256(data).hexdigest()[:32] + p.suffix.lower()
        dst = Path(assets_dir) / name
        if not dst.exists():
            dst.write_bytes(data)
        return m.group(0).replace(src, prefix + name)
    return LOCAL_IMG.sub(rw, body)
