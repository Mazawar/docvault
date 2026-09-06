import { createRouter, createWebHashHistory } from 'vue-router'

/** hash 路由：离线静态包在任意静态服务器/子路径下都可直达 */
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'portal', component: () => import('@/views/PortalView.vue') },
    { path: '/shelf', name: 'shelf', component: () => import('@/views/ShelfView.vue') },
    { path: '/project/:pid', name: 'project', component: () => import('@/views/ProjectView.vue') },
    // slug 是嵌套路径（如 海量数据处理/01.xxx），必须允许跨段匹配
    { path: '/read/:pid/:bid/:slug(.*)?', name: 'reader', component: () => import('@/views/ReaderView.vue') },
    { path: '/notes', name: 'notes', component: () => import('@/views/NotesView.vue') },
    { path: '/admin', name: 'admin', component: () => import('@/views/AdminView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ],
  scrollBehavior() {
    // 实际滚动发生在 App.vue 的内部 scroller 上，这里仅兜底 window 场景
    return { top: 0 }
  }
})

/** 书架滚动位置记忆：进项目页前保存，返回书架时由 PortalView 数据就绪后恢复 */
let shelfScrollY = 0

export function saveShelfScroll(y: number): void {
  shelfScrollY = y
}

export function takeShelfScroll(): number {
  const y = shelfScrollY
  shelfScrollY = 0
  return y
}

export default router
