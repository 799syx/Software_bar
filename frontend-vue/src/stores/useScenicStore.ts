import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { safeApiGet } from "../api";
import {
  fallbackAnalytics,
  fallbackAsrStatus,
  fallbackCapabilities,
  fallbackLlmStatus,
  fallbackPersona,
  fallbackRouteOptions,
  fallbackSpots,
  fallbackTtsStatus
} from "../fallback";
import type { AnalyticsOverview, AsrStatus, LlmStatus, Persona, RouteOptions, ScenicSpot, SystemCapabilities, TtsStatus } from "../types";

export const useScenicStore = defineStore("scenic", () => {
  const loading = ref(true);
  const persona = ref<Persona>(fallbackPersona);
  const llmStatus = ref<LlmStatus>(fallbackLlmStatus);
  const ttsStatus = ref<TtsStatus>(fallbackTtsStatus);
  const asrStatus = ref<AsrStatus>(fallbackAsrStatus);
  const capabilities = ref<SystemCapabilities>(fallbackCapabilities);
  const analytics = ref<AnalyticsOverview>(fallbackAnalytics);
  const routeOptions = ref<RouteOptions>(fallbackRouteOptions);
  const spots = ref<ScenicSpot[]>(fallbackSpots);
  const suggestions = ref<string[]>(["灵山大佛有什么特色？", "九龙灌浴什么时候表演？", "适合亲子游的路线怎么走？"]);

  const connected = computed(() => !loading.value && (llmStatus.value.available || analytics.value.spotCount > 0));

  async function loadData() {
    loading.value = true;
    const [spotData, nextPersona, nextLlm, nextTts, nextAsr, nextCapabilities, nextAnalytics, nextSuggestions, nextRouteOptions] = await Promise.all([
      safeApiGet<{ items: ScenicSpot[] }>("/api/spots", { items: fallbackSpots }),
      safeApiGet<Persona>("/api/persona", fallbackPersona),
      safeApiGet<LlmStatus>("/api/llm/status", fallbackLlmStatus),
      safeApiGet<TtsStatus>("/api/tts/status", fallbackTtsStatus),
      safeApiGet<AsrStatus>("/api/asr/status", fallbackAsrStatus),
      safeApiGet<SystemCapabilities>("/api/system/capabilities", fallbackCapabilities),
      Promise.resolve(fallbackAnalytics),
      safeApiGet<{ items: string[] }>("/api/chat/suggestions", { items: suggestions.value }),
      safeApiGet<RouteOptions>("/api/routes/options", fallbackRouteOptions)
    ]);

    spots.value = spotData.items.length ? spotData.items : fallbackSpots;
    persona.value = nextPersona;
    llmStatus.value = nextLlm;
    ttsStatus.value = nextTts;
    asrStatus.value = nextAsr;
    capabilities.value = nextCapabilities;
    analytics.value = nextAnalytics;
    suggestions.value = nextSuggestions.items.length ? nextSuggestions.items : suggestions.value;
    routeOptions.value = nextRouteOptions;
    loading.value = false;
  }

  return {
    loading,
    persona,
    llmStatus,
    ttsStatus,
    asrStatus,
    capabilities,
    analytics,
    routeOptions,
    spots,
    suggestions,
    connected,
    loadData
  };
});
