<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Mail, Lock, User, ShieldCheck, Loader2, ArrowRight } from 'lucide-vue-next'
import { useAuthStore } from '../store/authStore'
import axios from '../api/index'

const router = useRouter()
const authStore = useAuthStore()

const isLogin = ref(true)
const isLoading = ref(false)
const isSendingCode = ref(false)
const countdown = ref(0)
const errorMsg = ref('')

const form = ref({
  username: '',
  email: '',
  password: '',
  code: '' 
})

// 发送验证码逻辑
const sendCode = async () => {
  if (!form.value.email) return (errorMsg.value = '请先输入邮箱')
  isSendingCode.value = true
  errorMsg.value = ''
  try {
    await axios.post('/api/send-code', { email: form.value.email })
    alert('验证码已发送，请查收邮件（或查看后端控制台）')
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || '发送失败'
  } finally {
    isSendingCode.value = false
  }
}

const handleAuth = async () => {
  isLoading.value = true
  errorMsg.value = ''
  try {
    if (isLogin.value) {
      const res = await axios.post('/api/login', {
        email: form.value.email,
        password: form.value.password
      })
      authStore.login(res.data.user, res.data.access_token)
      router.push('/')
    } else {
      if (!form.value.code) {
        errorMsg.value = '请输入验证码'
        return
      }
      await axios.post('/api/register', {
        username: form.value.username,
        email: form.value.email,
        password: form.value.password,
        code: form.value.code
      })
      alert('注册成功，请登录！')
      isLogin.value = true
    }
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || '操作失败'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-md px-4">
    <div class="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 overflow-hidden rounded-[3rem] border border-gray-200 dark:border-white/10 shadow-2xl bg-white dark:bg-[#121212]">
      
      <!-- 左侧：视觉区域 -->
      <div class="hidden md:block relative bg-orange-500 overflow-hidden">
        <img src="https://images.unsplash.com/photo-1544568100-847a948585b9?q=80&w=1000" class="h-full w-full object-cover opacity-80" />
        <div class="absolute inset-0 bg-gradient-to-t from-orange-600/80 to-transparent"></div>
        <div class="absolute bottom-12 left-12 text-white">
          <h2 class="text-4xl font-black mb-4">加入我们</h2>
          <p class="text-orange-100 font-medium">与 1,200+ 志愿者一起，为流浪动物搭建温暖的港湾。</p>
        </div>
      </div>

      <!-- 右侧：表单区域 -->
      <div class="p-8 md:p-12 flex flex-col justify-center">
        <div class="mb-10 text-center md:text-left">
          <h3 class="text-3xl font-black text-gray-900 dark:text-white">{{ isLogin ? '欢迎回来' : '开启旅程' }}</h3>
          <p class="text-gray-500 mt-2">{{ isLogin ? '请登录您的账号以继续' : '只需几秒钟即可通过邮箱验证注册' }}</p>
        </div>

        <div class="space-y-4">
          <!-- 用户名 (仅注册) -->
          <div v-if="!isLogin" class="relative group">
            <User class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-orange-500 transition-colors" :size="18" />
            <input v-model="form.username" type="text" placeholder="您的称呼" 
                   class="w-full bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl py-4 pl-12 pr-4 text-gray-900 dark:text-white outline-none focus:border-orange-500 transition-all" />
          </div>

          <!-- 邮箱 -->
          <div class="relative group">
            <Mail class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-orange-500 transition-colors" :size="18" />
            <input v-model="form.email" type="email" placeholder="电子邮箱" 
                   class="w-full bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl py-4 pl-12 pr-4 text-gray-900 dark:text-white outline-none focus:border-orange-500 transition-all" />
          </div>

          <!-- 验证码 (仅注册) -->
          <div v-if="!isLogin" class="flex gap-3 group">
            <div class="relative flex-1">
              <ShieldCheck class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-orange-500 transition-colors" :size="18" />
              <input v-model="form.code" type="text" placeholder="6位验证码" 
                     class="w-full bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl py-4 pl-12 pr-4 text-gray-900 dark:text-white outline-none focus:border-orange-500 transition-all" />
            </div>
            <button type="button" @click="sendCode" :disabled="isSendingCode || countdown > 0"
                    class="px-4 rounded-2xl bg-orange-500/10 border border-orange-500/20 text-orange-500 font-bold text-xs hover:bg-orange-500 hover:text-white transition-all disabled:opacity-50 min-w-[100px]">
              {{ countdown > 0 ? `${countdown}s` : '获取码' }}
            </button>
          </div>

          <!-- 密码 -->
          <div class="relative group">
            <Lock class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-orange-500 transition-colors" :size="18" />
            <input v-model="form.password" type="password" placeholder="安全密码" 
                   class="w-full bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl py-4 pl-12 pr-4 text-gray-900 dark:text-white outline-none focus:border-orange-500 transition-all" />
          </div>

          <div v-if="errorMsg" class="text-red-500 text-xs px-2 font-bold">{{ errorMsg }}</div>

          <button 
            @click="handleAuth"
            :disabled="isLoading"
            class="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-gray-400 text-white py-4 rounded-2xl font-black flex items-center justify-center gap-2 transition-all shadow-lg shadow-orange-500/20"
          >
            <template v-if="isLoading">
              <Loader2 class="animate-spin" :size="20" /> 正在同步...
            </template>
            <template v-else>
              {{ isLogin ? '立即登录' : '确认注册' }} <ArrowRight :size="20" />
            </template>
          </button>
        </div>

        <div class="mt-8 text-center">
          <p class="text-gray-500 text-sm">
            {{ isLogin ? '还没有账号？' : '已经有账号了？' }}
            <span @click="isLogin = !isLogin" class="text-orange-500 font-bold cursor-pointer hover:underline underline-offset-4 ml-1">
              {{ isLogin ? '点击注册' : '点击登录' }}
            </span>
          </p>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
</style>
