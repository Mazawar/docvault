<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Delete, Edit, Download, Upload, MoreFilled } from '@element-plus/icons-vue'
import { adminApi } from '@/api/admin'
import { modeRef } from '@/api/http'
import type { Overview, ProjectFull } from '@/api/types'

const router = useRouter()
const ov = ref<Overview | null>(null)
const staticMode = computed(() => modeRef.value === 'static')
let timer: number | null = null

async function refresh() {
  if (staticMode.value) return
  ov.value = await adminApi.overview()
  loadStorage()
}

onMounted(async () => {
  if (staticMode.value) return
  await refresh()
  timer = window.setInterval(refresh, 3000)
})
onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})

const busy = reactive<Record<string, boolean>>({})

async function act(key: string, fn: () => Promise<unknown>, okMsg: string) {
  if (busy[key]) return
  busy[key] = true
  try {
    await fn()
    ElMessage.success(okMsg)
    setTimeout(refresh, 600)
    return true
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    busy[key] = false
  }
}

const syncOne = (pid: string) => act(`sync-${pid}`, () => adminApi.sync(pid), `已提交同步：${pid}`)

/* ---------- 存储与清理 ---------- */
const st = ref<Awaited<ReturnType<typeof adminApi.storage>> | null>(null)
async function loadStorage() {
  if (staticMode.value) return
  st.value = await adminApi.storage().catch(() => null)
}
const purgeRepos = (pid: string, name: string) =>
  ElMessageBox.confirm(
    `清理「${name}」的仓库缓存？文章与图片保留，阅读不受影响；下次同步会自动重新克隆。`,
    '清理仓库缓存', { confirmButtonText: '清理', type: 'warning' }
  ).then(() => act(`purge-${pid}`, () => adminApi.purgeRepos(pid), '已提交清理，进度见任务队列'))
    .then(loadStorage).catch(() => {})
const purgeOrphan = () =>
  act('purge-orphan', () => adminApi.purgeOrphanAssets(), '已提交清理，进度见任务队列')
    .then(loadStorage)
const syncAll = () => act('sync-all', () => adminApi.sync(''), '已提交全量同步')
const doExport = () => act('export', () => adminApi.exportZip(), '已提交静态站生成')
const doExportPack = () => act('export-pack', () => adminApi.exportPack(), '已提交资源包生成')
const packInput = ref<HTMLInputElement | null>(null)
const doImportPack = () => {
  ElMessageBox.confirm(
    '导入按项目合并：包内项目覆盖同 id 的现有项目，图片/笔记/PDF 跳过已有文件。继续导入？',
    '导入资源包',
    { confirmButtonText: '选择文件导入', cancelButtonText: '取消', type: 'warning' }
  )
    .then(() => packInput.value?.click())
    .catch(() => {})
}
const onPackFile = (e: Event) => {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  act('import-pack', () => adminApi.importPack(f), `已提交导入：${f.name}`)
  ;(e.target as HTMLInputElement).value = ''
}
const doPdf = () => {
  if (!pdfPid.value || !pdfBid.value) return ElMessage.warning('选择项目和书')
  act(`pdf-${pdfPid.value}-${pdfBid.value}`, () => adminApi.exportPdf(pdfPid.value, pdfBid.value), '已提交 PDF 导出')
}

/* ---------- 统计 ---------- */
const stats = computed(() => {
  const ps = ov.value?.projects || []
  const books = ps.reduce((s, p) => s + p.books.length, 0)
  const articles = ps.reduce((s, p) => s + p.books.reduce((s2, b) => s2 + b.n, 0), 0)
  return { projects: ps.length, books, articles }
})

/* ---------- 项目编辑 ---------- */
const formOpen = ref(false)
const editing = ref('')
const form = reactive({ id: '', name: '', type: 'github', repo: '', root: '', booksText: '', gtText: '' })

function parseGT(t: string): Record<string, Record<string, string>> {
  const gt: Record<string, Record<string, string>> = {}
  for (const line of t.split('\n')) {
    const i = line.indexOf('=')
    if (i <= 0) continue
    const path = line.slice(0, i).trim()
    const val = line.slice(i + 1).trim()
    const slash = path.indexOf('/')
    if (slash > 0 && path.slice(0, slash).trim() && path.slice(slash + 1).trim()) {
      const bid = path.slice(0, slash).trim()
      const dir = path.slice(slash + 1).trim()
      ;(gt[bid] = gt[bid] || {})[dir] = val
    }
  }
  return gt
}

function parseBooks(t: string): Record<string, string> {
  const books: Record<string, string> = {}
  for (const line of t.split('\n')) {
    const i = line.indexOf('=')
    if (i > 0 && line.slice(0, i).trim()) books[line.slice(0, i).trim()] = line.slice(i + 1).trim()
  }
  return books
}

function newProject() {
  editing.value = ''
  Object.assign(form, { id: '', name: '', type: 'github', repo: '', root: '', booksText: '', gtText: '' })
  formOpen.value = true
}

async function editProject(pid: string) {
  const list = await adminApi.listProjects()
  const p: ProjectFull | undefined = list.find((x) => x.id === pid)
  if (!p) return
  editing.value = pid
  Object.assign(form, {
    id: p.id,
    name: p.name,
    type: p.type,
    repo: p.repo || '',
    root: p.root || '',
    booksText: Object.entries(p.books || {})
      .map(([k, v]) => `${k}=${v}`)
      .join('\n'),
    gtText: Object.entries((p as any).group_titles || {})
      .map(([bid, m]) =>
        Object.entries(m as Record<string, string>)
          .map(([d, t]) => `${bid}/${d}=${t}`)
          .join('\n')
      )
      .filter(Boolean)
      .join('\n')
  })
  formOpen.value = true
}

async function saveProject() {
  try {
    await adminApi.saveProject({
      id: form.id.trim(),
      name: form.name.trim(),
      type: form.type,
      repo: form.repo.trim(),
      root: form.root.trim(),
      books: form.type === 'github' ? parseBooks(form.booksText) : {},
      groupTitles: form.type === 'github' ? parseGT(form.gtText) : {}
    })
    formOpen.value = false
    ElMessage.success('已保存，同步任务已提交')
    setTimeout(refresh, 600)
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

function delProject(pid: string) {
  ElMessageBox.confirm(`删除项目「${pid}」？其仓库缓存、文章、PDF 将一并清理`, '确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消'
  }).then(() => act(`del-${pid}`, () => adminApi.deleteProject(pid), '已删除'))
}

/* ---------- PDF ---------- */
const pdfPid = ref('')
const pdfBid = ref('')
const pdfBooks = computed(() => ov.value?.projects.find((p) => p.id === pdfPid.value)?.books || [])

</script>

<template>
  <div class="wrap">
    <el-alert
      v-if="staticMode"
      title="只读模式：管理功能不可用"
      description="当前运行在生成的静态站上。同步、上传、生成需要在完整部署的 DocVault 中操作。"
      type="info"
      show-icon
      :closable="false"
      class="mb-5"
    />

    <!-- 页头：标题 + 统计 + 主操作 -->
    <div class="pagehead">
      <div>
        <h1>资源管理</h1>
        <div class="stats">
          <span>{{ stats.projects }} 个项目</span>
          <span class="dot"></span>
          <span>{{ stats.books }} 本书</span>
          <span class="dot"></span>
          <span>{{ stats.articles }} 篇文章</span>
      </div>
      </div>
      <div class="actions">
        <el-button :icon="Refresh" :loading="busy['sync-all']" @click="syncAll">全部同步</el-button>
        <el-button type="primary" :icon="Upload" :loading="busy['import-pack']" @click="doImportPack">导入资源包</el-button>
        <input ref="packInput" type="file" accept=".zip" style="display: none" @change="onPackFile" />
      </div>
    </div>

    <!-- 项目卡片栅格 -->
    <div class="projgrid">
      <div v-for="p in ov?.projects" :key="p.id" class="projcard">
        <div class="projhead">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <b class="truncate text-[15px]">{{ p.name }}</b>
              <span class="ptype">{{ p.type === 'upload' ? '上传' : 'GitHub' }}</span>
            </div>
            <div class="mut mt-0.5 truncate">{{ p.type === 'github' ? p.repo : '本地目录' }} · 同步于 {{ p.updated || '从未' }}</div>
          </div>
          <el-dropdown trigger="click" @command="(c: string) => c === 'edit' ? editProject(p.id) : c === 'purge' ? purgeRepos(p.id, p.name) : delProject(p.id)">
            <el-button text :icon="MoreFilled" class="morebtn" />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit" :icon="Edit">编辑</el-dropdown-item>
                <el-dropdown-item v-if="p.type === 'github'" command="purge">清理仓库缓存</el-dropdown-item>
                <el-dropdown-item command="del" :icon="Delete" divided>删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div class="flex flex-wrap gap-1.5 py-3">
          <el-tag
            v-for="b in p.books"
            :key="b.id"
            class="booktag"
            @click="router.push(`/read/${p.id}/${b.id}/`)"
          >
            {{ b.title }} · {{ b.n }}
          </el-tag>
          <span v-if="!p.books.length" class="mut text-xs">尚未同步</span>
        </div>
        <div class="projfoot">
          <span class="mut">
            {{ p.books.length }} 本书
            <template v-if="st?.projects.find(x => x.id === p.id)?.repos_mb">
              · 仓库 {{ st.projects.find(x => x.id === p.id)?.repos_mb }}MB
            </template>
          </span>
          <el-button
            size="small"
            :icon="Refresh"
            :loading="busy['sync-' + p.id]"
            @click="syncOne(p.id)"
          >同步</el-button>
        </div>
      </div>

      <button class="addcard" @click="newProject">
        <el-icon :size="18"><Plus /></el-icon>
        添加项目
      </button>
    </div>

    <!-- 导出中心：两种产物，用途一目了然 -->
    <div class="card">
      <h2>导出中心</h2>
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div class="packcard">
          <div class="ptitle">📦 数据资源包 <el-tag size="small" type="success">推荐</el-tag></div>
          <p class="pdesc">完整数据：数据库 + 图片 + 笔记 + PDF + 前端产物。拷到内网机器导入 DocVault，即为完整实例——搜索、管理、笔记、阅读记忆全部可用，无需联网和 npm。</p>
          <div class="prow">
            <el-button size="small" :loading="busy['export-pack']" @click="doExportPack">生成资源包</el-button>
            <a v-if="ov?.pack" :href="adminApi.downloadPackUrl">
              <el-button size="small" type="primary" :icon="Download">下载资源包</el-button>
            </a>
            <span v-if="ov?.pack" class="pmut">{{ ov.pack }}（{{ fmtSize(ov.packSize) }}）</span>
            <span v-else-if="!busy['export-pack']" class="pmut">尚未生成</span>
          </div>
        </div>
        <div class="packcard">
          <div class="ptitle">🌐 只读静态站</div>
          <p class="pdesc">预渲染纯静态站点：不需要本程序，解压后 nginx / 任意静态服务器直接浏览。适合分享给没有安装 DocVault 的人。</p>
          <div class="prow">
            <el-button size="small" :loading="busy.export" @click="doExport">生成静态站</el-button>
            <a v-if="ov?.zip" :href="adminApi.downloadUrl">
              <el-button size="small" type="primary" :icon="Download">下载静态站</el-button>
            </a>
            <span v-if="ov?.zip" class="pmut">{{ ov.zip }}（{{ fmtSize(ov.zipSize) }}）</span>
            <span v-else-if="!busy.export" class="pmut">尚未生成</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 存储与清理 -->
    <div class="card" v-if="st">
      <h2>存储与清理</h2>
      <div class="flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px]">
        <span>图床 <b>{{ st.assets.mb }}MB</b> / {{ st.assets.files }} 个</span>
        <span>仓库缓存 <b>{{ st.repos_mb }}MB</b></span>
        <span>数据库 <b>{{ st.db_mb }}MB</b></span>
        <span>笔记 <b>{{ st.notes_mb }}MB</b></span>
        <span>导出产物 <b>{{ st.dist_mb }}MB</b></span>
      </div>
      <div class="mt-3 flex flex-wrap items-center gap-2.5">
        <el-button size="small" @click="purgeOrphan" :loading="busy['purge-orphan']">清理无效图片</el-button>
        <span class="mut">删除图床中未被任何文章/笔记引用的文件；仓库缓存请在各项目卡「···」里清理</span>
      </div>
    </div>

    <!-- 导出 PDF：按书生成阅读资源 -->
    <div class="grid grid-cols-1 gap-4 py-2 lg:grid-cols-5">
      <div class="card lg:col-span-3">
        <h2>导出 PDF（按书）</h2>
        <div class="flex flex-wrap items-center gap-2.5">
          <el-select v-model="pdfPid" placeholder="项目" class="!w-44" @change="pdfBid = ''">
            <el-option v-for="p in ov?.projects" :key="p.id" :value="p.id" :label="p.name" />
          </el-select>
          <el-select v-model="pdfBid" placeholder="书" class="!w-44">
            <el-option v-for="b in pdfBooks" :key="b.id" :value="b.id" :label="`${b.title} (${b.n})`" />
          </el-select>
        </div>
        <el-button class="mt-2.5" :loading="busy.export" @click="doPdf">导出整本书</el-button>
        <div class="mut mt-2 truncate">已有：{{ ov?.pdfs.join('　') || '无' }}</div>
      </div>
      <div class="card lg:col-span-2">
        <h2>笔记维护</h2>
        <div class="mut" style="line-height: 1.9">
          笔记的写作与内容管理已独立为「笔记」模块（导航「笔记」），支持 CSDN 式编辑器、
          标签、双链、传图与 PDF 导出。本页仅维护在线缓存资源。
        </div>
      </div>
    </div>

    <div class="card mt-4">
      <h2>任务队列</h2>
      <pre class="jobpre">{{ (ov?.jobs || []).length ? '' : '(暂无任务)' }}<template v-for="j in ov?.jobs" :key="j.id"><span>{{ j.status === 'done' ? '✓' : j.status === 'error' ? '✗' : '…' }} {{ j.name }}  {{ j.created }} → {{ j.finished || '进行中' }}</span>
<span v-for="(l, i) in j.log" :key="i" class="mut">  {{ l }}</span>
</template></pre>
    </div>

    <el-dialog v-model="formOpen" :title="editing ? '编辑项目 · ' + editing : '新增项目'" width="560">
      <el-form label-width="90" size="default">
        <el-form-item label="id">
          <el-input v-model="form.id" :disabled="!!editing" placeholder="小写字母数字-" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="form.type">
            <el-radio-button value="github">GitHub 仓库</el-radio-button>
            <el-radio-button value="upload">本地上传</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <template v-if="form.type === 'github'">
          <el-form-item label="仓库">
            <el-input v-model="form.repo" placeholder="owner/repo，如 doocs/advanced-java" />
          </el-form-item>
          <el-form-item label="md 根目录">
            <el-input v-model="form.root" placeholder="默认 ." />
          </el-form-item>
          <el-form-item label="多本书">
            <el-input
              v-model="form.booksText"
              type="textarea"
              :rows="4"
              placeholder="每行 目录=书名，如：&#10;network=图解网络&#10;mysql=图解MySQL&#10;留空则整库一本书"
            />
          </el-form-item>
          <el-form-item label="分组中文名">
            <el-input
              v-model="form.gtText"
              type="textarea"
              :rows="4"
              placeholder="可选。每行 书id/目录=章节中文名，与原站侧栏对齐，如：&#10;network/1_base=网络基础&#10;network/2_http=HTTP 篇&#10;留空则显示目录名"
            />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="formOpen = false">取消</el-button>
        <el-button type="primary" @click="saveProject">保存并同步</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 1120px;
  margin: 0 auto;
  padding: calc(var(--nav-h) + 28px) 20px 80px;
}
.pagehead {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}
.pagehead h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
}
.stats {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 12.5px;
  color: var(--text-3);
}
.stats .dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--text-3);
}
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.projgrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.projcard {
  border: 1px solid var(--divider);
  border-radius: 10px;
  padding: 14px 16px 10px;
  background: var(--bg);
  transition: border-color 0.15s;
}
.projcard:hover {
  border-color: var(--text-3);
}
.projhead {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}
.morebtn {
  color: var(--text-3);
}
.ptype {
  font-size: 11px;
  color: var(--text-3);
  border: 1px solid var(--divider);
  border-radius: 4px;
  padding: 0 5px;
  white-space: nowrap;
}
.booktag {
  cursor: pointer;
  border-radius: 5px;
  background: var(--bg-soft);
  border: 1px solid var(--divider);
  color: var(--text-2);
  font-weight: 400;
}
.booktag:hover {
  color: var(--brand);
  border-color: var(--brand);
}
.projfoot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid var(--divider);
  padding-top: 8px;
  margin-top: 2px;
}
.addcard {
  border: 1px dashed var(--divider);
  border-radius: 10px;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: transparent;
  color: var(--text-3);
  font-size: 13.5px;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.addcard:hover {
  border-color: var(--text-3);
  color: var(--text-1);
}
.card {
  border: 1px solid var(--divider);
  border-radius: 10px;
  padding: 16px 18px;
  background: var(--bg);
}
.card > h2 {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-1);
}
.mut {
  color: var(--text-3);
  font-size: 12px;
}
.jobpre {
  background: var(--bg-alt);
  border: 1px solid var(--divider);
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
  max-height: 240px;
  overflow: auto;
  white-space: pre-wrap;
  color: var(--text-2);
  font-family: ui-monospace, Consolas, monospace;
  margin: 0;
}
.jobpre span {
  display: inline;
}
.packcard {
  border: 1px solid var(--divider);
  border-radius: 12px;
  padding: 14px 16px;
  background: var(--bg-soft);
}
.ptitle {
  font-weight: 600;
  font-size: 14.5px;
  margin-bottom: 6px;
  color: var(--text-1);
}
.pdesc {
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--text-2);
  margin: 0 0 10px;
}
.prow {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.pmut {
  font-size: 12px;
  color: var(--text-3);
}
</style>
