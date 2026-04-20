<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search, Heart, Loader2, ChevronRight, Wand2, Sparkles, ShieldCheck, ListFilter, AlertTriangle, Check, X,
  User, Activity, Baby, Stethoscope, Scissors, Smile, FileText, Info, DollarSign, Clock, Home, Users,
  Zap, PawPrint, HeartHandshake, Shield, MapPin, Mail, Lock
} from 'lucide-vue-next'
import { useAuthStore } from '../store/authStore'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'

const router = useRouter()
const authStore = useAuthStore()

// --- 状态管理 ---
const applyStep = ref(0) // 0: 档案, 1: AI 追问, 2: 提交
const applicationForm = ref({ monthly_budget: 800, has_pet_experience: true })
const smartQuestions = ref<any[]>([])
const questionAnswers = ref<Record<string, string>>({})
const isLoadingQuestions = ref(false)
const isSubmittingApplication = ref(false)

const pets = ref<any[]>([])
const engineRecommendations = ref<any[]>([])
const isLoading = ref(true)
const isEngineLoading = ref(false)
const searchQuery = ref('')
const activeFilter = ref('全部')
const selectedPet = ref<any>(null)
const showDetailModal = ref(false)

// 针对选中宠物的推荐分
const getRecommendationForPet = (petId: number) => engineRecommendations.value.find(item => Number(item.pet_id) === Number(petId))

// 点击宠物卡片：开启弹窗并加载深度数据
const handlePetSelect = async (pet: any) => {
  selectedPet.value = pet
  showDetailModal.value = true
  applyStep.value = 0
  questionAnswers.value = {}

  if (!authStore.isLoggedIn) return

  isLoadingQuestions.value = true
  try {
    // 拉取 AI 针对性问题
    const res = await axios.get(`/api/ai/adoption-questions/${pet.id}`)
    smartQuestions.value = res.data.questions || []
  } catch (err) {
    console.error('加载追问失败', err)
  } finally {
    isLoadingQuestions.value = false
  }
}

const submitApplication = async () => {
  if (!selectedPet.value) return
  isSubmittingApplication.value = true
  try {
    const answerSummary = smartQuestions.value
      .filter(q => questionAnswers.value[q.key])
      .map(q => `${q.question}: ${q.options.find((o:any)=>o.value===questionAnswers.value[q.key])?.label || questionAnswers.value[q.key]}`)
      .join('\n')

    const payload = {
      pet_id: selectedPet.value.id,
      application_reason: answerSummary || '通过智能评估提交',
      monthly_budget: Number(applicationForm.value.monthly_budget),
      has_pet_experience: applicationForm.value.has_pet_experience,
      smart_answers: questionAnswers.value,
    }
    await axios.post('/api/user/applications', payload)
    window.alert(`申请已提交！系统正在进行智能审计，请前往“个人中心”查看报告。`)
    showDetailModal.value = false
    router.push('/profile')
  } catch (err: any) {
    alert(err.response?.data?.detail || '提交失败')
  } finally {
    isSubmittingApplication.value = false
  }
}

const fetchPets = async () => {
  isLoading.value = true
  try {
    const res = await axios.get('/api/pets')
    pets.value = res.data.map((p: any) => ({
      ...p,
      img: p.image_url || `https://images.unsplash.com/photo-1543466835-00a7907e9de1?sig=${p.id}`
    }))
  } catch (err) { console.error(err) }
  finally { isLoading.value = false }
}

const fetchEngineRecommendations = async () => {
  if (!authStore.isLoggedIn) return
  isEngineLoading.value = true
  try {
    const res = await axios.get(`/api/recommendation/pets/${authStore.user.id}`)
    engineRecommendations.value = res.data.results || []
  } catch (err) { console.error(err) }
  finally { isEngineLoading.value = false }
}

const filteredPets = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  return pets.value.filter(p => {
    const mK = !keyword || p.name?.toLowerCase().includes(keyword) || p.type?.toLowerCase().includes(keyword)
    const mT = activeFilter.value === '全部' || p.species === activeFilter.value
    return mK && mT
  })
})

const isAnalysisActive = ref(false)
const handleStartAnalysis = () => { isAnalysisActive.value = true; fetchEngineRecommendations(); }

onMounted(fetchPets)
</script>

<template>
  <div class="space-y-8 pb-20 px-4 max-w-6xl mx-auto text-gray-900 dark:text-white">
    <!-- 头部：搜索与 AI 开关 -->
    <section class="flex flex-col gap-6 pt-10">
      <div class="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-4">
        <div class="relative">
          <Search class="absolute left-5 top-1/2 -translate-y-1/2 text-gray-400" :size="20" />
          <input v-model="searchQuery" placeholder="搜索宠物名字、品种..." class="w-full pl-14 pr-6 py-4 bg-gray-50 dark:bg-white/5 rounded-2xl outline-none font-bold shadow-sm" />
        </div>
        <div class="flex gap-2">
          <button v-for="f in ['全部', '猫', '狗']" :key="f" @click="activeFilter = f" :class="activeFilter === f ? 'bg-orange-500 text-white shadow-lg' : 'bg-gray-100 dark:bg-white/5'" class="px-6 py-4 rounded-xl text-xs font-black transition-all">{{ f }}</button>
        </div>
      </div>

      <div v-if="authStore.isLoggedIn" class="p-4 bg-orange-500/5 border-2 border-dashed border-orange-500/20 rounded-2xl flex items-center justify-between">
        <div class="flex items-center gap-3">
          <Sparkles class="text-orange-500" :size="24" />
          <div class="hidden md:block"><p class="text-sm font-black">AI 智能匹配分析</p><p class="text-[10px] text-gray-400">一键扫描全库，获取专家点评与推荐分</p></div>
        </div>
        <button @click="handleStartAnalysis" :disabled="isEngineLoading" class="px-6 py-3 bg-orange-500 text-white rounded-xl font-bold text-xs flex items-center gap-2">
          <Loader2 v-if="isEngineLoading" class="animate-spin" :size="14" /> {{ isEngineLoading ? '分析中...' : '开启智能筛选' }}
        </button>
      </div>
    </section>

    <!-- 宠物列表网格 -->
    <div v-if="isLoading" class="py-20 flex justify-center"><Loader2 class="animate-spin text-orange-500" :size="40" /></div>
    <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
      <div v-for="pet in filteredPets" :key="pet.id" @click="handlePetSelect(pet)" class="bg-white dark:bg-[#111] rounded-2xl overflow-hidden border border-gray-100 dark:border-white/5 shadow-sm hover:shadow-xl transition-all cursor-pointer group">
        <div class="aspect-square relative">
          <img :src="pet.img" class="w-full h-full object-cover group-hover:scale-105 transition-all duration-500" />
          <div v-if="isAnalysisActive && getRecommendationForPet(pet.id)" class="absolute bottom-2 right-2 bg-orange-500 text-white px-2 py-1 rounded-lg font-black text-xs shadow-lg animate-in zoom-in-50">
            {{ getRecommendationForPet(pet.id)?.score }}
          </div>
          <div class="absolute top-2 left-2 px-2 py-0.5 bg-black/40 backdrop-blur-md text-white text-[9px] font-bold rounded">{{ pet.location }}</div>
        </div>
        <div class="p-4">
          <h4 class="font-black text-base">{{ pet.name }}</h4>
          <p class="text-[11px] text-gray-400 mt-1 line-clamp-1 italic">{{ pet.type }}</p>
        </div>
      </div>
    </div>

    <!-- 深度档案弹窗 (Modal) -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showDetailModal && selectedPet" class="fixed inset-0 z-[1000] flex items-center justify-center bg-black/80 backdrop-blur-md p-4" @click.self="showDetailModal = false">
          <BaseCard class="w-full max-w-2xl p-0 !bg-white dark:!bg-[#0f0f0f] rounded-[2.5rem] overflow-hidden shadow-2xl border-none">
            <div class="h-1.5 w-full bg-gradient-to-r from-orange-500 to-pink-500"></div>
            <div class="p-6 md:p-10 space-y-6 max-h-[90vh] overflow-y-auto custom-scrollbar">
              
              <!-- 头部 -->
              <div class="flex justify-between items-start">
                <div class="space-y-1">
                  <div class="flex items-center gap-2 text-orange-500 font-bold text-xs"><MapPin :size="14" /> {{ selectedPet.location }}</div>
                  <h3 class="text-4xl font-black italic tracking-tighter">{{ selectedPet.name }} <span class="text-sm font-bold text-gray-400 not-italic">· {{ selectedPet.age }}岁</span></h3>
                </div>
                <button @click="showDetailModal = false" class="p-2.5 bg-gray-100 dark:bg-white/5 rounded-full text-gray-400 hover:text-red-500 transition-colors"><X :size="24" /></button>
              </div>

              <!-- 宠物背景与送养原因 -->
              <div class="grid grid-cols-2 gap-4">
                <div class="p-5 bg-gray-50 dark:bg-white/5 rounded-3xl space-y-1">
                  <p class="text-[10px] font-black text-gray-400 uppercase">身世来源</p>
                  <p class="text-sm font-bold">{{ selectedPet.origin || '救助站收容' }}</p>
                </div>
                <div class="p-5 bg-gray-50 dark:bg-white/5 rounded-3xl space-y-1">
                  <p class="text-[10px] font-black text-gray-400 uppercase">送养原因</p>
                  <p class="text-sm font-bold">{{ selectedPet.adopt_reason || '寻找长期归宿' }}</p>
                </div>
              </div>

              <!-- 健康详细档案 -->
              <div class="p-6 bg-gray-50 dark:bg-white/5 rounded-[2rem] space-y-4 border border-gray-100 dark:border-white/5">
                <p class="text-xs font-black text-gray-400 flex items-center gap-2 tracking-widest"><Stethoscope :size="16" /> 深度健康/生理档案</p>
                <div class="grid grid-cols-3 gap-4 text-center">
                   <div class="space-y-1"><p class="text-[9px] text-gray-400">性别</p><p class="text-sm font-black">{{ selectedPet.feature_gender || '未知' }}</p></div>
                   <div class="space-y-1"><p class="text-[9px] text-gray-400">绝育状态</p><p class="text-sm font-black text-green-500">{{ selectedPet.sterilized ? '已绝育' : '未绝育' }}</p></div>
                   <div class="space-y-1"><p class="text-[9px] text-gray-400">健康状况</p><p class="text-sm font-black">{{ selectedPet.health_status || '健康良好' }}</p></div>
                </div>
                <div v-if="selectedPet.medical_needs" class="p-4 bg-red-500/5 rounded-2xl border border-red-500/10">
                   <p class="text-[10px] font-bold text-red-500">备注/隐藏病史：{{ selectedPet.medical_needs }}</p>
                </div>
              </div>

              <!-- 送养方联系信息 (加密逻辑) -->
              <div class="p-6 bg-slate-900 text-white rounded-[2rem] shadow-xl space-y-4">
                <p class="text-[10px] font-black text-orange-500 flex items-center gap-2 uppercase tracking-widest"><User :size="14" /> 送养人信息</p>
                <div class="flex items-center justify-between">
                   <div class="space-y-1">
                      <p class="text-base font-black">{{ selectedPet.owner_name }}</p>
                      <p class="text-xs font-bold text-gray-400 flex items-center gap-2"><Mail :size="12" /> {{ selectedPet.owner_email }}</p>
                   </div>
                   <div v-if="selectedPet.owner_contact_hidden" class="flex flex-col items-end gap-1.5">
                      <div class="px-4 py-1.5 bg-white/10 rounded-xl flex items-center gap-2 text-[10px] font-bold"><Lock :size="12" /> 联系方式加密</div>
                      <p class="text-[8px] text-gray-500 italic">领养申请通过后自动解锁</p>
                   </div>
                   <div v-else class="px-4 py-2 bg-green-500 text-white rounded-xl text-[10px] font-black animate-pulse">联系方式已解锁</div>
                </div>
              </div>

              <!-- 领养评估通道 -->
              <div class="pt-6 border-t dark:border-white/5">
                <button v-if="applyStep === 0" @click="applyStep = 1" class="w-full py-5 bg-orange-500 text-white rounded-[1.5rem] font-black text-base shadow-xl shadow-orange-500/20 active:scale-95 transition-all flex items-center justify-center gap-3">
                  <ShieldCheck :size="20" /> 开始 AI 领养评估
                </button>

                <div v-else class="space-y-8 animate-in fade-in slide-in-from-bottom-4">
                  <div v-if="isLoadingQuestions" class="py-10 flex flex-col items-center gap-3">
                    <Loader2 class="animate-spin text-orange-500" :size="32" />
                    <p class="text-xs font-bold text-gray-400">AI 专家正在分析该宠物特征并生成提问...</p>
                  </div>
                  <template v-else>
                    <!-- AI 针对性提问 -->
                    <div v-if="applyStep === 1" class="space-y-6">
                       <div class="flex items-center gap-2 text-sm font-black text-orange-500 uppercase tracking-widest"><Sparkles :size="18" /> AI 针对性追问</div>
                       <div v-for="q in smartQuestions" :key="q.key" class="space-y-3">
                          <p class="text-sm font-bold text-gray-600 dark:text-gray-300">{{ q.question }}</p>
                          <div class="flex flex-wrap gap-2">
                             <button v-for="opt in q.options" :key="opt.value" @click="questionAnswers[q.key] = opt.value" :class="questionAnswers[q.key] === opt.value ? 'bg-orange-500 text-white shadow-md' : 'bg-white dark:bg-white/5 border border-gray-100 dark:border-white/10 text-gray-500'" class="px-4 py-2 rounded-xl text-xs font-bold transition-all">{{ opt.label }}</button>
                          </div>
                       </div>
                       <button @click="applyStep = 2" class="w-full py-4 bg-slate-800 text-white rounded-2xl font-black text-sm">下一步：确认条件</button>
                    </div>
                    <!-- 量化条件确认 -->
                    <div v-if="applyStep === 2" class="space-y-6">
                       <div class="space-y-3">
                          <div class="flex justify-between text-xs font-black"><span>月均养宠预算</span><span class="text-orange-500">{{ applicationForm.monthly_budget }} 元</span></div>
                          <input type="range" v-model="applicationForm.monthly_budget" min="100" max="3000" step="50" class="w-full accent-orange-500" />
                       </div>
                       <div class="p-4 bg-orange-50 dark:bg-orange-500/5 rounded-2xl border border-orange-100 dark:border-orange-500/10">
                          <p class="text-[10px] text-orange-600 dark:text-orange-400 leading-relaxed font-bold">💡 提示：提交后，AI 将综合您的语义动机、量化能力及历史相似案例进行深度审计。结果将在个人中心实时更新。</p>
                       </div>
                       <div class="flex gap-3">
                          <button @click="applyStep = 1" class="px-6 py-4 bg-gray-100 dark:bg-white/5 rounded-2xl font-bold text-sm">上一步</button>
                          <button @click="submitApplication" :disabled="isSubmittingApplication" class="flex-1 py-4 bg-orange-500 text-white rounded-2xl font-black text-sm flex items-center justify-center gap-2 shadow-lg shadow-orange-500/20">
                            <Loader2 v-if="isSubmittingApplication" class="animate-spin" :size="18" /> 确认并提交正式申请
                          </button>
                       </div>
                    </div>
                  </template>
                </div>
              </div>

            </div>
          </BaseCard>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: scale(0.95); }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(249, 115, 22, 0.1); border-radius: 10px; }
</style>
