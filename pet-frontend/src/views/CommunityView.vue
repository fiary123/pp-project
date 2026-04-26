<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import {
  MessageCircle, Heart, Plus, X, Loader2,
  Upload, ChevronLeft, ChevronRight, Sparkles, ShieldCheck, Info
} from 'lucide-vue-next';
import { useAuthStore } from '../store/authStore';
import BaseCard from '../components/BaseCard.vue';
import axios from '../api/index';

const authStore = useAuthStore();

const defaultAdoptionPreferences = {
  allow_novice: true,
  accept_renting: true,
  require_stable_housing: true,
  require_followup_updates: true,
  forbid_children: false,
  forbid_other_pets: false,
  min_budget_level: '中',
  required_housing_type: '公寓',
  min_companion_hours: 2,
  special_notes: '',
  risk_tolerance: 'medium'
};

const parseAdoptionPreferences = (raw: unknown) => {
  if (!raw) return { ...defaultAdoptionPreferences };
  if (typeof raw === 'string') {
    try {
      return { ...defaultAdoptionPreferences, ...(JSON.parse(raw) as Record<string, unknown>) };
    } catch { return { ...defaultAdoptionPreferences }; }
  }
  return { ...defaultAdoptionPreferences, ...(raw as Record<string, unknown>) };
};

// 状态管理
const posts = ref<any[]>([]);
const activeType = ref<'all' | 'daily' | 'experience' | 'adopt_help'>('all');
const isLoading = ref(false);

const showPublishModal = ref(false);
const isEditing = ref(false);
const editingPostId = ref<number | null>(null);
const publishType = ref<'daily' | 'experience' | 'adopt_help'>('daily');
const publishForm = ref({
  title: '', content: '', image_urls: [] as string[],
  pet_name: '', pet_gender: 'male', pet_age: '1', pet_breed: '', adopt_reason: '', location: '',
  adoption_preferences: { ...defaultAdoptionPreferences }
});
const isPublishing = ref(false);
const isUploading = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

const likedPosts = ref<Set<number>>(new Set());
const activePostComments = ref<Record<number, any[]>>({});
const commentInputs = ref<Record<number, string>>({});

// 图片浏览器
const showViewer = ref(false);
const viewerImages = ref<string[]>([]);
const viewerIndex = ref(0);
const openViewer = (imgs: string[], idx = 0) => { viewerImages.value = imgs; viewerIndex.value = idx; showViewer.value = true; };

const fetchPosts = async () => {
  isLoading.value = true;
  try {
    const res = await axios.get('/api/posts');
    const items = Array.isArray(res.data) ? res.data : (res.data?.items || []);
    posts.value = items.map((p: any) => ({
      ...p,
      adoption_preferences: parseAdoptionPreferences(p.adoption_preferences),
      create_time: p.create_time ? new Date(p.create_time).toLocaleString() : '刚刚'
    }));
  } catch { posts.value = []; }
  finally { isLoading.value = false; }
};

const handlePublish = async () => {
  if (!publishForm.value.content) return;
  isPublishing.value = true;
  try {
    const payload = {
      ...publishForm.value,
      user_id: authStore.user?.id,
      image_url: publishForm.value.image_urls[0] || '',
      image_urls: JSON.stringify(publishForm.value.image_urls),
      type: publishType.value,
    };
    if (isEditing.value) await axios.put(`/api/posts/${editingPostId.value}`, payload);
    else await axios.post('/api/posts', payload);
    fetchPosts(); closeModal();
  } catch { alert('发布失败'); }
  finally { isPublishing.value = false; }
};

const closeModal = () => {
  showPublishModal.value = false;
  isEditing.value = false;
  publishForm.value = { title: '', content: '', image_urls: [], pet_name: '', pet_gender: 'male', pet_age: '1', pet_breed: '', adopt_reason: '', location: '', adoption_preferences: { ...defaultAdoptionPreferences } };
};

const startEdit = (post: any) => {
  isEditing.value = true;
  editingPostId.value = post.id;
  publishType.value = post.type;
  publishForm.value = {
    title: post.title || '', content: post.content,
    image_urls: post.image_urls ? JSON.parse(post.image_urls) : (post.image_url ? [post.image_url] : []),
    pet_name: post.pet_name || '', pet_gender: post.pet_gender || 'male',
    pet_age: post.pet_age || '1', pet_breed: post.pet_breed || '',
    adopt_reason: post.adopt_reason || '', location: post.location || '',
    adoption_preferences: parseAdoptionPreferences(post.adoption_preferences)
  };
  showPublishModal.value = true;
};

const handleFileUpload = async (e: Event) => {
  const files = (e.target as HTMLInputElement).files;
  if (!files?.length) return;
  isUploading.value = true;
  const fd = new FormData();
  Array.from(files).forEach(f => fd.append('files', f));
  try {
    const res = await axios.post('/api/upload-batch', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    if (res.data.urls) publishForm.value.image_urls.push(...res.data.urls);
  } catch { alert('上传失败'); }
  finally { isUploading.value = false; }
};

const togglePref = (key: string) => {
  const prefs = publishForm.value.adoption_preferences as any;
  prefs[key] = !prefs[key];
};

onMounted(fetchPosts);
</script>

<template>
  <div class="max-w-6xl mx-auto space-y-8 pb-32 px-4 text-gray-900 dark:text-white">
    <!-- 头部导航 -->
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-gray-100 dark:border-white/5 pb-6">
      <div class="space-y-1">
        <h2 class="text-4xl font-black italic tracking-tighter uppercase">宠物 <span class="text-orange-500">社区</span></h2>
        <p class="font-bold text-xs text-gray-400 tracking-widest uppercase">Community & Discovery</p>
      </div>
      <div class="flex gap-4 overflow-x-auto scrollbar-hide">
        <button v-for="t in [{id:'all', n:'全部'}, {id:'daily', n:'日常'}, {id:'experience', n:'攻略'}, {id:'adopt_help', n:'送养'}]"
          :key="t.id" @click="activeType = t.id as any"
          :class="activeType === t.id ? 'text-orange-500 border-b-2 border-orange-500 font-black scale-110' : 'text-gray-400 font-bold'"
          class="text-sm uppercase transition-all px-2 pb-2 whitespace-nowrap">{{ t.n }}</button>
      </div>
    </div>

    <div v-if="isLoading" class="py-20 flex justify-center"><Loader2 class="animate-spin text-orange-500" :size="48" /></div>

    <!-- 帖子列表 -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
      <BaseCard v-for="post in posts.filter(p => activeType === 'all' || p.type === activeType)" :key="post.id" class="!p-0 !bg-white dark:!bg-[#111] overflow-hidden !border-gray-100 dark:!border-white/5 shadow-sm flex flex-col h-full hover:shadow-xl transition-all rounded-2xl">
        <div v-if="authStore.user?.id === post.user_id" class="px-3 py-1.5 bg-gray-50 dark:bg-white/5 border-b border-gray-100 dark:border-white/5 flex justify-between items-center">
          <span class="text-[8px] font-black text-gray-400 uppercase">My Post</span>
          <button @click="startEdit(post)" class="text-blue-500 hover:text-blue-400 text-[10px] font-bold">编辑</button>
        </div>

        <div class="p-3 flex items-center gap-2">
          <div class="w-8 h-8 rounded-full border border-orange-500/10 overflow-hidden shrink-0">
            <img :src="`https://i.pravatar.cc/100?u=${post.username}`" />
          </div>
          <div class="min-w-0">
            <h4 class="font-bold text-xs truncate">{{ post.username }}</h4>
            <p class="text-[8px] text-gray-400">{{ post.create_time }}</p>
          </div>
        </div>

        <div class="relative aspect-square cursor-pointer overflow-hidden" @click="openViewer(post.image_urls ? JSON.parse(post.image_urls) : [post.image_url])">
          <img :src="post.image_url || 'https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=800'" class="w-full h-full object-cover hover:scale-110 transition-transform duration-500" />
        </div>

        <div class="p-3 flex-1 space-y-1">
          <h3 class="text-sm font-black italic tracking-tight line-clamp-1">{{ post.title }}</h3>
          <p class="text-gray-500 dark:text-gray-400 text-[11px] leading-relaxed line-clamp-2">{{ post.content }}</p>
        </div>

        <div class="px-3 py-2 border-t border-gray-100 dark:border-white/5 mt-auto flex items-center justify-between bg-gray-50/50 dark:bg-transparent">
          <div class="flex gap-3">
             <button class="flex items-center gap-1 text-[10px] text-gray-400"><Heart :size="14" /> {{ post.likes }}</button>
             <button class="flex items-center gap-1 text-[10px] text-gray-400"><MessageCircle :size="14" /> {{ post.comment_count }}</button>
          </div>
          <span class="text-[8px] font-black text-gray-300 uppercase tracking-widest">{{ post.type === 'daily' ? '日常' : post.type === 'experience' ? '攻略' : '送养' }}</span>
        </div>
      </BaseCard>
    </div>

    <!-- 浮动发布按钮 -->
    <button @click="showPublishModal = true" class="fixed bottom-10 right-10 w-16 h-16 bg-orange-500 text-white rounded-full flex items-center justify-center shadow-2xl z-50 hover:scale-110 transition-all">
      <Plus :size="32" />
    </button>

    <!-- 发布弹窗 -->
    <Teleport to="body">
      <div v-if="showPublishModal" class="fixed inset-0 z-[500] flex items-center justify-center bg-black/80 backdrop-blur-md px-4">
        <BaseCard class="w-full max-w-xl p-8 relative !bg-white dark:!bg-zinc-900 shadow-2xl max-h-[90vh] overflow-y-auto text-gray-900 dark:text-white">
          <button @click="closeModal" class="absolute top-6 right-6 text-gray-400 hover:text-orange-500"><X :size="24" /></button>
          <h3 class="text-2xl font-black mb-8 italic uppercase tracking-tighter">{{ isEditing ? '编辑发布' : '开启新动态' }}</h3>
          
          <div class="space-y-6">
            <!-- 类型切换 -->
            <div class="grid grid-cols-3 gap-2">
              <button v-for="t in [{id:'daily', n:'动态'}, {id:'experience', n:'攻略'}, {id:'adopt_help', n:'送养'}]" 
                      :key="t.id" @click="publishType = t.id as any"
                      :class="publishType === t.id ? 'bg-orange-500 text-white' : 'bg-gray-100 dark:bg-white/5 text-gray-500'"
                      class="py-2.5 rounded-xl text-xs font-black transition-all">{{ t.n }}</button>
            </div>

            <input v-model="publishForm.title" placeholder="输入一个吸引人的标题..." class="w-full bg-gray-50 dark:bg-white/5 border border-gray-100 dark:border-white/10 rounded-xl px-5 py-4 text-sm outline-none focus:border-orange-500" />
            <textarea v-model="publishForm.content" class="w-full h-28 bg-gray-50 dark:bg-white/5 border border-gray-100 dark:border-white/10 rounded-xl p-5 text-sm outline-none focus:border-orange-500" placeholder="分享点什么吧..."></textarea>

            <!-- 送养专有：强化约束设置 -->
            <div v-if="publishType === 'adopt_help'" class="p-6 bg-orange-500/5 border border-orange-500/20 rounded-[2rem] space-y-6 animate-in fade-in duration-500">
               <p class="text-[10px] font-black text-orange-500 uppercase tracking-widest flex items-center gap-2"><Sparkles :size="14" /> AI 评估前置约束设置</p>
               
               <div class="grid grid-cols-2 gap-4">
                  <div class="space-y-1.5">
                    <label class="text-[9px] font-black text-gray-400 uppercase">宠物名字</label>
                    <input v-model="publishForm.pet_name" class="w-full p-3 bg-white dark:bg-black/20 rounded-xl border-none text-xs font-bold outline-none" placeholder="如：团团" />
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-[9px] font-black text-gray-400 uppercase">品种/类型</label>
                    <input v-model="publishForm.pet_breed" class="w-full p-3 bg-white dark:bg-black/20 rounded-xl border-none text-xs font-bold outline-none" placeholder="如：金毛" />
                  </div>
               </div>

               <div class="grid grid-cols-2 gap-4">
                  <div class="space-y-1.5">
                    <label class="text-[9px] font-black text-gray-400 uppercase">要求预算等级</label>
                    <select v-model="publishForm.adoption_preferences.min_budget_level" class="w-full p-3 bg-white dark:bg-black/20 rounded-xl border-none text-xs font-black">
                       <option value="低">不限 (低)</option>
                       <option value="中">适中 (中)</option>
                       <option value="高">较高 (高)</option>
                    </select>
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-[9px] font-black text-gray-400 uppercase">要求住房类型</label>
                    <select v-model="publishForm.adoption_preferences.required_housing_type" class="w-full p-3 bg-white dark:bg-black/20 rounded-xl border-none text-xs font-black">
                       <option value="公寓">普通公寓</option>
                       <option value="独立住宅">带院子住宅</option>
                       <option value="不限">不限类型</option>
                    </select>
                  </div>
               </div>

               <div class="space-y-3">
                  <p class="text-[9px] font-black text-gray-400 uppercase">排他性约束</p>
                  <div class="flex flex-wrap gap-2">
                     <button v-for="opt in [{k:'forbid_children', l:'不接受幼儿'}, {k:'forbid_other_pets', l:'不接受其他宠物'}, {k:'allow_novice', l:'欢迎新手', inv:true}]" 
                             :key="opt.k" @click="togglePref(opt.k)"
                             :class="publishForm.adoption_preferences[opt.k] ? 'bg-orange-500 text-white' : 'bg-white dark:bg-white/10 text-gray-500'"
                             class="px-4 py-2 rounded-full border border-gray-100 dark:border-white/5 text-[10px] font-bold transition-all">{{ opt.l }}</button>
                  </div>
               </div>

               <div class="space-y-1.5">
                  <label class="text-[9px] font-black text-gray-400 uppercase">送养人备注 (将作为评估依据)</label>
                  <textarea v-model="publishForm.adoption_preferences.special_notes" class="w-full p-3 bg-white dark:bg-black/20 rounded-xl border-none text-[10px] font-bold outline-none" rows="2" placeholder="写下您对领养人最关心的点..."></textarea>
               </div>
            </div>

            <!-- 图片上传 -->
            <div class="grid grid-cols-4 gap-2">
               <div v-for="(url, i) in publishForm.image_urls" :key="i" class="aspect-square rounded-xl overflow-hidden relative group">
                  <img :src="url" class="w-full h-full object-cover" />
                  <button @click="publishForm.image_urls.splice(i,1)" class="absolute inset-0 bg-red-500/80 text-white opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center font-black text-[10px]">删除</button>
               </div>
               <button v-if="publishForm.image_urls.length < 4" @click="fileInput?.click()" class="aspect-square border-2 border-dashed border-gray-100 dark:border-white/10 rounded-xl flex items-center justify-center text-gray-400 hover:border-orange-500 transition-all">
                  <Plus v-if="!isUploading" />
                  <Loader2 v-else class="animate-spin" />
               </button>
               <input type="file" ref="fileInput" class="hidden" multiple @change="handleFileUpload" />
            </div>

            <button @click="handlePublish" :disabled="isPublishing || isUploading" class="w-full py-5 bg-orange-500 text-white rounded-2xl font-black text-lg shadow-xl shadow-orange-500/20 flex items-center justify-center gap-3 active:scale-95 transition-all">
               <Loader2 v-if="isPublishing" class="animate-spin" />
               {{ isEditing ? '保存修改' : '立即发布送养' }}
            </button>
          </div>
        </BaseCard>
      </div>
    </Teleport>

    <!-- 查看器 Teleport 略 -->
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(249, 115, 22, 0.1); border-radius: 10px; }
.scrollbar-hide::-webkit-scrollbar { display: none; }
</style>
