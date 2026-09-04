/** 与后端 API 契约对应的类型定义 */

export interface BookBrief {
  id: string
  title: string
  n: number
}

export interface ProjectBrief {
  id: string
  name: string
  type: 'github' | 'upload'
  updated: string
  books: BookBrief[]
  files: string[]
}

export interface IndexPayload {
  projects: ProjectBrief[]
}

export interface ArticleItem {
  slug: string
  title: string
}

export interface BookPayload {
  pid: string
  bid: string
  title: string
  n: number
  pname: string
  updated: string
  gt?: Record<string, string>
  articles: ArticleItem[]
}

export interface ArticlePayload {
  pid: string
  bid: string
  slug: string
  title: string
  html: string
  prev: ArticleItem | null
  next: ArticleItem | null
  updated: string
  source: string
  pname: string
  btitle: string
}

export interface SearchHit {
  pid: string
  bid: string
  slug: string
  title: string
  snip: string
}

export interface ProjectFull {
  id: string
  name: string
  type: 'github' | 'upload'
  repo: string
  root: string
  group_titles?: Record<string, Record<string, string>>
  books: Record<string, string>
  sort: number
  updated: string
}

export interface ProjectRow {
  id: string
  name: string
  type: 'github' | 'upload'
  repo: string
  root: string
  updated: string
  books: BookBrief[]
}

export interface NoteItem {
  pid: string
  name: string
  size: number
}

export interface Job {
  id: number
  name: string
  status: 'queued' | 'running' | 'done' | 'error'
  log: string[]
  created: string
  finished: string
}

export interface Overview {
  projects: ProjectRow[]
  pdfs: string[]
  zip: string | null
  zipSize: number
  pack?: string | null
  packSize?: number
  notes: NoteItem[]
  jobs: Job[]
}
