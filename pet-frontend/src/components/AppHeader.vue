<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { PawPrint, Handshake, BookOpen, Search, ShieldCheck, Users, Salad } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const emit = defineEmits(['open-command'])

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
}
</script>

<template>
  <nav class="fixed top-0 z-50 w-full border-b border-white/10 bg-black/20 backdrop-blur-lg">        
    <div class="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
      <!-- Logo 区域 -->
      <div class="flex items-center gap-3 cursor-pointer group" @click="navigate('/')">
        <div class="bg-orange-500 p-2 rounded-xl text-white shadow-lg shadow-orange-500/40 group-hover:scale-110 transition-transform">
          <PawPrint :size="20" />
        </div>
        <h1 class="text-xl font-black tracking-tighter text-white drop-shadow-md">
          智宠 <span class="text-orange-400">平台</span>
        </h1>
      </div>

      <!-- 导航项 -->
      <div class="hidden md:flex gap-2">
        <button
          v-for="item in navItems"
          :key="item.path"
          @click="navigate(item.path)"
          :class="[
            'flex items-center gap-2 px-4 py-2 text-sm font-bold transition-all duration-300 rounded-xl border',
            route.path === item.path
              ? 'bg-orange-500 border-orange-400 text-white shadow-lg shadow-orange-500/30'
              : 'text-gray-300 border-transparent hover:bg-white/10 hover:text-white'
          ]"
        >
          <component :is="item.icon" :size="16" />
          {{ item.name }}
        </button>
      </div>

      <!-- 搜索和个人资料 -->
      <div class="flex items-center gap-4">
        <!-- 搜索按钮 -->
        <button
          @click="emit('open-command')"
          class="p-2 rounded-full bg-white/5 border border-white/10 text-gray-400 hover:text-orange-400 hover:bg-white/10 transition-all"
          title="智能搜索 (Ctrl+K)"
        >
          <Search :size="20" />
        </button>

        <div
          @click="navigate('/profile')"
          class="w-9 h-9 rounded-full border-2 border-white/20 overflow-hidden cursor-pointer hover:border-orange-400 transition-colors shadow-lg shadow-orange-500/10"
        >
          <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Lucky" alt="avatar" />
        </div>
      </div>
    </div>
  </nav>
</template>

<style scoped>
@reference "tailwindcss";
</style>
