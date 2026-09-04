<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Delete, Edit, Download, Upload } from '@element-plus/icons-vue'
import { adminApi } from '@/api/admin'
import { modeRef } from '@/api/http'
import type { Overview, ProjectFull } from '@/api/types'

const ov = ref<Overview | null>(null)
const staticMode = computed(() => modeRef.value === 'static')
let timer: number | null = null

async function refresh() {
  if (staticMode.value) return
  ov.value = await adminApi.overview()
}

onMounted(async () => {
  if (staticMode) return
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
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    busy[key] = false
  }
}

const syncOne = (pid: string) => act(`sync-${pid}`, () => adminApi.sync(pid), `已提交同步：${pid}`)
const syncAll = () => act('sync-all', () => adminApi.sync(''), '已提交全量同步')
const doExport = () => act('export', () => adminApi.exportZip(), '已提交离线包导出')
const doPdf = () => {
  if (!pdfPid.value || !pdfBid.value) return ElMessage.warning('选择项目和书')
  act(`pdf-${pdfPid.value}-${pdfBid.value}`, () => adminApi.exportPdf(pdfPid.value, pdfBid.value), '已提交 PDF 导出')
}

/* ---------- 项目编辑 ---------- */
const formOpen = ref(false)
const editing = ref('')
const form = reactive({ id: '', name: '', type: 'github', repo: '', root: '', booksText: '' })

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
  Object.assign(form, { id: '', name: '', type: 'github', repo: '', root: '', booksText: '' })
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
      books: form.type === 'github' ? parseBooks(form.booksText) : {}
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

/* ---------- 笔记 ---------- */
const notePid = ref('')
const noteName = ref('')
const noteText = ref('')
const notePidList = computed(() => ov.value?.projects.filter((p) => p.type === 'upload').map((p) => ({ id: p.id, name: p.name })) || [])
const noteList = computed(() => ov.value?.notes.filter((n) => !notePid.value || n.pid === notePid.value) || [])

async function loadNote() {
  if (!noteName.value) {
    noteText.value = ''
    return
  }
  const pid = notePid.value || noteName.value.split('/')[0]
  const name = noteName.value.includes('/') ? noteName.value.split('/')[1] : noteName.value
  const r = await adminApi.getNote(pid, name)
  noteText.value = r.content
}

async function saveNote() {
  let name = noteName.value || ''
  if (!name) {
    name = window.prompt('笔记文件名（不含 .md）') || ''
    if (!name) return
  }
  const pid = notePid.value || 'my-notes'
  await act('note', () => adminApi.saveNote(pid, name, noteText.value), `已保存 ${name}，发布中…`)
}

/* ---------- 上传 ---------- */
const upPid = ref('my-notes')
const upFiles = ref<File[]>([])
const uploadProjectList = computed(() => ov.value?.projects.filter((p) => p.type === 'upload').map((p) => ({ id: p.id, name: p.name })) || [])

function onFileChange(_f: unknown, fs: { raw?: File; name: string }[]) {
  upFiles.value = fs.map((f) => f.raw).filter((f): f is File => !!f)
}

async function doUpload() {
  if (!upFiles.value.length) return ElMessage.warning('选择文件')
  const r = await act('upload', () => adminApi.upload(upPid.value, upFiles.value), '已上传并提交同步')
  if (r) upFiles.value = []
}

function fmtSize(n: number): string {
  return n > 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB'
}
</script>

<template>
  <div class="wrap">
    <el-alert
      v-if="staticMode"
      title="离线包模式：管理功能不可用"
      description="当前运行在导出的静态离线包上，同步/上传/导出需要联机版的 DocVault。"
      type="info"
      show-icon
      :closable="false"
      class="mb-4"
    />

    <div class="card">
      <h2>📦 项目资源</h2>
      <el-table :data="ov?.projects || []" size="small" stripe>
        <el-table-column label="名称" min-width="140">
          <template #default="{ row }">
            <b>{{ row.name }}</b>
            <el-tag v-if="row.type === 'upload'" size="small" class="ml-1.5">上传</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="80" />
        <el-table-column label="内容" min-width="200">
          <template #default="{ row }">
            <span class="mut">{{ row.books.map((b: { title: string; n: number }) => `${b.title}(${b.n})`).join('、') || '尚未同步' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="updated" label="同步于" width="130">
          <template #default="{ row }"><span class="mut">{{ row.updated || '-' }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button size="small" :icon="Refresh" :loading="busy['sync-' + row.id]" @click="syncOne(row.id)">同步</el-button>
            <el-button size="small" :icon="Edit" @click="editProject(row.id)">编辑</el-button>
            <el-button size="small" type="danger" plain :icon="Delete" @click="delProject(row.id)">删</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="mt-3 flex flex-wrap items-center gap-2.5">
        <el-button type="primary" :icon="Plus" @click="newProject">新增项目</el-button>
        <el-button :icon="Refresh" :loading="busy['sync-all']" @click="syncAll">全部同步</el-button>
        <el-button :loading="busy.export" @click="doExport">📦 导出离线包</el-button>
        <a v-if="ov?.zip" :href="adminApi.downloadUrl"><el-button :icon="Download">⬇ 下载 {{ ov.zip }}</el-button></a>
        <span v-if="ov?.zip" class="mut">{{ fmtSize(ov.zipSize) }}</span>
      </div>
    </div>

    <div class="card">
      <h2>✍️ 笔记编辑</h2>
      <div class="mb-2.5 flex flex-wrap items-center gap-2.5">
        <el-select v-model="notePid" placeholder="项目" class="w-36" @change="noteName = ''">
          <el-option v-for="p in notePidList" :key="p.id" :value="p.id" :label="p.name" />
        </el-select>
        <el-select v-model="noteName" placeholder="＋ 新笔记…" filterable allow-create class="w-52" @change="loadNote">
          <el-option v-for="n in noteList" :key="n.pid + '/' + n.name" :value="n.name" :label="n.name" />
        </el-select>
        <el-button type="primary" :loading="busy.note" @click="saveNote">💾 保存并发布</el-button>
      </div>
      <el-input v-model="noteText" type="textarea" :rows="12" placeholder="# 用 Markdown 写点什么..." />
      <div class="mut mt-1.5">支持 GFM / 代码高亮 / [!TIP] 提示块，保存后自动同步发布</div>
    </div>

    <div class="card">
      <h2>📄 导出 PDF</h2>
      <div class="flex flex-wrap items-center gap-2.5">
        <el-select v-model="pdfPid" placeholder="项目" class="w-56" @change="pdfBid = ''">
          <el-option v-for="p in ov?.projects" :key="p.id" :value="p.id" :label="p.name" />
        </el-select>
        <el-select v-model="pdfBid" placeholder="书" class="w-56">
          <el-option v-for="b in pdfBooks" :key="b.id" :value="b.id" :label="`${b.title} (${b.n})`" />
        </el-select>
        <el-button :loading="busy.export" @click="doPdf">导出 PDF</el-button>
      </div>
      <div class="mut mt-2">已有 PDF：{{ ov?.pdfs.join('　') || '无' }}</div>
    </div>

    <div class="card">
      <h2>📎 上传附件</h2>
      <div class="flex flex-wrap items-center gap-2.5">
        <el-select v-model="upPid" placeholder="目标项目" class="w-56">
          <el-option v-for="p in uploadProjectList" :key="p.id" :value="p.id" :label="p.name" />
        </el-select>
        <el-upload :auto-upload="false" multiple :on-change="(_, fs) => onFileChange(fs)" :show-file-list="false">
          <el-button :icon="Upload">选择文件</el-button>
        </el-upload>
        <span v-if="upFiles.length" class="mut">{{ upFiles.map((f) => f.name).join(', ') }}</span>
        <el-button type="primary" :loading="busy.upload" @click="doUpload">上传</el-button>
      </div>
      <div class="mut mt-1.5">.md 文件自动成书，其它文件作为附件存放</div>
    </div>

    <div class="card">
      <h2>⏳ 任务队列</h2>
      <pre class="jobpre">{{ (ov?.jobs || []).length ? '' : '(暂无任务)' }}<template v-for="j in ov?.jobs" :key="j.id"><span>{{ j.status === 'done' ? '✅' : j.status === 'error' ? '❌' : '⏳' }} {{ j.name }}  {{ j.created }} → {{ j.finished || '…' }}</span>
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
        </template>
      </el-form>
      <template #footer>
        <el-button @click="formOpen = false">取消</el-button>
        <el-button type="primary" @click="saveProject">💾 保存并同步</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 1080px;
  margin: 0 auto;
  padding: calc(60px + 24px) 18px 80px;
}
.card {
  background: var(--bg);
  border: 1px solid var(--divider);
  border-radius: 14px;
  padding: 18px 22px;
  margin-bottom: 16px;
}
.card > h2 {
  margin: 0 0 12px;
  font-size: 15.5px;
  color: var(--text-1);
}
.mut {
  color: var(--text-3);
  font-size: 12px;
}
.jobpre {
  background: var(--bg-alt);
  border: 1px solid var(--divider);
  border-radius: 10px;
  padding: 12px;
  font-size: 12px;
  max-height: 260px;
  overflow: auto;
  white-space: pre-wrap;
  color: var(--text-2);
  font-family: ui-monospace, Consolas, monospace;
  margin: 0;
}
.jobpre span {
  display: inline;
}
</style>
