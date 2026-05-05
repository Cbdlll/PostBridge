import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        {
          path: '',
          name: 'Dashboard',
          component: () => import('@/views/Dashboard.vue'),
          meta: { titleKey: 'nav.dashboard' },
        },
        {
          path: 'accounts',
          name: 'Accounts',
          component: () => import('@/views/Accounts.vue'),
          meta: { titleKey: 'nav.accounts' },
        },
        {
          path: 'videos',
          name: 'VideoManager',
          component: () => import('@/views/VideoManager.vue'),
          meta: { titleKey: 'nav.videos' },
        },
        {
          path: 'manual-publish',
          name: 'ManualPublish',
          component: () => import('@/views/ManualPublish.vue'),
          meta: { titleKey: 'nav.manualPublish' },
        },
        {
          path: 'ai-create',
          name: 'AICreate',
          component: () => import('@/views/AICreate.vue'),
          meta: { titleKey: 'nav.aiCreate' },
        },
        {
          path: 'user-persona',
          name: 'UserPersona',
          component: () => import('@/views/UserPersona.vue'),
          meta: { titleKey: 'nav.userPersona' },
        },
        {
          path: 'tasks',
          name: 'Tasks',
          component: () => import('@/views/Tasks.vue'),
          meta: { titleKey: 'nav.tasks' },
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/Settings.vue'),
          meta: { titleKey: 'nav.settings' },
        },
      ],
    },
  ],
})

export default router
