import { createRouter, createWebHashHistory } from 'vue-router'

/** hash 路由：离线静态包在任意静态服务器/子路径下都可直达 */
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'portal', component: () => import('@/views/PortalView.vue') },
    // slug 是嵌套路径（如 海量数据处理/01.xxx），必须允许跨段匹配
    { path: '/read/:pid/:bid/:slug(.*)?', name: 'reader', component: () => import('@/views/ReaderView.vue') },
    { path: '/notes', name: 'notes', component: () => import('@/views/NotesView.vue') },
    { path: '/admin', name: 'admin', component: () => import('@/views/AdminView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ],
  scrollBehavior() {
    return { top: 0 }
  }
})

export default router
