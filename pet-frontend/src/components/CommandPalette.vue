<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Search, Sparkles, MoveRight, X } from 'lucide-vue-next'
import BaseCard from './BaseCard.vue'

const isOpen = ref(false)
const query = ref('')

// 模拟 Agent 联想结果
const suggestions = [
  { id: 1, text: '我想领养一只在上海的柯基', category: '智能搜索' },
  { id: 2, text: '下周出差三天，需要有人帮我喂猫', category: '宠物互助' },
  { id: 3, text: '如何训练狗狗定点排便', category: '百科知识' }
]

const toggle = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) query.value = ''
}

// 快捷键支持 (Ctrl + K)
const handleKeydown = (e: KeyboardEvent) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    toggle()
  }
  if (e.key === 'Escape' && isOpen.value) {
    isOpen.value = false
  }
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))

defineExpose({ toggle })
</script>

<template>
  <Teleport to="body">
    <transition name="scale">
      <div v-if="isOpen" class="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] px-4 bg-black/60 backdrop-blur-sm" @click.self="toggle">
        
        <div class="w-full max-w-2xl transform">
          <BaseCard class="!p-0 overflow-hidden shadow-[0_0_50px_rgba(249,115,22,0.2)] border-white/20">
            <!-- 搜索框 -->
            <div class="flex items-center px-6 py-5 border-b border-white/10">
              <Search class="text-orange-500 mr-4" :size="24" />
              <input 
                v-model="query"
                type="text" 
                class="flex-1 bg-transparent text-xl text-white outline-none placeholder:text-gray-500"
                placeholder="键入您的需求，例如：'我想领养...'"
                autofocus
              />
              <button @click="toggle" class="text-gray-500 hover:text-white transition-colors">
                <X :size="20" />
              </button>
            </div>

            <!-- 联想建议 -->
            <div class="p-4 space-y-2 max-h-[400px] overflow-y-auto">
              <div v-for="item in suggestions" :key="item.id" 
                   class="flex items-center justify-between p-4 rounded-2xl hover:bg-white/10 cursor-pointer transition-all group">
                <div class="flex items-center gap-4">
                  <div class="p-2 rounded-lg bg-orange-500/10 text-orange-400">
                    <Sparkles :size="18" />
                  </div>
                  <div>
                    <p class="text-white font-medium">{{ item.text }}</p>
                    <p class="text-[10px] text-gray-500 uppercase tracking-widest">{{ item.category }}</p>
                  </div>
                </div>
                <MoveRight class="text-gray-600 group-hover:text-orange-500 group-hover:translate-x-1 transition-all" :size="18" />
              </div>
            </div>

            <!-- 底部提示 -->
            <div class="px-6 py-3 bg-white/5 border-t border-white/10 flex justify-between items-center">
              <div class="flex gap-4 text-[10px] text-gray-500">
                <span><kbd class="bg-white/10 px-1.5 py-0.5 rounded text-gray-300">Enter</kbd> 确认查询</span>
                <span><kbd class="bg-white/10 px-1.5 py-0.5 rounded text-gray-300">Esc</kbd> 退出</span>
              </div>
              <div class="flex items-center gap-1 text-[10px] text-orange-500/80 font-bold">
                <Sparkles :size="12" /> AI 专家驱动
              </div>
            </div>
          </BaseCard>
        </div>

      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
@reference "tailwindcss";

.scale-enter-active, .scale-leave-active {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.scale-enter-from, .scale-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(-20px);
}

kbd { font-family: sans-serif; }
</style>
