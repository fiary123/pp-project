<template>
  <div class="space-y-10">
    <!-- A. 沉浸式 Banner -->
    <section class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <div class="lg:col-span-2 relative h-[500px] bg-black rounded-[3rem] overflow-hidden shadow-2xl group cursor-pointer">
        <video autoplay muted loop class="w-full h-full object-cover opacity-60 group-hover:scale-105 transition-transform duration-1000">
          <source src="https://assets.mixkit.co/videos/preview/mixkit-playful-kitten-68-large.mp4" type="video/mp4">
        </video>
        <div class="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent"></div>
        <div class="absolute bottom-12 left-12 text-white space-y-4">
          <span class="bg-orange-500 text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-widest">Featured Story</span>
          <h2 class="text-5xl font-black leading-tight">在这里，开启您的<br/><span class="text-orange-400">智能领养</span>之旅</h2>
          <p class="text-gray-300 text-lg max-w-md">利用多智能体 AI 技术，为流浪动物匹配最温暖的归宿。我们不仅仅是在领养，更是在构建连接。</p>
          <div class="flex gap-4 pt-4">
            <button @click="$router.push('/adopt')" class="bg-orange-500 px-8 py-3 rounded-2xl font-bold hover:bg-orange-600 transition-all">立即寻找</button>
            <button @click="$router.push('/wiki')" class="bg-white/10 backdrop-blur px-8 py-3 rounded-2xl font-bold hover:bg-white/20 transition-all">养宠百科</button>
          </div>
        </div>
      </div>

      <!-- 公告列表 -->
      <BaseCard class="flex flex-col">
        <div class="flex items-center justify-between mb-8">
          <h3 class="font-bold text-xl flex items-center gap-2"><Bell class="text-orange-500" :size="20"/> 系统公告</h3>
        </div>
        <div class="space-y-6 flex-1">
          <div v-for="i in 3" :key="i" class="group cursor-pointer">
            <p class="text-[10px] text-orange-400 font-bold mb-1">MARCH 03, 2026</p>
            <h4 class="text-sm font-bold text-white group-hover:text-orange-500 transition-colors">关于本周末线下领养日的防疫要求及活动指南</h4>
            <div class="mt-2 h-px w-full bg-white/5"></div>
          </div>
        </div>
        <button class="w-full mt-6 py-4 rounded-2xl border border-white/10 text-xs font-bold text-gray-400 hover:bg-white/5 transition-all">查看全部历史公告</button>
      </BaseCard>
    </section>

    <!-- B. 快速功能入口 (增加差异化) -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <BaseCard @click="$router.push('/triage')" class="cursor-pointer hover:border-orange-500/50 transition-all">
        <Heart class="text-orange-500 mb-4" :size="32" />
        <h4 class="font-bold text-lg text-white">智能分诊</h4>
        <p class="text-xs text-gray-400 mt-2">AI 医生 24/7 为您的宠物健康保驾护航</p>
      </BaseCard>
      <BaseCard @click="$router.push('/wiki')" class="cursor-pointer hover:border-blue-500/50 transition-all">
        <BookOpen class="text-blue-500 mb-4" :size="32" />
        <h4 class="font-bold text-lg text-white">养宠百科</h4>
        <p class="text-xs text-gray-400 mt-2">覆盖 100+ 品种的专业饲养知识库</p>
      </BaseCard>
      <BaseCard @click="$router.push('/dashboard')" class="cursor-pointer hover:border-green-500/50 transition-all">
        <ShieldCheck class="text-green-500 mb-4" :size="32" />
        <h4 class="font-bold text-lg text-white">管理大盘</h4>
        <p class="text-xs text-gray-400 mt-2">实时监控平台数据与领养审核动态</p>
      </BaseCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Bell, Heart, BookOpen, ShieldCheck } from 'lucide-vue-next';
import BaseCard from '../components/BaseCard.vue';
</script>

<style scoped>
@reference "tailwindcss";
</style>
