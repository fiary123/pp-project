<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import {
  MessageCircle, Heart, Plus, X, Loader2, MessageSquare, Edit3, Trash2,
  User, Send, Briefcase, Home, Star
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

// 评论管理
const activePostComments = ref<Record<number, any[]>>({});

// 用户信息弹窗
const showUserProfile = ref(false);
const profileUser = ref<any>(null);
const isLoadingProfile = ref(false);

const openUserProfile = async (userId: number, fallback: any) => {
  if (!userId || userId >= 1000) return; // 模拟帖子无真实用户
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
      content: '作为一名有着5年养猫经验的博主，今天要给各位新手家长排排雷。', 
      img: 'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=1200&q=80', 
      type: 'experience' 
    },
    { 
      title: '【急寻领养】温顺橘猫寻找温暖的家', 
      content: '在小区楼下发现的小橘，大概3个月大，已做完基础驱虫。性格超级粘人。', 
      img: 'https://images.unsplash.com/photo-1548247416-ec66f4900b2e?auto=format&fit=crop&w=1200&q=80', 
      type: 'adopt_help' 
    },
    { 
      title: '自制宠物零食：鸡肉干教程', 
      content: '步骤很简单：1. 鸡胸肉切薄片；2. 烘干机70度烘干8小时。', 
      img: 'https://images.unsplash.com/photo-1601758228041-f3b2795255f1?auto=format&fit=crop&w=1200&q=80', 
      type: 'experience' 
    }
  ];

  return contents.map((c, i) => ({
    id: 1000 + i,
    user_id: 99 + i,
    username: users[i % users.length],
    role: i % 2 === 0 ? '达人' : '个人',
    title: c.title,
    content: c.content,
    image_url: c.img,
    type: c.type,
    likes: 12 + i * 5,
    comments_count: 5 + i,
    create_time: '2026-03-04 10:00'
  }));
};

// 2. 加载数据
const fetchPosts = async () => {
  console.log('[DEBUG] 当前用户信息:', authStore.user);
  isLoading.value = true;
  try {
    const res = await axios.get('/api/posts');
    if (res.data && res.data.length > 0) {
      posts.value = res.data.map((p: any) => ({
        ...p,
        likes: p.likes || Math.floor(Math.random() * 20),
        create_time: p.create_time ? new Date(p.create_time).toLocaleString() : '刚刚'
      }));
    } else {
      posts.value = generateMockPosts();
    }
  } catch (err) {
    posts.value = generateMockPosts();
  } finally {
    isLoading.value = false;
  }
};

// 3. 互动逻辑
const handleLike = async (postId: number) => {
  try {
    const post = posts.value.find(p => p.id === postId);
    if (post) {
      post.likes = (post.likes || 0) + 1;
      await axios.post(`/api/posts/${postId}/like`).catch(() => {});
    }
  } catch (err) {}
};

const loadComments = async (postId: number) => {
  if (activePostComments.value[postId]) {
    delete activePostComments.value[postId];
    return;
  }
  try {
    const res = await axios.get(`/api/posts/${postId}/comments`);
    activePostComments.value[postId] = res.data.length ? res.data : [{ id: 1, username: '系统', content: '快来发表第一条评论吧！' }];
  } catch (err) {
    activePostComments.value[postId] = [{ id: 1, username: '小萌新', content: '前排围观！' }];
  }
};


// 4. 管理员功能
const startEdit = (post: any) => {
  isEditing.value = true;
  editingPostId.value = post.id;
  publishType.value = post.type;
  publishForm.value = { title: post.title || '', content: post.content, image_url: post.image_url || '' };
  showPublishModal.value = true;
};

const handleDelete = async (postId: number) => {
  if (!confirm('确定要删除这条帖子吗？')) return;
  try {
    await axios.delete(`/api/posts/${postId}`);
    posts.value = posts.value.filter(p => p.id !== postId);
  } catch (err: any) {
    if (postId >= 1000 || err.response?.status === 404) {
      posts.value = posts.value.filter(p => p.id !== postId);
    }
  }
};

// 5. 提交逻辑
const handlePublish = async () => {
  if (!publishForm.value.content) return;
  isPublishing.value = true;
  try {
    if (isEditing.value && editingPostId.value) {
      try {
        await axios.put(`/api/posts/${editingPostId.value}`, { ...publishForm.value, type: publishType.value });
      } catch (err: any) {
        if (editingPostId.value < 1000 && err.response?.status !== 404) throw err;
      }
      const idx = posts.value.findIndex(p => p.id === editingPostId.value);
      if (idx !== -1) posts.value[idx] = { ...posts.value[idx], ...publishForm.value, type: publishType.value };
    } else {
      await axios.post('/api/posts', { user_id: authStore.user?.id || 1, type: publishType.value, ...publishForm.value });
      fetchPosts();
    }
  } catch (err) {
    if (!isEditing.value) {
      posts.value.unshift({ id: Date.now(), username: authStore.user?.username || '本地用户', role: '个人', ...publishForm.value, type: publishType.value, likes: 0, create_time: '刚刚' });
    }
  } finally {
    closeModal();
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

// 计算属性：判断是否为管理员
const isAdmin = computed(() => {
  const role = authStore.user?.role;
  return role === 'admin' || role === 'root';
});

onMounted(fetchPosts);
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-8 pb-32 px-4">
    <div class="flex items-end justify-between border-b border-white/5 pb-6">
      <div>
        <h2 class="text-4xl font-black text-white italic tracking-tighter uppercase">宠物 <span class="text-orange-500">社区</span></h2>
        <p class="text-gray-400 font-bold text-[10px] uppercase tracking-widest mt-1">
          {{ isAdmin ? '超级管理员模式已开启' : '记录萌宠点滴，分享养宠干货' }}
        </p>
      </div>
      <div class="flex gap-4">
        <button v-for="t in [{id:'all', n:'全部'}, {id:'daily', n:'日常'}, {id:'experience', n:'攻略'}, {id:'adopt_help', n:'互助'}]" 
                :key="t.id" @click="activeType = t.id as any"
                :class="activeType === t.id ? 'text-orange-500 border-b-2 border-orange-500 font-black' : 'text-gray-500'"
                class="text-xs uppercase tracking-widest transition-all px-2 pb-1">{{ t.n }}</button>
      </div>
    </div>

    <div v-if="isLoading" class="py-20 flex justify-center"><Loader2 class="animate-spin text-orange-500" :size="48" /></div>
    
    <div v-else class="space-y-10">
      <BaseCard v-for="post in filteredPosts" :key="post.id" class="!p-0 overflow-hidden border-white/5 relative">
        <!-- 管理员面板：常驻显示 -->
        <div v-if="isAdmin" class="px-6 py-3 bg-orange-500/10 border-b border-orange-500/20 flex justify-between items-center">
          <span class="text-[9px] font-black text-orange-500 uppercase tracking-widest">管理员控制面板</span>
          <div class="flex gap-3">
            <button @click="startEdit(post)" class="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/20 text-blue-400 hover:bg-blue-500 hover:text-white rounded-lg border border-blue-500/30 transition-all text-[10px] font-black uppercase">
              <Edit3 :size="12" /> 编辑
            </button>
            <button @click="handleDelete(post.id)" class="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/20 text-red-400 hover:bg-red-500 hover:text-white rounded-lg border border-red-500/30 transition-all text-[10px] font-black uppercase">
              <Trash2 :size="12" /> 删除
            </button>
          </div>
        </div>

        <!-- 头部 -->
        <div class="p-6 flex items-center justify-between">
          <div class="flex items-center gap-4">
            <button @click="openUserProfile(post.user_id, { id: post.user_id, username: post.username, role: post.role })"
              class="w-10 h-10 rounded-full border-2 border-orange-500/20 overflow-hidden hover:border-orange-500 transition-all hover:scale-110 flex-shrink-0">
              <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${post.username}`" />
            </button>
            <div>
              <h4 class="font-bold text-white text-sm flex items-center gap-2">
                <button @click="openUserProfile(post.user_id, { id: post.user_id, username: post.username, role: post.role })"
                  class="hover:text-orange-500 transition-colors">{{ post.username }}</button>
                <span class="text-[8px] bg-orange-500/10 text-orange-500 px-1.5 py-0.5 rounded border border-orange-500/20 uppercase">
                  {{ ({individual:'爱宠人士',org_admin:'救助站',root:'管理员'} as Record<string,string>)[post.role] || post.role }}
                </span>
              </h4>
              <p class="text-[10px] text-gray-600 font-mono mt-0.5">{{ post.create_time }}</p>
            </div>
          </div>
        </div>

        <!-- 内容 -->
        <div class="px-8 pb-6 space-y-4">
          <h3 v-if="post.title" class="text-2xl font-black text-white italic tracking-tight">{{ post.title }}</h3>
          <p class="text-gray-300 text-sm leading-relaxed whitespace-pre-line">{{ post.content }}</p>
          <img v-if="post.image_url" :src="post.image_url" class="rounded-[2.5rem] w-full h-auto max-h-[600px] object-cover border border-white/5" />
        </div>

        <!-- 互动栏 -->
        <div class="px-8 py-4 bg-white/5 flex items-center gap-10">
          <button @click="handleLike(post.id)" class="flex items-center gap-2 text-xs font-bold transition-all text-gray-500 hover:text-red-500">
            <Heart :size="20" /> {{ post.likes }}
          </button>
          <button @click="loadComments(post.id)" class="flex items-center gap-2 text-xs font-bold text-gray-500 hover:text-blue-500">
            <MessageCircle :size="20" /> 评论
          </button>
        </div>

        <!-- 评论列表 -->
        <div v-if="activePostComments[post.id]" class="bg-black/20 p-8 space-y-6 border-t border-white/5">
          <div v-for="c in activePostComments[post.id]" :key="c.id" class="flex gap-4">
            <div class="w-8 h-8 rounded-full bg-white/5 overflow-hidden"><img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${c.username}`" /></div>
            <div class="flex-1 bg-white/5 rounded-2xl p-4 border border-white/5">
              <p class="text-[10px] font-black text-orange-500 uppercase mb-1">{{ c.username }}</p>
              <p class="text-xs text-gray-300">{{ c.content }}</p>
            </div>
          </div>
        </div>
      </BaseCard>
    </div>

    <!-- 发布/编辑弹窗 -->
    <button @click="showPublishModal = true" class="fixed bottom-12 right-12 w-16 h-16 bg-orange-500 text-white rounded-full flex items-center justify-center shadow-2xl z-50 hover:scale-110 transition-all"><Plus :size="32" /></button>
    <Teleport to="body">
      <div v-if="showPublishModal" class="fixed inset-0 z-[500] flex items-center justify-center bg-black/95 backdrop-blur-md px-4">
        <BaseCard class="w-full max-w-xl p-10 relative">
          <button @click="closeModal" class="absolute top-6 right-6 text-gray-500"><X :size="24"/></button>
          <h3 class="text-2xl font-black text-white mb-8 italic uppercase tracking-tighter">{{ isEditing ? '编辑帖子' : '发布帖子' }}</h3>
          <div class="space-y-6">
            <div class="grid grid-cols-3 gap-3">
              <button v-for="t in [{id:'daily', n:'日常'}, {id:'experience', n:'攻略'}, {id:'adopt_help', n:'送养'}]" :key="t.id" @click="publishType = t.id as any" :class="publishType === t.id ? 'bg-orange-500 text-white' : 'bg-white/5 text-gray-500'" class="py-3 rounded-xl text-[10px] font-bold uppercase transition-all">{{ t.n }}</button>
            </div>
            <input v-model="publishForm.title" placeholder="文章标题 (可选)" class="w-full bg-white/5 border border-white/10 rounded-xl px-6 py-4 text-sm text-white outline-none focus:border-orange-500" />
            <textarea v-model="publishForm.content" class="w-full h-40 bg-white/5 border border-white/10 rounded-2xl p-6 text-white outline-none focus:border-orange-500" placeholder="分享点什么吧..."></textarea>
            <input v-model="publishForm.image_url" placeholder="封面图片链接 https://..." class="w-full bg-white/5 border border-white/10 rounded-xl px-6 py-4 text-sm text-white outline-none focus:border-orange-500" />
            <button @click="handlePublish" :disabled="isPublishing" class="w-full bg-orange-500 text-white py-4 rounded-xl font-black text-lg hover:bg-orange-600 transition-all flex justify-center items-center gap-2">
              <Loader2 v-if="isPublishing" class="animate-spin" :size="20" />{{ isEditing ? '确认修改' : '立即发布' }}
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
          <button @click="showUserProfile = false" class="absolute top-6 right-6 text-gray-500 hover:text-white transition-colors">
            <X :size="20" />
          </button>

          <!-- 加载中 -->
          <div v-if="isLoadingProfile" class="flex justify-center py-8">
            <Loader2 class="animate-spin text-orange-500" :size="32" />
          </div>

          <template v-else-if="profileUser">
            <!-- 头像 + 名字 -->
            <div class="flex flex-col items-center gap-4 text-center">
              <div class="w-20 h-20 rounded-3xl border-2 border-orange-500/30 overflow-hidden">
                <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${profileUser.username}`" class="w-full h-full" />
              </div>
              <div>
                <h3 class="text-2xl font-black text-white">{{ profileUser.username }}</h3>
                <span class="text-[10px] bg-orange-500/10 text-orange-500 px-2 py-0.5 rounded border border-orange-500/20 uppercase font-black">
                  {{ ({individual:'爱宠人士', org_admin:'救助站', root:'管理员'} as Record<string,string>)[profileUser.role] || profileUser.role || '用户' }}
                </span>
              </div>
            </div>

            <!-- 用户信息 -->
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

            <!-- 操作按钮 -->
            <div class="flex gap-3 pt-2">
              <!-- 不是自己才显示私信按钮 -->
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
