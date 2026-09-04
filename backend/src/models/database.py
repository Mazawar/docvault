"""SQLite 连接与建表（模型层·基础设施）。查询入口见 repository.py。"""
import json
import sqlite3
import threading
from ..core import config

_lock = threading.Lock()
_initialized = False


def connect() -> sqlite3.Connection:
    config.DATA.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(config.DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    return c


SCHEMA = '''
CREATE TABLE IF NOT EXISTS projects(
  id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL DEFAULT 'github',
  repo TEXT NOT NULL DEFAULT '', root TEXT NOT NULL DEFAULT '.',
  books_json TEXT NOT NULL DEFAULT '', group_titles TEXT NOT NULL DEFAULT '',
  sort INTEGER NOT NULL DEFAULT 0, updated TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS books(
  pid TEXT NOT NULL, id TEXT NOT NULL, title TEXT NOT NULL,
  root TEXT NOT NULL DEFAULT '', PRIMARY KEY(pid, id));
CREATE TABLE IF NOT EXISTS articles(
  pid TEXT NOT NULL, bid TEXT NOT NULL, slug TEXT NOT NULL,
  title TEXT NOT NULL, body TEXT NOT NULL, ord INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(pid, bid, slug));
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
  pid UNINDEXED, bid UNINDEXED, slug UNINDEXED, title, body);
CREATE TABLE IF NOT EXISTS jobs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, status TEXT NOT NULL,
  log TEXT NOT NULL DEFAULT '[]', created TEXT NOT NULL DEFAULT '',
  finished TEXT NOT NULL DEFAULT '');
'''


def init():
    """建库建表；空库时从 projects.json 导入种子配置。幂等。"""
    global _initialized
    if _initialized:
        return
    with _lock, connect() as c:
        c.executescript(SCHEMA)
        cols = {r[1] for r in c.execute('PRAGMA table_info(projects)')}
        if 'group_titles' not in cols:
            c.execute("ALTER TABLE projects ADD COLUMN group_titles TEXT NOT NULL DEFAULT ''")
        if not c.execute('SELECT 1 FROM projects LIMIT 1').fetchone():
            _seed_projects(c)
    _initialized = True


def _seed_projects(c):
    f = config.BASE / 'projects.json'
    if not f.exists():
        return
    try:
        cfg = json.loads(f.read_text(encoding='utf-8'))
    except Exception:
        return
    for i, p in enumerate(cfg.get('projects', [])):
        c.execute("INSERT OR IGNORE INTO projects(id,name,type,repo,root,books_json,group_titles,sort) VALUES(?,?,?,?,?,?,?,?)",
                  (p['id'], p.get('name', p['id']), p.get('type', 'github'),
                   p.get('repo', ''), p.get('root', '.'),
                   json.dumps(p.get('books') or {}, ensure_ascii=False),
                   json.dumps(p.get('groupTitles') or {}, ensure_ascii=False), i))
