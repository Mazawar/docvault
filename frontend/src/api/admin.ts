/** 管理侧 API（仅联机模式可用；离线包里管理台不可用） */
import { getJSON, postJSON } from './http'
import type { Job, Overview, ProjectFull } from './types'

async function del<T>(url: string): Promise<T> {
  const r = await fetch(url, { method: 'DELETE' })
  const data = (await r.json()) as T & { error?: string }
  if (!r.ok) throw new Error(data.error || `请求失败 ${r.status}`)
  return data
}

export const adminApi = {
  overview: () => getJSON<Overview>('api/admin/overview'),

  sync: (pid = '') => postJSON<{ ok: boolean }>('api/admin/sync', { pid }),
  exportZip: () => postJSON<{ ok: boolean }>('api/admin/export'),
  exportPack: (pid = '') => postJSON<{ ok: boolean }>('api/admin/export-pack', { pid }),
  projectPackUrl: (pid: string) => `api/admin/export-project-pack?pid=${encodeURIComponent(pid)}`,
  importPack: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return fetch('api/admin/import-pack', { method: 'POST', body: fd }).then(async (r) => {
      const data = (await r.json()) as { ok?: boolean; error?: string }
      if (!r.ok) throw new Error(data.error || `请求失败 ${r.status}`)
      return data
    })
  },
  storage: () => getJSON<{    projects: { id: string; name: string; type: string; repos_mb: number; articles: number }[]
    assets: { mb: number; files: number }
    repos_mb: number; db_mb: number; notes_mb: number; uploads_mb: number; dist_mb: number
  }>('api/admin/storage'),
  purgeRepos: (pid: string) => postJSON<{ ok: boolean }>('api/admin/purge-repos', { pid }),
  purgeOrphanAssets: () => postJSON<{ ok: boolean }>('api/admin/purge-orphan-assets'),
  exportNotePdf: (folder: string, name: string) =>
    postJSON<{ ok: boolean }>('api/admin/pdf-note', { folder, name }),

  saveProject: (p: {
    id: string
    name: string
    type: string
    repo: string
    root: string
    books: Record<string, string>
    groupTitles: Record<string, Record<string, string>>
  }) => postJSON<{ ok: boolean }>('api/admin/projects', p),
  deleteProject: (pid: string) => del<{ ok: boolean }>(`api/admin/projects/${pid}`),
  listProjects: () => getJSON<ProjectFull[]>('api/admin/projects'),

  downloadUrl: 'api/admin/download',
  downloadPackUrl: 'api/admin/download-pack'
}
