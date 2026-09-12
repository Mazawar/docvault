/**
 * 资源管理共享状态与动作（单例）。
 * AdminView 与各子组件共用同一份 ov/st/busy，动作统一走这里。
 */
import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'
import { modeRef } from '@/api/http'
import type { Overview } from '@/api/types'

export const staticMode = computed(() => modeRef.value === 'static')

const ov = ref<Overview | null>(null)
const st = ref<Awaited<ReturnType<typeof adminApi.storage>> | null>(null)
const busy = reactive<Record<string, boolean>>({})
let pollTimer: number | null = null
let polling = false
const knownJobs = new Map<number, string>()
export const jobTitle = (name: string) =>
  name.startsWith('sync-') ? `同步 ${name.slice(5)}` : name
const latestJob = (name: string) => (ov.value?.jobs || []).find((j) => j.name === name)
export const jobRunning = (name: string) => latestJob(name)?.status === 'running'

/* ---------- 统计 ---------- */
export const stats = computed(() => {
  const ps = ov.value?.projects || []
  const books = ps.reduce((s, p) => s + p.books.length, 0)
  const articles = ps.reduce((s, p) => s + p.books.reduce((s2, b) => s2 + b.n, 0), 0)
  return { projects: ps.length, books, articles }
})

/* ---------- 刷新与轮询 ---------- */
async function refresh() {
  if (staticMode.value) return
  ov.value = await adminApi.overview()
  const first = knownJobs.size === 0
  for (const j of ov.value.jobs || []) {
    const prev = knownJobs.get(j.id)
    const finished = j.status === 'done' || j.status === 'error'
    const appeared = prev === undefined && !first
    if ((appeared || prev === 'queued' || prev === 'running') && finished) {
      if (j.status === 'done') ElMessage.success(`${jobTitle(j.name)} 完成`)
      else {
        const msg = (j.log.find((l) => l.startsWith('ERROR: ')) || '').replace(/^ERROR: /, '')
        ElMessage.error(`${jobTitle(j.name)} 失败：${msg.slice(0, 160)}`)
      }
    }
    knownJobs.set(j.id, j.status)
  }
  loadStorage()
}

async function loadStorage() {
  if (staticMode.value) return
  st.value = await adminApi.storage().catch(() => null)
}

function startPolling() {
  if (polling) return
  polling = true
  refresh()
  pollTimer = window.setInterval(refresh, 3000)
}
function stopPolling() {
  if (pollTimer) window.clearInterval(pollTimer)
  pollTimer = null
  polling = false
}

/* ---------- 动作基座 ---------- */
async function act(key: string, fn: () => Promise<unknown>, okMsg: string) {
  if (busy[key]) return
  busy[key] = true
  try {
    await fn()
    ElMessage.success(okMsg)
    setTimeout(refresh, 600)
    return true
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    busy[key] = false
  }
}

/* ---------- 同步 ---------- */
const syncAll = () => act('sync-all', () => adminApi.sync(''), '已提交全量同步')
const syncOne = (pid: string) => act(`sync-${pid}`, () => adminApi.sync(pid), `已提交同步：${pid}`)
const syncActive = (pid: string) =>
  !!busy[`sync-${pid}`] || !!busy['sync-all'] || jobRunning(`sync-${pid}`) || jobRunning('sync-all')

/* ---------- 导出 ---------- */
const doExport = () => act('export', () => adminApi.exportZip(), '已提交静态站生成')
const doExportPack = () => act('export-pack', () => adminApi.exportPack(), '已提交资源包生成')
const packBusy = computed(() => !!busy['export-pack'] || jobRunning('生成资源包'))
const zipBusy = computed(() => !!busy.export || jobRunning('生成静态站'))

/* ---------- 清理 ---------- */
const purgeRepos = (pid: string, name: string) =>
  ElMessageBox.confirm(
    `清理「${name}」的仓库缓存？文章与图片保留，阅读不受影响；下次同步会自动重新克隆。`,
    '清理仓库缓存', { confirmButtonText: '清理', type: 'warning' }
  ).then(() => act(`purge-${pid}`, () => adminApi.purgeRepos(pid), '已提交清理，进度见任务队列'))
    .then(loadStorage).catch(() => {})
const purgeOrphan = () =>
  act('purge-orphan', () => adminApi.purgeOrphanAssets(), '已提交清理，进度见任务队列')
    .then(loadStorage)
const purgeDist = () =>
  ElMessageBox.confirm(
    '删除全部导出产物：资源包、离线站包、静态站、PDF、下载临时文件。这些都是可随时重新生成的产物，文章数据（数据库/图床/仓库）不动。',
    '清理导出产物', { confirmButtonText: '清理', type: 'warning' }
  ).then(() => act('purge-dist', () => adminApi.purgeDist(), '已提交清理，进度见任务队列'))
    .then(loadStorage).catch(() => {})

/* ---------- 按项目下载资源包 ---------- */
function downloadPack(pid: string) {
  ElMessage.info('正在打包，完成后浏览器将开始下载…')
  window.location.href = adminApi.projectPackUrl(pid)
}

/* ---------- 格式化 ---------- */
export function fmtSize(n: number): string {
  return n < 1024 ? `${n}B` : n < 1048576 ? `${(n / 1024).toFixed(1)}K` : `${(n / 1048576).toFixed(1)}M`
}

/* ---------- 导出产物描述 ---------- */
export const distDesc = computed(() => {
  if (!st.value) return ''
  const d = st.value.dist
  const parts: string[] = []
  if (d.pack) parts.push(`资源包 ${d.pack.mb}MB`)
  if (d.offline) parts.push(`离线包 ${d.offline.mb}MB`)
  if (d.site_mb) parts.push(`静态站 ${d.site_mb}MB`)
  if (d.pdf_mb) parts.push(`PDF ${d.pdf_mb}MB`)
  if (d.temp.mb) parts.push(`临时 ${d.temp.mb}MB`)
  return parts.join(' · ') || '暂无产物'
})
export const totalMb = computed(() => {
  if (!st.value) return 0
  const s = st.value
  return Math.round(s.assets.mb + s.repos_mb + s.db_mb + s.notes_mb + s.uploads_mb + s.dist.mb)
})

export function useAdmin() {
  return {
    ov, st, busy, staticMode, stats, fmtSize, jobRunning,
    refresh, loadStorage, startPolling, stopPolling, act,
    syncAll, syncOne, syncActive,
    doExport, doExportPack, packBusy, zipBusy,
    purgeRepos, purgeOrphan, purgeDist, downloadPack,
    distDesc, totalMb,
  }
}
