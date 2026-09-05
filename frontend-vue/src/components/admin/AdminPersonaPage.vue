<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  applyPresetToPersona,
  buildPresetSummary,
  presetConfigFromKey,
  presetLabel,
  resolvePresetFromPersona,
  selectablePresetCards,
  type LiveTalkingPresetKey
} from "../../config/liveTalkingPresets";
import {
  applyLiveTalkingPreset as syncLiveTalkingRuntime,
  disconnectLiveTalking,
  ensureLiveTalkingConnected,
  interruptLiveTalking,
  personaPresetLocked,
  liveTalkingAudioStream,
  liveTalkingBaseUrl,
  liveTalkingConnected,
  liveTalkingEnabled,
  liveTalkingError,
  liveTalkingProjectDir,
  liveTalkingSessionId,
  liveTalkingStatus,
  liveTalkingStatusText,
  liveTalkingVideoStream,
  saveLiveTalkingPresetVoice,
  speakWithLiveTalking
} from "../../composables/useLiveTalkingAvatar";
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
  personaForm,
  savePersona,
  useFallbackImage
} = props.ctx;

const liveVideoRef = ref<HTMLVideoElement | null>(null);
const liveAudioRef = ref<HTMLAudioElement | null>(null);
const sendingPreview = ref(false);
const savingPreset = ref(false);
const bindStatus = ref("");
const testMessage = ref("阿弥陀佛，欢迎来到灵山胜境数字人实时导览。");
const presetCards = selectablePresetCards();

const selectedPresetKey = computed<LiveTalkingPresetKey>(() => {
  const key = personaForm.value.avatarPresetKey;
  return key === "female" || key === "custom" ? key : "male";
});

const currentRuntime = computed(() => resolvePresetFromPersona(personaForm.value));
const currentPresetLabel = computed(() => presetLabel(currentRuntime.value));
const currentPresetDetail = computed(() => buildPresetSummary(currentRuntime.value));
const nativeLiveTalkingPage = computed(() => `${liveTalkingBaseUrl}/index.html`);
const avatarGeneratorPage = computed(() => `${liveTalkingBaseUrl}/avatar.html`);
const liveTalkingSessionDisplay = computed(() => (liveTalkingSessionId.value ? `SID: ${liveTalkingSessionId.value}` : "SID: -"));
const liveTalkingStatusDisplay = computed(() => {
  if (liveTalkingStatus.value === "error" && liveTalkingError.value) return `${liveTalkingStatusText.value}：${liveTalkingError.value}`;
  return liveTalkingStatusText.value;
});
const liveTalkingActionText = computed(() => {
  if (liveTalkingStatus.value === "connecting") return "连接中";
  if (liveTalkingConnected.value) return "重新连接";
  return "开始连接";
});
const liveTalkingSummaryCards = computed(() => [
  { label: "运行目录", value: "portable_livetalking", detail: liveTalkingProjectDir },
  { label: "服务接口", value: liveTalkingBaseUrl, detail: `Avatar: ${currentRuntime.value.avatarId}` },
  { label: "音色链路", value: currentRuntime.value.ttsMode, detail: currentRuntime.value.voice }
]);

function attachMedia(element: HTMLMediaElement | null, stream: MediaStream | null) {
  if (!element || element.srcObject === stream) return;
  element.srcObject = stream;
}

function syncPersonaFromRuntime() {
  const runtime = resolvePresetFromPersona(personaForm.value);
  personaForm.value = applyPresetToPersona(personaForm.value, runtime);
}

async function selectPreset(key: LiveTalkingPresetKey) {
  if (selectedPresetKey.value === key && key !== "custom" && liveTalkingConnected.value) return;

  if (liveTalkingSessionId.value) {
    await interruptLiveTalking();
  }
  disconnectLiveTalking();

  personaPresetLocked.value = true;
  const runtime = presetConfigFromKey(key, key === "custom" ? resolvePresetFromPersona(personaForm.value) : undefined);
  personaForm.value = applyPresetToPersona({ ...personaForm.value }, runtime);
  syncLiveTalkingRuntime(runtime);
  bindStatus.value = `已选择：${presetLabel(runtime)}，正在连接新形象...`;

  const connected = await ensureLiveTalkingConnected({ force: true });
  bindStatus.value = connected
    ? `已切换：${presetLabel(runtime)}（Avatar: ${runtime.avatarId}）`
    : `已选择：${presetLabel(runtime)}，连接失败，请点「重新连接」`;
}

async function connectLiveTalkingPreview() {
  syncLiveTalkingRuntime(currentRuntime.value);
  await ensureLiveTalkingConnected({ force: true });
}

async function sendPreviewMessage() {
  sendingPreview.value = true;
  try {
    syncLiveTalkingRuntime(currentRuntime.value);
    await speakWithLiveTalking(testMessage.value);
  } finally {
    sendingPreview.value = false;
  }
}

async function saveLiveTalkingContent() {
  savingPreset.value = true;
  try {
    syncPersonaFromRuntime();
    const runtime = resolvePresetFromPersona(personaForm.value);
    syncLiveTalkingRuntime(runtime);
    await savePersona();
    if (runtime.ttsMode === "cosyvoice" || runtime.ttsMode === "gpt-sovits") {
      await saveLiveTalkingPresetVoice(runtime);
    }
    bindStatus.value = `已保存：${presetLabel(runtime)}`;
  } catch (error) {
    bindStatus.value = error instanceof Error ? error.message : "保存失败";
  } finally {
    savingPreset.value = false;
  }
}

watch([liveVideoRef, liveTalkingVideoStream], () => attachMedia(liveVideoRef.value, liveTalkingVideoStream.value), { immediate: true });
watch([liveAudioRef, liveTalkingAudioStream], () => attachMedia(liveAudioRef.value, liveTalkingAudioStream.value), { immediate: true });

onMounted(() => {
  syncLiveTalkingRuntime(resolvePresetFromPersona(personaForm.value));
});

onBeforeUnmount(() => {
  attachMedia(liveVideoRef.value, null);
  attachMedia(liveAudioRef.value, null);
});
</script>

<template>
  <section class="admin-page persona-page">
    <form class="persona-one-screen" @submit.prevent="saveLiveTalkingContent">
      <section class="persona-preview-3d">
        <div class="avatar-ring"></div>
        <video
          v-show="liveTalkingVideoStream"
          ref="liveVideoRef"
          class="persona-live-video"
          autoplay
          playsinline
          muted
        ></video>
        <img
          v-show="!liveTalkingVideoStream"
          :src="digitalHumanAvatar"
          alt="数字人形象管理 形象预览"
          @error="useFallbackImage($event, digitalHumanAvatarFallback)"
        />
        <audio v-if="liveTalkingEnabled" ref="liveAudioRef" autoplay></audio>
        <strong>数字人形象管理</strong>
        <span>当前形象源已切换到本机 portable_livetalking 实时数字人服务。</span>
        <div class="persona-preview-badges">
          <article v-for="item in liveTalkingSummaryCards" :key="item.label">
            <small>{{ item.label }}</small>
            <b>{{ item.value }}</b>
            <span>{{ item.detail }}</span>
          </article>
        </div>
      </section>

      <section class="persona-block">
        <h3>服务目录</h3>
        <label>运行目录<input :value="liveTalkingProjectDir" readonly /></label>
        <label>服务地址<input :value="liveTalkingBaseUrl" readonly /></label>
        <label>原生页面<input :value="nativeLiveTalkingPage" readonly /></label>
      </section>

      <section class="persona-block persona-preset-block">
        <h3>预设形象</h3>
        <div class="persona-preset-grid">
          <button
            v-for="card in presetCards"
            :key="card.key"
            type="button"
            class="persona-preset-card"
            :class="{ active: selectedPresetKey === card.key }"
            @click="selectPreset(card.key)"
          >
            <strong>{{ card.label }}</strong>
            <span>Avatar: {{ card.avatarId || "自定义" }}</span>
            <span>{{ card.key === "custom" ? card.summary : `音色：${card.voice}` }}</span>
            <em>{{ card.voiceHint }}</em>
          </button>
        </div>
        <p class="persona-preset-summary">当前选择：{{ currentPresetLabel }}，预设音频：{{ currentRuntime.refAudio }}</p>
        <label>当前 Avatar<input :value="currentRuntime.avatarId" readonly /></label>
      </section>

      <section class="persona-block">
        <h3>音色绑定</h3>
        <template v-if="selectedPresetKey === 'custom'">
          <label>
            Avatar ID
            <input v-model="personaForm.avatarId" placeholder="例如 my_avatar_01" />
          </label>
          <label>
            参考音频路径
            <input v-model="personaForm.refAudio" placeholder="data/ref_audio/xxx.wav" />
          </label>
          <label>
            参考文本
            <input v-model="personaForm.refText" />
          </label>
          <label>
            音色标识
            <input v-model="personaForm.avatarVoice" placeholder="zh-CN-YunyangNeural" />
          </label>
          <label>
            TTS 模式
            <select v-model="personaForm.ttsMode">
              <option value="edgetts">edgetts</option>
              <option value="cosyvoice">cosyvoice</option>
              <option value="gpt-sovits">gpt-sovits</option>
            </select>
          </label>
          <p class="persona-custom-hint">
            需要新形象？打开
            <a :href="avatarGeneratorPage" target="_blank" rel="noreferrer">avatar.html 生成数字人</a>
            ，训练完成后在此填写 avatar_id 与参考音频路径。
          </p>
        </template>
        <template v-else>
          <label>参考音频文件<input :value="currentRuntime.refAudio" readonly /></label>
          <label>参考文本<input :value="currentRuntime.refText" readonly /></label>
          <label>音色模式<input :value="`${currentRuntime.ttsMode} / ${currentRuntime.voice}`" readonly /></label>
          <label>形象摘要<input :value="currentPresetDetail" readonly /></label>
        </template>
        <p v-if="bindStatus" class="persona-bind-status">{{ bindStatus }}</p>
      </section>

      <section class="persona-block">
        <h3>实时画面</h3>
        <label>连接状态<input :value="liveTalkingStatusDisplay" readonly /></label>
        <label>会话编号<input :value="liveTalkingSessionDisplay" readonly /></label>
        <label>
          测试播报
          <input v-model="testMessage" />
        </label>
        <button
          class="secondary-action compact"
          type="button"
          :disabled="!liveTalkingEnabled || liveTalkingStatus === 'connecting'"
          @click="connectLiveTalkingPreview"
        >
          {{ liveTalkingActionText }}
        </button>
        <button
          class="secondary-action compact"
          type="button"
          :disabled="!liveTalkingEnabled || sendingPreview"
          @click="sendPreviewMessage"
        >
          {{ sendingPreview ? "发送中" : "发送测试" }}
        </button>
        <button class="secondary-action compact" type="button" :disabled="!liveTalkingSessionId" @click="interruptLiveTalking">
          打断
        </button>
        <button
          class="primary-action compact"
          type="submit"
          :class="actionStatusClass('savePersona')"
          :disabled="isActionBusy('savePersona') || savingPreset"
        >
          <Save :size="16" />
          {{ savingPreset ? "保存中" : actionLabel("savePersona", "保存预设音色", "保存中", "已保存", "保存失败") }}
        </button>
      </section>
    </form>
  </section>
</template>
