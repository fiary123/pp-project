<script setup lang="ts">
import { ref } from 'vue';
import AppHeader from './components/AppHeader.vue'
import CommandPalette from './components/CommandPalette.vue'

const paletteRef = ref<any>(null)
const openPalette = () => paletteRef.value?.toggle()
</script>

<template>
  <div class="relative min-h-screen w-full overflow-x-hidden font-sans antialiased text-white selection:bg-orange-500/30">
    
    <!-- 全局沉浸式背景 -->
    <div class="fixed inset-0 -z-10 overflow-hidden">
      <div class="absolute inset-0 bg-gradient-to-b from-black/70 via-black/40 to-black/80 z-10"></div>
      <img 
        src="https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?q=80&w=2000" 
        class="h-full w-full object-cover scale-105 blur-[2px]"
        alt="background"
      />
    </div>

    <!-- 沉浸式导航栏 -->
    <AppHeader @open-command="openPalette" />

    <!-- 智能指令中心 -->
    <CommandPalette ref="paletteRef" />

    <!-- 主内容区域 -->
    <main class="relative pt-28 pb-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style>
@reference "tailwindcss";

/* 丝滑转场动画 */
.fade-slide-enter-active, 
.fade-slide-leave-active { 
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); 
}

.fade-slide-enter-from { 
  opacity: 0; 
  transform: translateY(15px); 
}

.fade-slide-leave-to { 
  opacity: 0; 
  transform: translateY(-15px); 
}

/* 统一滚动条风格 */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  @apply bg-transparent;
}
::-webkit-scrollbar-thumb {
  @apply bg-white/10 rounded-full hover:bg-orange-500/50 transition-colors;
}
</style>
