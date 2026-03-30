import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './store/authStore'
import './style.css' // 确保你已经安装了 tailwind 并配置了基础 css

const app = createApp(App)
const pinia = createPinia()
const authStore = useAuthStore(pinia)

app.use(pinia)
authStore.hydrate()
app.use(router)

app.mount('#app')
