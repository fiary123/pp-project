import axios from 'axios'
import { useAuthStore } from '../store/authStore'

/**
 * 统一 Axios 实例
 * - baseURL 从环境变量读取，开发/生产自动切换
 * - 请求拦截器：自动注入 JWT Bearer Token
 * - 响应拦截器：401 时自动跳转登录页
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  const token = authStore.token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
