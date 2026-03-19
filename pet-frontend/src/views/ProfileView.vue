<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../store/authStore'
import {
  User, Shield, LogOut, KeyRound, FileText, ChevronRight, Loader2, Heart
} from 'lucide-vue-next'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'

const authStore = useAuthStore()
const activeTab = ref('info')

// 1. 密码修改
const passForm = ref({ old: '', new: '' })
const statusMsg = ref('')
const handleUpdatePassword = async () => {
  try {
    await axios.post('/api/user/change-password', {
      user_id: authStore.user.id,
      old_password: passForm.value.old,
      new_password: passForm.value.new
    })
    statusMsg.value = '密码更新成功！'
    passForm.value = { old: '', new: '' }
  } catch (err: any) {
    statusMsg.value = err.response?.data?.detail || '操作失败'
  }
}

// 2. 申请记录加载
const applications = ref<any[]>([])
const isLoadingApps = ref(false)

const fetchApplications = async () => {
  isLoadingApps.value = true
  try {
    const res = await axios.get(`/api/user/applications/${authStore.user?.id || 1}`)
    applications.value = res.data
  } catch (err) {
    console.error('获取记录失败')
  } finally {
    isLoadingApps.value = false
  }
}

// 切换标签时加载数据
const switchTab = (tab: string) => {
  activeTab.value = tab
  if (tab === 'records') fetchApplications()
}
</script>

<template>
  <div class="max-w-5xl mx-auto space-y-8">
    <h2 class="text-3xl font-black text-white">个人中心</h2>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-8">
      <!-- A. 左侧边栏 -->
      <BaseCard class="md:col-span-1 !p-3 flex flex-col gap-1 h-fit">
        <button @click="switchTab('info')" :class="activeTab === 'info' ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' : 'text-gray-400 hover:bg-white/5'" class="flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-bold transition-all">
          <User :size="18" /> 基本资料
        </button>
        <button @click="switchTab('records')" :class="activeTab === 'records' ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' : 'text-gray-400 hover:bg-white/5'" class="flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-bold transition-all">
          <FileText :size="18" /> 申请记录
        </button>
        <button @click="switchTab('security')" :class="activeTab === 'security' ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' : 'text-gray-400 hover:bg-white/5'" class="flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-bold transition-all">
          <Shield :size="18" /> 安全设置
        </button>
        
        <div class="mt-6 pt-4 border-t border-white/5">
          <button @click="authStore.logout(); $router.push('/login')" class="w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-bold text-red-400 hover:bg-red-500/10 transition-all">
            <LogOut :size="18" /> 退出账户
          </button>
        </div>
      </BaseCard>

      <!-- B. 右侧主内容 -->
      <div class="md:col-span-3 min-h-[600px]">
        <transition name="fade" mode="out-in">
          
          <!-- 1. 资料页 -->
          <div v-if="activeTab === 'info'" key="info" class="space-y-6">
            <BaseCard class="p-8">
              <div class="flex items-center gap-8 mb-10">
                <div class="w-24 h-24 rounded-full bg-orange-500/20 border-2 border-orange-500 overflow-hidden shadow-2xl">
                  <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Lucky" />
                </div>
                <div>
                  <h3 class="text-3xl font-black text-white">{{ authStore.user?.username }}</h3>
                  <div class="flex gap-2 mt-2">
                    <span class="px-3 py-1 bg-orange-500/10 text-orange-500 text-[10px] font-black uppercase tracking-widest rounded-full border border-orange-500/20">
                      {{ authStore.roleName }}
                    </span>
                    <span class="px-3 py-1 bg-green-500/10 text-green-500 text-[10px] font-black uppercase tracking-widest rounded-full border border-green-500/20">
                      账户正常
                    </span>
                  </div>
                </div>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div class="p-6 bg-white/5 rounded-3xl border border-white/5">
                  <p class="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-1">电子邮箱</p>
                  <p class="text-white font-medium">{{ authStore.user?.email }}</p>
                </div>
                <div class="p-6 bg-white/5 rounded-3xl border border-white/5">
                  <p class="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-1">账户唯一 ID</p>
                  <p class="text-white font-mono">UID-{{ authStore.user?.id?.toString().padStart(6, '0') }}</p>
                </div>
              </div>
            </BaseCard>
          </div>

          <!-- 2. 申请记录页 -->
          <div v-else-if="activeTab === 'records'" key="records" class="space-y-6">
            <div v-if="isLoadingApps" class="h-64 flex items-center justify-center">
              <Loader2 class="animate-spin text-orange-500" :size="48" />
            </div>
            
            <template v-else-if="applications.length > 0">
              <BaseCard v-for="app in applications" :key="app.id" class="!p-6 group hover:border-orange-500/30 transition-all cursor-pointer">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-6">
                    <div class="w-16 h-16 rounded-2xl bg-orange-500/10 flex items-center justify-center text-orange-500">
                      <Heart :size="32" />
                    </div>
                    <div>
                      <h4 class="text-xl font-bold text-white">领养申请：宠物ID-{{ app.pet_id }}</h4>
                      <p class="text-xs text-gray-500 mt-1">提交时间：{{ app.apply_date }}</p>
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="px-4 py-1.5 rounded-full bg-orange-500/10 text-orange-500 text-[10px] font-black uppercase tracking-widest border border-orange-500/20">
                      {{ app.status || 'AI 评估中' }}
                    </div>
                    <p class="text-[10px] text-gray-600 mt-2 font-bold uppercase">查看详情 <ChevronRight class="inline" :size="12"/></p>
                  </div>
                </div>
              </BaseCard>
            </template>

            <div v-else class="h-64 flex flex-col items-center justify-center border-2 border-dashed border-white/5 rounded-[3rem] text-gray-600 space-y-4">
              <FileText :size="48" class="opacity-20" />
              <p class="font-bold">暂无申请记录</p>
              <button @click="$router.push('/adopt')" class="text-xs text-orange-500 font-black hover:underline underline-offset-4 uppercase tracking-widest">前往寻找伙伴</button>
            </div>
          </div>

          <!-- 3. 安全设置页 -->
          <div v-else-if="activeTab === 'security'" key="security" class="space-y-6">
            <BaseCard class="p-10 space-y-8">
              <div class="flex items-center gap-4 border-b border-white/5 pb-6">
                <div class="p-3 bg-orange-500 rounded-2xl text-white shadow-lg"><KeyRound :size="24" /></div>
                <h3 class="text-xl font-black text-white">账户安全中心</h3>
              </div>
              <div class="space-y-6 max-w-md">
                <div class="space-y-2">
                  <label class="text-[10px] text-gray-500 font-bold uppercase tracking-widest">当前旧密码</label>
                  <input v-model="passForm.old" type="password" class="w-full bg-white/5 border border-white/10 rounded-2xl py-4 px-6 text-white focus:border-orange-500 outline-none" />
                </div>
                <div class="space-y-2">
                  <label class="text-[10px] text-gray-500 font-bold uppercase tracking-widest">设置新密码</label>
                  <input v-model="passForm.new" type="password" class="w-full bg-white/5 border border-white/10 rounded-2xl py-4 px-6 text-white focus:border-orange-500 outline-none" />
                </div>
                <p v-if="statusMsg" class="text-xs text-orange-500 font-bold italic">{{ statusMsg }}</p>
                <button @click="handleUpdatePassword" class="w-full bg-orange-500 text-white py-4 rounded-2xl font-black shadow-xl shadow-orange-500/20 hover:bg-orange-600 transition-all">
                  确认修改
                </button>
              </div>
            </BaseCard>
          </div>

        </transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* @reference "tailwindcss"; */
.fade-enter-active, .fade-leave-active { transition: all 0.3s ease; }
.fade-enter-from { opacity: 0; transform: translateY(10px); }
.fade-leave-to { opacity: 0; transform: translateY(-10px); }
</style>
