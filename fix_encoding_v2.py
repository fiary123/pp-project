import sys

content = """<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import {
  Search, Heart, Loader2, X, Wand2, ChevronRight,
  CheckCircle2, BrainCircuit,
  Send, Sparkles, Star, Info
} from 'lucide-vue-next';
import { useAuthStore } from '../store/authStore';
import axios from '../api/index';

const router = useRouter();
const authStore = useAuthStore();

const defaultAdoptionPreferences = {
  hard_preferences: [] as string[],
  soft_preferences: ['住房稳定性', '陪伴时间', '责任意识'],
  allow_novice: true,
  accept_renting: true,
  require_stable_housing: false,
  require_financial_capacity: false,
  require_followup_updates: false,
  prefer_local: false,
  require_family_agreement: false,
  prefer_quiet_household: false,
  prefer_multi_pet_experience: false,
  focus_experience: false,
  focus_companionship: true,
  focus_stability: true,
  risk_tolerance: 'medium'
};

const parseAdoptionPreferences = (raw: unknown) => {
  if (!raw) return { ...defaultAdoptionPreferences };
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
    return { ...defaultAdoptionPreferences, ...(parsed as Record<string, unknown>) };
  } catch {
    return { ...defaultAdoptionPreferences };
  }
};

const riskToleranceLabel = (value?: string) => {
  if (value === 'conservative') return '保守型'
  if (value === 'relaxed') return '宽松型'
  return '中性'
}

const dimensionRiskClass = (level?: string) => {
  if (level === 'Low') return 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300';
  if (level === 'High') return 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300';
  return 'bg-amber-100 text-amber-700 dark:bg-yellow-500/20 dark:text-yellow-300';
};

const housingTypeLabel = (value?: string) => {
  if (value === 'house') return '独立住宅';
  if (value === 'other') return '其他';
  return '公寓';
};

const summarizePetExpectations = (prefs: any) => {
  const chips: string[] = [];
  if (prefs.require_stable_housing) chips.push('稳定居住');
  if (prefs.require_financial_capacity) chips.push('基础经济能力');
  if (prefs.require_followup_updates) chips.push('接受送养回访');
  if (prefs.require_family_agreement) chips.push('家庭同意');
  if (!prefs.allow_novice) chips.push('有经验优先');
  if (!prefs.accept_renting) chips.push('谨慎租房');
  if (prefs.prefer_local) chips.push('本地优先');
  if (prefs.prefer_quiet_household) chips.push('偏好安静家庭');
  if (prefs.prefer_multi_pet_experience) chips.push('多宠经验加分');
  return chips.slice(0, 6);
}

const buildMockAdoptionPreferences = () => ({
  ...defaultAdoptionPreferences,
  require_followup_updates: true,
  soft_preferences: [...defaultAdoptionPreferences.soft_preferences, '接受送养回访']
});

// 1. 状态管理
const pets = ref<any[]>([]);
const isLoading = ref(true);
const searchQuery = ref('');
const activeFilter = ref('全部');
const sourceFilter = ref('全部'); 
const selectedPet = ref<any>(null);

// 2. 图片预览与多图状态
const activeImgIndex = ref(0);
const showImageViewer = ref(false);
const previewImages = computed(() => {
  if (!selectedPet.value) return [];
  const main = selectedPet.value.img;
  let others: string[] = [];
  try {
    const raw = selectedPet.value.image_urls;
    if (raw) {
      others = typeof raw === 'string' ? JSON.parse(raw) : raw;
    }
  } catch (e) { others = []; }
  
  const all = [main, ...others].filter(Boolean);
  const uniqueUrls = [...new Set(all)];
  return uniqueUrls.length > 0 ? uniqueUrls : ['https://images.unsplash.com/photo-1543466835-00a7907e9de1'];
});

// AI 匹配状态
const aiQuery = ref('');
const isAiMatching = ref(false);
const isLoadingFollowup = ref(false);
const recommendedMatches = ref<Record<string, any>>({});
const showMatchResultModal = ref(false); 
const soulmateThreshold = 90;
const recommendationDisplayLimit = 6;

// --- 推荐系统核心 ---
const engineRecommendations = ref<any[]>([]);
const isEngineLoading = ref(false);

const fetchEngineRecommendations = async () => {
  if (!authStore.isLoggedIn || !authStore.user?.id) return;
  isEngineLoading.value = true;
  try {
    const res = await axios.get(`/api/recommendation/pets/${authStore.user.id}`);
    engineRecommendations.value = Array.isArray(res.data) ? res.data : [];
  } catch (err) {
    console.error('获取引擎推荐失败', err);
  } finally {
    isEngineLoading.value = false;
  }
};

const getPetDisplayScore = (pet: any) => {
  const rawScore = Number(recommendedMatches.value[String(pet.id)]?.fit_score);
  if (Number.isFinite(rawScore) && rawScore > 0) return Math.round(rawScore);
  return Math.max(60, Math.round(Number(pet.match) || 0));
};

const sortPetsByDisplayScore = (list: any[]) => {
  return [...list].sort((a, b) => getPetDisplayScore(b) - getPetDisplayScore(a));
};

const fetchPets = async () => {
  isLoading.value = true;
  try {
    const res = await axios.get('/api/pets');
    if (res.data) {
      const realPets = res.data.map((p: any) => ({
        ...p,
        id: Number(p.id),
        img: p.image_url || p.post_image_url || `https://images.unsplash.com/photo-1543466835-00a7907e9de1?sig=${p.id}`,
        desc: p.description || p.post_content || '暂无详细介绍',
        type: p.type || '狗狗',
        owner_type: p.owner_type || 'org',
        adoption_preferences: parseAdoptionPreferences(p.adoption_preferences),
        tags: p.tags ? (typeof p.tags === 'string' ? JSON.parse(p.tags) : p.tags) : ['温顺', '粘人'],
        match: 80 + (p.id % 20)
      }));
      pets.value = realPets;
    }
  } catch (err) { console.error('获取列表失败'); }
  finally { isLoading.value = false; }
};

const filteredPets = computed(() => {
  return pets.value.filter(p => {
    const search = searchQuery.value.toLowerCase();
    const matchesText = p.name.toLowerCase().includes(search) || p.species.toLowerCase().includes(search);
    const matchesType = activeFilter.value === '全部' || p.type === activeFilter.value;
    const matchesSource = sourceFilter.value === '全部'
      || (sourceFilter.value === '机构' && p.owner_type === 'org')
      || (sourceFilter.value === '个人' && p.owner_type === 'personal');
    return matchesText && matchesType && matchesSource;
  }).sort((a, b) => b.match - a.match);
});

watch(selectedPet, (pet) => {
  if (pet) { /* load chat history etc */ }
});

onMounted(() => {
  fetchPets();
  fetchEngineRecommendations();
});
</script>

<template>
  <div class="space-y-8 md:space-y-12 pb-16 md:pb-20 px-3 md:px-4 max-w-[1600px] mx-auto text-gray-900 dark:text-white transition-colors duration-300">
    
    <!-- 1. Hero AI 匹配区 -->
    <div class="relative py-10 md:py-16 text-center space-y-6 md:space-y-8 overflow-hidden rounded-[2.2rem] md:rounded-[4rem] bg-gradient-to-b from-orange-500/10 to-transparent border border-gray-200 dark:border-white/5 shadow-2xl transition-all">
      <div class="relative z-10 space-y-4 px-4 md:px-6 text-gray-900 dark:text-white">
        <h2 class="text-3xl sm:text-4xl md:text-6xl font-black italic tracking-tighter uppercase text-orange-500 leading-tight">寻找您的 <br/>完美伙伴</h2>
        <p class="text-xs md:text-sm text-gray-500 dark:text-gray-400 italic font-black">AI 语义识别 · 多轮深度对话 · 精准全库匹配</p>

        <!-- 输入步 -->
        <div class="max-w-4xl mx-auto mt-6 md:mt-8 transition-all">
          <div class="bg-white/80 dark:bg-[#1a1a1a]/80 backdrop-blur-3xl p-2 rounded-[2rem] md:rounded-[2.5rem] border border-gray-200 dark:border-white/10 flex flex-col md:flex-row items-stretch md:items-center shadow-xl">
            <Wand2 class="hidden md:block ml-6 text-orange-500 shrink-0" :size="28" />
            <input v-model="aiQuery" type="text" placeholder="描述您的理想伙伴（如：想养一只温顺的小猫...）" class="flex-1 bg-transparent py-4 md:py-6 px-5 md:px-6 outline-none text-gray-900 dark:text-white text-base md:text-lg font-bold" />
            <button class="bg-orange-500 text-white px-6 md:px-10 py-4 md:py-5 rounded-[1.4rem] md:rounded-[2rem] font-black flex items-center justify-center gap-2 transition-all active:scale-95 shadow-lg">
              <Wand2 :size="20" /> 开始匹配
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. 列表区 -->
    <div class="flex flex-col md:flex-row items-stretch md:items-center justify-between px-1 md:px-4 gap-4 md:gap-6 text-gray-900 dark:text-white">
      <div class="flex items-center gap-2 bg-gray-100 dark:bg-white/5 p-1.5 rounded-2xl border border-transparent dark:border-white/5 shadow-inner transition-all overflow-x-auto scrollbar-hide">
        <button v-for="cat in ['全部', '猫咪', '狗狗', '异宠']" :key="cat" @click="activeFilter = cat"
          :class="activeFilter === cat ? 'bg-orange-500 text-white shadow-lg' : 'text-gray-500 dark:text-gray-400 hover:text-orange-500'" class="px-5 md:px-8 py-3 rounded-xl font-bold transition-all text-sm whitespace-nowrap">
          {{ cat }}
        </button>
      </div>
      <div class="relative w-full md:w-96 group">
        <Search class="absolute left-5 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-orange-500 transition-colors" :size="18" />
        <input v-model="searchQuery" type="text" placeholder="搜索资源库..." class="w-full bg-gray-100 dark:bg-white/5 border border-transparent dark:border-white/5 rounded-2xl py-4 pl-14 pr-6 outline-none focus:bg-white dark:focus:bg-white/10 font-black transition-all" />
      </div>
    </div>

    <div class="px-2">
      <div v-if="isLoading" class="py-40 flex flex-col items-center"><Loader2 class="animate-spin text-orange-500" :size="48" /><p class="text-gray-500 font-black mt-4 uppercase tracking-widest">检索中...</p></div>
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4 md:gap-6">
        <div v-for="pet in filteredPets" :key="pet.id" @click="selectedPet = pet" 
          class="bg-white dark:bg-[#1a1a1a] rounded-[2rem] md:rounded-[2.5rem] overflow-hidden border border-gray-100 dark:border-white/5 transition-all group cursor-pointer shadow-sm hover:shadow-2xl relative flex flex-col hover:-translate-y-2 duration-500 shadow-orange-500/5">
          <div class="relative aspect-square">
            <img :src="pet.img" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-1000" />
            <h4 class="absolute bottom-4 left-6 font-black text-xl text-gray-900 dark:text-white">{{ pet.name }}</h4>
          </div>
          <div class="p-5 md:p-6 flex-1 flex flex-col justify-between text-gray-900 dark:text-white">
            <div class="space-y-3">
              <p class="text-xs md:text-sm text-gray-600 dark:text-gray-300 leading-6 line-clamp-2 min-h-[3rem]">
                {{ pet.desc || '这是一条待领养宠物信息，欢迎点开查看详情。' }}
              </p>
            </div>
            <div class="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-white/5 mt-4 text-gray-400 dark:text-gray-500 font-bold uppercase tracking-widest">
              <p class="text-sm text-gray-700 dark:text-gray-200 tracking-[0.18em]">{{ pet.species }}</p>
              <ChevronRight class="text-orange-500 group-hover:translate-x-1 transition-transform" :size="16" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.4s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.scrollbar-hide::-webkit-scrollbar { display: none; }
.scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
</style>
"""

with open('pet-frontend/src/views/AdoptView.vue', 'wb') as f:
    f.write(content.encode('utf-8'))
