<script setup lang="ts">
import { computed, ref } from 'vue'
import { Salad, Loader2, Sparkles, AlertTriangle, RefreshCcw, ClipboardCheck } from 'lucide-vue-next'
import axios from '../api/index'
import BaseCard from '../components/BaseCard.vue'
import AppSelect from '../components/AppSelect.vue'
import { useAuthStore } from '../store/authStore'

const authStore = useAuthStore()

type NutritionPlan = {
  daily_kcal?: number
  daily_food_g?: number
  feedings_per_day?: number
  daily_water_ml?: string | number
  confidence_level?: number
  requires_vet?: boolean
  recheck_in_days?: number
  adjustment_summary?: string
}

const form = ref({
  pet_name: '',
  species: 'cat',
  age_months: 12,
  weight_kg: 4,
  neutered: true,
  activity_level: 'medium',
  goal: 'maintain',
  food_kcal_per_100g: 380,
  symptoms_text: ''
})

const feedbackForm = ref({
  weight_change: 'stable',
  appetite_status: 'normal',
  stool_status: 'normal',
  activity_change: 'stable'
})

const isGenerating = ref(false)
const isSubmittingFeedback = ref(false)
const isReplanning = ref(false)
const plan = ref<NutritionPlan | null>(null)
const markdown = ref('')
const feedbackStatus = ref('')
const errorMsg = ref('')
const currentPlanId = ref<number | null>(null)
const feedbackId = ref<number | null>(null)
const speciesOptions = [
  { label: '猫', value: 'cat' },
  { label: '狗', value: 'dog' },
]
const activityLevelOptions = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
]
const goalOptions = [
  { label: '维持', value: 'maintain' },
  { label: '减脂', value: 'lose_weight' },
  { label: '增重', value: 'gain_weight' },
]
const weightChangeOptions = [
  { label: '增重', value: 'gain' },
  { label: '稳定', value: 'stable' },
  { label: '减重', value: 'lose' },
]
const appetiteOptions = [
  { label: '良好', value: 'good' },
  { label: '正常', value: 'normal' },
  { label: '较差', value: 'poor' },
]
const stoolOptions = [
  { label: '正常', value: 'normal' },
  { label: '偏软', value: 'soft' },
  { label: '偏硬', value: 'hard' },
  { label: '腹泻', value: 'diarrhea' },
]
const activityChangeOptions = [
  { label: '增加', value: 'increase' },
  { label: '稳定', value: 'stable' },
  { label: '减少', value: 'decrease' },
]

const canSubmit = computed(() => (
  form.value.weight_kg > 0 &&
  form.value.age_months >= 0 &&
  form.value.pet_name.trim() !== ''
))

const hasPlan = computed(() => currentPlanId.value !== null && plan.value !== null)
const canReplan = computed(() => hasPlan.value && feedbackId.value !== null)

const confidenceText = computed(() => {
  if (plan.value?.confidence_level == null) return '未提供'
  return `${Math.round(plan.value.confidence_level * 100)}%`
})

const generatePlan = async () => {
  if (!canSubmit.value) return
  isGenerating.value = true
  errorMsg.value = ''
  feedbackStatus.value = ''
  feedbackId.value = null

  try {
    const symptoms = form.value.symptoms_text
      .split('、')
      .map((s) => s.trim())
      .filter(Boolean)

    const res = await axios.post('/api/nutrition/plan', {
      user_id: authStore.user?.id ?? 0,
      pet_name: form.value.pet_name.trim(),
      species: form.value.species,
      age_months: Number(form.value.age_months),
      weight_kg: Number(form.value.weight_kg),
      neutered: form.value.neutered,
      activity_level: form.value.activity_level,
      goal: form.value.goal,
      food_kcal_per_100g: Number(form.value.food_kcal_per_100g),
      symptoms
    })

    plan.value = res.data.plan
    markdown.value = res.data.explanation_markdown
    currentPlanId.value = res.data.plan_id
    feedbackStatus.value = '初始方案已生成，现在可以提交近 7 天反馈。'
  } catch (err: any) {
    errorMsg.value = err.response?.data?.detail || '生成失败，请检查后端服务。'
  } finally {
    isGenerating.value = false
  }
}

const submitFeedback = async () => {
  if (!currentPlanId.value) return
  isSubmittingFeedback.value = true
  errorMsg.value = ''

  try {
    const res = await axios.post('/api/nutrition/feedback', {
      plan_id: currentPlanId.value,
      ...feedbackForm.value
    })
    feedbackId.value = res.data.feedback_id
    feedbackStatus.value = '近 7 天反馈已记录，现在可以执行营养再规划。'
  } catch (err: any) {
    errorMsg.value = err.response?.data?.detail || '反馈提交失败，请检查后端服务。'
  } finally {
    isSubmittingFeedback.value = false
  }
}

const replanNutrition = async () => {
  if (!currentPlanId.value || !feedbackId.value) return
  isReplanning.value = true
  errorMsg.value = ''

  try {
    const res = await axios.post('/api/nutrition/replan', {
      plan_id: currentPlanId.value,
      feedback_id: feedbackId.value
    })

    plan.value = res.data.plan
    markdown.value = res.data.explanation_markdown
    feedbackStatus.value = '营养再规划已完成，旧方案已归档，当前展示的是最新方案。'
    feedbackId.value = null
  } catch (err: any) {
    errorMsg.value = err.response?.data?.detail || '再规划失败，请检查后端服务。'
  } finally {
    isReplanning.value = false
  }
}
</script>

<template>
  <div class="space-y-8 text-gray-900 dark:text-white">
    <div class="text-center space-y-3">
      <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold uppercase tracking-[0.2em]">
        <Sparkles :size="14" /> 营养专家
      </div>
      <h2 class="text-5xl font-black italic" style="color: var(--text-primary);">营养与喂养专家</h2>
      <p style="color: var(--text-secondary);">先生成初始方案，再提交近 7 天反馈，完成动态营养再规划</p>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-[1.1fr_0.9fr] gap-6">
      <BaseCard class="!p-8 space-y-5">
        <div class="grid grid-cols-2 gap-4">
          <label class="text-xs text-gray-500 dark:text-gray-400" for="pet_name">宠物昵称
            <input id="pet_name" name="pet_name" v-model="form.pet_name" type="text" placeholder="例: 豆包" class="nutrition-field w-full mt-1 rounded-xl px-3 py-2" />
          </label>
          <label class="text-xs text-gray-500 dark:text-gray-400" for="species">宠物类型
            <div class="mt-1">
              <AppSelect v-model="form.species" :options="speciesOptions" />
            </div>
          </label>
          <label class="text-xs text-gray-500 dark:text-gray-400" for="age_months">年龄（月）
            <input id="age_months" name="age_months" v-model.number="form.age_months" type="number" min="0" class="nutrition-field w-full mt-1 rounded-xl px-3 py-2" />
          </label>
          <label class="text-xs text-gray-500 dark:text-gray-400" for="weight_kg">体重（kg）
            <input id="weight_kg" name="weight_kg" v-model.number="form.weight_kg" type="number" min="0.1" step="0.1" class="nutrition-field w-full mt-1 rounded-xl px-3 py-2" />
          </label>
          <label class="text-xs text-gray-500 dark:text-gray-400" for="food_kcal">粮食能量(kcal/100g)
            <input id="food_kcal" name="food_kcal" v-model.number="form.food_kcal_per_100g" type="number" min="1" class="nutrition-field w-full mt-1 rounded-xl px-3 py-2" />
          </label>
          <label class="text-xs text-gray-500 dark:text-gray-400" for="activity_level">活动量
            <div class="mt-1">
              <AppSelect v-model="form.activity_level" :options="activityLevelOptions" />
            </div>
          </label>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <label class="text-xs text-gray-500 dark:text-gray-400" for="goal">目标
            <div class="mt-1">
              <AppSelect v-model="form.goal" :options="goalOptions" />
            </div>
          </label>
          <label class="text-xs text-gray-500 dark:text-gray-400 flex items-end pb-3 gap-2" for="neutered">
            <input id="neutered" name="neutered" type="checkbox" v-model="form.neutered" /> 已绝育
          </label>
        </div>

        <label class="text-xs text-gray-500 dark:text-gray-400" for="symptoms">特殊情况（使用“、”分隔）
          <input id="symptoms" name="symptoms" v-model="form.symptoms_text" type="text" placeholder="软便、掉毛" class="nutrition-field w-full mt-1 rounded-xl px-3 py-2" />
        </label>

        <button @click="generatePlan" :disabled="isGenerating || !canSubmit" class="w-full bg-emerald-500 hover:bg-emerald-600 disabled:bg-gray-700 rounded-2xl py-3 font-black text-white flex items-center justify-center gap-2 transition-all">
          <Loader2 v-if="isGenerating" class="animate-spin" :size="18" />
          <Salad v-else :size="18" />
          生成喂养方案
        </button>

        <div class="rounded-3xl border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 p-5 space-y-4" :class="{ 'opacity-70': !hasPlan }">
          <div class="flex items-center gap-2 text-sm font-black text-gray-900 dark:text-white">
            <ClipboardCheck :size="16" class="text-emerald-400" />
            近 7 天执行反馈
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label class="text-xs text-gray-500 dark:text-gray-400">体重变化
              <div class="mt-1">
                <AppSelect v-model="feedbackForm.weight_change" :options="weightChangeOptions" />
              </div>
            </label>
            <label class="text-xs text-gray-500 dark:text-gray-400">食欲状态
              <div class="mt-1">
                <AppSelect v-model="feedbackForm.appetite_status" :options="appetiteOptions" />
              </div>
            </label>
            <label class="text-xs text-gray-500 dark:text-gray-400">排便情况
              <div class="mt-1">
                <AppSelect v-model="feedbackForm.stool_status" :options="stoolOptions" />
              </div>
            </label>
            <label class="text-xs text-gray-500 dark:text-gray-400">活动量变化
              <div class="mt-1">
                <AppSelect v-model="feedbackForm.activity_change" :options="activityChangeOptions" />
              </div>
            </label>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <button @click="submitFeedback" :disabled="!hasPlan || isSubmittingFeedback" class="w-full bg-sky-500 hover:bg-sky-600 disabled:bg-gray-700 rounded-2xl py-3 font-black text-white flex items-center justify-center gap-2 transition-all">
              <Loader2 v-if="isSubmittingFeedback" class="animate-spin" :size="18" />
              <ClipboardCheck v-else :size="18" />
              提交近 7 天反馈
            </button>

            <button @click="replanNutrition" :disabled="!canReplan || isReplanning" class="w-full bg-amber-500 hover:bg-amber-600 disabled:bg-gray-700 rounded-2xl py-3 font-black text-white flex items-center justify-center gap-2 transition-all">
              <Loader2 v-if="isReplanning" class="animate-spin" :size="18" />
              <RefreshCcw v-else :size="18" />
              重新规划营养方案
            </button>
          </div>

          <p class="text-xs text-gray-600 dark:text-gray-400">流程说明：先生成初始方案，再提交反馈，最后触发 NutritionOptimizer 进行闭环再规划。</p>
        </div>

        <p v-if="feedbackStatus" class="text-emerald-400 text-sm">{{ feedbackStatus }}</p>
        <p v-if="errorMsg" class="text-red-400 text-sm flex items-center gap-2"><AlertTriangle :size="16" /> {{ errorMsg }}</p>
      </BaseCard>

      <BaseCard class="!p-8" v-if="plan">
        <div class="flex items-start justify-between gap-4 mb-4">
          <div>
            <h3 class="text-xl font-black text-gray-900 dark:text-white">结构化结果</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">当前展示的是最新激活方案</p>
          </div>
          <div v-if="currentPlanId" class="text-xs text-gray-600 dark:text-gray-400">方案 ID：{{ currentPlanId }}</div>
        </div>

        <div class="grid grid-cols-2 gap-3 text-sm">
          <div class="bg-gray-50 dark:bg-white/5 rounded-xl p-3">每日热量：<span class="font-bold text-emerald-400">{{ plan.daily_kcal }} kcal</span></div>
          <div class="bg-gray-50 dark:bg-white/5 rounded-xl p-3">每日喂食：<span class="font-bold text-emerald-400">{{ plan.daily_food_g }} g</span></div>
          <div class="bg-gray-50 dark:bg-white/5 rounded-xl p-3">喂食频次：<span class="font-bold text-emerald-400">{{ plan.feedings_per_day }} 次/天</span></div>
          <div class="bg-gray-50 dark:bg-white/5 rounded-xl p-3">饮水建议：<span class="font-bold text-emerald-400">{{ plan.daily_water_ml }} ml</span></div>
          <div class="bg-gray-50 dark:bg-white/5 rounded-xl p-3">置信度：<span class="font-bold text-amber-400">{{ confidenceText }}</span></div>
          <div class="bg-gray-50 dark:bg-white/5 rounded-xl p-3">复查周期：<span class="font-bold text-emerald-400">{{ plan.recheck_in_days ?? '未提供' }} 天</span></div>
        </div>

        <div class="mt-4 rounded-2xl border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-black/20 p-4 text-sm">
          <div class="text-gray-600 dark:text-gray-400">就医建议</div>
          <div class="mt-1 font-bold" :class="plan.requires_vet ? 'text-red-400' : 'text-emerald-400'">
            {{ plan.requires_vet ? '建议尽快联系兽医' : '当前可继续家庭观察' }}
          </div>
          <p v-if="plan.adjustment_summary" class="mt-3 text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-6">{{ plan.adjustment_summary }}</p>
        </div>

        <div class="mt-5 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-7">{{ markdown }}</div>
      </BaseCard>
    </div>
  </div>
</template>

<style scoped>
.nutrition-field {
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgb(229 231 235);
  color: rgb(17 24 39);
}

.nutrition-field::placeholder {
  color: rgb(156 163 175);
}

.nutrition-field:focus {
  outline: none;
  border-color: rgb(16 185 129);
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.12);
}

:global(.dark) .nutrition-field {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

:global(.dark) .nutrition-field::placeholder {
  color: rgb(75 85 99);
}

</style>
