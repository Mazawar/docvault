<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { readUrl, type IndexPayload } from '@/api/http'
import { getIndex } from '@/api/reading'

/** 全部书籍：把所有项目的书摊平成瀑布流，按书直达阅读 */
const data = ref<IndexPayload | null>(null)
const q = ref('')

onMounted(async () => {
  data.value = await getIndex()
})

interface BookCard {
  pid: string
  bid: string
  title: string
  project: string
  type: string
  n: number
  updated: string
  href: string
}

const books = computed<BookCard[]>(() => {
  const out: BookCard[] = []
  for (const p of data.value?.projects ?? []) {
    for (const b of p.books) {
      out.push({
        pid: p.id, bid: b.id, title: b.title, project: p.name, type: p.type,
        n: b.n, updated: p.updated, href: readUrl(p.id, b.id, ''),
      })
    }
  }
  return out
})

const filtered = computed(() => {
  const t = q.value.trim().toLowerCase()
  if (!t) return books.value
  return books.value.filter(
    b => b.title.toLowerCase().includes(t) || b.project.toLowerCase().includes(t)
  )
})

const stats = computed(() => {
  const all = data.value?.projects ?? []
  return {
    projects: all.length,
    books: all.reduce((s, p) => s + p.books.length, 0),
    articles: all.reduce((s, p) => s + p.books.reduce((x, b) => x + b.n, 0), 0),
  }
})

function typeLabel(t: string): string {
  return t === 'notebook' ? '笔记本' : t === 'upload' ? '上传' : 'GitHub'
}

function fmtDay(s: string): string {
  return s && s !== '-' ? s.split(' ')[0] : ''
}
</script>

<template>
  <div class="mx-auto max-w-5xl px-6 pb-16 pt-10">
    <div class="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="m-0 text-[20px] font-semibold">全部书籍</h1>
        <p class="mt-1 text-xs text-[var(--text-3)]">
          共 {{ stats.projects }} 个项目 · {{ stats.books }} 本书 · {{ stats.articles }} 篇
        </p>
      </div>
      <input
        v-model="q"
        class="shelf-filter"
        type="search"
        placeholder="搜索书名或项目…"
      />
    </div>

    <div v-if="!data" class="text-sm text-[var(--text-3)]">加载中…</div>
    <div v-else-if="!filtered.length" class="rounded-xl border border-dashed border-[var(--divider)] p-8 text-center text-sm text-[var(--text-3)]">
      没有匹配的书籍
    </div>
    <!-- 瀑布流：多列布局，书卡按列自然下落 -->
    <div v-else class="falls">
      <a v-for="b in filtered" :key="b.pid + '/' + b.bid" class="book-card" :href="b.href">
        <div class="flex items-baseline justify-between gap-2">
          <h3 class="m-0 text-[15px] font-semibold leading-snug">{{ b.title }}</h3>
          <span class="shrink-0 text-[11px] text-[var(--text-3)] tabular-nums">{{ b.n }} 篇</span>
        </div>
        <div class="mt-1 text-xs text-[var(--text-3)]">
          {{ b.project }} · {{ typeLabel(b.type) }} · 同步于 {{ fmtDay(b.updated) || '从未' }}
        </div>
        <div class="read-hint">阅读 →</div>
      </a>
    </div>

    <a class="mt-8 inline-block text-[13px] text-[var(--text-3)] transition-colors hover:text-[var(--brand)]" href="#/">
      ← 返回首页
    </a>
  </div>
</template>

<style scoped>
.falls {
  columns: 1;
  column-gap: 12px;
}
@media (min-width: 768px) {
  .falls {
    columns: 2;
  }
}
@media (min-width: 1280px) {
  .falls {
    columns: 3;
  }
}
.falls > .book-card {
  break-inside: avoid;
  display: block;
  margin-bottom: 12px;
  border: 1px solid var(--divider);
  border-radius: 10px;
  padding: 14px 16px;
  background: var(--bg);
  color: var(--text-1);
  transition: border-color 0.15s;
}
.falls > .book-card:hover {
  border-color: var(--brand);
}
.book-card .read-hint {
  margin-top: 8px;
  border-top: 1px dashed var(--divider);
  padding-top: 7px;
  font-size: 11.5px;
  color: var(--text-3);
  transition: color 0.15s;
}
.book-card:hover .read-hint {
  color: var(--brand);
}
.shelf-filter {
  width: 220px;
  border: 1px solid var(--divider);
  border-radius: var(--radius);
  padding: 6px 10px;
  font-size: 13px;
  background: var(--bg);
  color: var(--text-1);
  outline: none;
  transition: border-color 0.15s;
}
.shelf-filter:focus {
  border-color: var(--brand);
}
</style>
