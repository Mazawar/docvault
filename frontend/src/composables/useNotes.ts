/** 笔记模块共享状态与动作（单例）：写作 / 内容管理 / 壳层共用同一份。 */
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  backlinks, createFolder, createNote, daily, deleteFolder, deleteNote, noteContent,
  noteRendered, notesIndex, renameFolder, renameNote, saveNote, uploadAttachment,
  uploadImage, type NoteItem, type NotesIndex
} from '@/api/notes'
import { isStatic } from '@/api/http'
import { adminApi } from '@/api/admin'

export type NotesMode = 'write' | 'manage'

const mode = ref<NotesMode>('manage')
const idx = ref<NotesIndex | null>(null)
const activeFolder = ref('')
const activeNote = ref<NoteItem | null>(null)
const titleInput = ref('')
const tags = ref<string[]>([])
const content = ref('')
const dirty = ref(false)
const saving = ref(false)
const backlinksList = ref<{ folder: string; name: string; title: string }[]>([])
const showBacklinks = ref(false)
const draftSavedAt = ref('')
const previewFallback = ref('')

/* 内容管理筛选 */
const qFilter = ref('')
const tagFilter = ref('')
const folderFilter = ref('')

/* 笔记本管理弹窗 */
const nbOpen = ref(false)
const newNbName = ref('')

export function setMode(m: NotesMode) {
  mode.value = m
}

/* ---------------- 派生列表 ---------------- */
const folders = computed(() => idx.value?.folders || [])

const manageRows = computed(() => {
  let rows: { folder: string; note: NoteItem }[] = []
  for (const f of folders.value) {
    if (folderFilter.value && f.folder !== folderFilter.value) continue
    for (const n of f.notes) rows.push({ folder: f.folder, note: n })
  }
  const t = tagFilter.value
  if (t) rows = rows.filter((r) => r.note.tags?.includes(t))
  const q = qFilter.value.trim().toLowerCase()
  if (q) rows = rows.filter((r) => (r.note.title + r.note.name).toLowerCase().includes(q))
  return rows.sort((a, b) => b.note.ts - a.note.ts)
})

const allTags = computed(() => {
  const s = new Set<string>()
  for (const f of folders.value) for (const n of f.notes) for (const t of n.tags || []) s.add(t)
  return [...s]
})

const folderNotes = computed(
  () => folders.value.find((f) => f.folder === activeFolder.value)?.notes || [])

const draftKey = computed(() => `dvDraft:${activeFolder.value}/${activeNote.value?.name || ''}`)

/* ---------------- 刷新与打开 ---------------- */
async function refresh(selectFolder?: string) {
  idx.value = await notesIndex()
  if (!folders.value.length && !isStatic()) {
    await createFolder('我的笔记')
    idx.value = await notesIndex()
  }
  activeFolder.value = selectFolder
    || (folders.value.some((f) => f.folder === activeFolder.value)
      ? activeFolder.value
      : folders.value[0]?.folder || '')
}

function firstH1(body: string): string {
  for (const line of body.split('\n')) if (line.startsWith('# ')) return line.slice(2).trim()
  return ''
}

async function pickNote(folder: string, name: string) {
  if (dirty.value && !confirm('有未发布的修改，确定离开？')) return
  dirty.value = false
  showBacklinks.value = false
  draftSavedAt.value = ''
  activeFolder.value = folder
  const item = folders.value.find((f) => f.folder === folder)?.notes.find((x) => x.name === name)
  activeNote.value = item || null
  mode.value = 'write'
  if (!item) return
  if (!isStatic()) {
    const r = await noteContent(folder, name)
    let title = r.fm_title || firstH1(r.content) || r.title
    let body = r.content
    // 正文首行 h1 与标题相同时提升到标题栏，避免重复
    if (!r.fm_title && body.startsWith('# ')) {
      const nl = body.indexOf('\n')
      const h1 = body.slice(2, nl < 0 ? undefined : nl).trim()
      body = nl < 0 ? '' : body.slice(nl + 1).replace(/^\s+/, '')
      title = h1 || title
    }
    titleInput.value = title
    tags.value = r.tags || []
    content.value = body
    const raw = localStorage.getItem(draftKey.value)
    if (raw) {
      try {
        const d = JSON.parse(raw)
        if (d && d.ts > item.ts && (d.content !== body || (d.title || '') !== title)) {
          ElMessageBox.confirm('检测到本地草稿（比线上更新），是否恢复？', '草稿恢复',
            { confirmButtonText: '恢复', cancelButtonText: '丢弃', type: 'warning' })
            .then(() => {
              titleInput.value = d.title || titleInput.value
              tags.value = d.tags || tags.value
              content.value = d.content || ''
              dirty.value = true
            })
            .catch(() => localStorage.removeItem(draftKey.value))
        }
      } catch { /* ignore */ }
    }
  } else {
    titleInput.value = item.title
    tags.value = item.tags || []
    content.value = ''
    previewFallback.value = (await noteRendered(folder, name)).html
  }
}

function refreshNoteMeta() {
  const f = folders.value.find((x) => x.folder === activeFolder.value)
  const n = f?.notes.find((x) => x.name === activeNote.value?.name)
  if (n) activeNote.value = n
}

/* ---------------- 草稿与自动发布 ---------------- */
let draftTimer: number | null = null
watch([content, titleInput, tags], () => {
  if (!activeNote.value) return
  dirty.value = true
  if (isStatic()) return
  try {
    localStorage.setItem(draftKey.value, JSON.stringify({
      title: titleInput.value, tags: tags.value, content: content.value, ts: Date.now()
    }))
    draftSavedAt.value = new Date().toLocaleTimeString()
  } catch { /* ignore */ }
  if (draftTimer) window.clearTimeout(draftTimer)
  draftTimer = window.setTimeout(() => {
    if (!dirty.value || !activeNote.value) return
    saveNote(activeFolder.value, activeNote.value.name, content.value, tags.value,
      titleInput.value.trim()).then(() => {
      dirty.value = false
      localStorage.removeItem(draftKey.value)
      refreshNoteMeta()
    }).catch(() => {})
  }, 3000)
})

/* ---------------- 发布 ---------------- */
async function doSave(silent = false) {
  if (!activeNote.value) return
  if (!titleInput.value.trim()) return ElMessage.warning('请输入标题')
  saving.value = true
  try {
    await saveNote(activeFolder.value, activeNote.value.name, content.value, tags.value,
      titleInput.value.trim())
    dirty.value = false
    localStorage.removeItem(draftKey.value)
    if (!silent) ElMessage.success('已发布')
    await refresh(activeFolder.value)
    refreshNoteMeta()
    if (showBacklinks.value) {
      backlinksList.value = await backlinks(activeFolder.value, activeNote.value.name)
    }
  } finally {
    saving.value = false
  }
}
function onEditorSave() { doSave() }
function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); doSave() }
}

/* ---------------- 编辑器钩子（由写作组件回调） ---------------- */
async function onUploadImg(files: File[], callback: (urls: string[]) => void) {
  const urls: string[] = []
  for (const f of files) {
    try {
      urls.push(f.type.startsWith('image/')
        ? (await uploadImage(f)).url
        : (await uploadAttachment(f)).url)
    } catch (e) {
      ElMessage.error((e as Error).message || '上传失败')
    }
  }
  callback(urls)
}

/* ---------------- 管理动作 ---------------- */
function newNote() {
  if (!activeFolder.value) return ElMessage.warning('先选择笔记本')
  ElMessageBox.prompt('笔记文件名（不含 .md）', '新建笔记', { confirmButtonText: '创建' })
    .then(async ({ value }) => {
      if (!value?.trim()) return
      await createNote(activeFolder.value, value.trim())
      await refresh(activeFolder.value)
      await pickNote(activeFolder.value, value.trim())
      titleInput.value = value.trim()
    }).catch(() => {})
}
function renameNote2(row?: { folder: string; note: NoteItem }) {
  const folder = row?.folder || activeFolder.value
  const name = row?.note.name || activeNote.value?.name
  if (!name) return
  ElMessageBox.prompt('新文件名（不含 .md）', '重命名', { inputValue: name })
    .then(async ({ value }) => {
      if (!value?.trim()) return
      await renameNote(folder, name, value.trim())
      dirty.value = false
      await refresh(folder)
      ElMessage.success('已重命名')
    }).catch(() => {})
}
function delNote(row?: { folder: string; note: NoteItem }) {
  const folder = row?.folder || activeFolder.value
  const name = row?.note.name || activeNote.value?.name
  const title = row?.note.title || activeNote.value?.title || name
  if (!name) return
  ElMessageBox.confirm(`删除「${title}」？不可恢复`, '删除笔记', { type: 'warning' })
    .then(async () => {
      await deleteNote(folder, name)
      if (activeNote.value?.name === name) { activeNote.value = null; content.value = '' }
      await refresh(folder)
    }).catch(() => {})
}
async function renameNb(f: string) {
  const r = await ElMessageBox.prompt('新的笔记本名称', `重命名「${f}」`, {
    inputValue: f, confirmButtonText: '重命名', cancelButtonText: '取消'
  }).catch(() => null)
  const nn = (r?.value || '').trim()
  if (!nn || nn === f) return
  await renameFolder(f, nn)
  ElMessage.success('已重命名')
  folderFilter.value = folderFilter.value === f ? nn : folderFilter.value
  await refresh(activeFolder.value === f ? nn : undefined)
}
async function deleteNb(f: string) {
  const cnt = folders.value.find((x) => x.folder === f)?.notes.length ?? 0
  const msg = cnt
    ? `笔记本「${f}」里还有 ${cnt} 篇笔记，将一并删除且不可恢复，确定？`
    : `删除空笔记本「${f}」？`
  const ok = await ElMessageBox.confirm(msg, '删除笔记本', {
    type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消'
  }).then(() => true).catch(() => false)
  if (!ok) return
  await deleteFolder(f, cnt > 0)
  ElMessage.success('已删除')
  folderFilter.value = folderFilter.value === f ? '' : folderFilter.value
  if (activeFolder.value === f) activeFolder.value = ''
  await refresh('')
}
async function createNb() {
  const name = newNbName.value.trim()
  if (!name) return ElMessage.warning('请输入笔记本名称')
  await createFolder(name)
  newNbName.value = ''
  ElMessage.success('已创建')
  await refresh(name)
}
function editTags() {
  ElMessageBox.prompt('标签（英文逗号分隔）', '编辑标签', { inputValue: tags.value.join(',') })
    .then(async ({ value }) => {
      tags.value = (value || '').split(/[,，]/).map((x) => x.trim()).filter(Boolean)
      await doSave(true)
    }).catch(() => {})
}
function removeTag(t: string) {
  tags.value = tags.value.filter((x) => x !== t)
  dirty.value = true
  doSave(true)
}
async function toggleBacklinks() {
  if (!activeNote.value) return
  if (!showBacklinks.value) {
    backlinksList.value = await backlinks(activeFolder.value, activeNote.value.name)
  }
  showBacklinks.value = !showBacklinks.value
}
async function doDaily() {
  const r = await daily()
  await refresh(r.folder)
  await pickNote(r.folder, r.name)
  ElMessage.success('今日笔记已就绪')
}
async function doPdf(kind: 'note' | 'notebook') {
  if (kind === 'note' && !activeNote.value) return
  await adminApi.exportNotePdf(activeFolder.value,
    kind === 'note' ? activeNote.value!.name : '')
  ElMessage.success('已提交 PDF 导出，进度见资源管理 · 任务队列')
}

export function useNotes() {
  return {
    mode, idx, folders, activeFolder, activeNote,
    titleInput, tags, content, dirty, saving,
    previewFallback, backlinksList, showBacklinks, draftSavedAt,
    qFilter, tagFilter, folderFilter, nbOpen, newNbName,
    manageRows, allTags, folderNotes, draftKey,
    refresh, pickNote, refreshNoteMeta, doSave, onEditorSave, onUploadImg,
    newNote, renameNote2, delNote, renameNb, deleteNb, createNb,
    editTags, removeTag, toggleBacklinks, doDaily, doPdf, setMode,
  }
}
