<script setup lang="ts">
import { ref, computed } from 'vue'
import { Salad, Loader2, Sparkles, AlertTriangle } from 'lucide-vue-next'
import axios from 'axios'
import BaseCard from '../components/BaseCard.vue'
import { useAuthStore } from '../store/authStore'

const authStore = useAuthStore()

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

const isLoading = ref(false)
const plan = ref<any | null>(null)
const markdown = ref('')
const errorMsg = ref('')

const canSubmit = computed(() => form.value.weight_kg > 0 && form.value.age_months >= 0 && form.value.pet_name.trim() !== '')

const generatePlan = async () => {
  if (!canSubmit.value) return
  isLoading.value = true
  errorMsg.value = ''
  try {
    const symptoms = form.value.symptoms_text
      .split('、')
      .map(s => s.trim())
      .filter(Boolean)

    const res = await axios.post('http://127.0.0.1:8000/api/nutrition/plan', {
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
  } catch (err: any) {
    errorMsg.value = err.response?.data?.detail || '生成失败，请检查后端服务。'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="space-y-8">
    <div class="text-center space-y-3">
      <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold uppercase tracking-[0.2em]">
        <Sparkles :size="14" /> Nutrition Expert
      </div>
      <h2 class="text-5xl font-black text-white italic">营养与喂养专家</h2>
      <p class="text-gray-400">按年龄、体重、绝育状态、活动量生成结构化喂养方案</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <BaseCard class="!p-8 space-y-5">
        <div class="grid grid-cols-2 gap-4">
          <label class="text-xs text-gray-400">宠物类型
            <select v-model="form.species" class="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white">
              <option value="cat">猫</option>
              <option value="dog">狗</option>
            </select>
          </label>
          <label class="text-xs text-gray-400">年龄（月）
            <input v-model.number="form.age_months" type="number" min="0" class="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white" />
          </label>
          <label class="text-xs text-gray-400">体重（kg）
            <input v-model.number="form.weight_kg" type="number" min="0.1" step="0.1" class="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white" />
          </label>
          <label class="text-xs text-gray-400">粮食能量(kcal/100g)
            <input v-model.number="form.food_kcal_per_100g" type="number" min="1" class="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white" />
          </label>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <label class="text-xs text-gray-400">活动量
            <select v-model="form.activity_level" class="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white">
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
            </select>
          </label>
          <label class="text-xs text-gray-400">目标
            <select v-model="form.goal" class="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white">
              <option value="maintain">维持</option>
              <option value="lose_weight">减脂</option>
              <option value="gain_weight">增重</option>
            </select>
          </label>
        </div>

        <label class="text-xs text-gray-400 flex items-center gap-2">
          <input type="checkbox" v-model="form.neutered" /> 已绝育
        </label>

        <label class="text-xs text-gray-400">特殊情况（使用“、”分隔）
          <input v-model="form.symptoms_text" type="text" placeholder="软便、掉毛" class="w-full mt-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white" />
        </label>

        <button @click="generatePlan" :disabled="isLoading || !canSubmit" class="w-full bg-emerald-500 hover:bg-emerald-600 disabled:bg-gray-700 rounded-2xl py-3 font-black text-white flex items-center justify-center gap-2 transition-all">
          <Loader2 v-if="isLoading" class="animate-spin" :size="18" />
          <Salad v-else :size="18" />
          生成喂养方案
        </button>

        <p v-if="errorMsg" class="text-red-400 text-sm flex items-center gap-2"><AlertTriangle :size="16" /> {{ errorMsg }}</p>
      </BaseCard>

      <BaseCard class="!p-8" v-if="plan">
        <h3 class="text-xl font-black text-white mb-4">结构化结果</h3>
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div class="bg-white/5 rounded-xl p-3">每日热量：<span class="font-bold text-emerald-400">{{ plan.daily_kcal }} kcal</span></div>
          <div class="bg-white/5 rounded-xl p-3">每日喂食：<span class="font-bold text-emerald-400">{{ plan.daily_food_g }} g</span></div>
          <div class="bg-white/5 rounded-xl p-3">喂食频次：<span class="font-bold text-emerald-400">{{ plan.feedings_per_day }} 次/天</span></div>
          <div class="bg-white/5 rounded-xl p-3">饮水建议：<span class="font-bold text-emerald-400">{{ plan.daily_water_ml }} ml</span></div>
        </div>

        <div class="mt-5 text-sm text-gray-300 whitespace-pre-wrap leading-7">{{ markdown }}</div>
      </BaseCard>
    </div>
  </div>
</template>
