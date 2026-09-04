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
  jobs: () => getJSON<{ jobs: Job[] }>('api/jobs').then((r) => r.jobs),

  sync: (pid = '') => postJSON<{ ok: boolean }>('api/admin/sync', { pid }),
  exportZip: () => postJSON<{ ok: boolean }>('api/admin/export'),
  exportPdf: (pid: string, bid: string) => postJSON<{ ok: boolean }>('api/admin/pdf', { pid, bid }),

  saveProject: (p: {
    id: string
    name: string
    type: string
    repo: string
    root: string
    books: Record<string, string>
  }) => postJSON<{ ok: boolean }>('api/admin/projects', p),
  deleteProject: (pid: string) => del<{ ok: boolean }>(`api/admin/projects/${pid}`),
  listProjects: () => getJSON<ProjectFull[]>('api/admin/projects'),

  upload: async (pid: string, files: File[]): Promise<{ ok: boolean; saved: string[] }> => {
    const fd = new FormData()
    fd.append('pid', pid)
    for (const f of files) fd.append('files', f)
    const r = await fetch('api/admin/upload', { method: 'POST', body: fd })
    const data = (await r.json()) as { ok: boolean; saved: string[]; error?: string }
    if (!r.ok) throw new Error(data.error || '上传失败')
    return data
  },

  getNote: (pid: string, name: string) =>
    getJSON<{ name: string; content: string }>(
      `api/admin/note?pid=${encodeURIComponent(pid)}&name=${encodeURIComponent(name)}`),
  saveNote: (pid: string, name: string, content: string) =>
    postJSON<{ ok: boolean; name: string }>('api/admin/note', { pid, name, content }),

  downloadUrl: 'api/admin/download'
}
