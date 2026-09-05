"""数据访问层：projects / books / articles / jobs / FTS 检索。

安全约定：SQL 一律为完整静态字符串 + ? 参数绑定；禁止任何形式拼接 SQL 文本。
用户输入只允许作为绑定参数出现；搜索词先做白名单字符清洗。
"""
import json
import re
import time
from ..core import config
from . import database

# ---------- projects ----------

def get_project(pid):
    with database.connect() as c:
        return _prow(c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone())


def list_projects():
    with database.connect() as c:
        return [_prow(r) for r in c.execute("SELECT * FROM projects ORDER BY sort, id").fetchall()]


def _prow(r):
    if not r:
        return None
    return {'id': r['id'], 'name': r['name'], 'type': r['type'], 'repo': r['repo'],
            'root': r['root'], 'books': json.loads(r['books_json'] or '{}'),
            'group_titles': json.loads(r['group_titles'] or '{}'),
            'sort': r['sort'], 'updated': r['updated']}


def upsert_project(p, sort=None):
    with database._lock, database.connect() as c:
        sv = sort if sort is not None else p.get('sort')
        c.execute("INSERT INTO projects(id,name,type,repo,root,books_json,group_titles,sort) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, type=excluded.type, repo=excluded.repo, root=excluded.root, books_json=excluded.books_json, group_titles=excluded.group_titles, sort=COALESCE(?, projects.sort)",
                  (p['id'], p['name'], p['type'], p.get('repo', ''), p.get('root', '.'),
                   json.dumps(p.get('books') or {}, ensure_ascii=False),
                   json.dumps(p.get('group_titles') or {}, ensure_ascii=False),
                   sv, sv))


def delete_project(pid):
    with database._lock, database.connect() as c:
        c.execute("DELETE FROM articles WHERE pid=?", (pid,))
        c.execute("DELETE FROM books WHERE pid=?", (pid,))
        c.execute("DELETE FROM projects WHERE id=?", (pid,))


def touch_project(pid, updated=None):
    with database._lock, database.connect() as c:
        c.execute("UPDATE projects SET updated=? WHERE id=?",
                  (updated or time.strftime('%Y-%m-%d %H:%M'), pid))


# ---------- books / articles ----------

def list_books(pid):
    with database.connect() as c:
        return [dict(r) for r in c.execute("SELECT b.*, (SELECT COUNT(*) FROM articles a WHERE a.pid=b.pid AND a.bid=b.id) AS n FROM books b WHERE b.pid=? ORDER BY b.rowid", (pid,)).fetchall()]


def get_book(pid, bid):
    with database.connect() as c:
        r = c.execute("SELECT b.*, (SELECT COUNT(*) FROM articles a WHERE a.pid=b.pid AND a.bid=b.id) AS n FROM books b WHERE b.pid=? AND b.id=?", (pid, bid)).fetchone()
        return dict(r) if r else None


def list_articles(pid, bid):
    with database.connect() as c:
        return [dict(r) for r in c.execute("SELECT slug,title FROM articles WHERE pid=? AND bid=? ORDER BY ord", (pid, bid)).fetchall()]


def get_article(pid, bid, slug):
    with database.connect() as c:
        r = c.execute("SELECT slug,title,body FROM articles WHERE pid=? AND bid=? AND slug=?", (pid, bid, slug)).fetchone()
        return dict(r) if r else None


def replace_books(pid, books_):
    """sync 后整项目重写 books + articles（含 FTS），单事务。"""
    with database._lock, database.connect() as c:
        c.execute("DELETE FROM articles_fts WHERE pid=?", (pid,))
        c.execute("DELETE FROM articles WHERE pid=?", (pid,))
        c.execute("DELETE FROM books WHERE pid=?", (pid,))
        for b in books_:
            c.execute("INSERT INTO books(pid,id,title,root) VALUES(?,?,?,?)",
                      (pid, b['id'], b['title'], str(b['root'])))
            for i, a in enumerate(b['articles']):
                c.execute("INSERT INTO articles(pid,bid,slug,title,body,ord) VALUES(?,?,?,?,?,?)",
                          (pid, b['id'], a['slug'], a['title'], a['body'], i))
                c.execute("INSERT INTO articles_fts(pid,bid,slug,title,body) VALUES(?,?,?,?,?)",
                          (pid, b['id'], a['slug'], _cjk_split(a['title']), _cjk_split(a['body'])))


_CJK = r'\u4e00-\u9fff\u3400-\u4dbf'


def _cjk_split(s):
    """CJK 逐字切开（FTS unicode61 会把连续汉字当一个整词，短词无法命中）。"""
    return re.sub(f'([{_CJK}])', r'\1 ', s)


def _cjk_unsplit(s):
    return re.sub(f'(?<=[{_CJK}]) (?=[{_CJK}])', '', s)


def _make_snip(body, words, span=36):
    """从原文生成摘要：首个命中词位置取窗，轻量去 md 语法后转义并 <mark> 高亮。"""
    import html as _h
    flat = re.sub(r'[#*`>]+', ' ', body)
    flat = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', flat)
    flat = re.sub(r'\s+', ' ', flat)
    low = flat.lower()
    pos = -1
    hit = ''
    for w in words:
        p = low.find(w.lower())
        if p >= 0 and (pos < 0 or p < pos):
            pos, hit = p, w
    if pos < 0:
        return _h.escape(flat[:span * 2]) + ('…' if len(flat) > span * 2 else '')
    a = max(0, pos - span)
    frag = flat[a:pos + span * 2]
    out = _h.escape(frag).replace(_h.escape(hit), f'<mark>{_h.escape(hit)}</mark>')
    return ('…' if a > 0 else '') + out + ('…' if a + span * 3 < len(flat) else '')


def search(q, pid='', limit=60):
    """FTS5 全文搜索。

    MATCH 匹配串整体作为 ? 绑定值传入（非 SQL 文本）。用户输入先做白名单
    字符清洗，CJK 逐字切分后以隐式 AND 匹配，使 FTS 语法注入无从构造。
    摘要由 Python 从原文生成（FTS 列内是切分文本，不适合直接展示）。
    """
    clean = re.sub(r'[^\w ]+', ' ', q)[:120].strip()
    if not clean:
        return []
    match = _cjk_split(clean)
    params = [match]
    if pid:
        sql = "SELECT pid,bid,slug,title FROM articles_fts WHERE articles_fts MATCH ? AND pid=? ORDER BY rank LIMIT ?"
        params.append(pid)
    else:
        sql = "SELECT pid,bid,slug,title FROM articles_fts WHERE articles_fts MATCH ? ORDER BY rank LIMIT ?"
    params.append(max(1, min(int(limit), 200)))
    words = [w for w in clean.split() if w]
    with database.connect() as c:
        rows = [dict(r) for r in c.execute(sql, params).fetchall()]
        for r in rows:
            r['title'] = _cjk_unsplit(r['title'])
            raw = c.execute("SELECT body FROM articles WHERE pid=? AND bid=? AND slug=?",
                            (r['pid'], r['bid'], r['slug'])).fetchone()
            r['snip'] = _make_snip(raw['body'] if raw else '', words)
    return rows


# ---------- jobs ----------

def job_add(name):
    with database._lock, database.connect() as c:
        cur = c.execute("INSERT INTO jobs(name,status,created) VALUES(?,?,?)",
                        (name, 'queued', time.strftime('%H:%M:%S')))
        return cur.lastrowid


def job_save(jid, status, log, finished=''):
    """log 为字符串列表；SQL 全静态，值全部参数绑定。"""
    if not isinstance(log, str):
        log = json.dumps(log, ensure_ascii=False)
    with database._lock, database.connect() as c:
        c.execute("UPDATE jobs SET status=?, log=?, finished=? WHERE id=?",
                  (status, log, finished, jid))


def job_get(jid):
    with database.connect() as c:
        r = c.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        return _jrow(r) if r else None


def jobs_recent(n=30):
    with database.connect() as c:
        return [_jrow(r) for r in c.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (int(n),)).fetchall()]


def _jrow(r):
    d = dict(r)
    try:
        d['log'] = json.loads(d.get('log') or '[]')
    except Exception:
        d['log'] = [str(d.get('log'))]
    return d


def prune_jobs(keep=200):
    with database._lock, database.connect() as c:
        c.execute("DELETE FROM jobs WHERE id NOT IN (SELECT id FROM jobs ORDER BY id DESC LIMIT ?)", (int(keep),))


# ---------- 聚合 ----------

def index_payload():
    """portal / 侧栏 / 离线静态模式共用的书架数据。"""
    out = []
    for p in list_projects():
        if p['type'] == 'upload':
            continue  # 笔记走独立 /notes 模块（DESIGN.md 笔记模块）
        bs = [{'id': b['id'], 'title': b['title'], 'n': b['n']} for b in list_books(p['id'])]
        item = {'id': p['id'], 'name': p['name'], 'type': p['type'],
                'updated': p['updated'] or '-', 'books': bs, 'files': []}
        if p['type'] == 'upload':
            fdir = config.UPLOADS / p['id'] / '_files'
            if fdir.exists():
                item['files'] = sorted(f.name for f in fdir.iterdir() if f.is_file())
        out.append(item)
    return {'projects': out}
