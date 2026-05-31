<script setup lang="ts">
import { computed } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { Button, Tag } from 'ant-design-vue';

import StageAssertGen from './components/StageAssertGen.vue';
import StageCodeLocate from './components/StageCodeLocate.vue';
import StageFuzz from './components/StageFuzz.vue';
import StageRuleConfirm from './components/StageRuleConfirm.vue';
import StageSetup from './components/StageSetup.vue';
import { STAGE_LIST } from './types';
import { useWorkbench } from './useWorkbench';
import { formatDuration } from './utils';

const {
  stage,
  stageStatus,
  stageMessage,
  elapsedSeconds,
  isStopping,
  errorMessage,
  projectConfig,
  selectedRule,
  staticLogHtml,
  staticResult,
  assertLogText,
  assertDiffContent,
  assertResult,
  fuzzLogs,
  fuzzStats,
  fuzzSpeedSeries,
  commitSetup,
  backToSetup,
  startPipeline,
  stopPipeline,
  resetWorkbench,
} = useWorkbench();

const isRunning = computed(() => {
  return (
    stageStatus.code_locate === 'running' ||
    stageStatus.assert_gen === 'running' ||
    stageStatus.fuzz === 'running'
  );
});

const elapsedDisplay = computed(() => formatDuration(elapsedSeconds.value));

const currentStageIndex = computed(() => {
  const idx = STAGE_LIST.findIndex((s) => s.key === stage.value);
  return idx >= 0 ? idx : 0;
});
</script>

<template>
  <Page>
    <div class="workbench-shell">
      <aside class="workbench-sidebar">
        <div class="sidebar-brand">
          <div class="brand-icon">
            <IconifyIcon icon="mdi:shield-check" />
          </div>
          <div class="brand-text">
            <div class="brand-name">协议合规分析</div>
            <div class="brand-sub">工作台</div>
          </div>
        </div>

        <div class="sidebar-info">
          <div class="info-title">当前配置</div>
          <dl class="info-list">
            <div>
              <dt>协议</dt>
              <dd>{{ projectConfig.protocolType }}</dd>
            </div>
            <div>
              <dt>实现</dt>
              <dd>{{ projectConfig.implementation }}</dd>
            </div>
            <div>
              <dt>目标</dt>
              <dd>{{ projectConfig.targetHost }}:{{ projectConfig.targetPort }}</dd>
            </div>
            <div v-if="selectedRule">
              <dt>规则</dt>
              <dd>{{ selectedRule.description?.slice(0, 30) || 'N/A' }}</dd>
            </div>
          </dl>
        </div>
      </aside>

      <main class="workbench-main">
        <header class="workbench-header">
          <div class="header-left">
            <h2 class="header-title">协议合规分析流水线</h2>
            <div v-if="selectedRule" class="header-rule">
              <span class="rule-label">当前规则:</span>
              <code>{{ selectedRule.description }}</code>
            </div>
          </div>
          <div class="header-right">
            <div class="header-status" :class="{ 'header-status--idle': !isRunning }">
              <span class="status-dot" />
              <span>{{ isRunning ? '运行中' : '空闲' }}</span>
            </div>
            <div class="header-elapsed">{{ elapsedDisplay }}</div>
            <Button
              v-if="isRunning"
              danger
              :loading="isStopping"
              @click="stopPipeline"
            >
              <template #icon><IconifyIcon icon="mdi:stop" /></template>
              停止
            </Button>
            <Button v-else @click="resetWorkbench">
              <template #icon><IconifyIcon icon="mdi:refresh" /></template>
              重置
            </Button>
          </div>
        </header>

        <section class="workbench-stepper">
          <div
            v-for="(s, idx) in STAGE_LIST"
            :key="s.key"
            class="stepper-item"
            :class="{
              'stepper-item--done': stageStatus[s.key] === 'done',
              'stepper-item--active': stageStatus[s.key] === 'running',
              'stepper-item--error': stageStatus[s.key] === 'error',
            }"
          >
            <div class="stepper-circle">
              <IconifyIcon v-if="stageStatus[s.key] === 'done'" icon="mdi:check" />
              <IconifyIcon v-else-if="stageStatus[s.key] === 'error'" icon="mdi:close" />
              <span v-else>{{ s.index }}</span>
            </div>
            <div class="stepper-label">{{ s.title }}</div>
            <div v-if="idx < STAGE_LIST.length - 1" class="stepper-arrow">
              <IconifyIcon icon="mdi:chevron-right" />
            </div>
          </div>
        </section>

        <section v-if="stageMessage" class="workbench-banner">
          <IconifyIcon icon="mdi:information-outline" />
          <span>{{ stageMessage }}</span>
        </section>

        <section v-if="errorMessage" class="workbench-error">
          <IconifyIcon icon="mdi:alert-circle" />
          <span>{{ errorMessage }}</span>
        </section>

        <section class="workbench-content">
          <StageSetup
            v-if="stage === 'setup'"
            :config="projectConfig"
            :disabled="isRunning"
            @commit="commitSetup"
          />

          <StageRuleConfirm
            v-else-if="stage === 'rule_confirm'"
            :protocol-type="projectConfig.protocolType"
            :disabled="isRunning"
            @start="startPipeline"
            @back="backToSetup"
          />

          <StageCodeLocate
            v-else-if="stage === 'code_locate'"
            :log-html="staticLogHtml"
            :result="staticResult"
            :running="stageStatus.code_locate === 'running'"
          />

          <StageAssertGen
            v-else-if="stage === 'assert_gen'"
            :log-text="assertLogText"
            :diff-content="assertDiffContent"
            :result="assertResult"
            :running="stageStatus.assert_gen === 'running'"
          />

          <StageFuzz
            v-else-if="stage === 'fuzz' || stage === 'done'"
            :logs="fuzzLogs"
            :stats="fuzzStats"
            :speed-series="fuzzSpeedSeries"
            :running="stageStatus.fuzz === 'running'"
          />
        </section>
      </main>
    </div>
  </Page>
</template>

<style scoped>
.workbench-shell {
  display: grid;
  grid-template-columns: 260px 1fr;
  min-height: calc(100vh - 120px);
  gap: 16px;
}

.workbench-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 12px;
}

.sidebar-brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--ant-color-border-secondary);
}

.brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  font-size: 22px;
  color: #fff;
  background: linear-gradient(135deg, #1677ff, #4096ff);
  border-radius: 10px;
}

.brand-name {
  font-size: 15px;
  font-weight: 600;
}

.brand-sub {
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.sidebar-info {
  padding: 14px;
  background: var(--ant-color-fill-quaternary);
  border-radius: 10px;
}

.info-title {
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  font-size: 12px;
}

.info-list > div {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.info-list dt {
  color: var(--ant-text-color-secondary);
}

.info-list dd {
  margin: 0;
  font-weight: 500;
  text-align: right;
}

.workbench-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.workbench-header {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 12px;
}

.header-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.header-rule {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 4px;
  font-size: 13px;
}

.rule-label {
  color: var(--ant-text-color-secondary);
}

.header-rule code {
  padding: 2px 8px;
  font-size: 12px;
  background: var(--ant-color-fill-quaternary);
  border-radius: 4px;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.header-status {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  color: #16a34a;
  background: rgb(22 163 74 / 12%);
  border-radius: 999px;
}

.header-status--idle {
  color: var(--ant-text-color-secondary);
  background: var(--ant-color-fill-quaternary);
}

.status-dot {
  width: 6px;
  height: 6px;
  background: currentcolor;
  border-radius: 50%;
}

.header-elapsed {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 14px;
  font-weight: 500;
}

.workbench-stepper {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 18px 20px;
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 12px;
}

.stepper-item {
  display: flex;
  flex: 1;
  gap: 10px;
  align-items: center;
}

.stepper-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ant-text-color-secondary);
  background: var(--ant-color-fill-quaternary);
  border-radius: 50%;
  transition: all 0.3s;
}

.stepper-item--active .stepper-circle {
  color: #fff;
  background: #1677ff;
  box-shadow: 0 0 0 4px rgb(22 119 255 / 15%);
}

.stepper-item--done .stepper-circle {
  color: #fff;
  background: #16a34a;
}

.stepper-item--error .stepper-circle {
  color: #fff;
  background: #dc2626;
}

.stepper-label {
  font-size: 14px;
  font-weight: 500;
}

.stepper-arrow {
  margin-left: auto;
  font-size: 18px;
  color: var(--ant-color-border);
}

.workbench-banner {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px 16px;
  font-size: 13px;
  color: var(--ant-text-color);
  background: rgb(22 119 255 / 6%);
  border: 1px solid rgb(22 119 255 / 18%);
  border-radius: 10px;
}

.workbench-banner :first-child {
  font-size: 16px;
  color: #1677ff;
}

.workbench-error {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px 16px;
  font-size: 13px;
  color: #dc2626;
  background: rgb(220 38 38 / 6%);
  border: 1px solid rgb(220 38 38 / 18%);
  border-radius: 10px;
}

.workbench-error :first-child {
  font-size: 16px;
}

.workbench-content {
  min-height: 400px;
}
</style>
