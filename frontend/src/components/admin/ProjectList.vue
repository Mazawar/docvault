<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, MoreFilled, Plus, Refresh } from '@element-plus/icons-vue'
import { adminApi } from '@/api/admin'
import { notesIndex } from '@/api/notes'
import { useAdmin } from '../../composables/useAdmin'

const ADMIN_GRID_CAP = 6
const router = useRouter()
const { ov, st, busy, syncOne, syncActive, purgeRepos, downloadPack, refresh } = useAdmin()

const showAllProjects = ref(false)
const visibleProjects = computed(() => {
  const list = ov.value?.projects ?? []
  return showAllProjects.value ? list : list.slice(0, ADMIN_GRID_CAP)
})
const hiddenProjects = computed(() => Math.max(0, (ov.value?.projects.length ?? 0) - ADMIN_GRID_CAP))

function delProject(pid: string) {
  ElMessageBox.confirm(`删除项目「${pid}」？其仓库缓存、文章、PDF 将一并清理`, '确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消'
  }).then(() => act(`del-${pid}`, () => adminApi.deleteProject(pid), '已删除'))
}

/* ---------- 项目编辑 ---------- */
const formOpen = ref(false)
const editing = ref('')
const form = reactive({ id: '', name: '', type: 'github', repo: '', root: '', booksText: '', gtText: '' })
const nbFolders = ref<string[]>([])
async function loadNbFolders() {
  if (nbFolders.value.length) return
  try {
    nbFolders.value = (await notesIndex()).folders.map((f) => f.folder)
  } catch { /* 离线/接口异常时忽略 */ }
}

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
  const p = list.find((x) => x.id === pid)
  if (!p) return
  editing.value = pid
  Object.assign(form, {
    id: p.id,
    name: p.name,
    type: p.type,
    repo: p.repo || '',
    root: p.root || '',
    booksText: Object.entries(p.books || {}).map(([k, v]) => `${k}=${v}`).join('\n'),
    gtText: Object.entries((p as any).group_titles || {})
      .map(([bid, m]) =>
        Object.entries(m as Record<string, string>).map(([d, t]) => `${bid}/${d}=${t}`).join('\n')
      ).filter(Boolean).join('\n')
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
</script>

<template>
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
          <el-tag v-for="b in p.books.slice(0, 4)" :key="b.id" class="booktag" @click="router.push(`/read/${p.id}/${b.id}/`)">
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
        <el-button size="small" :icon="Download" :disabled="!p.updated"
          :title="p.updated ? '下载该项目资源包' : '先同步一次才能下载'" @click="downloadPack(p.id)">下载</el-button>
        <el-button size="small" :icon="Refresh" :loading="syncActive(p.id)" @click="syncOne(p.id)">同步</el-button>
        <el-button v-if="p.type === 'github'" size="small" :icon="Brush"
          title="清理仓库缓存（文章与图片保留，下次同步重新克隆）" @click="purgeRepos(p.id, p.name)">清理</el-button>
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
            <el-input v-model="form.booksText" type="textarea" :rows="4"
              placeholder="每行 目录=书名，如：&#10;network=图解网络&#10;mysql=图解MySQL&#10;留空则整库一本书" />
          </el-form-item>
          <el-form-item label="分组中文名">
            <el-input v-model="form.gtText" type="textarea" :rows="4"
              placeholder="可选。每行 书id/目录=章节中文名，与原站侧栏对齐，如：&#10;network/1_base=网络基础&#10;network/2_http=HTTP 篇&#10;留空则显示目录名" />
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
.pmrow:last-child { border-bottom: none; }
.pmrow:hover { background: var(--bg-soft); }
.pmain { min-width: 0; flex: 1; }
.pline1 { display: flex; align-items: center; gap: 8px; min-width: 0; }
.pline1 b { font-size: 14px; flex-shrink: 0; }
.prepo { font-size: 12px; color: var(--text-3); }
.pline2 { margin-top: 5px; display: flex; gap: 6px; overflow: hidden; flex-wrap: wrap; }
.bmore { font-size: 11.5px; color: var(--text-3); white-space: nowrap; align-self: center; }
.pside { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.pside :deep(.el-button + .el-button) { margin-left: 0; }
.psize { font-size: 12px; color: var(--text-3); white-space: nowrap; }
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
.pmrow-add:hover { color: var(--brand); background: var(--bg-soft); }
.pmrow-add { border-bottom-style: dashed; }
.morebtn { color: var(--text-3); }
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
.booktag:hover { color: var(--brand); border-color: var(--brand); }
.edgebar {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  overflow: hidden;
  pointer-events: none;
  z-index: 1;
}
.edgebar::before {
  content: '';
  position: absolute;
  top: 0; bottom: 0;
  width: 40%;
  left: -40%;
  background: linear-gradient(90deg, transparent, var(--brand), transparent);
  animation: edge-slide 1.4s ease-in-out infinite;
}
@keyframes edge-slide { to { left: 100%; } }
.pmrow.running { border-color: var(--brand); }
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (max-width: 768px) {
  .pmrow { flex-direction: column; align-items: stretch; gap: 8px; padding: 12px; }
  .pmrow.pmrow-more,
  .pmrow.pmrow-add {
    flex-direction: row;
    align-items: center;
    justify-content: center;
  }
  .pline1 { flex-wrap: wrap; row-gap: 2px; }
  .pline1 b { font-size: 14.5px; }
  .pside { flex-wrap: wrap; justify-content: flex-end; gap: 6px; }
  .psize { flex: 1; text-align: left; }
}
</style>
