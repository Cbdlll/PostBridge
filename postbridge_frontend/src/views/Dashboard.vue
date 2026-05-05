<template>
  <div class="dashboard-page page-container">
    <div class="section-title">{{ t('dashboard.shortcuts') }}</div>
    <div class="shortcuts-grid">
      <div class="shortcut-card bg-gradient-purple" @click="$router.push('/ai-create')">
        <div class="shortcut-icon"><el-icon><MagicStick /></el-icon></div>
        <div class="shortcut-info">
          <h3>{{ t('dashboard.smartCreation') }}</h3>
          <p>{{ t('dashboard.smartCreationDesc') }}</p>
        </div>
      </div>
      <div class="shortcut-card bg-gradient-blue" @click="$router.push('/user-persona')">
        <div class="shortcut-icon"><el-icon><User /></el-icon></div>
        <div class="shortcut-info">
          <h3>{{ t('dashboard.personas') }}</h3>
          <p>{{ t('dashboard.personasDesc') }}</p>
        </div>
      </div>
      <div class="shortcut-card bg-gradient-green" @click="$router.push('/accounts')">
        <div class="shortcut-icon"><el-icon><UserFilled /></el-icon></div>
        <div class="shortcut-info">
          <h3>{{ t('dashboard.accountManager') }}</h3>
          <p>{{ t('dashboard.accountManagerDesc') }}</p>
        </div>
      </div>
      <div class="shortcut-card bg-gradient-orange" @click="$router.push('/videos')">
        <div class="shortcut-icon"><el-icon><VideoPlay /></el-icon></div>
        <div class="shortcut-info">
          <h3>{{ t('dashboard.videoLibrary') }}</h3>
          <p>{{ t('dashboard.videoLibraryDesc') }}</p>
        </div>
      </div>
    </div>

    <div class="section-title" style="margin-top: 40px;">{{ t('dashboard.userInsights') }}</div>
    <p class="section-subtitle">{{ t('dashboard.userInsightsDesc') }}</p>

    <div class="charts-container">
      <div class="chart-card">
        <div class="chart-header">
          <span class="chart-title">{{ t('dashboard.userDistribution') }}</span>
          <span class="chart-subtitle">{{ t('dashboard.usersUnit') }}</span>
        </div>
        <v-chart :option="userDistributionOption" autoresize class="chart" />
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <span class="chart-title">{{ t('dashboard.radar') }}</span>
          <span class="chart-subtitle">{{ t('dashboard.radarDesc') }}</span>
        </div>
        <v-chart :option="radarOption" autoresize class="chart" />
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <span class="chart-title">{{ t('dashboard.engagement') }}</span>
          <span class="chart-subtitle">{{ t('dashboard.engagementDesc') }}</span>
        </div>
        <v-chart :option="engagementOption" autoresize class="chart" />
      </div>
    </div>

    <div class="section-title" style="margin-top: 32px;">{{ t('dashboard.contentStrategy') }}</div>
    <div class="personas-grid">
      <div
        v-for="platform in platformCards"
        :key="platform.id"
        class="persona-card"
        :style="{ '--platform-color': platform.color, '--platform-glow': platform.glow }"
      >
        <div class="persona-header">
          <div class="platform-badge">
            <span class="platform-icon">{{ platform.icon }}</span>
            <span class="platform-name">{{ platform.name }}</span>
          </div>
          <div class="user-count">
            <span class="count-value">{{ platform.users }}</span>
            <span class="count-label">{{ t('dashboard.monthlyUsers') }}</span>
          </div>
        </div>

        <div class="persona-tags">
          <span v-for="tag in platform.tags" :key="tag" class="tag-item">{{ tag }}</span>
        </div>

        <div class="persona-style">
          <span class="style-label">{{ t('dashboard.contentStyle') }}</span>
          <span class="style-value">{{ platform.style }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart, RadarChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  RadarComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { MagicStick, User, UserFilled, VideoPlay } from '@element-plus/icons-vue'

import { locale, t } from '@/i18n'

use([
  CanvasRenderer,
  PieChart,
  RadarChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  RadarComponent,
])

const localizedCopy = {
  en: {
    douyin: {
      name: 'DY',
      users: '766M',
      tags: ['Algorithm reach', 'Interest commerce', 'Wide funnel', 'Immersive conversion'],
      style: 'Full-funnel conversion',
    },
    xhs: {
      name: 'XHS',
      users: '350M',
      tags: ['Search intent', 'Seeding', 'Brand affinity', 'Tier-1 cities'],
      style: 'Discovery-led trust',
    },
    ks: {
      name: 'KS',
      users: '731M',
      tags: ['Community trust', 'Trust commerce', 'New-tier cities', 'Daily goods'],
      style: 'Community conversion',
    },
    wx: {
      name: 'WX',
      users: '1B+',
      tags: ['Private traffic', 'Social spread', 'Older users', 'High AOV'],
      style: 'Private-domain trust',
    },
    bilibili: {
      name: 'Bili',
      users: '348M',
      tags: ['Community fit', 'Gen Z', 'Long-tail value', 'Campus density'],
      style: 'Credibility-led influence',
    },
  },
  'zh-CN': {
    douyin: {
      name: '抖音',
      users: '7.66亿',
      tags: ['算法分发', '兴趣电商', '全域漏斗', '沉浸转化'],
      style: '全链路成交型内容',
    },
    xhs: {
      name: '小红书',
      users: '3.5亿',
      tags: ['主动搜索', '种草决策', '品牌调性', '高线城市'],
      style: '种草驱动信任建立',
    },
    ks: {
      name: '快手',
      users: '7.31亿',
      tags: ['社区关系', '信任电商', '下沉市场', '日常消费'],
      style: '社区信任转化内容',
    },
    wx: {
      name: '视频号',
      users: '10亿+',
      tags: ['私域闭环', '社交传播', '银发用户', '高客单价'],
      style: '私域信任闭环内容',
    },
    bilibili: {
      name: 'B站',
      users: '3.48亿',
      tags: ['圈层共鸣', 'Z世代', '长尾价值', '校园密度'],
      style: '内容可信度驱动影响力',
    },
  },
} as const

const platformTheme = [
  { id: 'douyin', icon: 'D', color: '#0f172a', glow: 'rgba(15, 23, 42, 0.35)', userValue: 7.66, engagement: 85, female: 48, young: 75, content: 90 },
  { id: 'xhs', icon: 'X', color: '#e11d48', glow: 'rgba(225, 29, 72, 0.3)', userValue: 3.5, engagement: 72, female: 70, young: 85, content: 85 },
  { id: 'ks', icon: 'K', color: '#f97316', glow: 'rgba(249, 115, 22, 0.3)', userValue: 7.31, engagement: 78, female: 48, young: 55, content: 75 },
  { id: 'wx', icon: 'W', color: '#16a34a', glow: 'rgba(22, 163, 74, 0.3)', userValue: 10, engagement: 65, female: 47, young: 35, content: 70 },
  { id: 'bilibili', icon: 'B', color: '#0284c7', glow: 'rgba(2, 132, 199, 0.3)', userValue: 3.48, engagement: 90, female: 43, young: 90, content: 88 },
]

const localizedPlatforms = computed(() =>
  platformTheme.map((item) => ({
    ...item,
    ...localizedCopy[locale.value][item.id as keyof typeof localizedCopy.en],
  })),
)

const platformCards = computed(() => localizedPlatforms.value)

const userDistributionOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter:
      locale.value === 'zh-CN'
        ? '{b}: {c} ({d}%)'
        : '{b}: {c} ({d}%)',
  },
  legend: {
    orient: 'vertical',
    right: 10,
    top: 'center',
    type: 'scroll',
    textStyle: { color: '#6b7280', fontSize: 11 },
  },
  series: [
    {
      type: 'pie',
      radius: ['42%', '70%'],
      center: ['40%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#ffffff', borderWidth: 3 },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#111827' },
      },
      data: localizedPlatforms.value.map((platform) => ({
        value: platform.userValue,
        name: platform.name,
        itemStyle: { color: platform.color },
      })),
    },
  ],
}))

const radarOption = computed(() => ({
  tooltip: {},
  legend: {
    bottom: 0,
    textStyle: { color: '#6b7280', fontSize: 10 },
    data: localizedPlatforms.value.map((platform) => ({
      name: platform.name,
      itemStyle: { color: platform.color },
    })),
  },
  radar: {
    indicator: [
      { name: t('dashboard.radarIndicators.engagement'), max: 100 },
      { name: t('dashboard.radarIndicators.female'), max: 100 },
      { name: t('dashboard.radarIndicators.young'), max: 100 },
      { name: t('dashboard.radarIndicators.content'), max: 100 },
    ],
    radius: '60%',
    axisName: { color: '#6b7280', fontSize: 11 },
    splitArea: { areaStyle: { color: ['rgba(15, 23, 42, 0.02)', 'rgba(15, 23, 42, 0.05)'] } },
    axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.18)' } },
    splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.18)' } },
  },
  series: [
    {
      type: 'radar',
      symbol: 'none',
      data: localizedPlatforms.value.map((platform) => ({
        value: [platform.engagement, platform.female, platform.young, platform.content],
        name: platform.name,
        lineStyle: { color: platform.color, width: 2 },
        areaStyle: { color: `${platform.color}22` },
        itemStyle: { color: platform.color },
      })),
    },
  ],
}))

const engagementOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: {
    type: 'category',
    data: localizedPlatforms.value.map((platform) => platform.name),
    axisLabel: {
      color: '#6b7280',
      interval: 0,
      rotate: 0,
      width: 72,
      overflow: 'break',
    },
    axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.18)' } },
  },
  yAxis: {
    type: 'value',
    max: 100,
    axisLabel: { color: '#6b7280' },
    splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } },
  },
  series: [
    {
      type: 'bar',
      barWidth: '50%',
      data: localizedPlatforms.value.map((platform) => ({
        value: platform.engagement,
        itemStyle: { color: platform.color, borderRadius: [6, 6, 0, 0] },
      })),
    },
  ],
}))
</script>

<style scoped>
.section-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.section-subtitle {
  color: var(--text-secondary);
  font-size: 14px;
  margin-top: -8px;
  margin-bottom: 20px;
}

.shortcuts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 20px;
}

@media (max-width: 600px) {
  .shortcuts-grid {
    grid-template-columns: 1fr;
  }
}

.shortcut-card {
  min-height: 112px;
  border-radius: 14px;
  padding: 18px;
  display: flex;
  align-items: center;
  gap: 16px;
  color: #fff;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  min-width: 0;
}

.shortcut-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.18);
}

.shortcut-icon {
  width: 48px;
  height: 48px;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex: 0 0 48px;
}

.shortcut-info {
  min-width: 0;
}

.shortcut-info h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 2px;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.shortcut-info p {
  font-size: 12px;
  opacity: 0.92;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.bg-gradient-blue {
  background: linear-gradient(135deg, #0891b2 0%, #22c55e 100%);
}

.bg-gradient-purple {
  background: linear-gradient(135deg, #0f172a 0%, #2563eb 100%);
}

.bg-gradient-green {
  background: linear-gradient(135deg, #047857 0%, #14b8a6 100%);
}

.bg-gradient-orange {
  background: linear-gradient(135deg, #ea580c 0%, #f59e0b 100%);
}

.charts-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 20px;
}

.chart-card {
  background: #ffffff;
  border-radius: 14px;
  padding: 20px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
  min-width: 0;
}

.chart-header {
  margin-bottom: 12px;
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.chart-subtitle {
  font-size: 11px;
  color: var(--text-secondary);
  margin-left: 0;
  line-height: 1.35;
}

.chart {
  height: 240px;
}

.personas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

@media (max-width: 600px) {
  .personas-grid {
    grid-template-columns: 1fr;
  }
}

.persona-card {
  background: #ffffff;
  border-radius: 14px;
  padding: 18px;
  color: var(--text-primary);
  position: relative;
  overflow: hidden;
  transition: transform 0.3s, box-shadow 0.3s;
  border: 1px solid rgba(148, 163, 184, 0.16);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
  min-width: 0;
}

.persona-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 4px;
  background: var(--platform-color);
  box-shadow: 0 0 18px var(--platform-glow);
}

.persona-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.1);
}

.persona-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}

.platform-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.platform-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--platform-color);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  flex: 0 0 28px;
}

.platform-name {
  font-size: 16px;
  font-weight: 700;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.user-count {
  text-align: right;
  flex: 0 0 auto;
}

.count-value {
  display: block;
  font-size: 15px;
  font-weight: 700;
  color: var(--platform-color);
}

.count-label {
  font-size: 10px;
  color: var(--text-secondary);
  display: block;
  max-width: 76px;
  line-height: 1.15;
}

.persona-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.tag-item {
  padding: 3px 8px;
  background: rgba(15, 23, 42, 0.04);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 10px;
  font-size: 10px;
  color: var(--text-regular);
  line-height: 1.3;
  overflow-wrap: anywhere;
}

.persona-style {
  padding-top: 10px;
  border-top: 1px solid rgba(148, 163, 184, 0.16);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.style-label {
  font-size: 10px;
  color: var(--text-secondary);
}

.style-value {
  font-size: 11px;
  color: var(--text-regular);
  font-weight: 500;
  line-height: 1.35;
  overflow-wrap: anywhere;
}
</style>
