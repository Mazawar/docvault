<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Upload } from '@element-plus/icons-vue'
import ProjectList from '../components/admin/ProjectList.vue'
import ExportCenter from '../components/admin/ExportCenter.vue'
import ArticleManage from '../components/admin/ArticleManage.vue'
import StorageCleanup from '../components/admin/StorageCleanup.vue'
import PdfExport from '../components/admin/PdfExport.vue'
import JobQueue from '../components/admin/JobQueue.vue'
import { useAdmin } from '../composables/useAdmin'

const { ov, stats, staticMode, busy, jobRunning, refresh, startPolling, stopPolling } = useAdmin()

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
  useAdmin().act('import-pack', () => adminApiImport(f), `已提交导入：${f.name}`)
  ;(e.target as HTMLInputElement).value = ''
}
function adminApiImport(file: File) {
  return import('@/api/admin').then((m) => m.adminApi.importPack(file))
}

onMounted(() => {
  startPolling()
})
onBeforeUnmount(() => {
  stopPolling()
})
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

    <ProjectList />
    <ExportCenter />
    <ArticleManage />

    <!-- 维护：存储与队列并排 -->
    <div class="grid grid-cols-1 gap-4 lg:grid-cols-3 mb-4">
      <StorageCleanup />
      <JobQueue class="lg:col-span-2" />
    </div>

    <PdfExport />
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
@media (max-width: 768px) {
  .wrap { padding: 16px 12px 64px; }
  .pagehead h1 { font-size: 18px; }
}
</style>
