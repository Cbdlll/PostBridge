<template>
  <el-container class="main-layout">
    <el-aside width="240px" class="sidebar">
      <div class="logo">
        <div class="logo-icon">
          <el-icon :size="24"><Cpu /></el-icon>
        </div>
        <span class="logo-text">{{ t('appName') }}</span>
      </div>

      <el-menu :default-active="currentRoute" router class="sidebar-menu" :unique-opened="true">
        <el-menu-item index="/">
          <el-icon><HomeFilled /></el-icon>
          <span>{{ t('nav.dashboard') }}</span>
        </el-menu-item>

        <el-menu-item index="/accounts">
          <el-icon><UserFilled /></el-icon>
          <span>{{ t('nav.accounts') }}</span>
        </el-menu-item>

        <el-menu-item index="/videos">
          <el-icon><VideoPlay /></el-icon>
          <span>{{ t('nav.videos') }}</span>
        </el-menu-item>

        <el-menu-item index="/manual-publish">
          <el-icon><Promotion /></el-icon>
          <span>{{ t('nav.manualPublish') }}</span>
        </el-menu-item>

        <div class="menu-group">
          <div class="menu-group-title">
            <el-icon><MagicStick /></el-icon>
            <span>{{ t('nav.aiGroup') }}</span>
          </div>
          <el-menu-item index="/ai-create">
            <el-icon><Edit /></el-icon>
            {{ t('nav.aiCreate') }}
          </el-menu-item>
          <el-menu-item index="/user-persona">
            <el-icon><Avatar /></el-icon>
            {{ t('nav.userPersona') }}
          </el-menu-item>
        </div>

        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <span>{{ t('nav.tasks') }}</span>
        </el-menu-item>

        <el-menu-item index="/settings">
          <el-icon><Tools /></el-icon>
          <span>{{ t('nav.settings') }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="content-wrapper">
      <el-header class="header">
        <div class="header-left">
          <span class="page-title">{{ pageTitle }}</span>
        </div>
        <div class="header-right">
          <el-select
            :model-value="locale"
            class="language-switch"
            size="small"
            @change="handleLocaleChange"
          >
            <el-option value="en" :label="t('english')" />
            <el-option value="zh-CN" :label="t('chinese')" />
          </el-select>

          <div class="user-profile">
            <el-avatar
              :size="32"
              src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png"
            />
            <span>{{ t('admin') }}</span>
          </div>

          <el-button circle plain size="small" @click="refreshData">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Avatar,
  Cpu,
  Edit,
  HomeFilled,
  List,
  MagicStick,
  Promotion,
  Refresh,
  Tools,
  UserFilled,
  VideoPlay,
} from '@element-plus/icons-vue'

import eventBus from '@/utils/eventBus'
import { locale, setLocale, t, type Locale } from '@/i18n'

const route = useRoute()

const currentRoute = computed(() => route.path)

const pageTitle = computed(() => {
  const titleKey = route.meta?.titleKey as string | undefined
  return titleKey ? t(titleKey) : t('appName')
})

const refreshData = () => {
  eventBus.emit('refreshData')
  ElMessage.success(t('refreshSuccess'))
}

const handleLocaleChange = (value: Locale) => {
  setLocale(value)
}
</script>

<style scoped>
.main-layout {
  height: 100vh;
  background-color: var(--bg-color);
}

.sidebar {
  background: #fff;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.02);
  z-index: 10;
}

.logo {
  height: 80px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 12px;
  border-bottom: 1px solid var(--border-color);
}

.logo-icon {
  width: 40px;
  height: 40px;
  background: var(--primary-color);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 4px 10px rgba(14, 116, 144, 0.25);
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.sidebar-menu {
  border-right: none;
  padding: 16px 12px;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  border-radius: 8px;
  margin-bottom: 4px;
  height: 48px;
  color: var(--text-regular);
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background-color: var(--bg-color);
  color: var(--primary-color);
}

:deep(.el-menu-item.is-active) {
  background-color: rgba(14, 116, 144, 0.1);
  color: var(--primary-color);
  font-weight: 600;
}

.menu-group {
  margin-bottom: 4px;
}

.menu-group-title {
  height: 48px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  color: var(--text-primary);
  font-weight: 600;
  font-size: 14px;
  gap: 8px;
}

.menu-group-title .el-icon {
  font-size: 18px;
  color: var(--primary-color);
}

.menu-group :deep(.el-menu-item) {
  padding-left: 48px !important;
  height: 40px;
  margin-bottom: 2px;
}

.content-wrapper {
  flex-direction: column;
  height: 100vh;
}

.header {
  background: transparent;
  padding: 0 32px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.language-switch {
  width: 120px;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  padding: 6px 12px 6px 6px;
  border-radius: 20px;
  border: 1px solid var(--border-color);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-regular);
}

.main-content {
  padding: 0 32px 32px;
  overflow-y: auto;
}

@media (max-width: 900px) {
  .header {
    padding: 0 16px;
  }

  .main-content {
    padding: 0 16px 16px;
  }

  .language-switch {
    width: 100px;
  }
}
</style>
