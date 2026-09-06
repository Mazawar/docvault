import { config } from 'md-editor-v3'

/**
 * 标题 id 生成对齐 VitePress/GitHub 语义：小写、去标点、空格转连字符——
 * 正文里的 #锚点 链接（原 {#id} 锚点的目标）依赖它。
 * 无状态：md-editor-v3 会在渲染与目录同步等时机多次调用，去重计数无法保证幂等，
 * 重复 slug 一律返回同 id（跳转命中第一个，与源站行为一致）。
 */
const slugify = (t: string) =>
  t
    .toLowerCase()
    .trim()
    .replace(/[^\w\u4e00-\u9fff -]/g, '')
    .replace(/\s+/g, '-')

export function mdHeadingId({ text }: { text: string; index?: number }): string {
  const base = slugify(text)
  return base || 'h'
}

/** 围栏信息串：```lang{1,2-4} [标签]（VitePress 行高亮 + code-group 标签） */
function parseInfo(info: string): { lang: string; meta: string; label: string } | null {
  const m = info.trim().match(/^([^\s{[\]]+)\s*(?:\{([^}]*)\})?\s*(?:\[(.+)\])?$/)
  if (!m || (!m[2] && !m[3])) return null
  return { lang: m[1], meta: (m[2] || '').trim(), label: (m[3] || '').trim() }
}

/**
 * fence 元数据插件：把 lang{行号} [标签] 转成 token 属性（data-hl / data-cg-label），
 * 再以纯 lang 交给后续渲染。属性随 token 落到 .md-editor-code 容器上，
 * 由 ArticleBody 渲染后做行高亮条纹与标签页归组。
 *
 * 通过 markdownItPlugins 追加，保证注册在原生 code 插件之后——否则原生插件
 * 会先把 [标签] 从 info 里剥掉，这里就再也拿不到了。
 */
interface FenceToken {
  info: string
  attrSet: (name: string, value: string) => void
}

type FenceRule = (tokens: FenceToken[], idx: number, opts: unknown, env: unknown, self: unknown) => string

const fenceMetaPlugin = (md: { renderer: { rules: { fence?: FenceRule } } }) => {
  const inner = md.renderer.rules.fence
  if (!inner) return
  md.renderer.rules.fence = (tokens, idx, opts, env, self) => {
    const t = tokens[idx]
    const parsed = parseInfo(String(t.info || ''))
    if (!parsed) return inner(tokens, idx, opts, env, self)
    t.info = parsed.lang
    if (parsed.meta) t.attrSet('data-hl', parsed.meta)
    if (parsed.label) t.attrSet('data-cg-label', parsed.label)
    return inner(tokens, idx, opts, env, self)
  }
}

config({
  markdownItPlugins: (plugins) => [
    ...plugins,
    { type: 'fence-meta', plugin: fenceMetaPlugin, options: {} },
  ],
})
