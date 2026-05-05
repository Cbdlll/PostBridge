import { computed, ref } from 'vue'
import enUs from 'element-plus/dist/locale/en.mjs'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

export type Locale = 'en' | 'zh-CN'

const STORAGE_KEY = 'postbridge_locale'

const messages = {
  en: {
    appName: 'PostBridge',
    admin: 'Admin',
    refreshSuccess: 'Refreshed',
    english: 'English',
    chinese: 'Chinese',
    nav: {
      dashboard: 'Dashboard',
      accounts: 'Accounts',
      videos: 'Videos',
      manualPublish: 'Manual Publish',
      aiGroup: 'AI Studio',
      aiCreate: 'AI Task Builder',
      userPersona: 'Audience Profiles',
      tasks: 'Tasks',
      settings: 'Settings',
    },
    dashboard: {
      shortcuts: 'Quick Actions',
      userInsights: 'Platform Audience Insights',
      userInsightsDesc:
        'Use platform-specific audience signals to shape better content ideas, publishing plans, and conversion paths.',
      contentStrategy: 'Platform Content Strategy',
      smartCreation: 'AI Studio',
      smartCreationDesc: 'Generate copy and video ideas',
      personas: 'Audience Profiles',
      personasDesc: 'Compare platform behavior patterns',
      accountManager: 'Account Manager',
      accountManagerDesc: 'Manage connected publisher accounts',
      videoLibrary: 'Video Library',
      videoLibraryDesc: 'Review uploaded media assets',
      userDistribution: 'Monthly Active Users',
      usersUnit: 'Unit: 100M users',
      radar: 'Platform Signal Radar',
      radarDesc: 'Cross-platform score comparison',
      engagement: 'Engagement Index',
      engagementDesc: 'Likes, comments, and share activity',
      monthlyUsers: 'Monthly active users',
      contentStyle: 'Content style',
      radarIndicators: {
        engagement: 'Engagement',
        female: 'Female share',
        young: 'Young users',
        content: 'Content quality',
      },
    },
    settings: {
      titleLanguage: 'Language',
      interfaceLanguage: 'Interface language',
      languageTip: 'The app uses English by default and remembers your choice in this browser.',
      llmTitle: 'LLM Settings',
      llmSubtitle: 'OpenAI-compatible endpoint',
      model: 'Model',
      modelPlaceholder: 'For example: gpt-4o, gpt-4.1, deepseek-chat',
      baseUrlPlaceholder: 'For example: https://api.openai.com/v1',
      videoTitle: 'Video Generation',
      provider: 'Provider',
      providerMock: 'Mock (local testing)',
      providerWanxiang: 'Wanxiang (Alibaba)',
      providerTransit: 'Transit API',
      providerDoubao: 'Doubao (Volcengine)',
      mockUrl: 'Mock video URL',
      mockUrlPlaceholder: 'For example: https://example.com/demo-video.mp4',
      mockUrlTip: 'Used only in Mock mode. Leave blank to fall back to the placeholder video.',
      wanApiKey: 'Wanxiang API Key',
      transitApiKey: 'Transit API Key',
      doubaoApiKey: 'Doubao API Key',
      providerModel: 'Model ID',
      duration: 'Duration',
      resolution: 'Resolution',
      aspectRatio: 'Aspect ratio',
      shotType: 'Shot style',
      shotSingle: 'Single shot',
      shotMulti: 'Multi-shot narrative',
      watermark: 'Add watermark',
      browserTitle: 'Browser',
      chromePath: 'Chrome path',
      chromePathPlaceholder:
        'Leave blank to auto-detect, or enter a full path such as C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      chromePathTip:
        'If Chrome is installed in a custom location, enter the full executable path here.',
      testConnection: 'Test connection',
      saveConfig: 'Save settings',
      testPath: 'Test',
      fixed720Vertical: 'Fixed to 720p vertical output.',
      fixed720: 'Fixed to 720p output.',
      fixed916: 'Fixed to 9:16.',
      fixed169: 'Fixed to 16:9.',
      fixed12s: 'Fixed to 12 seconds.',
      soundOn: 'Enabled',
      soundOnTip: 'Native audio stays enabled.',
      info:
        'These settings are stored locally in your browser. They are only used when requests are sent from this app.',
      saveSuccess: 'Settings saved',
      chromeSaved: 'Chrome path saved',
      fillBaseUrlAndKey: 'Please fill in Base URL and API Key first.',
      llmSuccess: 'Connection test passed.',
      llmFailed: 'Connection test failed: ',
      saveFailed: 'Save failed: ',
      chromeTestSaved: 'Chrome path saved. Please verify it during account login.',
      loadFailed: 'Failed to load local settings.',
      loadAppFailed: 'Failed to load app settings.',
    },
  },
  'zh-CN': {
    appName: 'PostBridge',
    admin: '管理员',
    refreshSuccess: '刷新成功',
    english: '英文',
    chinese: '中文',
    nav: {
      dashboard: '首页',
      accounts: '账号管理',
      videos: '视频管理',
      manualPublish: '手动发布',
      aiGroup: 'AI 创作',
      aiCreate: 'AI 任务创建',
      userPersona: '用户画像',
      tasks: '任务管理',
      settings: '系统设置',
    },
    dashboard: {
      shortcuts: '快捷入口',
      userInsights: '平台用户画像分析',
      userInsightsDesc: '结合平台用户特征，帮助你设计更合适的内容主题、发布节奏和转化路径。',
      contentStrategy: '平台内容策略',
      smartCreation: 'AI 创作',
      smartCreationDesc: '智能生成文案和视频想法',
      personas: '用户画像',
      personasDesc: '对比平台用户行为特征',
      accountManager: '账号管理',
      accountManagerDesc: '管理已连接的平台账号',
      videoLibrary: '视频素材',
      videoLibraryDesc: '查看已上传的视频素材',
      userDistribution: '月活用户分布',
      usersUnit: '单位：亿',
      radar: '平台特征雷达图',
      radarDesc: '跨平台指标对比',
      engagement: '互动指数',
      engagementDesc: '点赞、评论、分享活跃度',
      monthlyUsers: '月活用户',
      contentStyle: '内容风格',
      radarIndicators: {
        engagement: '用户互动',
        female: '女性占比',
        young: '年轻用户',
        content: '内容质量',
      },
    },
    settings: {
      titleLanguage: '语言设置',
      interfaceLanguage: '界面语言',
      languageTip: '系统默认使用英文，并会在当前浏览器中记住你的选择。',
      llmTitle: 'LLM 设置',
      llmSubtitle: '兼容 OpenAI 的接口配置',
      model: '模型',
      modelPlaceholder: '例如：gpt-4o、gpt-4.1、deepseek-chat',
      baseUrlPlaceholder: '例如：https://api.openai.com/v1',
      videoTitle: '视频生成设置',
      provider: '服务商',
      providerMock: 'Mock（本地测试）',
      providerWanxiang: '万相（阿里云）',
      providerTransit: '中转 API',
      providerDoubao: '豆包（火山方舟）',
      mockUrl: 'Mock 视频 URL',
      mockUrlPlaceholder: '例如：https://example.com/demo-video.mp4',
      mockUrlTip: '仅在 Mock 模式下使用。留空时将回退到占位视频。',
      wanApiKey: '万相 API Key',
      transitApiKey: '中转 API Key',
      doubaoApiKey: '豆包 API Key',
      providerModel: '模型 ID',
      duration: '时长',
      resolution: '分辨率',
      aspectRatio: '视频比例',
      shotType: '镜头类型',
      shotSingle: '单镜头',
      shotMulti: '多镜头叙事',
      watermark: '添加水印',
      browserTitle: '浏览器设置',
      chromePath: 'Chrome 路径',
      chromePathPlaceholder:
        '留空则自动检测，或填写完整路径，例如 C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      chromePathTip: '如果 Chrome 安装在非默认位置，请填写完整的可执行文件路径。',
      testConnection: '测试连接',
      saveConfig: '保存配置',
      testPath: '测试',
      fixed720Vertical: '固定为 720p 竖屏输出。',
      fixed720: '固定为 720p 输出。',
      fixed916: '固定为 9:16。',
      fixed169: '固定为 16:9。',
      fixed12s: '固定为 12 秒。',
      soundOn: '已启用',
      soundOnTip: '默认保留原生音频。',
      info: '这些配置会保存在当前浏览器本地，仅在本应用发起请求时使用。',
      saveSuccess: '配置已保存',
      chromeSaved: 'Chrome 路径已保存',
      fillBaseUrlAndKey: '请先填写 Base URL 和 API Key。',
      llmSuccess: '连接测试成功。',
      llmFailed: '连接测试失败：',
      saveFailed: '保存失败：',
      chromeTestSaved: 'Chrome 路径已保存，请在账号登录时验证是否可用。',
      loadFailed: '本地配置加载失败。',
      loadAppFailed: '应用配置加载失败。',
    },
  },
} as const

const zhToEnTextMap: Record<string, string> = {
  '首页': 'Dashboard',
  '账号管理': 'Accounts',
  '视频管理': 'Videos',
  '手动发布': 'Manual Publish',
  'AI 获客': 'AI Studio',
  'AI 创作': 'AI Studio',
  '任务创建': 'Task Builder',
  '用户画像': 'Audience Profiles',
  '任务管理': 'Tasks',
  '系统设置': 'Settings',
  '管理员': 'Admin',
  '刷新成功': 'Refreshed',
  '添加账号': 'Add account',
  '同步中...': 'Syncing...',
  '同步状态': 'Sync status',
  '平台': 'Platform',
  '账号名称': 'Account name',
  '状态': 'Status',
  '有效': 'Active',
  '失效': 'Inactive',
  '操作': 'Actions',
  '删除': 'Delete',
  '取消': 'Cancel',
  '确定': 'Confirm',
  '继续': 'Continue',
  '详情': 'Details',
  '输入': 'Enter',
  '发布': 'Publish',
  '重命名': 'Rename',
  '预览': 'Preview',
  '文件名': 'Filename',
  '文件大小': 'Size',
  '上传时间': 'Uploaded',
  '上传新视频': 'Upload video',
  '搜索文件名...': 'Search filename...',
  '批量删除': 'Delete selected',
  '批量删除成功': 'Batch delete completed',
  '抖音': 'Douyin',
  '小红书': 'Xiaohongshu',
  '快手': 'Kuaishou',
  '视频号': 'WeChat Channels',
  'B站': 'Bilibili',
  '未知': 'Unknown',
  '快捷入口': 'Quick Actions',
  '视频素材': 'Video Library',
  '自动发布': 'Auto publish',
  '发布账号': 'Publishing accounts',
  '生成数量': 'Number of drafts',
  '内容风格': 'Visual style',
  '目标平台（可多选）': 'Target platforms',
  '创作主题': 'Topic',
  '创建 AI 获客任务': 'Create AI task',
  '请选择平台': 'Please select a platform',
  '请输入创作主题': 'Please enter a topic',
  '正在打开浏览器...': 'Opening browser...',
  '开始登录': 'Start login',
}

const enToZhTextMap = Object.fromEntries(
  Object.entries(zhToEnTextMap).map(([zh, en]) => [en, zh]),
) as Record<string, string>

function getStoredLocale(): Locale {
  const saved = localStorage.getItem(STORAGE_KEY)
  return saved === 'zh-CN' ? 'zh-CN' : 'en'
}

export const locale = ref<Locale>(getStoredLocale())

export const elementLocale = computed(() => (locale.value === 'zh-CN' ? zhCn : enUs))

export function setLocale(value: Locale) {
  locale.value = value
  localStorage.setItem(STORAGE_KEY, value)
}

export function t(path: string): string {
  const segments = path.split('.')
  let current: any = messages[locale.value === 'zh-CN' ? 'zh-CN' : 'en']

  for (const segment of segments) {
    current = current?.[segment]
  }

  return typeof current === 'string' ? current : path
}

export function translateRuntimeText(input: string): string {
  if (!input) return input

  const map = locale.value === 'zh-CN' ? enToZhTextMap : zhToEnTextMap
  let output = input

  for (const [from, to] of Object.entries(map).sort((a, b) => b[0].length - a[0].length)) {
    output = output.split(from).join(to)
  }

  return output
}

function translateNodeText(node: Node) {
  if (node.nodeType === Node.TEXT_NODE) {
    const original = node.textContent ?? ''
    const translated = translateRuntimeText(original)
    if (translated !== original) node.textContent = translated
    return
  }

  if (!(node instanceof HTMLElement)) return

  for (const attr of ['placeholder', 'title', 'aria-label']) {
    const value = node.getAttribute(attr)
    if (!value) continue
    const translated = translateRuntimeText(value)
    if (translated !== value) node.setAttribute(attr, translated)
  }

  node.childNodes.forEach(translateNodeText)
}

export function applyRuntimeTranslations(root: ParentNode) {
  root.childNodes.forEach(translateNodeText)
}
