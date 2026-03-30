import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const AUTH_ERROR_DETAILS = ['登录已过期或无效，请重新登录', 'Token 格式错误', '用户不存在']
const PROTECTED_ROUTE_PREFIXES = ['/profile', '/chat', '/dashboard']
let isHandlingAuthFailure = false

/**
 * 统一 Axios 实例
 * - baseURL 从环境变量读取，开发/生产自动切换
 * - 请求拦截器：自动注入 JWT Bearer Token
 * - 响应拦截器：401 时自动跳转登录页
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 120000,
})

api.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  const hadToken = !!authStore.token
  const hasValidSession = authStore.ensureValidSession()
  const token = hasValidSession ? authStore.token : null

  if (!hasValidSession && hadToken) {
    const currentPath = window.location.pathname
    const isProtectedRoute = PROTECTED_ROUTE_PREFIXES.some((prefix) => currentPath.startsWith(prefix))
    if (isProtectedRoute && !isHandlingAuthFailure) {
      isHandlingAuthFailure = true
      window.location.href = '/login'
      window.setTimeout(() => {
        isHandlingAuthFailure = false
      }, 0)
    }
  }

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const authStore = useAuthStore()
    const detail = error.response?.data?.detail as string | undefined
    const graceful401 = error.config?.headers?.['X-Graceful-401'] === '1'
    const shouldForceLogout =
      error.response?.status === 401 &&
      !!authStore.token &&
      !graceful401 &&
      typeof detail === 'string' &&
      AUTH_ERROR_DETAILS.includes(detail)

    if (shouldForceLogout && !isHandlingAuthFailure) {
      isHandlingAuthFailure = true
      authStore.logout()
      const currentPath = window.location.pathname
      const isProtectedRoute = PROTECTED_ROUTE_PREFIXES.some((prefix) => currentPath.startsWith(prefix))
      if (isProtectedRoute) {
        window.location.href = '/login'
      }
      window.setTimeout(() => {
        isHandlingAuthFailure = false
      }, 0)
    }
    return Promise.reject(error)
  }
)

export default api
