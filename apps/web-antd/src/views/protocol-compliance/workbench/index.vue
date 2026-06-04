<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

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

interface OverviewSummary {
  analysisRecords: number;
  codeSnippets: number;
  databaseFiles: number;
  implementations: number;
  noViolationRules: number;
  ruleResults: number;
  unknownRules: number;
  violationLocations: number;
  violationRules: number;
}

interface OverviewProtocolStats {
  analysisRecords: number;
  codeSnippets: number;
  implementations: number;
  name: string;
  noViolationRules: number;
  ruleResults: number;
  unknownRules: number;
  violationLocations: number;
  violationRules: number;
}

interface OverviewImplementationStats
  extends Omit<OverviewProtocolStats, 'implementations' | 'name'> {
  database: string;
  name: string;
  protocol: string;
}

interface OverviewFinding {
  implementation: string;
  protocol: string;
  reason?: null | string;
  rule?: null | string;
}

interface ProtocolGuardOverviewStats {
  generatedAt: string;
  implementations: OverviewImplementationStats[];
  protocols: OverviewProtocolStats[];
  sourceDirectory: string;
  summary: OverviewSummary;
  tableTotals: Record<string, number>;
  topFindings: OverviewFinding[];
}

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
  aflNetPocPath,
  resultHistory,
  fuzzStats,
  fuzzSpeedSeries,
  downloadingPocArtifactId,
  commitSetup,
  backToSetup,
  selectStageView,
  startPipeline,
  stopPipeline,
  resetWorkbench,
  downloadHistoryPocArtifact,
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

const overviewStats = ref<null | ProtocolGuardOverviewStats>(null);
const overviewLoadError = ref('');

const projectIntroParagraphs = [
  '网络协议实现应严格遵循其规范，以保障通信的可靠性与安全性。然而，自然语言规范固有的模糊性易导致开发者理解偏差，使实际实现偏离标准行为。此类协议不合规漏洞在现实世界的协议实现中普遍存在，可引发行为错误、互操作性故障乃至严重的安全漏洞。例如，MatrixSSL 中的高危漏洞 CVE-2022-46505 即源于其会话恢复处理对 RFC 的错误实现，该验证逻辑缺陷允许攻击者通过精心构造的会话 ID 强制重用空的主密钥，最终导致全球数万台设备的安全通信被完全解密。与内存损坏型漏洞不同，不合规漏洞常表现为静默的逻辑错误，缺乏崩溃等明显异常信号，因此难以被模糊测试等传统方法有效检测。现有检测方法通常依赖大量人工来验证发现和进行根因分析，严重制约了其在实际应用中的可扩展性。',
  '为此，我们提出 ProtocolGuard，一种新颖的框架，通过将大语言模型引导的静态分析与基于模糊测试的动态验证相结合，系统化检测协议实现中的非合规性漏洞。ProtocolGuard 首先采用混合方法从协议规范中自动提取规范规则，并执行大语言模型引导的程序切片，精准抽取与每条规则相关的代码片段。随后，利用大语言模型识别这些规则与代码逻辑之间的语义不一致，并动态验证此类不一致是否可被实际触发。首先 ProtocolGuard 先借助大语言模型自动生成断言语句，并通过代码插桩将静默的不一致转化为可观测的断言失败；接着，利用大语言模型生成更可能触发漏洞的初始测试用例；最后，对插桩后的代码实施动态测试，以确认漏洞存在并生成概念验证测试用例。',
  '当前成果统计以 database 目录下的 SQLite 结果库为准，覆盖 MQTT、TLS、DHCPv6、FTP 与 CoAP 等协议实现。平台会聚合规则分析、程序切片、代码片段、LLM 判定与违规定位等数据，形成面向甲方演示的总体成果视图。',
];

const fallbackSummary: OverviewSummary = {
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

const overviewMetrics = computed(() => [
  {
    accent: 'blue',
    icon: 'mdi:database-search-outline',
    label: '结果数据库',
    suffix: '个',
    value: overviewSummary.value.databaseFiles,
  },
  {
    accent: 'cyan',
    icon: 'mdi:chart-box-outline',
    label: '分析记录',
    suffix: '条',
    value: overviewSummary.value.analysisRecords,
  },
  {
    accent: 'green',
    icon: 'mdi:clipboard-check-outline',
    label: '规则级结果',
    suffix: '条',
    value: overviewSummary.value.ruleResults,
  },
  {
    accent: 'red',
    icon: 'mdi:alert-octagon-outline',
    label: '违规判定',
    suffix: '条',
    value: overviewSummary.value.violationRules,
  },
  {
    accent: 'orange',
    icon: 'mdi:source-branch',
    label: '违规定位',
    suffix: '处',
    value: overviewSummary.value.violationLocations,
  },
  {
    accent: 'purple',
    icon: 'mdi:code-braces',
    label: '代码片段',
    suffix: '段',
    value: overviewSummary.value.codeSnippets,
  },
]);

const protocolOverview = computed(() => overviewStats.value?.protocols || []);
const implementationOverview = computed(
  () => overviewStats.value?.implementations || [],
);
const topFindings = computed(() => overviewStats.value?.topFindings || []);
const tableTotalEntries = computed(() => {
  return Object.entries(overviewStats.value?.tableTotals || {}).sort(
    (left, right) => right[1] - left[1],
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

function formatPercent(value: number, total: number) {
  if (!total) return '0%';
  return `${Math.round((value / total) * 100)}%`;
}

function barWidth(value: number, total: number) {
  if (!total || value <= 0) return '0%';
  return `${Math.max(4, Math.round((value / total) * 100))}%`;
}

onMounted(async () => {
  try {
    const response = await fetch(
      `${import.meta.env.BASE_URL}protocolguard-overview.json`,
      {
        cache: 'no-store',
      },
    );
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    overviewStats.value = (await response.json()) as ProtocolGuardOverviewStats;
  } catch (error) {
    overviewLoadError.value =
      error instanceof Error ? error.message : '统计数据读取失败';
  }
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
          <section v-if="activeSideNav === 'overview'" class="overview-shell">
            <header class="overview-hero">
              <div class="overview-hero-copy">
                <div class="overview-kicker">
                  <IconifyIcon icon="mdi:shield-search" />
                  <span>ProtocolGuard</span>
                </div>
                <h1>协议实现非合规漏洞检测与验证平台</h1>
                <p>
                  将规范规则提取、LLM 引导静态分析、断言插桩和动态验证串联为可复用流程，
                  面向协议实现中的静默逻辑缺陷形成端到端证据链。
                </p>
              </div>
              <div class="overview-hero-panel">
                <span>数据来源</span>
                <strong>{{ overviewStats?.sourceDirectory || 'database' }}</strong>
                <small>更新时间: {{ generatedAtDisplay }}</small>
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

            <section class="overview-grid">
              <article class="overview-card overview-card--intro">
                <header class="overview-card-head">
                  <div>
                    <h2>项目介绍</h2>
                    <p>面向协议实现语义偏差的自动化分析框架</p>
                  </div>
                  <Tag color="blue">LLM + 静态分析 + Fuzz</Tag>
                </header>
                <div class="intro-copy">
                  <p
                    v-for="paragraph in projectIntroParagraphs"
                    :key="paragraph"
                  >
                    {{ paragraph }}
                  </p>
                </div>
              </article>

              <article class="overview-card overview-card--pipeline">
                <header class="overview-card-head">
                  <div>
                    <h2>分析链路</h2>
                    <p>数据库中的多阶段分析记录</p>
                  </div>
                </header>
                <div class="pipeline-records">
                  <div
                    v-for="[tableName, count] in tableTotalEntries"
                    :key="tableName"
                    class="pipeline-record"
                  >
                    <div>
                      <strong>{{ tableName }}</strong>
                      <span>{{ formatNumber(count) }} 条</span>
                    </div>
                    <div class="record-track">
                      <i
                        :style="{
                          width: barWidth(
                            count,
                            overviewSummary.analysisRecords,
                          ),
                        }"
                      />
                    </div>
                  </div>
                </div>
              </article>
            </section>

            <section class="overview-card">
              <header class="overview-card-head">
                <div>
                  <h2>成果展示</h2>
                  <p>按协议族聚合的规则结果与违规定位情况</p>
                </div>
                <Tag color="red">
                  违规占比
                  {{
                    formatPercent(
                      overviewSummary.violationRules,
                      overviewSummary.ruleResults,
                    )
                  }}
                </Tag>
              </header>

              <div class="protocol-scoreboard">
                <article
                  v-for="item in protocolOverview"
                  :key="item.name"
                  class="protocol-card"
                >
                  <div class="protocol-card-head">
                    <strong>{{ item.name }}</strong>
                    <span>{{ item.implementations }} 个实现</span>
                  </div>
                  <div class="protocol-main-value">
                    {{ formatNumber(item.violationRules) }}
                    <small>条违规判定</small>
                  </div>
                  <div class="protocol-bars">
                    <div>
                      <span>规则覆盖</span>
                      <strong>{{ formatNumber(item.ruleResults) }}</strong>
                    </div>
                    <div class="score-track">
                      <i
                        class="score-track__ok"
                        :style="{
                          width: barWidth(
                            item.noViolationRules,
                            item.ruleResults,
                          ),
                        }"
                      />
                      <i
                        class="score-track__risk"
                        :style="{
                          width: barWidth(
                            item.violationRules,
                            item.ruleResults,
                          ),
                        }"
                      />
                    </div>
                  </div>
                  <div class="protocol-meta">
                    <span>定位 {{ formatNumber(item.violationLocations) }} 处</span>
                    <span>记录 {{ formatNumber(item.analysisRecords) }} 条</span>
                  </div>
                </article>
              </div>
            </section>

            <section class="overview-grid overview-grid--results">
              <article class="overview-card">
                <header class="overview-card-head">
                  <div>
                    <h2>实现排名</h2>
                    <p>按违规判定数量排序</p>
                  </div>
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
                    v-for="item in implementationOverview"
                    :key="item.database"
                    class="implementation-row"
                  >
                    <strong>{{ item.name }}</strong>
                    <span>{{ item.protocol }}</span>
                    <span>{{ formatNumber(item.ruleResults) }}</span>
                    <span class="risk-text">
                      {{ formatNumber(item.violationRules) }}
                    </span>
                    <span>{{ formatNumber(item.violationLocations) }}</span>
                  </div>
                </div>
              </article>

              <article class="overview-card">
                <header class="overview-card-head">
                  <div>
                    <h2>典型发现</h2>
                    <p>来自规则结果库的代表性违规样例</p>
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
                <h1>日志信息</h1>
                <p>历史运行结果 · 共 {{ resultHistory.length }} 条</p>
              </div>
              <Tag :color="resultHistory.length > 0 ? 'blue' : 'default'">
                {{ resultHistory.length > 0 ? '已记录' : '暂无结果' }}
              </Tag>
            </header>

            <div v-if="resultHistory.length > 0" class="result-history-list">
              <article
                v-for="entry in resultHistory"
                :key="entry.id"
                class="result-history-card"
              >
                <div class="result-history-head">
                  <div>
                    <div class="result-history-title">
                      {{ entry.implementation }} {{ entry.protocolType }} 分析结果
                    </div>
                    <div class="result-history-meta">
                      {{ formatTime(entry.finishedAt) }} · {{ entry.conclusion }}
                    </div>
                  </div>
                  <Tag :color="entry.stats.crashes > 0 ? 'error' : 'default'">
                    {{ entry.stats.crashes > 0 ? '发现崩溃' : '已停止' }}
                  </Tag>
                </div>

                <section class="result-history-grid">
                  <div class="history-block history-block--wide">
                    <span>触发规则</span>
                    <p>{{ entry.ruleText }}</p>
                  </div>
                  <div class="history-block history-block--wide">
                    <span>定位结论</span>
                    <p>{{ entry.violationReason }}</p>
                  </div>
                  <div class="history-block">
                    <span>代码定位</span>
                    <strong>{{ entry.targetFile }}:{{ entry.targetLine }}</strong>
                    <small>{{ entry.functionCount }} 个相关函数 · {{ entry.codeLocateSource }}</small>
                  </div>
                  <div class="history-block">
                    <span>断言生成</span>
                    <strong>{{ entry.assertionSummary }}</strong>
                    <small>{{ entry.changedFileCount }} 个文件变更</small>
                  </div>
                  <div class="history-block">
                    <span>Fuzz 结果</span>
                    <strong>
                      崩溃 {{ entry.stats.crashes }} · 挂起 {{ entry.stats.hangs }}
                    </strong>
                    <small>
                      路径 {{ entry.stats.currentPath }}/{{ entry.stats.pathsTotal }} ·
                      覆盖率 {{ entry.stats.coverage.toFixed(2) }}%
                    </small>
                  </div>
                  <div class="history-block">
                    <span>POC 输出</span>
                    <strong>
                      {{
                        entry.stats.crashes <= 0
                          ? '未生成 POC 包'
                          : entry.pocSnapshotStatus === 'ready'
                            ? 'POC 包已归档'
                            : entry.pocSnapshotStatus === 'failed'
                              ? 'POC 归档失败'
                              : entry.pocSnapshotStatus === 'saving'
                                ? '正在归档 POC 包'
                                : '未归档 POC 包'
                      }}
                    </strong>
                    <small>
                      速度 {{ entry.stats.speed.toFixed(2) }} exec/sec
                    </small>
                    <Button
                      v-if="entry.pocSnapshotStatus !== 'idle'"
                      class="history-poc-download"
                      size="small"
                      type="link"
                      :disabled="entry.pocSnapshotStatus !== 'ready'"
                      :loading="
                        entry.pocSnapshotStatus === 'saving' ||
                        downloadingPocArtifactId === entry.id
                      "
                      @click="downloadHistoryPocArtifact(entry.id)"
                    >
                      <template #icon><IconifyIcon icon="mdi:download" /></template>
                      下载 POC
                    </Button>
                  </div>
                </section>

                <details v-if="entry.codeFunctions.length > 0" class="history-source">
                  <summary>查看相关函数源码</summary>
                  <section
                    v-for="fn in entry.codeFunctions"
                    :key="`${entry.id}-${fn.name}`"
                    class="history-source-section"
                  >
                    <div class="history-source-head">
                      <strong>{{ fn.name }}</strong>
                      <code>{{ fn.path || entry.targetFile }}:{{ fn.targetLine || '-' }}</code>
                    </div>
                    <div class="history-source-code">
                      <div
                        v-for="(row, idx) in fn.codeRows"
                        :key="`${entry.id}-${fn.name}-${row.line}-${idx}`"
                        class="history-code-row"
                        :class="{ 'history-code-row--emphasis': row.emphasis }"
                      >
                        <span>{{ row.line }}</span>
                        <code>{{ row.text }}</code>
                      </div>
                    </div>
                  </section>
                </details>

                <details v-if="entry.diffContent" class="history-diff">
                  <summary>查看插桩代码差异</summary>
                  <pre>{{ entry.diffContent }}</pre>
                </details>
              </article>
            </div>

            <section v-else class="result-history-empty">
              <div>暂无历史运行结果</div>
              <p>流水线进入结果验证或手动停止后，会在这里记录一条结果快照。</p>
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

.overview-shell {
  min-height: 100%;
  padding: 24px 28px 28px;
}

.overview-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 18px;
  align-items: stretch;
  margin-bottom: 16px;
}

.overview-hero-copy,
.overview-hero-panel,
.overview-card,
.overview-metric-card,
.overview-error {
  background: #fff;
  border: 1px solid #e7edf5;
  border-radius: 8px;
  box-shadow: 0 8px 22px rgb(15 23 42 / 4%);
}

.overview-hero-copy {
  min-width: 0;
  padding: 22px 24px;
}

.overview-kicker {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 800;
  color: #1677ff;
}

.overview-kicker :first-child {
  font-size: 18px;
}

.overview-hero h1 {
  margin: 0;
  font-size: 25px;
  font-weight: 850;
  line-height: 1.28;
  color: #111827;
  letter-spacing: 0;
}

.overview-hero p {
  max-width: 920px;
  margin: 10px 0 0;
  font-size: 14px;
  line-height: 1.75;
  color: #475569;
}

.overview-hero-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  padding: 18px;
  background: linear-gradient(135deg, #ffffff 0%, #f5f9ff 100%);
}

.overview-hero-panel span,
.overview-hero-panel small {
  font-size: 12px;
  color: #64748b;
}

.overview-hero-panel strong {
  margin: 7px 0 8px;
  overflow: hidden;
  font-size: 28px;
  font-weight: 850;
  line-height: 1.1;
  color: #1677ff;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.overview-error {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
  padding: 11px 14px;
  font-size: 13px;
  color: #dc2626;
  background: #fff5f5;
}

.overview-metrics {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.overview-metric-card {
  display: flex;
  gap: 12px;
  align-items: center;
  min-width: 0;
  padding: 14px;
}

.metric-icon {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  font-size: 22px;
  border-radius: 8px;
}

.overview-metric-card span {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  color: #64748b;
}

.overview-metric-card strong {
  display: block;
  min-width: 0;
  overflow: hidden;
  font-size: 22px;
  font-weight: 850;
  line-height: 1.15;
  color: #172033;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.overview-metric-card small {
  margin-left: 3px;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.overview-metric-card--blue .metric-icon {
  color: #1677ff;
  background: #edf5ff;
}

.overview-metric-card--cyan .metric-icon {
  color: #0891b2;
  background: #ecfeff;
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

.overview-metric-card--purple .metric-icon {
  color: #7c3aed;
  background: #f5f3ff;
}

.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
  gap: 16px;
  margin-bottom: 16px;
}

.overview-grid--results {
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  align-items: start;
}

.overview-card {
  min-width: 0;
  padding: 18px;
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
  font-size: 17px;
  font-weight: 850;
  line-height: 1.25;
  color: #172033;
  letter-spacing: 0;
}

.overview-card-head p {
  margin: 5px 0 0;
  font-size: 12px;
  color: #64748b;
}

.intro-copy {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.intro-copy p {
  margin: 0;
  font-size: 14px;
  line-height: 1.85;
  color: #334155;
  text-align: justify;
}

.pipeline-records {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pipeline-record {
  min-width: 0;
}

.pipeline-record div:first-child {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.pipeline-record strong {
  min-width: 0;
  overflow: hidden;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 12px;
  color: #172033;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pipeline-record span {
  flex: 0 0 auto;
  font-size: 12px;
  color: #64748b;
}

.record-track,
.score-track {
  position: relative;
  height: 8px;
  overflow: hidden;
  background: #eef2f7;
  border-radius: 999px;
}

.record-track i,
.score-track i {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  display: block;
  border-radius: inherit;
}

.record-track i {
  background: #1677ff;
}

.protocol-scoreboard {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.protocol-card {
  min-width: 0;
  padding: 14px;
  background: #fbfdff;
  border: 1px solid #dbeafe;
  border-radius: 8px;
}

.protocol-card-head,
.protocol-meta,
.protocol-bars div:first-child {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}

.protocol-card-head strong {
  font-size: 15px;
  color: #172033;
}

.protocol-card-head span,
.protocol-meta span,
.protocol-bars span {
  font-size: 12px;
  color: #64748b;
}

.protocol-main-value {
  margin: 14px 0 12px;
  font-size: 26px;
  font-weight: 850;
  line-height: 1.1;
  color: #dc2626;
}

.protocol-main-value small {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.protocol-bars strong {
  font-size: 12px;
  color: #172033;
}

.score-track {
  display: flex;
  margin: 7px 0 11px;
}

.score-track__ok {
  background: #28a879;
}

.score-track__risk {
  left: auto !important;
  right: 0;
  background: #ef4444;
}

.implementation-table {
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.implementation-row {
  display: grid;
  grid-template-columns: minmax(110px, 1.3fr) 80px repeat(3, minmax(52px, 0.6fr));
  gap: 10px;
  align-items: center;
  min-height: 38px;
  padding: 0 12px;
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
  color: #172033;
}

.risk-text {
  font-weight: 800;
  color: #dc2626 !important;
}

.finding-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.finding-item {
  min-width: 0;
  padding: 12px;
  background: #fbfdff;
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
  font-size: 13px;
  color: #172033;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.finding-item p {
  display: -webkit-box;
  min-height: 42px;
  margin: 0 0 7px;
  overflow: hidden;
  font-size: 13px;
  line-height: 1.6;
  color: #172033;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.finding-item small {
  display: -webkit-box;
  overflow: hidden;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
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

.result-history-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
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
  font-size: 13px;
  color: #172033;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-block small {
  margin-top: 5px;
  font-size: 12px;
  color: #64748b;
}

.history-poc-download {
  height: 24px;
  padding: 0;
  margin-top: 8px;
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
  margin: 0;
  padding: 12px;
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

.result-history-empty {
  padding: 56px 20px;
  text-align: center;
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

@media (max-width: 1180px) {
  .guard-layout {
    grid-template-columns: 1fr;
  }

  .guard-sidebar {
    display: none;
  }

  .overview-hero,
  .overview-grid,
  .overview-grid--results {
    grid-template-columns: 1fr;
  }

  .overview-metrics,
  .protocol-scoreboard {
    grid-template-columns: repeat(2, minmax(0, 1fr));
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

  .overview-shell {
    padding: 18px 14px;
  }

  .overview-hero-copy,
  .overview-card,
  .overview-hero-panel {
    padding: 16px;
  }

  .overview-hero h1 {
    font-size: 22px;
  }

  .overview-metrics,
  .protocol-scoreboard,
  .finding-list {
    grid-template-columns: 1fr;
  }

  .overview-card-head {
    flex-direction: column;
  }

  .implementation-table {
    overflow-x: auto;
  }

  .implementation-row {
    min-width: 540px;
  }

  .logs-shell {
    padding: 18px 14px;
  }

  .result-history-grid {
    grid-template-columns: 1fr;
  }
}
</style>
