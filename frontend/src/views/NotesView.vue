<script setup lang="ts">
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Setting } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'
import { isStatic } from '@/api/http'
import NotesWrite from '@/components/notes/NotesWrite.vue'
import NotesManage from '@/components/notes/NotesManage.vue'
import { useNotes } from '../composables/useNotes'

const route = useRoute()
const theme = useThemeStore()
const {
  mode, setMode, idx, folders, activeFolder, doDaily, doSave,
  nbOpen, newNbName, renameNb, deleteNb, createNb,
  refresh, pickNote,
} = useNotes()

onMounted(async () => {
  theme.init()
  await refresh()
  if (folders.value.length) activeFolder.value = folders.value[0].folder
  const f = String(route.query.folder || '')
  const n = String(route.query.name || '')
  if (f && n) await pickNote(f, n)
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); doSave() }
}
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
            @click="setMode('write')"
          >写作</button>
          <button
            class="rounded-md px-3.5 py-1 transition-colors"
            :class="mode === 'manage' ? 'bg-[var(--bg)] font-semibold text-[var(--text-1)] shadow-sm' : 'text-[var(--text-2)] hover:text-[var(--text-1)]'"
            @click="setMode('manage')"
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

    <!-- 写作 / 内容管理 -->
    <NotesWrite v-if="mode === 'write'" @open-manage="setMode('manage')" />
    <NotesManage v-else />
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
</style>
