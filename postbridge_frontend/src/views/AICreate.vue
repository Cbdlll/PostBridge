<template>
  <div class="ai-create-page page-container" style="padding-top: 5px;">
    <div class="card" style="max-width: 1000px; margin: 0 auto;">
      <div class="card-header">
        <span class="card-title">AI 获客任务创建</span>
        <div v-if="llmModel" class="header-tag">
           当前模型: {{ llmModel }}
        </div>
      </div>
      
      <div class="card-content" style="min-height: 600px;">
        <el-form :model="form" label-position="top">
           <!-- 第一行：创作主题 -->
           <el-form-item label="创作主题" required>
              <el-input 
                v-model="form.topic" 
                placeholder="例如：智能手表推荐、新年穿搭分享"
                size="large"
              >
                <template #prefix>
                   <el-icon><EditPen /></el-icon>
                </template>
              </el-input>
              <div class="form-tip">输入产品名称或话题，AI 将自动生成营销文案</div>
           </el-form-item>

           <!-- 第二行：平台、风格、数量 -->
           <div class="grid grid-cols-3 gap-4">
             <el-form-item label="目标平台（可多选）">
                <div class="platform-chips">
                  <div 
                    v-for="p in platformOptions" 
                    :key="p.value"
                    class="platform-chip"
                    :class="{ active: form.platforms.includes(p.value) }"
                    @click="togglePlatform(p.value)"
                  >
                    {{ p.label }}
                  </div>
                </div>
                <div class="form-tip" v-if="form.platforms.length > 1">已选 {{ form.platforms.length }} 个平台，将分别应用对应用户画像生成内容</div>
             </el-form-item>
             
             <el-form-item label="内容风格">
                <el-select 
                  v-model="form.style" 
                  size="large" 
                  style="width: 100%"
                  filterable
                  allow-create
                  default-first-option
                  placeholder="选择或输入自定义风格"
                >
                  <el-option label="真实风" value="真实风" />
                  <el-option label="动漫风" value="动漫风" />
                  <el-option label="3D渲染风" value="3D渲染风" />
                  <el-option label="水彩画风" value="水彩画风" />
                  <el-option label="油画风" value="油画风" />
                  <el-option label="简约风" value="简约风" />
                </el-select>
             </el-form-item>

             <el-form-item label="生成数量">
                <el-select v-model="form.count" size="large" style="width: 100%">
                  <el-option label="1 个方案" :value="1" />
                  <el-option label="2 个方案" :value="2" />
                  <el-option label="3 个方案" :value="3" />
                  <el-option label="4 个方案" :value="4" />
                  <el-option label="5 个方案" :value="5" />
                </el-select>
             </el-form-item>
           </div>

           <el-divider content-position="left">发布设置</el-divider>

           <!-- 第三行：发布账号（按平台分组） -->
           <el-form-item label="发布账号" required>
              <div v-if="form.platforms.length === 0" class="form-tip">请先选择目标平台</div>
              <div v-else class="accounts-by-platform">
                <div v-for="platform in form.platforms" :key="platform" class="platform-accounts-group">
                  <div class="platform-group-header">
                    <span class="platform-label">{{ getPlatformLabel(platform) }}</span>
                  </div>
                  <div class="account-chips">
                    <div 
                      v-for="acc in getAccountsByPlatform(platform)" 
                      :key="acc[0]"
                      class="account-chip"
                      :class="{ active: isAccountSelected(platform, acc[0]), disabled: acc[4] !== 1 }"
                      @click="toggleAccount(platform, acc)"
                    >
                      <span>{{ acc[3] }}</span>
                      <el-tag size="small" :type="acc[4] === 1 ? 'success' : 'danger'">
                        {{ acc[4] === 1 ? '有效' : '失效' }}
                      </el-tag>
                    </div>
                    <div v-if="getAccountsByPlatform(platform).length === 0" class="form-tip">
                      暂无{{ getPlatformLabel(platform) }}账号
                    </div>
                  </div>
                </div>
              </div>
           </el-form-item>

            <!-- 自动发布开关 -->
            <el-form-item>
              <div style="display: flex; align-items: center; gap: 16px;">
                <el-switch 
                  v-model="form.autoPublish" 
                  size="large"
                  active-text="自动发布"
                  inactive-text="手动发布"
                  :disabled="!hasSelectedAccounts"
                  @change="handleAutoPublishChange"
                />
                <div class="form-tip" style="margin: 0;">
                  <el-icon><InfoFilled /></el-icon>
                  开启后,视频生成完成将自动发布到选定账号
                </div>
              </div>
            </el-form-item>

           <!-- 第四行：Mock选项和提交按钮 -->
           <div class="grid grid-cols-2 gap-4 items-end">
             <el-form-item>
                <el-checkbox v-model="form.useMock" label="使用模拟生成 (Mock)" border size="large" />
             </el-form-item>

             <el-button 
               type="primary" 
               size="large" 
               @click="createTask" 
               :loading="creating"
             >
                <el-icon class="mr-2"><MagicStick /></el-icon>
                创建 AI 获客任务
             </el-button>
           </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick, EditPen, Select, InfoFilled } from '@element-plus/icons-vue'
import { createPrompt, getAccounts, getTasks } from '@/api'

// 最大同时进行任务数
const MAX_RUNNING_TASKS = 5

const router = useRouter()

const form = ref({
  topic: '',
  platforms: [] as string[],  // 多选平台（默认不选中）
  style: '真实风',
  useMock: false,
  count: 1,
  accountsByPlatform: {} as Record<string, number[]>,  // 按平台分组的账号ID
  autoPublish: true
})

const creating = ref(false)
const apiConfig = ref<any>({})

// 账号管理
const accounts = ref<any[]>([])
const loadingAccounts = ref(false)

// 平台选项
const platformOptions = [
  { label: '抖音', value: 'douyin', num: 3 },
  { label: '小红书', value: 'xhs', num: 1 },
  { label: '快手', value: 'ks', num: 4 },
  { label: '视频号', value: 'wx', num: 2 },
  { label: 'B站', value: 'bilibili', num: 5 }
]

// 平台映射
const PLATFORM_MAP: Record<string, number> = {
  douyin: 3,
  xhs: 1,
  ks: 4,
  wx: 2,
  bilibili: 5
}

const PLATFORM_NAMES: Record<number, string> = {
  1: '小红书',
  2: '视频号',
  3: '抖音',
  4: '快手',
  5: 'B站'
}

const platformName = (type: number) => PLATFORM_NAMES[type] || '未知'

// 获取平台显示名称
const getPlatformLabel = (platformCode: string) => {
  const opt = platformOptions.find(p => p.value === platformCode)
  return opt ? opt.label : platformCode
}

// 切换平台选择
const togglePlatform = (platformCode: string) => {
  const index = form.value.platforms.indexOf(platformCode)
  if (index > -1) {
    // 允许完全取消选中
    form.value.platforms.splice(index, 1)
    // 清除该平台的账号选择
    delete form.value.accountsByPlatform[platformCode]
  } else {
    form.value.platforms.push(platformCode)
    form.value.accountsByPlatform[platformCode] = []
  }
}

// 根据平台获取账号
const getAccountsByPlatform = (platformCode: string) => {
  const platformNum = PLATFORM_MAP[platformCode]
  return accounts.value.filter(acc => acc[1] === platformNum)
}

// 检查账号是否被选中
const isAccountSelected = (platformCode: string, accountId: number) => {
  return form.value.accountsByPlatform[platformCode]?.includes(accountId) ?? false
}

// 切换账号选择
const toggleAccount = (platformCode: string, acc: any) => {
  if (acc[4] !== 1) return  // 失效账号不可选
  
  const accountId = acc[0]
  if (!form.value.accountsByPlatform[platformCode]) {
    form.value.accountsByPlatform[platformCode] = []
  }
  
  const list = form.value.accountsByPlatform[platformCode]
  const index = list.indexOf(accountId)
  if (index > -1) {
    list.splice(index, 1)
  } else {
    list.push(accountId)
  }
}

// 是否有选中的账号
const hasSelectedAccounts = computed(() => {
  return form.value.platforms.some(p => 
    (form.value.accountsByPlatform[p]?.length ?? 0) > 0
  )
})

// 平台标签颜色
const getPlatformTagType = (p: number) => {
  const map: Record<number, string> = { 1: 'danger', 2: 'success', 3: 'info', 4: 'warning' }
  return map[p] || 'info'
}

// 注意：不再监听 accountsByPlatform 的变化来自动关闭 autoPublish
// 只在 hasSelectedAccounts 为 false 时通过 :disabled 禁用开关即可

// 切换到手动发布时二次确认
const handleAutoPublishChange = async (value: boolean) => {
  // 如果是从自动切换到手动,需要确认
  if (value === false) {
    try {
      await ElMessageBox.confirm(
        '关闭自动发布后,视频生成完成需要手动发布。确定要切换到手动发布吗?',
        '确认切换',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      // 用户确认,保持 false
    } catch {
      // 用户取消,恢复为 true
      form.value.autoPublish = true
    }
  }
}

const loadAccounts = async () => {
  loadingAccounts.value = true
  try {
    const res = await getAccounts()
    accounts.value = res.data || []
  } catch (e) {
    console.error('Failed to load accounts', e)
  } finally {
    loadingAccounts.value = false
  }
}

const llmModel = computed(() => apiConfig.value.llmModel || '')

onMounted(() => {
  const saved = localStorage.getItem('api_config')
  if (saved) {
    try {
      apiConfig.value = JSON.parse(saved)
    } catch (e) {
      console.error('Failed to load api config', e)
    }
  }
  
  if (!apiConfig.value.llmApiKey) {
      form.value.useMock = true
  }
  
  loadAccounts()
})

// 创建任务
const createTask = async () => {
  if (!form.value.topic) {
    ElMessage.warning('请输入创作主题')
    return
  }
  
  // 验证每个平台至少有一个账号
  for (const platform of form.value.platforms) {
    const accounts = form.value.accountsByPlatform[platform] || []
    if (accounts.length === 0) {
      ElMessage.warning(`请为${getPlatformLabel(platform)}选择至少一个发布账号`)
      return
    }
  }

  creating.value = true

  try {
    // 检查进行中任务数量
    const tasksRes = await getTasks()
    const tasks = tasksRes.data || []
    const runningTasks = tasks.filter((t: any) => 
      ['prompt_pending', 'prompt_generating', 'video_pending', 'video_generating'].includes(t.status)
    )
    
    // 多平台时，检查总任务数
    const newTaskCount = form.value.platforms.length
    if (runningTasks.length + newTaskCount > MAX_RUNNING_TASKS) {
      ElMessage.warning(`当前有 ${runningTasks.length} 个任务进行中，新建 ${newTaskCount} 个将超过最大限制（${MAX_RUNNING_TASKS}个）`)
      creating.value = false
      return
    }

    // 发送多平台参数
    const res = await createPrompt({
      topic: form.value.topic,
      platforms: form.value.platforms,  // 多选平台
      accounts_by_platform: form.value.accountsByPlatform,  // 按平台分组账号
      style: form.value.style,
      use_mock: form.value.useMock,
      count: form.value.count,
      auto_publish: form.value.autoPublish,
      llm_config: apiConfig.value
    } as any)
    
    const taskIds = res.data?.task_ids || [res.data?.task_id]
    if (!taskIds || taskIds.length === 0) {
      throw new Error('任务创建失败')
    }
    
    // 成功提示
    await ElMessageBox.confirm(
      `已创建 ${taskIds.length} 个AI获客任务！AI 正在生成文案，您可以到任务管理页面查看任务详情和进度。`,
      '任务已创建',
      {
        confirmButtonText: '前往任务管理',
        cancelButtonText: '继续创建',
        type: 'success'
      }
    ).then(() => {
      router.push('/tasks?tab=ai')
    }).catch(() => {
      // 继续创建 - 重置表单
    })
    
    // 重置表单
    form.value.topic = ''
    form.value.count = 1
    form.value.accountsByPlatform = {}
    for (const p of form.value.platforms) {
      form.value.accountsByPlatform[p] = []
    }
    
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error.response?.data?.msg || '任务创建失败')
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.form-tip {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.header-tag {
    font-size: 12px;
    background: var(--bg-color);
    padding: 4px 10px;
    border-radius: 4px;
    color: #666;
    margin-left: auto;
}

.account-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.account-tags {
  display: flex;
  gap: 4px;
}

.auto-publish-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--el-color-success);
}

/* 平台多选样式 */
.platform-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.platform-chip {
  padding: 8px 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  background: #fff;
}

.platform-chip:hover {
  border-color: var(--el-color-primary);
}

.platform-chip.active {
  background: var(--el-color-primary);
  color: #fff;
  border-color: var(--el-color-primary);
}

/* 账号分组样式 - 横向排列 */
.accounts-by-platform {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 12px;
}

.platform-accounts-group {
  background: #f9fafb;
  border-radius: 6px;
  padding: 10px 12px;
  flex: 1;
  min-width: 200px;
  max-width: 300px;
}

.platform-group-header {
  margin-bottom: 6px;
}

.platform-label {
  font-weight: 600;
  font-size: 12px;
  color: #374151;
}

.account-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.account-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid var(--el-border-color);
  border-radius: 16px;
  cursor: pointer;
  font-size: 12px;
  background: #fff;
  transition: all 0.2s;
}

.account-chip:hover {
  border-color: var(--el-color-primary);
}

.account-chip.active {
  background: rgba(99, 102, 241, 0.1);
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}

.account-chip.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
