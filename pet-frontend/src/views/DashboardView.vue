<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  Users, CheckCircle2, XCircle, Loader2,
  ShieldAlert, MicOff, UserX, UserCheck, ShieldCheck,
  Handshake, Flag, BarChart2, Ban, X
} from 'lucide-vue-next'
import { useAuthStore } from '../store/authStore'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'

const authStore = useAuthStore()

// 1. 状态管理
const activeMainTab = ref<'audit' | 'announcement' | 'logs' | 'users' | 'mutual_aid'>('audit')
const applications = ref<any[]>([])
const announcements = ref<any[]>([])
const moderationLogs = ref<any[]>([])
const allUsers = ref<any[]>([])
const isLoading = ref(false)

// 处罚表单
const showSanctionModal = ref(false)
const sanctionTarget = ref<any>(null)
const sanctionForm = ref({ type: 'muted' as 'muted' | 'banned', reason: '', evidence: '' })
const isSanctionSubmitting = ref(false)

// 互助监控数据
const mutualAidStats = ref<any>(null)
const mutualAidTasks = ref<any[]>([])
const mutualAidReports = ref<any[]>([])
const mutualAidTaskFilter = ref('')
const isMutualAidLoading = ref(false)
const cancellingTaskId = ref<number | null>(null)

// 仲裁弹窗
const resolveTarget = ref<any>(null)
const resolveForm = ref({ action: 'dismiss', note: '', ban_publisher: false, ban_reason: '' })
const isResolving = ref(false)

const fetchMutualAidData = async () => {
  isMutualAidLoading.value = true
  try {
    const [stats, tasks, reports] = await Promise.all([
      axios.get('/api/admin/mutual-aid/stats'),
      axios.get('/api/admin/mutual-aid/tasks', { params: { status: mutualAidTaskFilter.value, limit: 50 } }),
      axios.get('/api/admin/mutual-aid/reports', { params: { status: 'pending' } }),
    ])
    mutualAidStats.value = stats.data
    mutualAidTasks.value = tasks.data
    mutualAidReports.value = reports.data
  } finally { isMutualAidLoading.value = false }
}

const adminCancelTask = async (taskId: number) => {
  const reason = prompt('请输入下架原因：')
  if (!reason) return
  cancellingTaskId.value = taskId
  try {
    await axios.post(`/api/admin/mutual-aid/tasks/${taskId}/cancel`, { reason })
    await fetchMutualAidData()
  } finally { cancellingTaskId.value = null }
}

const openResolve = (report: any) => {
  resolveTarget.value = report
  resolveForm.value = { action: 'dismiss', note: '', ban_publisher: false, ban_reason: '' }
}

const submitResolve = async () => {
  if (!resolveTarget.value) return
  isResolving.value = true
  try {
    await axios.post(`/api/admin/mutual-aid/reports/${resolveTarget.value.id}/resolve`, resolveForm.value)
    resolveTarget.value = null
    await fetchMutualAidData()
  } finally { isResolving.value = false }
}

// 2. 数据加载
const fetchData = async () => {
  isLoading.value = true
  try {
    const [apps, notices, logs, users] = await Promise.all([
      axios.get('/api/admin/applications'),
      axios.get('/api/announcements'),
      axios.get('/api/admin/moderation/logs'),
      axios.get('/api/admin/users')
    ])
    applications.value = apps.data
    announcements.value = notices.data
    moderationLogs.value = logs.data
    allUsers.value = users.data
  } finally { isLoading.value = false }
}

const switchMainTab = (tab: typeof activeMainTab.value) => {
  activeMainTab.value = tab
  if (tab === 'mutual_aid') fetchMutualAidData()
}

// 3. 业务操作
const openSanctionModal = (user: any) => {
  sanctionTarget.value = user
  showSanctionModal.value = true
}

const handleSanction = async () => {
  if (!sanctionForm.value.reason) return
  isSanctionSubmitting.value = true
  await axios.post('/api/admin/users/sanction', {
    user_id: sanctionTarget.value.id,
    admin_id: authStore.user?.id || 0,
    ...sanctionForm.value
  })
  showSanctionModal.value = false
  sanctionForm.value = { type: 'muted', reason: '', evidence: '' }
  fetchData()
  isSanctionSubmitting.value = false
}

const reactivateUser = async (id: number) => {
  await axios.post(`/api/admin/users/reactivate?user_id=${id}`)
  fetchData()
}

// (其余审核/公告操作逻辑保持)
const handleAudit = async (appId: number, status: string) => {
  await axios.post('/api/admin/applications/update', { app_id: appId, status })
  fetchData()
}

onMounted(fetchData)
</script>

<template>
  <div class="space-y-8 pb-20 px-4">
    <!-- A. 顶部切换导航 -->
    <div class="flex flex-wrap gap-4 border-b border-white/5 pb-4">
      <button @click="switchMainTab('audit')" :class="activeMainTab === 'audit' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all">领养审核中心</button>
      <button @click="switchMainTab('announcement')" :class="activeMainTab === 'announcement' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all">全站公告发布</button>
      <button @click="switchMainTab('users')" :class="activeMainTab === 'users' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all">全站用户治理</button>
      <button @click="switchMainTab('logs')" :class="activeMainTab === 'logs' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all">内容治理日志</button>
      <button @click="switchMainTab('mutual_aid')" :class="activeMainTab === 'mutual_aid' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all flex items-center gap-1">
        <Handshake :size="12" />互助监控
        <span v-if="mutualAidStats?.pending_reports > 0" class="ml-1 px-1.5 py-0.5 bg-red-500 text-white text-[10px] font-black rounded-full">{{ mutualAidStats.pending_reports }}</span>
      </button>
    </div>

    <div v-if="isLoading" class="h-96 flex items-center justify-center">
      <Loader2 class="animate-spin text-orange-500" :size="48" />
    </div>

    <div v-else class="animate-in fade-in duration-700">
      
      <!-- 1. 用户治理中心 -->
      <div v-if="activeMainTab === 'users'" class="space-y-6">
        <div class="flex items-center justify-between mb-2">
          <h2 class="text-2xl font-black text-white flex items-center gap-3">
            <div class="p-2 bg-blue-500/10 text-blue-500 rounded-lg"><Users :size="20" /></div>
            系统用户信用列表
          </h2>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <BaseCard v-for="user in allUsers" :key="user.id" 
                    :class="user.status === 'banned' ? 'border-red-500/40 bg-red-500/5' : (user.status === 'muted' ? 'border-yellow-500/40 bg-yellow-500/5' : 'border-white/5')"
                    class="!p-6 group relative">
            
            <div class="flex items-start justify-between">
              <div class="flex gap-4">
                <div class="w-12 h-12 rounded-full border-2 border-white/10 overflow-hidden bg-white/5">
                  <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${user.username}`" />
                </div>
                <div>
                  <h4 class="font-bold text-white">{{ user.username }}</h4>
                  <p class="text-[10px] text-gray-500 font-mono">{{ user.email }}</p>
                </div>
              </div>
              
              <!-- 状态图标 -->
              <div class="p-2 rounded-lg bg-white/5">
                <UserCheck v-if="user.status === 'active'" class="text-green-500" :size="18" />
                <MicOff v-else-if="user.status === 'muted'" class="text-yellow-500" :size="18" />
                <UserX v-else class="text-red-500" :size="18" />
              </div>
            </div>

            <div class="mt-6 flex justify-between items-center pt-4 border-t border-white/5">
              <span class="text-[10px] font-black uppercase text-gray-600 tracking-widest">角色：{{ ({individual:'爱宠人士',org_admin:'救助站管理员'} as Record<string,string>)[user.role] || user.role }}</span>
              <div class="flex gap-2">
                <button v-if="user.status !== 'active'" @click="reactivateUser(user.id)" class="px-3 py-1 bg-green-500/10 text-green-500 rounded-lg text-[10px] font-bold hover:bg-green-500 hover:text-white transition-all">恢复正常</button>
                <button v-else @click="openSanctionModal(user)" class="px-3 py-1 bg-red-500/10 text-red-500 rounded-lg text-[10px] font-bold hover:bg-red-500 hover:text-white transition-all">违规处罚</button>
              </div>
            </div>
          </BaseCard>
        </div>
      </div>

      <!-- 2. 其它 Tab (略，保持逻辑) -->
      <div v-else-if="activeMainTab === 'audit'" class="space-y-4">
        <!-- 领养审核代码... -->
        <BaseCard v-for="app in applications" :key="app.id" class="!p-6 flex items-center justify-between">
          <div class="flex items-center gap-6">
            <div class="w-12 h-12 rounded-xl bg-orange-500/10 flex items-center justify-center text-orange-500"><Users :size="24"/></div>
            <div><h4 class="text-lg font-bold text-white">{{ app.user_name }}</h4><p class="text-xs text-gray-400 mt-1">理由：{{ app.reason }}</p></div>
          </div>
          <div class="flex gap-2">
            <button @click="handleAudit(app.id, '已通过')" class="p-2 bg-green-500/10 text-green-500 rounded-lg hover:bg-green-500 hover:text-white transition-all"><CheckCircle2 :size="18"/></button>
            <button @click="handleAudit(app.id, '已驳回')" class="p-2 bg-red-500/10 text-red-500 rounded-lg hover:bg-red-500 hover:text-white transition-all"><XCircle :size="18"/></button>
          </div>
        </BaseCard>
      </div>

      <div v-else-if="activeMainTab === 'logs'">
        <BaseCard v-for="log in moderationLogs" :key="log.id" class="!p-6 mb-4">
          <div class="flex justify-between items-center">
            <div class="flex items-center gap-4"><ShieldAlert class="text-red-500" /><div class="text-white font-bold">{{ log.reason }}</div></div>
            <div class="text-xs text-gray-500">{{ log.delete_time }}</div>
          </div>
        </BaseCard>
      </div>

      <!-- 5. 互助监控 -->
      <div v-else-if="activeMainTab === 'mutual_aid'" class="space-y-8">
        <div v-if="isMutualAidLoading" class="flex items-center justify-center py-20 text-gray-500">
          <Loader2 class="animate-spin mr-2" :size="24" /> 加载中...
        </div>
        <template v-else>
          <!-- 统计卡片 -->
          <div v-if="mutualAidStats" class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <BaseCard v-for="card in [
              { label: '今日新增', value: mutualAidStats.today_new, color: 'text-orange-400', icon: BarChart2 },
              { label: '接单率',   value: mutualAidStats.accept_rate + '%', color: 'text-blue-400', icon: Handshake },
              { label: '完成率',   value: mutualAidStats.complete_rate + '%', color: 'text-green-400', icon: CheckCircle2 },
              { label: '待处理举报', value: mutualAidStats.pending_reports, color: 'text-red-400', icon: Flag },
            ]" :key="card.label" class="!p-5 text-center space-y-2">
              <component :is="card.icon" :size="24" :class="[card.color, 'mx-auto']" />
              <p :class="['text-3xl font-black', card.color]">{{ card.value }}</p>
              <p class="text-xs text-gray-500 font-bold uppercase tracking-widest">{{ card.label }}</p>
            </BaseCard>
          </div>

          <!-- 举报仲裁 -->
          <div>
            <h3 class="text-lg font-black text-white flex items-center gap-2 mb-4">
              <Flag :size="18" class="text-red-400" /> 待处理举报
              <span v-if="mutualAidReports.length > 0" class="px-2 py-0.5 bg-red-500 text-white text-xs font-black rounded-full">{{ mutualAidReports.length }}</span>
            </h3>
            <div v-if="mutualAidReports.length === 0" class="text-center py-10 text-gray-600 border border-dashed border-white/5 rounded-2xl text-sm">暂无待处理举报</div>
            <BaseCard v-for="report in mutualAidReports" :key="report.id" class="mb-3 border-red-500/10">
              <div class="flex items-start justify-between gap-4">
                <div class="flex-1 space-y-1.5">
                  <div class="flex items-center gap-2 flex-wrap text-xs">
                    <span class="font-bold text-red-400 flex items-center gap-1"><Flag :size="11" />举报 #{{ report.id }}</span>
                    <span class="text-gray-500">举报人：<span class="text-white">{{ report.reporter_name }}</span></span>
                    <span class="text-gray-500">任务：<span class="text-orange-400">{{ report.task_type }} · {{ report.pet_name }}</span></span>
                    <span class="text-gray-500">发布人：<span class="text-white">{{ report.task_owner_name }}</span></span>
                  </div>
                  <p class="text-sm text-white font-medium">{{ report.reason }}</p>
                  <p class="text-xs text-gray-500">地点：{{ report.location }} · 任务状态：{{ report.task_status }}</p>
                  <p class="text-xs text-gray-600">{{ report.create_time }}</p>
                </div>
                <button @click="openResolve(report)"
                  class="shrink-0 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-xs font-bold rounded-xl transition-all">
                  处理
                </button>
              </div>
            </BaseCard>
          </div>

          <!-- 任务列表 -->
          <div>
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-black text-white flex items-center gap-2">
                <Handshake :size="18" class="text-orange-400" /> 全部互助任务
              </h3>
              <select v-model="mutualAidTaskFilter" @change="fetchMutualAidData"
                class="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white text-xs focus:outline-none focus:border-orange-500 transition-all">
                <option value="">全部状态</option>
                <option value="open">待接单</option>
                <option value="accepted">已接单</option>
                <option value="completed">已完成</option>
                <option value="cancelled">已下架</option>
              </select>
            </div>
            <div v-if="mutualAidTasks.length === 0" class="text-center py-10 text-gray-600 border border-dashed border-white/5 rounded-2xl text-sm">暂无任务数据</div>
            <BaseCard v-for="task in mutualAidTasks" :key="task.id" class="mb-3"
              :class="task.status === 'cancelled' ? 'opacity-50' : ''">
              <div class="flex items-center justify-between gap-4">
                <div class="flex-1 space-y-1 min-w-0">
                  <div class="flex items-center gap-2 flex-wrap text-xs">
                    <span class="font-bold text-orange-400">{{ task.task_type }}</span>
                    <span :class="['px-2 py-0.5 rounded-full font-bold', {
                      'bg-green-500/20 text-green-400': task.status === 'open',
                      'bg-blue-500/20 text-blue-400': task.status === 'accepted',
                      'bg-gray-500/20 text-gray-400': task.status === 'completed',
                      'bg-red-500/20 text-red-400': task.status === 'cancelled',
                    }]">{{ ({ open:'待接单', accepted:'已接单', completed:'已完成', cancelled:'已下架' } as Record<string,string>)[task.status] || task.status }}</span>
                    <span class="text-gray-500">发布人：{{ task.publisher_name }}</span>
                  </div>
                  <p class="text-white font-bold text-sm truncate">{{ task.pet_name }}（{{ task.pet_species }}）· {{ task.location }}</p>
                  <p class="text-gray-500 text-xs">{{ task.start_time }} ~ {{ task.end_time || '待定' }} · {{ task.create_time?.slice(0,10) }}</p>
                </div>
                <button v-if="task.status !== 'cancelled' && task.status !== 'completed'"
                  @click="adminCancelTask(task.id)" :disabled="cancellingTaskId === task.id"
                  class="shrink-0 flex items-center gap-1 px-3 py-2 bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white text-xs font-bold rounded-xl transition-all">
                  <Loader2 v-if="cancellingTaskId === task.id" class="animate-spin" :size="12" />
                  <Ban v-else :size="12" />下架
                </button>
              </div>
            </BaseCard>
          </div>
        </template>
      </div>

    </div>

    <!-- 举报仲裁弹窗 -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="resolveTarget" class="fixed inset-0 z-[500] flex items-center justify-center bg-black/90 backdrop-blur-md px-4" @click.self="resolveTarget = null">
          <div class="w-full max-w-lg bg-[#121212] rounded-[3rem] border border-orange-500/20 p-10 shadow-2xl space-y-6">
            <div class="flex items-center justify-between">
              <h3 class="text-xl font-black text-white flex items-center gap-2"><Flag :size="18" class="text-red-400" /> 举报仲裁</h3>
              <button @click="resolveTarget = null" class="text-gray-500 hover:text-white transition-colors"><X :size="18" /></button>
            </div>
            <div class="p-4 bg-white/5 rounded-2xl text-sm space-y-1">
              <p class="text-gray-400">举报原因：<span class="text-white font-bold">{{ resolveTarget?.reason }}</span></p>
              <p class="text-gray-400">被举报任务：<span class="text-orange-400">{{ resolveTarget?.task_type }} · {{ resolveTarget?.pet_name }}</span></p>
              <p class="text-gray-400">发布人：<span class="text-white">{{ resolveTarget?.task_owner_name }}</span></p>
            </div>
            <!-- 操作选择 -->
            <div class="grid grid-cols-2 gap-3">
              <button @click="resolveForm.action = 'dismiss'"
                :class="resolveForm.action === 'dismiss' ? 'bg-gray-500 text-white' : 'bg-white/5 text-gray-400'"
                class="py-3 rounded-2xl text-xs font-black uppercase transition-all">驳回举报</button>
              <button @click="resolveForm.action = 'cancel'"
                :class="resolveForm.action === 'cancel' ? 'bg-red-500 text-white' : 'bg-white/5 text-gray-400'"
                class="py-3 rounded-2xl text-xs font-black uppercase transition-all">下架任务</button>
            </div>
            <!-- 下架时可选封禁 -->
            <div v-if="resolveForm.action === 'cancel'" class="space-y-3">
              <label class="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" v-model="resolveForm.ban_publisher" class="w-4 h-4 accent-red-500" />
                <span class="text-sm text-gray-300 font-bold">同时封禁发布人账号</span>
              </label>
              <input v-if="resolveForm.ban_publisher" v-model="resolveForm.ban_reason"
                placeholder="封禁理由（选填）"
                class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-red-500 transition-all" />
            </div>
            <!-- 备注 -->
            <textarea v-model="resolveForm.note" rows="3" placeholder="仲裁备注（选填）"
              class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-orange-500 transition-all resize-none" />
            <div class="flex gap-4">
              <button @click="resolveTarget = null" class="flex-1 py-4 rounded-2xl bg-white/5 text-gray-400 font-bold text-sm">取消</button>
              <button @click="submitResolve" :disabled="isResolving"
                :class="resolveForm.action === 'cancel' ? 'bg-red-500 hover:bg-red-600 shadow-red-500/20' : 'bg-orange-500 hover:bg-orange-600 shadow-orange-500/20'"
                class="flex-1 py-4 rounded-2xl text-white font-black text-sm flex items-center justify-center gap-2 transition-all shadow-lg">
                <Loader2 v-if="isResolving" class="animate-spin" :size="16" />
                <template v-else>{{ resolveForm.action === 'cancel' ? '执行下架' : '驳回举报' }}</template>
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- 用户处罚存证弹窗 -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showSanctionModal" class="fixed inset-0 z-[500] flex items-center justify-center bg-black/95 backdrop-blur-md px-4">
          <div class="w-full max-w-lg bg-[#121212] rounded-[3rem] border border-red-500/30 p-10 shadow-2xl">
            <div class="text-center space-y-4 mb-8">
              <div class="w-16 h-16 bg-red-500/20 text-red-500 rounded-full flex items-center justify-center mx-auto"><ShieldCheck :size="32" /></div>
              <h3 class="text-2xl font-black text-white italic uppercase tracking-tighter">用户违规处罚</h3>
              <p class="text-xs text-gray-500">正在对用户 {{ sanctionTarget?.username }} 启动处罚存证</p>
            </div>

            <div class="space-y-6">
              <div class="grid grid-cols-2 gap-4">
                <button @click="sanctionForm.type = 'muted'" :class="sanctionForm.type === 'muted' ? 'bg-yellow-500 text-black' : 'bg-white/5 text-gray-500'" class="py-4 rounded-2xl text-xs font-black uppercase transition-all">限制发言</button>
                <button @click="sanctionForm.type = 'banned'" :class="sanctionForm.type === 'banned' ? 'bg-red-500 text-white' : 'bg-white/5 text-gray-500'" class="py-4 rounded-2xl text-xs font-black uppercase transition-all">封禁账号</button>
              </div>
              <div class="space-y-2">
                <label class="text-[10px] text-gray-500 font-bold uppercase">处罚正当理由 (必填)</label>
                <select v-model="sanctionForm.reason" class="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white outline-none">
                  <option value="广告/垃圾信息骚扰">广告/垃圾信息骚扰</option>
                  <option value="恶意辱骂/语言暴力">恶意辱骂/语言暴力</option>
                  <option value="发布虚假领养信息">发布虚假领养信息</option>
                  <option value="诱导私下交易/诈骗">诱导私下交易/诈骗</option>
                </select>
              </div>
              <textarea v-model="sanctionForm.reason" class="w-full h-24 bg-white/5 border border-white/10 rounded-xl p-4 text-white text-xs" placeholder="补充详细违规说明..."></textarea>
              
              <div class="flex gap-4">
                <button @click="showSanctionModal = false" class="flex-1 py-4 rounded-2xl bg-white/5 text-gray-400 font-bold">取消</button>
                <button @click="handleSanction" :disabled="isSanctionSubmitting" class="flex-1 py-4 rounded-2xl bg-red-500 text-white font-black flex items-center justify-center gap-2 hover:bg-red-600 transition-all shadow-lg shadow-red-500/20">
                  <Loader2 v-if="isSanctionSubmitting" class="animate-spin" />
                  <template v-else>立即执行处罚</template>
                </button>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<style scoped>
/* @reference "tailwindcss"; */
</style>
