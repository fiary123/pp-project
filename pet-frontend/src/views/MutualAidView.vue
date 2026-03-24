<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  Handshake, PlusCircle, ListChecks, BrainCircuit, Loader2,
  CheckCircle2, MapPin, Clock, Cat, Star, Flag, X,
  ClipboardList, AlertTriangle
} from 'lucide-vue-next'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'
import { useAuthStore } from '../store/authStore'

const authStore = useAuthStore()

// ── Tab ──────────────────────────────────────────────────
const activeTab = ref<'list' | 'publish' | 'mine'>('list')

// ── 任务列表（大厅） ───────────────────────────────────────
const tasks = ref<any[]>([])
const isLoadingTasks = ref(false)

const fetchTasks = async () => {
  isLoadingTasks.value = true
  try {
    const res = await axios.get('/api/mutual-aid/tasks', { params: { status: 'open' } })
    tasks.value = res.data
  } catch { tasks.value = [] }
  finally { isLoadingTasks.value = false }
}

// ── 我的互助 ─────────────────────────────────────────────
const myPublished = ref<any[]>([])
const myAccepted  = ref<any[]>([])
const isLoadingMine = ref(false)

const fetchMine = async () => {
  isLoadingMine.value = true
  try {
    const res = await axios.get('/api/mutual-aid/tasks/mine')
    myPublished.value = res.data.published
    myAccepted.value  = res.data.accepted
  } catch { myPublished.value = []; myAccepted.value = [] }
  finally { isLoadingMine.value = false }
}

const switchTab = (tab: 'list' | 'publish' | 'mine') => {
  activeTab.value = tab
  if (tab === 'list') fetchTasks()
  if (tab === 'mine') fetchMine()
}

// ── 发布表单 ──────────────────────────────────────────────
const form = ref({
  task_type: '上门喂养', pet_name: '', pet_species: '猫',
  start_time: '', end_time: '', location: '', description: '',
})
const taskTypes = ['上门喂养', '上门铲屎', '代遛狗', '宠物陪伴', '其他互助']
const isPublishing = ref(false)
const publishSuccess = ref(false)

const publishTask = async () => {
  if (!form.value.pet_name || !form.value.location || !form.value.start_time) return
  isPublishing.value = true
  publishSuccess.value = false
  try {
    await axios.post('/api/mutual-aid/tasks', { ...form.value, user_id: authStore.user?.id })
    publishSuccess.value = true
    form.value = { task_type: '上门喂养', pet_name: '', pet_species: '猫', start_time: '', end_time: '', location: '', description: '' }
    await fetchTasks()
    switchTab('list')
  } catch { } finally { isPublishing.value = false }
}

// ── 接单 ──────────────────────────────────────────────────
const acceptingId = ref<number | null>(null)

const acceptTask = async (taskId: number) => {
  acceptingId.value = taskId
  try {
    await axios.post(`/api/mutual-aid/tasks/${taskId}/accept`, { helper_id: authStore.user?.id })
    await fetchTasks()
  } catch { } finally { acceptingId.value = null }
}

// ── 完成任务 ──────────────────────────────────────────────
const completingId = ref<number | null>(null)

const completeTask = async (taskId: number) => {
  completingId.value = taskId
  try {
    await axios.post(`/api/mutual-aid/tasks/${taskId}/complete`)
    await fetchMine()
  } catch { } finally { completingId.value = null }
}

// ── 举报 ──────────────────────────────────────────────────
const reportTarget = ref<number | null>(null)
const reportReason = ref('')
const isReporting = ref(false)
const reportSuccess = ref(false)

const openReport = (taskId: number) => {
  reportTarget.value = taskId
  reportReason.value = ''
  reportSuccess.value = false
}

const submitReport = async () => {
  if (!reportTarget.value || !reportReason.value.trim()) return
  isReporting.value = true
  try {
    await axios.post(`/api/mutual-aid/tasks/${reportTarget.value}/report`, {
      reporter_id: authStore.user?.id,
      reason: reportReason.value
    })
    reportSuccess.value = true
    setTimeout(() => { reportTarget.value = null }, 1500)
  } catch { } finally { isReporting.value = false }
}

// ── AI 匹配 ───────────────────────────────────────────────
const matchQuery    = ref('')
const isMatching    = ref(false)
const matchThoughts = ref<string[]>([])
const matchProgress = ref(0)
const matchResult   = ref('')

const runAIMatch = async () => {
  if (!matchQuery.value.trim()) return
  isMatching.value = true
  matchResult.value = ''
  matchThoughts.value = ['[TaskAnalyzer] 正在解析互助需求...']
  matchProgress.value = 20
  setTimeout(() => { matchThoughts.value.push('[TaskAnalyzer] 需求结构化完成，识别任务类型与时间要求...'); matchProgress.value = 50 }, 800)
  setTimeout(() => { matchThoughts.value.push('[HelperMatcher] 正在检索开放任务，计算匹配度...'); matchProgress.value = 75 }, 1800)
  try {
    const res = await axios.post('/api/mutual-aid/match', { query: matchQuery.value, user_id: authStore.user?.id })
    matchProgress.value = 100
    matchResult.value = res.data.reply
    matchThoughts.value.push('[HelperMatcher] 匹配完成，推荐方案已生成。')
  } catch { matchResult.value = 'AI 匹配服务暂时无法响应，请稍后重试。' }
  finally { isMatching.value = false }
}

// ── 样式辅助 ──────────────────────────────────────────────
const typeColor: Record<string, string> = {
  '上门喂养': 'bg-orange-500/20 text-orange-400',
  '上门铲屎': 'bg-yellow-500/20 text-yellow-400',
  '代遛狗':   'bg-blue-500/20 text-blue-400',
  '宠物陪伴': 'bg-pink-500/20 text-pink-400',
  '其他互助': 'bg-gray-500/20 text-gray-400',
}
const statusLabel: Record<string, { text: string; cls: string }> = {
  open:      { text: '待接单', cls: 'bg-green-500/20 text-green-400' },
  accepted:  { text: '已接单', cls: 'bg-blue-500/20 text-blue-400' },
  completed: { text: '已完成', cls: 'bg-gray-500/20 text-gray-400' },
  cancelled: { text: '已下架', cls: 'bg-red-500/20 text-red-400' },
}

onMounted(fetchTasks)
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-10 px-4">

    <!-- 顶部标题 -->
    <div class="text-center space-y-4">
      <div class="inline-flex items-center gap-2 px-4 py-2 bg-orange-500/10 border border-orange-500/20 rounded-full text-orange-500 text-xs font-bold uppercase tracking-[0.2em]">
        <BrainCircuit :size="14" /> 多智能体协同系统
      </div>
      <h2 class="text-5xl font-black text-white drop-shadow-2xl italic">宠物互助平台</h2>
      <p class="text-gray-400 max-w-2xl mx-auto text-lg font-medium">发布上门喂养、代遛等互助需求，或接单帮助其他宠主，AI 智能为你匹配最合适的方案</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <!-- 左侧 -->
      <div class="lg:col-span-6 space-y-6">

        <!-- Tab 切换 -->
        <div class="flex gap-2 p-1 bg-white/5 rounded-2xl border border-white/10">
          <button v-for="tab in [
            { key: 'list',    label: '互助大厅',  icon: ListChecks },
            { key: 'publish', label: '发布需求',  icon: PlusCircle },
            { key: 'mine',    label: '我的互助',  icon: ClipboardList },
          ]" :key="tab.key"
            @click="switchTab(tab.key as any)"
            :class="['flex-1 py-3 rounded-xl font-bold text-sm flex items-center justify-center gap-1.5 transition-all',
              activeTab === tab.key ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/30' : 'text-gray-400 hover:text-white']"
          >
            <component :is="tab.icon" :size="15" />{{ tab.label }}
          </button>
        </div>

        <!-- ── 互助大厅 ── -->
        <div v-if="activeTab === 'list'" class="space-y-4">
          <div v-if="isLoadingTasks" class="flex items-center justify-center py-20 text-gray-500">
            <Loader2 class="animate-spin mr-2" :size="20" /> 加载中...
          </div>
          <div v-else-if="tasks.length === 0" class="text-center py-20 text-gray-600">
            <Handshake :size="48" class="mx-auto mb-4 opacity-20" />
            <p class="font-bold">暂无互助任务</p>
            <p class="text-sm mt-1">成为第一个发布互助的人吧</p>
          </div>
          <BaseCard v-for="task in tasks" :key="task.id" class="hover:border-orange-500/30 transition-all">
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 space-y-2 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span :class="['text-xs font-bold px-3 py-1 rounded-full', typeColor[task.task_type] || 'bg-gray-500/20 text-gray-400']">{{ task.task_type }}</span>
                  <span class="text-xs font-bold px-3 py-1 rounded-full bg-green-500/20 text-green-400">待接单</span>
                </div>
                <p class="font-bold text-white text-lg">
                  <Cat :size="16" class="inline mr-1 text-orange-400" />{{ task.pet_name }}（{{ task.pet_species }}）
                </p>
                <p class="text-gray-400 text-sm flex items-center gap-1"><MapPin :size="13" class="text-orange-400 shrink-0" />{{ task.location }}</p>
                <p class="text-gray-400 text-sm flex items-center gap-1"><Clock :size="13" class="text-orange-400 shrink-0" />{{ task.start_time }} ~ {{ task.end_time || '待定' }}</p>
                <p v-if="task.description" class="text-gray-500 text-sm line-clamp-2">{{ task.description }}</p>
              </div>
              <div class="shrink-0 flex flex-col gap-2">
                <!-- 接单按钮（非本人任务） -->
                <button v-if="task.user_id !== authStore.user?.id"
                  @click="acceptTask(task.id)" :disabled="acceptingId === task.id"
                  class="flex items-center gap-1 px-4 py-2 bg-orange-500 hover:bg-orange-600 disabled:bg-gray-700 text-white text-sm font-bold rounded-xl transition-all"
                >
                  <Loader2 v-if="acceptingId === task.id" class="animate-spin" :size="14" />
                  <Handshake v-else :size="14" />接单
                </button>
                <!-- 举报按钮 -->
                <button @click="openReport(task.id)"
                  class="flex items-center gap-1 px-3 py-1.5 border border-white/10 text-gray-500 hover:text-red-400 hover:border-red-500/30 text-xs font-bold rounded-xl transition-all"
                >
                  <Flag :size="12" />举报
                </button>
              </div>
            </div>
          </BaseCard>
        </div>

        <!-- ── 发布需求 ── -->
        <BaseCard v-if="activeTab === 'publish'" class="space-y-5">
          <h3 class="font-bold text-xl text-white flex items-center gap-2">
            <PlusCircle :size="20" class="text-orange-400" /> 发布互助需求
          </h3>
          <div v-if="publishSuccess" class="flex items-center gap-3 p-4 bg-green-500/10 border border-green-500/30 rounded-2xl text-green-400 font-bold">
            <CheckCircle2 :size="20" /> 发布成功！
          </div>
          <div>
            <label class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 block">互助类型</label>
            <div class="flex flex-wrap gap-2">
              <button v-for="t in taskTypes" :key="t" @click="form.task_type = t"
                :class="['px-4 py-2 rounded-xl text-sm font-bold border transition-all',
                  form.task_type === t ? 'bg-orange-500 border-orange-400 text-white' : 'border-white/10 text-gray-400 hover:border-orange-500/50 hover:text-white']">
                {{ t }}
              </button>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 block">宠物名字 *</label>
              <input v-model="form.pet_name" placeholder="例如：小橘"
                class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-orange-500 transition-all" />
            </div>
            <div>
              <label class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 block">宠物种类</label>
              <select v-model="form.pet_species"
                class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-orange-500 transition-all">
                <option value="猫">猫</option><option value="狗">狗</option><option value="其他">其他</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 block">开始时间 *</label>
              <input v-model="form.start_time" type="datetime-local"
                class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-orange-500 transition-all" />
            </div>
            <div>
              <label class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 block">结束时间</label>
              <input v-model="form.end_time" type="datetime-local"
                class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-orange-500 transition-all" />
            </div>
          </div>
          <div>
            <label class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 block">地点 *</label>
            <input v-model="form.location" placeholder="例如：上海市浦东新区 XX 小区"
              class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-orange-500 transition-all" />
          </div>
          <div>
            <label class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 block">补充说明</label>
            <textarea v-model="form.description" rows="3" placeholder="例如：猫咪每天喂两次，饮水盆需加满..."
              class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-orange-500 transition-all resize-none" />
          </div>
          <button @click="publishTask" :disabled="isPublishing || !form.pet_name || !form.location || !form.start_time"
            class="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-gray-700 text-white py-4 rounded-2xl font-black text-lg flex items-center justify-center gap-2 transition-all">
            <Loader2 v-if="isPublishing" class="animate-spin" :size="20" />
            <PlusCircle v-else :size="20" />
            {{ isPublishing ? '发布中...' : '发布互助需求' }}
          </button>
        </BaseCard>

        <!-- ── 我的互助 ── -->
        <div v-if="activeTab === 'mine'" class="space-y-6">
          <div v-if="isLoadingMine" class="flex items-center justify-center py-20 text-gray-500">
            <Loader2 class="animate-spin mr-2" :size="20" /> 加载中...
          </div>
          <template v-else>
            <!-- 我发布的 -->
            <div>
              <h4 class="text-sm font-black text-gray-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                <PlusCircle :size="14" class="text-orange-400" /> 我发布的任务（{{ myPublished.length }}）
              </h4>
              <div v-if="myPublished.length === 0" class="text-center py-8 text-gray-600 text-sm border border-dashed border-white/5 rounded-2xl">暂无发布记录</div>
              <BaseCard v-for="task in myPublished" :key="'pub-'+task.id" class="mb-3">
                <div class="flex items-start justify-between gap-3">
                  <div class="flex-1 space-y-1.5">
                    <div class="flex items-center gap-2 flex-wrap">
                      <span :class="['text-xs font-bold px-2 py-0.5 rounded-full', typeColor[task.task_type] || 'bg-gray-500/20 text-gray-400']">{{ task.task_type }}</span>
                      <span :class="['text-xs font-bold px-2 py-0.5 rounded-full', statusLabel[task.status]?.cls || 'bg-gray-500/20 text-gray-400']">{{ statusLabel[task.status]?.text || task.status }}</span>
                    </div>
                    <p class="font-bold text-white">{{ task.pet_name }}（{{ task.pet_species }}）</p>
                    <p class="text-gray-400 text-xs flex items-center gap-1"><MapPin :size="11" class="text-orange-400" />{{ task.location }}</p>
                    <p class="text-gray-400 text-xs flex items-center gap-1"><Clock :size="11" class="text-orange-400" />{{ task.start_time }}</p>
                    <!-- 接单人信息 -->
                    <div v-if="task.helper_name" class="flex items-center gap-2 mt-2 p-2 bg-blue-500/10 border border-blue-500/20 rounded-xl text-xs text-blue-300">
                      <Handshake :size="13" />
                      接单人：<span class="font-bold">{{ task.helper_name }}</span>
                    </div>
                  </div>
                  <!-- 确认完成按钮 -->
                  <button v-if="task.status === 'accepted'"
                    @click="completeTask(task.id)" :disabled="completingId === task.id"
                    class="shrink-0 flex items-center gap-1 px-3 py-2 bg-green-500 hover:bg-green-600 disabled:bg-gray-700 text-white text-xs font-bold rounded-xl transition-all"
                  >
                    <Loader2 v-if="completingId === task.id" class="animate-spin" :size="12" />
                    <CheckCircle2 v-else :size="12" />确认完成
                  </button>
                  <div v-else-if="task.status === 'completed'" class="shrink-0 flex items-center gap-1 px-3 py-2 bg-gray-700 text-gray-400 text-xs font-bold rounded-xl">
                    <CheckCircle2 :size="12" />已完成
                  </div>
                </div>
              </BaseCard>
            </div>

            <!-- 我接的单 -->
            <div>
              <h4 class="text-sm font-black text-gray-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                <Handshake :size="14" class="text-orange-400" /> 我接的单（{{ myAccepted.length }}）
              </h4>
              <div v-if="myAccepted.length === 0" class="text-center py-8 text-gray-600 text-sm border border-dashed border-white/5 rounded-2xl">暂无接单记录</div>
              <BaseCard v-for="task in myAccepted" :key="'acc-'+task.id" class="mb-3">
                <div class="flex items-start justify-between gap-3">
                  <div class="flex-1 space-y-1.5">
                    <div class="flex items-center gap-2 flex-wrap">
                      <span :class="['text-xs font-bold px-2 py-0.5 rounded-full', typeColor[task.task_type] || 'bg-gray-500/20 text-gray-400']">{{ task.task_type }}</span>
                      <span :class="['text-xs font-bold px-2 py-0.5 rounded-full', statusLabel[task.status]?.cls || 'bg-gray-500/20 text-gray-400']">{{ statusLabel[task.status]?.text || task.status }}</span>
                    </div>
                    <p class="font-bold text-white">{{ task.pet_name }}（{{ task.pet_species }}）</p>
                    <p class="text-gray-400 text-xs flex items-center gap-1"><MapPin :size="11" class="text-orange-400" />{{ task.location }}</p>
                    <p class="text-gray-400 text-xs flex items-center gap-1"><Clock :size="11" class="text-orange-400" />{{ task.start_time }}</p>
                    <p v-if="task.description" class="text-gray-500 text-xs line-clamp-2">{{ task.description }}</p>
                  </div>
                  <!-- 完成按钮 -->
                  <button v-if="task.status === 'accepted'"
                    @click="completeTask(task.id)" :disabled="completingId === task.id"
                    class="shrink-0 flex items-center gap-1 px-3 py-2 bg-green-500 hover:bg-green-600 disabled:bg-gray-700 text-white text-xs font-bold rounded-xl transition-all"
                  >
                    <Loader2 v-if="completingId === task.id" class="animate-spin" :size="12" />
                    <CheckCircle2 v-else :size="12" />标记完成
                  </button>
                  <div v-else-if="task.status === 'completed'" class="shrink-0 flex items-center gap-1 px-3 py-2 bg-gray-700 text-gray-400 text-xs font-bold rounded-xl">
                    <CheckCircle2 :size="12" />已完成
                  </div>
                </div>
              </BaseCard>
            </div>
          </template>
        </div>
      </div>

      <!-- 右侧：AI 匹配 -->
      <div class="lg:col-span-6 space-y-6">
        <BaseCard class="space-y-5">
          <h3 class="font-bold text-xl text-white flex items-center gap-3">
            <div class="p-2 bg-orange-500/20 text-orange-400 rounded-xl"><BrainCircuit :size="20" /></div>
            AI 智能匹配
          </h3>
          <p class="text-gray-400 text-sm">描述你的互助需求，AI 多智能体将分析需求并推荐最合适的互助方案。</p>
          <textarea v-model="matchQuery" :disabled="isMatching" rows="4"
            placeholder="例如：我下周三到周五出差，需要有人帮我喂猫，猫咪在上海浦东，两岁英短，比较认生..."
            class="w-full bg-white/5 border border-white/10 rounded-2xl px-5 py-4 text-white text-sm focus:outline-none focus:border-orange-500 transition-all resize-none placeholder:text-gray-600" />
          <button @click="runAIMatch" :disabled="isMatching || !matchQuery.trim()"
            class="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-gray-700 text-white py-4 rounded-2xl font-black text-lg flex items-center justify-center gap-2 transition-all active:scale-95">
            <Loader2 v-if="isMatching" class="animate-spin" :size="20" />
            <Star v-else :size="20" />
            {{ isMatching ? 'AI 匹配中...' : '智能匹配' }}
          </button>
        </BaseCard>

        <!-- 推理过程 -->
        <BaseCard v-if="isMatching || matchThoughts.length > 0" class="border-orange-500/20 bg-black/20">
          <div class="flex items-center justify-between mb-4">
            <h4 class="text-xs font-black text-orange-500 uppercase tracking-widest flex items-center gap-2">
              <BrainCircuit :size="14" /> 智能体推理过程
            </h4>
            <span class="text-[10px] font-mono text-gray-500">{{ matchProgress }}%</span>
          </div>
          <div class="h-1.5 w-full bg-white/5 rounded-full overflow-hidden mb-6">
            <div class="h-full bg-orange-500 transition-all duration-1000" :style="{ width: matchProgress + '%' }"></div>
          </div>
          <div class="space-y-3">
            <div v-for="(thought, i) in matchThoughts" :key="i" class="flex items-start gap-3 text-[13px] font-mono text-gray-400">
              <CheckCircle2 v-if="i < matchThoughts.length - 1 || matchProgress === 100" class="text-green-500 mt-0.5 shrink-0" :size="15" />
              <Loader2 v-else class="text-orange-500 animate-spin mt-0.5 shrink-0" :size="15" />
              {{ thought }}
            </div>
          </div>
        </BaseCard>

        <!-- 匹配结果 -->
        <transition name="fade-slide">
          <BaseCard v-if="matchResult" class="bg-white text-gray-900 border-none shadow-[0_50px_100px_rgba(0,0,0,0.3)]">
            <div class="flex items-center gap-4 mb-6 border-b border-gray-100 pb-5">
              <div class="p-3 bg-orange-500 text-white rounded-2xl shadow-lg shadow-orange-500/30">
                <Handshake :size="24" />
              </div>
              <div>
                <h3 class="font-black text-xl uppercase tracking-tighter">AI 匹配推荐报告</h3>
                <p class="text-xs text-gray-400 font-bold uppercase">TaskAnalyzer + HelperMatcher 协同生成</p>
              </div>
            </div>
            <div class="text-base leading-loose text-gray-700 whitespace-pre-wrap font-medium">{{ matchResult }}</div>
          </BaseCard>
        </transition>

        <div v-if="!isMatching && matchThoughts.length === 0 && !matchResult"
          class="flex flex-col items-center justify-center p-16 border-4 border-dashed border-white/5 rounded-[3rem] text-gray-700 text-center space-y-4">
          <Handshake :size="64" class="opacity-10" />
          <div class="space-y-1">
            <p class="text-xl font-black text-white/20">等待匹配需求</p>
            <p class="text-sm max-w-xs mx-auto">在上方输入你的互助需求，AI 专家团将为你分析并推荐</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 举报弹窗 -->
    <Teleport to="body">
      <transition name="fade-slide">
        <div v-if="reportTarget !== null"
          class="fixed inset-0 z-[100] flex items-center justify-center px-4 bg-black/70 backdrop-blur-sm"
          @click.self="reportTarget = null">
          <BaseCard class="w-full max-w-md space-y-5 shadow-2xl">
            <div class="flex items-center justify-between">
              <h3 class="font-black text-white flex items-center gap-2">
                <AlertTriangle :size="18" class="text-red-400" /> 举报任务
              </h3>
              <button @click="reportTarget = null" class="text-gray-500 hover:text-white transition-colors"><X :size="18" /></button>
            </div>
            <div v-if="reportSuccess" class="flex items-center gap-3 p-4 bg-green-500/10 border border-green-500/30 rounded-2xl text-green-400 font-bold text-sm">
              <CheckCircle2 :size="18" /> 举报已提交，管理员将在 24 小时内处理
            </div>
            <template v-else>
              <div>
                <label class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 block">举报原因 *</label>
                <textarea v-model="reportReason" rows="4"
                  placeholder="请描述违规内容，例如：虚假信息、诈骗、违禁物品代运..."
                  class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-red-500 transition-all resize-none" />
              </div>
              <button @click="submitReport" :disabled="isReporting || !reportReason.trim()"
                class="w-full bg-red-500 hover:bg-red-600 disabled:bg-gray-700 text-white py-3 rounded-2xl font-black flex items-center justify-center gap-2 transition-all">
                <Loader2 v-if="isReporting" class="animate-spin" :size="18" />
                <Flag v-else :size="18" />
                {{ isReporting ? '提交中...' : '提交举报' }}
              </button>
            </template>
          </BaseCard>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<style scoped>
.fade-slide-enter-active { transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.fade-slide-enter-from { opacity: 0; transform: translateY(20px); }
.fade-slide-leave-active { transition: all 0.2s ease; }
.fade-slide-leave-to { opacity: 0; }
</style>
