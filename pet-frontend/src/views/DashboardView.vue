<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { 
  BarChart3, Users, Dog, FileCheck, Bell, Trash2, 
  Plus, CheckCircle2, XCircle, BrainCircuit, Loader2, Send, 
  History, ShieldAlert, ExternalLink, MicOff, UserX, UserCheck, ShieldCheck
} from 'lucide-vue-next'
import { useAuthStore } from '../store/authStore'
import BaseCard from '../components/BaseCard.vue'
import axios from 'axios'

const authStore = useAuthStore()

// 1. 状态管理
const activeMainTab = ref<'audit' | 'announcement' | 'logs' | 'users'>('audit')
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

// 2. 数据加载
const fetchData = async () => {
  isLoading.value = true
  try {
    const [apps, notices, logs, users] = await Promise.all([
      axios.get('http://127.0.0.1:8000/api/admin/applications'),
      axios.get('http://127.0.0.1:8000/api/announcements'),
      axios.get('http://127.0.0.1:8000/api/admin/moderation/logs'),
      axios.get('http://127.0.0.1:8000/api/admin/users')
    ])
    applications.value = apps.data
    announcements.value = notices.data
    moderationLogs.value = logs.data
    allUsers.value = users.data
  } finally { isLoading.value = false }
}

// 3. 业务操作
const openSanctionModal = (user: any) => {
  sanctionTarget.value = user
  showSanctionModal.value = true
}

const handleSanction = async () => {
  if (!sanctionForm.value.reason) return
  isSanctionSubmitting.value = true
  await axios.post('http://127.0.0.1:8000/api/admin/users/sanction', {
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
  await axios.post(`http://127.0.0.1:8000/api/admin/users/reactivate?user_id=${id}`)
  fetchData()
}

// (其余审核/公告操作逻辑保持)
const handleAudit = async (appId: number, status: string) => {
  await axios.post('http://127.0.0.1:8000/api/admin/applications/update', { app_id: appId, status })
  fetchData()
}

onMounted(fetchData)
</script>

<template>
  <div class="space-y-8 pb-20 px-4">
    <!-- A. 顶部切换导航 -->
    <div class="flex flex-wrap gap-4 border-b border-white/5 pb-4">
      <button @click="activeMainTab = 'audit'" :class="activeMainTab === 'audit' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all">领养审核中心</button>
      <button @click="activeMainTab = 'announcement'" :class="activeMainTab === 'announcement' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all">全站公告发布</button>
      <button @click="activeMainTab = 'users'" :class="activeMainTab === 'users' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all">全站用户治理</button>
      <button @click="activeMainTab = 'logs'" :class="activeMainTab === 'logs' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all">内容治理日志</button>
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
              <span class="text-[10px] font-black uppercase text-gray-600 tracking-widest">Role: {{ user.role }}</span>
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
        <!-- 存证日志代码已存在... -->
        <BaseCard v-for="log in moderationLogs" :key="log.id" class="!p-6 mb-4">
          <div class="flex justify-between items-center">
            <div class="flex items-center gap-4"><ShieldAlert class="text-red-500" /><div class="text-white font-bold">{{ log.reason }}</div></div>
            <div class="text-xs text-gray-500">{{ log.delete_time }}</div>
          </div>
        </BaseCard>
      </div>

    </div>

    <!-- 用户处罚存证弹窗 -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showSanctionModal" class="fixed inset-0 z-[500] flex items-center justify-center bg-black/95 backdrop-blur-md px-4">
          <div class="w-full max-w-lg bg-[#121212] rounded-[3rem] border border-red-500/30 p-10 shadow-2xl">
            <div class="text-center space-y-4 mb-8">
              <div class="w-16 h-16 bg-red-500/20 text-red-500 rounded-full flex items-center justify-center mx-auto"><ShieldCheck :size="32" /></div>
              <h3 class="text-2xl font-black text-white italic uppercase tracking-tighter">Account Enforcement</h3>
              <p class="text-xs text-gray-500">正在对用户 {{ sanctionTarget?.username }} 启动处罚存证</p>
            </div>

            <div class="space-y-6">
              <div class="grid grid-cols-2 gap-4">
                <button @click="sanctionForm.type = 'muted'" :class="sanctionForm.type === 'muted' ? 'bg-yellow-500 text-black' : 'bg-white/5 text-gray-500'" class="py-4 rounded-2xl text-xs font-black uppercase transition-all">限制发言 (MUTE)</button>
                <button @click="sanctionForm.type = 'banned'" :class="sanctionForm.type === 'banned' ? 'bg-red-500 text-white' : 'bg-white/5 text-gray-500'" class="py-4 rounded-2xl text-xs font-black uppercase transition-all">封禁账号 (BAN)</button>
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
@reference "tailwindcss";
</style>
