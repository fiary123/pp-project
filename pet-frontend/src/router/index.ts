import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/authStore'
import HomeView from '../views/HomeView.vue'
import MutualAidView from '../views/MutualAidView.vue'
import WikiView from '../views/WikiView.vue'
import AdoptView from '../views/AdoptView.vue'
import CommunityView from '../views/CommunityView.vue'
import ChatView from '../views/ChatView.vue'
import DashboardView from '../views/DashboardView.vue'
import LoginView from '../views/LoginView.vue'
import ProfileView from '../views/ProfileView.vue'
import NutritionView from '../views/NutritionView.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginView },
  { path: '/profile', name: 'profile', component: ProfileView, meta: { requiresAuth: true } },
  { path: '/', name: 'home', component: HomeView },
  { path: '/mutual-aid', name: 'mutualAid', component: MutualAidView },
  { path: '/wiki', name: 'wiki', component: WikiView },
  { path: '/nutrition', name: 'nutrition', component: NutritionView },
  { path: '/adopt', name: 'adopt', component: AdoptView },
  { path: '/community', name: 'community', component: CommunityView },
  { path: '/chat', name: 'chat', component: ChatView, meta: { requiresAuth: true } },
  { 
    path: '/dashboard', 
    name: 'dashboard', 
    component: DashboardView,
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 导航守卫 (权限控制)
router.beforeEach((to, _from) => {
  const authStore = useAuthStore()
  const hasSession = authStore.ensureValidSession()

  // 1. 如果访问需要登录的页面
  if (to.meta.requiresAuth && !hasSession) {
    return '/login'
  }

  // 2. 如果访问需要管理员权限的页面
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    alert('权限不足：该页面仅限系统管理员访问')
    return '/'
  }
})

export default router
