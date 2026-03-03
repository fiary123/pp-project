import { defineStore } from 'pinia'

/**
 * 身份认证存储 (Pinia)
 * 负责管理用户登录状态、角色权限
 * 这是实现 RBAC (基于角色的访问控制) 的前端核心
 */
export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: JSON.parse(localStorage.getItem('user') || 'null') as any,
    isLoggedIn: !!localStorage.getItem('user'),
  }),

  getters: {
    // 判断是否为管理员
    isAdmin: (state) => ['root', 'org_admin'].includes(state.user?.role),
    // 获取当前角色名（中文显示）
    roleName: (state) => {
      const roles: Record<string, string> = {
        'individual': '爱宠人士',
        'org_admin': '救助站管理员',
        'root': '系统超级管理员'
      }
      return roles[state.user?.role] || '游客'
    }
  },

  actions: {
    /**
     * 设置登录状态
     */
    login(userData: any) {
      this.user = userData
      this.isLoggedIn = true
      localStorage.setItem('user', JSON.stringify(userData))
    },

    /**
     * 退出登录
     */
    logout() {
      this.user = null
      this.isLoggedIn = false
      localStorage.removeItem('user')
    }
  }
})
