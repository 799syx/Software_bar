<script setup lang="ts">
import { toRefs } from "vue";
import { useMapGuideExperience, type MapGuideExperienceProps } from "./guide/useMapGuideExperience";

const props = defineProps<MapGuideExperienceProps>();
const { persona, llmStatus, ttsStatus, asrStatus, suggestions, routeOptions, spots, compact } = toRefs(props);
const guideExperience = useMapGuideExperience(props);

const {
  activeSpots, activeZone, ALLOWED_IMAGE_TYPES, AMAP_FIXED_GCJ02_COORDS, AMAP_KEY, AMAP_POI_FIRST_SPOT_NAMES,
  AMAP_POI_KEYWORD_ALIASES, AMAP_POI_NAME_ALIASES, AMAP_SCRIPT_ID, AMAP_SECURITY_CODE, AMAP_ZONE_VIEW, amapContainer,
  amapFixedPositionForSpot, amapLoadFailed, amapMap, amapPlaceSearch, amapPoiKeywords, amapPoiLookupFailed,
  amapPoiMatchNames, amapPoiPositionFromResult, amapPoiPositions, amapPositionForSpot, amapScriptPromise, amapZoneView,
  apiGet, apiPost, applyLocationAnchor, ArrowLeft, askCurrentSpot, askImageExplanation,
  asking, asrBusy, asrChunks, asrRecording, asrStream, assistantCollapsed,
  audioRef, autoSpeak, backToMap, blobToDataUrl, buildRoute, buildSpotIntro,
  ChevronDown, clearSelectedImage, Clock, computed, coordinateBounds, createAmapCurrentLocationContent,
  createAmapSpotContent, currentLocation, currentLocationPoint, DEMO_LOCATION_POINT, destroyAmapMap, DigitalHumanPanel,
  ensureAmapPoiPositions, error, escapeHtml, estimatedTime, expression, extractLocationCode,
  fileToDataUrl, fileToVisionDataUrl, focusAmapZone, formatLatency, handleImageSelect, hasVerifiedAmapPosition,
  imageAnswer, imageAnswerLatencyMs, imageAnswerRefs, imageFileName, imageForSpot, imagePreview,
  imageQuestion, ImageUp, lastAnswerLatencyMs, lastAnswerRefs, loadAmapPlaceSearch, loadAmapScript,
  loadImage, localIntro, locateCurrentPosition, LocateFixed, locationBusy, locationCode,
  locationCodeFromUrl, locationText, MAP_FALLBACK_SLOTS, MAP_SPOT_LAYOUTS, mapLabelLines, mapLabelMetrics,
  mapLayoutForSpot, MapPin, mapPointForCoordinate, mapPointForSpot, mapSpotPoints, MAX_IMAGE_BYTES,
  mediaRecorder, MessageCircle, Mic, MicOff, mode, MoreHorizontal,
  mouthShape, Navigation2, nextTick, normalizedMapZone, normalizeSpotName, notice,
  onMounted, onUnmounted, openSpotDetail, question, quickQuestions, ref,
  relatedQuestions, renderAmapOverlays, resetSpeech, resolveLocationCode, Route, routeBusy,
  routeDuration, routeMapPoints, routePolyline, routePreference, routeResult, routeSpotIds,
  routeSpotOrder, searchAmapPoiPosition, selectedAnchorCode, selectedBasemap, selectedImage, selectedSpot,
  selectedSpotId, selectedSpotIndex, Send, shortIntro, shouldPreferAmapPoi, sourceTypeLabel,
  Sparkles, speakText, speakWithBrowser, speech, speechInputSupported, speechProgress,
  speechTimer, spokenText, stage, startServerAsr, stopServerAsr, stopSpeaking,
  switchBasemap, switchMapZone, switchToSpotZone, syncAmapMap, toggleVoiceInput, uniqueTexts,
  updateSpeechProgress, useAmap, useFallbackImage, useSelectedAnchor, useSpeechRecognition, visibleLocationAnchors,
  visibleSpots, VISION_IMAGE_MAX_EDGE, VISION_IMAGE_QUALITY, visionBusy, voiceButtonText, watch,
  X
} = guideExperience;
</script>

<template>
  <main class="map-experience" :class="[{ compact }, `mode-${mode}`]">
    <section v-if="mode === 'map'" class="map-workbench home-map-screen">
      <div class="local-map-panel">
        <div class="map-toolbar">
          <div>
            <p class="section-kicker"><Navigation2 :size="16" /> 灵山胜境 3D 地图</p>
            <strong>{{ routeResult ? routeResult.title : "点击景点进入详情讲解" }}</strong>
            <span><Clock :size="14" /> 推荐动线约 {{ estimatedTime }} 分钟</span>
          </div>
          <div class="map-toolbar-actions">
            <div class="zone-selectors" aria-label="地图分区">
              <button type="button" :class="{ active: activeZone === 'lingshan' }" @click="switchMapZone('lingshan')">灵山</button>
              <button type="button" :class="{ active: activeZone === 'nianhua' }" @click="switchMapZone('nianhua')">拈花湾</button>
            </div>
            <div class="basemap-selectors" aria-label="底图模式">
              <button type="button" :class="{ active: selectedBasemap === 'custom' }" @click="switchBasemap('custom')">景区图</button>
              <button type="button" :class="{ active: selectedBasemap === 'amap' }" @click="switchBasemap('amap')">高德</button>
            </div>
            <div class="route-selectors">
              <select v-model.number="routeDuration" aria-label="游览时长">
                <option v-for="duration in routeOptions.durations" :key="duration" :value="duration">{{ duration }} 分钟</option>
              </select>
              <select v-model="routePreference" aria-label="兴趣偏好">
                <option v-for="preference in routeOptions.preferences" :key="preference" :value="preference">{{ preference }}</option>
              </select>
            </div>
            <button class="primary-action compact" type="button" :disabled="routeBusy" @click="buildRoute">
              <Route :size="17" />
              {{ routeBusy ? "生成中" : "路线" }}
            </button>
          </div>
        </div>

        <div class="location-assist-strip" :class="`quality-${currentLocation.confidence}`">
          <div class="location-status-copy">
            <strong><LocateFixed :size="15" /> 现场定位</strong>
            <span>{{ locationText }}</span>
          </div>
          <button class="secondary-action compact" type="button" :disabled="locationBusy" @click="locateCurrentPosition">
            <LocateFixed :size="16" />
            {{ locationBusy ? "定位中" : "GPS 定位" }}
          </button>
          <select v-model="selectedAnchorCode" aria-label="选择现场校准点" @change="useSelectedAnchor">
            <option value="">手动选择点位</option>
            <option v-for="spot in visibleLocationAnchors" :key="spot.id" :value="String(spot.locationCode || spot.id)">
              {{ spot.name }} · {{ spot.locationCode || spot.id }}
            </option>
          </select>
          <form class="location-code-field" @submit.prevent="resolveLocationCode()">
            <input v-model="locationCode" type="text" maxlength="80" placeholder="输入点位码或扫码链接，如 LS-002" />
            <button class="primary-action compact" type="submit" :disabled="locationBusy">
              校准
            </button>
          </form>
        </div>

        <div class="local-map-canvas" :class="{ 'with-amap': useAmap, 'with-guide-image': !useAmap }">
          <div v-if="useAmap" ref="amapContainer" class="real-amap-canvas" role="img" aria-label="高德地图底图上的灵山胜境景点"></div>
          <svg v-else class="guide-map-svg" viewBox="0 0 1334 1179" role="img" aria-label="灵山胜境景区导览图">
            <!-- The basemap is a scenic illustration supplied for the demo guide experience. -->
            <defs>
              <linearGradient id="mapLakeGradient" x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stop-color="#a9dce2" />
                <stop offset="48%" stop-color="#c6e8ea" />
                <stop offset="100%" stop-color="#e9f5ee" />
              </linearGradient>
              <linearGradient id="mapLandGradient" x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stop-color="#f9e4b7" />
                <stop offset="44%" stop-color="#dceacb" />
                <stop offset="100%" stop-color="#b8d7bd" />
              </linearGradient>
              <linearGradient id="mapSideGradient" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="#91b97f" />
                <stop offset="100%" stop-color="#4e7d63" />
              </linearGradient>
              <linearGradient id="mapRoadGradient" x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stop-color="#fff4ce" />
                <stop offset="100%" stop-color="#ca9c5e" />
              </linearGradient>
              <filter id="mapGlow" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation="5" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <filter id="mapShadow" x="-20%" y="-20%" width="150%" height="150%">
                <feDropShadow dx="0" dy="16" stdDeviation="14" flood-color="#163328" flood-opacity="0.2" />
              </filter>
            </defs>

            <image class="guide-map-basemap" href="/assets/scenic/guide-map.png" x="0" y="0" width="1334" height="1179" preserveAspectRatio="xMidYMid meet" />
            <ellipse cx="508" cy="566" rx="438" ry="46" class="map-base-shadow" />
            <path class="map-land-side" d="M64 106 L924 76 Q958 278 896 500 Q536 602 148 526 Q62 330 64 106 Z" />
            <path class="map-land-top" d="M64 78 L924 48 Q958 250 896 472 Q536 574 148 498 Q62 302 64 78 Z" />
            <path class="map-lake" d="M112 382 C212 342 292 426 420 394 C556 360 616 408 764 316 C842 266 914 290 946 246 L918 472 C734 524 594 568 390 540 C260 520 178 504 104 466 Z" />
            <path class="map-lake-shine" d="M276 424 C376 394 464 440 548 408 C620 382 676 366 748 334" />
            <path class="map-ridge ridge-a" d="M104 228 C192 120 316 148 398 78 C500 170 626 96 734 142 C810 176 858 218 914 168 L934 64 L66 96 Z" />
            <path class="map-ridge ridge-b" d="M128 500 C198 386 302 390 392 314 C492 228 586 250 686 166 C764 256 850 248 904 358 C790 424 666 498 502 532 C346 564 218 548 128 500 Z" />
            <g class="map-building-layer" aria-hidden="true">
              <path class="map-building tower" d="M700 154 l34 -16 l34 16 v58 l-34 18 l-34 -18 Z" />
              <path class="map-building palace" d="M480 220 l86 -40 l86 40 v54 l-86 42 l-86 -42 Z" />
              <path class="map-building temple" d="M262 354 l66 -32 l66 32 v48 l-66 30 l-66 -30 Z" />
              <path class="map-building street" d="M702 410 l88 -36 l82 34 v42 l-84 42 l-86 -40 Z" />
              <circle class="map-building buddha" cx="594" cy="148" r="34" />
            </g>
            <path d="M86 516 C222 438 354 438 478 366 C610 288 724 292 900 182" class="local-road road-shadow" />
            <path d="M86 516 C222 438 354 438 478 366 C610 288 724 292 900 182" class="local-road main" />
            <path d="M168 384 C286 318 352 314 466 256 C584 194 694 188 842 128" class="local-road branch" />
            <path d="M244 520 C312 420 374 374 462 312 C548 252 616 220 706 132" class="local-road branch thin" />
            <polyline v-if="routeResult && routeMapPoints.length > 1" :points="routePolyline" class="local-route-shadow" />
            <polyline v-if="routeResult && routeMapPoints.length > 1" :points="routePolyline" class="local-route-line" />

            <g
              v-for="(spot, index) in mapSpotPoints"
              :key="spot.id"
              :class="['local-spot-marker', { selected: selectedSpotId === spot.id, routed: spot.inRoute, dimmed: routeResult && !spot.inRoute }]"
              :transform="`translate(${spot.x} ${spot.y})`"
              :aria-label="spot.name"
              role="button"
              tabindex="0"
              @click="openSpotDetail(spot.id)"
              @keyup.enter="openSpotDetail(spot.id)"
            >
              <title>{{ spot.name }}</title>
              <circle class="guide-map-hotspot" r="34" />
              <line class="local-spot-label-line" x1="0" y1="0" :x2="spot.labelLineX" :y2="spot.labelLineY" />
              <ellipse class="marker-shadow" cx="7" cy="26" rx="28" ry="11" />
              <path class="marker-side" d="M-18 0 L0 18 L18 0 L18 18 L0 36 L-18 18 Z" />
              <circle class="marker-pulse" r="28" />
              <circle class="marker-top" r="19" />
              <text v-if="spot.pinLabel" class="local-pin-number" text-anchor="middle" dominant-baseline="central">
                {{ spot.pinLabel }}
              </text>
              <rect
                class="local-spot-label-bg"
                :x="spot.labelBoxX"
                :y="spot.labelBoxY"
                :width="spot.labelWidth"
                :height="spot.labelHeight"
                rx="8"
              />
              <text class="local-spot-label" :x="spot.labelX" :y="spot.labelY" :text-anchor="spot.labelAnchor">
                <tspan
                  v-for="(line, lineIndex) in spot.labelLines"
                  :key="`${spot.id}-${lineIndex}`"
                  :x="spot.labelX"
                  :dy="lineIndex === 0 ? 0 : 17"
                >
                  {{ line }}
                </tspan>
              </text>
            </g>

            <g class="local-current-location" :transform="`translate(${currentLocationPoint.x} ${currentLocationPoint.y})`">
              <circle r="22" />
              <circle r="7" />
              <text x="26" y="6">当前位置</text>
            </g>
          </svg>
        </div>
      </div>

      <aside class="map-guide-rail assistant-rail">
        <section class="side-assistant-panel" :class="{ collapsed: assistantCollapsed }">
          <header class="assistant-panel-header">
            <div>
              <p class="section-kicker"><Sparkles :size="15" /> 侧边助手</p>
              <h2>{{ persona.name }}导览</h2>
              <span>{{ stage === "speaking" ? "正在讲解" : stage === "thinking" ? "生成讲解中" : stage === "listening" ? "正在听" : "待命" }} · {{ visibleSpots.length }} 个景点</span>
            </div>
            <div class="assistant-header-actions">
              <button class="ghost-action compact icon-only" type="button" :aria-label="assistantCollapsed ? '展开助手' : '收起助手'" @click="assistantCollapsed = !assistantCollapsed">
                <ChevronDown :size="16" />
              </button>
              <button class="ghost-action compact icon-only" type="button" aria-label="更多助手信息" @click="notice = locationText">
                <MoreHorizontal :size="16" />
              </button>
            </div>
          </header>

          <div v-if="!assistantCollapsed" class="assistant-panel-body">
            <div class="assistant-avatar-slot">
              <DigitalHumanPanel
                :persona="persona"
                :llm-status="llmStatus"
                :tts-status="ttsStatus"
                :stage="stage"
                :expression="expression"
                :mouth-shape="mouthShape"
                :spoken-text="spokenText || shortIntro"
                :speech-progress="speechProgress"
                :auto-speak="autoSpeak"
                :speech-supported="speechInputSupported"
                @toggle-auto-speak="(value) => (autoSpeak = value)"
                @speak-greeting="speakText(localIntro)"
                @stop-speaking="stopSpeaking"
              />
            </div>
          </div>

          <footer v-if="!assistantCollapsed" class="assistant-panel-footer">
            <form class="assistant-input-bar" @submit.prevent="askCurrentSpot()">
              <MessageCircle :size="17" />
              <input v-model="question" type="text" maxlength="500" placeholder="问当前景点或路线建议" />
              <button
                class="voice-button compact assistant-voice-button"
                type="button"
                :class="{ active: speech.listening.value || asrRecording }"
                :disabled="asking || asrBusy"
                @click="toggleVoiceInput"
              >
                <MicOff v-if="speech.listening.value || asrRecording" :size="16" />
                <Mic v-else :size="16" />
                {{ voiceButtonText }}
              </button>
              <button class="primary-action compact icon-only" type="submit" :disabled="!question.trim() || asking" aria-label="发送问题">
                <Send :size="16" />
              </button>
            </form>
          </footer>
        </section>
      </aside>
    </section>

    <section v-else class="spot-detail-screen">
      <article class="spot-detail-panel">
        <header class="spot-detail-header">
          <button class="ghost-action compact" type="button" @click="backToMap">
            <ArrowLeft :size="17" />
            返回地图
          </button>
          <span>{{ selectedSpotIndex + 1 }}/{{ visibleSpots.length }}</span>
        </header>

        <div class="spot-detail-body">
          <figure class="spot-detail-photo">
            <img :src="selectedImage" :alt="selectedSpot?.name || '景点图片'" @error="useFallbackImage" />
            <figcaption>{{ selectedSpot?.location || "景区点位" }}</figcaption>
          </figure>

          <section class="spot-detail-copy">
            <p class="section-kicker"><MapPin :size="15" /> 景点介绍</p>
            <h1>{{ selectedSpot?.name || "请选择景点" }}</h1>
            <p>{{ selectedSpot?.description || "点击地图上的景点后，这里会显示图片、位置和游览建议。" }}</p>
            <p v-if="selectedSpot?.story" class="spot-story">{{ selectedSpot.story }}</p>

            <div class="spot-meta-row">
              <span><Clock :size="14" /> {{ selectedSpot?.duration || 0 }} 分钟</span>
              <span>{{ selectedSpot?.openTime || "以景区公告为准" }}</span>
            </div>
            <div class="spot-tags">
              <span v-for="tag in selectedSpot?.tags || []" :key="tag">{{ tag }}</span>
            </div>
          </section>
        </div>

        <form class="spot-question-box detail-question-box" @submit.prevent="askCurrentSpot()">
          <div class="quick-question-row">
            <button v-for="item in quickQuestions" :key="item" type="button" :disabled="asking" @click="askCurrentSpot(item)">
              {{ item }}
            </button>
          </div>
          <div class="spot-question-input">
            <MessageCircle :size="18" />
            <input v-model="question" type="text" maxlength="500" placeholder="继续问当前景点，比如适合几点去、怎么拍照、下一站去哪" />
            <button
              class="voice-button compact"
              type="button"
              :class="{ active: speech.listening.value || asrRecording }"
              :disabled="asking || asrBusy"
              @click="toggleVoiceInput"
            >
              <MicOff v-if="speech.listening.value || asrRecording" :size="16" />
              <Mic v-else :size="16" />
              {{ voiceButtonText }}
            </button>
            <button class="primary-action compact" type="submit" :disabled="!question.trim() || asking">
              <Send :size="16" />
              {{ asking ? "提问中" : "问 AI" }}
            </button>
          </div>
          <div class="vision-question-box">
            <label class="image-drop compact-image-drop">
              <img v-if="imagePreview" :src="imagePreview" alt="待讲解照片预览" />
              <span v-else>
                <ImageUp :size="24" />
                上传照片讲解
              </span>
              <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" @change="handleImageSelect" />
            </label>
            <div class="vision-question-copy">
              <div class="vision-question-row">
                <input v-model="imageQuestion" type="text" maxlength="220" placeholder="可补充：这是什么景点、适合怎么游览？" />
                <button class="primary-action compact" type="button" :disabled="!imagePreview || visionBusy" @click="askImageExplanation">
                  <ImageUp :size="16" />
                  {{ visionBusy ? "识别中" : "图片讲解" }}
                </button>
                <button v-if="imagePreview" class="ghost-action compact icon-only" type="button" aria-label="清除图片" @click="clearSelectedImage">
                  <X :size="15" />
                </button>
              </div>
              <small>{{ imageFileName || "支持 JPEG、PNG、WebP、GIF，单张不超过 4MB。" }}</small>
              <p v-if="imageAnswer" class="vision-answer">{{ imageAnswer }}</p>
              <div v-if="imageAnswerRefs.length || imageAnswerLatencyMs !== null" class="source-ref-row">
                <span v-if="imageAnswerLatencyMs !== null">响应：{{ formatLatency(imageAnswerLatencyMs) }}</span>
                <span v-for="ref in imageAnswerRefs.slice(0, 4)" :key="`vision-${ref.type}-${ref.id || ref.title}`">
                  {{ sourceTypeLabel(ref) }}：{{ ref.title }}
                </span>
              </div>
            </div>
          </div>
          <div v-if="lastAnswerRefs.length || lastAnswerLatencyMs !== null" class="source-ref-row">
            <span v-if="lastAnswerLatencyMs !== null">响应：{{ formatLatency(lastAnswerLatencyMs) }}</span>
            <span v-for="ref in lastAnswerRefs.slice(0, 4)" :key="`${ref.type}-${ref.id || ref.title}`">
              {{ sourceTypeLabel(ref) }}：{{ ref.title }}
            </span>
          </div>
        </form>
      </article>

      <aside class="spot-detail-guide">
        <DigitalHumanPanel
          :persona="persona"
          :llm-status="llmStatus"
          :tts-status="ttsStatus"
          :stage="stage"
          :expression="expression"
          :mouth-shape="mouthShape"
          :spoken-text="spokenText || localIntro"
          :speech-progress="speechProgress"
          :auto-speak="autoSpeak"
          :speech-supported="speechInputSupported"
          @toggle-auto-speak="(value) => (autoSpeak = value)"
          @speak-greeting="speakText(localIntro)"
          @stop-speaking="stopSpeaking"
        />
      </aside>
    </section>

    <p v-if="notice" class="inline-alert map-alert">{{ notice }}</p>
    <p v-if="error" class="inline-alert error map-alert">
      {{ error }}
      <button type="button" @click="error = ''"><X :size="14" /></button>
    </p>
  </main>
</template>
