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

function fmtDay(s: string): string {
  return s && s !== '-' ? s.split(' ')[0] : ''
}
</script>

<template>
  <div class="mx-auto max-w-5xl px-6">
    <!-- Hero：VitePress 风格（渐变标题 + 需求回归） -->
    <section class="pb-12 pt-20 text-center">
      <h1 class="hero-title m-0 text-5xl font-bold tracking-tight">DocVault</h1>
      <p class="mx-auto mb-7 mt-4 max-w-xl text-[17px] leading-relaxed text-[var(--text-2)]">
        多源技术文档缓存站 —— 在线可更新，离线可携带，看过的每一篇都被记住
      </p>
      <div class="flex justify-center gap-2.5">
        <a class="btn-pri" href="#shelf">开始阅读</a>
        <a v-if="!isStatic()" class="btn-ghost" href="#/admin">管理资源</a>
      </div>
    </section>

    <!-- 特性：纯文字栅格，无卡片装饰 -->
    <section class="grid grid-cols-2 gap-x-8 gap-y-6 border-b border-[var(--divider)] py-9 lg:grid-cols-4">
      <div>
        <div class="mb-1 text-[13.5px] font-semibold">多源缓存</div>
        <div class="text-[13px] leading-relaxed text-[var(--text-3)]">GitHub 仓库一键镜像，图片全部本地化</div>
      </div>
      <div>
        <div class="mb-1 text-[13.5px] font-semibold">全文搜索</div>
        <div class="text-[13px] leading-relaxed text-[var(--text-3)]">SQLite FTS5，中文短词即输即搜</div>
      </div>
      <div>
        <div class="mb-1 text-[13.5px] font-semibold">阅读记忆</div>
        <div class="text-[13px] leading-relaxed text-[var(--text-3)]">已读标记、最近浏览，接着上次继续</div>
      </div>
      <div>
        <div class="mb-1 text-[13.5px] font-semibold">离线携带</div>
        <div class="text-[13px] leading-relaxed text-[var(--text-3)]">导出静态资源包，内网部署零依赖</div>
      </div>
    </section>

    <!-- 书架 -->
    <section id="shelf" class="pb-10 pt-10">
      <h2 class="mb-5 text-[15px] font-semibold">书架</h2>
      <div v-if="loading" class="text-sm text-[var(--text-3)]">加载中…</div>
      <div v-else-if="!data?.projects.length" class="rounded-lg border border-[var(--divider)] p-6 text-sm text-[var(--text-3)]">
        还没有项目。到管理台添加 GitHub 仓库，或执行 <code class="inline-code">python -m src.main sync all</code>。
      </div>
      <div class="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        <div v-for="p in data?.projects" :key="p.id" class="shelf-card">
          <div class="flex items-baseline justify-between gap-2">
            <h3 class="m-0 text-[15px] font-semibold leading-snug">{{ p.name }}</h3>
            <span class="shrink-0 text-[11px] text-[var(--text-3)]">{{ p.type === 'upload' ? '上传' : 'GitHub' }}</span>
          </div>
          <div class="mt-0.5 mb-2.5 text-xs text-[var(--text-3)]">
            同步于 {{ fmtDay(p.updated) || '从未' }}
          </div>
          <ul class="m-0 list-none border-t border-[var(--divider)] p-0">
            <li v-for="b in p.books" :key="b.id">
              <a class="book-row" :href="readUrl(p.id, b.id, '')">
                <span class="truncate">{{ b.title }}</span>
                <span class="cnt">{{ b.n }}</span>
              </a>
            </li>
            <li v-for="f in isStatic() ? [] : p.files" :key="f">
              <a class="book-row" :href="`files/${p.id}/${f}`" target="_blank">
                <span class="truncate">{{ f }}</span>
                <span class="cnt">附件</span>
              </a>
            </li>
            <li v-if="!p.books.length" class="px-0.5 py-2 text-xs text-[var(--text-3)]">尚未同步</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- 最近阅读 -->
    <section class="pb-24">
      <h2 class="mb-4 text-[15px] font-semibold">最近阅读</h2>
      <div v-if="recent.length" class="rounded-lg border border-[var(--divider)]">
        <router-link
          v-for="(x, i) in recent.slice(0, 8)"
          :key="x.u"
          :to="x.u.replace('#', '')"
          class="recent-row"
          :class="{ 'border-t': i > 0 }"
        >
          <span class="truncate">{{ x.t }}</span>
          <span class="shrink-0 text-xs text-[var(--text-3)]">{{ fmtTs(x.ts) }}</span>
        </router-link>
      </div>
      <div v-else class="text-sm text-[var(--text-3)]">暂无记录，读一篇文章试试</div>
    </section>
  </div>
</template>

<style scoped>
.btn-pri {
  display: inline-block;
  border-radius: var(--radius);
  padding: 7px 18px;
  font-size: 13.5px;
  font-weight: 600;
  background: var(--text-1);
  color: var(--bg);
  border: 1px solid var(--text-1);
  cursor: pointer;
}
.btn-pri:hover {
  opacity: 0.85;
  color: var(--bg);
}
.btn-ghost {
  display: inline-block;
  border-radius: var(--radius);
  padding: 7px 18px;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--text-1);
  border: 1px solid var(--divider);
  cursor: pointer;
  transition: border-color 0.15s;
}
.btn-ghost:hover {
  border-color: var(--text-3);
  color: var(--text-1);
}
.shelf-card {
  border: 1px solid var(--divider);
  border-radius: 10px;
  padding: 14px 16px;
  background: var(--bg);
  transition: border-color 0.15s;
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
.recent-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 14px;
  font-size: 13.5px;
  color: var(--text-1);
}
.recent-row:hover {
  background: var(--bg-soft);
  color: var(--text-1);
}
.recent-row.border-t {
  border-top: 1px solid var(--divider);
}
.inline-code {
  background: var(--inline-code-bg);
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 12.5px;
}
</style>
