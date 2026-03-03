import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import TriageView from '../views/TriageView.vue'
import WikiView from '../views/WikiView.vue'
import AdoptView from '../views/AdoptView.vue'
import DashboardView from '../views/DashboardView.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/triage',
    name: 'triage',
    component: TriageView
  },
  {
    path: '/wiki',
    name: 'wiki',
    component: WikiView
  },
  {
    path: '/adopt',
    name: 'adopt',
    component: AdoptView
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
