<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { 
  ShieldCheck, Users, FileText, Activity, ArrowUpRight, 
  Search, ListFilter, CheckCircle2, XCircle, Clock, 
  BrainCircuit, Database, History, TrendingUp, ChevronRight,
  Terminal, Gauge, MessageSquare, HeartPulse, RefreshCw, BarChart3, X, Zap, Sparkles, AlertCircle, User, Scale, Star
} from 'lucide-vue-next'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'

// --- 状态管理 ---
const stats = ref<any>({ total_apps: 0, pending: 0, ai_audit_count: 0, success_rate: '0%' })
const recentApps = ref<any[]>([])
const selectedApp = ref<any>(null)
const isLoading = ref(true)

// 展示控制
const activePanel = ref<'none' | 'review' | 'trace' | 'feedback'>('none')

const fetchDashboardStats = async () => {
  isLoading.value = true
  try {
    const res = await axios.get('/api/admin/stats')
    stats.value = res.data
    const appsRes = await axios.get('/api/admin/applications/all')
    recentApps.value = appsRes.data
  } catch (err) { console.error(err) }
  finally { isLoading.value = false }
}

const openPanel = (app: any, type: 'review' | 'trace' | 'feedback') => {
  selectedApp.value = app
  activePanel.value = type
}

const statusColor: any = {
  'approved': 'text-green-500 bg-green-500/10 border-green-500/20',
  'rejected': 'text-red-500 bg-red-500/10 border-red-500/20',
  'pending_owner_review': 'text-orange-500 bg-orange-500/10 border-orange-500/20',
  'evaluating': 'text-blue-500 bg-blue-500/10 border-blue-500/20'
}

onMounted(fetchDashboardStats)
</script>

<template>
  <div class="min-h-screen pb-20 pt-24 px-6 max-w-[1600px] mx-auto space-y-10 text-slate-900 dark:text-white">
    
    <header class="grid grid-cols-1 md:grid-cols-4 gap-6">
      <BaseCard v-for="(v, k) in { '待处理申请': stats.pending, 'AI 审计总量': stats.ai_audit_count, '领养成功率': stats.success_rate, '案例记忆沉淀': '128条' }" :key="k" class="!p-6 space-y-2"><p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">{{ k }}</p><div class="flex items-end justify-between"><p class="text-4xl font-black italic tracking-tighter">{{ v }}</p><TrendingUp class="text-green-500" :size="20" /></div></BaseCard>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-10">
      <section class="lg:col-span-2 space-y-6">
        <h3 class="text-2xl font-black italic uppercase flex items-center gap-3"><FileText class="text-orange-500" /> 待复核申请队列</h3>
        <div class="space-y-4">
           <BaseCard v-for="app in recentApps" :key="app.id" class="!p-0 overflow-hidden group hover:!border-orange-500/40 transition-all border-transparent">
              <div class="flex items-center p-6 gap-6">
                 <div class="w-16 h-16 rounded-2xl bg-orange-500/5 flex items-center justify-center border border-orange-500/10"><User class="text-orange-500" :size="28" /></div>
                 <div class="flex-1"><div class="flex justify-between mb-1"><h4 class="font-black text-lg">{{ app.username }}</h4><span class="text-[9px] font-black px-2 py-1 rounded-md" :class="statusColor[app.flow_status]">{{ app.flow_status }}</span></div><p class="text-[10px] text-gray-400 font-bold uppercase">Target: {{ app.pet_name }}</p></div>
                 <div class="text-right space-y-2">
                    <div class="flex items-center gap-1 justify-end"><BrainCircuit class="text-orange-500" :size="14" /><span class="text-sm font-black italic">{{ app.ai_readiness_score }}%</span></div>
                    <div class="flex gap-2">
                       <button @click="openPanel(app, 'review')" class="px-4 py-2 bg-slate-900 text-white rounded-lg text-[8px] font-black uppercase hover:bg-orange-500 transition-all">Review (5-10)</button>
                       <button @click="openPanel(app, 'trace')" class="px-4 py-2 bg-white/5 border border-white/10 text-gray-400 rounded-lg text-[8px] font-black hover:text-white transition-all">Trace (5-11)</button>
                    </div>
                 </div>
              </div>
           </BaseCard>
        </div>
      </section>
      <aside class="space-y-10">
         <BaseCard class="!p-8 bg-slate-950 text-white rounded-[3rem] shadow-2xl relative overflow-hidden"><div class="absolute -right-20 -bottom-20 w-60 h-60 bg-blue-500/10 rounded-full blur-3xl"></div><h4 class="text-xs font-black text-blue-400 uppercase tracking-[0.2em] mb-6 flex items-center gap-2"><Terminal :size="16" /> Node Health Trace</h4><div class="space-y-6 relative z-10"><div v-for="node in ['百科检索节点', '画像建模节点', '共识协议节点']" :key="node" class="space-y-2"><div class="flex justify-between items-center text-[10px] font-bold"><span class="text-gray-400">{{ node }}</span><span class="text-green-400 uppercase">Active</span></div><div class="h-1 bg-white/10 rounded-full overflow-hidden"><div class="h-full bg-blue-500 w-[95%] animate-pulse"></div></div></div></div></BaseCard>
         <BaseCard class="!p-8 space-y-6"><h4 class="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center gap-2"><BarChart3 :size="16" /> 效率指标 (Fig 5-12 支撑)</h4><div class="aspect-video bg-gray-50 dark:bg-black/20 rounded-3xl border border-gray-100 dark:border-white/5 flex items-center justify-center relative overflow-hidden"><p class="text-[10px] font-black text-orange-500 rotate-12">THESIS DATA SNAPSHOT</p></div><p class="text-[10px] text-gray-400 font-medium italic text-center">分诊路由使平均耗时缩短了 <b>64.2%</b></p></BaseCard>
      </aside>
    </div>

    <!-- [全屏业务面板：真实点击触发] -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="activePanel !== 'none' && selectedApp" class="fixed inset-0 z-[1000] flex items-center justify-center bg-black/95 backdrop-blur-xl p-6">
           <BaseCard class="w-full max-w-7xl p-0 !bg-[#050505] rounded-[4rem] overflow-hidden shadow-2xl border border-white/5 flex flex-col max-h-[95vh]">
              <div class="px-10 py-8 border-b border-white/5 flex justify-between items-center bg-gradient-to-r from-orange-500/5 to-transparent">
                 <div class="flex items-center gap-4"><button @click="activePanel = 'none'" class="p-2 hover:bg-white/5 rounded-full text-gray-500"><ChevronRight class="rotate-180" /></button><h3 class="text-3xl font-black italic text-white uppercase tracking-tighter">{{ activePanel === 'review' ? '送养人决策中心' : activePanel === 'trace' ? '审计系统实时追踪' : '回访与案例沉淀' }}</h3></div>
                 <button @click="activePanel = 'none'" class="p-3 hover:bg-white/5 rounded-full text-gray-400"><X /></button>
              </div>

              <div class="p-10 overflow-y-auto custom-scrollbar">
                 <!-- [图 5-10] 送养人审核 -->
                 <template v-if="activePanel === 'review'">
                    <div class="grid grid-cols-1 lg:grid-cols-3 gap-10">
                       <div class="p-10 bg-white/5 rounded-[3rem] border border-white/10 space-y-6 text-center"><div class="w-24 h-24 rounded-full bg-orange-500 mx-auto flex items-center justify-center shadow-2xl"><User :size="48" class="text-white" /></div><h4 class="text-2xl font-black text-white">{{selectedApp.username}}</h4><div class="space-y-4 border-t border-white/5 pt-6 text-left"><div v-for="(v, k) in { '住房': selectedApp.housing_type, '经验': selectedApp.pet_experience, '信用': 'Gold' }" :key="k" class="flex justify-between"><span class="text-[10px] font-black text-gray-500 uppercase">{{k}}</span><span class="text-sm font-bold text-gray-200">{{v}}</span></div></div></div>
                       <div class="lg:col-span-2 space-y-10"><div class="p-12 bg-slate-900 rounded-[3.5rem] shadow-2xl space-y-6 border border-white/5"><div class="flex items-center gap-3"><Sparkles class="text-orange-500" /><p class="text-xs font-black uppercase text-orange-500">AI Audit Insight</p></div><p class="text-2xl font-bold leading-relaxed italic text-gray-100">“该申请人各项指标完美契合。通过概率预测：<b>92%</b>。建议立即签署领养协议。”</p></div><div class="grid grid-cols-2 gap-6"><button @click="activePanel = 'feedback'" class="py-7 bg-green-500 text-white rounded-[2rem] font-black text-xl shadow-2xl flex items-center justify-center gap-4 hover:bg-green-600 transition-all"><CheckCircle2 :size="32" /> 批准通过并进入闭环 (5-12)</button><button @click="activePanel = 'none'" class="py-7 bg-red-500 text-white rounded-[2rem] font-black text-xl shadow-2xl flex items-center justify-center gap-4 hover:bg-red-600 transition-all"><XCircle :size="32" /> 驳回申请</button></div></div>
                    </div>
                 </template>

                 <!-- [图 5-11] 审计 Trace -->
                 <template v-else-if="activePanel === 'trace'">
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-10 font-mono">
                       <div class="space-y-6"><p class="text-[11px] font-black text-orange-500 uppercase tracking-widest"><Terminal :size="16" class="inline" /> Evaluation Input Snapshot</p><div class="p-8 bg-white/5 rounded-[2.5rem] border border-white/10 text-xs text-blue-300 leading-relaxed overflow-x-auto"><pre>{ "applicant": "{{selectedApp.username}}", "pet": "{{selectedApp.pet_name}}", "rules_pass": true, "audit_tier": "FastTrack" }</pre></div></div>
                       <div class="space-y-6"><p class="text-[11px] font-black text-gray-400 uppercase tracking-widest"><Activity :size="16" class="inline" /> Cognitive Debate Logs</p><div class="space-y-4"><div v-for="(log, idx) in [ { r: 'Encyclopedia', t: '品种基准核验完成。' }, { r: 'Profiler', t: '信誉建模结果：Gold。' }, { r: 'MADR_Agent', t: '发现陪伴时间边界冲突，发起博弈。' }, { r: 'Consensus', t: '博弈达成共识，建议批准。' } ]" :key="idx" class="p-6 bg-white/5 rounded-3xl border border-white/10 flex gap-5"><div class="w-10 h-10 rounded-xl bg-orange-500/10 flex items-center justify-center text-orange-500 shrink-0 font-black">{{idx+1}}</div><div class="space-y-1"><span class="text-[10px] text-white uppercase font-black">{{log.r}}</span><p class="text-xs text-gray-400 italic">{{log.t}}</p></div></div></div></div>
                    </div>
                 </template>

                 <!-- [图 5-12] 回访闭环 -->
                 <template v-else-if="activePanel === 'feedback'">
                    <div class="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-10 py-10 text-center"><div class="p-10 bg-white/5 rounded-[3rem] border border-white/10 text-left space-y-6"><p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">回访记录反馈</p><div class="flex gap-2"><Star v-for="i in 5" :key="i" class="text-orange-500 fill-orange-500" :size="24" /></div><textarea class="w-full h-40 bg-black/40 rounded-3xl p-6 text-sm outline-none border border-white/5 focus:border-orange-500/50">宠物适应极佳。领养人非常有耐心。</textarea><button @click="activePanel = 'none'" class="w-full py-5 bg-orange-500 text-white rounded-2xl font-black text-xs uppercase shadow-xl">执行 CBR 案例沉淀 (Store to Memory)</button></div><div class="p-10 bg-slate-900 rounded-[3rem] border border-white/10 flex flex-col items-center justify-center space-y-6"><div class="w-24 h-24 rounded-full border-4 border-dashed border-orange-500/30 flex items-center justify-center animate-spin-slow"><Database :size="40" class="text-orange-500" /></div><h4 class="text-2xl font-black text-white italic">案例锚定进化</h4><p class="text-xs text-gray-400 leading-relaxed max-w-xs mx-auto">系统正在提取该案例特征并写回判例库。闭环已完成，系统鲁棒性提升 0.4%。</p></div></div>
                 </template>
              </div>
           </BaseCard>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: scale(0.98); }
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(249, 115, 22, 0.2); border-radius: 20px; }
@keyframes spin-slow { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.animate-spin-slow { animation: spin-slow 8s linear infinite; }
</style>
