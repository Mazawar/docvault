<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { isStatic, readUrl, type IndexPayload } from '@/api/http'
import { getIndex } from '@/api/reading'
import { useReadState } from '@/composables/useReadState'

const data = ref<IndexPayload | null>(null)
const loading = ref(true)
const { recent } = useReadState()

onMounted(async () => {
  try {
    data.value = await getIndex()
  } finally {
    loading.value = false
  }
})

function fmtTs(ts: number): string {
  const d = new Date(ts)
  const pad = (n: number) => (n < 10 ? '0' : '') + n
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
</script>

<template>
  <div>
    <section class="px-6 pb-10 pt-28 text-center">
      <h1
        class="m-0 bg-gradient-to-r from-[var(--brand)] to-[#41d1ff] bg-clip-text text-4xl font-bold leading-tight tracking-tight text-transparent md:text-5xl"
      >
        DocVault
      </h1>
      <p class="mx-auto mt-5 mb-8 max-w-xl text-lg text-[var(--text-2)] md:text-xl">
        多源技术文档缓存站 · 在线可更新，离线可携带
      </p>
      <div class="flex flex-wrap justify-center gap-3.5">
        <a class="btn-pri" href="#books">开始阅读</a>
        <a v-if="!isStatic()" class="btn-alt" href="#/admin">管理资源</a>
      </div>
    </section>

    <section class="mx-auto grid max-w-4xl grid-cols-1 gap-4 px-6 pb-10 sm:grid-cols-2 lg:grid-cols-4">
      <div class="feat">📥<b>多源缓存</b><span>GitHub 教程一键镜像，图片全部本地化</span></div>
      <div class="feat">🔍<b>全文搜索</b><span>SQLite FTS5，中文短词即输即搜</span></div>
      <div class="feat">✅<b>阅读记忆</b><span>已读打勾、最近浏览，接着上次继续</span></div>
      <div class="feat">📦<b>一包带走</b><span>导出离线 zip，拷进内网开箱即用</span></div>
    </section>

    <section id="books" class="mx-auto max-w-5xl px-6 pb-24">
      <h2 class="mb-4 mt-10 text-[22px]">📚 书架</h2>
      <div v-if="loading" class="text-[var(--text-3)]">加载中…</div>
      <div v-else-if="!data?.projects.length" class="card p-6 text-[var(--text-3)]">
        还没有项目。到管理台添加 GitHub 仓库，或执行 <code>python -m src.main sync all</code>。
      </div>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div v-for="p in data?.projects" :key="p.id" class="card transition-colors hover:border-[var(--brand)]">
          <h3 class="mb-0.5 text-[17px]">{{ p.name }}</h3>
          <div class="mb-3 text-xs text-[var(--text-3)]">同步: {{ p.updated }} · {{ p.type }}</div>
          <ul class="m-0 list-none p-0">
            <li v-for="b in p.books" :key="b.id" class="my-1">
              <a class="text-[var(--text-1)] hover:text-[var(--brand)]" :href="readUrl(p.id, b.id, '')">
                📖 {{ b.title }} <span class="text-xs text-[var(--text-3)]">({{ b.n }})</span>
              </a>
            </li>
            <li v-for="f in isStatic() ? [] : p.files" :key="f" class="my-1">
              <a class="text-[var(--text-1)] hover:text-[var(--brand)]" :href="`files/${p.id}/${f}`" target="_blank">
                📎 {{ f }}
              </a>
            </li>
            <li v-if="!p.books.length" class="text-xs text-[var(--text-3)]">尚未同步</li>
          </ul>
        </div>
      </div>

      <h2 class="mb-4 mt-12 text-[22px]">🕘 最近阅读</h2>
      <div class="card p-5">
        <ul v-if="recent.length" class="m-0 list-none p-0">
          <li v-for="x in recent.slice(0, 8)" :key="x.u" class="flex justify-between gap-2.5">
            <a :href="x.u" class="truncate text-[var(--text-1)] hover:text-[var(--brand)]">{{ x.t }}</a>
            <span class="shrink-0 text-xs text-[var(--text-3)]">{{ fmtTs(x.ts) }}</span>
          </li>
        </ul>
        <div v-else class="text-sm text-[var(--text-3)]">暂无记录，读一篇文章试试</div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.btn-pri {
  border-radius: 22px;
  padding: 9px 22px;
  font-size: 15px;
  font-weight: 600;
  background: var(--brand);
  color: #fff;
  border: 1px solid var(--brand);
}
.btn-pri:hover {
  background: var(--brand-hover);
  color: #fff;
}
.btn-alt {
  border-radius: 22px;
  padding: 9px 22px;
  font-size: 15px;
  font-weight: 600;
  background: var(--bg-soft);
  color: var(--text-1);
  border: 1px solid var(--divider);
}
.btn-alt:hover {
  border-color: var(--brand);
  color: var(--brand);
}
.feat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  border: 1px solid var(--divider);
  border-radius: 14px;
  padding: 18px;
  font-size: 13px;
  color: var(--text-2);
  line-height: 1.6;
  text-align: left;
}
.feat b {
  color: var(--text-1);
  font-size: 15px;
}
.card {
  border: 1px solid var(--divider);
  border-radius: 14px;
  padding: 18px 20px;
  background: var(--bg);
}
</style>
