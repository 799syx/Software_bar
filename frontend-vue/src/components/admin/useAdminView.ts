import { computed, onMounted, reactive, ref, watch, type Component } from "vue";
import {
  Activity,
  BadgeCheck,
  Bot,
  CheckCircle2,
  Clock3,
  Database,
  Download,
  FileText,
  Gauge,
  HeartPulse,
  MapPinned,
  MessageSquareText,
  Radar,
  RefreshCw,
  Route,
  Save,
  ShieldAlert,
  SmilePlus,
  Star,
  Target,
  Trash2,
  Upload,
  Users,
  Zap,
  X
} from "lucide-vue-next";
import { apiDelete, apiGet, apiPost, apiPut } from "../../api";
import { digitalHumanAvatar, digitalHumanAvatarFallback, useFallbackImage } from "../../assets";
import { fallbackKnowledgeDocuments } from "../../fallback";
import { imageForSpot, photoOptions } from "../../photos";
import MetricChart from "../MetricChart.vue";
import {
  clampNumber,
  clonePersona,
  compactText,
  compactTrendLabel,
  distributionCount,
  emptyKnowledgeForm,
  emptySpotForm,
  formatNumber,
  markdownTable,
  percentNumber,
  pressurePercent,
  readInitialAdminTab,
  readSessionAdminToken,
  rememberSessionAdminToken,
  type ActionStatus,
  type AdminAction,
  type AdminTab,
  type KnowledgeForm,
  type ModalName,
  type SpotForm
} from "./adminViewUtils";
import type {
  AnalyticsOverview,
  BehaviorAnalytics,
  ChatResponse,
  KnowledgeDocument,
  LlmStatus,
  OperationsOverview,
  Persona,
  PublicDataImportResult,
  ScenicSpot,
  SystemCapabilities
} from "../../types";

type KnowledgeDocxUploadResult = {
  items: KnowledgeDocument[];
  imported: number;
  paragraphCount: number;
  sourceFile: string;
  mode: string;
};

export type AdminViewProps = {
  analytics: AnalyticsOverview;
  llmStatus: LlmStatus;
  capabilities: SystemCapabilities;
  spots: ScenicSpot[];
  persona: Persona;
};

export type AdminViewEmit = (event: "refresh") => void;

export function useAdminView(props: AdminViewProps, emit: AdminViewEmit) {

const adminTabs: Array<{ key: AdminTab; label: string; icon: Component }> = [
  { key: "screen", label: "运营概览", icon: Activity },
  { key: "knowledge", label: "内容维护", icon: FileText },
  { key: "persona", label: "数字人", icon: Bot },
  { key: "report", label: "体验报告", icon: Star }
];

const activeTab = ref<AdminTab>(readInitialAdminTab());
const modal = ref<ModalName>(null);
const adminToken = ref(readSessionAdminToken());
const adminSpots = ref<ScenicSpot[]>(props.spots);
const knowledgeDocs = ref<KnowledgeDocument[]>(fallbackKnowledgeDocuments);
const chatRecords = ref<ChatResponse[]>(props.analytics.recentQuestions || []);
const behaviorData = ref<BehaviorAnalytics | null>(props.analytics.behaviorBaseline || null);
const operationsOverview = ref<OperationsOverview | null>(null);
const busy = ref(false);
const saving = ref(false);
const importingPublicData = ref(false);
const importingBehaviorRows = ref(false);
const convertingChatId = ref("");
const notice = ref("");
const adminError = ref("");
const knowledgeQuery = ref("");
const knowledgeCategory = ref("all");
const selectedKnowledgeId = ref<string | null>(null);
const selectedSpotId = ref<number | null>(null);
const knowledgeUploadInput = ref<HTMLInputElement | null>(null);
const knowledgeForm = ref<KnowledgeForm>(emptyKnowledgeForm());
const spotForm = ref<SpotForm>(emptySpotForm());
const personaForm = ref<Persona>(clonePersona(props.persona));
const actionStatus = reactive<Record<AdminAction, ActionStatus>>({
  refresh: "idle",
  importPublic: "idle",
  importBehavior: "idle",
  uploadKnowledge: "idle",
  saveKnowledge: "idle",
  deleteKnowledge: "idle",
  convertChat: "idle",
  saveSpot: "idle",
  deleteSpot: "idle",
  savePersona: "idle"
});
const spotPhotoChoices = photoOptions();

const behavior = computed(() => behaviorData.value || props.analytics.behaviorBaseline);
const behaviorSampleRows = computed(() => behavior.value?.rowCount || behavior.value?.behaviorRecordCount || 0);
const behaviorMatchedRows = computed(() => behavior.value?.matchedScenicRows || 0);
const activeKnowledgeDocs = computed(() => knowledgeDocs.value.filter((item) => item.status === "active"));
const officialKnowledgeDocs = computed(() => {
  const officialDocs = knowledgeDocs.value.filter((document) => {
    const title = document.title || "";
    const category = document.category || "";
    return document.sourceType === "official_docx" || title.includes("官方资料包") || category.includes("官方");
  });
  return officialDocs.length ? officialDocs : knowledgeDocs.value;
});
const knowledgeCategories = computed(() =>
  Array.from(new Set(officialKnowledgeDocs.value.map((document) => document.category).filter(Boolean))).sort()
);
const filteredKnowledgeDocs = computed(() => {
  const query = knowledgeQuery.value.trim().toLowerCase();
  return officialKnowledgeDocs.value.filter((document) => {
    const categoryMatched = knowledgeCategory.value === "all" || document.category === knowledgeCategory.value;
    const text = `${document.title} ${document.category} ${document.content} ${document.sourceFile || ""} ${document.sourceSection || ""}`.toLowerCase();
    return categoryMatched && (!query || text.includes(query));
  });
});
const officialKnowledgeGroups = computed(() => {
  const serviceKeywords = ["路线", "门票", "开放", "贴士", "游览", "亲子", "交通", "服务"];
  const documents = filteredKnowledgeDocs.value;
  const guideDocs: KnowledgeDocument[] = [];
  const serviceDocs: KnowledgeDocument[] = [];
  documents.forEach((document) => {
    const text = `${document.title} ${document.category} ${document.content}`;
    if (serviceKeywords.some((keyword) => text.includes(keyword))) {
      serviceDocs.push(document);
    } else {
      guideDocs.push(document);
    }
  });
  if (!guideDocs.length || !serviceDocs.length) {
    const midpoint = Math.ceil(documents.length / 2);
    return [
      { key: "guide", label: "景区讲解资料", items: documents.slice(0, midpoint) },
      { key: "service", label: "游览服务资料", items: documents.slice(midpoint) }
    ];
  }
  return [
    { key: "guide", label: "景区讲解资料", items: guideDocs },
    { key: "service", label: "游览服务资料", items: serviceDocs }
  ];
});
const selectedKnowledge = computed(() => filteredKnowledgeDocs.value.find((item) => item.id === selectedKnowledgeId.value) || filteredKnowledgeDocs.value[0] || null);
const selectedSpot = computed(() => adminSpots.value.find((spot) => spot.id === selectedSpotId.value) || adminSpots.value[0] || null);
const spotImagePreview = computed(() =>
  imageForSpot({
    name: spotForm.value.name,
    tags: spotForm.value.tagsText.split(/[、,，\s]+/).filter(Boolean),
    image: spotForm.value.image,
    mapZone: spotForm.value.mapZone
  })
);
const lowConfidenceRecords = computed(() =>
  (chatRecords.value.length ? chatRecords.value : props.analytics.recentQuestions).filter((record) => Number(record.confidence || 0) < 0.65)
);
const visibleRecords = computed(() => (chatRecords.value.length ? chatRecords.value : props.analytics.recentQuestions).slice(0, 8));
const feedbackRecords = computed(() => visibleRecords.value.filter((record) => Number(record.satisfaction || 0) > 0));
const hotQuestionEntries = computed(() => props.analytics.hotQuestions.slice(0, 5));
const hotSpotEntries = computed(() => (props.analytics.hotSpots.length ? props.analytics.hotSpots : adminSpots.value.map((spot) => [spot.name, spot.popularity] as [string, number])).slice(0, 5));
const trendLabels = computed(() =>
  props.analytics.satisfactionTrend.length
    ? props.analytics.satisfactionTrend.slice(-6).map((item) => item.date)
    : ["D-5", "D-4", "D-3", "D-2", "D-1", "今天"]
);
const trendValues = computed(() =>
  props.analytics.satisfactionTrend.length
    ? props.analytics.satisfactionTrend.slice(-6).map((item) => Number(item.score.toFixed(2)))
    : [4.2, 4.3, 4.4, 4.5, 4.4, props.analytics.averageSatisfaction || 4.6]
);
const behaviorTrendLabels = computed(() => (behavior.value?.satisfactionTrend || []).slice(-6).map((item) => item.date));
const behaviorTrendValues = computed(() => (behavior.value?.satisfactionTrend || []).slice(-6).map((item) => Number(item.score || 0)));
const reportTrendLabels = computed(() => (behaviorTrendLabels.value.length ? behaviorTrendLabels.value : trendLabels.value));
const reportTrendValues = computed(() => (behaviorTrendValues.value.length ? behaviorTrendValues.value : trendValues.value));
const reportTrendTitle = computed(() => (behaviorTrendLabels.value.length ? "行业样本满意度走势" : "满意度走势"));
const sentimentLabels = computed(() => Object.keys(props.analytics.sentimentDistribution || {}).slice(0, 4));
const sentimentValues = computed(() => Object.values(props.analytics.sentimentDistribution || {}).map((value) => Number(value)).slice(0, 4));
const intentLabels = computed(() => Object.keys(props.analytics.intentDistribution || {}).slice(0, 5));
const intentValues = computed(() => Object.values(props.analytics.intentDistribution || {}).map((value) => Number(value)).slice(0, 5));
const screenBaseLoad = computed(() => props.analytics.todayServiceCount || props.analytics.questionCount || adminSpots.value.length * 12 || 1);
const derivedScreenCapacityRate = computed(() => clampNumber(52 + (screenBaseLoad.value % 36), 48, 92));
const derivedScreenPassIndex = computed(() => clampNumber(96 - Math.round(derivedScreenCapacityRate.value * 0.32), 58, 92));
const derivedScreenPatrolCoverage = computed(() => clampNumber(72 + (adminSpots.value.length % 18), 68, 96));
const derivedScreenDeviceHealth = computed(() => clampNumber(94 - Math.min(lowConfidenceRecords.value.length || props.analytics.unresolvedCount || 0, 18), 76, 98));
const screenCapacityRate = computed(() => operationMetric("capacity")?.value ?? derivedScreenCapacityRate.value);
const screenPassIndex = computed(() => operationMetric("passage")?.value ?? derivedScreenPassIndex.value);
const screenPatrolCoverage = computed(() => operationMetric("patrol")?.value ?? derivedScreenPatrolCoverage.value);
const screenDeviceHealth = computed(() => operationMetric("device")?.value ?? derivedScreenDeviceHealth.value);
const screenMetrics = computed(() => [
  operationMetricCard("capacity", "园区承载", screenCapacityRate.value, "%", "主游线当前负载", Users),
  operationMetricCard("passage", "通行指数", screenPassIndex.value, "分", "入口与主轴线顺畅度", Activity),
  operationMetricCard("patrol", "巡检覆盖", screenPatrolCoverage.value, "%", "重点片区巡检完成度", MapPinned),
  operationMetricCard("device", "设备健康", screenDeviceHealth.value, "%", "闸机、屏显与广播状态", Gauge)
]);
const hotSpotScoreMap = computed<Record<string, number>>(() =>
  Object.fromEntries(hotSpotEntries.value.map(([name, count]) => [name, Number(count) || 0]))
);
const topSpotMaxValue = computed(() =>
  Math.max(
    ...hotSpotEntries.value.map(([, count]) => Number(count) || 0),
    ...adminSpots.value.slice(0, 7).map((spot) => Number(spot.popularity) || 0),
    1
  )
);
const screenAssetCards = computed(() =>
  operationsOverview.value?.resources?.length
    ? operationsOverview.value.resources.slice(0, 3)
    : [
        { label: "闸机状态", value: `${screenPassIndex.value}%`, detail: "入口通行能力保持稳定" },
        { label: "广播联动", value: "正常", detail: "服务中心与主轴线可联动播报" },
        { label: "应急值守", value: "待命", detail: "高峰片区保留机动处置能力" }
      ]
);
const screenStationIcons = [Users, Route, ShieldAlert];
const screenAgentCards = computed(() =>
  operationsOverview.value?.stations?.length
    ? operationsOverview.value.stations.slice(0, 3).map((station, index) => ({
        name: station.name,
        role: station.role,
        status: station.status,
        icon: screenStationIcons[index] || ShieldAlert
      }))
    : [
        { name: "北入口", role: "入园通行", status: `负载 ${screenCapacityRate.value}%`, icon: Users },
        { name: "主轴线", role: "客流疏导", status: `通行 ${screenPassIndex.value} 分`, icon: Route },
        { name: "服务中心", role: "现场值守", status: `巡检 ${screenPatrolCoverage.value}%`, icon: ShieldAlert }
      ]
);
const screenTourFlowBars = computed(() => {
  const operationFlow = operationsOverview.value?.flow || [];
  const values = operationFlow.length
    ? operationFlow.slice(0, 5).map((item) => item.value)
    : [
        screenCapacityRate.value,
        screenPassIndex.value,
        screenPatrolCoverage.value,
        screenDeviceHealth.value,
        Math.max(56, 100 - screenCapacityRate.value + 38)
      ];
  const labels = operationFlow.length ? operationFlow.slice(0, 5).map((item) => item.label) : ["入口", "主轴", "巡检", "设备", "出口"];
  const max = Math.max(...values, 1);
  return labels.map((label, index) => ({
    label,
    value: formatNumber(values[index]),
    height: `${Math.max(16, Math.round((values[index] / max) * 92))}%`
  }));
});
const screenTrendPoints = computed(() => {
  const operationTrend = operationsOverview.value?.trend || [];
  const values = operationTrend.length
    ? operationTrend.map((item) => item.value)
    : [
        Math.max(42, screenCapacityRate.value - 18),
        Math.max(48, screenCapacityRate.value - 6),
        screenCapacityRate.value,
        Math.min(96, screenCapacityRate.value + 8),
        Math.max(52, screenCapacityRate.value - 10)
      ];
  const labels = operationTrend.length ? operationTrend.map((item) => item.label) : ["08:00", "10:00", "12:00", "14:00", "16:00"];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const width = 230;
  const height = 94;
  const range = Math.max(max - min, 0.1);
  const step = values.length > 1 ? width / (values.length - 1) : width;
  return values.map((value, index) => ({
    x: 12 + index * step,
    y: 12 + (1 - (value - min) / range) * (height - 24),
    value: Number(value).toFixed(1),
    label: labels[index] || ""
  }));
});
const screenTrendPolyline = computed(() => screenTrendPoints.value.map((point) => `${point.x},${point.y}`).join(" "));
const screenCore = computed(
  () =>
    operationsOverview.value?.core || {
      title: "灵山胜境",
      keyArea: "主轴线",
      dutyStatus: "正常",
      summary: "以园区承载、通行动线、设备健康和现场值守为核心视角，监控景区当日运行状态。"
    }
);
const screenScenicPins = computed(() => {
  const coordinates = [
    { x: 122, y: 274, labelX: -62, labelY: -32 },
    { x: 246, y: 212, labelX: -48, labelY: -34 },
    { x: 368, y: 144, labelX: 14, labelY: -32 },
    { x: 488, y: 218, labelX: 16, labelY: -24 },
    { x: 548, y: 118, labelX: -82, labelY: -32 },
    { x: 308, y: 318, labelX: 14, labelY: 6 }
  ];
  return adminSpots.value.slice(0, 6).map((spot, index) => {
    const point = coordinates[index] || coordinates[coordinates.length - 1];
    return {
      spot,
      x: point.x,
      y: point.y,
      labelX: point.labelX,
      labelY: point.labelY,
      label: spot.name.length > 5 ? `${spot.name.slice(0, 5)}...` : spot.name,
      radius: screenSpotRadius(spot),
      heat: screenSpotHeat(spot)
    };
  });
});
const screenRecentRows = computed(() =>
  operationsOverview.value?.briefings?.length
    ? operationsOverview.value.briefings.slice(0, 4).map((item) => ({
        question: item.message,
        intent: item.intent,
        confidence: item.value
      }))
    : [
        { question: "北入口闸机与安检口保持顺畅", intent: "入口", confidence: `${screenPassIndex.value}分` },
        { question: "主轴线客流进入可控高位", intent: "主游线", confidence: `${screenCapacityRate.value}%` },
        { question: "核心片区巡检任务按计划推进", intent: "巡检", confidence: `${screenPatrolCoverage.value}%` },
        { question: "广播、屏显、应急联动链路正常", intent: "设备", confidence: `${screenDeviceHealth.value}%` }
      ]
);
const knowledgeStats = computed(() => [
  { label: "启用知识", value: formatNumber(activeKnowledgeDocs.value.length), detail: "参与问答召回", icon: CheckCircle2 },
  { label: "资料包条目", value: formatNumber(officialKnowledgeDocs.value.length), detail: "官方与结构化来源", icon: FileText },
  { label: "待沉淀问题", value: formatNumber(lowConfidenceRecords.value.length), detail: "低置信问答", icon: MessageSquareText },
  { label: "资料分类", value: formatNumber(knowledgeCategories.value.length), detail: "当前可筛选类别", icon: Database }
]);
const personaSummaryCards = computed(() => [
  { label: "角色", value: personaForm.value.role || "未设置", detail: personaForm.value.name || "数字人" },
  { label: "语速", value: Number(personaForm.value.voiceSpeed || 1).toFixed(2), detail: "游客端播报节奏" },
  { label: "语调", value: Number(personaForm.value.voicePitch || 1).toFixed(2), detail: "语音情绪倾向" }
]);
const sourceTypeLabelMap: Record<string, string> = {
  manual: "手工录入",
  seed: "系统种子",
  official_docx: "官方 DOCX",
  behavior_excel: "行为 Excel",
  chat_draft: "问答沉淀"
};
const reportSampleLabels = computed(() => ["行业样本", "灵山命中"]);
const reportSampleValues = computed(() => [
  Math.max(behaviorSampleRows.value - behaviorMatchedRows.value, 0),
  behaviorMatchedRows.value
]);
const reportSuggestionItems = computed(() => {
  const topIntent = intentLabels.value[0] || "导览咨询";
  const topQuestion = compactText(hotQuestionEntries.value[0]?.[0] || "热门问答", 18);
  const lowConfidenceCount = lowConfidenceRecords.value.length;
  return [
    `优先补齐「${topQuestion}」等高频问题的答案口径，减少游客重复追问。`,
    `围绕「${topIntent}」集中优化导览话术，并同步到数字人开场问候。`,
    lowConfidenceCount
      ? `当前有 ${formatNumber(lowConfidenceCount)} 条低置信问答，建议转入知识库审核后再启用。`
      : "低置信问答处于可控范围，可继续关注新问题沉淀。"
  ];
});
const reportRefreshTime = new Date().toLocaleString("zh-CN", {
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit"
});
const reportRecordTotal = computed(() =>
  Math.max((chatRecords.value.length ? chatRecords.value : props.analytics.recentQuestions).length, props.analytics.questionCount || 0, 1)
);
const reportSentimentTotal = computed(() =>
  Object.values(props.analytics.sentimentDistribution || {}).reduce((total, value) => total + Number(value || 0), 0)
);
const reportPositiveCount = computed(() =>
  distributionCount(props.analytics.sentimentDistribution || {}, ["positive", "正", "积极", "好评", "满意", "愉悦", "开心"])
);
const reportPositiveRate = computed(() => {
  if (reportSentimentTotal.value > 0) return percentNumber(reportPositiveCount.value, reportSentimentTotal.value);
  return Math.round(clampNumber(Number(props.analytics.averageSatisfaction || 4.6) / 5, 0, 1) * 100);
});
const reportRiskRate = computed(() =>
  percentNumber(lowConfidenceRecords.value.length || props.analytics.unresolvedCount || 0, reportRecordTotal.value)
);
const reportSatisfactionPercent = computed(() =>
  Math.round(clampNumber(Number(props.analytics.averageSatisfaction || 4.6) / 5, 0, 1) * 100)
);
const reportCompositeScore = computed(() =>
  Math.round(
    clampNumber(
      reportSatisfactionPercent.value * 0.58 + reportPositiveRate.value * 0.26 + (100 - reportRiskRate.value) * 0.16,
      0,
      100
    )
  )
);
const reportTrendDelta = computed(() => {
  const values = reportTrendValues.value;
  if (values.length < 2) return 0;
  return Number((values[values.length - 1] - values[values.length - 2]).toFixed(2));
});
const reportTrendDeltaLabel = computed(() => `${reportTrendDelta.value >= 0 ? "+" : ""}${reportTrendDelta.value.toFixed(2)}`);
const reportScopeLabel = computed(() => {
  const range = behavior.value?.dateRange;
  if (range?.start && range?.end) return `${range.start} 至 ${range.end}`;
  return behavior.value?.analysisScope || "实时交互样本";
});
const reportSourceCards = computed(() => [
  {
    label: "反馈样本",
    value: formatNumber(feedbackRecords.value.length || visibleRecords.value.length),
    detail: "体验分析反馈条目",
    icon: MessageSquareText
  },
  {
    label: "行为样本",
    value: formatNumber(behaviorSampleRows.value),
    detail: "Excel 全量行业样本",
    icon: Database
  },
  {
    label: "关联样本",
    value: formatNumber(behaviorMatchedRows.value),
    detail: "关键词命中样本",
    icon: Radar
  }
]);
const reportKpiCards = computed(() => [
  {
    label: "满意评分",
    value: Number(props.analytics.averageSatisfaction || 4.6).toFixed(1),
    unit: "分",
    detail: `${reportSatisfactionPercent.value}% 满意度折算`,
    icon: Star
  },
  {
    label: "正向情绪",
    value: reportPositiveRate.value,
    unit: "%",
    detail: `${formatNumber(reportPositiveCount.value)} 条正向反馈`,
    icon: SmilePlus
  },
  {
    label: "体验风险",
    value: reportRiskRate.value,
    unit: "%",
    detail: "负向与待复核反馈占比",
    icon: ShieldAlert
  },
  {
    label: "样本命中",
    value: behaviorSampleRows.value ? percentNumber(behaviorMatchedRows.value, behaviorSampleRows.value) : 0,
    unit: "%",
    detail: "行业样本关联灵山",
    icon: Target
  }
]);
const reportExperienceFactors = computed(() => {
  const questionFocusScore = clampNumber(100 - reportRiskRate.value, 42, 98);
  const clarityScore = clampNumber(reportSatisfactionPercent.value - reportRiskRate.value * 0.18, 45, 98);
  const sampleScore = behaviorSampleRows.value
    ? clampNumber(percentNumber(behaviorMatchedRows.value, behaviorSampleRows.value) + 58, 48, 94)
    : 72;
  const revisitScore = clampNumber((reportPositiveRate.value + reportSatisfactionPercent.value) / 2, 45, 98);

  return [
    { label: "情绪体验", value: reportPositiveRate.value, icon: HeartPulse },
    { label: "表达清晰", value: Math.round(clarityScore), icon: BadgeCheck },
    { label: "痛点可控", value: Math.round(questionFocusScore), icon: ShieldAlert },
    { label: "复游意愿", value: Math.round(revisitScore || sampleScore), icon: Target }
  ];
});
const reportSentimentItems = computed(() => {
  const entries = Object.entries(props.analytics.sentimentDistribution || {})
    .map(([label, value]) => [label, Number(value || 0)] as [string, number])
    .filter(([, value]) => value > 0);
  const normalizedEntries: Array<[string, number]> = entries.length
    ? entries
    : [
        ["正向", reportPositiveRate.value],
        ["中性", Math.max(0, 100 - reportPositiveRate.value - reportRiskRate.value)],
        ["负向", reportRiskRate.value]
      ];
  const total = Math.max(normalizedEntries.reduce((sum, [, value]) => sum + value, 0), 1);

  return normalizedEntries.slice(0, 4).map(([label, value], index) => ({
    label,
    value: formatNumber(value),
    percent: `${percentNumber(value, total)}%`,
    tone: index === 1 ? "blue" : index === 2 ? "amber" : "green"
  }));
});
const reportAttentionItems = computed(() => {
  const intentEntries = Object.entries(props.analytics.intentDistribution || {})
    .map(([label, value]) => [label, Number(value || 0)] as [string, number])
    .filter(([, value]) => value > 0);
  const fallbackEntries = hotQuestionEntries.value.map(([label, value]) => [label, Number(value || 0)] as [string, number]);
  const entries = (intentEntries.length ? intentEntries : fallbackEntries).slice(0, 5);
  const max = Math.max(...entries.map(([, value]) => value), 1);

  return entries.map(([label, value], index) => ({
    label,
    value: formatNumber(value),
    percent: pressurePercent(value, max),
    tone: index % 3 === 1 ? "blue" : index % 3 === 2 ? "amber" : "green"
  }));
});
const reportRiskItems = computed(() => {
  const lowConfidenceCount = lowConfidenceRecords.value.length || props.analytics.unresolvedCount || 0;
  const topQuestion = hotQuestionEntries.value[0];
  const unresolvedPercent = percentNumber(lowConfidenceCount, reportRecordTotal.value);
  const matchedPercent = behaviorSampleRows.value ? percentNumber(behaviorMatchedRows.value, behaviorSampleRows.value) : 0;

  return [
    {
      label: "不满情绪",
      value: formatNumber(lowConfidenceCount),
      meta: lowConfidenceCount ? "需要关注反馈表达" : "稳定",
      percent: `${Math.max(unresolvedPercent, lowConfidenceCount ? 12 : 4)}%`,
      tone: lowConfidenceCount ? "warning" : "ok"
    },
    {
      label: "高频追问",
      value: topQuestion ? formatNumber(topQuestion[1]) : "0",
      meta: compactText(topQuestion?.[0] || "暂无集中问题", 20),
      percent: pressurePercent(Number(topQuestion?.[1] || 0), Math.max(props.analytics.questionCount || 1, Number(topQuestion?.[1] || 0), 1)),
      tone: topQuestion ? "watch" : "ok"
    },
    {
      label: "样本命中率",
      value: `${matchedPercent}%`,
      meta: "行业样本关联灵山",
      percent: `${Math.max(matchedPercent, 4)}%`,
      tone: matchedPercent >= 20 ? "ok" : "watch"
    },
    {
      label: "体验波动",
      value: reportTrendDeltaLabel.value,
      meta: "满意度环比变化",
      percent: `${Math.min(100, Math.max(8, Math.round(Math.abs(reportTrendDelta.value) * 40)))}%`,
      tone: reportTrendDelta.value < 0 ? "warning" : "ok"
    }
  ];
});
const reportRecentRows = computed(() =>
  visibleRecords.value.slice(0, 3).map((record) => ({
    question: record.question,
    intent: record.intent || "导览咨询",
    sentiment: record.sentiment || "neutral",
    score: record.satisfaction ? `${Number(record.satisfaction).toFixed(1)}分` : `${Math.round((record.confidence || 0) * 100)}%`,
    confidence: `${Math.round((record.confidence || 0) * 100)}%`
  }))
);
const reportTrendPoints = computed(() => {
  const values = reportTrendValues.value.length ? reportTrendValues.value : [4.2, 4.3, 4.4, 4.5, 4.6];
  const labels = reportTrendLabels.value.length ? reportTrendLabels.value : values.map((_, index) => `D-${values.length - index}`);
  const min = Math.min(...values, 3.8);
  const max = Math.max(...values, 5);
  const width = 340;
  const height = 128;
  const range = Math.max(max - min, 0.1);
  const step = values.length > 1 ? width / (values.length - 1) : width;

  return values.map((value, index) => ({
    x: 20 + index * step,
    y: 16 + (1 - (value - min) / range) * (height - 34),
    value: Number(value).toFixed(1),
    label: compactTrendLabel(labels[index] || "")
  }));
});
const reportTrendPolyline = computed(() => reportTrendPoints.value.map((point) => `${point.x},${point.y}`).join(" "));
const reportTrendAreaPath = computed(() => {
  const points = reportTrendPoints.value;
  if (!points.length) return "";
  const bottom = 132;
  return `M${points[0].x},${bottom} L${points.map((point) => `${point.x},${point.y}`).join(" L")} L${points[points.length - 1].x},${bottom} Z`;
});

function operationMetric(key: string) {
  return operationsOverview.value?.metrics?.find((metric) => metric.key === key) || null;
}

function operationMetricCard(key: string, label: string, fallbackValue: number, fallbackUnit: string, fallbackDetail: string, icon: Component) {
  const metric = operationMetric(key);
  return {
    label: metric?.label || label,
    value: metric?.value ?? fallbackValue,
    unit: metric?.unit || fallbackUnit,
    detail: metric?.detail || fallbackDetail,
    icon
  };
}

function screenSpotHeat(spot: ScenicSpot) {
  return hotSpotScoreMap.value[spot.name] ?? Number(spot.popularity || 0);
}

function screenSpotRadius(spot: ScenicSpot) {
  return 8 + Math.round((screenSpotHeat(spot) / topSpotMaxValue.value) * 10);
}

watch(
  () => props.spots,
  (spots) => {
    if (!adminSpots.value.length) adminSpots.value = spots;
  }
);

watch(
  () => props.persona,
  (persona) => {
    personaForm.value = clonePersona(persona);
  },
  { deep: true }
);

watch(adminToken, (token) => {
  rememberSessionAdminToken(token);
});

watch(filteredKnowledgeDocs, () => {
  syncSelectedKnowledge();
});

onMounted(() => {
  void reloadAdminData();
});

function sourceTypeLabel(sourceType?: string) {
  return sourceTypeLabelMap[sourceType || "manual"] || sourceType || "未知来源";
}

function setNotice(message: string) {
  notice.value = message;
  adminError.value = "";
}

function setError(message: string) {
  adminError.value = message;
  notice.value = "";
}

function setActionStatus(action: AdminAction, status: ActionStatus) {
  actionStatus[action] = status;
}

function isActionBusy(action: AdminAction) {
  return actionStatus[action] === "loading";
}

function actionStatusClass(action: AdminAction) {
  return `action-${actionStatus[action]}`;
}

function actionLabel(action: AdminAction, idle: string, loading: string, success: string, failed: string) {
  if (actionStatus[action] === "loading") return loading;
  if (actionStatus[action] === "success") return success;
  if (actionStatus[action] === "error") return failed;
  return idle;
}

function exportVisitorReport() {
  const exportedAt = new Date();
  const trendRows = reportTrendLabels.value.map((label, index) => [label, reportTrendValues.value[index] ?? 0]);
  const sentimentRows = sentimentLabels.value.map((label, index) => [label, sentimentValues.value[index] ?? 0]);
  const intentRows = intentLabels.value.map((label, index) => [label, intentValues.value[index] ?? 0]);
  const sampleRows = reportSampleLabels.value.map((label, index) => [label, formatNumber(reportSampleValues.value[index] || 0)]);
  const trendSource = reportTrendTitle.value.includes("行业") ? "长三角多景区行业样本" : "系统游客反馈";

  const content = [
    "# 体验分析报告",
    "",
    `导出时间：${exportedAt.toLocaleString("zh-CN")}`,
    "",
    "## 核心指标",
    "",
    markdownTable(
      ["指标", "数值", "说明"],
      [
        ["平均满意度", Number(props.analytics.averageSatisfaction || 4.6).toFixed(1), "系统交互评分"],
        ["低置信问题", formatNumber(props.analytics.unresolvedCount), "待知识沉淀"],
        ["全量行业样本", formatNumber(behaviorSampleRows.value), "长三角多景区"],
        ["灵山相关明细", formatNumber(behaviorMatchedRows.value), "关键词粗筛结果"]
      ]
    ),
    "",
    "## 满意度走势",
    "",
    `趋势来源：${trendSource}`,
    "",
    markdownTable(["时间", "满意度"], trendRows),
    "",
    "## 情绪分布",
    "",
    markdownTable(["情绪", "数量"], sentimentRows),
    "",
    "## 关注点分析",
    "",
    markdownTable(["关注点", "数量"], intentRows),
    "",
    "## 样本构成",
    "",
    markdownTable(["类别", "样本量"], sampleRows),
    ""
  ].join("\n");

  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `体验分析报告-${exportedAt.toISOString().slice(0, 10)}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setNotice("体验分析报告已导出。");
}

function syncSelectedKnowledge() {
  const documents = filteredKnowledgeDocs.value;
  if (!documents.length) {
    selectedKnowledgeId.value = null;
    return;
  }
  if (!selectedKnowledgeId.value || !documents.some((document) => document.id === selectedKnowledgeId.value)) {
    selectedKnowledgeId.value = documents[0].id;
  }
}

function mutationToken() {
  const token = adminToken.value.trim();
  if (!token) throw new Error("请先填写管理令牌。");
  return token;
}

function closeModal() {
  modal.value = null;
}

async function reloadAdminData() {
  busy.value = true;
  try {
    let token = "";
    try {
      token = mutationToken();
    } catch (error) {
      setError(error instanceof Error ? error.message : "请先填写管理令牌。");
      return false;
    }
    const results = await Promise.allSettled([
      apiGet<{ items: ScenicSpot[] }>("/api/admin/spots", token).then((spotData) => {
        adminSpots.value = spotData.items;
        if (!selectedSpotId.value || !spotData.items.some((spot) => spot.id === selectedSpotId.value)) {
          selectedSpotId.value = spotData.items[0]?.id || null;
        }
      }),
      apiGet<{ items: KnowledgeDocument[] }>("/api/admin/knowledge", token).then((knowledgeData) => {
        knowledgeDocs.value = knowledgeData.items;
        syncSelectedKnowledge();
      }),
      apiGet<{ items: ChatResponse[] }>("/api/admin/chat-records?limit=50", token).then((recordData) => {
        chatRecords.value = recordData.items;
      }),
      apiGet<BehaviorAnalytics>("/api/admin/analytics/behavior", token).then((behaviorResult) => {
        behaviorData.value = behaviorResult;
      }),
      apiGet<OperationsOverview>("/api/admin/operations/overview", token)
        .then((operationResult) => {
          operationsOverview.value = operationResult;
        })
        .catch(() => {
          operationsOverview.value = null;
      })
    ]);
    const failed = results.find((result): result is PromiseRejectedResult => result.status === "rejected");
    if (failed) {
      setError(failed.reason instanceof Error ? failed.reason.message : "后台数据加载失败");
      return false;
    }
    adminError.value = "";
    return true;
  } finally {
    busy.value = false;
  }
}

async function refreshAdminSnapshot() {
  const ok = await reloadAdminData();
  if (ok) emit("refresh");
  return ok;
}

async function refreshAll() {
  setActionStatus("refresh", "loading");
  const ok = await refreshAdminSnapshot();
  setActionStatus("refresh", ok ? "success" : "error");
  if (ok) {
    setNotice("后台数据已刷新。");
  }
}

async function reimportPublicData(importBehaviorRows = false) {
  const busyRef = importBehaviorRows ? importingBehaviorRows : importingPublicData;
  const action: AdminAction = importBehaviorRows ? "importBehavior" : "importPublic";
  busyRef.value = true;
  setActionStatus(action, "loading");
  try {
    const result = await apiPost<PublicDataImportResult>("/api/admin/public-data/reimport", { importBehaviorRows }, mutationToken());
    await refreshAdminSnapshot();
    const behaviorText =
      importBehaviorRows && typeof result.behaviorRecordCount === "number" ? `，${result.behaviorRecordCount} 条行为明细` : "";
    if (importBehaviorRows) {
      setNotice(result.imported ? `行为明细已刷新/重建：${result.spotCount} 个景点，${result.knowledgeCount} 条知识文档${behaviorText}。` : result.message);
    } else {
      setNotice(result.imported ? `资料包已重新导入：${result.spotCount} 个景点，${result.knowledgeCount} 条知识文档${behaviorText}。` : result.message);
    }
    setActionStatus(action, "success");
  } catch (error) {
    setError(error instanceof Error ? error.message : "资料包重新导入失败");
    setActionStatus(action, "error");
  } finally {
    busyRef.value = false;
  }
}

function openKnowledgeDetail(document?: KnowledgeDocument | null) {
  if (document) selectedKnowledgeId.value = document.id;
  if (selectedKnowledge.value) modal.value = "knowledgeDetail";
}

function openKnowledgeEditor(document?: KnowledgeDocument | null) {
  if (document) {
    selectedKnowledgeId.value = document.id;
    knowledgeForm.value = {
      id: document.id,
      title: document.title,
      category: document.category,
      content: document.content,
      status: document.status,
      sourceType: document.sourceType || "manual",
      sourceFile: document.sourceFile || "",
      sourceSection: document.sourceSection || ""
    };
  } else {
    selectedKnowledgeId.value = null;
    knowledgeForm.value = emptyKnowledgeForm();
  }
  modal.value = "knowledge";
}

function triggerKnowledgeUpload() {
  knowledgeUploadInput.value?.click();
}

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("资料文件读取失败"));
    reader.readAsDataURL(file);
  });
}

async function uploadKnowledgeDocx(file: File) {
  const dataUrl = await readFileAsDataUrl(file);
  const result = await apiPost<KnowledgeDocxUploadResult>(
    "/api/admin/knowledge/upload-docx",
    { fileName: file.name, dataUrl },
    mutationToken()
  );
  const importedIds = new Set(result.items.map((item) => item.id));
  const importedTitles = new Set(result.items.map((item) => item.title));
  knowledgeDocs.value = [
    ...result.items,
    ...knowledgeDocs.value.filter((item) => !importedIds.has(item.id) && !importedTitles.has(item.title))
  ];
  selectedKnowledgeId.value = result.items[0]?.id || null;
  syncSelectedKnowledge();
  const modeText = result.mode === "structured_spots" ? "按景点结构化解析" : "按正文分块解析";
  setNotice(`已导入 ${result.sourceFile}：${result.imported} 条知识，${result.paragraphCount} 段文本，${modeText}。`);
}

async function handleKnowledgeUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  setActionStatus("uploadKnowledge", "loading");
  try {
    if (/\.docx$/i.test(file.name)) {
      await uploadKnowledgeDocx(file);
      setActionStatus("uploadKnowledge", "success");
      return;
    }
    if (!/\.(txt|md|json)$/i.test(file.name)) {
      throw new Error("仅支持 .docx、.txt、.md、.json 资料文件。");
    }
    const text = await file.text();
    let title = file.name.replace(/\.[^.]+$/, "");
    let category = "上传资料";
    let content = text;
    let sourceSection = "";

    if (file.name.toLowerCase().endsWith(".json")) {
      const parsed = JSON.parse(text);
      const document = Array.isArray(parsed) ? parsed[0] : parsed;
      if (document && typeof document === "object") {
        title = String(document.title || title);
        category = String(document.category || category);
        content = String(document.content || document.answer || document.text || text);
        sourceSection = String(document.sourceSection || document.question || "");
      }
    }

    knowledgeForm.value = {
      ...emptyKnowledgeForm(),
      title,
      category,
      content,
      sourceType: "manual",
      sourceFile: file.name,
      sourceSection
    };
    selectedKnowledgeId.value = null;
    modal.value = "knowledge";
    setNotice(`已读取 ${file.name}，检查内容后点击保存知识。`);
    setActionStatus("uploadKnowledge", "success");
  } catch (error) {
    setError(error instanceof Error ? error.message : "资料文件读取失败");
    setActionStatus("uploadKnowledge", "error");
  } finally {
    input.value = "";
  }
}

function knowledgePayload() {
  return {
    title: knowledgeForm.value.title,
    category: knowledgeForm.value.category,
    content: knowledgeForm.value.content,
    status: knowledgeForm.value.status,
    sourceType: knowledgeForm.value.sourceType,
    sourceFile: knowledgeForm.value.sourceFile,
    sourceSection: knowledgeForm.value.sourceSection
  };
}

async function saveKnowledge() {
  saving.value = true;
  setActionStatus("saveKnowledge", "loading");
  try {
    const token = mutationToken();
    if (knowledgeForm.value.id) {
      await apiPut<KnowledgeDocument>(`/api/admin/knowledge/${knowledgeForm.value.id}`, knowledgePayload(), token);
    } else {
      const created = await apiPost<KnowledgeDocument>("/api/admin/knowledge", knowledgePayload(), token);
      selectedKnowledgeId.value = created.id;
      knowledgeForm.value.id = created.id;
    }
    closeModal();
    setNotice("知识文档已保存。");
    await refreshAdminSnapshot();
    setActionStatus("saveKnowledge", "success");
  } catch (error) {
    setError(error instanceof Error ? error.message : "知识文档保存失败");
    setActionStatus("saveKnowledge", "error");
  } finally {
    saving.value = false;
  }
}

async function deleteKnowledge() {
  if (!knowledgeForm.value.id || !window.confirm("确定删除这条知识文档？")) return;
  saving.value = true;
  setActionStatus("deleteKnowledge", "loading");
  try {
    await apiDelete<{ ok: boolean }>(`/api/admin/knowledge/${knowledgeForm.value.id}`, mutationToken());
    closeModal();
    setNotice("知识文档已删除。");
    await refreshAdminSnapshot();
    setActionStatus("deleteKnowledge", "success");
  } catch (error) {
    setError(error instanceof Error ? error.message : "知识文档删除失败");
    setActionStatus("deleteKnowledge", "error");
  } finally {
    saving.value = false;
  }
}

async function convertRecordToKnowledge(record: ChatResponse) {
  if (!record.id) return;
  convertingChatId.value = record.id;
  setActionStatus("convertChat", "loading");
  try {
    const document = await apiPost<KnowledgeDocument>("/api/admin/knowledge/from-chat", { chatId: record.id, status: "inactive" }, mutationToken());
    knowledgeDocs.value = [document, ...knowledgeDocs.value.filter((item) => item.id !== document.id)];
    openKnowledgeEditor(document);
    activeTab.value = "knowledge";
    setNotice("低置信问题已生成待核验知识文档。");
    setActionStatus("convertChat", "success");
  } catch (error) {
    setError(error instanceof Error ? error.message : "低置信问题转知识失败");
    setActionStatus("convertChat", "error");
  } finally {
    convertingChatId.value = "";
  }
}

function openSpotManager(spot?: ScenicSpot | null) {
  const target = spot || selectedSpot.value;
  if (target) {
    selectedSpotId.value = target.id;
    spotForm.value = {
      id: target.id,
      name: target.name,
      description: target.description,
      story: target.story,
      tagsText: target.tags.join("、"),
      image: target.image,
      openTime: target.openTime,
      duration: target.duration,
      popularity: target.popularity,
      location: target.location,
      mapZone: target.mapZone || "lingshan",
      mapX: target.mapX ?? null,
      mapY: target.mapY ?? null,
      lat: target.lat ?? null,
      lon: target.lon ?? null,
      verifiedLocation: Boolean(target.verifiedLocation),
      status: target.status || "active"
    };
  } else {
    spotForm.value = emptySpotForm();
  }
  modal.value = "spots";
}

function spotPayload() {
  return {
    name: spotForm.value.name,
    description: spotForm.value.description,
    story: spotForm.value.story,
    tags: spotForm.value.tagsText,
    image: spotForm.value.image,
    openTime: spotForm.value.openTime,
    duration: spotForm.value.duration,
    popularity: spotForm.value.popularity,
    location: spotForm.value.location,
    mapZone: spotForm.value.mapZone,
    mapX: spotForm.value.mapX,
    mapY: spotForm.value.mapY,
    lat: spotForm.value.lat,
    lon: spotForm.value.lon,
    verifiedLocation: spotForm.value.verifiedLocation,
    status: spotForm.value.status
  };
}

async function saveSpot() {
  saving.value = true;
  setActionStatus("saveSpot", "loading");
  try {
    const token = mutationToken();
    if (spotForm.value.id) {
      await apiPut<ScenicSpot>(`/api/admin/spots/${spotForm.value.id}`, spotPayload(), token);
    } else {
      const created = await apiPost<ScenicSpot>("/api/admin/spots", spotPayload(), token);
      selectedSpotId.value = created.id;
      spotForm.value.id = created.id;
    }
    closeModal();
    setNotice("景点点位已保存。");
    await refreshAdminSnapshot();
    setActionStatus("saveSpot", "success");
  } catch (error) {
    setError(error instanceof Error ? error.message : "景点保存失败");
    setActionStatus("saveSpot", "error");
  } finally {
    saving.value = false;
  }
}

async function deactivateSpot() {
  if (!spotForm.value.id || !window.confirm("确定停用这个景点？")) return;
  saving.value = true;
  setActionStatus("deleteSpot", "loading");
  try {
    await apiDelete<{ ok: boolean }>(`/api/admin/spots/${spotForm.value.id}`, mutationToken());
    closeModal();
    setNotice("景点已停用。");
    await refreshAdminSnapshot();
    setActionStatus("deleteSpot", "success");
  } catch (error) {
    setError(error instanceof Error ? error.message : "景点停用失败");
    setActionStatus("deleteSpot", "error");
  } finally {
    saving.value = false;
  }
}

async function savePersona() {
  saving.value = true;
  setActionStatus("savePersona", "loading");
  try {
    await apiPut<Persona>("/api/admin/persona", personaForm.value, mutationToken());
    setNotice("数字人配置已保存，游客端会同步更新。");
    await refreshAdminSnapshot();
    setActionStatus("savePersona", "success");
  } catch (error) {
    setError(error instanceof Error ? error.message : "数字人配置保存失败");
    setActionStatus("savePersona", "error");
  } finally {
    saving.value = false;
  }
}

  return {
    actionLabel,
    actionStatus,
    actionStatusClass,
    activeKnowledgeDocs,
    activeTab,
    Activity,
    adminError,
    adminSpots,
    adminTabs,
    adminToken,
    apiDelete,
    apiGet,
    apiPost,
    apiPut,
    BadgeCheck,
    behavior,
    behaviorData,
    behaviorMatchedRows,
    behaviorSampleRows,
    behaviorTrendLabels,
    behaviorTrendValues,
    Bot,
    busy,
    chatRecords,
    CheckCircle2,
    clampNumber,
    Clock3,
    clonePersona,
    closeModal,
    compactText,
    compactTrendLabel,
    computed,
    convertingChatId,
    convertRecordToKnowledge,
    Database,
    deactivateSpot,
    deleteKnowledge,
    derivedScreenCapacityRate,
    derivedScreenDeviceHealth,
    derivedScreenPassIndex,
    derivedScreenPatrolCoverage,
    digitalHumanAvatar,
    digitalHumanAvatarFallback,
    distributionCount,
    Download,
    emptyKnowledgeForm,
    emptySpotForm,
    exportVisitorReport,
    fallbackKnowledgeDocuments,
    feedbackRecords,
    FileText,
    filteredKnowledgeDocs,
    formatNumber,
    Gauge,
    handleKnowledgeUpload,
    HeartPulse,
    hotQuestionEntries,
    hotSpotEntries,
    hotSpotScoreMap,
    imageForSpot,
    importingBehaviorRows,
    importingPublicData,
    intentLabels,
    intentValues,
    isActionBusy,
    knowledgeCategories,
    knowledgeCategory,
    knowledgeDocs,
    knowledgeForm,
    knowledgePayload,
    knowledgeQuery,
    knowledgeStats,
    knowledgeUploadInput,
    lowConfidenceRecords,
    MapPinned,
    markdownTable,
    MessageSquareText,
    MetricChart,
    modal,
    mutationToken,
    notice,
    officialKnowledgeDocs,
    officialKnowledgeGroups,
    onMounted,
    openKnowledgeDetail,
    openKnowledgeEditor,
    openSpotManager,
    operationMetric,
    operationMetricCard,
    operationsOverview,
    percentNumber,
    personaForm,
    personaSummaryCards,
    photoOptions,
    pressurePercent,
    Radar,
    reactive,
    readFileAsDataUrl,
    readInitialAdminTab,
    readSessionAdminToken,
    ref,
    refreshAdminSnapshot,
    refreshAll,
    RefreshCw,
    reimportPublicData,
    reloadAdminData,
    rememberSessionAdminToken,
    reportAttentionItems,
    reportCompositeScore,
    reportExperienceFactors,
    reportKpiCards,
    reportPositiveCount,
    reportPositiveRate,
    reportRecentRows,
    reportRecordTotal,
    reportRefreshTime,
    reportRiskItems,
    reportRiskRate,
    reportSampleLabels,
    reportSampleValues,
    reportSatisfactionPercent,
    reportScopeLabel,
    reportSentimentItems,
    reportSentimentTotal,
    reportSourceCards,
    reportSuggestionItems,
    reportTrendAreaPath,
    reportTrendDelta,
    reportTrendDeltaLabel,
    reportTrendLabels,
    reportTrendPoints,
    reportTrendPolyline,
    reportTrendTitle,
    reportTrendValues,
    Route,
    Save,
    saveKnowledge,
    savePersona,
    saveSpot,
    saving,
    screenAgentCards,
    screenAssetCards,
    screenBaseLoad,
    screenCapacityRate,
    screenCore,
    screenDeviceHealth,
    screenMetrics,
    screenPassIndex,
    screenPatrolCoverage,
    screenRecentRows,
    screenScenicPins,
    screenSpotHeat,
    screenSpotRadius,
    screenStationIcons,
    screenTourFlowBars,
    screenTrendPoints,
    screenTrendPolyline,
    selectedKnowledge,
    selectedKnowledgeId,
    selectedSpot,
    selectedSpotId,
    sentimentLabels,
    sentimentValues,
    setActionStatus,
    setError,
    setNotice,
    ShieldAlert,
    SmilePlus,
    sourceTypeLabel,
    sourceTypeLabelMap,
    spotForm,
    spotImagePreview,
    spotPayload,
    spotPhotoChoices,
    Star,
    syncSelectedKnowledge,
    Target,
    topSpotMaxValue,
    Trash2,
    trendLabels,
    trendValues,
    triggerKnowledgeUpload,
    Upload,
    uploadKnowledgeDocx,
    useFallbackImage,
    Users,
    visibleRecords,
    watch,
    X,
    Zap
  };
}
