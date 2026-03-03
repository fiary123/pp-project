<script setup lang="ts">
import { ref } from 'vue'
import { Cat, Dog, Bird, ThermometerSnowflake, Info, Wheat, ShieldCheck } from 'lucide-vue-next'
import BaseCard from '../components/BaseCard.vue'

// 1. 定义百科数据结构
const categories = [
  { id: 'cat', name: '猫咪', icon: Cat, color: 'text-orange-400' },
  { id: 'dog', name: '狗狗', icon: Dog, color: 'text-blue-400' },
  { id: 'bird', name: '鸟类', icon: Bird, color: 'text-green-400' },
  { id: 'reptile', name: '爬宠/蛇', icon: ThermometerSnowflake, color: 'text-purple-400' },
]

const wikiData: Record<string, any> = {
  cat: {
    title: '猫咪饲养百科',
    habit: '独居性动物，喜欢高处，每天睡眠时间长达 12-16 小时。通过呼噜声表达满足感。',
    feeding: '高蛋白质饮食为主。需定时喂水，建议使用流动水源增加饮水量。',
    health: '需定期接种妙三多疫苗，注意预防肾脏疾病和肥胖。',
    tags: ['高冷', '爱干净', '夜行性']
  },
  dog: {
    title: '狗狗饲养百科',
    habit: '群居性动物，高度忠诚，需要大量的社交和户外运动。通过摇尾巴表达兴奋。',
    feeding: '杂食性倾向。严禁喂食巧克力、洋葱、葡萄等对狗有毒的食物。',
    health: '需接种狂犬疫苗和五联/八联疫苗。定期驱虫是保持健康的关键。',
    tags: ['忠诚', '运动量大', '易训练']
  },
  reptile: {
    title: '爬宠（蛇/蜥蜴）百科',
    habit: '变温动物，依赖环境温度调节体温。性格安静，不需要大量的社交互动。',
    feeding: '根据品种不同，有肉食性（如玉米蛇）和植食性。需添加钙粉补充营养。',
    health: '环境湿度和温度控制至关重要。需配备专业的 UVB 晒灯和加热垫。',
    tags: ['极简饲养', '冷酷美感', '长寿']
  },
  bird: {
    title: '鸟类饲养百科',
    habit: '智商极高，善于模仿声音。需要宽敞的笼舍空间和丰富的玩具进行智力开发。',
    feeding: '主食混合谷物，辅以新鲜蔬果。需注意补充墨鱼骨以获取钙质。',
    health: '对空气质量极其敏感，严禁在鸟房使用喷雾或特氟龙厨具。',
    tags: ['善于社交', '声音悦耳', '高智商']
  }
}

const activeTab = ref('cat')
const currentInfo = ref(wikiData['cat'])

const switchTab = (id: string) => {
  activeTab.value = id
  currentInfo.value = wikiData[id]
}
</script>

<template>
  <div class="space-y-8 max-w-6xl mx-auto">
    <!-- A. 顶部标题 -->
    <div class="text-center space-y-2">
      <h2 class="text-4xl font-black text-white drop-shadow-2xl italic tracking-widest uppercase">Pet Encyclopedia</h2>
      <p class="text-orange-400 font-bold tracking-[0.3em] uppercase text-xs">全能宠物饲养百科手册</p>
    </div>

    <!-- B. 分类切换按钮组 -->
    <div class="flex flex-wrap justify-center gap-4">
      <button 
        v-for="cat in categories" 
        :key="cat.id"
        @click="switchTab(cat.id)"
        :class="[
          'flex items-center gap-3 px-8 py-4 rounded-2xl font-bold transition-all duration-500 border-2',
          activeTab === cat.id 
            ? 'bg-orange-500 border-orange-400 text-white shadow-lg shadow-orange-500/40 scale-105' 
            : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10 hover:border-white/20'
        ]"
      >
        <component :is="cat.icon" :class="activeTab === cat.id ? 'text-white' : cat.color" :size="24" />
        {{ cat.name }}
      </button>
    </div>

    <!-- C. 知识详情展示区 -->
    <transition name="fade-slide" mode="out-in">
      <div :key="activeTab" class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <!-- 左侧：基础画像 -->
        <BaseCard class="lg:col-span-1 flex flex-col items-center text-center justify-center space-y-6 min-h-[400px]">
          <div class="w-32 h-32 rounded-full bg-orange-500/20 flex items-center justify-center border-2 border-orange-500/50 shadow-inner">
             <component :is="categories.find(c => c.id === activeTab)?.icon" class="text-orange-500" :size="64" />
          </div>
          <div>
            <h3 class="text-3xl font-black text-white mb-2">{{ currentInfo.title }}</h3>
            <div class="flex flex-wrap justify-center gap-2">
              <span v-for="tag in currentInfo.tags" :key="tag" class="text-[10px] px-2 py-1 bg-white/10 rounded-lg text-orange-400 border border-white/5">
                # {{ tag }}
              </span>
            </div>
          </div>
        </BaseCard>

        <!-- 右侧：详细内容 -->
        <div class="lg:col-span-2 space-y-6">
          <BaseCard>
            <div class="flex items-start gap-4">
              <div class="p-3 rounded-xl bg-blue-500/20 text-blue-400 shadow-lg"><Info :size="20"/></div>
              <div>
                <h4 class="font-bold text-blue-400 mb-1">生活习性 / Habits</h4>
                <p class="text-gray-300 leading-relaxed">{{ currentInfo.habit }}</p>
              </div>
            </div>
          </BaseCard>

          <BaseCard>
            <div class="flex items-start gap-4">
              <div class="p-3 rounded-xl bg-orange-500/20 text-orange-400 shadow-lg"><Wheat :size="20"/></div>
              <div>
                <h4 class="font-bold text-orange-400 mb-1">喂养建议 / Feeding</h4>
                <p class="text-gray-300 leading-relaxed">{{ currentInfo.feeding }}</p>
              </div>
            </div>
          </BaseCard>

          <BaseCard>
            <div class="flex items-start gap-4">
              <div class="p-3 rounded-xl bg-green-500/20 text-green-400 shadow-lg"><ShieldCheck :size="20"/></div>
              <div>
                <h4 class="font-bold text-green-400 mb-1">健康医疗 / Health</h4>
                <p class="text-gray-300 leading-relaxed">{{ currentInfo.health }}</p>
              </div>
            </div>
          </BaseCard>
        </div>

      </div>
    </transition>
  </div>
</template>

<style scoped>
@reference "tailwindcss";

.fade-slide-enter-active, .fade-slide-leave-active {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
.fade-slide-enter-from { opacity: 0; transform: translateX(30px); }
.fade-slide-leave-to { opacity: 0; transform: translateX(-30px); }
</style>
