<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Delete, Edit, Download, Upload, MoreFilled, Brush } from '@element-plus/icons-vue'
import { adminApi } from '@/api/admin'
import { notesIndex } from '@/api/notes'
import { modeRef } from '@/api/http'
import type { Overview, ProjectFull } from '@/api/types'

const router = useRouter()
const ov = ref<Overview | null>(null)
const staticMode = computed(() => modeRef.value === 'static')
let timer: number | null = null

/** 项目卡默认只显示两行（3 列 × 2 行），其余进「查看更多」展开的瀑布流 */
const ADMIN_GRID_CAP = 6
const showAllProjects = ref(false)
const visibleProjects = computed(() => {
  const list = ov.value?.projects ?? []
  return showAllProjects.value ? list : list.slice(0, ADMIN_GRID_CAP)
})
const hiddenProjects = computed(() => Math.max(0, (ov.value?.projects.length ?? 0) - ADMIN_GRID_CAP))

const knownJobs = new Map<number, string>()
const jobTitle = (name: string) => (name.startsWith('sync-') ? `同步 ${name.slice(5)}` : name)

async function refresh() {
  if (staticMode.value) return
  ov.value = await adminApi.overview()
  const first = knownJobs.size === 0
  for (const j of ov.value.jobs || []) {
    const prev = knownJobs.get(j.id)
    const finished = j.status === 'done' || j.status === 'error'
    // 页面加载后才出现的任务，首次被看到即已完成也算（快任务可能在两次轮询间结束）
    const started = prev === undefined && !first
    if ((started || prev === 'queued' || prev === 'running') && finished) {
      if (j.status === 'done') ElMessage.success(`${jobTitle(j.name)} 完成`)
      else {
        const msg = (j.log.find((l) => l.startsWith('ERROR: ')) || '').replace(/^ERROR: /, '')
        ElMessage.error(`${jobTitle(j.name)} 失败：${msg.slice(0, 160)}`)
      }
    }
    knownJobs.set(j.id, j.status)
  }
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
function downloadPack(pid: string) {
  ElMessage.info('正在打包，完成后浏览器将开始下载…')
  window.location.href = adminApi.projectPackUrl(pid)
}
/* ---------- 存储与清理 ---------- */
const st = ref<Awaited<ReturnType<typeof adminApi.storage>> | null>(null)
const distDesc = computed(() => {
  if (!st.value) return ''
  const d = st.value.dist
  const parts: string[] = []
  if (d.pack) parts.push(`资源包 ${d.pack.mb}MB`)
  if (d.offline) parts.push(`离线包 ${d.offline.mb}MB`)
  if (d.site_mb) parts.push(`静态站 ${d.site_mb}MB`)
  if (d.pdf_mb) parts.push(`PDF ${d.pdf_mb}MB`)
  if (d.temp.mb) parts.push(`临时 ${d.temp.mb}MB`)
  return parts.join(' · ') || '暂无产物'
})
const totalMb = computed(() => {
  if (!st.value) return 0
  const s = st.value
  return Math.round(s.assets.mb + s.repos_mb + s.db_mb + s.notes_mb + s.uploads_mb + s.dist.mb)
})
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
const purgeDist = () =>
  ElMessageBox.confirm(
    '删除全部导出产物：资源包、离线站包、静态站、PDF、下载临时文件。这些都是可随时重新生成的产物，文章数据（数据库/图床/仓库）不动。',
    '清理导出产物', { confirmButtonText: '清理', type: 'warning' }
  ).then(() => act('purge-dist', () => adminApi.purgeDist(), '已提交清理，进度见任务队列'))
    .then(loadStorage).catch(() => {})
const syncAll = () => act('sync-all', () => adminApi.sync(''), '已提交全量同步')
const doExport = () => act('export', () => adminApi.exportZip(), '已提交静态站生成')
const doExportPack = () => act('export-pack', () => adminApi.exportPack(), '已提交资源包生成')

/* 生成/导入是后台任务：按钮 loading 与进行中动效跟任务真实状态走（overview 3s 轮询） */
const latestJob = (name: string) => (ov.value?.jobs || []).find((j) => j.name === name)
const jobRunning = (name: string) => latestJob(name)?.status === 'running'

/* 动效开关：点击瞬间（busy）与后台任务运行期（jobRunning）都算"进行中" */
const packBusy = computed(() => !!busy['export-pack'] || jobRunning('生成资源包'))
const zipBusy = computed(() => !!busy.export || jobRunning('生成静态站'))
const syncActive = (pid: string) =>
  !!busy[`sync-${pid}`] || !!busy['sync-all'] || jobRunning(`sync-${pid}`) || jobRunning('sync-all')
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

function fmtSize(n: number): string {
  return n < 1024 ? `${n}B` : n < 1048576 ? `${(n / 1024).toFixed(1)}K` : `${(n / 1048576).toFixed(1)}M`
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
  loadNbFolders()
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
  loadNbFolders()
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

/* 笔记本导入：可选笔记本列表 */
const nbFolders = ref<string[]>([])
async function loadNbFolders() {
  if (nbFolders.value.length) return
  try {
    nbFolders.value = (await notesIndex()).folders.map((f) => f.folder)
  } catch { /* 离线/接口异常时忽略 */ }
}

function delProject(pid: string) {  ElMessageBox.confirm(`删除项目「${pid}」？其仓库缓存、文章、PDF 将一并清理`, '确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消'
  }).then(() => act(`del-${pid}`, () => adminApi.deleteProject(pid), '已删除'))
}

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
        <el-button
          type="primary"
          :icon="Upload"
          :loading="busy['import-pack'] || jobRunning('导入资源包')"
          @click="doImportPack"
        >{{ jobRunning('导入资源包') ? '导入中…' : '导入资源包' }}</el-button>
        <input ref="packInput" type="file" accept=".zip" style="display: none" @change="onPackFile" />
      </div>
    </div>

    <!-- 项目管理：两行式列表，默认 6 行，可展开 -->
    <div class="plist">
      <div v-for="p in visibleProjects" :key="p.id" class="pmrow" :class="{ running: syncActive(p.id) }">
        <Transition name="fade">
          <div v-if="syncActive(p.id)" class="edgebar"></div>
        </Transition>
        <div class="pmain">
          <div class="pline1">
            <b class="truncate">{{ p.name }}</b>
            <span class="ptype">{{ p.type === 'notebook' ? '笔记本' : p.type === 'upload' ? '上传' : 'GitHub' }}</span>
            <span class="prepo truncate">
              {{ p.type === 'github' ? p.repo : p.type === 'notebook' ? '笔记本 · ' + p.repo : '本地目录' }}
              · 同步于 {{ p.updated || '从未' }}
            </span>
          </div>
          <div class="pline2">
            <el-tag
              v-for="b in p.books.slice(0, 4)"
              :key="b.id"
              class="booktag"
              @click="router.push(`/read/${p.id}/${b.id}/`)"
            >
              {{ b.title }} · {{ b.n }}
            </el-tag>
            <span v-if="p.books.length > 4" class="bmore">共 {{ p.books.length }} 本</span>
            <span v-if="!p.books.length" class="mut text-xs">尚未同步</span>
          </div>
        </div>
        <div class="pside">
          <span class="psize">
            {{ p.books.length }} 本书
            <template v-if="st?.projects.find(x => x.id === p.id)?.repos_mb">
              · {{ st.projects.find(x => x.id === p.id)?.repos_mb }}MB
            </template>
          </span>
          <el-button
            size="small"
            :icon="Download"
            :disabled="!p.updated"
            :title="p.updated ? '下载该项目资源包' : '先同步一次才能下载'"
            @click="downloadPack(p.id)"
          >下载</el-button>
          <el-button
            size="small"
            :icon="Refresh"
            :loading="syncActive(p.id)"
            @click="syncOne(p.id)"
          >同步</el-button>
          <el-button
            v-if="p.type === 'github'"
            size="small"
            :icon="Brush"
            title="清理仓库缓存（文章与图片保留，下次同步重新克隆）"
            @click="purgeRepos(p.id, p.name)"
          >清理</el-button>
          <el-dropdown trigger="click" @command="(c: string) => c === 'edit' ? editProject(p.id) : delProject(p.id)">
            <el-button text :icon="MoreFilled" class="morebtn" />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit" :icon="Edit">编辑</el-dropdown-item>
                <el-dropdown-item command="del" :icon="Delete" divided>删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <button v-if="hiddenProjects > 0 || showAllProjects" class="pmrow pmrow-more" @click="showAllProjects = !showAllProjects">
        <template v-if="!showAllProjects">还有 {{ hiddenProjects }} 个项目 · 查看全部 →</template>
        <template v-else>收起 ↑</template>
      </button>

      <button class="pmrow pmrow-add" @click="newProject">
        <el-icon :size="16"><Plus /></el-icon>
        添加项目
      </button>
    </div>

    <!-- 导出中心：两种产物，用途一目了然 -->
    <div class="card">
      <h2>导出中心</h2>
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div class="packcard" :class="{ running: packBusy }">
          <Transition name="fade">
            <div v-if="packBusy" class="edgebar"></div>
          </Transition>
          <div class="ptitle">📦 数据资源包 <el-tag size="small" type="success">推荐</el-tag></div>
          <p class="pdesc">完整数据：数据库 + 图片 + 笔记 + PDF + 前端产物。拷到内网机器导入 DocVault，即为完整实例——搜索、管理、笔记、阅读记忆全部可用，无需联网和 npm。</p>
          <div class="prow">
            <el-button size="small" :loading="busy['export-pack'] || jobRunning('生成资源包')" @click="doExportPack">
              {{ jobRunning('生成资源包') ? '生成中…' : '生成资源包' }}
            </el-button>
            <a v-if="ov?.pack" :href="adminApi.downloadPackUrl">
              <el-button size="small" type="primary" :icon="Download">下载资源包</el-button>
            </a>
            <span v-if="ov?.pack" class="pmut">{{ ov.pack }}（{{ fmtSize(ov.packSize ?? 0) }}）</span>
            <span v-else-if="!busy['export-pack'] && !jobRunning('生成资源包')" class="pmut">尚未生成</span>
          </div>
        </div>
        <div class="packcard" :class="{ running: zipBusy }">
          <Transition name="fade">
            <div v-if="zipBusy" class="edgebar"></div>
          </Transition>
          <div class="ptitle">🌐 只读静态站</div>
          <p class="pdesc">预渲染纯静态站点：不需要本程序，解压后 nginx / 任意静态服务器直接浏览。适合分享给没有安装 DocVault 的人。</p>
          <div class="prow">
            <el-button size="small" :loading="busy.export || jobRunning('生成静态站')" @click="doExport">
              {{ jobRunning('生成静态站') ? '生成中…' : '生成静态站' }}
            </el-button>
            <a v-if="ov?.zip" :href="adminApi.downloadUrl">
              <el-button size="small" type="primary" :icon="Download">下载静态站</el-button>
            </a>
            <span v-if="ov?.zip" class="pmut">{{ ov.zip }}（{{ fmtSize(ov.zipSize) }}）</span>
            <span v-else-if="!busy.export && !jobRunning('生成静态站')" class="pmut">尚未生成</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 维护：存储与队列并排 -->
    <div class="grid grid-cols-1 gap-4 lg:grid-cols-3 mb-4">
      <div class="card">
        <div class="mb-3 flex items-center justify-between gap-2">
          <h2 class="!m-0 text-[14px] font-semibold text-[var(--text-1)]">存储与清理</h2>
          <span v-if="st" class="text-xs text-[var(--text-3)]">合计约 {{ totalMb }} MB</span>
        </div>
        <template v-if="st">
          <div class="strow">
            <div class="stlabel">
              <b>图片缓存</b>
              <i>文章/笔记引用的图床文件</i>
            </div>
            <div class="stsize">{{ st.assets.mb }}MB<span class="ssub"> · {{ st.assets.files }} 个</span></div>
            <el-button size="small" :loading="busy['purge-orphan']" @click="purgeOrphan">清理未引用</el-button>
          </div>
          <div class="strow">
            <div class="stlabel">
              <b>导出产物</b>
              <i>{{ distDesc }}</i>
            </div>
            <div class="stsize">{{ st.dist.mb }}MB<span class="ssub" v-if="st.dist.temp.mb"> · 临时 {{ st.dist.temp.mb }}MB</span></div>
            <el-button size="small" :loading="busy['purge-dist'] || jobRunning('清理导出产物')" @click="purgeDist">清理全部</el-button>
          </div>
          <div class="strow">
            <div class="stlabel">
              <b>文章数据库</b>
              <i>核心数据，不可清理</i>
            </div>
            <div class="stsize">{{ st.db_mb }}MB</div>
          </div>
          <div class="strow">
            <div class="stlabel">
              <b>笔记与附件</b>
              <i>用户数据</i>
            </div>
            <div class="stsize">{{ st.notes_mb + st.uploads_mb }}MB</div>
          </div>
        </template>
        <div v-else class="mut text-[13px]">统计加载中…</div>
      </div>
      <div class="card lg:col-span-2">
        <h2>任务队列</h2>
        <pre class="jobpre">{{ (ov?.jobs || []).length ? '' : '(暂无任务)' }}<template v-for="j in ov?.jobs" :key="j.id"><span>{{ j.status === 'done' ? '✓' : j.status === 'error' ? '✗' : '…' }} {{ j.name }}  {{ j.created }} → {{ j.finished || '进行中' }}</span>
<span v-for="(l, i) in j.log" :key="i" class="mut">  {{ l }}</span>
</template></pre>
      </div>
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
          <el-radio-group v-model="form.type" :disabled="!!editing">
            <el-radio-button value="github">GitHub 仓库</el-radio-button>
            <el-radio-button value="notebook">导入笔记本</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.type === 'notebook'" label="选择笔记本">
          <div class="w-full">
            <el-select v-model="form.repo" placeholder="选择要导入的笔记本" class="!w-full">
              <el-option v-for="f in nbFolders" :key="f" :value="f" :label="f" />
            </el-select>
            <div class="mut mt-1.5">同步后书架出现这本书；笔记更新后在项目卡点「同步」刷新。去笔记页可新建笔记本。</div>
          </div>
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
  padding: 28px 20px 80px;
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
/* 项目管理列表：两行式行卡，默认 6 行可展开 */
.plist {
  border: 1px solid var(--divider);
  border-radius: 10px;
  background: var(--bg);
  overflow: hidden;
  margin-bottom: 20px;
}
.pmrow {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 11px 16px;
  border-bottom: 1px solid var(--divider);
  transition: background 0.15s;
}
.pmrow:last-child {
  border-bottom: none;
}
.pmrow:hover {
  background: var(--bg-soft);
}
.pmain {
  min-width: 0;
  flex: 1;
}
.pline1 {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.pline1 b {
  font-size: 14px;
  flex-shrink: 0;
}
.prepo {
  font-size: 12px;
  color: var(--text-3);
}
.pline2 {
  margin-top: 5px;
  display: flex;
  gap: 6px;
  overflow: hidden;
}
.bmore {
  font-size: 11.5px;
  color: var(--text-3);
  white-space: nowrap;
  align-self: center;
}
.pside {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.psize {
  font-size: 12px;
  color: var(--text-3);
  white-space: nowrap;
}
.pmrow-more,
.pmrow-add {
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-3);
  background: transparent;
  cursor: pointer;
  min-height: 44px;
  transition: background 0.15s, color 0.15s;
}
.pmrow-more:hover,
.pmrow-add:hover {
  color: var(--brand);
  background: var(--bg-soft);
}
.pmrow-add {
  border-bottom-style: dashed;
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
.card {
  margin-bottom: 16px;
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
.strow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto 110px;
  grid-template-rows: auto auto;
  column-gap: 12px;
  row-gap: 1px;
  align-items: center;
  padding: 7px 0;
  font-size: 13px;
  color: var(--text-3);
}
.strow + .strow {
  border-top: 1px dashed var(--divider);
}
.stlabel {
  grid-row: 1 / span 2;
  min-width: 0;
}
.stlabel b {
  display: block;
  color: var(--text-2);
  font-weight: 600;
}
.stlabel i {
  display: block;
  font-size: 11.5px;
  font-style: normal;
  color: var(--text-3);
  opacity: 0.85;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.stsize {
  grid-column: 2;
  grid-row: 1 / span 2;
  color: var(--text-1);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}
.stsize .ssub {
  font-size: 11px;
  color: var(--text-3);
  font-weight: 400;
}
.strow .el-button {
  grid-column: 3;
  grid-row: 1 / span 2;
  justify-self: end;
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
  position: relative;
  overflow: hidden;
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
/* 任务进行中：卡片上边缘流动进度线（绝对定位，不改变卡片尺寸） */
.edgebar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  overflow: hidden;
  pointer-events: none;
  z-index: 1;
}
.edgebar::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  width: 40%;
  left: -40%;
  background: linear-gradient(90deg, transparent, var(--brand), transparent);
  animation: edge-slide 1.4s ease-in-out infinite;
}
@keyframes edge-slide {
  to { left: 100%; }
}
.projcard.running, .packcard.running {
  border-color: var(--brand);
}
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}
</style>
