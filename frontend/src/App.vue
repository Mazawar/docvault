<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import TopBar from '@/components/TopBar.vue'

const top = ref<InstanceType<typeof TopBar> | null>(null)

function onKey(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    top.value?.focus()
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="min-h-screen bg-[var(--bg)] text-[var(--text-1)]">
    <TopBar ref="top" />
    <router-view />
  </div>
</template>
