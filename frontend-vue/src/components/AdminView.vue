<script setup lang="ts">
import { toRefs } from "vue";
import AdminModalLayer from "./admin/AdminModalLayer.vue";
import AdminPersonaPage from "./admin/AdminPersonaPage.vue";
import AdminShellHeader from "./admin/AdminShellHeader.vue";
import { useAdminView, type AdminViewEmit, type AdminViewProps } from "./admin/useAdminView";

const props = defineProps<AdminViewProps>();
const emit = defineEmits<AdminViewEmit>();
const { analytics, llmStatus, capabilities, spots, persona } = toRefs(props);
const adminView = useAdminView(props, emit);

const {
  actionLabel, actionStatus, actionStatusClass, activeKnowledgeDocs, activeTab, Activity,
  adminError, adminSpots, adminTabs, apiDelete, apiGet,
  apiPost, apiPut, BadgeCheck, behavior, behaviorData, behaviorMatchedRows,
  behaviorSampleRows, behaviorTrendLabels, behaviorTrendValues, behaviorUploadInput, Bot, busy, chatRecords,
  CheckCircle2, clampNumber, Clock3, clonePersona, closeModal, compactText,
  compactTrendLabel, computed, convertingChatId, convertRecordToKnowledge, Database, deactivateSpot,
  deleteKnowledge, derivedScreenCapacityRate, derivedScreenDeviceHealth, derivedScreenPassIndex, derivedScreenPatrolCoverage, digitalHumanAvatar,
  digitalHumanAvatarFallback, distributionCount, Download, emptyKnowledgeForm, emptySpotForm, exportVisitorReport,
  fallbackKnowledgeDocuments, feedbackRecords, FileText, filteredKnowledgeDocs, formatNumber, Gauge,
  handleBehaviorUpload, handleKnowledgeUpload, HeartPulse, hotQuestionEntries, hotSpotEntries, hotSpotScoreMap, imageForSpot,
  importingBehaviorRows, importingPublicData, intentLabels, intentValues, isActionBusy, knowledgeCategories,
  knowledgeCategory, knowledgeDocs, knowledgeForm, knowledgePayload, knowledgeQuery, knowledgeStats,
  knowledgeUploadInput, lowConfidenceRecords, MapPinned, markdownTable, MessageSquareText, MetricChart,
  modal, mutationToken, notice, officialKnowledgeDocs, officialKnowledgeGroups, onMounted,
  openKnowledgeDetail, openKnowledgeEditor, openSpotManager, operationMetric, operationMetricCard, operationsOverview,
  percentNumber, personaForm, personaSummaryCards, photoOptions, pressurePercent, Radar,
  reactive, readFileAsDataUrl, readInitialAdminTab, ref, refreshAdminSnapshot,
  refreshAll, RefreshCw, reimportPublicData, reloadAdminData, reportAttentionItems,
  reportAverageSatisfaction, reportCompositeScore, reportExperienceFactors, reportKpiCards, reportPositiveCount, reportPositiveRate, reportRecentRows,
  reportRecordTotal, reportRefreshTime, reportRiskItems, reportRiskRate, reportSampleLabels, reportSampleValues,
  reportSatisfactionPercent, reportSatisfactionSourceLabel, reportScopeLabel, reportSentimentItems, reportSentimentTotal, reportSourceCards, reportSuggestionItems,
  reportTrendAreaPath, reportTrendDelta, reportTrendDeltaLabel, reportTrendLabels, reportTrendPoints, reportTrendPolyline,
  reportTrendTitle, reportTrendValues, Route, Save, saveKnowledge, savePersona,
  saveSpot, saving, screenAgentCards, screenAssetCards, screenBaseLoad, screenCapacityRate,
  screenDeviceHealth, screenMetrics, screenPassIndex, screenPatrolCoverage, screenRecentRows,
  screenScenicPins, screenSpotHeat, screenSpotRadius, screenStationIcons, screenTourFlowBars, screenTrendPoints,
  screenTrendPolyline, selectedKnowledge, selectedKnowledgeId, selectedSpot, selectedSpotId, sentimentLabels,
  sentimentValues, setActionStatus, setError, setNotice, ShieldAlert, SmilePlus,
  sourceTypeLabel, sourceTypeLabelMap, spotForm, spotImagePreview, spotPayload, spotPhotoChoices,
  Star, syncSelectedKnowledge, Target, topSpotMaxValue, Trash2, trendLabels,
  trendValues, triggerBehaviorUpload, triggerKnowledgeUpload, Upload, uploadKnowledgeDocx, useFallbackImage, Users,
  visibleRecords, watch, X, Zap
} = adminView;
</script>

<template>
  <main class="admin-view admin-four-page">
    <AdminShellHeader :ctx="adminView" />

    <section v-if="activeTab === 'screen'" class="admin-page screen-heritage-page">
      <div class="heritage-screen" aria-label="灵山胜境数字人服务数据大屏">
        <i class="heritage-corner top-left"></i>
        <i class="heritage-corner top-right"></i>
        <i class="heritage-corner bottom-left"></i>
        <i class="heritage-corner bottom-right"></i>

        <header class="heritage-title-wrap">
          <span></span>
          <h2>灵山数字人服务大屏</h2>
        </header>

        <section class="heritage-panel panel-left panel-kpis">
          <header>
            <strong>服务总览</strong>
            <small>今日 · 本周</small>
          </header>
          <div class="heritage-kpi-grid">
            <article v-for="item in screenMetrics" :key="item.label">
              <span><component :is="item.icon" :size="17" /></span>
              <div>
                <small>{{ item.label }}</small>
                <strong>{{ item.value }}<b>{{ item.unit }}</b></strong>
              </div>
            </article>
          </div>
        </section>

        <section class="heritage-panel panel-left panel-bars">
          <header>
            <strong>游客关注热点</strong>
            <small>行为类型与偏好</small>
          </header>
          <div class="heritage-bars">
            <article v-for="item in screenTourFlowBars" :key="item.label">
              <span>{{ item.value }}</span>
              <i><b :style="{ height: item.height }"></b></i>
              <small>{{ item.label }}</small>
            </article>
          </div>
        </section>

        <section class="heritage-panel panel-left panel-trend">
          <header>
            <strong>满意度趋势</strong>
            <small>最近 6 期</small>
          </header>
          <svg viewBox="0 0 260 120" role="img" aria-label="游客满意度趋势折线">
            <path class="trend-grid" d="M12 20 H246 M12 52 H246 M12 84 H246" />
            <polyline class="trend-line" :points="screenTrendPolyline" />
            <g v-for="point in screenTrendPoints" :key="`${point.label}-${point.value}`">
              <circle class="trend-dot" :cx="point.x" :cy="point.y" r="4" />
              <text :x="point.x" y="112">{{ point.label }}</text>
            </g>
          </svg>
        </section>

        <section class="heritage-center">
          <svg class="heritage-landscape" viewBox="0 0 640 410" role="img" aria-label="灵山胜境数字人服务热点图">
            <defs>
              <linearGradient id="heritageMountain" x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stop-color="#d8efe1" />
                <stop offset="58%" stop-color="#a9d2c2" />
                <stop offset="100%" stop-color="#7db49f" />
              </linearGradient>
              <linearGradient id="heritageRoof" x1="0" x2="1">
                <stop offset="0%" stop-color="#355b51" />
                <stop offset="100%" stop-color="#c79357" />
              </linearGradient>
              <linearGradient id="heritageWater" x1="0" x2="1">
                <stop offset="0%" stop-color="#bfe6de" />
                <stop offset="100%" stop-color="#f4ead0" />
              </linearGradient>
              <filter id="softInk" x="-15%" y="-20%" width="130%" height="140%">
                <feGaussianBlur stdDeviation="1.8" />
              </filter>
            </defs>
            <path class="ink-cloud cloud-a" d="M44 144 C100 94 166 126 208 88 C260 42 314 96 356 74 C422 38 480 84 532 68 C578 54 606 76 616 110 L616 220 L44 220Z" />
            <path class="ink-cloud cloud-b" d="M20 270 C126 220 218 268 308 220 C406 166 512 210 620 160 L620 336 C438 374 214 374 20 332Z" />
            <path class="mountain back" d="M12 178 L116 90 L190 154 L282 72 L388 166 L468 86 L628 188 L628 280 L12 280Z" />
            <path class="mountain front" d="M36 238 L142 136 L224 214 L312 118 L400 230 L482 150 L616 246 L616 310 L36 310Z" />
            <path class="lake" d="M42 278 C140 236 226 282 322 246 C420 210 506 236 604 202 L612 314 C438 374 212 372 40 326Z" />
            <g class="temple temple-left">
              <path d="M150 214 L240 190 L318 214 L292 222 L174 222Z" />
              <rect x="178" y="222" width="106" height="44" rx="4" />
              <path d="M194 188 L274 170 L300 190 L232 208Z" />
            </g>
            <g class="temple temple-main">
              <path d="M248 174 L358 130 L478 176 L438 190 L292 190Z" />
              <rect x="306" y="190" width="120" height="70" rx="5" />
              <path d="M330 128 L420 100 L460 132 L382 160Z" />
              <path d="M356 96 L392 68 L426 98 L392 112Z" />
            </g>
            <g class="temple temple-right">
              <path d="M420 236 L512 206 L590 236 L558 246 L452 246Z" />
              <rect x="454" y="246" width="94" height="48" rx="4" />
            </g>
            <path class="map-route" d="M104 284 C196 236 274 248 340 192 C414 130 488 142 570 102" />
            <g v-for="pin in screenScenicPins" :key="pin.spot.id" class="heritage-pin" :transform="`translate(${pin.x} ${pin.y})`">
              <line x1="0" y1="0" x2="0" y2="-30" />
              <circle :r="pin.radius" />
            </g>
          </svg>
        </section>

        <section class="heritage-panel panel-right panel-agents">
          <header>
            <strong>服务触点</strong>
            <small>游客端能力</small>
          </header>
          <div class="agent-strip">
            <article v-for="agent in screenAgentCards" :key="agent.name">
              <component :is="agent.icon" :size="24" />
              <strong>{{ agent.name }}</strong>
              <span>{{ agent.role }}</span>
              <small>{{ agent.status }}</small>
            </article>
          </div>
        </section>

        <section class="heritage-panel panel-right panel-assets">
          <header>
            <strong>知识闭环</strong>
            <small>内容质量</small>
          </header>
          <div class="asset-stack">
            <article v-for="item in screenAssetCards" :key="item.label">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <small>{{ item.detail }}</small>
            </article>
          </div>
        </section>

        <section class="heritage-panel panel-right panel-records">
          <header>
            <strong>热点记录</strong>
            <small>行为库 / 问答</small>
          </header>
          <div class="record-table compact-record-table">
            <article v-for="record in screenRecentRows" :key="record.question">
              <span>{{ record.intent }}</span>
              <strong>{{ record.confidence }}</strong>
              <small>{{ record.question }}</small>
            </article>
            <p v-if="!screenRecentRows.length">暂无热点记录。</p>
          </div>
        </section>

        <div class="heritage-actions">
          <button class="active" type="button" :class="actionStatusClass('refresh')" :disabled="isActionBusy('refresh')" @click="refreshAll">
            <RefreshCw :size="16" />
            {{ actionLabel("refresh", "刷新数据", "刷新中", "已刷新", "刷新失败") }}
          </button>
          <button type="button" @click="modal = 'records'">
            <MessageSquareText :size="16" />
            问答明细
          </button>
          <button type="button" @click="modal = 'spots'">
            <MapPinned :size="16" />
            热点点位
          </button>
          <button type="button" @click="modal = 'reportDetail'">
            <FileText :size="16" />
            体验报告
          </button>
          <button type="button" :disabled="isActionBusy('importBehavior')" @click="triggerBehaviorUpload">
            <Upload :size="16" />
            导入行为数据
          </button>
          <input ref="behaviorUploadInput" class="visually-hidden-file" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" @change="handleBehaviorUpload" />
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'knowledge'" class="admin-page knowledge-page">
      <div class="page-hero compact-hero">
        <div>
          <p class="section-kicker">内容维护</p>
          <h2>讲解词、点位资料、FAQ 与问答沉淀统一维护</h2>
        </div>
        <div class="page-actions">
          <button class="secondary-action compact" type="button" :class="actionStatusClass('importPublic')" :disabled="isActionBusy('importPublic')" @click="reimportPublicData(false)">
            <RefreshCw :size="16" />
            {{ actionLabel("importPublic", "资料导入", "导入中", "已导入", "导入失败") }}
          </button>
          <button class="secondary-action compact" type="button" :class="actionStatusClass('importBehavior')" :disabled="isActionBusy('importBehavior')" @click="reimportPublicData(true)">
            <Database :size="16" />
            {{ actionLabel("importBehavior", "刷新/重建明细", "重建中", "已重建", "重建失败") }}
          </button>
          <button class="secondary-action compact" type="button" :class="actionStatusClass('importBehavior')" :disabled="isActionBusy('importBehavior')" @click="triggerBehaviorUpload">
            <Upload :size="16" />
            导入行为 Excel
          </button>
          <button class="secondary-action compact" type="button" :class="actionStatusClass('uploadKnowledge')" :disabled="isActionBusy('uploadKnowledge')" @click="triggerKnowledgeUpload">
            <Upload :size="16" />
            {{ actionLabel("uploadKnowledge", "上传资料", "读取中", "已读取", "读取失败") }}
          </button>
          <button class="primary-action compact" type="button" @click="openKnowledgeEditor(null)">
            <FileText :size="16" />
            新增知识
          </button>
          <input ref="behaviorUploadInput" class="visually-hidden-file" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" @change="handleBehaviorUpload" />
          <input ref="knowledgeUploadInput" class="visually-hidden-file" type="file" accept=".docx,.txt,.md,.json,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,application/json" @change="handleKnowledgeUpload" />
        </div>
      </div>

      <div class="knowledge-layout">
        <section class="knowledge-control-card">
          <div class="admin-stat-strip knowledge-stat-strip">
            <article v-for="item in knowledgeStats" :key="item.label">
              <component :is="item.icon" :size="18" />
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <small>{{ item.detail }}</small>
            </article>
          </div>
          <div class="knowledge-filter-bar">
            <label>
              搜索资料
              <input v-model="knowledgeQuery" type="search" placeholder="按标题、正文、来源文件检索" />
            </label>
            <label>
              资料分类
              <select v-model="knowledgeCategory">
                <option value="all">全部分类</option>
                <option v-for="category in knowledgeCategories" :key="category" :value="category">{{ category }}</option>
              </select>
            </label>
            <span>显示 {{ filteredKnowledgeDocs.length }} / {{ knowledgeDocs.length }} 条资料</span>
          </div>
        </section>

        <section v-for="group in officialKnowledgeGroups" :key="group.key" class="knowledge-list-card official-package-card">
          <header>
            <h3>{{ group.label }}</h3>
            <span>{{ group.items.length }} 条资料</span>
          </header>
          <div class="official-package-list">
            <button
              v-for="document in group.items"
              :key="document.id"
              type="button"
              :class="{ active: selectedKnowledge?.id === document.id }"
              @click="openKnowledgeDetail(document)"
            >
              <strong>{{ document.title }}</strong>
              <span>{{ document.category || "官方资料包" }} · {{ document.status === "active" ? "启用" : "停用" }}</span>
            </button>
            <p v-if="!group.items.length" class="knowledge-empty-note">暂无资料。</p>
          </div>
        </section>

        <section class="knowledge-draft-card">
          <h3>低置信问答沉淀</h3>
          <article v-for="record in lowConfidenceRecords.slice(0, 3)" :key="record.id">
            <span>{{ record.question }}</span>
            <button class="ghost-action compact" type="button" :class="convertingChatId === record.id ? 'action-loading' : actionStatusClass('convertChat')" :disabled="convertingChatId === record.id" @click="convertRecordToKnowledge(record)">
              {{ convertingChatId === record.id ? "生成中" : actionStatus.convertChat === "error" ? "生成失败" : "转知识" }}
            </button>
          </article>
          <p v-if="!lowConfidenceRecords.length" class="knowledge-empty-note">暂无低置信问答。</p>
          <button class="secondary-action compact" type="button" @click="modal = 'records'">查看问答来源</button>
        </section>
      </div>
    </section>

    <AdminPersonaPage v-else-if="activeTab === 'persona'" :ctx="adminView" />

    <section v-else class="admin-page report-page report-dashboard-page">
      <div class="visitor-screen" aria-label="游客感受度可视化监测大屏">
        <i class="visitor-corner top-left"></i>
        <i class="visitor-corner top-right"></i>
        <i class="visitor-corner bottom-left"></i>
        <i class="visitor-corner bottom-right"></i>

        <header class="visitor-screen-header">
          <div class="visitor-screen-clock">
            <Clock3 :size="15" />
            <span>{{ reportRefreshTime }}</span>
          </div>
          <div class="visitor-screen-title">
            <small>游客感受度报告</small>
            <h2>游客体验分析</h2>
          </div>
          <div class="visitor-actions">
            <button type="button" @click="exportVisitorReport">
              <Download :size="15" />
              导出
            </button>
            <button type="button" @click="modal = 'reportDetail'">
              <FileText :size="15" />
              明细
            </button>
          </div>
        </header>

        <div class="visitor-grid">
          <section class="visitor-panel report-source-panel">
            <header>
              <strong>交互记录</strong>
              <small>{{ reportScopeLabel }}</small>
            </header>
            <article v-for="item in reportSourceCards" :key="item.label" class="source-line">
              <component :is="item.icon" :size="18" />
              <div>
                <small>{{ item.label }}</small>
                <strong>{{ item.value }}</strong>
                <span>{{ item.detail }}</span>
              </div>
            </article>
          </section>

          <section class="visitor-panel report-kpi-panel report-focus-panel">
            <header>
              <strong>游客关注点分析</strong>
              <small>TOP {{ reportAttentionItems.length }}</small>
            </header>
            <p v-if="!reportAttentionItems.length" class="knowledge-empty-note">暂无真实关注点记录。</p>
            <article v-for="item in reportAttentionItems" :key="item.label" class="focus-line" :class="`tone-${item.tone}`">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <i><b :style="{ width: item.percent }"></b></i>
            </article>
          </section>

          <section class="visitor-core-panel">
            <div class="visitor-core-frame">
              <div class="visitor-gauge" :style="{ '--score-angle': `${reportCompositeScore * 3.6}deg` }">
                <div>
                  <Gauge :size="26" />
                  <strong>{{ reportCompositeScore }}</strong>
                  <span>综合感受指数</span>
                </div>
              </div>
              <div class="visitor-core-copy">
                <small>满意度 {{ reportAverageSatisfaction.toFixed(1) }} / 5.0（{{ reportSatisfactionSourceLabel }}）</small>
                <h3>{{ reportPositiveRate }}% 正向情感</h3>
                <p>以满意评分、情感倾向、反馈痛点和行为样本命中情况合成游客感受判断。</p>
              </div>
              <div class="visitor-factor-grid">
                <article v-for="factor in reportExperienceFactors" :key="factor.label">
                  <component :is="factor.icon" :size="17" />
                  <span>{{ factor.label }}</span>
                  <strong>{{ factor.value }}%</strong>
                  <i><b :style="{ width: `${factor.value}%` }"></b></i>
                </article>
              </div>
            </div>
          </section>

          <section class="visitor-panel report-sentiment-panel">
            <header>
              <strong>情感趋势</strong>
              <small>{{ formatNumber(reportSentimentTotal) }} 条情感记录</small>
            </header>
            <article v-for="item in reportSentimentItems" :key="item.label" :class="`tone-${item.tone}`">
              <span>{{ item.label }}</span>
              <strong>{{ item.percent }}</strong>
              <i><b :style="{ width: item.percent }"></b></i>
              <small>{{ item.value }} 条</small>
            </article>
          </section>

          <section class="visitor-panel report-risk-panel">
            <header>
              <strong>服务建议</strong>
              <small>运营优化</small>
            </header>
            <article v-for="(item, index) in reportSuggestionItems" :key="item" class="service-suggestion-line risk-ok">
              <CheckCircle2 :size="17" />
              <div>
                <span>建议 {{ index + 1 }}</span>
                <strong>{{ item }}</strong>
              </div>
            </article>
          </section>

        </div>
      </div>
    </section>

    <AdminModalLayer v-if="modal" :ctx="adminView" />
  </main>
</template>
