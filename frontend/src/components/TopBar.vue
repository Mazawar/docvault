<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Moon, Sunny, Reading, Search } from '@element-plus/icons-vue'
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

/* ---- 书籍切换器 ---- */
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

/* ---- 导航链接激活态 ---- */
const path = computed(() => route.path)

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
  if (my !== seq) return
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

function focusSearch() {
  nextTick(() => inputEl.value?.focus())
}

watch(q, () => {
  if (!q.value.trim()) boxOpen.value = false
})
watch(() => route.fullPath, () => {
  boxOpen.value = false
})

defineExpose({ focus: focusSearch })
</script>

<template>
  <header
    class="fixed inset-x-0 top-0 z-80 flex h-[var(--nav-h)] items-center border-b border-[var(--divider)] bg-[var(--bg)]/85 pl-4 pr-4 backdrop-blur-md md:pl-6"
  >
    <a class="mr-5 flex items-center gap-2 whitespace-nowrap" href="#/">
      <span class="logo-mark"></span>
      <span class="text-[15px] font-bold tracking-tight text-[var(--text-1)]">DocVault</span>
    </a>

    <nav class="navlinks h-full">
      <RouterLink to="/" class="navlink" :class="{ on: path === '/' }">首页</RouterLink>
      <RouterLink to="/search" class="navlink" :class="{ on: path === '/search' }">搜索</RouterLink>
      <RouterLink v-if="!isStatic()" to="/admin" class="navlink" :class="{ on: path === '/admin' }">管理</RouterLink>
    </nav>

    <span class="flex-1"></span>

    <el-select
      :model-value="currentBook"
      placeholder="选择书籍"
      filterable
      class="booksel"
      size="default"
      @change="onSwitchBook"
    >
      <template #prefix>
        <el-icon class="text-[var(--text-3)]"><Reading /></el-icon>
      </template>
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

    <div class="searchwrap relative ml-2">
      <el-icon class="sicon"><Search /></el-icon>
      <input
        ref="inputEl"
        v-model="q"
        placeholder="搜索… Ctrl+K"
        autocomplete="off"
        class="w-28 rounded-md bg-[var(--bg-soft)] py-1.5 pl-8 pr-3 text-[13px] outline-none transition-all placeholder:text-[var(--text-3)] focus:w-60 focus:bg-[var(--bg)] focus:shadow-[0_0_0_1px_var(--divider)] md:w-48"
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

    <button class="tbtn" title="切换主题" @click="theme.init(), theme.toggle()">
      <el-icon><Moon v-if="!theme.dark" /><Sunny v-else /></el-icon>
    </button>
  </header>
</template>

<style scoped>
.logo-mark {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  background: var(--brand);
  display: inline-block;
}
.navlinks {
  display: flex;
  align-items: stretch;
  gap: 2px;
}
.navlink {
  position: relative;
  display: flex;
  align-items: center;
  padding: 0 12px;
  font-size: 13.5px;
  color: var(--text-2);
  transition: color 0.15s;
}
.navlink:hover {
  color: var(--text-1);
}
.navlink.on {
  color: var(--text-1);
  font-weight: 600;
}
.navlink.on::after {
  content: '';
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: 0;
  height: 2px;
  border-radius: 2px 2px 0 0;
  background: var(--brand);
}
.booksel {
  width: 150px;
}
@media (min-width: 768px) {
  .booksel {
    width: 200px;
  }
}
.booksel :deep(.el-select__wrapper) {
  background: transparent;
  box-shadow: none;
  border-radius: 6px;
  min-height: 32px;
  font-size: 13px;
  transition: background 0.15s;
}
.booksel :deep(.el-select__wrapper:hover) {
  background: var(--bg-soft);
}
.booksel :deep(.el-select__wrapper.is-focused) {
  background: var(--bg-soft);
  box-shadow: none;
}
.sicon {
  position: absolute;
  left: 9px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-3);
  font-size: 13px;
  pointer-events: none;
}
.searchwrap input {
  transition: width 0.2s, background 0.2s, box-shadow 0.2s;
}
.tbtn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  margin-left: 4px;
  border: none;
  background: transparent;
  color: var(--text-2);
  border-radius: 6px;
  cursor: pointer;
  font-size: 15px;
  transition: 0.15s;
}
.tbtn:hover {
  color: var(--text-1);
  background: var(--bg-soft);
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
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
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
  background: rgba(255, 213, 79, 0.5);
  color: inherit;
  border-radius: 2px;
}
.mut {
  color: var(--text-3);
  font-size: 12.5px;
}
@media (max-width: 900px) {
  .dropdown {
    width: 300px;
  }
  .booksel {
    width: 110px;
  }
}
</style>
