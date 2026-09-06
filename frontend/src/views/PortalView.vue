<script setup lang="ts">
import { computed, inject, nextTick, onMounted, ref } from 'vue'
import type { Ref } from 'vue'
import { useRouter } from 'vue-router'
import { isStatic, readUrl, type IndexPayload } from '@/api/http'
import { getIndex } from '@/api/reading'
import { useReadState } from '@/composables/useReadState'
import { takeShelfScroll } from '@/router'
import ShelfCard from '@/components/ShelfCard.vue'
import type { ProjectBrief } from '@/api/types'

const router = useRouter()
const data = ref<IndexPayload | null>(null)
const loading = ref(true)
const { recent, clearAll } = useReadState()
const shelfQ = ref('')
const scroller = inject<Ref<HTMLElement | null>>('pageScroller')

onMounted(async () => {
  try {
    data.value = await getIndex()
    // 从项目页返回书架：等列表渲染完再恢复离开时的位置，避免被短页面截断
    const y = takeShelfScroll()
    if (y > 0) {
      await nextTick()
      if (scroller?.value) scroller.value.scrollTop = y
    }
  } finally {
    loading.value = false
  }
})

function fmtTs(ts: number): string {
  const d = new Date(ts)
  const pad = (n: number) => (n < 10 ? '0' : '') + n
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function matchProject(p: ProjectBrief, t: string): boolean {
  return (
    p.name.toLowerCase().includes(t) ||
    p.books.some(b => b.title.toLowerCase().includes(t) || b.id.toLowerCase().includes(t)) ||
    p.files.some(f => f.toLowerCase().includes(t))
  )
}

const q = computed(() => shelfQ.value.trim().toLowerCase())
const filtered = computed(() => {
  const list = data.value?.projects ?? []
  const t = q.value
  return t ? list.filter(p => matchProject(p, t)) : list
})
const totalBooks = computed(() => (data.value?.projects ?? []).reduce((s, p) => s + p.books.length, 0))

/** 「更多书籍」卡的预览行：全站书单前 3 本 */
const peek = computed(() => {
  const out: { title: string; n: number; href: string }[] = []
  for (const p of data.value?.projects ?? []) {
    for (const b of p.books) {
      out.push({ title: b.title, n: b.n, href: readUrl(p.id, b.id, '') })
    }
  }
  return out.slice(0, 3)
})
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
        <a class="btn-ghost" href="#/notes">我的笔记</a>
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

    <!-- 书架：完整项目列表 + 搜索，末尾「查看更多」进全部书籍瀑布流 -->
    <section id="shelf" class="pb-10 pt-10">
      <div class="mb-5 flex items-center justify-between gap-4">
        <h2 class="text-[15px] font-semibold">书架</h2>
        <input
          v-model="shelfQ"
          class="shelf-filter"
          type="search"
          placeholder="搜索项目或书名…"
        />
      </div>
      <div v-if="loading" class="text-sm text-[var(--text-3)]">加载中…</div>
      <div v-else-if="!data?.projects.length" class="rounded-xl border border-dashed border-[var(--divider)] p-8 text-center">
        <div class="text-sm text-[var(--text-3)]">
          书架还是空的——缓存什么、缓存多少，完全由你决定。
        </div>
        <div class="mt-4 flex justify-center gap-2.5">
          <a class="btn-pri" href="#/admin">去资源管理添加项目</a>
          <a class="btn-ghost" href="#/notes">先写点笔记</a>
        </div>
      </div>
      <div v-else-if="!filtered.length" class="rounded-xl border border-dashed border-[var(--divider)] p-8 text-center text-sm text-[var(--text-3)]">
        没有匹配的项目
      </div>
      <div v-else class="falls">
        <ShelfCard v-for="p in filtered" :key="p.id" :p="p" :q="shelfQ" />
        <div v-if="!q" class="more-card" @click="router.push('/shelf')">
          <div class="flex items-baseline justify-between gap-2">
            <h3 class="m-0 text-[15px] font-semibold leading-snug">更多书籍</h3>
            <span class="shrink-0 text-[11px] text-[var(--text-3)] tabular-nums">{{ totalBooks }} 本</span>
          </div>
          <div class="mt-0.5 mb-2.5 text-xs text-[var(--text-3)]">全部书籍瀑布流</div>
          <ul class="preview-list m-0 list-none border-t border-[var(--divider)] p-0">
            <li v-for="b in peek" :key="b.href">
              <a class="book-row" :href="b.href" @click.stop>
                <span class="truncate">{{ b.title }}</span>
                <span class="cnt">{{ b.n }}</span>
              </a>
            </li>
          </ul>
          <div class="more-hint">查看全部 →</div>
        </div>
      </div>
    </section>

    <!-- 最近阅读（有记录才显示，避免重复空态） -->
    <section v-if="recent.length" class="pb-24">
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-[15px] font-semibold">最近阅读</h2>
        <a
          class="cursor-pointer text-xs text-[var(--text-3)] transition-colors hover:text-[var(--brand)]"
          @click="clearAll()"
        >清空记录</a>
      </div>
      <div class="rounded-lg border border-[var(--divider)]">
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
    </section>

    <footer class="mt-10 border-t border-[var(--divider)] pt-5 pb-2 text-center text-xs text-[var(--text-3)]">
      DocVault · 内容仅供个人学习参考，版权归原作者所有，请支持原站
    </footer>
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
/* 书架瀑布流：多列布局，卡片按列自然下落（与 /shelf 一致） */
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
.falls > :deep(.shelf-card) {
  break-inside: avoid;
  margin-bottom: 12px;
}
/* 「更多书籍」卡与项目卡同款质感 */
.more-card {
  border: 1px solid var(--divider);
  border-radius: 10px;
  padding: 14px 16px;
  background: var(--bg);
  transition: border-color 0.15s;
  cursor: pointer;
}
.more-card:hover {
  border-color: var(--brand);
}
.more-card .book-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 2px;
  font-size: 13.5px;
  color: var(--text-2);
  border-bottom: 1px solid var(--divider);
}
.more-card ul > li:last-child .book-row {
  border-bottom: none;
}
.more-card .book-row:hover {
  color: var(--brand);
}
.more-card .book-row .cnt {
  font-size: 11.5px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}
.more-card .more-hint {
  margin-top: 2px;
  padding: 7px 2px 0;
  border-top: 1px dashed var(--divider);
  font-size: 11.5px;
  color: var(--text-3);
  transition: color 0.15s;
}
.more-card:hover .more-hint {
  color: var(--brand);
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
