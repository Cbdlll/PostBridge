<template>
  <div class="tasks-page page-container">
    <div class="page-header">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange" class="flex-1">
        <el-tab-pane label="AI获客任务" name="ai" />
        <el-tab-pane label="手动发布任务" name="manual" />
      </el-tabs>
      <div class="header-actions">
        <el-input 
          v-model="searchQuery" 
          placeholder="搜索标题或主题..." 
          clearable
          style="width: 250px;"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select 
          v-model="platformFilter" 
          placeholder="选择平台" 
          clearable
          style="width: 140px;"
        >
          <el-option label="全部平台" :value="null" />
          <el-option label="小红书" :value="1" />
          <el-option label="视频号" :value="2" />
          <el-option label="抖音" :value="3" />
          <el-option label="快手" :value="4" />
        </el-select>
        <el-button 
          v-if="selectedTasks.length > 0" 
          type="danger" 
          @click="handleBatchDelete"
        >
          批量删除 ({{ selectedTasks.length }})
        </el-button>
        <el-button type="primary" @click="refreshTasks">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <div class="card mt-4">
      <el-table 
        :data="filteredTasks" 
        stripe 
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column v-if="activeTab === 'ai'" prop="topic" label="主题" min-width="180" />
        <el-table-column prop="title" label="标题" min-width="200">
          <template #default="{ row }">
            <!-- AI任务根据状态显示 -->
            <template v-if="activeTab === 'ai'">
              <el-tag v-if="row.status === 'prompt_pending' || row.status === 'prompt_generating'" type="info" size="small">
                待生成
              </el-tag>
              <el-tag v-else-if="row.status === 'prompt_completed'" type="warning" size="small">
                待选择
              </el-tag>
              <span v-else>{{ row.title || '-' }}</span>
            </template>
            <!-- 手动任务直接显示标题 -->
            <span v-else>{{ row.title || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="platform" label="平台" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="getPlatformType(row.platform)">
              {{ getPlatformName(row.platform) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="180">
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <!-- 优先显示验证码状态 -->
              <template v-if="row.status === 'need_verification' || row.publish_status === 'need_verification'">
                <el-tag type="warning" size="small" effect="dark">
                  需要验证码
                </el-tag>
              </template>
              <!-- 然后显示发布状态 -->
              <template v-else-if="row.publish_status">
                <el-tag :type="getPublishStatusType(row.publish_status)" size="small">
                  {{ getPublishStatusText(row.publish_status) }}
                </el-tag>
                <el-tooltip v-if="row.publish_status === 'publish_failed' && row.publish_error" :content="row.publish_error">
                  <el-icon class="text-danger"><Warning /></el-icon>
                </el-tooltip>
              </template>
              <!-- 否则显示任务状态 -->
              <template v-else>
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ getStatusText(row.status) }}
                </el-tag>
                <el-tooltip v-if="row.status === 'prompt_failed' && row.error_message" :content="row.error_message">
                  <el-icon class="text-danger"><Warning /></el-icon>
                </el-tooltip>
              </template>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <!-- 验证码输入按钮 -->
              <el-button 
                v-if="row.status === 'need_verification' || row.publish_status === 'need_verification'"
                type="warning" 
                link 
                size="small" 
                @click="openVerificationDialog(row)"
              >
                输入
              </el-button>
              <!-- AI 任务：文案生成完成后可继续 -->
              <el-button 
                v-if="activeTab === 'ai' && row.status === 'prompt_completed'"
                type="success" 
                link 
                size="small" 
                @click="continueTask(row)"
              >
                 继续
              </el-button>
              <el-button type="primary" link size="small" @click="viewDetail(row)">
                 详情
              </el-button>
              <el-button type="danger" link size="small" @click="handleDelete(row)">
                 删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="任务详情" width="600px">
      <el-descriptions :column="1" border v-if="currentTask">
        <el-descriptions-item label="ID">{{ currentTask.id }}</el-descriptions-item>
        <el-descriptions-item v-if="activeTab === 'ai'" label="主题">{{ currentTask.topic }}</el-descriptions-item>
        <el-descriptions-item label="标题">{{ currentTask.title || '-' }}</el-descriptions-item>
        <el-descriptions-item label="简介">{{ currentTask.description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentTask.status)">
            {{ getStatusText(currentTask.status) }}
          </el-tag>
          <div v-if="currentTask.error_message" class="mt-2 text-xs" style="color: var(--el-color-danger);">
            <strong>失败原因：</strong>{{ currentTask.error_message }}
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ currentTask.created_at }}</el-descriptions-item>
        <el-descriptions-item v-if="currentTask.video_path || currentTask.local_video_path" label="视频路径">
           {{ currentTask.video_path || currentTask.local_video_path }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- AI 任务继续对话框：选择方案 -->
    <el-dialog 
      v-model="continueDialogVisible" 
      title="选择生成方案" 
      width="1200px"
      top="5vh"
      class="large-dialog"
    >
      <div v-if="promptResults.length > 0" class="results-grid" style="height: 75vh; min-height: 700px;">
        <div 
          v-for="(item, index) in promptResults" 
          :key="index"
          class="result-card"
          :class="{ active: selectedResultIndex === index }"
          @click="selectedResultIndex = index"
        >
          <div class="flex justify-between items-start mb-2">
             <div class="result-title">{{ item.title }}</div>
             <el-icon v-if="selectedResultIndex === index" color="var(--el-color-success)"><Select /></el-icon>
          </div>
          <div class="result-desc">{{ item.description }}</div>
          <div class="result-tags">
             <el-tag v-for="tag in item.tags" :key="tag" size="small" effect="plain">#{{ tag }}</el-tag>
          </div>
          <div class="result-prompt">
             <div class="prompt-label">画面提示词：</div>
             <div class="prompt-text">{{ item.video_prompt }}</div>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无生成结果" />
      
      <template #footer>
        <el-button @click="continueDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="openEditDialog" :disabled="selectedResultIndex < 0">
          编辑选中方案
        </el-button>
      </template>
    </el-dialog>

    <!-- 编辑方案对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑并提交" width="600px">
      <el-form v-if="editingResult" label-position="top">
         <el-form-item label="视频标题">
            <el-input v-model="editingResult.title" placeholder="请输入视频标题" />
         </el-form-item>

         <el-form-item label="视频简介">
            <el-input 
                v-model="editingResult.description" 
                type="textarea" 
                :rows="2"
                placeholder="请输入视频简介" 
            />
         </el-form-item>

         <el-form-item label="话题标签">
            <el-select
                v-model="editingResult.tags"
                multiple
                filterable
                allow-create
                default-first-option
                :reserve-keyword="false"
                placeholder="请输入标签并回车"
                style="width: 100%"
            >
            </el-select>
         </el-form-item>

         <el-form-item label="画面提示词 (Prompt)">
            <el-input 
                v-model="editingResult.video_prompt" 
                type="textarea" 
                :rows="6"
                placeholder="生成视频的详细提示词..." 
            />
         </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button 
          type="success" 
          @click="submitVideoGeneration"
          :loading="submitting"
          :disabled="!editingResult?.video_prompt"
        >
          <el-icon class="mr-2"><VideoPlay /></el-icon>
          保存并生成视频
        </el-button>
      </template>
    </el-dialog>

    <!-- 验证码输入对话框 -->
    <el-dialog v-model="verificationDialogVisible" title="输入验证码" width="400px">
      <div class="verification-container">
        <el-alert 
          v-if="verificationError" 
          :title="verificationError" 
          type="error" 
          show-icon 
          class="mb-4"
        />
        <p class="mb-4" style="color: #666;">请输入您收到的6位数字验证码</p>
        <p class="mb-4" style="color: #666;">仔细核对，不要输入错误！</p>
        <el-input 
          v-model="verificationCode" 
          placeholder="请输入6位数字验证码" 
          size="large"
          maxlength="6"
          @input="handleVerificationInput"
          @keyup.enter="submitVerification"
        />
      </div>
      <template #footer>
        <el-button @click="verificationDialogVisible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="submitVerification"
          :loading="verificationSubmitting"
          :disabled="!isVerificationCodeValid"
        >
          提交验证码
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Warning, Select, VideoPlay, Search } from '@element-plus/icons-vue'
import { getPublishTasks, deletePublishTask, deleteTask, getTasks, getCreationTaskStatus, continueTaskWithVideo, submitVerificationCode } from '@/api'
import eventBus from '@/utils/eventBus'

const route = useRoute()

// 从 URL 参数获取初始 tab，只接受有效值
const getInitialTab = () => {
  const tabParam = route.query.tab as string
  const validTabs = ['manual', 'ai']
  return validTabs.includes(tabParam) ? tabParam : 'ai'
}

const activeTab = ref(getInitialTab())
const loading = ref(false)
const tasks = ref<any[]>([])
const detailVisible = ref(false)
const currentTask = ref<any>(null)
let timer: any = null

// 搜索和过滤相关状态
const searchQuery = ref('')
const platformFilter = ref<number | null>(null)
const selectedTasks = ref<any[]>([])

// 过滤后的任务列表
const filteredTasks = computed(() => {
  let result = tasks.value
  
  // 平台过滤
  if (platformFilter.value !== null) {
    result = result.filter(task => task.platform === platformFilter.value)
  }
  
  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(task => {
      const title = (task.title || '').toLowerCase()
      const topic = (task.topic || '').toLowerCase()
      return title.includes(query) || topic.includes(query)
    })
  }
  
  return result
})

// AI 任务继续相关状态
const continueDialogVisible = ref(false)
const editDialogVisible = ref(false)
const promptResults = ref<any[]>([])
const selectedResultIndex = ref(-1)
const editingResult = ref<any>(null)
const editingTaskId = ref<number | null>(null)
const submitting = ref(false)

// 验证码相关状态
const verificationDialogVisible = ref(false)
const verificationCode = ref('')
const verificationError = ref('')
const verificationSubmitting = ref(false)
const verificationTaskId = ref('')
const verificationTaskType = ref<'manual' | 'ai'>('manual')

// 验证码是否有效（6位数字）
const isVerificationCodeValid = computed(() => /^\d{6}$/.test(verificationCode.value))

// 只允许输入数字
const handleVerificationInput = (value: string) => {
  verificationCode.value = value.replace(/\D/g, '')
}

const handleTabChange = () => {
  loadTasks()
}

const getPlatformName = (p: any) => {
  const map: any = { 1: '小红书', 2: '视频号', 3: '抖音', 4: '快手', 5: 'B站' }
  return map[p] || p || '-'
}

const getPlatformType = (p: any) => {
  const map: any = { 1: 'danger', 2: 'success', 3: 'info', 4: 'warning', 5: 'primary' }
  return map[p] || 'info'
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    need_verification: 'warning',
    prompt_pending: 'info',
    prompt_generating: 'warning',
    prompt_completed: 'success',
    prompt_failed: 'danger',
    video_pending: 'info',
    video_generating: 'warning',
    video_completed: 'success',
    video_failed: 'danger',
    completed: 'success',
    published: 'success',
    failed: 'danger',
    pending: 'info',
    running: 'primary',
    generating: 'warning'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    need_verification: '需要验证码',
    prompt_pending: '待生成文案',
    prompt_generating: '文案生成中',
    prompt_completed: '文案已生成',
    prompt_failed: '文案生成失败',
    video_pending: '待生成视频',
    video_generating: '视频生成中',
    video_completed: '视频已生成',
    video_failed: '视频生成失败',
    completed: '已完成',
    published: '已发布',
    failed: '失败',
    pending: '待处理',
    running: '执行中',
    generating: '生成中'
  }
  return map[status] || status
}

// 发布状态类型
const getPublishStatusType = (status: string) => {
  const map: Record<string, string> = {
    publishing: 'warning',
    published: 'success',
    publish_failed: 'danger'
  }
  return map[status] || 'info'
}

// 发布状态文本
const getPublishStatusText = (status: string) => {
  const map: Record<string, string> = {
    need_verification: '需要验证码',
    publishing: '发布中',
    published: '已发布',
    publish_failed: '发布失败'
  }
  return map[status] || status
}

const loadTasks = async () => {
  loading.value = true
  try {
    if (activeTab.value === 'manual') {
      const res = await getPublishTasks('manual')
      tasks.value = res.data || []
    } else {
      const res = await getTasks()
      tasks.value = res.data || []
    }
  } catch (error) {
    console.error('加载任务失败', error)
  } finally {
    loading.value = false
  }
}

const refreshTasks = () => {
  loadTasks()
  ElMessage.success('刷新成功')
}

const viewDetail = (row: any) => {
  currentTask.value = row
  detailVisible.value = true
}

// AI 任务继续：打开方案选择对话框
const continueTask = async (row: any) => {
  editingTaskId.value = row.id
  selectedResultIndex.value = -1
  
  // 获取最新任务状态
  try {
    const res = await getCreationTaskStatus(row.id)
    const task = res.data
    
    if (task.prompt_results && Array.isArray(task.prompt_results)) {
      promptResults.value = task.prompt_results
    } else if (typeof task.prompt_results === 'string') {
      promptResults.value = JSON.parse(task.prompt_results)
    } else {
      promptResults.value = []
    }
    
    continueDialogVisible.value = true
  } catch (e) {
    console.error(e)
    ElMessage.error('获取任务详情失败')
  }
}

// 打开编辑对话框
const openEditDialog = () => {
  if (selectedResultIndex.value >= 0 && promptResults.value[selectedResultIndex.value]) {
    editingResult.value = JSON.parse(JSON.stringify(promptResults.value[selectedResultIndex.value]))
    continueDialogVisible.value = false
    editDialogVisible.value = true
  }
}

// 提交视频生成
const submitVideoGeneration = async () => {
  if (!editingResult.value?.video_prompt || !editingTaskId.value) return
  
  submitting.value = true
  
  try {
    // 获取 API 配置
    const apiConfig = JSON.parse(localStorage.getItem('api_config') || '{}')
    
    // 调用新API:更新现有任务而非创建新任务
    await continueTaskWithVideo(editingTaskId.value, {
      title: editingResult.value.title || '',
      description: editingResult.value.description || '',
      tags: editingResult.value.tags || [],
      video_prompt: editingResult.value.video_prompt,
      video_config: {
        provider: apiConfig.videoProvider || 'mock',
        // 只传递当前 provider 对应的 API Key
        wanApiKey: apiConfig.videoProvider === 'wanxiang' ? apiConfig.wanApiKey : '',
        transit2ApiKey: apiConfig.videoProvider === 'sora' ? apiConfig.transit2ApiKey : '',
        doubaoApiKey: apiConfig.videoProvider === 'doubao' ? apiConfig.doubaoApiKey : '',
        mockVideoUrl: apiConfig.videoProvider === 'mock' ? apiConfig.mockVideoUrl : '',
        // 时长
        duration: apiConfig.videoProvider === 'sora' ? apiConfig.transit2Duration : apiConfig.videoDuration,
        // 当前 provider 的模型
        transit2Model: apiConfig.videoProvider === 'sora' ? apiConfig.transit2Model : '',
        doubaoModel: apiConfig.videoProvider === 'doubao' ? apiConfig.doubaoModel : '',
        wanxiangModel: apiConfig.videoProvider === 'wanxiang' ? apiConfig.wanxiangModel : '',
        // Wanxiang 专属参数
        shotType: apiConfig.videoProvider === 'wanxiang' ? apiConfig.videoShotType : undefined,
        watermark: apiConfig.videoProvider === 'wanxiang' ? apiConfig.videoWatermark : undefined
      }
    })
    
    ElMessage.success('视频生成已开始')
    editDialogVisible.value = false
    loadTasks()
    
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error.response?.data?.msg || '提交失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定要删除该任务吗？', '提示', {
      type: 'warning'
    })
    if (activeTab.value === 'manual') {
      await deletePublishTask(row.id)
    } else {
      await deleteTask(row.id)
    }
    ElMessage.success('删除成功')
    loadTasks()
  } catch (error) {
    // 用户取消
  }
}

// 处理选择变化
const handleSelectionChange = (selection: any[]) => {
  selectedTasks.value = selection
}

// 批量删除
const handleBatchDelete = async () => {
  if (selectedTasks.value.length === 0) {
    ElMessage.warning('请先选择要删除的任务')
    return
  }
  
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedTasks.value.length} 个任务吗？`, '提示', {
      type: 'warning'
    })
    
    // 依次删除所有选中的任务
    for (const task of selectedTasks.value) {
      if (activeTab.value === 'manual') {
        await deletePublishTask(task.id)
      } else {
        await deleteTask(task.id)
      }
    }
    
    ElMessage.success('批量删除成功')
    selectedTasks.value = []
    loadTasks()
  } catch (error) {
    // 用户取消
  }
}

// 打开验证码输入对话框
const openVerificationDialog = (row: any) => {
  verificationCode.value = ''
  verificationError.value = ''
  // 根据任务类型构造 taskId
  if (activeTab.value === 'manual') {
    verificationTaskId.value = `manual_${row.id}`
    verificationTaskType.value = 'manual'
  } else {
    verificationTaskId.value = `ai_${row.id}`
    verificationTaskType.value = 'ai'
  }
  verificationDialogVisible.value = true
}

// 提交验证码
const submitVerification = async () => {
  if (!verificationCode.value) return
  
  verificationSubmitting.value = true
  verificationError.value = ''
  
  try {
    const res = await submitVerificationCode(verificationTaskId.value, verificationCode.value) as any
    
    if (res?.data?.status === 'success') {
      // 验证成功
      ElMessage.success('验证码验证成功！发布继续进行中...')
      verificationDialogVisible.value = false
      // 刷新任务列表
      loadTasks()
    } else if (res?.data?.status === 'failed') {
      // 验证失败，提示重新输入，不关闭弹窗
      verificationError.value = '验证码错误，请重新输入'
      verificationCode.value = ''
    } else if (res?.data?.status === 'timeout') {
      verificationError.value = '等待验证结果超时，请重试'
    } else {
      // 其他情况，关闭弹窗
      ElMessage.info('验证码已提交')
      verificationDialogVisible.value = false
      loadTasks()
    }
  } catch (error: any) {
    console.error(error)
    verificationError.value = error.response?.data?.msg || '提交失败，请重试'
  } finally {
    verificationSubmitting.value = false
  }
}

// 轮询更新状态(每分钟一次)
onMounted(() => {
  loadTasks()
  // 监听刷新事件
  eventBus.on('refreshData', loadTasks)
  
  timer = setInterval(() => {
    const hasRunning = tasks.value.some(t => 
      ['prompt_pending', 'prompt_generating', 'video_generating', 'running', 'generating'].includes(t.status) ||
      t.publish_status === 'publishing'
    )
    if (hasRunning) {
      loadTasks()
    }
  }, 60000)  // 每分钟轮询一次
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  // 移除事件监听
  eventBus.off('refreshData', loadTasks)
})
</script>

<style scoped>
/* 大对话框样式 */
.large-dialog :deep(.el-dialog__body) {
  min-height: 80vh;
  max-height: 85vh;
  overflow-y: hidden;
  padding: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.text-danger {
  color: var(--el-color-danger);
}
.mt-4 { margin-top: 16px; }
.gap-2 { gap: 8px; }
.action-buttons {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  white-space: nowrap;
}

/* 结果网格 */
.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.result-card {
  background: #f8fafc;
  border: 2px solid var(--el-border-color);
  padding: 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.result-card:hover {
  border-color: var(--el-color-primary);
  background: #f0f9ff;
}

.result-card.active {
  border-color: var(--el-color-success);
  background: #f0fdf4;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}

.result-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  line-height: 1.4;
  margin-bottom: 8px;
}

.result-desc {
  font-size: 13px;
  color: #666;
  margin: 10px 0;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.result-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}

.result-prompt {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.prompt-label {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 6px;
}

.prompt-text {
  font-size: 12px;
  color: #4b5563;
  line-height: 1.6;
  overflow-y: auto;
  background: #f9fafb;
  padding: 10px;
  border-radius: 4px;
  flex: 1;
  min-height: 150px;
}

/* 调整网格为更大的卡片 */
.results-grid {
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  height: 80vh;
  overflow-y: auto;
  gap: 20px;
}
</style>
