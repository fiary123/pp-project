<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Mail, Lock, User, Shield, ArrowRight, Loader2 } from 'lucide-vue-next'
import { useAuthStore } from '../store/authStore'
import axios from 'axios'
import BaseCard from '../components/BaseCard.vue'

const router = useRouter()
const authStore = useAuthStore()

const isLogin = ref(true)
const isLoading = ref(false)
const errorMsg = ref('')

const form = ref({
  username: '',
  email: '',
  password: '',
  role: 'individual'
})

const handleAuth = async () => {
  isLoading.value = true
  errorMsg.value = ''
  
  try {
    if (isLogin.value) {
      // 登录逻辑
      const res = await axios.post('http://127.0.0.1:8000/api/login', {
        email: form.value.email,
        password: form.value.password
      })
      authStore.login(res.data.user)
      router.push('/')
    } else {
      // 注册逻辑
      await axios.post('http://127.0.0.1:8000/api/register', form.value)
      isLogin.value = true
      alert('注册成功，请登录！')
    }
  } catch (err: any) {
    errorMsg.value = err.response?.data?.detail || '认证失败，请检查网络'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-md px-4">
    <div class="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 overflow-hidden rounded-[3rem] border border-white/10 shadow-2xl">
      
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
      <div class="bg-[#121212] p-8 md:p-12 flex flex-col justify-center">
        <div class="mb-10">
          <h3 class="text-3xl font-black text-white">{{ isLogin ? '欢迎回来' : '开启旅程' }}</h3>
          <p class="text-gray-500 mt-2">{{ isLogin ? '请登录您的账号以继续' : '只需几秒钟即可完成注册' }}</p>
        </div>

        <div class="space-y-4">
          <!-- 角色选择 (仅注册) -->
          <div v-if="!isLogin" class="grid grid-cols-2 gap-3 mb-6">
            <button @click="form.role = 'individual'" :class="form.role === 'individual' ? 'bg-orange-500 text-white' : 'bg-white/5 text-gray-400'" class="py-2 rounded-xl text-xs font-bold transition-all border border-white/5">个人用户</button>
            <button @click="form.role = 'org_admin'" :class="form.role === 'org_admin' ? 'bg-orange-500 text-white' : 'bg-white/5 text-gray-400'" class="py-2 rounded-xl text-xs font-bold transition-all border border-white/5">救助机构</button>
          </div>

          <div v-if="!isLogin" class="relative group">
            <User class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-orange-500 transition-colors" :size="18" />
            <input v-model="form.username" type="text" placeholder="您的称呼" class="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white focus:outline-none focus:border-orange-500 transition-all" />
          </div>

          <div class="relative group">
            <Mail class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-orange-500 transition-colors" :size="18" />
            <input v-model="form.email" type="email" placeholder="电子邮箱" class="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white focus:outline-none focus:border-orange-500 transition-all" />
          </div>

          <div class="relative group">
            <Lock class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-orange-500 transition-colors" :size="18" />
            <input v-model="form.password" type="password" placeholder="安全密码" class="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white focus:outline-none focus:border-orange-500 transition-all" />
          </div>

          <div v-if="errorMsg" class="text-red-500 text-xs px-2 font-bold">{{ errorMsg }}</div>

          <button 
            @click="handleAuth"
            :disabled="isLoading"
            class="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-gray-700 text-white py-4 rounded-2xl font-black flex items-center justify-center gap-2 transition-all shadow-lg shadow-orange-500/20"
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
@reference "tailwindcss";
</style>
