<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Bot, Mic, Radio, Square, Video, Volume2 } from "lucide-vue-next";
import { digitalHumanAvatar, digitalHumanAvatarFallback, useFallbackImage } from "../assets";
import {
  ensureLiveTalkingConnected,
  liveTalkingAudioStream,
  liveTalkingConnected,
  liveTalkingEnabled,
  liveTalkingError,
  liveTalkingStatus,
  liveTalkingStatusText,
  liveTalkingVideoStream
} from "../composables/useLiveTalkingAvatar";
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

const liveVideoRef = ref<HTMLVideoElement | null>(null);
const liveAudioRef = ref<HTMLAudioElement | null>(null);

const liveTalkingLabel = computed(() => {
  if (!liveTalkingEnabled) return "静态头像";
  if (liveTalkingError.value && liveTalkingStatus.value === "error") return "可重连";
  return liveTalkingStatusText.value;
});

const liveTalkingActionText = computed(() => {
  if (liveTalkingStatus.value === "connecting") return "连接中";
  if (liveTalkingConnected.value) return "重连数字人";
  return "连接数字人";
});

function attachMedia(element: HTMLMediaElement | null, stream: MediaStream | null) {
  if (!element || element.srcObject === stream) return;
  element.srcObject = stream;
}

watch([liveVideoRef, liveTalkingVideoStream], () => attachMedia(liveVideoRef.value, liveTalkingVideoStream.value), { immediate: true });
watch([liveAudioRef, liveTalkingAudioStream], () => attachMedia(liveAudioRef.value, liveTalkingAudioStream.value), { immediate: true });

onBeforeUnmount(() => {
  attachMedia(liveVideoRef.value, null);
  attachMedia(liveAudioRef.value, null);
});
</script>

<template>
  <aside
    class="digital-panel"
    :class="[stage, `expression-${expression}`, `mouth-${mouthShape}`, { 'has-caption': !!spokenText, 'live-connected': liveTalkingConnected }]"
  >
    <div class="avatar-stage">
      <div class="avatar-orbit"></div>
      <div class="avatar-aura"></div>
      <div class="avatar-portrait-stage" :class="{ 'with-live-video': !!liveTalkingVideoStream }">
        <video
          v-show="liveTalkingVideoStream"
          ref="liveVideoRef"
          class="live-avatar-video"
          autoplay
          playsinline
          muted
        ></video>
        <img
          v-show="!liveTalkingVideoStream"
          class="avatar-image"
          :src="digitalHumanAvatar"
          :alt="`${persona.name} 数字导览员`"
          @error="useFallbackImage($event, digitalHumanAvatarFallback)"
        />
      </div>
      <audio v-if="liveTalkingEnabled" ref="liveAudioRef" class="live-avatar-audio" autoplay></audio>
      <div v-if="liveTalkingEnabled" class="live-avatar-status" :class="liveTalkingStatus">
        <Video :size="14" />
        <span>{{ liveTalkingLabel }}</span>
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
        <strong>{{ liveTalkingEnabled ? liveTalkingLabel : ttsStatus.available ? "云端语音" : "浏览器语音" }}</strong>
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
      <button
        v-if="liveTalkingEnabled"
        type="button"
        class="secondary-action compact"
        :disabled="liveTalkingStatus === 'connecting'"
        @click="ensureLiveTalkingConnected({ force: true })"
      >
        <Video :size="17" />
        {{ liveTalkingActionText }}
      </button>
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
