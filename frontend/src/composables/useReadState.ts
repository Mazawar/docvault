/** 阅读记忆：已读集合 + 最近阅读（localStorage，离线模式同样生效） */
import { ref } from 'vue'

const KEY_READ = 'dvRead'
const KEY_RECENT = 'dvRecent'

export interface RecentItem {
  u: string
  t: string
  ts: number
}

function load<T>(key: string, def: T): T {
  try {
    return JSON.parse(localStorage.getItem(key) || '') ?? def
  } catch {
    return def
  }
}

function save(key: string, v: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(v))
  } catch {
    /* ignore */
  }
}

const readMap = ref<Record<string, number>>(load(KEY_READ, {}))
const recent = ref<RecentItem[]>(load(KEY_RECENT, []))

export function useReadState() {
  function isRead(url: string) {
    return !!readMap.value[url]
  }

  function markRead(url: string, title: string) {
    if (readMap.value[url]) return
    readMap.value[url] = Date.now()
    save(KEY_READ, readMap.value)
    recent.value = recent.value.filter((x) => x.u !== url)
    recent.value.unshift({ u: url, t: title, ts: Date.now() })
    recent.value = recent.value.slice(0, 12)
    save(KEY_RECENT, recent.value)
  }

  return { readMap, recent, isRead, markRead }
}
