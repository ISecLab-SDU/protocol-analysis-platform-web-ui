<script setup lang="ts">
import type {
  ProtocolDatabaseOverviewStats,
  ProtocolDatabaseOverviewSummary,
  ProtocolStaticAnalysisRuleResultStatus,
  ProtocolViolationHistoryEntry,
} from '#/api/protocol-compliance';

import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { Button, message, Popconfirm, Select, Tag } from 'ant-design-vue';

import {
  deleteProtocolViolationHistory,
  fetchProtocolDatabaseOverview,
  fetchProtocolViolationHistory,
} from '#/api/protocol-compliance';

import StageAssertGen from './components/StageAssertGen.vue';
import StageCodeLocate from './components/StageCodeLocate.vue';
import StageFuzz from './components/StageFuzz.vue';
import StageResultVerification from './components/StageResultVerification.vue';
import StageRuleConfirm from './components/StageRuleConfirm.vue';
import StageRuleExtract from './components/StageRuleExtract.vue';
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
  isAwaitingAssertConfirmation,
  demoModeActive,
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
  aflNetPocPath,
  fuzzStats,
  fuzzSpeedSeries,
  commitSetup,
  confirmAssertGeneration,
  backToSetup,
  selectStageView,
  startPipeline,
  stopPipeline,
  resetWorkbench,
  loadDemoConfig,
  canViewStage,
} = useWorkbench();

const isRunning = computed(() => {
  return (
    stageStatus.code_locate === 'running' ||
    stageStatus.assert_gen === 'running' ||
    stageStatus.fuzz === 'running' ||
    isTransitioning.value ||
    isAwaitingAssertConfirmation.value
  );
});

const elapsedDisplay = computed(() => formatDuration(elapsedSeconds.value));

const currentRuleText = computed(() => {
  return (
    selectedRule.value?.rule ||
    selectedRule.value?.description ||
    '请选择规则后启动自动化分析流程'
  );
});

const currentRuleId = computed(() => {
  const optionId = (selectedRule.value as null | { id?: string })?.id;
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
  return `${projectConfig.protocolType} ${projectConfig.protocolVersion}`;
});

const startedAtDisplay = computed(() => {
  return startedAt.value ? formatTime(startedAt.value.toISOString()) : '-';
});

const sourceArchiveName = computed(
  () => projectConfig.archive?.name || '未上传',
);

const sideNavItems = [
  { icon: 'mdi:view-dashboard-outline', key: 'overview', label: '概览' },
  { icon: 'mdi:briefcase-outline', key: 'workbench', label: '工作台' },
  { icon: 'mdi:clipboard-text-clock-outline', key: 'logs', label: '历史结果' },
] as const;

const workbenchSubNavItems = [
  { icon: 'mdi:file-document-edit-outline', key: 'extract', label: '规则提取' },
  { icon: 'mdi:playlist-check', key: 'workbench', label: '分析流程' },
] as const;

type SideNavKey =
  | (typeof sideNavItems)[number]['key']
  | (typeof workbenchSubNavItems)[number]['key'];

const activeSideNav = ref<SideNavKey>('overview');
const demoConfigLoading = ref(false);
const VISIBLE_HISTORY_LIMIT = 5;
const violationHistory = ref<ProtocolViolationHistoryEntry[]>([]);
const violationHistoryError = ref('');
const violationHistoryGeneratedAt = ref('');
const violationHistoryLoaded = ref(false);
const violationHistoryLoading = ref(false);
const violationHistoryRefreshQueued = ref(false);
const violationHistoryQueuedRefreshOverview = ref(false);
const violationHistoryWarnings = ref<string[]>([]);
const selectedViolationHistoryId = ref('');
const deletingViolationHistoryId = ref('');
const bannerProgress = ref(0);
let bannerProgressStageKey = '';
let bannerProgressTimer: null | ReturnType<typeof setTimeout> = null;
const historyFilters = reactive<{
  implementation: string;
  protocol: string;
  result: '' | ProtocolStaticAnalysisRuleResultStatus;
  timeRange: '' | 'month' | 'week' | 'year';
}>({
  implementation: '',
  protocol: '',
  result: '',
  timeRange: '',
});

const activeSideNavLabel = computed(() => {
  if (activeSideNav.value === 'extract') return '工作台 / 规则提取';
  if (activeSideNav.value === 'workbench') return '工作台 / 分析流程';
  return (
    sideNavItems.find((item) => item.key === activeSideNav.value)?.label ||
    '概览'
  );
});

const isWorkbenchSectionActive = computed(() =>
  ['extract', 'workbench'].includes(activeSideNav.value),
);

const violationHistoryRefreshing = computed(
  () =>
    violationHistoryLoading.value &&
    (violationHistoryLoaded.value || violationHistory.value.length > 0),
);

const shouldShowBannerProgress = computed(() => {
  if (activeSideNav.value !== 'workbench') return false;
  if (activeStageView.value === 'done' || stageStatus.done === 'done')
    return false;
  return (
    isRunning.value ||
    stageStatus.code_locate === 'done' ||
    stageStatus.assert_gen === 'done' ||
    stageStatus.fuzz === 'done' ||
    stageStatus.fuzz === 'running'
  );
});

const bannerProgressText = computed(
  () => `${Math.round(bannerProgress.value)}%`,
);

const activeWorkbenchStageStatus = computed(() => {
  return stageStatus[activeStageView.value];
});

const shouldCompleteBannerProgress = computed(() => {
  return (
    activeSideNav.value === 'workbench' &&
    activeStageView.value !== 'done' &&
    activeWorkbenchStageStatus.value === 'done'
  );
});

const visibleViolationHistory = computed(() =>
  violationHistory.value.slice(0, VISIBLE_HISTORY_LIMIT),
);

const overviewStats = ref<null | ProtocolDatabaseOverviewStats>(null);
const overviewLoadError = ref('');

const fallbackSummary: ProtocolDatabaseOverviewSummary = {
  analysisRecords: 0,
  codeSnippets: 0,
  databaseFiles: 0,
  implementations: 0,
  noViolationRules: 0,
  ruleResults: 0,
  unknownRules: 0,
  violationLocations: 0,
  violationRules: 0,
};

const overviewSummary = computed(() => {
  return overviewStats.value?.summary || fallbackSummary;
});

const protocolOverview = computed(() => overviewStats.value?.protocols || []);
const implementationOverview = computed(
  () => overviewStats.value?.implementations || [],
);
const topFindings = computed(() => {
  return (overviewStats.value?.topFindings || []).slice(0, 2);
});

const overviewMetrics = computed(() => [
  {
    accent: 'blue',
    icon: 'mdi:layers-triple-outline',
    label: '协议类型',
    suffix: '类',
    value: protocolOverview.value.length,
  },
  {
    accent: 'green',
    icon: 'mdi:clipboard-check-outline',
    label: '提取规则',
    suffix: '条',
    value: overviewSummary.value.ruleResults,
  },
  {
    accent: 'blue',
    icon: 'mdi:cube-scan',
    label: '协议实现',
    suffix: '个',
    value: overviewSummary.value.implementations,
  },
  {
    accent: 'indigo',
    icon: 'mdi:chart-box-outline',
    label: '分析记录',
    suffix: '条',
    value: overviewSummary.value.analysisRecords,
  },
  {
    accent: 'orange',
    icon: 'mdi:alert-outline',
    label: '违规判定',
    suffix: '条',
    value: overviewSummary.value.violationRules,
  },
]);

const heroPipelineSteps = [
  { icon: 'mdi:filter-variant', label: '规则提取' },
  { icon: 'mdi:share-variant-outline', label: '静态分析' },
  { icon: 'mdi:code-json', label: '断言插桩' },
  { icon: 'mdi:check-circle-outline', label: '动态验证' },
] as const;

const workflowSteps = [
  {
    description: '从标准文档中筛选关键规则，形成可分析的规则集。',
    icon: 'mdi:filter-variant',
    label: '规则筛选与抽取',
  },
  {
    description: '基于规则与代码理解，定位潜在不合规路径。',
    icon: 'mdi:share-variant-outline',
    label: 'LLM 引导静态分析',
  },
  {
    description: '生成断言并精确定位到相关代码片段。',
    icon: 'mdi:code-json',
    label: '生成断言与代码片段定位',
  },
  {
    description: '插桩验证并收集证据，确认违规并生成报告。',
    icon: 'mdi:shield-check-outline',
    label: '动态验证与结果确认',
  },
] as const;

const protocolCards = computed(() => {
  return protocolOverview.value.map((item) => ({
    ...item,
    accent: protocolAccent(item.name),
  }));
});

const implementationRanking = computed(() => {
  return [...implementationOverview.value].sort(
    (left, right) => right.violationRules - left.violationRules,
  );
});

const historyProtocolOptions = computed(() => [
  { label: '全部协议', value: '' },
  ...protocolOverview.value.map((item) => ({
    label: item.name,
    value: item.name,
  })),
]);

const historyImplementationOptions = computed(() => {
  const seen = new Set<string>();
  const protocolFilter = normalizeFilterValue(historyFilters.protocol);
  const options = implementationOverview.value
    .filter((item) => {
      if (!protocolFilter) return true;
      return normalizeFilterValue(item.protocol) === protocolFilter;
    })
    .filter((item) => {
      const key = normalizeFilterValue(item.name);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map((item) => ({
      label: item.name,
      value: item.name,
    }));
  return [{ label: '全部程序', value: '' }, ...options];
});

const historyTimeRangeOptions = [
  { label: '全部时间', value: '' },
  { label: '近一周', value: 'week' },
  { label: '近一个月', value: 'month' },
  { label: '近一年', value: 'year' },
];

const historyResultOptions = [
  { label: '全部结果', value: '' },
  { label: '发现违规', value: 'violation_found' },
  { label: '合规', value: 'no_violation' },
  { label: '未判定', value: 'unknown' },
];

const maxImplementationViolation = computed(() => {
  return Math.max(
    1,
    ...implementationRanking.value.map((item) => item.violationRules),
  );
});

const generatedAtDisplay = computed(() => {
  if (!overviewStats.value?.generatedAt) return '等待生成';
  return new Date(overviewStats.value.generatedAt).toLocaleString('zh-CN', {
    hour12: false,
  });
});

function formatNumber(value: number) {
  return new Intl.NumberFormat('zh-CN').format(value);
}

function barWidth(value: number, total: number) {
  if (!total || value <= 0) return '0%';
  return `${Math.max(4, Math.round((value / total) * 100))}%`;
}

function clearBannerProgressTimer() {
  if (!bannerProgressTimer) return;
  clearTimeout(bannerProgressTimer);
  bannerProgressTimer = null;
}

function getBannerProgressDelay(current: number, isAssertStage: boolean) {
  if (isAssertStage) {
    if (current < 70) return 1900 + Math.random() * 1200;
    if (current < 90) return 3000 + Math.random() * 1800;
    return 3400 + Math.random() * 2000;
  }

  if (current < 70) return 950 + Math.random() * 650;
  if (current < 90) return 1600 + Math.random() * 900;
  return 1400 + Math.random() * 1300;
}

function getBannerProgressIncrement(value: number, isAssertStage: boolean) {
  if (isAssertStage) {
    if (value < 70) return 0.7 + Math.random() * 1.2;
    if (value < 90) return 0.22 + Math.random() * 0.55;
    return 0.1 + Math.random() * 0.25;
  }

  if (value < 70) return 2 + Math.random() * 2.8;
  if (value < 90) return 0.7 + Math.random() * 1.2;
  return 0.3 + Math.random() * 0.9;
}

function scheduleBannerProgressTick() {
  clearBannerProgressTimer();
  if (
    !shouldShowBannerProgress.value ||
    shouldCompleteBannerProgress.value ||
    stageStatus.done === 'done'
  )
    return;

  const current = bannerProgress.value;
  const isAssertStage = activeStageView.value === 'assert_gen';
  const delay = getBannerProgressDelay(current, isAssertStage);

  bannerProgressTimer = setTimeout(() => {
    if (
      !shouldShowBannerProgress.value ||
      shouldCompleteBannerProgress.value ||
      stageStatus.done === 'done'
    )
      return;

    const value = bannerProgress.value;
    const isCurrentAssertStage = activeStageView.value === 'assert_gen';
    const increment = getBannerProgressIncrement(value, isCurrentAssertStage);
    const cap = value < 90 ? 90 : 98;
    bannerProgress.value = Math.min(cap, value + increment);
    scheduleBannerProgressTick();
  }, delay);
}

function syncBannerProgress() {
  if (!shouldShowBannerProgress.value) {
    clearBannerProgressTimer();
    bannerProgress.value = 0;
    bannerProgressStageKey = '';
    return;
  }

  const nextStageKey = `${activeSideNav.value}:${activeStageView.value}`;
  if (bannerProgressStageKey !== nextStageKey) {
    clearBannerProgressTimer();
    bannerProgress.value = 0;
    bannerProgressStageKey = nextStageKey;
  }

  if (shouldCompleteBannerProgress.value || stageStatus.done === 'done') {
    clearBannerProgressTimer();
    bannerProgress.value = 100;
    return;
  }

  if (bannerProgress.value <= 0 || bannerProgress.value >= 100) {
    bannerProgress.value = Math.max(8, Math.min(bannerProgress.value, 88));
  }
  scheduleBannerProgressTick();
}

function protocolAccent(name: string) {
  const key = name.toLowerCase();
  if (key.includes('dhcp')) return 'dhcp';
  if (key.includes('ftp')) return 'ftp';
  if (key.includes('mqtt')) return 'mqtt';
  if (key.includes('tls')) return 'tls';
  return 'coap';
}

async function loadViolationHistory(
  force = false,
  refreshOverview = true,
  silent = false,
) {
  if (violationHistoryLoading.value) {
    if (force) {
      violationHistoryRefreshQueued.value = true;
      violationHistoryQueuedRefreshOverview.value =
        violationHistoryQueuedRefreshOverview.value || refreshOverview;
    }
    return;
  }
  if (!force && violationHistoryLoaded.value) return;

  violationHistoryLoading.value = true;
  if (!silent) {
    violationHistoryError.value = '';
  }
  try {
    const response = await fetchProtocolViolationHistory({
      implementation: historyFilters.implementation || undefined,
      protocol: historyFilters.protocol || undefined,
      result: historyFilters.result || undefined,
      timeRange: historyFilters.timeRange || undefined,
    });
    violationHistoryError.value = '';
    violationHistory.value = response.items || [];
    violationHistoryWarnings.value = response.warnings || [];
    violationHistoryGeneratedAt.value = response.generatedAt || '';
    violationHistoryLoaded.value = true;
    if (refreshOverview) {
      void loadOverviewStats(true);
    }
    if (
      selectedViolationHistoryId.value &&
      !violationHistory.value.some(
        (entry) => entry.id === selectedViolationHistoryId.value,
      )
    ) {
      selectedViolationHistoryId.value = '';
    }
  } catch (error) {
    if (!silent || !violationHistoryLoaded.value) {
      violationHistoryError.value =
        error instanceof Error ? error.message : '历史结果读取失败';
    }
  } finally {
    violationHistoryLoading.value = false;
    const shouldRefreshQueued = violationHistoryRefreshQueued.value;
    const shouldRefreshOverview = violationHistoryQueuedRefreshOverview.value;
    violationHistoryRefreshQueued.value = false;
    violationHistoryQueuedRefreshOverview.value = false;
    if (shouldRefreshQueued) {
      void loadViolationHistory(
        true,
        shouldRefreshOverview,
        violationHistoryLoaded.value || violationHistory.value.length > 0,
      );
    }
  }
}

async function loadOverviewStats(force = false) {
  if (!force && overviewStats.value) return;
  overviewLoadError.value = '';
  try {
    overviewStats.value = await fetchProtocolDatabaseOverview();
  } catch (error) {
    overviewLoadError.value =
      error instanceof Error ? error.message : '统计数据读取失败';
  }
}

function openViolationHistory() {
  activeSideNav.value = 'logs';
  void refreshViolationHistoryOnEnter();
}

function handleSideNavClick(key: SideNavKey) {
  activeSideNav.value = key;
  if (key === 'logs') void refreshViolationHistoryOnEnter();
}

function handleRuleExtractGoWorkbench() {
  activeSideNav.value = 'workbench';
  if (!isRunning.value) {
    stage.value = 'setup';
    activeStageView.value = 'setup';
  }
}

function handleApplyExtractedRules(file: File) {
  if (isRunning.value) {
    message.warning('请先停止当前分析流程');
    return;
  }

  resetWorkbench();
  projectConfig.rules = file;
  activeSideNav.value = 'workbench';
  stage.value = 'setup';
  activeStageView.value = 'setup';
  stageMessage.value = '规则 JSON 已填入项目设置，请补充所需文件后进入规则确认';
  message.success(`已填入协议规则 JSON：${file.name}`);
}

function refreshViolationHistoryOnEnter() {
  void nextTick(() => {
    if (activeSideNav.value !== 'logs') return;
    void loadViolationHistory(true, true, violationHistoryLoaded.value);
  });
}

function handleHistoryFilterChange() {
  selectedViolationHistoryId.value = '';
  void loadViolationHistory(true);
}

function handleHistoryProtocolChange() {
  const implementationStillAvailable = historyImplementationOptions.value.some(
    (option) => option.value === historyFilters.implementation,
  );
  if (!implementationStillAvailable) {
    historyFilters.implementation = '';
  }
  handleHistoryFilterChange();
}

function normalizeFilterValue(value: null | string | undefined) {
  return String(value || '')
    .trim()
    .toLowerCase();
}

function formatOptionalTime(value?: null | string) {
  return value ? formatTime(value) : '-';
}

function truncateText(value: null | string | undefined, maxLength: number) {
  const text = value?.trim();
  if (!text) return '数据库未记录';
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
}

async function toggleViolationHistoryDetail(
  entry: ProtocolViolationHistoryEntry,
) {
  const shouldCollapse = selectedViolationHistoryId.value === entry.id;
  selectedViolationHistoryId.value = shouldCollapse ? '' : entry.id;

  if (!shouldCollapse) return;

  await nextTick();
  document
    .querySelector(`[data-history-entry-id="${entry.id}"]`)
    ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function historyResultTitle(entry: ProtocolViolationHistoryEntry) {
  if (entry.result === 'violation_found') return '违规结果';
  if (entry.result === 'no_violation') return '合规结果';
  return '规则结果';
}

function historyResultTagColor(entry: ProtocolViolationHistoryEntry) {
  if (entry.result === 'violation_found') return 'error';
  if (entry.result === 'no_violation') return 'success';
  return 'warning';
}

function historyReasonLabel(entry: ProtocolViolationHistoryEntry) {
  if (entry.result === 'violation_found') return '违规原因';
  if (entry.result === 'no_violation') return '合规说明';
  return '判定说明';
}

function historyReasonFallback(entry: ProtocolViolationHistoryEntry) {
  if (entry.result === 'violation_found') return '数据库未记录原因';
  if (entry.result === 'no_violation') return '数据库未记录合规说明';
  return '数据库未记录判定说明';
}

function readErrorMessage(error: unknown) {
  if (!error || typeof error !== 'object') return '';
  const payload = error as { message?: unknown; response?: { data?: unknown } };
  const responseData = payload.response?.data;
  if (responseData && typeof responseData === 'object') {
    const messageValue = (responseData as { message?: unknown }).message;
    return typeof messageValue === 'string' ? messageValue : '';
  }
  return typeof payload.message === 'string' ? payload.message : '';
}

function isViolationHistoryMissingError(error: unknown) {
  if (!error || typeof error !== 'object') return false;
  const response = (error as { response?: { status?: number } }).response;
  return (
    response?.status === 404 ||
    readErrorMessage(error).includes('历史记录不存在')
  );
}

async function handleDeleteViolationHistory(
  entry: ProtocolViolationHistoryEntry,
) {
  if (deletingViolationHistoryId.value) return;

  deletingViolationHistoryId.value = entry.id;
  try {
    await deleteProtocolViolationHistory(entry.id, {
      callGraph: entry.callGraph,
      codeSnippet: entry.codeSnippet,
      databaseName: entry.databaseName,
      databasePath: entry.databasePath,
      reason: entry.reason,
      ruleDesc: entry.ruleDesc,
      violations: entry.violations,
    });
    violationHistory.value = violationHistory.value.filter(
      (item) => item.id !== entry.id,
    );
    if (selectedViolationHistoryId.value === entry.id) {
      selectedViolationHistoryId.value = '';
    }
    void loadOverviewStats(true);
    message.success('历史记录已删除');
  } catch (error) {
    console.error('删除历史记录失败:', error);
    if (isViolationHistoryMissingError(error)) {
      selectedViolationHistoryId.value = '';
      await loadViolationHistory(true, true, true);
      message.warning('历史列表已刷新，请重新选择后删除');
      return;
    }
    message.error('删除历史记录失败');
  } finally {
    deletingViolationHistoryId.value = '';
  }
}

function formatViolationLocations(entry: ProtocolViolationHistoryEntry) {
  const violations = entry.violations || [];
  if (violations.length === 0) {
    return entry.result === 'violation_found'
      ? '数据库未记录具体位置'
      : '无违规定位';
  }
  return violations
    .map((item) => {
      const file = item.filename || '未知文件';
      const fn = item.functionName ? ` · ${item.functionName}` : '';
      const lines = item.codeLines?.length
        ? `:${item.codeLines.join(',')}`
        : '';
      return `${file}${lines}${fn}`;
    })
    .join('；');
}

function formatLlmRaw(value: unknown) {
  if (typeof value === 'string') return value;
  if (value === null || value === undefined) return '';
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function handleViolationHistoryUpdated() {
  void loadViolationHistory(true, true, true);
}

watch(
  () => [
    activeSideNav.value,
    activeStageView.value,
    isRunning.value,
    isTransitioning.value,
    stageStatus.code_locate,
    stageStatus.assert_gen,
    stageStatus.fuzz,
    stageStatus.done,
    stageMessage.value,
  ],
  syncBannerProgress,
  { immediate: true },
);

onMounted(() => {
  window.addEventListener(
    'protocol-violation-history-updated',
    handleViolationHistoryUpdated,
  );
  void loadOverviewStats();
  void loadViolationHistory(false, false);
});

onBeforeUnmount(() => {
  clearBannerProgressTimer();
  window.removeEventListener(
    'protocol-violation-history-updated',
    handleViolationHistoryUpdated,
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

function handleStageSelect(key: (typeof STAGE_LIST)[number]['key']) {
  selectStageView(key);
}

function switchRule() {
  if (isRunning.value) return;
  resetWorkbench();
  stageStatus.setup = 'done';
  stage.value = 'rule_confirm';
  activeStageView.value = 'rule_confirm';
  stageMessage.value = '请选择一条规则后启动自动化分析流程';
}

async function handleLoadDemoConfig() {
  if (demoConfigLoading.value || isRunning.value) return;
  demoConfigLoading.value = true;
  try {
    await loadDemoConfig();
  } finally {
    demoConfigLoading.value = false;
  }
}
</script>

<template>
  <Page content-class="p-0">
    <div
      class="guard-shell"
      :class="{ 'guard-shell--overview': activeSideNav === 'overview' }"
    >
      <header class="guard-topbar">
        <div class="topbar-left">
          <div class="brand-mark">
            <IconifyIcon icon="mdi:shield-check-outline" />
          </div>
          <div class="brand-name">ProtocolGuard</div>
          <div class="topbar-divider"></div>
          <div class="topbar-section">{{ activeSideNavLabel }}</div>
        </div>

        <div v-if="activeSideNav === 'workbench'" class="topbar-actions">
          <div
            class="runtime-status"
            :class="{ 'runtime-status--idle': !isRunning }"
          >
            <span class="status-dot"></span>
            <span>{{ isRunning ? '运行中' : '空闲' }}</span>
          </div>
          <div
            v-if="demoModeActive"
            class="demo-mode-indicator"
            title="当前为演示模式"
          >
            <IconifyIcon icon="mdi:presentation-play" />
            <span>演示模式</span>
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
          <div class="avatar">PG</div>
        </div>
      </header>

      <div class="guard-layout">
        <aside class="guard-sidebar">
          <div class="sidebar-main">
            <nav class="sidebar-nav">
              <div
                v-for="item in sideNavItems"
                :key="item.key"
                class="nav-group"
              >
                <button
                  class="nav-item"
                  :class="{
                    'nav-item--active':
                      item.key === activeSideNav ||
                      (item.key === 'workbench' && isWorkbenchSectionActive),
                  }"
                  type="button"
                  @click="handleSideNavClick(item.key)"
                >
                  <IconifyIcon :icon="item.icon" />
                  <span>{{ item.label }}</span>
                </button>

                <div
                  v-if="item.key === 'workbench' && isWorkbenchSectionActive"
                  class="sub-nav"
                >
                  <button
                    v-for="child in workbenchSubNavItems"
                    :key="child.key"
                    class="sub-nav-item"
                    :class="{
                      'sub-nav-item--active': child.key === activeSideNav,
                    }"
                    type="button"
                    @click="handleSideNavClick(child.key)"
                  >
                    <IconifyIcon :icon="child.icon" />
                    <span>{{ child.label }}</span>
                  </button>
                </div>
              </div>
            </nav>
          </div>

          <section v-if="activeSideNav === 'workbench'" class="current-task">
            <div class="current-task-title">当前任务</div>
            <dl>
              <div>
                <dt>项目:</dt>
                <dd>
                  {{ projectConfig.protocolType }} ({{
                    projectConfig.implementation
                  }})
                </dd>
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
          <section v-if="activeSideNav === 'overview'" class="overview-shell">
            <header class="overview-hero">
              <div class="overview-hero-copy">
                <h1>LLM驱动的协议实现合规与安全分析平台</h1>
                <p>
                  结合协议规则提取、LLM 引导静态分析、断言插桩和动态验证，
                  自动化发现协议实现中的不合规漏洞并完成可验证确认。
                </p>

                <div class="overview-hero-flow">
                  <div
                    v-for="(item, index) in heroPipelineSteps"
                    :key="item.label"
                    class="hero-flow-step"
                  >
                    <IconifyIcon :icon="item.icon" />
                    <span>{{ item.label }}</span>
                    <IconifyIcon
                      v-if="index < heroPipelineSteps.length - 1"
                      class="hero-flow-arrow"
                      icon="mdi:chevron-right"
                    />
                  </div>
                </div>

                <div class="overview-hero-badges">
                  <div class="hero-badge">
                    <IconifyIcon icon="mdi:check-decagram-outline" />
                    <span>
                      已支持
                      <strong>{{
                        formatNumber(protocolOverview.length)
                      }}</strong>
                      类协议
                    </span>
                  </div>
                  <div class="hero-badge hero-badge--green">
                    <IconifyIcon icon="mdi:server-network" />
                    <span>
                      已接入
                      <strong>{{
                        formatNumber(overviewSummary.implementations)
                      }}</strong>
                      个实现
                    </span>
                  </div>
                </div>
              </div>

              <div class="overview-hero-art" aria-hidden="true">
                <div class="hero-art-plane hero-art-plane--back"></div>
                <div class="hero-art-plane">
                  <div class="hero-art-document">
                    <IconifyIcon icon="mdi:shield-check" />
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <div class="hero-art-magnifier"></div>
                </div>
                <i class="hero-art-cube hero-art-cube--one"></i>
                <i class="hero-art-cube hero-art-cube--two"></i>
                <i class="hero-art-cube hero-art-cube--three"></i>
              </div>
            </header>

            <section v-if="overviewLoadError" class="overview-error">
              <IconifyIcon icon="mdi:alert-circle" />
              <span>成果统计读取失败：{{ overviewLoadError }}</span>
            </section>

            <section class="overview-metrics">
              <article
                v-for="metric in overviewMetrics"
                :key="metric.label"
                class="overview-metric-card"
                :class="`overview-metric-card--${metric.accent}`"
              >
                <div class="metric-icon">
                  <IconifyIcon :icon="metric.icon" />
                </div>
                <div>
                  <span>{{ metric.label }}</span>
                  <strong>
                    {{ formatNumber(metric.value) }}
                    <small>{{ metric.suffix }}</small>
                  </strong>
                </div>
              </article>
            </section>

            <section class="overview-grid overview-grid--primary">
              <article class="overview-card overview-card--coverage">
                <header class="overview-card-head">
                  <div>
                    <h2>当前支持与覆盖</h2>
                    <p>
                      来自数据库汇总结果，共
                      {{ formatNumber(protocolOverview.length) }} 类协议、
                      {{ formatNumber(overviewSummary.implementations) }}
                      个实现。
                    </p>
                  </div>
                  <span class="card-count">
                    全部 {{ formatNumber(protocolOverview.length) }} 类
                  </span>
                </header>

                <div class="protocol-scoreboard">
                  <article
                    v-for="item in protocolCards"
                    :key="item.name"
                    class="protocol-card"
                    :class="`protocol-card--${item.accent}`"
                  >
                    <div class="protocol-card-head">
                      <div class="protocol-badge">{{ item.name }}</div>
                      <div>
                        <strong>{{ item.name }}</strong>
                        <span>{{ item.implementations }} 个实现</span>
                      </div>
                    </div>
                    <div class="protocol-bars">
                      <div>
                        <span>规则覆盖</span>
                        <strong>{{ formatNumber(item.ruleResults) }} 条</strong>
                      </div>
                      <div class="score-track">
                        <i class="score-track__ok"></i>
                      </div>
                    </div>
                    <div class="protocol-meta">
                      <span
                        >定位
                        {{ formatNumber(item.violationLocations) }} 处</span
                      >
                      <span
                        >记录 {{ formatNumber(item.analysisRecords) }} 条</span
                      >
                    </div>
                  </article>
                </div>
              </article>

              <article class="overview-card overview-card--ranking">
                <header class="overview-card-head">
                  <div>
                    <h2>风险发现概览</h2>
                    <p>
                      按违规数排序，展示全部
                      {{ formatNumber(implementationRanking.length) }} 个实现。
                    </p>
                  </div>
                  <Button
                    size="small"
                    type="primary"
                    @click="openViolationHistory"
                  >
                    查看详情
                    <template #icon>
                      <IconifyIcon icon="mdi:arrow-right" />
                    </template>
                  </Button>
                </header>
                <div class="implementation-table">
                  <div class="implementation-row implementation-row--head">
                    <span>实现</span>
                    <span>协议</span>
                    <span>规则</span>
                    <span>违规</span>
                    <span>定位</span>
                  </div>
                  <div
                    v-for="item in implementationRanking"
                    :key="`${item.name}-${item.protocol}`"
                    class="implementation-row"
                  >
                    <strong>{{ item.name }}</strong>
                    <span>{{ item.protocol }}</span>
                    <span>{{ formatNumber(item.ruleResults) }}</span>
                    <span class="risk-cell">
                      <strong>{{ formatNumber(item.violationRules) }}</strong>
                      <i>
                        <em
                          :style="{
                            width: barWidth(
                              item.violationRules,
                              maxImplementationViolation,
                            ),
                          }"
                        ></em>
                      </i>
                    </span>
                    <span>{{ formatNumber(item.violationLocations) }}</span>
                  </div>
                </div>
              </article>
            </section>

            <section class="overview-grid overview-grid--results">
              <article class="overview-card">
                <header class="overview-card-head">
                  <div>
                    <h2>平台是如何工作的</h2>
                    <p>更新时间：{{ generatedAtDisplay }}</p>
                  </div>
                </header>
                <div class="workflow-list">
                  <div
                    v-for="(item, index) in workflowSteps"
                    :key="item.label"
                    class="workflow-step"
                  >
                    <span class="workflow-index">{{ index + 1 }}</span>
                    <div class="workflow-icon">
                      <IconifyIcon :icon="item.icon" />
                    </div>
                    <div>
                      <strong>{{ item.label }}</strong>
                      <p>{{ item.description }}</p>
                    </div>
                  </div>
                </div>
              </article>

              <article class="overview-card">
                <header class="overview-card-head">
                  <div>
                    <h2>典型发现</h2>
                    <p>
                      来自规则结果库的代表性违规样例，共
                      {{ formatNumber(topFindings.length) }} 条。
                    </p>
                  </div>
                </header>
                <div class="finding-list">
                  <article
                    v-for="finding in topFindings"
                    :key="`${finding.protocol}-${finding.implementation}-${finding.rule}`"
                    class="finding-item"
                  >
                    <div class="finding-head">
                      <Tag color="blue">{{ finding.protocol }}</Tag>
                      <strong>{{ finding.implementation }}</strong>
                    </div>
                    <p>{{ finding.rule }}</p>
                    <small>{{ finding.reason }}</small>
                  </article>
                </div>
              </article>
            </section>
          </section>

          <section
            v-else-if="activeSideNav === 'extract'"
            class="extract-shell"
          >
            <StageRuleExtract
              :disabled="isRunning"
              :protocol-type="projectConfig.protocolType"
              :rules-file="projectConfig.rules"
              @apply-rules="handleApplyExtractedRules"
              @go-workbench="handleRuleExtractGoWorkbench"
            />
          </section>

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
                <template #icon>
                  <IconifyIcon icon="mdi:chevron-down" />
                </template>
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
                  <IconifyIcon
                    v-if="stageStatus[s.key] === 'done'"
                    icon="mdi:check"
                  />
                  <IconifyIcon
                    v-else-if="stageStatus[s.key] === 'skipped'"
                    icon="mdi:debug-step-over"
                  />
                  <IconifyIcon
                    v-else-if="stageStatus[s.key] === 'error'"
                    icon="mdi:close"
                  />
                  <span v-else>{{ s.index }}</span>
                </div>
                <div class="stepper-copy">
                  <div class="stepper-title">{{ s.title }}</div>
                  <div class="stepper-state">{{ stageStateLabel(s.key) }}</div>
                </div>
                <div v-if="idx < STAGE_LIST.length - 1" class="stepper-arrow">
                  <IconifyIcon icon="mdi:arrow-right" />
                </div>
              </button>
            </section>

            <section
              v-if="stageMessage"
              class="workbench-banner"
              :class="{
                'workbench-banner--progress': shouldShowBannerProgress,
              }"
              :style="{
                '--banner-progress': `${bannerProgress}%`,
              }"
            >
              <span
                v-if="shouldShowBannerProgress"
                class="workbench-banner-fill"
                aria-hidden="true"
              ></span>
              <IconifyIcon
                class="workbench-banner-icon"
                icon="mdi:information-outline"
              />
              <span class="workbench-banner-text">{{ stageMessage }}</span>
              <span
                v-if="shouldShowBannerProgress"
                class="workbench-banner-percent"
              >
                {{ bannerProgressText }}
              </span>
              <Button
                v-if="activeStageView === 'setup'"
                class="demo-mode-button"
                size="small"
                type="primary"
                :disabled="isRunning"
                :loading="demoConfigLoading"
                title="自动上传 New-Input 中的演示文件"
                @click="handleLoadDemoConfig"
              >
                演示模式
              </Button>
              <Button
                v-if="isAwaitingAssertConfirmation"
                class="confirm-assert-button"
                size="small"
                type="primary"
                :disabled="!staticResult"
                @click="confirmAssertGeneration"
              >
                进入断言生成
                <template #icon>
                  <IconifyIcon icon="mdi:arrow-right" />
                </template>
              </Button>
            </section>

            <section v-if="errorMessage" class="workbench-error">
              <IconifyIcon icon="mdi:alert-circle" />
              <span>{{ errorMessage }}</span>
            </section>

            <section class="workbench-content">
              <StageSetup
                v-if="activeStageView === 'setup'"
                v-model:config="projectConfig"
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
                :poc-path="aflNetPocPath"
                :protocol-type="projectConfig.protocolType"
                :rule="selectedRule"
                :static-result="staticResult"
                :stats="fuzzStats"
              />
            </section>
          </section>

          <section v-else-if="activeSideNav === 'logs'" class="logs-shell">
            <header class="logs-header">
              <div>
                <h1>历史结果</h1>
                <p>
                  数据库规则判定记录
                  <template v-if="violationHistoryGeneratedAt">
                    · 更新时间
                    {{ formatOptionalTime(violationHistoryGeneratedAt) }}
                  </template>
                  <template v-if="violationHistoryRefreshing">
                    · 正在同步最新数据
                  </template>
                </p>
              </div>
              <div class="logs-header-actions">
                <Button
                  size="small"
                  :loading="violationHistoryLoading"
                  @click="loadViolationHistory(true)"
                >
                  <template #icon><IconifyIcon icon="mdi:refresh" /></template>
                  刷新
                </Button>
              </div>
            </header>

            <section class="history-filter-bar">
              <Select
                v-model:value="historyFilters.protocol"
                class="history-filter-select"
                :options="historyProtocolOptions"
                @change="handleHistoryProtocolChange"
              />
              <Select
                v-model:value="historyFilters.implementation"
                class="history-filter-select"
                :options="historyImplementationOptions"
                @change="handleHistoryFilterChange"
              />
              <Select
                v-model:value="historyFilters.result"
                class="history-filter-select"
                :options="historyResultOptions"
                @change="handleHistoryFilterChange"
              />
              <Select
                v-model:value="historyFilters.timeRange"
                class="history-filter-select"
                :options="historyTimeRangeOptions"
                @change="handleHistoryFilterChange"
              />
            </section>

            <section
              v-if="violationHistoryError"
              class="result-history-empty result-history-empty--error"
            >
              <div>历史结果读取失败</div>
              <p>{{ violationHistoryError }}</p>
            </section>

            <section
              v-else-if="
                violationHistoryLoading &&
                violationHistory.length === 0 &&
                !violationHistoryLoaded
              "
              class="result-history-empty"
            >
              <div>正在读取历史结果</div>
              <p>系统正在从当前数据库文件中汇总规则判定记录。</p>
            </section>

            <section
              v-if="violationHistoryWarnings.length > 0"
              class="history-warning"
            >
              <IconifyIcon icon="mdi:alert-outline" />
              <span>{{ violationHistoryWarnings.join('；') }}</span>
            </section>

            <div v-if="violationHistory.length > 0" class="result-history-list">
              <article
                v-for="entry in visibleViolationHistory"
                :key="entry.id"
                class="result-history-card result-history-card--summary"
                :class="{
                  'result-history-card--selected':
                    entry.id === selectedViolationHistoryId,
                }"
                :data-history-entry-id="entry.id"
              >
                <div class="result-history-head">
                  <div>
                    <div class="result-history-title">
                      {{ entry.implementationName }} {{ entry.protocolName }}
                      {{ historyResultTitle(entry) }}
                    </div>
                    <div class="result-history-meta">
                      {{ entry.databaseName }} ·
                      {{
                        formatOptionalTime(entry.updatedAt || entry.extractedAt)
                      }}
                    </div>
                  </div>
                  <Tag :color="historyResultTagColor(entry)">
                    {{ entry.resultLabel }}
                  </Tag>
                </div>

                <section class="history-summary-body">
                  <div>
                    <span>规则内容</span>
                    <p>{{ truncateText(entry.ruleDesc, 180) }}</p>
                  </div>
                  <div>
                    <span>{{ historyReasonLabel(entry) }}</span>
                    <p>{{ truncateText(entry.reason, 180) }}</p>
                  </div>
                </section>

                <footer class="history-summary-footer">
                  <span>{{ formatViolationLocations(entry) }}</span>
                  <div class="history-summary-actions">
                    <Popconfirm
                      cancel-text="取消"
                      ok-text="确定"
                      title="确定删除这条历史记录吗？"
                      description="此操作会删除数据库中的对应记录，且不可撤销。"
                      @confirm="handleDeleteViolationHistory(entry)"
                    >
                      <Button
                        danger
                        size="small"
                        :loading="deletingViolationHistoryId === entry.id"
                      >
                        <template #icon>
                          <IconifyIcon icon="mdi:delete-outline" />
                        </template>
                        删除
                      </Button>
                    </Popconfirm>
                    <Button
                      v-if="entry.id !== selectedViolationHistoryId"
                      size="small"
                      type="primary"
                      @click="toggleViolationHistoryDetail(entry)"
                    >
                      查看详情
                      <template #icon>
                        <IconifyIcon icon="mdi:chevron-down" />
                      </template>
                    </Button>
                  </div>
                </footer>

                <section
                  v-if="entry.id === selectedViolationHistoryId"
                  class="history-detail-panel"
                >
                  <header class="history-detail-head">
                    <div>
                      <span>结果详情</span>
                      <h2>
                        {{ entry.implementationName }} {{ entry.protocolName }}
                      </h2>
                      <p>
                        {{ entry.databaseName }} ·
                        {{
                          formatOptionalTime(
                            entry.updatedAt || entry.extractedAt,
                          )
                        }}
                      </p>
                    </div>
                    <Tag :color="historyResultTagColor(entry)">
                      {{ entry.resultLabel }}
                    </Tag>
                  </header>

                  <section class="result-history-grid">
                    <div class="history-block history-block--wide">
                      <span>规则内容</span>
                      <p>{{ entry.ruleDesc }}</p>
                    </div>
                    <div class="history-block history-block--wide">
                      <span>{{ historyReasonLabel(entry) }}</span>
                      <p>{{ entry.reason || historyReasonFallback(entry) }}</p>
                    </div>
                    <div class="history-block">
                      <span>协议实现</span>
                      <strong>{{ entry.implementationName }}</strong>
                      <small>{{ entry.protocolName }}</small>
                    </div>
                    <div class="history-block">
                      <span>数据库</span>
                      <strong>{{ entry.databaseName }}</strong>
                      <small>{{ entry.databasePath || '-' }}</small>
                    </div>
                    <div class="history-block history-block--wide">
                      <span>定位信息</span>
                      <p>{{ formatViolationLocations(entry) }}</p>
                    </div>
                  </section>

                  <details v-if="entry.codeSnippet" class="history-source">
                    <summary>查看数据库代码片段</summary>
                    <pre>{{ entry.codeSnippet }}</pre>
                  </details>

                  <details v-if="entry.callGraph" class="history-diff">
                    <summary>查看调用图</summary>
                    <pre>{{ entry.callGraph }}</pre>
                  </details>

                  <details v-if="entry.llmRaw" class="history-diff">
                    <summary>查看 LLM 原始结果</summary>
                    <pre>{{ formatLlmRaw(entry.llmRaw) }}</pre>
                  </details>

                  <footer class="history-detail-actions">
                    <Button
                      size="small"
                      type="primary"
                      @click="toggleViolationHistoryDetail(entry)"
                    >
                      收起详情
                      <template #icon>
                        <IconifyIcon icon="mdi:chevron-up" />
                      </template>
                    </Button>
                  </footer>
                </section>
              </article>
            </div>

            <section
              v-else-if="
                (!violationHistoryLoading || violationHistoryLoaded) &&
                !violationHistoryError
              "
              class="result-history-empty"
            >
              <div>暂无历史结果</div>
              <p>当前数据库文件中没有读取到规则判定记录。</p>
            </section>
          </section>

          <section v-else class="overview-blank"></section>
        </main>
      </div>
    </div>
  </Page>
</template>

<style scoped>
.guard-shell {
  min-height: calc(100vh - 92px);
  overflow: hidden;
  font-size: 17px;
  color: #111827;
  background: #f4f7fb;
}

.guard-shell--overview {
  background: #f5f8fd;
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

.demo-mode-indicator {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  justify-content: center;
  height: 32px;
  padding: 0 12px;
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  white-space: nowrap;
  background: #fff;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
}

.demo-mode-indicator svg {
  font-size: 16px;
  color: #1677ff;
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
  grid-template-columns: 246px minmax(0, 1fr);
  min-height: calc(100vh - 156px);
}

.guard-sidebar {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 18px 16px;
  background: #fff;
  border-right: 1px solid #e7edf5;
}

.sidebar-main {
  min-width: 0;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-group {
  min-width: 0;
}

.nav-item {
  display: flex;
  gap: 13px;
  align-items: center;
  width: 100%;
  height: 58px;
  padding: 0 16px;
  font-size: 21px;
  font-weight: 800;
  line-height: 1.25;
  color: #101b36;
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 6px;
}

.nav-item :first-child {
  font-size: 24px;
}

.nav-item--active {
  position: relative;
  font-weight: 800;
  color: #1677ff;
  background: linear-gradient(90deg, #eaf3ff 0%, #f3f8ff 100%);
}

.nav-item--active::before {
  position: absolute;
  top: 0;
  bottom: 0;
  left: -16px;
  width: 4px;
  content: '';
  background: #1677ff;
  border-radius: 0 3px 3px 0;
}

.sub-nav {
  display: grid;
  gap: 6px;
  padding: 8px 0 0 20px;
  margin-left: 16px;
  border-left: 1px solid #dbe8f8;
}

.sub-nav-item {
  display: flex;
  gap: 10px;
  align-items: center;
  width: 100%;
  min-height: 40px;
  padding: 0 12px;
  font-size: 15px;
  font-weight: 700;
  color: #475569;
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 6px;
}

.sub-nav-item :first-child {
  flex: 0 0 auto;
  font-size: 18px;
}

.sub-nav-item--active {
  color: #1677ff;
  background: #eef6ff;
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
  text-overflow: ellipsis;
  font-size: 12px;
  font-weight: 600;
  color: #172033;
  white-space: nowrap;
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.sidebar-footer-item,
.sidebar-footer-user {
  display: flex;
  align-items: center;
  width: 100%;
  color: #64748b;
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 0;
}

.sidebar-footer-item {
  gap: 12px;
  height: 36px;
  padding: 0 12px;
  font-size: 14px;
  font-weight: 700;
}

.sidebar-footer-item :first-child {
  font-size: 20px;
}

.sidebar-footer-user {
  gap: 10px;
  min-height: 42px;
  padding: 0 10px;
  font-size: 15px;
  font-weight: 700;
  color: #475569;
}

.sidebar-footer-user :last-child {
  margin-left: auto;
  font-size: 16px;
}

.sidebar-avatar {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  font-size: 12px;
  font-weight: 850;
  color: #1677ff;
  background: linear-gradient(180deg, #dceaff 0%, #c9ddff 100%);
  border-radius: 50%;
}

.guard-main {
  min-width: 0;
  padding: 0;
}

.overview-blank {
  min-height: 100%;
}

.overview-shell {
  width: 100%;
  min-height: 100%;
  padding: 28px 28px 24px;
}

.overview-shell,
.extract-shell,
.task-shell,
.logs-shell {
  animation: guard-view-enter 140ms ease-out;
}

@keyframes guard-view-enter {
  from {
    opacity: 0.72;
    transform: translateY(4px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.overview-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 0.64fr) minmax(340px, 0.36fr);
  gap: 20px;
  min-height: 310px;
  padding: 44px 48px 32px;
  margin-bottom: 16px;
  overflow: hidden;
  background:
    radial-gradient(circle at 82% 24%, rgb(89 143 255 / 24%), transparent 36%),
    linear-gradient(104deg, #fff 0%, #f4f8ff 48%, #eaf2ff 100%);
  border: 1px solid #e1ebfb;
  border-radius: 8px;
  box-shadow: 0 12px 30px rgb(20 45 82 / 7%);
}

.overview-card,
.overview-metric-card,
.overview-error {
  background: #fff;
  border: 1px solid #e7edf5;
  border-radius: 8px;
  box-shadow: 0 8px 22px rgb(15 23 42 / 4%);
}

.overview-hero-copy {
  position: relative;
  z-index: 1;
  min-width: 0;
}

.overview-hero h1 {
  max-width: 760px;
  margin: 0;
  font-size: 32px;
  font-weight: 850;
  line-height: 1.24;
  color: #101b36;
  letter-spacing: 0;
}

.overview-hero p {
  max-width: 980px;
  margin: 14px 0 0;
  font-size: 15px;
  line-height: 1.8;
  color: #5b6b83;
  white-space: nowrap;
}

.overview-hero-flow {
  display: inline-grid;
  grid-template-columns: repeat(4, max-content);
  column-gap: 20px;
  width: fit-content;
  max-width: 100%;
  min-height: 58px;
  margin-top: 22px;
  overflow: hidden;
  background: rgb(255 255 255 / 86%);
  border: 1px solid #dce8f9;
  border-radius: 8px;
  box-shadow: 0 10px 24px rgb(45 91 155 / 8%);
}

.hero-flow-step {
  position: relative;
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: flex-start;
  min-width: 0;
  padding: 0 24px;
  font-size: 14px;
  font-weight: 800;
  color: #1d2b46;
}

.hero-flow-step:first-child {
  padding-left: 20px;
}

.hero-flow-step > :first-child {
  flex: 0 0 auto;
  font-size: 30px;
  color: #1677ff;
}

.hero-flow-step:nth-child(2) > :first-child {
  color: #10b3b1;
}

.hero-flow-step:nth-child(3) > :first-child {
  color: #7c5cff;
}

.hero-flow-step:nth-child(4) > :first-child {
  color: #22b26f;
}

.hero-flow-step span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hero-flow-arrow {
  position: absolute;
  right: -22px;
  z-index: 1;
  font-size: 24px !important;
  color: #9aaac0 !important;
}

.overview-hero-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
}

.hero-badge {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  min-height: 38px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 800;
  color: #1677ff;
  background: rgb(255 255 255 / 82%);
  border: 1px solid #dceaff;
  border-radius: 8px;
  box-shadow: 0 8px 18px rgb(45 91 155 / 6%);
}

.hero-badge :first-child {
  flex: 0 0 auto;
  font-size: 16px;
}

.hero-badge strong {
  margin: 0 4px;
  font-size: 16px;
}

.hero-badge--green {
  color: #17a261;
  border-color: #d7f1e2;
}

.overview-hero-art {
  position: relative;
  min-height: 230px;
}

.hero-art-plane,
.hero-art-plane--back {
  position: absolute;
  right: 28px;
  bottom: 20px;
  width: min(420px, 100%);
  height: 174px;
  background:
    linear-gradient(
      135deg,
      rgb(255 255 255 / 72%) 0%,
      rgb(81 139 255 / 18%) 100%
    ),
    linear-gradient(
      135deg,
      transparent 48%,
      rgb(64 133 255 / 28%) 49%,
      transparent 51%
    );
  border: 1px solid rgb(64 133 255 / 28%);
  box-shadow: 0 22px 46px rgb(42 100 205 / 20%);
  transform: skewY(-10deg) rotate(-4deg);
}

.hero-art-plane--back {
  right: -10px;
  bottom: 54px;
  opacity: 0.56;
  transform: skewY(-10deg) rotate(-4deg) scale(1.12);
}

.hero-art-document {
  position: absolute;
  right: 122px;
  bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 150px;
  height: 166px;
  padding: 72px 24px 0;
  background: linear-gradient(180deg, #fff 0%, #e7f0ff 100%);
  border: 1px solid #d5e3fb;
  box-shadow: 0 18px 26px rgb(40 89 174 / 17%);
  transform: skewY(10deg) rotate(4deg);
}

.hero-art-document :first-child {
  position: absolute;
  top: -34px;
  left: 36px;
  font-size: 78px;
  color: #4c8cff;
  filter: drop-shadow(0 14px 16px rgb(38 105 230 / 26%));
}

.hero-art-document span {
  display: block;
  height: 10px;
  background: #d5e2f4;
  border-radius: 999px;
}

.hero-art-document span:nth-child(3) {
  width: 80%;
}

.hero-art-document span:nth-child(4) {
  width: 64%;
}

.hero-art-magnifier {
  position: absolute;
  right: 56px;
  bottom: 16px;
  width: 72px;
  height: 72px;
  border: 10px solid rgb(68 132 240 / 72%);
  border-radius: 50%;
  transform: skewY(10deg) rotate(4deg);
}

.hero-art-magnifier::after {
  position: absolute;
  right: -36px;
  bottom: -30px;
  width: 58px;
  height: 11px;
  content: '';
  background: #4b8cff;
  border-radius: 999px;
  transform: rotate(45deg);
}

.hero-art-cube {
  position: absolute;
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #dbe9ff 0%, #8fb7ff 100%);
  box-shadow: 0 10px 20px rgb(64 133 255 / 15%);
  transform: rotate(45deg) skew(-8deg, -8deg);
}

.hero-art-cube--one {
  top: 46px;
  left: 34px;
}

.hero-art-cube--two {
  top: 58px;
  right: 16px;
  width: 22px;
  height: 22px;
}

.hero-art-cube--three {
  bottom: 24px;
  left: 18px;
  width: 20px;
  height: 20px;
}

.overview-error {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 11px 14px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #dc2626;
  background: #fff5f5;
}

.overview-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.overview-metric-card {
  display: flex;
  gap: 14px;
  align-items: center;
  min-width: 0;
  min-height: 96px;
  padding: 18px 20px;
}

.metric-icon {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  font-size: 28px;
  border-radius: 50%;
}

.overview-metric-card span {
  display: block;
  margin-bottom: 7px;
  font-size: 13px;
  font-weight: 800;
  color: #64748b;
}

.overview-metric-card strong {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 30px;
  font-weight: 850;
  line-height: 1.15;
  color: #111b34;
  white-space: nowrap;
}

.overview-metric-card small {
  margin-left: 3px;
  font-size: 13px;
  font-weight: 700;
  color: #64748b;
}

.overview-metric-card--blue .metric-icon {
  color: #1677ff;
  background: #edf5ff;
}

.overview-metric-card--indigo .metric-icon {
  color: #2188ff;
  background: #eef6ff;
}

.overview-metric-card--green .metric-icon {
  color: #0f9f6e;
  background: #ecfdf5;
}

.overview-metric-card--red .metric-icon {
  color: #dc2626;
  background: #fff1f2;
}

.overview-metric-card--orange .metric-icon {
  color: #d97706;
  background: #fff7ed;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 16px;
  align-items: stretch;
  margin-bottom: 16px;
}

.overview-grid--primary {
  grid-template-columns: minmax(0, 1.1fr) minmax(420px, 0.9fr);
}

.overview-grid--results {
  grid-template-columns: minmax(0, 1.1fr) minmax(460px, 0.9fr);
  align-items: stretch;
}

.overview-grid--results > .overview-card {
  display: flex;
  flex-direction: column;
}

.overview-card--ranking {
  display: flex;
  flex-direction: column;
}

.overview-card {
  min-width: 0;
  padding: 18px 20px;
}

.overview-card-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}

.overview-card-head h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 850;
  line-height: 1.25;
  color: #0f172a;
  letter-spacing: 0;
}

.overview-card-head p {
  margin: 5px 0 0;
  font-size: 12px;
  color: #64748b;
}

.card-count {
  display: flex;
  flex: 0 0 auto;
  gap: 6px;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 800;
  color: #1677ff;
  background: #eef6ff;
  border: 1px solid #d7eaff;
  border-radius: 8px;
}

.score-track {
  position: relative;
  display: flex;
  height: 8px;
  margin: 10px 0 16px;
  overflow: hidden;
  background: transparent;
  border-radius: 999px;
}

.score-track i {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  display: block;
  border-radius: inherit;
}

.protocol-scoreboard {
  display: grid;
  grid-template-columns: repeat(5, minmax(188px, 1fr));
  gap: 10px;
  padding-bottom: 4px;
  overflow-x: auto;
}

.protocol-card {
  min-width: 188px;
  padding: 16px 14px;
  background: #fff;
  border: 1px solid #dfe8f5;
  border-radius: 8px;
}

.protocol-card-head {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: flex-start;
  margin-bottom: 18px;
}

.protocol-meta,
.protocol-bars div:first-child {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}

.protocol-card-head strong {
  display: block;
  font-size: 15px;
  color: #0f172a;
}

.protocol-card-head span,
.protocol-meta span,
.protocol-bars span {
  font-size: 12px;
  color: #64748b;
}

.protocol-meta span {
  white-space: nowrap;
}

.protocol-badge {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  overflow: hidden;
  font-size: 13px;
  font-weight: 850;
  color: #fff;
  text-align: center;
  border-radius: 50%;
}

.protocol-bars strong {
  font-size: 12px;
  color: #0f172a;
}

.score-track__ok {
  width: 100%;
  background: #20b977;
}

.protocol-card--coap .protocol-badge {
  background: #3a8cff;
}

.protocol-card--dhcp .protocol-badge {
  background: #16c6c0;
}

.protocol-card--ftp .protocol-badge {
  background: #8a65e6;
}

.protocol-card--mqtt .protocol-badge {
  background: #f6a31a;
}

.protocol-card--tls .protocol-badge {
  background: #26b85d;
}

.implementation-table {
  overflow: auto;
  scrollbar-gutter: stable;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.overview-card--ranking .implementation-table {
  flex: 1;
  min-height: 0;
  max-height: 220px;
}

.implementation-row {
  display: grid;
  grid-template-columns:
    minmax(100px, 1.2fr) 76px 68px minmax(136px, 1.2fr)
    74px;
  gap: 10px;
  align-items: center;
  min-height: 42px;
  padding: 0 16px;
  font-size: 12px;
  color: #334155;
  border-top: 1px solid #eef2f7;
}

.implementation-row:first-child {
  border-top: 0;
}

.implementation-row--head {
  min-height: 34px;
  font-weight: 800;
  color: #64748b;
  background: #f8fafc;
}

.implementation-row strong,
.implementation-row span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.implementation-row strong {
  color: #0f172a;
}

.risk-cell {
  display: grid !important;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
}

.risk-cell strong {
  font-weight: 850;
  color: #ff3346;
}

.risk-cell i {
  position: relative;
  height: 6px;
  overflow: hidden;
  background: #edf2f7;
  border-radius: 999px;
}

.risk-cell em {
  position: absolute;
  inset: 0 auto 0 0;
  display: block;
  background: #ff3346;
  border-radius: inherit;
}

.workflow-list {
  display: grid;
  flex: 1;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 28px;
}

.workflow-step {
  position: relative;
  min-width: 0;
  min-height: 136px;
  padding: 18px 16px;
  background: linear-gradient(180deg, #fff 0%, #f8fbff 100%);
  border: 1px solid #e2eaf5;
  border-radius: 8px;
}

.workflow-step:not(:last-child)::after {
  position: absolute;
  top: 50%;
  right: -21px;
  width: 12px;
  height: 12px;
  content: '';
  border-top: 2px solid #9aaac0;
  border-right: 2px solid #9aaac0;
  transform: translateY(-50%) rotate(45deg);
}

.workflow-index {
  position: absolute;
  top: 12px;
  left: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  font-size: 12px;
  font-weight: 850;
  color: #fff;
  background: #1677ff;
  border-radius: 50%;
}

.workflow-step:nth-child(2) .workflow-index {
  background: #20b977;
}

.workflow-step:nth-child(3) .workflow-index {
  background: #8a65e6;
}

.workflow-step:nth-child(4) .workflow-index {
  background: #59b356;
}

.workflow-icon {
  display: flex;
  justify-content: center;
  margin: 2px 0 12px;
  font-size: 40px;
  color: #1677ff;
}

.workflow-step:nth-child(2) .workflow-icon {
  color: #10b3b1;
}

.workflow-step:nth-child(3) .workflow-icon {
  color: #8a65e6;
}

.workflow-step:nth-child(4) .workflow-icon {
  color: #28a879;
}

.workflow-step strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  font-weight: 850;
  color: #172033;
  text-align: center;
  white-space: nowrap;
}

.workflow-step p {
  display: -webkit-box;
  margin: 8px 0 0;
  overflow: hidden;
  -webkit-line-clamp: 2;
  font-size: 12px;
  line-height: 1.55;
  color: #64748b;
  text-align: center;
  -webkit-box-orient: vertical;
}

.finding-list {
  display: grid;
  flex: 1;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.finding-item {
  min-width: 0;
  min-height: 138px;
  padding: 14px;
  background: linear-gradient(180deg, #fff 0%, #fbfdff 100%);
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.finding-head {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.finding-head strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  color: #0f172a;
  white-space: nowrap;
}

.finding-item p {
  display: -webkit-box;
  min-height: 42px;
  margin: 0 0 7px;
  overflow: hidden;
  -webkit-line-clamp: 2;
  font-size: 13px;
  line-height: 1.6;
  color: #0f172a;
  -webkit-box-orient: vertical;
}

.finding-item small {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 3;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
  -webkit-box-orient: vertical;
}

.task-shell {
  min-height: 100%;
  padding: 24px 28px 28px;
}

.extract-shell {
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
  font-size: 24px;
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
  font-size: 15px;
  color: #475569;
}

.task-rule strong {
  font-size: 15px;
  color: #172033;
}

.task-rule code {
  max-width: min(860px, 100%);
  padding: 3px 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 15px;
  color: #172033;
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
  padding: 18px 20px;
  margin-bottom: 18px;
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
  text-overflow: ellipsis;
  font-size: 16px;
  font-weight: 800;
  color: #111827;
  white-space: nowrap;
}

.stepper-state {
  margin-top: 4px;
  font-size: 14px;
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
  font-weight: 700;
  color: #1677ff;
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
  font-weight: 700;
  color: #475569;
}

.stepper-item--error .stepper-circle {
  color: #fff;
  background: #ef4444;
  border-color: #ef4444;
}

.stepper-item--error .stepper-state {
  font-weight: 700;
  color: #dc2626;
}

.workbench-banner,
.workbench-error {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 11px 14px;
  margin-bottom: 14px;
  font-size: 15px;
  border-radius: 8px;
}

.workbench-banner {
  position: relative;
  overflow: hidden;
  color: #0b5cad;
  background: #eef6ff;
  border: 1px solid #d7eaff;
}

.workbench-banner-fill {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--banner-progress, 0%);
  pointer-events: none;
  background: linear-gradient(90deg, #cfe7ff 0%, #b9dcff 58%, #d8ecff 100%);
  border-radius: inherit;
  transition: width 520ms ease;
}

.workbench-banner--progress::after {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--banner-progress, 0%);
  pointer-events: none;
  content: '';
  background: linear-gradient(
    110deg,
    transparent 0%,
    rgb(255 255 255 / 0%) 36%,
    rgb(255 255 255 / 52%) 50%,
    rgb(255 255 255 / 0%) 64%,
    transparent 100%
  );
  transform: translateX(-30%);
  animation: banner-progress-shine 1.8s ease-in-out infinite;
}

.workbench-banner-icon,
.workbench-banner-text,
.workbench-banner-percent,
.workbench-banner .ant-btn {
  position: relative;
  z-index: 1;
}

.workbench-banner-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workbench-banner-percent {
  flex: none;
  margin-left: auto;
  font-size: 14px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  color: #075da8;
}

@keyframes banner-progress-shine {
  0% {
    transform: translateX(-45%);
  }

  100% {
    transform: translateX(120%);
  }
}

.demo-mode-button {
  flex: none;
}

.workbench-error {
  color: #dc2626;
  background: #fff5f5;
  border: 1px solid #ffd6d6;
}

.workbench-content {
  min-height: 420px;
}

.logs-shell {
  min-height: 100%;
  padding: 24px 28px 28px;
}

.logs-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 18px;
}

.logs-header h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  line-height: 1.25;
  letter-spacing: 0;
}

.logs-header p {
  margin: 7px 0 0;
  font-size: 13px;
  color: #64748b;
}

.logs-header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.history-filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin: -4px 0 14px;
}

.history-filter-select {
  width: 180px;
}

.result-history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-history-card,
.result-history-empty {
  background: #fff;
  border: 1px solid #e7edf5;
  border-radius: 8px;
  box-shadow: 0 8px 22px rgb(15 23 42 / 4%);
}

.result-history-card {
  padding: 16px;
}

.result-history-card--summary {
  padding: 14px;
}

.result-history-card--selected {
  border-color: #91caff;
  box-shadow: 0 10px 28px rgb(22 119 255 / 10%);
}

.result-history-head {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}

.result-history-title {
  font-size: 16px;
  font-weight: 800;
  color: #172033;
}

.result-history-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.history-detail-panel {
  padding-top: 14px;
  margin-top: 14px;
  border-top: 1px solid #dbeafe;
}

.history-detail-head {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 14px;
  margin-bottom: 14px;
  border-bottom: 1px solid #e2e8f0;
}

.history-detail-head span {
  display: block;
  margin-bottom: 5px;
  font-size: 12px;
  font-weight: 700;
  color: #1677ff;
}

.history-detail-head h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  line-height: 1.25;
  color: #172033;
}

.history-detail-head p {
  margin: 6px 0 0;
  font-size: 12px;
  color: #64748b;
}

.history-summary-body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.history-summary-body div {
  min-width: 0;
  padding: 10px 12px;
  background: #fbfdff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.history-summary-body span {
  display: block;
  margin-bottom: 5px;
  font-size: 12px;
  color: #64748b;
}

.history-summary-body p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  -webkit-line-clamp: 2;
  font-size: 13px;
  line-height: 1.55;
  color: #334155;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
}

.history-summary-footer {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}

.history-summary-footer span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

.history-summary-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 8px;
  align-items: center;
}

.history-detail-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 14px;
  margin-top: 14px;
  border-top: 1px solid #e2e8f0;
}

.result-history-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.history-block {
  min-width: 0;
  padding: 12px;
  background: #fbfdff;
  border: 1px solid #dbeafe;
  border-radius: 8px;
}

.history-block--wide {
  grid-column: 1 / -1;
}

.history-block span,
.history-block strong,
.history-block small {
  display: block;
}

.history-block span {
  margin-bottom: 6px;
  font-size: 12px;
  color: #64748b;
}

.history-block strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  color: #172033;
  white-space: nowrap;
}

.history-block small {
  margin-top: 5px;
  font-size: 12px;
  color: #64748b;
  overflow-wrap: anywhere;
}

.history-block p {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: #334155;
  overflow-wrap: anywhere;
}

.history-source,
.history-diff {
  margin-top: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.history-warning {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 10px 12px;
  margin-bottom: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: #92400e;
  background: rgb(245 158 11 / 8%);
  border: 1px solid rgb(245 158 11 / 24%);
  border-radius: 8px;
}

.history-source summary,
.history-diff summary {
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 700;
  color: #1677ff;
  cursor: pointer;
}

.history-source-section {
  border-top: 1px solid #e2e8f0;
}

.history-source-section + .history-source-section {
  border-top-color: #dbe4ef;
}

.history-source-head {
  display: grid;
  grid-template-columns: minmax(140px, 0.36fr) minmax(0, 0.64fr);
  gap: 10px;
  align-items: center;
  padding: 9px 12px;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 12px;
  background: #f8fafc;
}

.history-source-head strong,
.history-source-head code {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-source-head code {
  color: #64748b;
  background: transparent;
}

.history-source-code {
  max-height: 360px;
  padding: 8px 0;
  overflow: auto;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 12px;
  line-height: 1.65;
  color: #334155;
  background: #fff;
}

.history-code-row {
  display: grid;
  grid-template-columns: 62px minmax(0, 1fr);
  min-height: 24px;
  padding: 0 12px;
}

.history-code-row--emphasis {
  color: #0b5cad;
  background: #e8f2ff;
}

.history-code-row span {
  color: #94a3b8;
  user-select: none;
}

.history-code-row code {
  min-width: 0;
  color: inherit;
  white-space: pre-wrap;
  background: transparent;
}

.history-diff pre {
  max-height: 360px;
  padding: 12px;
  margin: 0;
  overflow: auto;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 12px;
  line-height: 1.55;
  color: #334155;
  white-space: pre;
  background: #fbfdff;
  border-top: 1px solid #e2e8f0;
}

.history-source pre {
  max-height: 360px;
  padding: 12px;
  margin: 0;
  overflow: auto;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 12px;
  line-height: 1.55;
  color: #334155;
  white-space: pre-wrap;
  background: #fbfdff;
  border-top: 1px solid #e2e8f0;
}

.result-history-empty {
  padding: 56px 20px;
  text-align: center;
}

.result-history-empty--error {
  color: #991b1b;
  background: #fff7f7;
  border-color: #fecaca;
}

.result-history-empty div {
  font-size: 16px;
  font-weight: 800;
  color: #172033;
}

.result-history-empty p {
  margin: 8px 0 0;
  font-size: 13px;
  color: #64748b;
}

.overview-card-head p,
.card-count,
.current-task dt,
.current-task dd,
.protocol-card-head span,
.protocol-meta span,
.protocol-bars span,
.protocol-bars strong,
.workflow-index,
.stepper-state,
.workbench-banner-percent,
.result-history-meta,
.history-detail-head span,
.history-detail-head p,
.history-summary-body span,
.history-summary-footer span,
.history-block span,
.history-block small,
.history-source-head,
.history-code-row span,
.result-history-empty p {
  font-size: 14px;
}

.runtime-status,
.overview-error,
.overview-metric-card span,
.overview-metric-card small,
.implementation-row,
.workflow-step p,
.finding-head strong,
.finding-item p,
.finding-item small,
.workbench-banner,
.logs-header p,
.history-summary-body p,
.history-block strong,
.history-block p,
.history-warning,
.history-source summary,
.history-diff summary {
  font-size: 15px;
}

.protocol-card-head strong,
.workflow-step strong,
.stepper-title,
.result-history-title {
  font-size: 16px;
}

.history-source-code,
.history-diff pre,
.history-source pre {
  font-size: 15px;
}

@media (max-width: 1180px) {
  .guard-layout {
    grid-template-columns: 1fr;
  }

  .guard-sidebar {
    display: none;
  }

  .overview-hero,
  .overview-grid--primary,
  .overview-grid,
  .overview-grid--results {
    grid-template-columns: 1fr;
  }

  .overview-hero {
    min-height: 0;
    padding: 32px;
  }

  .overview-hero-art {
    display: none;
  }

  .overview-hero-flow,
  .workflow-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .overview-hero p {
    white-space: normal;
  }

  .overview-metrics,
  .protocol-scoreboard {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .protocol-card {
    min-width: 0;
  }

  .workflow-step:not(:last-child)::after {
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

  .extract-shell,
  .task-shell {
    padding: 18px 14px;
  }

  .overview-shell {
    padding: 18px 14px;
  }

  .overview-hero,
  .overview-card {
    padding: 16px;
  }

  .overview-hero h1 {
    font-size: 24px;
  }

  .overview-hero-flow {
    display: grid;
    width: 100%;
  }

  .overview-metrics,
  .protocol-scoreboard,
  .finding-list,
  .overview-hero-flow,
  .workflow-list {
    grid-template-columns: 1fr;
  }

  .hero-flow-arrow {
    display: none;
  }

  .overview-card-head {
    flex-direction: column;
  }

  .implementation-table {
    overflow-x: auto;
  }

  .overview-card--ranking .implementation-table {
    max-height: 340px;
  }

  .implementation-row {
    min-width: 540px;
  }

  .logs-shell {
    padding: 18px 14px;
  }

  .history-filter-select {
    width: 100%;
  }

  .result-history-grid {
    grid-template-columns: 1fr;
  }

  .history-summary-body {
    grid-template-columns: 1fr;
  }

  .history-summary-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .history-summary-footer span {
    width: 100%;
    white-space: normal;
  }

  .history-summary-actions {
    justify-content: flex-end;
    width: 100%;
  }
}
</style>
