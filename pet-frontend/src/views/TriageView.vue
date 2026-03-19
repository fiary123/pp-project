<script setup lang="ts">
import { ref } from 'vue'
import { 
  Stethoscope, BrainCircuit, Activity, AlertCircle, 
  Image as ImageIcon, Video as VideoIcon, Loader2,
  CheckCircle2, ChevronRight, X, FileText
} from 'lucide-vue-next'
import BaseCard from '../components/BaseCard.vue'
import axios from '../api/index'

// 1. 状态管理
const symptom = ref('')
const selectedFile = ref<File | null>(null)
const filePreview = ref<string | null>(null)
const fileType = ref<'image' | 'video' | null>(null)

const isAnalyzing = ref(false)
const progress = ref(0)
const thoughts = ref<string[]>([])
const diagnosisResult = ref('')

// 2. 文件处理
const onFileSelect = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  
  selectedFile.value = file
  fileType.value = file.type.startsWith('video') ? 'video' : 'image'
  
  const reader = new FileReader()
  reader.onload = (res) => {
    filePreview.value = res.target?.result as string
  }
  reader.readAsDataURL(file)
}

const removeFile = () => {
  selectedFile.value = null
  filePreview.value = null
  fileType.value = null
}

// 3. 核心分析逻辑 (支持多模态)
const analyzeSymptom = async () => {
  if (!symptom.value.trim()) return
  
  isAnalyzing.value = true
  progress.value = 5
  thoughts.value = ['[Navigator] 正在接收多模态输入...', '[System] 唤醒视觉分析专家团...']
  diagnosisResult.value = ''

  try {
    // 模拟多智能体会诊过程
    setTimeout(() => {
      progress.value = 30
      thoughts.value.push(fileType.value ? `[VisionAgent] 正在分析${fileType.value === 'video' ? '视频帧' : '图片'}纹理与病灶...` : '[VisionAgent] 跳过视觉扫描（无文件上传）...')
    }, 800)

    setTimeout(() => {
      progress.value = 60
      thoughts.value.push('[MedicalExpert] 正在结合病历手册进行语义对齐...')
    }, 2000)

    // 构造 FormData
    const formData = new FormData()
    formData.append('symptom', symptom.value)
    if (selectedFile.value) {
      formData.append('file', selectedFile.value)
    }

    const res = await axios.post('/api/triage/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    progress.value = 100
    diagnosisResult.value = res.data.reply
    thoughts.value.push('[AuditExpert] 审计通过，最终报告生成。')
  } catch (err) {
    diagnosisResult.value = "AI 系统响应异常，请检查后端网络或模型 Key。"
  } finally {
    isAnalyzing.value = false
  }
}
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-10 px-4">
    <!-- 顶部 -->
    <div class="text-center space-y-4">
      <div class="inline-flex items-center gap-2 px-4 py-2 bg-orange-500/10 border border-orange-500/20 rounded-full text-orange-500 text-xs font-bold uppercase tracking-[0.2em]">
        <BrainCircuit :size="14" /> 多模态智能体系统
      </div>
      <h2 class="text-5xl font-black text-white drop-shadow-2xl italic">智能多模态分诊</h2>
      <p class="text-gray-400 max-w-2xl mx-auto text-lg font-medium">上传患处图片或症状视频，由 AI 专家团为您进行深度视觉扫描与初步诊断</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <!-- 左侧：工作台 -->
      <div class="lg:col-span-6 space-y-6">
        <BaseCard class="h-full flex flex-col min-h-[600px] !p-8">
          <div class="flex items-center justify-between mb-8">
            <h3 class="font-bold text-2xl text-white flex items-center gap-3">
              <div class="p-3 bg-blue-500/20 text-blue-400 rounded-2xl"><Stethoscope :size="24" /></div>
              诊断输入
            </h3>
          </div>
          
          <!-- 文本描述 -->
          <textarea 
            v-model="symptom"
            :disabled="isAnalyzing"
            class="w-full h-40 bg-white/5 border border-white/10 rounded-[2rem] p-6 text-white focus:outline-none focus:border-orange-500 transition-all resize-none text-lg placeholder:text-gray-600 mb-6"
            placeholder="描述症状，例如：猫咪眼睛红肿，伴有分泌物..."
          ></textarea>

          <!-- 多模态上传区域 -->
          <div class="flex-1 space-y-4">
            <div v-if="!filePreview" class="relative h-full">
              <input type="file" @change="onFileSelect" accept="image/*,video/*" class="absolute inset-0 w-full h-full opacity-0 z-10 cursor-pointer" />
              <div class="h-full min-h-[200px] border-2 border-dashed border-white/10 rounded-[2.5rem] flex flex-col items-center justify-center space-y-4 bg-white/5 hover:bg-white/10 transition-colors">
                <div class="flex gap-4">
                  <div class="p-4 bg-orange-500/20 text-orange-500 rounded-full"><ImageIcon :size="32" /></div>
                  <div class="p-4 bg-purple-500/20 text-purple-500 rounded-full"><VideoIcon :size="32" /></div>
                </div>
                <p class="text-gray-400 font-bold">点击或拖拽上传图片/视频</p>
                <p class="text-[10px] text-gray-600 uppercase tracking-widest">支持 JPG、PNG、MP4（最大 20MB）</p>
              </div>
            </div>

            <!-- 预览区域 -->
            <div v-else class="relative rounded-[2.5rem] overflow-hidden border border-white/10 shadow-2xl bg-black">
              <img v-if="fileType === 'image'" :src="filePreview" class="w-full h-auto max-h-[300px] object-contain" />
              <video v-else :src="filePreview" controls class="w-full max-h-[300px]"></video>
              <button @click="removeFile" class="absolute top-4 right-4 p-2 bg-black/60 text-white rounded-full hover:bg-red-500 transition-all">
                <X :size="20" />
              </button>
            </div>
          </div>

          <button 
            @click="analyzeSymptom"
            :disabled="isAnalyzing || !symptom"
            class="mt-8 w-full bg-orange-500 hover:bg-orange-600 disabled:bg-gray-700 text-white py-6 rounded-[2rem] font-black text-xl flex items-center justify-center gap-3 transition-all shadow-xl shadow-orange-500/30 active:scale-95"
          >
            <template v-if="isAnalyzing">
              <Loader2 class="animate-spin" :size="28" /> 智能会诊中...
            </template>
            <template v-else>
              提交专家团分析 <ChevronRight :size="28" />
            </template>
          </button>
        </BaseCard>
      </div>

      <!-- 右侧：报告区 -->
      <div class="lg:col-span-6 space-y-6">
        <!-- 推理流 -->
        <BaseCard v-if="isAnalyzing || thoughts.length > 0" class="border-orange-500/20 bg-black/20">
          <div class="flex items-center justify-between mb-6">
            <h4 class="text-xs font-black text-orange-500 uppercase tracking-widest flex items-center gap-2">
              <Activity :size="14" /> 智能体推理过程
            </h4>
            <span class="text-[10px] font-mono text-gray-500">{{ progress }}%</span>
          </div>
          <div class="h-1.5 w-full bg-white/5 rounded-full overflow-hidden mb-8">
            <div class="h-full bg-orange-500 transition-all duration-1000" :style="{ width: progress + '%' }"></div>
          </div>
          <div class="space-y-4">
            <div v-for="(thought, i) in thoughts" :key="i" 
                 class="flex items-start gap-3 text-[13px] font-mono text-gray-400">
              <CheckCircle2 v-if="i < thoughts.length - 1 || progress === 100" class="text-green-500 mt-0.5" :size="16" />
              <Loader2 v-else class="text-orange-500 animate-spin mt-0.5" :size="16" />
              {{ thought }}
            </div>
          </div>
        </BaseCard>

        <!-- 诊断结论 -->
        <transition name="fade-slide">
          <BaseCard v-if="diagnosisResult" class="bg-white text-gray-900 border-none shadow-[0_50px_100px_rgba(0,0,0,0.3)]">
            <div class="flex items-center gap-4 mb-8 border-b border-gray-100 pb-6">
              <div class="p-4 bg-orange-500 text-white rounded-[1.5rem] shadow-lg shadow-orange-500/30"><FileText :size="28" /></div>
              <div>
                <h3 class="font-black text-2xl uppercase tracking-tighter">AI 智能诊断报告</h3>
                <p class="text-xs text-gray-400 font-bold uppercase">SmartPet 专家团队</p>
              </div>
            </div>
            
            <div class="text-lg leading-loose text-gray-700 whitespace-pre-wrap font-medium">
              {{ diagnosisResult }}
            </div>

            <div class="mt-12 p-8 bg-red-50 rounded-[2.5rem] border border-red-100 flex items-start gap-5">
              <AlertCircle class="text-red-500 flex-shrink-0" :size="24" />
              <p class="text-sm text-red-800 leading-relaxed font-bold">
                ⚠️ 本报告由多智能体协作生成，包含视觉扫描分析。报告仅供参考，若宠物状况紧急（休克、大出血、呼吸困难），请立即送医！
              </p>
            </div>
          </BaseCard>
        </transition>

        <!-- 初始 -->
        <div v-if="!isAnalyzing && thoughts.length === 0" class="h-full flex flex-col items-center justify-center p-20 border-4 border-dashed border-white/5 rounded-[4rem] text-gray-700 text-center space-y-6">
          <BrainCircuit :size="80" class="opacity-10" />
          <div class="space-y-2">
            <p class="text-2xl font-black text-white/20">等待分析中</p>
            <p class="text-sm max-w-xs mx-auto">请在左侧上传宠物的现状信息，AI 视觉与医疗专家组已待命</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* @reference "tailwindcss"; */

.fade-slide-enter-active { transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1); }
.fade-slide-enter-from { opacity: 0; transform: translateY(40px); }

.prose { max-width: none; }
</style>
