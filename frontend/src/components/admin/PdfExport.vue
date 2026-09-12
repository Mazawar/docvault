<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '../../composables/useAdmin'

const { ov, busy, act } = useAdmin()
const pdfPid = ref('')
const pdfBid = ref('')
const pdfBooks = computed(() => ov.value?.projects.find((p) => p.id === pdfPid.value)?.books || [])
const doPdf = () => {
  if (!pdfPid.value || !pdfBid.value) return
  act(`pdf-${pdfPid.value}-${pdfBid.value}`,
    () => adminApi.exportPdf(pdfPid.value, pdfBid.value), '已提交 PDF 导出')
}
watch(pdfPid, () => (pdfBid.value = ''))
</script>

<template>
  <div class="card">
    <h2>导出 PDF（按书）</h2>
    <div class="flex flex-wrap items-center gap-2.5">
      <el-select v-model="pdfPid" placeholder="项目" class="!w-44" @change="pdfBid = ''">
        <el-option v-for="p in ov?.projects" :key="p.id" :value="p.id" :label="p.name" />
      </el-select>
      <el-select v-model="pdfBid" placeholder="书" class="!w-44">
        <el-option v-for="b in pdfBooks" :key="b.id" :value="b.id" :label="`${b.title} (${b.n})`" />
      </el-select>
    </div>
    <el-button class="mt-2.5" :loading="busy.pdf" @click="doPdf">导出整本书</el-button>
    <div class="mut mt-2 truncate">已有：{{ ov?.pdfs.join('　') || '无' }}</div>
  </div>
</template>
