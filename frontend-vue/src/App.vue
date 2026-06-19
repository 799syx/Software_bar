<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { storeToRefs } from "pinia";
import SiteNav from "./components/SiteNav.vue";
import LandingView from "./components/LandingView.vue";
import HomeView from "./components/HomeView.vue";
import GuideView from "./components/GuideView.vue";
import AdminView from "./components/AdminView.vue";
import { useScenicStore } from "./stores/useScenicStore";

type ViewName = "landing" | "home" | "guide" | "admin";

const view = ref<ViewName>(readView());
const scenicStore = useScenicStore();
const { persona, llmStatus, ttsStatus, asrStatus, capabilities, analytics, routeOptions, spots, suggestions, connected } = storeToRefs(scenicStore);

function readView(): ViewName {
  const hash = window.location.hash.replace("#", "").split("?")[0];
  if (hash === "home" || hash === "guide" || hash === "admin") return hash;
  return "landing";
}

function navigate(next: ViewName) {
  view.value = next;
  window.location.hash = next === "landing" ? "" : next;
}

function syncFromHash() {
  view.value = readView();
}

onMounted(() => {
  window.addEventListener("hashchange", syncFromHash);
  void scenicStore.loadData();
});

onUnmounted(() => {
  window.removeEventListener("hashchange", syncFromHash);
});
</script>

<template>
  <div class="app-shell" :class="`view-${view}`">
    <SiteNav
      :view="view"
      :persona="persona"
      :llm-status="llmStatus"
      :connected="connected"
      @navigate="navigate"
    />

    <Transition name="view-switch" mode="out-in">
      <div :key="view" class="view-frame">
        <LandingView v-if="view === 'landing'" @navigate="navigate" />
        <HomeView
          v-else-if="view === 'home'"
          :persona="persona"
          :llm-status="llmStatus"
          :capabilities="capabilities"
          :analytics="analytics"
          :route-options="routeOptions"
          :spots="spots"
          @navigate="navigate"
        />
        <GuideView
          v-else-if="view === 'guide'"
          :persona="persona"
          :llm-status="llmStatus"
          :tts-status="ttsStatus"
          :asr-status="asrStatus"
          :suggestions="suggestions"
          :route-options="routeOptions"
          :spots="spots"
        />
        <AdminView
          v-else
          :analytics="analytics"
          :llm-status="llmStatus"
          :capabilities="capabilities"
          :spots="spots"
          :persona="persona"
          @refresh="scenicStore.loadData"
        />
      </div>
    </Transition>
  </div>
</template>
