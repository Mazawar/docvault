<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { isStatic, readUrl } from '@/api/http'
import { getIndex } from '@/api/reading'
import type { ProjectBrief } from '@/api/types'

const route = useRoute()
const pid = computed(() => route.params.pid as string)

const project = ref<ProjectBrief | null>(null)
const loading = ref(true)

/** 复用书架索引：项目与书目数据已齐全，无需单独接口；pid 变化时重载 */
async function load(): Promise<void> {
  loading.value = true
  try {
    const idx = await getIndex()
    project.value = idx.projects.find(p => p.id === pid.value) ?? null
  } finally {
    loading.value = false
  }
}

watch(pid, load, { immediate: true })

interface Row { key: string; title: string; cnt: string; href: string; ext: boolean }

const rows = computed<Row[]>(() => {
  const p = project.value
  if (!p) return []
  const list: Row[] = p.books.map(b => ({
    key: b.id, title: b.title, cnt: `${b.n} 篇`, href: readUrl(p.id, b.id, ''), ext: false
  }))
  if (!isStatic()) {
    list.push(...p.files.map(f => ({ key: f, title: f, cnt: '附件', href: `files/${p.id}/${f}`, ext: true })))
  }
  return list
})

/** 大项目分批渲染：先挂 100 条，筛选或加载更多时再增量挂载 */
const shown = ref(100)
const q = ref('')
watch(q, () => { shown.value = 100 })

const filtered = computed(() => {
  const t = q.value.trim().toLowerCase()
  return t ? rows.value.filter(r => r.title.toLowerCase().includes(t)) : rows.value
})
const visible = computed(() => filtered.value.slice(0, shown.value))

function typeLabel(t: string): string {
  return t === 'notebook' ? '笔记本' : t === 'upload' ? '上传' : 'GitHub'
}

function fmtDay(s: string): string {
  return s && s !== '-' ? s.split(' ')[0] : ''
}
</script>

<template>
  <div class="mx-auto max-w-5xl px-6">
    <div v-if="loading" class="pt-16 text-sm text-[var(--text-3)]">加载中…</div>

    <template v-else-if="project">
      <header class="pb-8 pt-8">
        <router-link class="back-link" to="/">← 返回书架</router-link>
        <div class="mt-4 flex items-baseline justify-between gap-3">
          <h1 class="m-0 text-3xl font-bold tracking-tight">{{ project.name }}</h1>
          <span class="type-badge">{{ typeLabel(project.type) }}</span>
        </div>
        <div class="mt-2 text-[13px] text-[var(--text-3)]">
          同步于 {{ fmtDay(project.updated) || '从未' }} · 共 {{ rows.length }} 项
        </div>
      </header>

      <section class="pb-10">
        <input v-model="q" class="filter-input" type="search" placeholder="筛选书名或附件…" />
        <div
          v-if="!filtered.length"
          class="rounded-lg border border-dashed border-[var(--divider)] p-8 text-center text-sm text-[var(--text-3)]"
        >
          没有匹配的内容
        </div>
        <div v-else class="rounded-lg border border-[var(--divider)]">
          <a
            v-for="(r, i) in visible"
            :key="r.key"
            class="item-row"
            :class="{ 'item-bordered': i > 0 }"
            :href="r.href"
            :target="r.ext ? '_blank' : undefined"
          >
            <span class="truncate">{{ r.title }}</span>
            <span class="shrink-0 text-xs text-[var(--text-3)]">{{ r.cnt }}</span>
          </a>
        </div>
        <div v-if="filtered.length > shown" class="mt-4 text-center">
          <button class="more-btn" @click="shown += 100">
            显示更多（{{ shown }} / {{ filtered.length }}）
          </button>
        </div>
      </section>
    </template>

    <div v-else class="pt-24 text-center">
      <div class="text-sm text-[var(--text-3)]">项目不存在或已被删除</div>
      <div class="mt-5">
        <router-link class="back-btn" to="/">返回书架</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.back-link {
  font-size: 13px;
  color: var(--text-3);
  text-decoration: none;
  transition: color 0.15s;
}
.back-link:hover {
  color: var(--brand);
}
.type-badge {
  flex-shrink: 0;
  border: 1px solid var(--divider);
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 11px;
  color: var(--text-3);
}
.filter-input {
  width: 100%;
  box-sizing: border-box;
  margin-bottom: 12px;
  border: 1px solid var(--divider);
  border-radius: var(--radius);
  padding: 8px 12px;
  font-size: 13.5px;
  background: var(--bg);
  color: var(--text-1);
  outline: none;
  transition: border-color 0.15s;
}
.filter-input:focus {
  border-color: var(--brand);
}
.item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 14px;
  font-size: 13.5px;
  color: var(--text-1);
  transition: background 0.15s, color 0.15s;
}
.item-row:hover {
  background: var(--bg-soft);
  color: var(--brand);
}
.item-bordered {
  border-top: 1px solid var(--divider);
}
.more-btn {
  border: 1px solid var(--divider);
  border-radius: var(--radius);
  padding: 7px 18px;
  font-size: 13px;
  color: var(--text-1);
  background: var(--bg);
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.more-btn:hover {
  border-color: var(--brand);
  color: var(--brand);
}
.back-btn {
  display: inline-block;
  border: 1px solid var(--divider);
  border-radius: var(--radius);
  padding: 7px 18px;
  font-size: 13.5px;
  color: var(--text-1);
  text-decoration: none;
  transition: border-color 0.15s, color 0.15s;
}
.back-btn:hover {
  border-color: var(--brand);
  color: var(--brand);
}
</style>
