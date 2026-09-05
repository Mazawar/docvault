<script setup lang="ts">
import { onBeforeUnmount, onMounted, provide, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import TopBar from '@/components/TopBar.vue'

const top = ref<InstanceType<typeof TopBar> | null>(null)
const scroller = ref<HTMLElement | null>(null)
provide('pageScroller', scroller)

const route = useRoute()
watch(() => route.path, () => { if (scroller.value) scroller.value.scrollTop = 0 })

function onKey(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    top.value?.openSearch()
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="h-screen overflow-hidden bg-[var(--bg)] pt-[var(--nav-h)] text-[var(--text-1)]">
    <TopBar ref="top" />
    <div ref="scroller" class="h-full overflow-y-auto">
      <router-view />
    </div>
  </div>
</template>
