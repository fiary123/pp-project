<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../store/authStore';
import { Send, ChevronLeft, Loader2, MessageCircle } from 'lucide-vue-next';
import BaseCard from '../components/BaseCard.vue';
import api from '../api';

interface Message {
  id: number;
  sender_id: number;
  receiver_id: number;
  content: string;
  sender_name?: string;
  receiver_name?: string;
  create_time: string;
}

interface Contact {
  other_id: number;
  other_name: string;
  last_msg: string;
  last_time: string;
}

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();

// 状态
const contacts = ref<Contact[]>([]);
const messages = ref<Message[]>([]);
const userInput = ref('');
const isInitialLoading = ref(true);
const isMsgLoading = ref(false);
const errorMsg = ref('');
const scrollContainer = ref<HTMLElement | null>(null);
const activeContactId = ref<number | null>(null);
const activeContactName = ref('');
let pollTimer: ReturnType<typeof setInterval> | null = null;

// 获取联系人列表
const fetchContacts = async () => {
  const uid = authStore.user?.id;
  if (!uid) return;
  try {
    const res = await api.get<Contact[]>(`/api/user/messages/${uid}/contacts`);
    contacts.value = res.data;
  } catch {
    // 联系人加载失败静默处理
  }
};

// 获取与指定用户的对话
const fetchMessages = async (silent = false) => {
  const uid = authStore.user?.id;
  if (!uid || !activeContactId.value) return;
  if (!silent) isMsgLoading.value = true;
  try {
    const res = await api.get<Message[]>(
      `/api/user/messages/${uid}/with/${activeContactId.value}`
    );
    if (res.data.length !== messages.value.length) {
      messages.value = res.data;
      scrollToBottom();
    }
  } catch {
    if (!silent) errorMsg.value = '消息加载失败，请刷新重试';
  } finally {
    isMsgLoading.value = false;
    isInitialLoading.value = false;
  }
};

// 切换对话
const selectContact = (contactId: number, contactName: string) => {
  activeContactId.value = contactId;
  activeContactName.value = contactName;
  messages.value = [];
  errorMsg.value = '';
  router.replace({ query: { to: String(contactId) } });
  fetchMessages();
};

// 发送消息
const handleSend = async () => {
  if (!userInput.value.trim() || !activeContactId.value) return;
  const content = userInput.value;
  userInput.value = '';
  const uid = authStore.user?.id;
  try {
    await api.post('/api/user/messages/send', {
      sender_id: uid,
      receiver_id: activeContactId.value,
      content
    });
    await fetchMessages(true);
    await fetchContacts();
  } catch {
    errorMsg.value = '发送失败，请重试';
    userInput.value = content;
  }
};

const scrollToBottom = async () => {
  await nextTick();
  if (scrollContainer.value) {
    scrollContainer.value.scrollTo({ top: scrollContainer.value.scrollHeight, behavior: 'smooth' });
  }
};

// 格式化时间：今天显示 HH:mm，否则显示 MM-DD
const formatTime = (ts: string) => {
  if (!ts) return '';
  const d = new Date(ts);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

onMounted(async () => {
  isInitialLoading.value = true;
  await fetchContacts();

  // 优先从 query param 恢复对话，否则默认选第一个联系人
  const toId = Number(route.query.to);
  if (toId) {
    const found = contacts.value.find(c => c.other_id === toId);
    selectContact(toId, found?.other_name || `用户${toId}`);
  } else if (contacts.value.length > 0) {
    selectContact(contacts.value[0]!.other_id, contacts.value[0]!.other_name);
  } else {
    isInitialLoading.value = false;
  }

  pollTimer = setInterval(async () => {
    await fetchMessages(true);
    await fetchContacts();
  }, 3000);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
});
</script>

<template>
  <div class="max-w-5xl mx-auto h-[85vh] flex gap-6 pb-10 px-4">
    <!-- 左侧联系人列表 -->
    <BaseCard class="hidden md:flex flex-col w-80 !p-0 overflow-hidden border-white/5 bg-black/40">
      <div class="p-6 border-b border-white/5 flex items-center justify-between">
        <h3 class="font-black text-white italic uppercase tracking-tighter">私信</h3>
        <div class="flex items-center gap-1.5">
          <span class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          <span class="text-[8px] text-gray-500 font-bold uppercase tracking-widest">Real-time</span>
        </div>
      </div>
      <div class="flex-1 overflow-y-auto">
        <!-- 无联系人提示 -->
        <div v-if="contacts.length === 0" class="p-8 text-center text-gray-600 text-sm space-y-2">
          <MessageCircle class="mx-auto text-gray-700" :size="32" />
          <p>暂无会话</p>
          <p class="text-xs text-gray-700">从用户主页发起私信</p>
        </div>
        <!-- 联系人列表 -->
        <div
          v-for="c in contacts"
          :key="c.other_id"
          @click="selectContact(c.other_id, c.other_name)"
          :class="activeContactId === c.other_id
            ? 'bg-orange-500/10 border-l-4 border-orange-500'
            : 'border-l-4 border-transparent hover:bg-white/5'"
          class="p-4 flex items-center gap-3 cursor-pointer transition-all"
        >
          <div class="w-10 h-10 rounded-xl overflow-hidden flex-shrink-0 border border-white/10">
            <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${c.other_name}`" />
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between">
              <p class="text-sm font-bold text-white truncate">{{ c.other_name }}</p>
              <span class="text-[9px] text-gray-600 flex-shrink-0 ml-1">{{ formatTime(c.last_time) }}</span>
            </div>
            <p class="text-[10px] text-gray-500 truncate mt-0.5">{{ c.last_msg }}</p>
          </div>
        </div>
      </div>
    </BaseCard>

    <!-- 右侧对话窗口 -->
    <div class="flex-1 flex flex-col rounded-[3rem] border border-white/5 overflow-hidden bg-white/5 backdrop-blur-3xl shadow-2xl relative">
      <!-- 头部 -->
      <div class="p-6 bg-black/20 border-b border-white/5 flex items-center gap-4 flex-shrink-0">
        <button @click="$router.back()" class="md:hidden p-2 text-gray-400 hover:text-white"><ChevronLeft /></button>
        <div class="relative" v-if="activeContactId">
          <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${activeContactName}`" class="w-12 h-12 rounded-2xl border border-orange-500/20" />
          <div class="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 border-2 border-black rounded-full"></div>
        </div>
        <div v-if="activeContactId">
          <h4 class="font-black text-white tracking-tight">{{ activeContactName }}</h4>
          <p class="text-[9px] text-gray-500 font-bold uppercase tracking-[0.2em]">私信对话</p>
        </div>
        <div v-else class="text-gray-500 text-sm">请选择一个联系人</div>
      </div>

      <!-- 错误提示 -->
      <div v-if="errorMsg" class="px-8 py-3 bg-red-500/10 border-b border-red-500/20 text-red-400 text-xs font-bold">
        {{ errorMsg }}
      </div>

      <!-- 加载中 -->
      <div v-if="isInitialLoading || isMsgLoading" class="flex-1 flex items-center justify-center">
        <Loader2 class="animate-spin text-orange-500" :size="48" />
      </div>

      <!-- 无对话选中 -->
      <div v-else-if="!activeContactId" class="flex-1 flex flex-col items-center justify-center text-gray-600 space-y-3">
        <MessageCircle :size="48" />
        <p class="text-sm">从左侧选择联系人开始对话</p>
      </div>

      <!-- 消息列表 -->
      <div v-else ref="scrollContainer" class="flex-1 p-8 overflow-y-auto space-y-6 scrollbar-hide">
        <div v-if="messages.length === 0" class="text-center text-gray-600 text-sm py-16">
          还没有消息，发送第一条吧 👋
        </div>
        <div
          v-for="m in messages"
          :key="m.id"
          :class="m.sender_id === authStore.user?.id ? 'flex-row-reverse' : 'flex-row'"
          class="flex items-end gap-3 animate-in fade-in slide-in-from-bottom-2"
        >
          <div class="w-9 h-9 rounded-xl bg-white/5 overflow-hidden flex-shrink-0 border border-white/10">
            <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${m.sender_name || 'User'}`" />
          </div>
          <div class="flex flex-col gap-1" :class="m.sender_id === authStore.user?.id ? 'items-end' : 'items-start'">
            <div
              :class="m.sender_id === authStore.user?.id
                ? 'bg-orange-500 text-white rounded-tr-none'
                : 'bg-white/10 text-gray-200 rounded-tl-none border border-white/5'"
              class="max-w-xs px-5 py-3 rounded-[1.5rem] text-sm leading-relaxed shadow-xl break-words"
            >
              {{ m.content }}
            </div>
            <span class="text-[9px] text-gray-600 px-1">{{ formatTime(m.create_time) }}</span>
          </div>
        </div>
      </div>

      <!-- 输入框 -->
      <div class="p-6 bg-black/40 border-t border-white/5 flex-shrink-0">
        <div class="flex gap-3 items-center">
          <input
            v-model="userInput"
            @keyup.enter="handleSend"
            :disabled="!activeContactId"
            placeholder="在此输入消息..."
            class="flex-1 bg-white/5 border border-white/10 rounded-[1.5rem] py-4 px-6 text-sm text-white focus:border-orange-500 outline-none transition-all placeholder:text-gray-600 disabled:opacity-40"
          />
          <button
            @click="handleSend"
            :disabled="!activeContactId || !userInput.trim()"
            class="p-4 bg-orange-500 rounded-[1.5rem] text-white hover:bg-orange-600 transition-all shadow-xl shadow-orange-500/30 active:scale-95 disabled:bg-orange-500/40 disabled:cursor-not-allowed"
          >
            <Send :size="22" />
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
