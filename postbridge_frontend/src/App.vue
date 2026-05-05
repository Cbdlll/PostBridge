<template>
  <el-config-provider :locale="elementLocale">
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, watch } from 'vue'

import { applyRuntimeTranslations, elementLocale, locale } from './i18n'

let observer: MutationObserver | null = null
let translating = false
let queued = false

const runTranslations = async () => {
  if (translating) {
    queued = true
    return
  }

  translating = true
  await nextTick()
  applyRuntimeTranslations(document.body)
  translating = false

  if (queued) {
    queued = false
    void runTranslations()
  }
}

onMounted(() => {
  void runTranslations()

  observer = new MutationObserver(() => {
    void runTranslations()
  })

  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
  })
})

watch(
  locale,
  () => {
    document.documentElement.lang = locale.value
    void runTranslations()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>
