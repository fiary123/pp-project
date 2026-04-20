<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import {
  MessageCircle, Heart, Plus, X, Loader2,
  Upload, ChevronLeft, ChevronRight
} from 'lucide-vue-next';
import { useAuthStore } from '../store/authStore';
import BaseCard from '../components/BaseCard.vue';
import axios from '../api/index';

const authStore = useAuthStore();

const defaultAdoptionPreferences = {
  hard_preferences: [] as string[],
  soft_preferences: ['住房稳定', '陪伴时间', '责任意识'],
  allow_novice: true,
  accept_renting: true,
  require_stable_housing: false,
  require_financial_capacity: false,
  require_followup_updates: false,
  prefer_local: false,
  require_family_agreement: false,
  prefer_quiet_household: false,
  prefer_multi_pet_experience: false,
  focus_experience: false,
  focus_companionship: true,
  focus_stability: true,
  risk_tolerance: 'medium'
};

const parseAdoptionPreferences = (raw: unknown) => {
  if (!raw) return { ...defaultAdoptionPreferences };
  if (typeof raw === 'string') {
    try {
      return { ...defaultAdoptionPreferences, ...(JSON.parse(raw) as Record<string, unknown>) };
    } catch {
      return { ...defaultAdoptionPreferences };
    }
  }
  return { ...defaultAdoptionPreferences, ...(raw as Record<string, unknown>) };
};

const requirementOptions = [
  { key: 'allow_novice', label: '接受新手' },
  { key: 'accept_renting', label: '接受租房' },
  { key: 'prefer_local', label: '优先同城' },
  { key: 'require_family_agreement', label: '需家人同意' },
  { key: 'require_stable_housing', label: '稳定住房' },
  { key: 'require_financial_capacity', label: '预算能力' }
] as const;

// 1. 状态管理
const posts = ref<any[]>([]);
const activeType = ref<'all' | 'daily' | 'experience' | 'adopt_help'>('all');
const isLoading = ref(false);

// 发布与编辑弹窗
const showPublishModal = ref(false);
const isEditing = ref(false);
const editingPostId = ref<number | null>(null);
const publishType = ref<'daily' | 'experience' | 'adopt_help'>('daily');
const publishForm = ref({
  title: '', content: '',
  image_urls: [] as string[],
  pet_name: '', pet_gender: '', pet_age: '', pet_breed: '', adopt_reason: '', location: '',
  adoption_preferences: { ...defaultAdoptionPreferences }
});
const isPublishing = ref(false);
const isUploading = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

// 图片查看器
const viewerImages = ref<string[]>([]);
const viewerIndex = ref(0);
const showViewer = ref(false);
const openViewer = (imgs: string[], idx = 0) => { viewerImages.value = imgs; viewerIndex.value = idx; showViewer.value = true; };

// 评论管理
const activePostComments = ref<Record<number, any[]>>({});
const commentInputs = ref<Record<number, string>>({});
const isSubmittingComment = ref<Record<number, boolean>>({});
const likedPosts = ref<Set<number>>(new Set());
const MOCK_COMMENT_STORAGE_KEY = 'community_mock_comments_v2';

const readMockComments = (): Record<number, any[]> => {
  try {
    const raw = localStorage.getItem(MOCK_COMMENT_STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
};

const writeMockComments = (commentsMap: Record<number, any[]>) => {
  localStorage.setItem(MOCK_COMMENT_STORAGE_KEY, JSON.stringify(commentsMap));
};

const getStoredMockComments = (postId: number) => {
  const commentsMap = readMockComments();
  if (commentsMap[postId]) return commentsMap[postId];
  if (postId >= 9000) {
    return [
      { id: 10001, username: '小林同学', content: '这也太可爱了吧！我也想养一只。', create_time: '2026-03-27 10:20' },
      { id: 10002, username: '家有恶犬', content: '哈哈，这种性格真的很适合新手。', create_time: '2026-03-27 11:45' }
    ].slice(0, (postId % 2) + 1);
  }
  return [];
};

// 用户信息弹窗
const showUserProfile = ref(false);
const profileUser = ref<any>(null);
const isLoadingProfile = ref(false);

const openUserProfile = async (userId: number, fallback: any) => {
  profileUser.value = fallback;
  showUserProfile.value = true;
  if (!userId || userId >= 9000) return;
  isLoadingProfile.value = true;
  try {
    const res = await axios.get(`/api/user/profile/${userId}`);
    profileUser.value = res.data;
  } catch { /* use fallback */ }
  finally { isLoadingProfile.value = false; }
};

const isVideo = (url: string) => ['.mp4', '.webm', '.mov'].some(ext => (url || '').toLowerCase().endsWith(ext));

const toggleAdoptionPreference = (key: string) => {
  const prefs = publishForm.value.adoption_preferences as any;
  prefs[key] = !prefs[key];
};

// 模拟数据生成
const generateMockPosts = () => {
  const users = [
    { n: '猫片达人', r: 'user' }, { n: '狗狗日记', r: 'user' },
    { n: '宠物百科', r: 'admin' }, { n: '爱宠志愿者', r: 'admin' }
  ];
  const contents = [
    { title: '今天在公园遇到了超可爱的柴犬', content: '今天带我家主子去公园散步，柴犬的主人还分享了好多遛狗的心得，收获满满的一天！', img: 'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=800', type: 'daily' },
    { title: '我家猫不爱吃猫罐头正常吗？', content: '求助各位资深家长！我家主子快1岁了，最近突然对罐头失去了兴趣，只吃干粮。这属于挑食吗？', img: 'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=800', type: 'experience' },
    { title: '【急寻领养】温顺橘猫寻找温暖的家', content: '在小区楼下发现的小橘，性格超级粘人。希望能找一个能科学喂养、不离不弃的家庭。', img: 'https://images.unsplash.com/photo-1548247416-ec66f4900b2e?w=800', type: 'adopt_help' }
  ];
  return contents.map((c, i) => ({
    id: 9000 + i, user_id: 0, username: users[i % users.length].n, role: users[i % users.length].r,
    title: c.title, content: c.content, image_url: c.img, image_urls: JSON.stringify([c.img]),
    type: c.type, likes: 10 + i, create_time: '2026-04-10', comment_count: 2,
    adoption_preferences: c.type === 'adopt_help' ? defaultAdoptionPreferences : null
  }));
};

const fetchPosts = async () => {
  isLoading.value = true;
  try {
    const res = await axios.get('/api/posts');
    const dbItems = Array.isArray(res.data) ? res.data : (res.data?.items || []);
    posts.value = [...dbItems.map((p: any) => ({
      ...p,
      adoption_preferences: parseAdoptionPreferences(p.adoption_preferences),
      create_time: p.create_time ? new Date(p.create_time).toLocaleString() : '刚刚'
    })), ...generateMockPosts()];
  } catch {
    posts.value = generateMockPosts();
  } finally { isLoading.value = false; }
};

const handleLike = async (postId: number) => {
  if (likedPosts.value.has(postId)) return;
  const post = posts.value.find(p => p.id === postId);
  if (!post) return;
  post.likes++;
  likedPosts.value.add(postId);
  if (postId < 9000) axios.post(`/api/posts/${postId}/like`).catch(() => {});
};

const loadComments = async (postId: number) => {
  if (activePostComments.value[postId]) { delete activePostComments.value[postId]; return; }
  if (postId >= 9000) { activePostComments.value[postId] = getStoredMockComments(postId); return; }
  try {
    const res = await axios.get(`/api/posts/${postId}/comments`);
    activePostComments.value[postId] = res.data || [];
  } catch { activePostComments.value[postId] = []; }
};

const handleSubmitComment = async (postId: number) => {
  const content = commentInputs.value[postId]?.trim();
  if (!content || !authStore.user) return;
  const newComment = { id: Date.now(), username: authStore.user.username, content, create_time: '刚刚' };
  
  if (postId >= 9000) {
    const next = [...(activePostComments.value[postId] || []), newComment];
    activePostComments.value[postId] = next;
    const map = readMockComments(); map[postId] = next; writeMockComments(map);
    commentInputs.value[postId] = '';
    return;
  }
  try {
    await axios.post('/api/posts/comment', { post_id: postId, user_id: authStore.user.id, content });
    commentInputs.value[postId] = '';
    const res = await axios.get(`/api/posts/${postId}/comments`);
    activePostComments.value[postId] = res.data || [];
  } catch { alert('评论失败'); }
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

const removeImage = (i: number) => publishForm.value.image_urls.splice(i, 1);

const startEdit = (post: any) => {
  if (post.id >= 9000) return alert('演示贴不支持编辑');
  isEditing.value = true;
  editingPostId.value = post.id;
  publishType.value = post.type;
  publishForm.value = {
    title: post.title || '', content: post.content,
    image_urls: post.image_urls ? JSON.parse(post.image_urls) : (post.image_url ? [post.image_url] : []),
    pet_name: post.pet_name || '', pet_gender: post.pet_gender || '',
    pet_age: post.pet_age || '', pet_breed: post.pet_breed || '',
    adopt_reason: post.adopt_reason || '', location: post.location || '',
    adoption_preferences: parseAdoptionPreferences(post.adoption_preferences)
  };
  showPublishModal.value = true;
};

const handleDelete = async (id: number) => {
  if (id >= 9000) { posts.value = posts.value.filter(p => p.id !== id); return; }
  if (!confirm('确定删除吗？')) return;
  try { await axios.delete(`/api/posts/${id}`); posts.value = posts.value.filter(p => p.id !== id); } catch {}
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
  publishForm.value = { title: '', content: '', image_urls: [], pet_name: '', pet_gender: '', pet_age: '', pet_breed: '', adopt_reason: '', location: '', adoption_preferences: { ...defaultAdoptionPreferences } };
};

const filteredPosts = computed(() => activeType.value === 'all' ? posts.value : posts.value.filter(p => p.type === activeType.value));
const isAdmin = computed(() => authStore.user?.role === 'admin');
const roleLabel: Record<string, string> = { user: '爱宠人士', admin: '救助站' };

onMounted(fetchPosts);
</script>

<template>
  <div class="max-w-6xl mx-auto space-y-8 pb-32 px-4 text-gray-900 dark:text-white">
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-gray-200 dark:border-white/5 pb-6">
      <div>
        <h2 class="text-4xl font-black italic tracking-tighter uppercase">宠物 <span class="text-orange-500">社区</span></h2>
        <p class="font-bold text-sm text-gray-500 uppercase tracking-widest mt-2">
          {{ isAdmin ? '管理模式已开启' : '记录萌宠点滴，分享养宠干货' }}
        </p>
      </div>
      <div class="flex gap-6 overflow-x-auto scrollbar-hide">
        <button v-for="t in [{id:'all', n:'全部'}, {id:'daily', n:'日常'}, {id:'experience', n:'攻略'}, {id:'adopt_help', n:'送养'}]"
          :key="t.id" @click="activeType = t.id as any"
          :class="activeType === t.id ? 'text-orange-500 border-b-2 border-orange-500 font-black scale-110' : 'text-gray-500'"
          class="text-base uppercase tracking-widest transition-all px-3 pb-2 whitespace-nowrap">{{ t.n }}</button>
      </div>
    </div>

    <div v-if="isLoading" class="py-20 flex justify-center"><Loader2 class="animate-spin text-orange-500" :size="48" /></div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
      <BaseCard v-for="post in filteredPosts" :key="post.id" class="!p-0 !bg-white dark:!bg-[#111] overflow-hidden !border-gray-100 dark:!border-white/5 shadow-sm flex flex-col h-full hover:shadow-xl transition-all duration-300 rounded-2xl">
        <div v-if="isAdmin || (authStore.user && authStore.user.id === post.user_id)" class="px-3 py-1.5 bg-gray-50 dark:bg-white/5 border-b border-gray-100 dark:border-white/5 flex justify-between items-center">
          <span class="text-[8px] font-black text-gray-400 uppercase">{{ authStore.user?.id === post.user_id ? 'MINE' : 'ADMIN' }}</span>
          <div class="flex gap-2">
            <button @click="startEdit(post)" class="text-blue-500 hover:text-blue-400 text-[10px] font-bold">编辑</button>
            <button @click="handleDelete(post.id)" class="text-red-500 hover:text-red-400 text-[10px] font-bold">删除</button>
          </div>
        </div>

        <div class="p-3 flex items-center gap-2">
          <div @click="openUserProfile(post.user_id, post)" class="w-8 h-8 rounded-full border border-orange-500/10 overflow-hidden cursor-pointer shrink-0">
            <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${post.username}`" />
          </div>
          <div class="min-w-0">
            <h4 class="font-bold text-xs truncate flex items-center gap-1.5">
              <span @click="openUserProfile(post.user_id, post)" class="hover:text-orange-500 cursor-pointer">{{ post.username }}</span>
            </h4>
            <p class="text-[8px] text-gray-400">{{ post.create_time }}</p>
          </div>
        </div>

        <div class="relative aspect-square cursor-pointer overflow-hidden bg-gray-50 dark:bg-white/5" @click="openViewer(post.image_urls ? JSON.parse(post.image_urls) : [post.image_url])">
          <video v-if="isVideo(post.image_url)" :src="post.image_url" class="w-full h-full object-cover" />
          <img v-else :src="post.image_url || 'https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=800'" class="w-full h-full object-cover hover:scale-110 transition-transform duration-500" />
        </div>

        <div class="p-3 flex-1 space-y-1">
          <h3 class="text-sm font-black italic tracking-tight line-clamp-1">{{ post.title }}</h3>
          <p class="text-gray-500 dark:text-gray-400 text-[11px] leading-relaxed line-clamp-2">{{ post.content }}</p>
        </div>

        <div class="px-3 py-2 bg-gray-50/50 dark:bg-white/[0.01] flex items-center justify-between border-t border-gray-100 dark:border-white/5 mt-auto">
          <div class="flex gap-3">
            <button @click="handleLike(post.id)" :class="likedPosts.has(post.id) ? 'text-red-500' : 'text-gray-400 hover:text-red-500'" class="flex items-center gap-1 text-[10px] font-bold transition-all">
              <Heart :size="14" :fill="likedPosts.has(post.id) ? 'currentColor' : 'none'" /> {{ post.likes }}
            </button>
            <button @click="loadComments(post.id)" class="flex items-center gap-1 text-[10px] font-bold text-gray-400 hover:text-blue-500">
              <MessageCircle :size="14" /> {{ post.comment_count }}
            </button>
          </div>
          <span class="text-[8px] font-black text-gray-300 uppercase">{{ post.type === 'daily' ? '日常' : post.type === 'experience' ? '攻略' : '送养' }}</span>
        </div>

        <div v-if="activePostComments[post.id]" class="bg-slate-100/80 dark:bg-black/20 border-t border-slate-200 dark:border-white/5 p-4 space-y-3">
          <div class="max-h-40 overflow-y-auto space-y-2 custom-scrollbar">
            <div v-for="c in activePostComments[post.id]" :key="c.id" class="text-xs">
              <span class="font-black text-orange-500 mr-1">{{ c.username }}:</span>
              <span class="text-gray-600 dark:text-gray-400">{{ c.content }}</span>
            </div>
          </div>
          <div class="flex gap-2">
            <input v-model="commentInputs[post.id]" @keyup.enter="handleSubmitComment(post.id)" placeholder="说点什么..." class="flex-1 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-lg px-3 py-2 text-xs outline-none focus:border-orange-500" />
            <button @click="handleSubmitComment(post.id)" class="text-orange-500 font-black text-xs uppercase">发送</button>
          </div>
        </div>
      </BaseCard>
    </div>

    <button @click="showPublishModal = true" class="fixed bottom-10 right-10 w-16 h-16 bg-orange-500 text-white rounded-full flex items-center justify-center shadow-2xl z-50 hover:scale-110 transition-all shadow-orange-500/20">
      <Plus :size="32" />
    </button>

    <Teleport to="body">
      <div v-if="showPublishModal" class="fixed inset-0 z-[500] flex items-center justify-center bg-black/80 backdrop-blur-md px-4">
        <BaseCard class="w-full max-w-xl p-8 relative !bg-white dark:!bg-zinc-900 shadow-2xl max-h-[90vh] overflow-y-auto text-gray-900 dark:text-white">
          <button @click="closeModal" class="absolute top-6 right-6 text-gray-400 hover:text-orange-500"><X :size="24" /></button>
          <h3 class="text-3xl font-black mb-8 italic uppercase tracking-tighter">{{ isEditing ? '编辑帖子' : '发布动态' }}</h3>
          <div class="space-y-6">
            <div class="grid grid-cols-3 gap-3">
              <button v-for="t in [{id:'daily', n:'日常'}, {id:'experience', n:'攻略'}, {id:'adopt_help', n:'送养'}]" :key="t.id" @click="publishType = t.id as any" :class="publishType === t.id ? 'bg-orange-500 text-white shadow-lg' : 'bg-gray-100 dark:bg-white/5 text-gray-500'" class="py-3 rounded-xl text-xs font-black uppercase transition-all tracking-widest">{{ t.n }}</button>
            </div>
            <input v-model="publishForm.title" placeholder="标题 (可选)" class="w-full bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl px-5 py-4 text-sm outline-none focus:border-orange-500 transition-all" />
            <textarea v-model="publishForm.content" class="w-full h-32 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl p-5 text-sm outline-none focus:border-orange-500 transition-all leading-relaxed" placeholder="这一刻的想法..."></textarea>

            <div v-if="publishType === 'adopt_help'" class="bg-orange-500/5 border border-orange-500/20 rounded-2xl p-5 space-y-4">
              <p class="text-[10px] font-black text-orange-500 uppercase tracking-widest">宠物信息与要求</p>
              <div class="grid grid-cols-2 gap-3">
                <input v-model="publishForm.pet_name" placeholder="宠物名字" class="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-3 text-xs outline-none" />
                <input v-model="publishForm.pet_breed" placeholder="品种" class="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-3 text-xs outline-none" />
              </div>
              <div class="flex flex-wrap gap-2">
                <button v-for="item in requirementOptions" :key="item.key" @click="toggleAdoptionPreference(item.key)" :class="publishForm.adoption_preferences[item.key] ? 'bg-orange-500 text-white border-orange-500' : 'bg-white dark:bg-white/5 text-gray-500'" class="rounded-full border px-3 py-1.5 text-[10px] font-bold transition-all">{{ item.label }}</button>
              </div>
            </div>

            <div class="grid grid-cols-3 gap-2">
              <div v-for="(url, idx) in publishForm.image_urls" :key="idx" class="relative group aspect-square rounded-xl overflow-hidden shadow-sm">
                <img :src="url" class="w-full h-full object-cover" />
                <button @click="removeImage(idx)" class="absolute inset-0 bg-red-500/80 text-white opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center font-black">删除</button>
              </div>
              <div v-if="publishForm.image_urls.length < 9" @click="fileInput?.click()" class="aspect-square rounded-xl border-2 border-dashed border-gray-200 dark:border-white/10 flex flex-col items-center justify-center cursor-pointer hover:border-orange-500/50 transition-all text-gray-400">
                <Loader2 v-if="isUploading" class="animate-spin" />
                <Plus v-else />
                <span class="text-[8px] mt-1 font-black">上传</span>
              </div>
              <input type="file" ref="fileInput" class="hidden" multiple @change="handleFileUpload" />
            </div>

            <button @click="handlePublish" :disabled="isPublishing || isUploading" class="w-full bg-orange-500 text-white py-5 rounded-2xl font-black text-lg hover:bg-orange-600 disabled:opacity-50 transition-all shadow-xl shadow-orange-500/20 flex justify-center items-center gap-3">
              <Loader2 v-if="isPublishing" class="animate-spin" /> {{ isEditing ? '保存修改' : '立即发布' }}
            </button>
          </div>
        </BaseCard>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showViewer" class="fixed inset-0 z-[700] flex items-center justify-center bg-black/95 px-4" @click.self="showViewer = false">
        <button @click="showViewer = false" class="absolute top-8 right-8 text-white hover:text-orange-500"><X :size="32" /></button>
        <button v-if="viewerIndex > 0" @click="viewerIndex--" class="absolute left-8 text-white hover:text-orange-500"><ChevronLeft :size="48" /></button>
        <img :src="viewerImages[viewerIndex]" class="max-w-full max-h-[85vh] object-contain rounded-xl shadow-2xl" />
        <button v-if="viewerIndex < viewerImages.length - 1" @click="viewerIndex++" class="absolute right-8 text-white hover:text-orange-500"><ChevronRight :size="48" /></button>
      </div>
    </Teleport>

    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showUserProfile && profileUser" class="fixed inset-0 z-[600] flex items-center justify-center bg-black/80 backdrop-blur-md" @click.self="showUserProfile = false">
          <div class="bg-white dark:bg-[#111] border border-gray-200 dark:border-white/10 rounded-[2.5rem] w-full max-w-sm p-10 space-y-8 text-center text-gray-900 dark:text-white">
            <div class="w-24 h-24 rounded-[2rem] border-4 border-orange-500/20 overflow-hidden mx-auto shadow-2xl">
              <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${profileUser.username}`" />
            </div>
            <div>
              <h3 class="text-3xl font-black italic">{{ profileUser.username }}</h3>
              <span class="px-3 py-1 bg-orange-500/10 text-orange-500 rounded-full text-xs font-black uppercase mt-2 inline-block">{{ roleLabel[profileUser.role] || '爱宠人士' }}</span>
            </div>
            <div class="flex gap-4">
              <button v-if="authStore.user && authStore.user.id !== profileUser.id" @click="$router.push(`/chat?to=${profileUser.id}`)" class="flex-1 bg-orange-500 text-white py-4 rounded-2xl font-black shadow-lg">私信交流</button>
              <button @click="showUserProfile = false" class="flex-1 bg-gray-100 dark:bg-white/10 py-4 rounded-2xl font-black">返回社区</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(249, 115, 22, 0.2); border-radius: 10px; }
</style>
