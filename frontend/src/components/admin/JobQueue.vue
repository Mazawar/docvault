<script setup lang="ts">
import { useAdmin } from '../../composables/useAdmin'

const { ov } = useAdmin()
</script>

<template>
  <div class="card">
    <h2>任务队列</h2>
    <pre class="jobpre">{{ (ov?.jobs || []).length ? '' : '(暂无任务)' }}<template v-for="j in ov?.jobs" :key="j.id"><span>{{ j.status === 'done' ? '✓' : j.status === 'error' ? '✗' : '…' }} {{ j.name }}  {{ j.created }} → {{ j.finished || '进行中' }}</span>
<span v-for="(l, i) in j.log" :key="i" class="mut">  {{ l }}</span>
</template></pre>
  </div>
</template>

<style scoped>
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
.jobpre span { display: inline; }
</style>
