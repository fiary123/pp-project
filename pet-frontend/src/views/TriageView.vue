<template>
  <div class="space-y-8">
    <div class="text-center space-y-4">
      <h2 class="text-4xl font-black text-white drop-shadow-xl">宠医 AI 智能分诊</h2>
      <p class="text-gray-300">描述症状，AI 专家团将为您提供初步诊断建议</p>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
      <BaseCard class="h-96 flex flex-col">
        <h3 class="font-bold text-xl mb-4 text-orange-400">症状描述</h3>
        <textarea 
          class="flex-1 bg-white/5 border border-white/10 rounded-2xl p-4 text-white focus:outline-none focus:border-orange-500 transition-colors resize-none"
          placeholder="例如：我家猫咪今天精神萎靡，不爱吃粮，还有轻微呕吐..."
        ></textarea>
        <button class="mt-4 bg-orange-500 py-3 rounded-xl font-bold hover:bg-orange-600 transition-all shadow-lg shadow-orange-500/20">
          立即分析
        </button>
      </BaseCard>
      
      <BaseCard class="h-96">
        <h3 class="font-bold text-xl mb-4 text-green-400">诊断报告 (AI 生成)</h3>
        <div class="text-gray-400 text-sm flex items-center justify-center h-full border-2 border-dashed border-white/5 rounded-2xl">
          等待输入分析...
        </div>
      </BaseCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import BaseCard from '../components/BaseCard.vue'
</script>
