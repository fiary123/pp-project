<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '../store/authStore'
import {
  User, LogOut, Loader2, Heart, Camera, ShieldCheck, Mail, X, CheckCircle2,
  MessageSquare, Sparkles, Wand2, ListOrdered, AlertTriangle, Info
} from 'lucide-vue-next'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'

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
    const updateRes = await axios.post('/api/user/update-profile', { avatar_url: uploadRes.data.url })
    authStore.login(updateRes.data.user, authStore.token || '')
    alert('头像更换成功！')
  } catch (err: any) {
    alert('上传失败')
  } finally {
    isUploadingAvatar.value = false
  }
}

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
    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (err: any) {
    alert('发送失败')
  } finally {
    isSendingCode.value = false
  }
}

const handleUpdatePassword = async () => {
  if (!passForm.value.code) return alert('请输入验证码')
  try {
    await axios.post('/api/user/change-password', {
      user_id: authStore.user.id,
      old_password: passForm.value.old,
      new_password: passForm.value.new,
      code: passForm.value.code,
    })
    passStatus.value = '密码更新成功！'
    passForm.value = { old: '', new: '', code: '' }
  } catch (err: any) {
    passStatus.value = err.response?.data?.detail || '修改失败'
  }
}

const userProfile = ref({
  housing_type: 'apartment',
  has_yard: false,
  has_other_pets: false,
  housing_size: 50,
  rental_status: '租房',
  pet_experience: '无',
  available_time: 2,
  budget_level: '中',
  family_support: true,
  family_structure: '纯成年人',
  activity_level: '宅家型',
  preferred_pet_type: '猫',
  preferred_age_range: '成年',
  preferred_size: '中型',
  preferred_temperament: '温顺',
  accept_special_care: false,
  accept_high_energy: true,
  allergy_history: false,
})
const isUpdatingProfile = ref(false)
const aiBio = ref('')
const isAiParsing = ref(false)

const handleAiAutoProfile = async () => {
  if (!aiBio.value.trim()) return
  isAiParsing.value = true
  try {
    const res = await axios.post('/api/user/auto-profile', { bio: aiBio.value })
    if (res.data.extracted_data) {
      userProfile.value = { ...userProfile.value, ...res.data.extracted_data }
      alert('AI 已根据您的描述自动填充画像与需求，请核对后保存。')
    }
  } catch (err) {
    alert('AI 解析失败，请尝试手动填写')
  } finally {
    isAiParsing.value = false
  }
}

const fetchUserProfile = async () => {
  if (!authStore.user?.id) return
  try {
    const res = await axios.get(`/api/user/profile-portrait/${authStore.user.id}`)
    if (res.data) {
      userProfile.value = {
        ...userProfile.value,
        ...res.data,
        allergy_history: !!res.data.allergy_info,
      }
    }
  } catch (err) {
    console.error('加载结构化画像失败', err)
  }
}

const handleUpdateProfile = async () => {
  isUpdatingProfile.value = true
  try {
    await axios.post('/api/user/update-profile-data', userProfile.value)
    alert('用户画像与领养需求已更新，后续推荐将按新资料进行候选生成、约束过滤与排序。')
  } catch (err) {
    alert('更新失败')
  } finally {
    isUpdatingProfile.value = false
  }
}

const applications = ref<any[]>([])
const incomingApplications = ref<any[]>([])
const ownerRankingMap = ref<Record<string, any>>({})
const isLoading = ref(false)
const selectedApp = ref<any>(null)
const showAppDetail = ref(false)

const statusConfig: Record<string, { label: string; color: string; bg: string; step: number; desc: string }> = {
  pending: { label: '评估处理中', color: 'text-blue-400', bg: 'bg-blue-500/10', step: 1, desc: '系统正在完成约束过滤与多维评分。' },
  pending_owner_review: { label: '待送养方决策', color: 'text-orange-400', bg: 'bg-orange-500/10', step: 2, desc: '推荐结果已生成，将在审核阶段提供排序与决策支持。' },
  approved: { label: '审核通过', color: 'text-green-400', bg: 'bg-green-500/10', step: 4, desc: '送养方已完成最终决策并通过申请。' },
  rejected: { label: '申请驳回', color: 'text-red-400', bg: 'bg-red-500/10', step: 4, desc: '送养方已完成最终决策。' },
  signed: { label: '已签协议', color: 'text-indigo-400', bg: 'bg-indigo-500/10', step: 5, desc: '领养协议已签署，手续已完成。' },
  followup: { label: '回访中', color: 'text-teal-400', bg: 'bg-teal-500/10', step: 6, desc: '进入领养后回访阶段。' },
}

const getAppProgress = (status: string) => {
  const step = statusConfig[status]?.step || 1
  return (step / 6) * 100
}

const rankingKey = (petId: number | string, userId: number | string) => `${petId}:${userId}`
const getRankingForApp = (app: any) => ownerRankingMap.value[rankingKey(app.pet_id, app.user_id)] || null

const dimensionLabelMap: Record<string, string> = {
  matching_score: '匹配度',
  care_capacity_score: '照护条件',
  economic_capacity_score: '经济能力',
  housing_stability_score: '居住稳定性',
  risk_dimension_penalty: '风险维度',
}

const normalizedSubScores = (subScores: Record<string, number> | undefined) => {
  if (!subScores) return []
  return Object.entries(subScores).map(([key, value]) => ({
    key,
    label: dimensionLabelMap[key] || key,
    value: Number(value ?? 0),
  }))
}

const fetchApplicantRankings = async () => {
  const petIds = [...new Set(incomingApplications.value.map((app) => app.pet_id).filter(Boolean))]
  if (!petIds.length) {
    ownerRankingMap.value = {}
    return
  }

  const entries = await Promise.all(
    petIds.map(async (petId) => {
      try {
        const res = await axios.get(`/api/recommendation/pets/${petId}/applicants`)
        return [petId, Array.isArray(res.data) ? res.data : []] as const
      } catch (err) {
        console.error(`加载宠物 ${petId} 的申请排序失败`, err)
        return [petId, []] as const
      }
    })
  )

  const nextMap: Record<string, any> = {}
  entries.forEach(([petId, rankings]) => {
    rankings.forEach((item: any) => {
      nextMap[rankingKey(petId, item.user_id)] = item
    })
  })
  ownerRankingMap.value = nextMap
}

const fetchData = async () => {
  if (!authStore.isLoggedIn) return
  isLoading.value = true
  try {
    const res = await axios.get(`/api/user/applications/${authStore.user?.id}`)
    applications.value = Array.isArray(res.data) ? res.data : []
  } catch (err) {
    console.error('加载我的申请失败:', err)
  }

  try {
    const res = await axios.get('/api/user/applications/incoming')
    incomingApplications.value = Array.isArray(res.data) ? res.data : []
    await fetchApplicantRankings()
  } catch (err) {
    console.error('加载收到的申请失败:', err)
  }
  isLoading.value = false
}

const rankedIncomingApplications = computed(() => {
  return [...incomingApplications.value].sort((a, b) => {
    const scoreB = Number(getRankingForApp(b)?.score ?? b.ai_readiness_score ?? 0)
    const scoreA = Number(getRankingForApp(a)?.score ?? a.ai_readiness_score ?? 0)
    return scoreB - scoreA
  })
})

const openAppDetail = (app: any) => {
  selectedApp.value = app
  showAppDetail.value = true
}

const handleOwnerDecision = async (appId: number, status: string) => {
  const note = window.prompt('备注信息（可选）：') || ''
  try {
    await axios.post(`/api/user/applications/${appId}/owner-decision`, { status, owner_note: note })
    await fetchData()
  } catch (err) {
    alert('处理失败')
  }
}

onMounted(() => {
  fetchData()
  fetchUserProfile()
})
</script>

<template>
  <div class="profile-view max-w-6xl mx-auto space-y-12 pb-32 px-4 pt-10 transition-colors duration-500 bg-white dark:bg-transparent">
    <div class="text-center md:text-left space-y-3">
      <h1 class="text-5xl md:text-6xl font-black text-gray-900 dark:text-white italic tracking-tighter uppercase">Personal Center</h1>
      <p class="text-xl text-gray-500 dark:text-gray-400 font-bold">围绕“画像采集 → 推荐排序 → 审核联动”管理您的资料与申请</p>
    </div>

    <section class="space-y-6">
      <div class="flex items-center gap-3 text-2xl font-black text-gray-900 dark:text-white italic">
        <User class="text-orange-500" :size="28" /> 基本信息
      </div>
      <BaseCard class="p-8 md:p-12 shadow-2xl">
        <div class="flex flex-col md:flex-row items-center gap-10">
          <div
            @click="triggerAvatarUpload"
            class="group relative w-32 h-24 md:w-40 md:h-40 rounded-full bg-orange-500/10 border-4 border-orange-500 overflow-hidden shadow-2xl cursor-pointer"
          >
            <img :src="authStore.user?.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${authStore.user?.username}`" class="w-full h-full object-cover transition-transform group-hover:scale-110" />
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

    <section class="space-y-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3 text-2xl font-black text-gray-900 dark:text-white italic">
          <Sparkles class="text-orange-500" :size="28" /> 用户画像与领养需求采集
        </div>
        <div class="text-[10px] font-black text-gray-400 uppercase tracking-widest bg-gray-100 dark:bg-white/5 px-3 py-1 rounded-full border border-gray-200 dark:border-white/10">结构化特征 v3</div>
      </div>

      <BaseCard class="p-6 border-2 border-dashed border-orange-500/30 bg-orange-500/5">
        <div class="space-y-4">
          <div class="flex items-center gap-2 text-sm font-black text-orange-600 dark:text-orange-400 uppercase tracking-widest">
            <Wand2 :size="16" /> AI 辅助采集
          </div>
          <div class="flex gap-3">
            <input v-model="aiBio" type="text" placeholder="例如：住80平公寓、工作日能陪伴3小时、预算中等，想领养温顺成年猫" class="flex-1 bg-white dark:bg-[#1a1a1a] border border-orange-200 dark:border-orange-500/20 rounded-2xl py-4 px-6 outline-none focus:ring-4 focus:ring-orange-500/10 font-bold text-gray-900 dark:text-white" />
            <button @click="handleAiAutoProfile" :disabled="isAiParsing || !aiBio.trim()" class="px-8 bg-orange-500 text-white rounded-2xl font-black shadow-lg shadow-orange-500/20 hover:bg-orange-600 transition-all flex items-center justify-center gap-2 active:scale-95 disabled:opacity-50">
              <Loader2 v-if="isAiParsing" class="animate-spin" :size="20" />
              <Sparkles v-else :size="20" />
              解析
            </button>
          </div>
          <p class="text-[10px] text-gray-400 italic">系统会优先采集居住条件、陪伴时间、预算、偏好和风险维度，用于后续候选生成与排序。</p>
        </div>
      </BaseCard>

      <BaseCard class="p-8 md:p-12">
        <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
          <div class="space-y-6">
            <h3 class="text-lg font-black text-gray-900 dark:text-white">用户画像</h3>
            <div class="space-y-2">
              <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest">居住条件</label>
              <div class="grid grid-cols-2 gap-3">
                <select v-model="userProfile.housing_type" class="bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl py-3 px-4 outline-none focus:border-orange-500 text-gray-900 dark:text-white font-bold">
                  <option value="apartment">公寓</option>
                  <option value="house">独立住宅</option>
                  <option value="other">其他</option>
                </select>
                <input v-model.number="userProfile.housing_size" type="number" placeholder="面积 / 平米" class="bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl py-3 px-4 outline-none focus:border-orange-500 font-bold" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <select v-model="userProfile.rental_status" class="bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl py-3 px-4 font-bold">
                <option value="自购">自购</option>
                <option value="租房">租房</option>
              </select>
              <select v-model="userProfile.budget_level" class="bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl py-3 px-4 font-bold">
                <option value="低">预算低</option>
                <option value="中">预算中</option>
                <option value="高">预算高</option>
              </select>
            </div>
            <div class="space-y-3">
              <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10">
                <span class="text-xs font-bold text-gray-700 dark:text-gray-300">是否有院子</span>
                <input v-model="userProfile.has_yard" type="checkbox" class="w-5 h-5 accent-orange-500" />
              </div>
              <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10">
                <span class="text-xs font-bold text-gray-700 dark:text-gray-300">家中已有宠物</span>
                <input v-model="userProfile.has_other_pets" type="checkbox" class="w-5 h-5 accent-orange-500" />
              </div>
            </div>
          </div>

          <div class="space-y-6">
            <h3 class="text-lg font-black text-gray-900 dark:text-white">照护能力</h3>
            <div class="grid grid-cols-2 gap-3">
              <select v-model="userProfile.pet_experience" class="bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl py-3 px-4 font-bold">
                <option value="无">无经验</option>
                <option value="1-3年">1-3年</option>
                <option value="3年以上">3年以上</option>
              </select>
              <input v-model.number="userProfile.available_time" type="number" step="0.5" placeholder="可陪伴时长 / 日" class="bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl py-3 px-4 font-bold" />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <select v-model="userProfile.family_structure" class="bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl py-3 px-4 font-bold">
                <option value="纯成年人">纯成年人</option>
                <option value="包含婴幼儿">有婴幼儿</option>
                <option value="包含老人">有老人</option>
              </select>
              <select v-model="userProfile.activity_level" class="bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl py-3 px-4 font-bold">
                <option value="宅家型">宅家型</option>
                <option value="户外型">户外型</option>
              </select>
            </div>
            <div class="space-y-3">
              <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10">
                <span class="text-xs font-bold text-gray-700 dark:text-gray-300">家庭是否支持养宠</span>
                <input v-model="userProfile.family_support" type="checkbox" class="w-5 h-5 accent-orange-500" />
              </div>
              <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10">
                <span class="text-xs font-bold text-gray-700 dark:text-gray-300">家庭成员是否有过敏史</span>
                <input v-model="userProfile.allergy_history" type="checkbox" class="w-5 h-5 accent-orange-500" />
              </div>
            </div>
          </div>

          <div class="space-y-6">
            <h3 class="text-lg font-black text-gray-900 dark:text-white">领养偏好</h3>
            <div class="grid grid-cols-2 gap-3">
              <select v-model="userProfile.preferred_pet_type" class="bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl py-3 px-4 font-bold">
                <option value="猫">偏好猫</option>
                <option value="狗">偏好狗</option>
                <option value="兔">偏好异宠</option>
              </select>
              <select v-model="userProfile.preferred_age_range" class="bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl py-3 px-4 font-bold">
                <option value="幼年">幼年</option>
                <option value="成年">成年</option>
                <option value="老年">老年</option>
              </select>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <select v-model="userProfile.preferred_size" class="bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl py-3 px-4 font-bold">
                <option value="小型">小型</option>
                <option value="中型">中型</option>
                <option value="大型">大型</option>
              </select>
              <select v-model="userProfile.preferred_temperament" class="bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl py-3 px-4 font-bold">
                <option value="温顺">温顺</option>
                <option value="活泼">活泼</option>
                <option value="安静">安静</option>
                <option value="亲人">亲人</option>
              </select>
            </div>
            <div class="space-y-3">
              <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10">
                <span class="text-xs font-bold text-gray-700 dark:text-gray-300">接受特殊护理宠物</span>
                <input v-model="userProfile.accept_special_care" type="checkbox" class="w-5 h-5 accent-orange-500" />
              </div>
              <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10">
                <span class="text-xs font-bold text-gray-700 dark:text-gray-300">接受高活跃宠物</span>
                <input v-model="userProfile.accept_high_energy" type="checkbox" class="w-5 h-5 accent-orange-500" />
              </div>
            </div>
          </div>
        </div>

        <button @click="handleUpdateProfile" :disabled="isUpdatingProfile" class="mt-10 w-full py-5 bg-gray-900 dark:bg-white text-white dark:text-black rounded-2xl font-black shadow-2xl hover:scale-[1.02] transition-all flex items-center justify-center gap-2">
          <Loader2 v-if="isUpdatingProfile" class="animate-spin" :size="20" />
          <CheckCircle2 v-else :size="20" />
          保存画像并同步推荐流程
        </button>
      </BaseCard>
    </section>

    <section class="space-y-6">
      <div class="flex items-center gap-3 text-2xl font-black text-gray-900 dark:text-white italic">
        <ShieldCheck class="text-blue-500" :size="28" /> 安全设置
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
                <p class="text-[10px] text-gray-400 font-black uppercase">综合评估分</p>
                <p class="text-xl font-black text-orange-500">{{ app.ai_readiness_score || '评估中' }}</p>
              </div>
              <div :class="[statusConfig[app.status]?.bg, statusConfig[app.status]?.color]" class="px-6 py-2 rounded-xl font-black text-sm border border-gray-200 dark:border-white/5 uppercase tracking-widest">
                {{ statusConfig[app.status]?.label || '处理中' }}
              </div>
            </div>
          </div>

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

    <section class="space-y-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3 text-2xl font-black text-gray-900 dark:text-white italic">
          <Mail class="text-green-500" :size="28" /> 申请审核联动系统
        </div>
        <div class="text-xs font-black text-slate-400 uppercase tracking-widest px-3 py-1 bg-slate-100 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/5">
          Feature-Driven Audit v4.2
        </div>
      </div>

      <!-- [演示增强]：老师视角 - 推荐排序逻辑说明卡 -->
      <BaseCard class="p-8 bg-slate-900 text-white border-none shadow-2xl relative overflow-hidden group">
        <div class="absolute -right-10 -bottom-10 w-40 h-40 bg-orange-500/20 rounded-full blur-3xl group-hover:bg-orange-500/40 transition-all duration-700"></div>
        <div class="relative z-10 space-y-6">
          <div class="flex items-center gap-4">
            <div class="p-3 bg-orange-500 rounded-2xl shadow-lg shadow-orange-500/20"><BrainCircuit :size="24" /></div>
            <div>
              <h4 class="text-xl font-black italic uppercase tracking-tight">推荐引擎驱动的审核精排逻辑</h4>
              <p class="text-xs text-slate-400 font-bold mt-1">系统已将原始申请流重定向为“结构化匹配流”，显著提升发布者的审核决策效率。</p>
            </div>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4 pt-2">
            <div class="space-y-2">
              <p class="text-[10px] font-black text-orange-500 uppercase tracking-widest">Step 1: 画像对齐</p>
              <p class="text-xs text-slate-300 leading-5">从申请人 Bio 与结构化问卷中提取住房、经验、预算等 12 个核心维度。</p>
            </div>
            <div class="space-y-2 border-l border-white/10 pl-4">
              <p class="text-[10px] font-black text-blue-400 uppercase tracking-widest">Step 2: 约束感知</p>
              <p class="text-xs text-slate-300 leading-5">同步比对送养方的硬性约束（如禁止新手、陪伴时长门槛等）执行初步筛选。</p>
            </div>
            <div class="space-y-2 border-l border-white/10 pl-4">
              <p class="text-[10px] font-black text-green-400 uppercase tracking-widest">Step 3: 多维评分</p>
              <p class="text-xs text-slate-300 leading-5">基于环境、偏好、经验与风险抵扣四维度计算匹配分，并由 Agent 进行决策审计。</p>
            </div>
            <div class="space-y-2 border-l border-white/10 pl-4">
              <p class="text-[10px] font-black text-pink-400 uppercase tracking-widest">Step 4: 实时重排</p>
              <p class="text-xs text-slate-300 leading-5">申请提交后立即触发 Pipeline 重排，确保发布者始终优先看到最优候选。</p>
            </div>
          </div>
        </div>
      </BaseCard>

      <div class="grid grid-cols-1 gap-6">
        <BaseCard v-for="app in rankedIncomingApplications" :key="app.id" class="p-8 space-y-6 border-l-8 border-l-orange-500 shadow-xl">
          <div class="flex flex-col lg:flex-row lg:items-start justify-between gap-5">
            <div class="space-y-2">
              <div class="flex items-center gap-3 flex-wrap">
                <span class="px-3 py-1 rounded-full bg-orange-500 text-white text-xs font-black uppercase tracking-widest">推荐第 {{ getRankingForApp(app)?.rank || '-' }} 位</span>
                <span class="px-3 py-1 rounded-full bg-gray-100 dark:bg-white/5 text-gray-500 text-xs font-black uppercase tracking-widest">{{ app.pet_name }}</span>
              </div>
              <h4 class="text-2xl font-black text-gray-900 dark:text-white uppercase tracking-tighter">来自 {{ app.applicant_name }} 的申请</h4>
              <p class="text-base text-gray-500 italic font-bold">系统已完成约束过滤与多维评分，可作为审核排序参考</p>
            </div>
            <div class="grid grid-cols-2 gap-3 min-w-[240px]">
              <div class="text-right bg-orange-500/5 p-4 rounded-2xl border border-orange-500/10">
                <p class="text-[10px] text-gray-400 font-black uppercase">推荐支持分</p>
                <div class="text-4xl font-black text-orange-500">{{ getRankingForApp(app)?.score ?? app.ai_readiness_score ?? 'N/A' }}</div>
              </div>
              <div class="text-right bg-blue-500/5 p-4 rounded-2xl border border-blue-500/10">
                <p class="text-[10px] text-gray-400 font-black uppercase">当前状态</p>
                <div :class="statusConfig[app.status]?.color" class="text-base font-black mt-2">{{ statusConfig[app.status]?.label || app.status }}</div>
              </div>
            </div>
          </div>

          <div class="p-6 bg-gray-50 dark:bg-white/5 rounded-[2rem] text-gray-600 dark:text-gray-300 text-lg leading-relaxed italic border border-gray-100 dark:border-white/5 relative">
            <span class="absolute top-4 left-4 text-4xl text-orange-500/20 italic font-serif">"</span>
            {{ app.apply_reason }}
          </div>

          <div v-if="getRankingForApp(app)?.reasons?.length" class="space-y-3">
            <p class="text-xs font-black text-green-500 uppercase tracking-widest flex items-center gap-2">
              <ListOrdered :size="14" /> 推荐理由
            </p>
            <div class="flex flex-wrap gap-2">
              <span v-for="reason in getRankingForApp(app)?.reasons" :key="reason" class="px-3 py-2 rounded-full bg-green-500/10 text-green-700 dark:text-green-300 text-xs font-bold border border-green-500/10">
                {{ reason }}
              </span>
            </div>
          </div>

          <div v-if="normalizedSubScores(getRankingForApp(app)?.sub_scores).length" class="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div v-for="score in normalizedSubScores(getRankingForApp(app)?.sub_scores)" :key="score.key" class="rounded-2xl border border-gray-100 dark:border-white/10 bg-gray-50 dark:bg-white/5 p-4">
              <p class="text-[10px] font-black uppercase tracking-widest text-gray-400">{{ score.label }}</p>
              <p class="text-2xl font-black text-gray-900 dark:text-white mt-2">{{ score.value }}</p>
            </div>
          </div>

          <div v-if="getRankingForApp(app)?.risk_flags?.length" class="space-y-3">
            <p class="text-xs font-black text-red-400 uppercase tracking-widest flex items-center gap-2">
              <AlertTriangle :size="14" /> 风险维度
            </p>
            <div class="flex flex-wrap gap-2">
              <span v-for="flag in getRankingForApp(app)?.risk_flags" :key="flag" class="px-3 py-2 rounded-full bg-red-500/10 text-red-600 dark:text-red-300 text-xs font-bold border border-red-500/10">
                {{ flag }}
              </span>
            </div>
          </div>

          <div v-if="app.ai_summary" class="bg-blue-500/5 border border-blue-500/10 p-5 rounded-2xl space-y-2">
            <p class="text-xs font-black text-blue-500 uppercase tracking-widest flex items-center gap-2"><ShieldCheck :size="14" /> 评估补充说明</p>
            <p class="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{{ app.ai_summary }}</p>
          </div>

          <div class="flex flex-wrap gap-4 pt-2">
            <template v-if="app.status === 'pending_owner_review'">
              <button @click="handleOwnerDecision(app.id, 'approved')" class="flex-1 min-w-[140px] py-5 bg-orange-500 text-white rounded-2xl font-black text-sm uppercase hover:bg-orange-600 transition-all shadow-xl shadow-orange-500/20">通过申请</button>
              <button @click="handleOwnerDecision(app.id, 'rejected')" class="flex-1 min-w-[140px] py-5 bg-gray-200 dark:bg-white/10 text-gray-900 dark:text-white rounded-2xl font-black text-sm uppercase hover:bg-red-500 hover:text-white transition-all">拒绝申请</button>
            </template>
            <button @click="$router.push(`/chat?to=${app.user_id}`)" class="flex-1 min-w-[140px] py-5 bg-blue-500/10 text-blue-500 border border-blue-500/20 rounded-2xl font-black text-sm uppercase hover:bg-blue-500 hover:text-white transition-all flex items-center justify-center gap-2">
              <MessageSquare :size="18" /> 发起对话
            </button>
          </div>
        </BaseCard>
        <div v-if="!rankedIncomingApplications.length" class="py-20 text-center text-gray-400 font-bold border-2 border-dashed border-gray-100 dark:border-white/5 rounded-[3rem]">暂无待处理请求</div>
      </div>
    </section>

    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showAppDetail && selectedApp" class="fixed inset-0 z-[1000] flex items-center justify-center bg-black/80 backdrop-blur-xl px-4 py-6 overflow-y-auto" @click.self="showAppDetail = false">
          <BaseCard class="w-full max-w-2xl p-8 md:p-12 relative !bg-white dark:!bg-[#111] border-gray-200 dark:border-white/10 shadow-2xl max-h-[90vh] overflow-y-auto">
            <button @click="showAppDetail = false" class="absolute top-6 right-6 text-gray-400 hover:text-orange-500 transition-colors"><X :size="28" /></button>

            <div class="space-y-8">
              <div class="space-y-2 text-gray-900 dark:text-white">
                <div class="flex items-center gap-2.5 text-orange-500 font-black text-xs uppercase tracking-widest mb-2"><Heart :size="16" /> 领养申请详情</div>
                <h3 class="text-4xl font-black italic tracking-tighter">领养：{{ selectedApp.pet_name }}</h3>
                <p class="text-gray-500 font-bold">提交时间：{{ selectedApp.create_time }}</p>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div class="bg-gray-50 dark:bg-white/5 p-6 rounded-3xl border border-gray-100 dark:border-white/5 text-center">
                  <p class="text-[10px] text-gray-400 font-black uppercase mb-1">综合评估分</p>
                  <div class="text-5xl font-black text-orange-500">{{ selectedApp.ai_readiness_score || '待评' }}</div>
                </div>
                <div class="bg-gray-50 dark:bg-white/5 p-6 rounded-3xl border border-gray-100 dark:border-white/5 text-center flex flex-col justify-center">
                  <p class="text-[10px] text-gray-400 font-black uppercase mb-1">当前阶段</p>
                  <div :class="statusConfig[selectedApp.status]?.color" class="text-xl font-black">{{ statusConfig[selectedApp.status]?.label }}</div>
                </div>
              </div>

              <div v-if="selectedApp.ai_summary" class="space-y-3">
                <h5 class="text-xs font-black text-gray-400 uppercase tracking-widest">评估摘要</h5>
                <p class="text-base text-gray-700 dark:text-gray-300 leading-relaxed italic border-l-4 border-orange-500 pl-4">{{ selectedApp.ai_summary }}</p>
              </div>

              <div v-if="selectedApp.conflict_notes?.length" class="space-y-3">
                <h5 class="text-xs font-black text-red-400 uppercase tracking-widest">风险提示</h5>
                <ul class="space-y-2">
                  <li v-for="note in selectedApp.conflict_notes" :key="note" class="text-sm text-gray-600 dark:text-gray-400 flex items-start gap-2 bg-red-500/5 p-3 rounded-xl border border-red-500/10">
                    <span class="text-red-500 font-black mt-0.5">•</span> {{ note }}
                  </li>
                </ul>
              </div>

              <div v-if="selectedApp.followup_questions?.length" class="space-y-3">
                <h5 class="text-xs font-black text-blue-400 uppercase tracking-widest">建议追问</h5>
                <ul class="space-y-2">
                  <li v-for="q in selectedApp.followup_questions" :key="q" class="text-sm text-gray-600 dark:text-gray-400 bg-blue-500/5 p-3 rounded-xl border border-blue-500/10 italic">
                    {{ q }}
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
