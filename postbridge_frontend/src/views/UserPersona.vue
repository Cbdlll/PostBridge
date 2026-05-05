<template>
  <div class="user-persona-page page-container">
    <div class="page-header">
      <h2>用户画像管理</h2>
    </div>

    <el-row :gutter="16" v-loading="loading" class="persona-row">
      <el-col :xs="24" :sm="12" :md="12" :lg="8" v-for="(persona, code) in personas" :key="code" class="persona-col">
        <el-card class="persona-card" :body-style="{ padding: '0px', height: '100%', display: 'flex', flexDirection: 'column' }">
          <template #header>
            <div class="card-header" :style="{ borderLeft: `4px solid ${persona.ui_data.color || '#409EFF'}` }">
              <div class="header-title">
                <el-icon :size="18" :color="persona.ui_data.color"><component :is="getIcon(persona.ui_data.icon)" /></el-icon>
                <span class="title-text">{{ persona.name }}</span>
              </div>
              <div class="header-actions">
                <el-button link type="primary" size="small" @click="openViewPrompt(persona)">查看提示词</el-button>
                <el-button type="primary" link size="small" @click="openEdit(persona)">
                  <el-icon><Edit /></el-icon>
                  &nbsp;编辑
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="card-content">
            <div class="scrollable-content">
              <div class="info-group">
                <div class="group-title">🎯 用户群体</div>
                <div class="compact-list">
                  <div 
                    v-for="(item, idx) in parseStructuredContent(persona.ui_data.features?.users || '')" 
                    :key="idx" 
                    class="compact-item"
                  >
                    <span class="c-label" v-if="item.label">{{ item.label }}:</span>
                    <span class="c-value">{{ item.value }}</span>
                  </div>
                </div>
              </div>
              
              <div class="info-group">
                <div class="group-title">🎨 内容风格</div>
                <div class="compact-list">
                   <div 
                    v-for="(item, idx) in parseStructuredContent(persona.ui_data.features?.style || '')" 
                    :key="idx" 
                    class="compact-item"
                  >
                    <span class="c-label" v-if="item.label">{{ item.label }}:</span>
                    <span class="c-value">{{ item.value }}</span>
                  </div>
                </div>
              </div>

              <div class="info-group">
                <div class="group-title">🔥 近期热点</div>
                 <div class="hot-topic-box" v-if="persona.ui_data.hot_topics">{{ persona.ui_data.hot_topics }}</div>
                 <div class="text-gray small" v-else>暂无配置</div>
              </div>
            </div>

            <div class="card-footer-tags">
              <div class="tags-scroll">
                <el-tag 
                  v-for="kw in (persona.ui_data.features?.keywords || [])" 
                  :key="kw" 
                  size="small" 
                  effect="light"
                  class="mini-tag"
                >
                  {{ kw }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Redesigned Edit Modal -->
    <el-dialog
      v-model="editDialogVisible"
      :title="null"
      width="80%"
      top="5vh"
      destroy-on-close
      class="redesigned-modal"
      :show-close="false"
    >
      <template #header="{ close, titleId, titleClass }">
        <div class="modal-custom-header">
           <div class="modal-title">
              <el-icon :size="22" class="mr-2" color="#409EFF"><Edit /></el-icon>
              <span>编辑用户画像 - {{ editingPersona?.name }}</span>
           </div>
           <el-button circle plain icon="Close" @click="close" size="small"></el-button>
        </div>
      </template>

      <div class="modal-body-content" v-if="editingForm">
        <el-row :gutter="30" style="height: 100%">
            <!-- Left Column: Structured Data -->
            <el-col :span="14" class="left-panel">
                <div class="panel-section">
                    <div class="section-header">
                        <span class="label">🎯 用户群体特征</span>
                        <el-button type="primary" link size="small" @click="addItem(structuredUsers, 'users')">+ 添加</el-button>
                    </div>
                    <div class="edit-list-container" ref="usersListRef">
                        <div v-for="(item, index) in structuredUsers" :key="index" class="edit-list-row">
                            <el-input v-model="item.label" placeholder="标签 (如:年龄)" class="input-label" size="small" />
                            <span class="colon">:</span>
                            <el-input v-model="item.value" placeholder="描述内容" class="input-value" size="small" />
                            <el-button type="danger" link v-if="structuredUsers.length > 1" class="del-btn" @click="removeItem(structuredUsers, index)">
                                <el-icon><Delete /></el-icon>
                            </el-button>
                        </div>
                    </div>
                </div>

                <div class="panel-section mt-4">
                    <div class="section-header">
                        <span class="label">🎨 内容风格偏好</span>
                        <el-button type="primary" link size="small" @click="addItem(structuredStyle, 'style')">+ 添加</el-button>
                    </div>
                    <div class="edit-list-container" ref="styleListRef">
                         <div v-for="(item, index) in structuredStyle" :key="index" class="edit-list-row">
                            <el-input v-model="item.label" placeholder="标签 (如:视觉)" class="input-label" size="small" />
                            <span class="colon">:</span>
                            <el-input v-model="item.value" placeholder="描述内容" class="input-value" size="small" />
                            <el-button type="danger" link v-if="structuredStyle.length > 1" class="del-btn" @click="removeItem(structuredStyle, index)">
                                <el-icon><Delete /></el-icon>
                            </el-button>
                        </div>
                    </div>
                </div>
            </el-col>

            <!-- Right Column: Extras -->
            <el-col :span="10" class="right-panel">
                 <div class="panel-card">
                    <div class="card-label">🔥 近期热点 / 趋势</div>
                    <el-input 
                        v-model="editingForm.hot_topics" 
                        type="textarea" 
                        :rows="4" 
                        placeholder="输入当前关联的热点话题..." 
                        class="modern-textarea"
                    />
                 </div>

                 <div class="panel-card mt-4" style="flex: 1; display: flex; flex-direction: column;">
                    <div class="card-label">🏷️ 内容关键词</div>
                    <div class="keywords-instruction">输入后按回车生成标签</div>
                    <el-select
                        v-model="editingForm.features.keywords"
                        multiple
                        filterable
                        allow-create
                        default-first-option
                        :reserve-keyword="false"
                        placeholder="添加关键词..."
                        class="keyword-select"
                    >
                    </el-select>
                 </div>
            </el-col>
        </el-row>
      </div>

      <template #footer>
        <div class="modal-custom-footer">
          <el-button @click="editDialogVisible = false" size="large">取消</el-button>
          <el-button type="primary" @click="handleSave" :loading="saving" size="large" class="save-btn">
            保存修改
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- View Prompt Modal -->
    <el-dialog
      v-model="promptDialogVisible"
      :title="`${viewingPersona?.name || ''} 完整 Prompt`"
      width="800px"
      top="5vh"
    >
      <el-input
        v-model="viewingPrompt"
        type="textarea"
        :rows="20"
        readonly
        resize="none"
        style="font-family: monospace; font-size: 13px;"
      />
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { getPersonas, updatePersona } from '@/api'
import { locale } from '@/i18n'
import { ElMessage } from 'element-plus'
import { Edit, VideoPlay, VideoCamera, ChatDotRound, Iphone, Camera, Delete, Close } from '@element-plus/icons-vue'

const personas = ref<any>({})
const loading = ref(false)

// Edit State
const editDialogVisible = ref(false)
const editingPersona = ref<any>(null)
const editingForm = ref<any>(null)
const saving = ref(false)

// Structured Edit State
const structuredUsers = ref<any[]>([])
const structuredStyle = ref<any[]>([])
const usersListRef = ref<HTMLElement | null>(null)
const styleListRef = ref<HTMLElement | null>(null)

// View Prompt State
const promptDialogVisible = ref(false)
const viewingPersona = ref<any>(null)
const viewingPrompt = ref('')

const getIcon = (iconName: string) => {
    const icons: any = {
        'video-play': VideoPlay,
        'video-camera': VideoCamera,
        'chat-dot-round': ChatDotRound,
        'iphone': Iphone,
        'camera': Camera
    }
    return icons[iconName] || VideoPlay
}

const loadData = async () => {
    loading.value = true
    try {
        const res = await getPersonas(locale.value)
        personas.value = res.data
    } catch (error) {
        console.error(error)
        ElMessage.error('加载用户画像失败')
    } finally {
        loading.value = false
    }
}

// Helper to parse string to structured array
const parseToStructured = (text: string) => {
    if (!text) return []
    return text.split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
        .map(line => {
             // 1. Remove Bullet/Numbering to get clean content
             let cleanLine = line.replace(/^(\*|-|\d+\.)\s*/, '');
             
             // 2. Try match: **Label**: Value OR Label: Value
             // We prioritize finding a colon that looks like a separator
             
             // Regex explanation:
             // ^(\*\*)?       - Optional starting bold
             // (.*?)          - Label content (lazy)
             // (\*\*)?        - Optional ending bold
             // [:：]          - The separator
             // \s*(.*)$       - The value
             const match = cleanLine.match(/^(\*\*)?(.*?)(\*\*)?[:：]\s*(.*)$/);
             
             if (match && match[2] && match[4]) {
                 let label = match[2].trim();
                 let value = match[4].trim();
                 
                 // If label starts with http, it's likely a URL, not a KV pair
                 if (/^https?:\/\//i.test(label)) {
                      return { label: '', value: cleanLine }
                 }

                 // Fix: Remove any leading colons from value (fixes :::::: issue)
                 value = value.replace(/^[:：]+\s*/, '');
                 
                 // Fix: Remove leading/trailing markdown bold/italic markers from value
                 value = value.replace(/^(\*\*|\*)\s*/, '').replace(/(\*\*|\*)$/, '');

                 return { label, value }
             }
             
             return { label: '', value: cleanLine }
        })
}

// Helper to stringify structured array back to markdown
const stringifyStructured = (items: any[]) => {
    return items
        .filter(item => item.value && item.value.trim() !== '')
        .map(item => {
            if (item.label && item.label.trim() !== '') {
                return `* **${item.label.trim()}:** ${item.value.trim()}`
            }
            return `* ${item.value.trim()}`
        })
        .join('\n')
}

const addItem = async (list: any[], type: 'users' | 'style') => {
    list.push({ label: '', value: '' })
    await nextTick()
    const container = type === 'users' ? usersListRef.value : styleListRef.value
    if (container) {
        container.scrollTop = container.scrollHeight
    }
}

const removeItem = (list: any[], index: number) => {
    list.splice(index, 1)
}

const openEdit = (persona: any) => {
    editingPersona.value = persona
    // Deep copy for form
    editingForm.value = JSON.parse(JSON.stringify(persona.ui_data))
    // Ensure nested objects exist
    if (!editingForm.value.features) editingForm.value.features = {}
    if (!editingForm.value.features.keywords) editingForm.value.features.keywords = []
    if (!editingForm.value.hot_topics) editingForm.value.hot_topics = ""

    // Init structured data
    structuredUsers.value = parseToStructured(editingForm.value.features.users || '')
    structuredStyle.value = parseToStructured(editingForm.value.features.style || '')
    
    // Ensure at least one empty item if empty
    if (structuredUsers.value.length === 0) addItem(structuredUsers.value, 'users')
    if (structuredStyle.value.length === 0) addItem(structuredStyle.value, 'style')
    
    editDialogVisible.value = true
}

const handleSave = async () => {
    if (!editingPersona.value || !editingForm.value) return
    
    saving.value = true
    try {
        // Reconstruct strings
        editingForm.value.features.users = stringifyStructured(structuredUsers.value)
        editingForm.value.features.style = stringifyStructured(structuredStyle.value)

        await updatePersona({
            code: editingPersona.value.code,
            lang: locale.value,
            ui_data: editingForm.value
        })
        ElMessage.success('保存成功')
        editDialogVisible.value = false
        loadData() // Reload to get updated prompt and data
    } catch (error) {
        console.error(error)
        ElMessage.error('保存失败')
    } finally {
        saving.value = false
    }
}

const openViewPrompt = (persona: any) => {
    viewingPersona.value = persona
    viewingPrompt.value = persona.prompt
    promptDialogVisible.value = true
}

onMounted(() => {
    loadData()
})

watch(locale, () => {
    loadData()
})

// Helper to parse structured markdown content for Display
const parseStructuredContent = (text: string) => {
    // Reuse the same logic for consistency, but we don't need to rebuild the object, just return it.
    // However, display might need to handle the raw bullet points if they exist in `text` which comes from DB/Markdown.
    return parseToStructured(text);
}
</script>

<style scoped>
.page-container {
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden; /* Prevent page scroll, use internal scroll */
    padding: 20px;
    box-sizing: border-box;
}

.page-header {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.page-header h2 {
    margin: 0;
    font-size: 20px;
    color: #1f2937;
}

/* Row/Col Layout */
.persona-row {
    flex: 1;
    overflow-y: auto; /* Allow scrolling if really needed on small screens, or hide if we want "one page" */
    overflow-x: hidden;
    padding-bottom: 20px;
}

/* Card Styling */
.persona-card {
    height: calc(100vh - 100px); /* Adjust based on header */
    max-height: 650px; /* Reasonable max height */
    border: none;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    border-radius: 12px;
    transition: all 0.3s ease;
    display: flex;
    flex-direction: column;
}

.persona-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 24px rgba(0,0,0,0.1);
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background-color: #ffffff;
    border-bottom: 1px solid #f3f4f6;
    flex-shrink: 0;
}

.header-title {
    display: flex;
    align-items: center;
    gap: 10px;
}

.title-text {
    font-weight: 700;
    font-size: 16px;
    color: #111827;
}

.card-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 0;
    overflow: hidden;
    background: #ffffff;
}

.scrollable-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
}

/* Custom Scrollbar for card content */
.scrollable-content::-webkit-scrollbar {
    width: 6px;
}
.scrollable-content::-webkit-scrollbar-thumb {
    background-color: #e5e7eb;
    border-radius: 3px;
}

.info-group {
    margin-bottom: 16px;
}

.info-group:last-child {
    margin-bottom: 0;
}

.group-title {
    font-size: 12px;
    font-weight: 700;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
}

.group-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #f3f4f6;
    margin-left: 8px;
}

/* Compact List */
.compact-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.compact-item {
    font-size: 13px;
    line-height: 1.5;
    color: #4b5563;
    display: flex;
    align-items: flex-start;
}

.c-label {
    font-weight: 600;
    color: #374151;
    margin-right: 6px;
    white-space: nowrap;
}

.c-value {
    color: #4b5563;
    word-break: break-word;
}

.hot-topic-box {
    background: #fef2f2;
    color: #ef4444;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    border: 1px solid #fee2e2;
}

.small { font-size: 12px; }
.text-gray { color: #9ca3af; }

.card-footer-tags {
    padding: 12px 16px;
    background: #f9fafb;
    border-top: 1px solid #f3f4f6;
    flex-shrink: 0;
}

.tags-scroll {
    display: flex;
    flex-wrap: wrap; /* Wrap tags to show them all, or can make it scrollable horizontally */
    gap: 6px;
    max-height: 60px; /* Limit height of tags area */
    overflow-y: auto;
}

.mini-tag {
    font-size: 12px;
    border: none;
    background: #eef2ff;
    color: #4f46e5;
}

/* Redesigned Modal Styling */
.redesigned-modal :deep(.el-dialog__header) {
    padding: 0;
    margin: 0;
    display: none; /* Hide default header to use custom */
}

.redesigned-modal :deep(.el-dialog__body) {
    padding: 0;
    height: 600px; /* Fixed height for consistency */
    display: flex;
    flex-direction: column;
}

.modal-custom-header {
    padding: 16px 24px;
    border-bottom: 1px solid #f0f0f0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #fcfcfc;
}

.modal-title {
    font-size: 18px;
    font-weight: 600;
    color: #1f2937;
    display: flex;
    align-items: center;
}

.modal-body-content {
    flex: 1;
    padding: 24px;
    background: #ffffff;
    overflow-y: auto;
}

.left-panel {
    border-right: 1px solid #f0f0f0;
    padding-right: 20px;
    display: flex;
    flex-direction: column;
    gap: 24px;
}

.right-panel {
    display: flex;
    flex-direction: column;
}

.panel-section {
    display: flex;
    flex-direction: column;
    flex: 1;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid #ebedf0;
}

.section-header .label {
    font-size: 14px;
    font-weight: 700;
    color: #374151;
}

.edit-list-container {
    display: flex;
    flex-direction: column;
    gap: 8px;
    overflow-y: auto;
    flex: 1;
    max-height: 250px; /* Limit list height specially in modal */
    padding-right: 6px;
}

.edit-list-row {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #f9fafb;
    padding: 6px;
    border-radius: 6px;
}

.input-label {
    width: 120px;
    flex-shrink: 0;
}
.input-label :deep(.el-input__wrapper) {
    background-color: #ffffff;
    box-shadow: none !important;
    border: 1px solid #e5e7eb;
}

.colon {
    font-weight: bold;
    color: #d1d5db;
}

.input-value {
    flex: 1;
}
.input-value :deep(.el-input__wrapper) {
    background-color: #ffffff;
    box-shadow: none !important;
    border: 1px solid #e5e7eb;
}

.del-btn {
    padding: 4px;
}

.panel-card {
    background: #f9fafb;
    padding: 16px;
    border-radius: 8px;
    border: 1px solid #f3f4f6;
}

.card-label {
    font-size: 14px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 12px;
    display: block;
}

.modern-textarea :deep(.el-textarea__inner) {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 12px;
    font-size: 14px;
    box-shadow: none;
}
.modern-textarea :deep(.el-textarea__inner:focus) {
    border-color: #409eff;
}

.keywords-instruction {
    font-size: 12px;
    color: #9ca3af;
    margin-bottom: 8px;
}

.keyword-select {
    width: 100%;
}

.modal-custom-footer {
    padding: 16px 24px;
    border-top: 1px solid #f0f0f0;
    background: #fcfcfc;
    display: flex;
    justify-content: flex-end;
    gap: 12px;
}

.save-btn {
    min-width: 100px;
}

.mt-4 { margin-top: 16px; }
.mr-2 { margin-right: 8px; }

/* Scrollbar styling for edit lists */
.edit-list-container::-webkit-scrollbar {
    width: 4px;
}
.edit-list-container::-webkit-scrollbar-thumb {
    background: #d1d5db;
    border-radius: 2px;
}

/* Responsiveness for cards */
@media (max-width: 768px) {
    .page-container {
        height: auto;
        overflow-y: auto;
    }
    .persona-card {
        height: 500px;
        margin-bottom: 20px;
    }
}
</style>
