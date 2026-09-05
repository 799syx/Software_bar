import type { Persona } from "../types";

export type LiveTalkingPresetKey = "male" | "female" | "custom";

export type LiveTalkingPresetConfig = {
  key: LiveTalkingPresetKey;
  label: string;
  avatarId: string;
  refAudio: string;
  refText: string;
  voice: string;
  voiceHint: string;
  ttsMode: string;
  summary: string;
};

export const DEFAULT_REF_TEXT =
  "阿弥陀佛，施主您好。欢迎来到灵山胜景。请随我漫步胜景，静听这千年的钟声，享受美景吧！";

export const AVATAR_PRESETS: Record<Exclude<LiveTalkingPresetKey, "custom">, LiveTalkingPresetConfig> = {
  male: {
    key: "male",
    label: "男性僧人",
    avatarId: "test1",
    refAudio: "data/ref_audio/test1.wav",
    refText: DEFAULT_REF_TEXT,
    voice: "zh-CN-YunyangNeural",
    voiceHint: "慢速 · 低沉 · 稳重",
    ttsMode: "edgetts",
    summary: "Avatar: test1 / Yunyang / 慢速 · 低沉 · 稳重"
  },
  female: {
    key: "female",
    label: "女性僧人",
    avatarId: "test2",
    refAudio: "data/ref_audio/test2_1.wav",
    refText: DEFAULT_REF_TEXT,
    voice: "zh-CN-XiaoyiNeural",
    voiceHint: "舒缓 · 柔和 · 平稳",
    ttsMode: "edgetts",
    summary: "Avatar: test2 / Xiaoyi / 舒缓 · 柔和 · 平稳"
  }
};

export type LiveTalkingRuntimeConfig = {
  presetKey: LiveTalkingPresetKey;
  avatarId: string;
  refAudio: string;
  refText: string;
  voice: string;
  ttsMode: string;
};

function envOr(value: unknown, fallback: string) {
  const text = String(value ?? "").trim();
  return text || fallback;
}

export function defaultRuntimeFromEnv(): LiveTalkingRuntimeConfig {
  return {
    presetKey: envOr(import.meta.env.VITE_LIVETALKING_AVATAR, "test1") === "test2" ? "female" : "male",
    avatarId: envOr(import.meta.env.VITE_LIVETALKING_AVATAR, AVATAR_PRESETS.male.avatarId),
    refAudio: envOr(import.meta.env.VITE_LIVETALKING_REF_AUDIO, AVATAR_PRESETS.male.refAudio),
    refText: envOr(import.meta.env.VITE_LIVETALKING_REF_TEXT, DEFAULT_REF_TEXT),
    voice: envOr(import.meta.env.VITE_LIVETALKING_VOICE, AVATAR_PRESETS.male.voice),
    ttsMode: envOr(import.meta.env.VITE_LIVETALKING_TTS_MODE, "edgetts")
  };
}

export function presetConfigFromKey(key: LiveTalkingPresetKey, overrides: Partial<LiveTalkingRuntimeConfig> = {}): LiveTalkingRuntimeConfig {
  if (key === "custom") {
    const defaults = defaultRuntimeFromEnv();
    return {
      presetKey: "custom",
      avatarId: overrides.avatarId || defaults.avatarId,
      refAudio: overrides.refAudio || defaults.refAudio,
      refText: overrides.refText || defaults.refText,
      voice: overrides.voice || defaults.voice,
      ttsMode: overrides.ttsMode || defaults.ttsMode
    };
  }
  const preset = AVATAR_PRESETS[key];
  return {
    ...overrides,
    presetKey: key,
    avatarId: overrides.avatarId || preset.avatarId,
    refAudio: overrides.refAudio || preset.refAudio,
    refText: overrides.refText || preset.refText,
    voice: overrides.voice || preset.voice,
    ttsMode: overrides.ttsMode || preset.ttsMode
  };
}

export function resolvePresetFromPersona(persona: Persona): LiveTalkingRuntimeConfig {
  const key = (persona.avatarPresetKey || "male") as LiveTalkingPresetKey;
  if (key === "male" || key === "female") {
    const preset = AVATAR_PRESETS[key];
    return {
      presetKey: key,
      avatarId: persona.avatarId || preset.avatarId,
      refAudio: persona.refAudio || preset.refAudio,
      refText: persona.refText || persona.expressionProfile || preset.refText,
      voice: persona.avatarVoice || preset.voice,
      ttsMode: persona.ttsMode || preset.ttsMode
    };
  }
  return {
    presetKey: "custom",
    avatarId: persona.avatarId || defaultRuntimeFromEnv().avatarId,
    refAudio: persona.refAudio || defaultRuntimeFromEnv().refAudio,
    refText: persona.refText || persona.expressionProfile || DEFAULT_REF_TEXT,
    voice: persona.avatarVoice || defaultRuntimeFromEnv().voice,
    ttsMode: persona.ttsMode || defaultRuntimeFromEnv().ttsMode
  };
}

export function buildPresetSummary(config: LiveTalkingRuntimeConfig) {
  if (config.presetKey === "male") return AVATAR_PRESETS.male.summary;
  if (config.presetKey === "female") return AVATAR_PRESETS.female.summary;
  return `Avatar: ${config.avatarId} / ${config.voice} / 自定义`;
}

export function presetLabel(config: LiveTalkingRuntimeConfig) {
  if (config.presetKey === "male") return AVATAR_PRESETS.male.label;
  if (config.presetKey === "female") return AVATAR_PRESETS.female.label;
  return "自定义生成";
}

export function applyPresetToPersona(persona: Persona, config: LiveTalkingRuntimeConfig): Persona {
  const next = { ...persona };
  next.avatarPresetKey = config.presetKey;
  next.avatarId = config.avatarId;
  next.refAudio = config.refAudio;
  next.refText = config.refText;
  next.avatarVoice = config.voice;
  next.ttsMode = config.ttsMode;
  next.style = presetLabel(config);
  next.costume = buildPresetSummary(config);
  next.voice = `${config.ttsMode} / ${config.voice}`;
  next.expressionProfile = config.refText;
  return next;
}

export function selectablePresetCards() {
  return [
    AVATAR_PRESETS.male,
    AVATAR_PRESETS.female,
    {
      key: "custom" as const,
      label: "自定义生成",
      avatarId: "",
      refAudio: "",
      refText: DEFAULT_REF_TEXT,
      voice: "zh-CN-YunyangNeural",
      voiceHint: "可输入 avatar 与参考音频",
      ttsMode: "edgetts",
      summary: "使用 avatar.html 训练新形象，或手动填写参数"
    }
  ];
}
