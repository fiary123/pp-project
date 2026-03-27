import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ColorTheme = 'blue' | 'green' | 'pink' | 'gray' | 'orange'

export const useThemeStore = defineStore('theme', () => {
  const isDark = ref<boolean>(localStorage.getItem('isDark') === 'true')
  const colorTheme = ref<ColorTheme>((localStorage.getItem('colorTheme') as ColorTheme) || 'blue')

  const apply = () => {
    // 处理深色模式类
    if (isDark.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    
    // 处理主题色属性
    document.documentElement.setAttribute('data-color-theme', colorTheme.value)
    
    // 持久化
    localStorage.setItem('isDark', String(isDark.value))
    localStorage.setItem('colorTheme', colorTheme.value)
  }

  watch([isDark, colorTheme], apply, { immediate: true })

  const toggleDark = () => {
    isDark.value = !isDark.value
  }

  const setColorTheme = (theme: ColorTheme) => {
    colorTheme.value = theme
  }

  return { isDark, colorTheme, toggleDark, setColorTheme }
})
