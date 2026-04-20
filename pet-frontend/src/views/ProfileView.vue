<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/authStore'
import {
  User, Loader2, Heart, Camera, ShieldCheck, X, CheckCircle2,
  MessageSquare, Sparkles, ListOrdered, BrainCircuit, Star, ThumbsUp, ThumbsDown, FileText,
  Home, Clock, DollarSign, BookOpen, LogOut, Info, Shield, MapPin
} from 'lucide-vue-next'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'

const router = useRouter()
const authStore = useAuthStore()

const fileInput = ref<HTMLInputElement | null>(null)
const isUploadingAvatar = ref(false)
const triggerAvatarUpload = () => fileInput.value?.click()
const onFileChange = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  isUploadingAvatar.value = true
  const formData = new FormData()
  formData.append('file', file)
  try {
    const uploadRes = await axios.post('/api/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
    await axios.post('/api/user/update-profile', { avatar_url: uploadRes.data.url })
    alert('头像更换成功！')
  } catch (err: any) { alert('上传失败') }
  finally { isUploadingAvatar.value = false }
}

const userProfile = ref<any>({ housing_type: '公寓', rental_status: '租房', available_time: 2, budget_level: '中', pet_experience: '无' })
const fetchUserProfile = async () => {
  if (!authStore.user?.id) return
  try {
    const res = await axios.get(`/api/user/profile-portrait/${authStore.user.id}`)
    if (res.data) userProfile.value = { ...userProfile.value, ...res.data.profile }
  } catch (err) { console.error('加载画像失败', err) }
}

const applications = ref<any[]>([])
const incomingApplications = ref<any[]>([])
const isLoading = ref(false)
const selectedApp = ref<any>(null)
const showAppDetail = ref(false)

const flowStatusConfig: Record<string, { label: string; color: string; bg: string; step: number }> = {
  submitted: { label: '已提交', color: 'text-gray-400', bg: 'bg-gray-500/10', step: 1 },
  evaluating: { label: 'AI 审计中', color: 'text-purple-400', bg: 'bg-purple-500/10', step: 2 },
  need_more_info: { label: '待补充资料', color: 'text-orange-400', bg: 'bg-orange-500/10', step: 3 },
  waiting_publisher: { label: '待送养人审核', color: 'text-blue-400', bg: 'bg-blue-500/10', step: 4 },
  manual_review: { label: '人工复核', color: 'text-pink-400', bg: 'bg-pink-500/10', step: 4 },
  approved: { label: '申请已通过', color: 'text-green-400', bg: 'bg-green-500/10', step: 5 },
  rejected: { label: '申请已驳回', color: 'text-red-400', bg: 'bg-red-500/10', step: 5 },
  adopted: { label: '已领养回家', color: 'text-teal-400', bg: 'bg-teal-500/10', step: 6 },
  followup_completed: { label: '评估闭环完成', color: 'text-indigo-400', bg: 'bg-indigo-500/10', step: 6 },
}

const eventTypeMap: Record<string, string> = {
  SUBMIT_APPLICATION: '提交领养申请',
  START_EVALUATION: '启动 AI 自动审计',
  FINISH_EVALUATION: 'AI 审计任务完成',
  OWNER_DECISION: '送养人裁决',
  CONFIRM_ADOPTION: '确认接回宠物',
  SUBMIT_FEEDBACK: '提交回访反馈',
}

const getAppProgress = (app: any) => {
  const status = app.flow_status || app.status || 'submitted'
  return ((flowStatusConfig[status]?.step || 1) / 6) * 100
}

const openAppDetail = async (app: any) => {
  isLoading.value = true
  try {
    const res = await axios.get(`/api/user/applications/${app.id}/detail`)
    selectedApp.value = res.data
    showAppDetail.value = true
    showFeedbackForm.value = false
    if (selectedApp.value.ai_review) {
      const outputs = selectedApp.value.ai_review.agent_outputs_json || {}
      selectedApp.value._dimension_scores = outputs.dimension_scores || []
    }
  } catch (err) { alert('详情加载失败') }
  finally { isLoading.value = false }
}

const isOwnerOfSelectedApp = computed(() => selectedApp.value?.pet_owner_id === authStore.user?.id)
const ownerDecisionForm = ref({ status: 'approved' as any, owner_note: '' })
const isSubmittingDecision = ref(false)
const submitOwnerDecision = async () => {
  if (!selectedApp.value) return
  isSubmittingDecision.value = true
  try {
    await axios.post(`/api/user/applications/${selectedApp.value.id}/owner-decision`, ownerDecisionForm.value)
    alert('裁决提交成功')
    showAppDetail.value = false
    fetchData()
  } catch (err) { alert('提交失败') }
  finally { isSubmittingDecision.value = false }
}

const isConfirmingAdoption = ref(false)
const handleConfirmAdoption = async () => {
  if (!selectedApp.value) return
  isConfirmingAdoption.value = true
  try {
    await axios.post(`/api/user/applications/${selectedApp.value.id}/confirm-adoption`)
    alert('领养确认成功！')
    showAppDetail.value = false
    fetchData()
  } catch (err) { alert('确认失败') }
  finally { isConfirmingAdoption.value = false }
}

const showFeedbackForm = ref(false)
const feedbackForm = ref({ overall_satisfaction: 5, bond_level: 'close' as any, free_feedback: '', would_recommend: true })
const isSubmittingFeedback = ref(false)
const submitFeedback = async () => {
  if (!selectedApp.value) return
  isSubmittingFeedback.value = true
  try {
    await axios.post(`/api/user/applications/${selectedApp.value.id}/feedback`, feedbackForm.value)
    alert('反馈已提交')
    showAppDetail.value = false
    showFeedbackForm.value = false
    fetchData()
  } catch (err) { alert('提交失败') }
  finally { isSubmittingFeedback.value = false }
}

const fetchData = async () => {
  if (!authStore.isLoggedIn) return
  isLoading.value = true
  try {
    const [res1, res2] = await Promise.all([
      axios.get(`/api/user/applications/${authStore.user?.id}`),
      axios.get('/api/user/applications/incoming')
    ])
    applications.value = Array.isArray(res1.data) ? res1.data : []
    incomingApplications.value = Array.isArray(res2.data) ? res2.data : []
  } catch (err) { console.error('加载失败:', err) }
  finally { isLoading.value = false }
}

onMounted(() => { fetchData(); fetchUserProfile(); })
</script>

<template>
  <div class="profile-view max-w-4xl mx-auto space-y-6 pb-20 px-4 pt-8 bg-white dark:bg-transparent text-gray-900 dark:text-white transition-colors">
    <!-- 个人名片区 -->
    <BaseCard class="p-6 border-none shadow-md !bg-gray-50 dark:!bg-white/5 flex items-center gap-6 rounded-3xl">
      <div @click="triggerAvatarUpload" class="group relative w-16 h-16 rounded-full border-2 border-orange-500 overflow-hidden shrink-0 cursor-pointer">
        <img :src="authStore.user?.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${authStore.user?.username}`" class="w-full h-full object-cover" />
        <input ref="fileInput" type="file" class="hidden" @change="onFileChange" />
      </div>
      <div class="flex-1 min-0">
        <div class="flex items-center gap-3">
          <h1 class="text-xl font-black truncate">{{ authStore.user?.username }}</h1>
          <span class="px-2 py-0.5 bg-orange-500 text-white text-[9px] font-bold rounded-md shrink-0">用户中心</span>
        </div>
        <div class="flex flex-wrap gap-2 mt-2">
          <span v-for="tag in [userProfile.housing_type, userProfile.budget_level + '预算', userProfile.pet_experience + '经验']" :key="tag" class="text-[9px] text-gray-400 font-bold px-2 py-0.5 bg-white dark:bg-white/10 rounded-md border border-gray-100 dark:border-white/5">{{ tag }}</span>
        </div>
      </div>
      <div class="flex gap-2 shrink-0">
        <button @click="$router.push('/chat')" class="p-2.5 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-all"><MessageSquare :size="18" /></button>
        <button @click="authStore.logout(); $router.push('/login')" class="p-2.5 bg-gray-200 dark:bg-white/10 text-gray-500 dark:text-gray-300 rounded-xl hover:bg-red-500 hover:text-white transition-all"><LogOut :size="18" /></button>
      </div>
    </BaseCard>

    <div class="space-y-8">
      <!-- 领养进度 -->
      <section class="space-y-4">
        <h2 class="text-sm font-black flex items-center gap-2 text-gray-500 dark:text-gray-400 uppercase tracking-widest"><Heart :size="16" /> 我发起的领养记录</h2>
        <div v-if="isLoading" class="py-10 flex justify-center"><Loader2 class="animate-spin text-orange-500" /></div>
        <div v-else-if="applications.length === 0" class="p-12 text-center text-xs text-gray-400 bg-gray-50 dark:bg-white/5 rounded-3xl border-2 border-dashed border-gray-100 dark:border-white/5">暂无申请记录</div>
        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <BaseCard v-for="app in applications" :key="app.id" @click="openAppDetail(app)" class="p-4 flex flex-col gap-3 cursor-pointer hover:border-orange-500 border-2 border-transparent transition-all shadow-sm">
            <div class="flex justify-between items-start">
              <div>
                <h4 class="text-sm font-bold">领养：{{ app.pet_name }}</h4>
                <p class="text-[10px] text-gray-400 mt-1">送养人：{{ app.owner_name }}</p>
              </div>
              <span class="text-[10px] font-black" :class="flowStatusConfig[app.flow_status || app.status]?.color">{{ flowStatusConfig[app.flow_status || app.status]?.label }}</span>
            </div>
            <div class="h-1 bg-gray-100 dark:bg-white/10 rounded-full overflow-hidden">
              <div class="h-full bg-orange-500 transition-all duration-700" :style="{ width: `${getAppProgress(app)}%` }"></div>
            </div>
          </BaseCard>
        </div>
      </section>

      <!-- 审核任务 -->
      <section v-if="incomingApplications.length > 0" class="space-y-4">
        <h2 class="text-sm font-black flex items-center gap-2 text-gray-500 dark:text-gray-400 uppercase tracking-widest"><ShieldCheck :size="16" /> 我收到的领养申请</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <BaseCard v-for="app in incomingApplications" :key="app.id" @click="openAppDetail(app)" class="p-4 flex items-center justify-between cursor-pointer hover:border-blue-500 border-2 border-transparent transition-all shadow-sm">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-blue-500 text-white flex items-center justify-center font-bold text-xs italic">!</div>
              <div>
                <h4 class="text-sm font-bold">{{ app.applicant_name }} 申请 {{ app.pet_name }}</h4>
                <p class="text-[9px] text-gray-400 mt-0.5">{{ app.create_time }}</p>
              </div>
            </div>
            <span class="px-2 py-1 bg-blue-50 dark:bg-blue-500/10 text-blue-500 text-[9px] font-bold rounded-md">待审核</span>
          </BaseCard>
        </div>
      </section>
    </div>

    <!-- 详情弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showAppDetail && selectedApp" class="fixed inset-0 z-[1000] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" @click.self="showAppDetail = false">
          <BaseCard class="w-full max-w-2xl p-0 !bg-white dark:!bg-[#0f0f0f] rounded-[2rem] overflow-hidden shadow-2xl border-none flex flex-col max-h-[90vh]">
            <div class="h-1 w-full bg-gradient-to-r from-orange-500 to-pink-500"></div>
            <div class="p-6 md:p-8 space-y-6 overflow-y-auto custom-scrollbar">
              <div class="flex justify-between items-center">
                <h3 class="text-xl font-black">{{ isOwnerOfSelectedApp ? '申请人详细背景' : '领养审计详情' }}</h3>
                <button @click="showAppDetail = false" class="text-gray-400 hover:text-gray-600 transition-colors"><X :size="20" /></button>
              </div>

              <!-- [送养人视角]：领养人详细档案 -->
              <div v-if="isOwnerOfSelectedApp" class="space-y-6">
                 <!-- 1. 领养人基础名片 -->
                 <div class="p-4 bg-gray-50 dark:bg-white/5 rounded-3xl flex items-center gap-4">
                    <img :src="selectedApp.applicant_user?.avatar_url || 'https://i.pravatar.cc/100'" class="w-12 h-12 rounded-full border-2 border-orange-500" />
                    <div>
                       <p class="text-sm font-black">{{ selectedApp.applicant_user?.username }}</p>
                       <p class="text-[10px] text-gray-400 font-bold">{{ selectedApp.applicant_user?.email }}</p>
                    </div>
                 </div>

                 <!-- 2. 画像核心指标 -->
                 <div v-if="selectedApp.applicant_profile" class="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div class="p-3 bg-white dark:bg-black/20 rounded-2xl border border-gray-100 dark:border-white/5 text-center">
                       <p class="text-[8px] font-bold text-gray-400 uppercase mb-1">居住环境</p>
                       <p class="text-xs font-black text-orange-500">{{ selectedApp.applicant_profile.housing_type }}</p>
                    </div>
                    <div class="p-3 bg-white dark:bg-black/20 rounded-2xl border border-gray-100 dark:border-white/5 text-center">
                       <p class="text-[8px] font-bold text-gray-400 uppercase mb-1">养宠经验</p>
                       <p class="text-xs font-black text-orange-500">{{ selectedApp.applicant_profile.pet_experience }}</p>
                    </div>
                    <div class="p-3 bg-white dark:bg-black/20 rounded-2xl border border-gray-100 dark:border-white/5 text-center">
                       <p class="text-[8px] font-bold text-gray-400 uppercase mb-1">月均预算</p>
                       <p class="text-xs font-black text-orange-500">{{ selectedApp.applicant_profile.budget_level }}</p>
                    </div>
                    <div class="p-3 bg-white dark:bg-black/20 rounded-2xl border border-gray-100 dark:border-white/5 text-center">
                       <p class="text-[8px] font-bold text-gray-400 uppercase mb-1">每日陪伴</p>
                       <p class="text-xs font-black text-orange-500">{{ selectedApp.applicant_profile.available_time }}h</p>
                    </div>
                 </div>

                 <!-- 3. 详细填写内容 -->
                 <div class="space-y-4">
                    <div class="space-y-2">
                       <h5 class="text-[10px] font-bold text-gray-400 flex items-center gap-2 tracking-widest uppercase"><FileText :size="12" /> 申请人填写的详细内容</h5>
                       <div class="p-4 bg-orange-50/50 dark:bg-orange-500/5 rounded-2xl border border-orange-100 dark:border-orange-500/10">
                          <p class="text-xs text-gray-600 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">{{ selectedApp.apply_reason || '未填写理由' }}</p>
                       </div>
                    </div>
                    <!-- 其他画像细节 -->
                    <div class="grid grid-cols-2 gap-4">
                       <div class="flex items-center justify-between p-3 border-b border-gray-100 dark:border-white/5">
                          <span class="text-[10px] font-bold text-gray-400">家中有无幼儿</span>
                          <span class="text-xs font-black">{{ selectedApp.applicant_profile?.has_children ? '有' : '无' }}</span>
                       </div>
                       <div class="flex items-center justify-between p-3 border-b border-gray-100 dark:border-white/5">
                          <span class="text-[10px] font-bold text-gray-400">家中有无宠物</span>
                          <span class="text-xs font-black">{{ selectedApp.applicant_profile?.has_other_pets ? '有' : '无' }}</span>
                       </div>
                    </div>
                 </div>
              </div>

              <!-- AI 审计摘要 (通用) -->
              <div class="space-y-2">
                <h5 class="text-[10px] font-bold text-gray-400 flex items-center gap-2 tracking-widest uppercase"><Shield :size="12" /> AI 智能审计摘要</h5>
                <div class="p-4 bg-gray-50 dark:bg-white/5 rounded-2xl text-xs leading-relaxed italic text-gray-600 dark:text-gray-300 border-l-4 border-orange-500">
                   {{ selectedApp.ai_summary || 'AI 正在分析领养人资质，请稍后...' }}
                </div>
              </div>

              <!-- 操作区 -->
              <div class="pt-4 space-y-3">
                 <div v-if="isOwnerOfSelectedApp && selectedApp.flow_status === 'waiting_publisher'" class="space-y-4">
                    <div class="p-4 bg-slate-900 rounded-3xl space-y-4">
                       <p class="text-[10px] font-black text-orange-500 uppercase tracking-widest">送养人裁决工作台</p>
                       <textarea v-model="ownerDecisionForm.owner_note" rows="2" placeholder="输入审核理由或对领养人的建议..." class="w-full p-3 bg-white/5 border border-white/10 rounded-xl text-xs outline-none text-white"></textarea>
                       <div class="grid grid-cols-2 gap-3">
                          <button @click="ownerDecisionForm.status = 'approved'" :class="ownerDecisionForm.status === 'approved' ? 'bg-green-500 text-white' : 'bg-white/5 text-gray-400'" class="py-3 rounded-xl text-xs font-black transition-all">通过申请</button>
                          <button @click="ownerDecisionForm.status = 'rejected'" :class="ownerDecisionForm.status === 'rejected' ? 'bg-red-500 text-white' : 'bg-white/5 text-gray-400'" class="py-3 rounded-xl text-xs font-black transition-all">驳回申请</button>
                       </div>
                       <button @click="submitOwnerDecision" :disabled="isSubmittingDecision" class="w-full py-4 bg-orange-500 text-white rounded-xl font-black text-sm shadow-lg flex items-center justify-center gap-2">
                          <Loader2 v-if="isSubmittingDecision" class="animate-spin" :size="18" /> 提交最终决策并发送邮件
                       </button>
                    </div>
                 </div>
                 <button @click="showAppDetail = false" class="w-full py-3 bg-gray-100 dark:bg-white/5 text-gray-400 rounded-xl text-xs font-bold transition-all hover:bg-gray-200">返回控制台</button>
              </div>
            </div>
          </BaseCard>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(10px); }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(249, 115, 22, 0.1); border-radius: 10px; }
</style>
