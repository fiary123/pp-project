<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../store/authStore'
import { User, Shield, MessageCircle, AtSign, LogOut, KeyRound } from 'lucide-vue-next'
import BaseCard from '../components/BaseCard.vue'
import axios from 'axios'

const authStore = useAuthStore()
const activeTab = ref('info')

const passForm = ref({ old: '', new: '' })
const statusMsg = ref('')

const handleUpdatePassword = async () => {
  try {
    await axios.post('http://127.0.0.1:8000/api/user/change-password', {
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

const bindSocial = async (platform: string) => {
  alert(`正在跳转至 ${platform} 授权页面... (本系统目前为演示版本)`)
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-8">
    <h2 class="text-3xl font-black text-white">个人中心 / <span class="text-orange-500">Profile</span></h2>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-8">
      <!-- 左侧菜单 -->
      <BaseCard class="md:col-span-1 !p-2 flex flex-col gap-1">
        <button @click="activeTab = 'info'" :class="activeTab === 'info' ? 'bg-orange-500 text-white shadow-lg' : 'text-gray-400 hover:bg-white/5'" class="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all">
          <User :size="18" /> 基本资料
        </button>
        <button @click="activeTab = 'security'" :class="activeTab === 'security' ? 'bg-orange-500 text-white shadow-lg' : 'text-gray-400 hover:bg-white/5'" class="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all">
          <Shield :size="18" /> 安全设置
        </button>
        <button @click="activeTab = 'social'" :class="activeTab === 'social' ? 'bg-orange-500 text-white shadow-lg' : 'text-gray-400 hover:bg-white/5'" class="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all">
          <AtSign :size="18" /> 账号绑定
        </button>
        <div class="mt-4 border-t border-white/5 pt-2">
          <button @click="authStore.logout(); $router.push('/login')" class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold text-red-400 hover:bg-red-500/10 transition-all">
            <LogOut :size="18" /> 退出登录
          </button>
        </div>
      </BaseCard>

      <!-- 右侧内容区域 -->
      <div class="md:col-span-3">
        <transition name="fade" mode="out-in">
          <!-- 1. 基本资料 -->
          <BaseCard v-if="activeTab === 'info'" key="info" class="space-y-6">
            <div class="flex items-center gap-6 mb-8">
              <div class="w-20 h-20 rounded-full bg-orange-500/20 border-2 border-orange-500 flex items-center justify-center overflow-hidden shadow-inner">
                <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Lucky" />
              </div>
              <div>
                <h3 class="text-2xl font-bold text-white">{{ authStore.user?.username }}</h3>
                <p class="text-orange-500 text-xs font-black uppercase tracking-widest mt-1">{{ authStore.roleName }}</p>
              </div>
            </div>
            
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-8">
              <div class="space-y-1 p-4 bg-white/5 rounded-2xl border border-white/5">
                <p class="text-[10px] text-gray-500 font-bold uppercase tracking-widest">账户邮箱</p>
                <p class="text-white font-medium">{{ authStore.user?.email }}</p>
              </div>
              <div class="space-y-1 p-4 bg-white/5 rounded-2xl border border-white/5">
                <p class="text-[10px] text-gray-500 font-bold uppercase tracking-widest">系统 ID</p>
                <p class="text-white font-mono">UID-{{ authStore.user?.id?.toString().padStart(6, '0') }}</p>
              </div>
            </div>
          </BaseCard>

          <!-- 2. 安全设置 -->
          <BaseCard v-else-if="activeTab === 'security'" key="security" class="space-y-6">
            <h3 class="text-xl font-bold text-white mb-4 flex items-center gap-2"><KeyRound class="text-orange-500" /> 修改登录密码</h3>
            <div class="space-y-4">
              <div class="space-y-2">
                <label class="text-xs text-gray-400 font-bold uppercase">当前旧密码</label>
                <input v-model="passForm.old" type="password" class="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white focus:border-orange-500 outline-none transition-all" />
              </div>
              <div class="space-y-2">
                <label class="text-xs text-gray-400 font-bold uppercase">设置新密码</label>
                <input v-model="passForm.new" type="password" class="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white focus:border-orange-500 outline-none transition-all" />
              </div>
              <p v-if="statusMsg" :class="statusMsg.includes('成功') ? 'text-green-400' : 'text-orange-500'" class="text-xs font-bold">{{ statusMsg }}</p>
              <button @click="handleUpdatePassword" class="bg-orange-500 px-8 py-3 rounded-xl font-bold text-white hover:bg-orange-600 transition-all shadow-lg shadow-orange-500/20">确认更新</button>
            </div>
          </BaseCard>

          <!-- 3. 账号绑定 -->
          <BaseCard v-else key="social" class="space-y-6">
            <h3 class="text-xl font-bold text-white mb-4">第三方账号绑定</h3>
            <div class="space-y-4">
              <div class="flex items-center justify-between p-5 bg-white/5 rounded-2xl border border-white/10 group hover:border-green-500/50 transition-all">
                <div class="flex items-center gap-4">
                  <div class="p-3 bg-green-500/20 text-green-500 rounded-xl"><MessageCircle :size="24" /></div>
                  <div>
                    <p class="text-white font-bold">微信 / WeChat</p>
                    <p class="text-xs text-gray-500">用于快捷登录与接收领养进度通知</p>
                  </div>
                </div>
                <button @click="bindSocial('WeChat')" class="text-xs font-bold text-orange-500 border border-orange-500/30 px-4 py-2 rounded-lg hover:bg-orange-500 hover:text-white transition-all">立即绑定</button>
              </div>

              <div class="flex items-center justify-between p-5 bg-white/5 rounded-2xl border border-white/10 group hover:border-blue-500/50 transition-all">
                <div class="flex items-center gap-4">
                  <div class="p-3 bg-blue-500/20 text-blue-500 rounded-xl"><AtSign :size="24" /></div>
                  <div>
                    <p class="text-white font-bold">QQ 账号</p>
                    <p class="text-xs text-gray-500">绑定后可使用 QQ 一键登录</p>
                  </div>
                </div>
                <button @click="bindSocial('QQ')" class="text-xs font-bold text-orange-500 border border-orange-500/30 px-4 py-2 rounded-lg hover:bg-orange-500 hover:text-white transition-all">立即绑定</button>
              </div>
            </div>
          </BaseCard>
        </transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
@reference "tailwindcss";
.fade-enter-active, .fade-leave-active { transition: all 0.3s ease; }
.fade-enter-from { opacity: 0; transform: translateY(10px); }
.fade-leave-to { opacity: 0; transform: translateY(-10px); }
</style>
