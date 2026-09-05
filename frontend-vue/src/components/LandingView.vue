<script setup lang="ts">
import { Bot, Map, Navigation2, Sparkles } from "lucide-vue-next";
import { useFallbackImage } from "../assets";

type ViewName = "landing" | "home" | "guide" | "admin";

const emit = defineEmits<{
  navigate: [view: ViewName];
}>();

const landingHeroImage = "/assets/scenic/landing-hero.png";
const landingSpotImage = "/assets/scenic/photos/lingshan-grand-buddha-card.png";
const landingSpotName = "灵山大佛";
const landingSpotDescription =
  "景区核心地标、祈福朝圣与佛教造像艺术展示，适合游客登顶抱佛脚、俯瞰太湖并了解佛教手印寓意。右手施无畏印，寓意除却众生痛苦；左手施与愿印，寓意赐予众生欢乐。216级登云道暗合108烦恼与108愿望。";
const landingSpotLocation =
  "祥符禅寺北侧，秦履峰南侧，矗立在景区最高处，是整个灵山胜境的核心地标，可俯瞰整个景区及太湖风光。";
const landingGuideStatus = "和尚 · 浏览器语音";
</script>

<template>
  <main class="landing-view">
    <section class="hero-section scenic-home-hero">
      <div class="hero-backdrop">
        <img :src="landingHeroImage" alt="灵山胜境" @error="useFallbackImage" />
      </div>
      <div class="hero-content">
        <div class="hero-copy">
          <p class="eyebrow"><Sparkles :size="17" /> 灵山胜境 AI 数字人导览</p>
          <h1>灵山胜境</h1>
          <p class="hero-text">
            以灵山大佛、九龙灌浴、灵山梵宫和五印坛城为核心，提供景点总览、路线入口和数字人欢迎讲解。
          </p>
          <div class="hero-actions">
            <button class="primary-action" type="button" @click="emit('navigate', 'home')">
              <Map :size="18" />
              景区首页
            </button>
            <button class="secondary-action" type="button" @click="emit('navigate', 'guide')">
              <Navigation2 :size="19" />
              进入智能导览
            </button>
            <button class="secondary-action" type="button" @click="emit('navigate', 'admin')">
              <Bot :size="18" />
              管理后台
            </button>
          </div>
        </div>

        <article class="hero-photo-card scenic-feature-card">
          <img :src="landingSpotImage" :alt="landingSpotName" @error="useFallbackImage" />
          <div class="photo-card-caption">
            <small>实景导览</small>
            <strong>{{ landingSpotName }}</strong>
            <span>{{ landingSpotDescription }}</span>
          </div>
          <div class="hero-spot-chip">
            <img :src="landingSpotImage" :alt="landingSpotName" @error="useFallbackImage" />
            <div>
              <small>{{ landingGuideStatus }}</small>
              <strong>{{ landingSpotLocation }}</strong>
            </div>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>
