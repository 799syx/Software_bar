<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { Bot, Clock, MapPinned, Navigation2, Route, Sparkles } from "lucide-vue-next";
import { useFallbackImage } from "../assets";
import { imageForSpot } from "../photos";
import type { AnalyticsOverview, LlmStatus, Persona, RouteOptions, ScenicSpot, SystemCapabilities } from "../types";

type ViewName = "landing" | "home" | "guide" | "admin";

const props = defineProps<{
  persona: Persona;
  llmStatus: LlmStatus;
  capabilities: SystemCapabilities;
  analytics: AnalyticsOverview;
  routeOptions: RouteOptions;
  spots: ScenicSpot[];
}>();

const emit = defineEmits<{
  navigate: [view: ViewName];
}>();

const homeRoot = ref<HTMLElement | null>(null);
let revealObserver: IntersectionObserver | null = null;

const activeSpots = computed(() => props.spots.filter((spot) => spot.status !== "inactive"));
const coreSpots = computed(() => activeSpots.value.filter((spot) => spot.mapZone !== "nianhua").slice(0, 6));
const nianhuaSpots = computed(() => activeSpots.value.filter((spot) => spot.mapZone === "nianhua").slice(0, 4));
const coreSpotCards = computed(() => {
  const usedKeys = new Set<string>();
  return coreSpots.value.map((spot) => ({ spot, image: imageForSpot(spot, usedKeys) }));
});
const nianhuaSpotCards = computed(() => {
  const usedKeys = new Set<string>();
  return nianhuaSpots.value.map((spot) => ({ spot, image: imageForSpot(spot, usedKeys) }));
});
const routePreferencePreview = computed(() => props.routeOptions.preferences.slice(0, 5));
const heroSpot = computed(() => coreSpotCards.value[0] || null);
const satisfactionScore = computed(() => {
  const feedbackScore = Number(props.analytics.averageSatisfaction || 0);
  const behaviorScore = Number(props.analytics.behaviorBaseline?.averageSatisfaction || 0);
  return feedbackScore > 0 ? feedbackScore : behaviorScore;
});
const satisfactionDetail = computed(() => {
  if (Number(props.analytics.feedbackCount || 0) > 0) return `${props.analytics.feedbackCount} 条游客反馈`;
  if (satisfactionScore.value > 0) return "灵山游客行为评分";
  return "暂无评分样本";
});
const homeStats = computed(() => [
  { label: "开放景点", value: `${props.analytics.spotCount}`, detail: "后台当前启用点位" },
  { label: "知识条目", value: `${props.analytics.knowledgeCount}`, detail: "后台启用知识文档" },
  {
    label: "满意评分",
    value: satisfactionScore.value > 0 ? satisfactionScore.value.toFixed(1) : "暂无",
    detail: satisfactionDetail.value
  }
]);
const routeSlices = computed(() => {
  const names = activeSpots.value.map((spot) => spot.name);
  const has = (keyword: string) => names.find((name) => name.includes(keyword));
  return [
    {
      title: "礼佛文化线",
      duration: props.routeOptions.durations.includes(180) ? "180 分钟" : `${props.routeOptions.durations[0] || 120} 分钟`,
      focus: [has("大佛"), has("祥符"), has("梵宫"), has("坛城")].filter(Boolean).join("、") || "灵山核心礼佛动线",
      detail: "从山门、禅寺到大佛与梵宫，适合首次到访和文化讲解演示。"
    },
    {
      title: "亲子演艺线",
      duration: props.routeOptions.durations.includes(120) ? "120 分钟" : `${props.routeOptions.durations[0] || 90} 分钟`,
      focus: [has("九龙"), has("梵宫"), has("弥勒")].filter(Boolean).join("、") || "演出与互动景观",
      detail: "围绕准点演出和短停留景点组织，减少跨区折返。"
    },
    {
      title: "拈花湾休闲线",
      duration: props.routeOptions.durations.includes(300) ? "300 分钟" : `${props.routeOptions.durations.at(-1) || 180} 分钟`,
      focus: [has("拈花广场"), has("香月花街"), has("梵天花海"), has("拈花堂")].filter(Boolean).join("、") || "拈花湾小镇慢游",
      detail: "把餐饮、街区、花海与夜游节点单独组织，避免与核心区混成步行动线。"
    }
  ];
});

onMounted(() => {
  const revealTargets = Array.from(homeRoot.value?.querySelectorAll<HTMLElement>("[data-reveal-scope]") || []);
  if (!revealTargets.length) return;
  if (!("IntersectionObserver" in window)) {
    revealTargets.forEach((target) => target.classList.add("is-visible"));
    return;
  }

  revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        revealObserver?.unobserve(entry.target);
      });
    },
    { rootMargin: "0px 0px -8% 0px", threshold: 0.16 }
  );
  revealTargets.forEach((target) => revealObserver?.observe(target));
});

onUnmounted(() => {
  revealObserver?.disconnect();
  revealObserver = null;
});
</script>

<template>
  <main ref="homeRoot" class="home-view">
    <section class="home-overview-panel" aria-label="景区概览板块">
      <div class="home-overview-inner">
        <section class="home-story-hero" data-reveal-scope>
          <div class="home-hero-copy">
            <p class="section-kicker home-reveal-title"><MapPinned :size="16" /> 灵山胜境智能导览</p>
            <h1 class="home-reveal-title">先看懂景区，再进入现场导览。</h1>
            <p class="home-reveal-lead">
              首页用真实点位、主题路线和景点图像建立游览判断，地图页负责语音问答、路线生成和数字人讲解。
            </p>
            <div class="home-hero-actions home-reveal-card" style="--reveal-delay: 240ms">
              <button class="primary-action" type="button" @click="emit('navigate', 'guide')">
                <Navigation2 :size="18" />
                打开智能导览
              </button>
              <button class="secondary-action" type="button" @click="emit('navigate', 'admin')">
                <Sparkles :size="18" />
                查看运营后台
              </button>
            </div>
            <div class="home-stat-row">
              <article v-for="(item, index) in homeStats" :key="item.label" class="home-reveal-card" :style="{ '--reveal-delay': `${330 + index * 90}ms` }">
                <strong>{{ item.value }}</strong>
                <span>{{ item.label }}</span>
                <small>{{ item.detail }}</small>
              </article>
            </div>
          </div>

          <figure class="home-hero-photo home-reveal-card" style="--reveal-delay: 690ms">
            <img src="/assets/scenic/landing-hero.png" alt="灵山胜境核心景区航拍视角" @error="useFallbackImage" />
            <figcaption v-if="heroSpot">
              <img :src="heroSpot.image" :alt="heroSpot.spot.name" @error="useFallbackImage" />
              <span>
                <strong>{{ heroSpot.spot.name }}</strong>
                <small>{{ heroSpot.spot.location }}</small>
              </span>
            </figcaption>
          </figure>
        </section>

        <section class="home-route-slices" data-reveal-scope>
          <div class="home-section-head home-nowrap-head">
            <p class="section-kicker home-reveal-title"><Route :size="16" /> 推荐游览主题</p>
            <h2 class="home-reveal-title home-nowrap-title">把景区拆成可讲解、可执行的路线切片。</h2>
            <p class="section-lead home-reveal-lead">
              帮助游客先理解“为什么这样走”
            </p>
          </div>
          <div class="route-slice-grid">
            <article v-for="(item, index) in routeSlices" :key="item.title" class="route-slice-card home-reveal-card" :style="{ '--reveal-delay': `${240 + index * 90}ms` }">
              <span>{{ item.duration }}</span>
              <h3>{{ item.title }}</h3>
              <strong>{{ item.focus }}</strong>
              <p>{{ item.detail }}</p>
              <button class="ghost-action compact" type="button" @click="emit('navigate', 'guide')">
                <Navigation2 :size="16" />
                去生成路线
              </button>
            </article>
          </div>
        </section>

        <section class="photo-gallery compact-gallery home-story-gallery" data-reveal-scope>
          <div class="gallery-header">
            <div>
              <p class="section-kicker home-reveal-title"><Sparkles :size="16" /> 核心景点</p>
              <h2 class="home-reveal-title">灵山胜境核心游览节点</h2>
            </div>
            <button class="secondary-action compact home-reveal-card" style="--reveal-delay: 240ms" type="button" @click="emit('navigate', 'guide')">
              <Navigation2 :size="17" />
              打开导览地图
            </button>
          </div>
          <div class="spot-grid story-spot-grid">
            <article v-for="({ spot, image }, index) in coreSpotCards" :key="spot.id" class="spot-card home-reveal-card" :style="{ '--reveal-delay': `${240 + index * 90}ms` }">
              <img :src="image" :alt="spot.name" @error="useFallbackImage" />
              <div>
                <h3>{{ spot.name }}</h3>
                <p>{{ spot.description }}</p>
                <span>{{ spot.location }}</span>
              </div>
            </article>
          </div>
        </section>

        <section v-if="nianhuaSpotCards.length" class="content-section nianhua-story-section" data-reveal-scope>
          <div class="home-section-head home-nowrap-head">
            <p class="section-kicker home-reveal-title"><MapPinned :size="16" /> 拈花湾分区</p>
            <h2 class="home-reveal-title home-nowrap-title">拈花湾作为休闲小镇分区单独组织路线。</h2>
            <p class="section-lead home-reveal-lead">街区、广场、花海和夜游点位保持独立，不与灵山核心礼佛线混成一条步行动线。</p>
          </div>
          <div class="home-zone-strip">
            <article v-for="({ spot, image }, index) in nianhuaSpotCards" :key="spot.id" class="home-reveal-card" :style="{ '--reveal-delay': `${240 + index * 90}ms` }">
              <img :src="image" :alt="spot.name" @error="useFallbackImage" />
              <strong>{{ spot.name }}</strong>
              <span>{{ spot.duration }} 分钟 · {{ spot.tags.slice(0, 2).join("、") }}</span>
            </article>
          </div>
        </section>

        <section class="content-section two-column home-service-section" data-reveal-scope>
          <div>
            <p class="section-kicker home-reveal-title"><Bot :size="16" /> 导览能力</p>
            <h2 class="home-reveal-title">游客端看路线，后台看运行，数字人负责把知识说清楚。</h2>
          </div>
          <div class="service-grid">
            <article class="service-card home-reveal-card" style="--reveal-delay: 240ms">
              <Route :size="22" />
              <h3>个性化路线</h3>
              <p>{{ routePreferencePreview.join("、") }} 等偏好可在智能导览中生成路线。</p>
            </article>
            <article class="service-card home-reveal-card" style="--reveal-delay: 330ms">
              <Bot :size="22" />
              <h3>数字人讲解</h3>
              <p>{{ persona.style }}，支持问答、播报和口型表情状态。</p>
            </article>
            <article class="service-card home-reveal-card" style="--reveal-delay: 420ms">
              <Clock :size="22" />
              <h3>游览节奏</h3>
              <p>按 60、120、180、300 分钟组织路线，避免跨区混成不合理步行动线。</p>
            </article>
            <article class="service-card home-reveal-card" style="--reveal-delay: 510ms">
              <Navigation2 :size="22" />
              <h3>现场导航</h3>
              <p>灵山核心区和拈花湾分区展示，地图点位使用人工校准坐标。</p>
            </article>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>
