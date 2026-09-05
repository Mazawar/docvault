<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus } from '@element-plus/icons-vue'
import {
  createFolder, createNote, deleteNote, noteRendered, notesIndex, renameNote,
  renderPreview, saveNote, type NoteItem, type NotesIndex
} from '@/api/notes'
import { isStatic } from '@/api/http'

const idx = ref<NotesIndex | null>(null)
const activeFolder = ref('')
const activeNote = ref<NoteItem | null>(null)
const content = ref('')
const preview = ref('')
const dirty = ref(false)
const saving = ref(false)
const previewPane = ref(true)

const folders = computed(() => idx.value?.folders || [])
const notes = computed(
  () => folders.value.find((f) => f.folder === activeFolder.value)?.notes || [])

async function refresh(selectFolder?: string) {
  idx.value = await notesIndex()
  if (!folders.value.length) {
    if (!isStatic()) await createFolder('我的笔记')
    idx.value = await notesIndex()
  }
  activeFolder.value = selectFolder
    || (folders.value.some((f) => f.folder === activeFolder.value)
      ? activeFolder.value
      : folders.value[0]?.folder || '')
}

function pickNote(n: NoteItem) {
  if (dirty.value && !confirm('有未保存的修改，确定离开？')) return
  dirty.value = false
  activeNote.value = n
  if (!isStatic()) {
    import('@/api/notes').then((m) => m.noteContent(activeFolder.value, n.name))
      .then((r) => { content.value = r.content })
  } else {
    noteRendered(activeFolder.value, n.name).then((r) => { preview.value = r.html })
  }
}

let timer: number | null = null
watch(content, () => {
  dirty.value = true
  if (isStatic()) return
  if (timer) window.clearTimeout(timer)
  timer = window.setTimeout(async () => {
    if (!activeNote.value) return
    const r = await renderPreview(activeFolder.value, activeNote.value.name, content.value)
    preview.value = r.html
  }, 600)
})

async function doSave() {
  if (!activeNote.value) return
  saving.value = true
  try {
    await saveNote(activeFolder.value, activeNote.value.name, content.value)
    dirty.value = false
    ElMessage.success('已保存')
    await refresh(activeFolder.value)
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

onMounted(async () => {
  await refresh()
  if (folders.value.length) activeFolder.value = folders.value[0].folder
  window.addEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="flex min-h-screen flex-col pt-[var(--nav-h)] md:flex-row">
    <!-- 左栏：笔记本 + 笔记列表 -->
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
      <div class="hidden items-center justify-between border-t border-[var(--divider)] px-3 pt-2 md:flex">
        <span class="text-[13px] font-semibold text-[var(--text-1)]">笔记</span>
        <el-button v-if="!isStatic()" size="small" text :icon="Plus" @click="newNote">新建</el-button>
      </div>
      <nav class="hidden px-2 pb-3 md:block">
        <a
          v-for="n in notes" :key="n.name"
          class="block cursor-pointer rounded-lg px-2.5 py-1.5 text-[13px] leading-snug"
          :class="activeNote?.name === n.name ? 'bg-[var(--brand-soft)] font-semibold text-[var(--brand)]' : 'text-[var(--text-2)] hover:bg-[var(--bg)]'"
          :title="n.title"
          @click="pickNote(n)"
        >
          {{ n.title }}
          <div class="mt-0.5 text-[11px] text-[var(--text-3)]">{{ n.updated }}</div>
        </a>
        <div v-if="!notes.length" class="px-2 py-3 text-xs text-[var(--text-3)]">本笔记本还没有笔记</div>
      </nav>
      <!-- 移动端笔记下拉 -->
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

    <!-- 右侧：编辑 / 预览 -->
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
            <el-button size="small" :icon="Edit" @click="renameNote2">重命名</el-button>
            <el-button size="small" type="danger" plain :icon="Delete" @click="delNote">删除</el-button>
            <el-button size="small" type="primary" :loading="saving" @click="doSave">
              保存{{ dirty ? '•' : '' }}
            </el-button>
          </template>
        </div>

        <div :class="isStatic() ? '' : 'grid grid-cols-1 lg:grid-cols-2'">
          <textarea
            v-if="!isStatic()"
            v-model="content"
            class="h-[calc(100vh-110px)] w-full resize-none border-r border-[var(--divider)] bg-[var(--bg)] p-4 font-mono text-[13.5px] leading-relaxed text-[var(--text-1)] outline-none lg:h-[calc(100vh-117px)]"
            placeholder="# 用 Markdown 书写…"
            spellcheck="false"
          />
          <div class="overflow-y-auto bg-[var(--bg)] p-4 lg:h-[calc(100vh-117px)] lg:p-6">
            <article class="article-body !mx-0 !max-w-none !p-0" v-html="preview" />
          </div>
        </div>
      </template>
    </main>
  </div>
</template>
