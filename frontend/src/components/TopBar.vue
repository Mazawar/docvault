<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Moon, Sunny, Setting, Search } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'
import { isStatic, type IndexPayload } from '@/api/http'
import { getIndex, hitUrl, searchAll } from '@/api/reading'
import type { SearchHit } from '@/api/types'

const theme = useThemeStore()
const route = useRoute()
const router = useRouter()
const q = ref('')
const boxOpen = ref(false)
const hits = ref<SearchHit[]>([])
const inputEl = ref<HTMLInputElement | null>(null)
let timer: number | null = null
let seq = 0

/* ---- 书籍切换器（全局，任意页面可跳书） ---- */
const idx = ref<IndexPayload | null>(null)
getIndex().then((i) => (idx.value = i))

const currentBook = computed(() => {
  const pid = String(route.params.pid || '')
  const bid = String(route.params.bid || '')
  return pid && bid ? `${pid}/${bid}` : ''
})

function onSwitchBook(v: string) {
  if (v) router.push('/read/' + v + '/')
}

/* ---- Ctrl+K 全文搜索下拉 ---- */
async function run() {
  const t = q.value.trim()
  if (!t) {
    hits.value = []
    boxOpen.value = false
    return
  }
  const my = ++seq
  const r = await searchAll(t, '')
  if (my !== seq) return // 只保留最后一次输入的结果
  hits.value = r.slice(0, 12)
  boxOpen.value = true
}

function onInput() {
  if (timer) window.clearTimeout(timer)
  timer = window.setTimeout(run, 200)
}

function go(h: SearchHit) {
  boxOpen.value = false
  q.value = ''
  router.push({ path: '/read/' + h.pid + '/' + h.bid + '/' + h.slug })
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') boxOpen.value = false
}

function onTheme() {
  theme.init()
  theme.toggle()
}

watch(q, () => {
  if (!q.value.trim()) boxOpen.value = false
})
// 路由变化时收起下拉
watch(() => route.fullPath, () => {
  boxOpen.value = false
})

defineExpose({
  focus() {
    nextTick(() => inputEl.value?.focus())
  }
})
</script>

<template>
  <header
    class="fixed inset-x-0 top-0 z-80 flex h-[60px] items-center gap-2.5 border-b border-[var(--divider)] bg-[var(--bg)]/82 px-3 backdrop-blur-md md:gap-3.5 md:px-5"
  >
    <a class="logo whitespace-nowrap text-[17px] font-bold" href="#/">Doc<b class="text-[var(--brand)]">Vault</b></a>

    <el-select
      :model-value="currentBook"
      placeholder="切换书籍…"
      filterable
      class="booksel"
      size="default"
      @change="onSwitchBook"
    >
      <el-option-group v-for="p in idx?.projects" :key="p.id" :label="p.name">
        <el-option
          v-for="b in p.books"
          :key="p.id + '/' + b.id"
          :value="p.id + '/' + b.id"
          :label="b.title"
        >
          <span class="flex items-center justify-between gap-3">
            <span>{{ b.title }}</span>
            <span class="text-xs text-[var(--text-3)]">{{ b.n }}</span>
          </span>
        </el-option>
      </el-option-group>
    </el-select>

    <span class="flex-1"></span>

    <div class="searchwrap relative">
      <input
        ref="inputEl"
        v-model="q"
        placeholder="全文搜索… Ctrl+K"
        autocomplete="off"
        class="w-32 rounded-lg border border-[var(--divider)] bg-[var(--bg-alt)] px-3 py-1.5 text-[13px] outline-none transition-colors focus:w-64 focus:border-[var(--brand)] focus:bg-[var(--bg)] md:w-52"
        @input="onInput"
        @keydown="onKeydown"
      />
      <div v-if="boxOpen" class="dropdown" @mousedown.prevent>
        <a v-for="h in hits" :key="h.pid + h.bid + h.slug" class="item" :href="hitUrl(h)" @click="go(h)">
          <div class="t">{{ h.title }}</div>
          <!-- eslint-disable-next-line vue/no-v-html — 后端生成的 <mark> 摘要 -->
          <div class="s" v-html="h.snip"></div>
        </a>
        <div v-if="!hits.length" class="item mut">无结果</div>
      </div>
    </div>
    <button class="tbtn" title="搜索" @click="inputEl?.focus()">
      <el-icon><Search /></el-icon>
    </button>
    <button class="tbtn" title="切换主题" @click="theme.init(), theme.toggle()">
      <el-icon><Moon v-if="!theme.dark" /><Sunny v-else /></el-icon>
    </button>
    <a v-if="!isStatic()" class="adminlink" href="#/admin" title="资源管理">
      <el-icon><Setting /></el-icon><span class="ml-1 hidden text-[13px] md:inline">管理</span>
    </a>
  </header>
</template>

<style scoped>
.logo b {
  color: var(--brand);
}
.booksel {
  width: 150px;
}
@media (min-width: 768px) {
  .booksel {
    width: 230px;
  }
}
.booksel :deep(.el-select__wrapper) {
  background: var(--bg-alt);
  box-shadow: 0 0 0 1px var(--divider) inset;
  border-radius: 8px;
  min-height: 32px;
  font-size: 13px;
}
.booksel :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--brand) inset;
}
.tbtn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 30px;
  border: 1px solid var(--divider);
  background: var(--bg);
  color: var(--text-2);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: 0.15s;
}
.tbtn:hover {
  color: var(--brand);
  border-color: var(--brand);
}
.adminlink {
  display: inline-flex;
  align-items: center;
  color: var(--text-2);
  font-size: 13px;
  white-space: nowrap;
}
.adminlink:hover {
  color: var(--brand);
}
.searchwrap input {
  transition: width 0.2s, border 0.2s, background 0.2s;
}
.dropdown {
  position: absolute;
  right: 0;
  top: 38px;
  width: 400px;
  max-height: 66vh;
  overflow: auto;
  background: var(--bg);
  border: 1px solid var(--divider);
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.14);
  z-index: 99;
}
.item {
  display: block;
  padding: 9px 14px;
  border-bottom: 1px solid var(--divider);
  cursor: pointer;
}
.item:last-child {
  border-bottom: none;
}
.item:hover {
  background: var(--bg-soft);
}
.item .t {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-1);
}
.item .s {
  font-size: 12px;
  color: var(--text-3);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.item .s :deep(mark),
.item .s mark {
  background: rgba(255, 208, 75, 0.45);
  color: inherit;
  border-radius: 3px;
}
.mut {
  color: var(--text-3);
  font-size: 12.5px;
}
@media (max-width: 900px) {
  .dropdown {
    width: 300px;
  }
}
</style>
