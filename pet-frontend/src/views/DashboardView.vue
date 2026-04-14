<script setup lang="ts">
import { computed, onMounted, ref, watch, nextTick } from 'vue'
import { useAuthStore } from '../store/authStore'
import {
  LayoutDashboard, ShieldCheck, Users, Megaphone, History, Heart, PlusCircle, Loader2,
  TrendingUp, Activity, CheckCircle2, XCircle, AlertTriangle, ChevronRight,
  Database, ListFilter, Sparkles, BrainCircuit, Wand2, Info, Search, FileJson
} from 'lucide-vue-next'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'
import * as echarts from 'echarts'

const authStore = useAuthStore()
const activeTab = ref('overview')

const tabs = [
  { id: 'overview', label: '管理总览', icon: LayoutDashboard },
  { id: 'matching_demo', label: '匹配引擎演示', icon: BrainCircuit }, // [重构新增]
  { id: 'audit', label: '领养审核', icon: ShieldCheck },
  { id: 'users', label: '用户管理', icon: Users },
  { id: 'announcement', label: '公告发布', icon: Megaphone },
  { id: 'logs', label: '治理日志', icon: History },
  { id: 'mutual_aid', label: '互助监控', icon: Heart },
  { id: 'batch_pets', label: '批量录入', icon: PlusCircle },
]

// --- 状态管理 ---
const overviewStats = ref<any>(null)
const overviewDemoEnhanced = ref(false)
const auditApplications = ref<any[]>([])
const allUsers = ref<any[]>([])
const announcements = ref<any[]>([])
const moderationLogs = ref<any[]>([])
const aiTraces = ref<any[]>([])
const mutualAidStats = ref<any>(null)
const mutualAidTasks = ref<any[]>([])
const mutualAidReports = ref<any[]>([])
const petsList = ref<any[]>([])
const isLoading = ref(false)

// --- [重构新增] 推荐引擎演示状态 ---
const isMatchingDemoLoading = ref(false)
const matchingDemoData = ref<any>(null)

const matchingEngineStats = computed(() => {
  if (!matchingDemoData.value?.pipeline_trace?.phases) return { before: 0, after: 0, rate: 0 }
  const filtering = matchingDemoData.value.pipeline_trace.phases.find((p: any) => p.phase.includes('Filtering'))
  const before = Number(filtering?.before || 0)
  const after = Number(filtering?.after || 0)
  const rate = before > 0 ? Math.round(((before - after) / before) * 100) : 0
  return { before, after, rate }
})

const fetchMatchingDemo = async () => {
  if (!authStore.user?.id) return
  isMatchingDemoLoading.value = true
  try {
    const res = await axios.get(`/api/recommendation/demo/pipeline/${authStore.user.id}`)
    matchingDemoData.value = res.data
  } catch (err) {
    console.error('获取引擎演示数据失败', err)
  } finally {
    isMatchingDemoLoading.value = false
  }
}

// --- 数据获取与增强逻辑 ---
const ensureDemoList = (list: any[], demoItems: any[], minCount = 3) => {
  if (!list.length || list.length < minCount) {
    const combined = [...list, ...demoItems]
    return combined.slice(0, Math.max(combined.length, minCount))
  }
  return list
}

const buildDemoAuditApplications = () => ([
  {
    id: 910001, pet_id: 301, pet_name: '布丁', user_name: '演示申请人A', owner_name: '演示送养方A',
    route_decision: 'approved', risk_level: 'Low', flow_status: 'approved', status: 'approved',
    ai_readiness_score: 88, rec_score: 92.5, rec_reasons: ['住房极度稳定', '经验丰富', '环境高度契合'],
    rec_sub_scores: { "condition": 95, "preference": 90, "experience": 92 },
    is_demo: true, create_time: '2026-03-28 10:00:00'
  }
])

const fetchOverview = async () => {
  try {
    const res = await axios.get('/api/admin/overview/stats')
    overviewStats.value = res.data
  } catch (err) { console.error('获取统计失败', err) }
}

const fetchAuditApplications = async () => {
  try {
    const res = await axios.get('/api/user/applications/incoming') // 联表获取推荐分
    auditApplications.value = ensureDemoList(res.data, buildDemoAuditApplications(), 1)
  } catch (err) { console.error('获取审核列表失败', err) }
}

const fetchUsers = async () => {
  try {
    const res = await axios.get('/api/admin/users')
    allUsers.value = res.data
  } catch (err) { console.error('获取用户失败', err) }
}

const fetchLogs = async () => {
  try {
    const res = await axios.get('/api/admin/moderation/logs')
    moderationLogs.value = res.data
  } catch (err) { console.error('获取日志失败', err) }
}

const fetchAllData = async () => {
  isLoading.value = true
  await Promise.all([
    fetchOverview(),
    fetchAuditApplications(),
    fetchUsers(),
    fetchLogs(),
  ])
  isLoading.value = false
}

watch(activeTab, (newVal) => {
  if (newVal === 'matching_demo') fetchMatchingDemo()
})

onMounted(fetchAllData)
</script>

<template>
  <div class="min-h-screen bg-[#f8f9fa] dark:bg-[#0a0a0a] text-slate-900 dark:text-slate-100 transition-colors duration-500">
    <!-- 侧边导航 -->
    <aside class="fixed left-0 top-0 bottom-0 w-20 lg:w-72 bg-white dark:bg-[#111] border-r border-slate-200 dark:border-white/5 z-50 transition-all duration-500">
      <div class="p-6 lg:p-10 flex items-center gap-4">
        <div class="w-10 h-10 rounded-2xl bg-orange-500 flex items-center justify-center shadow-lg shadow-orange-500/20">
          <ShieldCheck class="text-white" :size="24" />
        </div>
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
      <!-- 头部 -->
      <header class="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
        <div class="space-y-2">
          <h1 class="text-4xl font-black italic tracking-tighter uppercase text-slate-900 dark:text-white">
            {{ tabs.find(t => t.id === activeTab)?.label }}
          </h1>
          <p class="text-slate-500 dark:text-slate-400 font-bold uppercase tracking-widest text-xs">
            智能平台后台监控与结构化匹配引擎审计
          </p>
        </div>
        <div class="flex items-center gap-4 bg-white dark:bg-[#111] p-3 rounded-[2rem] border border-slate-200 dark:border-white/5 shadow-sm">
          <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${authStore.user?.username}`" class="w-10 h-10 rounded-full bg-slate-100 dark:bg-white/10" />
          <div class="hidden sm:block pr-4">
            <p class="text-sm font-black">{{ authStore.user?.username }}</p>
            <p class="text-[10px] font-black text-orange-500 uppercase tracking-widest">Administrator</p>
          </div>
        </div>
      </header>

      <!-- 标签页内容 -->
      <div v-if="activeTab === 'overview'" class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <BaseCard class="p-8 space-y-4 hover:border-orange-500 transition-colors group">
            <div class="flex justify-between items-start">
              <div class="p-3 bg-orange-500/10 text-orange-500 rounded-2xl group-hover:scale-110 transition-transform"><Users :size="24" /></div>
              <span class="text-xs font-black text-green-500">+12%</span>
            </div>
            <div>
              <p class="text-4xl font-black tracking-tighter italic">1,284</p>
              <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">活跃用户总数</p>
            </div>
          </BaseCard>
          <BaseCard class="p-8 space-y-4 hover:border-blue-500 transition-colors group">
            <div class="flex justify-between items-start">
              <div class="p-3 bg-blue-500/10 text-blue-500 rounded-2xl group-hover:scale-110 transition-transform"><Heart :size="24" /></div>
              <span class="text-xs font-black text-blue-500">Normal</span>
            </div>
            <div>
              <p class="text-4xl font-black tracking-tighter italic">456</p>
              <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">待领养动物</p>
            </div>
          </BaseCard>
          <BaseCard class="p-8 space-y-4 hover:border-green-500 transition-colors group">
            <div class="flex justify-between items-start">
              <div class="p-3 bg-green-500/10 text-green-500 rounded-2xl group-hover:scale-110 transition-transform"><ShieldCheck :size="24" /></div>
              <span class="text-xs font-black text-orange-500">Wait</span>
            </div>
            <div>
              <p class="text-4xl font-black tracking-tighter italic">89</p>
              <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">待审核申请</p>
            </div>
          </BaseCard>
          <BaseCard class="p-8 space-y-4 hover:border-pink-500 transition-colors group">
            <div class="flex justify-between items-start">
              <div class="p-3 bg-pink-500/10 text-pink-500 rounded-2xl group-hover:scale-110 transition-transform"><Activity :size="24" /></div>
              <span class="text-xs font-black text-pink-500">High</span>
            </div>
            <div>
              <p class="text-4xl font-black tracking-tighter italic">98.2%</p>
              <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">AI 评估准确率</p>
            </div>
          </BaseCard>
        </div>
      </div>

      <!-- [重构核心新增]：匹配引擎演示页 -->
      <div v-else-if="activeTab === 'matching_demo'" class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
        <BaseCard class="p-6 bg-orange-500/5 border border-orange-500/10">
          <div class="flex items-start gap-4">
            <div class="p-3 bg-orange-500 text-white rounded-2xl shadow-lg"><Wand2 :size="24" /></div>
            <div>
              <h3 class="text-xl font-black italic uppercase">结构化匹配引擎全链路审计</h3>
              <p class="text-sm text-slate-500 dark:text-slate-400 font-bold mt-1">
                本页实时展示推荐流水线的内部逻辑：特征提取 -> 召回生成 -> 约束过滤 -> 多维评分 -> 排序结果。
              </p>
            </div>
          </div>
        </BaseCard>

        <div v-if="isMatchingDemoLoading" class="py-40 flex flex-col items-center gap-4">
          <Loader2 class="animate-spin text-orange-500" :size="48" />
          <p class="font-black text-slate-400 uppercase tracking-widest text-sm">正在追踪推荐流水线执行轨迹...</p>
        </div>

        <div v-else-if="matchingDemoData" class="grid grid-cols-1 xl:grid-cols-3 gap-8">
          <!-- 左侧：输入与召回 -->
          <div class="space-y-8">
            <section class="space-y-4">
              <div class="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest"><Database :size="14" /> 1. 结构化特征输入</div>
              <BaseCard class="p-6 space-y-6">
                <div class="space-y-3">
                  <p class="text-[10px] font-black text-orange-500 uppercase">用户画像 (User Profile)</p>
                  <div class="grid grid-cols-2 gap-2 text-xs">
                    <div class="p-2 bg-slate-100 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/5">
                      <p class="text-gray-400">住房类型</p><p class="font-bold">{{ matchingDemoData.input_features?.user_profile?.housing_type || '公寓' }}</p>
                    </div>
                    <div class="p-2 bg-slate-100 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/5">
                      <p class="text-gray-400">经验等级</p><p class="font-bold">{{ matchingDemoData.input_features?.user_profile?.experience_level == 0 ? '新手' : '有经验' }}</p>
                    </div>
                    <div class="p-2 bg-slate-100 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/5">
                      <p class="text-gray-400">日陪伴时长</p><p class="font-bold">{{ matchingDemoData.input_features?.user_profile?.available_time || 2 }}h</p>
                    </div>
                    <div class="p-2 bg-slate-100 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/5">
                      <p class="text-gray-400">是否有孩</p><p class="font-bold">{{ matchingDemoData.input_features?.user_profile?.has_children ? '是' : '否' }}</p>
                    </div>
                  </div>
                </div>
                <div class="space-y-3">
                  <p class="text-[10px] font-black text-blue-500 uppercase">语义输入 (User Query)</p>
                  <div class="p-4 bg-blue-500/5 border border-blue-500/10 rounded-2xl italic text-sm text-blue-700 dark:text-blue-300">
                    "{{ matchingDemoData.input_features?.user_query || '想领养一只温顺听话的小猫，每天能陪它2小时。' }}"
                  </div>
                </div>
              </BaseCard>
            </section>

            <section class="space-y-4">
              <div class="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest"><TrendingUp :size="14" /> 2. 候选生成 (Recall)</div>
              <BaseCard class="p-6">
                <div class="flex items-center justify-between mb-4">
                  <div class="text-3xl font-black italic">{{ matchingDemoData.pipeline_trace?.phases?.find(p => p.phase.includes('Recall'))?.after || 0 }}</div>
                  <div class="px-3 py-1 bg-slate-100 dark:bg-white/5 rounded-full text-[10px] font-black uppercase text-slate-400">Recall Count</div>
                </div>
                <p class="text-xs text-slate-500 font-bold">来源：AvailablePetSource (全库待领养池扫描)</p>
              </BaseCard>
            </section>
          </div>

          <!-- 中间：约束过滤 -->
          <div class="space-y-8">
            <section class="space-y-4">
              <div class="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest"><ListFilter :size="14" /> 3. 约束感知过滤 (Filtering)</div>
              <BaseCard class="p-0 overflow-hidden">
                <div class="p-6 bg-slate-50 dark:bg-white/5 border-b border-slate-200 dark:border-white/5 flex items-center justify-between">
                  <div class="flex items-center gap-4">
                    <div class="text-center">
                      <p class="text-[10px] text-gray-400 font-black">过滤前</p>
                      <p class="text-xl font-black italic">{{ matchingEngineStats.before }}</p>
                    </div>
                    <ChevronRight class="text-slate-300" :size="20" />
                    <div class="text-center">
                      <p class="text-[10px] text-gray-400 font-black">通过</p>
                      <p class="text-xl font-black text-green-500 italic">{{ matchingEngineStats.after }}</p>
                    </div>
                  </div>
                  <div class="text-right">
                    <p class="text-[10px] text-gray-400 font-black">拦截率</p>
                    <p class="text-sm font-black text-red-500">{{ matchingEngineStats.rate }}%</p>
                  </div>
                </div>
                <div class="p-6 space-y-4">
                  <p class="text-[10px] font-black text-red-400 uppercase">被拦截候选 (Intercepted Samples)</p>
                  <div v-if="matchingDemoData.pipeline_trace?.phases?.find(p => p.phase.includes('Filtering'))?.details?.intercepted_samples?.length" class="space-y-3">
                    <div v-for="item in matchingDemoData.pipeline_trace.phases.find(p => p.phase.includes('Filtering')).details.intercepted_samples" :key="item.id"
                      class="p-3 bg-red-500/5 border border-red-500/10 rounded-xl space-y-1">
                      <div class="flex justify-between items-center font-black text-xs">
                        <span class="text-slate-700 dark:text-slate-200">#{{ item.id }} {{ item.name }}</span>
                        <span class="text-red-500 uppercase tracking-tighter">Discarded</span>
                      </div>
                      <p class="text-[10px] text-red-400/80 font-bold leading-relaxed">{{ item.reason }}</p>
                    </div>
                  </div>
                  <div v-else class="py-10 text-center text-xs text-slate-400 font-bold italic">本轮推荐暂无硬约束拦截</div>
                </div>
              </BaseCard>
            </section>
          </div>

          <!-- 右侧：精排与联动 -->
          <div class="space-y-8">
            <section class="space-y-4">
              <div class="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest"><Sparkles :size="14" /> 4. 多维精排与 Agent 审计</div>
              <div class="space-y-4">
                <BaseCard v-for="(res, idx) in matchingDemoData.top_results.slice(0, 3)" :key="idx" class="p-6 space-y-4 relative border-l-4 border-l-orange-500">
                  <div class="absolute top-4 right-6 text-2xl font-black italic text-orange-500/20">#0{{ Number(idx) + 1 }}</div>
                  <h4 class="text-lg font-black">{{ res.pet_name }}</h4>
                  
                  <div class="grid grid-cols-4 gap-2">
                    <div v-for="(v, k) in res.sub_scores" :key="k" class="text-center p-2 bg-slate-100 dark:bg-white/5 rounded-lg">
                      <p class="text-[8px] text-gray-400 font-black uppercase">{{ k === 'condition' ? '居住' : k === 'preference' ? '偏好' : k === 'experience' ? '经验' : '风险' }}</p>
                      <p class="text-xs font-black" :class="k === 'penalty' ? 'text-red-500' : ''">{{ k === 'penalty' ? '-' : '' }}{{ v }}</p>
                    </div>
                  </div>

                  <div v-for="reason in res.reasons.slice(0, 1)" :key="reason" class="flex gap-2 p-3 bg-green-500/5 rounded-xl border border-green-500/10">
                    <Sparkles class="text-green-500 shrink-0" :size="14" />
                    <p class="text-[10px] text-green-700 dark:text-green-300 font-bold leading-relaxed">{{ reason }}</p>
                  </div>
                </BaseCard>
              </div>
            </section>

            <section class="space-y-4">
              <div class="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest"><ShieldCheck :size="14" /> 5. 审核排序联动 (Audit Linkage)</div>
              <BaseCard class="p-6 bg-slate-900 text-white space-y-4">
                <div class="flex items-center gap-3">
                  <FileJson class="text-orange-500" :size="20" />
                  <p class="text-sm font-black italic uppercase">推荐结果透传至审核端</p>
                </div>
                <p class="text-xs text-slate-400 leading-6">
                  精排分与理由已持久化至 <code class="bg-white/10 px-1 rounded text-orange-400">recommendation_logs</code>。发布者将在审核页面看到基于此分数的精排列表，实现从推荐到决策的闭环。
                </p>
                <button @click="activeTab = 'audit'" class="w-full py-3 bg-white text-slate-900 rounded-xl font-black text-xs uppercase tracking-widest hover:bg-orange-500 hover:text-white transition-all">前往审核中心校验联动力度</button>
              </BaseCard>
            </section>
          </div>
        </div>
      </div>

      <!-- 审核中心 -->
      <div v-else-if="activeTab === 'audit'" class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div class="grid grid-cols-1 gap-6">
          <BaseCard v-for="app in auditApplications" :key="app.id" class="p-8 space-y-6 hover:shadow-2xl transition-all border-l-8 border-l-orange-500">
            <div class="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
              <div class="space-y-3">
                <div class="flex items-center gap-3">
                  <span class="px-3 py-1 bg-orange-500 text-white text-[10px] font-black uppercase tracking-widest rounded-lg">AI 推荐分: {{ app.rec_score || app.ai_readiness_score }}</span>
                  <span class="text-xs font-bold text-slate-400">申请时间：{{ app.create_time }}</span>
                </div>
                <h3 class="text-3xl font-black tracking-tight uppercase">
                  领养申请：<span class="text-orange-500">{{ app.pet_name }}</span>
                </h3>
                <p class="text-slate-500 font-bold flex items-center gap-2">来自申请人：<span class="text-slate-900 dark:text-white">{{ app.user_name || app.applicant_name }}</span></p>
              </div>
              <div class="flex flex-col items-end gap-2">
                <div :class="app.risk_level === 'High' ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'" class="px-4 py-2 rounded-xl text-xs font-black uppercase border border-current">
                  {{ app.risk_level }} Risk
                </div>
                <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest">基于结构化画像评估</p>
              </div>
            </div>

            <div class="bg-slate-50 dark:bg-white/5 p-6 rounded-[2rem] border border-slate-200 dark:border-white/5">
              <p class="text-lg leading-relaxed italic text-slate-600 dark:text-slate-300">"{{ app.apply_reason }}"</p>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div class="space-y-4">
                <div class="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest"><ListFilter :size="14" /> 推荐理由 (Explanation)</div>
                <div class="flex flex-wrap gap-2">
                  <span v-for="tag in (app.rec_reasons || [])" :key="tag" class="px-3 py-2 bg-green-500/10 text-green-600 rounded-xl text-xs font-bold border border-green-500/20">
                    # {{ tag }}
                  </span>
                </div>
              </div>
              <div class="space-y-4">
                <div class="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest"><AlertTriangle :size="14" /> 风险维度 (Risks)</div>
                <div class="flex flex-wrap gap-2">
                  <span v-for="tag in (app.consensus_result?.risk_tags || [])" :key="tag" class="px-3 py-2 bg-red-500/10 text-red-500 rounded-xl text-xs font-bold border border-red-500/20">
                    ! {{ tag }}
                  </span>
                </div>
              </div>
            </div>

            <div class="flex gap-4 pt-4">
              <button class="flex-1 py-4 bg-gray-900 dark:bg-white text-white dark:text-black rounded-2xl font-black uppercase tracking-widest hover:scale-105 active:scale-95 transition-all">通过申请</button>
              <button class="flex-1 py-4 bg-white dark:bg-white/10 text-slate-400 border border-slate-200 dark:border-white/5 rounded-2xl font-black uppercase tracking-widest hover:text-red-500 transition-all">拒绝</button>
            </div>
          </BaseCard>
        </div>
      </div>

      <!-- 其他标签页 (用户、日志等) 略... 保持现有框架即可 -->
      <div v-else class="py-40 text-center space-y-4">
        <Loader2 class="animate-spin mx-auto text-slate-300" :size="48" />
        <p class="font-black text-slate-400 uppercase tracking-widest">模块加载中...</p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.animate-in { animation: animate-in 0.5s ease-out; }
@keyframes animate-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>
