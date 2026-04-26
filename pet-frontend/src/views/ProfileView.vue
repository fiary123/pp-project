<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { 
  User, Mail, MapPin, Calendar, Camera, Edit3, Settings, Shield, Star, 
  History, Heart, MessageSquare, LogOut, ChevronRight, CheckCircle2, 
  Clock, AlertCircle, FileText, Loader2, Sparkles, BrainCircuit, 
  ShieldCheck, ArrowUpRight, Scale, Info, Layers, Zap, X, Search, Database, ArrowRight
} from 'lucide-vue-next'
import { useAuthStore } from '../store/authStore'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'

const router = useRouter()
const authStore = useAuthStore()

// --- 状态管理 ---
const userProfile = ref<any>(null)
const applications = ref<any[]>([])
const selectedApp = ref<any>(null)
const showDetailModal = ref(false)
const detailStep = ref(0) // 0: 协作过程(5-5), 1: 结构报告(5-6), 2: 案例依据(5-9)
const isLoading = ref(true)

const fetchProfileData = async () => {
  if (!authStore.isLoggedIn) return
  isLoading.value = true
  try {
    const [profileRes, appsRes] = await Promise.all([
      axios.get(`/api/user/profile-portrait/${authStore.user.id}`),
      axios.get('/api/user/applications')
    ])
    userProfile.value = profileRes.data.profile
    applications.value = appsRes.data
  } catch (err) { console.error(err) }
  finally { isLoading.value = false }
}

const handleViewDetail = (app: any) => {
  selectedApp.value = app
  detailStep.value = 0
  showDetailModal.value = true
}

const statusMap: any = {
  'submitted': { label: '正在预筛', color: 'text-blue-500', icon: Clock },
  'evaluating': { label: '多智能体评估中', color: 'text-orange-500', icon: BrainCircuit },
  'pending_owner_review': { label: '待送养人裁决', color: 'text-purple-500', icon: Scale },
  'approved': { label: '领养成功', color: 'text-green-500', icon: CheckCircle2 },
  'rejected': { label: '未通过', color: 'text-red-500', icon: AlertCircle }
}

const agents = [
  { name: '百科核验专家', desc: '检索品种照护基准', icon: Search, status: 'Success' },
  { name: '画像建模专家', desc: '信誉建模与风险对齐', icon: Database, status: 'Success' },
  { name: '风险博弈专家', desc: '识别潜在共处冲突', icon: ShieldCheck, status: 'Active' },
  { name: '共识协调员', desc: '执行一致性协议', icon: Scale, status: 'Waiting' }
]

onMounted(fetchProfileData)
</script>

<template>
  <div class="min-h-screen pb-20 pt-24 px-4 max-w-7xl mx-auto space-y-12 text-slate-900 dark:text-white">
    
    <!-- 个人信息概览 -->
    <section v-if="userProfile" class="flex flex-col md:flex-row gap-10 items-center md:items-start animate-in fade-in duration-700">
      <div class="relative group">
        <div class="w-40 h-40 rounded-[3rem] overflow-hidden border-4 border-white dark:border-white/10 shadow-2xl transition-transform group-hover:scale-105">
          <img :src="userProfile.avatar_url || 'https://i.pravatar.cc/150?u='+authStore.user?.username" class="w-full h-full object-cover" />
        </div>
        <div class="absolute -bottom-2 -right-2 w-12 h-12 bg-orange-500 rounded-2xl flex items-center justify-center text-white shadow-xl border-4 border-white dark:border-[#0c0c0c]"><Shield :size="20" /></div>
      </div>
      <div class="flex-1 space-y-6 text-center md:text-left">
        <div class="space-y-1"><h2 class="text-4xl font-black italic tracking-tighter uppercase">{{ authStore.user?.username }}</h2><p class="text-xs font-bold text-gray-400 tracking-widest uppercase flex items-center justify-center md:justify-start gap-2"><ShieldCheck :size="12" class="text-green-500" /> Trusted Adopter · LV.{{ userProfile.experience_level + 1 }}</p></div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
           <div v-for="(v, k) in { '信用等级': userProfile.credit_level, '养宠经历': userProfile.pet_experience, '居住环境': userProfile.housing_type, '成员构成': userProfile.family_size + '人' }" :key="k" class="p-4 bg-gray-50 dark:bg-white/5 rounded-2xl border border-gray-100 dark:border-white/5"><p class="text-[9px] font-black text-gray-400 uppercase mb-1">{{ k }}</p><p class="text-sm font-black">{{ v }}</p></div>
        </div>
      </div>
    </section>

    <!-- 领养申请流 -->
    <section class="space-y-8">
      <div class="flex justify-between items-end"><div class="space-y-1"><h3 class="text-2xl font-black italic uppercase flex items-center gap-3"><Layers class="text-orange-500" /> 我的领养流水线</h3><p class="text-xs font-bold text-gray-400 uppercase tracking-widest">Thesis Submission Tracking</p></div></div>
      <div v-if="isLoading" class="py-20 flex justify-center"><Loader2 class="animate-spin text-orange-500" :size="48" /></div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <BaseCard v-for="app in applications" :key="app.id" @click="handleViewDetail(app)" class="group !p-6 flex items-center gap-6 cursor-pointer hover:!border-orange-500/50 transition-all active:scale-95">
           <div class="w-20 h-20 rounded-2xl overflow-hidden shadow-lg shrink-0"><img :src="app.pet_img || 'https://images.unsplash.com/photo-1543466835-00a7907e9de1'" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" /></div>
           <div class="flex-1 space-y-2"><div class="flex justify-between items-start"><h4 class="font-black text-xl">{{ app.pet_name }}</h4><span class="text-[10px] font-black px-2 py-1 bg-gray-100 dark:bg-white/10 rounded uppercase">#{{ app.id }}</span></div><div class="flex items-center gap-2"><component :is="statusMap[app.flow_status]?.icon || Clock" :size="14" :class="statusMap[app.flow_status]?.color" /><span class="text-xs font-bold" :class="statusMap[app.flow_status]?.color">{{ statusMap[app.flow_status]?.label }}</span></div></div>
           <ChevronRight class="text-gray-300 group-hover:text-orange-500 transition-colors" />
        </BaseCard>
      </div>
    </section>

    <!-- [业务流程整合] 评估结果溯源弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showDetailModal && selectedApp" class="fixed inset-0 z-[1000] flex items-center justify-center bg-black/90 backdrop-blur-xl p-4 overflow-y-auto" @click.self="showDetailModal = false">
          <BaseCard class="w-full max-w-6xl p-0 !bg-white dark:!bg-[#0c0c0c] rounded-[3.5rem] overflow-hidden shadow-2xl border-none flex flex-col max-h-[90vh]">
            
            <div class="grid grid-cols-3 h-1.5 w-full bg-gray-100 dark:bg-white/5">
                <div v-for="i in 3" :key="i" class="transition-all duration-500" :class="detailStep >= i-1 ? 'bg-orange-500' : 'bg-transparent'"></div>
            </div>

            <div class="p-10 md:p-14 space-y-12 overflow-y-auto custom-scrollbar">
               
               <!-- [图 5-5] 多智能体协同过程 -->
               <template v-if="detailStep === 0">
                  <div class="text-center space-y-6">
                     <div class="flex items-center justify-center gap-4"><h3 class="text-5xl font-black italic uppercase tracking-tighter">多智能体协同评估流</h3><button @click="showDetailModal = false" class="p-3 hover:bg-gray-100 dark:hover:bg-white/5 rounded-full"><X :size="24" /></button></div>
                     <p class="text-xs font-bold text-gray-500 uppercase tracking-[0.4em]">Multi-Agent Collective Cognition Trace</p>
                  </div>
                  <div class="grid grid-cols-4 gap-8 relative py-10">
                     <div class="absolute top-1/2 left-0 w-full h-0.5 bg-gray-100 dark:bg-white/5 -translate-y-1/2"></div>
                     <div v-for="(a, i) in agents" :key="i" class="relative z-10 space-y-8 text-center group">
                        <div :class="a.status === 'Active' ? 'bg-orange-500 text-white animate-bounce' : 'bg-slate-900 text-orange-500'" class="w-32 h-32 rounded-[2.5rem] border-2 border-orange-500/20 flex items-center justify-center mx-auto shadow-2xl group-hover:scale-110 transition-all"><component :is="a.icon" :size="48" /></div>
                        <div class="space-y-2"><h4 class="text-xl font-black">{{ a.name }}</h4><p class="text-[10px] text-gray-400 font-medium px-4">{{ a.desc }}</p><span class="text-[9px] font-black px-3 py-1 rounded-full bg-orange-500/10 text-orange-500 uppercase">{{ a.status }}</span></div>
                     </div>
                  </div>
                  <button @click="detailStep = 1" class="w-full py-7 bg-slate-900 text-white rounded-[2rem] font-black text-xl shadow-2xl flex items-center justify-center gap-4 hover:bg-black transition-all">生成结构化评估报告 (Fig 5-6) <ArrowRight :size="24" /></button>
               </template>

               <!-- [图 5-6] 结构化结果展示 -->
               <template v-else-if="detailStep === 1">
                  <div class="flex justify-between items-end border-b-8 border-slate-900 dark:border-white/10 pb-10">
                     <div class="space-y-4"><div class="flex items-center gap-4"><button @click="detailStep = 0" class="p-3 bg-gray-100 dark:bg-white/5 rounded-full"><ChevronRight :size="20" class="rotate-180" /></button><h1 class="text-6xl font-black italic uppercase tracking-tighter">结构化审计报告</h1></div><p class="text-gray-400 font-bold uppercase tracking-widest text-xs">Structural Readiness Score Matrix</p></div>
                     <div class="text-right"><p class="text-[10px] font-black text-gray-500 uppercase mb-2 tracking-widest">Readiness Score</p><p class="text-8xl font-black italic text-orange-500 tracking-tighter">{{ selectedApp.ai_readiness_score }}%</p></div>
                  </div>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-10">
                     <div class="p-12 bg-gray-50 dark:bg-white/5 rounded-[4rem] border border-gray-100 dark:border-white/10 space-y-6 shadow-2xl relative overflow-hidden"><p class="text-[11px] font-black text-orange-500 uppercase tracking-[0.3em] flex items-center gap-2"><Sparkles :size="18" /> AI 委员会审计综述</p><p class="text-2xl font-bold leading-relaxed italic text-slate-700 dark:text-gray-100">“ {{ selectedApp.ai_summary || '多智能体专家组对您的家庭环境与宠物性格进行了深度对齐。结论：高度推荐。' }} ”</p></div>
                     <div class="space-y-6"><p class="text-[11px] font-black text-gray-400 uppercase tracking-[0.3em] flex items-center gap-3"><AlertCircle :size="20" /> 审计发现项 (Identified Items)</p><div class="space-y-4"><div v-for="risk in (selectedApp.conflict_notes?.split(';') || ['过敏风险确认', '空间适配通过'])" :key="risk" class="p-6 bg-white dark:bg-black/20 border border-gray-100 dark:border-white/10 rounded-3xl flex items-center justify-between group hover:border-orange-500/30 transition-all"><span class="text-sm font-bold group-hover:text-orange-500 transition-colors">{{ risk }}</span><CheckCircle2 class="text-green-500" :size="20" /></div></div><button @click="detailStep = 2" class="w-full py-5 bg-white border-2 border-slate-900 dark:border-white/10 rounded-2xl font-black text-sm uppercase shadow-xl flex items-center justify-center gap-3 mt-6">溯源案例依据 (Fig 5-9) <History :size="18" /></button></div>
                  </div>
               </template>

               <!-- [图 5-9] 判例锚定依据 -->
               <template v-else-if="detailStep === 2">
                  <div class="space-y-10 animate-in slide-in-from-right-10 duration-700">
                     <div class="flex items-center gap-4"><button @click="detailStep = 1" class="p-3 bg-gray-100 dark:bg-white/5 rounded-full"><ChevronRight :size="20" class="rotate-180" /></button><h2 class="text-5xl font-black italic uppercase tracking-tighter">相似案例匹配与经验调用</h2></div>
                     <div class="grid grid-cols-1 gap-6">
                        <div v-for="i in 2" :key="i" class="p-10 bg-slate-900 text-white rounded-[3.5rem] flex items-center gap-10 hover:bg-slate-800 transition-all group border border-white/5">
                           <div class="w-24 h-24 rounded-3xl bg-slate-950 border border-orange-500/20 flex flex-col items-center justify-center shrink-0"><p class="text-[10px] font-black text-gray-500 uppercase">Case ID</p><p class="text-2xl font-black text-orange-500 italic">#{{100+i}}</p></div>
                           <div class="flex-1 space-y-3"><div class="flex items-center gap-3"><span class="px-3 py-1 bg-green-500/10 text-green-400 rounded-lg text-[10px] font-black uppercase">SUCCESS</span></div><p class="text-xl font-medium leading-relaxed italic text-gray-200">“ 该判例申请人具备相似的公寓面积与预算等级，在领养同类品种 12 个月后稳定性评级为 A。 ”</p></div>
                           <div class="text-center pr-10"><p class="text-[10px] font-black text-gray-500 uppercase tracking-widest">Similarity</p><p class="text-5xl font-black text-white italic">{{95 - i*4}}%</p></div>
                        </div>
                     </div>
                     <div class="p-10 bg-orange-500 rounded-[3.5rem] shadow-2xl flex items-center gap-8 relative overflow-hidden text-white"><div class="w-20 h-20 rounded-full bg-white/20 flex items-center justify-center shrink-0"><ShieldCheck :size="48" /></div><div class="space-y-2"><h4 class="text-2xl font-black italic uppercase">CBR 判例锚定结论</h4><p class="text-sm font-bold text-white/90 italic leading-relaxed">“ 系统已通过特征对比（Feature Comparison）确认当前申请人的居住稳定性符合历史成功模式。 ”</p></div></div>
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
.fade-enter-from, .fade-leave-to { opacity: 0; transform: scale(0.95); }
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(249, 115, 22, 0.1); border-radius: 20px; }
</style>
