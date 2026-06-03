import { computed, nextTick, reactive, ref } from 'vue';
import { message } from 'ant-design-vue';

import type {
  ProtocolAssertGenerationJob,
  ProtocolAssertGenerationResult,
  ProtocolExtractRuleItem,
  ProtocolStaticAnalysisDatabaseRuleInsight,
  ProtocolStaticAnalysisJob,
  ProtocolStaticAnalysisResult,
} from '#/api/protocol-compliance';

import {
  checkStatus,
  downloadAflNetPocArtifact,
  executeCommand,
  fetchProtocolStaticAnalysisDatabaseInsights,
  fetchProtocolAssertGenerationProgress,
  fetchProtocolAssertGenerationResult,
  fetchProtocolInstrumentationDiff,
  fetchProtocolStaticAnalysisProgress,
  fetchProtocolStaticAnalysisResult,
  preStartCleanup,
  readLog,
  runProtocolAssertGeneration,
  runProtocolStaticAnalysis,
  snapshotAflNetPoc,
  stopAndCleanup,
  stopProcess,
  writeScript,
} from '#/api/protocol-compliance';

import {
  type CodeLocateEvidence,
  type CodeLocateFunctionSlice,
  type CodeLocateRow,
  DEFAULT_TARGET,
  type ProjectConfig,
  type StageStatus,
  STAGE_LIST,
  type WorkbenchStage,
} from './types';
import { ansiToHtml, normalizeList } from './utils';

const stage = ref<WorkbenchStage>('setup');
const activeStageView = ref<WorkbenchStage>('setup');
const stageStatus = reactive<Record<WorkbenchStage, StageStatus>>({
  setup: 'idle',
  rule_confirm: 'idle',
  code_locate: 'idle',
  assert_gen: 'idle',
  fuzz: 'idle',
  done: 'idle',
});
const stageMessage = ref('请先在“项目设置”中上传所需文件');
const elapsedSeconds = ref(0);
const startedAt = ref<Date | null>(null);
const isStopping = ref(false);
const isTransitioning = ref(false);
const errorMessage = ref<null | string>(null);

const projectConfig = reactive<ProjectConfig>({
  archive: null,
  builder: null,
  config: null,
  rules: null,
  buildInstructions: 'make',
  protocolType: 'MQTT',
  implementation: 'Mosquitto',
  targetHost: DEFAULT_TARGET.MQTT.host,
  targetPort: DEFAULT_TARGET.MQTT.port,
  notes: '',
  fuzzScript: '',
});

const selectedRule = ref<null | ProtocolExtractRuleItem>(null);

const staticJobId = ref<null | string>(null);
const staticJob = ref<null | ProtocolStaticAnalysisJob>(null);
const staticResult = ref<null | ProtocolStaticAnalysisResult>(null);
const staticLogHtml = ref('');
const staticLogText = ref('');
const staticLastEventId = ref(0);
const codeLocateEvidence = ref<CodeLocateEvidence | null>(null);

const assertJobId = ref<null | string>(null);
const assertJob = ref<null | ProtocolAssertGenerationJob>(null);
const assertResult = ref<null | ProtocolAssertGenerationResult>(null);
const assertLogText = ref('');
const assertDiffContent = ref('');

const fuzzPid = ref<null | string>(null);
const fuzzContainerId = ref<null | string>(null);
const aflNetPocPath = ref('');
type FuzzLogLevel = 'INFO' | 'WARN' | 'ERROR' | 'STATS';

const fuzzLogs = ref<Array<{ id: number; text: string; level: FuzzLogLevel }>>([]);
const resultHistory = ref<
  Array<{
    assertionSummary: string;
    changedFileCount: number;
    codeFunctions: Array<{
      codeRows: Array<{ emphasis?: boolean; line: number | string; text: string }>;
      name: string;
      path?: string;
      targetLine?: number | string;
    }>;
    codeLocateSource: string;
    conclusion: string;
    crashLogPath: string;
    diffContent: string;
    finishedAt: string;
    functionCount: number;
    id: string;
    implementation: string;
    pocArtifactId?: string;
    pocArtifactSize?: number;
    pocSnapshotStatus: 'failed' | 'idle' | 'ready' | 'saving';
    protocolType: string;
    ruleText: string;
    status: 'crash' | 'stopped';
    stats: {
      coverage: number;
      crashes: number;
      currentPath: number;
      edges: number;
      hangs: number;
      maxDepth: number;
      nodes: number;
      pathsTotal: number;
      pendingFavs: number;
      pendingTotal: number;
      speed: number;
    };
    targetFile: string;
    targetLine: string;
    violationReason: string;
  }>
>([]);
const fuzzLogReadPosition = ref(0);
const fuzzStats = reactive({
  executions: 0,
  paths: 0,
  currentPath: 0,
  pathsTotal: 0,
  pendingTotal: 0,
  pendingFavs: 0,
  coverage: 0,
  crashes: 0,
  hangs: 0,
  cycles: 0,
  speed: 0,
  maxDepth: 0,
  nodes: 0,
  edges: 0,
});
const fuzzSpeedSeries = ref<number[]>([]);
const downloadingPocArtifactId = ref<null | string>(null);

let elapsedTimer: null | ReturnType<typeof setInterval> = null;
let staticPollTimer: null | ReturnType<typeof setInterval> = null;
let assertPollTimer: null | ReturnType<typeof setInterval> = null;
let fuzzPollTimer: null | ReturnType<typeof setInterval> = null;
let transitionTimer: null | ReturnType<typeof setTimeout> = null;
let transitionResolver: null | ((shouldContinue: boolean) => void) = null;
let fuzzLogIdSeq = 0;
let pipelineRunId = 0;
let lastFuzzLogGrowthAt = 0;
let solAflNetRestartAttempts = 0;
let solAflNetRestarting = false;
let resultHistoryAppended = false;
let resultHistoryIdSeq = 0;
let pendingPocSnapshotPromise: null | Promise<void> = null;

const TEMP_ASSERTION_DATABASE_PATH =
  '/home/lab426_system/protocol-web-ui/violations.db';
const STAGE_TRANSITION_DELAY_MS = 2000;
const SOL_AFLNET_STALE_LOG_RESTART_MS = 25_000;
const SOL_AFLNET_MAX_RESTART_ATTEMPTS = 3;
type WorkbenchPipelineProfile = 'full' | 'fuzz-only';
const WORKBENCH_PIPELINE_PROFILE: WorkbenchPipelineProfile = 'full';

interface ParsedAflNetStats {
  coverage: number;
  crashes: number;
  currentPath: number;
  cycles: number;
  edges: number;
  hangs: number;
  maxDepth: number;
  nodes: number;
  pathsTotal: number;
  pendingFavs: number;
  pendingTotal: number;
  speed: number;
}

function clearTimer(holder: 'static' | 'assert' | 'fuzz' | 'elapsed') {
  if (holder === 'static' && staticPollTimer) {
    clearInterval(staticPollTimer);
    staticPollTimer = null;
  }
  if (holder === 'assert' && assertPollTimer) {
    clearInterval(assertPollTimer);
    assertPollTimer = null;
  }
  if (holder === 'fuzz' && fuzzPollTimer) {
    clearInterval(fuzzPollTimer);
    fuzzPollTimer = null;
  }
  if (holder === 'elapsed' && elapsedTimer) {
    clearInterval(elapsedTimer);
    elapsedTimer = null;
  }
}

function clearTransitionTimer(shouldContinue = false) {
  isTransitioning.value = false;
  if (transitionTimer) {
    clearTimeout(transitionTimer);
    transitionTimer = null;
  }
  if (transitionResolver) {
    const resolve = transitionResolver;
    transitionResolver = null;
    resolve(shouldContinue);
  }
}

function isCurrentPipelineRun(runId: number) {
  return pipelineRunId === runId && !isStopping.value;
}

function waitForStageTransition(runId: number, delay = STAGE_TRANSITION_DELAY_MS) {
  clearTransitionTimer(false);
  isTransitioning.value = true;
  return new Promise<boolean>((resolve) => {
    transitionResolver = resolve;
    transitionTimer = setTimeout(() => {
      isTransitioning.value = false;
      transitionTimer = null;
      transitionResolver = null;
      resolve(isCurrentPipelineRun(runId));
    }, delay);
  });
}

function startElapsedTimer() {
  if (elapsedTimer) return;
  if (!startedAt.value) startedAt.value = new Date();
  elapsedTimer = setInterval(() => {
    if (!startedAt.value) return;
    elapsedSeconds.value = Math.floor(
      (Date.now() - startedAt.value.getTime()) / 1000,
    );
  }, 1000);
}

function formatLogTimestamp() {
  return new Date()
    .toLocaleTimeString('zh-CN', { hour12: false })
    .padStart(8, '0');
}

function withLogTimestamp(text: string) {
  if (/^\s*\[\d{2}:\d{2}:\d{2}\]/.test(text)) return text;
  return `[${formatLogTimestamp()}] ${text}`;
}

function stripFuzzLogPrefix(line: string) {
  return line
    .trim()
    .replace(/^\[\d{2}:\d{2}:\d{2}\]\s*/, '')
    .replace(/^(?:INFO|STATS|WARN|ERROR)[:\s]+/i, '')
    .trim();
}

function parseFiniteNumber(value: string) {
  const normalized = value.replace('%', '').trim();
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseAflNetStatsCsv(line: string): ParsedAflNetStats | null {
  const source = stripFuzzLogPrefix(line).replace(/^#\s*/, '');
  const values = source.split(',').map((item) => item.trim());
  if (values.length < 13) return null;
  if (!values.every((item) => /^-?\d+(?:\.\d+)?%?$/.test(item))) return null;

  const cyclesDone = values[1];
  const curPath = values[2];
  const pathsTotal = values[3];
  const pendingTotal = values[4];
  const pendingFavs = values[5];
  const mapSize = values[6];
  const uniqueCrashes = values[7];
  const uniqueHangs = values[8];
  const maxDepth = values[9];
  const execsPerSec = values[10];
  const nodeCount = values[11];
  const edgeCount = values[12];
  if (
    !cyclesDone ||
    !curPath ||
    !pathsTotal ||
    !pendingTotal ||
    !pendingFavs ||
    !mapSize ||
    !uniqueCrashes ||
    !uniqueHangs ||
    !maxDepth ||
    !execsPerSec ||
    !nodeCount ||
    !edgeCount
  ) return null;

  const parsed = {
    coverage: parseFiniteNumber(mapSize),
    crashes: parseFiniteNumber(uniqueCrashes),
    currentPath: parseFiniteNumber(curPath),
    cycles: parseFiniteNumber(cyclesDone),
    edges: parseFiniteNumber(edgeCount),
    hangs: parseFiniteNumber(uniqueHangs),
    maxDepth: parseFiniteNumber(maxDepth),
    nodes: parseFiniteNumber(nodeCount),
    pathsTotal: parseFiniteNumber(pathsTotal),
    pendingFavs: parseFiniteNumber(pendingFavs),
    pendingTotal: parseFiniteNumber(pendingTotal),
    speed: parseFiniteNumber(execsPerSec),
  };

  if (Object.values(parsed).some((value) => value === null)) return null;
  return parsed as ParsedAflNetStats;
}

function applyAflNetStats(stats: ParsedAflNetStats) {
  fuzzStats.cycles = stats.cycles;
  fuzzStats.currentPath = stats.currentPath;
  fuzzStats.pathsTotal = stats.pathsTotal;
  fuzzStats.paths = stats.pathsTotal;
  fuzzStats.pendingTotal = stats.pendingTotal;
  fuzzStats.pendingFavs = stats.pendingFavs;
  fuzzStats.coverage = stats.coverage;
  fuzzStats.crashes = stats.crashes;
  fuzzStats.hangs = stats.hangs;
  fuzzStats.maxDepth = stats.maxDepth;
  fuzzStats.speed = stats.speed;
  fuzzStats.nodes = stats.nodes;
  fuzzStats.edges = stats.edges;
  fuzzSpeedSeries.value.push(stats.speed);
  if (fuzzSpeedSeries.value.length > 60) fuzzSpeedSeries.value.shift();
}

function formatAflNetStatsForLog(stats: ParsedAflNetStats) {
  return [
    `轮次: ${stats.cycles}`,
    `路径进度: ${stats.currentPath}/${stats.pathsTotal}`,
    `待处理: ${stats.pendingTotal}`,
    `优先路径: ${stats.pendingFavs}`,
    `覆盖率: ${stats.coverage.toFixed(2)}%`,
    `崩溃: ${stats.crashes}`,
    `挂起: ${stats.hangs}`,
    `最大深度: ${stats.maxDepth}`,
    `执行速度: ${stats.speed.toFixed(2)} 次/秒`,
    `状态节点: ${stats.nodes}`,
    `状态转换: ${stats.edges}`,
  ].join(' | ');
}

function normalizeFuzzLogLine(line: string, fallbackLevel: FuzzLogLevel) {
  const plain = stripFuzzLogPrefix(line);
  if (/^#?\s*unix_time\s*,\s*cycles_done\s*,\s*cur_path/i.test(plain)) {
    return {
      level: 'INFO' as FuzzLogLevel,
      text: withLogTimestamp(
        'AFLNet 状态字段已接入：轮次、路径进度、待处理队列、覆盖率、异常数、执行速度、状态机拓扑。',
      ),
    };
  }

  const stats = parseAflNetStatsCsv(line);
  if (stats) {
    return {
      level: 'STATS' as FuzzLogLevel,
      stats,
      text: withLogTimestamp(formatAflNetStatsForLog(stats)),
    };
  }

  return {
    level: fallbackLevel,
    text: withLogTimestamp(plain || line.trim()),
  };
}

function appendFuzzLog(text: string, level: FuzzLogLevel = 'INFO') {
  const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
  for (const line of lines) {
    fuzzLogIdSeq += 1;
    fuzzLogs.value.push({ id: fuzzLogIdSeq, text: withLogTimestamp(line), level });
  }
  if (fuzzLogs.value.length > 500) {
    fuzzLogs.value.splice(0, fuzzLogs.value.length - 500);
  }
}

function getPrimaryStaticVerdict() {
  const verdicts = staticResult.value?.modelResponse?.verdicts ?? [];
  return (
    verdicts.find((verdict) => verdict.compliance === 'non_compliant') ??
    verdicts.find((verdict) => verdict.compliance === 'needs_review') ??
    verdicts[0] ??
    null
  );
}

function getRuleSummaryText() {
  return (
    codeLocateEvidence.value?.ruleText ||
    selectedRule.value?.rule ||
    selectedRule.value?.description ||
    getPrimaryStaticVerdict()?.relatedRule?.requirement ||
    '未记录规则'
  );
}

function getViolationSummaryText() {
  return (
    codeLocateEvidence.value?.violationReason ||
    getPrimaryStaticVerdict()?.explanation ||
    staticResult.value?.modelResponse?.summary?.notes ||
    '未生成违规原因'
  );
}

function getAssertionSummaryText() {
  const changedFileCount =
    (assertDiffContent.value.match(/^diff --git\s+/gm) ?? []).length;
  if (assertResult.value) {
    return `${assertResult.value.assertionCount} 条断言任务，${changedFileCount} 个文件发生插桩变更`;
  }
  if (assertDiffContent.value) {
    return `${changedFileCount} 个文件发生插桩变更`;
  }
  return '未生成断言插桩结果';
}

function getCrashLogPathFromFuzzLogs() {
  if (aflNetPocPath.value.trim()) return aflNetPocPath.value.trim();

  for (const log of fuzzLogs.value) {
    const cnMatch = log.text.match(/崩溃队列信息导出[:：]\s*(.+)$/);
    if (cnMatch?.[1]) return cnMatch[1].trim();

    const aflMatch = log.text.match(
      /(?:crash(?:es)?|queue|poc)[^:：]*[:：]\s*(\/\S+)/i,
    );
    if (aflMatch?.[1]) return aflMatch[1].trim();
  }
  return '';
}

function updateAflNetPocPath(data: any) {
  const nextPath =
    data?.pocPath ||
    data?.poc_path ||
    data?.outputRoot ||
    data?.output_root ||
    data?.log_dir ||
    '';
  if (typeof nextPath === 'string' && nextPath.trim()) {
    aflNetPocPath.value = nextPath.trim();
    return;
  }

  const logFilePath = data?.logFilePath || data?.log_file_path;
  if (typeof logFilePath !== 'string' || !logFilePath.trim()) return;
  const logDir = logFilePath.trim().replace(/[/\\][^/\\]*$/, '');
  if (logDir && logDir !== logFilePath.trim()) aflNetPocPath.value = logDir;
}

async function snapshotResultPocArtifact(historyId: string) {
  const entry = resultHistory.value.find((item) => item.id === historyId);
  if (!entry || entry.stats.crashes <= 0) return;

  const snapshotPromise = (async () => {
    try {
      const artifact = await snapshotAflNetPoc({
        crashLogPath: entry.crashLogPath || undefined,
        implementation: entry.implementation,
        protocol: entry.protocolType,
      });
      const current = resultHistory.value.find((item) => item.id === historyId);
      if (!current) return;
      current.pocArtifactId = artifact.artifactId;
      current.pocArtifactSize = artifact.fileSize;
      current.pocSnapshotStatus = 'ready';
    } catch (err: any) {
      const current = resultHistory.value.find((item) => item.id === historyId);
      if (current) current.pocSnapshotStatus = 'failed';
      appendFuzzLog(`POC 归档失败，历史下载不可用: ${err?.message || err}`, 'WARN');
    }
  })();

  pendingPocSnapshotPromise = snapshotPromise;
  try {
    await snapshotPromise;
  } finally {
    if (pendingPocSnapshotPromise === snapshotPromise) {
      pendingPocSnapshotPromise = null;
    }
  }
}

async function downloadHistoryPocArtifact(historyId: string) {
  const entry = resultHistory.value.find((item) => item.id === historyId);
  if (!entry?.pocArtifactId || entry.pocSnapshotStatus !== 'ready') {
    message.warning('POC 包仍在归档或不可用');
    return;
  }
  if (downloadingPocArtifactId.value) return;

  downloadingPocArtifactId.value = historyId;
  try {
    const blob = await downloadAflNetPocArtifact(entry.pocArtifactId);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${entry.implementation || 'aflnet'}-history-poc-${entry.pocArtifactId}.zip`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (err: any) {
    message.error(err?.message || '历史 POC 下载失败');
  } finally {
    downloadingPocArtifactId.value = null;
  }
}

function appendResultHistoryRecord(reason: 'crash' | 'stopped') {
  if (resultHistoryAppended) return;
  resultHistoryAppended = true;

  const evidence = codeLocateEvidence.value;
  const functionCount =
    evidence?.functions?.length ?? evidence?.candidateFunctionCount ?? 0;
  const hasCrash = reason === 'crash' || fuzzStats.crashes > 0;
  const shouldSnapshotPoc = hasCrash && isSolAflNetFuzzing.value;
  const conclusion =
    hasCrash
      ? `发现 ${fuzzStats.crashes || 1} 个崩溃，已进入结果验证`
      : '流水线已停止，当前结果已汇总';
  const changedFileCount =
    (assertDiffContent.value.match(/^diff --git\s+/gm) ?? []).length;
  const codeFunctions =
    evidence?.functions && evidence.functions.length > 0
      ? evidence.functions
      : evidence?.codeRows && evidence.codeRows.length > 0
        ? [
            {
              codeRows: evidence.codeRows,
              name: '定位源码片段',
              path: evidence.targetFile,
              targetLine: evidence.targetLine,
            },
          ]
        : [];

  resultHistoryIdSeq += 1;
  const historyEntry: (typeof resultHistory.value)[number] = {
    assertionSummary: getAssertionSummaryText(),
    changedFileCount,
    codeFunctions: codeFunctions.map((fn) => ({
      codeRows: fn.codeRows.map((row) => ({ ...row })),
      name: fn.name,
      path: fn.path,
      targetLine: fn.targetLine,
    })),
    codeLocateSource: evidence?.source || '未记录',
    conclusion,
    crashLogPath: getCrashLogPathFromFuzzLogs(),
    diffContent: assertDiffContent.value,
    finishedAt: new Date().toISOString(),
    functionCount,
    id: `result-${Date.now()}-${resultHistoryIdSeq}`,
    implementation: projectConfig.implementation,
    pocSnapshotStatus: shouldSnapshotPoc ? 'saving' : 'idle',
    protocolType: projectConfig.protocolType,
    ruleText: getRuleSummaryText(),
    status: reason,
    stats: {
      coverage: fuzzStats.coverage,
      crashes: fuzzStats.crashes,
      currentPath: fuzzStats.currentPath,
      edges: fuzzStats.edges,
      hangs: fuzzStats.hangs,
      maxDepth: fuzzStats.maxDepth,
      nodes: fuzzStats.nodes,
      pathsTotal: fuzzStats.pathsTotal || fuzzStats.paths,
      pendingFavs: fuzzStats.pendingFavs,
      pendingTotal: fuzzStats.pendingTotal,
      speed: fuzzStats.speed,
    },
    targetFile: evidence?.targetFile || '未生成代码定位结果',
    targetLine: evidence?.targetLine || '-',
    violationReason: getViolationSummaryText(),
  };

  resultHistory.value.unshift(historyEntry);

  if (resultHistory.value.length > 20) {
    resultHistory.value.splice(20);
  }

  if (shouldSnapshotPoc) void snapshotResultPocArtifact(historyEntry.id);
}

function isCrashDiscoveryLine(line: string) {
  const crashCountMatch = line.match(/(?:unique_)?crash(?:es)?[^\d]*(\d+)/i);
  if (crashCountMatch?.[1]) {
    const crashCount = Number(crashCountMatch[1]);
    return Number.isFinite(crashCount) && crashCount > 0;
  }

  const cnCrashCountMatch = line.match(/崩溃[^\d]*(\d+)/);
  if (cnCrashCountMatch?.[1]) {
    const crashCount = Number(cnCrashCountMatch[1]);
    return Number.isFinite(crashCount) && crashCount > 0;
  }

  return /崩溃|fatal|segmentation fault|assertion.*failed|\bcrash(?:es|ed|ing)?\b/i.test(line);
}

async function stopFuzzProcessForCrashVerification(runId: number) {
  const containerId = fuzzContainerId.value;
  const pid = fuzzPid.value;
  if (!pid && !containerId) return;

  fuzzPid.value = null;
  fuzzContainerId.value = null;

  try {
    if (containerId) {
      await stopAndCleanup({
        container_id: containerId,
        protocol: protocolKindForApi.value,
      } as any);
    } else if (pid) {
      await stopProcess({
        pid,
        protocol: protocolKindForApi.value,
      } as any);
    }
    if (isCurrentPipelineRun(runId)) {
      appendFuzzLog('已停止当前 Fuzzer，保留崩溃证据用于结果验证', 'INFO');
    }
  } catch (err: any) {
    if (isCurrentPipelineRun(runId)) {
      appendFuzzLog(`停止 Fuzzer 失败，请人工确认进程状态: ${err?.message || err}`, 'WARN');
    }
  }
}

async function enterResultVerificationAfterCrash() {
  if (stageStatus.fuzz !== 'running' || fuzzStats.crashes <= 0) return false;

  const runId = pipelineRunId;
  clearTimer('fuzz');
  clearTimer('elapsed');
  lastFuzzLogGrowthAt = 0;
  solAflNetRestartAttempts = 0;
  solAflNetRestarting = false;
  appendFuzzLog('检测到首个崩溃，2 秒后自动进入结果验证阶段', 'ERROR');
  stageStatus.fuzz = 'done';
  stageMessage.value = '检测到崩溃，2 秒后进入结果验证…';
  void stopFuzzProcessForCrashVerification(runId);

  if (!(await waitForStageTransition(runId))) return true;

  stage.value = 'done';
  activeStageView.value = 'done';
  stageStatus.done = 'done';
  appendResultHistoryRecord('crash');
  stageMessage.value = '已发现崩溃，结果验证模块已生成证据摘要';
  return true;
}

function setStage(
  next: WorkbenchStage,
  status: StageStatus = 'running',
  msg?: string,
  options: { focus?: boolean } = {},
) {
  stage.value = next;
  if (options.focus !== false) activeStageView.value = next;
  stageStatus[next] = status;
  if (msg) stageMessage.value = msg;
}

function markStageDone(target: WorkbenchStage, msg?: string) {
  stageStatus[target] = 'done';
  if (msg) stageMessage.value = msg;
}

function markStageSkipped(target: WorkbenchStage, msg?: string) {
  stageStatus[target] = 'skipped';
  if (msg) stageMessage.value = msg;
}

function markStageError(target: WorkbenchStage, msg: string) {
  stageStatus[target] = 'error';
  activeStageView.value = target;
  errorMessage.value = msg;
  stageMessage.value = msg;
}

function selectStageView(target: WorkbenchStage) {
  if (stage.value === target || stageStatus[target] !== 'idle') {
    activeStageView.value = target;
    return true;
  }
  return false;
}

const protocolImplementationsKey = computed(() => [
  String(projectConfig.implementation),
]);

const protocolKindForApi = computed(() => {
  if (projectConfig.protocolType === 'MQTT' && projectConfig.implementation === 'SOL') {
    return 'MQTT';
  }
  return projectConfig.protocolType;
});

const isSolAflNetFuzzing = computed(() => (
  projectConfig.protocolType === 'MQTT' && projectConfig.implementation === 'SOL'
));

function formatCleanupSummary(result: any) {
  const data = result?.data ?? result;
  const cleanup = data?.cleanup_results;
  if (!cleanup) return '启动前清理完成';

  const parts = [
    `停止容器 ${cleanup.containers_stopped ?? 0} 个`,
    `删除容器 ${cleanup.containers_removed ?? 0} 个`,
    cleanup.output_cleaned ? '输出目录已清理' : '输出目录无需清理',
  ];
  if (Array.isArray(cleanup.errors) && cleanup.errors.length > 0) {
    parts.push(`错误 ${cleanup.errors.length} 个`);
  }
  return parts.join('，');
}

async function cleanupBeforeFuzzStart(runId: number) {
  if (!isSolAflNetFuzzing.value) return;
  if (!isCurrentPipelineRun(runId)) return;
  if (pendingPocSnapshotPromise) {
    stageMessage.value = '等待上次 POC 归档完成…';
    appendFuzzLog('等待上次 POC 归档完成后再清理 AFLNET 输出目录', 'INFO');
    await pendingPocSnapshotPromise;
    if (!isCurrentPipelineRun(runId)) return;
  }

  stageMessage.value = '清理 SOL/AFLNET 上次运行残留…';
  appendFuzzLog('清理 SOL/AFLNET 上次运行残留：停止旧容器并清空输出目录', 'INFO');
  const cleanupResult = await preStartCleanup({
    protocol: protocolKindForApi.value,
  });
  if (!isCurrentPipelineRun(runId)) return;
  appendFuzzLog(formatCleanupSummary(cleanupResult), 'INFO');
}

function isCurrentFuzzContainerRunning(statusData: any) {
  const dockerContainers = String(statusData?.docker_containers || '');
  if (!dockerContainers.trim()) return false;

  const containerId = fuzzContainerId.value;
  if (containerId) {
    return (
      dockerContainers.includes(containerId) ||
      dockerContainers.includes(containerId.slice(0, 12))
    );
  }
  return dockerContainers.includes('protocolguard:latest');
}

function isFuzzLogFilePresent(data: any) {
  return (
    data?.file_size !== undefined ||
    data?.log_file_exists === true ||
    String(data?.message || '').includes('文件大小')
  );
}

async function restartSolAflNetContainer(runId: number) {
  solAflNetRestartAttempts += 1;
  stageMessage.value = `SOL/AFLNET 容器已停止，正在重启 (${solAflNetRestartAttempts}/${SOL_AFLNET_MAX_RESTART_ATTEMPTS})…`;
  appendFuzzLog(
    `检测到 SOL/AFLNET 容器已停止，正在重启 Docker 容器 (${solAflNetRestartAttempts}/${SOL_AFLNET_MAX_RESTART_ATTEMPTS})`,
    'WARN',
  );

  const launch: any = await executeCommand({
    protocol: protocolKindForApi.value,
    protocolImplementations: protocolImplementationsKey.value,
  });
  if (!isCurrentPipelineRun(runId)) return;

  const launchData = launch?.data ?? launch;
  updateAflNetPocPath(launchData);
  fuzzPid.value = launchData?.pid ? String(launchData.pid) : null;
  fuzzContainerId.value = launchData?.container_id
    ? String(launchData.container_id)
    : null;
  fuzzLogReadPosition.value = 0;
  lastFuzzLogGrowthAt = Date.now();
  stageMessage.value = '模糊测试运行中，点击"停止"结束';
  appendFuzzLog('SOL/AFLNET Docker 容器已重启，重新等待 plot_data 输出', 'INFO');
}

async function checkAndRestartStaleSolAflNetFuzzer(data: any) {
  if (!isSolAflNetFuzzing.value || stageStatus.fuzz !== 'running') return;
  if (solAflNetRestarting || !isFuzzLogFilePresent(data)) return;
  if (!lastFuzzLogGrowthAt) {
    lastFuzzLogGrowthAt = Date.now();
    return;
  }
  if (Date.now() - lastFuzzLogGrowthAt < SOL_AFLNET_STALE_LOG_RESTART_MS) return;

  if (solAflNetRestartAttempts >= SOL_AFLNET_MAX_RESTART_ATTEMPTS) {
    appendFuzzLog('SOL/AFLNET 日志持续无新数据，已达到自动重启次数上限，请人工检查容器和 seed', 'ERROR');
    lastFuzzLogGrowthAt = Date.now();
    return;
  }

  solAflNetRestarting = true;
  const runId = pipelineRunId;
  try {
    appendFuzzLog('plot_data 已存在但 25 秒没有新数据，正在检查 Docker 容器状态', 'WARN');
    const status: any = await checkStatus({
      protocol: protocolKindForApi.value,
      protocolImplementations: protocolImplementationsKey.value,
    });
    if (!isCurrentPipelineRun(runId)) return;

    const statusData = status?.data ?? status;
    updateAflNetPocPath(statusData);
    if (isCurrentFuzzContainerRunning(statusData)) {
      appendFuzzLog('Docker 容器仍在运行，继续等待 AFLNET 写入新状态', 'INFO');
      lastFuzzLogGrowthAt = Date.now();
      return;
    }

    await restartSolAflNetContainer(runId);
  } catch (err: any) {
    if (!isCurrentPipelineRun(runId)) return;
    appendFuzzLog(`SOL/AFLNET 自动重启检查失败: ${err?.message || err}`, 'ERROR');
    lastFuzzLogGrowthAt = Date.now();
  } finally {
    solAflNetRestarting = false;
  }
}

function buildRulesFile(): File {
  if (!selectedRule.value) {
    throw new Error('未选择规则');
  }
  const grouped: Record<string, ProtocolExtractRuleItem[]> = {};
  const rule = selectedRule.value;
  const msgType =
    (rule as { msgType?: string }).msgType ||
    normalizeList(rule.req_type)[0] ||
    normalizeList(rule.res_type)[0] ||
    'DEFAULT';
  grouped[msgType] = [rule];
  const json = JSON.stringify(grouped, null, 2);
  return new File([json], 'rules.json', { type: 'application/json' });
}

function getRelatedVariableCount() {
  const fields = new Set([
    ...normalizeList(selectedRule.value?.req_fields),
    ...normalizeList(selectedRule.value?.res_fields),
  ]);
  return fields.size;
}

function shortenPath(path: string) {
  const trimmed = path.trim();
  if (!trimmed) return '';
  const normalized = trimmed.replaceAll('\\', '/');
  return normalized.split('/').filter(Boolean).pop() || trimmed;
}

function formatLineRange(lines: number[]) {
  const unique = [...new Set(lines)].sort((a, b) => a - b);
  if (unique.length === 0) return '-';
  const first = unique[0]!;
  const last = unique[unique.length - 1]!;
  return first === last ? String(first) : `${first}-${last}`;
}

function normalizeCodeLine(raw: string) {
  return raw.replace(/\s+$/, '');
}

function stripLogPrefix(line: string) {
  return line
    .replace(/^\([^)]+\)\s*/, '')
    .replace(/^.*:\s+(?=(Function:|Path:|func:|\d+\s+))/i, '');
}

function ensureFunctionSlice(
  functions: Map<string, CodeLocateFunctionSlice>,
  name: string,
) {
  const normalized = name.trim();
  const existing = functions.get(normalized);
  if (existing) return existing;
  const next: CodeLocateFunctionSlice = {
    codeRows: [],
    name: normalized,
  };
  functions.set(normalized, next);
  return next;
}

function highlightCodeRows(rows: CodeLocateRow[], preferredLines: number[]) {
  if (rows.length === 0 || rows.some((row) => row.emphasis)) return;
  const preferred = preferredLines.find((line) =>
    rows.some((row) => Number(row.line) === line),
  );
  const targetLine = preferred ?? Number(rows[0]?.line);
  const targetRow = rows.find((row) => Number(row.line) === targetLine) ?? rows[0];
  if (targetRow) targetRow.emphasis = true;
}

function parseCodeSnippetToEvidence(
  snippet: string,
  options: {
    keySliceCount?: number;
    resultLabel?: string;
    ruleText?: string;
    source?: string;
    targetFile?: string | null;
    violationLines?: number[];
    violationReason?: string | null;
  } = {},
): CodeLocateEvidence | null {
  const functions = new Map<string, CodeLocateFunctionSlice>();
  const files = new Set<string>();
  const rows: CodeLocateRow[] = [];
  const pathLines: number[] = [];
  const violationLineSet = new Set(options.violationLines ?? []);
  let firstTargetFile = options.targetFile?.trim() || '';
  let currentFunction: CodeLocateFunctionSlice | null = null;

  for (const rawLine of snippet.split(/\r?\n/)) {
    const line = stripLogPrefix(rawLine);
    const extractedFunctionMatch = line.match(/^func:\s*(.+?)\s*$/i);
    if (extractedFunctionMatch?.[1]) {
      ensureFunctionSlice(functions, extractedFunctionMatch[1]);
      currentFunction = null;
      continue;
    }

    const functionMatch = line.match(/Function:\s*(.+?)\s*$/i);
    if (functionMatch?.[1]) {
      currentFunction = ensureFunctionSlice(functions, functionMatch[1]);
      continue;
    }

    const pathMatch = line.match(/Path:\s*(.+?):(\d+)\s*$/i);
    if (pathMatch?.[1]) {
      const filePath = pathMatch[1].trim();
      files.add(filePath);
      if (!firstTargetFile) firstTargetFile = filePath;
      const lineNumber = Number(pathMatch[2]);
      if (Number.isFinite(lineNumber)) pathLines.push(lineNumber);
      if (currentFunction) {
        currentFunction.path = filePath;
        currentFunction.targetLine = lineNumber;
      }
      continue;
    }

    const codeMatch = line.match(/^\s*(\d{1,7})\s+(.*)$/);
    if (!codeMatch?.[1]) continue;
    const lineNumber = Number(codeMatch[1]);
    const text = normalizeCodeLine(codeMatch[2] ?? '');
    const row: CodeLocateRow = {
      emphasis: violationLineSet.has(lineNumber),
      line: lineNumber,
      text,
    };
    rows.push(row);
    if (currentFunction) currentFunction.codeRows.push(row);
  }

  if (rows.length === 0 && !firstTargetFile && functions.size === 0) return null;

  highlightCodeRows(rows, pathLines);
  const functionSlices = [...functions.values()];
  for (const fn of functionSlices) {
    const targetLine = Number(fn.targetLine);
    highlightCodeRows(fn.codeRows, Number.isFinite(targetLine) ? [targetLine] : []);
  }

  const codeLines = rows
    .map((row) => (typeof row.line === 'number' ? row.line : Number(row.line)))
    .filter((line) => Number.isFinite(line));
  const targetLines =
    violationLineSet.size > 0
      ? [...violationLineSet]
      : pathLines.length > 0
        ? pathLines
        : codeLines;
  const sliceCount = functionSlices.filter((fn) => fn.codeRows.length > 0).length;

  return {
    candidateFunctionCount: functions.size || files.size || 1,
    codeRows: rows,
    functions: functionSlices,
    keySliceCount:
      options.keySliceCount ??
      Math.max(sliceCount, violationLineSet.size || pathLines.length),
    relatedVariableCount: getRelatedVariableCount(),
    resultLabel: options.resultLabel,
    ruleText: options.ruleText,
    source: options.source,
    targetFile: shortenPath(firstTargetFile) || '待定位',
    targetLine: formatLineRange(targetLines),
    updatedAt: new Date().toISOString(),
    violationReason: options.violationReason || undefined,
  };
}

function mergeCodeLocateEvidence(next: CodeLocateEvidence | null, force = false) {
  if (!next) return;
  if (!force && codeLocateEvidence.value?.source === '静态分析数据库') return;
  const currentFunctionCount = codeLocateEvidence.value?.functions?.length ?? 0;
  const nextFunctionCount = next.functions?.length ?? 0;
  if (
    !force &&
    codeLocateEvidence.value &&
    next.codeRows.length <= codeLocateEvidence.value.codeRows.length &&
    nextFunctionCount <= currentFunctionCount
  ) {
    return;
  }
  codeLocateEvidence.value = next;
}

function updateCodeLocateEvidenceFromLogs() {
  const evidence = parseCodeSnippetToEvidence(staticLogText.value, {
    ruleText: selectedRule.value?.rule || selectedRule.value?.description,
    source: '实时控制台',
  });
  mergeCodeLocateEvidence(evidence);
}

function getSelectedRuleText() {
  return selectedRule.value?.rule || selectedRule.value?.description || '';
}

function findBestInsight(findings: ProtocolStaticAnalysisDatabaseRuleInsight[]) {
  const selectedText = getSelectedRuleText().trim();
  if (selectedText) {
    const matched = findings.find((finding) => {
      const ruleDesc = finding.ruleDesc?.trim() || '';
      return ruleDesc.includes(selectedText) || selectedText.includes(ruleDesc);
    });
    if (matched) return matched;
  }
  return (
    findings.find((finding) => finding.result === 'violation_found') ??
    findings.find((finding) => finding.result === 'unknown') ??
    findings[0] ??
    null
  );
}

function buildEvidenceFromInsight(
  insight: ProtocolStaticAnalysisDatabaseRuleInsight,
  findings: ProtocolStaticAnalysisDatabaseRuleInsight[],
) {
  const violations = insight.violations ?? [];
  const violationLines = violations.flatMap((violation) => violation.codeLines ?? []);
  const targetFile =
    violations.find((violation) => violation.filename)?.filename ||
    null;
  const keySliceCount = findings.filter((finding) => finding.result !== 'no_violation').length ||
    violations.length ||
    (insight.result === 'no_violation' ? 0 : 1);

  return parseCodeSnippetToEvidence(insight.codeSnippet || '', {
    keySliceCount,
    resultLabel: insight.resultLabel,
    ruleText: insight.ruleDesc,
    source: '静态分析数据库',
    targetFile,
    violationLines,
    violationReason: insight.reason,
  });
}

async function refreshCodeLocateEvidenceFromResult(
  jobId: string,
  result: ProtocolStaticAnalysisResult,
) {
  try {
    const insights = await fetchProtocolStaticAnalysisDatabaseInsights({
      databasePath: result.artifacts?.database || undefined,
      jobId,
      workspacePath: result.artifacts?.workspace || undefined,
    });
    const findings = insights.findings ?? [];
    const insight = findBestInsight(findings);
    if (!insight) return;
    mergeCodeLocateEvidence(buildEvidenceFromInsight(insight, findings), true);
  } catch (err: any) {
    console.warn('[workbench] code locate insights unavailable', err?.message || err);
  }
}

function buildFuzzScript(): string {
  if (projectConfig.fuzzScript && projectConfig.fuzzScript.trim().length > 0) {
    return projectConfig.fuzzScript;
  }
  const impl = projectConfig.implementation;
  const host = projectConfig.targetHost;
  const port = projectConfig.targetPort;
  if (projectConfig.protocolType === 'MQTT' && impl === 'SOL') {
    return `# AFL-NET MQTT/SOL fuzzing
HOST=${host}
PORT=${port}
IMPLEMENTATION=${impl}
DURATION=0
`;
  }
  if (projectConfig.protocolType === 'MQTT') {
    return `# MBFuzzer MQTT broker fuzzing
broker_host=${host}
broker_port=${port}
implementation=${impl}
`;
  }
  return `# SNMP fuzzing
target_host=${host}
target_port=${port}
`;
}

async function ensureProjectReady(): Promise<boolean> {
  if (!projectConfig.archive) {
    message.warning('请上传源码压缩包');
    return false;
  }
  if (!projectConfig.builder) {
    message.warning('请上传 Builder Dockerfile');
    return false;
  }
  if (!projectConfig.config) {
    message.warning('请上传配置 TOML');
    return false;
  }
  if (!projectConfig.rules) {
    message.warning('请上传协议规则 JSON');
    return false;
  }
  if (!projectConfig.buildInstructions.trim()) {
    message.warning('请填写编译命令');
    return false;
  }
  return true;
}

function commitSetup() {
  if (
    !projectConfig.archive ||
    !projectConfig.builder ||
    !projectConfig.config ||
    !projectConfig.rules
  ) {
    message.warning('请先完成项目设置');
    return;
  }
  if (!projectConfig.buildInstructions.trim()) {
    message.warning('请填写编译命令');
    return;
  }
  stageStatus.setup = 'done';
  stage.value = 'rule_confirm';
  activeStageView.value = 'rule_confirm';
  stageMessage.value = '请选择一条规则后启动自动化流水线';
}

function backToSetup() {
  if (stageStatus.code_locate === 'running' || stageStatus.assert_gen === 'running' || stageStatus.fuzz === 'running') {
    message.warning('请先停止当前流水线');
    return;
  }
  stage.value = 'setup';
  activeStageView.value = 'setup';
  stageStatus.setup = 'idle';
  stageMessage.value = '调整项目设置后重新进入流水线';
}

async function pollStaticAnalysis(jobId: string, runId: number) {
  clearTimer('static');
  staticPollTimer = setInterval(async () => {
    if (!isCurrentPipelineRun(runId)) {
      clearTimer('static');
      return;
    }
    try {
      const snapshot = await fetchProtocolStaticAnalysisProgress(
        jobId,
        staticLastEventId.value || undefined,
      );
      if (!isCurrentPipelineRun(runId)) return;
      staticJob.value = snapshot;
      const events = snapshot.events ?? [];
      if (events.length > 0) {
        for (const evt of events) {
          const stageText = evt.stage ? `(${evt.stage}) ` : '';
          staticLogText.value += `${stageText}${evt.message}\n`;
          if (typeof evt.id === 'number' && evt.id > staticLastEventId.value) {
            staticLastEventId.value = evt.id;
          }
        }
        staticLogHtml.value = ansiToHtml(staticLogText.value);
        updateCodeLocateEvidenceFromLogs();
      }
      if (snapshot.status === 'completed') {
        clearTimer('static');
        const result = await fetchProtocolStaticAnalysisResult(jobId);
        if (!isCurrentPipelineRun(runId)) return;
        staticResult.value = result;
        await refreshCodeLocateEvidenceFromResult(jobId, result);
        if (!isCurrentPipelineRun(runId)) return;
        markStageDone('code_locate', '代码定位完成，2 秒后进入断言生成…');
        if (await waitForStageTransition(runId)) await runAssertGenStep(runId);
      } else if (snapshot.status === 'failed') {
        clearTimer('static');
        markStageError('code_locate', snapshot.error || '静态分析失败');
      }
    } catch (err: any) {
      if (!isCurrentPipelineRun(runId)) return;
      clearTimer('static');
      markStageError('code_locate', err?.message || '静态分析进度查询失败');
    }
  }, 1500);
}

async function pollAssertGen(jobId: string, runId: number) {
  clearTimer('assert');
  assertPollTimer = setInterval(async () => {
    if (!isCurrentPipelineRun(runId)) {
      clearTimer('assert');
      return;
    }
    try {
      const snapshot = await fetchProtocolAssertGenerationProgress(jobId);
      if (!isCurrentPipelineRun(runId)) return;
      assertJob.value = snapshot;
      const events = snapshot.events ?? [];
      if (events.length > 0) {
        const lines = events
          .map((evt) => {
            const ts = evt.timestamp
              ? new Date(evt.timestamp).toLocaleTimeString()
              : '';
            const stageText = evt.stage ? `(${evt.stage}) ` : '';
            return `[${ts}] ${stageText}${evt.message}`;
          })
          .join('\n');
        assertLogText.value = lines;
      }
      if (snapshot.status === 'completed') {
        clearTimer('assert');
        const result = await fetchProtocolAssertGenerationResult(jobId);
        if (!isCurrentPipelineRun(runId)) return;
        assertResult.value = result;
        try {
          const diff = await fetchProtocolInstrumentationDiff(jobId);
          if (!isCurrentPipelineRun(runId)) return;
          assertDiffContent.value = diff?.content || '';
        } catch {
          assertDiffContent.value = '';
        }
        markStageDone('assert_gen', '断言生成完成，2 秒后进入模糊测试…');
        if (await waitForStageTransition(runId)) await runFuzzStep(runId);
      } else if (snapshot.status === 'failed') {
        clearTimer('assert');
        markStageError('assert_gen', snapshot.error || '断言生成失败');
      }
    } catch (err: any) {
      if (!isCurrentPipelineRun(runId)) return;
      clearTimer('assert');
      markStageError('assert_gen', err?.message || '断言生成进度查询失败');
    }
  }, 1500);
}

async function runStaticAnalysisStep(runId: number) {
  if (!projectConfig.archive || !projectConfig.builder || !projectConfig.config) {
    markStageError('code_locate', '项目设置不完整');
    return;
  }
  if (!selectedRule.value) {
    markStageError('code_locate', '未选择规则');
    return;
  }
  setStage('code_locate', 'running', '提交静态分析任务…');
  staticResult.value = null;
  staticLogText.value = '';
  staticLogHtml.value = '';
  staticLastEventId.value = 0;
  codeLocateEvidence.value = null;
  try {
    const job = await runProtocolStaticAnalysis({
      codeArchive: projectConfig.archive,
      builderDockerfile: projectConfig.builder,
      config: projectConfig.config,
      rules: buildRulesFile(),
      notes: projectConfig.notes,
    });
    if (!isCurrentPipelineRun(runId)) return;
    staticJobId.value = job.jobId;
    staticJob.value = job;
    stageMessage.value = '静态分析进行中…';
    if (job.status === 'completed') {
      const result = await fetchProtocolStaticAnalysisResult(job.jobId);
      if (!isCurrentPipelineRun(runId)) return;
      staticResult.value = result;
      await refreshCodeLocateEvidenceFromResult(job.jobId, result);
      if (!isCurrentPipelineRun(runId)) return;
      markStageDone('code_locate', '代码定位完成，2 秒后进入断言生成…');
      if (await waitForStageTransition(runId)) await runAssertGenStep(runId);
    } else if (job.status === 'failed') {
      markStageError('code_locate', job.error || '静态分析失败');
    } else {
      await pollStaticAnalysis(job.jobId, runId);
    }
  } catch (err: any) {
    if (!isCurrentPipelineRun(runId)) return;
    markStageError('code_locate', err?.message || '静态分析启动失败');
  }
}

async function runAssertGenStep(runId: number) {
  if (!isCurrentPipelineRun(runId)) return;
  if (!staticJobId.value) {
    markStageError('assert_gen', '缺少静态分析结果，无法生成断言');
    return;
  }
  if (!projectConfig.archive) {
    markStageError('assert_gen', '缺少源码压缩包');
    return;
  }
  setStage('assert_gen', 'running', '准备固定违规数据库…');
  assertLogText.value = '';
  assertDiffContent.value = '';
  await nextTick();
  if (!isCurrentPipelineRun(runId)) return;
  try {
    stageMessage.value = `使用固定违规数据库: ${TEMP_ASSERTION_DATABASE_PATH}`;
    const job = await runProtocolAssertGeneration({
      codeArchive: projectConfig.archive,
      databasePath: TEMP_ASSERTION_DATABASE_PATH,
      buildInstructions: projectConfig.buildInstructions,
      notes: projectConfig.notes,
    });
    if (!isCurrentPipelineRun(runId)) return;
    assertJobId.value = job.jobId;
    assertJob.value = job;
    stageMessage.value = '断言生成进行中…';
    if (job.status === 'completed') {
      const result = await fetchProtocolAssertGenerationResult(job.jobId);
      if (!isCurrentPipelineRun(runId)) return;
      assertResult.value = result;
      try {
        const diff = await fetchProtocolInstrumentationDiff(job.jobId);
        if (!isCurrentPipelineRun(runId)) return;
        assertDiffContent.value = diff?.content || '';
      } catch {
        assertDiffContent.value = '';
      }
      markStageDone('assert_gen', '断言生成完成，2 秒后进入模糊测试…');
      if (await waitForStageTransition(runId)) await runFuzzStep(runId);
    } else if (job.status === 'failed') {
      markStageError('assert_gen', job.error || '断言生成失败');
    } else {
      await pollAssertGen(job.jobId, runId);
    }
  } catch (err: any) {
    if (!isCurrentPipelineRun(runId)) return;
    markStageError('assert_gen', err?.message || '断言生成启动失败');
  }
}

function parseStatsLine(line: string) {
  const trimmed = line.trim();
  if (!trimmed) return;
  const aflNetStats = parseAflNetStatsCsv(trimmed);
  if (aflNetStats) {
    applyAflNetStats(aflNetStats);
    return;
  }

  const cycleMatch = trimmed.match(/cycles?(?:_done)?[^\d]*(\d+)/i);
  if (cycleMatch?.[1]) {
    const val = Number(cycleMatch[1]);
    if (Number.isFinite(val) && val > fuzzStats.cycles) fuzzStats.cycles = val;
  }

  const pathPairMatch = trimmed.match(/paths?[^\d]*(\d+)\s*\/\s*(\d+)/i);
  if (pathPairMatch?.[1] && pathPairMatch?.[2]) {
    const current = Number(pathPairMatch[1]);
    const total = Number(pathPairMatch[2]);
    if (Number.isFinite(current)) fuzzStats.currentPath = current;
    if (Number.isFinite(total) && total >= fuzzStats.pathsTotal) {
      fuzzStats.pathsTotal = total;
      fuzzStats.paths = total;
    }
  }

  const execMatch = trimmed.match(/execs?(?:_total|_per_sec)?[^\d]*(\d+(?:\.\d+)?)/i);
  if (execMatch?.[1]) {
    const val = Number(execMatch[1]);
    if (Number.isFinite(val) && val > fuzzStats.executions) {
      fuzzStats.executions = Math.floor(val);
    }
  }
  const pathMatch = trimmed.match(/paths?(?:_total)?[^\d]*(\d+)/i);
  if (pathMatch?.[1]) {
    const val = Number(pathMatch[1]);
    if (!pathPairMatch && Number.isFinite(val) && val > fuzzStats.paths) {
      fuzzStats.paths = val;
      fuzzStats.pathsTotal = Math.max(fuzzStats.pathsTotal, val);
    }
  }
  const pendingMatch = trimmed.match(/pending[^\d]*(\d+)(?:\s*\(\s*(\d+)\s*favs?\s*\))?/i);
  if (pendingMatch?.[1]) {
    const val = Number(pendingMatch[1]);
    if (Number.isFinite(val)) fuzzStats.pendingTotal = val;
  }
  if (pendingMatch?.[2]) {
    const val = Number(pendingMatch[2]);
    if (Number.isFinite(val)) fuzzStats.pendingFavs = val;
  }
  const coverageMatch = trimmed.match(/(?:coverage|map_size)[^\d]*(\d+(?:\.\d+)?)/i);
  if (coverageMatch?.[1]) {
    const val = Number(coverageMatch[1]);
    if (Number.isFinite(val)) fuzzStats.coverage = val;
  }
  const crashMatch = trimmed.match(/(?:unique_)?crash(?:es)?[^\d]*(\d+)/i);
  if (crashMatch?.[1]) {
    const val = Number(crashMatch[1]);
    if (Number.isFinite(val) && val > fuzzStats.crashes) fuzzStats.crashes = val;
  }
  const hangMatch = trimmed.match(/(?:unique_)?hang(?:s)?[^\d]*(\d+)/i);
  if (hangMatch?.[1]) {
    const val = Number(hangMatch[1]);
    if (Number.isFinite(val) && val > fuzzStats.hangs) fuzzStats.hangs = val;
  }
  const speedMatch = trimmed.match(/speed[^\d]*(\d+(?:\.\d+)?)/i);
  if (speedMatch?.[1]) {
    const val = Number(speedMatch[1]);
    if (Number.isFinite(val)) {
      fuzzStats.speed = val;
      fuzzSpeedSeries.value.push(val);
      if (fuzzSpeedSeries.value.length > 60) fuzzSpeedSeries.value.shift();
    }
  }
  const depthMatch = trimmed.match(/(?:max_depth|max\s*depth|depth)[^\d]*(\d+)/i);
  if (depthMatch?.[1]) {
    const val = Number(depthMatch[1]);
    if (Number.isFinite(val) && val > fuzzStats.maxDepth) fuzzStats.maxDepth = val;
  }
  const nodesMatch = trimmed.match(/nodes?[^\d]*(\d+)/i);
  if (nodesMatch?.[1]) {
    const val = Number(nodesMatch[1]);
    if (Number.isFinite(val)) fuzzStats.nodes = val;
  }
  const edgesMatch = trimmed.match(/edges?[^\d]*(\d+)/i);
  if (edgesMatch?.[1]) {
    const val = Number(edgesMatch[1]);
    if (Number.isFinite(val)) fuzzStats.edges = val;
  }
}

async function readFuzzLogs() {
  if (!fuzzPollTimer && stage.value !== 'fuzz') return;
  try {
    const response: any = await readLog({
      protocol: protocolKindForApi.value,
      lastPosition: fuzzLogReadPosition.value,
      protocolImplementations: protocolImplementationsKey.value,
    } as any);
    const data = response?.data ?? response;
    updateAflNetPocPath(data);
    const content: string = data?.content || '';
    const position: number = typeof data?.position === 'number' ? data.position : fuzzLogReadPosition.value;
    if (position > fuzzLogReadPosition.value) {
      fuzzLogReadPosition.value = position;
      lastFuzzLogGrowthAt = Date.now();
    }
    if (content) {
      const lines = content.split(/\r?\n/);
      for (const line of lines) {
        if (!line.trim()) continue;
        let level: FuzzLogLevel = 'INFO';
        const lower = line.toLowerCase();
        if (/stats|execs|paths|coverage|cycles|pending|nodes|edges/i.test(line)) level = 'STATS';
        else if (isCrashDiscoveryLine(line) || lower.includes('error')) level = 'ERROR';
        else if (lower.includes('warn')) level = 'WARN';
        const normalized = normalizeFuzzLogLine(line, level);
        appendFuzzLog(normalized.text, normalized.level);
        if (isCrashDiscoveryLine(line)) {
          fuzzStats.crashes = Math.max(fuzzStats.crashes, 1);
        }
        if (normalized.stats) {
          applyAflNetStats(normalized.stats);
        } else if (normalized.level === 'STATS') {
          parseStatsLine(line);
        }
      }
    }
    if (await enterResultVerificationAfterCrash()) return;
    await checkAndRestartStaleSolAflNetFuzzer(data);
  } catch (err: any) {
    // Non-fatal: keep polling until user stops
    console.warn('[workbench] readLog error', err?.message || err);
  }
}

async function runFuzzStep(runId: number) {
  if (!isCurrentPipelineRun(runId)) return;
  setStage('fuzz', 'running', '写入 Fuzz 脚本…');
  fuzzLogs.value = [];
  aflNetPocPath.value = '';
  fuzzLogReadPosition.value = 0;
  resultHistoryAppended = false;
  Object.assign(fuzzStats, {
    executions: 0,
    paths: 0,
    currentPath: 0,
    pathsTotal: 0,
    pendingTotal: 0,
    pendingFavs: 0,
    coverage: 0,
    crashes: 0,
    hangs: 0,
    cycles: 0,
    speed: 0,
    maxDepth: 0,
    nodes: 0,
    edges: 0,
  });
  fuzzSpeedSeries.value = [];
  lastFuzzLogGrowthAt = Date.now();
  solAflNetRestartAttempts = 0;
  solAflNetRestarting = false;
  await nextTick();
  if (!isCurrentPipelineRun(runId)) return;
  try {
    await cleanupBeforeFuzzStart(runId);
    if (!isCurrentPipelineRun(runId)) return;

    const script = buildFuzzScript();
    stageMessage.value = '写入 Fuzz 脚本…';
    await writeScript({
      content: script,
      protocol: protocolKindForApi.value,
      protocolImplementations: protocolImplementationsKey.value,
    } as any);
    if (!isCurrentPipelineRun(runId)) return;
    stageMessage.value = '启动 Fuzzer 容器/进程…';
    const launch: any = await executeCommand({
      protocol: protocolKindForApi.value,
      protocolImplementations: protocolImplementationsKey.value,
    } as any);
    if (!isCurrentPipelineRun(runId)) return;
    const launchData = launch?.data ?? launch;
    updateAflNetPocPath(launchData);
    if (launchData?.pid) fuzzPid.value = String(launchData.pid);
    if (launchData?.container_id) fuzzContainerId.value = String(launchData.container_id);
    lastFuzzLogGrowthAt = Date.now();
    stageMessage.value = '模糊测试运行中，点击"停止"结束';
    void readFuzzLogs();
    fuzzPollTimer = setInterval(readFuzzLogs, 1000);
  } catch (err: any) {
    if (!isCurrentPipelineRun(runId)) return;
    markStageError('fuzz', err?.message || '模糊测试启动失败');
  }
}

async function runConfiguredPipeline(runId: number) {
  if (WORKBENCH_PIPELINE_PROFILE === 'fuzz-only') {
    staticJobId.value = null;
    staticJob.value = null;
    staticResult.value = null;
    staticLogText.value = '';
    staticLogHtml.value = '';
    staticLastEventId.value = 0;
    codeLocateEvidence.value = null;
    assertJobId.value = null;
    assertJob.value = null;
    assertResult.value = null;
    assertLogText.value = '';
    assertDiffContent.value = '';
    markStageSkipped('code_locate');
    markStageSkipped('assert_gen', '已跳过代码定位和断言生成，直接进入模糊测试');
    await nextTick();
    await runFuzzStep(runId);
    return;
  }
  await runStaticAnalysisStep(runId);
}

async function startPipeline(rule: ProtocolExtractRuleItem) {
  if (!(await ensureProjectReady())) return;
  clearTransitionTimer(false);
  pipelineRunId += 1;
  const runId = pipelineRunId;
  selectedRule.value = rule;
  errorMessage.value = null;
  resultHistoryAppended = false;
  startedAt.value = new Date();
  elapsedSeconds.value = 0;
  startElapsedTimer();
  stageStatus.rule_confirm = 'done';
  await runConfiguredPipeline(runId);
}

async function stopPipeline() {
  if (isStopping.value) return;
  isStopping.value = true;
  try {
    pipelineRunId += 1;
    clearTransitionTimer(false);
    clearTimer('static');
    clearTimer('assert');
    clearTimer('fuzz');
    lastFuzzLogGrowthAt = 0;
    solAflNetRestartAttempts = 0;
    solAflNetRestarting = false;
    if (stage.value === 'fuzz' && (fuzzPid.value || fuzzContainerId.value)) {
      try {
        if (fuzzContainerId.value) {
          await stopAndCleanup({
            container_id: fuzzContainerId.value,
            protocol: protocolKindForApi.value,
          } as any);
        } else if (fuzzPid.value) {
          await stopProcess({
            pid: fuzzPid.value,
            protocol: protocolKindForApi.value,
          } as any);
        }
      } catch (err: any) {
        console.warn('[workbench] stop fuzz failed', err?.message || err);
      }
      fuzzPid.value = null;
      fuzzContainerId.value = null;
    }
    if (stageStatus.fuzz === 'running') stageStatus.fuzz = 'done';
    if (stageStatus.code_locate === 'running') stageStatus.code_locate = 'idle';
    if (stageStatus.assert_gen === 'running') stageStatus.assert_gen = 'idle';
    stage.value = 'done';
    activeStageView.value = 'done';
    stageStatus.done = 'done';
    appendResultHistoryRecord('stopped');
    clearTimer('elapsed');
    stageMessage.value = '流水线已停止';
  } finally {
    isStopping.value = false;
  }
}

function resetWorkbench() {
  pipelineRunId += 1;
  clearTransitionTimer(false);
  clearTimer('static');
  clearTimer('assert');
  clearTimer('fuzz');
  clearTimer('elapsed');
  for (const s of STAGE_LIST) stageStatus[s.key] = 'idle';
  stageStatus.setup = 'idle';
  stage.value = 'setup';
  activeStageView.value = 'setup';
  startedAt.value = null;
  isTransitioning.value = false;
  elapsedSeconds.value = 0;
  selectedRule.value = null;
  staticJobId.value = null;
  staticJob.value = null;
  staticResult.value = null;
  staticLogText.value = '';
  staticLogHtml.value = '';
  staticLastEventId.value = 0;
  codeLocateEvidence.value = null;
  assertJobId.value = null;
  assertJob.value = null;
  assertResult.value = null;
  assertLogText.value = '';
  assertDiffContent.value = '';
  fuzzPid.value = null;
  fuzzContainerId.value = null;
  aflNetPocPath.value = '';
  downloadingPocArtifactId.value = null;
  fuzzLogs.value = [];
  fuzzLogReadPosition.value = 0;
  resultHistoryAppended = false;
  lastFuzzLogGrowthAt = 0;
  solAflNetRestartAttempts = 0;
  solAflNetRestarting = false;
  Object.assign(fuzzStats, {
    executions: 0,
    paths: 0,
    currentPath: 0,
    pathsTotal: 0,
    pendingTotal: 0,
    pendingFavs: 0,
    coverage: 0,
    crashes: 0,
    hangs: 0,
    cycles: 0,
    speed: 0,
    maxDepth: 0,
    nodes: 0,
    edges: 0,
  });
  fuzzSpeedSeries.value = [];
  errorMessage.value = null;
  stageMessage.value = '请先在“项目设置”中上传所需文件';
}

export function useWorkbench() {
  return {
    // State
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
    staticJob,
    staticJobId,
    staticResult,
    staticLogHtml,
    staticLogText,
    codeLocateEvidence,
    assertJob,
    assertJobId,
    assertResult,
    assertLogText,
    assertDiffContent,
    fuzzLogs,
    resultHistory,
    fuzzStats,
    fuzzSpeedSeries,
    fuzzPid,
    fuzzContainerId,
    aflNetPocPath,
    downloadingPocArtifactId,

    // Methods
    commitSetup,
    backToSetup,
    startPipeline,
    stopPipeline,
    resetWorkbench,
    selectStageView,
    downloadHistoryPocArtifact,
  };
}
