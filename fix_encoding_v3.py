import sys

# Unicode escaped content to avoid any encoding issues during script transmission
content = """<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import {
  Search, Heart, Loader2, X, Wand2, ChevronRight,
  CheckCircle2, BrainCircuit,
  Send, Sparkles, Star, Info
} from 'lucide-vue-next';
import { useAuthStore } from '../store/authStore';
import axios from '../api/index';

const router = useRouter();
const authStore = useAuthStore();

const defaultAdoptionPreferences = {
  hard_preferences: [] as string[],
  soft_preferences: ['\u4f4f\u623f\u7a33\u5b9a\u6027', '\u966a\u4f34\u65f6\u95f4', '\u8d23\u4efb\u610f\u8bc6'],
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
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
    return { ...defaultAdoptionPreferences, ...(parsed as Record<string, unknown>) };
  } catch {
    return { ...defaultAdoptionPreferences };
  }
};

const riskToleranceLabel = (value?: string) => {
  if (value === 'conservative') return '\u4fdd\u5守\u578b'
  if (value === 'relaxed') return '\u5bbd\u677e\u578b'
  return '\u4e2d\u6027'
}

const dimensionRiskClass = (level?: string) => {
  if (level === 'Low') return 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300';
  if (level === 'High') return 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300';
  return 'bg-amber-100 text-amber-700 dark:bg-yellow-500/20 dark:text-yellow-300';
};

const housingTypeLabel = (value?: string) => {
  if (value === 'house') return '\u72ec\u7acb\u4f4f\u5b85';
  if (value === 'other') return '\u5176\u4ed6';
  return '\u516c\u5bd3';
};

const summarizePetExpectations = (prefs: any) => {
  const chips: string[] = [];
  if (prefs.require_stable_housing) chips.push('\u7a33\u5b9a\u5c45\u4f4f');
  if (prefs.require_financial_capacity) chips.push('\u57fa\u7840\u7ecf\u6d4e\u80fd\u529b');
  if (prefs.require_followup_updates) chips.push('\u63a5\u53d7\u9001\u517b\u56de\u8bbf');
  if (prefs.require_family_agreement) chips.push('\u5bb6\u5ead\u540c\u610f');
  if (!prefs.allow_novice) chips.push('\u6709\u7ecf\u9a8c\u4f18\u5148');
  if (!prefs.accept_renting) chips.push('\u8c28\u614e\u79df\u623f');
  if (prefs.prefer_local) chips.push('\u672c\u5730\u4f18\u5148');
  if (prefs.prefer_quiet_household) chips.push('\u504f\u597d\u5b89\u9759\u5bb6\u5ead');
  if (prefs.prefer_multi_pet_experience) chips.push('\u591a\u5ba0\u7ecf\u9a8c\u52a0\u5206');
  return chips.slice(0, 6);
}

const buildMockAdoptionPreferences = () => ({
  ...defaultAdoptionPreferences,
  require_followup_updates: true,
  soft_preferences: [...defaultAdoptionPreferences.soft_preferences, '\u63a5\u53d7\u9001\u517b\u56de\u8bbf']
});

// 1. \u72b6\u6001\u7ba1\u7406
const pets = ref<any[]>([]);
const isLoading = ref(true);
const searchQuery = ref('');
const activeFilter = ref('\u5168\u90e8');
const sourceFilter = ref('\u5168\u90e8'); 
const selectedPet = ref<any>(null);

const fetchPets = async () => {
  isLoading.value = true;
  try {
    const res = await axios.get('/api/pets');
    if (res.data) {
      const realPets = res.data.map((p: any) => ({
        ...p,
        id: Number(p.id),
        img: p.image_url || p.post_image_url || `https://images.unsplash.com/photo-1543466835-00a7907e9de1?sig=${p.id}`,
        desc: p.description || p.post_content || '\u6682\u65e0\u8be6\u7ec6\u4ecb\u7ecd',
        type: p.type || '\u72d7\u72d7',
        owner_type: p.owner_type || 'org',
        adoption_preferences: parseAdoptionPreferences(p.adoption_preferences),
        tags: p.tags ? (typeof p.tags === 'string' ? JSON.parse(p.tags) : p.tags) : ['\u6e29\u987a', '\u7c98\u4eba'],
        match: 80 + (p.id % 20)
      }));
      pets.value = realPets;
    }
  } catch (err) { console.error('\u83b7\u53d6\u5217\u8868\u5931\u8d25'); }
  finally { isLoading.value = false; }
};

const filteredPets = computed(() => {
  return pets.value.filter(p => {
    const search = searchQuery.value.toLowerCase();
    const matchesText = p.name.toLowerCase().includes(search) || p.species.toLowerCase().includes(search);
    const matchesType = activeFilter.value === '\u5168\u90e8' || p.type === activeFilter.value;
    const matchesSource = sourceFilter.value === '\u5168\u90e8'
      || (sourceFilter.value === '\u673a\u6784' && p.owner_type === 'org')
      || (sourceFilter.value === '\u4e2a\u4eba' && p.owner_type === 'personal');
    return matchesText && matchesType && matchesSource;
  }).sort((a, b) => b.match - a.match);
});

onMounted(() => {
  fetchPets();
});
</script>

<template>
  <div class="space-y-8 md:space-y-12 pb-16 md:pb-20 px-3 md:px-4 max-w-[1600px] mx-auto text-gray-900 dark:text-white transition-colors duration-300">
    <!-- 1. Hero AI \u5339\u914d\u533a -->
    <div class="relative py-10 md:py-16 text-center space-y-6 md:space-y-8 overflow-hidden rounded-[2.2rem] md:rounded-[4rem] bg-gradient-to-b from-orange-500/10 to-transparent border border-gray-200 dark:border-white/5 shadow-2xl transition-all">
      <div class="relative z-10 space-y-4 px-4 md:px-6 text-gray-900 dark:text-white">
        <h2 class="text-3xl sm:text-4xl md:text-6xl font-black italic tracking-tighter uppercase text-orange-500 leading-tight">\u5bfb\u627e\u60a8\u7684 <br/>\u5b8c\u7f8e\u4f19\u4f34</h2>
        <p class="text-xs md:text-sm text-gray-500 dark:text-gray-400 italic font-black">AI \u8bed\u4e49\u8bc6\u522b \u00b7 \u591a\u8f6e\u6df1\u5ea6\u5bf9\u8bdd \u00b7 \u7cbe\u51c6\u5168\u5e93\u5339\u914d</p>
      </div>
    </div>

    <!-- 2. \u5217\u8868\u533a -->
    <div class="flex flex-col md:flex-row items-stretch md:items-center justify-between px-1 md:px-4 gap-4 md:gap-6 text-gray-900 dark:text-white">
      <div class="flex items-center gap-2 bg-gray-100 dark:bg-white/5 p-1.5 rounded-2xl border border-transparent dark:border-white/5 shadow-inner transition-all overflow-x-auto scrollbar-hide">
        <button v-for="cat in ['\u5168\u90e8', '\u732b\u54aa', '\u72d7\u72d7', '\u5f02\u5ba0']" :key="cat" @click="activeFilter = cat"
          :class="activeFilter === cat ? 'bg-orange-500 text-white shadow-lg' : 'text-gray-500 dark:text-gray-400 hover:text-orange-500'" class="px-5 md:px-8 py-3 rounded-xl font-bold transition-all text-sm whitespace-nowrap">
          {{ cat }}
        </button>
      </div>
    </div>

    <div class="px-2">
      <div v-if="isLoading" class="py-40 flex flex-col items-center"><Loader2 class="animate-spin text-orange-500" :size="48" /><p class="text-gray-500 font-black mt-4 uppercase tracking-widest">\u6 retrieval \u4e2d...</p></div>
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4 md:gap-6">
        <div v-for="pet in filteredPets" :key="pet.id" 
          class="bg-white dark:bg-[#1a1a1a] rounded-[2rem] md:rounded-[2.5rem] overflow-hidden border border-gray-100 dark:border-white/5 transition-all group cursor-pointer shadow-sm hover:shadow-2xl relative flex flex-col hover:-translate-y-2 duration-500 shadow-orange-500/5">
          <div class="relative aspect-square">
            <img :src="pet.img" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-1000" />
            <h4 class="absolute bottom-4 left-6 font-black text-xl text-gray-900 dark:text-white">{{ pet.name }}</h4>
          </div>
          <div class="p-5 md:p-6 flex-1 flex flex-col justify-between text-gray-900 dark:text-white">
            <div class="space-y-3">
              <p class="text-xs md:text-sm text-gray-600 dark:text-gray-300 leading-6 line-clamp-2 min-h-[3rem]">
                {{ pet.desc || '\u8fd9\u662f\u4e00\u6761\u5f85\u9886\u517b\u5ba0\u7269\u4fe1\u606f\uff0c\u6b22\u8fce\u70b9\u5f00\u67e5\u770b\u8be6\u60c5\u3002' }}
              </p>
            </div>
            <div class="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-white/5 mt-4 text-gray-400 dark:text-gray-500 font-bold uppercase tracking-widest">
              <p class="text-sm text-gray-700 dark:text-gray-200 tracking-[0.18em]">{{ pet.species }}</p>
              <ChevronRight class="text-orange-500 group-hover:translate-x-1 transition-transform" :size="16" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.4s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.scrollbar-hide::-webkit-scrollbar { display: none; }
.scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
</style>
"""

with open('pet-frontend/src/views/AdoptView.vue', 'wb') as f:
    f.write(content.encode('utf-8'))
