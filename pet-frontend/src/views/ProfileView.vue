<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../store/authStore'
import {
  User, LogOut, Loader2, Heart, Camera, ShieldCheck, Mail, X, CheckCircle2, MessageSquare
} from 'lucide-vue-next'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'

const authStore = useAuthStore()

// 1. 头像上传逻辑
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
    const updateRes = await axios.post('/api/user/update-profile', { avatar_url: uploadRes.data.url })
    authStore.login(updateRes.data.user, authStore.token || '')
    alert('头像更换成功！')
  } catch (err: any) { alert('上传失败') } finally { isUploadingAvatar.value = false }
}

// 2. 密码修改逻辑
const passForm = ref({ old: '', new: '', code: '' })
const isSendingCode = ref(false)
const countdown = ref(0)
const passStatus = ref('')

const sendPassCode = async () => {
  isSendingCode.value = true
  try {
    await axios.post('/api/send-code', { email: authStore.user?.email })
    alert('验证码已发送至您的注册邮箱')
    countdown.value = 60
    const timer = setInterval(() => { countdown.value--; if (countdown.value <= 0) clearInterval(timer) }, 1000)
  } catch (err: any) { alert('发送失败') } finally { isSendingCode.value = false }
}

const handleUpdatePassword = async () => {
  if (!passForm.value.code) return alert('请输入验证码')
  try {
    await axios.post('/api/user/change-password', {
      user_id: authStore.user.id,
      old_password: passForm.value.old,
      new_password: passForm.value.new,
      code: passForm.value.code
    })
    passStatus.value = '密码更新成功！'
    passForm.value = { old: '', new: '', code: '' }
  } catch (err: any) { passStatus.value = err.response?.data?.detail || '修改失败' }
}

// 3. 数据加载 (增强版)
const applications = ref<any[]>([])
const incomingApplications = ref<any[]>([])
const isLoading = ref(false)
const selectedApp = ref<any>(null)
const showAppDetail = ref(false)

const fetchData = async () => {
  if (!authStore.isLoggedIn) return;
  isLoading.value = true;
  
  // 独立请求，互不影响
  try {
    const res = await axios.get(`/api/user/applications/${authStore.user?.id}`);
    applications.value = Array.isArray(res.data) ? res.data : [];
  } catch (err) {
    console.error('加载我的申请失败:', err);
  }

  try {
    const res = await axios.get('/api/user/applications/incoming');
    incomingApplications.value = Array.isArray(res.data) ? res.data : [];
  } catch (err) {
    console.error('加载收到的申请失败:', err);
  }
  
  isLoading.value = false;
}

// 状态映射
const statusConfig: Record<string, { label: string; color: string; bg: string; step: number; desc: string }> = {
  pending: { label: 'AI 审计中', color: 'text-blue-400', bg: 'bg-blue-500/10', step: 1, desc: 'AI 正在分析您的领养资质与宠物契合度...' },
  pending_owner_review: { label: '待人工复核', color: 'text-orange-400', bg: 'bg-orange-500/10', step: 2, desc: 'AI 已完成初步评估，正等待送养方查看报告。' },
  approved: { label: '审核通过', color: 'text-green-400', bg: 'bg-green-500/10', step: 4, desc: '恭喜！您的领养申请已获得批准。' },
  rejected: { label: '申请驳回', color: 'text-red-400', bg: 'bg-red-500/10', step: 4, desc: '抱歉，此次申请未通过，建议查看 AI 评估建议。' },
  signed: { label: '已签协议', color: 'text-indigo-400', bg: 'bg-indigo-500/10', step: 5, desc: '领养协议已签署，手续已完成。' },
  followup: { label: '回访中', color: 'text-teal-400', bg: 'bg-teal-500/10', step: 6, desc: '领养后的定期幸福回访进行中。' }
}

const getAppProgress = (status: string) => {
  const step = statusConfig[status]?.step || 1
  return (step / 6) * 100
}

const openAppDetail = (app: any) => {
  selectedApp.value = app
  showAppDetail.value = true
}

const handleOwnerDecision = async (appId: number, status: string) => {
  const note = window.prompt('备注信息（可选）：') || ''
  try {
    await axios.post(`/api/user/applications/${appId}/owner-decision`, { status, owner_note: note })
    fetchData()
  } catch (err) {
    alert('处理失败');
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="profile-view max-w-4xl mx-auto space-y-12 pb-32 px-4 pt-10 transition-colors duration-500 bg-white dark:bg-transparent">
    
    <!-- 1. 顶部标题 -->
    <div class="text-center md:text-left space-y-2">
      <h1 class="text-5xl md:text-6xl font-black text-gray-900 dark:text-white italic tracking-tighter uppercase">Personal Center</h1>
      <p class="text-xl text-gray-500 dark:text-gray-400 font-bold">管理您的资料、申请与安全设置</p>
    </div>

    <!-- 2. 基本资料 -->
    <section class="space-y-6">
      <div class="flex items-center gap-3 text-2xl font-black text-gray-900 dark:text-white italic">
        <User class="text-orange-500" :size="28" /> 基本信息
      </div>
      <BaseCard class="p-8 md:p-12 shadow-2xl">
        <div class="flex flex-col md:flex-row items-center gap-10">
          <div @click="triggerAvatarUpload" 
               class="group relative w-32 h-24 md:w-40 md:h-40 rounded-full bg-orange-500/10 border-4 border-orange-500 overflow-hidden shadow-2xl cursor-pointer">
            <img :src="authStore.user?.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${authStore.user?.username}`" 
                 class="w-full h-full object-cover transition-transform group-hover:scale-110" />
            <div class="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              <Camera v-if="!isUploadingAvatar" class="text-white" :size="32" />
              <Loader2 v-else class="text-white animate-spin" :size="32" />
            </div>
            <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFileChange" />
          </div>
          <div class="flex-1 text-center md:text-left space-y-4">
            <h3 class="text-4xl font-black text-gray-900 dark:text-white">{{ authStore.user?.username }}</h3>
            <div class="flex flex-wrap justify-center md:justify-start gap-3">
              <span class="px-4 py-1.5 bg-orange-500/10 text-orange-500 text-xs font-black uppercase tracking-widest rounded-full border border-orange-500/20">{{ authStore.roleName }}</span>
              <span class="px-4 py-1.5 bg-green-500/10 text-green-600 text-xs font-black uppercase tracking-widest rounded-full border border-green-500/20">账户活跃</span>
            </div>
            <p class="text-gray-500 text-lg font-medium">{{ authStore.user?.email }}</p>
          </div>
          <div class="flex flex-col gap-3 min-w-[160px]">
            <button @click="$router.push('/chat')" class="px-8 py-4 bg-orange-500 text-white rounded-2xl font-black hover:bg-orange-600 transition-all flex items-center justify-center gap-2 shadow-lg shadow-orange-500/20">
              <MessageSquare :size="20" /> 私信中心
            </button>
            <button @click="authStore.logout(); $router.push('/login')" class="px-8 py-4 bg-red-500/10 text-red-500 rounded-2xl font-black hover:bg-red-500 hover:text-white transition-all flex items-center justify-center gap-2">
              <LogOut :size="20" /> 退出登录
            </button>
          </div>
        </div>
      </BaseCard>
    </section>

    <!-- 3. 安全设置 -->
    <section class="space-y-6">
      <div class="flex items-center gap-3 text-2xl font-black text-gray-900 dark:text-white italic">
        <ShieldCheck class="text-blue-500" :size="28" /> 安全校验修改
      </div>
      <BaseCard class="p-8 md:p-12">
        <div class="max-w-2xl space-y-8">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="space-y-3">
              <label class="text-xs font-black text-gray-400 uppercase tracking-widest ml-2">当前旧密码</label>
              <input v-model="passForm.old" type="password" placeholder="验证身份" class="w-full bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl py-5 px-6 text-gray-900 dark:text-white text-lg focus:border-orange-500 outline-none transition-all" />
            </div>
            <div class="space-y-3">
              <label class="text-xs font-black text-gray-400 uppercase tracking-widest ml-2">设置新密码</label>
              <input v-model="passForm.new" type="password" placeholder="输入新密码" class="w-full bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl py-5 px-6 text-gray-900 dark:text-white text-lg focus:border-orange-500 outline-none transition-all" />
            </div>
          </div>
          
          <div class="space-y-3">
            <label class="text-xs font-black text-gray-400 uppercase tracking-widest ml-2">邮箱验证码 (发送至 {{ authStore.user?.email }})</label>
            <div class="flex gap-4">
              <input v-model="passForm.code" type="text" placeholder="6位数字" class="flex-1 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl py-5 px-6 text-gray-900 dark:text-white text-lg outline-none focus:border-orange-500 transition-all" />
              <button @click="sendPassCode" :disabled="isSendingCode || countdown > 0" class="px-8 rounded-2xl bg-blue-500 text-white font-black text-sm uppercase hover:bg-blue-600 disabled:opacity-50 transition-all min-w-[140px]">
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </button>
            </div>
          </div>

          <div v-if="passStatus" class="p-4 rounded-xl bg-orange-500/10 text-orange-500 font-bold italic">{{ passStatus }}</div>
          
          <button @click="handleUpdatePassword" class="w-full py-5 bg-gray-900 dark:bg-white text-white dark:text-black rounded-2xl font-black text-lg shadow-2xl hover:scale-[1.02] transition-all">
            保存新密码并重新加密
          </button>
        </div>
      </BaseCard>
    </section>

    <!-- 4. 我的领养申请 -->
    <section class="space-y-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3 text-2xl font-black text-gray-900 dark:text-white italic">
          <Heart class="text-pink-500" :size="28" /> 我的领养申请
        </div>
        <span class="text-sm font-bold text-gray-400">{{ applications.length }} 条记录</span>
      </div>
      <div v-if="isLoading" class="py-20 flex justify-center"><Loader2 class="animate-spin text-orange-500" :size="48" /></div>
      <div v-else class="grid grid-cols-1 gap-6">
        <BaseCard v-for="app in applications" :key="app.id" @click="openAppDetail(app)" class="p-6 md:p-8 space-y-6 cursor-pointer hover:border-orange-500 transition-all group">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div class="flex items-center gap-6">
              <div class="w-16 h-16 rounded-2xl bg-orange-500/10 flex items-center justify-center text-orange-500 font-black text-2xl italic group-hover:scale-110 transition-transform">#{{ app.pet_id }}</div>
              <div>
                <h4 class="text-2xl font-black text-gray-900 dark:text-white">领养：{{ app.pet_name || '宠物' }}</h4>
                <p class="text-gray-500 font-bold italic mt-1">送养方：{{ app.owner_name || '系统' }} · {{ app.create_time }}</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <div class="text-right hidden md:block">
                <p class="text-[10px] text-gray-400 font-black uppercase">AI 匹配分</p>
                <p class="text-xl font-black text-orange-500">{{ app.ai_readiness_score || '审议中' }}</p>
              </div>
              <div :class="[statusConfig[app.status]?.bg, statusConfig[app.status]?.color]" class="px-6 py-2 rounded-xl font-black text-sm border border-gray-200 dark:border-white/5 uppercase tracking-widest">
                {{ statusConfig[app.status]?.label || '处理中' }}
              </div>
            </div>
          </div>

          <!-- 进度条 -->
          <div class="space-y-2">
            <div class="flex justify-between text-[10px] font-black uppercase tracking-widest text-gray-400">
              <span>申请进度</span>
              <span>{{ Math.round(getAppProgress(app.status)) }}%</span>
            </div>
            <div class="h-3 bg-gray-100 dark:bg-white/5 rounded-full overflow-hidden">
              <div class="h-full bg-gradient-to-r from-orange-500 to-pink-500 transition-all duration-1000 ease-out" :style="{ width: `${getAppProgress(app.status)}%` }"></div>
            </div>
            <p class="text-xs text-gray-500 italic font-medium">{{ statusConfig[app.status]?.desc }}</p>
          </div>
        </BaseCard>
        <div v-if="!applications.length" class="py-20 text-center text-gray-400 font-bold border-2 border-dashed border-gray-100 dark:border-white/5 rounded-[3rem]">暂无发出申请</div>
      </div>
    </section>

    <!-- 5. 收到的申请 -->
    <section class="space-y-6">
      <div class="flex items-center gap-3 text-2xl font-black text-gray-900 dark:text-white italic">
        <Mail class="text-green-500" :size="28" /> 收到的领养请求
      </div>
      <div class="grid grid-cols-1 gap-6">
        <BaseCard v-for="app in incomingApplications" :key="app.id" class="p-8 space-y-6 border-l-8 border-l-orange-500 shadow-xl">
          <div class="flex justify-between items-start">
            <div class="space-y-1">
              <h4 class="text-2xl font-black text-gray-900 dark:text-white uppercase tracking-tighter">来自 {{ app.applicant_name }} 的请求</h4>
              <p class="text-lg text-gray-500 italic font-bold">目标宠物：{{ app.pet_name }}</p>
            </div>
            <div class="text-right bg-orange-500/5 p-3 rounded-2xl border border-orange-500/10">
              <p class="text-[10px] text-gray-400 font-black uppercase">AI 准备度</p>
              <div class="text-4xl font-black text-orange-500">{{ app.ai_readiness_score || 'N/A' }}</div>
            </div>
          </div>
          <div class="p-6 bg-gray-50 dark:bg-white/5 rounded-[2rem] text-gray-600 dark:text-gray-300 text-lg leading-relaxed italic border border-gray-100 dark:border-white/5 relative">
            <span class="absolute top-4 left-4 text-4xl text-orange-500/20 italic font-serif">"</span>
            {{ app.apply_reason }}
          </div>
          
          <div v-if="app.ai_summary" class="bg-blue-500/5 border border-blue-500/10 p-5 rounded-2xl space-y-2">
            <p class="text-xs font-black text-blue-500 uppercase tracking-widest flex items-center gap-2"><ShieldCheck :size="14"/> AI 辅助审计摘要</p>
            <p class="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{{ app.ai_summary }}</p>
          </div>

          <div class="flex flex-wrap gap-4 pt-2">
            <template v-if="app.status === 'pending_owner_review'">
              <button @click="handleOwnerDecision(app.id, 'approved')" class="flex-1 min-w-[140px] py-5 bg-orange-500 text-white rounded-2xl font-black text-sm uppercase hover:bg-orange-600 transition-all shadow-xl shadow-orange-500/20">确认通过申请</button>
              <button @click="handleOwnerDecision(app.id, 'rejected')" class="flex-1 min-w-[140px] py-5 bg-gray-200 dark:bg-white/10 text-gray-900 dark:text-white rounded-2xl font-black text-sm uppercase hover:bg-red-500 hover:text-white transition-all">委婉拒绝</button>
            </template>
            <button @click="$router.push(`/chat?to=${app.user_id}`)" class="flex-1 min-w-[140px] py-5 bg-blue-500/10 text-blue-500 border border-blue-500/20 rounded-2xl font-black text-sm uppercase hover:bg-blue-500 hover:text-white transition-all flex items-center justify-center gap-2">
              <MessageSquare :size="18" /> 发起对话
            </button>
          </div>
          <div v-if="app.status !== 'pending_owner_review'" class="text-sm font-black text-gray-400 italic flex items-center gap-2">
            <CheckCircle2 v-if="app.status==='approved'" class="text-green-500" :size="16" />
            已处理状态：{{ statusConfig[app.status]?.label || app.status }}
          </div>
        </BaseCard>
        <div v-if="!incomingApplications.length" class="py-20 text-center text-gray-400 font-bold border-2 border-dashed border-gray-100 dark:border-white/5 rounded-[3rem]">暂无待处理请求</div>
      </div>
    </section>

    <!-- 6. 申请详情弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showAppDetail && selectedApp" class="fixed inset-0 z-[1000] flex items-center justify-center bg-black/80 backdrop-blur-xl px-4 py-6 overflow-y-auto" @click.self="showAppDetail = false">
          <BaseCard class="w-full max-w-2xl p-8 md:p-12 relative !bg-white dark:!bg-[#111] border-gray-200 dark:border-white/10 shadow-2xl max-h-[90vh] overflow-y-auto">
            <button @click="showAppDetail = false" class="absolute top-6 right-6 text-gray-400 hover:text-orange-500 transition-colors"><X :size="28"/></button>
            
            <div class="space-y-8">
              <div class="space-y-2 text-gray-900 dark:text-white">
                <div class="flex items-center gap-2.5 text-orange-500 font-black text-xs uppercase tracking-widest mb-2"><Heart :size="16"/> 领养申请详情报告</div>
                <h3 class="text-4xl font-black italic tracking-tighter">領養：{{ selectedApp.pet_name }}</h3>
                <p class="text-gray-500 font-bold">提交时间：{{ selectedApp.create_time }}</p>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div class="bg-gray-50 dark:bg-white/5 p-6 rounded-3xl border border-gray-100 dark:border-white/5 text-center">
                  <p class="text-[10px] text-gray-400 font-black uppercase mb-1">AI 准备度得分</p>
                  <div class="text-5xl font-black text-orange-500">{{ selectedApp.ai_readiness_score || '待评' }}</div>
                </div>
                <div class="bg-gray-50 dark:bg-white/5 p-6 rounded-3xl border border-gray-100 dark:border-white/5 text-center flex flex-col justify-center">
                  <p class="text-[10px] text-gray-400 font-black uppercase mb-1">当前生命周期</p>
                  <div :class="statusConfig[selectedApp.status]?.color" class="text-xl font-black">{{ statusConfig[selectedApp.status]?.label }}</div>
                </div>
              </div>

              <div v-if="selectedApp.ai_summary" class="space-y-3">
                <h5 class="text-xs font-black text-gray-400 uppercase tracking-widest">AI 综合审计评价</h5>
                <p class="text-base text-gray-700 dark:text-gray-300 leading-relaxed italic border-l-4 border-orange-500 pl-4">{{ selectedApp.ai_summary }}</p>
              </div>

              <div v-if="selectedApp.conflict_notes?.length" class="space-y-3">
                <h5 class="text-xs font-black text-red-400 uppercase tracking-widest flex items-center gap-2">⚠️ 风险/关注点告知</h5>
                <ul class="space-y-2">
                  <li v-for="note in selectedApp.conflict_notes" :key="note" class="text-sm text-gray-600 dark:text-gray-400 flex items-start gap-2 bg-red-500/5 p-3 rounded-xl border border-red-500/10">
                    <span class="text-red-500 font-black mt-0.5">•</span> {{ note }}
                  </li>
                </ul>
              </div>

              <div v-if="selectedApp.followup_questions?.length" class="space-y-3">
                <h5 class="text-xs font-black text-blue-400 uppercase tracking-widest flex items-center gap-2">💬 后续沟通建议题</h5>
                <ul class="space-y-2">
                  <li v-for="q in selectedApp.followup_questions" :key="q" class="text-sm text-gray-600 dark:text-gray-400 bg-blue-500/5 p-3 rounded-xl border border-blue-500/10 italic">
                    "{{ q }}"
                  </li>
                </ul>
              </div>

              <button @click="showAppDetail = false" class="w-full py-5 bg-gray-900 dark:bg-white text-white dark:text-black rounded-2xl font-black text-lg transition-all active:scale-95 shadow-xl">返回控制台</button>
            </div>
          </BaseCard>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: all 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: scale(0.98); }
</style>
