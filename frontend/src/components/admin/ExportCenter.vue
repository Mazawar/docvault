<script setup lang="ts">
import { Download } from '@element-plus/icons-vue'
import { useAdmin } from '../../composables/useAdmin'

const { ov, packBusy, zipBusy, jobRunning, doExport, doExportPack, fmtSize } = useAdmin()
</script>

<template>
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
          <el-button size="small" :loading="packBusy" @click="doExportPack">
            {{ jobRunning('生成资源包') ? '生成中…' : '生成资源包' }}
          </el-button>
          <a v-if="ov?.pack" :href="adminApi.downloadPackUrl">
            <el-button size="small" type="primary" :icon="Download">下载资源包</el-button>
          </a>
          <span v-if="ov?.pack" class="pmut">{{ ov.pack }}（{{ fmtSize(ov.packSize ?? 0) }}）</span>
          <span v-else-if="!packBusy" class="pmut">尚未生成</span>
        </div>
      </div>
      <div class="packcard" :class="{ running: zipBusy }">
        <Transition name="fade">
          <div v-if="zipBusy" class="edgebar"></div>
        </Transition>
        <div class="ptitle">🌐 只读静态站</div>
        <p class="pdesc">预渲染纯静态站点：不需要本程序，解压后 nginx / 任意静态服务器直接浏览。适合分享给没有安装 DocVault 的人。</p>
        <div class="prow">
          <el-button size="small" :loading="zipBusy" @click="doExport">
            {{ jobRunning('生成静态站') ? '生成中…' : '生成静态站' }}
          </el-button>
          <a v-if="ov?.zip" :href="adminApi.downloadUrl">
            <el-button size="small" type="primary" :icon="Download">下载静态站</el-button>
          </a>
          <span v-if="ov?.zip" class="pmut">{{ ov.zip }}（{{ fmtSize(ov.zipSize ?? 0) }}）</span>
          <span v-else-if="!zipBusy" class="pmut">尚未生成</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.packcard {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--divider);
  border-radius: 12px;
  padding: 14px 16px;
  background: var(--bg-soft);
}
.packcard.running { border-color: var(--brand); }
.ptitle { font-weight: 600; font-size: 14.5px; margin-bottom: 6px; color: var(--text-1); }
.pdesc { font-size: 12.5px; line-height: 1.7; color: var(--text-2); margin: 0 0 10px; }
.prow { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.pmut { font-size: 12px; color: var(--text-3); }
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
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
