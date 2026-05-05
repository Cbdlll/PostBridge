<template>
  <div class="accounts-page page-container">
    <div class="page-header" style="justify-content: flex-end; gap: 12px;">
      <el-button 
        type="success"
        size="large" 
        @click="showAddDialog = true"
        style="color: #fff;"
      >
        <el-icon class="mr-2"><Plus /></el-icon>
        添加账号
      </el-button>
      <el-button 
        type="primary"
        color="#6366f1"
        size="large" 
        @click="syncAllStatus"
        :loading="syncingAll"
        style="color: #fff;"
      >
        <el-icon class="mr-2"><Refresh /></el-icon>
        {{ syncingAll ? '同步中...' : '同步状态' }}
      </el-button>
    </div>


    <div class="card">
      <el-table :data="accounts" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="平台" width="120">
          <template #default="{ row }">
             <div class="flex items-center gap-2">
                <el-icon><component :is="getPlatformIcon(row.type)" /></el-icon>
                <span>{{ getPlatformName(row.type) }}</span>
             </div>
          </template>
        </el-table-column>
        <el-table-column label="账号名称" min-width="150">
          <template #default="{ row }">
            <span v-if="!row.editing">{{ row.name }}</span>
            <el-input v-model="row.editName" size="small" v-else @blur="saveName(row)" @keyup.enter="saveName(row)" />
            <el-icon v-if="!row.editing" class="edit-icon" @click="startEdit(row)"><Edit /></el-icon>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '有效' : '失效' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="同步账号状态" placement="top">
                <el-button type="success" link @click="handleSyncStatus(row)" :loading="row.syncing">
                  <el-icon><Refresh /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="打开浏览器，可正常使用增加痕迹" placement="top">
                <el-button type="primary" link @click="handleOpenBrowser(row)" :loading="row.openingBrowser">
                  <el-icon><Monitor /></el-icon>
                </el-button>
              </el-tooltip>
              <el-popconfirm title="确定删除该账号吗？" @confirm="handleDelete(row)">
                <template #reference>
                  <el-button type="danger" link>删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 添加账号弹窗 -->
    <el-dialog
      v-model="showAddDialog"
      title="添加账号"
      width="480px"
      :close-on-click-modal="false"
    >
      <div class="add-account-dialog">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
        >
          <template #title>
            <span style="font-weight: 500;">操作步骤</span>
          </template>
          <ol style="margin: 8px 0 0 0; padding-left: 18px; line-height: 1.8;">
            <li>选择要添加的平台</li>
            <li>点击"开始登录"后会自动打开浏览器</li>
            <li>在浏览器中完成扫码/密码登录</li>
            <li><strong>登录成功后关闭浏览器</strong></li>
            <li>系统会自动检测并保存账号</li>
          </ol>
        </el-alert>

        <el-form label-width="80px">
          <el-form-item label="平台">
            <el-select v-model="addForm.platform" placeholder="请选择平台" style="width: 100%;">
              <el-option label="抖音" value="douyin">
                <el-icon style="margin-right: 8px;"><VideoPlay /></el-icon>
                <span>抖音</span>
              </el-option>
              <el-option label="小红书" value="xhs">
                <el-icon style="margin-right: 8px;"><Iphone /></el-icon>
                <span>小红书</span>
              </el-option>
              <el-option label="快手" value="kuaishou">
                <el-icon style="margin-right: 8px;"><VideoCamera /></el-icon>
                <span>快手</span>
              </el-option>
              <el-option label="B站" value="bilibili">
                <el-icon style="margin-right: 8px;"><VideoCamera /></el-icon>
                <span>B站</span>
              </el-option>
              <el-option label="视频号" value="shipinhao">
                <el-icon style="margin-right: 8px;"><ChatDotRound /></el-icon>
                <span>视频号</span>
              </el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="账号名称">
            <el-input 
              v-model="addForm.accountName" 
              placeholder="可选，用于区分多个账号" 
            />
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="handleStartLogin"
          :loading="addingAccount"
          :disabled="!addForm.platform"
        >
          {{ addingAccount ? '正在打开浏览器...' : '开始登录' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Edit, VideoPlay, Iphone, ChatDotRound, VideoCamera, Plus, Monitor } from '@element-plus/icons-vue'
import { getAccounts, getValidAccounts, deleteAccount, updateUserinfo, startLogin, openBrowser, syncAccountStatus } from '@/api'
import eventBus from '@/utils/eventBus'

const accounts = ref<any[]>([])
const loading = ref(false)
const syncingAll = ref(false)
const showAddDialog = ref(false)
const addingAccount = ref(false)

const addForm = ref({
  platform: '',
  accountName: ''
})

const getPlatformName = (type: number) => {
  const map: Record<number, string> = { 3: '抖音', 1: '小红书', 2: '视频号', 4: '快手', 5: 'B站' }
  return map[type] || '未知'
}

const getPlatformIcon = (type: number) => {
  const map: Record<number, string> = { 3: 'VideoPlay', 1: 'Iphone', 2: 'ChatDotRound', 4: 'VideoCamera', 5: 'VideoCamera' }
  return map[type] || 'VideoPlay'
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getAccounts()
    accounts.value = (res.data || []).map((item: any) => ({
      ...item,
      name: item[3],
      type: item[1],
      id: item[0],
      status: item[4],
      cookie_path: item[2],
      editing: false,
      editName: item[3],
      syncing: false,
      openingBrowser: false
    }))
  } catch (error) {
    console.error('加载账号失败', error)
  } finally {
    loading.value = false
  }
}

const startEdit = (row: any) => {
  row.editing = true
  row.editName = row.name
}

const saveName = async (row: any) => {
  if (row.editName === row.name) {
    row.editing = false
    return
  }
  try {
    await updateUserinfo({ id: row.id, name: row.editName, status: row.status })
    row.name = row.editName
    row.editing = false
    ElMessage.success('名称已更新')
  } catch (error) {
    ElMessage.error('更新失败')
  }
}

const syncAllStatus = async () => {
  syncingAll.value = true
  try {
    await getValidAccounts(true)  // 强制刷新，不使用缓存
    await loadData()
    ElMessage.success('所有账号状态已同步')
  } catch (error) {
    ElMessage.error('同步失败')
  } finally {
    syncingAll.value = false
  }
}

const handleSyncStatus = async (row: any) => {
  row.syncing = true
  try {
    const res = await syncAccountStatus(row.id) as any
    if (res.data) {
      row.status = res.data.status
      ElMessage.success(res.data?.msg || '状态同步成功')
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.msg || '同步失败')
  } finally {
    row.syncing = false
  }
}

const handleDelete = async (row: any) => {
  try {
    await deleteAccount(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const handleOpenBrowser = async (row: any) => {
  row.openingBrowser = true
  try {
    const res = await openBrowser(row.id)
    if (res.data?.msg) {
      ElMessage.success(res.data.msg)
    } else {
      ElMessage.success('浏览器已打开，请正常使用，关闭后痕迹会自动保存')
    }
  } catch (error: any) {
    console.error('Open browser error:', error)
    ElMessage.error(error.response?.data?.msg || '打开浏览器失败')
  } finally {
    row.openingBrowser = false
  }
}

const handleStartLogin = async () => {
  if (!addForm.value.platform) {
    ElMessage.warning('请选择平台')
    return
  }
  
  addingAccount.value = true
  try {
    const res = await startLogin(addForm.value.platform, addForm.value.accountName)
    if (res.data?.msg) {
      ElMessage.success(res.data.msg)
    } else {
      ElMessage.success('浏览器已打开，请完成登录后关闭浏览器')
    }
    showAddDialog.value = false
    
    // 重置表单
    addForm.value = { platform: '', accountName: '' }
    
    // 提示用户
    ElMessage.info({
      message: '登录完成并关闭浏览器后，请点击"同步状态"刷新账号列表',
      duration: 5000
    })
  } catch (error: any) {
    ElMessage.error(error.response?.data?.msg || '启动登录失败')
  } finally {
    addingAccount.value = false
  }
}

onMounted(() => {
  loadData()
  // 监听刷新事件
  eventBus.on('refreshData', loadData)
})

onUnmounted(() => {
  // 移除事件监听
  eventBus.off('refreshData', loadData)
})
</script>

<style scoped>
.edit-icon {
  margin-left: 8px;
  cursor: pointer;
  color: var(--primary-color);
  opacity: 0;
  transition: opacity 0.2s;
}

.el-table__row:hover .edit-icon {
  opacity: 1;
}

.action-buttons {
  display: flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

.add-account-dialog ol {
  color: var(--text-secondary);
}

.add-account-dialog ol li {
  margin-bottom: 4px;
}
</style>
