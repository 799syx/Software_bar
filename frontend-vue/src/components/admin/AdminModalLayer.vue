<script setup lang="ts">
import type { AnalyticsOverview } from "../../types";
import type { useAdminView } from "./useAdminView";

type AdminViewContext = ReturnType<typeof useAdminView>;

const props = defineProps<{
  ctx: AdminViewContext;
  analytics: AnalyticsOverview;
}>();

const {
  MapPinned,
  Save,
  Trash2,
  X,
  actionLabel,
  actionStatus,
  actionStatusClass,
  adminSpots,
  closeModal,
  convertRecordToKnowledge,
  convertingChatId,
  deactivateSpot,
  deleteKnowledge,
  feedbackRecords,
  formatNumber,
  isActionBusy,
  knowledgeForm,
  lowConfidenceRecords,
  modal,
  openKnowledgeEditor,
  openSpotManager,
  personaForm,
  saveKnowledge,
  savePersona,
  saveSpot,
  selectedKnowledge,
  selectedSpot,
  selectedSpotId,
  sourceTypeLabel,
  spotForm,
  spotImagePreview,
  spotPhotoChoices,
  useFallbackImage,
  visibleRecords
} = props.ctx;
</script>

<template>
  <section v-if="modal" class="admin-modal-backdrop" @click.self="closeModal">
    <div class="admin-modal" :class="{ wide: modal === 'records' || modal === 'reportDetail' || modal === 'spots' || modal === 'knowledgeDetail' }">
      <header>
        <h2>
          {{
            modal === "knowledge"
              ? knowledgeForm.id ? "编辑知识文档" : "新增知识文档"
              : modal === "knowledgeDetail"
                ? "知识文档详情"
                : modal === "spots"
                  ? "景点点位管理"
                  : modal === "records"
                    ? "问答记录明细"
                    : modal === "personaAdvanced"
                      ? "数字人高级设置"
                      : "游客反馈明细"
          }}
        </h2>
        <button class="ghost-action compact icon-only" type="button" @click="closeModal"><X :size="17" /></button>
      </header>

      <form v-if="modal === 'knowledge'" class="modal-form" @submit.prevent="saveKnowledge">
        <div class="admin-form-grid">
          <label>标题<input v-model="knowledgeForm.title" required /></label>
          <label>分类<input v-model="knowledgeForm.category" /></label>
          <label>状态<select v-model="knowledgeForm.status"><option value="active">启用</option><option value="inactive">停用</option></select></label>
          <label>来源类型<select v-model="knowledgeForm.sourceType"><option value="manual">手工录入</option><option value="official_docx">官方 DOCX</option><option value="behavior_excel">行为 Excel</option><option value="chat_draft">问答沉淀</option><option value="seed">系统种子</option></select></label>
          <label>来源文件<input v-model="knowledgeForm.sourceFile" placeholder="资料文件名" /></label>
          <label>来源章节<input v-model="knowledgeForm.sourceSection" placeholder="章节、景点 ID 或问答 ID" /></label>
        </div>
        <label>内容<textarea v-model="knowledgeForm.content" required></textarea></label>
        <div class="editor-actions">
          <button class="primary-action compact" type="submit" :class="actionStatusClass('saveKnowledge')" :disabled="isActionBusy('saveKnowledge') || isActionBusy('deleteKnowledge')">
            <Save :size="16" />{{ actionLabel("saveKnowledge", "保存知识", "保存中", "已保存", "保存失败") }}
          </button>
          <button v-if="knowledgeForm.id" class="ghost-action compact danger" type="button" :class="actionStatusClass('deleteKnowledge')" :disabled="isActionBusy('saveKnowledge') || isActionBusy('deleteKnowledge')" @click="deleteKnowledge">
            <Trash2 :size="16" />{{ actionLabel("deleteKnowledge", "删除", "删除中", "已删除", "删除失败") }}
          </button>
        </div>
      </form>

      <div v-else-if="modal === 'knowledgeDetail'" class="modal-list knowledge-detail-modal">
        <article v-if="selectedKnowledge" class="knowledge-detail-full">
          <header>
            <div>
              <h3>{{ selectedKnowledge.title }}</h3>
              <span>{{ selectedKnowledge.category }} · {{ sourceTypeLabel(selectedKnowledge.sourceType) }} · {{ selectedKnowledge.status === "active" ? "启用" : "停用" }}</span>
            </div>
            <button class="secondary-action compact" type="button" @click="openKnowledgeEditor(selectedKnowledge)">编辑</button>
          </header>
          <div class="source-ref-row">
            <span>来源文件：{{ selectedKnowledge.sourceFile || "未填写" }}</span>
            <span>来源章节：{{ selectedKnowledge.sourceSection || "未填写" }}</span>
            <span>更新时间：{{ selectedKnowledge.updatedAt ? new Date(selectedKnowledge.updatedAt * 1000).toLocaleString() : "未知" }}</span>
          </div>
          <p>{{ selectedKnowledge.content }}</p>
        </article>
        <p v-else class="knowledge-empty-note">当前没有可查看的知识文档。</p>
      </div>

      <form v-else-if="modal === 'spots'" class="modal-form" @submit.prevent="saveSpot">
        <div class="modal-two-col">
          <aside class="compact-spot-list">
            <button v-for="spot in adminSpots.slice(0, 12)" :key="spot.id" type="button" :class="{ active: selectedSpotId === spot.id }" @click="openSpotManager(spot)">
              <MapPinned :size="15" /> {{ spot.name }}
            </button>
          </aside>
          <div class="admin-form-grid">
            <label>景点名称<input v-model="spotForm.name" required /></label>
            <label>开放信息<input v-model="spotForm.openTime" /></label>
            <label>位置<input v-model="spotForm.location" /></label>
            <label>标签<input v-model="spotForm.tagsText" /></label>
            <label>地图分区<select v-model="spotForm.mapZone"><option value="lingshan">灵山胜境</option><option value="nianhua">拈花湾</option></select></label>
            <label>状态<select v-model="spotForm.status"><option value="active">启用</option><option value="inactive">停用</option></select></label>
            <label>点位码<input :value="spotForm.id ? selectedSpot?.locationCode || `SPOT-${spotForm.id}` : '保存后生成'" readonly /></label>
            <label class="checkbox-field"><input v-model="spotForm.verifiedLocation" type="checkbox" /> 已现场校准</label>
            <label>景点图片<select v-model="spotForm.image"><option value="">按景点名称自动匹配</option><option v-for="photo in spotPhotoChoices" :key="photo.key" :value="photo.key">{{ photo.title }} · {{ photo.key }}</option></select></label>
            <label>图片 key / URL<input v-model="spotForm.image" placeholder="grand-buddha 或 /assets/scenic/photos/..." /></label>
            <label>地图 X<input v-model.number="spotForm.mapX" type="number" min="0" max="1000" /></label>
            <label>地图 Y<input v-model.number="spotForm.mapY" type="number" min="0" max="620" /></label>
            <label>纬度<input v-model.number="spotForm.lat" type="number" step="0.000001" /></label>
            <label>经度<input v-model.number="spotForm.lon" type="number" step="0.000001" /></label>
            <label>建议时长<input v-model.number="spotForm.duration" type="number" min="5" max="480" /></label>
            <label>热度<input v-model.number="spotForm.popularity" type="number" min="0" max="100" /></label>
          </div>
        </div>
        <figure class="spot-image-preview">
          <img :src="spotImagePreview" :alt="`${spotForm.name || '景点'}图片预览`" @error="useFallbackImage" />
          <figcaption>图片预览：{{ spotForm.image || "按名称/标签自动匹配" }}</figcaption>
        </figure>
        <label>简介<textarea v-model="spotForm.description" required></textarea></label>
        <label>讲解词<textarea v-model="spotForm.story" required></textarea></label>
        <div class="editor-actions">
          <button class="primary-action compact" type="submit" :class="actionStatusClass('saveSpot')" :disabled="isActionBusy('saveSpot') || isActionBusy('deleteSpot')">
            <Save :size="16" />{{ actionLabel("saveSpot", "保存点位", "保存中", "已保存", "保存失败") }}
          </button>
          <button v-if="spotForm.id" class="ghost-action compact danger" type="button" :class="actionStatusClass('deleteSpot')" :disabled="isActionBusy('saveSpot') || isActionBusy('deleteSpot')" @click="deactivateSpot">
            <Trash2 :size="16" />{{ actionLabel("deleteSpot", "停用", "停用中", "已停用", "停用失败") }}
          </button>
        </div>
      </form>

      <div v-else-if="modal === 'records'" class="modal-list">
        <article v-for="record in visibleRecords" :key="record.id" class="record-row">
          <div>
            <strong>{{ record.question }}</strong>
            <p>{{ record.answer }}</p>
            <small>来源：{{ record.sourceRefs?.map((ref) => ref.title).join("、") || "暂无" }}</small>
          </div>
          <aside>
            <span>{{ record.intent || "导览咨询" }}</span>
            <small>置信度 {{ Math.round((record.confidence || 0) * 100) }}%</small>
            <button v-if="(record.confidence || 0) < 0.65" class="ghost-action compact" type="button" :class="convertingChatId === record.id ? 'action-loading' : actionStatusClass('convertChat')" :disabled="convertingChatId === record.id" @click="convertRecordToKnowledge(record)">
              {{ convertingChatId === record.id ? "生成中" : actionStatus.convertChat === "error" ? "生成失败" : "转知识" }}
            </button>
          </aside>
        </article>
      </div>

      <form v-else-if="modal === 'personaAdvanced'" class="modal-form" @submit.prevent="savePersona">
        <label>开场问候<textarea v-model="personaForm.greeting" required></textarea></label>
        <label>讲解风格<input v-model="personaForm.style" /></label>
        <label>表情口型策略<input v-model="personaForm.expressionProfile" /></label>
        <div class="editor-actions">
          <button class="primary-action compact" type="submit" :class="actionStatusClass('savePersona')" :disabled="isActionBusy('savePersona')">
            <Save :size="16" />{{ actionLabel("savePersona", "保存高级设置", "保存中", "已保存", "保存失败") }}
          </button>
        </div>
      </form>

      <div v-else class="modal-list">
        <article v-for="record in feedbackRecords" :key="record.id" class="record-row">
          <div>
            <strong>{{ record.question }}</strong>
            <p>{{ record.answer }}</p>
          </div>
          <aside>
            <span>{{ record.satisfaction }} 分</span>
            <small>{{ record.sentiment }}</small>
          </aside>
        </article>
        <article class="data-source-note">
          <strong>服务记录口径</strong>
          <span>当前展示系统问答、游客反馈和知识沉淀记录。</span>
          <small>低置信问题 {{ formatNumber(lowConfidenceRecords.length) }} 条；平均满意度 {{ Number(analytics.averageSatisfaction || 4.6).toFixed(1) }} 分。</small>
        </article>
      </div>
    </div>
  </section>
</template>
