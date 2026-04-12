<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import {
  Search, Heart, Loader2, X, Wand2, ChevronRight,
  CheckCircle2, BrainCircuit,
  Send, Sparkles, Star
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

const getPetDisplayScore = (pet: any) => {
  const rawScore = Number(recommendedMatches.value[String(pet.id)]?.fit_score);
  if (Number.isFinite(rawScore) && rawScore > 0) return Math.round(rawScore);
  return Math.max(60, Math.round(Number(pet.match) || 0));
};

const sortPetsByDisplayScore = (list: any[]) => {
  return [...list].sort((a, b) => getPetDisplayScore(b) - getPetDisplayScore(a));
};

// 获取 AI 直接命中的匹配宠物
const aiMatchedPets = computed(() => {
  const recIds = new Set(Object.keys(recommendedMatches.value));
  return pets.value
    .filter(p => recIds.has(String(p.id)))
    .sort((a, b) => getPetDisplayScore(b) - getPetDisplayScore(a));
});

const soulmatePets = computed(() => {
  return aiMatchedPets.value.filter((pet) => getPetDisplayScore(pet) >= soulmateThreshold);
});

const closeMatchPets = computed(() => {
  const aiCloseMatches = aiMatchedPets.value.filter((pet) => getPetDisplayScore(pet) < soulmateThreshold);
  const selectedIds = new Set(aiCloseMatches.map((pet) => String(pet.id)));
  const fallbackCandidates = sortPetsByDisplayScore(pets.value)
    .filter((pet) => !selectedIds.has(String(pet.id)))
    .slice(0, recommendationDisplayLimit);
  return sortPetsByDisplayScore([...aiCloseMatches, ...fallbackCandidates]).slice(0, recommendationDisplayLimit);
});

const displayedMatchPets = computed(() => {
  return soulmatePets.value.length > 0 ? aiMatchedPets.value : closeMatchPets.value;
});

const hasSoulmateMatches = computed(() => soulmatePets.value.length > 0);

const displayedMatchCount = computed(() => displayedMatchPets.value.length);

const matchResultHeading = computed(() => {
  if (hasSoulmateMatches.value) return `为您发现 ${soulmatePets.value.length} 位高契合伙伴`;
  if (displayedMatchCount.value > 0) return '当前没有特别契合的灵魂伴侣';
  return '暂未找到合适候选';
});

const matchResultSubtitle = computed(() => {
  if (hasSoulmateMatches.value) return 'AI 已完成多维偏好比对，已优先筛出当前最契合的候选。';
  if (displayedMatchCount.value > 0) return '系统继续为您补充展示几位相近候选，方便继续比较和了解。';
  return '可以稍微放宽描述条件，系统会继续为您检索更多候选。';
});

const getPetMatchReason = (pet: any) => {
  return recommendedMatches.value[String(pet.id)]?.reason
    || `系统结合宠物特征、陪伴需求和当前偏好，为您筛出了这位较接近的候选。`;
};

const getPetMatchAdvantages = (pet: any) => {
  const advantages = recommendedMatches.value[String(pet.id)]?.fit_advantages;
  if (Array.isArray(advantages) && advantages.length) return advantages.slice(0, 3);
  if (Array.isArray(pet.tags) && pet.tags.length) {
    return pet.tags.slice(0, 3).map((tag: string) => `具备${tag}特征`);
  }
  return ['当前整体条件较稳定', '适合作为相近候选继续了解', '建议结合档案与互动进一步判断'];
};

const getPetMatchLabel = (pet: any) => {
  return getPetDisplayScore(pet) >= soulmateThreshold ? '高契合' : '相近推荐';
};

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
  {
    id: 9007,
    name: '糖糖',
    species: '玄凤鹦鹉',
    type: '异宠',
    owner_type: 'personal',
    image_url: 'https://images.unsplash.com/photo-1444464666168-49d633b86797?auto=format&fit=crop&w=900&q=80',
    description: '亲人爱互动，喜欢和人说话学口哨，适合能接受日常放飞和稳定陪伴的家庭。',
    tags: ['会互动', '爱说话', '需放飞'],
    match: 86,
  },
  {
    id: 9008,
    name: '小葵',
    species: '虎皮鹦鹉',
    type: '异宠',
    owner_type: 'org',
    image_url: 'https://images.unsplash.com/photo-1522858547137-f1dcec554f55?auto=format&fit=crop&w=900&q=80',
    description: '活泼好奇，适应力不错，但需要主人有耐心建立信任并保持环境整洁安静。',
    tags: ['活泼', '好奇心强', '需要耐心'],
    match: 84,
  },
  {
    id: 9009,
    name: '泡泡',
    species: '斗鱼',
    type: '异宠',
    owner_type: 'personal',
    image_url: 'https://images.unsplash.com/photo-1524704654690-b56c05c78a00?auto=format&fit=crop&w=900&q=80',
    description: '颜色漂亮，观赏性很强，适合愿意认真维护水质和规律换水的新手鱼友。',
    tags: ['观赏性强', '需稳水质', '安静陪伴'],
    match: 80,
  },
  {
    id: 9010,
    name: '栗子',
    species: '金丝熊仓鼠',
    type: '异宠',
    owner_type: 'personal',
    image_url: 'https://images.unsplash.com/photo-1425082661705-1834bfd09dca?auto=format&fit=crop&w=900&q=80',
    description: '晚上比较活跃，性格温和但胆子小，适合作息相对规律、能提供独立安静空间的人。',
    tags: ['夜间活跃', '胆小', '需要安静'],
    match: 83,
  },
  {
    id: 9011,
    name: '慢慢',
    species: '中华草龟',
    type: '异宠',
    owner_type: 'org',
    image_url: 'https://images.unsplash.com/photo-1466721591366-2d5fba72006d?auto=format&fit=crop&w=900&q=80',
    description: '状态稳定，饲养节奏相对平缓，但需要长期稳定的晒背、过滤和水陆环境管理。',
    tags: ['长寿', '需晒背', '稳定饲养'],
    match: 79,
  },
  {
    id: 9012,
    name: '团团',
    species: '垂耳兔',
    type: '异宠',
    owner_type: 'personal',
    image_url: 'https://images.unsplash.com/photo-1585110396000-c9ffd4e4b308?auto=format&fit=crop&w=900&q=80',
    description: '外表软萌，性格温和，适合愿意做环境防咬、关注肠胃和口腔护理的家庭。',
    tags: ['温和', '软萌', '需防咬环境'],
    match: 82,
  },
  {
    id: 9013,
    name: '年糕',
    species: '英短蓝猫',
    type: '猫咪',
    owner_type: 'personal',
    image_url: 'https://images.unsplash.com/photo-1574158622682-e40e69881006?auto=format&fit=crop&w=900&q=80',
    description: '圆滚滚的小胖猫，亲人爱蹭腿，食欲很好，适合愿意控制饮食并保持互动减重的家庭。',
    tags: ['胖猫', '粘人', '贪吃'],
    match: 87,
  },
  {
    id: 9014,
    name: '小满',
    species: '中华田园猫',
    type: '猫咪',
    owner_type: 'org',
    image_url: 'https://images.unsplash.com/photo-1519052537078-e6302a4968d4?auto=format&fit=crop&w=900&q=80',
    description: '三个月左右的小猫，活泼好奇，喜欢追逐玩具，适合愿意花时间陪伴引导的家庭。',
    tags: ['幼猫', '活泼', '好奇心强'],
    match: 86,
  },
  {
    id: 9015,
    name: '可可',
    species: '美短',
    type: '猫咪',
    owner_type: 'personal',
    image_url: 'https://images.unsplash.com/photo-1495360010541-f48722b34f7d?auto=format&fit=crop&w=900&q=80',
    description: '成年猫，性格稳定，不算特别黏人，更喜欢在你附近安静待着，适合偏安静作息的人。',
    tags: ['成年猫', '独立', '安静'],
    match: 81,
  },
  {
    id: 9016,
    name: '雪球',
    species: '布偶猫',
    type: '猫咪',
    owner_type: 'org',
    image_url: 'https://images.unsplash.com/photo-1592194996308-7b43878e84a6?auto=format&fit=crop&w=900&q=80',
    description: '颜值很高的小猫，超级粘人，喜欢被抱和跟前跟后，适合陪伴时间充足的家庭。',
    tags: ['小猫', '超粘人', '喜欢被抱'],
    match: 89,
  },
  {
    id: 9017,
    name: '煤球',
    species: '黑猫',
    type: '猫咪',
    owner_type: 'personal',
    image_url: 'https://images.unsplash.com/photo-1533738363-b7f9aef128ce?auto=format&fit=crop&w=900&q=80',
    description: '慢热谨慎，刚到新环境可能会先躲一阵子，但熟悉以后会主动靠近，是典型外冷内热型。',
    tags: ['慢热', '不太粘人', '需要耐心'],
    match: 80,
  },
  {
    id: 9018,
    name: '拿铁',
    species: '博美',
    type: '狗狗',
    owner_type: 'personal',
    image_url: 'https://images.unsplash.com/photo-1517849845537-4d257902454a?auto=format&fit=crop&w=900&q=80',
    description: '小体型、元气足，亲人爱撒娇，适合喜欢高频互动、能接受精力旺盛的小型犬家庭。',
    tags: ['小型犬', '爱撒娇', '精力旺'],
    match: 86,
  },
  {
    id: 9019,
    name: '北北',
    species: '哈士奇',
    type: '狗狗',
    owner_type: 'org',
    image_url: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=900&q=80',
    description: '颜值很高但精力旺盛，运动量大，若长期无聊可能会拆家，更适合有遛狗经验的家庭。',
    tags: ['大型犬', '会拆家', '运动量大'],
    match: 78,
  },
  {
    id: 9020,
    name: '安安',
    species: '拉布拉多',
    type: '狗狗',
    owner_type: 'personal',
    image_url: 'https://images.unsplash.com/photo-1561037404-61cd46aa615b?auto=format&fit=crop&w=900&q=80',
    description: '典型大暖男，稳定友好，不怎么拆家，适合喜欢大型犬但希望相对省心的家庭。',
    tags: ['大型犬', '不拆家', '温顺稳定'],
    match: 88,
  },
  {
    id: 9021,
    name: '豆包',
    species: '比熊',
    type: '狗狗',
    owner_type: 'org',
    image_url: 'https://images.unsplash.com/photo-1548199973-03cce0bbc87b?auto=format&fit=crop&w=900&q=80',
    description: '小体型、亲人、喜欢黏着主人，对家庭互动感要求比较高，适合居家时间较多的人。',
    tags: ['小型犬', '粘人', '陪伴需求高'],
    match: 85,
  },
  {
    id: 9022,
    name: '老麦',
    species: '中华田园犬',
    type: '狗狗',
    owner_type: 'personal',
    image_url: 'https://images.unsplash.com/photo-1518717758536-85ae29035b6d?auto=format&fit=crop&w=900&q=80',
    description: '成犬，情绪稳定，日常很省心，散步节奏平稳，适合第一次养中大型犬的人慢慢上手。',
    tags: ['成犬', '稳重', '不闹腾'],
    match: 82,
  },
  {
    id: 9023,
    name: '闪电',
    species: '边牧',
    type: '狗狗',
    owner_type: 'org',
    image_url: 'https://images.unsplash.com/photo-1558788353-f76d92427f16?auto=format&fit=crop&w=900&q=80',
    description: '聪明敏捷，学习能力很强，但也需要大量运动和脑力消耗，适合愿意训练互动的家庭。',
    tags: ['聪明', '高精力', '需要训练'],
    match: 83,
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
        adoption_preferences: parseAdoptionPreferences(p.adoption_preferences),
        tags: p.tags ? (typeof p.tags === 'string' ? JSON.parse(p.tags) : p.tags) : ['温顺', '粘人'],
        match: 80 + (p.id % 20)
      }));
      const mockPets = generatePets().map((p: any) => ({
        ...p,
        img: p.image_url,
        desc: p.description,
        adoption_preferences: buildMockAdoptionPreferences(),
      }));
      pets.value = [...realPets, ...mockPets];
    } else {
      pets.value = generatePets().map((p: any) => ({ ...p, img: p.image_url, desc: p.description, adoption_preferences: buildMockAdoptionPreferences() }));
    }
  } catch (err) {
    console.error('获取列表失败');
    pets.value = generatePets().map((p: any) => ({ ...p, img: p.image_url, desc: p.description, adoption_preferences: buildMockAdoptionPreferences() }));
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
      target_pet_name: adoptingPet.value?.name || '未知宠物',
      publisher_preferences: adoptingPet.value?.adoption_preferences || defaultAdoptionPreferences,
    }, { timeout: 180000 });
    assessmentResult.value = res.data;
  } catch (err: any) { alert('评估服务异常'); }
  finally { isAssessing.value = false; }
};

const submitAdoptionApplication = async () => {
  if (!adoptingPet.value || !assessmentResult.value) return;
  if (!authStore.ensureValidSession() || !authStore.user?.id) {
    alert('正式提交领养申请前请先登录。');
    router.push('/login');
    return;
  }
  isSubmittingApplication.value = true;
  try {
    const submitRes = await axios.post('/api/user/applications/submit', {
      pet_id: adoptingPet.value.id,
      apply_reason: adoptForm.value.application_reason || adoptForm.value.applicant_info,
      ai_decision: assessmentResult.value.decision,
      ai_readiness_score: assessmentResult.value.readiness_score,
      ai_summary: assessmentResult.value.final_summary,
      risk_level: assessmentResult.value.risk_level,
      consensus_score: assessmentResult.value.confidence_level ? assessmentResult.value.confidence_level * 100 : null,
      conflict_notes: assessmentResult.value.conflict_notes || [],
      followup_questions: assessmentResult.value.followup_questions || [],
      memory_scope: assessmentResult.value.trace_id ? `/adoption/${assessmentResult.value.trace_id}` : '',
      assessment_payload: {
        ...adoptForm.value,
        target_pet_name: adoptingPet.value?.name || '未知宠物',
        target_species: adoptForm.value.target_species,
        publisher_preferences: adoptingPet.value?.adoption_preferences || defaultAdoptionPreferences,
        latest_assessment: assessmentResult.value,
      }
    });
    if (submitRes.data?.application_id) {
      await axios.post(`/api/adoption/evaluate/${submitRes.data.application_id}`);
    }
    alert('申请已提交，系统已启动生命周期评估，请到个人中心查看流程状态。');
    showAdoptModal.value = false;
    assessmentResult.value = null;
  } catch (err: any) {
    if (err.response?.status === 401) {
      alert('登录状态已失效，请重新登录后再提交领养申请。');
      router.push('/login');
    } else {
      alert(err.response?.data?.detail || '提交失败');
    }
  }
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
                  <h3 class="text-xl sm:text-2xl md:text-4xl font-black italic uppercase leading-tight">{{ matchResultHeading }}</h3>
                  <p class="text-xs md:text-sm text-gray-500 dark:text-gray-400 mt-1 font-black">{{ matchResultSubtitle }}</p>
                </div>
              </div>
              <button @click="showMatchResultModal = false" class="self-end sm:self-auto w-12 h-12 md:w-14 md:h-14 rounded-full bg-gray-200 dark:bg-white/5 flex items-center justify-center text-gray-500 dark:text-gray-400 hover:text-orange-500 transition-all active:scale-90 shadow-sm"><X :size="24" class="md:hidden"/><X :size="28" class="hidden md:block"/></button>
            </div>

            <div class="flex-1 overflow-y-auto p-4 md:p-10 scrollbar-hide">
              <div v-if="displayedMatchPets.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-8">
                <div v-for="pet in displayedMatchPets" :key="pet.id" 
                  class="group bg-white dark:bg-white/5 border border-gray-200 dark:border-white/5 rounded-[3rem] overflow-hidden flex flex-col shadow-sm hover:shadow-2xl transition-all duration-500">
                  <div class="relative aspect-video">
                    <img :src="pet.img" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
                    <div class="absolute inset-0 bg-gradient-to-t from-gray-50 dark:from-[#111] via-transparent to-transparent opacity-80"></div>
                    <div class="absolute top-4 right-4 bg-orange-500 text-white px-4 py-2 rounded-2xl font-black text-sm flex items-center gap-1 shadow-lg">
                      <Star :size="14" fill="currentColor" /> {{ getPetDisplayScore(pet) }}% {{ getPetMatchLabel(pet) }}
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
                      <p class="text-sm text-orange-700 dark:text-orange-300 font-bold italic leading-relaxed">"{{ getPetMatchReason(pet) }}"</p>
                      
                      <!-- 新增：得分 Breakdown 展示 -->
                      <div v-if="recommendedMatches[String(pet.id)]?.scores" class="grid grid-cols-2 gap-2 pb-2 border-b border-orange-200/30">
                        <div class="flex flex-col">
                          <span class="text-[8px] text-gray-400 font-black uppercase">居住契合</span>
                          <span class="text-xs font-black text-orange-600">{{ Math.round(recommendedMatches[String(pet.id)].scores.condition || 0) }}</span>
                        </div>
                        <div class="flex flex-col">
                          <span class="text-[8px] text-gray-400 font-black uppercase">偏好对齐</span>
                          <span class="text-xs font-black text-blue-600">{{ Math.round(recommendedMatches[String(pet.id)].scores.preference || 0) }}</span>
                        </div>
                        <div class="flex flex-col">
                          <span class="text-[8px] text-gray-400 font-black uppercase">经验适配</span>
                          <span class="text-xs font-black text-green-600">{{ Math.round(recommendedMatches[String(pet.id)].scores.experience || 0) }}</span>
                        </div>
                        <div class="flex flex-col">
                          <span class="text-[8px] text-gray-400 font-black uppercase">风险抵扣</span>
                          <span class="text-xs font-black text-red-600">-{{ Math.round(recommendedMatches[String(pet.id)].scores.penalty || 0) }}</span>
                        </div>
                      </div>

                      <div class="space-y-2">
                        <div v-for="adv in getPetMatchAdvantages(pet)" :key="adv" class="text-xs text-green-700 dark:text-green-400 font-black flex items-start gap-2">
                          <CheckCircle2 :size="14" class="shrink-0 mt-0.5" /> {{ adv }}
                        </div>
                        <!-- 新增：拦截原因展示 -->
                        <div v-for="reason in recommendedMatches[String(pet.id)]?.reasons?.filter(r => r.includes('拦截'))" :key="reason" class="text-xs text-red-600 dark:text-red-400 font-black flex items-start gap-2">
                          <AlertTriangle :size="14" class="shrink-0 mt-0.5" /> {{ reason }}
                        </div>
                      </div>
                    </div>
                    <button @click="startAdopt(pet)" class="mt-auto w-full bg-gray-900 dark:bg-white text-white dark:text-black py-4 md:py-5 rounded-2xl font-black text-sm hover:bg-orange-500 hover:text-white transition-all shadow-xl active:scale-95">立即发起领养</button>
                  </div>
                </div>
              </div>
              <div v-else class="min-h-[18rem] flex flex-col items-center justify-center text-center rounded-[2.5rem] bg-white dark:bg-white/5 border border-gray-200 dark:border-white/5 px-6">
                <div class="w-16 h-16 rounded-3xl bg-orange-100 dark:bg-orange-500/10 text-orange-500 flex items-center justify-center mb-5">
                  <Sparkles :size="28" />
                </div>
                <h4 class="text-2xl font-black text-gray-900 dark:text-white">这次还没刷出特别合适的候选</h4>
                <p class="mt-3 max-w-xl text-sm md:text-base text-gray-500 dark:text-gray-400 font-bold leading-7">
                  可以换一种描述方式，补充喜欢的性格、家庭环境或陪伴时间，系统会继续从当前宠物库里为您筛选更接近的对象。
                </p>
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

    <!-- 4. 详情与互动聊天 (左右并列布局) -->
    <Transition name="fade">
      <div v-if="selectedPet" class="fixed inset-0 z-[1100] flex items-center justify-center p-2 md:p-4 backdrop-blur-xl">
        <div class="absolute inset-0 bg-black/60" @click="selectedPet = null"></div>
        <div class="relative bg-white dark:bg-[#111] border border-gray-200 dark:border-white/10 rounded-[1.5rem] md:rounded-[2rem] max-w-5xl w-full shadow-2xl max-h-[92vh] flex flex-col overflow-hidden text-gray-900 dark:text-white transition-all">
          
          <!-- 头部 - 紧凑型 -->
          <div class="flex items-center justify-between px-4 py-3 md:py-4 border-b border-gray-100 dark:border-white/5 flex-shrink-0 bg-gray-50/50 dark:bg-white/2">
            <div class="flex items-center gap-3">
              <img :src="selectedPet.img" class="w-10 h-10 md:w-12 md:h-12 rounded-xl object-cover shadow-sm border border-black/5 dark:border-white/5" />
              <div>
                <h3 class="text-lg md:text-xl font-black leading-tight">{{ selectedPet.name }}</h3>
                <div class="flex items-center gap-2 mt-0.5">
                  <span class="bg-orange-500/10 text-orange-600 px-2 py-0.5 rounded text-[8px] md:text-[9px] font-black uppercase tracking-wider">{{ selectedPet.type }}</span>
                  <span class="text-[9px] md:text-[10px] text-gray-400 font-bold uppercase">{{ selectedPet.species }}</span>
                </div>
              </div>
            </div>
            <button @click="selectedPet = null" class="w-8 h-8 md:w-10 md:h-10 bg-gray-100 dark:bg-white/5 rounded-full flex items-center justify-center text-gray-400 hover:text-orange-500 transition-all active:scale-90"><X :size="18" /></button>
          </div>

          <!-- 主体内容 - 左右并列 -->
          <div class="flex flex-col md:flex-row flex-1 overflow-hidden min-h-0">
            
            <!-- 左侧：宠物信息与偏好 -->
            <div class="w-full md:w-[45%] overflow-y-auto p-4 md:p-6 space-y-4 md:space-y-5 border-b md:border-b-0 md:border-r border-gray-100 dark:border-white/5 scrollbar-hide">
              
              <!-- 图片画廊区 -->
              <div class="space-y-3">
                <div class="relative aspect-video rounded-2xl overflow-hidden group cursor-zoom-in shadow-md" @click="showImageViewer = true">
                  <img :src="previewImages[activeImgIndex]" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" />
                  <div class="absolute bottom-3 right-3 bg-black/50 backdrop-blur-md text-white px-2 py-1 rounded-lg text-[10px] font-black flex items-center gap-1.5">
                    <Sparkles :size="12" /> {{ activeImgIndex + 1 }} / {{ previewImages.length }}
                  </div>
                </div>
                <!-- 缩略图列表 -->
                <div v-if="previewImages.length > 1" class="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                  <button 
                    v-for="(img, idx) in previewImages" 
                    :key="idx" 
                    @click="activeImgIndex = idx"
                    :class="activeImgIndex === idx ? 'ring-2 ring-orange-500 opacity-100' : 'opacity-60 hover:opacity-100'"
                    class="relative w-16 h-12 md:w-20 md:h-14 rounded-lg overflow-hidden shrink-0 transition-all"
                  >
                    <img :src="img" class="w-full h-full object-cover" />
                  </button>
                </div>
              </div>

              <div class="space-y-2">
                <p class="text-[9px] md:text-[10px] font-black text-orange-500 uppercase tracking-widest">宠物档案</p>
                <p class="text-xs md:text-sm leading-6 text-gray-700 dark:text-gray-300 font-black italic">{{ selectedPet.desc }}</p>
              </div>

              <!-- 领养偏好卡片 - 更加紧凑 -->
              <div class="bg-orange-50/50 dark:bg-white/2 border border-orange-100/50 dark:border-white/5 rounded-xl p-3 md:p-4 space-y-3">
                <div class="flex items-center justify-between gap-2">
                  <p class="text-[8px] md:text-[9px] font-black text-orange-600 uppercase tracking-widest">送养关注</p>
                  <span class="px-2 py-0.5 rounded-full bg-white dark:bg-white/10 text-[9px] md:text-[10px] font-black text-gray-600 dark:text-gray-300">
                    {{ riskToleranceLabel(selectedPet.adoption_preferences?.risk_tolerance) }}倾向
                  </span>
                </div>
                <div class="flex flex-wrap gap-1.5">
                  <span
                    v-for="item in summarizePetExpectations(selectedPet.adoption_preferences || defaultAdoptionPreferences)"
                    :key="item"
                    class="px-2 py-1 rounded-lg bg-white/80 dark:bg-white/5 text-[10px] md:text-xs font-black text-gray-700 dark:text-gray-200 border border-orange-100/30 dark:border-white/5"
                  >
                    {{ item }}
                  </span>
                </div>
                <div v-if="selectedPet.adoption_preferences?.hard_preferences?.length" class="space-y-0.5 pt-1">
                  <p class="text-[8px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">硬性条件</p>
                  <p class="text-[10px] md:text-xs leading-5 text-gray-600 dark:text-gray-400">{{ selectedPet.adoption_preferences.hard_preferences.join('、') }}</p>
                </div>
              </div>

              <!-- 底部操作按钮 -->
              <div class="flex gap-2 pt-2 md:pt-4">
                <button @click="startAdopt(selectedPet)" class="flex-1 bg-gray-950 dark:bg-white text-white dark:text-black py-2.5 md:py-3 rounded-lg font-black text-[11px] md:text-xs hover:bg-orange-500 hover:text-white transition-all shadow-lg flex items-center justify-center gap-2 active:scale-95"><Sparkles :size="14" />立即申请领养</button>
                <button @click="openFeedbackModal(selectedPet)" class="px-3 md:px-4 py-2.5 md:py-3 bg-white dark:bg-white/5 text-gray-400 dark:text-white rounded-lg border border-gray-200 dark:border-white/10 hover:text-green-500 transition-all active:scale-90"><Heart :size="16" /></button>
              </div>
            </div>

            <!-- 右侧：AI 拟人对话区 -->
            <div class="flex-1 flex flex-col bg-gray-50/30 dark:bg-black/10 min-h-0">
              <div class="px-4 py-2.5 border-b border-gray-100 dark:border-white/5 bg-white/50 dark:bg-white/2">
                <p class="text-[10px] md:text-xs font-black text-gray-800 dark:text-gray-200 flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                  正在与 {{ selectedPet.name }} 交流
                </p>
              </div>
              
              <!-- 聊天记录 - 自动占满剩余空间 -->
              <div ref="petChatScrollRef" class="flex-1 overflow-y-auto px-4 py-4 space-y-3 scrollbar-hide">
                <div v-for="(msg, i) in petChatHistory" :key="i" :class="msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'" class="flex items-end gap-2">
                  <div class="w-6 h-6 md:w-7 md:h-7 rounded-full overflow-hidden border border-gray-200 dark:border-white/10 shadow-sm shrink-0">
                    <img v-if="msg.role === 'pet'" :src="selectedPet.img" class="w-full h-full object-cover" />
                    <img v-else :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${authStore.user?.username}`" />
                  </div>
                  <div :class="msg.role === 'user' ? 'bg-orange-500 text-white rounded-tr-none' : 'bg-white dark:bg-white/10 text-gray-800 dark:text-gray-200 border border-gray-100 dark:border-white/5 rounded-tl-none font-bold'" class="px-3 py-2 rounded-xl text-[11px] md:text-xs max-w-[85%] leading-5 shadow-sm break-words">{{ msg.content }}</div>
                </div>
              </div>

              <!-- 输入框 -->
              <div class="p-3 md:p-4 border-t border-gray-100 dark:border-white/5 bg-white dark:bg-transparent">
                <div class="flex gap-2">
                  <input v-model="petChatMsg" @keyup.enter="handlePetChat" type="text" placeholder="给它发个消息..." class="flex-1 bg-gray-100 dark:bg-white/5 border border-transparent dark:border-white/10 rounded-lg px-3 py-2 text-[11px] md:text-xs outline-none focus:border-orange-500 transition-colors text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 font-bold" />
                  <button @click="handlePetChat" :disabled="isPetChatLoading || !petChatMsg.trim()" class="px-3 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 shadow-md active:scale-95 transition-all flex items-center justify-center"><Send :size="14" /></button>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </Transition>

    <!-- 5. 领养申请弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
          <div v-if="showAdoptModal" class="fixed inset-0 z-[1200] flex items-start md:items-center justify-center bg-white/92 dark:bg-black/92 backdrop-blur-md px-2 md:px-4 py-3 md:py-6 overflow-y-auto transition-all">
          <div class="bg-white dark:bg-[#111] border border-gray-300/80 dark:border-white/10 rounded-[1.5rem] md:rounded-[2.5rem] w-full max-w-xl my-auto text-gray-900 dark:text-white shadow-2xl overflow-hidden transition-all max-h-[calc(100vh-1rem)] flex flex-col">
            <div class="p-4 md:p-8 md:pb-0 flex justify-between items-start gap-4 text-gray-900 dark:text-white flex-shrink-0">
              <div class="space-y-1">
                <div class="flex items-center gap-2.5"><BrainCircuit class="text-orange-500" :size="24" /><span class="text-[9px] md:text-[10px] font-black text-orange-500 uppercase tracking-[0.2em]">AI 智能专家评审</span></div>
                <h3 class="text-xl md:text-3xl font-black italic uppercase text-gray-950 dark:text-white leading-tight">申请领养</h3>
                <p class="text-xs md:text-sm text-slate-600 dark:text-slate-300 font-black">正在为 <span class="text-orange-500">{{ adoptingPet?.name }}</span> 建立匹配报告</p>
              </div>
              <button @click="showAdoptModal = false" class="text-slate-400 hover:text-orange-500 transition-all active:scale-90"><X :size="24"/></button>
            </div>
            
            <div class="flex-1 overflow-y-auto p-4 md:p-8 scrollbar-hide">
              <div v-if="!assessmentResult" class="space-y-4 md:space-y-6">
                <div class="bg-orange-50/80 dark:bg-white/5 border border-orange-200 dark:border-white/10 rounded-[1rem] md:rounded-[1.5rem] p-3 md:p-4">
                  <p class="text-[9px] md:text-[10px] text-orange-600 font-black uppercase tracking-widest mb-2">送养方关注项</p>
                  <div class="flex flex-wrap gap-1.5">
                    <span
                      v-for="item in summarizePetExpectations(adoptingPet?.adoption_preferences || defaultAdoptionPreferences)"
                      :key="item"
                      class="px-2.5 py-1.5 rounded-lg bg-white dark:bg-white/10 text-[11px] md:text-xs font-black text-slate-800 dark:text-gray-100 border border-orange-200 dark:border-white/10"
                    >
                      {{ item }}
                    </span>
                  </div>
                </div>
                <div class="space-y-1.5">
                  <label class="text-[9px] md:text-[10px] text-slate-600 dark:text-slate-300 font-black uppercase tracking-widest">个人画像描述 (不低于10字)</label>
                  <textarea v-model="adoptForm.applicant_info" rows="3" placeholder="描述居住环境、职业稳定性、家庭态度等..." class="w-full bg-white dark:bg-[#1a1a1a] border border-gray-300 dark:border-white/10 rounded-xl md:rounded-2xl px-4 md:px-5 py-3 md:py-4 outline-none focus:border-orange-500 focus:ring-4 focus:ring-orange-500/10 transition-all shadow-inner text-sm leading-6 text-gray-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 placeholder:font-bold font-black" />
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                  <div class="space-y-1.5">
                    <label class="text-[9px] md:text-[10px] text-slate-600 dark:text-slate-300 font-black uppercase tracking-widest">月预算（元）</label>
                    <input v-model.number="adoptForm.monthly_budget" type="number" min="0" class="w-full bg-white dark:bg-[#1a1a1a] border border-gray-300 dark:border-white/10 rounded-xl px-4 py-2.5 outline-none focus:border-orange-500 text-sm text-gray-900 dark:text-white font-black" />
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-[9px] md:text-[10px] text-slate-600 dark:text-slate-300 font-black uppercase tracking-widest">日陪伴时长</label>
                    <input v-model.number="adoptForm.daily_companion_hours" type="number" min="0" max="24" step="0.5" class="w-full bg-white dark:bg-[#1a1a1a] border border-gray-300 dark:border-white/10 rounded-xl px-4 py-2.5 outline-none focus:border-orange-500 text-sm text-gray-900 dark:text-white font-black" />
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-[9px] md:text-[10px] text-slate-600 dark:text-slate-300 font-black uppercase tracking-widest">住房类型</label>
                    <select v-model="adoptForm.housing_type" class="w-full bg-white dark:bg-[#1a1a1a] border border-gray-300 dark:border-white/10 rounded-xl px-4 py-2.5 outline-none focus:border-orange-500 text-sm text-gray-900 dark:text-white font-black">
                      <option value="apartment">公寓</option>
                      <option value="house">独立住宅</option>
                      <option value="other">其他</option>
                    </select>
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-[9px] md:text-[10px] text-slate-600 dark:text-slate-300 font-black uppercase tracking-widest">原住宠物</label>
                    <input v-model="adoptForm.existing_pets" type="text" placeholder="如：已有一只母猫" class="w-full bg-white dark:bg-[#1a1a1a] border border-gray-300 dark:border-white/10 rounded-xl px-4 py-2.5 outline-none focus:border-orange-500 text-sm text-gray-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 placeholder:font-bold font-black" />
                  </div>
                </div>
                <div class="space-y-2">
                  <label class="text-[9px] md:text-[10px] text-slate-600 dark:text-slate-300 font-black uppercase tracking-widest">养宠经验</label>
                  <div class="flex gap-2.5">
                    <button @click="adoptForm.has_pet_experience = true" :class="adoptForm.has_pet_experience ? 'bg-orange-500 text-white border-orange-500 shadow-md shadow-orange-500/10' : 'bg-white dark:bg-white/5 text-slate-700 dark:text-slate-200 border-gray-300 dark:border-white/10 hover:border-orange-300'" class="flex-1 rounded-xl border px-3 py-2.5 text-xs font-black transition-all">有经验</button>
                    <button @click="adoptForm.has_pet_experience = false" :class="!adoptForm.has_pet_experience ? 'bg-orange-500 text-white border-orange-500 shadow-md shadow-orange-500/10' : 'bg-white dark:bg-white/5 text-slate-700 dark:text-slate-200 border-gray-300 dark:border-white/10 hover:border-orange-300'" class="flex-1 rounded-xl border px-3 py-2.5 text-xs font-black transition-all">首次养宠</button>
                  </div>
                </div>
                <button @click="handleAdoptAssess" :disabled="isAssessing || adoptForm.applicant_info.length < 10" class="w-full bg-orange-500 disabled:bg-orange-500/40 text-white py-3.5 md:py-5 rounded-xl md:rounded-2xl font-black text-sm md:text-base flex justify-center items-center gap-3 transition-all active:scale-95 shadow-xl shadow-orange-500/10">
                  <Loader2 v-if="isAssessing" class="animate-spin" :size="20" />
                  <BrainCircuit v-else :size="20" />
                  {{ isAssessing ? '正在审计资质...' : '开始 AI 多维评估' }}
                </button>
              </div>

              <div v-else class="space-y-5 md:space-y-6">
                <div class="bg-white dark:bg-white/5 rounded-2xl md:rounded-3xl p-5 md:p-8 border border-gray-200 dark:border-white/5 text-center space-y-2 shadow-lg">
                  <div class="text-4xl md:text-6xl font-black text-orange-500">{{ assessmentResult.readiness_score }}</div>
                  <p class="text-[9px] md:text-[10px] text-slate-500 dark:text-slate-300 font-black uppercase tracking-widest">领养准备度总分</p>
                  <div :class="[riskLevelConfig[assessmentResult.risk_level]?.bg, riskLevelConfig[assessmentResult.risk_level]?.text]" class="inline-block px-4 py-1.5 rounded-full text-[10px] font-black uppercase">{{ riskLevelConfig[assessmentResult.risk_level]?.label }}</div>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                  <div class="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl md:rounded-2xl p-3 md:p-4">
                    <p class="text-[9px] md:text-[10px] font-black text-slate-500 dark:text-slate-300 uppercase tracking-widest mb-1">系统建议动作</p>
                    <p class="text-sm md:text-base font-black text-gray-900 dark:text-white">
                      {{ assessmentResult.decision === 'pass' ? '建议通过' : assessmentResult.decision === 'conditional_pass' ? '需沟通后通过' : assessmentResult.decision === 'reject' ? '建议拒绝' : '建议人工复核' }}
                    </p>
                  </div>
                  <div class="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl md:rounded-2xl p-3 md:p-4">
                    <p class="text-[9px] md:text-[10px] font-black text-slate-500 dark:text-slate-300 uppercase tracking-widest mb-1">申请画像摘要</p>
                    <p class="text-[11px] md:text-xs text-gray-700 dark:text-gray-300 leading-5 font-semibold">
                      {{ adoptForm.has_pet_experience ? '有经验' : '首次' }}，{{ housingTypeLabel(adoptForm.housing_type) }}居住，约{{ adoptForm.daily_companion_hours }}h陪伴，月预算{{ adoptForm.monthly_budget }}元。
                    </p>
                  </div>
                </div>

                <div v-if="assessmentResult.dimension_scores?.length" class="space-y-3">
                  <div class="flex items-center justify-between gap-2">
                    <h4 class="text-sm md:text-base font-black">七维领养评估</h4>
                    <span class="text-[9px] font-black text-slate-500 dark:text-slate-300 uppercase tracking-widest">AI辅助审计</span>
                  </div>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                    <div v-for="dimension in assessmentResult.dimension_scores" :key="dimension.key" class="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl md:rounded-2xl p-3 md:p-4 space-y-2">
                      <div class="flex items-start justify-between gap-2">
                        <div>
                          <p class="text-xs md:text-sm font-black text-gray-900 dark:text-white">{{ dimension.label }}</p>
                          <p class="text-[10px] md:text-[11px] text-slate-500 dark:text-slate-300 mt-0.5 font-semibold">评分 {{ dimension.score }}/100</p>
                        </div>
                        <span :class="dimensionRiskClass(dimension.risk_level)" class="px-2 py-0.5 rounded-full text-[8px] font-black uppercase">{{ dimension.risk_level }}</span>
                      </div>
                      <p class="text-[10px] md:text-[11px] leading-5 text-gray-700 dark:text-gray-300">{{ dimension.suggestion }}</p>
                    </div>
                  </div>
                </div>
                
                <p v-if="assessmentResult.final_summary" class="text-[11px] md:text-xs leading-5 md:leading-6 text-gray-700 dark:text-gray-300 bg-white/70 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl md:rounded-2xl p-3 md:p-4 font-semibold italic">
                  {{ assessmentResult.final_summary }}
                </p>

                <div v-if="assessmentResult.followup_questions?.length || assessmentResult.recommendations?.length" class="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                  <div v-if="assessmentResult.followup_questions?.length" class="bg-orange-50 dark:bg-orange-500/10 border border-orange-100 dark:border-orange-500/20 rounded-xl md:rounded-2xl p-3 md:p-4">
                    <p class="text-[9px] md:text-[10px] font-black text-orange-600 uppercase tracking-widest mb-2">建议追问</p>
                    <ul class="space-y-1">
                      <li v-for="item in assessmentResult.followup_questions.slice(0, 3)" :key="item" class="text-[10px] md:text-[11px] leading-4 text-orange-700 dark:text-orange-200">? {{ item }}</li>
                    </ul>
                  </div>
                  <div v-if="assessmentResult.recommendations?.length" class="bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 rounded-xl md:rounded-2xl p-3 md:p-4">
                    <p class="text-[9px] md:text-[10px] font-black text-blue-600 uppercase tracking-widest mb-2">优化建议</p>
                    <ul class="space-y-1">
                      <li v-for="item in assessmentResult.recommendations.slice(0, 3)" :key="item" class="text-[10px] md:text-[11px] leading-4 text-blue-700 dark:text-blue-200">• {{ item }}</li>
                    </ul>
                  </div>
                </div>
                
                <button @click="submitAdoptionApplication" :disabled="isSubmittingApplication" class="w-full bg-orange-500 text-white py-3.5 md:py-5 rounded-xl md:rounded-2xl font-black text-sm md:text-base transition-all active:scale-95 shadow-xl shadow-orange-500/10">确认并正式提交申请</button>
              </div>
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

    <!-- 7. 全屏图片查看器 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showImageViewer && previewImages.length" class="fixed inset-0 z-[2000] bg-black/95 backdrop-blur-xl flex flex-col items-center justify-center p-4 overflow-hidden">
          <button @click="showImageViewer = false" class="absolute top-6 right-6 w-12 h-12 rounded-full bg-white/10 flex items-center justify-center text-white hover:bg-white/20 transition-all z-[2010]"><X :size="28" /></button>
          
          <div class="relative w-full max-w-5xl aspect-auto flex items-center justify-center group">
            <!-- 切换按钮 -->
            <button v-if="previewImages.length > 1" @click="activeImgIndex = (activeImgIndex - 1 + previewImages.length) % previewImages.length" 
              class="absolute left-4 w-12 h-12 rounded-full bg-white/10 flex items-center justify-center text-white hover:bg-white/20 transition-all opacity-0 group-hover:opacity-100"><ChevronRight class="rotate-180" :size="24" /></button>
            
            <img :src="previewImages[activeImgIndex]" class="max-w-full max-h-[80vh] object-contain shadow-2xl rounded-lg" />
            
            <button v-if="previewImages.length > 1" @click="activeImgIndex = (activeImgIndex + 1) % previewImages.length" 
              class="absolute right-4 w-12 h-12 rounded-full bg-white/10 flex items-center justify-center text-white hover:bg-white/20 transition-all opacity-0 group-hover:opacity-100"><ChevronRight :size="24" /></button>
          </div>

          <!-- 底部缩略图指示器 -->
          <div v-if="previewImages.length > 1" class="absolute bottom-10 flex gap-3 px-4 overflow-x-auto max-w-full scrollbar-hide">
            <button 
              v-for="(img, idx) in previewImages" 
              :key="idx" 
              @click="activeImgIndex = idx"
              :class="activeImgIndex === idx ? 'ring-2 ring-orange-500 scale-110' : 'opacity-40 hover:opacity-100'"
              class="w-16 h-12 rounded-md overflow-hidden transition-all shrink-0"
            >
              <img :src="img" class="w-full h-full object-cover" />
            </button>
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
