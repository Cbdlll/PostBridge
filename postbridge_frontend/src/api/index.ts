import axios from 'axios'
import { ElMessage } from 'element-plus'
import { translateRuntimeText } from '@/i18n'

const api = axios.create({
    timeout: 300000,
    headers: {
        'Content-Type': 'application/json'
    }
})

// 响应拦截器
api.interceptors.response.use(
    (response) => {
        const data = response.data
        if (data.code && data.code !== 200) {
            ElMessage.error(translateRuntimeText(data.msg || '请求失败'))
            return Promise.reject(new Error(data.msg))
        }
        return data
    },
    (error) => {
        // 尝试从响应中获取后端返回的错误消息
        const responseData = error.response?.data
        const errorMsg = responseData?.msg || error.message || '网络错误'
        ElMessage.error(translateRuntimeText(errorMsg))
        return Promise.reject(new Error(errorMsg))
    }
)

// ============== 文件管理 API ==============

export const uploadFile = (file: File, filename?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (filename) {
        formData.append('filename', filename)
    }
    return api.post('/uploadSave', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    })
}

export const getFiles = () => api.get('/getFiles')

export const deleteFile = (id: number) => api.get('/deleteFile', { params: { id } })

export const renameFile = (id: number, newFilename: string) =>
    api.post('/renameFile', { id, filename: newFilename })

export const getFileUrl = (filename: string) => `/getFile?filename=${encodeURIComponent(filename)}`

// ============== 账号管理 API ==============

export const getAccounts = () => api.get('/getAccounts')

export const getValidAccounts = (force = false) =>
    api.get('/getValidAccounts', { params: { force } })

export const deleteAccount = (id: number) => api.get('/deleteAccount', { params: { id } })

export const updateUserinfo = (data: { id: number; name?: string; type?: number; userName?: string; status?: number }) =>
    api.post('/updateUserinfo', data)

export const startLogin = (platform: string, accountName?: string) =>
    api.post('/api/startLogin', { platform, accountName })

export const openBrowser = (accountId: number) =>
    api.post('/api/openBrowser', { accountId })

export const syncAccountStatus = (accountId: number) =>
    api.post(`/api/syncAccountStatus/${accountId}`)

export const uploadCookie = (file: File, id: number, platform: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('id', String(id))
    formData.append('platform', platform)
    return api.post('/uploadCookie', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    })
}

export const downloadCookie = (filePath: string) =>
    `/downloadCookie?filePath=${encodeURIComponent(filePath)}`

// ============== 视频发布 API ==============

export interface PostVideoParams {
    fileList: string[]
    accountList: number[]
    type: number
    title: string
    description?: string
    tags: string[]
    category?: number
    enableTimer?: boolean
    videosPerDay?: number
    dailyTimes?: string[]
    startDays?: number
    thumbnail?: string
    isDraft?: boolean
    taskId?: string
}

export const postVideo = (data: PostVideoParams) => api.post('/postVideo', data)

export const submitVerificationCode = (taskId: string, code: string) =>
    api.post('/submitVerificationCode', { taskId, code })

// ============== AI 创作 API ==============

export interface CreatePromptParams {
    topic: string
    platform?: string
    style?: string
    use_mock?: boolean
    count?: number
    account_id?: number | null
    auto_publish?: boolean
    llm_config?: any
}

export const createPrompt = (data: CreatePromptParams) => api.post('/api/create_prompt', data)

export interface GenerateVideoParams {
    prompt: string
    provider?: string
    api_key?: string
}

export const generateVideo = (data: GenerateVideoParams) => api.post('/api/generate_video', data)

export const getVideoStatus = (taskId: string, provider = 'mock') =>
    api.get('/api/video_status', { params: { task_id: taskId, provider } })

export interface AIWorkflowParams {
    topic: string
    platform?: string
    style?: string
    auto_publish?: boolean
    llm_config?: {
        base_url?: string
        api_key?: string
        model?: string
    }
    video_config?: {
        provider?: string
        api_key?: string
    }
}

export const runAIWorkflow = (data: AIWorkflowParams) => api.post('/api/ai_workflow', data)

// ============== 任务管理 API ==============

export const getTasks = () => api.get('/api/tasks')

export const getPublishTasks = (type?: 'manual' | 'ai') =>
    api.get('/api/publish_tasks', { params: { type } })

export const deletePublishTask = (id: number) => api.delete(`/api/publish_tasks/${id}`)

export const createTask = (data: { topic: string; platform?: string; video_prompt?: string }) =>
    api.post('/api/tasks', data)

export const updateTask = (id: number, status: string) =>
    api.put(`/api/tasks/${id}`, { status })

export const deleteTask = (id: number) => api.delete(`/api/tasks/${id}`)

export const getPersonas = (lang?: 'en' | 'zh-CN') => api.get('/api/personas', { params: { lang } })

export const updatePersona = (data: { code: string; lang?: 'en' | 'zh-CN'; prompt?: string; ui_data?: object }) =>
    api.post('/api/personas/update', data)

// ============== AI 获客任务完整流程 API ==============

export interface CreateAITaskParams {
    topic?: string  // 原始主题 (用户创建任务时输入的主题)
    prompt_data: {
        title: string
        description: string
        tags: string[]
        video_prompt: string
    }
    account_id?: number | null
    auto_publish?: boolean
    platform?: string
    video_config?: {
        provider?: string
        api_key?: string
        resolution?: string
        duration?: number
        // Extended config fields
        wanApiKey?: string
        transit2ApiKey?: string
        doubaoApiKey?: string
        mockVideoUrl?: string
        transit2Model?: string
        doubaoModel?: string
        wanxiangModel?: string
        shotType?: string
        watermark?: boolean
    }
}

export const createAITask = (data: CreateAITaskParams) =>
    api.post('/api/ai_task/create', data)

export const getAITaskStatus = (taskId: number) =>
    api.get(`/api/ai_task/${taskId}/status`)

export const getCreationTaskStatus = (taskId: number) =>
    api.get(`/api/creation_task/${taskId}/status`)

export const continueTaskWithVideo = (
    taskId: number,
    data: {
        title: string
        description: string
        tags: string[]
        video_prompt: string
        video_config?: {
            provider?: string
            api_key?: string
            resolution?: string
            duration?: number
            // Extended config fields
            wanApiKey?: string
            transit2ApiKey?: string
            doubaoApiKey?: string
            mockVideoUrl?: string
            transit2Model?: string
            doubaoModel?: string
            wanxiangModel?: string
            shotType?: string
            watermark?: boolean
        }
    }
) => api.put(`/api/tasks/${taskId}/continue`, data)

export default api
