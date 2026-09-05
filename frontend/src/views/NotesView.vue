<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Setting } from '@element-plus/icons-vue'
import { MdEditor, MdPreview } from 'md-editor-v3'
import type { ExposeParam, ToolbarNames } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import {
  backlinks, createFolder, createNote, daily, deleteFolder, deleteNote, noteContent, noteRendered,
  notesIndex, renameFolder, renameNote, saveNote, uploadAttachment, uploadImage,
  type NoteItem, type NotesIndex
} from '@/api/notes'
import { isStatic } from '@/api/http'
import { adminApi } from '@/api/admin'
import { useThemeStore } from '@/stores/theme'

const route = useRoute()
const router = useRouter()
const theme = useThemeStore()

type Mode = 'write' | 'manage'
type ViewKind = 'edit' | 'preview'
const mode = ref<Mode>('manage')
const view = ref<ViewKind>('edit')

const idx = ref<NotesIndex | null>(null)
const activeFolder = ref('')
const activeNote = ref<NoteItem | null>(null)
const titleInput = ref('')
const tags = ref<string[]>([])
const content = ref('')
const dirty = ref(false)
const saving = ref(false)
const editorRef = ref<ExposeParam | null>(null)
const backlinksList = ref<{ folder: string; name: string; title: string }[]>([])
const showBacklinks = ref(false)
const draftSavedAt = ref('')

/* ---------------- 列表与管理 ---------------- */
const qFilter = ref('')
const tagFilter = ref('')
const folderFilter = ref('')

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

/* ---------------- 打开笔记 ---------------- */
function firstH1(body: string): string {
  for (const line of body.split('\n')) if (line.startsWith('# ')) return line.slice(2).trim()
  return ''
}

const draftKey = computed(() => `dvDraft:${activeFolder.value}/${activeNote.value?.name || ''}`)

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
const previewFallback = ref('')

let draftTimer: number | null = null
let timer: number | null = null
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
  if (timer) window.clearTimeout(timer)
  timer.value = window.setTimeout(() => {
    if (!dirty.value) return
    saveNote(activeFolder.value, activeNote.value.name, content.value, tags.value,
      titleInput.value.trim()).then(() => {
      dirty.value = false
      localStorage.removeItem(draftKey.value)
      refreshNoteMeta()
    }).catch(() => {})
  }, 3000)
})
function refreshNoteMeta() {
  const f = folders.value.find((x) => x.folder === activeFolder.value)
  const n = f?.notes.find((x) => x.name === activeNote.value?.name)
  if (n) activeNote.value = n
}

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

/* md-editor 在部分环境挂载时会误入 previewOnly，这里兜底切回 */
function guardPreviewOnly() {
  setTimeout(() => {
    const ed = document.querySelector('.md-editor')
    if (ed?.classList.contains('md-editor-previewOnly')) {
      ;(editorRef.value as unknown as { togglePreviewOnly?: (v?: boolean) => void })
        ?.togglePreviewOnly?.(false)
      ed.classList.remove('md-editor-previewOnly')
    }
  }, 500)
}

/* ---------------- 编辑器配置 ---------------- */
const editorTheme = computed(() => (theme.dark ? 'dark' : 'light'))
const toolbars: ToolbarNames[] = [
  'bold', 'italic', 'strikeThrough', '-', 'title', 'quote', 'unorderedList', 'orderedList',
  'task', '-', 'codeRow', 'code', 'link', 'image', 'table', '-', 'revoke', 'next', 'save',
  '=', 'catalog', 'pageFullscreen'
]
async function onUploadImg(files: File[], callback: (urls: string[]) => void) {
  const urls: string[] = []
  for (const f of files) {
    try {
      urls.push(f.type.startsWith('image/') ? (await uploadImage(f)).url : (await uploadAttachment(f)).url)
    } catch (e) {
      ElMessage.error((e as Error).message || '上传失败')
    }
  }
  callback(urls)
}

/* ---------------- 插入/管理动作 ---------------- */
function insertText(text: string) {
  editorRef.value?.insert((selected) => ({
    targetValue: selected ? text.replace('$t', selected) : text,
    select: false, deviationStart: 0, deviationEnd: 0
  }))
}
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
const nbOpen = ref(false)
const newNbName = ref('')

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
async function openFromQuery() {
  const f = String(route.query.folder || '')
  const n = String(route.query.name || '')
  if (f && n) await pickNote(f, n)
}
function goWrite(folder?: string, name?: string) {
  if (folder && name) return pickNote(folder, name)
  mode.value = 'write'
  if (folder) activeFolder.value = folder
}
function fmtSize(n: number) { return n < 1024 ? `${n}B` : `${(n / 1024).toFixed(1)}K` }

onMounted(async () => {
  theme.init()
  await refresh()
  if (folders.value.length) activeFolder.value = folders.value[0].folder
  await openFromQuery()
  window.addEventListener('keydown', onKeydown)
  guardPreviewOnly()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div>
    <!-- 顶栏 -->
    <div class="px-5 pt-4">
      <div class="flex flex-wrap items-center gap-3">
        <nav class="flex items-center gap-0.5 rounded-lg bg-[var(--bg-soft)] p-1 text-[13.5px]">
          <button
            class="rounded-md px-3.5 py-1 transition-colors"
            :class="mode === 'write' ? 'bg-[var(--bg)] font-semibold text-[var(--text-1)] shadow-sm' : 'text-[var(--text-2)] hover:text-[var(--text-1)]'"
            @click="mode = 'write'"
          >写作</button>
          <button
            class="rounded-md px-3.5 py-1 transition-colors"
            :class="mode === 'manage' ? 'bg-[var(--bg)] font-semibold text-[var(--text-1)] shadow-sm' : 'text-[var(--text-2)] hover:text-[var(--text-1)]'"
            @click="mode = 'manage'"
          >内容管理</button>
        </nav>
        <span class="flex-1" />
        <el-select
          v-model="activeFolder" size="small" class="!w-40" placeholder="笔记本"
        >
          <el-option v-for="f in folders" :key="f.folder" :value="f.folder" :label="f.folder" />
        </el-select>
        <template v-if="!isStatic()">
          <el-button size="small" @click="doDaily">今日笔记</el-button>
          <el-tooltip content="笔记本管理" placement="left">
            <button class="nbset" @click="nbOpen = true">
              <el-icon><Setting /></el-icon>
            </button>
          </el-tooltip>
        </template>
      </div>
    </div>

    <!-- 笔记本管理弹窗 -->
    <el-dialog v-model="nbOpen" title="笔记本管理" width="440">
      <div v-for="f in folders" :key="f.folder" class="nbrow">
        <span class="truncate">{{ f.folder }}</span>
        <span class="flex-1" />
        <span class="nbmut">{{ f.notes.length }} 篇</span>
        <el-button size="small" text @click="renameNb(f.folder)">重命名</el-button>
        <el-button size="small" text type="danger" @click="deleteNb(f.folder)">删除</el-button>
      </div>
      <div v-if="!folders.length" class="py-6 text-center text-[13px] text-[var(--text-3)]">还没有笔记本</div>
      <div class="mt-3 flex gap-2">
        <el-input v-model="newNbName" size="small" placeholder="新笔记本名称" @keydown.enter="createNb" />
        <el-button size="small" type="primary" @click="createNb">新建</el-button>
      </div>
    </el-dialog>

    <!-- ================= 写作 ================= -->
    <div v-if="mode === 'write'">
      <div v-if="!activeNote" class="mx-auto max-w-md px-6 py-20 text-center">
        <p class="mb-5 text-[15px] text-[var(--text-3)]">
          从「内容管理」选择一篇笔记开始编辑，或新建一篇
        </p>
        <el-button type="primary" @click="mode = 'manage'">打开内容管理</el-button>
      </div>
      <template v-else>
        <!-- 标题 -->
        <input
          v-model="titleInput"
          class="w-full border-none bg-transparent px-6 pb-1 pt-5 text-[30px] font-bold tracking-tight text-[var(--text-1)] outline-none placeholder:text-[var(--text-3)]"
          placeholder="请输入标题…"
          @keydown.enter="($event.target as HTMLInputElement).blur()"
        />
        <!-- 标签 -->
        <div class="flex flex-wrap items-center gap-1.5 px-6 pb-3">
          <span
            v-for="t in tags" :key="t"
            class="group flex items-center gap-1 rounded-md bg-[var(--brand-soft)] px-2 py-0.5 text-[12px] text-[var(--brand)]"
          >
            #{{ t }}
            <span v-if="!isStatic()" class="cursor-pointer opacity-50 hover:opacity-100" @click="removeTag(t)">×</span>
          </span>
          <button
            v-if="!isStatic()"
            class="rounded-md border border-dashed border-[var(--divider)] px-2 py-0.5 text-[12px] text-[var(--text-3)] transition-colors hover:border-[var(--brand)] hover:text-[var(--brand)]"
            @click="editTags"
          >+ 标签</button>
        </div>
        <!-- 反链 -->
        <div v-if="showBacklinks" class="mx-6 mb-2 rounded-lg bg-[var(--bg-soft)] px-4 py-2.5 text-[12.5px]">
          <span class="mr-2 text-[var(--text-3)]">反向链接（{{ backlinksList.length }}）：</span>
          <a
            v-for="b in backlinksList" :key="b.folder + b.name"
            class="mr-3 cursor-pointer text-[var(--brand)]"
            @click="pickNote(b.folder, b.name)"
          >{{ b.title }}</a>
          <span v-if="!backlinksList.length" class="text-[var(--text-3)]">暂无</span>
        </div>
        <!-- 编辑器 -->
        <div class="px-5">
          <MdPreview
            v-if="isStatic()"
            :model-value="previewFallback"
            preview-theme="vuepress"
            code-theme="github"
            :theme="editorTheme"
            class="dv-editor dv-preview"
          />
          <MdEditor
            v-else
            ref="editorRef"
            v-model="content"
            class="dv-editor"
            :theme="editorTheme"
            preview-theme="vuepress"
            code-theme="github"
            placeholder="从此刻开始写点什么…"
            :preview-only="false"
            :toolbars="toolbars as ToolbarNames[]"
            :footers="['markdownTotal', '=', 'scrollSwitch']"
            :auto-focus="false"
            no-katex
            no-mermaid
            @on-save="onEditorSave"
            @on-upload-img="onUploadImg as any"
          />
        </div>
        <!-- 状态栏 -->
        <div class="flex flex-wrap items-center gap-4 px-6 py-2.5 text-[12.5px] text-[var(--text-3)]">
          <span v-if="dirty" class="font-medium text-[#d97706]">有未发布的内容</span>
          <span v-else-if="draftSavedAt">草稿已本地留存 {{ draftSavedAt }}</span>
          <span v-else>已发布</span>
          <span>更新于 {{ activeNote.updated }}</span>
          <span class="flex-1" />
          <a v-if="showBacklinks" class="cursor-pointer text-[var(--brand)]" @click="toggleBacklinks">收起反链</a>
          <a v-else class="cursor-pointer text-[var(--brand)]" @click="toggleBacklinks">反向链接</a>
          <a class="cursor-pointer text-[var(--brand)]" @click="doPdf('note')">导出本文 PDF</a>
          <a class="cursor-pointer text-[var(--brand)]" @click="doPdf('notebook')">导出笔记本</a>
          <a v-if="!isStatic()" class="cursor-pointer text-[var(--brand)]" @click="newNote">新建</a>
          <a class="cursor-pointer text-[var(--brand)]" @click="renameNote2()">重命名</a>
          <a class="cursor-pointer text-[var(--brand)]" @click="delNote()">删除</a>
        </div>
      </template>
    </div>

    <!-- ================= 内容管理 ================= -->
    <div v-else class="mx-auto max-w-5xl px-6 pb-16 pt-2">
      <div class="mb-4 flex flex-wrap items-center gap-2.5">
        <input
          v-model="qFilter"
          placeholder="搜索标题 / 文件名…"
          class="w-60 rounded-lg border border-[var(--divider)] bg-[var(--bg)] px-3.5 py-2 text-[13.5px] outline-none focus:border-[var(--brand)]"
        />
        <select
          v-model="folderFilter"
          class="rounded-lg border border-[var(--divider)] bg-[var(--bg)] px-2.5 py-2 text-[13px] text-[var(--text-1)]"
        >
          <option value="">全部笔记本</option>
          <option v-for="f in folders" :key="f.folder" :value="f.folder">{{ f.folder }}</option>
        </select>
        <select
          v-model="tagFilter"
          class="rounded-lg border border-[var(--divider)] bg-[var(--bg)] px-2.5 py-2 text-[13px] text-[var(--text-1)]"
        >
          <option value="">全部标签</option>
          <option v-for="t in allTags" :key="t" :value="t">#{{ t }}</option>
        </select>
        <span class="flex-1" />
        <span class="text-[12.5px] text-[var(--text-3)]">共 {{ manageRows.length }} 篇</span>
      </div>

      <!-- 文章行（内容管理样式） -->
      <div>
        <div
          v-for="r in manageRows" :key="r.folder + '/' + r.note.name"
          class="group flex items-start gap-4 border-b border-[var(--divider)] px-1 py-4 transition-colors hover:bg-[var(--bg-soft)]"
        >
          <div class="min-w-0 flex-1 cursor-pointer" @click="pickNote(r.folder, r.note.name)">
            <div class="truncate text-[15.5px] font-semibold text-[var(--text-1)] group-hover:text-[var(--brand)]">
              {{ r.note.title }}
            </div>
            <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-[var(--text-3)]">
              <span>{{ r.folder }}</span>
              <span v-for="t in r.note.tags" :key="t" class="text-[var(--brand)]">#{{ t }}</span>
              <span>编辑于 {{ r.note.updated }}</span>
              <span>{{ fmtSize(r.note.size) }}</span>
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-1 pt-1">
            <el-button size="small" text type="primary" :icon="Edit" @click="pickNote(r.folder, r.note.name)">编辑</el-button>
            <el-button size="small" text @click="renameNote2(r)">重命名</el-button>
            <el-button size="small" text type="danger" :icon="Delete" @click="delNote(r)">删除</el-button>
          </div>
        </div>
        <div v-if="!manageRows.length" class="py-16 text-center text-sm text-[var(--text-3)]">
          没有匹配的笔记
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.nbset {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--divider);
  background: var(--bg);
  color: var(--text-2);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: 0.15s;
}
.nbset:hover {
  color: var(--brand);
  border-color: var(--brand);
}
.nbrow {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 2px;
  border-bottom: 1px dashed var(--divider);
  font-size: 13.5px;
  color: var(--text-1);
}
.nbmut {
  font-size: 12px;
  color: var(--text-3);
}
.dv-editor {
  height: calc(100vh - 220px - var(--nav-h));
  border-radius: 10px;
  border-color: var(--divider);
}
:deep(.md-editor-preview-wrapper) { padding: 0 12px; }
:deep(.md-editor-footer-item) { font-size: 12px; }
:deep(.wikilink) {
  color: var(--brand);
  border-bottom: 1px dashed var(--brand);
  cursor: pointer;
}
:deep(.wikilink.missing) {
  color: var(--text-3);
  border-bottom: 1px dashed var(--text-3);
}
</style>
