import { computed, ref } from "vue";
import {
  defaultRuntimeFromEnv,
  type LiveTalkingRuntimeConfig
} from "../config/liveTalkingPresets";

type LiveTalkingStatus = "disabled" | "idle" | "connecting" | "connected" | "speaking" | "error";

type LiveTalkingOfferResponse = {
  sdp?: string;
  type?: RTCSdpType;
  sessionid?: string;
  code?: number;
  msg?: string;
};

type LiveTalkingJsonResponse = {
  code?: number;
  msg?: string;
};

const DEFAULT_PROJECT_DIR = String.raw`D:\download\portable_livetalking.zip\景区数字人\portable_livetalking`;

function normalizeBaseUrl(value: string) {
  return value.trim().replace(/\/$/, "");
}

function envFlag(value: unknown, fallback = true) {
  if (value === undefined || value === null || String(value).trim() === "") return fallback;
  return !["0", "false", "no", "off", "disabled"].includes(String(value).trim().toLowerCase());
}

export const liveTalkingBaseUrl = normalizeBaseUrl(String(import.meta.env.VITE_LIVETALKING_BASE || "http://127.0.0.1:8010"));
export const liveTalkingProjectDir = String(import.meta.env.VITE_LIVETALKING_DIR || DEFAULT_PROJECT_DIR).trim();
export const liveTalkingEnabled = envFlag(import.meta.env.VITE_LIVETALKING_ENABLED, true) && Boolean(liveTalkingBaseUrl);

const runtimeDefaults = defaultRuntimeFromEnv();
const runtimePresetKey = ref(runtimeDefaults.presetKey);
const runtimeAvatarId = ref(runtimeDefaults.avatarId);
const runtimeRefAudio = ref(runtimeDefaults.refAudio);
const runtimeRefText = ref(runtimeDefaults.refText);
const runtimeVoice = ref(runtimeDefaults.voice);
const runtimeTtsMode = ref(runtimeDefaults.ttsMode);

export const liveTalkingAvatarId = computed(() => runtimeAvatarId.value);
export const liveTalkingVoice = computed(() => runtimeVoice.value);
export const liveTalkingTtsMode = computed(() => runtimeTtsMode.value);
export const liveTalkingRefAudio = computed(() => runtimeRefAudio.value);
export const liveTalkingRefText = computed(() => runtimeRefText.value);
export const liveTalkingPresetKey = computed(() => runtimePresetKey.value);

export const liveTalkingStatus = ref<LiveTalkingStatus>(liveTalkingEnabled ? "idle" : "disabled");
export const liveTalkingError = ref("");
export const liveTalkingSessionId = ref("");
export const liveTalkingVideoStream = ref<MediaStream | null>(null);
export const liveTalkingAudioStream = ref<MediaStream | null>(null);

let peerConnection: RTCPeerConnection | null = null;
let connectingPromise: Promise<boolean> | null = null;
let unavailableUntil = 0;

/** 管理端正在编辑未保存的预设时，阻止全局 persona 轮询覆盖本地选择 */
export const personaPresetLocked = ref(false);

export const liveTalkingConnected = computed(
  () => liveTalkingStatus.value === "connected" || liveTalkingStatus.value === "speaking"
);

export const liveTalkingStatusText = computed(() => {
  if (!liveTalkingEnabled) return "未启用";
  if (liveTalkingStatus.value === "connecting") return "连接中";
  if (liveTalkingStatus.value === "connected") return "已接入";
  if (liveTalkingStatus.value === "speaking") return "讲解中";
  if (liveTalkingStatus.value === "error") return "未连接";
  return "待连接";
});

function endpoint(path: string) {
  return `${liveTalkingBaseUrl}${path}`;
}

function waitForIceGatheringComplete(pc: RTCPeerConnection) {
  if (pc.iceGatheringState === "complete") return Promise.resolve();
  return new Promise<void>((resolve) => {
    const checkState = () => {
      if (pc.iceGatheringState !== "complete") return;
      pc.removeEventListener("icegatheringstatechange", checkState);
      resolve();
    };
    pc.addEventListener("icegatheringstatechange", checkState);
  });
}

function offerRefAudio() {
  if (runtimeTtsMode.value === "cosyvoice" || runtimeTtsMode.value === "gpt-sovits") return runtimeRefAudio.value;
  return runtimeVoice.value;
}

function closePeerConnection(nextStatus: LiveTalkingStatus = liveTalkingEnabled ? "idle" : "disabled") {
  if (peerConnection) {
    peerConnection.ontrack = null;
    peerConnection.onconnectionstatechange = null;
    peerConnection.close();
    peerConnection = null;
  }
  liveTalkingSessionId.value = "";
  liveTalkingVideoStream.value = null;
  liveTalkingAudioStream.value = null;
  liveTalkingStatus.value = nextStatus;
}

export function applyLiveTalkingPreset(config: LiveTalkingRuntimeConfig) {
  const changed =
    runtimePresetKey.value !== config.presetKey ||
    runtimeAvatarId.value !== config.avatarId ||
    runtimeRefAudio.value !== config.refAudio ||
    runtimeRefText.value !== config.refText ||
    runtimeVoice.value !== config.voice ||
    runtimeTtsMode.value !== config.ttsMode;

  runtimePresetKey.value = config.presetKey;
  runtimeAvatarId.value = config.avatarId;
  runtimeRefAudio.value = config.refAudio;
  runtimeRefText.value = config.refText;
  runtimeVoice.value = config.voice;
  runtimeTtsMode.value = config.ttsMode;

  if (changed && (peerConnection || liveTalkingSessionId.value)) {
    closePeerConnection("idle");
    liveTalkingError.value = "";
  }
}

async function connectLiveTalking(force = false) {
  if (!liveTalkingEnabled || typeof RTCPeerConnection === "undefined") {
    liveTalkingStatus.value = "disabled";
    return false;
  }
  if (!force && liveTalkingConnected.value && peerConnection && liveTalkingSessionId.value) return true;
  if (connectingPromise) {
    if (!force) return connectingPromise;
    await connectingPromise.catch(() => false);
  }
  if (!force && unavailableUntil > Date.now()) return false;

  connectingPromise = (async () => {
    closePeerConnection("connecting");
    liveTalkingError.value = "";

    try {
      const pc = new RTCPeerConnection();
      peerConnection = pc;
      pc.addTransceiver("video", { direction: "recvonly" });
      pc.addTransceiver("audio", { direction: "recvonly" });

      pc.ontrack = (event) => {
        const stream = event.streams[0] || new MediaStream([event.track]);
        if (event.track.kind === "video") liveTalkingVideoStream.value = stream;
        if (event.track.kind === "audio") liveTalkingAudioStream.value = stream;
      };

      pc.onconnectionstatechange = () => {
        if (!peerConnection || pc !== peerConnection) return;
        if (pc.connectionState === "connected") {
          liveTalkingStatus.value = liveTalkingStatus.value === "speaking" ? "speaking" : "connected";
          liveTalkingError.value = "";
        }
        if (pc.connectionState === "failed" || pc.connectionState === "closed") {
          closePeerConnection("error");
          liveTalkingError.value = "数字人连接已断开";
        }
      };

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      await waitForIceGatheringComplete(pc);

      const localDescription = pc.localDescription;
      if (!localDescription?.sdp || !localDescription.type) throw new Error("WebRTC offer 创建失败");

      const response = await fetch(endpoint("/offer"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sdp: localDescription.sdp,
          type: localDescription.type,
          avatar: runtimeAvatarId.value,
          refaudio: offerRefAudio(),
          reftext: runtimeRefText.value
        })
      });
      const answer = (await response.json().catch(() => ({}))) as LiveTalkingOfferResponse;
      if (!response.ok || answer.code === -1 || !answer.sdp || !answer.type) {
        throw new Error(answer.msg || "LiveTalking 信令协商失败");
      }

      liveTalkingSessionId.value = String(answer.sessionid || "");
      await pc.setRemoteDescription({ type: answer.type, sdp: answer.sdp });
      liveTalkingStatus.value = "connected";
      unavailableUntil = 0;
      return true;
    } catch (error) {
      closePeerConnection("error");
      unavailableUntil = Date.now() + 15_000;
      liveTalkingError.value = error instanceof Error ? error.message : "LiveTalking 服务不可用";
      return false;
    } finally {
      connectingPromise = null;
    }
  })();

  return connectingPromise;
}

export function ensureLiveTalkingConnected(options: { force?: boolean } = {}) {
  return connectLiveTalking(Boolean(options.force));
}

export async function speakWithLiveTalking(text: string) {
  if (!text.trim()) return false;
  const connected = await ensureLiveTalkingConnected();
  if (!connected || !liveTalkingSessionId.value) return false;

  const ttsPayload: Record<string, string> = { voice: runtimeVoice.value };
  if (runtimeTtsMode.value === "cosyvoice" || runtimeTtsMode.value === "gpt-sovits") {
    ttsPayload.ref_file = runtimeRefAudio.value;
    ttsPayload.ref_text = runtimeRefText.value;
    ttsPayload.tts_mode = runtimeTtsMode.value;
  }

  try {
    liveTalkingStatus.value = "speaking";
    const response = await fetch(endpoint("/human"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        type: "echo",
        interrupt: true,
        sessionid: liveTalkingSessionId.value,
        tts: ttsPayload
      })
    });
    const result = (await response.json().catch(() => ({}))) as LiveTalkingJsonResponse;
    if (!response.ok || result.code === -1) throw new Error(result.msg || "数字人播报失败");
    return true;
  } catch (error) {
    liveTalkingStatus.value = "error";
    liveTalkingError.value = error instanceof Error ? error.message : "数字人播报失败";
    return false;
  }
}

export async function saveLiveTalkingPresetVoice(config: LiveTalkingRuntimeConfig) {
  const form = new FormData();
  form.append("avatar_id", config.avatarId);
  form.append("ref_text", config.refText);
  form.append("voice", config.voice);
  form.append("tts_mode", config.ttsMode);
  const response = await fetch(endpoint("/api/preset_voice"), {
    method: "POST",
    body: form
  });
  const result = (await response.json().catch(() => ({}))) as LiveTalkingJsonResponse;
  if (!response.ok || result.code === -1) {
    throw new Error(result.msg || "预设音色保存失败");
  }
}

export async function interruptLiveTalking() {
  if (!liveTalkingEnabled || !liveTalkingSessionId.value) return;
  try {
    await fetch(endpoint("/interrupt_talk"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessionid: liveTalkingSessionId.value })
    });
    if (liveTalkingStatus.value === "speaking") liveTalkingStatus.value = "connected";
  } catch {
    liveTalkingStatus.value = "error";
  }
}

export function disconnectLiveTalking() {
  connectingPromise = null;
  closePeerConnection();
}

applyLiveTalkingPreset(runtimeDefaults);
