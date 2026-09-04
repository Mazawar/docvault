<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getBook, getArticle } from '@/api/reading'
import { readUrl as toUrl } from '@/api/http'
import type { ArticlePayload, BookPayload } from '@/api/types'
import { useReadState } from '@/composables/useReadState'
import ArticleBody from '@/components/ArticleBody.vue'

const route = useRoute()
const { isRead, markRead, readMap } = useReadState()

const book = ref<BookPayload | null>(null)
const art = ref<ArticlePayload | null>(null)
const loading = ref(true)
const progress = ref(0)
const drawerOpen = ref(false)
const bodyEl = ref<HTMLElement | null>(null)

interface TocItem {
  id: string
  text: string
  level: number
}
const toc = ref<TocItem[]>([])
const tocActive = ref('')

const pid = computed(() => String(route.params.pid || ''))
const bid = computed(() => String(route.params.bid || ''))
const slug = computed(() => String(route.params.slug || ''))

interface Group {
  name: string
  items: { slug: string; title: string }[]
}

/** 侧栏按一级子目录分组（与旧站规则一致） */
const groups = computed<Group[]>(() => {
  if (!book.value) return []
  const map = new Map<string, { slug: string; title: string }[]>()
  for (const a of book.value.articles) {
    const segs = a.slug.split('/')
    const g = segs.length > 1 ? segs[0] : ''
    if (!map.has(g)) map.set(g, [])
    map.get(g)!.push(a)
  }
  return [...map.entries()].map(([g, items]) => ({
    name: g
      ? g.replace(/^\d+[_.\s-]*/, '').replace(/[_-]/g, ' ').trim() || g
      : '',
    items
  }))
})

async function loadBook() {
  if (!pid.value || !bid.value) return
  loading.value = true
  try {
    book.value = await getBook(pid.value, bid.value)
    if (!slug.value && book.value.articles.length) {
      const first = book.value.articles[0].slug
      window.location.hash = toUrl(pid.value, bid.value, first)
      return
    }
  } finally {
    loading.value = false
  }
}

async function loadArticle() {
  if (!pid.value || !bid.value || !slug.value) return
  loading.value = true
  art.value = null
  toc.value = []
  try {
    art.value = await getArticle(pid.value, bid.value, slug.value)
    if (art.value) document.title = `${art.value.title} · DocVault`
    await nextTick()
    buildToc()
    onScroll()
    checkRead()
  } catch {
    art.value = null
  } finally {
    loading.value = false
  }
}

/** 从渲染后的正文提取 h2/h3 目录；滚动时由 onScroll 同步高亮 */
let headingEls: HTMLElement[] = []

function buildToc() {
  const el = bodyEl.value
  if (!el) return
  const items: TocItem[] = []
  headingEls = Array.from(el.querySelectorAll('h2, h3'))
  headingEls.forEach((h, i) => {
    if (!h.id) h.id = `h-${i}`
    items.push({ id: h.id, text: h.textContent || '', level: h.tagName === 'H2' ? 2 : 3 })
  })
  toc.value = items
  tocActive.value = items[0]?.id || ''
}

function syncTocActive() {
  if (!headingEls.length) return
  let cur = headingEls[0].id
  for (const h of headingEls) {
    if (h.getBoundingClientRect().top <= 96) cur = h.id
    else break
  }
  if (tocActive.value !== cur) {
    tocActive.value = cur
    nextTick(() => {
      bodyEl.value
        ?.parentElement
        ?.querySelector('.toc a.on')
        ?.scrollIntoView({ block: 'nearest' })
    })
  }
}

function onScroll() {
  const h = document.documentElement
  const max = h.scrollHeight - h.clientHeight
  progress.value = max > 0 ? Math.min(100, (h.scrollTop / max) * 100) : 0
  syncTocActive()
  checkRead()
}

/** 滚动过 82% 记为已读 */
let marked = false
function checkRead() {
  if (marked || !art.value) return
  const h = document.documentElement
  if ((h.scrollTop + h.clientHeight) / h.scrollHeight > 0.82) {
    marked = true
    markRead(toUrl(pid.value, bid.value, slug.value), art.value.title)
  }
}

function goto(slug2: string) {
  drawerOpen.value = false
  window.location.hash = toUrl(pid.value, bid.value, slug2)
}

onBeforeUnmount(() => {
  headingEls = []
})

watch([pid, bid], loadBook)
watch(slug, loadArticle)
watch(readMap, () => nextTick())

onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
  loadBook().then(() => (slug.value ? loadArticle() : undefined))
})
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <div class="flex pt-[var(--nav-h)]">
    <div id="progress" :style="{ width: progress + '%' }"></div>
    <div class="backdrop" :class="{ show: drawerOpen }" @click="drawerOpen = false"></div>

    <aside
      class="sidebar"
      :class="{ open: drawerOpen }"
    >
      <div v-if="book">
        <div class="px-2.5 pb-2 text-[13px] font-semibold text-[var(--text-1)] truncate" :title="book.title">
          {{ book.pname !== book.title ? book.pname + ' · ' + book.title : book.title }}
        </div>
        <details v-for="g in groups" :key="g.name" open>
          <summary v-if="g.name">{{ g.name }}</summary>
          <a
            v-for="a in g.items"
            :key="a.slug"
            :class="{ on: a.slug === slug, read: isRead(toUrl(pid, bid, a.slug)) }"
            :href="toUrl(pid, bid, a.slug)"
            :title="a.title"
          >{{ a.title }}</a>
        </details>
      </div>
    </aside>

    <main class="min-w-0 flex-1">
      <button class="mburger tbtn" @click="drawerOpen = !drawerOpen">☰ 目录</button>
      <div v-if="loading && !art" class="mx-auto max-w-[784px] px-6 py-20 text-[var(--text-3)]">加载中…</div>
      <div v-else-if="!art" class="mx-auto max-w-[784px] px-6 py-20 text-[var(--text-3)]">文章不存在</div>
      <template v-else>
        <div class="crumb">
          <span>{{ art.pname }}</span> / <span>{{ art.btitle }}</span>
        </div>
        <h1 class="tt">{{ art.title }}</h1>
        <div ref="bodyEl" class="bodywrap">
          <ArticleBody :payload="art" />
          <aside v-if="toc.length > 2" class="toc">
            <div class="toc-tt">目录</div>
            <nav class="toc-rail">
              <a
                v-for="t in toc"
                :key="t.id"
                :href="'#' + t.id"
                :class="['lv' + t.level, { on: tocActive === t.id }]"
                :title="t.text"
              >{{ t.text }}</a>
            </nav>
          </aside>
        </div>
        <div class="pager">
          <a v-if="art.prev" :href="toUrl(pid, bid, art.prev.slug)">
            <span class="lab">← 上一篇</span><span class="ti">{{ art.prev.title }}</span>
          </a>
          <span v-else></span>
          <a v-if="art.next" class="next" :href="toUrl(pid, bid, art.next.slug)">
            <span class="lab">下一篇 →</span><span class="ti">{{ art.next.title }}</span>
          </a>
          <span v-else></span>
        </div>
        <div class="mx-auto max-w-[784px] border-t border-[var(--divider)] px-6 pb-14 pt-4 text-xs text-[var(--text-3)]">
          DocVault · 同步于 {{ art.updated }}
          <a v-if="art.source" :href="art.source" target="_blank">源</a>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped src="@/styles/reader.scss"></style>
