<script setup lang="ts">
import { computed } from 'vue'
import { isStatic, readUrl } from '@/api/http'
import type { ProjectBrief } from '@/api/types'

/** 书架卡片（首页与全部书架页共用）。q 为搜索词：书名命中时预览收窄到匹配的书 */
const props = withDefaults(defineProps<{ p: ProjectBrief; q?: string }>(), { q: '' })

const query = computed(() => props.q.trim().toLowerCase())
const nameHit = computed(() => !!query.value && props.p.name.toLowerCase().includes(query.value))
const filtered = computed(() => !!query.value && !nameHit.value)

interface PreviewItem { key: string; title: string; cnt: string; href: string; ext: boolean }

/** 卡片只放最多 3 条预览；搜索命中书名时先过滤书目再截取，保证匹配的书一定出现 */
const preview = computed<PreviewItem[]>(() => {
  const p = props.p
  const hit = (s: string) => s.toLowerCase().includes(query.value)
  const books = !query.value || nameHit.value
    ? p.books
    : p.books.filter(b => hit(b.title) || hit(b.id))
  const items: PreviewItem[] = books.map(b => ({
    key: b.id, title: b.title, cnt: String(b.n), href: readUrl(p.id, b.id, ''), ext: false
  }))
  if (!isStatic() && (!query.value || nameHit.value)) {
    items.push(...p.files.map(f => ({ key: f, title: f, cnt: '附件', href: `files/${p.id}/${f}`, ext: true })))
  }
  return items.slice(0, 3)
})

const total = computed(() => props.p.books.length + (isStatic() ? 0 : props.p.files.length))

function typeLabel(t: string): string {
  return t === 'notebook' ? '笔记本' : t === 'upload' ? '上传' : 'GitHub'
}

function fmtDay(s: string): string {
  return s && s !== '-' ? s.split(' ')[0] : ''
}
</script>

<template>
  <div class="shelf-card" @click="$router.push(`/project/${p.id}`)">
    <div class="flex items-baseline justify-between gap-2">
      <h3 class="m-0 text-[15px] font-semibold leading-snug">{{ p.name }}</h3>
      <span class="shrink-0 text-[11px] text-[var(--text-3)]">{{ typeLabel(p.type) }}</span>
    </div>
    <div class="mt-0.5 mb-2.5 text-xs text-[var(--text-3)]">
      同步于 {{ fmtDay(p.updated) || '从未' }} · 共 {{ total }} 项
    </div>
    <ul class="preview-list m-0 list-none border-t border-[var(--divider)] p-0">
      <li v-for="it in preview" :key="it.key">
        <a class="book-row" :href="it.href" :target="it.ext ? '_blank' : undefined" @click.stop>
          <span class="truncate">{{ it.title }}</span>
          <span class="cnt">{{ it.cnt }}</span>
        </a>
      </li>
      <li v-if="!total" class="px-0.5 py-2 text-xs text-[var(--text-3)]">尚未同步</li>
      <li v-else-if="filtered && !preview.length" class="px-0.5 py-2 text-xs text-[var(--text-3)]">没有匹配的书名</li>
    </ul>
    <div v-if="!filtered && total > preview.length" class="more-hint">
      还有 {{ total - preview.length }} 项 · 查看全部
    </div>
  </div>
</template>

<style scoped>
.shelf-card {
  border: 1px solid var(--divider);
  border-radius: 10px;
  padding: 14px 16px;
  background: var(--bg);
  transition: border-color 0.15s;
  cursor: pointer;
}
.shelf-card:hover {
  border-color: var(--text-3);
}
.book-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 2px;
  font-size: 13.5px;
  color: var(--text-2);
  border-bottom: 1px solid var(--divider);
}
ul > li:last-child .book-row {
  border-bottom: none;
}
.book-row:hover {
  color: var(--brand);
}
.book-row .cnt {
  font-size: 11.5px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}
.more-hint {
  margin-top: 2px;
  padding: 7px 2px 0;
  border-top: 1px dashed var(--divider);
  font-size: 11.5px;
  color: var(--text-3);
  transition: color 0.15s;
}
.shelf-card:hover .more-hint {
  color: var(--brand);
}
</style>
