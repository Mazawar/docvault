<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import type { ArticlePayload } from '@/api/types'
import { useThemeStore } from '@/stores/theme'
import { mdHeadingId } from '@/lib/mdconfig'

const props = defineProps<{ payload: ArticlePayload }>()
const theme = useThemeStore()
const editorTheme = computed(() => (theme.dark ? 'dark' : 'light'))
const root = ref<HTMLElement | null>(null)

/** "1,3-4" → 1 起始的行号集合 */
function parseHl(meta: string, total: number): Set<number> {
  const out = new Set<number>()
  for (const part of meta.split(',')) {
    const m = part.trim().match(/^(\d+)(?:\s*-\s*(\d+))?$/)
    if (!m) continue
    const a = Math.max(1, parseInt(m[1], 10))
    const b = Math.min(m[2] ? parseInt(m[2], 10) : a, total)
    for (let i = a; i <= b; i++) out.add(i)
  }
  return out
}

/** 渲染后增强：code-group 归组标签页 + {1,2-4} 行高亮条纹 */
function enhance(el: HTMLElement) {
  el.querySelectorAll<HTMLElement>('.md-editor-admonition-code-group').forEach((box) => {
    if (box.dataset.cgDone) return
    box.dataset.cgDone = '1'
    // md-editor 对 [label] 围栏逐个渲染单标签盒，这里归并成一个标签组
    const blocks = [...box.children].filter(
      (c) => c.classList.contains('md-editor-code') && c.tagName === 'DETAILS'
    ) as HTMLElement[]
    if (blocks.length < 2) return
    const bar = document.createElement('div')
    bar.className = 'cg-bar'
    blocks.forEach((b, i) => {
      const native = b.querySelector('.md-editor-codetab-label label')
      const btn = document.createElement('button')
      btn.type = 'button'
      btn.className = 'cg-tab' + (i === 0 ? ' on' : '')
      btn.textContent = (b.getAttribute('data-cg-label') || native?.textContent || `代码 ${i + 1}`).trim()
      btn.addEventListener('click', () => {
        ;[...bar.children].forEach((x) => x.classList.remove('on'))
        btn.classList.add('on')
        blocks.forEach((x, j) => {
          x.hidden = j !== i
        })
      })
      bar.appendChild(btn)
    })
    box.insertBefore(bar, blocks[0])
    blocks.forEach((b, j) => {
      b.hidden = j !== 0
    })
  })

  el.querySelectorAll<HTMLElement>('[data-hl]').forEach((el2) => {
    if (el2.dataset.hlDone) return
    el2.dataset.hlDone = '1'
    const code = el2.querySelector<HTMLElement>('pre code')
    if (!code) return
    const total = (code.textContent || '').replace(/\n$/, '').split('\n').length
    const targets = parseHl(el2.dataset.hl || '', total)
    if (!targets.size) return
    const cs = getComputedStyle(code)
    const lh = parseFloat(cs.lineHeight) || 21
    const pad = parseFloat(cs.paddingTop) || 0
    const segs = [...targets].map((n) => {
      const s = (pad + (n - 1) * lh).toFixed(2)
      const e = (pad + n * lh).toFixed(2)
      return `transparent ${s}px, var(--vp-hl) ${s}px, var(--vp-hl) ${e}px, transparent ${e}px`
    })
    code.style.backgroundImage = `linear-gradient(${segs.join(', ')})`
  })
}

function runEnhance() {
  if (root.value) enhance(root.value)
}

/* MdPreview 的 markdown 在其自身挂载后才渲染，用 MutationObserver 兜住任意时机；
   enhance 内部有 dataset 幂等护栏，重复触发无副作用 */
let obs: MutationObserver | null = null
onMounted(() => {
  runEnhance()
  if (!root.value) return
  obs = new MutationObserver(runEnhance)
  obs.observe(root.value, { childList: true, subtree: true })
})
onBeforeUnmount(() => {
  obs?.disconnect()
  obs = null
})
</script>

<template>
  <article ref="root" class="article-body">
    <!-- 新管线：前端 markdown-it（md-editor-v3 内核，VitePress 同款）渲染，
         md 字段由后端完成方言清洗与资源/链接改写 -->
    <MdPreview
      v-if="props.payload.md"
      :model-value="props.payload.md"
      preview-theme="vuepress"
      code-theme="github"
      :theme="editorTheme"
      :md-heading-id="mdHeadingId"
      class="dv-preview"
    />
    <!-- 旧离线包只有预渲染 HTML，走回退 -->
    <!-- eslint-disable-next-line vue/no-v-html — 内容来自本地同步的受信 md 源 -->
    <div v-else v-html="props.payload.html"></div>
  </article>
</template>
