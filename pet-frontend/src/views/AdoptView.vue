<template>
  <div class="space-y-10">
    <!-- A. 搜索与筛选区域 -->
    <div class="text-center space-y-4">
      <h2 class="text-4xl font-black text-white drop-shadow-2xl">寻找您的完美伴侣</h2>
      <p class="text-gray-400">基于 AI 智能算法，为您匹配最合适的宠物成员</p>
      
      <div class="max-w-2xl mx-auto flex gap-4 mt-8">
        <div class="flex-1 relative">
          <Search class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" :size="20" />
          <input type="text" placeholder="搜索品种、性格、关键词..." 
                 class="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white focus:outline-none focus:border-orange-500 transition-all shadow-xl">
        </div>
        <button class="bg-orange-500 px-8 rounded-2xl font-bold hover:bg-orange-600 transition-all shadow-lg shadow-orange-500/20">
          筛选
        </button>
      </div>
    </div>

    <!-- B. 瀑布流展示区 -->
    <section>
      <div class="columns-1 sm:columns-2 lg:columns-4 gap-6 space-y-6">
        <div v-for="pet in pets" :key="pet.id" 
             class="break-inside-avoid bg-white/5 backdrop-blur-md rounded-3xl overflow-hidden border border-white/10 hover:shadow-2xl hover:-translate-y-2 transition-all duration-500 group cursor-pointer"
             @click="goToDetail(pet)">
          <div class="relative overflow-hidden">
            <img :src="pet.img" class="w-full h-auto object-cover group-hover:scale-110 transition-transform duration-700 opacity-90 group-hover:opacity-100">
            <div class="absolute top-4 left-4 bg-orange-500 text-white px-3 py-1 rounded-full text-[10px] font-bold shadow-sm">
               {{ pet.type }}
            </div>
          </div>
          <div class="p-6">
            <div class="flex justify-between items-start mb-3">
              <div>
                <h4 class="font-bold text-xl text-white">{{ pet.name }}</h4>
                <p class="text-xs text-gray-400">{{ pet.species }} · {{ pet.age }}岁</p>
              </div>
              <div class="text-right">
                <span class="text-orange-500 font-black text-lg">{{ pet.match }}%</span>
                <p class="text-[8px] text-orange-400 uppercase tracking-widest font-bold">匹配度</p>
              </div>
            </div>
            <div class="flex flex-wrap gap-2 mb-4">
               <span v-for="tag in pet.tags" :key="tag" 
                     class="text-[10px] bg-white/5 px-2 py-1 rounded-md text-gray-400 border border-white/5">
                 #{{ tag }}
               </span>
            </div>
            <p class="text-xs text-gray-400 line-clamp-2 leading-relaxed">{{ pet.desc }}</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Search } from 'lucide-vue-next';

const pets = ref([
  { id: 1, name: '布丁', species: '英国短毛猫', age: 2, type: '待领养', match: 98, img: 'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?q=80&w=1000', tags: ['安静', '温顺'], desc: '性格温和，喜欢陪伴工作中的主人。' },
  { id: 2, name: '豆包', species: '比熊犬', age: 1, type: '待领养', match: 92, img: 'https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?q=80&w=1000', tags: ['活泼', '不掉毛'], desc: '体型小，聪明，不掉毛，适合公寓居住。' },
  { id: 3, name: '辛巴', species: '金毛', age: 3, type: '流浪救助', match: 85, img: 'https://images.unsplash.com/photo-1552053831-71594a27632d?q=80&w=1000', tags: ['亲人', '运动型'], desc: '典型的大暖男，对人非常友好。' },
  { id: 4, name: '年糕', species: '萨摩耶', age: 1, type: '待领养', match: 88, img: 'https://images.unsplash.com/photo-1529429617329-8a79e088c02c?q=80&w=1000', tags: ['微笑天使'], desc: '颜值极高，性格活泼。' }
]);

const goToDetail = (pet: any) => console.log('详情:', pet.name);
</script>

<style scoped>
@reference "tailwindcss";
</style>
