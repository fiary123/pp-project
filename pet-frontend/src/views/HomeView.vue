<script setup lang="ts">
import { ref, onMounted, computed, markRaw } from 'vue';
import { 
  ArrowRight, ShieldCheck, Zap, Heart, Sparkles,
  Plus, Trash2, Loader2, X, Megaphone, RefreshCw, Calendar
} from 'lucide-vue-next';
import { useAuthStore } from '../store/authStore';
import axios from '../api/index';

const authStore = useAuthStore();
const announcements = ref<any[]>([]);
const isLoadingAnnouncements = ref(false);
const selectedAnnounce = ref<any>(null); // 新增：当前选中的公告

const defaultAnnouncements = [
  {
    id: 1,
    title: '智能领养辅助评估功能已正式上线',
    date: '2026-03-25',
    is_hot: 1,
    content: '尊敬的用户：\n\n我们非常激动地宣布，智慧宠物平台的核心功能——“AI 智能领养辅助评估系统”现已正式上线。该系统集成了三个专业的 AI 代理专家：品种分析专家、生活方式匹配专家和环境安全审核专家。当您提交领养申请后，专家团将从您的居住环境、陪伴时间、养宠经验等多个维度进行深度评估，并为送养方提供一份科学的决策报告。此举旨在降低二次弃养的风险，为每一只毛孩子寻找真正合适的归宿。'
  },
  {
    id: 2,
    title: '春季领养关爱主题活动现已启动',
    date: '2026-03-22',
    is_hot: 1,
    content: '万物复苏，爱心启航。平台现正式启动“春日寻家”领养月活动。在此期间，我们将加大对高龄宠物和长期滞留宠物的曝光力度。同时，成功通过平台领养宠物的用户，将获得由合作机构提供的首月免费宠物保险及基础体检套餐。我们倡导“领养代替购买”，更强调“理性领养”。请记住，领养不仅是一次心动的瞬间，更是一份长达十余年的生命承诺。'
  }
];

// 管理员功能状态
const showAnnounceModal = ref(false);
const isPublishing = ref(false);
const announceForm = ref({ title: '', content: '', is_hot: 0 });

const fetchAnnouncements = async () => {
  isLoadingAnnouncements.value = true;
  try {
    const res = await axios.get('/api/announcements');
    const data = Array.isArray(res.data) ? res.data : [];
    announcements.value = data.length > 0 ? data : defaultAnnouncements;
  } catch (err) {
    announcements.value = defaultAnnouncements;
  } finally {
    isLoadingAnnouncements.value = false;
  }
};

const isAdmin = computed(() => authStore.user?.role === 'admin');

const handlePublishAnnounce = async () => {
  if (!announceForm.value.title) return;
  isPublishing.value = true;
  try {
    await axios.post('/api/announcements', announceForm.value);
    fetchAnnouncements();
    showAnnounceModal.value = false;
    announceForm.value = { title: '', content: '', is_hot: 0 };
  } catch (err: any) {
    alert('发布失败');
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

const selectedTip = ref<any>(null);

const knowledgeTips = [
  { id: 1, tag: '喂养指南', tagClass: 'border-green-500/40 text-green-600 dark:text-green-400', species: '🐱 猫咪', title: '猫咪能吃哪些水果？', summary: '苹果、蓝莓、西瓜等水果少量喂食安全，但葡萄、柑橘、牛油果对猫有毒。', content: '猫是严格肉食动物...' },
  { id: 2, tag: '健康护理', tagClass: 'border-blue-500/40 text-blue-600 dark:text-blue-400', species: '🐶 狗狗', title: '天气冷需要穿毛衣吗？', summary: '短毛、无毛及小型犬在低温下需要保暖，但哈士奇等厚毛犬种不需要。', content: '并非所有狗都需要穿毛衣...' },
  { id: 3, tag: '日常护理', tagClass: 'border-orange-500/40 text-orange-600 dark:text-orange-400', species: '🐾 通用', title: '如何帮宠物缓解分离焦虑？', summary: '出门前先运动消耗体力，提供益智玩具转移注意力，告别时保持冷静。', content: '分离焦虑、破坏行为的解决方案...' },
  { id: 4, tag: '健康护理', tagClass: 'border-purple-500/40 text-purple-600 dark:text-purple-400', species: '🐱 猫咪', title: '摇晃猫综合征是什么？', summary: '猫小脑发育不全表现为走路踉跄、平衡差。不传染不恶化，能正常生活。', content: '病因、症状及护理要点...' },
  { id: 5, tag: '健康护理', tagClass: 'border-blue-500/40 text-blue-600 dark:text-blue-400', species: '🐱 猫咪', title: '幼猫便秘怎么办？', summary: '两天以上无便需关注。轻症可加南瓜泥缓解；出现呕吐须立即就医。', content: '症状、原因及居家处理...' },
  { id: 6, tag: '领养知识', tagClass: 'border-yellow-500/40 text-yellow-600 dark:text-yellow-400', species: '🐾 通用', title: '真的准备好领养了吗？', summary: '领养前需评估时间、经济、家庭共识等。遵循「3-3-3法则」建立信任。', content: '五大维度自查清单...' }
];

const displayTips = ref<any[]>([]);
const isRefreshing = ref(false);

const refreshTips = () => {
  isRefreshing.value = true;
  const shuffled = knowledgeTips.sort(() => 0.5 - Math.random());
  setTimeout(() => {
    displayTips.value = shuffled.slice(0, 4);
    isRefreshing.value = false;
  }, 300);
};

onMounted(() => {
  fetchAnnouncements();
  refreshTips();
});
</script>

<template>
  <div class="home-view space-y-16 md:space-y-24 pb-20 overflow-hidden bg-white dark:bg-[#0a0a0a] transition-colors duration-500">
    <!-- 1. Hero 顶部 -->
    <section class="relative min-h-[85vh] flex items-center justify-center pt-20">
      <div class="absolute inset-0 z-0">
        <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-orange-500/10 dark:bg-orange-500/20 blur-[120px] rounded-full"></div>
        <div class="absolute bottom-1/4 right-1/4 w-[30rem] h-[30rem] bg-blue-500/5 dark:bg-blue-500/10 blur-[150px] rounded-full"></div>
      </div>
      <div class="container relative z-10 px-4 md:px-6">
        <div class="max-w-4xl mx-auto text-center space-y-8 md:space-y-10">
          <div class="inline-flex items-center gap-2 px-4 py-2 bg-orange-500/10 rounded-full border border-orange-500/20">
            <Sparkles class="text-orange-500" :size="16" />
            <span class="text-xs font-black text-orange-500 tracking-[0.2em] uppercase">AI Powered Pet Care</span>
          </div>
          <h1 class="text-5xl md:text-8xl font-black italic tracking-tighter leading-[0.9]">
            <span class="text-gray-900 dark:text-white">GIVE THEM A</span><br />
            <span class="text-orange-500">BETTER HOME</span>
          </h1>
          <p class="text-lg md:text-xl text-gray-600 dark:text-gray-400 font-medium max-w-2xl mx-auto">
            连接爱心与责任。通过 AI 智能匹配、在线互助和专业知识库，为每一只流浪宠物寻找最适合的家。
          </p>
          <div class="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <router-link to="/adopt" class="w-full sm:w-auto px-10 py-5 bg-orange-500 hover:bg-orange-600 text-white font-black rounded-2xl transition-all shadow-xl">立即领养</router-link>
            <router-link to="/community" class="w-full sm:w-auto px-10 py-5 bg-gray-100 dark:bg-white/5 text-gray-900 dark:text-white font-black rounded-2xl border border-gray-200 dark:border-white/10">发布送养</router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- 2. 全站动态/公告 -->
    <section class="container mx-auto px-4 md:px-6">
      <div class="flex items-center justify-between mb-8 md:mb-12">
        <div class="space-y-2">
          <div class="flex items-center gap-2 text-orange-500">
            <Megaphone :size="18" />
            <span class="text-xs font-black uppercase tracking-widest">Platform Announcements</span>
          </div>
          <h2 class="text-3xl md:text-4xl font-black text-gray-900 dark:text-white italic">全站动态公告</h2>
        </div>
        <button v-if="isAdmin" @click="showAnnounceModal = true" class="p-3 bg-gray-100 dark:bg-white/5 hover:bg-orange-500 hover:text-white text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-white/10 rounded-xl transition-all">
          <Plus :size="20" />
        </button>
      </div>

      <div v-if="isLoadingAnnouncements" class="h-48 flex items-center justify-center">
        <Loader2 class="animate-spin text-orange-500" :size="32" />
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div v-for="item in announcements" :key="item.id" 
             @click="selectedAnnounce = item"
             class="group cursor-pointer relative bg-gray-50 dark:bg-white/[0.03] border border-gray-200 dark:border-white/5 rounded-3xl p-6 hover:bg-gray-100 dark:hover:bg-white/[0.06] transition-all flex items-start gap-5 shadow-sm dark:shadow-none">
          <div class="shrink-0 p-3 bg-orange-500/10 text-orange-500 rounded-2xl group-hover:scale-110 transition-transform">
            <Megaphone :size="20" />
          </div>
          <div class="flex-1 space-y-2 min-w-0">
            <div class="flex items-center gap-3">
              <h3 class="text-gray-900 dark:text-white font-black truncate text-lg">{{ item.title }}</h3>
              <span v-if="item.is_hot" class="px-2 py-0.5 bg-red-500 text-white text-[10px] font-black rounded uppercase italic">HOT</span>
            </div>
            <p class="text-sm text-gray-600 dark:text-gray-500 line-clamp-2 leading-relaxed">{{ item.content }}</p>
            <div class="flex items-center justify-between pt-2">
              <span class="text-[10px] text-gray-400 font-mono flex items-center gap-1"><Calendar :size="10" /> {{ item.date || item.create_time?.slice(0,10) }}</span>
              <button v-if="isAdmin" @click.stop="handleDeleteAnnounce(item.id)" class="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all">
                <Trash2 :size="14" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 3. 功能特色 -->
    <section class="container mx-auto px-4 md:px-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
        <div v-for="feature in [
          { icon: markRaw(ShieldCheck), title: '智能资质评估', desc: 'AI 专家团深度分析领养人画像，降低弃养风险。', color: 'text-orange-500' },
          { icon: markRaw(Zap), title: '极速互助响应', desc: '社区化互助系统，临时寄养、上门喂食一键发布。', color: 'text-blue-500' },
          { icon: markRaw(Heart), title: '终身成长记录', desc: '记录爱宠从领养到老去的点滴，打造温情数字档案。', color: 'text-pink-500' }
        ]" :key="feature.title" class="p-10 bg-gray-50 dark:bg-white/[0.02] border border-gray-200 dark:border-white/5 rounded-[2.5rem] hover:bg-gray-100 dark:hover:bg-white/[0.05] transition-all shadow-sm dark:shadow-none">
          <component :is="feature.icon" :class="feature.color" :size="48" class="mb-8" />
          <h3 class="text-xl font-black text-gray-900 dark:text-white mb-4 italic uppercase tracking-tight">{{ feature.title }}</h3>
          <p class="text-gray-600 dark:text-gray-500 leading-relaxed">{{ feature.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 4. 宠物知识 (精简带刷新) -->
    <section class="container mx-auto px-4 md:px-6">
      <div class="flex items-center justify-between mb-8 md:mb-12">
        <div class="space-y-2">
          <div class="flex items-center gap-2 text-green-500">
            <Sparkles :size="18" />
            <span class="text-xs font-black uppercase tracking-widest">Education</span>
          </div>
          <h2 class="text-3xl md:text-4xl font-black text-gray-900 dark:text-white italic">宠物知识精选</h2>
        </div>
        <button @click="refreshTips" :disabled="isRefreshing" 
                class="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-white/5 text-gray-600 dark:text-gray-400 rounded-xl border border-gray-200 dark:border-white/5 transition-all disabled:opacity-50">
          <RefreshCw :size="16" :class="{ 'animate-spin': isRefreshing }" />
          <span class="text-xs font-bold">换一批</span>
        </button>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 transition-all duration-500" :class="{ 'opacity-50 scale-95': isRefreshing }">
        <div v-for="tip in displayTips" :key="tip.id" 
             @click="selectedTip = tip"
             class="group cursor-pointer bg-gray-50 dark:bg-white/[0.02] border border-gray-200 dark:border-white/5 rounded-[2rem] p-6 hover:bg-gray-100 dark:hover:bg-white/[0.05] transition-all flex flex-col h-full shadow-sm dark:shadow-none">
          <div class="flex items-center justify-between mb-4">
            <span :class="tip.tagClass" class="px-2.5 py-1 rounded-lg border text-[10px] font-black uppercase tracking-widest">{{ tip.tag }}</span>
            <span class="text-xs">{{ tip.species }}</span>
          </div>
          <h3 class="text-gray-900 dark:text-white font-bold leading-tight mb-3 group-hover:text-orange-500 transition-colors">{{ tip.title }}</h3>
          <p class="text-xs text-gray-600 dark:text-gray-500 leading-relaxed line-clamp-3 mb-6">{{ tip.summary }}</p>
          <div class="mt-auto pt-4 border-t border-gray-200 dark:border-white/5 flex items-center text-[10px] font-black text-orange-500 gap-2">了解详情 <ArrowRight :size="12" /></div>
        </div>
      </div>
    </section>

    <!-- 公告详情弹窗 -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="selectedAnnounce" class="fixed inset-0 z-[1000] flex items-center justify-center p-4 md:p-8 bg-black/90 backdrop-blur-md" @click.self="selectedAnnounce = null">
          <div class="bg-white dark:bg-[#121212] w-full max-w-2xl max-h-[85vh] rounded-[3rem] border border-gray-200 dark:border-white/10 flex flex-col shadow-2xl overflow-hidden">
            <div class="p-8 pb-4 flex justify-between items-start">
              <div class="space-y-3">
                <div class="flex items-center gap-2 text-orange-500">
                  <Megaphone :size="16" />
                  <span class="text-[10px] font-black uppercase tracking-[0.3em]">Platform Official</span>
                </div>
                <h2 class="text-3xl font-black text-gray-900 dark:text-white italic tracking-tight">{{ selectedAnnounce.title }}</h2>
                <p class="text-xs text-gray-400 font-mono">发布日期：{{ selectedAnnounce.date || selectedAnnounce.create_time?.slice(0,10) }}</p>
              </div>
              <button @click="selectedAnnounce = null" class="p-2 bg-gray-100 dark:bg-white/5 text-gray-500 rounded-full"><X :size="20" /></button>
            </div>
            <div class="flex-1 overflow-y-auto p-8 pt-4">
              <div class="text-lg text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
                {{ selectedAnnounce.content }}
              </div>
            </div>
            <div class="p-8 border-t border-gray-100 dark:border-white/5 bg-gray-50 dark:bg-white/[0.02]">
              <button @click="selectedAnnounce = null" class="w-full py-4 bg-orange-500 text-white font-black rounded-2xl shadow-xl">我知道了</button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- 知识详情弹窗 -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="selectedTip" class="fixed inset-0 z-[1000] flex items-center justify-center p-4 md:p-8 bg-black/90 backdrop-blur-md" @click.self="selectedTip = null">
          <div class="bg-white dark:bg-[#121212] w-full max-w-2xl max-h-[85vh] rounded-[3rem] border border-gray-200 dark:border-white/10 flex flex-col shadow-2xl overflow-hidden">
            <div class="p-8 pb-4 flex justify-between items-start">
              <div class="space-y-2">
                <span :class="selectedTip.tagClass" class="px-3 py-1 rounded-lg border text-xs font-black uppercase">{{ selectedTip.tag }}</span>
                <h2 class="text-2xl font-black text-gray-900 dark:text-white italic">{{ selectedTip.title }}</h2>
              </div>
              <button @click="selectedTip = null" class="p-2 bg-gray-100 dark:bg-white/5 text-gray-500 rounded-full"><X :size="20" /></button>
            </div>
            <div class="flex-1 overflow-y-auto p-8 pt-4">
              <div class="prose dark:prose-invert max-w-none text-gray-700 dark:text-gray-400 whitespace-pre-wrap leading-relaxed">{{ selectedTip.content }}</div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- 管理员发布公告弹窗 -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showAnnounceModal" class="fixed inset-0 z-[1000] flex items-center justify-center p-4 bg-black/95 backdrop-blur-xl">
          <div class="bg-white dark:bg-[#121212] w-full max-w-lg rounded-[3rem] border border-gray-200 dark:border-orange-500/20 p-10 space-y-8 shadow-2xl">
            <div class="flex items-center justify-between text-gray-900 dark:text-white font-black italic text-2xl uppercase">
              <h3>发布全站公告</h3>
              <button @click="showAnnounceModal = false" class="text-gray-400"><X /></button>
            </div>
            <div class="space-y-4">
              <input v-model="announceForm.title" placeholder="公告标题" class="w-full bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl px-6 py-4 text-gray-900 dark:text-white outline-none focus:border-orange-500" />
              <textarea v-model="announceForm.content" placeholder="正文内容（支持多段落文字）" rows="8" class="w-full bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl px-6 py-4 text-gray-900 dark:text-white outline-none focus:border-orange-500 resize-none"></textarea>
              <label class="flex items-center gap-3 cursor-pointer group">
                <input type="checkbox" v-model="announceForm.is_hot" :true-value="1" :false-value="0" class="w-5 h-5 rounded-lg accent-orange-500" />
                <span class="text-sm font-bold text-gray-500 group-hover:text-orange-500">标记为 HOT (热门公告)</span>
              </label>
            </div>
            <button @click="handlePublishAnnounce" :disabled="isPublishing" class="w-full py-5 bg-orange-500 hover:bg-orange-600 text-white font-black rounded-2xl shadow-xl flex items-center justify-center gap-3 transition-all">
              <Loader2 v-if="isPublishing" class="animate-spin" />
              <template v-else>立即发布公告</template>
            </button>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
