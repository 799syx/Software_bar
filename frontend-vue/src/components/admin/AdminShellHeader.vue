<script setup lang="ts">
import type { useAdminView } from "./useAdminView";

type AdminViewContext = ReturnType<typeof useAdminView>;

const props = defineProps<{
  ctx: AdminViewContext;
}>();

const {
  RefreshCw,
  actionLabel,
  actionStatusClass,
  adminError,
  adminTabs,
  adminToken,
  activeTab,
  isActionBusy,
  notice,
  refreshAll
} = props.ctx;
</script>

<template>
  <nav class="admin-tabs four-tabs" aria-label="管理功能">
    <button v-for="tab in adminTabs" :key="tab.key" type="button" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">
      <component :is="tab.icon" :size="17" />
      {{ tab.label }}
    </button>
  </nav>

  <section class="admin-utility-bar">
    <div>
      <strong>灵山胜境管理台</strong>
      <span>四个主入口保留，常用维护集中在内容与点位。</span>
    </div>
    <label class="token-field compact-token-field">
      管理令牌
      <input v-model="adminToken" type="password" autocomplete="off" placeholder="用于保存、导入和停用" />
    </label>
    <button class="secondary-action compact" type="button" :class="actionStatusClass('refresh')" :disabled="isActionBusy('refresh')" @click="refreshAll">
      <RefreshCw :size="16" />
      {{ actionLabel("refresh", "刷新", "刷新中", "已刷新", "刷新失败") }}
    </button>
  </section>

  <p v-if="notice" class="inline-alert admin-alert">{{ notice }}</p>
  <p v-if="adminError" class="inline-alert error admin-alert">{{ adminError }}</p>
</template>
