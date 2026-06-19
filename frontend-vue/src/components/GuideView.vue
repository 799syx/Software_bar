<script setup lang="ts">
import MapGuideExperience from "./MapGuideExperience.vue";
import type { AsrStatus, LlmStatus, Persona, RouteOptions, ScenicSpot, TtsStatus } from "../types";

defineProps<{
  persona: Persona;
  llmStatus: LlmStatus;
  ttsStatus: TtsStatus;
  asrStatus: AsrStatus;
  suggestions: string[];
  routeOptions: RouteOptions;
  spots: ScenicSpot[];
}>();
</script>

<template>
  <MapGuideExperience
    :persona="persona"
    :llm-status="llmStatus"
    :tts-status="ttsStatus"
    :asr-status="asrStatus"
    :suggestions="suggestions"
    :route-options="routeOptions"
    :spots="spots"
    compact
  />
</template>
