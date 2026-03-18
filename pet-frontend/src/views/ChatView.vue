<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '../store/authStore';
import { Send, ChevronLeft, Loader2, Sparkles } from 'lucide-vue-next';
import BaseCard from '../components/BaseCard.vue';
import api from '../api';

interface Message {
  id: number;
  sender_id: number;
  receiver_id: number;
  content: string;
  sender_name?: string;
  create_time: string;
}

const authStore = useAuthStore();
const route = useRoute();

// 1. 状态管理
const messages = ref<Message[]>([]);
const userInput = ref('');
const isInitialLoading = ref(true);
const errorMsg = ref('');
const scrollContainer = ref<HTMLElement | null>(null);
let pollTimer: ReturnType<typeof setInterval> | null = null;

// 2. 加载消息 (支持静默模式)
const fetchMessages = async (silent = false) => {
  if (!silent) isInitialLoading.value = true;
  try {
    const res = await api.get<Message[]>(`/api/messages/${authStore.user?.id || 1}`);
    if (res.data.length !== messages.value.length) {
      messages.value = res.data;
      scrollToBottom();
    }
  } catch {
    if (!silent) errorMsg.value = '消息加载失败，请刷新重试';
  } finally {
    isInitialLoading.value = false;
  }
};

// 3. 发送消息
const handleSend = async () => {
  if (!userInput.value.trim()) return;
  const content = userInput.value;
  userInput.value = '';

  const receiverId = Number(route.query.to) || 2;
  try {
    await api.post('/api/messages/send', {
      sender_id: authStore.user?.id || 1,
      receiver_id: receiverId,
      content: content
    });
    fetchMessages(true);
  } catch {
    errorMsg.value = '发送失败，请重试';
    userInput.value = content;
  }
};

const scrollToBottom = async () => {
  await nextTick();
  if (scrollContainer.value) {
    scrollContainer.value.scrollTo({
      top: scrollContainer.value.scrollHeight,
      behavior: 'smooth'
    });
  }
};

// 4. 生命周期：启动/销毁实时轮询
onMounted(() => {
  fetchMessages();
  pollTimer = setInterval(() => {
    fetchMessages(true);
  }, 3000);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
});
</script>

<template>
  <div class="max-w-5xl mx-auto h-[85vh] flex gap-6 pb-10 px-4">
    <!-- 左侧列表 -->
    <BaseCard class="hidden md:flex flex-col w-80 !p-0 overflow-hidden border-white/5 bg-black/40">
      <div class="p-6 border-b border-white/5 flex items-center justify-between">
        <h3 class="font-black text-white italic uppercase tracking-tighter">Sessions</h3>
        <div class="flex items-center gap-1.5">
          <span class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          <span class="text-[8px] text-gray-500 font-bold uppercase tracking-widest">Real-time</span>
        </div>
      </div>
      <div class="flex-1 overflow-y-auto">
        <div class="p-5 bg-orange-500/10 border-l-4 border-orange-500 flex items-center gap-4 cursor-pointer transition-all">
          <div class="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center border border-white/10 text-orange-500">
            <Sparkles :size="24" />
          </div>
          <div>
            <p class="text-sm font-bold text-white tracking-tight">平台官方助理</p>
            <p class="text-[9px] text-orange-400 font-bold uppercase mt-0.5">Active Channel</p>
          </div>
        </div>
      </div>
    </BaseCard>

    <!-- 右侧窗口 -->
    <div class="flex-1 flex flex-col rounded-[3rem] border border-white/5 overflow-hidden bg-white/5 backdrop-blur-3xl shadow-2xl relative">
      <!-- 头部 -->
      <div class="p-6 bg-black/20 border-b border-white/5 flex items-center justify-between flex-shrink-0">
        <div class="flex items-center gap-4">
          <button @click="$router.back()" class="md:hidden p-2 text-gray-400 hover:text-white"><ChevronLeft /></button>
          <div class="relative">
            <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Admin" class="w-12 h-12 rounded-2xl border border-orange-500/20" />
            <div class="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 border-2 border-black rounded-full"></div>
          </div>
          <div>
            <h4 class="font-black text-white tracking-tight">领养咨询专家</h4>
            <p class="text-[9px] text-gray-500 font-bold uppercase tracking-[0.2em]">Response time: &lt; 5 mins</p>
          </div>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="errorMsg" class="px-8 py-3 bg-red-500/10 border-b border-red-500/20 text-red-400 text-xs font-bold">
        {{ errorMsg }}
      </div>

      <!-- 消息区域 -->
      <div v-if="isInitialLoading" class="flex-1 flex items-center justify-center">
        <Loader2 class="animate-spin text-orange-500" :size="48" />
      </div>

      <div v-else ref="scrollContainer" class="flex-1 p-8 overflow-y-auto space-y-8 scrollbar-hide">
        <div v-for="m in messages" :key="m.id"
             :class="m.sender_id === authStore.user?.id ? 'flex-row-reverse' : 'flex-row'"
             class="flex items-start gap-4 animate-in fade-in slide-in-from-bottom-2">
          <div class="w-10 h-10 rounded-xl bg-white/5 overflow-hidden flex-shrink-0 border border-white/10 shadow-lg">
            <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${m.sender_name || 'User'}`" />
          </div>
          <div :class="m.sender_id === authStore.user?.id ? 'bg-orange-500 text-white rounded-tr-none' : 'bg-white/10 text-gray-200 rounded-tl-none border border-white/5'"
               class="max-w-[75%] p-5 rounded-[1.5rem] text-sm leading-relaxed shadow-xl break-words">
            {{ m.content }}
          </div>
        </div>
      </div>

      <!-- 输入框 -->
      <div class="p-8 bg-black/40 border-t border-white/5 flex-shrink-0">
        <div class="flex gap-4 items-center">
          <input
            v-model="userInput"
            @keyup.enter="handleSend"
            placeholder="在此输入您的咨询信息..."
            class="flex-1 bg-white/5 border border-white/10 rounded-[1.5rem] py-5 px-8 text-sm text-white focus:border-orange-500 outline-none transition-all placeholder:text-gray-600 shadow-inner"
          />
          <button @click="handleSend" class="p-5 bg-orange-500 rounded-[1.5rem] text-white hover:bg-orange-600 transition-all shadow-xl shadow-orange-500/30 active:scale-95">
            <Send :size="24" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@reference "tailwindcss";
.scrollbar-hide::-webkit-scrollbar { display: none; }
</style>
