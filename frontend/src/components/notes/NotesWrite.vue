<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { MdEditor, MdPreview } from 'md-editor-v3'
import type { ExposeParam, ToolbarNames } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { ElMessage } from 'element-plus'
import { useThemeStore } from '@/stores/theme'
import { isStatic } from '@/api/http'
import { useNotes } from '../../composables/useNotes'

const theme = useThemeStore()
const editorRef = ref<ExposeParam | null>(null)

const {
  activeNote, activeFolder, titleInput, tags, content, dirty, saving,
  previewFallback, backlinksList, showBacklinks, draftSavedAt,
  editTags, removeTag, pickNote, toggleBacklinks, doSave, onEditorSave, onUploadImg,
} = useNotes()

const editorTheme = computed(() => (theme.dark ? 'dark' : 'light'))
const toolbars: ToolbarNames[] = [
  'bold', 'italic', 'strikeThrough', '-', 'title', 'quote', 'unorderedList', 'orderedList',
  'task', '-', 'codeRow', 'code', 'link', 'image', 'table', '-', 'revoke', 'next', 'save',
  '=', 'catalog', 'pageFullscreen'
]
async function onUploadImgWrap(files: File[], callback: (urls: string[]) => void) {
  await onUploadImg(files, callback)
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
onMounted(() => guardPreviewOnly())
watch(activeNote, () => setTimeout(guardPreviewOnly, 300))
</script>

<template>
  <div>
    <div v-if="!activeNote" class="mx-auto max-w-md px-6 py-20 text-center">
      <p class="mb-5 text-[15px] text-[var(--text-3)]">
        从「内容管理」选择一篇笔记开始编辑，或新建一篇
      </p>
      <el-button type="primary" @click="$emit('open-manage')">打开内容管理</el-button>
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
          @on-upload-img="onUploadImgWrap as any"
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
      </div>
    </template>
  </div>
</template>
