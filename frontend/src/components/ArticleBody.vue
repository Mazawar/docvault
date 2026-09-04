<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { ArticlePayload } from '@/api/types'

const props = defineProps<{ payload: ArticlePayload }>()
const root = ref<HTMLElement | null>(null)

/** 代码块复制按钮 */
function addCopyButtons() {
  const el = root.value
  if (!el) return
  el.querySelectorAll('.codehilite').forEach((box) => {
    if (box.querySelector('.copybtn')) return
    const b = document.createElement('button')
    b.className = 'copybtn'
    b.textContent = '复制'
    b.onclick = () => {
      navigator.clipboard
        .writeText((box.innerText || '').replace(/\n?复制$/, ''))
        .then(() => {
          b.textContent = '✓'
          setTimeout(() => (b.textContent = '复制'), 1200)
        })
    }
    box.appendChild(b)
  })
}

watch(
  () => props.payload?.html,
  () => nextTick(addCopyButtons),
  { immediate: true }
)
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html — 内容来自本地同步的受信 md 源 -->
  <article ref="root" class="article-body" v-html="payload.html"></article>
</template>
