<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import {
  Search, Heart, MapPin, Loader2, X, Wand2, ChevronRight, Edit3, Trash2, Upload,
  CheckCircle2, AlertTriangle, XCircle, ClipboardList, BrainCircuit, ShieldCheck,
  Send, Volume2
} from 'lucide-vue-next';
import { useAuthStore } from '../store/authStore';
import axios from '../api/index';

const authStore = useAuthStore();

// 1. 状态管理
const pets = ref<any[]>([]);
const isLoading = ref(true);
const searchQuery = ref('');
const activeFilter = ref('全部');
const selectedPet = ref<any>(null);

// AI 匹配状态 - 创新点1：多轮对话式需求显化
const aiQuery = ref('');
const isAiMatching = ref(false);
const isLoadingFollowup = ref(false);
const recommendedMatches = ref<Record<number, any>>({});

// 多轮对话状态
type MatchStep = 'input' | 'followup' | 'result';
const matchStep = ref<MatchStep>('input');
const followupQuestions = ref<Array<{ key: string; question: string; options: string[] }>>([]);
const followupAnswers = ref<Record<string, string>>({});

// 领养后回访状态 - 创新点3：数据飞轮闭环
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
const petChatHistory = ref<Array<{role: string; content: string; create_time?: string}>>([]);
const isPetChatLoading = ref(false);
const petChatScrollRef = ref<HTMLElement | null>(null);

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

const playAudioBase64 = (base64: string) => {
  try {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: 'audio/mpeg' });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play();
    audio.onended = () => URL.revokeObjectURL(url);
  } catch (e) {
    console.warn('语音播放失败', e);
  }
};

const handlePetChat = async () => {
  if (!petChatMsg.value.trim() || !selectedPet.value || isPetChatLoading.value) return;
  const msgContent = petChatMsg.value;
  petChatMsg.value = '';
  // 先在本地追加用户消息
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
    const replyText = res.data.text || '';
    petChatHistory.value.push({ role: 'pet', content: replyText });
    scrollChatToBottom();
    if (res.data.audio_base64) {
      playAudioBase64(res.data.audio_base64);
    }
  } catch {
    petChatHistory.value.push({ role: 'pet', content: '喵～暂时无法回应，稍后再试吧' });
    scrollChatToBottom();
  } finally {
    isPetChatLoading.value = false;
  }
};

const openAdoptModal = (pet: any) => {
  adoptForm.value.target_species = pet.type === '狗狗' ? 'dog' : 'cat';
  assessmentResult.value = null;
  showAdoptModal.value = true;
  selectedPet.value = null;
};

const handleAdoptAssess = async () => {
  if (!adoptForm.value.applicant_info.trim() || adoptForm.value.applicant_info.length < 10) return;
  isAssessing.value = true;
  assessmentResult.value = null;
  try {
    const token = localStorage.getItem('token');
    const res = await axios.post('/api/adoption/assess', {
      ...adoptForm.value,
      target_pet_name: adoptingPet.value?.name || '未知宠物'
    }, { headers: { Authorization: `Bearer ${token}` } });
    assessmentResult.value = res.data;
  } catch (err: any) {
    assessmentResult.value = {
      readiness_score: 0,
      risk_level: 'High',
      decision: 'review_required',
      final_summary: '评估服务暂时不可用，请稍后再试或联系管理员。',
      risk_factors: [],
      recommendations: [],
      baseline_report: '',
      profile_report: '',
      cohabitation_report: ''
    };
  } finally {
    isAssessing.value = false;
  }
};

const adoptingPet = ref<any>(null);
const startAdopt = (pet: any) => {
  adoptingPet.value = pet;
  openAdoptModal(pet);
};

const decisionConfig: Record<string, { label: string; color: string; icon: any }> = {
  pass: { label: '建议通过', color: 'text-green-400', icon: CheckCircle2 },
  conditional_pass: { label: '条件通过', color: 'text-yellow-400', icon: AlertTriangle },
  review_required: { label: '需人工复核', color: 'text-blue-400', icon: ShieldCheck },
  reject: { label: '建议驳回', color: 'text-red-400', icon: XCircle }
};

const riskLevelConfig: Record<string, { label: string; bg: string; text: string }> = {
  Low: { label: '低风险', bg: 'bg-green-500/20', text: 'text-green-400' },
  Medium: { label: '中风险', bg: 'bg-yellow-500/20', text: 'text-yellow-400' },
  High: { label: '高风险', bg: 'bg-red-500/20', text: 'text-red-400' }
};

const severityColor: Record<string, string> = {
  low: 'text-green-400',
  medium: 'text-yellow-400',
  high: 'text-red-400'
};

// 管理员编辑状态
const showEditModal = ref(false);
const isUpdatingPet = ref(false);
const isUploading = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);
const editPetForm = ref({ id: 0, name: '', species: '', img: '', desc: '' });

// 处理本地上传
const triggerUpload = () => fileInput.value?.click();
const handleFileUpload = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  isUploading.value = true;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const res = await axios.post('/api/upload', formData);
    editPetForm.value.img = res.data.url;
  } catch (err) { alert('图片上传失败'); }
  finally { isUploading.value = false; }
};

// 2. 模拟数据生成
const generatePets = () => {
  const dogNames = ['旺财', '大黄', '糯米', '团团', '坦克', '奥利奥', '咖啡', '豆点', '馒头', '辛巴'];
  const catNames = ['咪咪', '花卷', '奶酪', '年糕', '露露', '皮皮', '糖糖', '布丁'];
  const exoticNames = ['吱吱', '灰灰', '翠儿', '刺刺', '呆呆', '悠悠', '萌萌', '泡泡'];
  
  const dogSpecies = [
    { name: '柯基', img: 'https://images.unsplash.com/photo-1583511655826-05700d52f4d9' },
    { name: '金毛', img: 'https://images.unsplash.com/photo-1552053831-71594a27632d' },
    { name: '柴犬', img: 'https://images.unsplash.com/photo-1583337130417-3346a1be7dee' }
  ];

  const catSpecies = [
    { name: '布偶猫', img: 'https://images.unsplash.com/photo-1533743983669-94fa5c4338ec' },
    { name: '英短', img: 'https://images.unsplash.com/photo-1513245543132-31f507417b26' }
  ];

  const exoticSpecies = [
    { name: '龙猫', img: 'https://images.unsplash.com/photo-1559190394-df5a28aab5c5' }
  ];

  const data = [];
  for (let i = 0; i < 60; i++) {
    const typeIdx = i % 3;
    const itemIdx = Math.floor(i/3);
    let type: string, name: string, speciesInfo: { name: string; img: string };
    if (typeIdx === 0) { type='狗狗'; name=dogNames[itemIdx%dogNames.length]!; speciesInfo=dogSpecies[itemIdx%dogSpecies.length]!; }
    else if (typeIdx === 1) { type='猫咪'; name=catNames[itemIdx%catNames.length]!; speciesInfo=catSpecies[itemIdx%catSpecies.length]!; }
    else { type='异宠'; name=exoticNames[itemIdx%exoticNames.length]!; speciesInfo=exoticSpecies[itemIdx%exoticSpecies.length]!; }

    data.push({
      id: i + 1000,
      name,
      type,
      species: speciesInfo.name,
      match: 75 + Math.floor(Math.random() * 20),
      img: `${speciesInfo.img}?sig=${i}&auto=format&fit=crop&w=800&q=80`,
      tags: i % 2 === 0 ? ['温顺', '粘人'] : ['活泼', '聪明'],
      desc: `这是一只非常可爱的${speciesInfo.name}，期待新主人。`,
      distance: (Math.random() * 10).toFixed(1)
    });
  }
  return data;
};

// 3. 数据加载
const fetchPets = async () => {
  isLoading.value = true;
  try {
    const res = await axios.get('/api/pets');
    if (res.data && res.data.length >= 10) {
      pets.value = res.data.map((p: any) => ({
        ...p,
        img: p.image_url || `https://images.unsplash.com/photo-1543466835-00a7907e9de1?sig=${p.id}&auto=format&fit=crop&w=800&q=80`,
        desc: p.description || '暂无详细介绍',
        type: p.type || (p.id % 2 === 0 ? '狗狗' : '猫咪'),
        distance: (Math.random() * 5).toFixed(1),
        tags: p.tags ? p.tags.split(',') : ['温顺', '粘人'],
        match: 80 + (p.id % 20)
      }));
    } else {
      pets.value = generatePets();
    }
  } catch (err) {
    pets.value = generatePets();
  } finally {
    isLoading.value = false;
  }
};

const isAdmin = computed(() => authStore.user?.role === 'org_admin');

const startEditPet = (pet: any) => {
  editPetForm.value = { id: pet.id, name: pet.name, species: pet.species, img: pet.img, desc: pet.desc };
  showEditModal.value = true;
};

const handleUpdatePet = async () => {
  isUpdatingPet.value = true;
  try {
    if (editPetForm.value.id < 1000) {
      await axios.put(`/api/pets/${editPetForm.value.id}`, {
        name: editPetForm.value.name,
        species: editPetForm.value.species,
        image_url: editPetForm.value.img,
        description: editPetForm.value.desc
      });
    }
    const idx = pets.value.findIndex(p => p.id === editPetForm.value.id);
    if (idx !== -1) {
      pets.value[idx] = { ...pets.value[idx], ...editPetForm.value };
    }
  } catch (err) {}
  finally {
    showEditModal.value = false;
    isUpdatingPet.value = false;
  }
};

const handleDeletePet = async (petId: number) => {
  if (!confirm('确定要从领养列表中移除这只宠物吗？')) return;
  try {
    if (petId < 1000) await axios.delete(`/api/pets/${petId}`);
    pets.value = pets.value.filter(p => p.id !== petId);
  } catch (err) {}
};

// 创新点1：第一步 - 获取追问问题
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
  } catch (err) {
    await handleAiMatch();
  } finally {
    isLoadingFollowup.value = false;
  }
};

// 创新点1+3：第二步 - 携带追问答案进行 LLM 语义匹配
const handleAiMatch = async () => {
  if (!aiQuery.value.trim()) return;
  isAiMatching.value = true;
  matchStep.value = 'result';
  try {
    const res = await axios.post('/api/pets/smart-match', {
      user_query: aiQuery.value,
      pet_list: pets.value,
      followup_answers: Object.keys(followupAnswers.value).length ? followupAnswers.value : null
    });
    const matchMap: Record<number, any> = {};
    if (res.data?.matches) {
      res.data.matches.forEach((m: any) => {
        matchMap[m.id] = {
          fit_score: m.fit_score || 80,
          reason: m.reason || '综合推荐',
          fit_advantages: m.fit_advantages || [],
          potential_challenges: m.potential_challenges || [],
          mitigation: m.mitigation || ''
        };
      });
    }
    recommendedMatches.value = matchMap;
    activeFilter.value = '全部';
    searchQuery.value = '';
  } catch (err) {}
  finally { isAiMatching.value = false; }
};

const resetAiMatch = () => {
  matchStep.value = 'input';
  recommendedMatches.value = {};
  followupAnswers.value = {};
  followupQuestions.value = [];
};

// 创新点3：提交领养后回访
const openFeedbackModal = (pet: any) => {
  feedbackPet.value = pet;
  feedbackSubmitted.value = false;
  feedbackForm.value = { overall_satisfaction: 5, bond_level: 'close', unexpected_challenges: '', would_recommend: true, free_feedback: '' };
  showFeedbackModal.value = true;
};

const handleSubmitFeedback = async () => {
  if (!feedbackPet.value) return;
  isSubmittingFeedback.value = true;
  try {
    await axios.post('/api/adoption/feedback', {
      user_id: authStore.user?.id,
      pet_id: feedbackPet.value.id,
      pet_name: feedbackPet.value.name,
      ...feedbackForm.value
    });
    feedbackSubmitted.value = true;
  } catch (err) {
    alert('反馈提交失败，请稍后再试');
  } finally {
    isSubmittingFeedback.value = false;
  }
};

const filteredPets = computed(() => {
  const recIds = Object.keys(recommendedMatches.value).map(Number);
  let result = pets.value.filter(p => {
    const search = searchQuery.value.toLowerCase();
    const nameMatch = p.name.toLowerCase().includes(search);
    const speciesMatch = p.species.toLowerCase().includes(search);
    const matchesType = activeFilter.value === '全部' || p.type === activeFilter.value;
    return (nameMatch || speciesMatch) && matchesType;
  });
  if (recIds.length > 0) {
    return result.sort((a, b) => {
      const aScore = recommendedMatches.value[a.id]?.fit_score || 0;
      const bScore = recommendedMatches.value[b.id]?.fit_score || 0;
      return bScore - aScore;
    });
  }
  return result.sort((a, b) => b.match - a.match);
});

// 切换宠物时重置聊天状态并加载历史
watch(selectedPet, (pet) => {
  petChatMsg.value = '';
  petChatHistory.value = [];
  if (pet) loadPetChatHistory(pet.name);
});

onMounted(fetchPets);
</script>

<template>
  <div class="space-y-12 pb-20 px-4 max-w-[1600px] mx-auto">
    <!-- Hero 区：多轮对话式 AI 匹配 -->
    <div class="relative py-16 text-center space-y-8 overflow-hidden rounded-[4rem] bg-gradient-to-b from-orange-500/10 to-transparent border border-white/5 shadow-2xl">
      <div class="relative z-10 space-y-4">
        <h2 class="text-6xl font-black text-white italic tracking-tighter uppercase text-orange-500 leading-tight">寻找您的 <br/>完美伙伴</h2>
        <p class="text-gray-500 text-sm">AI 理解您的真实需求 · 多轮对话挖掘隐性偏好 · 可解释推荐理由</p>

        <!-- Step 1: 初始输入 -->
        <div v-if="matchStep === 'input'" class="max-w-4xl mx-auto px-6 mt-8">
          <div class="bg-[#1a1a1a]/80 backdrop-blur-3xl p-2 rounded-[2.5rem] border border-white/10 flex items-center">
            <Wand2 class="ml-6 text-orange-500 shrink-0" :size="28" />
            <input v-model="aiQuery" @keyup.enter="handleAiMatchStart" type="text" placeholder="描述您的理想伙伴，越详细越好..." class="flex-1 bg-transparent py-6 px-6 text-white outline-none" />
            <button @click="handleAiMatchStart" :disabled="isLoadingFollowup || !aiQuery.trim()" class="bg-orange-500 disabled:bg-orange-500/40 disabled:cursor-not-allowed text-white px-10 py-5 rounded-[2rem] font-black flex items-center gap-2 shrink-0">
              <Loader2 v-if="isLoadingFollowup" class="animate-spin" :size="20" />
              <Wand2 v-else :size="20" />
              {{ isLoadingFollowup ? '分析中...' : '开始匹配' }}
            </button>
          </div>
        </div>

        <!-- Step 2: 追问卡片（创新点1：隐性需求显化） -->
        <div v-else-if="matchStep === 'followup'" class="max-w-2xl mx-auto px-6 mt-8 space-y-4 text-left">
          <div class="flex items-center gap-3 mb-4">
            <BrainCircuit class="text-orange-500" :size="22" />
            <div>
              <p class="text-white font-bold text-sm">为您进一步了解需求</p>
              <p class="text-gray-500 text-xs">基于「{{ aiQuery }}」，我还想多了解一些</p>
            </div>
            <button @click="handleAiMatch" class="ml-auto text-xs text-gray-500 hover:text-orange-500 transition-colors">跳过 →</button>
          </div>
          <div v-for="(q, idx) in followupQuestions" :key="q.key" class="bg-[#1a1a1a]/80 border border-white/10 rounded-3xl p-6 space-y-3">
            <p class="text-white text-sm font-semibold">{{ idx + 1 }}. {{ q.question }}</p>
            <div class="flex flex-wrap gap-2">
              <button v-for="opt in q.options" :key="opt" @click="followupAnswers[q.key] = opt"
                :class="followupAnswers[q.key] === opt ? 'bg-orange-500 text-white border-orange-500' : 'bg-white/5 text-gray-400 border-white/10 hover:border-orange-500/50'"
                class="px-4 py-2 rounded-xl text-sm border transition-all font-medium">
                {{ opt }}
              </button>
            </div>
          </div>
          <button @click="handleAiMatch" :disabled="isAiMatching"
            class="w-full bg-orange-500 disabled:bg-orange-500/40 text-white py-5 rounded-2xl font-black flex items-center justify-center gap-2 mt-2">
            <Loader2 v-if="isAiMatching" class="animate-spin" :size="20" />
            <BrainCircuit v-else :size="20" />
            {{ isAiMatching ? 'AI 语义匹配中...' : '生成个性化推荐' }}
          </button>
        </div>

        <!-- Step 3: 匹配结果提示 -->
        <div v-else class="max-w-4xl mx-auto px-6 mt-6">
          <div class="bg-orange-500/10 border border-orange-500/20 rounded-3xl px-8 py-4 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <BrainCircuit class="text-orange-500" :size="20" />
              <span class="text-orange-400 text-sm font-bold">已为您找到 {{ Object.keys(recommendedMatches).length }} 只匹配宠物，排列在前面</span>
            </div>
            <button @click="resetAiMatch" class="text-gray-500 hover:text-white text-xs transition-colors flex items-center gap-1"><X :size="14" />重新搜索</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 过滤器 -->
    <div class="flex flex-col md:flex-row items-center justify-between gap-6 px-4">
      <div class="flex items-center gap-2 bg-white/5 p-1.5 rounded-2xl border border-white/5">
        <button v-for="cat in ['全部', '猫咪', '狗狗', '异宠']" :key="cat" @click="activeFilter = cat"
          :class="activeFilter === cat ? 'bg-orange-500 text-white' : 'text-gray-400 hover:text-white'" class="px-8 py-3 rounded-xl font-bold transition-all text-sm">
          {{ cat }}
        </button>
      </div>
      <div class="relative w-full md:w-96 group">
        <Search class="absolute left-5 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-orange-500 transition-colors" :size="18" />
        <input v-model="searchQuery" type="text" placeholder="搜索品种或名字..." class="w-full bg-white/5 border border-white/5 rounded-2xl py-4 pl-14 pr-6 text-white outline-none focus:bg-white/10 transition-all shadow-inner" />
      </div>
    </div>

    <!-- 卡片网格 -->
    <div class="px-2">
      <div v-if="isLoading" class="py-40 flex flex-col items-center"><Loader2 class="animate-spin text-orange-500" :size="48" /><p class="text-gray-500 font-black mt-4 uppercase">正在寻找伙伴...</p></div>
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-6">
        <div v-for="pet in filteredPets" :key="pet.id" class="bg-[#1a1a1a] rounded-3xl overflow-hidden border border-white/5 transition-all group cursor-pointer shadow-xl relative flex flex-col">
          <!-- 管理员控制台 -->
          <div v-if="isAdmin" class="p-3 bg-orange-500/10 border-b border-orange-500/20 flex justify-end gap-2">
            <button @click.stop="startEditPet(pet)" class="p-1.5 bg-blue-500/20 text-blue-400 hover:bg-blue-500 hover:text-white rounded border border-blue-500/30 transition-all"><Edit3 :size="14"/></button>
            <button @click.stop="handleDeletePet(pet.id)" class="p-1.5 bg-red-500/20 text-red-400 hover:bg-red-500 hover:text-white rounded border border-red-500/30 transition-all"><Trash2 :size="14"/></button>
          </div>

          <div @click="selectedPet = pet" class="relative aspect-square overflow-hidden">
            <img :src="pet.img" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
            <div class="absolute inset-0 bg-gradient-to-t from-[#1a1a1a]/80 via-transparent to-transparent"></div>
            <h4 class="absolute bottom-4 left-5 font-black text-xl text-white">{{ pet.name }}</h4>
          </div>
          <div @click="selectedPet = pet" class="p-5 space-y-3 flex-1">
            <!-- AI 推荐解释（创新点3：可解释推荐） -->
            <div v-if="recommendedMatches[pet.id]" class="bg-orange-500/10 border border-orange-500/20 rounded-2xl p-3 space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-[9px] font-black text-orange-500 uppercase tracking-wider flex items-center gap-1"><BrainCircuit :size="10" />AI 推荐</span>
                <span class="text-[9px] font-black text-orange-400">契合度 {{ recommendedMatches[pet.id]?.fit_score }}%</span>
              </div>
              <p class="text-[10px] text-orange-300 leading-relaxed">{{ recommendedMatches[pet.id]?.reason }}</p>
              <div v-if="recommendedMatches[pet.id]?.fit_advantages?.length" class="space-y-0.5">
                <p v-for="(adv, i) in recommendedMatches[pet.id].fit_advantages.slice(0,2)" :key="i" class="text-[9px] text-green-400 flex items-center gap-1"><span class="text-green-500">✓</span>{{ adv }}</p>
              </div>
              <p v-if="recommendedMatches[pet.id]?.potential_challenges?.length" class="text-[9px] text-yellow-400 flex items-center gap-1"><span>⚠</span>{{ recommendedMatches[pet.id].potential_challenges[0] }}</p>
            </div>
            <div v-else class="flex flex-wrap gap-1.5"><span v-for="t in pet.tags" :key="t" class="text-[9px] bg-white/5 px-2 py-1 rounded-lg text-gray-500">#{{ t }}</span></div>
            <div class="flex items-center justify-between pt-2 border-t border-white/5">
              <div><p class="text-[9px] text-gray-500 uppercase">{{ pet.species }}</p><div class="flex items-center gap-1 text-gray-400"><MapPin :size="10" /><span class="text-[9px] font-bold">{{ pet.distance }} KM</span></div></div>
              <ChevronRight class="text-orange-500" :size="16" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 智能领养申请弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showAdoptModal" class="fixed inset-0 z-[500] flex items-center justify-center bg-black/95 backdrop-blur-md px-4 py-8 overflow-y-auto">
          <div class="bg-[#111] border border-white/10 rounded-[3rem] w-full max-w-2xl my-auto">

            <!-- 弹窗头部 -->
            <div class="p-10 pb-0 flex justify-between items-start">
              <div>
                <div class="flex items-center gap-3 mb-2">
                  <BrainCircuit class="text-orange-500" :size="28" />
                  <span class="text-[10px] font-black text-orange-500 uppercase tracking-widest">AI 智能评估系统</span>
                </div>
                <h3 class="text-3xl font-black text-white italic uppercase tracking-tighter">领养资质评估</h3>
                <p class="text-gray-500 text-sm mt-1">正在为 <span class="text-orange-500 font-bold">{{ adoptingPet?.name }}</span> 寻找合适的家</p>
              </div>
              <button @click="showAdoptModal = false" class="text-gray-500 hover:text-white transition-colors mt-1"><X :size="24"/></button>
            </div>

            <!-- 表单区域（未评估时显示） -->
            <div v-if="!assessmentResult" class="p-10 space-y-6">
              <!-- 个人情况 -->
              <div class="space-y-2">
                <label class="text-xs font-black text-gray-400 uppercase tracking-wider">个人情况描述 <span class="text-orange-500">*</span></label>
                <textarea v-model="adoptForm.applicant_info" rows="3" placeholder="请详细描述您的居住环境（面积/楼层/是否封窗）、职业作息、家庭成员情况等..." class="w-full bg-white/5 border border-white/10 rounded-2xl px-6 py-4 text-white text-sm outline-none focus:border-orange-500 transition-colors resize-none placeholder-gray-600" />
              </div>

              <!-- 领养理由 -->
              <div class="space-y-2">
                <label class="text-xs font-black text-gray-400 uppercase tracking-wider">领养申请理由</label>
                <textarea v-model="adoptForm.application_reason" rows="2" placeholder="为什么想要领养这只宠物？您准备好了吗？" class="w-full bg-white/5 border border-white/10 rounded-2xl px-6 py-4 text-white text-sm outline-none focus:border-orange-500 transition-colors resize-none placeholder-gray-600" />
              </div>

              <!-- 量化信息 -->
              <div class="grid grid-cols-2 gap-4">
                <div class="space-y-2">
                  <label class="text-xs font-black text-gray-400 uppercase tracking-wider">月均养宠预算（元）</label>
                  <input v-model.number="adoptForm.monthly_budget" type="number" min="0" class="w-full bg-white/5 border border-white/10 rounded-2xl px-6 py-4 text-white text-sm outline-none focus:border-orange-500 transition-colors" />
                </div>
                <div class="space-y-2">
                  <label class="text-xs font-black text-gray-400 uppercase tracking-wider">每日陪伴时长（小时）</label>
                  <input v-model.number="adoptForm.daily_companion_hours" type="number" min="0" max="24" step="0.5" class="w-full bg-white/5 border border-white/10 rounded-2xl px-6 py-4 text-white text-sm outline-none focus:border-orange-500 transition-colors" />
                </div>
              </div>

              <!-- 选项 -->
              <div class="grid grid-cols-3 gap-4">
                <div class="space-y-2">
                  <label class="text-xs font-black text-gray-400 uppercase tracking-wider">住房类型</label>
                  <select v-model="adoptForm.housing_type" class="w-full bg-[#1a1a1a] border border-white/10 rounded-2xl px-4 py-4 text-white text-sm outline-none focus:border-orange-500 transition-colors">
                    <option value="apartment">公寓</option>
                    <option value="house">独栋/别墅</option>
                    <option value="other">其他</option>
                  </select>
                </div>
                <div class="space-y-2">
                  <label class="text-xs font-black text-gray-400 uppercase tracking-wider">宠物类型</label>
                  <select v-model="adoptForm.target_species" class="w-full bg-[#1a1a1a] border border-white/10 rounded-2xl px-4 py-4 text-white text-sm outline-none focus:border-orange-500 transition-colors">
                    <option value="cat">猫咪</option>
                    <option value="dog">狗狗</option>
                  </select>
                </div>
                <div class="space-y-2">
                  <label class="text-xs font-black text-gray-400 uppercase tracking-wider">养宠经验</label>
                  <select v-model="adoptForm.has_pet_experience" class="w-full bg-[#1a1a1a] border border-white/10 rounded-2xl px-4 py-4 text-white text-sm outline-none focus:border-orange-500 transition-colors">
                    <option :value="false">新手</option>
                    <option :value="true">有经验</option>
                  </select>
                </div>
              </div>

              <!-- 原住宠物 -->
              <div class="space-y-2">
                <label class="text-xs font-black text-gray-400 uppercase tracking-wider">家中原有宠物（无则留空）</label>
                <input v-model="adoptForm.existing_pets" placeholder="如：家有一只2岁英短猫，已绝育..." class="w-full bg-white/5 border border-white/10 rounded-2xl px-6 py-4 text-white text-sm outline-none focus:border-orange-500 transition-colors placeholder-gray-600" />
              </div>

              <!-- 提交按钮 -->
              <button @click="handleAdoptAssess" :disabled="isAssessing || adoptForm.applicant_info.length < 10" class="w-full bg-orange-500 disabled:bg-orange-500/30 disabled:cursor-not-allowed text-white py-5 rounded-2xl font-black text-lg hover:bg-orange-600 transition-all flex justify-center items-center gap-3">
                <Loader2 v-if="isAssessing" class="animate-spin" :size="22" />
                <BrainCircuit v-else :size="22" />
                {{ isAssessing ? 'AI 多智能体评估中...' : '开始智能评估' }}
              </button>
              <p class="text-center text-xs text-gray-600">由三位 AI 专家协同分析 · 结果仅供参考 · 最终决定由管理员审核</p>
            </div>

            <!-- 评估结果区域 -->
            <div v-else class="p-10 space-y-6">
              <!-- 评分头部 -->
              <div class="bg-white/5 rounded-3xl p-8 flex items-center justify-between border border-white/5">
                <div class="text-center">
                  <div class="text-6xl font-black" :class="assessmentResult.readiness_score >= 70 ? 'text-green-400' : assessmentResult.readiness_score >= 50 ? 'text-yellow-400' : 'text-red-400'">
                    {{ assessmentResult.readiness_score }}
                  </div>
                  <div class="text-xs text-gray-500 mt-1 font-bold uppercase">准备度评分</div>
                </div>
                <div class="text-center">
                  <div class="text-3xl font-black text-white">{{ Math.round((assessmentResult.success_probability || 0) * 100) }}%</div>
                  <div class="text-xs text-gray-500 mt-1 font-bold uppercase">成功倾向</div>
                </div>
                <div class="text-center">
                  <div :class="[riskLevelConfig[assessmentResult.risk_level]?.bg, riskLevelConfig[assessmentResult.risk_level]?.text]" class="px-4 py-2 rounded-full text-sm font-black">
                    {{ riskLevelConfig[assessmentResult.risk_level]?.label || assessmentResult.risk_level }}
                  </div>
                  <div class="text-xs text-gray-500 mt-1 font-bold uppercase">风险等级</div>
                </div>
                <div class="text-center">
                  <component :is="decisionConfig[assessmentResult.decision]?.icon || CheckCircle2" :size="32" :class="decisionConfig[assessmentResult.decision]?.color || 'text-gray-400'" />
                  <div :class="decisionConfig[assessmentResult.decision]?.color || 'text-gray-400'" class="text-xs mt-1 font-black uppercase">
                    {{ decisionConfig[assessmentResult.decision]?.label || assessmentResult.decision }}
                  </div>
                </div>
              </div>

              <!-- 综合报告 -->
              <div class="space-y-2">
                <div class="text-xs font-black text-gray-400 uppercase tracking-wider flex items-center gap-2"><BrainCircuit :size="14" class="text-orange-500" />综合评估摘要</div>
                <div class="bg-white/5 rounded-2xl p-6 text-sm text-gray-300 leading-relaxed border border-white/5 max-h-48 overflow-y-auto whitespace-pre-wrap">{{ assessmentResult.final_summary }}</div>
              </div>

              <!-- 风险因子 -->
              <div v-if="assessmentResult.risk_factors?.length" class="space-y-2">
                <div class="text-xs font-black text-gray-400 uppercase tracking-wider flex items-center gap-2"><AlertTriangle :size="14" class="text-yellow-500" />风险因子（{{ assessmentResult.risk_factors.length }}项）</div>
                <div class="space-y-2 max-h-40 overflow-y-auto pr-1">
                  <div v-for="(rf, i) in assessmentResult.risk_factors" :key="i" class="bg-white/5 rounded-xl px-5 py-3 flex items-start gap-3 border border-white/5">
                    <span :class="severityColor[rf.severity]" class="text-xs font-black uppercase mt-0.5 shrink-0">{{ rf.severity }}</span>
                    <div>
                      <span class="text-orange-400 text-xs font-bold mr-2">{{ rf.dimension }}</span>
                      <span class="text-gray-300 text-xs">{{ rf.description }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 建议 -->
              <div v-if="assessmentResult.recommendations?.length" class="space-y-2">
                <div class="text-xs font-black text-gray-400 uppercase tracking-wider flex items-center gap-2"><CheckCircle2 :size="14" class="text-green-500" />个性化建议</div>
                <ul class="space-y-1.5 max-h-32 overflow-y-auto pr-1">
                  <li v-for="(rec, i) in assessmentResult.recommendations" :key="i" class="flex items-start gap-2 text-xs text-gray-300">
                    <span class="text-orange-500 mt-0.5 shrink-0">›</span>{{ rec }}
                  </li>
                </ul>
              </div>

              <!-- 管理员备注 -->
              <div v-if="assessmentResult.review_note" class="bg-blue-500/10 border border-blue-500/20 rounded-2xl px-6 py-4">
                <div class="text-xs font-black text-blue-400 uppercase mb-1 flex items-center gap-2"><ShieldCheck :size="12" />管理员审核备注</div>
                <p class="text-sm text-gray-300">{{ assessmentResult.review_note }}</p>
              </div>

              <!-- 底部操作 -->
              <div class="flex gap-3 pt-2">
                <button @click="assessmentResult = null" class="flex-1 bg-white/10 text-white py-4 rounded-2xl font-black hover:bg-white/20 transition-all text-sm">重新填写</button>
                <button @click="showAdoptModal = false" class="flex-1 bg-orange-500 text-white py-4 rounded-2xl font-black hover:bg-orange-600 transition-all text-sm">已了解，关闭</button>
              </div>
              <p class="text-center text-xs text-gray-600">评估结果已同步至管理员后台 · Trace ID: {{ assessmentResult.trace_id?.slice(0,8) || 'N/A' }}</p>
            </div>

          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 宠物编辑弹窗 -->
    <Teleport to="body">
      <div v-if="showEditModal" class="fixed inset-0 z-[600] flex items-center justify-center bg-black/95 backdrop-blur-md px-4">
        <div class="bg-[#111] border border-white/10 p-10 rounded-[3rem] w-full max-w-xl space-y-6">
          <div class="flex justify-between items-center mb-4"><h3 class="text-2xl font-black text-white italic uppercase">编辑宠物信息</h3><button @click="showEditModal=false" class="text-gray-500"><X :size="24"/></button></div>
          <div class="space-y-4">
            <input v-model="editPetForm.name" placeholder="宠物名字" class="w-full bg-white/5 border border-white/10 rounded-xl px-6 py-4 text-white outline-none focus:border-orange-500" />
            <input v-model="editPetForm.species" placeholder="品种" class="w-full bg-white/5 border border-white/10 rounded-xl px-6 py-4 text-white outline-none focus:border-orange-500" />
            
            <!-- 图片上传区域 -->
            <div class="flex gap-4">
              <input v-model="editPetForm.img" placeholder="图片地址" class="flex-1 bg-white/5 border border-white/10 rounded-xl px-6 py-4 text-white outline-none focus:border-orange-500" />
              <input type="file" ref="fileInput" class="hidden" accept="image/*" @change="handleFileUpload" />
              <button @click="triggerUpload" :disabled="isUploading" class="bg-white/10 hover:bg-white/20 text-white px-6 rounded-xl font-bold transition-all flex items-center gap-2">
                <Loader2 v-if="isUploading" class="animate-spin" :size="16" />
                <span v-else class="flex items-center gap-2"><Upload :size="16"/> 上传</span>
              </button>
            </div>

            <textarea v-model="editPetForm.desc" placeholder="详细描述" class="w-full h-32 bg-white/5 border border-white/10 rounded-xl p-6 text-white outline-none focus:border-orange-500"></textarea>
            <button @click="handleUpdatePet" :disabled="isUpdatingPet" class="w-full bg-orange-500 text-white py-4 rounded-xl font-black text-lg hover:bg-orange-600 transition-all flex justify-center items-center gap-2">
              <Loader2 v-if="isUpdatingPet" class="animate-spin" :size="20" />确认修改
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 领养后回访弹窗（创新点3：数据飞轮闭环） -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showFeedbackModal" class="fixed inset-0 z-[700] flex items-center justify-center bg-black/95 backdrop-blur-md px-4 py-8 overflow-y-auto">
          <div class="bg-[#111] border border-white/10 rounded-[3rem] w-full max-w-lg my-auto">
            <div class="p-10 pb-0 flex justify-between items-start">
              <div>
                <div class="flex items-center gap-3 mb-2">
                  <Heart class="text-green-400" :size="24" />
                  <span class="text-[10px] font-black text-green-400 uppercase tracking-widest">领养后回访</span>
                </div>
                <h3 class="text-2xl font-black text-white italic uppercase tracking-tighter">{{ feedbackPet?.name }} 现在怎么样了？</h3>
                <p class="text-gray-500 text-sm mt-1">您的反馈帮助 AI 越来越精准 · 数据仅用于优化匹配</p>
              </div>
              <button @click="showFeedbackModal = false" class="text-gray-500 hover:text-white transition-colors mt-1"><X :size="24"/></button>
            </div>

            <!-- 反馈成功 -->
            <div v-if="feedbackSubmitted" class="p-10 text-center space-y-4">
              <div class="text-6xl">🐾</div>
              <p class="text-white font-black text-xl">感谢您的回访！</p>
              <p class="text-gray-400 text-sm">您的真实反馈已记录，将持续帮助改善宠物匹配算法。</p>
              <button @click="showFeedbackModal = false" class="w-full bg-orange-500 text-white py-4 rounded-2xl font-black hover:bg-orange-600 transition-all">关闭</button>
            </div>

            <!-- 反馈表单 -->
            <div v-else class="p-10 space-y-6">
              <!-- 整体满意度 -->
              <div class="space-y-2">
                <label class="text-xs font-black text-gray-400 uppercase tracking-wider">整体满意度</label>
                <div class="flex gap-2">
                  <button v-for="n in [1,2,3,4,5]" :key="n" @click="feedbackForm.overall_satisfaction = n"
                    :class="feedbackForm.overall_satisfaction >= n ? 'text-orange-400' : 'text-gray-600'"
                    class="text-3xl transition-colors hover:text-orange-400">★</button>
                </div>
              </div>
              <!-- 亲密程度 -->
              <div class="space-y-2">
                <label class="text-xs font-black text-gray-400 uppercase tracking-wider">与宠物的亲密程度</label>
                <div class="grid grid-cols-2 gap-2">
                  <button v-for="opt in [{val:'very_close',label:'非常亲密'},{val:'close',label:'比较亲密'},{val:'normal',label:'一般'},{val:'distant',label:'有距离感'}]" :key="opt.val"
                    @click="(feedbackForm.bond_level as any) = opt.val"
                    :class="feedbackForm.bond_level === opt.val ? 'bg-orange-500/20 border-orange-500 text-orange-400' : 'bg-white/5 border-white/10 text-gray-400'"
                    class="py-3 px-4 rounded-xl border text-sm font-bold transition-all">{{ opt.label }}</button>
                </div>
              </div>
              <!-- 意外挑战 -->
              <div class="space-y-2">
                <label class="text-xs font-black text-gray-400 uppercase tracking-wider">遇到的意外挑战（选填）</label>
                <input v-model="feedbackForm.unexpected_challenges" placeholder="如：掉毛比预期多、比较黏人..." class="w-full bg-white/5 border border-white/10 rounded-2xl px-6 py-4 text-white text-sm outline-none focus:border-orange-500 transition-colors placeholder-gray-600" />
              </div>
              <!-- 是否推荐 -->
              <div class="flex items-center gap-4">
                <label class="text-xs font-black text-gray-400 uppercase tracking-wider">会向朋友推荐领养吗？</label>
                <div class="flex gap-2 ml-auto">
                  <button @click="feedbackForm.would_recommend = true" :class="feedbackForm.would_recommend ? 'bg-green-500/20 text-green-400 border-green-500' : 'bg-white/5 text-gray-400 border-white/10'" class="px-4 py-2 rounded-xl border text-sm font-bold transition-all">会 ✓</button>
                  <button @click="feedbackForm.would_recommend = false" :class="!feedbackForm.would_recommend ? 'bg-red-500/20 text-red-400 border-red-500' : 'bg-white/5 text-gray-400 border-white/10'" class="px-4 py-2 rounded-xl border text-sm font-bold transition-all">不会</button>
                </div>
              </div>
              <!-- 自由反馈 -->
              <div class="space-y-2">
                <label class="text-xs font-black text-gray-400 uppercase tracking-wider">想对 AI 说的话（选填）</label>
                <textarea v-model="feedbackForm.free_feedback" rows="2" placeholder="AI 匹配准确吗？有什么想说的..." class="w-full bg-white/5 border border-white/10 rounded-2xl px-6 py-4 text-white text-sm outline-none focus:border-orange-500 transition-colors resize-none placeholder-gray-600" />
              </div>
              <button @click="handleSubmitFeedback" :disabled="isSubmittingFeedback" class="w-full bg-green-600 hover:bg-green-500 disabled:bg-green-600/40 text-white py-5 rounded-2xl font-black text-lg transition-all flex justify-center items-center gap-3">
                <Loader2 v-if="isSubmittingFeedback" class="animate-spin" :size="22" />
                <Heart v-else :size="22" />
                {{ isSubmittingFeedback ? '提交中...' : '提交回访反馈' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 详情弹窗 -->
    <Transition name="fade">
      <div v-if="selectedPet" class="fixed inset-0 z-[100] flex items-center justify-center p-4 backdrop-blur-2xl">
        <div class="absolute inset-0 bg-black/80" @click="selectedPet = null"></div>
        <div class="relative bg-[#111] border border-white/10 rounded-[4rem] max-w-6xl w-full flex flex-col lg:flex-row overflow-hidden shadow-2xl">
          <div class="lg:w-3/5 group overflow-hidden"><img :src="selectedPet.img" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-1000" /></div>
          <div class="lg:w-2/5 p-12 space-y-8 text-left">
            <div><span class="bg-orange-500/20 text-orange-500 px-4 py-1 rounded-full text-[10px] font-black uppercase">{{ selectedPet.type }}</span><h3 class="text-6xl font-black text-white mt-4">{{ selectedPet.name }}</h3></div>
            <p class="text-gray-400 text-lg leading-relaxed">{{ selectedPet.desc }}</p>
            <!-- 创新点3：详情页内联显示结构化推荐解释 -->
            <div v-if="recommendedMatches[selectedPet.id]" class="bg-orange-500/10 border border-orange-500/20 rounded-3xl p-6 space-y-4">
              <div class="flex items-center gap-2 mb-1">
                <BrainCircuit class="text-orange-500" :size="16" />
                <span class="text-orange-500 text-xs font-black uppercase tracking-wider">AI 个性化推荐分析</span>
                <span class="ml-auto text-orange-400 font-black">{{ recommendedMatches[selectedPet.id]?.fit_score }}% 契合</span>
              </div>
              <p class="text-orange-300 text-sm">{{ recommendedMatches[selectedPet.id]?.reason }}</p>
              <div v-if="recommendedMatches[selectedPet.id]?.fit_advantages?.length">
                <p class="text-xs text-gray-500 font-bold mb-1.5">适配优势</p>
                <ul class="space-y-1">
                  <li v-for="adv in recommendedMatches[selectedPet.id].fit_advantages" :key="adv" class="text-xs text-green-400 flex items-center gap-2"><span class="text-green-500">✓</span>{{ adv }}</li>
                </ul>
              </div>
              <div v-if="recommendedMatches[selectedPet.id]?.potential_challenges?.length">
                <p class="text-xs text-gray-500 font-bold mb-1.5">潜在挑战</p>
                <ul class="space-y-1">
                  <li v-for="ch in recommendedMatches[selectedPet.id].potential_challenges" :key="ch" class="text-xs text-yellow-400 flex items-center gap-2"><span>⚠</span>{{ ch }}</li>
                </ul>
              </div>
              <p v-if="recommendedMatches[selectedPet.id]?.mitigation" class="text-xs text-blue-400 bg-blue-500/10 rounded-xl px-4 py-2">💡 {{ recommendedMatches[selectedPet.id].mitigation }}</p>
            </div>
            <!-- 宠物语音聊天（拟人化互动 + TTS语音 + 长期记忆） -->
            <div class="bg-white/5 border border-white/10 rounded-3xl overflow-hidden">
              <div class="flex items-center gap-2 px-5 py-3 border-b border-white/5">
                <Volume2 class="text-orange-500" :size="14" />
                <span class="text-xs font-black text-orange-500 uppercase tracking-wider">和 {{ selectedPet.name }} 说说话</span>
                <span class="ml-auto text-[9px] text-gray-600 uppercase">Edge-TTS · 长期记忆</span>
              </div>
              <!-- 历史消息区域 -->
              <div ref="petChatScrollRef" class="h-48 overflow-y-auto px-4 py-3 space-y-3 scrollbar-hide">
                <div v-if="petChatHistory.length === 0" class="h-full flex items-center justify-center text-gray-600 text-xs">
                  快跟 {{ selectedPet.name }} 打个招呼吧 👋
                </div>
                <div v-for="(msg, i) in petChatHistory" :key="i"
                  :class="msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'"
                  class="flex items-end gap-2">
                  <div class="w-7 h-7 rounded-full overflow-hidden flex-shrink-0 border border-white/10">
                    <img v-if="msg.role === 'pet'" :src="selectedPet.img" class="w-full h-full object-cover" />
                    <img v-else :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${authStore.user?.username || 'me'}`" />
                  </div>
                  <div :class="msg.role === 'user'
                    ? 'bg-orange-500 text-white rounded-tr-none'
                    : 'bg-white/10 text-gray-200 rounded-tl-none border border-white/5'"
                    class="max-w-[75%] px-3 py-2 rounded-2xl text-xs leading-relaxed">
                    {{ msg.content }}
                  </div>
                </div>
                <!-- 加载中气泡 -->
                <div v-if="isPetChatLoading" class="flex items-end gap-2">
                  <div class="w-7 h-7 rounded-full overflow-hidden flex-shrink-0 border border-white/10">
                    <img :src="selectedPet.img" class="w-full h-full object-cover" />
                  </div>
                  <div class="bg-white/10 border border-white/5 px-4 py-2 rounded-2xl rounded-tl-none">
                    <Loader2 class="animate-spin text-orange-500" :size="14" />
                  </div>
                </div>
              </div>
              <!-- 输入框 -->
              <div class="flex gap-2 px-4 py-3 border-t border-white/5">
                <input v-model="petChatMsg" @keyup.enter="handlePetChat" type="text"
                  :placeholder="`跟${selectedPet.name}说...`"
                  class="flex-1 bg-white/5 border border-white/10 rounded-2xl px-4 py-2 text-white text-xs outline-none focus:border-orange-500 transition-colors placeholder-gray-600" />
                <button @click="handlePetChat" :disabled="isPetChatLoading || !petChatMsg.trim()"
                  class="px-3 py-2 bg-orange-500 disabled:bg-orange-500/40 text-white rounded-2xl transition-all flex items-center">
                  <Send :size="14" />
                </button>
              </div>
            </div>

            <div class="flex gap-4 pt-4">
              <button @click="startAdopt(selectedPet)" class="flex-1 bg-white text-black py-6 rounded-[2rem] font-black text-xl hover:bg-orange-500 hover:text-white transition-all flex items-center justify-center gap-2"><ClipboardList :size="22" />智能申请领养</button>
              <button @click="openFeedbackModal(selectedPet)" class="p-6 bg-white/5 text-white rounded-[2rem] border border-white/10 hover:bg-green-500/20 hover:border-green-500/30 hover:text-green-400 transition-all" title="领养后回访"><Heart :size="28" /></button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* @reference "tailwindcss"; */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.scrollbar-hide::-webkit-scrollbar { display: none; }
.scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
</style>
