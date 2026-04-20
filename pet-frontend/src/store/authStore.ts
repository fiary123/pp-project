import { defineStore } from 'pinia'

const parseJwtPayload = (token: string) => {
  try {
    const payload = token.split('.')[1]
    if (!payload) return null
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    const json = decodeURIComponent(
      atob(padded)
        .split('')
        .map((char) => `%${char.charCodeAt(0).toString(16).padStart(2, '0')}`)
        .join('')
    )
    return JSON.parse(json) as { exp?: number }
  } catch {
    return null
  }
}

const isTokenValid = (token: string | null) => {
  if (!token) return false
  const payload = parseJwtPayload(token)
  const exp = payload?.exp
  if (typeof exp !== 'number') return false
  return exp * 1000 > Date.now() + 5000
}

const readStoredSession = () => {
  const rawUser = localStorage.getItem('user')
  const token = localStorage.getItem('token')

  if (!rawUser || !isTokenValid(token)) {
    localStorage.removeItem('user')
    localStorage.removeItem('token')
    return { user: null, token: null, isLoggedIn: false }
  }

  return {
    user: JSON.parse(rawUser) as any,
    token,
    isLoggedIn: true,
  }
}

/**
 * 身份认证存储 (Pinia)
 * 负责管理用户登录状态、角色权限
 * 这是实现 RBAC (基于角色的访问控制) 的前端核心
 */
export const useAuthStore = defineStore('auth', {
  state: () => readStoredSession(),

  getters: {
    // 判断是否具备管理权限 (论文语义：系统审计员)
    isAdmin: (state) => state.isLoggedIn && state.user?.role === 'admin',
    // 获取当前角色名（论文视角展示）
    roleName: (state) => {
      const roles: Record<string, string> = {
        'user': '爱宠人士 / 领养申请人',
        'admin': '系统审计员 / 机构管理员',
      }
      return roles[state.user?.role] || '游客'
    }
  },

  actions: {
    /**
     * 设置登录状态
     */
    login(userData: any, accessToken: string) {
      this.user = userData
      this.token = accessToken
      this.isLoggedIn = isTokenValid(accessToken)
      localStorage.setItem('user', JSON.stringify(userData))
      localStorage.setItem('token', accessToken)
      if (!this.isLoggedIn) {
        this.logout()
      }
    },

    /**
     * 从 localStorage 恢复并校验会话
     */
    hydrate() {
      const session = readStoredSession()
      this.user = session.user
      this.token = session.token
      this.isLoggedIn = session.isLoggedIn
    },

    /**
     * 检查当前 token 是否仍然有效
     */
    ensureValidSession() {
      const valid = this.isLoggedIn && isTokenValid(this.token)
      if (!valid) {
        this.logout()
      }
      return valid
    },

    /**
     * 退出登录
     */
    logout() {
      this.user = null
      this.token = null
      this.isLoggedIn = false
      localStorage.removeItem('user')
      localStorage.removeItem('token')
    }
  }
})
