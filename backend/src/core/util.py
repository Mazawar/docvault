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


def _tasklist(text):
    """GFM 任务列表 → ☐/☑（仅代码块外，避免污染示例代码）。"""
    parts = re.split(r'(```.*?```|~~~.*?~~~)', text, flags=re.S)
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r'(?m)^(\s*(?:[-*+]|\d+[.)])\s+)\[ \] ', r'\1☐ ', parts[i])
        parts[i] = re.sub(r'(?m)^(\s*(?:[-*+]|\d+[.)])\s+)\[[xX]\] ', r'\1☑ ', parts[i])
    return ''.join(parts)


def md_to_html(text):
    text, _ = strip_fm(text)
    text = _vitepress(text)
    text = _tasklist(text)
    text = rewrite_refdefs(text)
    text = DEL.sub(r'<del>\1</del>', text)
    md = markdown.Markdown(**MD_KW)
    return md.convert(text)


_VP_C = re.compile(r'^ {0,3}:::\s*([A-Za-z-]+)?\s*(.*)$')
_VP_KIND = {'tip': 'tip', 'info': 'note', 'note': 'note', 'important': 'important',
            'warning': 'warning', 'danger': 'danger', 'details': 'note',
            'code-group': 'code-group'}
_FENCES = re.compile(r'(```.*?```|~~~.*?~~~)', re.S)


def _vitepress(text):
    """VitePress 方言 → 通用 Markdown：标题剥 {#锚点}；::: 容器 → admonition；
    标题/围栏前补空行（CommonMark 允许打断段落，Python-Markdown 不允许）。

    代码围栏内的 ::: 与 {#} 原样保留（示例代码不受影响）。"""
    parts = _FENCES.split(text)
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r'(?m)^(#{1,6} .+?)\s*\{#[^}]*\}\s*$', r'\1', parts[i])
        # VitePress 在 markdown 里裸写 <div> 包内容：声明让 md_in_html 解析其内部 Markdown
        parts[i] = re.sub(
            r'(?m)^(\s*<(?:div|section|details|blockquote)(?:\s[^>]*)?)>\s*$',
            r'\1 markdown="1">', parts[i])
    text = ''.join(parts)

    lines = []
    prev_blank = True
    for line in text.split('\n'):
        if not prev_blank and re.match(r'^(#{1,6} |```|~~~)', line):
            lines.append('')  # 块级元素前补空行，否则被并入上一段落
        lines.append(line)
        prev_blank = not line.strip()
    text = '\n'.join(lines)

    out, buf, in_c = [], None, False
    for line in text.split('\n'):
        if not in_c:
            m = _VP_C.match(line)
            if m and (m.group(1) or '').lower() in _VP_KIND:
                kind = _VP_KIND[m.group(1).lower()]
                title = m.group(2).strip().replace('"', "'")
                buf = [f'!!! {kind} "{title}"' if title else f'!!! {kind} ""']
                in_c = True
                continue
            out.append(line)
            continue
        if re.match(r'^ {0,3}:::\s*$', line):
            out.extend(buf)
            out.append('')
            buf, in_c = None, False
            continue
        buf.append(('    ' + line) if line.strip() else '')
    if buf:
        out.extend(buf)  # 未闭合容器兜底，避免吞掉后文
    return '\n'.join(out)


ALERT = re.compile(r'<blockquote>\s*<p>\[!(NOTE|TIP|IMPORTANT|WARNING|DANGER)\]\s*(.*?)</blockquote>', re.S)
ALERT_TITLE = {'NOTE': '笔记', 'TIP': '提示', 'IMPORTANT': '重要', 'WARNING': '警告', 'DANGER': '危险'}


def outside_fences(text, fn):
    """仅对代码围栏外的文本应用 fn（改写不能污染代码示例）。"""
    parts = _FENCES.split(text)
    for i in range(0, len(parts), 2):
        parts[i] = fn(parts[i])
    return ''.join(parts)


def strip_heading_meta(text):
    """剥标题行 VitePress 标记：{#锚点} 后缀、尾部 \\* / \\*\\*（API 专属记号）。围栏内不动。"""
    parts = _FENCES.split(text)
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r'(?m)^(#{1,6} .+?)\s*\{#[^}]*\}\s*$', r'\1', parts[i])
        parts[i] = re.sub(r'(?m)^(#{1,6} .*?\S)[ \t]+(?:\\\*|\*){1,2}[ \t]*$', r'\1', parts[i])
    return ''.join(parts)


def vp_containers(text):
    """VitePress ::: 容器 → md-editor-v3 内置 admonition 的 !!! 语法（内容不缩进）。
    开/闭标记允许 ≤3 空格缩进（CommonMark 块约定，源站允许闭合标记缩进）。
    围栏内不转换；未闭合容器补 !!! 兜底。"""
    out, in_c, fence = [], False, ''
    for line in text.split('\n'):
        s = line.lstrip(' ')
        if fence:
            if s.startswith(fence) and not s[len(fence):].strip():
                fence = ''
            out.append(line)
            continue
        m = re.match(r'^ {0,3}(```|~~~)', line)
        if m:
            fence = m.group(1)
            out.append(line)
            continue
        if not in_c:
            m2 = _VP_C.match(line)
            if m2 and (m2.group(1) or '').lower() in _VP_KIND:
                kind = _VP_KIND[m2.group(1).lower()]
                title = m2.group(2).strip()
                out.append(('!!! ' + kind + (' ' + title if title else '')).rstrip())
                in_c = True
                continue
            out.append(line)
            continue
        if re.match(r'^ {0,3}:::\s*$', line):
            out.append('!!!')
            in_c = False
            continue
        out.append(line)
    if in_c:
        out.append('!!!')  # 未闭合容器兜底
    return '\n'.join(out)


def localize_md_images(text, cur_dir, assets_dir, root=None):
    """Markdown 图片语法里的仓库内相对路径（及 / 开头的 public 目录路径）→ 缓存资源地址。"""

    def rw(m):
        alt, url = m.group(1), m.group(2)
        if url.startswith(('http://', 'https://', '/a/', 'data:')):
            return m.group(0)
        rel = urllib.parse.unquote(url.split('#')[0])
        if url.startswith('/'):
            base = Path(root) if root else Path(cur_dir)
            cands = [base / 'public' / rel.lstrip('/'), base / rel.lstrip('/')]
        else:
            cands = [Path(os.path.normpath(Path(cur_dir) / rel))]
        for p in cands:
            if p.is_file():
                data = p.read_bytes()
                name = hashlib.sha256(data).hexdigest()[:32] + p.suffix.lower()
                dst = Path(assets_dir) / name
                if not dst.exists():
                    dst.write_bytes(data)
                return f'![{alt}](/a/{name})'
        return m.group(0)

    return IMG_INLINE.sub(rw, text)


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
        return re.sub(r'\s*\{#[^}]*\}\s*$', '', t)
    for line in text.splitlines():
        if line.startswith('# '):
            return re.sub(r'\s*\{#[^}]*\}\s*$', '', line[2:].strip())
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
