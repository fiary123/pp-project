<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import {
  Search, Heart, Loader2, X, Wand2, ChevronRight,
  CheckCircle2, BrainCircuit,
  Send, Volume2, Sparkles, Star
} from 'lucide-vue-next';
import { useAuthStore } from '../store/authStore';
import axios from '../api/index';

const authStore = useAuthStore();

// 1. 状态管理
const pets = ref<any[]>([]);
const isLoading = ref(true);
const searchQuery = ref('');
const activeFilter = ref('全部');
const sourceFilter = ref('全部'); 
const selectedPet = ref<any>(null);

// AI 匹配状态
const aiQuery = ref('');
const isAiMatching = ref(false);
const isLoadingFollowup = ref(false);
const recommendedMatches = ref<Record<string, any>>({});
const showMatchResultModal = ref(false); 
const matchedCount = computed(() => Object.keys(recommendedMatches.value).length);

// 获取匹配宠物
const matchedPets = computed(() => {
  const recIds = new Set(Object.keys(recommendedMatches.value));
  return pets.value
    .filter(p => recIds.has(String(p.id)))
    .sort((a, b) => (recommendedMatches.value[String(b.id)]?.fit_score || 0) - (recommendedMatches.value[String(a.id)]?.fit_score || 0));
});

// 多轮对话状态
type MatchStep = 'input' | 'followup';
const matchStep = ref<MatchStep>('input');
const followupQuestions = ref<Array<{ key: string; question: string; options: string[] }>>([]);
const followupAnswers = ref<Record<string, string>>({});

// 领养后回访状态
const showFeedbackModal = ref(false);
const feedbackPet = ref<any>(null);
const feedbackForm = ref({
  overall_satisfaction: 5,
  bond_level: 'close' as 'very_close' | 'close' | 'normal' | 'distant',
  unexpected_challenges: '',
  would_recommend: true,
  free_feedback: ''
});
const isSubmittingFeedback = ref(false);
const feedbackSubmitted = ref(false);

// 领养申请状态
const showAdoptModal = ref(false);
const isAssessing = ref(false);
const isSubmittingApplication = ref(false);
const assessmentResult = ref<any>(null);
const adoptForm = ref({
  applicant_info: '',
  application_reason: '',
  target_species: 'cat' as 'cat' | 'dog',
  monthly_budget: 500,
  daily_companion_hours: 2,
  has_pet_experience: false,
  housing_type: 'apartment' as 'apartment' | 'house' | 'other',
  existing_pets: ''
});

// 宠物语音聊天状态
const petChatMsg = ref('');
const petChatHistory = ref<Array<{role: string; content: string; audio_base64?: string}>>([]);
const isPetChatLoading = ref(false);
const petChatScrollRef = ref<HTMLElement | null>(null);
const petInterviewProfile = ref({
  user_traits: [] as string[],
  strengths: [] as string[],
  risk_flags: [] as string[],
  missing_topics: [] as string[],
  next_probe: '',
  interview_stage: 'early',
  summary: ''
});

const scrollChatToBottom = async () => {
  await nextTick();
  if (petChatScrollRef.value) {
    petChatScrollRef.value.scrollTop = petChatScrollRef.value.scrollHeight;
  }
};

const loadPetChatHistory = async (petName: string) => {
  const uid = authStore.user?.id;
  if (!uid) return;
  try {
    const res = await axios.get('/api/pet-chat/history', { params: { pet_name: petName, user_id: uid } });
    petChatHistory.value = res.data || [];
  } catch {
    petChatHistory.value = [];
  }
  scrollChatToBottom();
};

const loadPetInterviewProfile = async (petName: string) => {
  const uid = authStore.user?.id;
  if (!uid) return;
  try {
    const res = await axios.get('/api/pet-chat/profile', { params: { pet_name: petName, user_id: uid } });
    petInterviewProfile.value = res.data?.profile || { user_traits: [], strengths: [], risk_flags: [], missing_topics: [], next_probe: '', interview_stage: 'early', summary: '' };
  } catch {
    petInterviewProfile.value = { user_traits: [], strengths: [], risk_flags: [], missing_topics: [], next_probe: '', interview_stage: 'early', summary: '' };
  }
};

const handlePetChat = async () => {
  if (!petChatMsg.value.trim() || !selectedPet.value || isPetChatLoading.value) return;
  const msgContent = petChatMsg.value;
  petChatMsg.value = '';
  petChatHistory.value.push({ role: 'user', content: msgContent });
  scrollChatToBottom();
  isPetChatLoading.value = true;
  try {
    const res = await axios.post('/api/pet-chat', {
      pet_name: selectedPet.value.name,
      pet_species: selectedPet.value.species,
      pet_desc: selectedPet.value.desc || '',
      user_msg: msgContent,
      user_id: authStore.user?.id || null
    });
    petChatHistory.value.push({
      role: 'pet',
      content: res.data.text || '',
      audio_base64: res.data.audio_base64 || undefined
    });
    if (res.data?.observer_profile) {
      petInterviewProfile.value = res.data.observer_profile;
    }
    scrollChatToBottom();
  } catch {
    petChatHistory.value.push({ role: 'pet', content: '喵～暂时无法回应，稍后再试吧' });
    scrollChatToBottom();
  } finally {
    isPetChatLoading.value = false;
  }
};

const handleAiMatchStart = async () => {
  if (!aiQuery.value.trim()) return;
  isLoadingFollowup.value = true;
  followupAnswers.value = {};
  try {
    const res = await axios.post('/api/pets/match-followup', { user_query: aiQuery.value });
    if (res.data?.questions?.length) {
      followupQuestions.value = res.data.questions;
      matchStep.value = 'followup';
    } else {
      await handleAiMatch();
    }
  } catch (err) { await handleAiMatch(); }
  finally { isLoadingFollowup.value = false; }
};

const handleAiMatch = async () => {
  if (!aiQuery.value.trim()) return;
  isAiMatching.value = true;
  try {
    const petSummaries = pets.value.map((p: any) => ({
      id: p.id, name: p.name, species: p.species || p.type, description: p.desc || p.description || ''
    }));
    const res = await axios.post('/api/pets/smart-match', {
      user_query: aiQuery.value,
      pet_list: petSummaries,
      followup_answers: Object.keys(followupAnswers.value).length ? followupAnswers.value : null
    }, { timeout: 180000 });
    
    const matchMap: Record<string, any> = {};
    if (res.data?.matches && res.data.matches.length > 0) {
      res.data.matches.forEach((m: any) => { if (m.id != null) { matchMap[String(m.id)] = m; } });
    }
    recommendedMatches.value = matchMap;
    matchStep.value = 'input'; 
    showMatchResultModal.value = true; 
  } catch (err) { console.error('匹配失败', err); }
  finally { isAiMatching.value = false; }
};

const generatePets = () => ([
  {
    id: 9001,
    name: '布丁',
    species: '金毛',
    type: '狗狗',
    owner_type: 'org',
    image_url: 'https://images.unsplash.com/photo-1552053831-71594a27632d?auto=format&fit=crop&w=900&q=80',
    description: '救助站接收后已完成基础体检，性格温顺、亲人，适合有稳定陪伴时间的家庭。',
    tags: ['温顺', '粘人', '爱互动'],
    match: 88,
  },
  {
    id: 9002,
    name: '糯米',
    species: '柯基',
    type: '狗狗',
    owner_type: 'personal',
    image_url: 'https://images.unsplash.com/photo-1583511655826-05700d52f4d9?auto=format&fit=crop&w=900&q=80',
    description: '小短腿很会撒娇，亲人活泼，适合喜欢互动和陪伴感的家庭。',
    tags: ['活泼', '亲人', '会撒娇'],
    match: 85,
  },
  {
    id: 9003,
    name: '奶油',
    species: '布偶猫',
    type: '猫咪',
    owner_type: 'personal',
    image_url: 'https://images.unsplash.com/photo-1513245543132-31f507417b26?auto=format&fit=crop&w=900&q=80',
    description: '慢热但很亲人，适应后喜欢在身边安静陪伴，适合温和家庭。',
    tags: ['安静', '亲人', '陪伴型'],
    match: 84,
  },
  {
    id: 9004,
    name: '花卷',
    species: '英短',
    type: '猫咪',
    owner_type: 'org',
    image_url: 'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=900&q=80',
    description: '圆脸小猫，温和稳定，比较适合第一次养猫的新手家庭。',
    tags: ['温顺', '省心', '新手友好'],
    match: 83,
  },
  {
    id: 9005,
    name: '灰灰',
    species: '龙猫',
    type: '异宠',
    owner_type: 'personal',
    image_url: 'https://images.unsplash.com/photo-1535241749838-299277b6305f?auto=format&fit=crop&w=900&q=80',
    description: '性格安静，喜欢干净环境，对噪音有点敏感，适合细心照顾异宠的人。',
    tags: ['安静', '敏感', '爱干净'],
    match: 81,
  },
  {
    id: 9006,
    name: '阿福',
    species: '狸花猫',
    type: '猫咪',
    owner_type: 'org',
    image_url: 'https://images.unsplash.com/photo-1548247416-ec66f4900b2e?auto=format&fit=crop&w=900&q=80',
    description: '后腿有一点旧伤留下的轻微跛感，但日常生活完全没问题，更适合安静陪伴型家庭。',
    tags: ['懂事', '慢热', '有点小缺陷'],
    match: 82,
  },
]);

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
        tags: p.tags ? (typeof p.tags === 'string' ? JSON.parse(p.tags) : p.tags) : ['温顺', '粘人'],
        match: 80 + (p.id % 20)
      }));
      const mockPets = generatePets().map((p: any) => ({
        ...p,
        img: p.image_url,
        desc: p.description,
      }));
      pets.value = [...realPets, ...mockPets];
    } else {
      pets.value = generatePets().map((p: any) => ({ ...p, img: p.image_url, desc: p.description }));
    }
  } catch (err) {
    console.error('获取列表失败');
    pets.value = generatePets().map((p: any) => ({ ...p, img: p.image_url, desc: p.description }));
  }
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

const openAdoptModal = (pet: any) => {
  adoptingPet.value = pet;
  adoptForm.value.target_species = pet.type === '狗狗' ? 'dog' : 'cat';
  showAdoptModal.value = true;
  showMatchResultModal.value = false;
};

const handleAdoptAssess = async () => {
  if (!adoptForm.value.applicant_info.trim() || adoptForm.value.applicant_info.length < 10) return;
  isAssessing.value = true;
  try {
    const res = await axios.post('/api/adoption/assess', {
      ...adoptForm.value,
      target_pet_name: adoptingPet.value?.name || '未知宠物'
    }, { timeout: 180000 });
    assessmentResult.value = res.data;
  } catch (err: any) { alert('评估服务异常'); }
  finally { isAssessing.value = false; }
};

const submitAdoptionApplication = async () => {
  if (!adoptingPet.value || !assessmentResult.value) return;
  isSubmittingApplication.value = true;
  try {
    await axios.post('/api/user/applications/submit', {
      pet_id: adoptingPet.value.id,
      apply_reason: adoptForm.value.application_reason || adoptForm.value.applicant_info,
      ai_decision: assessmentResult.value.decision,
      ai_readiness_score: assessmentResult.value.readiness_score,
      ai_summary: assessmentResult.value.final_summary
    });
    alert('申请已提交！');
    showAdoptModal.value = false;
    assessmentResult.value = null;
  } catch (err: any) { alert('提交失败'); }
  finally { isSubmittingApplication.value = false; }
};

const startAdopt = (pet: any) => {
  adoptingPet.value = pet;
  openAdoptModal(pet);
};

const adoptingPet = ref<any>(null);
const riskLevelConfig: Record<string, any> = {
  Low: { label: '低风险', bg: 'bg-green-100 dark:bg-green-500/20', text: 'text-green-600 dark:text-green-400' },
  Medium: { label: '中风险', bg: 'bg-yellow-100 dark:bg-yellow-500/20', text: 'text-yellow-600 dark:text-yellow-400' },
  High: { label: '高风险', bg: 'bg-red-100 dark:bg-red-500/20', text: 'text-red-600 dark:text-red-400' }
};

const openFeedbackModal = (pet: any) => {
  feedbackPet.value = pet;
  showFeedbackModal.value = true;
};

const handleSubmitFeedback = async () => {
  if (!feedbackPet.value) return;
  isSubmittingFeedback.value = true;
  try {
    await axios.post('/api/adoption/feedback', {
      user_id: authStore.user?.id, pet_id: feedbackPet.value.id, pet_name: feedbackPet.value.name, ...feedbackForm.value
    });
    feedbackSubmitted.value = true;
  } catch (err) { alert('提交失败'); }
  finally { isSubmittingFeedback.value = false; }
};

watch(selectedPet, (pet) => {
  petChatMsg.value = '';
  petChatHistory.value = [];
  if (pet) { loadPetChatHistory(pet.name); loadPetInterviewProfile(pet.name); }
});

onMounted(fetchPets);
</script>

<template>
  <div class="space-y-8 md:space-y-12 pb-16 md:pb-20 px-3 md:px-4 max-w-[1600px] mx-auto text-gray-900 dark:text-white transition-colors duration-300">
    
    <!-- 1. Hero AI 匹配区 -->
    <div class="relative py-10 md:py-16 text-center space-y-6 md:space-y-8 overflow-hidden rounded-[2.2rem] md:rounded-[4rem] bg-gradient-to-b from-orange-500/10 to-transparent border border-gray-200 dark:border-white/5 shadow-2xl transition-all">
      <div class="relative z-10 space-y-4 px-4 md:px-6 text-gray-900 dark:text-white">
        <h2 class="text-3xl sm:text-4xl md:text-6xl font-black italic tracking-tighter uppercase text-orange-500 leading-tight">寻找您的 <br/>完美伙伴</h2>
        <p class="text-xs md:text-sm text-gray-500 dark:text-gray-400 italic font-black">AI 语义识别 · 多轮深度对话 · 精准全库匹配</p>

        <!-- 输入步 -->
        <div v-if="matchStep === 'input'" class="max-w-4xl mx-auto mt-6 md:mt-8 transition-all">
          <div class="bg-white/80 dark:bg-[#1a1a1a]/80 backdrop-blur-3xl p-2 rounded-[2rem] md:rounded-[2.5rem] border border-gray-200 dark:border-white/10 flex flex-col md:flex-row items-stretch md:items-center shadow-xl">
            <Wand2 class="hidden md:block ml-6 text-orange-500 shrink-0" :size="28" />
            <input v-model="aiQuery" @keyup.enter="handleAiMatchStart" type="text" placeholder="描述您的理想伙伴（如：想养一只温顺的小猫...）" class="flex-1 bg-transparent py-4 md:py-6 px-5 md:px-6 outline-none text-gray-900 dark:text-white text-base md:text-lg font-bold" />
            <button @click="handleAiMatchStart" :disabled="isLoadingFollowup || !aiQuery.trim()" class="bg-orange-500 disabled:bg-orange-500/40 text-white px-6 md:px-10 py-4 md:py-5 rounded-[1.4rem] md:rounded-[2rem] font-black flex items-center justify-center gap-2 transition-all active:scale-95 shadow-lg">
              <Loader2 v-if="isLoadingFollowup" class="animate-spin" :size="20" />
              <Wand2 v-else :size="20" />
              {{ isLoadingFollowup ? '智能理解中...' : '开始匹配' }}
            </button>
          </div>
        </div>

        <!-- 追问步 -->
        <div v-else-if="matchStep === 'followup'" class="max-w-2xl mx-auto mt-6 md:mt-8 space-y-4 text-left">
          <div class="flex items-center gap-3 mb-4">
            <BrainCircuit class="text-orange-500" :size="22" />
            <p class="font-black text-sm text-gray-900 dark:text-white">请回答几个问题以锁定最佳伴侣</p>
            <button @click="handleAiMatch" class="ml-auto text-xs text-gray-500 hover:text-orange-500 font-bold transition-all">跳过 →</button>
          </div>
          <div v-for="(q, idx) in followupQuestions" :key="q.key" class="bg-white dark:bg-[#1a1a1a]/80 border border-gray-200 dark:border-white/10 rounded-[1.6rem] md:rounded-[2rem] p-4 md:p-6 space-y-3 shadow-md">
            <p class="text-sm font-black text-gray-800 dark:text-gray-100">{{ idx + 1 }}. {{ q.question }}</p>
            <div class="flex flex-wrap gap-2">
              <button v-for="opt in q.options" :key="opt" @click="followupAnswers[q.key] = opt"
                :class="followupAnswers[q.key] === opt ? 'bg-orange-500 text-white shadow-lg' : 'bg-gray-100 dark:bg-white/5 text-gray-600 dark:text-gray-400 border-transparent hover:bg-orange-500/10'"
                class="px-4 py-2 rounded-xl text-xs font-bold transition-all border border-transparent">
                {{ opt }}
              </button>
            </div>
          </div>
          <button @click="handleAiMatch" :disabled="isAiMatching" class="w-full bg-orange-500 disabled:bg-orange-500/40 text-white py-4 md:py-5 rounded-2xl font-black flex items-center justify-center gap-2 shadow-xl active:scale-95 transition-all">
            <Loader2 v-if="isAiMatching" class="animate-spin" :size="20" />
            <BrainCircuit v-else :size="20" />
            {{ isAiMatching ? '正在全库检索...' : '生成精准匹配结果' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 2. 全量匹配结果弹窗 -->
    <Teleport to="body">
      <Transition name="slide-up">
        <div v-if="showMatchResultModal" class="fixed inset-0 z-[1000] bg-white/95 dark:bg-black/95 backdrop-blur-2xl flex items-start md:items-center justify-center p-3 md:p-10 overflow-y-auto">
          <div class="relative bg-gray-50 dark:bg-[#111] border border-gray-200 dark:border-white/10 rounded-[2rem] md:rounded-[4rem] w-full max-w-7xl max-h-[calc(100vh-1.5rem)] md:max-h-full flex flex-col shadow-2xl overflow-hidden transition-all text-gray-900 dark:text-white my-auto">
            <div class="p-5 md:p-10 md:pb-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-gray-200 dark:border-white/5">
              <div class="flex items-center gap-4 md:gap-6 min-w-0">
                <div class="hidden sm:flex p-4 bg-orange-500 rounded-3xl text-white shadow-xl shadow-orange-500/20"><Sparkles :size="32" /></div>
                <div class="min-w-0">
                  <h3 class="text-xl sm:text-2xl md:text-4xl font-black italic uppercase leading-tight">为您发现 {{ matchedCount }} 位灵魂伴侣</h3>
                  <p class="text-xs md:text-sm text-gray-500 dark:text-gray-400 mt-1 font-black">AI 已通过多智能体博弈完成 100% 契合度比对</p>
                </div>
              </div>
              <button @click="showMatchResultModal = false" class="self-end sm:self-auto w-12 h-12 md:w-14 md:h-14 rounded-full bg-gray-200 dark:bg-white/5 flex items-center justify-center text-gray-500 dark:text-gray-400 hover:text-orange-500 transition-all active:scale-90 shadow-sm"><X :size="24" class="md:hidden"/><X :size="28" class="hidden md:block"/></button>
            </div>

            <div class="flex-1 overflow-y-auto p-4 md:p-10 scrollbar-hide">
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-8">
                <div v-for="pet in matchedPets" :key="pet.id" 
                  class="group bg-white dark:bg-white/5 border border-gray-200 dark:border-white/5 rounded-[3rem] overflow-hidden flex flex-col shadow-sm hover:shadow-2xl transition-all duration-500">
                  <div class="relative aspect-video">
                    <img :src="pet.img" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
                    <div class="absolute inset-0 bg-gradient-to-t from-gray-50 dark:from-[#111] via-transparent to-transparent opacity-80"></div>
                    <div class="absolute top-4 right-4 bg-orange-500 text-white px-4 py-2 rounded-2xl font-black text-sm flex items-center gap-1 shadow-lg">
                      <Star :size="14" fill="currentColor" /> {{ recommendedMatches[String(pet.id)]?.fit_score }}% 契合
                    </div>
                  </div>
                  <div class="p-5 md:p-8 space-y-4 md:space-y-5 flex-1 flex flex-col">
                    <div class="flex justify-between items-start">
                      <div class="min-w-0">
                        <h4 class="text-xl md:text-2xl font-black truncate">{{ pet.name }}</h4>
                        <p class="text-[10px] text-gray-500 dark:text-gray-400 font-black uppercase tracking-widest mt-1">{{ pet.species }} · {{ pet.type }}</p>
                      </div>
                      <button @click="selectedPet = pet" class="text-orange-500 font-black text-xs hover:underline underline-offset-4 shrink-0">查看档案 →</button>
                    </div>
                    <div class="bg-orange-50 dark:bg-black/30 border border-orange-100 dark:border-white/5 rounded-3xl p-5 space-y-4">
                      <p class="text-sm text-orange-700 dark:text-orange-300 font-bold italic leading-relaxed">"{{ recommendedMatches[String(pet.id)]?.reason }}"</p>
                      <div class="space-y-2">
                        <div v-for="adv in recommendedMatches[String(pet.id)]?.fit_advantages?.slice(0,3)" :key="adv" class="text-xs text-green-700 dark:text-green-400 font-black flex items-start gap-2">
                          <CheckCircle2 :size="14" class="shrink-0 mt-0.5" /> {{ adv }}
                        </div>
                      </div>
                    </div>
                    <button @click="startAdopt(pet)" class="mt-auto w-full bg-gray-900 dark:bg-white text-white dark:text-black py-4 md:py-5 rounded-2xl font-black text-sm hover:bg-orange-500 hover:text-white transition-all shadow-xl active:scale-95">立即发起领养</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 3. 常规列表区 (适配多主题) -->
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

    <!-- 网格列表 -->
    <div class="px-2">
      <div v-if="isLoading" class="py-40 flex flex-col items-center"><Loader2 class="animate-spin text-orange-500" :size="48" /><p class="text-gray-500 font-black mt-4 uppercase tracking-widest">检索中...</p></div>
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4 md:gap-6">
        <div v-for="pet in filteredPets" :key="pet.id" @click="selectedPet = pet" 
          class="bg-white dark:bg-[#1a1a1a] rounded-[2rem] md:rounded-[2.5rem] overflow-hidden border border-gray-100 dark:border-white/5 transition-all group cursor-pointer shadow-sm hover:shadow-2xl relative flex flex-col hover:-translate-y-2 duration-500 shadow-orange-500/5">
          <div class="relative aspect-square">
            <img :src="pet.img" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-1000" />
            <div class="absolute inset-0 bg-gradient-to-t from-white/90 dark:from-[#1a1a1a] via-transparent to-transparent opacity-60"></div>
            <div class="absolute top-4 left-4 flex gap-2">
              <span v-if="pet.owner_type === 'org'" class="px-2 py-1 bg-blue-500 text-white text-[8px] font-black rounded uppercase shadow-lg">机构</span>
              <span v-else class="px-2 py-1 bg-green-500 text-white text-[8px] font-black rounded uppercase shadow-lg">个人</span>
            </div>
            <h4 class="absolute bottom-4 left-6 font-black text-xl text-gray-900 dark:text-white">{{ pet.name }}</h4>
          </div>
          <div class="p-5 md:p-6 flex-1 flex flex-col justify-between text-gray-900 dark:text-white">
            <div class="space-y-3">
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="t in pet.tags?.slice(0,2)"
                  :key="t"
                  class="text-xs md:text-sm bg-orange-50 dark:bg-orange-500/10 px-3 md:px-3.5 py-1.5 md:py-2 rounded-xl text-orange-700 dark:text-orange-100 font-black border border-orange-100 dark:border-orange-500/20"
                >
                  #{{ t }}
                </span>
              </div>
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

    <!-- 4. 详情与语音聊天 (全主题字体适配) -->
    <Transition name="fade">
      <div v-if="selectedPet" class="fixed inset-0 z-[1100] flex items-center justify-center p-3 md:p-6 backdrop-blur-xl">
        <div class="absolute inset-0 bg-black/60" @click="selectedPet = null"></div>
        <div class="relative bg-white dark:bg-[#111] border border-gray-200 dark:border-white/10 rounded-[2rem] md:rounded-[4rem] max-w-lg w-full shadow-2xl max-h-[94vh] flex flex-col overflow-hidden text-gray-900 dark:text-white transition-all">
          <div class="flex items-center gap-4 px-5 md:px-10 py-5 md:py-8 border-b border-gray-100 dark:border-white/5 flex-shrink-0">
            <img :src="selectedPet.img" class="w-16 h-16 rounded-3xl object-cover shadow-xl border border-black/5 dark:border-white/5" />
            <div class="flex-1">
              <span class="bg-orange-500/10 text-orange-500 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest">{{ selectedPet.type }}</span>
              <h3 class="text-2xl font-black mt-1">{{ selectedPet.name }}</h3>
            </div>
            <button @click="selectedPet = null" class="w-12 h-12 bg-gray-100 dark:bg-white/5 rounded-full flex items-center justify-center text-gray-400 hover:text-orange-500 transition-all active:scale-90 shadow-sm"><X :size="24" /></button>
          </div>
          <div class="overflow-y-auto flex-1 p-5 md:p-10 space-y-6 md:space-y-8 scrollbar-hide text-gray-900 dark:text-white">
            <p class="text-gray-600 dark:text-gray-400 text-sm leading-relaxed font-black">{{ selectedPet.desc }}</p>
            
            <div class="bg-orange-50 dark:bg-white/5 border border-orange-100 dark:border-white/10 rounded-[2rem] md:rounded-[2.5rem] overflow-hidden shadow-inner text-gray-900 dark:text-white">
              <div class="flex items-center gap-2 px-6 py-4 border-b border-orange-100 dark:border-white/5 bg-orange-100/50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400">
                <Volume2 :size="16" />
                <span class="text-xs font-black uppercase tracking-widest italic">与 {{ selectedPet.name }} 语音交流中...</span>
              </div>
              <div ref="petChatScrollRef" class="h-52 md:h-64 overflow-y-auto px-4 md:px-6 py-4 md:py-5 space-y-4 md:space-y-5 scrollbar-hide text-gray-900 dark:text-white">
                <div v-for="(msg, i) in petChatHistory" :key="i" :class="msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'" class="flex items-end gap-3 transition-all">
                  <div class="w-9 h-9 rounded-full overflow-hidden border border-gray-200 dark:border-white/10 shadow-sm flex-shrink-0">
                    <img v-if="msg.role === 'pet'" :src="selectedPet.img" class="w-full h-full object-cover" />
                    <img v-else :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${authStore.user?.username}`" />
                  </div>
                  <div :class="msg.role === 'user' ? 'bg-orange-500 text-white rounded-tr-none shadow-orange-500/20' : 'bg-gray-100 dark:bg-white/10 text-gray-800 dark:text-gray-200 border border-gray-100 dark:border-white/5 rounded-tl-none font-black'" class="px-4 py-3 rounded-3xl text-sm max-w-[85%] md:max-w-[80%] leading-relaxed shadow-sm break-words">{{ msg.content }}</div>
                </div>
              </div>
              <div class="flex gap-2 px-4 md:px-6 py-4 md:py-5 border-t border-gray-100 dark:border-white/5 bg-white dark:bg-transparent">
                <input v-model="petChatMsg" @keyup.enter="handlePetChat" type="text" placeholder="输入文字，与它建立连接..." class="flex-1 min-w-0 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl px-4 md:px-5 py-3 text-sm outline-none focus:border-orange-500 transition-colors text-gray-900 dark:text-white font-black" />
                <button @click="handlePetChat" :disabled="isPetChatLoading || !petChatMsg.trim()" class="px-4 md:px-5 py-3 bg-orange-500 text-white rounded-2xl hover:bg-orange-600 shadow-lg active:scale-95 transition-all flex items-center justify-center shadow-orange-500/20"><Send :size="18" /></button>
              </div>
            </div>

            <div class="flex flex-col sm:flex-row gap-3 md:gap-4 pt-2">
              <button @click="startAdopt(selectedPet)" class="flex-1 bg-gray-900 dark:bg-white text-white dark:text-black py-4 md:py-5 rounded-[1.2rem] md:rounded-[1.5rem] font-black text-sm hover:bg-orange-500 hover:text-white transition-all shadow-2xl flex items-center justify-center gap-2 active:scale-95"><Sparkles :size="18" />立即申请领养</button>
              <button @click="openFeedbackModal(selectedPet)" class="px-6 py-4 md:py-5 bg-white dark:bg-white/5 text-gray-400 dark:text-white rounded-[1.2rem] md:rounded-[1.5rem] border border-gray-200 dark:border-white/10 hover:text-green-500 transition-all shadow-md active:scale-90 font-black flex items-center justify-center"><Heart :size="22" /></button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 5. 领养申请弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showAdoptModal" class="fixed inset-0 z-[1200] flex items-start md:items-center justify-center bg-white/95 dark:bg-black/95 backdrop-blur-md px-3 md:px-4 py-4 md:py-8 overflow-y-auto transition-all">
          <div class="bg-gray-50 dark:bg-[#111] border border-gray-200 dark:border-white/10 rounded-[2rem] md:rounded-[4rem] w-full max-w-2xl my-auto text-gray-900 dark:text-white shadow-2xl overflow-hidden transition-all max-h-[calc(100vh-2rem)] overflow-y-auto">
            <div class="p-5 md:p-12 md:pb-0 flex justify-between items-start gap-4 text-gray-900 dark:text-white">
              <div class="space-y-2">
                <div class="flex items-center gap-3"><BrainCircuit class="text-orange-500 md:hidden" :size="28" /><BrainCircuit class="hidden md:block text-orange-500" :size="32" /><span class="text-[10px] font-black text-orange-500 uppercase tracking-widest">AI 智能专家评审</span></div>
                <h3 class="text-2xl md:text-4xl font-black italic uppercase">申请领养</h3>
                <p class="text-xs md:text-sm text-gray-500 dark:text-gray-400 font-black">正在为 <span class="text-orange-500">{{ adoptingPet?.name }}</span> 建立匹配报告</p>
              </div>
              <button @click="showAdoptModal = false" class="text-gray-400 hover:text-orange-500 transition-all active:scale-90"><X :size="28"/></button>
            </div>
            <div v-if="!assessmentResult" class="p-5 md:p-12 space-y-5 md:space-y-8">
              <div class="space-y-2">
                <label class="text-[10px] text-gray-500 dark:text-gray-400 font-black uppercase tracking-widest">详细个人画像描述 (不低于10字)</label>
                <textarea v-model="adoptForm.applicant_info" rows="4" placeholder="请详细描述您的居住环境（面积/封窗）、职业稳定性、家庭成员态度等..." class="w-full bg-white dark:bg-[#1a1a1a] border border-gray-200 dark:border-white/10 rounded-[1.5rem] md:rounded-[2rem] px-5 md:px-8 py-4 md:py-6 outline-none focus:border-orange-500 transition-all shadow-inner text-gray-900 dark:text-white font-black" />
              </div>
              <button @click="handleAdoptAssess" :disabled="isAssessing || adoptForm.applicant_info.length < 10" class="w-full bg-orange-500 disabled:bg-orange-500/40 text-white py-4 md:py-6 rounded-[1.5rem] md:rounded-[2rem] font-black text-base md:text-xl flex justify-center items-center gap-4 transition-all active:scale-95 shadow-2xl">
                <Loader2 v-if="isAssessing" class="animate-spin" :size="24" />
                <BrainCircuit v-else :size="24" />
                {{ isAssessing ? '多智能体专家联合审计...' : '开始 AI 多维资质评估' }}
              </button>
            </div>
            <div v-else class="p-5 md:p-12 space-y-5 md:space-y-8">
               <div class="bg-white dark:bg-white/5 rounded-[2rem] md:rounded-[3rem] p-6 md:p-10 border border-gray-200 dark:border-white/5 text-center space-y-4 shadow-xl">
                 <div class="text-5xl md:text-7xl font-black text-orange-500">{{ assessmentResult.readiness_score }}</div>
                 <p class="text-[10px] text-gray-500 dark:text-gray-400 font-black uppercase tracking-widest">领养准备度总分</p>
                 <div :class="[riskLevelConfig[assessmentResult.risk_level]?.bg, riskLevelConfig[assessmentResult.risk_level]?.text]" class="inline-block px-6 py-2 rounded-full text-xs font-black">{{ riskLevelConfig[assessmentResult.risk_level]?.label }}</div>
               </div>
               <p v-if="assessmentResult.final_summary" class="text-sm leading-7 text-gray-600 dark:text-gray-300 bg-white/70 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-[1.4rem] md:rounded-[2rem] p-4 md:p-6">
                 {{ assessmentResult.final_summary }}
               </p>
               <button @click="submitAdoptionApplication" :disabled="isSubmittingApplication" class="w-full bg-orange-500 text-white py-4 md:py-6 rounded-[1.5rem] md:rounded-[2rem] font-black text-base md:text-xl transition-all active:scale-95 shadow-2xl shadow-orange-500/20">确认并正式提交申请</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 6. 领养回访弹窗 (多主题适配) -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showFeedbackModal" class="fixed inset-0 z-[1300] flex items-start md:items-center justify-center bg-white/95 dark:bg-black/95 backdrop-blur-md px-3 md:px-4 py-4 md:py-8 overflow-y-auto">
          <div class="bg-gray-50 dark:bg-[#111] border border-gray-200 dark:border-white/10 rounded-[2rem] md:rounded-[4rem] w-full max-w-lg my-auto text-gray-900 dark:text-white shadow-2xl p-5 md:p-12 space-y-5 md:space-y-8 transition-all max-h-[calc(100vh-2rem)] overflow-y-auto">
            <h3 class="text-2xl md:text-3xl font-black italic uppercase">领养回访反馈</h3>
            <p class="text-xs md:text-sm text-gray-500 dark:text-gray-400 font-black leading-relaxed">您的真实反馈将存入 AI 的长期经验库，帮助优化未来的领养匹配策略。</p>
            <div class="space-y-4">
              <label class="text-[10px] text-gray-500 dark:text-gray-400 font-black uppercase tracking-widest">您的整体满意度 (1-5)</label>
              <div class="flex gap-3 md:gap-4 text-gray-900 dark:text-white">
                <button v-for="n in 5" :key="n" @click="feedbackForm.overall_satisfaction = n" :class="feedbackForm.overall_satisfaction >= n ? 'text-orange-500' : 'text-gray-300 dark:text-gray-600'" class="text-3xl md:text-4xl transition-all active:scale-90">★</button>
              </div>
            </div>
            <textarea v-model="feedbackForm.unexpected_challenges" placeholder="分享您领养后遇到的挑战（如有），这将帮助 AI 学习..." class="w-full bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-[1.6rem] md:rounded-[2rem] p-4 md:p-6 outline-none focus:border-orange-500 min-h-[140px] text-gray-900 dark:text-white font-black" />
            <button @click="handleSubmitFeedback" :disabled="isSubmittingFeedback" class="w-full bg-orange-500 text-white py-4 md:py-5 rounded-[1.5rem] font-black text-base md:text-lg transition-all active:scale-95 shadow-xl shadow-orange-500/20">提交并更新 AI 记忆库</button>
            <button @click="showFeedbackModal = false" class="w-full text-gray-400 dark:text-gray-500 font-black text-xs hover:text-orange-500 transition-all uppercase tracking-widest">暂不反馈，返回</button>
          </div>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.4s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-up-enter-active, .slide-up-leave-active { transition: all 0.7s cubic-bezier(0.16, 1, 0.3, 1); }
.slide-up-enter-from { opacity: 0; transform: translateY(150px) scale(0.95); }
.slide-up-leave-to { opacity: 0; transform: translateY(150px) scale(0.95); }

.scrollbar-hide::-webkit-scrollbar { display: none; }
.scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
</style>
