<template>
  <div class="settings-page page-container">
    <div class="card settings-shell">
      <div class="settings-form">
        <div class="section-label">{{ t('settings.titleLanguage') }}</div>
        <el-form label-position="top">
          <el-form-item :label="t('settings.interfaceLanguage')">
            <el-select :model-value="locale" size="large" style="width: 100%" @change="handleLocaleChange">
              <el-option value="en" :label="t('english')" />
              <el-option value="zh-CN" :label="t('chinese')" />
            </el-select>
            <div class="form-tip">{{ t('settings.languageTip') }}</div>
          </el-form-item>
        </el-form>

        <el-divider />

        <div class="section-label">{{ t('settings.llmTitle') }}</div>
        <div class="section-subtitle">{{ t('settings.llmSubtitle') }}</div>
        <el-form label-position="top">
          <el-form-item label="Base URL">
            <el-input
              v-model="apiConfig.llmBaseUrl"
              :placeholder="t('settings.baseUrlPlaceholder')"
              size="large"
            />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input
              v-model="apiConfig.llmApiKey"
              type="password"
              placeholder="sk-..."
              show-password
              size="large"
            />
          </el-form-item>
          <el-form-item :label="t('settings.model')">
            <el-input
              v-model="apiConfig.llmModel"
              :placeholder="t('settings.modelPlaceholder')"
              size="large"
            />
          </el-form-item>
        </el-form>

        <el-divider />

        <div class="section-label">{{ t('settings.videoTitle') }}</div>
        <el-form label-position="top">
          <el-form-item :label="t('settings.provider')">
            <el-select v-model="apiConfig.videoProvider" size="large" style="width: 100%">
              <el-option :label="t('settings.providerMock')" value="mock" />
              <el-option :label="t('settings.providerWanxiang')" value="wanxiang" />
              <el-option :label="t('settings.providerTransit')" value="sora" />
              <el-option :label="t('settings.providerDoubao')" value="doubao" />
            </el-select>
          </el-form-item>

          <el-form-item v-if="apiConfig.videoProvider === 'mock'" :label="t('settings.mockUrl')">
            <el-input
              v-model="apiConfig.mockVideoUrl"
              :placeholder="t('settings.mockUrlPlaceholder')"
              size="large"
            >
              <template #prefix>
                <el-icon><Link /></el-icon>
              </template>
            </el-input>
            <div class="form-tip">{{ t('settings.mockUrlTip') }}</div>
          </el-form-item>

          <el-form-item v-if="apiConfig.videoProvider === 'wanxiang'" :label="t('settings.wanApiKey')">
            <el-input
              v-model="apiConfig.wanApiKey"
              type="password"
              placeholder="sk-xxx"
              show-password
              size="large"
            />
            <div class="form-tip">
              <a href="https://bailian.console.aliyun.com/" target="_blank">DashScope / Bailian</a>
            </div>
          </el-form-item>

          <el-form-item v-if="apiConfig.videoProvider === 'sora'" :label="t('settings.transitApiKey')">
            <el-input
              v-model="apiConfig.transit2ApiKey"
              type="password"
              placeholder="sk-xxx"
              show-password
              size="large"
            />
            <div class="form-tip">
              <a href="https://api.aiiai.top/" target="_blank">Transit API</a>
            </div>
          </el-form-item>

          <el-form-item v-if="apiConfig.videoProvider === 'doubao'" :label="t('settings.doubaoApiKey')">
            <el-input
              v-model="apiConfig.doubaoApiKey"
              type="password"
              placeholder="API Key"
              show-password
              size="large"
            />
            <div class="form-tip">
              <a href="https://console.volcengine.com/ark" target="_blank">Volcengine Ark</a>
            </div>
          </el-form-item>

          <div class="flex gap-4" v-if="apiConfig.videoProvider === 'sora'">
            <el-form-item :label="t('settings.providerModel')" class="flex-1">
              <el-select v-model="apiConfig.transit2Model" size="large" style="width: 100%" @change="onTransit2ModelChange">
                <el-option label="Sora-2" value="sora-2" />
                <el-option label="Sora-2-Pro" value="sora-2-pro" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('settings.duration')" class="flex-1">
              <el-select v-model="apiConfig.transit2Duration" size="large" style="width: 100%">
                <el-option v-if="apiConfig.transit2Model !== 'kling-video-o1'" label="10s" :value="10" />
                <el-option v-if="apiConfig.transit2Model !== 'kling-video-o1'" label="15s" :value="15" />
                <el-option v-if="apiConfig.transit2Model === 'kling-video-o1'" label="5s" :value="5" />
                <el-option v-if="apiConfig.transit2Model === 'kling-video-o1'" label="10s" :value="10" />
              </el-select>
            </el-form-item>
          </div>

          <div class="flex gap-4" v-if="apiConfig.videoProvider === 'sora'">
            <el-form-item :label="t('settings.resolution')" class="flex-1">
              <el-input value="720p" size="large" disabled style="width: 100%" />
              <div class="form-tip">{{ t('settings.fixed720Vertical') }}</div>
            </el-form-item>
            <el-form-item :label="t('settings.aspectRatio')" class="flex-1">
              <el-input value="9:16" size="large" disabled style="width: 100%" />
              <div class="form-tip">{{ t('settings.fixed916') }}</div>
            </el-form-item>
          </div>

          <el-form-item v-if="apiConfig.videoProvider === 'doubao'" :label="t('settings.providerModel')">
            <el-select v-model="apiConfig.doubaoModel" size="large" style="width: 100%">
              <el-option label="SeeDance 1.5 Pro" value="doubao-seedance-1-5-pro-251215" />
              <el-option label="SeeDance 1.0 Pro" value="doubao-seedance-1-0-pro-250528" />
            </el-select>
          </el-form-item>

          <div class="flex gap-4" v-if="apiConfig.videoProvider === 'wanxiang'">
            <el-form-item :label="t('settings.providerModel')" class="flex-1">
              <el-select v-model="apiConfig.wanxiangModel" size="large" style="width: 100%">
                <el-option label="Wanxiang 2.6" value="wan2.6-t2v" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('settings.resolution')" class="flex-1">
              <el-select v-model="apiConfig.videoResolution" size="large" style="width: 100%">
                <el-option label="720p" value="720p" />
                <el-option label="1080p" value="1080p" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('settings.duration')" class="flex-1">
              <el-select v-model="apiConfig.videoDuration" size="large" style="width: 100%">
                <el-option label="5s" :value="5" />
                <el-option label="10s" :value="10" />
                <el-option label="15s" :value="15" />
              </el-select>
            </el-form-item>
          </div>

          <div class="flex gap-4" v-if="apiConfig.videoProvider === 'wanxiang'">
            <el-form-item :label="t('settings.shotType')" class="flex-1">
              <el-select v-model="apiConfig.videoShotType" size="large" style="width: 100%">
                <el-option :label="t('settings.shotSingle')" value="single" />
                <el-option :label="t('settings.shotMulti')" value="multi" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('settings.watermark')" class="flex-1">
              <el-switch v-model="apiConfig.videoWatermark" size="large" />
            </el-form-item>
          </div>

          <div class="flex gap-4" v-if="apiConfig.videoProvider === 'doubao'">
            <el-form-item :label="t('settings.resolution')" class="flex-1">
              <el-input value="720p" size="large" disabled style="width: 100%" />
              <div class="form-tip">{{ t('settings.fixed720') }}</div>
            </el-form-item>
            <el-form-item :label="t('settings.aspectRatio')" class="flex-1">
              <el-input value="16:9" size="large" disabled style="width: 100%" />
              <div class="form-tip">{{ t('settings.fixed169') }}</div>
            </el-form-item>
          </div>

          <div class="flex gap-4" v-if="apiConfig.videoProvider === 'doubao'">
            <el-form-item :label="t('settings.duration')" class="flex-1">
              <el-input value="12s" size="large" disabled style="width: 100%" />
              <div class="form-tip">{{ t('settings.fixed12s') }}</div>
            </el-form-item>
            <el-form-item label="Audio" class="flex-1">
              <el-input :value="t('settings.soundOn')" size="large" disabled style="width: 100%" />
              <div class="form-tip">{{ t('settings.soundOnTip') }}</div>
            </el-form-item>
          </div>
        </el-form>

        <el-divider />

        <div class="section-label">{{ t('settings.browserTitle') }}</div>
        <el-form label-position="top">
          <el-form-item :label="t('settings.chromePath')">
            <el-input
              v-model="appConfig.chromePath"
              :placeholder="t('settings.chromePathPlaceholder')"
              size="large"
            >
              <template #append>
                <el-button @click="testChromePath" :loading="testingChrome">{{ t('settings.testPath') }}</el-button>
              </template>
            </el-input>
            <div class="form-tip">{{ t('settings.chromePathTip') }}</div>
          </el-form-item>
        </el-form>

        <div class="flex justify-center actions-row">
          <el-button
            type="success"
            size="large"
            class="action-button"
            @click="testLLMConnection"
            :loading="testing"
          >
            {{ t('settings.testConnection') }}
          </el-button>
          <el-button type="primary" size="large" class="action-button" @click="saveAllSettings">
            {{ t('settings.saveConfig') }}
          </el-button>
        </div>

        <div class="info-tip">
          <el-icon><InfoFilled /></el-icon>
          <span>{{ t('settings.info') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, Link } from '@element-plus/icons-vue'

import { locale, setLocale, t, type Locale } from '@/i18n'

const testing = ref(false)
const testingChrome = ref(false)

const appConfig = ref({
  chromePath: '',
})

const apiConfig = ref({
  llmBaseUrl: '',
  llmApiKey: '',
  llmModel: 'gpt-4o',
  videoProvider: 'mock',
  wanApiKey: '',
  doubaoApiKey: '',
  mockVideoUrl: '',
  wanxiangModel: 'wan2.6-t2v',
  videoResolution: '720p',
  videoDuration: 5,
  videoShotType: 'single',
  videoWatermark: false,
  transit2ApiKey: '',
  transit2Model: 'sora-2',
  transit2Duration: 10,
  doubaoModel: 'doubao-seedance-1-5-pro-251215',
})

const handleLocaleChange = (value: Locale) => {
  setLocale(value)
}

const onTransit2ModelChange = (model: string) => {
  apiConfig.value.transit2Duration = model === 'kling-video-o1' ? 5 : 10
}

const loadApiConfig = () => {
  const saved = localStorage.getItem('api_config')
  if (!saved) return

  try {
    apiConfig.value = { ...apiConfig.value, ...JSON.parse(saved) }
  } catch (error) {
    console.error(t('settings.loadFailed'), error)
  }
}

const persistApiConfig = () => {
  localStorage.setItem('api_config', JSON.stringify(apiConfig.value))
}

const saveApiConfig = () => {
  persistApiConfig()
  ElMessage.success(t('settings.saveSuccess'))
}

const loadAppConfig = async () => {
  try {
    const response = await axios.get('/api/config')
    if (response.data.code === 200) {
      appConfig.value = { ...appConfig.value, ...response.data.data }
    }
  } catch (error) {
    console.error(t('settings.loadAppFailed'), error)
  }
}

const saveAppConfig = async () => {
  const response = await axios.post('/api/config', {
    chrome_path: appConfig.value.chromePath,
  })

  if (response.data.code === 200) {
    ElMessage.success(t('settings.chromeSaved'))
    return
  }

  throw new Error(response.data.msg || t('settings.saveFailed'))
}

const saveAllSettings = async () => {
  try {
    persistApiConfig()
    await axios.post('/api/config', {
      chrome_path: appConfig.value.chromePath,
    })
    ElMessage.success(t('settings.saveSuccess'))
  } catch (error: any) {
    ElMessage.error(t('settings.saveFailed') + (error.response?.data?.msg || error.message))
  }
}

const testLLMConnection = async () => {
  if (!apiConfig.value.llmBaseUrl || !apiConfig.value.llmApiKey) {
    ElMessage.warning(t('settings.fillBaseUrlAndKey'))
    return
  }

  testing.value = true
  try {
    const response = await axios.post('/api/check-llm', {
      baseUrl: apiConfig.value.llmBaseUrl,
      apiKey: apiConfig.value.llmApiKey,
      model: apiConfig.value.llmModel,
    })

    if (response.data.code === 200) {
      ElMessage.success(t('settings.llmSuccess'))
    } else {
      ElMessage.error(t('settings.llmFailed') + response.data.msg)
    }
  } catch (error: any) {
    ElMessage.error(t('settings.llmFailed') + (error.response?.data?.msg || error.message || 'Network error'))
  } finally {
    testing.value = false
  }
}

const testChromePath = async () => {
  testingChrome.value = true
  try {
    await saveAppConfig()
    ElMessage.success(t('settings.chromeTestSaved'))
  } catch (error: any) {
    ElMessage.error(t('settings.saveFailed') + error.message)
  } finally {
    testingChrome.value = false
  }
}

onMounted(() => {
  loadApiConfig()
  void loadAppConfig()
})
</script>

<style scoped>
.settings-shell {
  max-width: 860px;
  margin: 0 auto;
}

.settings-form {
  padding-top: 24px;
}

.section-label {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-primary);
  display: flex;
  align-items: center;
}

.section-label::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 16px;
  background: var(--primary-color);
  margin-right: 8px;
  border-radius: 2px;
}

.section-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: -4px;
  margin-bottom: 16px;
}

.info-tip {
  margin-top: 24px;
  background: var(--bg-color);
  padding: 12px;
  border-radius: 8px;
  display: flex;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.form-tip {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.form-tip a {
  color: var(--primary-color);
  text-decoration: none;
}

.form-tip a:hover {
  text-decoration: underline;
}

.actions-row {
  margin-top: 32px;
  flex-wrap: wrap;
  gap: 16px;
}

.action-button {
  width: 220px;
}

@media (max-width: 700px) {
  .action-button {
    width: 100%;
  }
}
</style>
