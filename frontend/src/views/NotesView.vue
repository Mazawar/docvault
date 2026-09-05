<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus } from '@element-plus/icons-vue'
import {
  createFolder, createNote, daily, deleteNote, noteContent, noteRendered, notesIndex,
  renameNote, renderPreview, saveNote, uploadAttachment, uploadImage, backlinks,
  type NoteItem, type NotesIndex
} from '@/api/notes'
import { isStatic } from '@/api/http'
import { adminApi } from '@/api/admin'

const route = useRoute()
const idx = ref<NotesIndex | null>(null)
const activeFolder = ref('')
const activeNote = ref<NoteItem | null>(null)
const content = ref('')
const tags = ref<string[]>([])
const preview = ref('')
const dirty = ref(false)
const saving = ref(false)
const qFilter = ref('')
const tagFilter = ref('')
const backlinksList = ref<{ folder: string; name: string; title: string }[]>([])
const showBacklinks = ref(false)
const taEl = ref<HTMLTextAreaElement | null>(null)

const folders = computed(() => idx.value?.folders || [])
const filteredNotes = computed(() => {
  let list = folders.value.find((f) => f.folder === activeFolder.value)?.notes || []
  if (tagFilter.value) list = list.filter((n) => n.tags?.includes(tagFilter.value))
  const q = qFilter.value.trim().toLowerCase()
  if (q) list = list.filter((n) => (n.title + n.name).toLowerCase().includes(q))
  return list
})
const allTags = computed(() => {
  const s = new Set<string>()
  for (const f of folders.value) for (const n of f.notes) for (const t of n.tags || []) s.add(t)
  return [...s]
})

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

async function pickNote(n: NoteItem) {
  if (dirty.value && !confirm('有未保存的修改，确定离开？')) return
  dirty.value = false
  showBacklinks.value = false
  activeNote.value = n
  if (!isStatic()) {
    const r = await noteContent(activeFolder.value, n.name)
    content.value = r.content
    tags.value = r.tags || []
    preview.value = (await renderPreview(activeFolder.value, n.name, content.value)).html
  } else {
    preview.value = (await noteRendered(activeFolder.value, n.name)).html
  }
}

async function refreshNoteKeep() {
  await refresh(activeFolder.value)
  const n = filteredNotes.value.find((x) => x.name === activeNote.value?.name)
    || notes.value.find((x) => x.name === activeNote.value?.name)
  if (n) activeNote.value = n
}

let timer: number | null = null
watch(content, () => {
  dirty.value = true
  if (isStatic()) return
  if (timer) window.clearTimeout(timer)
  timer.value = window.setTimeout(async () => {
    if (!activeNote.value) return
    preview.value = (await renderPreview(activeFolder.value, activeNote.value.name, content.value)).html
  }, 600)
})

async function doSave() {
  if (!activeNote.value) return
  saving.value = true
  try {
    await saveNote(activeFolder.value, activeNote.value.name, content.value, tags.value)
    dirty.value = false
    ElMessage.success('已保存')
    await refreshNoteKeep()
    if (showBacklinks.value) backlinksList.value = await backlinks(activeFolder.value, activeNote.value.name)
  } finally {
    saving.value = false
  }
}

function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    doSave()
  }
}

function insertAtCursor(text: string) {
  const ta = taEl.value
  if (!ta) { content.value += text; return }
  const s = ta.selectionStart ?? content.value.length
  content.value = content.value.slice(0, s) + text + content.value.slice(ta.selectionEnd ?? s)
  dirty.value = true
}

async function handleFiles(files: FileList | File[]) {
  for (const f of Array.from(files)) {
    if (f.type.startsWith('image/')) {
      const r = await uploadImage(f)
      insertAtCursor(`\n![](${r.url})\n`)
    } else {
      const r = await uploadAttachment(f)
      insertAtCursor(`[📎 ${f.name}](${r.url})`)
    }
  }
  ElMessage.success('已插入')
}

function onPaste(e: ClipboardEvent) {
  const files = Array.from(e.clipboardData?.files || [])
  if (files.length) { e.preventDefault(); handleFiles(files) }
}

function onDrop(e: DragEvent) {
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length) { e.preventDefault(); handleFiles(files) }
}

function newNote() {
  ElMessageBox.prompt('笔记文件名（不含 .md）', '新建笔记', { confirmButtonText: '创建' })
    .then(async ({ value }) => {
      if (!value?.trim()) return
      await createNote(activeFolder.value || '我的笔记', value.trim())
      await refresh(activeFolder.value)
      const n = notes.value.find((x) => x.name === value.trim())
      if (n) pickNote(n)
    }).catch(() => {})
}

function renameNote2() {
  if (!activeNote.value) return
  ElMessageBox.prompt('新文件名（不含 .md）', '重命名', { inputValue: activeNote.value.name })
    .then(async ({ value }) => {
      if (!value?.trim()) return
      await renameNote(activeFolder.value, activeNote.value.name, value.trim())
      dirty.value = false
      await refresh(activeFolder.value)
      ElMessage.success('已重命名')
    }).catch(() => {})
}

function delNote() {
  if (!activeNote.value) return
  ElMessageBox.confirm(`删除「${activeNote.value.title}」？不可恢复`, '删除笔记', { type: 'warning' })
    .then(async () => {
      await deleteNote(activeFolder.value, activeNote.value.name)
      activeNote.value = null
      content.value = ''
      await refresh(activeFolder.value)
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

function editTags() {
  ElMessageBox.prompt('标签（英文逗号分隔）', '编辑标签', { inputValue: tags.value.join(',') })
    .then(async ({ value }) => {
      tags.value = (value || '').split(/[,，]/).map((x) => x.trim()).filter(Boolean)
      await doSave()
    }).catch(() => {})
}

async function toggleBacklinks() {
  if (!activeNote.value) return
  if (!showBacklinks.value) {
    backlinksList.value = await backlinks(activeFolder.value, activeNote.value.name)
  }
  showBacklinks.value = !showBacklinks.value
}

async function doPdf(kind: 'note' | 'notebook') {
  if (kind === 'note' && !activeNote.value) return
  await adminApi.exportNotePdf(
    kind === 'note' ? activeFolder.value : activeFolder.value,
    kind === 'note' ? activeNote.value!.name : '')
  ElMessage.success(`已提交${kind === 'note' ? '笔记' : '笔记本'} PDF 导出，进度见任务队列`)
}

async function doDaily() {
  const r = await daily()
  await refresh(r.folder)
  const n = notes.value.find((x) => x.name === r.name)
  if (n) pickNote(n)
  ElMessage.success('今日笔记已就绪')
}

async function openFromQuery() {
  const f = String(route.query.folder || '')
  const n = String(route.query.name || '')
  if (!f) return
  await refresh(f)
  activeFolder.value = f
  if (n) {
    const item = notes.value.find((x) => x.name === n)
    if (item) await pickNote(item)
  }
}

onMounted(async () => {
  await refresh()
  if (folders.value.length) activeFolder.value = folders.value[0].folder
  await openFromQuery()
  window.addEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="flex min-h-screen flex-col pt-[var(--nav-h)] md:flex-row">
    <!-- 左栏 -->
    <aside class="w-full shrink-0 border-b border-[var(--divider)] bg-[var(--bg-soft)] md:sticky md:top-[var(--nav-h)] md:h-[calc(100vh-var(--nav-h))] md:w-64 md:overflow-y-auto md:border-b-0 md:border-r">
      <div class="flex items-center justify-between px-3 pb-1 pt-3">
        <span class="text-[13px] font-semibold text-[var(--text-1)]">笔记本</span>
        <el-button v-if="!isStatic()" size="small" text :icon="Plus" @click="newFolder">新建</el-button>
      </div>
      <div class="flex gap-1.5 overflow-x-auto px-3 pb-2 md:flex-col md:overflow-visible">
        <button
          v-for="f in folders" :key="f.folder"
          class="whitespace-nowrap rounded-lg px-2.5 py-1.5 text-left text-[13px] transition-colors"
          :class="activeFolder === f.folder ? 'bg-[var(--brand-soft)] font-semibold text-[var(--brand)]' : 'text-[var(--text-2)] hover:bg-[var(--bg)]'"
          @click="activeFolder = f.folder"
        >
          📁 {{ f.folder }}
          <span class="ml-1 text-[11px] text-[var(--text-3)]">{{ f.notes.length }}</span>
        </button>
      </div>
      <div class="hidden border-t border-[var(--divider)] px-3 pt-2 md:block">
        <input
          v-model="qFilter"
          placeholder="筛选…"
          class="mb-1 w-full rounded-lg border border-[var(--divider)] bg-[var(--bg)] px-2.5 py-1.5 text-[12.5px] outline-none focus:border-[var(--brand)]"
        />
        <div v-if="allTags.length" class="flex flex-wrap gap-1 pb-1.5">
          <span
            v-for="t in allTags" :key="t"
            class="cursor-pointer rounded-full px-2 py-0.5 text-[11px]"
            :class="tagFilter === t ? 'bg-[var(--brand)] text-white' : 'bg-[var(--brand-soft)] text-[var(--brand)]'"
            @click="tagFilter = tagFilter === t ? '' : t"
          >#{{ t }}</span>
        </div>
      </div>
      <div class="hidden items-center justify-between border-t border-[var(--divider)] px-3 pt-2 md:flex">
        <span class="text-[13px] font-semibold text-[var(--text-1)]">笔记</span>
        <el-button v-if="!isStatic()" size="small" text :icon="Plus" @click="newNote">新建</el-button>
      </div>
      <nav class="hidden px-2 pb-3 md:block">
        <a
          v-for="n in filteredNotes" :key="n.name"
          class="block cursor-pointer rounded-lg px-2.5 py-1.5 text-[13px] leading-snug"
          :class="activeNote?.name === n.name ? 'bg-[var(--brand-soft)] font-semibold text-[var(--brand)]' : 'text-[var(--text-2)] hover:bg-[var(--bg)]'"
          :title="n.title"
          @click="pickNote(n)"
        >
          {{ n.title }}
          <div class="mt-0.5 flex items-center gap-1 text-[11px] text-[var(--text-3)]">
            <span>{{ n.updated }}</span>
            <span v-for="t in n.tags" :key="t" class="text-[var(--brand)]">#{{ t }}</span>
          </div>
        </a>
        <div v-if="!filteredNotes.length" class="px-2 py-3 text-xs text-[var(--text-3)]">无匹配笔记</div>
      </nav>
      <div class="px-3 pb-3 md:hidden">
        <select
          class="w-full rounded-lg border border-[var(--divider)] bg-[var(--bg)] px-2 py-2 text-[13px]"
          :value="activeNote?.name || ''"
          @change="(e: Event) => { const n = notes.find(x => x.name === (e.target as HTMLSelectElement).value); if (n) pickNote(n) }"
        >
          <option value="" disabled>选择笔记…</option>
          <option v-for="n in notes" :key="n.name" :value="n.name">{{ n.title }}</option>
        </select>
      </div>
    </aside>

    <!-- 右侧 -->
    <main class="min-w-0 flex-1">
      <div v-if="!activeNote" class="mx-auto max-w-md px-6 py-24 text-center text-[var(--text-3)]">
        <div class="mb-3 text-4xl">📝</div>
        从左侧选择一篇笔记{{ isStatic() ? '' : '，或新建一篇' }}
      </div>
      <template v-else>
        <div class="flex flex-wrap items-center gap-2 border-b border-[var(--divider)] px-4 py-2.5">
          <span class="mr-auto truncate text-[14px] font-semibold text-[var(--text-1)]" :title="activeNote.name">
            {{ activeNote.title }}
          </span>
          <template v-if="!isStatic()">
            <el-button size="small" @click="doDaily">📅 今日</el-button>
            <el-button size="small" :loading="showBacklinks" @click="toggleBacklinks">反链</el-button>
            <el-button size="small" :disabled="!activeNote.tags?.length" @click="toggleBacklinks">
              标签 {{ activeNote.tags?.length || 0 }}
            </el-button>
            <el-button size="small" :icon="Edit" @click="editTags">标签</el-button>
            <el-button size="small" :icon="Edit" @click="renameNote2">重命名</el-button>
            <el-button size="small" type="danger" plain :icon="Delete" @click="delNote">删除</el-button>
            <el-button size="small" @click="doPdf('note')">导出 PDF</el-button>
            <el-button size="small" @click="doPdf('notebook')">整本 PDF</el-button>
            <el-button size="small" type="primary" :loading="saving" @click="doSave">
              保存{{ dirty ? '•' : '' }}
            </el-button>
          </template>
        </div>

        <div v-if="showBacklinks && backlinksList.length" class="border-b border-[var(--divider)] bg-[var(--bg-soft)] px-4 py-2 text-[12.5px]">
          <span class="mr-2 text-[var(--text-3)]">反向链接：</span>
          <a
            v-for="b in backlinksList" :key="b.folder + b.name"
            class="mr-3 cursor-pointer text-[var(--brand)]"
            @click="activeFolder = b.folder; refresh(b.folder).then(() => { const n = notes.find(x => x.name === b.name); if (n) pickNote(n) })"
          >{{ b.title }}</a>
        </div>

        <div v-if="activeNote.tags?.length" class="flex flex-wrap gap-1.5 border-b border-[var(--divider)] px-4 py-2">
          <span
            v-for="t in activeNote.tags" :key="t"
            class="cursor-pointer rounded-full bg-[var(--brand-soft)] px-2 py-0.5 text-[11.5px] text-[var(--brand)]"
            :title="'筛选 #' + t"
            @click="tagFilter = t"
          >#{{ t }}</span>
          <span v-if="tagFilter" class="cursor-pointer text-[11.5px] text-[var(--text-3)]" @click="tagFilter = ''">✕ 清除筛选</span>
        </div>

        <div :class="isStatic() ? '' : 'grid grid-cols-1 lg:grid-cols-2'">
          <textarea
            v-if="!isStatic()"
            ref="taEl"
            v-model="content"
            class="h-[calc(100vh-110px)] w-full resize-none border-r border-[var(--divider)] bg-[var(--bg)] p-4 font-mono text-[13.5px] leading-relaxed text-[var(--text-1)] outline-none lg:h-[calc(100vh-117px)]"
            placeholder="# 用 Markdown 书写… 支持粘贴图片、[[双链]]"
            spellcheck="false"
            @paste="onPaste"
            @drop="onDrop"
            @dragover.prevent
          />
          <div class="overflow-y-auto bg-[var(--bg)] p-4 lg:h-[calc(100vh-117px)] lg:p-6">
            <article class="article-body !mx-0 !max-w-none !p-0" v-html="preview" />
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
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
