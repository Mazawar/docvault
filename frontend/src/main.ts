import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import '@/styles/tailwind.css'
import '@/styles/main.scss'
import App from './App.vue'
import router from './router'
import { useThemeStore } from '@/stores/theme'
import { detectMode } from '@/api/http'
import './lib/mdconfig'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
useThemeStore().init()
app.mount('#app')
detectMode()
