import { defineStore } from 'pinia'

/** 暗色主题：localStorage.dvTheme 与 <html>.dark 同步（与后端渲染时代保持同一 key） */
export const useThemeStore = defineStore('theme', {
  state: () => ({ dark: false }),
  actions: {
    init() {
      let t: string | null = null
      try {
        t = localStorage.dvTheme
      } catch {
        /* ignore */
      }
      this.dark = t ? t === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches
      this.apply()
    },
    apply() {
      document.documentElement.classList.toggle('dark', this.dark)
    },
    toggle() {
      this.dark = !this.dark
      this.apply()
      try {
        localStorage.dvTheme = this.dark ? 'dark' : 'light'
      } catch {
        /* ignore */
      }
    }
  }
})
