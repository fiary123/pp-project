<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../store/authStore'
import {
  User, LogOut, Loader2, Heart, Camera, ShieldCheck, Mail
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

// 2. 密码修改逻辑 (增加验证码)
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

// 3. 数据加载
const applications = ref<any[]>([])
const incomingApplications = ref<any[]>([])
const isLoading = ref(false)

const fetchData = async () => {
  isLoading.value = true
  try {
    const [res1, res2] = await Promise.all([
      axios.get(`/api/user/applications/${authStore.user?.id}`),
      axios.get('/api/user/applications/incoming')
    ])
    applications.value = res1.data
    incomingApplications.value = res2.data
  } finally { isLoading.value = false }
}

// 状态映射
const statusMap: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: '待处理', color: 'text-gray-400', bg: 'bg-white/5' },
  pending_owner_review: { label: '待审核', color: 'text-orange-400', bg: 'bg-orange-500/10' },
  approved: { label: '已通过', color: 'text-green-400', bg: 'bg-green-500/10' },
  rejected: { label: '已驳回', color: 'text-red-400', bg: 'bg-red-500/10' }
}

const handleOwnerDecision = async (appId: number, status: string) => {
  const note = window.prompt('备注信息（可选）：') || ''
  await axios.post(`/api/user/applications/${appId}/owner-decision`, { status, owner_note: note })
  fetchData()
}

onMounted(fetchData)
</script>

<template>
  <div class="profile-view max-w-4xl mx-auto space-y-12 pb-32 px-4 pt-10 transition-colors duration-500 bg-white dark:bg-transparent">
    
    <!-- 1. 顶部大标题 -->
    <div class="text-center md:text-left space-y-2">
      <h1 class="text-5xl md:text-6xl font-black text-gray-900 dark:text-white italic tracking-tighter uppercase">Personal Center</h1>
      <p class="text-xl text-gray-500 dark:text-gray-400 font-bold">管理您的资料、申请与安全设置</p>
    </div>

    <!-- 2. 基本资料大卡片 -->
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
          <button @click="authStore.logout(); $router.push('/login')" class="px-8 py-4 bg-red-500/10 text-red-500 rounded-2xl font-black hover:bg-red-500 hover:text-white transition-all flex items-center gap-2">
            <LogOut :size="20" /> 退出登录
          </button>
        </div>
      </BaseCard>
    </section>

    <!-- 3. 安全设置 (增加验证码) -->
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
      <div v-else class="grid grid-cols-1 gap-4">
        <BaseCard v-for="app in applications" :key="app.id" class="p-6 md:p-8 flex items-center justify-between gap-6 hover:bg-gray-50 dark:hover:bg-white/5 transition-all">
          <div class="flex items-center gap-6">
            <div class="w-16 h-16 rounded-2xl bg-orange-500/10 flex items-center justify-center text-orange-500 font-black text-2xl italic">#{{ app.pet_id }}</div>
            <div>
              <h4 class="text-2xl font-bold text-gray-900 dark:text-white">领养：{{ app.pet_name || '宠物' }}</h4>
              <p class="text-gray-500 font-medium">送养方：{{ app.owner_name || '系统' }} · {{ app.create_time }}</p>
            </div>
          </div>
          <div :class="[statusMap[app.status]?.bg, statusMap[app.status]?.color]" class="px-6 py-2 rounded-full font-black text-sm border border-gray-200 dark:border-white/10 uppercase tracking-widest">
            {{ statusMap[app.status]?.label || '处理中' }}
          </div>
        </BaseCard>
        <div v-if="!applications.length" class="py-20 text-center text-gray-400 font-bold border-2 border-dashed border-gray-100 dark:border-white/5 rounded-[3rem]">暂无发出申请</div>
      </div>
    </section>

    <!-- 5. 我收到的申请 -->
    <section class="space-y-6">
      <div class="flex items-center gap-3 text-2xl font-black text-gray-900 dark:text-white italic">
        <Mail class="text-green-500" :size="28" /> 收到的领养请求
      </div>
      <div class="grid grid-cols-1 gap-4">
        <BaseCard v-for="app in incomingApplications" :key="app.id" class="p-8 space-y-6 border-l-8 border-l-orange-500">
          <div class="flex justify-between items-start">
            <div class="space-y-1">
              <h4 class="text-2xl font-black text-gray-900 dark:text-white uppercase tracking-tighter">来自 {{ app.applicant_name }} 的请求</h4>
              <p class="text-lg text-gray-500 italic">目标宠物：{{ app.pet_name }}</p>
            </div>
            <div class="text-right">
              <p class="text-[10px] text-gray-400 font-black uppercase">AI 评分</p>
              <div class="text-4xl font-black text-orange-500">{{ app.ai_readiness_score || 'N/A' }}</div>
            </div>
          </div>
          <div class="p-6 bg-gray-50 dark:bg-white/5 rounded-3xl text-gray-600 dark:text-gray-300 text-lg leading-relaxed italic border border-gray-100 dark:border-white/5">
            "{{ app.apply_reason }}"
          </div>
          <div v-if="app.status === 'pending_owner_review'" class="flex gap-4">
            <button @click="handleOwnerDecision(app.id, 'approved')" class="flex-1 py-4 bg-green-600 text-white rounded-2xl font-black text-sm uppercase hover:bg-green-500 transition-all shadow-lg shadow-green-500/20">通过领养</button>
            <button @click="handleOwnerDecision(app.id, 'rejected')" class="flex-1 py-4 bg-gray-200 dark:bg-white/10 text-gray-900 dark:text-white rounded-2xl font-black text-sm uppercase hover:bg-red-500 hover:text-white transition-all">婉拒</button>
          </div>
          <div v-else class="text-sm font-black text-gray-400 italic">已处理状态：{{ app.status }}</div>
        </BaseCard>
        <div v-if="!incomingApplications.length" class="py-20 text-center text-gray-400 font-bold border-2 border-dashed border-gray-100 dark:border-white/5 rounded-[3rem]">暂无待处理请求</div>
      </div>
    </section>

  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: all 0.3s ease; }
.fade-enter-from { opacity: 0; transform: scale(0.98); }
</style>
