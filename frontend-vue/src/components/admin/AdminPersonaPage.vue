<script setup lang="ts">
import type { useAdminView } from "./useAdminView";

type AdminViewContext = ReturnType<typeof useAdminView>;

const props = defineProps<{
  ctx: AdminViewContext;
}>();

const {
  Save,
  actionLabel,
  actionStatusClass,
  digitalHumanAvatar,
  digitalHumanAvatarFallback,
  isActionBusy,
  modal,
  personaForm,
  personaSummaryCards,
  savePersona,
  useFallbackImage
} = props.ctx;
</script>

<template>
  <section class="admin-page persona-page">
    <form class="persona-one-screen" @submit.prevent="savePersona">
      <section class="persona-preview-3d">
        <div class="avatar-ring"></div>
        <img :src="digitalHumanAvatar" :alt="`${personaForm.name} 形象预览`" @error="useFallbackImage($event, digitalHumanAvatarFallback)" />
        <strong>{{ personaForm.name }}</strong>
        <span>{{ personaForm.role }}</span>
        <div class="persona-preview-badges">
          <article v-for="item in personaSummaryCards" :key="item.label">
            <small>{{ item.label }}</small>
            <b>{{ item.value }}</b>
            <span>{{ item.detail }}</span>
          </article>
        </div>
      </section>

      <section class="persona-block">
        <h3>基础形象</h3>
        <label>名称<input v-model="personaForm.name" /></label>
        <label>身份<input v-model="personaForm.role" /></label>
        <label>主色<input v-model="personaForm.accentColor" type="color" /></label>
      </section>
      <section class="persona-block">
        <h3>服装文化</h3>
        <label>服装设定<input v-model="personaForm.costume" /></label>
        <label>讲解风格<input v-model="personaForm.style" /></label>
      </section>
      <section class="persona-block">
        <h3>声音播报</h3>
        <label>语音标识<input v-model="personaForm.voice" /></label>
        <label class="range-field">
          <span>语速 <output>{{ Number(personaForm.voiceSpeed || 1).toFixed(2) }}</output></span>
          <input v-model.number="personaForm.voiceSpeed" type="range" min="0.75" max="1.25" step="0.01" />
        </label>
        <label class="range-field">
          <span>语调 <output>{{ Number(personaForm.voicePitch || 1).toFixed(2) }}</output></span>
          <input v-model.number="personaForm.voicePitch" type="range" min="0.8" max="1.2" step="0.01" />
        </label>
      </section>
      <section class="persona-block">
        <h3>表情口型</h3>
        <label>状态设定<input v-model="personaForm.expressionProfile" /></label>
        <button class="secondary-action compact" type="button" @click="modal = 'personaAdvanced'">进入高级设置</button>
        <button class="primary-action compact" type="submit" :class="actionStatusClass('savePersona')" :disabled="isActionBusy('savePersona')">
          <Save :size="16" />
          {{ actionLabel("savePersona", "保存数字人", "保存中", "已保存", "保存失败") }}
        </button>
      </section>
    </form>
  </section>
</template>
