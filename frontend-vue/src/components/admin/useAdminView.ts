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
import { applyLiveTalkingPreset, personaPresetLocked } from "../../composables/useLiveTalkingAvatar";
import { apiDelete, apiGet, apiPost, apiPut } from "../../api";
import { buildPresetSummary, presetLabel, resolvePresetFromPersona } from "../../config/liveTalkingPresets";
import { clearPersonaDraft, loadPersonaDraft, savePersonaDraft } from "../../utils/personaDraft";
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
  mergeNumericDistributions,
  percentNumber,
  pressurePercent,
  readInitialAdminTab,
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
  { key: "screen", label: "数据大屏概览", icon: Activity },
  { key: "knowledge", label: "知识库管理", icon: FileText },
  { key: "persona", label: "数字人形象管理", icon: Bot },
  { key: "report", label: "游客感受度报告", icon: Star }
];

const activeTab = ref<AdminTab>(readInitialAdminTab());
const modal = ref<ModalName>(null);
const adminSpots = ref<ScenicSpot[]>(props.spots);
const knowledgeDocs = ref<KnowledgeDocument[]>(fallbackKnowledgeDocuments);
const analyticsData = ref<AnalyticsOverview>(props.analytics);
const analyticsSnapshot = computed(() => analyticsData.value || props.analytics);
const chatRecords = ref<ChatResponse[]>(analyticsSnapshot.value.recentQuestions || []);
const behaviorData = ref<BehaviorAnalytics | null>(analyticsSnapshot.value.behaviorBaseline || null);
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
const behaviorUploadInput = ref<HTMLInputElement | null>(null);
const knowledgeForm = ref<KnowledgeForm>(emptyKnowledgeForm());
const spotForm = ref<SpotForm>(emptySpotForm());

function bootstrapPersonaForm(): Persona {
  const draft = loadPersonaDraft();
  if (draft) {
    personaPresetLocked.value = true;
    applyLiveTalkingPreset(resolvePresetFromPersona(draft));
    return clonePersona(draft);
  }
  return clonePersona(props.persona);
}

const personaForm = ref<Persona>(bootstrapPersonaForm());
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

const behavior = computed(() => behaviorData.value || analyticsSnapshot.value.behaviorBaseline);
const knowledgeEvaluation = computed(() => analyticsSnapshot.value.knowledgeEvaluation);
const behaviorSampleRows = computed(() => behavior.value?.rowCount || behavior.value?.behaviorRecordCount || 0);
const behaviorMatchedRows = computed(() => behavior.value?.matchedScenicRows || 0);
const activeKnowledgeDocs = computed(() => knowledgeDocs.value.filter((item) => item.status === "active"));
function matchesKnowledgeFilter(document: KnowledgeDocument) {
  const query = knowledgeQuery.value.trim().toLowerCase();
  const categoryMatched = knowledgeCategory.value === "all" || document.category === knowledgeCategory.value;
  const text = `${document.title} ${document.category} ${document.content} ${document.sourceFile || ""} ${document.sourceSection || ""}`.toLowerCase();
  return categoryMatched && (!query || text.includes(query));
}

const officialKnowledgeDocs = computed(() => knowledgeDocs.value);
const knowledgeCategories = computed(() =>
  Array.from(new Set(knowledgeDocs.value.map((document) => document.category).filter(Boolean))).sort()
);
const filteredKnowledgeDocs = computed(() => knowledgeDocs.value.filter(matchesKnowledgeFilter));

function isServiceKnowledgeDocument(document: KnowledgeDocument) {
  const title = document.title || "";
  const category = document.category || "";
  const sourceSection = document.sourceSection || "";
  const primaryText = `${title} ${category} ${sourceSection}`;
  const guideKeywords = ["景区讲解", "景点讲解", "讲解", "文化", "历史", "佛教", "景观", "地标"];
  const serviceKeywords = ["路线", "门票", "票务", "开放", "贴士", "游览服务", "交通", "停车", "安全", "政策", "研学", "亲子", "预约", "时间"];

  if (guideKeywords.some((keyword) => title.includes(keyword) || category.includes(keyword))) return false;
  return serviceKeywords.some((keyword) => primaryText.includes(keyword));
}

const officialKnowledgeGroups = computed(() => {
  const documents = filteredKnowledgeDocs.value;
  const guideDocs: KnowledgeDocument[] = [];
  const serviceDocs: KnowledgeDocument[] = [];
  documents.forEach((document) => {
    if (isServiceKnowledgeDocument(document)) {
      serviceDocs.push(document);
    } else {
      guideDocs.push(document);
    }
  });
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
const analyticsSourceMode = computed(() => String(analyticsSnapshot.value.dataSource?.mode || ""));
const usesSyntheticAnalytics = computed(() => ["fallback_demo", "demo_sample"].includes(analyticsSourceMode.value));
const reportUsesSyntheticAnalytics = usesSyntheticAnalytics;
const lowConfidenceRecords = computed(() =>
  (chatRecords.value.length ? chatRecords.value : analyticsSnapshot.value.recentQuestions).filter((record) => Number(record.confidence || 0) < 0.65)
);
const visibleRecords = computed(() => (chatRecords.value.length ? chatRecords.value : analyticsSnapshot.value.recentQuestions).slice(0, 8));
const reportVisibleRecords = computed(() => (reportUsesSyntheticAnalytics.value ? [] : visibleRecords.value));

function isDeepseekRecord(record: ChatResponse) {
  const modelRef = record.sourceRefs?.find((ref) => ref.type === "model");
  const providerText = `${record.llmProvider || ""} ${record.modelName || ""} ${modelRef?.category || ""} ${modelRef?.title || ""}`.toLowerCase();
  return providerText.includes("deepseek");
}

function shouldShowRecordConfidence(record: ChatResponse) {
  return !isDeepseekRecord(record);
}

function recordConfidenceLabel(record: ChatResponse) {
  return shouldShowRecordConfidence(record) ? `${Math.round((record.confidence || 0) * 100)}%` : "";
}

const reportLowConfidenceRecords = computed(() => reportVisibleRecords.value.filter((record) => shouldShowRecordConfidence(record) && Number(record.confidence || 0) < 0.65));
const feedbackRecords = computed(() => reportVisibleRecords.value.filter((record) => Number(record.satisfaction || 0) > 0));
const reportQuestionTotal = computed(() => (reportUsesSyntheticAnalytics.value ? 0 : Number(analyticsSnapshot.value.questionCount || 0)));
const reportFeedbackTotal = computed(() =>
  reportUsesSyntheticAnalytics.value ? 0 : Number(analyticsSnapshot.value.feedbackCount ?? feedbackRecords.value.length ?? 0)
);
const hotQuestionEntries = computed(() => analyticsSnapshot.value.hotQuestions.slice(0, 5));
const hotSpotEntries = computed(() => {
  if (usesSyntheticAnalytics.value) return [];
  const analyticsHotSpots = (analyticsSnapshot.value.hotSpots || [])
    .map(([name, count]) => [name, Number(count || 0)] as [string, number])
    .filter(([, count]) => count > 0);
  if (analyticsHotSpots.length) return analyticsHotSpots.slice(0, 5);
  return (behavior.value?.topAttractions || [])
    .map(([name, count]) => [String(name), Number(count || 0)] as [string, number])
    .filter(([, count]) => count > 0)
    .slice(0, 5);
});
const behaviorTrendLabels = computed(() => (behavior.value?.satisfactionTrend || []).slice(-6).map((item) => item.date));
const behaviorTrendValues = computed(() => (behavior.value?.satisfactionTrend || []).slice(-6).map((item) => Number(item.score || 0)));
const trendLabels = computed(() =>
  behaviorTrendLabels.value.length
    ? behaviorTrendLabels.value
    : analyticsSnapshot.value.satisfactionTrend.slice(-6).map((item) => item.date)
);
const trendValues = computed(() =>
  behaviorTrendValues.value.length
    ? behaviorTrendValues.value
    : analyticsSnapshot.value.satisfactionTrend.slice(-6).map((item) => Number(item.score.toFixed(2)))
);
const reportInteractionTrend = computed(() =>
  reportUsesSyntheticAnalytics.value
    ? []
    : (analyticsSnapshot.value.satisfactionTrend || []).filter((item) => Number(item.count || 0) > 0 || Number(item.score || 0) > 0).slice(-6)
);
const reportTrendLabels = computed(() =>
  behaviorTrendLabels.value.length ? behaviorTrendLabels.value : reportInteractionTrend.value.map((item) => item.date)
);
const reportTrendValues = computed(() =>
  behaviorTrendValues.value.length ? behaviorTrendValues.value : reportInteractionTrend.value.map((item) => Number(item.score || 0))
);
const reportTrendTitle = computed(() => (behaviorTrendLabels.value.length ? "灵山游客满意度走势" : "真实反馈满意度走势"));
const reportSentimentDistribution = computed<Record<string, number>>(() => {
  if (reportUsesSyntheticAnalytics.value) return {};
  const interactionDistribution = analyticsSnapshot.value.sentimentDistribution || {};
  const satisfactionDistribution = behavior.value?.satisfactionSentimentDistribution || {};
  return mergeNumericDistributions(interactionDistribution, satisfactionDistribution);
});
const sentimentLabels = computed(() => Object.keys(reportSentimentDistribution.value).slice(0, 4));
const sentimentValues = computed(() => Object.values(reportSentimentDistribution.value).map((value) => Number(value)).slice(0, 4));
const intentLabels = computed(() => Object.keys(analyticsSnapshot.value.intentDistribution || {}).slice(0, 5));
const intentValues = computed(() => Object.values(analyticsSnapshot.value.intentDistribution || {}).map((value) => Number(value)).slice(0, 5));
const screenHasBehaviorData = computed(() => !usesSyntheticAnalytics.value && behaviorSampleRows.value > 0);
const screenBehaviorAverageSatisfaction = computed(() => Number(behavior.value?.averageSatisfaction || 0));
const screenBehaviorSatisfactionPercent = computed(() => Math.round(clampNumber(screenBehaviorAverageSatisfaction.value / 5, 0, 1) * 100));
const screenBaseLoad = computed(() => behaviorSampleRows.value || analyticsSnapshot.value.todayServiceCount || analyticsSnapshot.value.questionCount || analyticsSnapshot.value.routeCount || 1);
const screenQuestionTotal = computed(() => (usesSyntheticAnalytics.value ? 0 : analyticsSnapshot.value.questionCount || 0));
const screenRouteTotal = computed(() => (usesSyntheticAnalytics.value ? 0 : analyticsSnapshot.value.routeCount || 0));
const screenTodayServiceCount = computed(() => (usesSyntheticAnalytics.value ? 0 : analyticsSnapshot.value.todayServiceCount || 0));
const screenWeekServiceCount = computed(() => (usesSyntheticAnalytics.value ? 0 : analyticsSnapshot.value.weekServiceCount || 0));
const screenKnowledgeReadyRate = computed(() => (usesSyntheticAnalytics.value ? 0 : knowledgeEvaluation.value?.accuracyRate ?? 0));
const screenCapacityRate = computed(() =>
  screenHasBehaviorData.value
    ? percentNumber(behaviorMatchedRows.value, behaviorSampleRows.value)
    : screenWeekServiceCount.value || screenTodayServiceCount.value
    ? percentNumber(screenTodayServiceCount.value, Math.max(screenWeekServiceCount.value, screenTodayServiceCount.value, 1))
    : 0
);
const screenPassIndex = computed(() =>
  screenHasBehaviorData.value
    ? screenBehaviorSatisfactionPercent.value
    : Math.round(clampNumber(Number(analyticsSnapshot.value.averageSatisfaction || 0) / 5, 0, 1) * 100)
);
const screenPatrolCoverage = computed(() => screenKnowledgeReadyRate.value);
const screenDeviceHealth = computed(() => Number(operationMetric("device")?.value ?? 0));
const derivedScreenCapacityRate = screenCapacityRate;
const derivedScreenPassIndex = screenPassIndex;
const derivedScreenPatrolCoverage = screenPatrolCoverage;
const derivedScreenDeviceHealth = screenDeviceHealth;
const screenMetricIconMap: Record<string, Component> = {
  sample: Database,
  satisfaction: Star,
  stay: Clock3,
  matched: Radar,
  capacity: Users,
  passage: Route,
  patrol: ShieldAlert,
  device: Gauge,
  questions: MessageSquareText,
  routes: Route,
  today: Users,
  week: Activity
};
const screenOperationMetrics = computed(() => (operationsOverview.value?.available ? operationsOverview.value.metrics || [] : []));
const screenMetrics = computed(() => [
  ...(screenOperationMetrics.value.length
    ? screenOperationMetrics.value.slice(0, 4).map((metric) => ({
        label: metric.label,
        value: formatScreenMetricValue(metric.value),
        unit: metric.unit,
        detail: metric.detail,
        icon: screenMetricIconMap[metric.key] || Activity
      }))
    : screenHasBehaviorData.value
    ? [
        {
          label: "行为样本",
          value: formatNumber(behaviorSampleRows.value),
          unit: "条",
          detail: "behavior_visit_record 已入库",
          icon: Database
        },
        {
          label: "关联样本",
          value: formatNumber(behaviorMatchedRows.value),
          unit: "条",
          detail: `${screenCapacityRate.value}% 关键词命中灵山`,
          icon: Radar
        },
        {
          label: "平均停留",
          value: Number(behavior.value?.averageStayDuration || 0).toFixed(1),
          unit: "小时",
          detail: `平均同行 ${Number(behavior.value?.averageGroupSize || 0).toFixed(1)} 人`,
          icon: Clock3
        },
        {
          label: "样本满意",
          value: screenBehaviorAverageSatisfaction.value.toFixed(1),
          unit: "分",
          detail: `${screenPassIndex.value}% 满意度折算`,
          icon: Star
        }
      ]
    : [
        {
          label: "今日服务",
          value: formatNumber(screenTodayServiceCount.value),
          unit: "人次",
          detail: "今日问答与路线服务",
          icon: Users
        },
        {
          label: "本周服务",
          value: formatNumber(screenWeekServiceCount.value),
          unit: "人次",
          detail: "本周累计服务触达",
          icon: Activity
        },
        {
          label: "问答总量",
          value: formatNumber(screenQuestionTotal.value),
          unit: "条",
          detail: "游客咨询记录沉淀",
          icon: MessageSquareText
        },
        {
          label: "满意评分",
          value: Number(analyticsSnapshot.value.averageSatisfaction || 0) > 0 ? Number(analyticsSnapshot.value.averageSatisfaction).toFixed(1) : "暂无",
          unit: "",
          detail: Number(analyticsSnapshot.value.averageSatisfaction || 0) > 0 ? `${screenPassIndex.value}% 满意度折算` : "暂无真实评分反馈",
          icon: Star
        }
      ])
]);
const hotSpotScoreMap = computed<Record<string, number>>(() =>
  Object.fromEntries(hotSpotEntries.value.map(([name, count]) => [name, Number(count) || 0]))
);
const topSpotMaxValue = computed(() =>
  Math.max(
    ...hotSpotEntries.value.map(([, count]) => Number(count) || 0),
    1
  )
);
const screenAssetCards = computed(() =>
  usesSyntheticAnalytics.value
    ? []
    : screenHasBehaviorData.value
    ? [
        {
          label: "行为数据库",
          value: formatNumber(behaviorSampleRows.value),
          detail: behavior.value?.sampleSourceFile || behavior.value?.dataSource?.file || "已导入行为 Excel"
        },
        {
          label: "满意度走势",
          value: `${behaviorTrendValues.value.length} 期`,
          detail: behavior.value?.dateRange?.start && behavior.value?.dateRange?.end ? `${behavior.value.dateRange.start} 至 ${behavior.value.dateRange.end}` : "按 visit_date 月度聚合"
        },
        {
          label: "知识准确率",
          value: `${screenKnowledgeReadyRate.value}%`,
          detail: `${knowledgeEvaluation.value?.passedQuestionCount ?? 0}/${knowledgeEvaluation.value?.testedQuestionCount ?? 0} 标准题通过`
        }
      ]
    : [
        {
          label: "知识准确率",
          value: `${screenKnowledgeReadyRate.value}%`,
          detail: `${knowledgeEvaluation.value?.passedQuestionCount ?? 0}/${knowledgeEvaluation.value?.testedQuestionCount ?? 0} 标准题通过`
        },
        {
          label: "启用资料",
          value: formatNumber(analyticsSnapshot.value.knowledgeCount || 0),
          detail: "后端 active 知识文档统计"
        },
        {
          label: "待沉淀问答",
          value: formatNumber(lowConfidenceRecords.value.length || analyticsSnapshot.value.unresolvedCount || 0),
          detail: "低置信问题进入知识库审核"
        }
      ]
);
const screenStationIcons = [Users, Route, ShieldAlert];
const screenAgentCards = computed(() => {
  if (usesSyntheticAnalytics.value) return [];
  const stations = operationsOverview.value?.available ? operationsOverview.value.stations || [] : [];
  if (stations.length) {
    return stations.slice(0, 3).map((station, index) => ({
      name: station.name,
      role: station.role,
      status: station.status,
      icon: screenStationIcons[index % screenStationIcons.length]
    }));
  }
  return screenHasBehaviorData.value
    ? [
        {
          name: "行为导入",
          role: "Excel 入库",
          status: `${formatNumber(behaviorSampleRows.value)} 条`,
          icon: Database
        },
        {
          name: "数字人问答",
          role: "文本/语音咨询",
          status: `累计 ${formatNumber(screenQuestionTotal.value)} 条`,
          icon: Bot
        },
        {
          name: "路线推荐",
          role: "个性化游线",
          status: `生成 ${formatNumber(screenRouteTotal.value)} 条`,
          icon: Route
        }
      ]
    : [
        {
          name: "数字人问答",
          role: "文本/语音咨询",
          status: `累计 ${formatNumber(screenQuestionTotal.value)} 条`,
          icon: Bot
        },
        {
          name: "路线推荐",
          role: "个性化游线",
          status: `生成 ${formatNumber(screenRouteTotal.value)} 条`,
          icon: Route
        },
        {
          name: "语音播报",
          role: "讲解与答复播报",
          status: props.capabilities.interaction.voiceOutput ? "服务可用" : "浏览器兜底",
          icon: Zap
        }
      ];
});
const screenTourFlowBars = computed(() => {
  const operationFlow = operationsOverview.value?.available ? operationsOverview.value.flow || [] : [];
  if (operationFlow.length) {
    const entries = operationFlow
      .map((item) => [item.label, Number(item.value || 0)] as [string, number])
      .filter(([, value]) => value > 0)
      .slice(0, 5);
    const max = Math.max(...entries.map(([, value]) => value), 1);
    return entries.map(([label, value]) => ({
      label: compactText(label, 5),
      value: formatNumber(value),
      height: `${Math.max(16, Math.round((value / max) * 92))}%`
    }));
  }
  const behaviorEntries = (behavior.value?.typeDistribution?.length ? behavior.value.typeDistribution : behavior.value?.topAttractions || [])
    .map(([label, value]) => [label, Number(value || 0)] as [string, number])
    .filter(([, value]) => value > 0);
  if (behaviorEntries.length) {
    const entries = behaviorEntries.slice(0, 5);
    const max = Math.max(...entries.map(([, value]) => value), 1);
    return entries.map(([label, value]) => ({
      label: compactText(label, 5),
      value: formatNumber(value),
      height: `${Math.max(16, Math.round((value / max) * 92))}%`
    }));
  }
  const intentEntries = Object.entries(analyticsSnapshot.value.intentDistribution || {})
    .map(([label, value]) => [label, Number(value || 0)] as [string, number])
    .filter(([, value]) => value > 0);
  const preferenceEntries = Object.entries(analyticsSnapshot.value.preferences || {})
    .map(([label, value]) => [label, Number(value || 0)] as [string, number])
    .filter(([, value]) => value > 0);
  const fallbackEntries = hotQuestionEntries.value.map(([label, value]) => [compactText(label, 6), Number(value || 0)] as [string, number]);
  const entries = (intentEntries.length ? intentEntries : preferenceEntries.length ? preferenceEntries : fallbackEntries).slice(0, 5);
  const finalEntries: Array<[string, number]> = entries.length ? entries : [];
  if (!finalEntries.length) return [];
  const values = finalEntries.map(([, value]) => value);
  const labels = finalEntries.map(([label]) => compactText(label, 5));
  const max = Math.max(...values, 1);
  return labels.map((label, index) => ({
    label,
    value: formatNumber(values[index]),
    height: `${Math.max(16, Math.round((values[index] / max) * 92))}%`
  }));
});
const screenTrendPoints = computed(() => {
  const operationTrend = operationsOverview.value?.available ? operationsOverview.value.trend || [] : [];
  const values = operationTrend.length ? operationTrend.map((item) => Number(item.value || 0)) : trendValues.value;
  const labels = operationTrend.length ? operationTrend.map((item) => item.label) : trendLabels.value;
  if (!values.length) return [];
  const usesPercentScale = values.some((value) => value > 10);
  const min = usesPercentScale ? Math.max(0, Math.min(...values) - 10) : Math.min(...values, 3.8);
  const max = usesPercentScale ? Math.min(100, Math.max(...values) + 10) : Math.max(...values, 5);
  const width = 230;
  const height = 94;
  const range = Math.max(max - min, 0.1);
  const step = values.length > 1 ? width / (values.length - 1) : width;
  return values.map((value, index) => ({
    x: 12 + index * step,
    y: 12 + (1 - (value - min) / range) * (height - 24),
    value: Number(value).toFixed(1),
    label: compactTrendLabel(labels[index] || "")
  }));
});
const screenTrendPolyline = computed(() => screenTrendPoints.value.map((point) => `${point.x},${point.y}`).join(" "));
const screenCore = computed(
  () => {
    if (usesSyntheticAnalytics.value) {
      return {
        title: "暂无真实数据",
        keyArea: "后端未连接",
        dutyStatus: "等待接口数据",
        summary: "后端分析接口未返回真实记录，数据大屏不展示演示样本。"
      };
    }
    if (operationsOverview.value?.available && operationsOverview.value.core) {
      return operationsOverview.value.core;
    }
    if (screenHasBehaviorData.value) {
      const topAttraction = behavior.value?.topAttractions?.[0]?.[0] || "暂无热点";
      const dateRange = behavior.value?.dateRange;
      const rangeText = dateRange?.start && dateRange?.end ? `${dateRange.start} 至 ${dateRange.end}` : "当前导入周期";
      return {
        title: "游客行为数据库",
        keyArea: compactText(topAttraction, 12),
        dutyStatus: `已入库 ${formatNumber(behaviorSampleRows.value)} 条`,
        summary: `${rangeText} 共导入 ${formatNumber(behaviorSampleRows.value)} 条游客行为记录，满意度均值 ${screenBehaviorAverageSatisfaction.value.toFixed(2)} 分，已同步驱动大屏和体验报告。`
      };
    }
    const topIntent = intentLabels.value[0] || hotQuestionEntries.value[0]?.[0] || "";
    const pendingCount = lowConfidenceRecords.value.length || analyticsSnapshot.value.unresolvedCount || 0;
    if (!screenQuestionTotal.value && !screenRouteTotal.value && !screenTodayServiceCount.value && !screenWeekServiceCount.value && !pendingCount) {
      return {
        title: "AI 数字人服务中枢",
        keyArea: "暂无热点",
        dutyStatus: "等待真实记录",
        summary: "暂无真实问答、路线或评分记录；新增游客交互后，大屏会按后端统计刷新。"
      };
    }
    return {
      title: "AI 数字人服务中枢",
      keyArea: compactText(topIntent || "暂无热点", 12),
      dutyStatus: pendingCount ? `${formatNumber(pendingCount)} 条待沉淀` : "知识库稳定",
      summary: `本周承接 ${formatNumber(screenWeekServiceCount.value)} 人次服务，联动问答、路线推荐、景点讲解与反馈分析，持续沉淀游客真实关注点。`
    };
  }
);
const screenScenicPins = computed(() => {
  if (usesSyntheticAnalytics.value) return [];
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
  usesSyntheticAnalytics.value
    ? []
    : operationsOverview.value?.available && operationsOverview.value.briefings?.length
    ? operationsOverview.value.briefings.slice(0, 4).map((item) => ({
        question: item.message,
        intent: item.intent,
        confidence: item.value
      }))
    : behavior.value?.topAttractions?.length
    ? behavior.value.topAttractions.slice(0, 4).map(([name, count]) => ({
        question: String(name),
        intent: "热门景区",
        confidence: `${formatNumber(Number(count || 0))}条`
      }))
    : hotQuestionEntries.value.length
    ? hotQuestionEntries.value.slice(0, 4).map(([question, count]) => ({
        question,
        intent: "高频问答",
        confidence: `${formatNumber(count)}次`
      }))
    : visibleRecords.value.slice(0, 4).map((record) => ({
        question: record.question,
        intent: record.intent || "游客咨询",
        confidence: record.satisfaction ? `${Number(record.satisfaction).toFixed(1)}分` : recordConfidenceLabel(record) || "DeepSeek"
      }))
);
const knowledgeStats = computed(() => [
  { label: "启用知识", value: formatNumber(activeKnowledgeDocs.value.length), detail: "参与问答召回", icon: CheckCircle2 },
  { label: "知识条目", value: formatNumber(knowledgeDocs.value.length), detail: "所有来源资料", icon: FileText },
  {
    label: "知识准确率",
    value: `${knowledgeEvaluation.value?.accuracyRate ?? 0}%`,
    detail: `${knowledgeEvaluation.value?.passedQuestionCount ?? 0}/${knowledgeEvaluation.value?.testedQuestionCount ?? 0} 标准题通过`,
    icon: Gauge
  },
  {
    label: "事实覆盖",
    value: `${knowledgeEvaluation.value?.coverageRate ?? 0}%`,
    detail: `${knowledgeEvaluation.value?.coveredFactCount ?? 0}/${knowledgeEvaluation.value?.requiredFactCount ?? 0} 关键事实命中`,
    icon: Target
  },
  { label: "待沉淀问题", value: formatNumber(lowConfidenceRecords.value.length), detail: "低置信问答", icon: MessageSquareText },
  { label: "资料分类", value: formatNumber(knowledgeCategories.value.length), detail: "当前可筛选类别", icon: Database }
]);
const personaSummaryCards = computed(() => {
  const runtime = resolvePresetFromPersona(personaForm.value);
  return [
    { label: "当前选择", value: presetLabel(runtime), detail: `Avatar: ${runtime.avatarId} / ${runtime.refAudio}` },
    { label: "默认音色", value: runtime.voice, detail: buildPresetSummary(runtime) },
    { label: "文本驱动", value: runtime.ttsMode, detail: "发送前打断当前播报" }
  ];
});
const sourceTypeLabelMap: Record<string, string> = {
  manual: "手工录入",
  seed: "系统种子",
  official_docx: "官方 DOCX",
  behavior_excel: "行为 Excel",
  chat_draft: "问答沉淀"
};
const reportSampleLabels = computed(() => ["系统交互", "灵山游客行为"]);
const reportSampleValues = computed(() => [
  reportRecordTotal.value,
  behaviorSampleRows.value
]);
const reportBehaviorAverageSatisfaction = computed(() => Number(behavior.value?.averageSatisfaction || 0));
const reportUsesBehaviorSatisfaction = computed(() => !reportFeedbackTotal.value && reportBehaviorAverageSatisfaction.value > 0);
const reportSatisfactionSourceLabel = computed(() => {
  if (reportFeedbackTotal.value) return "真实游客评分反馈";
  if (reportUsesBehaviorSatisfaction.value) return "灵山游客行为评分";
  return "暂无评分样本";
});
const reportAverageSatisfaction = computed(() => {
  if (reportFeedbackTotal.value) return Number(analyticsSnapshot.value.averageSatisfaction || 0);
  return reportBehaviorAverageSatisfaction.value;
});
const reportSuggestionItems = computed(() => {
  if (reportUsesSyntheticAnalytics.value) return ["后端分析接口未返回真实记录，游客感受度报告暂不展示演示样本。"];

  const items: string[] = [];
  const topIntent = intentLabels.value[0];
  const topQuestion = hotQuestionEntries.value[0]?.[0];
  const lowConfidenceCount = reportUsesSyntheticAnalytics.value ? 0 : reportLowConfidenceRecords.value.length || analyticsSnapshot.value.unresolvedCount || 0;

  if (!reportQuestionTotal.value && !reportFeedbackTotal.value) {
    items.push(
      reportUsesBehaviorSatisfaction.value
        ? "暂无系统内游客问答或评分反馈，当前满意度先按灵山游客行为记录展示。"
        : "暂无真实游客问答或评分反馈，先通过数字人问答和游客评分积累样本。"
    );
  }
  if (topQuestion) {
    items.push(`优先复核「${compactText(topQuestion, 18)}」等真实高频问题的答案口径。`);
  }
  if (topIntent) {
    items.push(`围绕「${topIntent}」集中优化导览话术，并同步到数字人开场问候。`);
  }
  if (lowConfidenceCount) {
    items.push(`当前有 ${formatNumber(lowConfidenceCount)} 条低置信问答，建议转入知识库审核后再启用。`);
  }
  if (!reportFeedbackTotal.value) {
    items.push(
      reportUsesBehaviorSatisfaction.value
        ? "暂无系统内游客评分反馈，满意度当前来自导入行为数据的 satisfaction 评分列。"
        : "暂无真实游客评分反馈，满意度和复游意愿需等待评分样本生成。"
    );
  }
  return items.length ? items.slice(0, 3) : ["当前真实反馈记录未发现明显风险，可继续观察新增问答和评分变化。"];
});
const reportRefreshTime = new Date().toLocaleString("zh-CN", {
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit"
});
const reportRecordTotal = computed(() => reportQuestionTotal.value + reportFeedbackTotal.value);
const reportSentimentTotal = computed(() =>
  reportUsesSyntheticAnalytics.value
    ? 0
    : Object.values(reportSentimentDistribution.value).reduce((total, value) => total + Number(value || 0), 0)
);
const reportPositiveCount = computed(() =>
  reportUsesSyntheticAnalytics.value
    ? 0
    : distributionCount(reportSentimentDistribution.value, ["positive", "正", "积极", "好评", "满意", "愉悦", "开心"])
);
const reportNegativeCount = computed(() =>
  reportUsesSyntheticAnalytics.value
    ? 0
    : distributionCount(reportSentimentDistribution.value, ["negative", "负", "消极", "差评", "不满", "投诉", "糟糕"])
);
const reportPositiveRate = computed(() => {
  if (reportSentimentTotal.value > 0) return percentNumber(reportPositiveCount.value, reportSentimentTotal.value);
  return 0;
});
const reportRiskRate = computed(() => {
  const lowConfidenceCount = reportUsesSyntheticAnalytics.value ? 0 : reportLowConfidenceRecords.value.length || analyticsSnapshot.value.unresolvedCount || 0;
  const total = Math.max(reportRecordTotal.value, reportSentimentTotal.value);
  return percentNumber(reportNegativeCount.value + lowConfidenceCount, total);
});
const reportSatisfactionPercent = computed(() =>
  Math.round(clampNumber(reportAverageSatisfaction.value / 5, 0, 1) * 100)
);
const reportHasSatisfactionSample = computed(() => reportAverageSatisfaction.value > 0);
const reportCompositeScore = computed(() => {
  if (!reportRecordTotal.value && !reportSentimentTotal.value && !reportHasSatisfactionSample.value) return 0;
  const sentimentComponent = reportSentimentTotal.value ? reportPositiveRate.value : reportSatisfactionPercent.value;
  const riskComponent = reportRecordTotal.value ? 100 - reportRiskRate.value : reportSatisfactionPercent.value;
  return Math.round(
    clampNumber(
      reportSatisfactionPercent.value * 0.58 + sentimentComponent * 0.26 + riskComponent * 0.16,
      0,
      100
    )
  );
});
const reportTrendDelta = computed(() => {
  const values = reportTrendValues.value;
  if (values.length < 2) return 0;
  return Number((values[values.length - 1] - values[values.length - 2]).toFixed(2));
});
const reportTrendDeltaLabel = computed(() => `${reportTrendDelta.value >= 0 ? "+" : ""}${reportTrendDelta.value.toFixed(2)}`);
const reportScopeLabel = computed(() => {
  const range = behavior.value?.dateRange;
  if (range?.start && range?.end) return `${range.start} 至 ${range.end}`;
  if (behavior.value?.analysisScope) return behavior.value.analysisScope;
  return reportRecordTotal.value ? "真实交互样本" : "暂无真实交互样本";
});
const reportSourceCards = computed(() => [
  {
    label: "反馈样本",
    value: formatNumber(reportFeedbackTotal.value),
    detail: reportFeedbackTotal.value ? "真实游客评分反馈" : "系统内评分反馈暂无",
    icon: MessageSquareText
  },
  {
    label: "问答记录",
    value: formatNumber(reportQuestionTotal.value),
    detail: "真实数字人交互记录",
    icon: MessageSquareText
  },
  {
    label: "行为样本",
    value: formatNumber(behaviorSampleRows.value),
    detail: "灵山游客行为记录，含评分列",
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
    value: reportAverageSatisfaction.value.toFixed(1),
    unit: "分",
    detail: `${reportSatisfactionPercent.value}% 满意度折算｜${reportSatisfactionSourceLabel.value}`,
    icon: Star
  },
  {
    label: "正向情感",
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
    detail: "已按灵山关键词筛选",
    icon: Target
  },
  {
    label: "知识准确率",
    value: knowledgeEvaluation.value?.accuracyRate ?? 0,
    unit: "%",
    detail: `${knowledgeEvaluation.value?.passedQuestionCount ?? 0}/${knowledgeEvaluation.value?.testedQuestionCount ?? 0} 标准题`,
    icon: Gauge
  }
]);
const reportExperienceFactors = computed(() => {
  const fallbackSatisfactionScore = reportHasSatisfactionSample.value ? reportSatisfactionPercent.value : 0;
  const sentimentScore = reportSentimentTotal.value ? reportPositiveRate.value : fallbackSatisfactionScore;
  const questionFocusScore = reportQuestionTotal.value ? clampNumber(100 - reportRiskRate.value, 0, 100) : fallbackSatisfactionScore;
  const clarityScore = reportQuestionTotal.value ? clampNumber(reportSatisfactionPercent.value - reportRiskRate.value * 0.18, 0, 100) : fallbackSatisfactionScore;
  const revisitScore = reportFeedbackTotal.value
    ? clampNumber((reportPositiveRate.value + reportSatisfactionPercent.value) / 2, 0, 100)
    : fallbackSatisfactionScore;

  return [
    { label: "情感体验", value: Math.round(sentimentScore), icon: HeartPulse },
    { label: "表达清晰", value: Math.round(clarityScore), icon: BadgeCheck },
    { label: "痛点可控", value: Math.round(questionFocusScore), icon: ShieldAlert },
    { label: "复游意愿", value: Math.round(revisitScore), icon: Target }
  ];
});
const reportSentimentItems = computed(() => {
  const normalizedEntries = reportUsesSyntheticAnalytics.value
    ? []
    : Object.entries(reportSentimentDistribution.value)
        .map(([label, value]) => [label, Number(value || 0)] as [string, number])
        .filter(([, value]) => value > 0);
  if (!normalizedEntries.length) {
    return [{ label: "暂无真实情感记录", value: "0", percent: "0%", tone: "blue" }];
  }
  const total = Math.max(normalizedEntries.reduce((sum, [, value]) => sum + value, 0), 1);

  return normalizedEntries.slice(0, 4).map(([label, value], index) => ({
    label,
    value: formatNumber(value),
    percent: `${percentNumber(value, total)}%`,
    tone: index === 1 ? "blue" : index === 2 ? "amber" : "green"
  }));
});
const reportAttentionItems = computed(() => {
  if (reportUsesSyntheticAnalytics.value) return [];
  const intentEntries = Object.entries(analyticsSnapshot.value.intentDistribution || {})
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
  const lowConfidenceCount = reportUsesSyntheticAnalytics.value ? 0 : reportLowConfidenceRecords.value.length || analyticsSnapshot.value.unresolvedCount || 0;
  const topQuestion = reportUsesSyntheticAnalytics.value ? undefined : hotQuestionEntries.value[0];
  const negativePercent = percentNumber(reportNegativeCount.value, reportSentimentTotal.value);
  const matchedPercent = behaviorSampleRows.value ? percentNumber(behaviorMatchedRows.value, behaviorSampleRows.value) : 0;

  return [
    {
      label: "负向情感",
      value: formatNumber(reportNegativeCount.value),
      meta: reportNegativeCount.value ? "需要关注反馈表达" : "稳定",
      percent: `${Math.max(negativePercent, reportNegativeCount.value ? 12 : 4)}%`,
      tone: reportNegativeCount.value ? "warning" : "ok"
    },
    {
      label: "高频追问",
      value: topQuestion ? formatNumber(topQuestion[1]) : "0",
      meta: compactText(topQuestion?.[0] || "暂无集中问题", 20),
      percent: pressurePercent(Number(topQuestion?.[1] || 0), Math.max(reportQuestionTotal.value || 1, Number(topQuestion?.[1] || 0), 1)),
      tone: topQuestion ? "watch" : "ok"
    },
    {
      label: "样本命中率",
      value: `${matchedPercent}%`,
      meta: "灵山游客行为记录",
      percent: `${Math.max(matchedPercent, 4)}%`,
      tone: matchedPercent >= 20 ? "ok" : "watch"
    },
    {
      label: "体验波动",
      value: reportTrendDeltaLabel.value,
      meta: "满意度环比变化",
      percent: `${Math.min(100, Math.max(8, Math.round(Math.abs(reportTrendDelta.value) * 40)))}%`,
      tone: reportTrendDelta.value < 0 ? "warning" : "ok"
    },
    {
      label: "知识低置信",
      value: `${knowledgeEvaluation.value?.lowConfidenceRate ?? 0}%`,
      meta: "RAG 待复核比例",
      percent: `${Math.max(knowledgeEvaluation.value?.lowConfidenceRate ?? 0, 4)}%`,
      tone: (knowledgeEvaluation.value?.lowConfidenceRate ?? 0) > 10 ? "watch" : "ok"
    }
  ];
});
const reportRecentRows = computed(() =>
  reportVisibleRecords.value.slice(0, 3).map((record) => ({
    question: record.question,
    intent: record.intent || "导览咨询",
    sentiment: record.sentiment || "neutral",
    score: record.satisfaction ? `${Number(record.satisfaction).toFixed(1)}分` : recordConfidenceLabel(record) || "DeepSeek",
    confidence: recordConfidenceLabel(record) || "DeepSeek"
  }))
);
const reportTrendPoints = computed(() => {
  const values = reportTrendValues.value;
  if (!values.length) return [];
  const labels = reportTrendLabels.value;
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

function formatScreenMetricValue(value: unknown) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return String(value ?? "");
  if (Number.isInteger(numericValue)) return formatNumber(numericValue);
  return numericValue.toFixed(1);
}

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
  return hotSpotScoreMap.value[spot.name] ?? 0;
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
  () => props.analytics,
  (analytics) => {
    analyticsData.value = analytics;
    if (analytics.behaviorBaseline) behaviorData.value = analytics.behaviorBaseline;
    if (analytics.recentQuestions?.length) {
      const recentIds = new Set(analytics.recentQuestions.map((record) => record.id));
      chatRecords.value = [
        ...analytics.recentQuestions,
        ...chatRecords.value.filter((record) => !recentIds.has(record.id))
      ].slice(0, 50);
    }
  },
  { deep: true }
);

function personaAvatarSignature(persona: Persona) {
  return [
    persona.avatarPresetKey,
    persona.avatarId,
    persona.refAudio,
    persona.refText,
    persona.avatarVoice,
    persona.ttsMode
  ].join("\0");
}

watch(
  personaForm,
  (form) => {
    if (personaAvatarSignature(form) !== personaAvatarSignature(props.persona)) {
      personaPresetLocked.value = true;
      savePersonaDraft(form);
      return;
    }
    if (!personaPresetLocked.value) {
      clearPersonaDraft();
    }
  },
  { deep: true }
);

watch(
  () => props.persona,
  (persona) => {
    if (personaPresetLocked.value) return;
    personaForm.value = clonePersona(persona);
    applyLiveTalkingPreset(resolvePresetFromPersona(persona));
    clearPersonaDraft();
  },
  { deep: true }
);

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
  const attentionRows = reportAttentionItems.value.map((item) => [item.label, item.value, item.percent]);
  const sampleRows = reportSampleLabels.value.map((label, index) => [label, formatNumber(reportSampleValues.value[index] || 0)]);
  const trendSource = behaviorTrendLabels.value.length ? "灵山游客行为记录" : "系统交互记录";
  const interactionRows = reportSourceCards.value.map((item) => [item.label, item.value, item.detail]);
  const suggestionBasisRows = reportRiskItems.value.map((item) => [item.label, item.value, item.meta]);
  const recentRows = reportRecentRows.value.map((record) => [record.question, record.intent, record.sentiment, record.score, record.confidence]);
  const primaryAttention = reportAttentionItems.value[0]?.label || "暂无真实关注点";
  const summaryRows = [
    ["综合感受指数", reportCompositeScore.value, "满意度、情感倾向与待复核问题综合折算"],
    ["平均满意度", `${reportAverageSatisfaction.value.toFixed(1)} / 5.0`, reportSatisfactionSourceLabel.value],
    ["正向情感占比", `${reportPositiveRate.value}%`, `${formatNumber(reportPositiveCount.value)} 条正向反馈`],
    [
      "低置信问答",
      formatNumber(reportUsesSyntheticAnalytics.value ? 0 : reportLowConfidenceRecords.value.length || analyticsSnapshot.value.unresolvedCount || 0),
      "建议审核后沉淀为知识条目"
    ]
  ];

  const escapeHtml = (value: string | number) =>
    String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  const htmlTable = (headers: string[], rows: Array<Array<string | number>>) => {
    const empty = `<tr><td colspan="${headers.length}">暂无数据</td></tr>`;
    const body = rows.length
      ? rows.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")
      : empty;
    return `<table><thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table>`;
  };
  const htmlCards = (rows: Array<Array<string | number>>) =>
    `<div class="metric-grid">${rows
      .map(
        ([label, value, detail]) =>
          `<article><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(detail)}</small></article>`
      )
      .join("")}</div>`;
  const htmlList = (items: string[]) =>
    `<ol>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>`;

  const content = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>游客感受度报告</title>
  <style>
    body { margin: 0; background: #f5f7f6; color: #17241f; font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif; }
    .report { max-width: 1120px; margin: 0 auto; padding: 32px; }
    .hero { border-radius: 12px; background: #ffffff; padding: 28px; box-shadow: 0 16px 40px rgba(35, 56, 48, 0.08); }
    h1, h2, h3, p { margin: 0; }
    h1 { font-size: 30px; line-height: 1.2; }
    h2 { margin-bottom: 14px; font-size: 21px; }
    h3 { margin: 18px 0 10px; font-size: 16px; }
    .meta { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; color: #5f6f68; font-size: 13px; }
    .meta span, .badge { border: 1px solid #dfe8e3; border-radius: 999px; background: #f8fbf9; padding: 6px 10px; }
    .summary { margin-top: 16px; color: #40514a; line-height: 1.7; }
    section { margin-top: 22px; border: 1px solid #dfe8e3; border-radius: 12px; background: #ffffff; padding: 22px; box-shadow: 0 12px 30px rgba(35, 56, 48, 0.05); }
    .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
    .metric-grid article { border: 1px solid #e4ece8; border-radius: 10px; background: #f8fbf9; padding: 14px; }
    .metric-grid span, .metric-grid small { display: block; color: #64766e; font-size: 12px; }
    .metric-grid strong { display: block; margin: 8px 0; color: #1f4f3a; font-size: 24px; }
    table { width: 100%; border-collapse: collapse; overflow: hidden; border-radius: 10px; font-size: 13px; }
    th, td { border-bottom: 1px solid #e8efeb; padding: 10px 12px; text-align: left; vertical-align: top; }
    th { background: #eef6f2; color: #264f3f; font-weight: 800; }
    tr:last-child td { border-bottom: 0; }
    ol { margin: 0; padding-left: 22px; line-height: 1.75; }
    li + li { margin-top: 8px; }
    .two-col { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
    @media (max-width: 760px) { .report { padding: 18px; } .two-col { grid-template-columns: 1fr; } }
    @media print { body { background: #ffffff; } .report { max-width: none; padding: 0; } section, .hero { box-shadow: none; break-inside: avoid; } }
  </style>
</head>
<body>
  <main class="report">
    <header class="hero">
      <span class="badge">游客感受度报告</span>
      <h1>灵山胜境游客感受度分析</h1>
      <div class="meta">
        <span>导出时间：${escapeHtml(exportedAt.toLocaleString("zh-CN"))}</span>
        <span>统计范围：${escapeHtml(reportScopeLabel.value)}</span>
        <span>趋势口径：${escapeHtml(trendSource)}</span>
        <span>满意度口径：${escapeHtml(reportSatisfactionSourceLabel.value)}</span>
      </div>
      <p class="summary">本报告基于系统交互记录、游客反馈、满意度走势和知识库低置信问答生成。当前首要关注点为「${escapeHtml(primaryAttention)}」，综合感受指数为 ${escapeHtml(reportCompositeScore.value)}。</p>
    </header>

    <section>
      <h2>概览</h2>
      ${htmlCards(summaryRows)}
    </section>

    <section>
      <h2>交互记录</h2>
      ${htmlTable(["记录类型", "数量/结果", "说明"], interactionRows)}
    </section>

    <section>
      <h2>游客关注点分析</h2>
      ${htmlTable(["关注点", "数量", "占比"], attentionRows)}
    </section>

    <section class="two-col">
      <div>
        <h2>情感趋势</h2>
        ${htmlTable(["情感倾向", "反馈数量"], sentimentRows)}
      </div>
      <div>
        <h2>满意度趋势</h2>
        ${htmlTable(["时间", "满意度"], trendRows)}
      </div>
    </section>

    <section>
      <h2>服务建议</h2>
      ${htmlList(reportSuggestionItems.value)}
      <h3>建议依据</h3>
      ${htmlTable(["指标", "当前值", "说明"], suggestionBasisRows)}
    </section>

    <section>
      <h2>近期交互样本</h2>
      ${htmlTable(["问题", "意图", "情感", "评分/命中", "置信度"], recentRows)}
    </section>

    <section>
      <h2>样本构成</h2>
      ${htmlTable(["类别", "样本量"], sampleRows)}
    </section>
  </main>
</body>
</html>`;

  const blob = new Blob([content], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `游客感受度报告-${exportedAt.toISOString().slice(0, 10)}.html`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setNotice("游客感受度报告已导出为 HTML。");
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
  return "";
}

function closeModal() {
  modal.value = null;
}

async function reloadAdminData() {
  busy.value = true;
  try {
    const token = mutationToken();
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
      apiGet<AnalyticsOverview>("/api/admin/analytics/overview", token).then((analyticsResult) => {
        analyticsData.value = analyticsResult;
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

function triggerBehaviorUpload() {
  behaviorUploadInput.value?.click();
}

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("资料文件读取失败"));
    reader.readAsDataURL(file);
  });
}

async function uploadBehaviorExcel(file: File) {
  if (!/\.xlsx$/i.test(file.name)) {
    throw new Error("仅支持 .xlsx 行为数据文件。");
  }
  const dataUrl = await readFileAsDataUrl(file);
  const result = await apiPost<PublicDataImportResult>(
    "/api/admin/behavior/upload-xlsx",
    { fileName: file.name, dataUrl },
    mutationToken()
  );
  await refreshAdminSnapshot();
  setNotice(`行为数据已导入数据库：${formatNumber(result.behaviorRecordCount || result.recordCount || 0)} 条记录，来源 ${file.name}。`);
}

async function handleBehaviorUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  importingBehaviorRows.value = true;
  setActionStatus("importBehavior", "loading");
  try {
    await uploadBehaviorExcel(file);
    setActionStatus("importBehavior", "success");
  } catch (error) {
    setError(error instanceof Error ? error.message : "行为数据导入失败");
    setActionStatus("importBehavior", "error");
  } finally {
    importingBehaviorRows.value = false;
    input.value = "";
  }
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
      const updated = await apiPut<KnowledgeDocument>(`/api/admin/knowledge/${knowledgeForm.value.id}`, knowledgePayload(), token);
      knowledgeDocs.value = knowledgeDocs.value.map((item) => (item.id === updated.id ? updated : item));
      selectedKnowledgeId.value = updated.id;
    } else {
      const created = await apiPost<KnowledgeDocument>("/api/admin/knowledge", knowledgePayload(), token);
      knowledgeQuery.value = "";
      knowledgeCategory.value = "all";
      knowledgeDocs.value = [created, ...knowledgeDocs.value.filter((item) => item.id !== created.id)];
      selectedKnowledgeId.value = created.id;
      knowledgeForm.value.id = created.id;
    }
    syncSelectedKnowledge();
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
  const deletedId = knowledgeForm.value.id;
  saving.value = true;
  setActionStatus("deleteKnowledge", "loading");
  try {
    await apiDelete<{ ok: boolean }>(`/api/admin/knowledge/${deletedId}`, mutationToken());
    knowledgeDocs.value = knowledgeDocs.value.filter((item) => item.id !== deletedId);
    syncSelectedKnowledge();
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
    personaPresetLocked.value = false;
    clearPersonaDraft();
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
    behaviorUploadInput,
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
    handleBehaviorUpload,
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
    knowledgeEvaluation,
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
    recordConfidenceLabel,
    readInitialAdminTab,
    ref,
    refreshAdminSnapshot,
    refreshAll,
    RefreshCw,
    reimportPublicData,
    reloadAdminData,
    reportAttentionItems,
    reportAverageSatisfaction,
    reportCompositeScore,
    reportExperienceFactors,
    reportKpiCards,
    reportFeedbackTotal,
    reportLowConfidenceRecords,
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
    reportSatisfactionSourceLabel,
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
    shouldShowRecordConfidence,
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
    triggerBehaviorUpload,
    Upload,
    uploadBehaviorExcel,
    uploadKnowledgeDocx,
    useFallbackImage,
    Users,
    visibleRecords,
    watch,
    X,
    Zap
  };
}
