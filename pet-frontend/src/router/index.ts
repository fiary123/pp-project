import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/authStore'
import HomeView from '../views/HomeView.vue'
import TriageView from '../views/TriageView.vue'
import WikiView from '../views/WikiView.vue'
import AdoptView from '../views/AdoptView.vue'
import CommunityView from '../views/CommunityView.vue'
import ChatView from '../views/ChatView.vue'
import DashboardView from '../views/DashboardView.vue'
import LoginView from '../views/LoginView.vue'
import ProfileView from '../views/ProfileView.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginView },
  { path: '/profile', name: 'profile', component: ProfileView },
  { path: '/', name: 'home', component: HomeView },
  { path: '/triage', name: 'triage', component: TriageView },
  { path: '/wiki', name: 'wiki', component: WikiView },
  { path: '/adopt', name: 'adopt', component: AdoptView },
  { path: '/community', name: 'community', component: CommunityView },
  { path: '/chat', name: 'chat', component: ChatView },
  { 
    path: '/dashboard', 
    name: 'dashboard', 
    component: DashboardView,
    meta: { requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 导航守卫 (权限控制)
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // 1. 如果访问需要管理员权限的页面
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    alert('权限不足：该页面仅限救助站管理员访问')
    return next('/')
  }

  // 2. 如果未登录且访问的不是登录页
  if (!authStore.isLoggedIn && to.name !== 'login') {
    return next('/login')
  }

  next()
})

export default router
