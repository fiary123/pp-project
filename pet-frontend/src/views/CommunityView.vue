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
  soft_preferences: ['住房稳定性', '陪伴时间', '责任意识'],
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
  if (typeof raw === 'object') {
    return { ...defaultAdoptionPreferences, ...(raw as Record<string, unknown>) };
  }
  return { ...defaultAdoptionPreferences };
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
  title: '', content: '', image_url: '',
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
const MOCK_COMMENT_STORAGE_KEY = 'community_mock_comments_v1';

const readMockComments = (): Record<number, any[]> => {
  try {
    const raw = localStorage.getItem(MOCK_COMMENT_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
};

const writeMockComments = (commentsMap: Record<number, any[]>) => {
  try {
    localStorage.setItem(MOCK_COMMENT_STORAGE_KEY, JSON.stringify(commentsMap));
  } catch {
    // 忽略本地存储异常，不阻塞评论流程
  }
};

const getStoredMockComments = (postId: number) => {
  const commentsMap = readMockComments();
  if (Array.isArray(commentsMap[postId])) return commentsMap[postId];
  
  // 如果是模拟帖子且本地没存过评论，则返回预置静态评论
  if (postId >= 9000) {
    const staticComments = [
      { id: 10001, username: '小林同学', content: '这也太可爱了吧！我也想养一只。', create_time: '2026-03-27 10:20' },
      { id: 10002, username: '家有恶犬', content: '哈哈，这种性格真的很适合新手。', create_time: '2026-03-27 11:45' },
      { id: 10003, username: '萌宠志愿者', content: '领养代替购买，支持一下！', create_time: '2026-03-27 14:10' }
    ];
    // 随机取 1-3 条
    const sliceEnd = (postId % 3) + 1;
    return staticComments.slice(0, sliceEnd);
  }
  return [];
};

const saveStoredMockComments = (postId: number, comments: any[]) => {
  const commentsMap = readMockComments();
  commentsMap[postId] = comments;
  writeMockComments(commentsMap);
};

// 用户信息弹窗
const showUserProfile = ref(false);
const profileUser = ref<any>(null);
const isLoadingProfile = ref(false);

const openUserProfile = async (userId: number, fallback: any) => {
  if (!userId || userId >= 9000) {
    profileUser.value = fallback;
    showUserProfile.value = true;
    isLoadingProfile.value = false;
    return;
  }
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

const toggleAdoptionPreference = (key: keyof typeof defaultAdoptionPreferences) => {
  if (!publishForm.value.adoption_preferences) {
    publishForm.value.adoption_preferences = { ...defaultAdoptionPreferences };
  }
  const current = publishForm.value.adoption_preferences[key];
  if (typeof current === 'boolean') {
    (publishForm.value.adoption_preferences as Record<string, unknown>)[key] = !current;
  }
};

const buildMockAdoptionPreferences = () => ({
  ...defaultAdoptionPreferences,
  require_followup_updates: true,
  soft_preferences: [...defaultAdoptionPreferences.soft_preferences, '接受送养回访']
});

// 模拟帖子生成器
const generateMockPosts = () => {
  const users = [
    { n: '猫片达人', r: 'individual' },
    { n: '狗狗日记', r: 'individual' },
    { n: '宠物百科', r: 'org_admin' },
    { n: '爱宠志愿者', r: 'org_admin' },
    { n: '铲屎官小李', r: 'individual' },
    { n: '家有恶霸犬', r: 'individual' },
    { n: '兽医张医生', r: 'org_admin' },
    { n: '糯米糍粑', r: 'individual' }
  ];
  const fallbackUser = { n: '匿名用户', r: 'individual' } as const;
  
  const contents = [
    {
      title: '今天在公园遇到了超可爱的柴犬！',
      content: '今天带我家主子去公园散步，结果遇到了一只超热情的柴犬，两只小可爱玩得不亦乐乎。柴犬的主人还分享了好多遛狗的心得，收获满满的一天！',
      img: 'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=1200&q=80',
      type: 'daily',
      user_idx: 0
    },
    {
      title: '我家猫不爱吃猫罐头正常吗？急！',
      content: '求助各位资深家长！我家主子快1岁了，最近突然对所有品牌的罐头都失去了兴趣，闻一下就走。但是吃干粮和冻干还是很香。这属于挑食吗？还是身体哪里不舒服？有没有遇到类似情况的？',
      img: 'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=1200&q=80',
      type: 'experience',
      user_idx: 4
    },
    {
      title: '【吐槽】现在的宠物美容店也太坑了吧...',
      content: '真的是气死我了！今天带我家修狗狗去洗澡剪毛，结果剪成了“秃头小宝贝”。跟美容师沟通的时候明明说好只修一下边缘，结果回来一看我差点没认出来。而且价格还比上次贵了50块，这种店真的不会再去第二次了！',
      img: 'https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?auto=format&fit=crop&w=1200&q=80',
      type: 'daily',
      user_idx: 5
    },
    {
      title: '晒一下我家的颜值担当：糯米！',
      content: '这就是我家的快乐源泉，每天下班看到它这个表情，感觉一天的疲惫都消失了。大家觉得它的眼神是在想什么呢？是在想晚饭吃什么吗？',
      img: 'https://images.unsplash.com/photo-1583511655826-05700d52f4d9?auto=format&fit=crop&w=1200&q=80',
      type: 'daily',
      user_idx: 7
    },
    {
      title: '新手养猫避坑指南：这些东西千万别买',
      content: '很多新手家长进坑时会买一大堆没用的东西。比如：1. 各种网红猫窝（它们大概率更喜欢快递纸箱）；2. 自动逗猫棒（有的猫会怕那个电机声）；3. 廉价的猫爬架（稳固性极差）。建议大家还是把钱花在刀刃上，比如优质的猫粮和定期的体检。',
      img: 'https://images.unsplash.com/photo-1513245543132-31f507417b26?auto=format&fit=crop&w=1200&q=80',
      type: 'experience',
      user_idx: 2
    },
    {
      title: '【急寻领养】温顺橘猫寻找温暖的家',
      content: '在小区楼下发现的小橘，大概3个月大，已做完基础驱虫。性格超级粘人，会踩奶，会用猫砂盆。因为家里已经有三只原住民了实在没办法再收编，希望能找一个有爱心、能科学喂养、不离不弃的家庭。',
      img: 'https://images.unsplash.com/photo-1548247416-ec66f4900b2e?auto=format&fit=crop&w=1200&q=80',
      type: 'adopt_help',
      user_idx: 3
    },
    {
      title: '春天到了，预防寄生虫不能掉以轻心',
      content: '最近诊室接到了很多因为草地玩耍导致体外寄生虫感染的病例。提醒各位家长：1. 驱虫一定要定期做；2. 去草丛茂密的地方回来要仔细检查爪缝和耳朵；3. 发现有异常红肿或频繁抓挠要及时就医。',
      img: 'https://images.unsplash.com/photo-1576201836106-be1758d1c87e?auto=format&fit=crop&w=1200&q=80',
      type: 'experience',
      user_idx: 6
    },
    // 新增咨询类型帖子
    {
      title: '咨询：兔子可以吃胡萝卜叶子吗？',
      content: '各位兔子家长好！我家兔子很喜欢吃胡萝卜，但是我听说叶子部分可能有问题。胡萝卜叶子可以喂兔子吗？需要注意什么？有没有推荐的兔子蔬菜清单？谢谢大家分享经验！',
      img: 'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=1200&q=80',
      type: 'experience',
      user_idx: 1
    },
    {
      title: '鸟类饲养咨询：鹦鹉需要什么营养？',
      content: '最近想养一只鹦鹉，但对鸟类营养不太了解。鹦鹉每天需要吃什么？有没有推荐的鸟粮品牌？除了鸟粮还需要补充什么维生素或矿物质吗？新手养鸟要注意哪些坑？',
      img: 'https://images.unsplash.com/photo-1444464666168-49d633b86797?auto=format&fit=crop&w=1200&q=80',
      type: 'experience',
      user_idx: 0
    },
    // 新增求助类型帖子
    {
      title: '【紧急求助】我家猫咪跑出去找不到啦！',
      content: '求助！今天下午我家猫咪从阳台跑出去了，到现在已经6个小时了还没找到。猫咪是黑白花的，脖子上有铃铛。已经找遍了小区和周围的巷子，但还是没消息。各位有经验的家长，猫咪跑出去一般会去哪里？有什么找猫的方法吗？现在天黑了真的好担心...',
      img: 'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=1200&q=80',
      type: 'daily',
      user_idx: 4
    },
    {
      title: '求助：仓鼠突然不爱动了，是生病了吗？',
      content: '我家仓鼠今天早上开始就不太对劲，一直蜷缩在角落不爱动，也不吃东西。平时很活泼的，现在看起来很虚弱。各位仓鼠家长遇到过这种情况吗？需要带去看兽医吗？还是在家观察一下？好担心它...',
      img: 'https://images.unsplash.com/photo-1425082661705-1834bfd09dca?auto=format&fit=crop&w=1200&q=80',
      type: 'daily',
      user_idx: 7
    },
    // 新增晒宠物类型帖子
    {
      title: '晒晒我家的金鱼宝宝们！',
      content: '今天给鱼缸换水的时候拍了几张照片，我家的金鱼们超级可爱！有红色的锦鲤和黑色的草金鱼，每天看它们游来游去心情都变好了。养鱼真的是一种很治愈的爱好，大家有养鱼的经验吗？',
      img: 'https://images.unsplash.com/photo-1520637836862-4d197d17c1a8?auto=format&fit=crop&w=1200&q=80',
      type: 'daily',
      user_idx: 5
    },
    {
      title: '我的小乌龟今天学会了爬坡！',
      content: '哈哈哈，今天发现我家的小乌龟居然能爬上那个小斜坡了！虽然动作很慢，但每次成功后它都会停下来休息一下，看起来超级有成就感。小乌龟真的太可爱了，每天观察它们的成长都让我觉得生活充满了惊喜。',
      img: 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?auto=format&fit=crop&w=1200&q=80',
      type: 'daily',
      user_idx: 2
    }
  ];

  return contents.map((c, i) => {
    const user = users[c.user_idx] ?? fallbackUser;
    return {
      id: 9000 + i,
      user_id: 0,
      username: user.n,
      role: user.r,
      title: c.title,
      content: c.content,
      image_url: c.img,
      image_urls: JSON.stringify([c.img]),
      type: c.type,
      adoption_preferences: c.type === 'adopt_help' ? buildMockAdoptionPreferences() : null,
      likes: Math.floor(Math.random() * 50) + 5,
      create_time: `2026-03-${28 - i} 1${i}:00`,
      comment_count: getStoredMockComments(9000 + i).length || Math.floor(Math.random() * 10),
    };
  });
};

const syncPostCommentCount = (postId: number, count: number) => {
  const target = posts.value.find((post) => post.id === postId);
  if (target) {
    target.comment_count = count;
  }
};

const getCommentCount = (post: any) => {
  const loadedCount = activePostComments.value[post.id];
  if (Array.isArray(loadedCount)) return loadedCount.length;
  if (typeof post.comment_count === 'number') return post.comment_count;
  return 0;
};

// 2. 加载数据
const fetchPosts = async () => {
  isLoading.value = true;
  try {
    const res = await axios.get('/api/posts');
    const dbItems = (res.data && res.data.items) ? res.data.items : (Array.isArray(res.data) ? res.data : []);
    const formattedDbItems = dbItems.map((p: any) => ({
      ...p,
      adoption_preferences: parseAdoptionPreferences(p.adoption_preferences),
      comment_count: Number(p.comment_count || 0),
      create_time: p.create_time ? new Date(p.create_time).toLocaleString() : '刚刚'
    }));
    // 合并展示
    posts.value = [...formattedDbItems, ...generateMockPosts()];
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
    const storedComments = getStoredMockComments(postId);
    activePostComments.value[postId] = storedComments;
    syncPostCommentCount(postId, storedComments.length);
    return;
  }
  try {
    const res = await axios.get(`/api/posts/${postId}/comments`);
    const comments = res.data || [];
    activePostComments.value[postId] = comments;
    syncPostCommentCount(postId, comments.length);
  } catch {
    activePostComments.value[postId] = [];
    syncPostCommentCount(postId, 0);
  }
};

const handleSubmitComment = async (postId: number) => {
  const content = commentInputs.value[postId]?.trim();
  if (!content || !authStore.user?.id) return;
  if (postId >= 9000) {
    const nextComments = [
      ...(activePostComments.value[postId] || getStoredMockComments(postId)),
      {
        id: Date.now(),
        username: authStore.user.username || '我',
        content,
        create_time: new Date().toLocaleString(),
      }
    ];
    activePostComments.value[postId] = nextComments;
    saveStoredMockComments(postId, nextComments);
    syncPostCommentCount(postId, nextComments.length);
    commentInputs.value[postId] = '';
    return;
  }
  isSubmittingComment.value[postId] = true;
  try {
    await axios.post('/api/posts/comment', { post_id: postId, user_id: authStore.user.id, content });
    commentInputs.value[postId] = '';
    const res = await axios.get(`/api/posts/${postId}/comments`);
    const comments = res.data || [];
    activePostComments.value[postId] = comments;
    syncPostCommentCount(postId, comments.length);
  } catch {
    alert('评论发送失败，请重试');
  } finally {
    isSubmittingComment.value[postId] = false;
  }
};

// 4. 文件上传
const triggerUpload = () => fileInput.value?.click();
const handleFileUpload = async (event: Event) => {
  const files = (event.target as HTMLInputElement).files;
  if (!files || files.length === 0) return;
  isUploading.value = true;
  try {
    const formData = new FormData();
    for (const file of Array.from(files)) {
      formData.append('files', file);
    }
    const res = await axios.post('/api/upload-batch', formData, { 
      headers: { 'Content-Type': 'multipart/form-data' } 
    });
    
    if (res.data.urls) {
      publishForm.value.image_urls.push(...res.data.urls);
      const [firstImage] = publishForm.value.image_urls;
      if (!publishForm.value.image_url && firstImage) {
        publishForm.value.image_url = firstImage;
      }
    }
  } catch (err: any) {
    alert(err.response?.data?.detail || '上传失败，请重试');
  } finally {
    isUploading.value = false;
    if (fileInput.value) fileInput.value.value = '';
  }
};
const removeImage = (idx: number) => {
  publishForm.value.image_urls.splice(idx, 1);
  publishForm.value.image_url = publishForm.value.image_urls[0] || '';
};

// 5. 管理员与编辑功能
const startEdit = (post: any) => {
  if (post.id >= 9000) { alert('演示贴不支持编辑哦'); return; }
  isEditing.value = true;
  editingPostId.value = post.id;
  publishType.value = post.type;
  const imgs = post.image_urls ? JSON.parse(post.image_urls) : (post.image_url ? [post.image_url] : []);
  publishForm.value = {
    title: post.title || '', content: post.content, image_url: post.image_url || '',
    image_urls: imgs,
    pet_name: post.pet_name || '', pet_gender: post.pet_gender || '',
    pet_age: post.pet_age || '', pet_breed: post.pet_breed || '',
    adopt_reason: post.adopt_reason || '', location: post.location || '',
    adoption_preferences: parseAdoptionPreferences(post.adoption_preferences)
  };
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
    const payload: any = {
      user_id: authStore.user?.id,
      title: publishForm.value.title,
      content: publishForm.value.content,
      image_url: publishForm.value.image_urls[0] || '',
      image_urls: JSON.stringify(publishForm.value.image_urls),
      type: publishType.value,
    };
    if (publishType.value === 'adopt_help') {
      payload.pet_name = publishForm.value.pet_name;
      payload.pet_gender = publishForm.value.pet_gender;
      payload.pet_age = publishForm.value.pet_age;
      payload.pet_breed = publishForm.value.pet_breed;
      payload.adopt_reason = publishForm.value.adopt_reason;
      payload.location = publishForm.value.location;
      payload.adoption_preferences = publishForm.value.adoption_preferences;
    }
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
  publishForm.value = {
    title: '', content: '', image_url: '', image_urls: [],
    pet_name: '', pet_gender: '', pet_age: '', pet_breed: '', adopt_reason: '', location: '',
    adoption_preferences: { ...defaultAdoptionPreferences }
  };
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
  <div class="max-w-6xl mx-auto space-y-6 md:space-y-8 pb-24 md:pb-32 px-3 md:px-4 text-gray-900 dark:text-white">
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-gray-200 dark:border-white/5 pb-4 md:pb-6">
      <div>
        <h2 class="text-3xl md:text-4xl font-black italic tracking-tighter uppercase" style="color: var(--text-primary);">宠物 <span class="text-orange-500">社区</span></h2>
        <p class="font-bold text-xs md:text-sm uppercase tracking-widest mt-2" style="color: var(--text-secondary);">
          {{ isAdmin ? '管理模式已开启' : '记录萌宠点滴，分享养宠干货' }}
        </p>
      </div>
      <div class="flex gap-4 md:gap-6 overflow-x-auto scrollbar-hide">
        <button v-for="t in [{id:'all', n:'全部'}, {id:'daily', n:'日常'}, {id:'experience', n:'攻略'}, {id:'adopt_help', n:'送养'}]"
          :key="t.id" @click="activeType = t.id as any"
          :class="activeType === t.id ? 'text-orange-500 border-b-2 border-orange-500 font-black scale-110' : 'text-gray-500'"
          class="text-sm md:text-base uppercase tracking-widest transition-all px-2 md:px-3 pb-2 whitespace-nowrap">{{ t.n }}</button>
      </div>
    </div>

    <div v-if="isLoading" class="py-20 flex justify-center"><Loader2 class="animate-spin text-orange-500" :size="48" /></div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
      <BaseCard v-for="post in filteredPosts" :key="post.id" class="!p-0 !bg-slate-50 dark:!bg-[#1a1a1a] overflow-hidden !border-slate-200 dark:!border-white/5 relative shadow-lg dark:shadow-2xl flex flex-col h-full hover:translate-y-[-4px] transition-transform duration-300">
        <!-- 管理员/本人控制栏 -->
        <div v-if="isAdmin || authStore.user?.id === post.user_id" class="px-4 py-2 bg-slate-100 dark:bg-white/5 border-b border-slate-200 dark:border-white/5 flex justify-between items-center">
          <span class="text-[8px] font-black text-slate-500 dark:text-gray-500 uppercase tracking-widest">{{ authStore.user?.id === post.user_id ? 'MINE' : 'ADMIN' }}</span>
          <div class="flex gap-2">
            <button @click="startEdit(post)" class="text-blue-400 hover:text-blue-300 text-[9px] font-black uppercase transition-colors">编辑</button>
            <button @click="handleDelete(post.id)" class="text-red-400 hover:text-red-300 text-[9px] font-black uppercase transition-colors">删除</button>
          </div>
        </div>

        <!-- 帖子头部 -->
        <div class="p-4 flex items-center gap-3">
          <button @click="openUserProfile(post.user_id, { id: post.user_id, username: post.username, role: post.role })"
            class="w-10 h-10 rounded-full border border-orange-500/20 overflow-hidden hover:border-orange-500 transition-all flex-shrink-0">
            <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${post.username}`" />
          </button>
          <div class="min-w-0">
            <h4 class="font-bold text-slate-900 dark:text-white text-sm truncate flex items-center gap-1.5">
              <button @click="openUserProfile(post.user_id, { id: post.user_id, username: post.username, role: post.role })"
                class="hover:text-orange-500 transition-colors truncate">{{ post.username }}</button>
              <span class="text-[8px] bg-orange-500/10 text-orange-500 px-1.5 py-0.5 rounded uppercase font-black shrink-0">
                {{ roleLabel[post.role] === '爱宠人士' ? '个人' : '机构' }}
              </span>
            </h4>
            <p class="text-[9px] text-slate-500 dark:text-gray-500 font-mono">{{ post.create_time }}</p>
          </div>
        </div>

        <!-- 图片展示 (统一高度) -->
        <div class="relative aspect-[4/3] cursor-pointer overflow-hidden bg-slate-200 dark:bg-white/5" @click="openViewer(post.image_urls ? JSON.parse(post.image_urls) : [post.image_url])">
          <template v-if="post.image_urls && JSON.parse(post.image_urls).length > 0">
            <video v-if="isVideo(JSON.parse(post.image_urls)[0])" :src="JSON.parse(post.image_urls)[0]" class="w-full h-full object-cover"></video>
            <img v-else :src="JSON.parse(post.image_urls)[0]" class="w-full h-full object-cover hover:scale-105 transition-transform duration-500" />
            <div v-if="JSON.parse(post.image_urls).length > 1" class="absolute top-2 right-2 px-2 py-1 bg-black/60 backdrop-blur-md rounded-lg text-white text-[10px] font-black">
              +{{ JSON.parse(post.image_urls).length - 1 }}
            </div>
          </template>
          <template v-else-if="post.image_url">
            <video v-if="isVideo(post.image_url)" :src="post.image_url" class="w-full h-full object-cover"></video>
            <img v-else :src="post.image_url" class="w-full h-full object-cover" />
          </template>
        </div>

        <!-- 帖子内容区 -->
        <div class="p-4 flex-1 flex flex-col gap-2">
          <h3 v-if="post.title" class="text-base md:text-lg font-black text-slate-900 dark:text-white italic tracking-tight line-clamp-1">{{ post.title }}</h3>
          
          <div v-if="post.type === 'adopt_help'" class="flex flex-wrap gap-1.5 mb-1">
            <span v-if="post.pet_name" class="px-2 py-0.5 bg-orange-500/10 text-orange-500 rounded text-[10px] font-bold">#{{ post.pet_name }}</span>
            <span v-if="post.location" class="px-2 py-0.5 bg-blue-500/10 text-blue-500 rounded text-[10px] font-bold">{{ post.location }}</span>
          </div>

          <p class="text-slate-800 dark:text-gray-300 text-xs md:text-sm leading-relaxed line-clamp-3 font-medium">{{ post.content }}</p>
        </div>

        <!-- 互动栏 -->
        <div class="px-4 py-3 bg-slate-100 dark:bg-white/[0.02] flex items-center justify-between border-t border-slate-200 dark:border-white/5 mt-auto">
          <div class="flex gap-4">
            <button @click="handleLike(post.id)"
              :class="likedPosts.has(post.id) ? 'text-red-500' : 'text-slate-600 dark:text-gray-500 hover:text-red-500'"
              class="flex items-center gap-1.5 text-xs font-black transition-all">
              <Heart :size="16" :fill="likedPosts.has(post.id) ? 'currentColor' : 'none'" />
              {{ post.likes }}
            </button>
            <button @click="loadComments(post.id)" class="flex items-center gap-1.5 text-xs font-black text-slate-600 dark:text-gray-500 hover:text-blue-500">
              <MessageCircle :size="16" />
              {{ getCommentCount(post) }}
            </button>
          </div>
          <span class="text-[10px] font-black uppercase px-2 py-0.5 rounded-full border border-slate-200 dark:border-white/10 text-slate-400">
            {{ post.type === 'daily' ? '日常' : post.type === 'experience' ? '攻略' : '送养' }}
          </span>
        </div>

        <!-- 紧凑评论区 -->
        <div v-if="activePostComments[post.id] !== undefined" class="bg-slate-100/80 dark:bg-black/20 border-t border-slate-200 dark:border-white/5 p-4 space-y-3">
          <div class="max-h-40 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
            <div v-for="c in activePostComments[post.id]" :key="c.id" class="text-[11px]">
              <span class="font-black text-orange-500 mr-1">{{ c.username }}:</span>
              <span class="text-slate-700 dark:text-gray-400">{{ c.content }}</span>
            </div>
          </div>
          <div class="flex gap-2">
            <input v-model="commentInputs[post.id]" @keyup.enter="handleSubmitComment(post.id)"
              placeholder="说点什么..."
              class="flex-1 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-lg px-3 py-1.5 text-[11px] outline-none focus:border-orange-500" />
            <button @click="handleSubmitComment(post.id)" class="text-orange-500 font-black text-[11px] uppercase">发送</button>
          </div>
        </div>
      </BaseCard>
    </div>

    <!-- 发布按钮 -->
    <button @click="showPublishModal = true" class="fixed bottom-5 right-5 md:bottom-12 md:right-12 w-14 h-14 md:w-16 md:h-16 bg-orange-500 text-white rounded-full flex items-center justify-center shadow-2xl z-50 hover:scale-110 transition-all shadow-orange-500/20">
      <Plus :size="32" />
    </button>

    <!-- 发布/编辑弹窗 -->
    <Teleport to="body">
      <div v-if="showPublishModal" class="fixed inset-0 z-[500] flex items-start md:items-center justify-center bg-black/70 dark:bg-black/95 backdrop-blur-md px-4 py-4 md:py-8 overflow-y-auto">
        <BaseCard class="w-full max-w-xl p-5 md:p-10 relative !bg-white dark:!bg-zinc-900 border-gray-200 dark:border-white/10 shadow-2xl my-auto max-h-[calc(100vh-2rem)] overflow-y-auto text-gray-900 dark:text-white">
          <button @click="closeModal" class="absolute top-4 right-4 md:top-6 md:right-6 text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors"><X :size="24" /></button>
          <h3 class="text-2xl md:text-3xl font-black text-gray-900 dark:text-white mb-6 md:mb-10 italic uppercase tracking-tighter">{{ isEditing ? '编辑帖子' : '发布动态' }}</h3>
          <div class="space-y-6 md:space-y-8">
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button v-for="t in [{id:'daily', n:'日常分享'}, {id:'experience', n:'养宠攻略'}, {id:'adopt_help', n:'寻主/求助'}]"
                :key="t.id" @click="publishType = t.id as any"
                :class="publishType === t.id ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20 border-orange-500' : 'bg-gray-100 dark:bg-white/5 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-white/5'"
                class="py-4 rounded-xl text-sm font-black uppercase transition-all tracking-widest border">
                {{ t.n }}
              </button>
            </div>
            <input v-model="publishForm.title" placeholder="给动态起个吸睛的标题吧 (可选)"
              class="w-full bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl px-4 md:px-6 py-4 md:py-5 text-sm md:text-base text-gray-900 dark:text-white outline-none focus:border-orange-500 transition-all placeholder-gray-400 dark:placeholder-gray-600" />
            <textarea v-model="publishForm.content"
              class="w-full h-32 md:h-36 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl p-4 md:p-6 text-sm md:text-base text-gray-900 dark:text-white outline-none focus:border-orange-500 transition-all leading-relaxed placeholder-gray-400 dark:placeholder-gray-600"
              placeholder="这一刻的想法..."></textarea>

            <div v-if="publishType === 'adopt_help'" class="bg-orange-50 dark:bg-orange-500/5 border border-orange-200 dark:border-orange-500/20 rounded-2xl p-4 md:p-5 space-y-4">
              <p class="text-xs font-black text-orange-500 uppercase tracking-widest">宠物信息</p>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input v-model="publishForm.pet_name" placeholder="宠物名字" class="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-3 text-sm text-gray-900 dark:text-white outline-none focus:border-orange-500 transition-all placeholder-gray-400 dark:placeholder-gray-600" />
                <input v-model="publishForm.pet_breed" placeholder="品种（如：英短、金毛）" class="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-3 text-sm text-gray-900 dark:text-white outline-none focus:border-orange-500 transition-all placeholder-gray-400 dark:placeholder-gray-600" />
                <input v-model="publishForm.pet_age" placeholder="年龄（如：2岁3个月）" class="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-3 text-sm text-gray-900 dark:text-white outline-none focus:border-orange-500 transition-all placeholder-gray-400 dark:placeholder-gray-600" />
                <div class="flex gap-2">
                  <button v-for="g in [['male','♂ 公'],['female','♀ 母'],['unknown','未知']]" :key="g[0]"
                    @click="publishForm.pet_gender = g[0] as string"
                    :class="publishForm.pet_gender === g[0] ? (g[0]==='male' ? 'bg-blue-500 text-white' : g[0]==='female' ? 'bg-pink-500 text-white' : 'bg-gray-500 text-white') : 'bg-white dark:bg-white/5 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-white/10'"
                    class="flex-1 py-3 rounded-xl text-xs font-bold transition-all border">{{ g[1] }}</button>
                </div>
              </div>
              <textarea v-model="publishForm.adopt_reason" placeholder="送养原因（如：主人工作调动、过敏等）"
                class="w-full h-20 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-3 text-sm text-gray-900 dark:text-white outline-none focus:border-orange-500 transition-all leading-relaxed placeholder-gray-400 dark:placeholder-gray-600"></textarea>
              <input v-model="publishForm.location" placeholder="所在地址（如：北京市朝阳区）"
                class="w-full bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-3 text-sm text-gray-900 dark:text-white outline-none focus:border-orange-500 transition-all placeholder-gray-400 dark:placeholder-gray-600" />

              <div class="space-y-3 pt-2 border-t border-orange-200 dark:border-orange-500/20">
                <div class="flex items-center justify-between gap-3 flex-wrap">
                  <p class="text-xs font-black text-orange-500 uppercase tracking-widest">送养偏好</p>
                </div>
                <div class="space-y-2">
                  <p class="text-[11px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest">基础要求</p>
                  <div class="flex flex-wrap gap-2">
                    <button
                      v-for="item in requirementOptions"
                      :key="item.key"
                      @click="toggleAdoptionPreference(item.key)"
                      :class="publishForm.adoption_preferences[item.key] ? 'bg-orange-500 text-white border-orange-500' : 'bg-white dark:bg-white/5 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-white/10'"
                      class="rounded-full border px-3 py-2 text-xs font-bold transition-all"
                    >
                      {{ item.label }}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div class="space-y-3">
              <div v-if="publishForm.image_urls.length > 0" class="grid grid-cols-2 md:grid-cols-3 gap-2">
                <div v-for="(url, idx) in publishForm.image_urls" :key="idx" class="relative group aspect-square rounded-xl overflow-hidden border border-white/10">
                  <img :src="url" class="w-full h-full object-cover" />
                  <button @click="removeImage(idx)" class="absolute top-1 right-1 w-6 h-6 bg-black/70 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all hover:bg-red-500"><X :size="12" /></button>
                </div>
                <div v-if="publishForm.image_urls.length < 9" @click="triggerUpload"
                  class="aspect-square rounded-xl border-2 border-dashed border-gray-200 dark:border-white/10 flex items-center justify-center cursor-pointer hover:border-orange-500/50 hover:bg-gray-50 dark:hover:bg-white/5 transition-all">
                  <Loader2 v-if="isUploading" class="animate-spin text-orange-500" :size="20" />
                  <Plus v-else class="text-gray-500" :size="24" />
                </div>
              </div>
              <div v-else @click="triggerUpload"
                class="w-full py-10 border-2 border-dashed border-gray-200 dark:border-white/10 rounded-2xl flex flex-col items-center justify-center gap-3 cursor-pointer hover:border-orange-500/50 hover:bg-gray-50 dark:hover:bg-white/5 transition-all">
                <Upload v-if="!isUploading" class="text-gray-500" :size="28" />
                <Loader2 v-else class="text-orange-500 animate-spin" :size="28" />
                <p class="text-xs font-black text-gray-500 uppercase tracking-widest">{{ isUploading ? '上传中...' : '点击上传图片' }}</p>
              </div>
              <input type="file" ref="fileInput" class="hidden" accept="image/*,video/*" multiple @change="handleFileUpload" />
            </div>
            <button @click="handlePublish" :disabled="isPublishing || isUploading"
              class="w-full bg-orange-500 text-white py-4 md:py-5 rounded-xl font-black text-base md:text-xl hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex justify-center items-center gap-3 shadow-xl shadow-orange-500/20">
              <Loader2 v-if="isPublishing" class="animate-spin" :size="24" />
              {{ isEditing ? '确认修改' : '立即发布动态' }}
            </button>
          </div>
        </BaseCard>
      </div>
    </Teleport>

    <!-- 图片查看器 -->
    <Teleport to="body">
      <div v-if="showViewer" class="fixed inset-0 z-[700] flex items-center justify-center bg-black/95 px-3" @click.self="showViewer = false">
        <button @click="showViewer = false" class="absolute top-4 right-4 md:top-6 md:right-6 w-10 h-10 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center text-white transition-all"><X :size="20" /></button>
        <button v-if="viewerIndex > 0" @click="viewerIndex--" class="absolute left-3 md:left-6 w-10 h-10 md:w-12 md:h-12 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center text-white transition-all"><ChevronLeft :size="24" /></button>
        <img :src="viewerImages[viewerIndex]" class="max-w-[90vw] max-h-[90vh] object-contain rounded-2xl" />
        <button v-if="viewerIndex < viewerImages.length - 1" @click="viewerIndex++" class="absolute right-3 md:right-6 w-10 h-10 md:w-12 md:h-12 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center text-white transition-all"><ChevronRight :size="24" /></button>
      </div>
    </Teleport>

    <!-- 用户资料弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showUserProfile" class="fixed inset-0 z-[600] flex items-center justify-center bg-black/80 backdrop-blur-md px-4" @click.self="showUserProfile = false">
          <div class="bg-white dark:bg-[#111] border border-gray-200 dark:border-white/10 rounded-[2rem] w-full max-w-sm p-6 md:p-10 space-y-6 relative text-gray-900 dark:text-white">
            <button @click="showUserProfile = false" class="absolute top-4 right-4 text-gray-500"><X :size="20" /></button>
            <div v-if="isLoadingProfile" class="flex justify-center py-8"><Loader2 class="animate-spin text-orange-500" /></div>
            <template v-else-if="profileUser">
              <div class="flex flex-col items-center gap-4 text-center">
                <div class="w-20 h-20 rounded-3xl border-2 border-orange-500/30 overflow-hidden shadow-xl">
                  <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${profileUser.username}`" class="w-full h-full" />
                </div>
                <div>
                  <h3 class="text-2xl font-black">{{ profileUser.username }}</h3>
                  <span class="text-[10px] bg-orange-500/10 text-orange-500 px-2 py-0.5 rounded border border-orange-500/20 uppercase font-black">{{ roleLabel[profileUser.role] || '用户' }}</span>
                </div>
              </div>
              <div class="flex gap-3 pt-2">
                <button v-if="authStore.user && authStore.user.id !== profileUser.id" @click="$router.push(`/chat?to=${profileUser.id}`)" class="flex-1 bg-orange-500 text-white py-3 rounded-2xl font-black text-sm">发私信</button>
                <button @click="showUserProfile = false" class="flex-1 bg-gray-100 dark:bg-white/10 py-3 rounded-2xl font-black text-sm">关闭</button>
              </div>
            </template>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(249, 115, 22, 0.2); border-radius: 10px; }
</style>
