import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import {
  ArrowLeft,
  ChevronDown,
  Clock,
  ImageUp,
  LocateFixed,
  MapPin,
  MessageCircle,
  Mic,
  MicOff,
  MoreHorizontal,
  Navigation2,
  Route,
  Send,
  Sparkles,
  X
} from "lucide-vue-next";
import DigitalHumanPanel, { type AvatarExpression, type AvatarMouthShape, type AvatarStage } from "../DigitalHumanPanel.vue";
import { apiGet, apiPost } from "../../api";
import { useFallbackImage } from "../../assets";
import { interruptLiveTalking, liveTalkingEnabled, speakWithLiveTalking } from "../../composables/useLiveTalkingAvatar";
import { useSpeechRecognition } from "../../composables/useSpeechRecognition";
import { imageForSpot } from "../../photos";
import type {
  AsrStatus,
  AsrTranscriptionResponse,
  ChatResponse,
  LocationConfidence,
  LocationResolveResponse,
  LlmStatus,
  NearbyLocationResponse,
  Persona,
  RouteOptions,
  RouteResponse,
  ScenicSpot,
  SourceRef,
  TtsStatus,
  TtsSynthesisResponse,
  VisionResponse
} from "../../types";

type HomeMode = "map" | "detail";
type MapZone = "lingshan" | "nianhua";
type MapLabelAnchor = "start" | "middle" | "end";
type BasemapMode = "custom" | "amap";
type LocationSource = "demo" | "gps" | "anchor";
type CurrentLocation = {
  lat: number;
  lon: number;
  accuracy: number;
  source: LocationSource;
  confidence: LocationConfidence | "demo";
};
type MapSpotLayout = {
  x: number;
  y: number;
  labelX: number;
  labelY: number;
  labelAnchor: MapLabelAnchor;
};
type AMapBoundsOptions = {
  northEast: [number, number];
  southWest: [number, number];
};
type AMapBoundsConstructor = new (southWest: [number, number], northEast: [number, number]) => unknown;
type AMapLayerConstructor = new (options?: Record<string, unknown>) => unknown;

type AMapInstance = {
  add: (overlay: unknown | unknown[]) => void;
  addControl: (control: unknown) => void;
  clearMap: () => void;
  destroy: () => void;
  resize?: () => void;
  setCenter: (center: [number, number]) => void;
  setFitView: (overlays?: unknown[], immediately?: boolean, avoid?: number[], maxZoom?: number) => void;
  setZoom: (zoom: number) => void;
};

type AMapNamespace = {
  Map: new (container: HTMLElement, options: Record<string, unknown>) => AMapInstance;
  Bounds?: AMapBoundsConstructor;
  ImageLayer?: AMapLayerConstructor;
  Marker: new (options: Record<string, unknown>) => unknown;
  Polyline: new (options: Record<string, unknown>) => unknown;
  Pixel: new (x: number, y: number) => unknown;
  Scale?: new () => unknown;
  TileLayer?: AMapLayerConstructor & {
    RoadNet?: AMapLayerConstructor;
    Satellite?: AMapLayerConstructor;
  };
  ToolBar?: new (options?: Record<string, unknown>) => unknown;
  PlaceSearch?: new (options?: Record<string, unknown>) => {
    search: (keyword: string, callback: (status: string, result: unknown) => void) => void;
  };
  plugin: (plugins: string | string[], callback: () => void) => void;
};
type AMapPlaceSearchInstance = {
  search: (keyword: string, callback: (status: string, result: unknown) => void) => void;
};

declare global {
  interface Window {
    AMap?: AMapNamespace;
    _AMapSecurityConfig?: {
      securityJsCode?: string;
    };
  }
}

export type MapGuideExperienceProps = {
  persona: Persona;
  llmStatus: LlmStatus;
  ttsStatus: TtsStatus;
  asrStatus?: AsrStatus;
  suggestions?: string[];
  routeOptions: RouteOptions;
  spots: ScenicSpot[];
  compact?: boolean;
};

export function useMapGuideExperience(props: MapGuideExperienceProps) {

const SOURCE_GUIDE_MAP_SIZE = { width: 1334, height: 1179 };
const GUIDE_MAP_SIZE = { width: 1672, height: 941 };
const GUIDE_MAP_X_SCALE = GUIDE_MAP_SIZE.width / SOURCE_GUIDE_MAP_SIZE.width;
const GUIDE_MAP_Y_SCALE = GUIDE_MAP_SIZE.height / SOURCE_GUIDE_MAP_SIZE.height;
const DEMO_LOCATION_POINT = scaleGuideMapPoint({ x: 905, y: 820 });
const MAX_IMAGE_BYTES = 4 * 1024 * 1024;
const VISION_IMAGE_MAX_EDGE = 1280;
const VISION_IMAGE_QUALITY = 0.82;
const ALLOWED_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);
const AMAP_KEY = String(import.meta.env.VITE_AMAP_KEY || "").trim();
const AMAP_SECURITY_CODE = String(import.meta.env.VITE_AMAP_SECURITY_CODE || "").trim();
const AMAP_SCRIPT_ID = "amap-jsapi-v2";
const AMAP_SPOT_MARKER_TIP_OFFSET_Y = -30;
const AMAP_SCENIC_IMAGE_URLS: Record<MapZone, string> = {
  lingshan: "/assets/scenic/lingshan-handdrawn-map.png",
  nianhua: "/assets/scenic/nianhua-handdrawn-map.png"
};
const AMAP_SCENIC_IMAGE_BOUNDS: Record<MapZone, AMapBoundsOptions> = {
  lingshan: {
    southWest: [120.0896, 31.42695],
    northEast: [120.0971, 31.43172]
  },
  nianhua: {
    southWest: [120.0784, 31.4131],
    northEast: [120.0834, 31.4154]
  }
};

const AMAP_ZONE_VIEW: Record<MapZone, { center: [number, number]; zoom: number }> = {
  lingshan: { center: [120.0941, 31.4301], zoom: 16 },
  nianhua: { center: [120.0813, 31.4147], zoom: 16 }
};

const AMAP_FIXED_GCJ02_COORDS: Record<string, { zone: MapZone; position: [number, number] }> = {
  游客服务中心: { zone: "lingshan", position: [120.0951, 31.4282] },
  灵山大照壁: { zone: "lingshan", position: [120.09482, 31.42852] },
  五明桥: { zone: "lingshan", position: [120.09448, 31.42874] },
  佛足坛: { zone: "lingshan", position: [120.09405, 31.42896] },
  五智门: { zone: "lingshan", position: [120.09368, 31.42916] },
  菩提大道: { zone: "lingshan", position: [120.09336, 31.42936] },
  九龙灌浴: { zone: "lingshan", position: [120.09302, 31.42948] },
  降魔浮雕: { zone: "lingshan", position: [120.0927, 31.42978] },
  阿育王柱: { zone: "lingshan", position: [120.09242, 31.43002] },
  百子戏弥勒: { zone: "lingshan", position: [120.09218, 31.4302] },
  祥符禅寺: { zone: "lingshan", position: [120.09202, 31.43042] },
  灵山大佛: { zone: "lingshan", position: [120.09136, 31.43125] },
  佛教文化博览馆: { zone: "lingshan", position: [120.09386, 31.43066] },
  灵山梵宫: { zone: "lingshan", position: [120.09458, 31.43024] },
  五印坛城: { zone: "lingshan", position: [120.09572, 31.43005] },
  曼飞龙塔: { zone: "lingshan", position: [120.09692, 31.43094] },
  无尽意斋: { zone: "lingshan", position: [120.09612, 31.43048] },
  拈花湾: { zone: "nianhua", position: [120.0813, 31.4147] },
  拈花广场: { zone: "nianhua", position: [120.08115, 31.41375] },
  梵天花海: { zone: "nianhua", position: [120.08025, 31.4149] },
  香月花街: { zone: "nianhua", position: [120.08125, 31.41535] },
  拈花堂: { zone: "nianhua", position: [120.08175, 31.4159] },
  五灯湖: { zone: "nianhua", position: [120.08245, 31.41275] }
};

const MAP_SPOT_LAYOUTS: Record<string, MapSpotLayout> = {
  游客服务中心: { x: 1288, y: 705, labelX: -88, labelY: 40, labelAnchor: "end" },
  灵山大照壁: { x: 1040, y: 853, labelX: 76, labelY: -26, labelAnchor: "start" },
  五明桥: { x: 1000, y: 813, labelX: -82, labelY: 38, labelAnchor: "end" },
  佛足坛: { x: 930, y: 697, labelX: 76, labelY: 38, labelAnchor: "start" },
  五智门: { x: 880, y: 656, labelX: -82, labelY: 38, labelAnchor: "end" },
  菩提大道: { x: 820, y: 594, labelX: -82, labelY: 38, labelAnchor: "end" },
  九龙灌浴: { x: 783, y: 510, labelX: 78, labelY: 40, labelAnchor: "start" },
  降魔浮雕: { x: 695, y: 406, labelX: -82, labelY: 38, labelAnchor: "end" },
  阿育王柱: { x: 607, y: 254, labelX: 78, labelY: -30, labelAnchor: "start" },
  灵山大佛: { x: 399, y: 89, labelX: 76, labelY: -22, labelAnchor: "start" },
  百子戏弥勒: { x: 555, y: 205, labelX: -82, labelY: 38, labelAnchor: "end" },
  祥符禅寺: { x: 509, y: 161, labelX: 76, labelY: -30, labelAnchor: "start" },
  佛教文化博览馆: { x: 875, y: 345, labelX: 78, labelY: -28, labelAnchor: "start" },
  灵山梵宫: { x: 989, y: 101, labelX: 76, labelY: -28, labelAnchor: "start" },
  五印坛城: { x: 1122, y: 486, labelX: 78, labelY: 38, labelAnchor: "start" },
  曼飞龙塔: { x: 1328, y: 355, labelX: -82, labelY: -34, labelAnchor: "end" },
  无尽意斋: { x: 1180, y: 570, labelX: 76, labelY: 36, labelAnchor: "start" },
  拈花湾: { x: 820, y: 470, labelX: -78, labelY: 42, labelAnchor: "end" },
  拈花广场: { x: 928, y: 681, labelX: -78, labelY: 42, labelAnchor: "end" },
  香月花街: { x: 1032, y: 435, labelX: 78, labelY: -32, labelAnchor: "start" },
  梵天花海: { x: 627, y: 199, labelX: 78, labelY: -32, labelAnchor: "start" },
  拈花堂: { x: 1086, y: 585, labelX: 78, labelY: 36, labelAnchor: "start" },
  五灯湖: { x: 430, y: 540, labelX: -78, labelY: 42, labelAnchor: "end" }
};

const MAP_FALLBACK_SLOTS: MapSpotLayout[] = [
  { x: 905, y: 820, labelX: 66, labelY: 24, labelAnchor: "start" },
  { x: 702, y: 140, labelX: 66, labelY: -24, labelAnchor: "start" },
  { x: 520, y: 596, labelX: 66, labelY: -24, labelAnchor: "start" },
  { x: 800, y: 600, labelX: 66, labelY: 24, labelAnchor: "start" },
  { x: 280, y: 214, labelX: 66, labelY: -24, labelAnchor: "start" },
  { x: 724, y: 967, labelX: 66, labelY: 24, labelAnchor: "start" },
  { x: 692, y: 938, labelX: -66, labelY: 30, labelAnchor: "end" },
  { x: 637, y: 812, labelX: 66, labelY: 24, labelAnchor: "start" },
  { x: 596, y: 760, labelX: -66, labelY: 24, labelAnchor: "end" },
  { x: 444, y: 482, labelX: -66, labelY: -24, labelAnchor: "end" },
  { x: 384, y: 304, labelX: 66, labelY: -24, labelAnchor: "start" },
  { x: 958, y: 432, labelX: -66, labelY: -24, labelAnchor: "end" }
];
const FIXED_MAP_PIN_LABELS: Record<string, string> = {
  香月花街: "4"
};

const mode = ref<HomeMode>("map");
const activeZone = ref<MapZone>("lingshan");
const selectedBasemap = ref<BasemapMode>(AMAP_KEY ? "amap" : "custom");
const assistantCollapsed = ref(false);
const question = ref("");
const error = ref("");
const notice = ref("");
const selectedSpotId = ref<number | null>(null);
const currentLocation = ref<CurrentLocation>({ lat: 31.4289, lon: 120.0948, accuracy: 0, source: "demo", confidence: "demo" });
const locationCode = ref("");
const selectedAnchorCode = ref("");
const routeDuration = ref(props.routeOptions.durations[1] || 120);
const routePreference = ref(props.routeOptions.preferences[0] || "佛教文化");
const routeResult = ref<RouteResponse | null>(null);
const routeBusy = ref(false);
const locationBusy = ref(false);
const asking = ref(false);
const visionBusy = ref(false);
const autoSpeak = ref(true);
const stage = ref<AvatarStage>("idle");
const expression = ref<AvatarExpression>("smile");
const mouthShape = ref<AvatarMouthShape>("rest");
const spokenText = ref("");
const speechProgress = ref(0);
const audioRef = ref<HTMLAudioElement | null>(null);
const lastAnswerRefs = ref<SourceRef[]>([]);
const lastAnswerLatencyMs = ref<number | null>(null);
const imagePreview = ref("");
const imageFileName = ref("");
const imageQuestion = ref("");
const imageAnswer = ref("");
const imageAnswerRefs = ref<SourceRef[]>([]);
const imageAnswerLatencyMs = ref<number | null>(null);
const asrRecording = ref(false);
const asrBusy = ref(false);
const mediaRecorder = ref<MediaRecorder | null>(null);
const amapContainer = ref<HTMLDivElement | null>(null);
const amapLoadFailed = ref(false);
let asrStream: MediaStream | null = null;
let asrChunks: Blob[] = [];
let speechTimer: number | undefined;
let amapScriptPromise: Promise<AMapNamespace> | null = null;
let amapMap: AMapInstance | null = null;
let amapPlaceSearch: AMapPlaceSearchInstance | null = null;
let amapLayerZone: MapZone | null = null;
let amapUsesScenicImageLayer = false;
const amapPoiPositions = new Map<number, [number, number]>();
const amapPoiLookupFailed = new Set<number>();

const speech = useSpeechRecognition({
  onTranscript: (text, final) => {
    if (!text) return;
    question.value = text;
    stage.value = final ? "idle" : "listening";
    expression.value = final ? "smile" : "focused";
    mouthShape.value = "rest";
    spokenText.value = final ? `识别到：${text}` : `正在听：${text}`;
    if (final) notice.value = "语音识别完成，可继续编辑或直接提问。";
  }
});

const activeSpots = computed(() => props.spots.filter((spot) => spot.status !== "inactive"));
const visibleSpots = computed(() => activeSpots.value.filter((spot) => (spot.mapZone || "lingshan") === activeZone.value));
const visibleLocationAnchors = computed(() =>
  visibleSpots.value.filter((spot) => spot.verifiedLocation && Number.isFinite(Number(spot.lat)) && Number.isFinite(Number(spot.lon)))
);
const useAmap = computed(() => selectedBasemap.value === "amap" && Boolean(AMAP_KEY) && !amapLoadFailed.value);
const selectedSpot = computed(() => {
  const selected = visibleSpots.value.find((spot) => spot.id === selectedSpotId.value);
  return selected || visibleSpots.value[0] || null;
});
const selectedImage = computed(() => imageForSpot(selectedSpot.value));
const selectedSpotIndex = computed(() => visibleSpots.value.findIndex((spot) => spot.id === selectedSpot.value?.id));
const routeSpotIds = computed(() => new Set((routeResult.value?.spots || []).map((spot) => spot.id)));
const routeSpotOrder = computed(() => new Map((routeResult.value?.spots || []).map((spot, index) => [spot.id, index + 1])));
const coordinateBounds = computed(() => {
  const coords = [
    ...activeSpots.value
      .filter((spot) => (spot.mapZone || "lingshan") === activeZone.value)
      .filter((spot) => Number.isFinite(Number(spot.lat)) && Number.isFinite(Number(spot.lon)))
      .map((spot) => ({ lat: Number(spot.lat), lon: Number(spot.lon) }))
  ];
  if (!coords.length) {
    const center = AMAP_ZONE_VIEW[activeZone.value].center;
    coords.push({ lon: center[0], lat: center[1] });
  }
  const latValues = coords.map((item) => item.lat);
  const lonValues = coords.map((item) => item.lon);
  const minLat = Math.min(...latValues);
  const maxLat = Math.max(...latValues);
  const minLon = Math.min(...lonValues);
  const maxLon = Math.max(...lonValues);
  return {
    minLat: minLat - Math.max((maxLat - minLat) * 0.16, 0.001),
    maxLat: maxLat + Math.max((maxLat - minLat) * 0.16, 0.001),
    minLon: minLon - Math.max((maxLon - minLon) * 0.16, 0.001),
    maxLon: maxLon + Math.max((maxLon - minLon) * 0.16, 0.001)
  };
});
const mapSpotPoints = computed(() =>
  visibleSpots.value.map((spot, index) => {
    const routeOrder = routeSpotOrder.value.get(spot.id) || null;
    return {
      ...spot,
      ...mapPointForSpot(spot, index, visibleSpots.value.length),
      mapVisible: ["拈花堂", "香月花街"].includes(spot.name),
      inRoute: routeSpotIds.value.has(spot.id),
      routeOrder,
      pinLabel: routeOrder ? String(routeOrder) : FIXED_MAP_PIN_LABELS[spot.name] || String(index + 1)
    };
  })
);
const routeMapPoints = computed(() => {
  const source = routeResult.value?.spots.length ? routeResult.value.spots : visibleSpots.value.slice(0, 5);
  return source
    .map((spot) => mapSpotPoints.value.find((point) => point.id === spot.id))
    .filter((point): point is (typeof mapSpotPoints.value)[number] => Boolean(point));
});
const routePolyline = computed(() => routeMapPoints.value.map((point) => `${point.x},${point.y}`).join(" "));
const currentLocationPoint = computed(() =>
  currentLocation.value.source === "demo"
    ? DEMO_LOCATION_POINT
    : mapPointForCoordinate(currentLocation.value.lat, currentLocation.value.lon, DEMO_LOCATION_POINT.x, DEMO_LOCATION_POINT.y)
);
const estimatedTime = computed(() =>
  routeResult.value ? routeResult.value.estimatedDuration : routeMapPoints.value.reduce((sum, spot) => sum + spot.duration, 0)
);
const locationText = computed(() => {
  if (currentLocation.value.source === "anchor") return "已使用现场点位码校准";
  if (currentLocation.value.source === "gps") {
    const confidenceText = currentLocation.value.confidence === "high" ? "可信" : currentLocation.value.confidence === "medium" ? "需复核" : "偏低";
    return `GPS ${confidenceText}，精度约 ${Math.round(currentLocation.value.accuracy || 0)} 米`;
  }
  return "示例位置：景区入口服务区";
});
const localIntro = computed(() => buildSpotIntro(selectedSpot.value));
const shortIntro = computed(() => {
  if (!selectedSpot.value) return "点击地图上的景点，我会进入详情页为你讲解重点。";
  return `${selectedSpot.value.name}：${selectedSpot.value.description}`;
});
const relatedQuestions = computed(() => {
  const name = selectedSpot.value?.name || "这个景点";
  return [`介绍${name}`, `${name}适合拍照吗？`, `${name}下一站去哪？`];
});
const quickQuestions = computed(() => [...relatedQuestions.value, ...(props.suggestions || [])].slice(0, 5));
const speechInputSupported = computed(() => speech.supported.value || Boolean(props.asrStatus?.available));
const voiceButtonText = computed(() => {
  if (speech.listening.value || asrRecording.value) return "停止";
  if (asrBusy.value) return "转写中";
  return "语音";
});

watch(
  selectedSpot,
  (spot) => {
    if (!spot) return;
    stage.value = "idle";
    expression.value = "smile";
    mouthShape.value = "rest";
    spokenText.value = `${spot.name}：${spot.description}`;
    speechProgress.value = 0;
  },
  { immediate: true }
);

watch(activeZone, () => {
  focusAmapZone();
});

watch(mode, (nextMode) => {
  if (nextMode !== "map") destroyAmapMap();
});

watch(selectedBasemap, (nextMode) => {
  if (nextMode === "custom") {
    destroyAmapMap();
    return;
  }
  void syncAmapMap();
});

watch(useAmap, (enabled) => {
  if (enabled && mode.value === "map") void syncAmapMap();
});

watch(
  () => speech.error.value,
  (message) => {
    if (!message) return;
    error.value = message;
    resetSpeech("error", "concerned");
  }
);

function mapPointForCoordinate(lat: number, lon: number, fallbackX: number, fallbackY: number) {
  const bounds = coordinateBounds.value;
  const lonSpan = Math.max(bounds.maxLon - bounds.minLon, 0.0001);
  const latSpan = Math.max(bounds.maxLat - bounds.minLat, 0.0001);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return { x: fallbackX, y: fallbackY };
  return scaleGuideMapPoint({
    x: 92 + ((lon - bounds.minLon) / lonSpan) * 1148,
    y: 1080 - ((lat - bounds.minLat) / latSpan) * 980
  });
}

function mapPointForSpot(spot: ScenicSpot, index: number, total: number) {
  const layout = mapLayoutForSpot(spot, index, total);
  const labelLines = mapLabelLines(spot.name);
  return {
    ...layout,
    labelLines,
    ...mapLabelMetrics(layout, labelLines)
  };
}

function mapLayoutForSpot(spot: ScenicSpot, index: number, total: number): MapSpotLayout {
  const normalizedName = normalizeSpotName(spot.name);
  const namedLayout = MAP_SPOT_LAYOUTS[normalizedName];
  if (namedLayout) return namedLayout;
  if (Number.isFinite(Number(spot.mapX)) && Number.isFinite(Number(spot.mapY))) {
    return scaleGuideMapLayout({
      x: Number(spot.mapX),
      y: Number(spot.mapY),
      labelX: 34,
      labelY: -22,
      labelAnchor: "start"
    });
  }
  const slot = MAP_FALLBACK_SLOTS[index % MAP_FALLBACK_SLOTS.length];
  const repeatOffset = Math.floor(index / MAP_FALLBACK_SLOTS.length) * 18;
  const alternatingOffset = index % 2 === 0 ? 0 : 12;
  const progressOffset = total > MAP_FALLBACK_SLOTS.length ? Math.min(16, total - MAP_FALLBACK_SLOTS.length) : 0;
  return scaleGuideMapLayout({
    ...slot,
    y: Math.min(526, slot.y + repeatOffset - progressOffset),
    labelY: slot.labelY + alternatingOffset
  });
}

function scaleGuideMapX(value: number) {
  return value * GUIDE_MAP_X_SCALE;
}

function scaleGuideMapY(value: number) {
  return value * GUIDE_MAP_Y_SCALE;
}

function scaleGuideMapPoint(point: { x: number; y: number }) {
  return {
    x: scaleGuideMapX(point.x),
    y: scaleGuideMapY(point.y)
  };
}

function scaleGuideMapLayout(layout: MapSpotLayout): MapSpotLayout {
  return {
    ...layout,
    x: scaleGuideMapX(layout.x),
    y: scaleGuideMapY(layout.y)
  };
}

function normalizeSpotName(name: string) {
  return name.replace(/\s+/g, "").replace(/（.*?）/g, "").replace(/\(.*?\)/g, "");
}

const AMAP_POI_FIRST_SPOT_NAMES = new Set(Object.keys(AMAP_FIXED_GCJ02_COORDS).map((name) => normalizeSpotName(name)));
const AMAP_POI_KEYWORD_ALIASES: Record<string, string[]> = {
  游客服务中心: ["灵山胜境游客服务中心", "灵山游客服务中心"],
  灵山大照壁: ["灵山胜境灵山大照壁", "灵山大照壁"],
  九龙灌浴: ["灵山胜境九龙灌浴", "九龙灌浴"],
  祥符禅寺: ["灵山胜境祥符禅寺", "祥符禅寺"],
  灵山大佛: ["灵山胜境灵山大佛", "无锡灵山大佛", "灵山大佛"],
  佛教文化博览馆: ["灵山胜境佛教文化博览馆", "灵山佛教文化博览馆"],
  灵山梵宫: ["灵山胜境灵山梵宫", "灵山梵宫", "梵宫"],
  五印坛城: ["灵山胜境五印坛城", "五印坛城"],
  曼飞龙塔: ["灵山胜境曼飞龙塔", "曼飞龙塔"],
  无尽意斋: ["灵山胜境无尽意斋", "无尽意斋"],
  拈花湾: ["拈花湾景区", "拈花湾禅意小镇", "无锡拈花湾"],
  拈花广场: ["拈花湾拈花广场", "拈花广场"],
  梵天花海: ["拈花湾梵天花海", "梵天花海"],
  香月花街: ["拈花湾香月花街", "香月花街"],
  拈花堂: ["拈花湾拈花堂", "拈花堂"],
  五灯湖: ["拈花湾五灯湖", "五灯湖"]
};
const AMAP_POI_NAME_ALIASES: Record<string, string[]> = {
  灵山大照壁: ["大照壁"],
  灵山梵宫: ["梵宫"],
  佛教文化博览馆: ["佛教文化博览馆"],
  拈花湾: ["拈花湾景区", "拈花湾禅意小镇"]
};

function mapLabelLines(name: string) {
  const chars = Array.from(name.trim());
  if (chars.length <= 5) return [name];
  const firstLineLength = chars.length <= 7 ? 4 : Math.ceil(chars.length / 2);
  return [chars.slice(0, firstLineLength).join(""), chars.slice(firstLineLength).join("")].filter(Boolean);
}

function mapLabelMetrics(layout: MapSpotLayout, labelLines: string[]) {
  const longestLine = Math.max(...labelLines.map((line) => Array.from(line).length), 1);
  const labelWidth = Math.max(116, Math.min(240, longestLine * 22 + 36));
  const labelHeight = labelLines.length * 28 + 22;
  const labelLineStep = 24;
  const labelBoxX =
    layout.labelAnchor === "end"
      ? layout.labelX - labelWidth + 10
      : layout.labelAnchor === "middle"
        ? layout.labelX - labelWidth / 2
        : layout.labelX - 10;
  const labelBoxY = layout.labelY - 20;
  const labelCenterX = labelBoxX + labelWidth / 2;
  const labelCenterY = labelBoxY + labelHeight / 2;
  return {
    labelAnchor: "middle" as const,
    labelX: labelCenterX,
    labelY: labelCenterY - ((labelLines.length - 1) * labelLineStep) / 2,
    labelLineStep,
    labelWidth,
    labelHeight,
    labelBoxX,
    labelBoxY,
    labelLineX: labelCenterX,
    labelLineY: labelCenterY
  };
}

function loadAmapScript() {
  if (window.AMap) return Promise.resolve(window.AMap);
  if (amapScriptPromise) return amapScriptPromise;
  if (!AMAP_KEY) return Promise.reject(new Error("缺少高德地图 Key"));

  if (AMAP_SECURITY_CODE) {
    window._AMapSecurityConfig = { securityJsCode: AMAP_SECURITY_CODE };
  }

  amapScriptPromise = new Promise<AMapNamespace>((resolve, reject) => {
    const existingScript = document.getElementById(AMAP_SCRIPT_ID) as HTMLScriptElement | null;
    if (existingScript && existingScript.dataset.loadState !== "loading") {
      existingScript.remove();
    }

    const script = (document.getElementById(AMAP_SCRIPT_ID) as HTMLScriptElement | null) || document.createElement("script");
    script.id = AMAP_SCRIPT_ID;
    script.async = true;
    script.dataset.loadState = "loading";
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(AMAP_KEY)}&plugin=AMap.Scale,AMap.ToolBar`;
    const timeout = window.setTimeout(() => {
      script.dataset.loadState = "failed";
      script.remove();
      amapScriptPromise = null;
      reject(new Error("高德地图脚本加载超时"));
    }, 12000);
    script.onload = () => {
      window.clearTimeout(timeout);
      script.dataset.loadState = window.AMap ? "loaded" : "failed";
      if (window.AMap) {
        resolve(window.AMap);
        return;
      }
      script.remove();
      amapScriptPromise = null;
      reject(new Error("高德地图脚本加载失败"));
    };
    script.onerror = () => {
      window.clearTimeout(timeout);
      script.dataset.loadState = "failed";
      script.remove();
      amapScriptPromise = null;
      reject(new Error("高德地图脚本加载失败"));
    };
    if (!script.parentElement) document.head.appendChild(script);
  });
  return amapScriptPromise;
}

function loadAmapPlaceSearch(AMap: AMapNamespace) {
  if (amapPlaceSearch) return Promise.resolve(amapPlaceSearch);
  return new Promise<AMapPlaceSearchInstance>((resolve, reject) => {
    AMap.plugin("AMap.PlaceSearch", () => {
      if (!AMap.PlaceSearch) {
        reject(new Error("高德 POI 搜索插件加载失败"));
        return;
      }
      amapPlaceSearch = new AMap.PlaceSearch({
        city: "无锡",
        citylimit: true,
        extensions: "base",
        pageSize: 8
      });
      resolve(amapPlaceSearch);
    });
  });
}

function normalizedMapZone(value?: string | null): MapZone {
  return value === "nianhua" ? "nianhua" : "lingshan";
}

function amapZoneView(zone: MapZone = activeZone.value) {
  return AMAP_ZONE_VIEW[zone];
}

function focusAmapZone(zone: MapZone = activeZone.value) {
  if (!amapMap) return;
  const view = amapZoneView(zone);
  amapMap.setCenter(view.center);
  amapMap.setZoom(view.zoom);
}

function clampRatio(value: number) {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

function amapCoordinateForGuidePoint(point: { x: number; y: number }, zone: MapZone = activeZone.value): [number, number] | null {
  const bounds = AMAP_SCENIC_IMAGE_BOUNDS[zone];
  if (!bounds) return null;
  const xRatio = clampRatio(point.x / GUIDE_MAP_SIZE.width);
  const yRatio = clampRatio(point.y / GUIDE_MAP_SIZE.height);
  return [
    bounds.southWest[0] + (bounds.northEast[0] - bounds.southWest[0]) * xRatio,
    bounds.northEast[1] - (bounds.northEast[1] - bounds.southWest[1]) * yRatio
  ];
}

function amapScenicImagePositionForSpot(spot: ScenicSpot & Partial<MapSpotLayout>): [number, number] | null {
  if (!amapUsesScenicImageLayer) return null;
  const x = Number(spot.x);
  const y = Number(spot.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  return amapCoordinateForGuidePoint({ x, y }, normalizedMapZone(spot.mapZone));
}

function isAmapPositionNearZone(position: [number, number], zone: MapZone) {
  const bounds = AMAP_SCENIC_IMAGE_BOUNDS[zone];
  const lonPadding = zone === "nianhua" ? 0.002 : 0.004;
  const latPadding = zone === "nianhua" ? 0.002 : 0.003;
  return (
    position[0] >= bounds.southWest[0] - lonPadding &&
    position[0] <= bounds.northEast[0] + lonPadding &&
    position[1] >= bounds.southWest[1] - latPadding &&
    position[1] <= bounds.northEast[1] + latPadding
  );
}

function amapFixedPositionForSpot(spot: ScenicSpot): [number, number] | null {
  const cached = AMAP_FIXED_GCJ02_COORDS[normalizeSpotName(spot.name)];
  if (!cached) return null;
  if (cached.zone !== normalizedMapZone(spot.mapZone)) return null;
  return cached.position;
}

function hasVerifiedAmapPosition(spot: ScenicSpot) {
  return Boolean(spot.verifiedLocation) && Number.isFinite(Number(spot.lat)) && Number.isFinite(Number(spot.lon));
}

function shouldPreferAmapPoi(spot: ScenicSpot) {
  return Boolean(normalizeSpotName(spot.name));
}

function uniqueTexts(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

function amapPoiMatchNames(spot: ScenicSpot) {
  const normalizedName = normalizeSpotName(spot.name);
  return uniqueTexts([normalizedName, ...(AMAP_POI_NAME_ALIASES[normalizedName] || []), ...(AMAP_POI_KEYWORD_ALIASES[normalizedName] || [])])
    .map((name) => normalizeSpotName(name))
    .filter(Boolean);
}

function amapPoiKeywords(spot: ScenicSpot) {
  const zoneName = (spot.mapZone || "lingshan") === "nianhua" ? "拈花湾" : "灵山胜境";
  const normalizedName = normalizeSpotName(spot.name);
  const names = uniqueTexts([normalizedName, ...(AMAP_POI_KEYWORD_ALIASES[normalizedName] || [])]);
  return uniqueTexts(names.flatMap((name) => [`${zoneName} ${name}`, `${name} ${zoneName}`, `无锡 ${zoneName} ${name}`, `无锡 ${name}`, name]));
}

function amapPoiPositionFromResult(result: unknown, spot: ScenicSpot): [number, number] | null {
  const poiList = (result as { poiList?: { pois?: unknown[] } })?.poiList?.pois || [];
  const matchNames = amapPoiMatchNames(spot);
  const zoneName = (spot.mapZone || "lingshan") === "nianhua" ? "拈花湾" : "灵山";
  const zone = normalizedMapZone(spot.mapZone);
  const pois = poiList
    .map((poi) => {
      const item = poi as { name?: string; address?: string; pname?: string; cityname?: string; adname?: string; location?: unknown };
      const location = item.location as { lng?: number; lat?: number } | string | undefined;
      const pair =
        typeof location === "string"
          ? location.split(",").map((value) => Number(value))
          : [Number(location?.lng), Number(location?.lat)];
      const name = normalizeSpotName(String(item.name || ""));
      const address = normalizeSpotName(`${item.address || ""}${item.pname || ""}${item.cityname || ""}${item.adname || ""}`);
      const nameMatched = Boolean(name) && matchNames.some((alias) => name === alias || name.includes(alias) || alias.includes(name));
      const addressMatched = matchNames.some((alias) => address.includes(alias));
      const zoneMatched = address.includes(zoneName) || name.includes(zoneName);
      const cityMatched = String(item.cityname || item.adname || address).includes("无锡");
      const positionInZone = isAmapPositionNearZone(pair as [number, number], zone);
      const score =
        (nameMatched ? 20 : 0) +
        (addressMatched ? 8 : 0) +
        (zoneMatched ? 4 : 0) +
        (cityMatched ? 2 : 0) +
        (positionInZone ? 6 : -12);
      return { position: pair as [number, number], score };
    })
    .filter((poi) => Number.isFinite(poi.position[0]) && Number.isFinite(poi.position[1]))
    .sort((left, right) => right.score - left.score);

  return pois[0]?.score >= 8 ? pois[0].position : null;
}

async function searchAmapPoiPosition(AMap: AMapNamespace, spot: ScenicSpot) {
  const search = await loadAmapPlaceSearch(AMap);
  if (!search) return null;

  for (const keyword of amapPoiKeywords(spot)) {
    const position = await new Promise<[number, number] | null>((resolve) => {
      search.search(keyword, (status, result) => {
        if (status !== "complete") {
          resolve(null);
          return;
        }
        resolve(amapPoiPositionFromResult(result, spot));
      });
    });
    if (position) return position;
  }
  return null;
}

async function ensureAmapPoiPositions(AMap: AMapNamespace) {
  const missingSpots = visibleSpots.value.filter(
    (spot) => shouldPreferAmapPoi(spot) && !amapPoiPositions.has(spot.id) && !amapPoiLookupFailed.has(spot.id)
  );
  for (const spot of missingSpots) {
    const position = await searchAmapPoiPosition(AMap, spot);
    if (position) {
      amapPoiPositions.set(spot.id, position);
      renderAmapOverlays(AMap);
    } else {
      amapPoiLookupFailed.add(spot.id);
    }
  }
}

function amapPositionForSpot(spot: ScenicSpot & Partial<MapSpotLayout>): [number, number] | null {
  const scenicPosition = amapScenicImagePositionForSpot(spot);
  if (scenicPosition) return scenicPosition;
  const poiPosition = amapPoiPositions.get(spot.id);
  if (poiPosition) return poiPosition;
  return null;
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function createAmapSpotContent(
  spot: ScenicSpot & MapSpotLayout & { inRoute: boolean; pinLabel: string; routeOrder: number | null }
) {
  const content = document.createElement("button");
  content.type = "button";
  content.className = [
    "amap-spot-callout",
    `label-${spot.labelAnchor}`,
    selectedSpotId.value === spot.id ? "selected" : "",
    spot.inRoute ? "routed" : "",
    routeResult.value && !spot.inRoute ? "dimmed" : ""
  ]
    .filter(Boolean)
    .join(" ");
  content.style.setProperty("--label-x", `${spot.labelX}px`);
  content.style.setProperty("--label-y", `${spot.labelY}px`);
  content.title = spot.name;
  content.setAttribute("aria-label", spot.name);
  content.innerHTML = `
    <span class="amap-spot-pin"><span>${escapeHtml(spot.pinLabel)}</span></span>
    <span class="amap-spot-name">${escapeHtml(spot.name)}</span>
  `;
  content.addEventListener("click", (event) => {
    event.stopPropagation();
    openSpotDetail(spot.id);
  });
  return content;
}

function createAmapCurrentLocationContent() {
  const content = document.createElement("span");
  content.className = "amap-current-location";
  content.textContent = "当前位置";
  return content;
}

function amapPositionForCurrentLocation(): [number, number] | null {
  if (amapUsesScenicImageLayer && currentLocation.value.source === "anchor") {
    const anchorSpot = mapSpotPoints.value.find((spot) => spot.id === selectedSpotId.value);
    const anchorPosition = anchorSpot ? amapScenicImagePositionForSpot(anchorSpot) : null;
    if (anchorPosition) return anchorPosition;
  }
  if (currentLocation.value.source === "demo") return null;
  const lat = Number(currentLocation.value.lat);
  const lon = Number(currentLocation.value.lon);
  return Number.isFinite(lat) && Number.isFinite(lon) ? [lon, lat] : null;
}

function createAmapScenicImageLayer(AMap: AMapNamespace, zone: MapZone) {
  if (!AMap.ImageLayer || !AMap.Bounds) return null;
  const bounds = AMAP_SCENIC_IMAGE_BOUNDS[zone];
  return new AMap.ImageLayer({
    bounds: new AMap.Bounds(bounds.southWest, bounds.northEast),
    opacity: 1,
    url: AMAP_SCENIC_IMAGE_URLS[zone],
    zIndex: 3,
    zooms: [13, 20]
  });
}

function createAmapBaseOptions() {
  return {
    features: ["bg", "road", "building", "point"],
    mapStyle: "amap://styles/normal"
  };
}

async function syncAmapMap() {
  if (!useAmap.value || mode.value !== "map") return;
  await nextTick();
  if (!amapContainer.value) return;

  try {
    const AMap = await loadAmapScript();
    if (amapMap && amapLayerZone !== activeZone.value) destroyAmapMap();
    if (!amapMap) {
      const view = amapZoneView();
      const baseLayerOptions = createAmapBaseOptions();
      amapLayerZone = activeZone.value;
      amapUsesScenicImageLayer = false;
      amapMap = new AMap.Map(amapContainer.value, {
        center: view.center,
        ...baseLayerOptions,
        resizeEnable: true,
        showLabel: true,
        viewMode: "2D",
        zoom: view.zoom
      });
      if (AMap.Scale) amapMap.addControl(new AMap.Scale());
      if (AMap.ToolBar) amapMap.addControl(new AMap.ToolBar({ position: "RB" }));
    }

    amapMap.resize?.();
    renderAmapOverlays(AMap);
    window.requestAnimationFrame(() => amapMap?.resize?.());
    if (!amapUsesScenicImageLayer && visibleSpots.value.some((spot) => shouldPreferAmapPoi(spot))) {
      void ensureAmapPoiPositions(AMap).then(() => renderAmapOverlays(AMap));
    }
  } catch (loadError) {
    const detail = loadError instanceof Error ? loadError.message : "未知错误";
    console.error("AMap load failed", loadError);
    amapLoadFailed.value = true;
    selectedBasemap.value = "custom";
    error.value = `高德地图加载失败：${detail}。已切换为示意地图，请检查 Web JS API Key、安全密钥、域名白名单和网络访问。`;
  }
}

function renderAmapOverlays(AMap: AMapNamespace) {
  if (!amapMap) return;
  amapMap.clearMap();
  focusAmapZone();

  const overlays: unknown[] = [];
  const fitOverlays: unknown[] = [];
  const routePositions = routeResult.value
    ? routeMapPoints.value.map(amapPositionForSpot).filter((position): position is [number, number] => Boolean(position))
    : [];
  if (routePositions.length > 1) {
    const routeOverlay = new AMap.Polyline({
      path: routePositions,
      showDir: true,
      strokeColor: "#df5b4d",
      strokeOpacity: 0.92,
      strokeWeight: 7,
      zIndex: 70
    });
    overlays.push(routeOverlay);
    fitOverlays.push(routeOverlay);
  }

  mapSpotPoints.value.forEach((spot) => {
    const position = amapPositionForSpot(spot);
    if (!position) return;
    const spotOverlay = new AMap.Marker({
      anchor: "center",
      content: createAmapSpotContent(spot),
      offset: new AMap.Pixel(0, AMAP_SPOT_MARKER_TIP_OFFSET_Y),
      position,
      title: spot.name,
      zIndex: selectedSpotId.value === spot.id ? 130 : spot.inRoute ? 120 : 100
    });
    overlays.push(spotOverlay);
    fitOverlays.push(spotOverlay);
  });

  const currentPosition = amapPositionForCurrentLocation();
  if (currentPosition) {
    overlays.push(
      new AMap.Marker({
        anchor: "center",
        content: createAmapCurrentLocationContent(),
        offset: new AMap.Pixel(0, 0),
        position: currentPosition,
        zIndex: 140
      })
    );
  }

  amapMap.add(overlays);
  if (fitOverlays.length) {
    amapMap.setFitView(fitOverlays, false, [72, 72, 72, 72], 17);
  } else {
    focusAmapZone();
  }
}

function destroyAmapMap() {
  if (amapMap) amapMap.destroy();
  amapMap = null;
  amapLayerZone = null;
  amapUsesScenicImageLayer = false;
}

function buildSpotIntro(spot: ScenicSpot | null) {
  if (!spot) return "请选择地图上的景点，我会为你做一段简短讲解。";
  const story = spot.story ? `讲解重点：${spot.story}` : "";
  return `${spot.name}位于${spot.location}，建议游览约 ${spot.duration} 分钟。${spot.description}${story ? ` ${story}` : ""}`;
}

function openSpotDetail(spotId: number) {
  selectedSpotId.value = spotId;
  const spot = activeSpots.value.find((item) => item.id === spotId);
  if (!spot) return;
  mode.value = "detail";
  notice.value = "";
  error.value = "";
  if (autoSpeak.value) void speakText(buildSpotIntro(spot));
}

function backToMap() {
  mode.value = "map";
  question.value = "";
  notice.value = "";
  error.value = "";
}

function switchMapZone(zone: MapZone) {
  mode.value = "map";
  activeZone.value = zone;
  selectedSpotId.value = null;
  routeResult.value = null;
  question.value = "";
  error.value = "";
  notice.value = zone === "nianhua" ? "已切换到拈花湾小镇分区。" : "已切换到灵山胜境核心区。";
  focusAmapZone(zone);
  void syncAmapMap();
}

function switchBasemap(nextMode: BasemapMode) {
  if (nextMode === "amap" && !AMAP_KEY) {
    selectedBasemap.value = "custom";
    amapLoadFailed.value = true;
    error.value = "未配置高德 Web JS API Key，演示已保持自定义景区图。";
    return;
  }
  if (nextMode === "amap") {
    amapLoadFailed.value = false;
    destroyAmapMap();
  }
  selectedBasemap.value = nextMode;
  error.value = "";
  notice.value = nextMode === "amap" ? "已切换到高德底图，可用于坐标校准。" : "已切换到自定义景区图，点位坐标继续复用。";
  if (nextMode === "amap") void syncAmapMap();
}

function resetSpeech(nextStage: AvatarStage = "idle", nextExpression: AvatarExpression = "smile") {
  if (speechTimer) {
    window.clearInterval(speechTimer);
    speechTimer = undefined;
  }
  stage.value = nextStage;
  expression.value = nextExpression;
  mouthShape.value = nextStage === "speaking" ? "a" : "rest";
  speechProgress.value = 0;
}

function mouthShapeForSpeech(text: string, cursor: number): AvatarMouthShape {
  const current = text[Math.max(0, Math.min(text.length - 1, cursor - 1))] || "";
  if (!current || /[\s，。！？、；：,.!?;:]/.test(current)) return "rest";
  const shapes: AvatarMouthShape[] = ["a", "o", "e", "i", "u"];
  const code = current.codePointAt(0) || cursor;
  return shapes[(code + cursor) % shapes.length];
}

function updateSpeechProgress(text: string, progress: number) {
  const safeProgress = Math.max(0, Math.min(1, progress));
  const cursor = Math.max(1, Math.round(text.length * safeProgress));
  spokenText.value = text.slice(Math.max(0, cursor - 18), Math.min(text.length, cursor + 24));
  speechProgress.value = safeProgress;
  mouthShape.value = safeProgress >= 0.995 ? "rest" : mouthShapeForSpeech(text, cursor);
}

function stopSpeaking(interruptAvatar = true) {
  window.speechSynthesis?.cancel();
  if (audioRef.value) {
    audioRef.value.pause();
    audioRef.value = null;
  }
  if (interruptAvatar) void interruptLiveTalking();
  resetSpeech();
}

function blobToDataUrl(blob: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("音频读取失败"));
    reader.readAsDataURL(blob);
  });
}

function fileToDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("图片读取失败"));
    reader.readAsDataURL(file);
  });
}

function loadImage(file: File) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("图片预处理失败"));
    };
    image.src = url;
  });
}

async function fileToVisionDataUrl(file: File) {
  if (file.type === "image/gif") return fileToDataUrl(file);
  const image = await loadImage(file);
  const width = image.naturalWidth || image.width;
  const height = image.naturalHeight || image.height;
  if (!width || !height) return fileToDataUrl(file);

  const scale = Math.min(1, VISION_IMAGE_MAX_EDGE / Math.max(width, height));
  if (scale === 1 && file.size <= 1.2 * 1024 * 1024) return fileToDataUrl(file);

  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(width * scale));
  canvas.height = Math.max(1, Math.round(height * scale));
  const context = canvas.getContext("2d");
  if (!context) return fileToDataUrl(file);
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(image, 0, 0, canvas.width, canvas.height);

  return new Promise<string>((resolve) => {
    canvas.toBlob(
      async (blob) => {
        if (!blob) {
          resolve(canvas.toDataURL("image/jpeg", VISION_IMAGE_QUALITY));
          return;
        }
        resolve(await blobToDataUrl(blob));
      },
      "image/jpeg",
      VISION_IMAGE_QUALITY
    );
  });
}

async function handleImageSelect(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  error.value = "";
  notice.value = "";
  if (!ALLOWED_IMAGE_TYPES.has(file.type)) {
    error.value = "图片讲解仅支持 JPEG、PNG、WebP 或 GIF。";
    return;
  }
  if (file.size > MAX_IMAGE_BYTES) {
    error.value = "图片过大，请压缩到 4MB 以内。";
    return;
  }
  try {
    imagePreview.value = await fileToVisionDataUrl(file);
    imageFileName.value = file.name;
    imageAnswer.value = "";
    imageAnswerRefs.value = [];
    imageAnswerLatencyMs.value = null;
    notice.value = "图片已读取，可补充问题后生成讲解。";
  } catch (readError) {
    error.value = readError instanceof Error ? readError.message : "图片读取失败";
  }
}

function clearSelectedImage() {
  imagePreview.value = "";
  imageFileName.value = "";
  imageQuestion.value = "";
  imageAnswer.value = "";
  imageAnswerRefs.value = [];
  imageAnswerLatencyMs.value = null;
}

function stopServerAsr() {
  if (mediaRecorder.value && mediaRecorder.value.state !== "inactive") {
    mediaRecorder.value.stop();
    return;
  }
  asrRecording.value = false;
}

async function startServerAsr() {
  if (!props.asrStatus?.available) {
    error.value = "当前浏览器不支持语音识别，后端 ASR 也未配置，请使用文字输入。";
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    error.value = "当前浏览器无法录音，请改用文字输入。";
    return;
  }
  stopSpeaking();
  try {
    asrStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    asrChunks = [];
    const recorderOptions = MediaRecorder.isTypeSupported("audio/webm") ? { mimeType: "audio/webm" } : undefined;
    const recorder = recorderOptions ? new MediaRecorder(asrStream, recorderOptions) : new MediaRecorder(asrStream);
    mediaRecorder.value = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) asrChunks.push(event.data);
    };
    recorder.onstart = () => {
      asrRecording.value = true;
      resetSpeech("listening", "focused");
      spokenText.value = "正在录音，请说出问题。";
    };
    recorder.onerror = () => {
      error.value = "录音失败，请检查麦克风权限。";
      resetSpeech("error", "concerned");
    };
    recorder.onstop = async () => {
      asrRecording.value = false;
      asrBusy.value = true;
      resetSpeech("thinking", "surprised");
      asrStream?.getTracks().forEach((track) => track.stop());
      asrStream = null;
      try {
        const blob = new Blob(asrChunks, { type: recorder.mimeType || "audio/webm" });
        const audio = await blobToDataUrl(blob);
        const result = await apiPost<AsrTranscriptionResponse>("/api/asr/transcribe", { audio });
        if (result.text) {
          question.value = result.text;
          spokenText.value = `识别到：${result.text}`;
          notice.value = "语音转写完成，可继续编辑或直接提问。";
          resetSpeech("idle", "smile");
        } else {
          error.value = result.message || "语音转写未返回文字，请改用文字输入。";
          resetSpeech("error", "concerned");
        }
      } catch (recordError) {
        error.value = recordError instanceof Error ? recordError.message : "语音转写失败";
        resetSpeech("error", "concerned");
      } finally {
        asrBusy.value = false;
        mediaRecorder.value = null;
      }
    };
    recorder.start();
  } catch {
    error.value = "麦克风权限未开启，请允许后再试。";
    resetSpeech("error", "concerned");
  }
}

function toggleVoiceInput() {
  error.value = "";
  notice.value = "";
  if (speech.supported.value) {
    if (speech.listening.value) {
      speech.stop();
      resetSpeech();
    } else {
      stopSpeaking();
      resetSpeech("listening", "focused");
      spokenText.value = "正在听，请说出你的问题。";
      speech.start();
    }
    return;
  }
  if (asrRecording.value) {
    stopServerAsr();
    return;
  }
  void startServerAsr();
}

function speakWithBrowser(text: string) {
  if (!text || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  resetSpeech("speaking", "smile");
  const startedAt = Date.now();
  const estimatedMs = Math.max(2200, text.length * 190);
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-CN";
  utterance.rate = props.persona.voiceSpeed || 0.92;
  utterance.pitch = props.persona.voicePitch || 1.02;
  utterance.onstart = () => resetSpeech("speaking", "smile");
  utterance.onboundary = (event) => updateSpeechProgress(text, Number(event.charIndex || 0) / Math.max(text.length, 1));
  utterance.onend = () => resetSpeech();
  utterance.onerror = () => resetSpeech("error", "concerned");
  speechTimer = window.setInterval(() => updateSpeechProgress(text, (Date.now() - startedAt) / estimatedMs), 180);
  window.speechSynthesis.speak(utterance);
}

async function speakText(text: string) {
  if (!text) return;
  stopSpeaking(false);
  if (liveTalkingEnabled) {
    resetSpeech("thinking", "surprised");
    const sentToAvatar = await speakWithLiveTalking(text);
    if (sentToAvatar) {
      resetSpeech("speaking", "smile");
      const startedAt = Date.now();
      const estimatedMs = Math.max(2600, text.length * 210);
      updateSpeechProgress(text, 0.01);
      speechTimer = window.setInterval(() => updateSpeechProgress(text, (Date.now() - startedAt) / estimatedMs), 180);
      return;
    }
  }
  if (props.ttsStatus.available) {
    try {
      resetSpeech("thinking", "surprised");
      const result = await apiPost<TtsSynthesisResponse>("/api/tts/synthesize", {
        text,
        speed: props.persona.voiceSpeed,
        pitch: props.persona.voicePitch
      });
      if (result.audioDataUrl && !result.fallback) {
        const audio = new Audio(result.audioDataUrl);
        audioRef.value = audio;
        audio.onplay = () => {
          resetSpeech("speaking", "smile");
          updateSpeechProgress(text, 0.01);
        };
        audio.ontimeupdate = () => updateSpeechProgress(text, audio.duration ? audio.currentTime / audio.duration : speechProgress.value);
        audio.onended = () => {
          audioRef.value = null;
          resetSpeech();
        };
        audio.onerror = () => {
          audioRef.value = null;
          speakWithBrowser(text);
        };
        await audio.play();
        return;
      }
    } catch {
      speakWithBrowser(text);
      return;
    }
  }
  speakWithBrowser(text);
}

function shouldAttachSelectedSpotContext(text: string) {
  const compact = text.replace(/\s+/g, "").toLowerCase();
  if (!compact) return false;
  if (/^(你好|您好|在吗|hello|hi|谢谢|谢谢你|感谢|辛苦了)$/.test(compact)) return false;
  if (/(你是谁|你叫什么|讲个笑话|写一首诗|现在几点|几点了|天气)/.test(compact)) return false;
  const explicitSpot = activeSpots.value.some((spot) => {
    const name = spot.name.replace(/\s+/g, "").toLowerCase();
    const aliases = [name, name.replace(/^灵山/, ""), name.replace(/^拈花湾/, ""), name.replace(/^拈花/, "")].filter((item) => item.length >= 2);
    return aliases.some((alias) => compact.includes(alias));
  });
  if (explicitSpot) return false;
  return /(这里|这个|当前|景点|它|开放|几点|表演|演出|拍照|打卡|介绍|亮点|特色|多久|路线|怎么走|在哪|位置|门票|适合|好玩|看什么|多高|面积|参数)/.test(compact);
}

async function askCurrentSpot(value?: string) {
  const spot = selectedSpot.value;
  const cleanQuestion = (value || question.value).trim();
  if (!cleanQuestion || asking.value) return;
  asking.value = true;
  error.value = "";
  notice.value = "";
  lastAnswerLatencyMs.value = null;
  resetSpeech("thinking", "surprised");
  try {
    const prompt = spot && shouldAttachSelectedSpotContext(cleanQuestion) ? `${cleanQuestion}。当前选中的景点是：${spot.name}。` : cleanQuestion;
    const result = await apiPost<ChatResponse>("/api/chat", { question: prompt });
    question.value = "";
    spokenText.value = result.answer;
    lastAnswerRefs.value = result.sourceRefs || [];
    lastAnswerLatencyMs.value = Number.isFinite(Number(result.latencyMs)) ? Number(result.latencyMs) : null;
    notice.value = result.fallback ? "已使用本地资料回答。" : "AI 已生成当前景点讲解。";
    if (autoSpeak.value) void speakText(result.answer);
    else resetSpeech();
  } catch (askError) {
    error.value = askError instanceof Error ? askError.message : "AI 讲解请求失败";
    resetSpeech("error", "concerned");
  } finally {
    asking.value = false;
  }
}

async function askImageExplanation() {
  if (!imagePreview.value || visionBusy.value) return;
  visionBusy.value = true;
  error.value = "";
  notice.value = "";
  imageAnswerLatencyMs.value = null;
  resetSpeech("thinking", "surprised");
  const spotName = selectedSpot.value?.name ? `当前景点是${selectedSpot.value.name}。` : "";
  const prompt = imageQuestion.value.trim() || `${spotName}请识别这张景区照片，并生成适合游客收听的讲解。`;
  try {
    const result = await apiPost<VisionResponse>("/api/vision/analyze", {
      image: imagePreview.value,
      question: prompt
    });
    imageAnswer.value = result.answer;
    imageAnswerRefs.value = result.sourceRefs || [];
    imageAnswerLatencyMs.value = Number.isFinite(Number(result.latencyMs)) ? Number(result.latencyMs) : null;
    spokenText.value = result.answer;
    notice.value = result.fallback ? "图片讲解暂未接通视觉模型，已返回配置提示。" : "图片讲解已生成。";
    if (autoSpeak.value) void speakText(result.answer);
    else resetSpeech();
  } catch (visionError) {
    error.value = visionError instanceof Error ? visionError.message : "图片讲解请求失败";
    resetSpeech("error", "concerned");
  } finally {
    visionBusy.value = false;
  }
}

function sourceTypeLabel(ref: SourceRef) {
  if (ref.type === "knowledge") {
    if (ref.sourceType === "official_docx") return "官方知识库";
    if (ref.sourceType === "behavior_excel") return "行为数据说明";
    if (ref.sourceType === "chat_draft") return "问答沉淀";
    return "知识库";
  }
  if (ref.type === "spot") return "景点资料";
  if (ref.type === "model") return "模型";
  if (ref.type === "fallback") return "本地兜底";
  return ref.category || "来源";
}

function formatLatency(ms: number | null) {
  if (!Number.isFinite(Number(ms))) return "";
  const value = Math.max(0, Number(ms));
  if (value < 1000) return `${Math.round(value)}ms`;
  return `${(value / 1000).toFixed(1)}s`;
}

function extractLocationCode(rawValue: string) {
  const raw = rawValue.trim();
  if (!raw) return "";
  try {
    const parsed = new URL(raw, window.location.origin);
    const hashQuery = parsed.hash.includes("?") ? parsed.hash.slice(parsed.hash.indexOf("?") + 1) : "";
    return parsed.searchParams.get("loc") || parsed.searchParams.get("code") || new URLSearchParams(hashQuery).get("loc") || raw;
  } catch {
    const match = raw.match(/(?:loc|code)=([^&#]+)/i);
    return match ? decodeURIComponent(match[1]) : raw;
  }
}

function locationCodeFromUrl() {
  const hash = window.location.hash || "";
  const hashQuery = hash.includes("?") ? hash.slice(hash.indexOf("?") + 1) : "";
  return new URLSearchParams(window.location.search).get("loc") || new URLSearchParams(hashQuery).get("loc") || "";
}

function switchToSpotZone(spot: ScenicSpot) {
  const zone = spot.mapZone === "nianhua" ? "nianhua" : "lingshan";
  if (activeZone.value !== zone) activeZone.value = zone;
}

function applyLocationAnchor(spot: ScenicSpot, message = "") {
  if (!Number.isFinite(Number(spot.lat)) || !Number.isFinite(Number(spot.lon))) {
    error.value = "该点位缺少可用坐标，请先在后台补充经纬度。";
    return;
  }
  switchToSpotZone(spot);
  selectedSpotId.value = spot.id;
  currentLocation.value = {
    lat: Number(spot.lat),
    lon: Number(spot.lon),
    accuracy: 5,
    source: "anchor",
    confidence: "high"
  };
  selectedAnchorCode.value = spot.locationCode || String(spot.id);
  notice.value = message || `已校准到 ${spot.name}。`;
  error.value = "";
}

async function resolveLocationCode(rawValue = locationCode.value) {
  const code = extractLocationCode(rawValue);
  if (!code) {
    error.value = "请输入标识牌点位码或扫码链接。";
    return;
  }
  locationBusy.value = true;
  error.value = "";
  try {
    const result = await apiGet<LocationResolveResponse>(`/api/location/resolve?code=${encodeURIComponent(code)}`);
    if (result.anchor) {
      applyLocationAnchor(result.anchor, result.message);
      locationCode.value = result.anchor.locationCode || code;
    } else {
      error.value = result.message;
    }
  } catch (resolveError) {
    const localSpot = activeSpots.value.find((spot) => {
      const normalized = (spot.locationCode || String(spot.id)).replace(/[\s_\-#：:]+/g, "").toUpperCase();
      const normalizedCode = code.replace(/[\s_\-#：:]+/g, "").toUpperCase();
      return normalized === normalizedCode || String(spot.id) === code || spot.name === code;
    });
    if (localSpot) {
      applyLocationAnchor(localSpot, `已使用本地点位数据校准到 ${localSpot.name}。`);
    } else {
      error.value = resolveError instanceof Error ? resolveError.message : "点位码解析失败。";
    }
  } finally {
    locationBusy.value = false;
  }
}

function useSelectedAnchor() {
  if (!selectedAnchorCode.value) return;
  void resolveLocationCode(selectedAnchorCode.value);
}

async function buildRoute() {
  routeBusy.value = true;
  error.value = "";
  try {
    const result = await apiPost<RouteResponse>("/api/routes/recommend", {
      duration: routeDuration.value,
      preference: routePreference.value
    });
    const resultZone = result.spots[0]?.mapZone;
    if ((resultZone === "nianhua" || resultZone === "lingshan") && activeZone.value !== resultZone) {
      activeZone.value = resultZone;
    }
    routeResult.value = result;
    if (result.spots[0]) selectedSpotId.value = result.spots[0].id;
    notice.value = `${result.title} 已生成，预计 ${result.estimatedDuration} 分钟。`;
  } catch (routeError) {
    error.value = routeError instanceof Error ? routeError.message : "路线生成失败";
  } finally {
    routeBusy.value = false;
  }
}

function locateCurrentPosition() {
  if (!navigator.geolocation) {
    error.value = "当前浏览器不支持定位，已保留入口示例位置。";
    return;
  }
  locationBusy.value = true;
  error.value = "";
  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const { latitude, longitude, accuracy } = position.coords;
      try {
        const data = await apiGet<NearbyLocationResponse>(
          `/api/spots/nearby?lat=${latitude}&lon=${longitude}&accuracy=${Math.round(accuracy || 0)}&limit=3`
        );
        currentLocation.value = { lat: latitude, lon: longitude, accuracy, source: "gps", confidence: data.confidence };
        if (data.nearest && data.confidence !== "low") {
          switchToSpotZone(data.nearest);
          selectedSpotId.value = data.nearest.id;
          notice.value = data.message;
        } else if (data.nearest) {
          notice.value = data.message;
        } else {
          notice.value = "已定位，但附近暂无景点坐标。";
        }
      } catch {
        currentLocation.value = { lat: latitude, lon: longitude, accuracy, source: "gps", confidence: accuracy > 120 ? "low" : "medium" };
        notice.value = "已定位，附近景点查询暂不可用。";
      } finally {
        locationBusy.value = false;
      }
    },
    () => {
      locationBusy.value = false;
      error.value = "定位失败，请检查浏览器权限。";
    },
    { timeout: 10000, maximumAge: 30000, enableHighAccuracy: true }
  );
}

onMounted(() => {
  void syncAmapMap();
  const initialLocationCode = locationCodeFromUrl();
  if (initialLocationCode) {
    locationCode.value = initialLocationCode;
    void resolveLocationCode(initialLocationCode);
  }
});

watch([useAmap, mode, activeZone, selectedSpotId, mapSpotPoints, routeMapPoints, currentLocation], () => {
  void syncAmapMap();
});

onUnmounted(() => {
  speech.stop();
  stopServerAsr();
  asrStream?.getTracks().forEach((track) => track.stop());
  stopSpeaking();
  destroyAmapMap();
});

  return {
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
  };
}
