<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { Sparkles, Send, ChevronLeft, Eye } from 'lucide-vue-next'
import axios from '../api/index'

// 1. 全量推文数据 (保持最新封面和内容)
const allPosts = [
  {
    id: 1,
    category: 'cat',
    title: '【猫咪篇】全能养护·疾病·营养·环境百科手册',
    summary: '猫咪高冷又软萌，看似省心，实则养护需兼顾营养、环境与疾病预防。掌握核心，守护它安稳一生。',
    cover: 'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?q=80&w=1000',
    date: '2026-03-03',
    author: 'SmartPet 官方',
    views: '3.8w',
    content: [
      { type: 'p', text: '猫咪高冷又软萌，看似省心，实则养护需兼顾营养、环境与疾病预防，掌握核心要点，就能守护它安稳度过一生，新手也能轻松上手。' },
      { type: 'h2', text: '🍲 营养方面：遵循“精准适配”' },
      { type: 'p', text: '• 幼猫：少食多餐，每天3-4次，喂幼猫专用粮+羊奶粉，忌喂牛奶以防乳糖不耐受。\n• 成猫：每天1-2次，定时定量，优先选无谷猫粮，搭配少量水煮鸡胸肉、无盐蛋黄补充。' },
      { type: 'quote', text: '“坚决避开巧克力、洋葱、葡萄等有毒食物，并保证充足的新鲜饮水。”' },
      { type: 'img', url: 'https://images.unsplash.com/photo-1573865662567-57effa574d7a?q=80&w=800' },
      { type: 'h2', text: '🏠 环境与护理：细节决定寿命' },
      { type: 'p', text: '• 居住安全：封窗防盗网是重中之重，必须确保万无一失，彻底杜绝坠楼风险。\n• 清洁频率：猫咪无需频繁洗澡，3-6个月一次即可。每周梳毛1-2次减少毛球症。\n• 日常维护：每月剪指甲，定期清理耳道和眼角。体内外驱虫：幼猫每月一次，成猫按需。' },
      { type: 'img', url: 'https://images.unsplash.com/photo-1592194996308-7b43878e84a6?q=80&w=800' },
      { type: 'h2', text: '🩺 疾病预防：疫苗与信号' },
      { type: 'p', text: '• 疫苗计划：幼猫8周龄开始接种猫三联，3月龄打狂犬疫苗，此后每年定期补针。\n• 警惕信号：拒食、精神萎靡、呕吐腹泻、粪便异常需及时就医。保持环境干燥清洁，是减少皮肤病和呼吸道疾病的关键。' }
    ]
  },
  {
    id: 2,
    category: 'dog',
    title: '【狗狗篇】科学饲养指南：给它最长情的告白',
    summary: '狗狗是人类最忠诚的伙伴，科学饲养是对它最长情的告白。涵盖饮食、护理、疫苗及文明养犬全指南。',
    cover: 'https://images.unsplash.com/photo-1552053831-71594a27632d?q=80&w=1000',
    date: '2026-03-02',
    author: '金牌训犬师',
    views: '2.1w',
    content: [
      { type: 'p', text: '狗狗是人类最忠诚的伙伴，科学饲养是对它最长情的告白。新手无需盲目跟风，抓住核心要点，就能陪它健康走过十几年时光。' },
      { type: 'h2', text: '🍲 饮食是基础：营养均衡' },
      { type: 'p', text: '• 幼犬：少食多餐，每天 3-4 次，喂幼犬专用粮+羊奶粉，严禁喂牛奶以免腹泻。\n• 成犬：每天 2 次，定时定量。可搭配少量水煮鸡胸肉、无盐蛋黄补充营养。\n• 绝禁食物：巧克力、葡萄、洋葱、木糖醇等对狗具有剧毒。' },
      { type: 'img', url: 'https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?q=80&w=800' },
      { type: 'h2', text: '🧼 日常护理与健康' },
      { type: 'p', text: '• 洗澡：短毛狗 1-2 个月一次，长毛狗 2-3 周一次。洗完必须彻底吹干以防皮肤病。\n• 清洁：每月剪指甲，每周梳毛并清理耳道。定期进行体内外驱虫。\n• 疫苗：幼犬 8 周龄开始打联苗（如六联/八联），3 月龄打狂犬疫苗，此后每年按时补针。' },
      { type: 'quote', text: '“疫苗接种和定期驱虫是狗狗健康生存的底线。”' },
      { type: 'h2', text: '🐾 陪伴、训练与文明养犬' },
      { type: 'p', text: '• 互动：每天抽出时间陪伴运动，避免孤独导致的行为焦虑。\n• 训练：耐心引导定点如厕和基础指令（坐、靠、等），不打骂，多用零食奖励。\n• 文明：外出务必牵牵引绳，随手清理粪便。做负责任的主人，让它安心陪伴。' },
      { type: 'img', url: 'https://images.unsplash.com/photo-1534361960057-19889db9621e?q=80&w=800' }
    ]
  },
  {
    id: 3,
    category: 'reptile',
    title: '【爬宠篇】冷血动物的温情：环境与疾病百科',
    summary: '爬宠（蜥蜴、乌龟、蛇等）虽为冷血动物，却也需要细致呵护。核心是模拟自然栖息地，把控温湿度。',
    cover: 'https://images.unsplash.com/photo-1528158222524-d4d912d2e208?q=80&w=1000',
    date: '2026-03-01',
    author: '爬界元老',
    views: '9.2k',
    content: [
      { type: 'p', text: '爬宠（蜥蜴、乌龟、蛇等）虽为冷血动物，却也需要细致呵护，核心是模拟其自然栖息地，把控温湿度与饮食，就能轻松养出健康状态，新手也能快速上手。' },
      { type: 'h2', text: '🏠 环境搭建：核心是“冷热分区”' },
      { type: 'p', text: '需打造精准的温度梯度：冷区保持 22-26℃，热区保持 30-32℃。使用加热灯或加热垫控温，避免温差过大导致感冒或消化不良。\n• 湿度控制：蜥蜴类通常需 50%-70%，乌龟类 60%-80%。建议配备加湿器或大水盆。\n• 垫材：选用无菌椰土或树皮，严禁使用带粉尘的垫材。' },
      { type: 'img', url: 'https://images.unsplash.com/photo-1504450874802-0ba2bcd9b5ae?q=80&w=800' },
      { type: 'h2', text: '🍽️ 饮食原则：按需投喂，宁少勿多' },
      { type: 'p', text: '• 蜥蜴：主食面包虫、蟋蟀，辅以少量蔬菜补充维生素。\n• 乌龟：水龟喂专用粮+小鱼虾；陆龟喂草本饲料+蔬菜。严禁含盐、油腻食物。\n• 频率：幼体每日一次，成体 2-3 天一次。' },
      { type: 'quote', text: '“养爬就是养环境。环境参数对了，你的爬宠就成功了一大半。”' },
      { type: 'h2', text: '🩺 疾病预防与信号' },
      { type: 'p', text: '减少应激：避免频繁上手把玩。警惕信号：\n1. 拒食/萎靡：检查温湿度是否波动。\n2. 皮肤脱皮/溃烂：立即消毒环境并药浴。\n3. 眼部肿胀/流涕：警惕呼吸道感染，需及时就医。' },
      { type: 'img', url: 'https://images.unsplash.com/photo-1508804052814-cd3ba865a116?q=80&w=800' }
    ]
  },
  {
    id: 4,
    category: 'all',
    title: '【综合】啮齿类与鸟类养护：小巧毛孩专属全攻略',
    summary: '仓鼠、龙猫、兔子及鹦鹉等鸟类如何精准养护？涵盖居住、饮食、清洁及健康全细节。',
    cover: 'https://images.pexels.com/photos/372166/pexels-photo-372166.jpeg?auto=compress&cs=tinysrgb&w=1000',
    date: '2026-02-28',
    author: '异宠达人',
    views: '2.8w',
    content: [
      { type: 'p', text: '啮齿类（仓鼠、龙猫、兔子等）和鸟类（鹦鹉、文鸟、玄凤等）体型小巧、性情温顺，是很多新手的入门选择。精准呵护才能让它们健康存活。' },
      { type: 'h2', text: '🐹 啮齿类养护（仓鼠、龙猫、兔子）' },
      { type: 'p', text: '• 仓鼠：需封闭式笼子防止越狱，垫材首选无尘纸棉。\n• 龙猫：环境需控制在15-25℃，极度怕热。\n• 兔子：宽敞空间避免应激，主食必须是提摩西草。' },
      { type: 'img', url: 'https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?q=80&w=800' }
    ]
  },
  {
    id: 5,
    category: 'fish',
    title: '【水族篇】从零打造家庭水族生态箱',
    summary: '想拥有一缸自循环的水下微世界？详细解析“先养水、再培菌、后放鱼”的硬核逻辑。',
    cover: 'https://images.unsplash.com/photo-1522069169874-c58ec4b76be5?q=80&w=1000',
    date: '2026-02-26',
    author: '水族造景师',
    views: '6.7k',
    content: [
      { type: 'p', text: '想拥有一缸自循环的水下微世界？新手打造生态箱，核心是 “先养水、再培菌、后放鱼”，抓住这三步，就能轻松建立稳定的水族生态。' },

      { type: 'h2', text: '🛠️ 第一步：设备选择与布局' },
      { type: 'p', text: '1. 鱼缸：新手优先选 40-60cm 超白玻璃缸，避开阳光直射（防爆藻）。\n2. 过滤：流量应为水体 5-8 倍/小时，滤材必选火山石+陶瓷环。\n3. 灯光：配 6500K 全光谱 LED，每日定时 8 小时。\n4. 底床：铺 3-5mm 火山石搭配少量水草泥，造景用沉木、溪流石。' },
      { type: 'img', url: 'https://images.unsplash.com/photo-1524704659690-3f8037203b3d?q=80&w=800' },

      { type: 'h2', text: '🌊 第二步：关键的开缸养水' },
      { type: 'p', text: '注入困过 24 小时的自来水，开启过滤后添加硝化细菌。前 3-5 天少量投喂鱼食模拟污染以促进菌群繁殖。持续运行 7-14 天，待氨和亚硝酸盐检测为零，硝化系统即告建立。' },
      { type: 'quote', text: '“养鱼先养水，水好鱼不愁。稳定的硝化系统是水族的灵魂。”' },

      { type: 'h2', text: '🐟 第三步：生物投放与日常维护' },
      { type: 'p', text: '1. 放闯缸生物：先放黑壳虾或苹果螺清理控藻，观察 3 天。\n2. 选品种：选灯科鱼、孔雀鱼等小型耐活品种，遵循 “1.5 升水养 1 条鱼” 的密度。\n3. 过温过水：入缸前温漂 15 分钟，再缓慢兑水以减少应激。\n4. 日常：2分钟吃完原则，每周换 1/4 困过的水，每月清洗表层滤材。' },
      { type: 'img', url: 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?q=80&w=800' }
    ]
  }
  ]
// 状态控制
const activeCategory = ref('all')
const categoryNames: Record<string, string> = { all: '全部', cat: '猫咪', dog: '狗狗', reptile: '爬宠', fish: '鱼类' }
const selectedArticleId = ref<number | null>(null)
const filteredPosts = computed(() => activeCategory.value === 'all' ? allPosts : allPosts.filter(p => p.category === activeCategory.value))
const currentArticle = computed(() => allPosts.find(p => p.id === selectedArticleId.value))

// AI 助手逻辑与滚动修复
const userInput = ref('')
const isThinking = ref(false)
const chatHistory = ref([{ role: 'ai', text: '你好！我是 AI 百科助手。有什么关于养宠的疑问吗？' }])
const scrollContainer = ref<HTMLElement | null>(null)

// 核心功能：自动滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (scrollContainer.value) {
    scrollContainer.value.scrollTo({
      top: scrollContainer.value.scrollHeight,
      behavior: 'smooth'
    })
  }
}

// 监听聊天记录变化，触发滚动
watch(chatHistory, () => {
  scrollToBottom()
}, { deep: true })

const handleAsk = async () => {
  if (!userInput.value.trim()) return
  const msg = userInput.value
  chatHistory.value.push({ role: 'user', text: msg })
  userInput.value = ''
  isThinking.value = true
  
  // 发送后立即触底
  scrollToBottom()

  try {
    const res = await axios.post('/api/chat', { message: msg })
    chatHistory.value.push({ role: 'ai', text: res.data.reply })
  } catch {
    chatHistory.value.push({ role: 'ai', text: '连接超时，专家正在路上' })
  } finally { 
    isThinking.value = false 
    scrollToBottom()
  }
}
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 max-w-[1600px] mx-auto px-4">
    
    <!-- 左侧：推文流 (占 7 列) -->
    <div class="lg:col-span-7">
      <transition name="fade-slide" mode="out-in">
        <div v-if="!selectedArticleId" key="list" class="space-y-8">
          <div class="flex items-end justify-between border-b border-white/10 pb-6">
            <div>
              <h2 class="text-4xl font-black text-white italic tracking-tighter uppercase text-orange-500">宠物百科</h2>
              <p class="text-gray-400 font-bold text-xs uppercase tracking-[0.3em] mt-1">智能百科知识库</p>
            </div>
            <div class="flex gap-4">
              <button v-for="c in [{v:'all',n:'全部'},{v:'cat',n:'猫咪'},{v:'dog',n:'狗狗'},{v:'reptile',n:'爬宠'},{v:'fish',n:'鱼类'}]" :key="c.v" @click="activeCategory = c.v"
                      :class="activeCategory === c.v ? 'text-orange-500 font-black border-b-2 border-orange-500' : 'text-gray-500'"
                      class="text-xs uppercase font-bold transition-all hover:text-white px-2">{{ c.n }}</button>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div v-for="post in filteredPosts" :key="post.id" @click="selectedArticleId = post.id"
                 class="group bg-[#1a1a1a] rounded-[2.5rem] overflow-hidden border border-white/5 hover:border-orange-500/40 transition-all cursor-pointer shadow-2xl">
              <div class="h-56 overflow-hidden relative">
                <img :src="post.cover" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-1000" />
                <div class="absolute top-4 left-4 bg-orange-500 text-white text-[10px] font-black px-2 py-1 rounded-full uppercase">{{ categoryNames[post.category] || post.category }}</div>
              </div>
              <div class="p-8 space-y-4">
                <h3 class="text-xl font-bold text-white group-hover:text-orange-400 leading-tight transition-colors">{{ post.title }}</h3>
                <p class="text-xs text-gray-500 leading-relaxed line-clamp-2">{{ post.summary }}</p>
                <div class="flex items-center justify-between pt-4 border-t border-white/5 text-gray-600 text-[10px] font-bold">
                  <span class="flex items-center gap-1"><Eye :size="12"/> {{ post.views }} 阅读</span>
                  <span class="text-orange-500 uppercase tracking-widest">阅读全文</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else key="reader" class="bg-white rounded-[3.5rem] text-gray-900 overflow-hidden shadow-2xl">
          <div class="relative h-[400px]">
            <img :src="currentArticle?.cover" class="w-full h-full object-cover" />
            <div class="absolute inset-0 bg-gradient-to-t from-white/20 via-transparent to-transparent"></div>
            <button @click="selectedArticleId = null" class="absolute top-10 left-10 p-4 bg-black/10 backdrop-blur-xl rounded-full text-white hover:bg-black/30 transition-all">
              <ChevronLeft :size="24" />
            </button>
          </div>
          <article class="max-w-2xl mx-auto py-12 px-8">
            <header class="mb-12 space-y-6 text-center">
              <h1 class="text-4xl font-black leading-tight tracking-tighter">{{ currentArticle?.title }}</h1>
              <p class="text-gray-400 text-sm"> SmartPet 官方认证知识库 • {{ currentArticle?.date }} </p>
            </header>
            <div class="space-y-10 prose prose-orange">
              <div v-for="(block, i) in currentArticle?.content" :key="i">
                <h2 v-if="block.type === 'h2'" class="text-2xl font-black text-black flex items-center gap-3 mt-10 mb-6">
                  <span class="w-1.5 h-6 bg-orange-500 rounded-full"></span> {{ block.text }}
                </h2>
                <p v-else-if="block.type === 'p'" class="text-lg leading-loose text-gray-700 whitespace-pre-line">{{ block.text }}</p>
                <div v-else-if="block.type === 'quote'" class="bg-orange-50 p-8 rounded-[2rem] border-l-[6px] border-orange-500 my-8">
                  <p class="text-lg font-bold text-orange-900">{{ block.text }}</p>
                </div>
                <img v-else-if="block.type === 'img'" :src="block.url" class="rounded-[2.5rem] shadow-xl my-10 w-full" />
              </div>
            </div>
          </article>
        </div>
      </transition>
    </div>

    <!-- 右侧：AI 问答侧边栏 (解决滚动失效版) -->
    <div class="lg:col-span-5 h-[800px] sticky top-28">
      <!-- 放弃 BaseCard，改用原生 div 确保 flex 布局高度严格受控 -->
      <div class="h-full flex flex-col rounded-[2.5rem] border border-orange-500/30 bg-[#121212]/95 backdrop-blur-2xl shadow-[0_30px_60px_rgba(0,0,0,0.5)] overflow-hidden">
        
        <!-- 头部 (高度固定) -->
        <div class="p-8 border-b border-white/5 bg-gradient-to-br from-orange-500/10 to-transparent flex-shrink-0">
          <div class="flex items-center gap-5">
            <div class="p-4 bg-orange-500 rounded-2xl text-white shadow-lg shadow-orange-500/40"><Sparkles :size="28" /></div>
            <div>
              <h4 class="text-xl font-black text-white uppercase tracking-tighter italic">AI 智能百科</h4>
              <p class="text-xs text-orange-400 font-bold tracking-widest mt-1 uppercase">全天候专家助手</p>
            </div>
          </div>
        </div>

        <!-- 聊天记录区域 (核心滚动修复：占据剩余空间并允许溢出滚动) -->
        <div 
          ref="scrollContainer"
          class="flex-1 p-8 overflow-y-auto space-y-8 scrollbar-custom"
        >
          <div v-for="(m, i) in chatHistory" :key="i" :class="m.role === 'ai' ? 'items-start' : 'items-end'" class="flex flex-col gap-3">
            <div :class="m.role === 'ai' ? 'bg-white/5 text-gray-100 rounded-tr-[2rem]' : 'bg-orange-500 text-white rounded-tl-[2rem] shadow-2xl shadow-orange-500/30'"
                 class="max-w-[95%] p-6 rounded-b-[2rem] text-base leading-relaxed border border-white/5 font-medium tracking-wide break-words whitespace-pre-wrap">
              {{ m.text }}
            </div>
          </div>
          
          <!-- Thinking 动画 -->
          <div v-if="isThinking" class="flex items-center gap-4 p-5 bg-white/5 rounded-3xl w-max">
            <div class="flex gap-1.5">
              <span class="w-2 h-2 bg-orange-500 rounded-full animate-bounce"></span>
              <span class="w-2 h-2 bg-orange-500 rounded-full animate-bounce [animation-delay:0.2s]"></span>
              <span class="w-2 h-2 bg-orange-500 rounded-full animate-bounce [animation-delay:0.4s]"></span>
            </div>
            <span class="text-xs font-bold text-orange-500 uppercase tracking-widest animate-pulse">Agent Analyzing...</span>
          </div>
        </div>

        <!-- 输入区域 (高度固定) -->
        <div class="p-8 bg-black/40 border-t border-white/5 flex-shrink-0">
          <div class="relative flex gap-4">
            <input 
              v-model="userInput" 
              @keyup.enter="handleAsk" 
              placeholder="在此输入您的问题..." 
              class="flex-1 bg-white/5 border border-white/10 rounded-[1.5rem] py-5 px-8 text-base text-white focus:border-orange-500 outline-none transition-all placeholder:text-gray-600" 
            />
            <button 
              @click="handleAsk" 
              class="p-5 bg-orange-500 rounded-[1.5rem] text-white hover:bg-orange-600 shadow-xl shadow-orange-500/30 transition-all active:scale-95"
            >
              <Send :size="24" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* @reference "tailwindcss"; */

/* 全局切换动画 */
.fade-slide-enter-active, .fade-slide-leave-active { transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1); }
.fade-slide-enter-from { opacity: 0; transform: translateY(40px); }
.fade-slide-leave-to { opacity: 0; transform: translateY(-40px); }

/* 关键：自定义滚动条样式 */
.scrollbar-custom::-webkit-scrollbar {
  width: 6px;
}
.scrollbar-custom::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-custom::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
}
.scrollbar-custom::-webkit-scrollbar-thumb:hover {
  background: #f97316;
}

/* 防止长英文单词撑破容器 */
.break-words {
  word-break: break-word;
  overflow-wrap: break-word;
}
</style>
