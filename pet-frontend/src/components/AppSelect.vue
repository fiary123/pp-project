<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'

type SelectOption = string | number | { label: string; value: string | number }

const props = defineProps<{
  modelValue: string | number
  options: SelectOption[]
  placeholder?: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
}>()

const rootRef = ref<HTMLElement | null>(null)
const isOpen = ref(false)

const normalizedOptions = computed(() =>
  (props.options || []).map((option) => {
    if (typeof option === 'object' && option !== null && 'value' in option) {
      return { label: String(option.label), value: option.value }
    }
    return { label: String(option), value: option }
  }),
)

const selectedLabel = computed(() => {
  const selected = normalizedOptions.value.find((option) => String(option.value) === String(props.modelValue))
  return selected?.label || props.placeholder || '请选择'
})

const toggleOpen = () => {
  if (props.disabled) return
  isOpen.value = !isOpen.value
}

const selectOption = (value: string | number) => {
  emit('update:modelValue', value)
  isOpen.value = false
}

const handleClickOutside = (event: MouseEvent) => {
  if (!rootRef.value) return
  if (event.target instanceof Node && !rootRef.value.contains(event.target)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div ref="rootRef" class="app-select relative">
    <button
      type="button"
      :disabled="disabled"
      @click="toggleOpen"
      class="app-select-trigger flex w-full items-center justify-between gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 text-left text-sm text-gray-900 shadow-sm transition-colors hover:border-orange-400 focus:outline-none focus:border-orange-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
    >
      <span class="truncate">{{ selectedLabel }}</span>
      <ChevronDown :size="16" class="shrink-0 text-slate-400 transition-transform" :class="{ 'rotate-180': isOpen }" />
    </button>

    <div
      v-if="isOpen"
      class="app-select-menu absolute left-0 right-0 top-[calc(100%+0.5rem)] z-[120] max-h-64 overflow-y-auto rounded-2xl border border-gray-200 bg-white p-2 shadow-2xl dark:border-slate-700 dark:bg-slate-900"
    >
      <button
        v-for="option in normalizedOptions"
        :key="String(option.value)"
        type="button"
        @click="selectOption(option.value)"
        class="flex w-full items-center rounded-xl px-3 py-2 text-left text-sm text-slate-700 transition-colors hover:bg-orange-50 hover:text-orange-600 dark:text-slate-200 dark:hover:bg-white/10 dark:hover:text-orange-300"
        :class="{ 'bg-orange-50 text-orange-600 dark:bg-white/10 dark:text-orange-300': String(option.value) === String(modelValue) }"
      >
        {{ option.label }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.app-select-menu {
  scrollbar-width: thin;
}
</style>
