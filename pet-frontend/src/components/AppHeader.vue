<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { PawPrint, Handshake, BookOpen, Search, ShieldCheck, Users, Salad, Menu, X, LogOut, User, Sun, Moon } from 'lucide-vue-next'
import { useAuthStore } from '../store/authStore'
import { useThemeStore } from '../store/themeStore'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const emit = defineEmits(['open-command'])

const drawerOpen = ref(false)

const navItems = [
  { name: '宠物互助', path: '/mutual-aid', icon: Handshake },
  { name: '百科指南', path: '/wiki', icon: BookOpen },
  { name: '营养喂养', path: '/nutrition', icon: Salad },
  { name: '宠物领养', path: '/adopt', icon: Search },
  { name: '社区交流', path: '/community', icon: Users },
  { name: '管理后台', path: '/dashboard', icon: ShieldCheck },
]

const navigate = (path: string) => {
  router.push(path)
  drawerOpen.value = false
}

const handleLogout = () => {
  authStore.logout()
  drawerOpen.value = false
  router.push('/login')
}

// 辅助函数：获取写实风格头像 (人/宠混合)
const getRealisticAvatar = (seed: string) => {
  const hash = seed.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  if (hash % 2 === 0) {
    return `https://i.pravatar.cc/150?u=${seed}`
  } else {
    const pets = ['dog', 'cat', 'rabbit']
    return `https://loremflickr.com/200/200/${pets[hash % pets.length]}?lock=${hash}`
  }
}
</script>

<template>
  <nav class="fixed top-0 z-50 w-full border-b nav-bar backdrop-blur-lg" style="border-color: var(--border); background: var(--nav-bg)">
    <div class="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 md:px-6 md:py-4">

      <!-- Logo -->
      <div class="flex items-center gap-3 cursor-pointer group" @click="navigate('/')">
        <div class="bg-orange-500 p-2 rounded-xl text-white shadow-lg shadow-orange-500/40 group-hover:scale-110 transition-transform">
          <PawPrint :size="20" />
        </div>
        <h1 class="text-lg md:text-xl font-black tracking-tighter drop-shadow-md" style="color: var(--text-primary)">
          智宠 <span class="text-orange-400">平台</span>
        </h1>
      </div>

      <!-- 桌面端导航 -->
      <div class="hidden md:flex gap-2">
        <button
          v-for="item in navItems"
          :key="item.path"
          @click="navigate(item.path)"
          :class="[
            'flex items-center gap-2 px-4 py-2 text-sm font-bold transition-all duration-300 rounded-xl border',
            route.path === item.path
              ? 'bg-orange-500 border-orange-400 text-white shadow-lg shadow-orange-500/30'
              : 'border-transparent hover:bg-black/10'
          ]"
          :style="route.path === item.path ? '' : `color: var(--text-secondary)`"
        >
          <component :is="item.icon" :size="16" />
          {{ item.name }}
        </button>
      </div>

      <!-- 右侧操作区 -->
      <div class="flex items-center gap-2">
        <!-- 主题切换按钮 -->
        <button
          @click="themeStore.toggleDark()"
          class="hidden md:flex p-2 rounded-full border transition-all hover:scale-110"
          :style="`border-color: var(--border); background: var(--bg-subtle); color: var(--text-secondary)`"
        >
          <Sun v-if="themeStore.isDark" :size="18" />
          <Moon v-else :size="18" />
        </button>

        <!-- 搜索按钮 -->
        <button
          @click="emit('open-command')"
          class="hidden md:flex p-2 rounded-full border transition-all"
          :style="`border-color: var(--border); background: var(--bg-subtle); color: var(--text-secondary)`"
        >
          <Search :size="18" />
        </button>

        <!-- 写实头像 (桌面端) -->
        <div
          @click="navigate('/profile')"
          class="hidden md:block w-9 h-9 rounded-full border-2 overflow-hidden cursor-pointer hover:border-orange-400 transition-colors shadow-lg shadow-orange-500/10"
          style="border-color: var(--border)"
        >
          <img :src="authStore.user?.avatar_url || getRealisticAvatar(authStore.user?.username || 'Lucky')" alt="avatar" class="w-full h-full object-cover" />
        </div>

        <!-- 汉堡菜单 -->
        <button
          @click="drawerOpen = true"
          class="md:hidden p-2 rounded-xl border transition-all"
          :style="`border-color: var(--border); background: var(--bg-subtle); color: var(--text-secondary)`"
        >
          <Menu :size="22" />
        </button>
      </div>
    </div>
  </nav>

  <!-- 手机端抽屉 -->
  <Teleport to="body">
    <transition name="drawer-fade">
      <div v-if="drawerOpen" class="fixed inset-0 z-[200] bg-black/60 backdrop-blur-sm md:hidden" @click="drawerOpen = false" />
    </transition>

    <transition name="drawer-slide">
      <div v-if="drawerOpen" class="fixed top-0 right-0 z-[210] h-full w-[88vw] max-w-72 border-l shadow-2xl md:hidden flex flex-col" :style="`background: var(--bg-card); border-color: var(--border)`">
        <div class="flex items-center justify-between px-6 py-5 border-b" :style="`border-color: var(--border)`">
          <div class="flex items-center gap-3">
            <div class="bg-orange-500 p-1.5 rounded-lg text-white"><PawPrint :size="16" /></div>
            <span class="font-black tracking-tight" :style="`color: var(--text-primary)`">智宠平台</span>
          </div>
          <button @click="drawerOpen = false" class="p-1.5 rounded-lg transition-all" :style="`color: var(--text-muted)`"><X :size="18" /></button>
        </div>

        <!-- 手机端头像区 -->
        <div class="px-6 py-4 border-b" :style="`border-color: var(--border)`">
          <div v-if="authStore.isLoggedIn" class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full border-2 border-orange-500/40 overflow-hidden">
              <img :src="authStore.user?.avatar_url || getRealisticAvatar(authStore.user?.username || 'Lucky')" class="w-full h-full object-cover" />
            </div>
            <div>
              <p class="font-bold text-sm" :style="`color: var(--text-primary)`">{{ authStore.user?.username }}</p>
              <p class="text-[10px] text-orange-400 font-black uppercase tracking-wider">{{ authStore.roleName }}</p>
            </div>
          </div>
          <div v-else class="text-sm" :style="`color: var(--text-muted)`">未登录</div>
        </div>

        <nav class="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
          <button v-for="item in navItems" :key="item.path" @click="navigate(item.path)" :class="['w-full flex items-center gap-4 px-4 py-3.5 rounded-2xl text-sm font-bold transition-all border', route.path === item.path ? 'bg-orange-500/15 text-orange-400 border-orange-500/30' : 'border-transparent']" :style="route.path === item.path ? '' : `color: var(--text-secondary)`">
            <component :is="item.icon" :size="18" /> {{ item.name }}
          </button>
        </nav>

        <div class="px-4 py-4 border-t space-y-2" :style="`border-color: var(--border)`">
          <button @click="navigate('/profile')" class="w-full flex items-center gap-4 px-4 py-3 rounded-2xl text-sm font-bold transition-all" :style="`color: var(--text-secondary)`"><User :size="18" /> 个人主页</button>
          <button v-if="authStore.isLoggedIn" @click="handleLogout" class="w-full flex items-center gap-4 px-4 py-3 rounded-2xl text-sm font-bold text-red-400 hover:bg-red-500/10 transition-all"><LogOut :size="18" /> 退出登录</button>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.drawer-fade-enter-active, .drawer-fade-leave-active { transition: opacity 0.25s ease; }
.drawer-fade-enter-from, .drawer-fade-leave-to { opacity: 0; }
.drawer-slide-enter-active, .drawer-slide-leave-active { transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.drawer-slide-enter-from, .drawer-slide-leave-to { transform: translateX(100%); }
</style>
