<template>
  <div class="video-manager-page page-container">
    <div class="page-header">
      <div class="search-bar">
        <el-input 
          v-model="searchQuery" 
          placeholder="搜索文件名..." 
          clearable
          style="width: 300px;"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
      <div class="header-actions">
        <el-button 
          v-if="selectedFiles.length > 0" 
          type="danger" 
          @click="handleBatchDelete"
        >
          批量删除 ({{ selectedFiles.length }})
        </el-button>
        <el-upload
          ref="uploadRef"
          action="/uploadSave"
          :show-file-list="false"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          accept="video/*"
        >
          <el-button type="primary" size="large">
            <el-icon class="mr-2"><Upload /></el-icon>
            上传新视频
          </el-button>
        </el-upload>
      </div>
    </div>

    <div class="card">
      <el-table 
        :data="filteredFiles" 
        v-loading="loading" 
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column label="文件名" prop="filename" min-width="200">
          <template #default="{ row }">
            <span class="font-medium">{{ row.filename }}</span>
          </template>
        </el-table-column>
        <el-table-column label="文件大小" width="120" align="center">
          <template #default="{ row }">
             <span class="text-secondary">{{ row.filesize }} MB</span>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" prop="upload_time" width="180" align="center" />
        <el-table-column label="预览" width="120" align="center">
          <template #default="{ row }">
            <el-button type="success" link @click="previewFile(row)">
              预览
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons" style="justify-content: center;">
              <el-button type="primary" link @click="useVideo(row)">
                发布
              </el-button>
              <el-button type="warning" link @click="handleRename(row)">
                重命名
              </el-button>
              <el-button type="danger" link @click="handleDelete(row)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 视频预览对话框 -->
    <el-dialog v-model="previewVisible" title="视频预览" width="800px" destroy-on-close center>
      <video 
        v-if="previewUrl" 
        :src="previewUrl" 
        controls 
        style="width: 100%; max-height: 500px; border-radius: 8px;"
      ></video>
    </el-dialog>

    <!-- 重命名对话框 -->
    <el-dialog v-model="renameVisible" title="重命名文件" width="500px">
      <el-form label-position="top">
        <el-form-item label="新文件名">
          <el-input 
            v-model="newFilename" 
            placeholder="请输入新文件名"
            @keyup.enter="submitRename"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renameVisible = false">取消</el-button>
        <el-button type="primary" @click="submitRename" :loading="renaming">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, VideoPlay, Search } from '@element-plus/icons-vue'
import { getFiles, deleteFile, getFileUrl, renameFile } from '@/api'
import eventBus from '@/utils/eventBus'

const router = useRouter()
const loading = ref(false)
const files = ref<any[]>([])
const previewVisible = ref(false)
const previewUrl = ref('')
const searchQuery = ref('')
const selectedFiles = ref<any[]>([])
const renameVisible = ref(false)
const newFilename = ref('')
const renamingFile = ref<any>(null)
const renaming = ref(false)

// 过滤后的文件列表
const filteredFiles = computed(() => {
  if (!searchQuery.value) return files.value
  const query = searchQuery.value.toLowerCase()
  return files.value.filter(file => 
    file.filename?.toLowerCase().includes(query)
  )
})

const loadFiles = async () => {
  loading.value = true
  try {
    const res = await getFiles()
    files.value = res.data || []
  } catch (error) {
    console.error('加载文件失败', error)
  } finally {
    loading.value = false
  }
}

const beforeUpload = (file: File) => {
  const isVideo = file.type.startsWith('video/')
  if (!isVideo) {
    ElMessage.error('只能上传视频文件！')
    return false
  }
  const isLt160M = file.size / 1024 / 1024 < 160
  if (!isLt160M) {
    ElMessage.error('视频大小不能超过 160MB！')
    return false
  }
  return true
}

const handleUploadSuccess = () => {
  ElMessage.success('上传成功')
  loadFiles()
}

const handleUploadError = () => {
  ElMessage.error('上传失败')
}

const previewFile = (row: any) => {
  previewUrl.value = getFileUrl(row.file_path)
  previewVisible.value = true
}

const useVideo = (row: any) => {
  // 跳转到发布页并选中该视频 TODO: 需要状态管理支持更佳，这里暂时只跳转
  router.push('/manual-publish')
}

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定要删除该视频吗？', '提示', {
      type: 'warning'
    })
    await deleteFile(row.id)
    ElMessage.success('删除成功')
    loadFiles()
  } catch (error) {
    // 用户取消
  }
}

// 处理选择变化
const handleSelectionChange = (selection: any[]) => {
  selectedFiles.value = selection
}

// 批量删除
const handleBatchDelete = async () => {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请先选择要删除的文件')
    return
  }
  
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedFiles.value.length} 个视频吗？`, '提示', {
      type: 'warning'
    })
    
    // 依次删除所有选中的文件
    for (const file of selectedFiles.value) {
      await deleteFile(file.id)
    }
    
    ElMessage.success('批量删除成功')
    selectedFiles.value = []
    loadFiles()
  } catch (error) {
    // 用户取消
  }
}

// 打开重命名对话框
const handleRename = (row: any) => {
  renamingFile.value = row
  newFilename.value = row.filename || ''
  renameVisible.value = true
}

// 提交重命名
const submitRename = async () => {
  if (!newFilename.value.trim()) {
    ElMessage.warning('文件名不能为空')
    return
  }
  
  if (!renamingFile.value) return
  
  renaming.value = true
  try {
    await renameFile(renamingFile.value.id, newFilename.value.trim())
    ElMessage.success('重命名成功')
    renameVisible.value = false
    loadFiles()
  } catch (error) {
    ElMessage.error('重命名失败')
  } finally {
    renaming.value = false
  }
}

onMounted(() => {
  loadFiles()
  // 监听刷新事件
  eventBus.on('refreshData', loadFiles)
})

onUnmounted(() => {
  // 移除事件监听
  eventBus.off('refreshData', loadFiles)
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.search-bar {
  flex: 1;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.font-medium { font-weight: 500; }
.text-secondary { color: var(--text-secondary); }
.mr-2 { margin-right: 8px; }

.action-buttons {
  display: flex;
  align-items: center;
  justify-content: flex-end; /* Align right as per original */
  gap: 8px;
  white-space: nowrap;
}

</style>
