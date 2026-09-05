<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getIndex } from '@/api/reading'
import { hitUrl, searchAll } from '@/api/reading'
import type { IndexPayload } from '@/api/http'
import type { SearchHit } from '@/api/types'

const route = useRoute()
const q = ref(String(route.query.q || ''))
const pid = ref('')
const idx = ref<IndexPayload | null>(null)
const hits = ref<SearchHit[]>([])
const searched = ref(false)
const timer = ref<number | null>(null)

async function run() {
  hits.value = await searchAll(q.value, pid.value)
  searched.value = true
}

function onInput() {
  if (timer.value) window.clearTimeout(timer.value)
  timer.value = window.setTimeout(run, 250)
}

onMounted(async () => {
  idx.value = await getIndex()
  if (q.value) await run()
})
</script>

<template>
  <div class="mx-auto max-w-3xl px-5 pb-24" style="padding-top: calc(var(--nav-h) + 36px)">
    <h1 class="mb-5 text-xl font-bold">全文搜索</h1>
    <div class="mb-2 flex flex-wrap items-center gap-2.5">
      <input
        v-model="q"
        placeholder="输入关键词，如：AQS、redis 持久化…"
        class="min-w-0 flex-1 rounded-md border border-[var(--divider)] bg-[var(--bg-alt)] px-3.5 py-2 text-sm outline-none focus:border-[var(--text-3)]"
        @input="onInput"
        @keydown.enter="run"
      />
      <select
        v-model="pid"
        class="rounded-lg border border-[var(--divider)] bg-[var(--bg-alt)] px-2.5 py-2 text-sm outline-none"
        @change="run"
      >
        <option value="">全部项目</option>
        <option v-for="p in idx?.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
    </div>
    <div class="mb-4 text-xs text-[var(--text-3)]">
      {{ searched ? `命中 ${hits.length} 篇` : '输入关键词开始搜索' }}
    </div>

    <div v-for="h in hits" :key="h.pid + '/' + h.bid + '/' + h.slug" class="qitem">
      <a :href="hitUrl(h)" class="text-[var(--text-1)] hover:text-[var(--brand)]">{{ h.pid === '__notes__' ? '📝 ' : '' }}{{ h.title }}</a>
      <!-- eslint-disable-next-line vue/no-v-html — 摘要含后端生成的 <mark> -->
      <div class="snip" v-html="h.snip"></div>
    </div>
    <div v-if="searched && !hits.length" class="mt-8 text-sm text-[var(--text-3)]">无匹配内容</div>
  </div>
</template>

<style scoped>
.qitem {
  padding: 10px 8px;
  border-bottom: 1px dashed var(--divider);
}
.qitem:hover {
  background: var(--bg-soft);
}
.qitem a {
  font-size: 14.5px;
  font-weight: 600;
}
.snip {
  margin-top: 3px;
  font-size: 12.5px;
  color: var(--text-3);
  line-height: 1.7;
}
.snip :deep(mark) {
  background: rgba(255, 208, 75, 0.45);
  color: inherit;
  border-radius: 3px;
  padding: 0 1px;
}
</style>
