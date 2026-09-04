/** 阅读侧 API：书架 / 书目录 / 文章 / 全文搜索（双模式） */
import { detectMode, getJSON, readUrl, type IndexPayload } from './http'
import type { ArticlePayload, BookPayload, SearchHit } from './types'

interface StaticSearchItem {
  pid: string
  bid: string
  slug: string
  t: string
  x: string
}

let staticSearchIndex: StaticSearchItem[] | null = null

function esc(s: string): string {
  return s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c] as string)
}

export async function getIndex(): Promise<IndexPayload> {
  if ((await detectMode()) === 'api') return getJSON<IndexPayload>('api/index')
  return getJSON<IndexPayload>('d/index.json')
}

export async function getBook(pid: string, bid: string): Promise<BookPayload> {
  if ((await detectMode()) === 'api') return getJSON<BookPayload>(`api/book/${pid}/${bid}`)
  return getJSON<BookPayload>(`d/${pid}/${bid}/toc.json`)
}

export async function getArticle(pid: string, bid: string, slug: string): Promise<ArticlePayload> {
  const path = slug.split('/').map(encodeURIComponent).join('/')
  if ((await detectMode()) === 'api') return getJSON<ArticlePayload>(`api/article/${pid}/${bid}/${path}`)
  return getJSON<ArticlePayload>(`d/${pid}/${bid}/${path}.json`)
}

export async function searchAll(q: string, pid = ''): Promise<SearchHit[]> {
  const query = q.trim()
  if (!query) return []
  if ((await detectMode()) === 'api') {
    const r = await getJSON<{ items: SearchHit[] }>(
      `api/search?q=${encodeURIComponent(query)}&pid=${encodeURIComponent(pid)}`)
    return r.items
  }
  // 离线静态模式：本地过滤预构建索引
  if (!staticSearchIndex) {
    staticSearchIndex = await getJSON<StaticSearchItem[]>('d/search.json')
  }
  const t = query.toLowerCase()
  return staticSearchIndex
    .filter((a) => (!pid || a.pid === pid) && (a.t + ' ' + a.x).toLowerCase().includes(t))
    .slice(0, 60)
    .map((a) => {
      const low = a.x.toLowerCase()
      const i = low.indexOf(t)
      const win = i < 0 ? a.x.slice(0, 90) : a.x.slice(Math.max(0, i - 24), i + 90)
      const re = new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
      const marked = esc(win).replace(re, (m) => `<mark>${m}</mark>`)
      return { pid: a.pid, bid: a.bid, slug: a.slug, title: a.t, snip: marked }
    })
}

export function hitUrl(hit: SearchHit): string {
  return readUrl(hit.pid, hit.bid, hit.slug)
}
