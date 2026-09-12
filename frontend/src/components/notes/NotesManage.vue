<script setup lang="ts">
import { Delete, Edit } from '@element-plus/icons-vue'
import { useNotes } from '../../composables/useNotes'

const {
  folders, manageRows, allTags, qFilter, tagFilter, folderFilter,
  pickNote, renameNote2, delNote,
} = useNotes()
function fmtSize(n: number) { return n < 1024 ? `${n}B` : `${(n / 1024).toFixed(1)}K` }
</script>

<template>
  <div class="mx-auto max-w-5xl px-6 pb-16 pt-2">
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
</template>
