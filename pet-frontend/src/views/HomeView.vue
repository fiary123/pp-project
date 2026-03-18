<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { 
  ArrowRight, ShieldCheck, Zap, Heart, Sparkles,
  Plus, Trash2, Loader2, X, Megaphone
} from 'lucide-vue-next';
import { useAuthStore } from '../store/authStore';
import axios from '../api/index';

const authStore = useAuthStore();
const announcements = ref<any[]>([]);
const isLoadingAnnouncements = ref(false);

// 管理员功能状态
const showAnnounceModal = ref(false);
const isPublishing = ref(false);
const announceForm = ref({ title: '', content: '', is_hot: 0 });

const fetchAnnouncements = async () => {
  isLoadingAnnouncements.value = true;
  try {
    const res = await axios.get('/api/announcements');
    announcements.value = res.data;
  } catch (err) {
    // 兜底模拟数据
    announcements.value = [
      { id: 1, title: '关于周末举办线下领养日的通知', date: '2026-03-05', is_hot: 1, content: '请参加活动的领养人携带好身份证件，我们将在中心公园准时开始。' },
      { id: 2, title: 'AI 宠物翻译官功能正式上线', date: '2026-03-02', is_hot: 0, content: '现在您可以通过上传视频，让 AI 分析宠物的肢体语言。' }
    ];
  } finally {
    isLoadingAnnouncements.value = false;
  }
};

const isAdmin = computed(() => authStore.user?.role === 'org_admin' || authStore.user?.role === 'root');

const handlePublishAnnounce = async () => {
  if (!announceForm.value.title) return;
  isPublishing.value = true;
  try {
    await axios.post('/api/announcements', announceForm.value);
    fetchAnnouncements();
    showAnnounceModal.value = false;
    announceForm.value = { title: '', content: '', is_hot: 0 };
  } catch (err: any) {
    const msg = err?.response?.data?.detail || '发布失败，请检查后端服务或登录状态';
    alert(msg);
  }
  finally { isPublishing.value = false; }
};

const handleDeleteAnnounce = async (id: number) => {
  if (!confirm('确定删除此公告？')) return;
  try {
    await axios.delete(`/api/announcements/${id}`);
    announcements.value = announcements.value.filter(a => a.id !== id);
  } catch (err) {
    announcements.value = announcements.value.filter(a => a.id !== id);
  }
};

onMounted(fetchAnnouncements);
</script>

<template>
  <div class="space-y-24 pb-20">
    <!-- Hero Section -->
    <section class="relative h-[90vh] flex items-center justify-center overflow-hidden rounded-[4rem] mx-4 mt-4 shadow-2xl">
      <div class="absolute inset-0 bg-gradient-to-br from-orange-600/20 via-black to-black z-10"></div>
      <img src="https://images.unsplash.com/photo-1450778869180-41d0601e046e?auto=format&fit=crop&w=2000&q=80" class="absolute inset-0 w-full h-full object-cover grayscale opacity-40" />
      
      <div class="relative z-20 text-center space-y-8 max-w-5xl px-6">
        <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-orange-500/10 border border-orange-500/20 text-orange-500 text-xs font-black tracking-widest uppercase animate-bounce">
          <Sparkles :size="14" /> AI 智能宠物平台
        </div>
        <h2 class="text-8xl md:text-9xl font-black text-white italic tracking-tighter leading-[0.8] uppercase">心灵 <br/> <span class="text-orange-500">相连接</span></h2>
        <p class="text-xl text-gray-400 font-medium max-w-2xl mx-auto leading-relaxed">利用先进的 AI 技术，为您与生命中的另一半建立深厚的情感连接。</p>
        <div class="flex flex-wrap justify-center gap-6 pt-8">
          <button @click="$router.push('/triage')" class="bg-orange-500 hover:bg-orange-600 text-white px-12 py-6 rounded-3xl font-black text-xl transition-all hover:scale-105 shadow-2xl flex items-center gap-3 uppercase italic">立即开始 <ArrowRight :size="24" /></button>
          <button @click="$router.push('/wiki')" class="bg-white/5 hover:bg-white/10 text-white px-12 py-6 rounded-3xl font-black text-xl border border-white/10 backdrop-blur-xl transition-all uppercase italic">了解更多</button>
        </div>
      </div>
    </section>

    <!-- 公告板块 -->
    <section class="max-w-7xl mx-auto px-6">
      <div class="flex items-end justify-between mb-12">
        <div class="space-y-2">
          <h3 class="text-5xl font-black text-white italic uppercase tracking-tighter">平台公告</h3>
          <p class="text-gray-500 font-bold uppercase tracking-widest text-xs">站内新鲜事与官方动态</p>
        </div>
        <!-- 管理员发布按钮 -->
        <button v-if="isAdmin" @click="showAnnounceModal = true" class="bg-orange-500 hover:bg-orange-600 text-white px-6 py-3 rounded-2xl font-black flex items-center gap-2 transition-all active:scale-95 shadow-xl">
          <Plus :size="18" /> 发布新公告
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div v-for="item in announcements" :key="item.id" class="group bg-white/5 border border-white/5 p-8 rounded-[2.5rem] hover:border-orange-500/30 transition-all relative">
          <div class="flex justify-between items-start mb-4">
            <span v-if="item.is_hot" class="px-3 py-1 bg-orange-500 text-white text-[10px] font-black rounded-full uppercase italic">热门</span>
            <span class="text-gray-600 font-mono text-xs ml-auto">{{ item.date }}</span>
          </div>
          <h4 class="text-2xl font-black text-white mb-4 group-hover:text-orange-500 transition-colors">{{ item.title }}</h4>
          <p class="text-gray-400 text-sm leading-relaxed line-clamp-2">{{ item.content }}</p>
          
          <!-- 管理员删除按钮 -->
          <button v-if="isAdmin" @click="handleDeleteAnnounce(item.id)" class="absolute top-6 right-6 p-2 text-red-500/40 hover:text-red-500 transition-all opacity-0 group-hover:opacity-100">
            <Trash2 :size="18" />
          </button>
        </div>
      </div>
    </section>

    <!-- 特色板块 (保持原样) -->
    <section class="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-3 gap-12">
      <div v-for="feat in [
        { i: Zap, t: 'AI 智能匹配', d: '深度神经网络分析，为您匹配性格最契合的伴侣。' },
        { i: ShieldCheck, t: '机构认证', d: '严格的救助机构资质审核，确保每一条信息的真实性。' },
        { i: Heart, t: '全程陪伴', d: '全生命周期的养护指导，从医疗到行为纠正一应俱全。' }
      ]" :key="feat.t" class="space-y-6 p-8 rounded-[3rem] bg-gradient-to-b from-white/5 to-transparent border border-white/5 hover:border-orange-500/30 transition-all group">
        <div class="w-16 h-16 bg-orange-500 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-orange-500/20 group-hover:rotate-12 transition-transform">
          <component :is="feat.i" :size="32" />
        </div>
        <h3 class="text-3xl font-black text-white italic uppercase tracking-tighter">{{ feat.t }}</h3>
        <p class="text-gray-500 font-medium leading-relaxed">{{ feat.d }}</p>
      </div>
    </section>

    <!-- 公告发布弹窗 -->
    <Teleport to="body">
      <div v-if="showAnnounceModal" class="fixed inset-0 z-[600] flex items-center justify-center bg-black/95 backdrop-blur-md px-4">
        <div class="bg-[#111] border border-white/10 p-10 rounded-[3rem] w-full max-w-xl space-y-6">
          <div class="flex justify-between items-center"><h3 class="text-2xl font-black text-white italic uppercase flex items-center gap-2"><Megaphone class="text-orange-500" /> 发布新公告</h3><button @click="showAnnounceModal=false" class="text-gray-500"><X :size="24"/></button></div>
          <div class="space-y-4">
            <input v-model="announceForm.title" placeholder="公告标题" class="w-full bg-white/5 border border-white/10 rounded-xl px-6 py-4 text-white outline-none focus:border-orange-500" />
            <textarea v-model="announceForm.content" placeholder="公告详细内容..." class="w-full h-40 bg-white/5 border border-white/10 rounded-xl p-6 text-white outline-none focus:border-orange-500"></textarea>
            <div class="flex items-center gap-3 p-4 bg-white/5 rounded-xl border border-white/10">
              <input type="checkbox" v-model="announceForm.is_hot" :true-value="1" :false-value="0" id="is_hot" class="accent-orange-500 w-4 h-4" />
              <label for="is_hot" class="text-sm text-gray-400 font-bold uppercase cursor-pointer">标记为热门公告</label>
            </div>
            <button @click="handlePublishAnnounce" :disabled="isPublishing" class="w-full bg-orange-500 text-white py-4 rounded-xl font-black text-lg hover:bg-orange-600 transition-all flex justify-center items-center gap-2">
              <Loader2 v-if="isPublishing" class="animate-spin" :size="20" />立即发布公告
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* @reference "tailwindcss"; */
</style>
