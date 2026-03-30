<template>
  <div class="group relative rounded-[2rem] border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 p-6 backdrop-blur-xl shadow-2xl transition-all duration-500 hover:bg-gray-50 dark:hover:bg-white/10 hover:border-gray-300 dark:hover:border-white/20">
    <!-- 内部装饰性微光 -->
    <div class="absolute -inset-px rounded-[2rem] bg-gradient-to-br from-gray-100/80 dark:from-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
    
    <div class="relative z-10">
      <slot />
    </div>
  </div>
</template>

<style scoped>
@reference "tailwindcss";
</style>
