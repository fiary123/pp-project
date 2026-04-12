<script setup lang="ts">
import { computed, ref, onMounted, nextTick, onUnmounted } from 'vue'
import { useAuthStore } from '../store/authStore'
import {
  Users, Loader2, ShieldCheck, Handshake, BarChart2, ClipboardList,
  FileText, Heart, Activity, AlertTriangle, Waypoints, Megaphone,
  ScrollText, Sparkles, Ban, VolumeX, RefreshCcw, Plus, Trash2, PackagePlus
} from 'lucide-vue-next'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'
import * as echarts from 'echarts'

type MainTab = 'overview' | 'audit' | 'announcement' | 'logs' | 'users' | 'mutual_aid' | 'batch_pets'

const authStore = useAuthStore()
const activeMainTab = ref<MainTab>('overview')
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
const latestPets = ref<any[]>([])
const isLoading = ref(false)
const announcementForm = ref({ title: '', content: '', is_hot: 0 })
const isSubmittingAnnouncement = ref(false)
const userActionLoading = ref<Record<number, boolean>>({})
const taskActionLoading = ref<Record<string, boolean>>({})
const reportActionLoading = ref<Record<number, boolean>>({})

const postTypeChartRef = ref<HTMLElement | null>(null)
const postTypeLineChartRef = ref<HTMLElement | null>(null)
const trendChartRef = ref<HTMLElement | null>(null)
let postTypeChart: echarts.ECharts | null = null
let postTypeLineChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null
let themeObserver: MutationObserver | null = null
let chartRefreshTimer: ReturnType<typeof setTimeout> | null = null

const batchTemplate = computed(() =>
  JSON.stringify({
    owner_id: authStore.user?.id ?? 0,
    pets: [{
      name: '奶糖',
      species: '猫',
      age: 2,
      gender: 'female',
      description: '亲人、已绝育、适合公寓家庭。',
      image_url: 'https://example.com/cat.jpg',
      location: '上海市徐汇区',
      tags: '["已免疫","亲人","适合新手"]',
    }],
  }, null, 2)
)

const isDarkMode = () => document.documentElement.classList.contains('dark')
const flowStatusLabel = (status?: string) => ({
  submitted: '已提交', evaluating: '评估中', need_more_info: '等待补充',
  waiting_publisher: '等待发布者', manual_review: '人工复核',
  approved: '已通过', rejected: '已拒绝',
}[status || ''] || (status || '未知状态'))
const routeLabel = (action?: string) => ({
  followup: '继续追问', manual_review: '人工复核',
  publisher_review: '发布者决策', reject_candidate: '建议拒绝',
}[action || ''] || (action || '待生成'))
const taskStatusLabel = (status?: string) => ({
  open: '待接单', accepted: '已接单', completed: '已完成', cancelled: '已取消',
}[status || ''] || (status || '未知'))
const reportStatusLabel = (status?: string) => ({
  pending: '待处理', resolved_cancel: '已下架处理', resolved_dismiss: '已驳回',
}[status || ''] || (status || '未知'))
const riskTone = (risk?: string) => {
  if (risk === 'High') return 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300'
  if (risk === 'Low') return 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300'
  return 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300'
}
const routeTone = (action?: string) => {
  if (action === 'manual_review') return 'bg-cyan-100 text-cyan-700 dark:bg-cyan-500/15 dark:text-cyan-300'
  if (action === 'followup') return 'bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300'
  if (action === 'reject_candidate') return 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300'
  return 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300'
}
const userStatusTone = (status?: string) => {
  if (status === 'banned') return 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300'
  if (status === 'muted') return 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300'
  return 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300'
}
const formatConsensus = (value?: number | null) => {
  if (value == null) return 'N/A'
  const normalized = value > 1 ? value / 100 : value
  return `${Math.round(normalized * 100)}%`
}
const formatDateTime = (value?: string | null) => {
  if (!value) return '暂无'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
const formatDateOnly = (value?: string | null) => {
  if (!value) return '暂无'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString('zh-CN')
}
const shortTrace = (traceId?: string | null) => !traceId ? '未生成' : (traceId.length > 16 ? `${traceId.slice(0, 16)}...` : traceId)
const getRecentDateLabels = (days = 7) => {
  return Array.from({ length: days }, (_, index) => {
    const date = new Date()
    date.setDate(date.getDate() - (days - index - 1))
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  })
}
const normalizeRecentSeries = (items: any[] = [], labels: string[] = []) => {
  const countMap = new Map(
    items.map((item: any) => {
      const raw = item?.d ? new Date(item.d) : null
      const key = raw && !Number.isNaN(raw.getTime())
        ? raw.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
        : String(item?.d ?? '')
      return [key, Number(item?.cnt || 0)]
    }),
  )
  return labels.map((label) => countMap.get(label) ?? 0)
}
const postTypeItems = computed(() => ([
  { name: '日常分享', value: Number(overviewStats.value?.post_breakdown?.daily || 0), color: 'bg-orange-500' },
  { name: '经验攻略', value: Number(overviewStats.value?.post_breakdown?.experience || 0), color: 'bg-blue-500' },
  { name: '送养帖子', value: Number(overviewStats.value?.post_breakdown?.adopt_help || 0), color: 'bg-green-500' },
]))
const recentTrendSummary = computed(() => {
  const labels = getRecentDateLabels(7)
  const posts = normalizeRecentSeries(overviewStats.value?.recent_posts || [], labels)
  const applications = normalizeRecentSeries(overviewStats.value?.recent_applications || [], labels)
  return {
    labels,
    posts,
    applications,
    postTotal: posts.reduce((sum, item) => sum + item, 0),
    applicationTotal: applications.reduce((sum, item) => sum + item, 0),
  }
})
const buildDemoOverviewStats = () => {
  const labels = getRecentDateLabels(7)
  const demoPostCounts = [2, 4, 3, 5, 4, 6, 5]
  const demoApplicationCounts = [1, 2, 3, 4, 5, 4, 6]
  return {
    summary: {
      total_users: 86,
      total_posts: 28,
      successful_adoptions: 11,
      total_applications: 34,
      pets_waiting: 14,
      total_pets: 23,
      total_announcements: 6,
      total_ai_traces: 42,
      owner_followed_ai: 18,
      owner_rejected_ai: 6,
      total_ai_reviews: 21,
      total_followups: 16,
      total_case_memories: 12,
      pending_manual_review: 3,
      pending_followups: 5,
      waiting_publisher: 4,
    },
    post_breakdown: {
      daily: 12,
      experience: 9,
      adopt_help: 7,
    },
    application_breakdown: {
      pending: 8,
      pending_owner_review: 6,
      approved: 15,
      rejected: 5,
    },
    framework_breakdown: {
      route_followup: 9,
      route_manual_review: 4,
      route_publisher_review: 11,
    },
    recent_posts: labels.map((d, index) => ({ d, cnt: demoPostCounts[index] || 0 })),
    recent_applications: labels.map((d, index) => ({ d, cnt: demoApplicationCounts[index] || 0 })),
  }
}
const mergeNumericObject = (demo: Record<string, any>, actual: Record<string, any> = {}) => {
  const merged: Record<string, any> = {}
  const keys = new Set([...Object.keys(demo || {}), ...Object.keys(actual || {})])
  keys.forEach((key) => {
    const demoValue = Number(demo?.[key] || 0)
    const actualValue = Number(actual?.[key] || 0)
    merged[key] = Math.max(demoValue, actualValue)
  })
  return merged
}
const mergeRecentSeriesForDisplay = (actualItems: any[] = [], demoItems: any[] = []) => {
  const labels = demoItems.map((item: any) => String(item?.d ?? ''))
  const actualCounts = normalizeRecentSeries(actualItems, labels)
  return labels.map((label, index) => ({
    d: label,
    cnt: Math.max(Number(demoItems[index]?.cnt || 0), Number(actualCounts[index] || 0)),
  }))
}
const shouldEnhanceOverviewWithDemo = (stats: any) => {
  if (!stats) return true
  const totalPosts = Number(stats?.summary?.total_posts || 0)
  const totalApplications = Number(stats?.summary?.total_applications || 0)
  const totalUsers = Number(stats?.summary?.total_users || 0)
  const recentPosts = normalizeRecentSeries(stats?.recent_posts || [], getRecentDateLabels(7)).reduce((sum, item) => sum + item, 0)
  const recentApplications = normalizeRecentSeries(stats?.recent_applications || [], getRecentDateLabels(7)).reduce((sum, item) => sum + item, 0)
  return totalPosts < 6 || totalApplications < 6 || totalUsers < 12 || recentPosts < 6 || recentApplications < 6
}
const buildDashboardOverviewForDisplay = (rawStats: any) => {
  const demoStats = buildDemoOverviewStats()
  if (!shouldEnhanceOverviewWithDemo(rawStats)) {
    return { data: rawStats, enhanced: false }
  }
  return {
    enhanced: true,
    data: {
      ...demoStats,
      ...rawStats,
      summary: mergeNumericObject(demoStats.summary, rawStats?.summary || {}),
      post_breakdown: mergeNumericObject(demoStats.post_breakdown, rawStats?.post_breakdown || {}),
      application_breakdown: mergeNumericObject(demoStats.application_breakdown, rawStats?.application_breakdown || {}),
      framework_breakdown: mergeNumericObject(demoStats.framework_breakdown, rawStats?.framework_breakdown || {}),
      recent_posts: mergeRecentSeriesForDisplay(rawStats?.recent_posts || [], demoStats.recent_posts),
      recent_applications: mergeRecentSeriesForDisplay(rawStats?.recent_applications || [], demoStats.recent_applications),
    },
  }
}
const ensureDemoList = <T extends Record<string, any>>(actualItems: T[] = [], demoItems: T[] = [], minCount = 3) => {
  const safeActual = Array.isArray(actualItems) ? [...actualItems] : []
  if (safeActual.length >= minCount) return safeActual
  const existingKeys = new Set(safeActual.map((item, index) => String(item?.id ?? item?.trace_id ?? item?.title ?? index)))
  const extras = demoItems.filter((item, index) => !existingKeys.has(String(item?.id ?? item?.trace_id ?? item?.title ?? index)))
  return [...safeActual, ...extras.slice(0, Math.max(0, minCount - safeActual.length))]
}
const mergeMutualAidStatsForDisplay = (rawStats: any = {}) => {
  const demoStats = { total: 14, today_new: 3, accept_rate: 78, complete_rate: 64, pending_reports: 2 }
  const shouldEnhance = Number(rawStats?.total || 0) < 4 && Number(rawStats?.pending_reports || 0) < 1
  if (!shouldEnhance) return rawStats
  return {
    ...demoStats,
    ...rawStats,
    total: Math.max(Number(rawStats?.total || 0), demoStats.total),
    today_new: Math.max(Number(rawStats?.today_new || 0), demoStats.today_new),
    accept_rate: Math.max(Number(rawStats?.accept_rate || 0), demoStats.accept_rate),
    complete_rate: Math.max(Number(rawStats?.complete_rate || 0), demoStats.complete_rate),
    pending_reports: Math.max(Number(rawStats?.pending_reports || 0), demoStats.pending_reports),
  }
}
const buildDemoAuditApplications = () => ([
  {
    id: 910001,
    pet_id: 301,
    pet_name: '团子',
    user_name: '演示申请人A',
    owner_name: '演示送养方A',
    route_decision: 'followup',
    risk_level: 'Medium',
    flow_status: 'need_more_info',
    status: 'pending_owner_review',
    ai_readiness_score: 82,
    consensus_result: { consensus_score: 0.86, disagreement_score: 0.18, risk_tags: ['居住稳定性待确认', '工作时长偏长'] },
    followup_questions: ['最近三个月是否有稳定照护时间安排？', '若出差时由谁照顾宠物？'],
    case_memory: { case_summary: '与两例城市公寓领养案例相似，补充照护计划后通过率较高。', risk_tags: ['居住稳定性待确认'] },
    recent_followups: [
      { question: '最近三个月是否有稳定照护时间安排？', answer: '工作日晚上和周末均可在家照顾。', source: '申请人补充', created_at: '2026-03-27 18:20:00' },
      { question: '若出差时由谁照顾宠物？', answer: '由同住家人代为照料。', source: '申请人补充', created_at: '2026-03-27 18:22:00' },
    ],
    is_demo: true,
  },
  {
    id: 910002,
    pet_id: 302,
    pet_name: '糯米',
    user_name: '演示申请人B',
    owner_name: '演示送养方B',
    route_decision: 'publisher_review',
    risk_level: 'Low',
    flow_status: 'waiting_publisher',
    status: 'approved',
    ai_readiness_score: 91,
    consensus_result: { consensus_score: 0.93, disagreement_score: 0.07, risk_tags: ['新手友好'] },
    followup_questions: [],
    case_memory: { case_summary: '申请人与历史高匹配样本特征接近，风险较低，适合直接交由发布者决策。', risk_tags: ['新手友好'] },
    recent_followups: [],
    is_demo: true,
  },
  {
    id: 910003,
    pet_id: 303,
    pet_name: '可乐',
    user_name: '演示申请人C',
    owner_name: '演示送养方C',
    route_decision: 'manual_review',
    risk_level: 'High',
    flow_status: 'manual_review',
    status: 'pending',
    ai_readiness_score: 63,
    consensus_result: { consensus_score: 0.61, disagreement_score: 0.39, risk_tags: ['历史养宠经验不足', '作息冲突'] },
    followup_questions: ['是否能提供既往养宠或寄养证明？'],
    case_memory: { case_summary: '历史相似案例中，若无法提供稳定照护证明，后续满意度偏低。', risk_tags: ['作息冲突'] },
    recent_followups: [{ question: '是否能提供既往养宠或寄养证明？', answer: '暂未补充。', source: '系统追问', created_at: '2026-03-27 20:10:00' }],
    is_demo: true,
  },
])
const buildDemoUsers = () => ([
  { id: 920001, username: 'demo_owner', email: 'demo_owner@smartpet.local', role: 'user', status: 'active', is_demo: true },
  { id: 920002, username: 'demo_helper', email: 'helper@smartpet.local', role: 'volunteer', status: 'muted', is_demo: true },
  { id: 920003, username: 'demo_guard', email: 'guard@smartpet.local', role: 'user', status: 'banned', is_demo: true },
  { id: 920004, username: 'demo_admin', email: 'admin_demo@smartpet.local', role: 'admin', status: 'active', is_demo: true },
])
const buildDemoAnnouncements = () => ([
  { id: 930001, title: '平台巡检演示公告', content: '本条为后台展示增强数据，用于演示公告管理、热门标识与发布时间排版。', is_hot: 1, date: '2026-03-28', is_demo: true },
  { id: 930002, title: '领养审核流程升级说明', content: '新增共识融合、路由分流与案例记忆摘要展示，便于管理员集中查看。', is_hot: 0, date: '2026-03-27', is_demo: true },
  { id: 930003, title: '互助任务仲裁提示', content: '如遇异常发布或举报争议，请在互助监控页进行统一处理。', is_hot: 0, date: '2026-03-26', is_demo: true },
])
const buildDemoModerationLogs = () => ([
  { id: 940001, target_id: 601, reason: '演示：帖子包含重复营销内容，已进入人工复核队列。', admin_id: 'A-01', delete_time: '2026-03-28 09:12:00', is_demo: true },
  { id: 940002, target_id: 602, reason: '演示：评论存在攻击性言论，触发社区治理记录。', admin_id: 'A-02', delete_time: '2026-03-27 18:44:00', is_demo: true },
  { id: 940003, target_id: 603, reason: '演示：图片内容与帖子主题无关，执行内容下架。', admin_id: 'A-01', delete_time: '2026-03-27 10:03:00', is_demo: true },
])
const buildDemoAiTraces = () => ([
  { id: 950001, trace_id: 'demo-trace-001', endpoint: '/api/adoption/evaluate', message: '演示：完成申请评估、协议校验与共识融合。', create_time: '2026-03-28 09:20:00', is_demo: true },
  { id: 950002, trace_id: 'demo-trace-002', endpoint: '/api/adoption/followup', summary: '演示：触发追问分流并写入案例记忆。', create_time: '2026-03-27 20:18:00', is_demo: true },
  { id: 950003, trace_id: 'demo-trace-003', endpoint: '/api/admin/overview/stats', message: '演示：后台统计模块聚合成功。', create_time: '2026-03-27 08:30:00', is_demo: true },
])
const buildDemoMutualAidTasks = () => ([
  { id: 960001, task_type: '上门喂养', pet_name: '年糕', status: 'open', publisher_name: '演示发布者A', location: '徐汇区', description: '演示任务：周末临时出差，需要两次上门添粮换水。', create_time: '2026-03-28 08:30:00', is_demo: true },
  { id: 960002, task_type: '临时寄养', pet_name: '橘子', status: 'accepted', publisher_name: '演示发布者B', location: '浦东新区', description: '演示任务：节假日期间临时寄养 3 天。', create_time: '2026-03-27 15:10:00', is_demo: true },
  { id: 960003, task_type: '送医陪诊', pet_name: '雪球', status: 'completed', publisher_name: '演示发布者C', location: '静安区', description: '演示任务：帮助前往宠物医院复诊并记录医嘱。', create_time: '2026-03-26 11:00:00', is_demo: true },
])
const buildDemoMutualAidReports = () => ([
  { id: 970001, pet_name: '年糕', status: 'pending', reporter_name: '演示举报人A', task_owner_name: '演示发布者A', reason: '演示举报：任务描述与联系方式不完整。', create_time: '2026-03-28 10:20:00', is_demo: true },
  { id: 970002, pet_name: '橘子', status: 'resolved_cancel', reporter_name: '演示举报人B', task_owner_name: '演示发布者B', reason: '演示举报：发布信息疑似重复，已执行下架。', create_time: '2026-03-27 14:05:00', is_demo: true },
  { id: 970003, pet_name: '雪球', status: 'resolved_dismiss', reporter_name: '演示举报人C', task_owner_name: '演示发布者C', reason: '演示举报：经复核后信息真实有效，已驳回。', create_time: '2026-03-26 16:30:00', is_demo: true },
])
const buildDemoPets = () => ([
  { id: 980001, name: '芝麻', species: '猫', age: 2, status: '待领养', description: '演示宠物：亲人安静，已完成基础免疫。', is_demo: true },
  { id: 980002, name: '布丁', species: '犬', age: 1, status: '待领养', description: '演示宠物：适合有活动空间的家庭。', is_demo: true },
  { id: 980003, name: '栗子', species: '猫', age: 3, status: '待领养', description: '演示宠物：适应能力强，熟悉猫砂。', is_demo: true },
  { id: 980004, name: '奶盖', species: '兔', age: 1, status: '待领养', description: '演示宠物：性格温顺，需要固定清洁笼舍。', is_demo: true },
])

const fetchOverview = async () => {
  const res = await axios.get('/api/admin/overview/stats')
  const dashboardOverview = buildDashboardOverviewForDisplay(res.data)
  overviewStats.value = dashboardOverview.data
  overviewDemoEnhanced.value = dashboardOverview.enhanced
  refreshCharts()
}
const fetchAuditApplications = async () => {
  const res = await axios.get('/api/admin/applications')
  auditApplications.value = ensureDemoList(Array.isArray(res.data) ? res.data : [], buildDemoAuditApplications(), 3)
}
const fetchUsers = async () => {
  const res = await axios.get('/api/admin/users')
  allUsers.value = ensureDemoList(Array.isArray(res.data) ? res.data : [], buildDemoUsers(), 5)
}
const fetchAnnouncements = async () => {
  const res = await axios.get('/api/announcements')
  announcements.value = ensureDemoList(Array.isArray(res.data) ? res.data : [], buildDemoAnnouncements(), 3)
}
const fetchLogs = async () => {
  const [logRes, traceRes] = await Promise.allSettled([
    axios.get('/api/admin/moderation/logs'),
    axios.get('/api/admin/ai/traces'),
  ])
  const logData = logRes.status === 'fulfilled' && Array.isArray(logRes.value.data) ? logRes.value.data : []
  const traceData = traceRes.status === 'fulfilled' && Array.isArray(traceRes.value.data) ? traceRes.value.data : []
  moderationLogs.value = ensureDemoList(logData, buildDemoModerationLogs(), 3)
  aiTraces.value = ensureDemoList(traceData, buildDemoAiTraces(), 3)
}
const fetchMutualAid = async () => {
  const [statsRes, tasksRes, reportsRes] = await Promise.all([
    axios.get('/api/admin/mutual-aid/stats'),
    axios.get('/api/admin/mutual-aid/tasks'),
    axios.get('/api/admin/mutual-aid/reports'),
  ])
  mutualAidStats.value = mergeMutualAidStatsForDisplay(statsRes.data)
  mutualAidTasks.value = ensureDemoList(Array.isArray(tasksRes.data) ? tasksRes.data : [], buildDemoMutualAidTasks(), 3)
  mutualAidReports.value = ensureDemoList(Array.isArray(reportsRes.data) ? reportsRes.data : [], buildDemoMutualAidReports(), 3)
}
const fetchPets = async () => {
  const res = await axios.get('/api/pets')
  latestPets.value = ensureDemoList(Array.isArray(res.data) ? res.data.slice(0, 8) : [], buildDemoPets(), 4)
}
const fetchForTab = async (tab: MainTab) => {
  isLoading.value = true
  try {
    if (tab === 'overview') return await fetchOverview()
    if (tab === 'audit') return await Promise.all([fetchOverview(), fetchAuditApplications()])
    if (tab === 'users') return await fetchUsers()
    if (tab === 'announcement') return await fetchAnnouncements()
    if (tab === 'logs') return await fetchLogs()
    if (tab === 'mutual_aid') return await fetchMutualAid()
    if (tab === 'batch_pets') return await fetchPets()
  } finally {
    isLoading.value = false
  }
}

const initCharts = () => {
  if (!overviewStats.value) return
  const darkMode = isDarkMode()
  const chartTextColor = darkMode ? '#94a3b8' : '#475569'
  const axisTextColor = darkMode ? '#64748b' : '#334155'
  const axisLineColor = darkMode ? 'rgba(255,255,255,0.1)' : 'rgba(15,23,42,0.12)'
  const splitLineColor = darkMode ? 'rgba(255,255,255,0.05)' : 'rgba(15,23,42,0.08)'
  const tooltipBackground = darkMode ? 'rgba(0,0,0,0.7)' : 'rgba(255,255,255,0.95)'
  const tooltipBorder = darkMode ? '#333' : '#cbd5e1'
  const tooltipText = darkMode ? '#fff' : '#0f172a'

  if (postTypeChartRef.value) {
    postTypeChart?.dispose()
    postTypeChart = echarts.init(postTypeChartRef.value)
    const totalPostCount = postTypeItems.value.reduce((sum, item) => sum + item.value, 0)
    postTypeChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)', backgroundColor: tooltipBackground, borderColor: tooltipBorder, textStyle: { color: tooltipText } },
      legend: { bottom: '0', left: 'center', textStyle: { color: chartTextColor, fontSize: 10 } },
      graphic: totalPostCount === 0 ? [{
        type: 'text',
        left: 'center',
        top: '42%',
        style: {
          text: '当前发帖数据为 0',
          fill: axisTextColor,
          fontSize: 14,
          fontWeight: 700,
        },
      }] : [],
      series: [{
        type: 'pie', radius: ['40%', '70%'], center: ['50%', '45%'],
        itemStyle: { borderRadius: 10, borderColor: 'transparent', borderWidth: 2 },
        stillShowZeroSum: true,
        label: { show: false }, emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data: postTypeItems.value.map((item) => ({ name: item.name, value: item.value })),
        color: ['#f97316', '#3b82f6', '#22c55e'],
      }],
    })
  }

  if (postTypeLineChartRef.value) {
    postTypeLineChart?.dispose()
    postTypeLineChart = echarts.init(postTypeLineChartRef.value)
    postTypeLineChart.setOption({
      tooltip: { trigger: 'axis', backgroundColor: tooltipBackground, borderColor: tooltipBorder, textStyle: { color: tooltipText } },
      grid: { left: '4%', right: '4%', top: '12%', bottom: '8%', containLabel: true },
      xAxis: {
        type: 'category',
        data: postTypeItems.value.map((item) => item.name),
        axisLabel: { color: axisTextColor, fontSize: 10 },
        axisLine: { lineStyle: { color: axisLineColor } },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        axisLabel: { color: axisTextColor },
        splitLine: { lineStyle: { color: splitLineColor, type: 'dashed' } },
      },
      series: [{
        name: '发帖数',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 10,
        data: postTypeItems.value.map((item) => item.value),
        color: '#f97316',
        lineStyle: { width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(249,115,22,0.25)' },
            { offset: 1, color: 'rgba(249,115,22,0.03)' },
          ]),
        },
      }],
    })
  }

  if (trendChartRef.value) {
    trendChart?.dispose()
    trendChart = echarts.init(trendChartRef.value)
    const dates = recentTrendSummary.value.labels
    const postCounts = recentTrendSummary.value.posts
    const appCounts = recentTrendSummary.value.applications
    trendChart.setOption({
      tooltip: { trigger: 'axis', backgroundColor: tooltipBackground, borderColor: tooltipBorder, textStyle: { color: tooltipText } },
      legend: { data: ['发帖数', '申请数'], textStyle: { color: chartTextColor }, right: '5%' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: dates, axisLabel: { color: axisTextColor, fontSize: 10 }, axisLine: { lineStyle: { color: axisLineColor } } },
      yAxis: { type: 'value', axisLabel: { color: axisTextColor }, splitLine: { lineStyle: { color: splitLineColor, type: 'dashed' } } },
      series: [
        { name: '发帖数', type: 'line', smooth: true, symbol: 'circle', symbolSize: 8, data: postCounts, color: '#f97316', areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(249,115,22,0.2)' }, { offset: 1, color: 'transparent' }]) } },
        { name: '申请数', type: 'line', smooth: true, symbol: 'circle', symbolSize: 8, data: appCounts, color: '#22c55e', areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(34,197,94,0.2)' }, { offset: 1, color: 'transparent' }]) } },
      ],
    })
  }
}
const refreshCharts = () => {
  if (activeMainTab.value !== 'overview') return
  nextTick(() => {
    initCharts()
    requestAnimationFrame(() => {
      postTypeChart?.resize()
      postTypeLineChart?.resize()
      trendChart?.resize()
    })
    if (chartRefreshTimer) clearTimeout(chartRefreshTimer)
    chartRefreshTimer = setTimeout(() => {
      postTypeChart?.resize()
      postTypeLineChart?.resize()
      trendChart?.resize()
      initCharts()
    }, 180)
  })
}

const createAnnouncement = async () => {
  if (!announcementForm.value.title.trim() || !announcementForm.value.content.trim()) {
    window.alert('请先填写公告标题和内容')
    return
  }
  isSubmittingAnnouncement.value = true
  try {
    await axios.post('/api/announcements', { ...announcementForm.value, is_hot: announcementForm.value.is_hot ? 1 : 0 })
    announcementForm.value = { title: '', content: '', is_hot: 0 }
    await fetchAnnouncements()
  } finally {
    isSubmittingAnnouncement.value = false
  }
}
const deleteAnnouncement = async (announcementId: number) => {
  if (!window.confirm('确认删除这条公告吗？')) return
  await axios.delete(`/api/announcements/${announcementId}`)
  await fetchAnnouncements()
}
const sanctionUser = async (user: any, type: 'muted' | 'banned') => {
  const reason = window.prompt(`请输入${type === 'muted' ? '禁言' : '封禁'}原因`)
  if (!reason?.trim()) return
  userActionLoading.value[user.id] = true
  try {
    await axios.post('/api/admin/users/sanction', { user_id: user.id, admin_id: authStore.user?.id ?? 0, type, reason: reason.trim(), evidence: '' })
    await fetchUsers()
  } finally {
    userActionLoading.value[user.id] = false
  }
}
const reactivateUser = async (userId: number) => {
  if (!window.confirm('确认恢复该用户状态吗？')) return
  userActionLoading.value[userId] = true
  try {
    await axios.post('/api/admin/users/reactivate', null, { params: { user_id: userId } })
    await fetchUsers()
  } finally {
    userActionLoading.value[userId] = false
  }
}

const cancelTask = async (taskId: number) => {
  const reason = window.prompt('请输入下架原因', '违规内容')
  if (!reason) return
  taskActionLoading.value[`task-${taskId}`] = true
  try {
    await axios.post(`/api/admin/mutual-aid/tasks/${taskId}/takedown`, { 
      reason,
      admin_id: authStore.user?.id
    })
    window.alert('互助任务已成功下架，反馈理由已通知发布者。')
    await fetchMutualAid()
  } catch (err: any) {
    window.alert('下架失败：' + (err.response?.data?.detail || '未知错误'))
  } finally {
    taskActionLoading.value[`task-${taskId}`] = false
  }
}

const resolveReport = async (reportId: number, action: 'cancel' | 'dismiss') => {
  if (action === 'cancel') {
    const report = mutualAidReports.value.find(r => r.id === reportId)
    if (report) {
      await cancelTask(report.task_id)
      return
    }
  }
  const note = window.prompt(action === 'cancel' ? '请输入下架处理说明' : '请输入驳回说明', '')
  if (note == null) return
  reportActionLoading.value[reportId] = true
  try {
    await axios.post(`/api/admin/mutual-aid/reports/${reportId}/resolve`, { action, note, ban_publisher: false, ban_reason: '' })
    await fetchMutualAid()
  } finally {
    reportActionLoading.value[reportId] = false
  }
}
const copyBatchTemplate = async () => {
  try {
    await navigator.clipboard.writeText(batchTemplate.value)
    window.alert('批量录入模板已复制')
  } catch {
    window.alert('当前环境不支持自动复制，请手动复制模板内容')
  }
}

const handleResize = () => { refreshCharts() }
const switchMainTab = async (tab: MainTab) => {
  activeMainTab.value = tab
  await fetchForTab(tab)
  if (tab === 'overview') refreshCharts()
}

onMounted(async () => {
  await fetchForTab('overview')
  window.addEventListener('resize', handleResize)
  themeObserver = new MutationObserver(() => { if (activeMainTab.value === 'overview') refreshCharts() })
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
})
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  themeObserver?.disconnect()
  themeObserver = null
  if (chartRefreshTimer) {
    clearTimeout(chartRefreshTimer)
    chartRefreshTimer = null
  }
  postTypeChart?.dispose()
  postTypeLineChart?.dispose()
  trendChart?.dispose()
  postTypeChart = null
  postTypeLineChart = null
  trendChart = null
})
</script>

<template>
  <div class="dashboard-view space-y-6 md:space-y-8 pb-16 md:pb-20 px-3 md:px-4">
    <div class="flex gap-3 md:gap-4 border-b border-white/5 pb-4 overflow-x-auto scrollbar-hide">
      <button @click="switchMainTab('overview')" :class="activeMainTab === 'overview' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all flex items-center gap-1"><BarChart2 :size="12" />数据总览</button>
      <button @click="switchMainTab('audit')" :class="activeMainTab === 'audit' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all">领养审核中心</button>
      <button @click="switchMainTab('users')" :class="activeMainTab === 'users' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all">全站用户治理</button>
      <button @click="switchMainTab('announcement')" :class="activeMainTab === 'announcement' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all">全站公告发布</button>
      <button @click="switchMainTab('logs')" :class="activeMainTab === 'logs' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all">内容治理日志</button>
      <button @click="switchMainTab('mutual_aid')" :class="activeMainTab === 'mutual_aid' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all flex items-center gap-1"><Handshake :size="12" />互助监控</button>
      <button @click="switchMainTab('batch_pets')" :class="activeMainTab === 'batch_pets' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-gray-500'" class="px-4 py-2 font-black uppercase tracking-widest text-xs transition-all flex items-center gap-1"><ClipboardList :size="12" />批量录入动物</button>
    </div>

    <div v-if="isLoading" class="h-96 flex items-center justify-center">
      <Loader2 class="animate-spin text-orange-500" :size="48" />
    </div>

    <div v-else class="animate-in fade-in duration-700">
      <!-- overview -->
      <div v-if="activeMainTab === 'overview'" class="space-y-6 md:space-y-8">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <h2 class="dash-section-title text-xl md:text-2xl font-black flex items-center gap-3">
            <div class="p-2 bg-orange-500/10 text-orange-500 rounded-lg"><BarChart2 :size="20" /></div>
            平台运营总览
          </h2>
          <div class="flex flex-wrap items-center gap-2">
            <span v-if="overviewDemoEnhanced" class="inline-flex items-center rounded-full bg-amber-100 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">
              当前为展示增强数据
            </span>
            <p class="text-[10px] md:text-xs text-gray-500 uppercase tracking-widest font-black">框架升级后的运营与审核指标</p>
          </div>
        </div>

        <div v-if="overviewStats?.summary" class="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
          <BaseCard v-for="card in [
            { label: '总发帖数', value: overviewStats.summary.total_posts, icon: FileText, color: 'text-orange-500' },
            { label: '领养成功数', value: overviewStats.summary.successful_adoptions, icon: Heart, color: 'text-green-500' },
            { label: '总申请数', value: overviewStats.summary.total_applications, icon: ClipboardList, color: 'text-blue-500' },
            { label: '总用户数', value: overviewStats.summary.total_users, icon: Users, color: 'text-yellow-600' },
            { label: 'AI 评估记录', value: overviewStats.summary.total_ai_reviews, icon: ShieldCheck, color: 'text-emerald-500' },
            { label: '追问记录数', value: overviewStats.summary.total_followups, icon: Waypoints, color: 'text-orange-600' },
            { label: '案例记忆数', value: overviewStats.summary.total_case_memories, icon: Activity, color: 'text-cyan-600' },
            { label: '待人工复核', value: overviewStats.summary.pending_manual_review, icon: AlertTriangle, color: 'text-rose-500' },
          ]" :key="card.label" class="!p-5 md:!p-7 space-y-3 md:space-y-4 shadow-xl">
            <div class="flex items-center justify-between">
              <component :is="card.icon" :size="24" :class="card.color" />
              <span class="dash-card-label text-xs md:text-sm uppercase tracking-widest font-black">{{ card.label }}</span>
            </div>
            <p :class="['text-3xl md:text-5xl font-black break-words tracking-tighter', card.color]">{{ card.value }}</p>
          </BaseCard>
        </div>

        <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <BaseCard class="overview-panel xl:col-span-1 !p-6 space-y-5">
            <div class="overview-panel-head flex items-center gap-3 font-black text-lg text-slate-900 dark:text-white">
              <FileText :size="20" class="text-orange-400" /> 发帖类型分布
            </div>
            <div class="overview-panel-body bg-slate-50 text-slate-900 border border-slate-200 dark:bg-white/5 dark:text-white dark:border-white/10">
              <div class="grid grid-cols-1 xl:grid-cols-2 gap-4 items-stretch">
                <div class="rounded-2xl border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
                  <div class="mb-3 flex items-center justify-between gap-2">
                    <p class="text-sm font-black text-slate-900 dark:text-white">发帖类型占比</p>
                    <span class="text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">饼图视图</span>
                  </div>
                  <div ref="postTypeChartRef" class="h-64 md:h-[20rem] w-full"></div>
                </div>
                <div class="rounded-2xl border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
                  <div class="mb-3 flex items-center justify-between gap-2">
                    <p class="text-sm font-black text-slate-900 dark:text-white">发帖类型折线图</p>
                    <span class="text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">按当前类型统计</span>
                  </div>
                  <div ref="postTypeLineChartRef" class="h-64 md:h-[20rem] w-full"></div>
                </div>
              </div>
              <div class="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div v-for="item in postTypeItems" :key="item.name" class="rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-white/10 dark:bg-white/5">
                  <div class="flex items-center gap-2 text-xs font-bold text-slate-600 dark:text-slate-400">
                    <span :class="item.color" class="inline-block h-2.5 w-2.5 rounded-full"></span>
                    {{ item.name }}
                  </div>
                  <p class="mt-2 text-2xl font-black text-slate-900 dark:text-white">{{ item.value }}</p>
                </div>
              </div>
            </div>
          </BaseCard>
          <BaseCard class="overview-panel xl:col-span-2 !p-6 space-y-5">
            <div class="overview-panel-head flex items-center gap-3 font-black text-lg text-slate-900 dark:text-white">
              <Activity :size="20" class="text-green-400" /> 近 7 天平台活跃趋势
            </div>
            <div class="overview-panel-body bg-slate-50 text-slate-900 border border-slate-200 dark:bg-white/5 dark:text-white dark:border-white/10">
              <div ref="trendChartRef" class="h-64 md:h-80 w-full"></div>
              <div class="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div class="rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-white/10 dark:bg-white/5">
                  <p class="text-xs font-bold uppercase tracking-widest text-slate-600 dark:text-slate-400">近 7 天发帖总数</p>
                  <p class="mt-2 text-2xl font-black text-orange-500">{{ recentTrendSummary.postTotal }}</p>
                </div>
                <div class="rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-white/10 dark:bg-white/5">
                  <p class="text-xs font-bold uppercase tracking-widest text-slate-600 dark:text-slate-400">近 7 天申请总数</p>
                  <p class="mt-2 text-2xl font-black text-green-500">{{ recentTrendSummary.applicationTotal }}</p>
                </div>
              </div>
            </div>
          </BaseCard>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <BaseCard class="overview-panel !p-6 space-y-5">
            <div class="overview-panel-head flex items-center gap-2 font-black text-slate-900 dark:text-white">
              <ClipboardList :size="18" class="text-orange-400" /> 领养申请状态分布
            </div>
            <div class="overview-panel-body space-y-4 bg-slate-50 text-slate-900 border border-slate-200 dark:bg-white/5 dark:text-white dark:border-white/10">
              <div v-for="item in [
                { label: '待处理', value: (overviewStats?.application_breakdown?.pending_owner_review || 0) + (overviewStats?.application_breakdown?.pending || 0), color: 'bg-yellow-500' },
                { label: '已通过', value: overviewStats?.application_breakdown?.approved || 0, color: 'bg-green-500' },
                { label: '已拒绝', value: overviewStats?.application_breakdown?.rejected || 0, color: 'bg-red-500' },
                { label: '待补充', value: overviewStats?.summary?.pending_followups || 0, color: 'bg-orange-500' },
              ]" :key="item.label" class="space-y-1">
                <div class="flex justify-between text-xs">
                  <span class="font-bold text-slate-600 dark:text-slate-400">{{ item.label }}</span>
                  <span class="font-black text-slate-900 dark:text-white">{{ item.value }}</span>
                </div>
                <div class="h-2 rounded-full bg-slate-200 dark:bg-white/5 overflow-hidden">
                  <div class="h-full transition-all duration-1000" :class="item.color" :style="{ width: `${Math.max(5, (item.value / Math.max(1, overviewStats?.summary?.total_applications || 1)) * 100)}%` }"></div>
                </div>
              </div>
            </div>
          </BaseCard>
          <BaseCard class="overview-panel !p-6 space-y-5">
            <div class="overview-panel-head flex items-center gap-2 font-black text-slate-900 dark:text-white">
              <ShieldCheck :size="18" class="text-emerald-400" /> AI 建议采纳情况
            </div>
            <div class="overview-panel-body flex items-center justify-around h-full pt-4 bg-slate-50 text-slate-900 border border-slate-200 dark:bg-white/5 dark:text-white dark:border-white/10">
              <div class="text-center space-y-2">
                <p class="text-xs font-bold uppercase text-slate-600 dark:text-slate-400">采纳次数</p>
                <p class="text-4xl font-black text-lime-500">{{ overviewStats?.summary?.owner_followed_ai || 0 }}</p>
              </div>
              <div class="w-px h-12 bg-slate-200 dark:bg-white/10"></div>
              <div class="text-center space-y-2">
                <p class="text-xs font-bold uppercase text-slate-600 dark:text-slate-400">拒绝/手动</p>
                <p class="text-4xl font-black text-rose-500">{{ overviewStats?.summary?.owner_rejected_ai || 0 }}</p>
              </div>
            </div>
          </BaseCard>
          <BaseCard class="overview-panel !p-6 space-y-5">
            <div class="overview-panel-head flex items-center gap-2 font-black text-slate-900 dark:text-white">
              <Waypoints :size="18" class="text-cyan-400" /> 框架路由动作
            </div>
            <div class="overview-panel-body space-y-3 bg-slate-50 text-slate-900 border border-slate-200 dark:bg-white/5 dark:text-white dark:border-white/10">
              <div class="flex items-center justify-between text-sm"><span class="font-bold text-slate-600 dark:text-slate-400">追问分流</span><span class="font-black text-slate-900 dark:text-white">{{ overviewStats?.framework_breakdown?.route_followup || 0 }}</span></div>
              <div class="flex items-center justify-between text-sm"><span class="font-bold text-slate-600 dark:text-slate-400">人工复核</span><span class="font-black text-slate-900 dark:text-white">{{ overviewStats?.framework_breakdown?.route_manual_review || 0 }}</span></div>
              <div class="flex items-center justify-between text-sm"><span class="font-bold text-slate-600 dark:text-slate-400">发布者决策</span><span class="font-black text-slate-900 dark:text-white">{{ overviewStats?.framework_breakdown?.route_publisher_review || 0 }}</span></div>
            </div>
          </BaseCard>
        </div>
      </div>

      <div v-else-if="activeMainTab === 'audit'" class="space-y-6">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <h2 class="text-2xl font-black flex items-center gap-3 text-slate-900 dark:text-white"><div class="p-2 bg-orange-500/10 text-orange-500 rounded-lg"><ClipboardList :size="20" /></div>领养审核中心</h2>
          <p class="text-[10px] md:text-xs text-gray-500 uppercase tracking-widest font-black">共识融合 / 路由决策 / 案例记忆</p>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <BaseCard class="!p-5 space-y-2"><p class="dash-card-label text-xs uppercase tracking-widest font-black">待补充信息</p><p class="text-3xl font-black text-orange-500">{{ overviewStats?.summary?.pending_followups || 0 }}</p></BaseCard>
          <BaseCard class="!p-5 space-y-2"><p class="dash-card-label text-xs uppercase tracking-widest font-black">人工复核</p><p class="text-3xl font-black text-rose-500">{{ overviewStats?.summary?.pending_manual_review || 0 }}</p></BaseCard>
          <BaseCard class="!p-5 space-y-2"><p class="dash-card-label text-xs uppercase tracking-widest font-black">等待发布者</p><p class="text-3xl font-black text-blue-500">{{ overviewStats?.summary?.waiting_publisher || 0 }}</p></BaseCard>
          <BaseCard class="!p-5 space-y-2"><p class="dash-card-label text-xs uppercase tracking-widest font-black">案例记忆</p><p class="text-3xl font-black text-cyan-500">{{ overviewStats?.summary?.total_case_memories || 0 }}</p></BaseCard>
        </div>
        <template v-if="auditApplications.length">
          <BaseCard v-for="app in auditApplications" :key="app.id" class="!p-6 space-y-5">
            <div class="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
              <div class="space-y-2">
                <div class="flex flex-wrap items-center gap-2">
                  <h3 class="text-xl font-black text-slate-900 dark:text-white">{{ app.pet_name || `宠物 ${app.pet_id}` }}</h3>
                  <span v-if="app.is_demo" class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">演示</span>
                  <span :class="routeTone(app.route_decision)" class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest">{{ routeLabel(app.route_decision) }}</span>
                  <span :class="riskTone(app.risk_level)" class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest">{{ app.risk_level || 'Medium' }}</span>
                </div>
                <p class="text-sm text-slate-600 dark:text-slate-400">申请人：<span class="font-bold text-slate-900 dark:text-white">{{ app.user_name || '未知用户' }}</span> · 发布者：<span class="font-bold text-slate-900 dark:text-white">{{ app.owner_name || '未知送养方' }}</span></p>
                <p class="text-sm text-slate-600 dark:text-slate-400">流程状态：<span class="font-bold text-slate-900 dark:text-white">{{ flowStatusLabel(app.flow_status) }}</span> · 当前状态：<span class="font-bold text-slate-900 dark:text-white">{{ app.status }}</span></p>
              </div>
              <div class="grid grid-cols-3 gap-3 min-w-[280px]">
                <div class="rounded-2xl bg-slate-50 border border-slate-200 px-4 py-3 dark:bg-white/5 dark:border-white/10"><p class="text-[10px] uppercase tracking-widest font-black text-slate-500 dark:text-slate-400">准备度</p><p class="text-2xl font-black text-orange-500">{{ app.ai_readiness_score ?? app.latest_ai_review?.overall_score ?? 'N/A' }}</p></div>
                <div class="rounded-2xl bg-slate-50 border border-slate-200 px-4 py-3 dark:bg-white/5 dark:border-white/10"><p class="text-[10px] uppercase tracking-widest font-black text-slate-500 dark:text-slate-400">共识分</p><p class="text-2xl font-black text-cyan-500">{{ formatConsensus(app.latest_ai_review?.consensus_score ?? app.consensus_result?.consensus_score) }}</p></div>
                <div class="rounded-2xl bg-slate-50 border border-slate-200 px-4 py-3 dark:bg-white/5 dark:border-white/10"><p class="text-[10px] uppercase tracking-widest font-black text-slate-500 dark:text-slate-400">分歧度</p><p class="text-2xl font-black text-rose-500">{{ formatConsensus(app.latest_ai_review?.disagreement_score ?? app.consensus_result?.disagreement_score) }}</p></div>
              </div>
            </div>
            <div class="grid grid-cols-1 xl:grid-cols-3 gap-4">
              <div class="rounded-2xl bg-slate-50 border border-slate-200 p-4 space-y-3 dark:bg-white/5 dark:border-white/10">
                <p class="text-[10px] uppercase tracking-widest font-black text-slate-500 dark:text-slate-400">风险标签</p>
                <div class="flex flex-wrap gap-2">
                  <span v-for="tag in (app.consensus_result?.risk_tags || app.case_memory?.risk_tags || [])" :key="tag" class="px-3 py-1 rounded-full bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300 text-[10px] font-black uppercase tracking-widest">{{ tag }}</span>
                  <span v-if="!(app.consensus_result?.risk_tags || app.case_memory?.risk_tags || []).length" class="text-sm text-slate-500 dark:text-slate-400">暂无风险标签</span>
                </div>
              </div>
              <div class="rounded-2xl bg-slate-50 border border-slate-200 p-4 space-y-3 dark:bg-white/5 dark:border-white/10">
                <p class="text-[10px] uppercase tracking-widest font-black text-slate-500 dark:text-slate-400">建议追问</p>
                <ul v-if="app.followup_questions?.length" class="space-y-2">
                  <li v-for="question in app.followup_questions.slice(0, 3)" :key="question" class="text-sm leading-6 text-slate-600 dark:text-slate-300">? {{ question }}</li>
                </ul>
                <p v-else class="text-sm text-slate-500 dark:text-slate-400">当前无需额外追问。</p>
              </div>
              <div class="rounded-2xl bg-slate-50 border border-slate-200 p-4 space-y-3 dark:bg-white/5 dark:border-white/10">
                <p class="text-[10px] uppercase tracking-widest font-black text-slate-500 dark:text-slate-400">案例记忆摘要</p>
                <p class="text-sm leading-6 text-slate-600 dark:text-slate-300">{{ app.case_memory?.case_summary || '当前尚未生成案例记忆摘要。' }}</p>
              </div>
            </div>
            <div v-if="app.recent_followups?.length" class="rounded-2xl bg-slate-50 border border-slate-200 p-4 space-y-3 dark:bg-white/5 dark:border-white/10">
              <p class="text-[10px] uppercase tracking-widest font-black text-slate-500 dark:text-slate-400">最近追问记录</p>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div v-for="item in app.recent_followups" :key="`${item.question}-${item.created_at}`" class="rounded-xl bg-white border border-slate-200 p-3 space-y-2 dark:bg-white/5 dark:border-white/5">
                  <p class="text-xs font-black text-orange-500">{{ item.question }}</p>
                  <p class="text-xs leading-6 text-slate-600 dark:text-slate-300">{{ item.answer || '未填写回答' }}</p>
                  <p class="text-[10px] text-slate-400 uppercase tracking-widest dark:text-slate-500">来源：{{ item.source }}</p>
                </div>
              </div>
            </div>
          </BaseCard>
        </template>
        <BaseCard v-else class="!p-8 text-center"><p class="dash-text-strong font-bold">当前暂无可展示的审核记录。</p></BaseCard>
      </div>

      <div v-else-if="activeMainTab === 'users'" class="space-y-6">
        <div class="flex items-center justify-between mb-2">
          <h2 class="dash-section-title text-2xl font-black flex items-center gap-3"><div class="p-2 bg-blue-500/10 text-blue-500 rounded-lg"><Users :size="20" /></div>系统用户列表</h2>
          <p class="text-[10px] md:text-xs text-gray-500 uppercase tracking-widest font-black">维持原有管理布局，补充直接治理动作</p>
        </div>
        <BaseCard class="!p-0 overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-white/5 border-b border-white/10">
                <tr>
                  <th class="px-4 py-3 text-left dash-card-label font-black uppercase tracking-widest">用户名</th>
                  <th class="px-4 py-3 text-left dash-card-label font-black uppercase tracking-widest">邮箱</th>
                  <th class="px-4 py-3 text-left dash-card-label font-black uppercase tracking-widest">角色</th>
                  <th class="px-4 py-3 text-left dash-card-label font-black uppercase tracking-widest">状态</th>
                  <th class="px-4 py-3 text-left dash-card-label font-black uppercase tracking-widest">治理动作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="user in allUsers" :key="user.id" class="border-b border-white/5">
                  <td class="px-4 py-4 dash-text-strong font-bold">
                    <div class="flex flex-wrap items-center gap-2">
                      <span>{{ user.username }}</span>
                      <span v-if="user.is_demo" class="px-2 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">演示</span>
                    </div>
                  </td>
                  <td class="px-4 py-4 text-gray-500">{{ user.email }}</td>
                  <td class="px-4 py-4 text-gray-500">{{ user.role }}</td>
                  <td class="px-4 py-4">
                    <span class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest" :class="userStatusTone(user.status)">{{ user.status || 'active' }}</span>
                  </td>
                  <td class="px-4 py-4">
                    <div class="flex flex-wrap gap-2">
                      <button v-if="!user.is_demo && user.status !== 'muted' && user.role !== 'admin'" @click="sanctionUser(user, 'muted')" :disabled="!!userActionLoading[user.id]" class="inline-flex items-center gap-1 px-3 py-2 rounded-xl text-xs font-black bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 disabled:opacity-50 transition-all"><VolumeX :size="12" />禁言</button>
                      <button v-if="!user.is_demo && user.status !== 'banned' && user.role !== 'admin'" @click="sanctionUser(user, 'banned')" :disabled="!!userActionLoading[user.id]" class="inline-flex items-center gap-1 px-3 py-2 rounded-xl text-xs font-black bg-red-500/10 text-red-500 hover:bg-red-500/20 disabled:opacity-50 transition-all"><Ban :size="12" />封禁</button>
                      <button v-if="!user.is_demo && (user.status === 'muted' || user.status === 'banned')" @click="reactivateUser(user.id)" :disabled="!!userActionLoading[user.id]" class="inline-flex items-center gap-1 px-3 py-2 rounded-xl text-xs font-black bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 disabled:opacity-50 transition-all"><RefreshCcw :size="12" />恢复</button>
                      <span v-if="user.is_demo" class="text-xs text-amber-600 dark:text-amber-300">演示账号仅供展示，不触发治理操作</span>
                      <span v-if="user.role === 'admin'" class="text-xs text-gray-500">系统管理员账号默认不做前台封禁</span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </BaseCard>
      </div>

      <div v-else-if="activeMainTab === 'announcement'" class="space-y-6">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <h2 class="text-2xl font-black flex items-center gap-3 text-slate-900 dark:text-white"><div class="p-2 bg-orange-500/10 text-orange-500 rounded-lg"><Megaphone :size="20" /></div>全站公告发布</h2>
          <p class="text-[10px] md:text-xs text-gray-500 uppercase tracking-widest font-black">保留原有后台风格，补回公告编发能力</p>
        </div>
        <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <BaseCard class="xl:col-span-1 !p-6 space-y-4">
            <div class="flex items-center gap-2 font-black text-slate-900 dark:text-white"><Plus :size="18" class="text-orange-400" /> 发布新公告</div>
            <input v-model="announcementForm.title" type="text" placeholder="公告标题" class="w-full rounded-2xl bg-slate-50 border border-slate-200 px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 outline-none dark:bg-white/5 dark:border-white/10 dark:text-white dark:placeholder:text-slate-500" />
            <textarea v-model="announcementForm.content" rows="8" placeholder="公告内容" class="w-full rounded-2xl bg-slate-50 border border-slate-200 px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 outline-none resize-none dark:bg-white/5 dark:border-white/10 dark:text-white dark:placeholder:text-slate-500"></textarea>
            <label class="inline-flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400">
              <input v-model="announcementForm.is_hot" :true-value="1" :false-value="0" type="checkbox" class="rounded border-slate-300 bg-white text-orange-500 dark:border-white/10 dark:bg-white/5" />
              设为热门公告
            </label>
            <button @click="createAnnouncement" :disabled="isSubmittingAnnouncement" class="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-2xl bg-orange-500 text-white text-sm font-black hover:bg-orange-600 disabled:opacity-60 transition-all">
              <Loader2 v-if="isSubmittingAnnouncement" class="animate-spin" :size="16" />
              <Plus v-else :size="16" />
              发布公告
            </button>
          </BaseCard>
          <BaseCard class="xl:col-span-2 !p-6 space-y-4">
            <div class="flex items-center gap-2 font-black text-slate-900 dark:text-white"><ScrollText :size="18" class="text-blue-400" /> 已发布公告</div>
            <div v-if="announcements.length" class="space-y-4">
              <div v-for="item in announcements" :key="item.id" class="rounded-2xl bg-slate-50 border border-slate-200 p-5 space-y-3 dark:bg-white/5 dark:border-white/10">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div class="flex flex-wrap items-center gap-2">
                    <h3 class="text-lg font-black text-slate-900 dark:text-white">{{ item.title }}</h3>
                    <span v-if="item.is_hot" class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300">热门</span>
                    <span v-if="item.is_demo" class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">演示</span>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-xs text-gray-500">{{ formatDateOnly(item.date) }}</span>
                    <button v-if="!item.is_demo" @click="deleteAnnouncement(item.id)" class="inline-flex items-center gap-1 px-3 py-2 rounded-xl text-xs font-black bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-all"><Trash2 :size="12" />删除</button>
                  </div>
                </div>
                <p class="text-sm leading-7 text-slate-600 whitespace-pre-line dark:text-slate-300">{{ item.content }}</p>
              </div>
            </div>
            <div v-else class="rounded-2xl bg-slate-50 border border-slate-200 p-8 text-center text-slate-500 dark:bg-white/5 dark:border-white/10 dark:text-slate-400">当前还没有公告内容。</div>
          </BaseCard>
        </div>
      </div>

      <div v-else-if="activeMainTab === 'logs'" class="space-y-6">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <h2 class="dash-section-title text-2xl font-black flex items-center gap-3"><div class="p-2 bg-orange-500/10 text-orange-500 rounded-lg"><ScrollText :size="20" /></div>内容治理日志</h2>
          <p class="dash-card-label text-[10px] md:text-xs uppercase tracking-widest font-black">审核处置日志与 AI Trace 双视图</p>
        </div>
        <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <BaseCard class="!p-6 space-y-4">
            <div class="dash-card-header flex items-center gap-2 font-black"><ShieldCheck :size="18" class="text-rose-400" /> 内容处置日志</div>
            <div v-if="moderationLogs.length" class="space-y-4 max-h-[34rem] overflow-y-auto pr-1">
              <div v-for="log in moderationLogs" :key="log.id" class="dash-log-card rounded-2xl p-4 space-y-2">
                <div class="flex items-center justify-between gap-3"><span class="dash-text-strong font-black">目标 ID #{{ log.target_id }}</span><div class="flex items-center gap-2"><span v-if="log.is_demo" class="px-2 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">演示</span><span class="dash-card-label text-xs">{{ formatDateTime(log.delete_time) }}</span></div></div>
                <p class="dash-log-desc text-sm leading-7">{{ log.reason }}</p>
                <p class="dash-log-meta text-xs uppercase tracking-widest">管理员：{{ log.admin_id || '未知' }}</p>
              </div>
            </div>
            <div v-else class="dash-log-empty rounded-2xl p-8 text-center">当前没有内容治理日志。</div>
          </BaseCard>
          <BaseCard class="!p-6 space-y-4">
            <div class="dash-card-header flex items-center gap-2 font-black"><Sparkles :size="18" class="text-cyan-400" /> AI 执行轨迹</div>
            <div v-if="aiTraces.length" class="space-y-4 max-h-[34rem] overflow-y-auto pr-1">
              <div v-for="trace in aiTraces" :key="trace.id" class="dash-log-card rounded-2xl p-4 space-y-2">
                <div class="flex items-center justify-between gap-3"><span class="dash-text-strong font-black">{{ shortTrace(trace.trace_id) }}</span><div class="flex items-center gap-2"><span v-if="trace.is_demo" class="px-2 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">演示</span><span class="dash-card-label text-xs">{{ formatDateTime(trace.create_time) }}</span></div></div>
                <p class="dash-log-meta text-xs uppercase tracking-widest">接口：{{ trace.endpoint || '未记录' }}</p>
                <p class="dash-log-desc text-sm leading-7 line-clamp-3">{{ trace.message || trace.summary || '该记录未携带额外说明。' }}</p>
              </div>
            </div>
            <div v-else class="dash-log-empty rounded-2xl p-8 text-center">当前没有 AI 轨迹日志。</div>
          </BaseCard>
        </div>
      </div>

      <div v-else-if="activeMainTab === 'mutual_aid'" class="space-y-6">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <h2 class="dash-section-title text-2xl font-black flex items-center gap-3"><div class="p-2 bg-orange-500/10 text-orange-500 rounded-lg"><Handshake :size="20" /></div>互助监控</h2>
          <p class="text-[10px] md:text-xs text-gray-500 uppercase tracking-widest font-black">任务总览、异常下架、举报仲裁</p>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <BaseCard v-for="card in [
            { label: '总任务数', value: mutualAidStats?.total || 0, color: 'text-orange-500' },
            { label: '今日新增', value: mutualAidStats?.today_new || 0, color: 'text-blue-500' },
            { label: '接单率', value: `${mutualAidStats?.accept_rate || 0}%`, color: 'text-emerald-500' },
            { label: '待处理举报', value: mutualAidStats?.pending_reports || 0, color: 'text-rose-500' },
          ]" :key="card.label" class="!p-5 space-y-2">
            <p class="dash-card-label text-xs uppercase tracking-widest font-black">{{ card.label }}</p>
            <p :class="['text-3xl font-black', card.color]">{{ card.value }}</p>
          </BaseCard>
        </div>
        <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <BaseCard class="!p-6 space-y-4">
            <div class="dash-card-header flex items-center gap-2 font-black"><ClipboardList :size="18" class="text-orange-400" /> 最近互助任务</div>
            <div v-if="mutualAidTasks.length" class="space-y-4 max-h-[40rem] overflow-y-auto pr-1">
              <div v-for="task in mutualAidTasks" :key="task.id" class="rounded-2xl bg-white/5 border border-white/10 p-4 space-y-3">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div class="space-y-1">
                    <div class="flex flex-wrap items-center gap-2">
                      <p class="dash-text-strong font-black">{{ task.task_type }} · {{ task.pet_name }}</p>
                      <span v-if="task.is_demo" class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">演示</span>
                      <span class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest" :class="task.status === 'cancelled' ? 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300' : task.status === 'completed' ? 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300' : task.status === 'accepted' ? 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300'">{{ taskStatusLabel(task.status) }}</span>
                    </div>
                    <p class="text-sm text-gray-500">发布者：{{ task.publisher_name || '未知用户' }} · {{ task.location || '未填写地点' }}</p>
                  </div>
                  <button v-if="!task.is_demo && task.status !== 'cancelled' && task.status !== 'completed'" @click="cancelTask(task.id)" :disabled="!!taskActionLoading[`task-${task.id}`]" class="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-black bg-red-500/10 text-red-500 hover:bg-red-500/20 disabled:opacity-50 transition-all"><Ban :size="12" />强制下架</button>
                </div>
                <p class="text-sm leading-7 text-gray-500">{{ task.description || '暂无任务说明。' }}</p>
                <p class="text-xs text-gray-400 uppercase tracking-widest">发布时间：{{ formatDateTime(task.create_time) }}</p>
              </div>
            </div>
            <div v-else class="rounded-2xl bg-white/5 border border-white/10 p-8 text-center text-gray-500">当前没有互助任务记录。</div>
          </BaseCard>
          <BaseCard class="!p-6 space-y-4">
            <div class="dash-card-header flex items-center gap-2 font-black"><AlertTriangle :size="18" class="text-rose-400" /> 举报仲裁</div>
            <div v-if="mutualAidReports.length" class="space-y-4 max-h-[40rem] overflow-y-auto pr-1">
              <div v-for="report in mutualAidReports" :key="report.id" class="rounded-2xl bg-white/5 border border-white/10 p-4 space-y-3">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div class="space-y-1">
                    <div class="flex flex-wrap items-center gap-2">
                      <p class="dash-text-strong font-black">举报 #{{ report.id }} · {{ report.pet_name || '未命名任务' }}</p>
                      <span v-if="report.is_demo" class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">演示</span>
                      <span class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest" :class="report.status === 'pending' ? 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300' : report.status === 'resolved_cancel' ? 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300' : 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300'">{{ reportStatusLabel(report.status) }}</span>
                    </div>
                    <p class="text-sm text-gray-500">举报人：{{ report.reporter_name || '未知用户' }} · 发布者：{{ report.task_owner_name || '未知用户' }}</p>
                  </div>
                  <div v-if="!report.is_demo && report.status === 'pending'" class="flex flex-wrap gap-2">
                    <button @click="resolveReport(report.id, 'dismiss')" :disabled="!!reportActionLoading[report.id]" class="inline-flex items-center gap-1 px-3 py-2 rounded-xl text-xs font-black bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 disabled:opacity-50 transition-all">驳回举报</button>
                    <button @click="resolveReport(report.id, 'cancel')" :disabled="!!reportActionLoading[report.id]" class="inline-flex items-center gap-1 px-3 py-2 rounded-xl text-xs font-black bg-red-500/10 text-red-500 hover:bg-red-500/20 disabled:opacity-50 transition-all">下架任务</button>
                  </div>
                </div>
                <p class="text-sm leading-7 text-gray-500">{{ report.reason }}</p>
                <p class="text-xs text-gray-400 uppercase tracking-widest">提交时间：{{ formatDateTime(report.create_time) }}</p>
              </div>
            </div>
            <div v-else class="rounded-2xl bg-white/5 border border-white/10 p-8 text-center text-gray-500">当前没有待处理举报。</div>
          </BaseCard>
        </div>
      </div>

      <div v-else-if="activeMainTab === 'batch_pets'" class="space-y-6">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <h2 class="dash-section-title text-2xl font-black flex items-center gap-3"><div class="p-2 bg-orange-500/10 text-orange-500 rounded-lg"><PackagePlus :size="20" /></div>批量录入动物</h2>
          <p class="text-[10px] md:text-xs text-gray-500 uppercase tracking-widest font-black">保留入口，不改权限设计，提供模板与结果预览</p>
        </div>
        <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <BaseCard class="xl:col-span-1 !p-6 space-y-4">
            <div class="dash-card-header flex items-center gap-2 font-black"><ClipboardList :size="18" class="text-orange-400" /> 批量录入模板</div>
            <p class="text-sm leading-7 text-gray-500">当前批量录入接口仍保持原有权限设计，仅限 <span class="dash-text-strong font-bold">org_admin</span> 使用。这里保留后台入口，方便系统管理员查看模板与联调格式，不直接改动既有角色边界。</p>
            <pre class="rounded-2xl bg-white/5 border border-white/10 p-4 text-xs leading-6 overflow-x-auto dash-text-strong">{{ batchTemplate }}</pre>
            <button @click="copyBatchTemplate" class="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-2xl bg-blue-500/10 text-blue-500 text-sm font-black hover:bg-blue-500/20 transition-all"><ClipboardList :size="16" />复制模板</button>
          </BaseCard>
          <BaseCard class="xl:col-span-2 !p-6 space-y-4">
            <div class="dash-card-header flex items-center gap-2 font-black"><Heart :size="18" class="text-green-400" /> 最近宠物数据预览</div>
            <div v-if="latestPets.length" class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div v-for="pet in latestPets" :key="pet.id" class="rounded-2xl bg-white/5 border border-white/10 p-4 space-y-2">
                <div class="flex items-center justify-between gap-3">
                  <div class="flex flex-wrap items-center gap-2">
                    <p class="dash-text-strong font-black">{{ pet.name }}</p>
                    <span v-if="pet.is_demo" class="px-2 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">演示</span>
                  </div>
                  <span class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300">{{ pet.status || '待领养' }}</span>
                </div>
                <p class="text-sm text-gray-500">{{ pet.species || '未知物种' }} · {{ pet.pet_age || pet.age || '年龄未填' }}</p>
                <p class="text-sm leading-7 text-gray-500 line-clamp-3">{{ pet.description || pet.post_content || '暂无描述' }}</p>
              </div>
            </div>
            <div v-else class="rounded-2xl bg-white/5 border border-white/10 p-8 text-center text-gray-500">当前还没有可预览的宠物数据。</div>
          </BaseCard>
        </div>
      </div>

      <div v-else class="space-y-6">
        <BaseCard class="!p-8 text-center"><p class="dash-text-strong font-bold">当前没有可展示内容。</p></BaseCard>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 默认模式（白天模式）- 使用深色文字 */
.dash-section-title, .dash-card-header, .dash-text-strong { color: #0f172a; }
.dash-card-label { color: #475569; }
.dash-log-desc { color: #334155; }
.dash-log-meta { color: #64748b; }

.dash-log-card {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
}
.dash-log-empty {
  background-color: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #64748b;
}

.overview-panel-head {
  padding: 0.95rem 1rem;
  border-radius: 1.25rem;
  background: linear-gradient(135deg, #fff7ed 0%, #ffffff 100%);
  border: 1px solid #fed7aa;
  box-shadow: 0 8px 24px rgba(249, 115, 22, 0.08);
}
.overview-panel-body {
  padding: 1rem;
  border-radius: 1.5rem;
  background: #f8fafc;
  border: 1px solid #dbe4f0;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.08);
}

/* 深色模式（Dark Mode）- 只有在 .dark 类存在时才切换为白色文字 */
:global(.dark) .dash-section-title, 
:global(.dark) .dash-card-header, 
:global(.dark) .dash-text-strong { color: #ffffff !important; }

:global(.dark) .dash-card-label { color: #94a3b8 !important; }

:global(.dark) .dash-log-card {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
}
:global(.dark) .dash-log-desc { color: #94a3b8 !important; }
:global(.dark) .dash-log-meta { color: #64748b !important; }
:global(.dark) .dash-log-empty {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  color: #64748b !important;
}

:global(.dark) .overview-panel-head {
  background: rgba(255, 255, 255, 0.06) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  box-shadow: none !important;
}
:global(.dark) .overview-panel-body {
  background: rgba(255, 255, 255, 0.04) !important;
  border: 1px solid rgba(255, 255, 255, 0.06) !important;
  box-shadow: none !important;
}

/* 额外的兜底：处理全局选择器 */
:global(html:not(.dark)) .dashboard-view input,
:global(html:not(.dark)) .dashboard-view textarea,
:global(html:not(.dark)) .dashboard-view pre {
  color: #0f172a !important;
  background-color: #f8fafc !important;
}
</style>
