<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus } from '@element-plus/icons-vue'
import {
  backlinks, createFolder, createNote, daily, deleteNote, noteContent, noteRendered,
  notesIndex, renameNote, renderPreview, saveNote, searchNotes, uploadAttachment,
  uploadImage, type NoteItem, type NotesIndex
} from '@/api/notes'
import { isStatic } from '@/api/http'
import { adminApi } from '@/api/admin'

const route = useRoute()
type Mode = 'write' | 'manage'
const mode = ref<Mode>('write')
const view = ref<'split' | 'edit' | 'preview'>('split')

const idx = ref<NotesIndex | null>(null)
const activeFolder = ref('')
const activeNote = ref<NoteItem | null>(null)
const titleInput = ref('')
const tags = ref<string[]>([])
const content = ref('')
const preview = ref('')
const dirty = ref(false)
const saving = ref(false)
const taEl = ref<HTMLTextAreaElement | null>(null)
const imgInput = ref<HTMLInputElement | null>(null)
const attInput = ref<HTMLInputElement | null>(null)
const backlinksList = ref<{ folder: string; name: string; title: string }[]>([])
const showBacklinks = ref(false)

/* ---------- 管理（内容管理）---------- */
const qFilter = ref('')
const tagFilter = ref('')
const folderFilter = ref('')

const folders = computed(() => idx.value?.folders || [])
const activeNotes = computed(
  () => folders.value.find((f) => f.folder === activeFolder.value)?.notes || [])
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
const wordCount = computed(() => content.value.replace(/\s/g, '').length)

/* ---------- 数据加载 ---------- */
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

function _first_h1(body: string): string {
  for (const line of body.splitlines?.() ?? body.split('\n')) {
    if (line.startsWith('# ')) return line.slice(2).trim()
  }
  return ''
}

async function pickNote(folder: string, name: string) {
  if (dirty.value && !confirm('有未保存的修改，确定离开？')) return
  dirty.value = false
  showBacklinks.value = false
  activeFolder.value = folder
  const item = folders.value.find((f) => f.folder === folder)?.notes.find((x) => x.name === name)
  activeNote.value = item || null
  mode.value = 'write'
  if (!item) return
  const draftKey = `dvDraft:${folder}/${name}`
  if (!isStatic()) {
    const r = await noteContent(folder, name)
    let title = r.fm_title || _first_h1(r.content) || r.title
    let body = r.content
    // 正文首行 h1 与标题重复时，提升为标题栏，正文不再重复显示
    if (!r.fm_title && body.startsWith('# ')) {
      const nl = body.indexOf('\n')
      const h1 = body.slice(2, nl < 0 ? undefined : nl).trim()
      body = nl < 0 ? '' : body.slice(nl + 1).replace(/^\s+/, '')
      title = h1 || title
    }
    titleInput.value = title
    tags.value = r.tags || []
    content.value = body
    const raw = localStorage.getItem(draftKey)
    if (raw) {
      try {
        const d = JSON.parse(raw)
        if (d && d.ts > item.ts && (d.content !== body || (d.title || '') !== title)) {
          ElMessageBox.confirm('检测到本地草稿（比线上更新），是否恢复？', '草稿恢复',
            { confirmButtonText: '恢复草稿', cancelButtonText: '丢弃', type: 'warning' })
            .then(() => {
              titleInput.value = d.title || titleInput.value
              tags.value = d.tags || tags.value
              content.value = d.content || ''
              dirty.value = true
            })
            .then(async () => render())
            .catch(() => localStorage.removeItem(draftKey))
        }
      } catch { /* ignore */ }
    }
    preview.value = (await renderPreview(folder, name, content.value)).html
  } else {
    titleInput.value = item.title
    tags.value = item.tags || []
    content.value = ''
    preview.value = (await noteRendered(folder, name)).html
  }
}

let timer: number | null = null
watch([content, titleInput, tags], () => {
  dirty.value = true
  if (isStatic()) return
  if (timer) window.clearTimeout(timer)
  timer.value = window.setTimeout(async () => {
    if (!activeNote.value) return
    preview.value = (await renderPreview(
      activeFolder.value, activeNote.value.name, content.value)).html
    try {
      localStorage.setItem(
        `dvDraft:${activeFolder.value}/${activeNote.value.name}`,
        JSON.stringify({ title: titleInput.value, tags: tags.value, content: content.value,
          ts: Date.now() }))
      draftSavedAt.value = new Date().toLocaleTimeString()
    } catch { /* ignore */ }
  }, 600)
})
const draftSavedAt = ref('')

/* ---------- 保存 ---------- */
async function doSave() {
  if (!activeNote.value) return
  if (!titleInput.value.trim()) return ElMessage.warning('请输入标题')
  saving.value = true
  try {
    await saveNote(activeFolder.value, activeNote.value.name, content.value, tags.value,
      titleInput.value.trim())
    dirty.value = false
    localStorage.removeItem(`dvDraft:${activeFolder.value}/${activeNote.value.name}`)
    ElMessage.success('已发布')
    await refresh(activeFolder.value)
    const n = folders.value.find((f) => f.folder === activeFolder.value)?.notes
      .find((x) => x.name === activeNote.value?.name)
    if (n) activeNote.value = n
    if (showBacklinks.value) {
      backlinksList.value = await backlinks(activeFolder.value, activeNote.value.name)
    }
  } finally {
    saving.value = false
  }
}

function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); doSave() }
}

/* ---------- 工具栏 ---------- */
function wrapSel(before: string, after = before) {
  const ta = taEl.value
  if (!ta) return
  const s = ta.selectionStart, e = ta.selectionEnd
  const sel = content.value.slice(s, e) || '文本'
  content.value = content.value.slice(0, s) + before + sel + after + content.value.slice(e)
  dirty.value = true
  nextTickFocus(s, before.length + sel.length + after.length)
}
function prefixLine(prefix: string) {
  const ta = taEl.value
  if (!ta) return
  const s = ta.selectionStart
  const ls = content.value.lastIndexOf('\n', s - 1) + 1
  content.value = content.value.slice(0, ls) + prefix + content.value.slice(ls)
  dirty.value = true
  nextTickFocus(ls + prefix.length, 0)
}
function insertBlock(text: string) {
  const ta = taEl.value
  const s = ta?.selectionStart ?? content.value.length
  content.value = content.value.slice(0, s) + '\n' + text + '\n' + content.value.slice(s)
  dirty.value = true
  nextTickFocus(s + text.length + 2, 0)
}
function nextTickFocus(pos: number, selLen: number) {
  queueMicrotask(() => {
    taEl.value?.focus()
    taEl.value?.setSelectionRange(pos, pos + selLen)
  })
}
const tools = {
  bold: () => wrapSel('**'),
  italic: () => wrapSel('*'),
  h2: () => prefixLine('## '),
  h3: () => prefixLine('### '),
  quote: () => prefixLine('> '),
  code: () => insertBlock('```\n\n```'),
  link: () => {
    ElMessageBox.prompt('链接地址', '插入链接', { inputValue: 'https://' })
      .then(({ value }) => wrapSel('[', `](${value || 'https://'})`))
      .catch(() => {})
  },
  table: () => insertBlock('| 列1 | 列2 |\n| --- | --- |\n|  |  |'),
}

async function pickImage(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  const r = await uploadImage(f)
  insertBlock(`![](${r.url})`)
  ;(e.target as HTMLInputElement).value = ''
}
async function pickAtt(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  const r = await uploadAttachment(f)
  insertBlock(`[📎 ${f.name}](${r.url})`)
  ;(e.target as HTMLInputElement).value = ''
}
function onPaste(e: ClipboardEvent) {
  const files = Array.from(e.clipboardData?.files || [])
  if (files.length) { e.preventDefault(); handleFiles(files) }
}
function onDrop(e: DragEvent) {
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length) { e.preventDefault(); handleFiles(files) }
}
async function handleFiles(files: FileList | File[]) {
  for (const f of Array.from(files)) {
    if (f.type.startsWith('image/')) {
      const r = await uploadImage(f)
      insertBlock(`\n![](${r.url})\n`)
    } else {
      const r = await uploadAttachment(f)
      insertBlock(`[📎 ${f.name}](${r.url})`)
    }
  }
  ElMessage.success('已插入')
}

/* ---------- 标签/反链/每日/PDF ---------- */
function editTags() {
  ElMessageBox.prompt('标签（英文逗号分隔）', '编辑标签', { inputValue: tags.value.join(',') })
    .then(async ({ value }) => {
      tags.value = (value || '').split(/[,，]/).map((x) => x.trim()).filter(Boolean)
      await doSave()
    }).catch(() => {})
}
function removeTag(t: string) {
  tags.value = tags.value.filter((x) => x !== t)
  dirty.value = true
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
  ElMessage.success(`已提交${kind === 'note' ? '笔记' : '笔记本'} PDF 导出`)
}

/* ---------- 笔记/笔记本管理动作 ---------- */
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
  if (!name) return
  ElMessageBox.confirm(`删除「${row?.note.title || name}」？不可恢复`, '删除笔记', { type: 'warning' })
    .then(async () => {
      await deleteNote(folder, name)
      if (activeNote.value?.name === name) { activeNote.value = null; content.value = '' }
      await refresh(folder)
    }).catch(() => {})
}
function newFolder() {
  ElMessageBox.prompt('笔记本名称', '新建笔记本', { confirmButtonText: '创建' })
    .then(async ({ value }) => {
      if (!value?.trim()) return
      await createFolder(value.trim())
      await refresh(value.trim())
    }).catch(() => {})
}

/* ---------- 挂载 ---------- */
onMounted(async () => {
  await refresh()
  if (folders.value.length) activeFolder.value = folders.value[0].folder
  const f = String(route.query.folder || '')
  const n = String(route.query.name || '')
  if (f && n) await pickNote(f, n)
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="min-h-screen pt-[var(--nav-h)]">
    <!-- 顶部：模式切换 + 全局动作 -->
    <div class="flex flex-wrap items-center gap-2 border-b border-[var(--divider)] px-4 py-2">
      <el-radio-group v-model="mode" size="small">
        <el-radio-button value="write">✍️ 写作</el-radio-button>
        <el-radio-button value="manage">🗂 内容管理</el-radio-button>
      </el-radio-group>
      <span class="sp"></span>
      <template v-if="!isStatic()">
        <el-button size="small" @click="doDaily">📅 今日笔记</el-button>
        <el-button size="small" :icon="Plus" @click="newFolder">新建笔记本</el-button>
      </template>
    </div>

    <!-- ============ 写作 ============ -->
    <div v-if="mode === 'write'">
      <div v-if="!activeNote" class="mx-auto max-w-md px-6 py-24 text-center text-[var(--text-3)]">
        <div class="mb-3 text-4xl">📝</div>
        从左侧/管理列表选择一篇笔记{{ isStatic() ? '' : '，或新建一篇' }}
      </div>
      <template v-else>
        <!-- 标题栏 -->
        <input
          v-model="titleInput"
          class="w-full border-none bg-transparent px-5 pb-1 pt-4 text-[26px] font-bold text-[var(--text-1)] outline-none placeholder:text-[var(--text-3)]"
          placeholder="请输入标题…"
        />
        <!-- 标签行 -->
        <div class="flex flex-wrap items-center gap-1.5 px-5 pb-2">
          <span
            v-for="t in tags" :key="t"
            class="flex items-center gap-1 rounded-full bg-[var(--brand-soft)] px-2.5 py-0.5 text-[12px] text-[var(--brand)]"
          >
            #{{ t }}
            <span v-if="!isStatic()" class="cursor-pointer opacity-60 hover:opacity-100" @click="removeTag(t)">✕</span>
          </span>
          <el-button v-if="!isStatic()" size="small" text :icon="Edit" @click="editTags">
            {{ tags.length ? '编辑' : '添加标签' }}
          </el-button>
        </div>
        <!-- 工具栏 -->
        <div
          v-if="!isStatic()"
          class="sticky top-[var(--nav-h)] z-10 flex flex-wrap items-center gap-1 border-b border-[var(--divider)] bg-[var(--bg-alt)]/90 px-4 py-1.5 backdrop-blur"
        >
          <button class="tbtn" title="加粗" @click="tools.bold"><b>B</b></button>
          <button class="tbtn" title="斜体" @click="tools.italic"><i>I</i></button>
          <button class="tbtn" title="二级标题" @click="tools.h2">H2</button>
          <button class="tbtn" title="三级标题" @click="tools.h3">H3</button>
          <button class="tbtn" title="引用" @click="tools.quote">❝</button>
          <button class="tbtn" title="代码块" @click="tools.code">{ }</button>
          <button class="tbtn" title="链接" @click="tools.link">🔗</button>
          <button class="tbtn" title="表格" @click="tools.table">▦</button>
          <button class="tbtn" title="插入图片（或直接粘贴/拖拽）" @click="imgInput?.click()">🖼</button>
          <input ref="imgInput" type="file" accept="image/*" style="display: none" @change="pickImage" />
          <button class="tbtn" title="上传附件" @click="attInput?.click()">📎</button>
          <input ref="attInput" type="file" multiple style="display: none" @change="pickAtt" />
          <span class="sp"></span>
          <el-radio-group v-model="view" size="small">
            <el-radio-button value="edit">编辑</el-radio-button>
            <el-radio-button value="split">分屏</el-radio-button>
            <el-radio-button value="preview">预览</el-radio-button>
          </el-radio-group>
          <el-button size="small" :loading="showBacklinks" @click="toggleBacklinks">反链</el-button>
          <el-button size="small" @click="doPdf('note')">PDF</el-button>
          <el-button size="small" :icon="Edit" @click="renameNote2">重命名</el-button>
          <el-button size="small" type="danger" plain :icon="Delete" @click="delNote">删除</el-button>
          <el-button size="small" type="primary" :loading="saving" @click="doSave">
            发布{{ dirty ? '•' : '' }}
          </el-button>
        </div>

        <!-- 反向链接 -->
        <div v-if="showBacklinks" class="border-b border-[var(--divider)] bg-[var(--bg-soft)] px-5 py-2 text-[12.5px]">
          <span class="mr-2 text-[var(--text-3)]">反向链接（{{ backlinksList.length }}）：</span>
          <a
            v-for="b in backlinksList" :key="b.folder + b.name"
            class="mr-3 cursor-pointer text-[var(--brand)]"
            @click="pickNote(b.folder, b.name)"
          >{{ b.title }}</a>
          <span v-if="!backlinksList.length" class="text-[var(--text-3)]">暂无</span>
        </div>

        <!-- 编辑/预览区 -->
        <div :class="view === 'split' && !isStatic() ? 'grid grid-cols-1 lg:grid-cols-2' : 'block'">
          <textarea
            v-if="!isStatic() && view !== 'preview'"
            ref="taEl"
            v-model="content"
            class="h-[calc(100vh-190px)] w-full resize-none bg-[var(--bg)] p-5 font-mono text-[14px] leading-relaxed text-[var(--text-1)] outline-none lg:h-[calc(100vh-150px)]"
            :class="view === 'split' ? 'border-r border-[var(--divider)]' : ''"
            placeholder="正文… 支持粘贴/拖拽图片、[[双链]]、[!TIP] 提示块"
            spellcheck="false"
            @paste="onPaste"
            @drop="onDrop"
            @dragover.prevent
          />
          <div
            v-if="isStatic() || view !== 'edit'"
            class="overflow-y-auto px-6 py-4 lg:h-[calc(100vh-150px)]"
          >
            <article class="article-body !mx-0 !max-w-none !p-0" v-html="preview" />
          </div>
        </div>

        <!-- 状态栏 -->
        <div class="fixed bottom-0 left-0 right-0 z-10 flex items-center gap-4 border-t border-[var(--divider)] bg-[var(--bg-alt)] px-5 py-1.5 text-[11.5px] text-[var(--text-3)] md:left-[var(--side-w,0px)]">
          <span>字数 {{ wordCount }}</span>
          <span v-if="dirty" class="text-[var(--yellow,#d97706)]">未发布修改</span>
          <span v-else-if="draftSavedAt">草稿已本地留存 {{ draftSavedAt }}</span>
          <span v-if="activeNote">更新于 {{ activeNote.updated }}</span>
          <span class="sp"></span>
          <span>Ctrl+S 发布</span>
        </div>
      </template>
    </div>

    <!-- ============ 内容管理 ============ -->
    <div v-else class="px-4 py-4" style="padding-top: calc(var(--nav-h) + 12px)">
      <div class="mb-3 flex flex-wrap items-center gap-2.5">
        <h1 class="mr-auto text-lg font-bold text-[var(--text-1)]">内容管理</h1>
        <input
          v-model="qFilter"
          placeholder="搜索标题/文件名…"
          class="w-56 rounded-lg border border-[var(--divider)] bg-[var(--bg-alt)] px-3 py-1.5 text-[13px] outline-none focus:border-[var(--brand)]"
        />
        <select
          v-model="folderFilter"
          class="rounded-lg border border-[var(--divider)] bg-[var(--bg-alt)] px-2.5 py-1.5 text-[13px]"
        >
          <option value="">全部笔记本</option>
          <option v-for="f in folders" :key="f.folder" :value="f.folder">{{ f.folder }}</option>
        </select>
        <select
          v-model="tagFilter"
          class="rounded-lg border border-[var(--divider)] bg-[var(--bg-alt)] px-2.5 py-1.5 text-[13px]"
        >
          <option value="">全部标签</option>
          <option v-for="t in allTags" :key="t" :value="t">#{{ t }}</option>
        </select>
        <el-button size="small" :icon="Plus" @click="newNote" v-if="!isStatic()">新建笔记</el-button>
      </div>
      <table class="w-full text-[13.5px]">
        <thead>
          <tr class="border-b border-[var(--divider)] text-left text-[var(--text-3)]">
            <th class="py-2 pr-3 font-semibold">标题</th>
            <th class="py-2 pr-3 font-semibold">笔记本</th>
            <th class="py-2 pr-3 font-semibold">标签</th>
            <th class="py-2 pr-3 font-semibold">更新</th>
            <th class="py-2 pr-3 font-semibold">大小</th>
            <th class="py-2 font-semibold">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in manageRows" :key="r.folder + '/' + r.note.name" class="border-b border-[var(--divider)] hover:bg-[var(--bg-soft)]">
            <td class="py-2 pr-3">
              <a class="cursor-pointer font-medium text-[var(--text-1)] hover:text-[var(--brand)]" @click="pickNote(r.folder, r.note.name)">
                {{ r.note.title }}
              </a>
            </td>
            <td class="py-2 pr-3 text-[var(--text-2)]">{{ r.folder }}</td>
            <td class="py-2 pr-3">
              <span v-for="t in r.note.tags" :key="t" class="mr-1 text-[11.5px] text-[var(--brand)]">#{{ t }}</span>
            </td>
            <td class="py-2 pr-3 text-[var(--text-3)]">{{ r.note.updated }}</td>
            <td class="py-2 pr-3 text-[var(--text-3)]">{{ (r.note.size / 1024).toFixed(1) }}K</td>
            <td class="py-2">
              <el-button size="small" text :icon="Edit" @click="renameNote2(r)">重命名</el-button>
              <el-button size="small" text type="danger" :icon="Delete" @click="delNote(r)">删除</el-button>
            </td>
          </tr>
          <tr v-if="!manageRows.length">
            <td colspan="6" class="py-8 text-center text-[var(--text-3)]">没有匹配的笔记</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.sp { flex: 1; }
:deep(.wikilink) {
  color: var(--brand);
  border-bottom: 1px dashed var(--brand);
}
:deep(.wikilink.missing) {
  color: var(--text-3);
  border-bottom: 1px dashed var(--text-3);
}
.tbtn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 30px;
  height: 28px;
  padding: 0 7px;
  border: 1px solid var(--divider);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-2);
  font-size: 12.5px;
  cursor: pointer;
}
.tbtn:hover { color: var(--brand); border-color: var(--brand); }
</style>
