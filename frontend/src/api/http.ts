/**
 * 数据源双模式适配层：
 *  - api    联机模式，FastAPI 服务（exe / python -m src.main serve）
 *  - static 离线包模式，纯静态 JSON（site/d/*.json，任意静态服务器）
 * 启动时探测 /api/status，失败即认为运行在离线静态包里。
 */
import { ref } from 'vue'
import type { IndexPayload } from './types'

export type SourceMode = 'api' | 'static'

/** 响应式模式状态：模板中经 isStatic() 读取，探测完成后自动刷新界面 */
export const modeRef = ref<SourceMode | null>(null)

let mode: SourceMode | null = null

export async function detectMode(): Promise<SourceMode> {
  if (mode) return mode
  try {
    const r = await fetch('api/status')
    mode = r.ok ? 'api' : 'static'
  } catch {
    mode = 'static'
  }
  modeRef.value = mode
  return mode
}

export function isStatic(): boolean {
  return modeRef.value === 'static'
}

export async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`请求失败 ${r.status}: ${url}`)
  return (await r.json()) as T
}

export async function postJSON<T>(url: string, body?: unknown): Promise<T> {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? '{}' : JSON.stringify(body)
  })
  const data = (await r.json()) as T & { error?: string }
  if (!r.ok) throw new Error((data as { error?: string; detail?: string }).error
    || (data as { detail?: string }).detail || `请求失败 ${r.status}`)
  return data
}

/** 阅读路由（hash 模式，静态包同样可用） */
export function readUrl(pid: string, bid: string, slug: string): string {
  return `#/read/${pid}/${bid}/${slug}`
}

export type { IndexPayload }
