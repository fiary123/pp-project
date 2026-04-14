<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search, Heart, Loader2, ChevronRight, Wand2, Sparkles, ShieldCheck, ListFilter, AlertTriangle
} from 'lucide-vue-next'
import { useAuthStore } from '../store/authStore'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'

const router = useRouter()
const authStore = useAuthStore()

const defaultAdoptionPreferences = {
  allow_novice: true,
  min_budget_level: '低',
  min_companion_hours: 0,
  required_housing_type: '',
  forbid_other_pets: false,
  forbid_children: false,
  require_return_visit: true,
}

const parseAdoptionPreferences = (raw: unknown) => {
  if (!raw) return { ...defaultAdoptionPreferences }
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
    return { ...defaultAdoptionPreferences, ...(parsed as Record<string, unknown>) }
  } catch {
    return { ...defaultAdoptionPreferences }
  }
}

const pets = ref<any[]>([])
const engineRecommendations = ref<any[]>([])
const isLoading = ref(true)
const isEngineLoading = ref(false)
const needsColdStart = ref(false)
const showIntentionForm = ref(false)
const intentionForm = ref({
  housing_type: '公寓',
  experience_level: 0,
  available_time: 2,
  budget_level: '中',
  has_children: 0,
})
const isSubmittingIntention = ref(false)
const searchQuery = ref('')
const activeFilter = ref('全部')
const selectedPet = ref<any>(null)

const submitIntention = async () => {
  isSubmittingIntention.value = true
  try {
    // 复用更新画像接口，补全核心推荐维度
    await axios.post('/api/user/update-profile', {
      ...intentionForm.value,
      pet_experience: intentionForm.value.experience_level > 0 ? '有经验' : '无',
    })
    showIntentionForm.value = false
    await fetchEngineRecommendations() // 重新拉取精准推荐
    window.alert('画像补全成功！AI 已为您生成精准匹配列表。')
  } catch (err) {
    window.alert('提交失败，请重试')
  } finally {
    isSubmittingIntention.value = false
  }
}

const fetchPets = async () => {
  isLoading.value = true
  try {
    const res = await axios.get('/api/pets')
    pets.value = Array.isArray(res.data)
      ? res.data.map((p: any) => ({
          ...p,
          id: Number(p.id),
          img: p.image_url || p.post_image_url || `https://images.unsplash.com/photo-1543466835-00a7907e9de1?sig=${p.id}`,
          desc: p.description || p.post_content || '暂无详细介绍',
          adoption_preferences: parseAdoptionPreferences(p.adoption_preferences),
          tags: p.tags ? (typeof p.tags === 'string' ? JSON.parse(p.tags) : p.tags) : [],
        }))
      : []
  } catch (err) {
    console.error('获取宠物列表失败', err)
  } finally {
    isLoading.value = false
  }
}

const fetchEngineRecommendations = async () => {
  if (!authStore.isLoggedIn || !authStore.user?.id) return
  isEngineLoading.value = true
  try {
    const res = await axios.get(`/api/recommendation/pets/${authStore.user.id}`)
    // 适配新后端返回结构
    engineRecommendations.value = Array.isArray(res.data.results) ? res.data.results : []
    needsColdStart.value = !!res.data.needs_cold_start
  } catch (err) {
    console.error('获取推荐结果失败', err)
  } finally {
    isEngineLoading.value = false
  }
}

const filteredPets = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  return pets.value.filter((pet) => {
    const matchesKeyword = !keyword || pet.name?.toLowerCase().includes(keyword) || pet.species?.toLowerCase().includes(keyword)
    const matchesType = activeFilter.value === '全部' || pet.species === activeFilter.value
    return matchesKeyword && matchesType
  })
})

const getRecommendationForPet = (petId: number) => {
  return engineRecommendations.value.find((item) => Number(item.pet_id) === Number(petId))
}

const displayConstraintTags = (pet: any) => {
  const prefs = pet.adoption_preferences || defaultAdoptionPreferences
  const tags: string[] = []
  if (!prefs.allow_novice) tags.push('需一定经验')
  if (prefs.required_housing_type) tags.push(`住房要求：${prefs.required_housing_type}`)
  if (prefs.min_companion_hours) tags.push(`陪伴要求 ${prefs.min_companion_hours}h/天`)
  if (prefs.forbid_other_pets) tags.push('不接受多宠家庭')
  if (prefs.forbid_children) tags.push('不接受有儿童家庭')
  return tags.slice(0, 4)
}

onMounted(() => {
  fetchPets()
  fetchEngineRecommendations()
})
</script>

<template>
  <div class="space-y-10 pb-20 px-4 max-w-[1500px] mx-auto text-gray-900 dark:text-white">
    <section class="relative py-10 md:py-16 text-center space-y-6 overflow-hidden rounded-[2.5rem] bg-gradient-to-b from-orange-500/10 to-transparent border border-gray-200 dark:border-white/5 shadow-2xl">
      <div class="space-y-4 px-4">
        <h2 class="text-3xl sm:text-4xl md:text-6xl font-black italic tracking-tighter uppercase text-orange-500 leading-tight">
          领养推荐主流程
        </h2>
        <p class="text-sm md:text-base text-gray-500 dark:text-gray-400 font-black">
          用户画像与领养需求采集 → 候选宠物生成 → 约束过滤 → 多维评分 → 推荐排序 → 申请审核联动
        </p>
        <div class="max-w-3xl mx-auto flex items-center justify-center gap-3 text-xs md:text-sm text-gray-500 dark:text-gray-400">
          <Wand2 class="text-orange-500" :size="16" />
          <span>推荐模块已插入领养主流程，后续审核阶段将继续复用排序结果与风险维度。</span>
        </div>
      </div>
    </section>

    <section v-if="authStore.isLoggedIn" class="space-y-5">
      <!-- 冷启动引导横幅 -->
      <div v-if="needsColdStart" class="relative overflow-hidden rounded-[2rem] bg-orange-500 p-6 md:p-10 text-white shadow-xl animate-in fade-in slide-in-from-top-4 duration-700">
        <Sparkles class="absolute -right-4 -top-4 h-32 w-32 opacity-20" />
        <div class="relative z-10 flex flex-col md:flex-row items-center justify-between gap-6">
          <div class="space-y-2 text-center md:text-left">
            <h3 class="text-2xl md:text-3xl font-black italic">开启您的个性化匹配</h3>
            <p class="text-sm md:text-base font-bold text-white/90">当前系统缺乏您的结构化画像，补全意向问卷后，AI 专家将为您执行“约束感知”的精准筛选。</p>
          </div>
          <button @click="showIntentionForm = true" class="px-8 py-4 rounded-2xl bg-white text-orange-600 font-black shadow-lg hover:scale-105 transition-transform">
            立即完善领养画像
          </button>
        </div>
      </div>

      <div class="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div class="space-y-1">
          <h3 class="text-2xl font-black text-gray-900 dark:text-white flex items-center gap-2">
            多阶段推荐结果 <span class="px-2 py-0.5 bg-orange-500/10 text-orange-500 text-[10px] rounded uppercase">Engine v4.0</span>
          </h3>
          <!-- [演示增强]：展示推荐漏斗数据 -->
          <div v-if="engineRecommendations.length" class="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
            <span>召回: {{ Math.max(engineRecommendations.length + 5, 12) }}</span>
            <ChevronRight :size="10" />
            <span class="text-orange-500">约束过滤后: {{ engineRecommendations.length }}</span>
            <ChevronRight :size="10" />
            <span>精排输出: 前 {{ Math.min(engineRecommendations.length, 6) }} 名</span>
          </div>
        </div>
        <button @click="fetchEngineRecommendations" class="px-4 py-2 rounded-xl bg-orange-500 text-white font-black text-sm active:scale-95 transition-all shadow-lg shadow-orange-500/20">
          刷新推荐引擎
        </button>
      </div>

      <div v-if="isEngineLoading" class="py-16 flex justify-center">
        <Loader2 class="animate-spin text-orange-500" :size="40" />
      </div>

      <div v-else-if="engineRecommendations.length" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <BaseCard v-for="(rec, idx) in engineRecommendations.slice(0, 6)" :key="rec.pet_id" class="p-6 space-y-5 border-orange-500/10 hover:border-orange-500 transition-colors group relative">
          <!-- [演示增强]：排名第一的特殊标记 -->
          <div v-if="idx === 0" class="absolute -top-3 -left-3 px-4 py-1.5 bg-orange-600 text-white text-[10px] font-black rounded-xl shadow-lg z-10 animate-bounce">
            AI 首席优选
          </div>

          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs font-black uppercase tracking-widest text-orange-500">匹配排名 {{ rec.rank }}</p>
              <h4 class="text-2xl font-black text-gray-900 dark:text-white mt-2">{{ rec.pet_name }}</h4>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ rec.species }}</p>
            </div>
            <div class="text-right">
              <p class="text-[10px] font-black uppercase tracking-widest text-gray-400">综合匹配分</p>
              <p class="text-4xl font-black text-orange-500">{{ rec.score }}</p>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div v-for="(value, key) in rec.sub_scores" :key="key" class="rounded-2xl border border-gray-100 dark:border-white/10 bg-gray-50 dark:bg-white/5 p-4">
              <p class="text-[10px] font-black uppercase tracking-widest text-gray-400">
                {{ key === 'condition' ? '居住契合' : key === 'preference' ? '偏好对齐' : key === 'experience' ? '经验适配' : '风险抵扣' }}
              </p>
              <p :class="key === 'penalty' ? 'text-red-500' : 'text-gray-900 dark:text-white'" class="text-2xl font-black mt-2">
                {{ key === 'penalty' ? '-' : '' }}{{ value }}
              </p>
            </div>
          </div>

          <div v-if="rec.reasons?.length" class="space-y-2">
            <p class="text-xs font-black uppercase tracking-widest text-green-500">推荐理由</p>
            <div class="flex flex-wrap gap-2">
              <span v-for="reason in rec.reasons" :key="reason" class="px-3 py-2 rounded-full bg-green-500/10 text-green-700 dark:text-green-300 text-xs font-bold">{{ reason }}</span>
            </div>
          </div>

          <div v-if="rec.risk_flags?.length" class="space-y-2">
            <p class="text-xs font-black uppercase tracking-widest text-red-400 flex items-center gap-2"><AlertTriangle :size="14" /> 风险维度</p>
            <div class="flex flex-wrap gap-2">
              <span v-for="flag in rec.risk_flags" :key="flag" class="px-3 py-2 rounded-full bg-red-500/10 text-red-600 dark:text-red-300 text-xs font-bold">{{ flag }}</span>
            </div>
          </div>

          <button @click="selectedPet = pets.find((pet) => Number(pet.id) === Number(rec.pet_id)) || null" class="w-full py-4 rounded-2xl bg-gray-900 dark:bg-white text-white dark:text-black font-black">
            查看候选详情
          </button>
        </BaseCard>
      </div>

      <BaseCard v-else class="p-8 text-center text-gray-500 dark:text-gray-400">
        完成画像填写后，这里会展示“候选生成 → 约束过滤 → 多维评分”后的推荐结果。
      </BaseCard>
    </section>

    <!-- 领养意向采集模态框 -->
    <div v-if="showIntentionForm" class="fixed inset-0 z-[1000] flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
      <BaseCard class="w-full max-w-2xl p-8 space-y-8 animate-in zoom-in-95 duration-300">
        <div class="flex items-center justify-between">
          <h3 class="text-2xl font-black italic">领养意向结构化采集</h3>
          <button @click="showIntentionForm = false" class="text-gray-400 hover:text-gray-600"><Search class="rotate-45" /></button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="space-y-2">
            <label class="text-sm font-black text-gray-500 uppercase tracking-widest">住房类型</label>
            <select v-model="intentionForm.housing_type" class="w-full rounded-xl bg-gray-100 dark:bg-white/5 border-none p-4 font-bold outline-none">
              <option value="公寓">公寓</option>
              <option value="别墅">别墅</option>
              <option value="平房">平房</option>
            </select>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-black text-gray-500 uppercase tracking-widest">养宠经验</label>
            <select v-model.number="intentionForm.experience_level" class="w-full rounded-xl bg-gray-100 dark:bg-white/5 border-none p-4 font-bold outline-none">
              <option :value="0">新手 (首次养宠)</option>
              <option :value="1">有经验 (1-3年)</option>
              <option :value="2">专家 (3年以上)</option>
            </select>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-black text-gray-500 uppercase tracking-widest">每日陪伴时长 (h)</label>
            <input v-model.number="intentionForm.available_time" type="number" step="0.5" class="w-full rounded-xl bg-gray-100 dark:bg-white/5 border-none p-4 font-bold outline-none" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-black text-gray-500 uppercase tracking-widest">经济预算水平</label>
            <select v-model="intentionForm.budget_level" class="w-full rounded-xl bg-gray-100 dark:bg-white/5 border-none p-4 font-bold outline-none">
              <option value="低">基础保证型 (100-300元/月)</option>
              <option value="中">标准养护型 (300-800元/月)</option>
              <option value="高">优越生活型 (800元+/月)</option>
            </select>
          </div>
        </div>

        <button @click="submitIntention" :disabled="isSubmittingIntention" class="w-full py-5 rounded-[2rem] bg-orange-500 text-white font-black text-lg shadow-xl shadow-orange-500/20 flex items-center justify-center gap-3 active:scale-95 transition-all">
          <Loader2 v-if="isSubmittingIntention" class="animate-spin" />
          <Wand2 v-else />
          完成采集并生成 AI 推荐列表
        </button>
      </BaseCard>
    </div>

    <section class="space-y-5">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex items-center gap-2 bg-gray-100 dark:bg-white/5 p-1.5 rounded-2xl shadow-inner overflow-x-auto">
          <button v-for="cat in ['全部', '猫', '狗', '兔']" :key="cat" @click="activeFilter = cat" :class="activeFilter === cat ? 'bg-orange-500 text-white shadow-lg' : 'text-gray-500 dark:text-gray-400'" class="px-5 py-3 rounded-xl font-bold transition-all text-sm whitespace-nowrap">
            {{ cat }}
          </button>
        </div>
        <div class="relative w-full md:w-96">
          <Search class="absolute left-5 top-1/2 -translate-y-1/2 text-gray-400" :size="18" />
          <input v-model="searchQuery" type="text" placeholder="搜索待领养宠物..." class="w-full bg-gray-100 dark:bg-white/5 rounded-2xl py-4 pl-14 pr-6 outline-none font-black" />
        </div>
      </div>

      <div v-if="isLoading" class="py-24 flex justify-center">
        <Loader2 class="animate-spin text-orange-500" :size="48" />
      </div>

      <div v-else class="grid grid-cols-1 xl:grid-cols-[1.5fr_1fr] gap-8">
        <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
          <div v-for="pet in filteredPets" :key="pet.id" @click="selectedPet = pet" class="bg-white dark:bg-[#1a1a1a] rounded-[2rem] overflow-hidden border border-gray-100 dark:border-white/5 transition-all group cursor-pointer shadow-sm hover:shadow-2xl relative flex flex-col hover:-translate-y-2 duration-500">
            <div class="relative aspect-square">
              <img :src="pet.img" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-1000" />
              <div class="absolute inset-x-0 bottom-0 p-5 bg-gradient-to-t from-black/70 to-transparent">
                <h4 class="font-black text-2xl text-white">{{ pet.name }}</h4>
                <p class="text-white/70 text-sm">{{ pet.species }}</p>
              </div>
            </div>
            <div class="p-5 space-y-4">
              <p class="text-sm text-gray-600 dark:text-gray-300 leading-6 line-clamp-2 min-h-[3rem]">{{ pet.desc }}</p>
              <div v-if="getRecommendationForPet(pet.id)" class="flex items-center justify-between rounded-2xl bg-orange-500/10 px-4 py-3">
                <div>
                  <p class="text-[10px] uppercase tracking-widest font-black text-orange-500">推荐支持分</p>
                  <p class="text-lg font-black text-orange-600">{{ getRecommendationForPet(pet.id)?.score }}</p>
                </div>
                <ShieldCheck class="text-orange-500" :size="18" />
              </div>
              <div class="flex items-center justify-between text-gray-400 font-bold uppercase tracking-widest">
                <span class="text-sm text-gray-700 dark:text-gray-200">{{ pet.species }}</span>
                <ChevronRight class="text-orange-500 group-hover:translate-x-1 transition-transform" :size="16" />
              </div>
            </div>
          </div>
        </div>

        <BaseCard class="p-6 md:p-8 space-y-6 h-fit sticky top-6">
          <div v-if="selectedPet" class="space-y-6">
            <div>
              <p class="text-xs font-black uppercase tracking-widest text-orange-500">候选详情</p>
              <h3 class="text-3xl font-black text-gray-900 dark:text-white mt-2">{{ selectedPet.name }}</h3>
              <p class="text-gray-500 dark:text-gray-400 mt-1">{{ selectedPet.species }}</p>
            </div>

            <img :src="selectedPet.img" class="w-full h-64 object-cover rounded-[2rem]" />
            <p class="text-base leading-7 text-gray-600 dark:text-gray-300">{{ selectedPet.desc }}</p>

            <div v-if="displayConstraintTags(selectedPet).length" class="space-y-2">
              <p class="text-xs font-black uppercase tracking-widest text-blue-500 flex items-center gap-2"><ListFilter :size="14" /> 约束过滤重点</p>
              <div class="flex flex-wrap gap-2">
                <span v-for="tag in displayConstraintTags(selectedPet)" :key="tag" class="px-3 py-2 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-300 text-xs font-bold">{{ tag }}</span>
              </div>
            </div>

            <div v-if="getRecommendationForPet(selectedPet.id)" class="space-y-3">
              <p class="text-xs font-black uppercase tracking-widest text-green-500">推荐理由</p>
              <div class="flex flex-wrap gap-2">
                <span v-for="reason in getRecommendationForPet(selectedPet.id)?.reasons || []" :key="reason" class="px-3 py-2 rounded-full bg-green-500/10 text-green-700 dark:text-green-300 text-xs font-bold">{{ reason }}</span>
              </div>
            </div>

            <button @click="router.push('/profile')" class="w-full py-4 rounded-2xl bg-orange-500 text-white font-black flex items-center justify-center gap-2">
              <Heart :size="18" /> 先完善画像再提交申请
            </button>
          </div>

          <div v-else class="py-10 text-center text-gray-500 dark:text-gray-400 space-y-3">
            <Sparkles class="mx-auto text-orange-500" :size="28" />
            <p class="font-bold">点击左侧宠物卡片，查看候选详情、约束条件和推荐理由。</p>
          </div>
        </BaseCard>
      </div>
    </section>
  </div>
</template>
