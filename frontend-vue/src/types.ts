export type ScenicSpot = {
  id: number;
  name: string;
  description: string;
  story: string;
  tags: string[];
  image: string;
  openTime: string;
  duration: number;
  popularity: number;
  location: string;
  status?: "active" | "inactive";
  updatedAt?: number;
  lat?: number | null;
  lon?: number | null;
  mapZone?: "lingshan" | "nianhua" | string;
  mapX?: number | null;
  mapY?: number | null;
  verifiedLocation?: boolean;
  distance?: number;
  locationCode?: string;
};

export type Persona = {
  name: string;
  role: string;
  greeting: string;
  style: string;
  costume: string;
  voice: string;
  accentColor: string;
  voiceSpeed?: number;
  voicePitch?: number;
  expressionProfile?: string;
  updatedAt?: number;
};

export type KnowledgeDocument = {
  id: string;
  title: string;
  category: string;
  content: string;
  status: "active" | "inactive";
  sourceType?: "manual" | "seed" | "official_docx" | "behavior_excel" | "chat_draft" | string;
  sourceFile?: string;
  sourceSection?: string;
  createdAt: number;
  updatedAt: number;
};

export type LlmStatus = {
  provider: string;
  baseUrl: string;
  model: string;
  configured?: boolean;
  enabled: boolean;
  available: boolean;
  hasApiKey: boolean;
  reason: string;
  multimodal: boolean;
  visionModel?: string;
  visionProvider?: string;
  visionBaseUrl?: string;
  visionAvailable?: boolean;
  visionReason?: string;
  visionHasApiKey?: boolean;
  visionMultimodal?: boolean;
  runtimeChecked?: boolean;
  runtimeReady?: boolean;
  runtimeReason?: string;
  runtimeHint?: string;
  modelInstalled?: boolean | null;
  installedModels?: string[];
  chatFastMode?: boolean;
};

export type SystemCapabilities = {
  coreAi: {
    textProvider: string;
    textModel: string;
    textAvailable: boolean;
    multimodalProvider: string;
    multimodalModel: string;
    multimodalAvailable: boolean;
    multimodalRequired: boolean;
    multimodalRole: string;
  };
  knowledge: {
    localKnowledgeEnabled: boolean;
    activeDocuments: number;
    sourcePolicy: string;
    accuracyTarget: number;
    evaluationMethod: string;
  };
  interaction: {
    textInput: boolean;
    browserSpeechInput: boolean;
    serverAsrAvailable: boolean;
    voiceOutput: boolean;
    browserVoiceFallback: boolean;
    expressionLipSync: boolean;
    imageUnderstanding: boolean;
  };
  quality: {
    factualAccuracyTarget: string;
    voiceQaLatencyTargetMs: number;
    stabilityTarget: string;
    fallbackPolicy: string;
  };
  positioning: {
    gpsSupported: boolean;
    fallbackStrategies: string[];
    difficultScenarioPlan: string;
  };
};

export type TtsStatus = {
  provider: string;
  enabled: boolean;
  available: boolean;
  reason: string;
  cluster?: string;
  voiceType?: string;
  hasAccessToken?: boolean;
  fallback?: string;
};

export type AsrStatus = {
  provider: string;
  enabled: boolean;
  available: boolean;
  reason: string;
  hasApiKey?: boolean;
  fallback?: string;
};

export type AsrTranscriptionResponse = {
  available?: boolean;
  fallback?: boolean;
  provider?: string;
  reason?: string;
  message?: string;
  text: string;
};

export type SourceRef = {
  id?: string | number;
  type?: string;
  title: string;
  category?: string;
  sourceType?: string;
  sourceFile?: string;
  sourceSection?: string;
};

export type ChatResponse = {
  id: string;
  question: string;
  answer: string;
  relatedSpots: ScenicSpot[];
  sourceRefs: SourceRef[];
  intent: string;
  confidence: number;
  sentiment: "positive" | "neutral" | "negative" | string;
  satisfaction?: number;
  llmProvider?: string;
  modelName?: string;
  fallback?: boolean;
  latencyMs?: number;
  createdAt?: number;
};

export type VisionResponse = {
  answer: string;
  modelName?: string;
  llmProvider?: string;
  fallback?: boolean;
  latencyMs?: number;
  sourceRefs?: SourceRef[];
};

export type TtsSynthesisResponse = {
  available?: boolean;
  fallback?: boolean;
  provider?: string;
  reason?: string;
  message?: string;
  audioDataUrl?: string;
};

export type RouteOptions = {
  durations: number[];
  preferences: string[];
};

export type RouteResponse = {
  id: string;
  title: string;
  duration: number;
  estimatedDuration: number;
  preference: string;
  spots: ScenicSpot[];
  reason: string;
  createdAt: number;
};

export type LocationConfidence = "high" | "medium" | "low";

export type NearbyLocationResponse = {
  items: ScenicSpot[];
  nearest?: ScenicSpot | null;
  accuracy?: number | null;
  confidence: LocationConfidence;
  insideScenic: boolean;
  message: string;
};

export type LocationResolveResponse = {
  ok: boolean;
  anchor: ScenicSpot | null;
  confidence: LocationConfidence;
  message: string;
};

export type PublicDataImportResult = {
  imported: boolean;
  spotCount: number;
  knowledgeCount: number;
  recordCount: number;
  behaviorRecordCount?: number | null;
  behaviorRecordImported?: boolean;
  dataDir: string;
  importedAt?: number;
  message: string;
};

export type AnalyticsOverview = {
  questionCount: number;
  routeCount: number;
  spotCount: number;
  knowledgeCount: number;
  todayServiceCount: number;
  weekServiceCount: number;
  averageSatisfaction: number;
  unresolvedCount: number;
  hotSpots: Array<[string, number]>;
  preferences: Record<string, number>;
  hotQuestions: Array<[string, number]>;
  intentDistribution: Record<string, number>;
  sentimentDistribution: Record<string, number>;
  satisfactionTrend: Array<{ date: string; score: number; count: number }>;
  recentQuestions: ChatResponse[];
  serviceSuggestions: string[];
  behaviorBaseline?: BehaviorAnalytics;
  dataSource?: Record<string, unknown>;
};

export type OperationsMetric = {
  key: string;
  label: string;
  value: number;
  unit: string;
  detail: string;
};

export type OperationsOverview = {
  available: boolean;
  generatedAt: number;
  sourceType: string;
  sourceDescription: string;
  core: {
    title: string;
    keyArea: string;
    dutyStatus: string;
    summary: string;
  };
  metrics: OperationsMetric[];
  stations: Array<{
    key: string;
    name: string;
    role: string;
    status: string;
    value?: number;
  }>;
  resources: Array<{
    key: string;
    label: string;
    value: string;
    detail: string;
  }>;
  flow: Array<{
    label: string;
    value: number;
  }>;
  trend: Array<{
    label: string;
    value: number;
  }>;
  briefings: Array<{
    intent: string;
    value: string;
    message: string;
  }>;
  dataSource?: Record<string, unknown>;
};

export type BehaviorAnalytics = {
  available: boolean;
  rowCount: number;
  matchedScenicRows?: number;
  structuredTableName?: string;
  structuredTableImported?: boolean;
  structuredTableCurrent?: boolean;
  behaviorRecordCount?: number;
  analysisScope?: string;
  analysisScopeDescription?: string;
  sampleSourceFile?: string;
  scenicMatchedKeywords?: string[];
  matchRuleDescription?: string;
  officialDocumentSources?: string[];
  lingshanDocumentSource?: string;
  message?: string;
  dateRange?: { start: string; end: string };
  averageSatisfaction?: number;
  averageStayDuration?: number;
  averageGroupSize?: number;
  topAttractions?: Array<[string, number]>;
  typeDistribution?: Array<[string, number]>;
  genderDistribution?: Record<string, number>;
  ageDistribution?: Record<string, number>;
  satisfactionTrend?: Array<{ date: string; score: number; count: number }>;
  consumptionBreakdown?: Array<{ name: string; value: number }>;
  dataSource?: {
    type: string;
    label: string;
    file: string;
    note?: string;
  };
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  pending?: boolean;
  meta?: Partial<ChatResponse>;
};
