<template>
  <div class="p-8 space-y-8 bg-gray-50 min-h-screen">
    <!-- A. 顶部统计概览 -->
    <div class="flex justify-between items-end">
      <div>
        <h1 class="text-3xl font-black text-gray-900">系统运行监控大盘</h1>
        <p class="text-gray-500 mt-1">实时监控全平台领养数据与 Agent 运行状态</p>
      </div>
      <div class="flex gap-3">
        <button class="bg-white border border-gray-200 px-4 py-2 rounded-xl text-sm font-bold shadow-sm hover:bg-gray-50 transition-all flex items-center gap-2">
          <Download :size="16"/> 导出报表
        </button>
        <button class="bg-orange-500 text-white px-4 py-2 rounded-xl text-sm font-bold shadow-lg shadow-orange-200 hover:bg-orange-600 transition-all">
          发布全站公告
        </button>
      </div>
    </div>

    <!-- B. 核心指标卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <div v-for="stat in stats" :key="stat.label" 
           class="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start">
          <p class="text-sm font-medium text-gray-400 uppercase tracking-wider">{{ stat.label }}</p>
          <div :class="stat.trend > 0 ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'" 
               class="px-2 py-0.5 rounded-lg text-[10px] font-bold">
            {{ stat.trend > 0 ? '+' : '' }}{{ stat.trend }}%
          </div>
        </div>
        <div class="mt-4 flex items-baseline gap-2">
          <h2 class="text-4xl font-black text-gray-800">{{ stat.value }}</h2>
          <span class="text-xs text-gray-400">本季度</span>
        </div>
        <div class="mt-4 h-1 w-full bg-gray-100 rounded-full overflow-hidden">
          <div :class="stat.color" class="h-full rounded-full" :style="{ width: stat.progress + '%' }"></div>
        </div>
      </div>
    </div>

    <!-- C. 深度分析图表区 -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- 趋势图占位 -->
      <div class="lg:col-span-2 bg-white p-8 rounded-[2rem] border border-gray-100 shadow-sm">
        <div class="flex items-center justify-between mb-8">
          <h3 class="font-bold text-xl">领养注册人数趋势 (按季度)</h3>
          <select class="text-xs bg-gray-50 border-none rounded-lg px-3 py-1">
            <option>2026年数据</option>
            <option>2025年数据</option>
          </select>
        </div>
        <div class="h-64 flex items-end justify-between px-4 gap-4">
          <div v-for="(val, i) in [40, 65, 90, 75, 85, 60]" :key="i" 
               class="flex-1 group relative">
            <div :style="{ height: val + '%' }" 
                 class="w-full bg-orange-400 rounded-2xl group-hover:bg-orange-600 transition-all duration-500 cursor-pointer shadow-sm shadow-orange-100 relative">
              <span class="absolute -top-8 left-1/2 -translate-x-1/2 text-xs font-bold text-orange-600 opacity-0 group-hover:opacity-100 transition-opacity">
                {{ val * 10 }}人
              </span>
            </div>
            <p class="text-center mt-4 text-[10px] font-bold text-gray-400 uppercase tracking-widest">Q{{ (i % 4) + 1 }}</p>
          </div>
        </div>
      </div>

      <!-- 分类占比占位 -->
      <div class="bg-white p-8 rounded-[2rem] border border-gray-100 shadow-sm flex flex-col">
        <h3 class="font-bold text-xl mb-8">流浪动物分类统计</h3>
        <div class="flex-1 flex flex-col items-center justify-center relative">
          <!-- 模拟饼图 -->
          <div class="w-48 h-48 rounded-full border-[32px] border-orange-500 border-l-orange-100 border-b-orange-200 rotate-45 relative">
            <div class="absolute inset-0 flex flex-col items-center justify-center -rotate-45">
              <span class="text-3xl font-black text-gray-800">452</span>
              <span class="text-[10px] text-gray-400 font-bold uppercase">总库存</span>
            </div>
          </div>
          <!-- 标签说明 -->
          <div class="mt-10 w-full grid grid-cols-2 gap-4">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-orange-500"></div>
              <span class="text-xs font-bold text-gray-600">待救助 (65%)</span>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-orange-200"></div>
              <span class="text-xs font-bold text-gray-600">待绝育 (20%)</span>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-orange-100"></div>
              <span class="text-xs font-bold text-gray-600">急寻主 (15%)</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- D. 最近活动日志 (Agent 审计追踪) -->
    <div class="bg-white p-8 rounded-[2rem] border border-gray-100 shadow-sm">
      <h3 class="font-bold text-xl mb-6">Agent 系统活动日志</h3>
      <div class="space-y-4">
        <div v-for="log in logs" :key="log.time" class="flex items-center gap-4 p-4 rounded-2xl hover:bg-gray-50 transition-colors">
          <span class="text-[10px] font-mono text-gray-400 bg-gray-100 px-2 py-1 rounded">{{ log.time }}</span>
          <div :class="log.typeColor" class="w-2 h-2 rounded-full"></div>
          <p class="text-sm text-gray-600 flex-1"><span class="font-bold text-gray-900">[{{ log.agent }}]</span> {{ log.action }}</p>
          <span class="text-[10px] font-bold text-orange-500 cursor-pointer">详情</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Download } from 'lucide-vue-next';
import { ref } from 'vue';

const stats = [
  { label: '累计注册用户', value: '1,280', trend: 12, progress: 75, color: 'bg-orange-500' },
  { label: '流浪动物入库', value: '452', trend: -5, progress: 40, color: 'bg-orange-300' },
  { label: '待处理领养申请', value: '24', trend: 18, progress: 20, color: 'bg-red-400' },
  { label: '本月捐赠金额', value: '¥8,500', trend: 25, progress: 90, color: 'bg-green-400' },
];

const logs = ref([
  { time: '14:22:15', agent: 'Navigator', action: '成功路由用户 ID:9527 的领养申请至医疗专家评估。', typeColor: 'bg-green-500' },
  { time: '14:15:02', agent: 'MedicalExpert', action: '完成对宠物“布丁”的健康画像生成，置信度 94%。', typeColor: 'bg-blue-500' },
  { time: '13:58:33', agent: 'AuditExpert', action: '检测到异常登录尝试，已自动冻结相关 IP 段。', typeColor: 'bg-orange-500' },
  { time: '13:45:10', agent: 'System', action: '数据库自动备份完成，同步至云端存储。', typeColor: 'bg-gray-400' },
]);
</script>
