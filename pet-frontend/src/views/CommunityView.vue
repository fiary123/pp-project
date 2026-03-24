<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import {
  MessageCircle, Heart, Plus, X, Loader2, MessageSquare, Edit3, Trash2,
  Upload, Briefcase, Home, Star
} from 'lucide-vue-next';
import { useAuthStore } from '../store/authStore';
import BaseCard from '../components/BaseCard.vue';
import axios from '../api/index';

const authStore = useAuthStore();

// 1. 状态管理
const posts = ref<any[]>([]);
const activeType = ref<'all' | 'daily' | 'experience' | 'adopt_help'>('all');
const isLoading = ref(false);

// 发布与编辑弹窗
const showPublishModal = ref(false);
const isEditing = ref(false);
const editingPostId = ref<number | null>(null);
const publishType = ref<'daily' | 'experience' | 'adopt_help'>('daily');
const publishForm = ref({ title: '', content: '', image_url: '' });
const isPublishing = ref(false);
const isUploading = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

// 评论管理
const activePostComments = ref<Record<number, any[]>>({});
const commentInputs = ref<Record<number, string>>({});
const isSubmittingComment = ref<Record<number, boolean>>({});
const likedPosts = ref<Set<number>>(new Set());

// 用户信息弹窗
const showUserProfile = ref(false);
const profileUser = ref<any>(null);
const isLoadingProfile = ref(false);

const openUserProfile = async (userId: number, fallback: any) => {
  if (!userId || userId >= 9000) return; // 模拟帖子无真实用户
  profileUser.value = fallback;
  showUserProfile.value = true;
  isLoadingProfile.value = true;
  try {
    const res = await axios.get(`/api/user/profile/${userId}`);
    profileUser.value = res.data;
  } catch {
    // 保留 fallback 数据
  } finally {
    isLoadingProfile.value = false;
  }
};

// 判断是否为视频
const isVideo = (url: string) => {
  if (!url) return false;
  return ['.mp4', '.webm', '.ogg', '.mov'].some(ext => url.toLowerCase().endsWith(ext));
};

// 模拟帖子生成器
const generateMockPosts = () => {
  const users = ['猫片达人', '狗狗日记', '宠物百科', '爱宠志愿者', '铲屎官小李'];
  const contents = [
    {
      title: '今天在公园遇到了超可爱的柴犬！',
      content: '今天带我家主子去公园散步，结果遇到了一只超热情的柴犬，两只小可爱玩得不亦乐乎。',
      img: 'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=1200&q=80',
      type: 'daily'
    },
    {
      title: '新手养猫避坑指南',
      content: '作为一名有着5年养猫经验的博主，今天要给各位新手家长排排雷。建议收藏！',
      img: 'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=1200&q=80',
      type: 'experience'
    },
    {
      title: '【急寻领养】温顺橘猫寻找温暖的家',
      content: '在小区楼下发现的小橘，大概3个月大，已做完基础驱虫。性格超级粘人。',
      img: 'https://images.unsplash.com/photo-1548247416-ec66f4900b2e?auto=format&fit=crop&w=1200&q=80',
      type: 'adopt_help'
    }
  ];
  return contents.map((c, i) => ({
    id: 9000 + i,
    user_id: 0,
    username: users[i % users.length],
    role: i % 2 === 0 ? 'org_admin' : 'individual',
    title: c.title,
    content: c.content,
    image_url: c.img,
    type: c.type,
    likes: 12 + i * 5,
    create_time: '2026-03-22 10:00'
  }));
};

// 2. 加载数据
const fetchPosts = async () => {
  isLoading.value = true;
  try {
    const res = await axios.get('/api/posts');
    const dbItems = (res.data && res.data.items) ? res.data.items : (Array.isArray(res.data) ? res.data : []);
    const formattedDbItems = dbItems.map((p: any) => ({
      ...p,
      create_time: p.create_time ? new Date(p.create_time).toLocaleString() : '刚刚'
    }));
    posts.value = formattedDbItems.length > 0
      ? [...formattedDbItems, ...generateMockPosts()]
      : generateMockPosts();
  } catch {
    posts.value = generateMockPosts();
  } finally {
    isLoading.value = false;
  }
};

// 3. 互动逻辑
const handleLike = async (postId: number) => {
  if (likedPosts.value.has(postId)) return;
  const post = posts.value.find(p => p.id === postId);
  if (!post) return;
  post.likes = (post.likes || 0) + 1;
  likedPosts.value.add(postId);
  if (postId < 9000) {
    try { await axios.post(`/api/posts/${postId}/like`); } catch {}
  }
};

const loadComments = async (postId: number) => {
  if (activePostComments.value[postId] !== undefined) {
    delete activePostComments.value[postId];
    return;
  }
  if (postId >= 9000) {
    activePostComments.value[postId] = [];
    return;
  }
  try {
    const res = await axios.get(`/api/posts/${postId}/comments`);
    activePostComments.value[postId] = res.data || [];
  } catch {
    activePostComments.value[postId] = [];
  }
};

const handleSubmitComment = async (postId: number) => {
  const content = commentInputs.value[postId]?.trim();
  if (!content || !authStore.user?.id) return;
  if (postId >= 9000) {
    if (!activePostComments.value[postId]) activePostComments.value[postId] = [];
    activePostComments.value[postId].push({ id: Date.now(), username: authStore.user.username || '我', content });
    commentInputs.value[postId] = '';
    return;
  }
  isSubmittingComment.value[postId] = true;
  try {
    await axios.post('/api/posts/comment', { post_id: postId, user_id: authStore.user.id, content });
    commentInputs.value[postId] = '';
    const res = await axios.get(`/api/posts/${postId}/comments`);
    activePostComments.value[postId] = res.data || [];
  } catch {
    alert('评论发送失败，请重试');
  } finally {
    isSubmittingComment.value[postId] = false;
  }
};

// 4. 文件上传
const triggerUpload = () => fileInput.value?.click();
const handleFileUpload = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  isUploading.value = true;
  try {
    const formData = new FormData();
    formData.append('file', file);
    const res = await axios.post('/api/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
    publishForm.value.image_url = res.data.url;
  } catch (err: any) {
    alert(err.response?.data?.detail || '上传失败，请重试');
  } finally {
    isUploading.value = false;
  }
};

// 5. 管理员与编辑功能
const startEdit = (post: any) => {
  if (post.id >= 9000) { alert('演示贴不支持编辑哦'); return; }
  isEditing.value = true;
  editingPostId.value = post.id;
  publishType.value = post.type;
  publishForm.value = { title: post.title || '', content: post.content, image_url: post.image_url || '' };
  showPublishModal.value = true;
};

const handleDelete = async (postId: number) => {
  if (postId >= 9000) { posts.value = posts.value.filter(p => p.id !== postId); return; }
  if (!confirm('确定要删除这条帖子吗？')) return;
  try {
    await axios.delete(`/api/posts/${postId}`);
    posts.value = posts.value.filter(p => p.id !== postId);
  } catch {}
};

const handlePublish = async () => {
  if (!publishForm.value.content) return;
  isPublishing.value = true;
  try {
    const payload = { user_id: authStore.user?.id, title: publishForm.value.title, content: publishForm.value.content, image_url: publishForm.value.image_url, type: publishType.value };
    if (isEditing.value && editingPostId.value) {
      await axios.put(`/api/posts/${editingPostId.value}`, payload);
    } else {
      await axios.post('/api/posts', payload);
    }
    fetchPosts();
    closeModal();
  } catch (err: any) {
    alert(err.response?.data?.detail || '发布失败');
  } finally {
    isPublishing.value = false;
  }
};

const closeModal = () => {
  showPublishModal.value = false;
  isEditing.value = false;
  editingPostId.value = null;
  publishForm.value = { title: '', content: '', image_url: '' };
};

const filteredPosts = computed(() => {
  if (activeType.value === 'all') return posts.value;
  return posts.value.filter(p => p.type === activeType.value);
});

const isAdmin = computed(() => {
  const role = authStore.user?.role;
  return role === 'org_admin';
});

const roleLabel: Record<string, string> = { individual: '爱宠人士', org_admin: '救助站' };

onMounted(fetchPosts);
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-8 pb-32 px-4">
    <div class="flex items-end justify-between border-b border-white/5 pb-6">
      <div>
        <h2 class="text-4xl font-black text-white italic tracking-tighter uppercase">宠物 <span class="text-orange-500">社区</span></h2>
        <p class="text-gray-400 font-bold text-sm uppercase tracking-widest mt-2">
          {{ isAdmin ? '管理模式已开启' : '记录萌宠点滴，分享养宠干货' }}
        </p>
      </div>
      <div class="flex gap-6">
        <button v-for="t in [{id:'all', n:'全部'}, {id:'daily', n:'日常'}, {id:'experience', n:'攻略'}, {id:'adopt_help', n:'送养'}]"
          :key="t.id" @click="activeType = t.id as any"
          :class="activeType === t.id ? 'text-orange-500 border-b-2 border-orange-500 font-black scale-110' : 'text-gray-500'"
          class="text-base uppercase tracking-widest transition-all px-3 pb-2">{{ t.n }}</button>
      </div>
    </div>

    <div v-if="isLoading" class="py-20 flex justify-center"><Loader2 class="animate-spin text-orange-500" :size="48" /></div>

    <div v-else class="space-y-10">
      <BaseCard v-for="post in filteredPosts" :key="post.id" class="!p-0 overflow-hidden border-white/5 relative">
        <!-- 管理员/本人控制栏 -->
        <div v-if="isAdmin || authStore.user?.id === post.user_id" class="px-6 py-3 bg-white/5 border-b border-white/5 flex justify-between items-center">
          <span class="text-[9px] font-black text-gray-500 uppercase tracking-widest">{{ authStore.user?.id === post.user_id ? '我的帖子' : '内容管理' }}</span>
          <div class="flex gap-3">
            <button @click="startEdit(post)" class="text-blue-400 hover:text-blue-300 text-[10px] font-black uppercase flex items-center gap-1 transition-colors"><Edit3 :size="12" /> 编辑</button>
            <button @click="handleDelete(post.id)" class="text-red-400 hover:text-red-300 text-[10px] font-black uppercase flex items-center gap-1 transition-colors"><Trash2 :size="12" /> 删除</button>
          </div>
        </div>

        <!-- 帖子头部：可点击头像/用户名弹出用户信息 -->
        <div class="p-6 flex items-center gap-4">
          <button @click="openUserProfile(post.user_id, { id: post.user_id, username: post.username, role: post.role })"
            class="w-12 h-12 rounded-full border-2 border-orange-500/20 overflow-hidden hover:border-orange-500 hover:scale-105 transition-all flex-shrink-0 shadow-lg">
            <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${post.username}`" />
          </button>
          <div>
            <h4 class="font-bold text-white text-lg flex items-center gap-2">
              <button @click="openUserProfile(post.user_id, { id: post.user_id, username: post.username, role: post.role })"
                class="hover:text-orange-500 transition-colors">{{ post.username }}</button>
              <span class="text-[10px] bg-orange-500/10 text-orange-500 px-2 py-0.5 rounded border border-orange-500/20 uppercase tracking-wider font-black">
                {{ roleLabel[post.role] || post.role || '用户' }}
              </span>
            </h4>
            <p class="text-xs text-gray-500 font-mono mt-0.5">{{ post.create_time }}</p>
          </div>
        </div>

        <!-- 帖子内容 -->
        <div class="px-8 pb-8 space-y-5">
          <h3 v-if="post.title" class="text-2xl font-black text-white italic tracking-tight">{{ post.title }}</h3>
          <p class="text-gray-300 text-base leading-relaxed whitespace-pre-line">{{ post.content }}</p>
          <div v-if="post.image_url" class="mt-4">
            <video v-if="isVideo(post.image_url)" :src="post.image_url" controls class="rounded-[2.5rem] w-full max-h-[600px] bg-black/40 border border-white/5"></video>
            <img v-else :src="post.image_url" class="rounded-[2.5rem] w-full h-auto max-h-[600px] object-cover border border-white/5 shadow-2xl" />
          </div>
        </div>

        <!-- 互动栏 -->
        <div class="px-8 py-5 bg-white/5 flex items-center gap-12 border-t border-white/5">
          <button @click="handleLike(post.id)"
            :class="likedPosts.has(post.id) ? 'text-red-500' : 'text-gray-500 hover:text-red-500'"
            class="flex items-center gap-3 text-base font-black transition-all group">
            <Heart :size="24" :fill="likedPosts.has(post.id) ? 'currentColor' : 'none'" class="group-hover:scale-110 transition-transform" />
            {{ post.likes }}
          </button>
          <button @click="loadComments(post.id)" class="flex items-center gap-3 text-base font-black text-gray-500 hover:text-blue-500 group">
            <MessageCircle :size="24" class="group-hover:scale-110 transition-transform" />
            评论
            <span v-if="activePostComments[post.id]?.length" class="text-xs text-gray-600">{{ activePostComments[post.id].length }}</span>
          </button>
        </div>

        <!-- 评论区 -->
        <div v-if="activePostComments[post.id] !== undefined" class="bg-black/20 border-t border-white/5">
          <div class="px-8 pt-6 space-y-4">
            <div v-if="activePostComments[post.id].length === 0" class="text-center text-gray-600 text-sm py-4">
              暂无评论，来发表第一条吧 👋
            </div>
            <div v-for="c in activePostComments[post.id]" :key="c.id" class="flex gap-4">
              <div class="w-9 h-9 rounded-full bg-white/5 overflow-hidden flex-shrink-0">
                <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${c.username}`" />
              </div>
              <div class="flex-1 bg-white/5 rounded-2xl px-4 py-3 border border-white/5">
                <p class="text-xs font-black text-orange-500 uppercase mb-1">{{ c.username }}</p>
                <p class="text-sm text-gray-300">{{ c.content }}</p>
              </div>
            </div>
          </div>
          <div class="px-8 py-5 flex gap-3 items-center">
            <div class="w-9 h-9 rounded-full bg-white/5 overflow-hidden flex-shrink-0 border border-white/10">
              <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${authStore.user?.username || 'me'}`" />
            </div>
            <input v-model="commentInputs[post.id]" @keyup.enter="handleSubmitComment(post.id)"
              :placeholder="authStore.user ? '写下你的评论...' : '登录后才能评论'"
              :disabled="!authStore.user"
              class="flex-1 bg-white/5 border border-white/10 rounded-2xl px-5 py-3 text-sm text-white outline-none focus:border-orange-500 transition-colors placeholder-gray-600 disabled:opacity-40" />
            <button @click="handleSubmitComment(post.id)"
              :disabled="!commentInputs[post.id]?.trim() || !authStore.user || isSubmittingComment[post.id]"
              class="px-5 py-3 bg-orange-500 disabled:bg-orange-500/40 text-white text-sm font-black rounded-2xl transition-all flex items-center gap-2">
              <Loader2 v-if="isSubmittingComment[post.id]" class="animate-spin" :size="14" />
              <span v-else>发送</span>
            </button>
          </div>
        </div>
      </BaseCard>
    </div>

    <!-- 发布按钮 -->
    <button @click="showPublishModal = true" class="fixed bottom-12 right-12 w-16 h-16 bg-orange-500 text-white rounded-full flex items-center justify-center shadow-2xl z-50 hover:scale-110 transition-all shadow-orange-500/20">
      <Plus :size="32" />
    </button>

    <!-- 发布/编辑弹窗 -->
    <Teleport to="body">
      <div v-if="showPublishModal" class="fixed inset-0 z-[500] flex items-center justify-center bg-black/95 backdrop-blur-md px-4">
        <BaseCard class="w-full max-w-xl p-10 relative !bg-zinc-900 border-white/10 shadow-2xl">
          <button @click="closeModal" class="absolute top-6 right-6 text-gray-500 hover:text-white transition-colors"><X :size="24"/></button>
          <h3 class="text-3xl font-black text-white mb-10 italic uppercase tracking-tighter">{{ isEditing ? '编辑帖子' : '发布动态' }}</h3>
          <div class="space-y-8">
            <div class="grid grid-cols-3 gap-3">
              <button v-for="t in [{id:'daily', n:'日常分享'}, {id:'experience', n:'养宠攻略'}, {id:'adopt_help', n:'寻主/求助'}]"
                :key="t.id" @click="publishType = t.id as any"
                :class="publishType === t.id ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' : 'bg-white/5 text-gray-500'"
                class="py-4 rounded-xl text-sm font-black uppercase transition-all tracking-widest border border-white/5">
                {{ t.n }}
              </button>
            </div>
            <input v-model="publishForm.title" placeholder="给动态起个吸睛的标题吧 (可选)"
              class="w-full bg-white/5 border border-white/10 rounded-xl px-6 py-5 text-base text-white outline-none focus:border-orange-500 transition-all" />
            <textarea v-model="publishForm.content"
              class="w-full h-48 bg-white/5 border border-white/10 rounded-2xl p-6 text-base text-white outline-none focus:border-orange-500 transition-all leading-relaxed"
              placeholder="这一刻的想法..."></textarea>
            <div class="relative group">
              <div v-if="publishForm.image_url" class="relative rounded-2xl overflow-hidden border border-white/10 aspect-video bg-black/40 shadow-xl">
                <video v-if="isVideo(publishForm.image_url)" :src="publishForm.image_url" class="w-full h-full object-contain"></video>
                <img v-else :src="publishForm.image_url" class="w-full h-full object-cover" />
                <button @click="publishForm.image_url = ''" class="absolute top-4 right-4 p-2 bg-black/60 text-white rounded-full hover:bg-red-500 transition-all opacity-0 group-hover:opacity-100"><X :size="18" /></button>
              </div>
              <div v-else @click="triggerUpload"
                class="w-full py-16 border-2 border-dashed border-white/10 rounded-2xl flex flex-col items-center justify-center gap-4 cursor-pointer hover:border-orange-500/50 hover:bg-white/5 transition-all group">
                <div class="p-5 bg-white/5 rounded-full group-hover:scale-110 transition-all">
                  <Upload v-if="!isUploading" class="text-gray-500 group-hover:text-orange-500" :size="32" />
                  <Loader2 v-else class="text-orange-500 animate-spin" :size="32" />
                </div>
                <div class="text-center">
                  <p class="text-sm font-black text-gray-500 uppercase tracking-widest group-hover:text-gray-300">{{ isUploading ? '正在处理文件...' : '点击上传图片或视频' }}</p>
                  <p class="text-xs text-gray-600 mt-2">支持 JPG, PNG, WebP, MP4, WebM (最大 50MB)</p>
                </div>
              </div>
              <input type="file" ref="fileInput" class="hidden" accept="image/*,video/*" @change="handleFileUpload" />
            </div>
            <button @click="handlePublish" :disabled="isPublishing || isUploading"
              class="w-full bg-orange-500 text-white py-5 rounded-xl font-black text-xl hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex justify-center items-center gap-3 shadow-xl shadow-orange-500/20">
              <Loader2 v-if="isPublishing" class="animate-spin" :size="24" />
              {{ isEditing ? '确认修改' : '立即发布动态' }}
            </button>
          </div>
        </BaseCard>
      </div>
    </Teleport>
  </div>

  <!-- 用户信息弹窗 -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="showUserProfile" class="fixed inset-0 z-[600] flex items-center justify-center bg-black/80 backdrop-blur-md px-4"
        @click.self="showUserProfile = false">
        <div class="bg-[#111] border border-white/10 rounded-[3rem] w-full max-w-sm p-10 space-y-6 relative">
          <button @click="showUserProfile = false" class="absolute top-6 right-6 text-gray-500 hover:text-white transition-colors"><X :size="20" /></button>

          <div v-if="isLoadingProfile" class="flex justify-center py-8">
            <Loader2 class="animate-spin text-orange-500" :size="32" />
          </div>

          <template v-else-if="profileUser">
            <div class="flex flex-col items-center gap-4 text-center">
              <div class="w-20 h-20 rounded-3xl border-2 border-orange-500/30 overflow-hidden shadow-xl">
                <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${profileUser.username}`" class="w-full h-full" />
              </div>
              <div>
                <h3 class="text-2xl font-black text-white">{{ profileUser.username }}</h3>
                <span class="text-[10px] bg-orange-500/10 text-orange-500 px-2 py-0.5 rounded border border-orange-500/20 uppercase font-black mt-1 inline-block">
                  {{ roleLabel[profileUser.role] || profileUser.role || '用户' }}
                </span>
              </div>
            </div>

            <div class="space-y-3">
              <div v-if="profileUser.occupation" class="flex items-center gap-3 text-sm text-gray-400">
                <Briefcase class="text-orange-500 flex-shrink-0" :size="16" />
                <span>{{ profileUser.occupation }}</span>
              </div>
              <div v-if="profileUser.living_env" class="flex items-center gap-3 text-sm text-gray-400">
                <Home class="text-orange-500 flex-shrink-0" :size="16" />
                <span>{{ profileUser.living_env }}</span>
              </div>
              <div v-if="profileUser.preference" class="flex items-center gap-3 text-sm text-gray-400">
                <Star class="text-orange-500 flex-shrink-0" :size="16" />
                <span>偏好：{{ profileUser.preference }}</span>
              </div>
              <div v-if="!profileUser.occupation && !profileUser.living_env && !profileUser.preference"
                class="text-center text-gray-600 text-sm py-2">该用户暂未填写个人资料</div>
            </div>

            <div class="flex gap-3 pt-2">
              <button v-if="authStore.user && authStore.user.id !== profileUser.id"
                @click="$router.push(`/chat?to=${profileUser.id}`); showUserProfile = false"
                class="flex-1 bg-orange-500 hover:bg-orange-600 text-white py-4 rounded-2xl font-black flex items-center justify-center gap-2 transition-all">
                <MessageSquare :size="18" /> 发私信
              </button>
              <button @click="showUserProfile = false"
                class="flex-1 bg-white/10 hover:bg-white/20 text-white py-4 rounded-2xl font-black transition-all">
                关闭
              </button>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* @reference "tailwindcss"; */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
