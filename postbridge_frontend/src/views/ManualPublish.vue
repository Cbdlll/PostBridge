<template>
  <div class="manual-publish-page page-container">
    <div class="flex gap-4 h-full" style="align-items: stretch; overflow: hidden;">
      <!-- 左侧：发布表单 -->
      <div class="card flex-1 flex flex-col" style="min-height: 0; overflow: hidden;">
        <div class="card-header shrink-0">
          <span class="card-title">创建发布任务</span>
        </div>
        
        <div class="card-body scrollable-content">
          <el-form :model="form" label-position="top" class="compact-form">
            
            <!-- 第一行：平台与账号 (Grid Layout) -->
            <div class="grid-row-4">
              <!-- 平台选择（多选） -->
              <el-form-item label="发布平台" required class="compact-item">
                <div class="platform-compact-list">
                  <div 
                    v-for="p in platforms" 
                    :key="p.value"
                    class="platform-chip"
                    :class="{ active: form.platforms.includes(p.value) }"
                    @click="togglePlatform(p.value)"
                  >
                    <el-icon :class="p.iconClass" :style="{ color: form.platforms.includes(p.value) ? '#fff' : p.color }"><component :is="p.icon" /></el-icon>
                    <span>{{ p.label }}</span>
                  </div>
                </div>
                <div class="form-tip" v-if="form.platforms.length > 1">已选择 {{ form.platforms.length }} 个平台，将分别创建发布任务</div>
              </el-form-item>

              <!-- 账号选择 -->
              <el-form-item label="发布账号" required class="compact-item">
                 <div class="account-scroll-container" v-if="filteredAccounts.length > 0">
                    <div 
                      v-for="acc in filteredAccounts" 
                      :key="acc[0]"
                      class="account-chip"
                      :class="{ active: form.accountList.includes(acc[0]), disabled: acc[4] !== 1 }"
                      @click="toggleAccount(acc)"
                    >
                      <div class="param-avatar tiny">{{ acc[3].charAt(0).toUpperCase() }}</div>
                      <span class="text-truncate">{{ acc[3] }}</span>
                      <div class="status-indicator" :class="acc[4] === 1 ? 'ok' : 'err'"></div>
                    </div>
                 </div>
                 <div v-else class="text-xs text-gray-400 py-2">无可用账号</div>
              </el-form-item>
            </div>

            <!-- 第二行：视频选择 -->
            <el-form-item label="视频素材" required class="compact-item">
               <el-select 
                  v-model="form.selectedFile" 
                  placeholder="请选择视频"
                  style="width: 100%"
                  filterable
                >
                  <el-option
                    v-for="file in files"
                    :key="file.id"
                    :label="file.filename"
                    :value="file.file_path"
                  >
                    <div class="flex justify-between items-center w-full">
                      <span class="truncate" style="max-width: 300px">{{ file.filename }}</span>
                      <span class="text-xs text-gray-400">{{ file.filesize }}MB</span>
                    </div>
                  </el-option>
                </el-select>
            </el-form-item>

            <!-- 第三行：标题 -->
            <el-form-item label="视频标题" required class="compact-item">
              <el-input 
                v-model="form.title" 
                placeholder="吸引人的标题..." 
                maxlength="30" 
                show-word-limit 
              />
            </el-form-item>

            <!-- 第四行：简介 -->
            <el-form-item label="视频简介" class="compact-item">
              <el-input 
                v-model="form.description" 
                type="textarea" 
                :rows="5" 
                placeholder="填写简介..."
                maxlength="800"
                show-word-limit
                resize="none"
              />
            </el-form-item>

            <!-- 第五行：话题标签 (Custom Input) -->
            <el-form-item label="话题标签" class="compact-item">
              <div class="tags-input-container">
                <div class="tags-wrapper">
                  <el-tag 
                    v-for="(tag, index) in form.tags" 
                    :key="index"
                    closable
                    type="info"
                    @close="removeTag(index)"
                    size="small"
                  >
                    #{{ tag }}
                  </el-tag>
                  <input 
                    v-model="tagInput"
                    @keydown.enter.prevent="addTag"
                    @keydown.backspace="handleBackspace"
                    placeholder="输入标签回车添加"
                    class="native-input"
                  />
                </div>
                <!-- 推荐标签移动到容器外部或底部对齐 -->
              </div>
              <div class="suggested-tags mt-2">
                <span class="text-xs text-gray-400 mr-2">推荐:</span>
                <span 
                  v-for="tag in suggestedTags" 
                  :key="tag" 
                  class="suggestion-chip"
                  @click="addSuggestedTag(tag)"
                >
                  #{{ tag }}
                </span>
              </div>
            </el-form-item>
          </el-form>
        </div>

        <div class="card-footer shrink-0 border-t pt-4 mt-auto">
          <el-button 
            type="primary" 
            size="large" 
            @click="handleSubmit" 
            :loading="submitting" 
            class="w-full shadow-button"
          >
            <el-icon class="mr-2"><Promotion /></el-icon>
            立即发布
          </el-button>
        </div>
      </div>

      <!-- 右侧：预览卡片 - 固定宽度 -->
      <div class="card shrink-0 flex flex-col items-center justify-center bg-gray-900" style="width: 300px; padding: 20px;">
        <div class="mobile-frame">
           <div class="preview-content">
              <!-- Video Placeholder -->
              <div class="preview-video-area">
                <el-icon :size="40" color="#666"><VideoPlay /></el-icon>
              </div>
              
              <!-- Overlay Info -->
              <div class="preview-overlay">
                <div class="preview-text title">{{ form.title || '视频标题' }}</div>
                <div class="preview-text desc">{{ form.description || '视频简介文案...' }}</div>
                <div class="preview-tags-line">
                  <span v-for="tag in form.tags" :key="tag">#{{ tag }}&nbsp;</span>
                </div>
              </div>

              <!-- Side Action Bar Simulation -->
              <div class="side-bar">
                 <div class="side-icon avatar-ph"></div>
                 <div class="side-icon"><div class="heart"></div></div>
                 <div class="side-icon"><div class="dots"></div></div>
                 <div class="side-icon"><div class="arrow"></div></div>
              </div>
           </div>
        </div>
        <div class="text-gray-500 text-xs mt-4">效果预览</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, Iphone, ChatDotRound, VideoCamera, Select, Promotion } from '@element-plus/icons-vue'
import { getFiles, getAccounts, postVideo } from '@/api'

const files = ref<any[]>([])
const accounts = ref<any[]>([])
const submitting = ref(false)

// Input for tags
const tagInput = ref('')

const form = ref({
  platforms: [] as number[],  // 多选平台（默认不选中）
  selectedFile: '', // Single file string
  accountList: [] as number[],
  title: '',
  description: '',
  tags: [] as string[]
})

const platforms = [
  { label: '抖音', value: 3, icon: 'VideoPlay', color: '#000000', iconClass: 'douyin-icon' },
  { label: '小红书', value: 1, icon: 'Iphone', color: '#eb1e32', iconClass: 'xhs-icon' },
  { label: '视频号', value: 2, icon: 'ChatDotRound', color: '#07c160', iconClass: 'wx-icon' },
  { label: '快手', value: 4, icon: 'VideoCamera', color: '#ff4906', iconClass: 'ks-icon' },
  { label: 'B站', value: 5, icon: 'VideoCamera', color: '#00a1d6', iconClass: 'bilibili-icon' }
]

const suggestedTags = ['推荐', '热门', 'Vlog', '日常']

// 根据选中平台过滤账号（支持多平台）
const filteredAccounts = computed(() => {
  return accounts.value.filter(a => form.value.platforms.includes(a[1]))
})

// 切换平台选择
const togglePlatform = (platformValue: number) => {
  const index = form.value.platforms.indexOf(platformValue)
  if (index > -1) {
    // 允许完全取消选中
    form.value.platforms.splice(index, 1)
    // 清除该平台下的账号选择
    form.value.accountList = form.value.accountList.filter(accId => {
      const acc = accounts.value.find(a => a[0] === accId)
      return acc && form.value.platforms.includes(acc[1])
    })
  } else {
    form.value.platforms.push(platformValue)
  }
}

// 获取平台名称
const getPlatformName = (type: number) => {
  const p = platforms.find(item => item.value === type)
  return p ? p.label : '未知'
}

const toggleAccount = (acc: any) => {
  if (acc[4] !== 1) return 
  const id = acc[0]
  const index = form.value.accountList.indexOf(id)
  if (index > -1) {
    form.value.accountList.splice(index, 1)
  } else {
    form.value.accountList.push(id)
  }
}

// Tag Functions
const addTag = () => {
  const val = tagInput.value.trim()
  if (val && !form.value.tags.includes(val)) {
    form.value.tags.push(val)
  }
  tagInput.value = ''
}

const addSuggestedTag = (tag: string) => {
  if (!form.value.tags.includes(tag)) {
    form.value.tags.push(tag)
  }
}

const removeTag = (index: number) => {
  form.value.tags.splice(index, 1)
}

const handleBackspace = () => {
  if (tagInput.value === '' && form.value.tags.length > 0) {
    form.value.tags.pop()
  }
}

const loadData = async () => {
  try {
    const [filesRes, accountsRes] = await Promise.all([
      getFiles(),
      getAccounts()
    ])
    files.value = filesRes.data || []
    accounts.value = accountsRes.data || []
  } catch (error) {
    console.error('加载数据失败', error)
  }
}

const handleSubmit = async () => {
  if (!form.value.selectedFile) return ElMessage.warning('请选择要发布的视频')
  if (form.value.accountList.length === 0) return ElMessage.warning('请选择发布账号')
  if (!form.value.title) return ElMessage.warning('请输入视频标题')

  // 验证每个选中的平台是否至少有一个账号
  for (const platform of form.value.platforms) {
    const platformAccounts = form.value.accountList.filter(accId => {
      const acc = accounts.value.find(a => a[0] === accId)
      return acc && acc[1] === platform
    })
    if (platformAccounts.length === 0) {
      const platformName = getPlatformName(platform)
      return ElMessage.warning(`请为${platformName}选择至少一个发布账号`)
    }
  }

  submitting.value = true
  try {
    // 按平台分组账号
    const accountsByPlatform: Record<number, number[]> = {}
    for (const platform of form.value.platforms) {
      accountsByPlatform[platform] = form.value.accountList.filter(accId => {
        const acc = accounts.value.find(a => a[0] === accId)
        return acc && acc[1] === platform
      })
    }

    // 发送多平台参数
    const payload = {
      platforms: form.value.platforms,
      accountsByPlatform,
      fileList: [form.value.selectedFile],
      title: form.value.title,
      description: form.value.description,
      tags: form.value.tags
    }
    
    await postVideo(payload as any)
    ElMessage.success(`🎉 已创建 ${form.value.platforms.length} 个发布任务！正在后台执行...`)
    
    // 重置表单
    form.value = {
      platforms: form.value.platforms,  // 保留平台选择
      selectedFile: '',
      accountList: [],
      title: '',
      description: '',
      tags: []
    }
    tagInput.value = ''
    
  } catch (error) {
    ElMessage.error('发布失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.page-container {
  height: calc(100vh - 84px); /* Adjust based on global header if needed, assuming compact */
  overflow: hidden;
  padding: 16px;
}

.scrollable-content {
  overflow-y: auto;
  flex: 1;
  padding: 0 4px; /* Space for scrollbar */
}

/* Compact Grid */
.grid-row-2 {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 20px;
}

.compact-item {
  margin-bottom: 16px;
}

/* Platform Chips */
.platform-compact-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.platform-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--el-border-color);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  background: #fff;
}

.platform-chip:hover {
  background: var(--bg-color-hover);
}

.platform-chip.active {
  background: var(--primary-color);
  color: #fff;
  border-color: var(--primary-color);
}

/* Account Chips */
.account-scroll-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 80px;
  overflow-y: auto;
}

.account-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 20px;
  border: 1px solid var(--el-border-color);
  background: #fff;
  cursor: pointer;
  font-size: 12px;
  width: auto;
  min-width: 100px;
  transition: all 0.2s;
}

.account-chip:hover { border-color: var(--primary-color); }

.account-chip.active {
  background: rgba(99, 102, 241, 0.1);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.account-chip.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #f3f4f6;
}

.param-avatar.tiny {
  width: 20px;
  height: 20px;
  font-size: 10px;
  background: #e0e7ff;
  color: var(--primary-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-left: auto;
}
.status-indicator.ok { background: var(--success-color); }
.status-indicator.err { background: var(--danger-color); }

/* Tag Input */
.tags-input-container {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  padding: 4px 12px;
  background: #fff;
  cursor: text;
  transition: all 0.22s;
  min-height: 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.tags-input-container:hover {
  border-color: var(--el-border-color-hover);
}

.tags-input-container:focus-within {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 1px var(--el-color-primary) inset;
}

.tags-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.native-input {
  border: none;
  outline: none;
  flex: 1;
  min-width: 100px;
  font-size: 14px;
  color: var(--text-color);
  background: transparent;
  padding: 4px 0;
}

.suggestion-chip {
  cursor: pointer;
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  margin-right: 6px;
  transition: all 0.2s;
}

.suggestion-chip:hover {
  background: var(--primary-color);
  color: #fff;
}

/* Mobile Preview Frame */
.mobile-frame {
  width: 240px;
  height: 480px;
  background: #000;
  border-radius: 30px;
  border: 8px solid #333;
  position: relative;
  overflow: hidden;
  box-shadow: 0 0 20px rgba(0,0,0,0.5);
}

.preview-content {
  height: 100%;
  width: 100%;
  position: relative;
  color: #fff;
}

.preview-video-area {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1f2937;
}

.preview-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  padding: 16px;
  background: linear-gradient(to top, rgba(0,0,0,0.8), transparent 100%);
}

.preview-text.title { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
.preview-text.desc { font-size: 12px; opacity: 0.9; margin-bottom: 8px; line-height: 1.4; }

.preview-tags-line {
  font-size: 12px; 
  color: #fbbf24;
}

.side-bar {
  position: absolute;
  right: 8px;
  bottom: 100px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
}

.side-icon {
  width: 32px;
  height: 32px;
  background: rgba(255,255,255,0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80px;
}
</style>
