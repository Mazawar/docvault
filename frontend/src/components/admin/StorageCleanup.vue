<script setup lang="ts">
import { useAdmin } from '../../composables/useAdmin'

const { st, busy, jobRunning, purgeOrphan, purgeDist, distDesc, totalMb } = useAdmin()
</script>

<template>
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
</template>

<style scoped>
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
.strow + .strow { border-top: 1px dashed var(--divider); }
.stlabel { grid-row: 1 / span 2; min-width: 0; }
.stlabel b { display: block; color: var(--text-2); font-weight: 600; }
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
.stsize .ssub { font-size: 11px; color: var(--text-3); font-weight: 400; }
.strow .el-button {
  grid-column: 3;
  grid-row: 1 / span 2;
  justify-self: end;
}
@media (max-width: 768px) {
  .strow { grid-template-columns: minmax(0, 1fr) auto; }
  .strow .el-button {
    grid-column: 1 / span 2;
    grid-row: auto;
    justify-self: end;
    margin-top: 4px;
  }
  .stlabel i { white-space: normal; }
}
</style>
