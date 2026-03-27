<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../store/authStore'
import {
  User, Shield, LogOut, KeyRound, FileText, ChevronRight, Loader2, Heart,
  MessageSquareReply, Scale, CheckCircle2, XCircle
} from 'lucide-vue-next'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'

const authStore = useAuthStore()
const activeTab = ref('info')

// 1. 状态映射
const statusMap: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: '待处理', color: 'text-gray-400', bg: 'bg-white/5' },
  pending_owner_review: { label: '待送养人审核', color: 'text-orange-400', bg: 'bg-orange-500/10' },
  approved: { label: '领养成功', color: 'text-green-400', bg: 'bg-green-500/10' },
  rejected: { label: '已拒绝', color: 'text-red-400', bg: 'bg-red-500/10' },
  probing: { label: '追问中', color: 'text-orange-300', bg: 'bg-orange-500/5' },
  human_review: { label: '待人工仲裁', color: 'text-blue-400', bg: 'bg-blue-500/10' }
}

const flowStatusMap: Record<string, { label: string; color: string; bg: string }> = {
  submitted: { label: '已提交', color: 'text-gray-300', bg: 'bg-white/5' },
  prechecked: { label: '已预筛', color: 'text-yellow-300', bg: 'bg-yellow-500/10' },
  expert_review: { label: '专家评估中', color: 'text-orange-300', bg: 'bg-orange-500/10' },
  need_more_info: { label: '等待补充信息', color: 'text-orange-400', bg: 'bg-orange-500/10' },
  waiting_publisher: { label: '等待送养方', color: 'text-blue-400', bg: 'bg-blue-500/10' },
  approved: { label: '流程通过', color: 'text-green-400', bg: 'bg-green-500/10' },
  rejected: { label: '流程驳回', color: 'text-red-400', bg: 'bg-red-500/10' },
  manual_review: { label: '进入人工复核', color: 'text-cyan-400', bg: 'bg-cyan-500/10' }
}

// 2. 密码修改
const passForm = ref({ old: '', new: '' })
const statusMsg = ref('')
const handleUpdatePassword = async () => {
  try {
    await axios.post('/api/user/change-password', {
      user_id: authStore.user.id,
      old_password: passForm.value.old,
      new_password: passForm.value.new
    })
    statusMsg.value = '密码更新成功！'
    passForm.value = { old: '', new: '' }
  } catch (err: any) {
    statusMsg.value = err.response?.data?.detail || '操作失败'
  }
}

// 3. 申请记录加载
const applications = ref<any[]>([])
const incomingApplications = ref<any[]>([])
const isLoadingApps = ref(false)

const fetchApplications = async () => {
  isLoadingApps.value = true
  try {
    const res = await axios.get(`/api/user/applications/${authStore.user?.id || 1}`)
    applications.value = res.data
  } catch (err) {
    console.error('获取记录失败')
  } finally {
    isLoadingApps.value = false
  }
}

const fetchIncomingApplications = async () => {
  isLoadingApps.value = true
  try {
    const res = await axios.get('/api/user/applications/incoming')
    incomingApplications.value = res.data
  } catch (err) {
    console.error('获取待处理申请失败')
  } finally {
    isLoadingApps.value = false
  }
}

const handleOwnerDecision = async (appId: number, status: 'approved' | 'rejected' | 'probing' | 'human_review') => {
  let promptMsg = ''
  if (status === 'approved') promptMsg = '通过备注（可选）'
  else if (status === 'rejected') promptMsg = '拒绝原因（可选）'
  else if (status === 'probing') promptMsg = '您想追问申请人什么问题？'
  else if (status === 'human_review') promptMsg = '请填写要求人工介入的理由'

  const owner_note = window.prompt(promptMsg) || ''
  if (status === 'probing' && !owner_note) return // 追问必须填内容

  try {
    await axios.post(`/api/user/applications/${appId}/owner-decision`, { status, owner_note })
    fetchIncomingApplications()
    if (activeTab.value === 'records') fetchApplications()
  } catch (err: any) {
    alert(err.response?.data?.detail || '处理失败')
  }
}

// 切换标签时加载数据
const switchTab = (tab: string) => {
  activeTab.value = tab
  if (tab === 'records') fetchApplications()
  if (tab === 'incoming') fetchIncomingApplications()
}
</script>

<template>
  <div class="max-w-5xl mx-auto space-y-8">
    <h2 class="text-3xl font-black text-white italic tracking-tighter uppercase">个人中心 / <span class="text-orange-500">{{ activeTab }}</span></h2>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-8">
      <!-- A. 左侧边栏 -->
      <BaseCard class="md:col-span-1 !p-3 flex flex-col gap-1 h-fit">
        <button @click="switchTab('info')" :class="activeTab === 'info' ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' : 'text-gray-400 hover:bg-white/5'" class="flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-bold transition-all">
          <User :size="18" /> 基本资料
        </button>
        <button @click="switchTab('records')" :class="activeTab === 'records' ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' : 'text-gray-400 hover:bg-white/5'" class="flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-bold transition-all">
          <FileText :size="18" /> 申请记录
        </button>
        <button @click="switchTab('incoming')" :class="activeTab === 'incoming' ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' : 'text-gray-400 hover:bg-white/5'" class="flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-bold transition-all">
          <Heart :size="18" /> 待我处理
        </button>
        <button @click="switchTab('security')" :class="activeTab === 'security' ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' : 'text-gray-400 hover:bg-white/5'" class="flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-bold transition-all">
          <Shield :size="18" /> 安全设置
        </button>
        
        <div class="mt-6 pt-4 border-t border-white/5">
          <button @click="authStore.logout(); $router.push('/login')" class="w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-bold text-red-400 hover:bg-red-500/10 transition-all">
            <LogOut :size="18" /> 退出账户
          </button>
        </div>
      </BaseCard>

      <!-- B. 右侧主内容 -->
      <div class="md:col-span-3 min-h-[600px]">
        <transition name="fade" mode="out-in">
          
          <!-- 1. 资料页 -->
          <div v-if="activeTab === 'info'" key="info" class="space-y-6">
            <BaseCard class="p-8">
              <div class="flex items-center gap-8 mb-10">
                <div class="w-24 h-24 rounded-full bg-orange-500/20 border-2 border-orange-500 overflow-hidden shadow-2xl">
                  <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Lucky" />
                </div>
                <div>
                  <h3 class="text-3xl font-black text-white italic">{{ authStore.user?.username }}</h3>
                  <div class="flex gap-2 mt-2">
                    <span class="px-3 py-1 bg-orange-500/10 text-orange-500 text-[10px] font-black uppercase tracking-widest rounded-full border border-orange-500/20">
                      {{ authStore.roleName }}
                    </span>
                    <span class="px-3 py-1 bg-green-500/10 text-green-500 text-[10px] font-black uppercase tracking-widest rounded-full border border-green-500/20">
                      账户正常
                    </span>
                  </div>
                </div>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div class="p-6 bg-white/5 rounded-3xl border border-white/5">
                  <p class="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-1">电子邮箱</p>
                  <p class="text-white font-medium">{{ authStore.user?.email }}</p>
                </div>
                <div class="p-6 bg-white/5 rounded-3xl border border-white/5">
                  <p class="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-1">账户唯一 ID</p>
                  <p class="text-white font-mono">UID-{{ authStore.user?.id?.toString().padStart(6, '0') }}</p>
                </div>
              </div>
            </BaseCard>
          </div>

          <!-- 2. 申请记录页 -->
          <div v-else-if="activeTab === 'records'" key="records" class="space-y-6">
            <div v-if="isLoadingApps" class="h-64 flex items-center justify-center">
              <Loader2 class="animate-spin text-orange-500" :size="48" />
            </div>
            
            <template v-else-if="applications.length > 0">
              <BaseCard v-for="app in applications" :key="app.id" class="!p-6 group hover:border-orange-500/30 transition-all cursor-pointer">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-6">
                    <div class="w-16 h-16 rounded-2xl bg-orange-500/10 flex items-center justify-center text-orange-500">
                      <Heart :size="32" />
                    </div>
                    <div>
                       <h4 class="text-xl font-bold text-white">领养申请：{{ app.pet_name || `宠物ID-${app.pet_id}` }}</h4>
                       <p class="text-xs text-gray-500 mt-1">提交时间：{{ app.create_time || app.apply_date || '刚刚' }}</p>
                       <p v-if="app.owner_name" class="text-xs text-gray-500 mt-1">送养方：{{ app.owner_name }}</p>
                     </div>
                   </div>
                   <div class="text-right">
                    <div :class="[statusMap[app.status]?.bg, statusMap[app.status]?.color]" class="px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest border border-white/5">
                      {{ statusMap[app.status]?.label || app.status || '待处理' }}
                    </div>
                    <div v-if="app.flow_status" :class="[flowStatusMap[app.flow_status]?.bg, flowStatusMap[app.flow_status]?.color]" class="mt-2 px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest border border-white/5">
                      {{ flowStatusMap[app.flow_status]?.label || app.flow_status }}
                    </div>
                    <p class="text-[10px] text-gray-600 mt-2 font-bold uppercase">查看详情 <ChevronRight class="inline" :size="12"/></p>
                  </div>
                </div>
                <div v-if="app.missing_fields || app.publisher_feedback || app.manual_review_reason" class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div v-if="app.publisher_feedback" class="p-4 rounded-2xl bg-blue-500/5 border border-blue-500/10 text-xs text-blue-200">
                    <p class="font-bold mb-1 uppercase tracking-widest">流程反馈</p>
                    {{ app.publisher_feedback }}
                  </div>
                  <div v-if="app.manual_review_reason" class="p-4 rounded-2xl bg-cyan-500/5 border border-cyan-500/10 text-xs text-cyan-200">
                    <p class="font-bold mb-1 uppercase tracking-widest">人工复核原因</p>
                    {{ app.manual_review_reason }}
                  </div>
                </div>
                <!-- 新增：向申请人展示送养方的反馈留言 -->
                <div v-if="app.owner_note" class="mt-4 p-4 rounded-2xl bg-orange-500/5 border border-orange-500/10 text-xs italic text-orange-300">
                  <p class="font-bold mb-1 uppercase tracking-tighter">送养方留言：</p>
                  "{{ app.owner_note }}"
                </div>
              </BaseCard>
            </template>

            <div v-else class="h-64 flex flex-col items-center justify-center border-2 border-dashed border-white/5 rounded-[3rem] text-gray-600 space-y-4">
              <FileText :size="48" class="opacity-20" />
              <p class="font-bold">暂无申请记录</p>
              <button @click="$router.push('/adopt')" class="text-xs text-orange-500 font-black hover:underline underline-offset-4 uppercase tracking-widest">前往寻找伙伴</button>
            </div>
          </div>

          <!-- 3. 待我处理页 (送养人视角) -->
          <div v-else-if="activeTab === 'incoming'" key="incoming" class="space-y-6">
            <div v-if="isLoadingApps" class="h-64 flex items-center justify-center">
              <Loader2 class="animate-spin text-orange-500" :size="48" />
            </div>

            <template v-else-if="incomingApplications.length > 0">
              <BaseCard v-for="app in incomingApplications" :key="app.id" class="!p-6 space-y-6">
                <!-- 头部信息 -->
                <div class="flex items-start justify-between gap-6 pb-4 border-b border-white/5">
                  <div class="flex items-center gap-6">
                    <div class="w-16 h-16 rounded-2xl bg-orange-500/10 flex items-center justify-center text-orange-500">
                      <Heart :size="32" />
                    </div>
                    <div>
                      <h4 class="text-xl font-black text-white italic tracking-tighter uppercase">{{ app.pet_name || '未知宠物' }}</h4>
                      <p class="text-xs text-gray-500 mt-1 flex items-center gap-2">申请人：<span class="text-white font-bold">{{ app.applicant_name }}</span></p>
                      <div :class="[statusMap[app.status]?.bg, statusMap[app.status]?.color]" class="inline-block mt-2 px-3 py-1 rounded-lg text-[9px] font-black uppercase border border-white/5">
                        {{ statusMap[app.status]?.label || '等待决策' }}
                      </div>
                      <div v-if="app.flow_status" :class="[flowStatusMap[app.flow_status]?.bg, flowStatusMap[app.flow_status]?.color]" class="inline-block mt-2 ml-2 px-3 py-1 rounded-lg text-[9px] font-black uppercase border border-white/5">
                        {{ flowStatusMap[app.flow_status]?.label || app.flow_status }}
                      </div>
                    </div>
                  </div>
                  <div class="text-right">
                    <p class="text-[10px] text-gray-500 font-bold uppercase mb-1">AI 准备度</p>
                    <div class="text-3xl font-black text-orange-500">{{ app.ai_readiness_score ?? 'N/A' }}</div>
                  </div>
                </div>

                <!-- 申请理由 -->
                <div class="space-y-2">
                  <p class="text-[10px] text-gray-500 font-black uppercase tracking-widest">申请人自我描述</p>
                  <div class="bg-white/5 rounded-2xl p-5 text-sm text-gray-300 whitespace-pre-wrap leading-6 border border-white/5">
                    {{ app.apply_reason }}
                  </div>
                </div>

                <div v-if="app.conflict_notes?.length || app.followup_questions?.length || app.publisher_feedback" class="grid grid-cols-1 xl:grid-cols-3 gap-4">
                  <div v-if="app.conflict_notes?.length" class="bg-red-500/5 border border-red-500/10 rounded-2xl p-5">
                    <p class="text-[10px] font-black text-red-400 uppercase tracking-widest mb-4">冲突点</p>
                    <ul class="space-y-2">
                      <li v-for="item in app.conflict_notes" :key="item" class="text-xs text-gray-300 flex items-start gap-2"><span class="text-red-500">!</span>{{ item }}</li>
                    </ul>
                  </div>
                  <div v-if="app.followup_questions?.length" class="bg-orange-500/5 border border-orange-500/10 rounded-2xl p-5">
                    <p class="text-[10px] font-black text-orange-300 uppercase tracking-widest mb-4">建议继续追问</p>
                    <ul class="space-y-2">
                      <li v-for="item in app.followup_questions" :key="item" class="text-xs text-gray-300 flex items-start gap-2"><span class="text-orange-500">?</span>{{ item }}</li>
                    </ul>
                  </div>
                  <div v-if="app.publisher_feedback" class="bg-blue-500/5 border border-blue-500/10 rounded-2xl p-5">
                    <p class="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-4">当前流程反馈</p>
                    <p class="text-xs text-gray-300 leading-6">{{ app.publisher_feedback }}</p>
                  </div>
                </div>

                <!-- AI 决策辅助决策参谋版 -->
                <div v-if="app.owner_ai_report" class="space-y-4">
                  <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
                    <div class="bg-orange-500/5 border border-orange-500/20 rounded-2xl p-5 space-y-3">
                      <p class="text-[10px] font-black text-orange-400 uppercase tracking-widest flex items-center gap-2">
                        <Scale :size="12" /> AI 决策辅助建议
                      </p>
                      <p class="text-sm text-white font-bold leading-relaxed">{{ app.owner_ai_report.applicant_summary }}</p>
                      <p class="text-xs text-orange-300/80 italic">系统建议动作：{{ app.owner_ai_report.suggested_action }}</p>
                    </div>
                    <div class="bg-white/5 border border-white/10 rounded-2xl p-5 space-y-3">
                      <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">匹配您的偏好</p>
                      <div class="flex flex-wrap gap-2">
                        <span v-if="app.pet_preferences?.focus_stability" class="px-3 py-1.5 rounded-lg bg-white/5 text-[10px] font-bold text-gray-300 border border-white/5">稳定性关注</span>
                        <span v-if="app.pet_preferences?.focus_companionship" class="px-3 py-1.5 rounded-lg bg-white/5 text-[10px] font-bold text-gray-300 border border-white/5">高陪伴要求</span>
                        <span v-if="app.pet_preferences?.allow_novice" class="px-3 py-1.5 rounded-lg bg-green-500/10 text-[10px] font-bold text-green-400 border border-green-500/20">接受新手</span>
                        <span v-else class="px-3 py-1.5 rounded-lg bg-red-500/10 text-[10px] font-bold text-red-400 border border-red-500/20">仅限熟手</span>
                      </div>
                    </div>
                  </div>

                  <!-- 三大核心分析 -->
                  <div class="grid grid-cols-1 xl:grid-cols-3 gap-4">
                    <div class="bg-green-500/5 border border-green-500/10 rounded-2xl p-5">
                      <p class="text-[10px] font-black text-green-400 uppercase tracking-widest mb-4">核心优势</p>
                      <ul class="space-y-3">
                        <li v-for="item in app.owner_ai_report.strengths" :key="item" class="text-xs text-gray-300 flex items-start gap-2"><span class="text-green-500">✓</span> {{ item }}</li>
                      </ul>
                    </div>
                    <div class="bg-red-500/5 border border-red-500/10 rounded-2xl p-5">
                      <p class="text-[10px] font-black text-red-400 uppercase tracking-widest mb-4">潜在风险</p>
                      <ul class="space-y-3">
                        <li v-for="item in app.owner_ai_report.risks" :key="item" class="text-xs text-gray-300 flex items-start gap-2"><span class="text-red-500">!</span> {{ item }}</li>
                      </ul>
                    </div>
                    <div class="bg-blue-500/5 border border-blue-500/10 rounded-2xl p-5">
                      <p class="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-4">面试建议追问</p>
                      <ul class="space-y-3">
                        <li v-for="item in app.owner_ai_report.confirm_questions" :key="item" class="text-xs text-gray-300 flex items-start gap-2"><span class="text-blue-500">?</span> {{ item }}</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <!-- 决策动作按钮组 (送养人专属) -->
                <div v-if="app.status !== 'approved' && app.status !== 'rejected'" class="flex flex-wrap gap-3 pt-4 border-t border-white/5">
                  <button @click="handleOwnerDecision(app.id, 'approved')" class="flex-1 bg-green-600 text-white py-4 rounded-2xl font-black text-sm hover:bg-green-500 transition-all flex items-center justify-center gap-2 border-b-4 border-green-800 active:border-b-0 active:translate-y-1">
                    <CheckCircle2 :size="18" /> 通过申请
                  </button>
                  <button @click="handleOwnerDecision(app.id, 'rejected')" class="flex-1 bg-red-600 text-white py-4 rounded-2xl font-black text-sm hover:bg-red-500 transition-all flex items-center justify-center gap-2 border-b-4 border-red-800 active:border-b-0 active:translate-y-1">
                    <XCircle :size="18" /> 拒绝申请
                  </button>
                  <button @click="handleOwnerDecision(app.id, 'probing')" class="flex-1 bg-orange-500 text-white py-4 rounded-2xl font-black text-sm hover:bg-orange-400 transition-all flex items-center justify-center gap-2 border-b-4 border-orange-700 active:border-b-0 active:translate-y-1">
                    <MessageSquareReply :size="18" /> 继续追问
                  </button>
                  <button @click="handleOwnerDecision(app.id, 'human_review')" class="flex-1 bg-blue-600 text-white py-4 rounded-2xl font-black text-sm hover:bg-blue-500 transition-all flex items-center justify-center gap-2 border-b-4 border-blue-800 active:border-b-0 active:translate-y-1">
                    <Scale :size="18" /> 要求人审
                  </button>
                </div>
                <!-- 已完成状态显示备注 -->
                <div v-else-if="app.owner_note" class="bg-white/5 rounded-2xl p-4 border border-white/5">
                  <p class="text-[10px] text-gray-500 font-black mb-1 uppercase tracking-widest">您的处理备注</p>
                  <p class="text-sm text-white italic">"{{ app.owner_note }}"</p>
                </div>
              </BaseCard>
            </template>

            <div v-else class="h-64 flex flex-col items-center justify-center border-2 border-dashed border-white/5 rounded-[3rem] text-gray-600 space-y-4">
              <Heart :size="48" class="opacity-20" />
              <p class="font-bold">暂无待处理申请</p>
            </div>
          </div>

          <!-- 4. 安全设置页 -->
          <div v-else-if="activeTab === 'security'" key="security" class="space-y-6">
            <BaseCard class="p-10 space-y-8">
              <div class="flex items-center gap-4 border-b border-white/5 pb-6">
                <div class="p-3 bg-orange-500 rounded-2xl text-white shadow-lg"><KeyRound :size="24" /></div>
                <h3 class="text-xl font-black text-white">账户安全中心</h3>
              </div>
              <div class="space-y-6 max-w-md">
                <div class="space-y-2">
                  <label class="text-[10px] text-gray-500 font-bold uppercase tracking-widest">当前旧密码</label>
                  <input v-model="passForm.old" type="password" class="w-full bg-white/5 border border-white/10 rounded-2xl py-4 px-6 text-white focus:border-orange-500 outline-none" />
                </div>
                <div class="space-y-2">
                  <label class="text-[10px] text-gray-500 font-bold uppercase tracking-widest">设置新密码</label>
                  <input v-model="passForm.new" type="password" class="w-full bg-white/5 border border-white/10 rounded-2xl py-4 px-6 text-white focus:border-orange-500 outline-none" />
                </div>
                <p v-if="statusMsg" class="text-xs text-orange-500 font-bold italic">{{ statusMsg }}</p>
                <button @click="handleUpdatePassword" class="w-full bg-orange-500 text-white py-4 rounded-2xl font-black shadow-xl shadow-orange-500/20 hover:bg-orange-600 transition-all">
                  确认修改
                </button>
              </div>
            </BaseCard>
          </div>

        </transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* @reference "tailwindcss"; */
.fade-enter-active, .fade-leave-active { transition: all 0.3s ease; }
.fade-enter-from { opacity: 0; transform: translateY(10px); }
.fade-leave-to { opacity: 0; transform: translateY(-10px); }
</style>
