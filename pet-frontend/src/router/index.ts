import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/authStore'
import HomeView from '../views/HomeView.vue'
import MutualAidView from '../views/MutualAidView.vue'
import WikiView from '../views/WikiView.vue'
import AdoptView from '../views/AdoptView.vue'
import CommunityView from '../views/CommunityView.vue'
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

router.beforeEach((to, _from) => {
  const authStore = useAuthStore()
  const hasSession = authStore.ensureValidSession()
  if (to.meta.requiresAuth && !hasSession) return '/login'
})

export default router
