<script setup lang="ts">
import { computed } from "vue";
import { Bot, LayoutDashboard, Map, Radio, Sparkles } from "lucide-vue-next";
import type { LlmStatus, Persona } from "../types";

type ViewName = "landing" | "home" | "guide" | "admin";

const props = defineProps<{
  view: ViewName;
  persona: Persona;
  llmStatus: LlmStatus;
  connected: boolean;
}>();

const emit = defineEmits<{
  navigate: [view: ViewName];
}>();

const runtimeText = computed(() => {
  if (props.llmStatus.visionAvailable && props.llmStatus.visionMultimodal) return `多模态：${props.llmStatus.visionModel || props.llmStatus.model}`;
  if (props.llmStatus.available) return `问答模型：${props.llmStatus.model}`;
  return "本地资料兜底";
});
</script>

<template>
  <header class="site-nav">
    <button class="brand" type="button" @click="emit('navigate', 'landing')">
      <span class="brand-mark"><Sparkles :size="18" /></span>
      <span>
        <strong>灵山胜境</strong>
        <small>{{ persona.name }} 小僧童导览</small>
      </span>
    </button>

    <nav class="nav-tabs" aria-label="主导航">
      <button :class="{ active: view === 'landing' }" type="button" @click="emit('navigate', 'landing')">
        <Sparkles :size="17" />
        大屏入口
      </button>
      <button :class="{ active: view === 'home' }" type="button" @click="emit('navigate', 'home')">
        <Map :size="17" />
        景区首页
      </button>
      <button :class="{ active: view === 'guide' }" type="button" @click="emit('navigate', 'guide')">
        <Bot :size="17" />
        智能导览
      </button>
      <button :class="{ active: view === 'admin' }" type="button" @click="emit('navigate', 'admin')">
        <LayoutDashboard :size="17" />
        管理后台
      </button>
    </nav>

    <div class="runtime-chip" :class="{ online: connected }" :title="runtimeText">
      <Radio :size="16" />
      <span>{{ runtimeText }}</span>
    </div>
  </header>
</template>
