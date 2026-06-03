<script setup lang="ts">
import { computed, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { Button, Tag } from 'ant-design-vue';

import StageAssertGen from './components/StageAssertGen.vue';
import StageCodeLocate from './components/StageCodeLocate.vue';
import StageFuzz from './components/StageFuzz.vue';
import StageResultVerification from './components/StageResultVerification.vue';
import StageRuleConfirm from './components/StageRuleConfirm.vue';
import StageSetup from './components/StageSetup.vue';
import { STAGE_LIST } from './types';
import { useWorkbench } from './useWorkbench';
import { formatDuration, formatTime } from './utils';

const {
  stage,
  activeStageView,
  stageStatus,
  stageMessage,
  elapsedSeconds,
  startedAt,
  isStopping,
  isTransitioning,
  errorMessage,
  projectConfig,
  selectedRule,
  staticLogHtml,
  staticLogText,
  staticResult,
  codeLocateEvidence,
  assertLogText,
  assertDiffContent,
  assertResult,
  fuzzLogs,
  fuzzStats,
  fuzzSpeedSeries,
  commitSetup,
  backToSetup,
  selectStageView,
  startPipeline,
  stopPipeline,
  resetWorkbench,
} = useWorkbench();

const isRunning = computed(() => {
  return (
    stageStatus.code_locate === 'running' ||
    stageStatus.assert_gen === 'running' ||
    stageStatus.fuzz === 'running' ||
    isTransitioning.value
  );
});

const elapsedDisplay = computed(() => formatDuration(elapsedSeconds.value));

const currentRuleText = computed(() => {
  return (
    selectedRule.value?.rule ||
    selectedRule.value?.description ||
    '请选择规则后启动自动化流水线'
  );
});

const currentRuleId = computed(() => {
  const optionId = (selectedRule.value as { id?: string } | null)?.id;
  const matched = currentRuleText.value.match(/\[(MQTT-[^\]]+)\]/i)?.[1];
  return matched || optionId || '未选择';
});

const taskTitle = computed(() => {
  if (projectConfig.protocolType === 'MQTT') {
    return `${projectConfig.implementation} MQTT Broker 分析任务`;
  }
  return `${projectConfig.protocolType} 协议实现分析任务`;
});

const protocolVersion = computed(() => {
  if (projectConfig.protocolType === 'MQTT') return 'MQTT 3.1.1';
  return 'SNMP v2c/v3';
});

const startedAtDisplay = computed(() => {
  return startedAt.value ? formatTime(startedAt.value.toISOString()) : '-';
});

const sourceArchiveName = computed(() => projectConfig.archive?.name || '未上传');

const sideNavItems = [
  { icon: 'mdi:view-dashboard-outline', key: 'overview', label: '概览' },
  { icon: 'mdi:briefcase-outline', key: 'workbench', label: '工作台' },
  { icon: 'mdi:clipboard-text-clock-outline', key: 'logs', label: '日志' },
] as const;

type SideNavKey = (typeof sideNavItems)[number]['key'];

const activeSideNav = ref<SideNavKey>('overview');

const activeSideNavLabel = computed(() => {
  return (
    sideNavItems.find((item) => item.key === activeSideNav.value)?.label ||
    '概览'
  );
});

function stageStateLabel(key: (typeof STAGE_LIST)[number]['key']) {
  const status = stageStatus[key];
  if (status === 'done') return '已完成';
  if (status === 'running') return '进行中';
  if (status === 'skipped') return '已跳过';
  if (status === 'error') return '异常';
  return stage.value === key ? '当前' : '等待中';
}

function canViewStage(key: (typeof STAGE_LIST)[number]['key']) {
  return stage.value === key || stageStatus[key] !== 'idle';
}

function handleStageSelect(key: (typeof STAGE_LIST)[number]['key']) {
  selectStageView(key);
}

function switchRule() {
  if (isRunning.value) return;
  resetWorkbench();
  stageStatus.setup = 'done';
  stage.value = 'rule_confirm';
  activeStageView.value = 'rule_confirm';
  stageMessage.value = '请选择一条规则后启动自动化流水线';
}
</script>

<template>
  <Page>
    <div class="guard-shell">
      <header class="guard-topbar">
        <div class="topbar-left">
          <div class="brand-mark">
            <IconifyIcon icon="mdi:shield-check-outline" />
          </div>
          <div class="brand-name">ProtocolGuard</div>
          <div class="topbar-divider" />
          <div class="topbar-section">{{ activeSideNavLabel }}</div>
        </div>

        <div v-if="activeSideNav === 'workbench'" class="topbar-actions">
          <div class="runtime-status" :class="{ 'runtime-status--idle': !isRunning }">
            <span class="status-dot" />
            <span>{{ isRunning ? '运行中' : '空闲' }}</span>
          </div>
          <div class="runtime-clock">{{ elapsedDisplay }}</div>
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
          <Button disabled>
            <template #icon><IconifyIcon icon="mdi:download" /></template>
            导出报告
          </Button>
          <div class="avatar">PG</div>
        </div>
      </header>

      <div class="guard-layout">
        <aside class="guard-sidebar">
          <nav class="sidebar-nav">
            <button
              v-for="item in sideNavItems"
              :key="item.key"
              class="nav-item"
              :class="{ 'nav-item--active': item.key === activeSideNav }"
              type="button"
              @click="activeSideNav = item.key"
            >
              <IconifyIcon :icon="item.icon" />
              <span>{{ item.label }}</span>
            </button>
          </nav>

          <section v-if="activeSideNav === 'workbench'" class="current-task">
            <div class="current-task-title">当前任务</div>
            <dl>
              <div>
                <dt>项目:</dt>
                <dd>{{ projectConfig.protocolType }} ({{ projectConfig.implementation }})</dd>
              </div>
              <div>
                <dt>协议版本:</dt>
                <dd>{{ protocolVersion }}</dd>
              </div>
              <div>
                <dt>源码包:</dt>
                <dd>{{ sourceArchiveName }}</dd>
              </div>
              <div>
                <dt>开始时间:</dt>
                <dd>{{ startedAtDisplay }}</dd>
              </div>
            </dl>
          </section>
        </aside>

        <main class="guard-main">
          <section v-if="activeSideNav === 'overview'" class="overview-blank" />

          <section v-else-if="activeSideNav === 'workbench'" class="task-shell">
            <header class="task-header">
              <div class="task-heading">
                <div class="task-title-line">
                  <h1>{{ taskTitle }}</h1>
                  <Tag color="blue">{{ protocolVersion }}</Tag>
                </div>
                <div class="task-rule">
                  <span>规则:</span>
                  <strong>{{ currentRuleId }}</strong>
                  <code>{{ currentRuleText }}</code>
                </div>
              </div>
              <Button
                :disabled="isRunning || stage === 'setup'"
                @click="switchRule"
              >
                切换规则
                <template #icon><IconifyIcon icon="mdi:chevron-down" /></template>
              </Button>
            </header>

            <section class="pipeline-stepper">
              <button
                v-for="(s, idx) in STAGE_LIST"
                :key="s.key"
                class="stepper-item"
                :class="{
                  'stepper-item--active':
                    stageStatus[s.key] === 'running' ||
                    (stage === s.key && stageStatus[s.key] !== 'done'),
                  'stepper-item--selected': activeStageView === s.key,
                  'stepper-item--done': stageStatus[s.key] === 'done',
                  'stepper-item--skipped': stageStatus[s.key] === 'skipped',
                  'stepper-item--error': stageStatus[s.key] === 'error',
                }"
                :disabled="!canViewStage(s.key)"
                type="button"
                @click="handleStageSelect(s.key)"
              >
                <div class="stepper-circle">
                  <IconifyIcon v-if="stageStatus[s.key] === 'done'" icon="mdi:check" />
                  <IconifyIcon
                    v-else-if="stageStatus[s.key] === 'skipped'"
                    icon="mdi:debug-step-over"
                  />
                  <IconifyIcon v-else-if="stageStatus[s.key] === 'error'" icon="mdi:close" />
                  <span v-else>{{ s.index }}</span>
                </div>
                <div class="stepper-copy">
                  <div class="stepper-title">{{ s.index }} {{ s.title }}</div>
                  <div class="stepper-state">{{ stageStateLabel(s.key) }}</div>
                </div>
                <div v-if="idx < STAGE_LIST.length - 1" class="stepper-arrow">
                  <IconifyIcon icon="mdi:arrow-right" />
                </div>
              </button>
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
                v-if="activeStageView === 'setup'"
                :config="projectConfig"
                :disabled="isRunning"
                @commit="commitSetup"
              />

              <StageRuleConfirm
                v-else-if="activeStageView === 'rule_confirm'"
                :protocol-type="projectConfig.protocolType"
                :rules-file="projectConfig.rules"
                :disabled="isRunning"
                @start="startPipeline"
                @back="backToSetup"
              />

              <StageCodeLocate
                v-else-if="activeStageView === 'code_locate'"
                :evidence="codeLocateEvidence"
                :log-html="staticLogHtml"
                :log-text="staticLogText"
                :result="staticResult"
                :rule="selectedRule"
                :running="stageStatus.code_locate === 'running'"
              />

              <StageAssertGen
                v-else-if="activeStageView === 'assert_gen'"
                :log-text="assertLogText"
                :diff-content="assertDiffContent"
                :result="assertResult"
                :running="stageStatus.assert_gen === 'running'"
              />

              <StageFuzz
                v-else-if="activeStageView === 'fuzz'"
                :elapsed="elapsedDisplay"
                :implementation="projectConfig.implementation"
                :logs="fuzzLogs"
                :protocol-type="projectConfig.protocolType"
                :rule="selectedRule"
                :stats="fuzzStats"
                :speed-series="fuzzSpeedSeries"
                :running="stageStatus.fuzz === 'running'"
              />

              <StageResultVerification
                v-else-if="activeStageView === 'done'"
                :assert-diff-content="assertDiffContent"
                :assert-result="assertResult"
                :evidence="codeLocateEvidence"
                :implementation="projectConfig.implementation"
                :logs="fuzzLogs"
                :protocol-type="projectConfig.protocolType"
                :rule="selectedRule"
                :static-result="staticResult"
                :stats="fuzzStats"
              />
            </section>
          </section>

          <section v-else class="overview-blank" />
        </main>
      </div>
    </div>
  </Page>
</template>

<style scoped>
.guard-shell {
  min-height: calc(100vh - 92px);
  overflow: hidden;
  color: #111827;
  background: #f6f8fb;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}

.guard-topbar {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 18px;
  background: #fff;
  border-bottom: 1px solid #e7edf5;
}

.topbar-left,
.topbar-actions {
  display: flex;
  gap: 14px;
  align-items: center;
}

.brand-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  font-size: 24px;
  color: #1677ff;
  border: 1px solid #cfe3ff;
  border-radius: 8px;
}

.brand-name {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0;
}

.topbar-divider {
  width: 1px;
  height: 26px;
  background: #e2e8f0;
}

.topbar-section {
  font-size: 15px;
  font-weight: 700;
}

.runtime-status {
  display: inline-flex;
  gap: 7px;
  align-items: center;
  font-size: 13px;
  font-weight: 700;
  color: #0f9f6e;
}

.runtime-status--idle {
  color: #64748b;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: currentcolor;
  border-radius: 50%;
}

.runtime-clock {
  min-width: 74px;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-weight: 700;
  text-align: right;
}

.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  font-size: 13px;
  font-weight: 800;
  color: #fff;
  background: #1677ff;
  border-radius: 50%;
}

.guard-layout {
  display: grid;
  grid-template-columns: 236px minmax(0, 1fr);
  min-height: calc(100vh - 156px);
}

.guard-sidebar {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 18px 14px;
  background: #fff;
  border-right: 1px solid #e7edf5;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  display: flex;
  gap: 12px;
  align-items: center;
  width: 100%;
  height: 44px;
  padding: 0 14px;
  font-size: 14px;
  font-weight: 700;
  color: #24324b;
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 6px;
}

.nav-item :first-child {
  font-size: 19px;
}

.nav-item--active {
  color: #1677ff;
  background: #edf5ff;
}

.current-task {
  padding: 16px;
  background: #fff;
  border: 1px solid #e7edf5;
  border-radius: 8px;
  box-shadow: 0 8px 22px rgb(15 23 42 / 4%);
}

.current-task-title {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 800;
}

.current-task dl {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 0;
}

.current-task div {
  min-width: 0;
}

.current-task dt {
  margin-bottom: 2px;
  font-size: 12px;
  color: #64748b;
}

.current-task dd {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  font-size: 12px;
  font-weight: 600;
  color: #172033;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.guard-main {
  min-width: 0;
  padding: 0;
}

.overview-blank {
  min-height: 100%;
}

.task-shell {
  min-height: 100%;
  padding: 24px 28px 28px;
}

.task-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 18px;
}

.task-heading {
  min-width: 0;
}

.task-title-line {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.task-title-line h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  line-height: 1.25;
  letter-spacing: 0;
}

.task-rule {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 7px;
  font-size: 13px;
  color: #475569;
}

.task-rule strong {
  color: #172033;
}

.task-rule code {
  max-width: min(860px, 100%);
  padding: 2px 6px;
  overflow: hidden;
  color: #172033;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: #eef5ff;
  border: 1px solid #dceaff;
  border-radius: 4px;
}

.pipeline-stepper {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  align-items: center;
  margin-bottom: 18px;
  padding: 18px 20px;
  background: #fff;
  border: 1px solid #e7edf5;
  border-radius: 8px;
  box-shadow: 0 8px 22px rgb(15 23 42 / 4%);
}

.stepper-item {
  position: relative;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 24px;
  gap: 12px;
  align-items: center;
  width: 100%;
  min-width: 0;
  padding: 0;
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 8px;
}

.stepper-item:last-child {
  grid-template-columns: 42px minmax(0, 1fr);
}

.stepper-item:disabled {
  cursor: default;
}

.stepper-item--selected {
  outline: 2px solid rgb(22 119 255 / 16%);
  outline-offset: 6px;
}

.stepper-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  font-size: 16px;
  font-weight: 800;
  color: #1f2937;
  background: #eef2f7;
  border: 1px solid #e2e8f0;
  border-radius: 50%;
}

.stepper-copy {
  min-width: 0;
}

.stepper-title {
  overflow: hidden;
  font-size: 14px;
  font-weight: 800;
  color: #111827;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stepper-state {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.stepper-arrow {
  color: #94a3b8;
}

.stepper-item--active .stepper-circle {
  color: #fff;
  background: #1677ff;
  border-color: #1677ff;
  box-shadow: 0 0 0 4px rgb(22 119 255 / 12%);
}

.stepper-item--active .stepper-state {
  color: #1677ff;
  font-weight: 700;
}

.stepper-item--done .stepper-circle {
  color: #fff;
  background: #28a879;
  border-color: #28a879;
}

.stepper-item--skipped .stepper-circle {
  color: #1f2937;
  background: #f8fafc;
  border-color: #94a3b8;
}

.stepper-item--skipped .stepper-state {
  color: #475569;
  font-weight: 700;
}

.stepper-item--error .stepper-circle {
  color: #fff;
  background: #ef4444;
  border-color: #ef4444;
}

.stepper-item--error .stepper-state {
  color: #dc2626;
  font-weight: 700;
}

.workbench-banner,
.workbench-error {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 14px;
  padding: 11px 14px;
  font-size: 13px;
  border-radius: 8px;
}

.workbench-banner {
  color: #0b5cad;
  background: #eef6ff;
  border: 1px solid #d7eaff;
}

.workbench-error {
  color: #dc2626;
  background: #fff5f5;
  border: 1px solid #ffd6d6;
}

.workbench-content {
  min-height: 420px;
}

@media (max-width: 1180px) {
  .guard-layout {
    grid-template-columns: 1fr;
  }

  .guard-sidebar {
    display: none;
  }

  .pipeline-stepper {
    grid-template-columns: 1fr;
  }

  .stepper-item,
  .stepper-item:last-child {
    grid-template-columns: 42px minmax(0, 1fr);
  }

  .stepper-arrow {
    display: none;
  }
}

@media (max-width: 760px) {
  .guard-topbar,
  .task-header,
  .topbar-actions {
    align-items: flex-start;
  }

  .guard-topbar,
  .task-header {
    flex-direction: column;
    height: auto;
    padding: 16px;
  }

  .topbar-actions {
    flex-wrap: wrap;
  }

  .task-shell {
    padding: 18px 14px;
  }
}
</style>
