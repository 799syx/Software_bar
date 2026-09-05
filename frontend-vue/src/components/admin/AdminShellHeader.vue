<script setup lang="ts">
import type { useAdminView } from "./useAdminView";

type AdminViewContext = ReturnType<typeof useAdminView>;

const props = defineProps<{
  ctx: AdminViewContext;
}>();

const {
  adminError,
  adminTabs,
  activeTab,
  notice
} = props.ctx;
</script>

<template>
  <nav class="admin-tabs four-tabs" aria-label="管理功能">
    <button v-for="tab in adminTabs" :key="tab.key" type="button" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">
      <component :is="tab.icon" :size="17" />
      {{ tab.label }}
    </button>
  </nav>

  <p v-if="notice" class="inline-alert admin-alert">{{ notice }}</p>
  <p v-if="adminError" class="inline-alert error admin-alert">{{ adminError }}</p>
</template>
