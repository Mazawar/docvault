<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit } from '@element-plus/icons-vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '../../composables/useAdmin'

const { ov } = useAdmin()
const amPid = ref('')
const amBid = ref('')
const amRows = ref<{
  slug: string; title: string; hidden: boolean
  titleOverride: boolean; bodyOverride: boolean; sort: number | null
}[]>([])
const amLoaded = ref(false)
const amBooks = computed(() => ov.value?.projects.find((p) => p.id === amPid.value)?.books || [])
const amVisible = computed(() => amRows.value.slice(0, 400))

async function loadArticles() {
  if (!amPid.value || !amBid.value) { amRows.value = []; return }
  amRows.value = (await adminApi.articleList(amPid.value, amBid.value)).items
}
function onAmProject(pid: string) {
  amPid.value = pid
  amBid.value = amBooks.value[0]?.id || ''
  loadArticles()
}
async function onAmBook() {
  await loadArticles()
}

async function amToggleHidden(r: { slug: string; hidden: boolean }) {
  await adminApi.articleSet({ pid: amPid.value, bid: amBid.value, slug: r.slug, hidden: !r.hidden })
  await loadArticles()
}
async function amMove(r: { slug: string }, dir: 'up' | 'down') {
  await adminApi.articleMove({ pid: amPid.value, bid: amBid.value, slug: r.slug, dir })
  await loadArticles()
}
const bodyDlg = ref(false)
const bodyForm = ref({ slug: '', title: '', content: '' })
const bodySaving = ref(false)
async function amEditBody(r: { slug: string; title: string }) {
  const art = await import('@/api/reading')
    .then((m) => m.getArticle(amPid.value, amBid.value, r.slug))
  bodyForm.value = { slug: r.slug, title: art.title, content: art.md || '' }
  bodyDlg.value = true
}
async function saveBody() {
  bodySaving.value = true
  try {
    await adminApi.articleSet({
      pid: amPid.value, bid: amBid.value, slug: bodyForm.value.slug,
      body: bodyForm.value.content, title: bodyForm.value.title
    })
    bodyDlg.value = false
    ElMessage.success('已保存为本地覆盖（同步不会覆盖你的修改）')
    await loadArticles()
  } finally {
    bodySaving.value = false
  }
}
async function amReset(r: { slug: string; title: string }) {
  ElMessageBox.confirm(`恢复「${r.title}」为原文（清除隐藏/标题/正文的本地覆盖）？`, '恢复默认',
    { type: 'warning', confirmButtonText: '恢复' })
    .then(async () => {
      await adminApi.articleReset({ pid: amPid.value, bid: amBid.value, slug: r.slug })
      await loadArticles()
      ElMessage.success('已恢复默认')
    }).catch(() => {})
}
</script>

<template>
  <div class="card">
    <h2>文章管理</h2>
    <div class="flex flex-wrap items-center gap-2.5 mb-3">
      <el-select v-model="amPid" placeholder="项目" class="!w-52" @change="onAmProject">
        <el-option v-for="p in ov?.projects" :key="p.id" :value="p.id" :label="p.name" />
      </el-select>
      <el-select v-model="amBid" placeholder="书" class="!w-52" :disabled="!amPid" @change="onAmBook">
        <el-option v-for="b in amBooks" :key="b.id" :value="b.id" :label="`${b.title} (${b.n})`" />
      </el-select>
      <span class="mut" v-if="amLoaded">
        共 {{ amRows.length }} 篇（隐藏 {{ amRows.filter(r => r.hidden).length }}
        · 本地修改 {{ amRows.filter(r => r.titleOverride || r.bodyOverride).length }}）
      </span>
    </div>
    <template v-if="amLoaded">
      <div v-for="r in amVisible" :key="r.slug" class="amrow">
        <div class="amorder">
          <button class="ammove" title="上移" @click="amMove(r, 'up')">↑</button>
          <button class="ammove" title="下移" @click="amMove(r, 'down')">↓</button>
        </div>
        <div class="ammain">
          <a
            class="amtitle" :class="{ hidden: r.hidden }"
            :href="`#/read/${amPid}/${amBid}/${r.slug}`" target="_blank"
            :title="r.title"
          >{{ r.title }}</a>
          <span v-if="r.hidden" class="amtag warn">已隐藏</span>
          <span v-if="r.titleOverride" class="amtag">改标题</span>
          <span v-if="r.bodyOverride" class="amtag">改正文</span>
          <span class="amslug">{{ r.slug }}</span>
        </div>
        <div class="amops">
          <el-switch
            size="small"
            :model-value="!r.hidden"
            title="切换显示/隐藏"
            @change="amToggleHidden(r)"
          />
          <el-button size="small" text type="primary" :icon="Edit" @click="amEditBody(r)">编辑</el-button>
          <el-button size="small" text @click="amReset(r)">恢复默认</el-button>
        </div>
      </div>
      <div v-if="amRows.length > 400" class="mut text-center text-xs pt-3">
        仅显示前 400 篇，请用全局搜索（Ctrl+K）定位其余文章
      </div>
    </template>
    <div v-else class="mut text-[13px]">选择项目和书后加载文章列表</div>

    <el-dialog v-model="bodyDlg" :title="'编辑正文 · ' + bodyForm.title" width="720" class="bodydlg">
      <el-input v-model="bodyForm.content" type="textarea" :rows="20" spellcheck="false" class="bodyta" />
      <template #footer>
        <el-button @click="bodyDlg = false">取消</el-button>
        <el-button type="primary" :loading="bodySaving" @click="saveBody">保存覆盖</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.amrow {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 4px;
  border-bottom: 1px dashed var(--divider);
}
.amrow:hover { background: var(--bg-soft); }
.amorder { display: flex; flex-direction: column; gap: 1px; }
.ammove {
  border: none;
  background: transparent;
  color: var(--text-3);
  cursor: pointer;
  font-size: 11px;
  line-height: 1;
  padding: 1px 4px;
}
.ammove:hover { color: var(--brand); }
.ammain {
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.amtitle {
  font-size: 13.5px;
  color: var(--text-1);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 420px;
}
.amtitle:hover { color: var(--brand); }
.amtitle.hidden { text-decoration: line-through; color: var(--text-3); }
.amtag {
  font-size: 11px;
  border-radius: 5px;
  padding: 0 6px;
  background: var(--brand-soft);
  color: var(--brand);
  white-space: nowrap;
}
.amtag.warn {
  background: rgba(217, 119, 6, 0.12);
  color: #d97706;
}
.amslug {
  font-size: 11px;
  color: var(--text-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 260px;
}
.amops { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
@media (max-width: 768px) {
  .ammain { flex-direction: column; align-items: flex-start; gap: 3px; }
  .amslug { max-width: 100%; }
  .amops { flex-wrap: wrap; }
}
</style>
