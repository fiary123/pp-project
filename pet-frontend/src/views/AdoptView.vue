<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { 
  Search, Heart, MapPin, Loader2, X, Wand2, Star, Quote, ChevronRight, Sparkles, Edit3, Trash2, Upload
} from 'lucide-vue-next';
import { useAuthStore } from '../store/authStore';
import axios from 'axios';

const authStore = useAuthStore();

// 1. 状态管理
const pets = ref<any[]>([]);
const isLoading = ref(true);
const searchQuery = ref('');
const activeFilter = ref('全部');
const selectedPet = ref<any>(null);

// AI 匹配状态
const aiQuery = ref('');
const isAiMatching = ref(false);
const recommendedMatches = ref<Record<number, string>>({});

// 管理员编辑状态
const showEditModal = ref(false);
const isUpdatingPet = ref(false);
const isUploading = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);
const editPetForm = ref({ id: 0, name: '', species: '', img: '', desc: '' });

// 处理本地上传
const triggerUpload = () => fileInput.value?.click();
const handleFileUpload = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  isUploading.value = true;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const res = await axios.post('http://127.0.0.1:8000/api/upload', formData);
    editPetForm.value.img = res.data.url;
  } catch (err) { alert('图片上传失败'); }
  finally { isUploading.value = false; }
};

// 2. 模拟数据生成
const generatePets = () => {
  const dogNames = ['旺财', '大黄', '糯米', '团团', '坦克', '奥利奥', '咖啡', '豆点', '馒头', '辛巴'];
  const catNames = ['咪咪', '花卷', '奶酪', '年糕', '露露', '皮皮', '糖糖', '布丁'];
  const exoticNames = ['吱吱', '灰灰', '翠儿', '刺刺', '呆呆', '悠悠', '萌萌', '泡泡'];
  
  const dogSpecies = [
    { name: '柯基', img: 'https://images.unsplash.com/photo-1583511655826-05700d52f4d9' },
    { name: '金毛', img: 'https://images.unsplash.com/photo-1552053831-71594a27632d' },
    { name: '柴犬', img: 'https://images.unsplash.com/photo-1583337130417-3346a1be7dee' }
  ];

  const catSpecies = [
    { name: '布偶猫', img: 'https://images.unsplash.com/photo-1533743983669-94fa5c4338ec' },
    { name: '英短', img: 'https://images.unsplash.com/photo-1513245543132-31f507417b26' }
  ];

  const exoticSpecies = [
    { name: '龙猫', img: 'https://images.unsplash.com/photo-1559190394-df5a28aab5c5' }
  ];

  const data = [];
  for (let i = 0; i < 60; i++) {
    const typeIdx = i % 3;
    const itemIdx = Math.floor(i/3);
    let type, name, speciesInfo;
    if (typeIdx === 0) { type='狗狗'; name=dogNames[itemIdx%dogNames.length]; speciesInfo=dogSpecies[itemIdx%dogSpecies.length]; }
    else if (typeIdx === 1) { type='猫咪'; name=catNames[itemIdx%catNames.length]; speciesInfo=catSpecies[itemIdx%catSpecies.length]; }
    else { type='异宠'; name=exoticNames[itemIdx%exoticNames.length]; speciesInfo=exoticSpecies[itemIdx%exoticSpecies.length]; }

    data.push({
      id: i + 1000,
      name,
      type,
      species: speciesInfo.name,
      match: 75 + Math.floor(Math.random() * 20),
      img: `${speciesInfo.img}?sig=${i}&auto=format&fit=crop&w=800&q=80`,
      tags: i % 2 === 0 ? ['温顺', '粘人'] : ['活泼', '聪明'],
      desc: `这是一只非常可爱的${speciesInfo.name}，期待新主人。`,
      distance: (Math.random() * 10).toFixed(1)
    });
  }
  return data;
};

// 3. 数据加载
const fetchPets = async () => {
  isLoading.value = true;
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/pets');
    if (res.data && res.data.length >= 10) {
      pets.value = res.data.map((p: any) => ({
        ...p,
        img: p.image_url || `https://images.unsplash.com/photo-1543466835-00a7907e9de1?sig=${p.id}&auto=format&fit=crop&w=800&q=80`,
        desc: p.description || '暂无详细介绍',
        type: p.type || (p.id % 2 === 0 ? '狗狗' : '猫咪'),
        distance: (Math.random() * 5).toFixed(1),
        tags: p.tags ? p.tags.split(',') : ['温顺', '粘人'],
        match: 80 + (p.id % 20)
      }));
    } else {
      pets.value = generatePets();
    }
  } catch (err) {
    pets.value = generatePets();
  } finally {
    isLoading.value = false;
  }
};

const isAdmin = computed(() => authStore.user?.role === 'org_admin' || authStore.user?.role === 'root');

const startEditPet = (pet: any) => {
  editPetForm.value = { id: pet.id, name: pet.name, species: pet.species, img: pet.img, desc: pet.desc };
  showEditModal.value = true;
};

const handleUpdatePet = async () => {
  isUpdatingPet.value = true;
  try {
    if (editPetForm.value.id < 1000) {
      await axios.put(`http://127.0.0.1:8000/api/pets/${editPetForm.value.id}`, {
        name: editPetForm.value.name,
        species: editPetForm.value.species,
        image_url: editPetForm.value.img,
        description: editPetForm.value.desc
      });
    }
    const idx = pets.value.findIndex(p => p.id === editPetForm.value.id);
    if (idx !== -1) {
      pets.value[idx] = { ...pets.value[idx], ...editPetForm.value };
    }
  } catch (err) {}
  finally {
    showEditModal.value = false;
    isUpdatingPet.value = false;
  }
};

const handleDeletePet = async (petId: number) => {
  if (!confirm('确定要从领养列表中移除这只宠物吗？')) return;
  try {
    if (petId < 1000) await axios.delete(`http://127.0.0.1:8000/api/pets/${petId}`);
    pets.value = pets.value.filter(p => p.id !== petId);
  } catch (err) {}
};

const handleAiMatch = async () => {
  if (!aiQuery.value.trim()) return;
  isAiMatching.value = true;
  try {
    const res = await axios.post('http://127.0.0.1:8000/api/pets/smart-match', { user_query: aiQuery.value, pet_list: pets.value });
    const matchMap: Record<number, string> = {};
    if (res.data?.matches) res.data.matches.forEach((m: any) => matchMap[m.id] = m.reason);
    recommendedMatches.value = matchMap;
    activeFilter.value = '全部';
    searchQuery.value = '';
  } catch (err) {}
  finally { isAiMatching.value = false; }
};

const filteredPets = computed(() => {
  const recIds = Object.keys(recommendedMatches.value).map(Number);
  let result = pets.value.filter(p => {
    const search = searchQuery.value.toLowerCase();
    const nameMatch = p.name.toLowerCase().includes(search);
    const speciesMatch = p.species.toLowerCase().includes(search);
    const matchesType = activeFilter.value === '全部' || p.type === activeFilter.value;
    return (nameMatch || speciesMatch) && matchesType;
  });
  if (recIds.length > 0) return result.sort((a, b) => (recIds.includes(b.id)?1:0) - (recIds.includes(a.id)?1:0));
  return result.sort((a, b) => b.match - a.match);
});

onMounted(fetchPets);
</script>

<template>
  <div class="space-y-12 pb-20 px-4 max-w-[1600px] mx-auto">
    <!-- 头部和 Hero 略，逻辑保持一致 -->
    <div class="relative py-16 text-center space-y-8 overflow-hidden rounded-[4rem] bg-gradient-to-b from-orange-500/10 to-transparent border border-white/5 shadow-2xl">
      <div class="relative z-10 space-y-4">
        <h2 class="text-6xl font-black text-white italic tracking-tighter uppercase text-orange-500 leading-tight">Find Your <br/>Perfect Match</h2>
        <div class="max-w-4xl mx-auto px-6 mt-8">
          <div class="bg-[#1a1a1a]/80 backdrop-blur-3xl p-2 rounded-[2.5rem] border border-white/10 flex items-center">
            <Wand2 class="ml-6 text-orange-500" :size="28" />
            <input v-model="aiQuery" @keyup.enter="handleAiMatch" type="text" placeholder="描述您的理想伙伴..." class="flex-1 bg-transparent py-6 px-6 text-white outline-none" />
            <button @click="handleAiMatch" :disabled="isAiMatching" class="bg-orange-500 text-white px-10 py-5 rounded-[2rem] font-black flex items-center gap-2">
              <Loader2 v-if="isAiMatching" class="animate-spin" :size="20" />立即匹配
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 过滤器 -->
    <div class="flex flex-col md:flex-row items-center justify-between gap-6 px-4">
      <div class="flex items-center gap-2 bg-white/5 p-1.5 rounded-2xl border border-white/5">
        <button v-for="cat in ['全部', '猫咪', '狗狗', '异宠']" :key="cat" @click="activeFilter = cat"
          :class="activeFilter === cat ? 'bg-orange-500 text-white' : 'text-gray-400 hover:text-white'" class="px-8 py-3 rounded-xl font-bold transition-all text-sm">
          {{ cat }}
        </button>
      </div>
      <div class="relative w-full md:w-96 group">
        <Search class="absolute left-5 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-orange-500 transition-colors" :size="18" />
        <input v-model="searchQuery" type="text" placeholder="搜索品种或名字..." class="w-full bg-white/5 border border-white/5 rounded-2xl py-4 pl-14 pr-6 text-white outline-none focus:bg-white/10 transition-all shadow-inner" />
      </div>
    </div>

    <!-- 卡片网格 -->
    <div class="px-2">
      <div v-if="isLoading" class="py-40 flex flex-col items-center"><Loader2 class="animate-spin text-orange-500" :size="48" /><p class="text-gray-500 font-black mt-4 uppercase">正在寻找伙伴...</p></div>
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-6">
        <div v-for="pet in filteredPets" :key="pet.id" class="bg-[#1a1a1a] rounded-3xl overflow-hidden border border-white/5 transition-all group cursor-pointer shadow-xl relative flex flex-col">
          <!-- 管理员控制台 -->
          <div v-if="isAdmin" class="p-3 bg-orange-500/10 border-b border-orange-500/20 flex justify-end gap-2">
            <button @click.stop="startEditPet(pet)" class="p-1.5 bg-blue-500/20 text-blue-400 hover:bg-blue-500 hover:text-white rounded border border-blue-500/30 transition-all"><Edit3 :size="14"/></button>
            <button @click.stop="handleDeletePet(pet.id)" class="p-1.5 bg-red-500/20 text-red-400 hover:bg-red-500 hover:text-white rounded border border-red-500/30 transition-all"><Trash2 :size="14"/></button>
          </div>

          <div @click="selectedPet = pet" class="relative aspect-square overflow-hidden">
            <img :src="pet.img" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
            <div class="absolute inset-0 bg-gradient-to-t from-[#1a1a1a]/80 via-transparent to-transparent"></div>
            <h4 class="absolute bottom-4 left-5 font-black text-xl text-white">{{ pet.name }}</h4>
          </div>
          <div @click="selectedPet = pet" class="p-5 space-y-4 flex-1">
            <div class="flex flex-wrap gap-1.5"><span v-for="t in pet.tags" :key="t" class="text-[9px] bg-white/5 px-2 py-1 rounded-lg text-gray-500">#{{ t }}</span></div>
            <div class="flex items-center justify-between pt-2 border-t border-white/5">
              <div><p class="text-[9px] text-gray-500 uppercase">{{ pet.species }}</p><div class="flex items-center gap-1 text-gray-400"><MapPin :size="10" /><span class="text-[9px] font-bold">{{ pet.distance }} KM</span></div></div>
              <ChevronRight class="text-orange-500" :size="16" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 宠物编辑弹窗 -->
    <Teleport to="body">
      <div v-if="showEditModal" class="fixed inset-0 z-[600] flex items-center justify-center bg-black/95 backdrop-blur-md px-4">
        <div class="bg-[#111] border border-white/10 p-10 rounded-[3rem] w-full max-w-xl space-y-6">
          <div class="flex justify-between items-center mb-4"><h3 class="text-2xl font-black text-white italic uppercase">Edit Pet Profile</h3><button @click="showEditModal=false" class="text-gray-500"><X :size="24"/></button></div>
          <div class="space-y-4">
            <input v-model="editPetForm.name" placeholder="宠物名字" class="w-full bg-white/5 border border-white/10 rounded-xl px-6 py-4 text-white outline-none focus:border-orange-500" />
            <input v-model="editPetForm.species" placeholder="品种" class="w-full bg-white/5 border border-white/10 rounded-xl px-6 py-4 text-white outline-none focus:border-orange-500" />
            
            <!-- 图片上传区域 -->
            <div class="flex gap-4">
              <input v-model="editPetForm.img" placeholder="图片地址" class="flex-1 bg-white/5 border border-white/10 rounded-xl px-6 py-4 text-white outline-none focus:border-orange-500" />
              <input type="file" ref="fileInput" class="hidden" accept="image/*" @change="handleFileUpload" />
              <button @click="triggerUpload" :disabled="isUploading" class="bg-white/10 hover:bg-white/20 text-white px-6 rounded-xl font-bold transition-all flex items-center gap-2">
                <Loader2 v-if="isUploading" class="animate-spin" :size="16" />
                <span v-else class="flex items-center gap-2"><Upload :size="16"/> 上传</span>
              </button>
            </div>

            <textarea v-model="editPetForm.desc" placeholder="详细描述" class="w-full h-32 bg-white/5 border border-white/10 rounded-xl p-6 text-white outline-none focus:border-orange-500"></textarea>
            <button @click="handleUpdatePet" :disabled="isUpdatingPet" class="w-full bg-orange-500 text-white py-4 rounded-xl font-black text-lg hover:bg-orange-600 transition-all flex justify-center items-center gap-2">
              <Loader2 v-if="isUpdatingPet" class="animate-spin" :size="20" />确认修改
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 详情弹窗 -->
    <Transition name="fade">
      <div v-if="selectedPet" class="fixed inset-0 z-[100] flex items-center justify-center p-4 backdrop-blur-2xl">
        <div class="absolute inset-0 bg-black/80" @click="selectedPet = null"></div>
        <div class="relative bg-[#111] border border-white/10 rounded-[4rem] max-w-6xl w-full flex flex-col lg:flex-row overflow-hidden shadow-2xl">
          <div class="lg:w-3/5 group overflow-hidden"><img :src="selectedPet.img" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-1000" /></div>
          <div class="lg:w-2/5 p-12 space-y-8 text-left">
            <div><span class="bg-orange-500/20 text-orange-500 px-4 py-1 rounded-full text-[10px] font-black uppercase">{{ selectedPet.type }}</span><h3 class="text-6xl font-black text-white mt-4">{{ selectedPet.name }}</h3></div>
            <p class="text-gray-400 text-lg leading-relaxed">{{ selectedPet.desc }}</p>
            <div class="flex gap-4 pt-4"><button class="flex-1 bg-white text-black py-6 rounded-[2rem] font-black text-xl hover:bg-orange-500 hover:text-white transition-all">立即领养</button><button class="p-6 bg-white/5 text-white rounded-[2rem] border border-white/10"><Heart :size="28" /></button></div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
@reference "tailwindcss";
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
