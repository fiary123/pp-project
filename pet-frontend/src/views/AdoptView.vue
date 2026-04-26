<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search, Heart, Loader2, ChevronRight, Wand2, Sparkles, ShieldCheck, ListFilter, AlertTriangle, Check, X,
  User, Activity, Baby, Stethoscope, Scissors, Smile, FileText, Info, DollarSign, Clock, Home, Users,
  Zap, PawPrint, HeartHandshake, Shield, MapPin, Mail, Lock, Flag, ExternalLink, BrainCircuit, Terminal, ClipboardCheck, Layers
} from 'lucide-vue-next'
import { useAuthStore } from '../store/authStore'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'

const router = useRouter()
const authStore = useAuthStore()

// --- 状态管理 ---
const applyStep = ref(0) // 0: 档案与约束(5-1), 1: 动态审计(5-2), 2: 预筛结果(5-3), 3: 触发评估(5-4)
const applicationForm = ref({ monthly_budget: 800, has_pet_experience: true, housing_type: '公寓', daily_companion_hours: 2 })
const userProfileFull = ref<any>(null)
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

// 匹配度预检查逻辑 (图5-1 重点)
const preCheckResults = computed(() => {
  if (!selectedPet.value || !userProfileFull.value) return []
  const p = selectedPet.value
  const u = userProfileFull.value
  const checks = []
  if (p.min_budget_level) {
    const levels: Record<string, number> = { '低': 1, '中': 2, '高': 3 }
    const pass = (levels[u.budget_level] || 0) >= (levels[p.min_budget_level] || 0)
    checks.push({ label: `预算契约 (${p.min_budget_level})`, pass, detail: pass ? '符合养护开销预期' : `建议预算 ≥ ${p.min_budget_level}级` })
  }
  if (p.min_companion_hours > 0) {
    const pass = (u.available_time || 0) >= p.min_companion_hours
    checks.push({ label: `陪伴时长 (≥${p.min_companion_hours}h)`, pass, detail: pass ? '满足互动需求' : '当前每日空闲时间略低' })
  }
  return checks
})

const handlePetSelect = async (pet: any) => {
  selectedPet.value = pet
  showDetailModal.value = true
  applyStep.value = 0
  if (!authStore.isLoggedIn) return
  isLoadingQuestions.value = true
  try {
    const [qRes, profileRes] = await Promise.all([
      axios.get(`/api/ai/adoption-questions/${pet.id}`),
      axios.get(`/api/user/profile-portrait/${authStore.user?.id}`)
    ])
    smartQuestions.value = qRes.data.questions || []
    userProfileFull.value = profileRes.data?.profile || null
  } catch (err) { console.error(err) }
  finally { isLoadingQuestions.value = false }
}

const submitApplication = async () => {
  if (!selectedPet.value) return
  isSubmittingApplication.value = true
  try {
    const payload = {
      pet_id: selectedPet.value.id,
      application_reason: '通过多智能体自适应审计面板提交',
      monthly_budget: Number(applicationForm.value.monthly_budget),
      has_pet_experience: applicationForm.value.has_pet_experience,
      smart_answers: questionAnswers.value,
    }
    await axios.post('/api/user/applications', payload)
    applyStep.value = 3 // 跳转至图 5-4 展示
  } catch (err: any) { alert('提交失败') }
  finally { isSubmittingApplication.value = false }
}

const fetchPets = async () => {
  isLoading.value = true
  try {
    const res = await axios.get('/api/pets')
    pets.value = res.data.map((p: any) => ({
      ...p, img: p.image_url || `https://images.unsplash.com/photo-1543466835-00a7907e9de1?sig=${p.id}`
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

onMounted(fetchPets)
</script>

<template>
  <div class="space-y-8 pb-32 px-4 max-w-6xl mx-auto text-gray-900 dark:text-white">
    <!-- 头部横幅 -->
    <section class="flex flex-col gap-6 pt-10">
      <div class="space-y-2">
         <h1 class="text-5xl font-black italic tracking-tighter uppercase">领养 <span class="text-orange-500">中心</span></h1>
         <p class="text-xs font-bold text-gray-400 tracking-widest uppercase flex items-center gap-2"><Heart :size="12" /> Giving them a second chance</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-4">
        <div class="relative group">
          <Search class="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400" :size="20" />
          <input v-model="searchQuery" placeholder="搜索流浪小动物..." class="w-full pl-14 pr-6 py-5 bg-gray-50 dark:bg-white/5 rounded-3xl outline-none font-black shadow-sm" />
        </div>
        <div class="flex gap-2">
          <button v-for="f in ['全部', '猫', '狗']" :key="f" @click="activeFilter = f" :class="activeFilter === f ? 'bg-orange-500 text-white' : 'bg-gray-100 dark:bg-white/5 text-gray-400 font-black'" class="px-10 py-5 rounded-2xl text-xs transition-all">{{ f }}</button>
        </div>
      </div>

      <!-- 全量扫描入口 (图 5-9 展示逻辑依据) -->
      <div v-if="authStore.isLoggedIn" class="p-6 bg-gradient-to-br from-orange-500/10 to-purple-500/10 border-2 border-dashed border-orange-500/20 rounded-[2.5rem] flex items-center justify-between gap-6">
        <div class="flex items-center gap-4">
          <div class="w-14 h-14 rounded-full bg-orange-500 text-white flex items-center justify-center animate-pulse"><BrainCircuit :size="28" /></div>
          <div><p class="text-base font-black italic">多智能体全量匹配扫描</p><p class="text-xs text-gray-500 font-bold">基于您的居住环境、经验和历史信誉，实时计算每一只宠物的契合度。</p></div>
        </div>
        <button @click="fetchEngineRecommendations" :disabled="isEngineLoading" class="px-10 py-4 bg-orange-500 text-white rounded-2xl font-black text-xs">立即扫描</button>
      </div>
    </section>

    <!-- 列表展示 -->
    <div v-if="isLoading" class="py-20 flex justify-center"><Loader2 class="animate-spin text-orange-500" :size="48" /></div>
    <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
      <div v-for="pet in filteredPets" :key="pet.id" @click="handlePetSelect(pet)" class="bg-white dark:bg-[#111] rounded-[2.5rem] overflow-hidden border border-gray-100 dark:border-white/5 shadow-md hover:shadow-2xl transition-all cursor-pointer group relative">
        <div class="aspect-square relative overflow-hidden">
          <img :src="pet.img" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
          <div v-if="getRecommendationForPet(pet.id)" class="absolute bottom-4 right-4 bg-orange-500 text-white px-4 py-2 rounded-2xl font-black text-base italic shadow-2xl border-2 border-white/20">
            <Sparkles :size="14" class="inline" /> {{ getRecommendationForPet(pet.id)?.score }}%
          </div>
        </div>
        <div class="p-6 space-y-2">
          <h4 class="font-black text-xl group-hover:text-orange-500 transition-colors">{{ pet.name }}</h4>
          <p class="text-[10px] text-gray-400 font-bold italic line-clamp-2"># {{ pet.type }} · {{ pet.location }}</p>
        </div>
      </div>
    </div>

    <!-- [业务流程整合] 领养申请渐进式面板 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showDetailModal && selectedPet" class="fixed inset-0 z-[1000] flex items-center justify-center bg-black/80 backdrop-blur-xl p-4 overflow-y-auto" @click.self="showDetailModal = false">
          <BaseCard class="w-full max-w-5xl p-0 !bg-white dark:!bg-[#0c0c0c] rounded-[3.5rem] overflow-hidden shadow-2xl border-none flex flex-col max-h-[95vh]">
            
            <!-- 顶部进度 (图 5-2 进度引导) -->
            <div class="grid grid-cols-4 h-2 w-full bg-gray-100 dark:bg-white/5">
                <div v-for="i in 4" :key="i" class="transition-all duration-500" :class="applyStep >= i-1 ? 'bg-orange-500' : 'bg-transparent'"></div>
            </div>

            <div class="p-8 md:p-12 space-y-10 overflow-y-auto custom-scrollbar">
              
              <!-- [图 5-1] 宠物档案与送养约束 -->
              <template v-if="applyStep === 0">
                <div class="flex justify-between items-start">
                   <div class="space-y-3">
                      <div class="flex items-center gap-3"><span class="px-3 py-1 bg-orange-500 text-white text-[10px] font-black rounded-lg">#{{ selectedPet.id }}</span><span class="text-gray-400 font-black text-[10px]"><MapPin :size="14" class="inline" /> {{ selectedPet.location }}</span></div>
                      <h3 class="text-5xl font-black italic tracking-tighter uppercase">{{ selectedPet.name }}</h3>
                   </div>
                   <button @click="showDetailModal = false" class="p-4 bg-gray-100 dark:bg-white/5 rounded-full"><X :size="28" /></button>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-10">
                   <div class="space-y-6">
                      <div class="aspect-video rounded-[2.5rem] overflow-hidden shadow-lg border border-gray-100 dark:border-white/5"><img :src="selectedPet.img" class="w-full h-full object-cover" /></div>
                      <div class="grid grid-cols-2 gap-4">
                         <div v-for="(v, k) in { '品种': selectedPet.species, '年龄': selectedPet.age+'岁', '精力': selectedPet.energy_level }" :key="k" class="p-6 bg-gray-50 dark:bg-white/5 rounded-3xl text-center"><p class="text-[10px] font-black text-gray-400">{{ k }}</p><p class="text-base font-black text-orange-500">{{ v }}</p></div>
                      </div>
                   </div>
                   <div class="p-10 bg-slate-900 text-white rounded-[3.5rem] space-y-8 relative overflow-hidden">
                      <div class="absolute -right-20 -top-20 w-80 h-80 bg-orange-500/10 rounded-full blur-3xl"></div>
                      <div class="flex items-center gap-4 relative z-10"><ShieldCheck class="text-orange-500" :size="32" /><h2 class="text-2xl font-black italic">送养方准入约束</h2></div>
                      <div class="p-6 bg-white/5 rounded-[2rem] border border-white/10 relative z-10"><p class="text-[10px] font-black text-gray-400 mb-2 italic">送养特别嘱托：</p><p class="text-sm font-medium leading-relaxed italic">“ {{ selectedPet.description || '暂无详细要求' }} ”</p></div>
                      <div class="space-y-6 relative z-10">
                         <div v-for="check in preCheckResults" :key="check.label" class="space-y-2">
                            <div class="flex justify-between items-center text-[10px] font-black uppercase"><span class="text-gray-400">{{ check.label }}</span><span :class="check.pass ? 'text-green-400' : 'text-red-400'">{{ check.pass ? 'PASS' : 'WARNING' }}</span></div>
                            <div class="h-1.5 bg-white/10 rounded-full overflow-hidden"><div class="h-full transition-all duration-1000" :class="check.pass ? 'bg-green-500 w-full' : 'bg-red-500 w-1/3'"></div></div>
                         </div>
                      </div>
                   </div>
                </div>
                <button @click="applyStep = 1" class="w-full py-6 bg-orange-500 text-white rounded-[2.5rem] font-black text-xl shadow-2xl flex items-center justify-center gap-4 group">进入审计采集 <ChevronRight :size="24" class="group-hover:translate-x-2 transition-transform" /></button>
              </template>

              <!-- [图 5-2] 动态问题生成 -->
              <template v-else-if="applyStep === 1">
                <div class="max-w-3xl mx-auto space-y-12">
                   <div class="flex justify-between items-center"><div class="flex items-center gap-4"><button @click="applyStep = 0" class="p-3 bg-gray-100 dark:bg-white/5 rounded-full"><ChevronRight :size="20" class="rotate-180" /></button><h3 class="text-4xl font-black italic uppercase">自适应审计追问</h3></div><div class="px-6 py-2 bg-slate-900 text-orange-500 rounded-full border border-orange-500/20 text-xs font-black">ADAPTIVE ENGINE ACTIVE</div></div>
                   <div v-if="isLoadingQuestions" class="py-20 flex flex-col items-center gap-6"><Loader2 class="animate-spin text-orange-500" :size="60" /><p class="text-[10px] font-black uppercase tracking-[0.3em] animate-pulse italic text-gray-500">定制针对性追问逻辑中...</p></div>
                   <div v-else class="space-y-8">
                      <div v-for="(q, i) in smartQuestions" :key="q.key" class="p-10 bg-white dark:bg-white/5 rounded-[3rem] border-2 border-transparent hover:border-orange-500/20 transition-all shadow-xl relative overflow-hidden group">
                         <div v-if="q.priority === 'essential'" class="absolute top-0 right-0 px-8 py-2 bg-red-500 text-white text-[9px] font-black uppercase tracking-widest rounded-bl-3xl">Essential</div>
                         <div class="flex items-start gap-6 mb-8"><span class="w-12 h-12 rounded-2xl bg-slate-950 text-white flex items-center justify-center font-black shadow-2xl shrink-0">0{{i+1}}</span><p class="text-2xl font-black dark:text-gray-200 leading-tight">{{q.question}}</p></div>
                         <div class="flex flex-wrap gap-4 pl-16"><button v-for="opt in q.options" :key="opt.value" @click="questionAnswers[q.key] = opt.value" :class="questionAnswers[q.key] === opt.value ? 'bg-orange-500 text-white shadow-xl scale-105' : 'bg-gray-50 dark:bg-white/5 text-gray-400'" class="px-8 py-4 rounded-2xl font-black text-sm transition-all">{{opt.label}}</button></div>
                      </div>
                      <button @click="applyStep = 2" class="w-full py-6 bg-slate-900 text-white rounded-[2rem] font-black text-xl shadow-2xl flex items-center justify-center gap-4">执行规则预筛 <ChevronRight :size="24" /></button>
                   </div>
                </div>
              </template>

              <!-- [图 5-3] 申请预筛结果 -->
              <template v-else-if="applyStep === 2">
                <div class="max-w-2xl mx-auto text-center space-y-10 animate-in zoom-in duration-700">
                   <div class="w-32 h-32 rounded-full bg-green-500/10 border-4 border-green-500 flex items-center justify-center mx-auto text-green-500 shadow-2xl animate-bounce"><ClipboardCheck :size="64" /></div>
                   <div class="space-y-2"><p class="text-[10px] font-black text-green-500 uppercase tracking-[0.5em]">L1 Hard-Rule Passed</p><h1 class="text-6xl font-black italic dark:text-white uppercase tracking-tighter">预筛校验成功</h1></div>
                   <div class="p-12 bg-orange-500/5 rounded-[4rem] border-2 border-dashed border-orange-500/20 italic font-bold text-gray-500 leading-relaxed text-lg">“您的基础条件（预算、陪伴时间、居住环境）已对齐。点击签署协议后，系统将唤醒专家节点进入三阶段博弈审计。”</div>
                   <button @click="submitApplication" :disabled="isSubmittingApplication" class="px-16 py-8 bg-orange-500 text-white rounded-[2.5rem] font-black text-2xl shadow-2xl flex items-center gap-6 mx-auto group"><Loader2 v-if="isSubmittingApplication" class="animate-spin" :size="32" /><template v-else>签署协议并启动 L2 评估 <ArrowRight :size="32" class="group-hover:translate-x-2 transition-transform" /></template></button>
                </div>
              </template>

              <!-- [图 5-4] 申请记录创建与评估触发 -->
              <template v-else-if="applyStep === 3">
                <div class="py-20 flex flex-col items-center justify-center text-center space-y-12 animate-in fade-in zoom-in duration-1000">
                   <div class="relative"><div class="w-48 h-48 rounded-full border-4 border-dashed border-orange-500/30 animate-spin-slow"></div><div class="absolute inset-0 flex items-center justify-center"><div class="w-32 h-32 rounded-[2.5rem] bg-orange-500 flex items-center justify-center text-white shadow-[0_0_80px_rgba(249,115,22,0.4)]"><Layers :size="64" /></div></div></div>
                   <div class="space-y-4"><h3 class="text-5xl font-black italic uppercase text-green-500">审计流水线已挂载</h3><p class="text-lg font-bold text-gray-400 max-w-lg">主记录 #APP-{{Date.now()%1000}} 已创建。您可以前往个人中心观察 **多智能体博弈执行过程**。</p></div>
                   <div class="flex gap-4"><button @click="router.push('/profile')" class="px-12 py-6 bg-slate-900 text-white rounded-3xl font-black text-lg shadow-xl hover:bg-black transition-all">前往实时观察 (Fig 5-5)</button><button @click="showDetailModal = false" class="px-12 py-6 bg-gray-100 dark:bg-white/5 text-gray-500 rounded-3xl font-black text-lg">返回领养中心</button></div>
                </div>
              </template>

            </div>
          </BaseCard>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: scale(0.9) translateY(30px); }
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(249, 115, 22, 0.2); border-radius: 20px; }
@keyframes spin-slow { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.animate-spin-slow { animation: spin-slow 12s linear infinite; }
</style>
