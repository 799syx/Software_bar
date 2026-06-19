<script setup lang="ts">
import { Bot, Mic, Radio, Square, Volume2 } from "lucide-vue-next";
import { digitalHumanAvatar, digitalHumanAvatarFallback, useFallbackImage } from "../assets";
import type { LlmStatus, Persona, TtsStatus } from "../types";

export type AvatarStage = "idle" | "listening" | "thinking" | "speaking" | "error";
export type AvatarExpression = "calm" | "smile" | "focused" | "surprised" | "concerned";
export type AvatarMouthShape = "rest" | "a" | "o" | "e" | "i" | "u";

defineProps<{
  persona: Persona;
  llmStatus: LlmStatus;
  ttsStatus: TtsStatus;
  stage: AvatarStage;
  expression: AvatarExpression;
  mouthShape: AvatarMouthShape;
  spokenText: string;
  speechProgress: number;
  autoSpeak: boolean;
  speechSupported: boolean;
}>();

const emit = defineEmits<{
  toggleAutoSpeak: [value: boolean];
  speakGreeting: [];
  stopSpeaking: [];
}>();

const stageText: Record<AvatarStage, string> = {
  idle: "待命",
  listening: "正在听",
  thinking: "思考中",
  speaking: "讲解中",
  error: "需处理"
};

const expressionText: Record<AvatarExpression, string> = {
  calm: "自然待命",
  smile: "微笑讲解",
  focused: "专注聆听",
  surprised: "灵感生成",
  concerned: "异常提醒"
};
</script>

<template>
  <aside class="digital-panel" :class="[stage, `expression-${expression}`, { 'has-caption': !!spokenText }]">
    <div class="avatar-stage">
      <div class="avatar-orbit"></div>
      <div class="avatar-aura"></div>
      <div class="avatar-portrait-stage">
        <img
          class="avatar-image"
          :src="digitalHumanAvatar"
          :alt="`${persona.name} 数字导览员`"
          @error="useFallbackImage($event, digitalHumanAvatarFallback)"
        />
      </div>
      <div class="avatar-caption" aria-live="polite">
        <span>{{ spokenText || expressionText[expression] }}</span>
        <i :style="{ width: `${Math.round(speechProgress * 100)}%` }"></i>
      </div>
      <div class="avatar-signal" aria-hidden="true">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>

    <div class="avatar-copy">
      <p class="section-kicker">数字导览员</p>
      <h2>{{ persona.name }}</h2>
      <p>{{ persona.role }}，{{ persona.style }}。当前状态：{{ stageText[stage] }} · {{ expressionText[expression] }}</p>
    </div>

    <div class="status-list">
      <div>
        <Bot :size="18" />
        <span>问答</span>
        <strong>{{ llmStatus.chatFastMode ? "资料快答" : llmStatus.available ? "AI 在线" : "本地资料" }}</strong>
      </div>
      <div>
        <Mic :size="18" />
        <span>语音输入</span>
        <strong>{{ speechSupported ? "可使用" : "文字兜底" }}</strong>
      </div>
      <div>
        <Radio :size="18" />
        <span>图片讲解</span>
        <strong>{{ llmStatus.visionAvailable && llmStatus.visionMultimodal ? "可使用" : "待配置" }}</strong>
      </div>
      <div>
        <Volume2 :size="18" />
        <span>播报</span>
        <strong>{{ ttsStatus.available ? "云端语音" : "浏览器语音" }}</strong>
      </div>
    </div>

    <label class="toggle-row">
      <input
        type="checkbox"
        :checked="autoSpeak"
        @change="emit('toggleAutoSpeak', ($event.target as HTMLInputElement).checked)"
      />
      <span>点击景点后自动播报</span>
    </label>

    <div class="panel-actions">
      <button type="button" class="secondary-action compact" @click="emit('speakGreeting')">
        <Volume2 :size="17" />
        播放讲解
      </button>
      <button type="button" class="ghost-action compact" @click="emit('stopSpeaking')">
        <Square :size="16" />
        停止
      </button>
    </div>
  </aside>
</template>
