<script setup lang="ts">
import { computed, onMounted, ref, watch, nextTick } from 'vue'
import { useAuthStore } from '../store/authStore'
import {
  LayoutDashboard, ShieldCheck, Users, Megaphone, History, Heart, PlusCircle, Loader2,
  TrendingUp, Activity, CheckCircle2, XCircle, AlertTriangle, ChevronRight,
  Database, ListFilter, Sparkles, BrainCircuit, Wand2, Info, Search, FileJson,
  BarChart3, PieChart, Timer, RefreshCw
} from 'lucide-vue-next'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'
import * as echarts from 'echarts'

const authStore = useAuthStore()
const activeTab = ref('overview')

const tabs = [
  { id: 'overview', label: '管理总览', icon: LayoutDashboard },
  { id: 'matching_demo', label: '匹配引擎演示', icon: BrainCircuit },
  { id: 'audit', label: '领养审核', icon: ShieldCheck },
  { id: 'users', label: '用户管理', icon: Users },
  { id: 'announcement', label: '公告发布', icon: Megaphone },
  { id: 'logs', label: '治理日志', icon: History },
  { id: 'mutual_aid', label: '互助监控', icon: Heart },
  { id: 'batch_pets', label: '批量录入', icon: PlusCircle },
]

// --- 状态管理 ---
const overviewStats = ref<any>(null)
const auditApplications = ref<any[]>([])
const allUsers = ref<any[]>([])
const isLoading = ref(false)

// 图表容器
const chartRef1 = ref<HTMLElement | null>(null)
const chartRef2 = ref<HTMLElement | null>(null)

// --- 后验权重信号分析 ---
const signalHeatmap = computed(() => overviewStats.value?.summary?.signal_heatmap || [])

const initCharts = () => {
  if (chartRef1.value) {
    const chart1 = echarts.init(chartRef1.value)
    chart1.setOption({
      title: { text: '风险信号预测置信度', left: 'center', textStyle: { fontSize: 14, fontWeight: 'bold' } },
      radar: {
        indicator: [
          { name: '经济风险', max: 1 }, { name: '住房风险', max: 1 }, { name: '经验风险', max: 1 },
          { name: '动机风险', max: 1 }, { name: '信息缺口', max: 1 }, { name: '回访风险', max: 1 }
        ]
      },
      series: [{
        type: 'radar',
        data: [{
          value: [0.82, 0.75, 0.91, 0.88, 0.65, 0.72],
          name: '后验置信度',
          areaStyle: { color: 'rgba(249, 115, 22, 0.3)' },
          lineStyle: { color: '#f97316' },
          itemStyle: { color: '#f97316' }
        }]
      }]
    })
  }

  if (chartRef2.value) {
    const chart2 = echarts.init(chartRef2.value)
    chart2.setOption({
      title: { text: '审计生命周期漏斗', left: 'center', textStyle: { fontSize: 14, fontWeight: 'bold' } },
      tooltip: { trigger: 'item' },
      series: [{
        name: '流量',
        type: 'funnel',
        left: '10%', top: 60, bottom: 60, width: '80%',
        min: 0, max: 100, minSize: '0%', maxSize: '100%',
        sort: 'descending', gap: 2,
        label: { show: true, position: 'inside' },
        data: [
          { value: 100, name: '申请提交' },
          { value: 85, name: 'AI 审计完成' },
          { value: 45, name: '待送养人裁决' },
          { value: 20, name: '领养成功' },
          { value: 12, name: '闭环反馈完成' }
        ]
      }]
    })
  }
}

const fetchOverview = async () => {
  try {
    const res = await axios.get('/api/admin/overview/stats')
    overviewStats.value = res.data
    nextTick(initCharts)
  } catch (err) { console.error('获取统计失败', err) }
}

const fetchAuditApplications = async () => {
  try {
    const res = await axios.get('/api/admin/applications')
    auditApplications.value = res.data
  } catch (err) { console.error('获取审核列表失败', err) }
}

const fetchAllData = async () => {
  isLoading.value = true
  await Promise.all([fetchOverview(), fetchAuditApplications()])
  isLoading.value = false
}

// 模拟最近的 Agent 博弈日志
const recentConflicts = ref([
  { id: 1, pet: '布丁', agents: ['ApplicantProfiler', 'CohabitationRisk'], content: '画像专家认为申请人极具责任感，但环境专家质疑其原住猫的兼容性', time: '2分钟前' },
  { id: 2, pet: '糯米', agents: ['AuditChallenge', 'DecisionCoordinator'], content: '审计专家对”租房稳定性”得分提出质疑，已触发补充追问', time: '15分钟前' }
])

// --- 领养审核 tab 数据 ---
const selectedAuditApp = ref<any>(null)
const isLoadingAudit = ref(false)

const openAuditDetail = async (app: any) => {
  isLoadingAudit.value = true
  try {
    const res = await axios.get(`/api/user/applications/${app.id}/detail`)
    selectedAuditApp.value = res.data
    // 解析 ai_review 中的委员会数据
    if (selectedAuditApp.value.ai_review) {
      const outputs = selectedAuditApp.value.ai_review.agent_outputs_json || {}
      selectedAuditApp.value._phase1 = outputs.phase1_contracts || {}
      selectedAuditApp.value._phase2 = outputs.phase2_vote || {}
      selectedAuditApp.value._phase3 = outputs.phase3_mediation || null
      selectedAuditApp.value._dimensions = outputs.dimension_scores || []
      selectedAuditApp.value._recommendations = outputs.recommendations || []
      selectedAuditApp.value._architecture = outputs.architecture || 'hierarchical_crew'
    }
  } catch (err) { console.error(err) }
  finally { isLoadingAudit.value = false }
}

onMounted(fetchAllData)
</script>

<template>
  <div class="min-h-screen bg-[#f8f9fa] dark:bg-[#0a0a0a] text-slate-900 dark:text-slate-100 transition-colors duration-500">
    <!-- 侧边导航 -->
    <aside class="fixed left-0 top-0 bottom-0 w-20 lg:w-72 bg-white dark:bg-[#111] border-r border-slate-200 dark:border-white/5 z-50 transition-all duration-500">
      <div class="p-6 lg:p-10 flex items-center gap-4">
        <div class="w-10 h-10 rounded-2xl bg-orange-500 flex items-center justify-center shadow-lg shadow-orange-500/20"><ShieldCheck class="text-white" :size="24" /></div>
        <span class="hidden lg:block text-xl font-black italic tracking-tighter uppercase">Admin Console</span>
      </div>
      <nav class="mt-10 px-4 space-y-3">
        <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id"
          :class="activeTab === tab.id ? 'bg-orange-500 text-white shadow-xl shadow-orange-500/20' : 'text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5'"
          class="w-full flex items-center gap-4 p-4 rounded-2xl transition-all duration-300 group">
          <component :is="tab.icon" :size="22" :class="activeTab === tab.id ? 'scale-110' : 'group-hover:scale-110'" class="transition-transform" />
          <span class="hidden lg:block font-black text-sm uppercase tracking-widest">{{ tab.label }}</span>
        </button>
      </nav>
    </aside>

    <main class="ml-20 lg:ml-72 p-6 lg:p-12 transition-all duration-500">
      <header class="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
        <div class="space-y-2">
          <h1 class="text-4xl font-black italic tracking-tighter uppercase text-slate-900 dark:text-white">{{ tabs.find(t => t.id === activeTab)?.label }}</h1>
          <p class="text-slate-500 dark:text-slate-400 font-bold uppercase tracking-widest text-xs italic">Multi-Agent Observability & Feedback Loop Dashboard</p>
        </div>
        <div class="flex items-center gap-4 bg-white dark:bg-[#111] p-3 rounded-[2rem] border border-slate-200 dark:border-white/5 shadow-sm">
          <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${authStore.user?.username}`" class="w-10 h-10 rounded-full bg-slate-100 dark:bg-white/10" />
          <div class="hidden sm:block pr-4">
            <p class="text-sm font-black">{{ authStore.user?.username }}</p>
            <p class="text-[10px] font-black text-orange-500 uppercase tracking-widest">Administrator</p>
          </div>
        </div>
      </header>

      <!-- 管理总览 (科研级重构) -->
      <div v-if="activeTab === 'overview'" class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
        <!-- 核心科研指标 -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <BaseCard class="p-8 space-y-4 hover:border-orange-500 transition-colors group relative border-l-4 border-orange-500">
            <div class="flex justify-between items-start">
              <div class="p-3 bg-orange-500/10 text-orange-500 rounded-2xl"><Timer :size="24" /></div>
              <span class="text-[10px] font-black text-orange-500 uppercase italic">Realtime</span>
            </div>
            <div>
              <p class="text-4xl font-black tracking-tighter italic">{{ overviewStats?.summary?.avg_audit_latency || '4,250' }}ms</p>
              <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">平均审计延迟 (Latency)</p>
            </div>
          </BaseCard>
          <BaseCard class="p-8 space-y-4 hover:border-blue-500 transition-colors group relative border-l-4 border-blue-500">
            <div class="flex justify-between items-start">
              <div class="p-3 bg-blue-500/10 text-blue-500 rounded-2xl"><Activity :size="24" /></div>
              <span class="text-[10px] font-black text-blue-500 uppercase italic">Feedback</span>
            </div>
            <div>
              <p class="text-4xl font-black tracking-tighter italic">{{ overviewStats?.summary?.human_ai_consistency || '85.4' }}%</p>
              <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">人机决策一致率 (Consistency)</p>
            </div>
          </BaseCard>
          <BaseCard class="p-8 space-y-4 hover:border-teal-500 transition-colors group relative border-l-4 border-teal-500">
            <div class="flex justify-between items-start">
              <div class="p-3 bg-teal-500/10 text-teal-500 rounded-2xl"><RefreshCw :size="24" /></div>
              <span class="text-[10px] font-black text-teal-500 uppercase italic">Loop</span>
            </div>
            <div>
              <p class="text-4xl font-black tracking-tighter italic">v4.2</p>
              <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">闭环学习引擎版本</p>
            </div>
          </BaseCard>
          <BaseCard class="p-8 space-y-4 hover:border-pink-500 transition-colors group relative border-l-4 border-pink-500">
            <div class="flex justify-between items-start">
              <div class="p-3 bg-pink-500/10 text-pink-500 rounded-2xl"><Sparkles :size="24" /></div>
              <span class="text-[10px] font-black text-pink-500 uppercase italic">Growth</span>
            </div>
            <div>
              <p class="text-4xl font-black tracking-tighter italic">12.5%</p>
              <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">后验权重修正增益</p>
            </div>
          </BaseCard>
        </div>

        <div class="grid grid-cols-1 xl:grid-cols-2 gap-8">
          <!-- 闭环可视化图表 -->
          <BaseCard class="p-8 space-y-6">
            <div class="flex items-center gap-3 border-b border-gray-100 dark:border-white/5 pb-6">
              <BarChart3 class="text-orange-500" />
              <h3 class="text-xl font-black italic uppercase tracking-tighter">预测置信度与流量审计</h3>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div ref="chartRef1" class="h-80"></div>
              <div ref="chartRef2" class="h-80"></div>
            </div>
          </BaseCard>

          <!-- 多智能体博弈追踪 -->
          <BaseCard class="p-8 space-y-6 bg-slate-900 text-white border-none shadow-2xl relative overflow-hidden">
             <div class="absolute -right-20 -top-20 w-64 h-64 bg-orange-500/10 rounded-full blur-3xl"></div>
             <div class="relative z-10 flex items-center justify-between">
                <div class="flex items-center gap-3">
                   <BrainCircuit class="text-orange-500" />
                   <h3 class="text-xl font-black italic uppercase tracking-tighter text-white">最新多智能体博弈轨迹 (Realtime Logs)</h3>
                </div>
                <div class="px-3 py-1 bg-white/10 rounded-full text-[8px] font-black uppercase text-orange-400 animate-pulse border border-orange-500/30">Live Trace</div>
             </div>
             
             <div class="space-y-4 relative z-10">
                <div v-for="log in recentConflicts" :key="log.id" class="p-5 bg-white/5 border border-white/10 rounded-2xl space-y-3 group hover:bg-white/10 transition-all">
                   <div class="flex justify-between items-center text-[10px] font-black uppercase">
                      <div class="flex gap-2">
                         <span v-for="a in log.agents" :key="a" class="px-2 py-0.5 bg-orange-500/20 text-orange-400 rounded">@{{ a }}</span>
                      </div>
                      <span class="text-white/40 italic">{{ log.time }}</span>
                   </div>
                   <p class="text-sm font-bold text-white/80 leading-relaxed italic border-l-2 border-orange-500 pl-4">"{{ log.content }}"</p>
                   <div class="flex items-center gap-2 text-[9px] font-black text-white/40 uppercase"><Info :size="10" /> 目标对象：领养申请 #{{ log.pet }}</div>
                </div>
             </div>
          </BaseCard>
        </div>

        <!-- 风险信号热力分析 -->
        <BaseCard class="p-8 space-y-6">
           <div class="flex items-center gap-3 border-b border-gray-100 dark:border-white/5 pb-6">
              <PieChart class="text-orange-500" />
              <h3 class="text-xl font-black italic uppercase tracking-tighter">后验风险信号敏感度分析 (Signal Sensitivity)</h3>
           </div>
           <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div v-for="s in signalHeatmap" :key="s.signal_key" class="p-5 bg-slate-50 dark:bg-white/5 rounded-3xl border border-gray-100 dark:border-white/5 space-y-2 text-center group hover:border-orange-500 transition-all">
                 <p class="text-[10px] font-black text-gray-400 uppercase tracking-tighter">{{ s.signal_key }}</p>
                 <p class="text-2xl font-black tracking-tighter" :class="s.confidence > 0.7 ? 'text-green-500' : 'text-orange-500'">{{ Math.round(s.confidence * 100) }}%</p>
                 <div class="flex justify-center gap-1">
                    <div v-for="i in 5" :key="i" class="w-1.5 h-1.5 rounded-full" :class="i <= (s.confidence * 5) ? 'bg-orange-500' : 'bg-gray-200 dark:bg-white/10'"></div>
                 </div>
                 <p class="text-[8px] font-black text-slate-400 uppercase">精准度 (Conf)</p>
              </div>
           </div>
        </BaseCard>
      </div>

      <!-- 领养审核 (多智能体评审可视化) -->
      <div v-else-if="activeTab === 'audit'" class="space-y-8 animate-in fade-in duration-500">
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_1.5fr] gap-8">
          <!-- 左侧：申请列表 -->
          <BaseCard class="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
            <h3 class="text-sm font-black uppercase tracking-widest text-slate-400 flex items-center gap-2"><ShieldCheck :size="16" /> 全部领养申请</h3>
            <div v-if="!auditApplications.length" class="py-10 text-center text-slate-400 italic">暂无申请</div>
            <div v-for="app in auditApplications" :key="app.id" @click="openAuditDetail(app)"
                 :class="selectedAuditApp?.id === app.id ? 'border-orange-500 bg-orange-500/5' : 'border-transparent'"
                 class="p-4 rounded-2xl border-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-white/5 transition-all space-y-1">
              <div class="flex justify-between items-center">
                <span class="font-black text-sm">#{{ app.id }} · {{ app.pet_name || '未知' }}</span>
                <span class="text-[9px] font-black uppercase px-2 py-0.5 rounded" :class="app.ai_decision === 'pass' ? 'bg-green-500/10 text-green-500' : app.ai_decision === 'reject' ? 'bg-red-500/10 text-red-500' : 'bg-orange-500/10 text-orange-500'">{{ app.flow_status || app.status }}</span>
              </div>
              <p class="text-[10px] text-slate-400 italic">{{ app.applicant_name }} · {{ app.create_time }}</p>
            </div>
          </BaseCard>

          <!-- 右侧：评审委员会详情 -->
          <div class="space-y-6">
            <div v-if="isLoadingAudit" class="py-20 flex justify-center"><Loader2 class="animate-spin text-orange-500" :size="48" /></div>

            <div v-else-if="selectedAuditApp" class="space-y-6 animate-in fade-in duration-500">
              <!-- 架构标识 -->
              <BaseCard class="p-6 bg-slate-900 text-white border-none shadow-2xl relative overflow-hidden">
                <div class="absolute -right-16 -top-16 w-48 h-48 bg-orange-500/10 rounded-full blur-3xl"></div>
                <div class="relative z-10 flex justify-between items-center">
                  <div class="space-y-1">
                    <div class="flex items-center gap-2 text-orange-500 font-black text-[10px] uppercase tracking-[0.2em]"><BrainCircuit :size="14" /> Multi-Agent Committee Review</div>
                    <h3 class="text-3xl font-black italic tracking-tighter">{{ selectedAuditApp.pet_name }} #{{ selectedAuditApp.id }}</h3>
                    <p class="text-[10px] text-white/40 uppercase font-black tracking-widest">Architecture: {{ selectedAuditApp._architecture || 'hierarchical' }}</p>
                  </div>
                  <div class="text-center">
                    <p class="text-5xl font-black italic text-orange-500">{{ selectedAuditApp.ai_readiness_score || '--' }}</p>
                    <p class="text-[8px] font-black uppercase text-white/40 mt-1">Final Score</p>
                  </div>
                </div>
              </BaseCard>

              <!-- Phase 1: 独立评审 -->
              <BaseCard v-if="Object.keys(selectedAuditApp._phase1 || {}).length" class="p-6 space-y-4">
                <h4 class="text-xs font-black uppercase tracking-widest text-purple-500 flex items-center gap-2"><Activity :size="14" /> Phase 1 — 独立评审 (Independent Review)</h4>
                <p class="text-[10px] text-slate-400 italic">每位专家在独立 Crew 中运行，互不可见彼此输出，避免锚定效应。</p>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div v-for="(contract, name) in (selectedAuditApp._phase1 as Record<string, any>)" :key="name"
                       class="p-5 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-200 dark:border-white/10 space-y-3">
                    <div class="flex items-center justify-between">
                      <span class="text-[10px] font-black uppercase tracking-widest text-slate-500">{{ name.replace('Review', '') }}</span>
                      <span class="text-xl font-black italic" :class="contract.score >= 75 ? 'text-green-500' : contract.score >= 55 ? 'text-orange-500' : 'text-red-500'">{{ contract.score }}</span>
                    </div>
                    <div class="h-1.5 bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
                      <div class="h-full rounded-full" :class="contract.score >= 75 ? 'bg-green-500' : contract.score >= 55 ? 'bg-orange-500' : 'bg-red-500'" :style="{ width: `${contract.score}%` }"></div>
                    </div>
                    <div class="text-[9px] font-bold text-slate-400 space-y-1">
                      <p>置信度: {{ (contract.confidence * 100).toFixed(0) }}%</p>
                      <p>建议: {{ contract.recommendation }}</p>
                      <div v-if="contract.risk_tags?.length" class="flex flex-wrap gap-1 mt-1">
                        <span v-for="tag in contract.risk_tags.slice(0, 3)" :key="tag" class="px-1.5 py-0.5 bg-red-500/10 text-red-500 rounded text-[8px]">{{ tag }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </BaseCard>

              <!-- Phase 2: 委员会表决 -->
              <BaseCard v-if="selectedAuditApp._phase2?.weighted_score !== undefined" class="p-6 space-y-4">
                <h4 class="text-xs font-black uppercase tracking-widest text-blue-500 flex items-center gap-2"><BarChart3 :size="14" /> Phase 2 — 委员会表决 (Committee Voting)</h4>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div class="p-4 bg-blue-500/5 rounded-2xl text-center">
                    <p class="text-2xl font-black italic text-blue-500">{{ selectedAuditApp._phase2.weighted_score }}</p>
                    <p class="text-[8px] font-black uppercase text-slate-400 mt-1">加权评分</p>
                  </div>
                  <div class="p-4 bg-blue-500/5 rounded-2xl text-center">
                    <p class="text-2xl font-black italic" :class="selectedAuditApp._phase2.disagreement >= 0.25 ? 'text-red-500' : 'text-green-500'">{{ (selectedAuditApp._phase2.disagreement * 100).toFixed(0) }}%</p>
                    <p class="text-[8px] font-black uppercase text-slate-400 mt-1">分歧度</p>
                  </div>
                  <div class="p-4 bg-blue-500/5 rounded-2xl text-center">
                    <p class="text-2xl font-black italic text-blue-500">{{ (selectedAuditApp._phase2.avg_confidence * 100).toFixed(0) }}%</p>
                    <p class="text-[8px] font-black uppercase text-slate-400 mt-1">平均置信度</p>
                  </div>
                  <div class="p-4 bg-blue-500/5 rounded-2xl text-center">
                    <p class="text-lg font-black italic" :class="selectedAuditApp._phase2.needs_mediation ? 'text-red-500' : 'text-green-500'">{{ selectedAuditApp._phase2.needs_mediation ? '已触发' : '未触发' }}</p>
                    <p class="text-[8px] font-black uppercase text-slate-400 mt-1">仲裁状态</p>
                  </div>
                </div>
                <div class="p-4 bg-slate-50 dark:bg-white/5 rounded-2xl">
                  <p class="text-[10px] font-black text-slate-400 uppercase">投票裁决: <span class="text-blue-500 ml-2">{{ selectedAuditApp._phase2.vote_decision }}</span></p>
                </div>
              </BaseCard>

              <!-- Phase 3: 分歧仲裁 -->
              <BaseCard v-if="selectedAuditApp._phase3" class="p-6 space-y-4 border-2 border-dashed border-red-500/30">
                <h4 class="text-xs font-black uppercase tracking-widest text-red-500 flex items-center gap-2"><AlertTriangle :size="14" /> Phase 3 — 分歧仲裁 (Conflict Mediation)</h4>
                <p class="text-[10px] text-slate-400 italic">专家间分歧度超过 25% 阈值，仲裁智能体介入分析根因。</p>
                <div class="p-5 bg-red-500/5 rounded-2xl space-y-3">
                  <div class="flex justify-between items-center">
                    <span class="text-[10px] font-black text-slate-400 uppercase">仲裁评分</span>
                    <span class="text-2xl font-black italic text-red-500">{{ selectedAuditApp._phase3.score }}/100</span>
                  </div>
                  <div v-if="selectedAuditApp._phase3.conflict_reason" class="p-4 bg-white dark:bg-black/20 rounded-xl border-l-4 border-red-500">
                    <p class="text-[10px] font-black text-red-500 uppercase mb-1">分歧根因</p>
                    <p class="text-sm font-bold italic text-slate-600 dark:text-slate-300">{{ selectedAuditApp._phase3.conflict_reason }}</p>
                  </div>
                  <div v-if="selectedAuditApp._phase3.adopted_opinion" class="text-[10px] font-bold text-slate-400">
                    采纳意见: <span class="text-green-500">{{ selectedAuditApp._phase3.adopted_opinion }}</span>
                  </div>
                </div>
              </BaseCard>

              <!-- 维度评分 -->
              <BaseCard v-if="selectedAuditApp._dimensions?.length" class="p-6 space-y-4">
                <h4 class="text-xs font-black uppercase tracking-widest text-teal-500 flex items-center gap-2"><TrendingUp :size="14" /> 维度评分详情</h4>
                <div class="space-y-3">
                  <div v-for="dim in selectedAuditApp._dimensions" :key="dim.key" class="flex items-center gap-4">
                    <span class="text-[10px] font-black text-slate-500 w-24 text-right">{{ dim.label }}</span>
                    <div class="flex-1 h-2 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                      <div class="h-full rounded-full transition-all" :class="dim.score >= 75 ? 'bg-teal-500' : dim.score >= 55 ? 'bg-orange-500' : 'bg-red-500'" :style="{ width: `${dim.score}%` }"></div>
                    </div>
                    <span class="text-xs font-black w-8" :class="dim.score >= 75 ? 'text-teal-500' : dim.score >= 55 ? 'text-orange-500' : 'text-red-500'">{{ dim.score }}</span>
                  </div>
                </div>
              </BaseCard>
            </div>

            <div v-else class="py-20 text-center text-slate-400">
              <BrainCircuit class="mx-auto mb-4 text-slate-300" :size="48" />
              <p class="font-black uppercase tracking-widest text-xs">选择一条申请查看多智能体评审详情</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 其他标签页 (匹配引擎演示等) -->
      <div v-else-if="activeTab === 'matching_demo'" class="animate-in fade-in duration-500">
         <BaseCard class="p-20 text-center text-slate-400 font-bold italic">匹配引擎演示模块已于 P0 阶段集成。本页主要用于展示推荐 Pipeline 的实时追踪。</BaseCard>
      </div>

      <div v-else class="py-40 text-center space-y-4">
        <Loader2 class="animate-spin mx-auto text-slate-300" :size="48" />
        <p class="font-black text-slate-400 uppercase tracking-widest">其他管理模块正在加载...</p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.animate-in { animation: animate-in 0.5s ease-out; }
@keyframes animate-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>
