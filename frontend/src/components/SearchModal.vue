<script setup lang="ts">
/** DocSearch 式全局搜索弹窗：文章按书分组、笔记独立分组，键盘 ↑↓ Enter Esc 导航 */
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { getIndex, hitUrl, searchAll } from '@/api/reading'
import type { IndexPayload } from '@/api/http'
import type { SearchHit } from '@/api/types'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const router = useRouter()
const q = ref('')
const hits = ref<SearchHit[]>([])
const active = ref(0)
const inputEl = ref<HTMLInputElement | null>(null)
const idx = ref<IndexPayload | null>(null)
let timer: number | null = null
let seq = 0

getIndex().then((i) => (idx.value = i))

watch(
  () => props.open,
  (v) => {
    if (v) {
      q.value = ''
      hits.value = []
      active.value = 0
      nextTick(() => inputEl.value?.focus())
    }
  }
)

function run() {
  const t = q.value.trim()
  if (!t) {
    hits.value = []
    return
  }
  const my = ++seq
  searchAll(t, '').then((r) => {
    if (my !== seq) return
    hits.value = r.slice(0, 20)
    active.value = 0
  })
}

function onInput() {
  if (timer) window.clearTimeout(timer)
  timer = window.setTimeout(run, 180)
}

const groups = computed(() => {
  const out: { label: string; items: { h: SearchHit; i: number }[] }[] = []
  hits.value.forEach((h, i) => {
    const label = h.pid === '__notes__' ? '笔记' : bookLabel(h)
    const last = out[out.length - 1]
    if (last && last.label === label) last.items.push({ h, i })
    else out.push({ label, items: [{ h, i }] })
  })
  return out
})

function bookLabel(h: SearchHit) {
  const p = idx.value?.projects.find((x) => x.id === h.pid)
  const b = p?.books.find((x) => x.id === h.bid)
  return `${p?.name || h.pid} · ${b?.title || h.bid}`
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    active.value = Math.min(active.value + 1, hits.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    active.value = Math.max(active.value - 1, 0)
  } else if (e.key === 'Enter') {
    if (hits.value[active.value]) go(hits.value[active.value])
  } else if (e.key === 'Escape') {
    close()
  }
}

watch(active, () => {
  nextTick(() => {
    document.querySelector('.sf-panel .row.on')?.scrollIntoView({ block: 'nearest' })
  })
})

function go(h: SearchHit) {
  close()
  if (h.pid === '__notes__') {
    router.push({ path: '/notes', query: { folder: h.bid, name: h.slug } })
    return
  }
  router.push('/read/' + h.pid + '/' + h.bid + '/' + h.slug)
}

function close() {
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <Transition name="sfade">
      <div v-if="open" class="sf-overlay" @mousedown.self="close()">
        <div class="sf-panel">
          <div class="sf-head">
            <el-icon class="hicon"><Search /></el-icon>
            <input
              ref="inputEl"
              v-model="q"
              placeholder="搜索全部文章与笔记…"
              autocomplete="off"
              spellcheck="false"
              @input="onInput"
              @keydown="onKey"
            />
            <span class="esc" @click="close()">Esc</span>
          </div>
          <div class="sf-body">
            <template v-for="g in groups" :key="g.label">
              <div class="glabel">{{ g.label }}</div>
              <a
                v-for="it in g.items"
                :key="it.h.pid + it.h.bid + it.h.slug"
                class="row"
                :class="{ on: it.i === active }"
                :href="hitUrl(it.h)"
                @mousedown.prevent
                @click="go(it.h)"
                @mousemove="active = it.i"
              >
                <div class="t">{{ it.h.title }}</div>
                <!-- eslint-disable-next-line vue/no-v-html — 后端生成的 <mark> 摘要 -->
                <div class="s" v-html="it.h.snip"></div>
              </a>
            </template>
            <div v-if="q.trim() && !hits.length" class="sf-empty">
              没有与「{{ q.trim() }}」匹配的结果
            </div>
            <div v-else-if="!q.trim()" class="sf-empty">输入关键词，搜索全部文章与笔记</div>
          </div>
          <div class="sf-foot">
            <span><b>↑</b><b>↓</b> 选择</span>
            <span><b>Enter</b> 打开</span>
            <span><b>Esc</b> 关闭</span>
            <span class="flex-1" />
            <span>{{ hits.length }} 条结果</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.sf-overlay {
  position: fixed;
  inset: 0;
  z-index: 95;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 11vh 16px 0;
}
.sfade-enter-active,
.sfade-leave-active {
  transition: opacity 0.18s ease;
}
.sfade-enter-from,
.sfade-leave-to {
  opacity: 0;
}
.sf-panel {
  width: min(640px, 100%);
  max-height: 72vh;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  border: 1px solid var(--divider);
  border-radius: 12px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
  overflow: hidden;
}
.sf-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 16px;
  border-bottom: 1px solid var(--divider);
}
.hicon {
  color: var(--text-3);
}
.sf-head input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 15px;
  color: var(--text-1);
}
.sf-head input::placeholder {
  color: var(--text-3);
}
.esc {
  font-size: 11px;
  color: var(--text-3);
  border: 1px solid var(--divider);
  border-radius: 4px;
  padding: 1px 6px;
  cursor: pointer;
}
.sf-body {
  overflow: auto;
  padding: 6px 0 10px;
}
.glabel {
  padding: 10px 16px 4px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-3);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.row {
  display: block;
  padding: 8px 16px;
  cursor: pointer;
  border-left: 2px solid transparent;
}
.row.on {
  background: var(--bg-soft);
  border-left-color: var(--brand);
}
.row .t {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-1);
}
.row.on .t {
  color: var(--brand);
}
.row .s {
  font-size: 12px;
  color: var(--text-3);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.row .s :deep(mark) {
  background: rgba(255, 213, 79, 0.5);
  color: inherit;
  border-radius: 2px;
}
.sf-empty {
  padding: 28px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--text-3);
}
.sf-foot {
  display: flex;
  gap: 14px;
  padding: 8px 16px;
  border-top: 1px solid var(--divider);
  font-size: 11.5px;
  color: var(--text-3);
}
.sf-foot b {
  font-weight: 500;
  border: 1px solid var(--divider);
  border-radius: 4px;
  padding: 0 5px;
  margin-right: 3px;
}
</style>
