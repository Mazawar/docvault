<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Moon, Sunny, Search } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'
import { isStatic } from '@/api/http'
import SearchModal from '@/components/SearchModal.vue'

const theme = useThemeStore()
const route = useRoute()
const path = computed(() => route.path)
const searchOpen = ref(false)

function openSearch() {
  searchOpen.value = true
}

defineExpose({ openSearch })

function onTheme() {
  theme.init()
  theme.toggle()
}
</script>

<template>
  <header
    class="fixed inset-x-0 top-0 z-80 flex h-[var(--nav-h)] items-center border-b border-[var(--divider)] bg-[var(--bg)]/85 pl-4 pr-4 backdrop-blur-md md:pl-6"
  >
    <a class="mr-5 flex items-center gap-2 whitespace-nowrap" href="#/">
      <span class="logo-mark"></span>
      <span class="text-[15px] font-bold tracking-tight text-[var(--text-1)]">DocVault</span>
    </a>

    <nav class="navlinks h-full">
      <RouterLink to="/" class="navlink" :class="{ on: path === '/' }">首页</RouterLink>
      <RouterLink to="/notes" class="navlink" :class="{ on: path === '/notes' }">笔记</RouterLink>
      <RouterLink v-if="!isStatic()" to="/admin" class="navlink" :class="{ on: path === '/admin' }">资源管理</RouterLink>
    </nav>

    <span class="flex-1"></span>

    <button class="searchbtn" @click="openSearch">
      <el-icon class="sicon"><Search /></el-icon>
      <span class="ph">搜索文章与笔记…</span>
      <span class="kbd">Ctrl K</span>
    </button>
    <SearchModal :open="searchOpen" @close="searchOpen = false" />

    <button class="tbtn" title="切换主题" @click="theme.init(), theme.toggle()">
      <el-icon><Moon v-if="!theme.dark" /><Sunny v-else /></el-icon>
    </button>
  </header>
</template>

<style scoped>
.logo-mark {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  background: var(--brand);
  display: inline-block;
}
.navlinks {
  display: flex;
  align-items: stretch;
  gap: 2px;
}
.navlink {
  position: relative;
  display: flex;
  align-items: center;
  padding: 0 12px;
  font-size: 13.5px;
  color: var(--text-2);
  transition: color 0.15s;
}
.navlink:hover {
  color: var(--text-1);
}
.navlink.on {
  color: var(--text-1);
  font-weight: 600;
}
.navlink.on::after {
  content: '';
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: 0;
  height: 2px;
  border-radius: 2px 2px 0 0;
  background: var(--brand);
}
.searchbtn {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  min-width: 210px;
  padding: 0 10px 0 12px;
  border: 1px solid var(--divider);
  background: var(--bg-soft);
  border-radius: 8px;
  color: var(--text-3);
  font-size: 13px;
  cursor: pointer;
  transition: 0.15s;
}
.searchbtn:hover {
  border-color: var(--text-3);
  color: var(--text-2);
}
.sicon {
  font-size: 13px;
}
.searchbtn .ph {
  flex: 1;
  text-align: left;
}
.kbd {
  font-size: 11px;
  border: 1px solid var(--divider);
  border-radius: 4px;
  padding: 0 5px;
  background: var(--bg);
}
.tbtn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  margin-left: 4px;
  border: none;
  background: transparent;
  color: var(--text-2);
  border-radius: 6px;
  cursor: pointer;
  font-size: 15px;
  transition: 0.15s;
}
.tbtn:hover {
  color: var(--text-1);
  background: var(--bg-soft);
}
@media (max-width: 900px) {
  .searchbtn {
    min-width: 0;
    width: 38px;
    justify-content: center;
    padding: 0;
  }
  .searchbtn .ph,
  .searchbtn .kbd {
    display: none;
  }
}
</style>
