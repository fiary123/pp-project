<script setup lang="ts">
import { ref } from 'vue';
import AppHeader from './components/AppHeader.vue'
import CommandPalette from './components/CommandPalette.vue'
import { useThemeStore } from './store/themeStore'

const paletteRef = ref<any>(null)
const openPalette = () => paletteRef.value?.toggle()

// 初始化主题
useThemeStore()
</script>

<template>
  <div class="app-root relative min-h-screen w-full overflow-x-hidden font-sans antialiased selection:bg-orange-500/30 transition-colors duration-500">

    <!-- 动态主题背景层 -->
    <div class="fixed inset-0 -z-10 app-bg transition-colors duration-500" />

    <!-- 沉浸式导航栏 -->
    <AppHeader @open-command="openPalette" />

    <!-- 智能指令中心 -->
    <CommandPalette ref="paletteRef" />

    <!-- 主内容区域 -->
    <main class="relative pt-28 pb-12 px-4 sm:px-6 lg:px-8 max-w-[1600px] mx-auto">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style>
/* ── 全局主题变量系统 ── */
:root {
  /* 默认浅色模式 (Light) */
  --bg-main: #fcfcfc;
  --bg-card: #ffffff;
  --bg-subtle: rgba(0,0,0,0.02);
  --border: rgba(0,0,0,0.06);
  --text-primary: #111827;
  --text-secondary: #4b5563;
  --nav-bg: rgba(255,255,255,0.8);
  --scrollbar: rgba(0,0,0,0.1);
}

.dark {
  /* 深色模式 (Dark) */
  --bg-main: #0a0a0a;
  --bg-card: #111111;
  --bg-subtle: rgba(255,255,255,0.03);
  --border: rgba(255,255,255,0.08);
  --text-primary: #ffffff;
  --text-secondary: #9ca3af;
  --nav-bg: rgba(0,0,0,0.6);
  --scrollbar: rgba(255,255,255,0.1);
}

.app-bg {
  background-color: var(--bg-main);
  /* 保持高级的极光纹理，降低深色模式下的对比度 */
  background-image: 
    radial-gradient(circle at 20% 20%, rgba(249,115,22,0.05) 0%, transparent 40%),
    radial-gradient(circle at 80% 80%, rgba(249,115,22,0.03) 0%, transparent 40%);
}

.app-root {
  background-color: var(--bg-main);
  color: var(--text-primary);
}

/* 丝滑的全局色彩过渡 */
* {
  transition-property: background-color, border-color, color, fill, stroke;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 300ms;
}

/* 动画与滚动条保持不变... */
.fade-slide-enter-active, .fade-slide-leave-active { transition: all 0.4s ease; }
.fade-slide-enter-from { opacity: 0; transform: translateY(10px); }
.fade-slide-leave-to { opacity: 0; transform: translateY(-10px); }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-thumb { background: var(--scrollbar); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #f97316; }
</style>
