import type {
  CodeLocateEvidence,
  CodeLocateFunctionSlice,
  CodeLocateRow,
  ProjectConfig,
  StageStatus,
  WorkbenchStage,
} from './types';

import type {
  ProtocolAssertGenerationJob,
  ProtocolAssertGenerationResult,
  ProtocolExtractRuleItem,
  ProtocolFuzzingJob,
  ProtocolStaticAnalysisDatabaseRuleInsight,
  ProtocolStaticAnalysisJob,
  ProtocolStaticAnalysisResult,
  ProtocolStaticAnalysisRuleViolationDetail,
} from '#/api/protocol-compliance';

import { nextTick, reactive, ref } from 'vue';

import { message } from 'ant-design-vue';

import {
  fetchProtocolAssertGenerationProgress,
  fetchProtocolAssertGenerationResult,
  fetchProtocolFuzzConfigLogs,
  fetchProtocolFuzzingLogs,
  fetchProtocolInstrumentationDiff,
  fetchProtocolStaticAnalysisDatabaseInsights,
  fetchProtocolStaticAnalysisProgress,
  fetchProtocolStaticAnalysisResult,
  runProtocolAssertGeneration,
  runProtocolStaticAnalysis,
  startProtocolFuzzConfigJob,
  startProtocolFuzzingDebugJob,
  startProtocolFuzzingJob,
  stopProtocolFuzzingJob,
} from '#/api/protocol-compliance';

import { STAGE_LIST } from './types';
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
const isAwaitingAssertConfirmation = ref(false);
const errorMessage = ref<null | string>(null);

const projectConfig = reactive<ProjectConfig>({
  archive: null,
  rules: null,
  notes: '',
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

const fuzzJobId = ref<null | string>(null);
const fuzzConfigJobId = ref<null | string>(null);
const fuzzJob = ref<null | ProtocolFuzzingJob>(null);
const aflNetPocPath = ref('');
type FuzzLogLevel = 'ERROR' | 'INFO' | 'STATS' | 'WARN';

const fuzzLogs = ref<Array<{ id: number; level: FuzzLogLevel; text: string }>>(
  [],
);
const resultHistory = ref<
  Array<{
    assertionSummary: string;
    changedFileCount: number;
    codeFunctions: Array<{
      codeRows: Array<{
        emphasis?: boolean;
        line: number | string;
        text: string;
      }>;
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
    ruleText: string;
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
    status: 'crash' | 'no-crash' | 'stopped';
    targetFile: string;
    targetLine: string;
    violationReason: string;
  }>
>([]);
const fuzzLogReadPosition = ref(0);
const fuzzConfigLogReadPosition = ref(0);
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

let elapsedTimer: null | ReturnType<typeof setInterval> = null;
let staticPollTimer: null | ReturnType<typeof setInterval> = null;
let assertPollTimer: null | ReturnType<typeof setInterval> = null;
let fuzzPollTimer: null | ReturnType<typeof setInterval> = null;
let transitionTimer: null | ReturnType<typeof setTimeout> = null;
let transitionResolver: ((shouldContinue: boolean) => void) | null = null;
let fuzzLogIdSeq = 0;
let pipelineRunId = 0;
let resultHistoryAppended = false;
let resultHistoryIdSeq = 0;

const STAGE_TRANSITION_DELAY_MS = 2000;

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

function clearTimer(holder: 'assert' | 'elapsed' | 'fuzz' | 'static') {
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

function waitForStageTransition(
  runId: number,
  delay = STAGE_TRANSITION_DELAY_MS,
) {
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

function parseCountNumber(value: string) {
  const parsed = parseFiniteNumber(value);
  return parsed === null ? null : Math.max(0, Math.trunc(parsed));
}

function parseAflNetStatsCsv(line: string): null | ParsedAflNetStats {
  const source = stripFuzzLogPrefix(line).replace(/^#\s*/, '');
  const values = source.split(',').map((item) => item.trim());
  if (values.length < 10) return null;
  if (!values.every((item) => /^-?\d+(?:\.\d+)?%?$/.test(item))) return null;

  const cyclesDone = values[1];
  const curPath = values[2];
  const pathsTotal = values[3];
  const pendingTotal = values[4];
  const hasExtendedTopologyColumns = values.length >= 13;
  const hasPendingFavsColumn = values.length >= 11;
  const pendingFavs = hasPendingFavsColumn ? values[5] : '0';
  const mapSize = hasPendingFavsColumn ? values[6] : values[5];
  const uniqueCrashes = hasPendingFavsColumn ? values[7] : values[6];
  const uniqueHangs = hasPendingFavsColumn ? values[8] : values[7];
  const maxDepth = hasPendingFavsColumn ? values[9] : values[8];
  const execsPerSec = hasPendingFavsColumn ? values[10] : values[9];
  const nodeCount = hasExtendedTopologyColumns ? values[11] : values[2];
  const edgeCount = hasExtendedTopologyColumns ? values[12] : values[3];
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
  )
    return null;

  const parsed = {
    coverage: parseFiniteNumber(mapSize),
    crashes: parseCountNumber(uniqueCrashes),
    currentPath: parseCountNumber(curPath),
    cycles: parseCountNumber(cyclesDone),
    edges: parseCountNumber(edgeCount),
    hangs: parseCountNumber(uniqueHangs),
    maxDepth: parseCountNumber(maxDepth),
    nodes: parseCountNumber(nodeCount),
    pathsTotal: parseCountNumber(pathsTotal),
    pendingFavs: parseCountNumber(pendingFavs),
    pendingTotal: parseCountNumber(pendingTotal),
    speed: parseFiniteNumber(execsPerSec),
  };

  if (Object.values(parsed).includes(null)) return null;
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
    return null;
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
    fuzzLogs.value.push({
      id: fuzzLogIdSeq,
      text: withLogTimestamp(line),
      level,
    });
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

function getResolvedStaticAnalysisProtocol() {
  const candidates = [
    staticResult.value?.modelResponse?.metadata?.protocol,
    staticResult.value?.inputs?.protocolName,
  ];
  const protocol = candidates.find((value) => {
    const normalized = value?.trim().toLowerCase();
    return normalized && !['auto', 'rules', 'unknown'].includes(normalized);
  });
  if (!protocol) {
    throw new Error('静态分析未能识别协议，无法生成 Fuzz 运行配置');
  }
  return protocol.trim();
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
    '未生成分析说明'
  );
}

function getAssertionSummaryText() {
  const changedFileCount = (
    assertDiffContent.value.match(/^diff --git\s+/gm) ?? []
  ).length;
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
    const cnSeparatorIndex = log.text.search(/[:：]/);
    if (log.text.startsWith('崩溃队列信息导出') && cnSeparatorIndex !== -1) {
      const queuePath = log.text.slice(cnSeparatorIndex + 1).trim();
      if (queuePath) return queuePath;
    }

    const aflMatch = log.text.match(
      /(?:crash|queue|poc)[^:：]*[:：]\s*(\/\S+)/i,
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

function getEvidenceFallbackFunctionSlices(
  evidence: CodeLocateEvidence | null,
  name: string,
) {
  if (!evidence?.codeRows || evidence.codeRows.length === 0) return [];
  return [
    {
      codeRows: evidence.codeRows,
      name,
      path: evidence.targetFile,
      targetLine: evidence.targetLine,
    },
  ];
}

function getResultHistoryConclusion(
  reason: 'crash' | 'no-crash' | 'stopped',
  crashCount: number,
) {
  if (reason === 'crash' || crashCount > 0) {
    return `AFL 发现 ${crashCount || 1} 个崩溃，已汇总运行产物`;
  }
  if (reason === 'no-crash') {
    return '静态分析未发现违规，后续断言生成和模糊测试已跳过';
  }
  return '分析流程已停止，当前 AFL 输出已汇总';
}

function appendResultHistoryRecord(reason: 'crash' | 'no-crash' | 'stopped') {
  if (resultHistoryAppended) return;
  resultHistoryAppended = true;

  const evidence = codeLocateEvidence.value;
  const functionCount =
    evidence?.functions?.length ?? evidence?.candidateFunctionCount ?? 0;
  const conclusion = getResultHistoryConclusion(reason, fuzzStats.crashes);
  const changedFileCount = (
    assertDiffContent.value.match(/^diff --git\s+/gm) ?? []
  ).length;
  const codeFunctions =
    evidence?.functions && evidence.functions.length > 0
      ? evidence.functions
      : getEvidenceFallbackFunctionSlices(evidence, '定位源码片段');

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
    implementation: 'Agent inferred',
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
}

function isCrashDiscoveryLine(line: string) {
  if (isFuzzerStartupErrorLine(line)) return false;

  const crashCountMatch = line.match(/(?:unique_)?crash\D*(\d+)/i);
  if (crashCountMatch?.[1]) {
    const crashCount = Number(crashCountMatch[1]);
    return Number.isFinite(crashCount) && crashCount > 0;
  }

  const cnCrashCountMatch = line.match(/崩溃\D*(\d+)/);
  if (cnCrashCountMatch?.[1]) {
    const crashCount = Number(cnCrashCountMatch[1]);
    return Number.isFinite(crashCount) && crashCount > 0;
  }

  return /崩溃|segmentation fault|assertion.*failed|\bcrash(?:es|ed|ing)?\b/i.test(
    line,
  );
}

function isFuzzerStartupErrorLine(line: string) {
  return /PROGRAM ABORT|PG_FUZZ_INSTRUMENTED_CODE_DIR|cannot infer how to build or launch|Seed corpus directory|Target binary not found|AFLNet startup failed/i.test(
    line,
  );
}

async function stopFuzzProcessForCrashVerification(runId: number) {
  const jobId = fuzzJobId.value;
  if (!jobId) return;

  try {
    await stopProtocolFuzzingJob(jobId);
    if (isCurrentPipelineRun(runId)) {
      appendFuzzLog('已停止当前 Fuzzer，保留 AFL 输出用于结果汇总', 'INFO');
    }
  } catch (error: any) {
    if (isCurrentPipelineRun(runId)) {
      appendFuzzLog(
        `停止 Fuzzer 失败，请人工确认进程状态: ${error?.message || error}`,
        'WARN',
      );
    }
  }
}

async function enterResultVerificationAfterCrash() {
  if (stageStatus.fuzz !== 'running' || fuzzStats.crashes <= 0) return false;

  const runId = pipelineRunId;
  clearTimer('fuzz');
  clearTimer('elapsed');
  appendFuzzLog('检测到首个崩溃，2 秒后自动进入 AFL 运行结果', 'ERROR');
  stageStatus.fuzz = 'done';
  stageMessage.value = '检测到崩溃，2 秒后进入 AFL 运行结果…';
  void stopFuzzProcessForCrashVerification(runId);

  if (!(await waitForStageTransition(runId))) return true;

  stage.value = 'done';
  activeStageView.value = 'done';
  stageStatus.done = 'done';
  appendResultHistoryRecord('crash');
  stageMessage.value = 'AFL 已发现崩溃，运行产物已汇总';
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

function completePipelineAfterNoStaticViolation(
  result: ProtocolStaticAnalysisResult,
) {
  const check = result.staticAnalysisCheck;
  const total =
    check?.totalCount ?? result.modelResponse?.summary?.compliantCount ?? 0;
  const invalid = check?.invalidCount ?? 0;
  const suffix = invalid > 0 ? `，其中 ${invalid} 条结果格式需要复核` : '';
  markStageDone('code_locate');
  markStageSkipped('assert_gen');
  markStageSkipped('fuzz');
  stage.value = 'done';
  activeStageView.value = 'done';
  stageStatus.done = 'done';
  stageMessage.value = `静态分析未发现违规（${total} 条规则结果均无违规${suffix}），后续流程已跳过`;
  appendResultHistoryRecord('no-crash');
}

function pauseBeforeAssertGeneration() {
  markStageDone('code_locate');
  stage.value = 'code_locate';
  activeStageView.value = 'code_locate';
  isAwaitingAssertConfirmation.value = true;
  stageMessage.value = '静态分析完成，请确认结果后进入断言生成';
}

function shouldSkipAfterStaticAnalysis(result: ProtocolStaticAnalysisResult) {
  const check = result.staticAnalysisCheck;
  if (check) return check.shouldSkipDownstream;
  const summary = result.modelResponse?.summary;
  return Boolean(summary && summary.nonCompliantCount === 0);
}

function selectStageView(target: WorkbenchStage) {
  if (canViewStage(target)) {
    activeStageView.value = target;
    return true;
  }
  return false;
}

function canViewStage(target: WorkbenchStage) {
  if (target === 'setup') return true;
  if (stage.value === target) return true;
  if (stageStatus[target] !== 'idle') return true;
  return false;
}

function resetPipelineStageState() {
  clearTransitionTimer(false);
  clearTimer('static');
  clearTimer('assert');
  clearTimer('fuzz');
  isAwaitingAssertConfirmation.value = false;

  for (const s of STAGE_LIST) stageStatus[s.key] = 'idle';
  stageStatus.rule_confirm = 'done';
  errorMessage.value = null;
  resultHistoryAppended = false;
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
  fuzzConfigJobId.value = null;
  fuzzConfigLogReadPosition.value = 0;
  fuzzJobId.value = null;
  fuzzJob.value = null;
  aflNetPocPath.value = '';
  fuzzLogs.value = [];
  fuzzLogReadPosition.value = 0;
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
}

function finishFuzzFromCurrentOutput() {
  clearTimer('fuzz');
  clearTimer('elapsed');
  stageStatus.fuzz = 'done';
  stage.value = 'done';
  activeStageView.value = 'done';
  stageStatus.done = 'done';
  appendResultHistoryRecord(fuzzStats.crashes > 0 ? 'crash' : 'stopped');
  stageMessage.value = getFuzzCompletionMessage();
}

function getFuzzCompletionMessage() {
  if (fuzzStats.crashes > 0) {
    return 'AFL 已发现崩溃，运行产物已汇总';
  }
  return '检测到容器停止，已读取当前输出数据';
}

function buildRulesFile(): File {
  if (!selectedRule.value) {
    throw new Error('未选择规则');
  }
  const grouped: Record<
    string,
    Array<{
      req_fields: string[];
      req_type: string;
      res_fields: string[];
      res_type: string;
      rule: string;
    }>
  > = {};
  const rule = selectedRule.value;
  const msgType =
    (rule as { msgType?: string }).msgType ||
    normalizeList(rule.req_type)[0] ||
    normalizeList(rule.res_type)[0] ||
    'DEFAULT';

  const req_type = normalizeList(rule.req_type)[0] || '';
  const req_fields = normalizeList(rule.req_fields);
  const res_type = normalizeList(rule.res_type)[0] || '';
  const res_fields = normalizeList(rule.res_fields);

  grouped[msgType] = [
    {
      rule: rule.rule || '',
      req_type,
      req_fields,
      res_type,
      res_fields,
    },
  ];
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
  return normalized.split('/').findLast(Boolean) || trimmed;
}

function formatLineRange(lines: number[]) {
  const unique = [...new Set(lines)].sort((a, b) => a - b);
  if (unique.length === 0) return '-';
  const [first] = unique;
  const last = unique.at(-1);
  if (first === undefined || last === undefined) return '-';
  return first === last ? String(first) : `${first}-${last}`;
}

function getCodeLocateTargetLines(
  violationLineSet: Set<number>,
  pathLines: number[],
  codeLines: number[],
) {
  if (violationLineSet.size > 0) return [...violationLineSet];
  if (pathLines.length > 0) return pathLines;
  return codeLines;
}

function getKeySliceCount(
  findings: ProtocolStaticAnalysisDatabaseRuleInsight[],
  violations: ProtocolStaticAnalysisRuleViolationDetail[],
  result: ProtocolStaticAnalysisDatabaseRuleInsight['result'],
) {
  const actionableFindingCount = findings.filter(
    (finding) => finding.result !== 'no_violation',
  ).length;
  if (actionableFindingCount > 0) return actionableFindingCount;
  if (violations.length > 0) return violations.length;
  return result === 'no_violation' ? 0 : 1;
}

function normalizeCodeLine(raw: string) {
  return raw.replace(/\s+$/, '');
}

function parseNumberedCodeLine(line: string) {
  const trimmedStart = line.trimStart();
  let digitEnd = 0;
  while (
    digitEnd < trimmedStart.length &&
    /\d/.test(trimmedStart.charAt(digitEnd))
  ) {
    digitEnd += 1;
  }
  if (digitEnd === 0 || digitEnd > 7) return null;
  const separator = trimmedStart[digitEnd];
  if (separator !== undefined && !/\s/.test(separator)) return null;

  return {
    lineNumber: Number(trimmedStart.slice(0, digitEnd)),
    text: trimmedStart.slice(digitEnd).trimStart(),
  };
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
  const targetRow =
    rows.find((row) => Number(row.line) === targetLine) ?? rows[0];
  if (targetRow) targetRow.emphasis = true;
}

function parseCodeSnippetToEvidence(
  snippet: string,
  options: {
    keySliceCount?: number;
    resultLabel?: string;
    ruleText?: string;
    source?: string;
    targetFile?: null | string;
    violationLines?: number[];
    violationReason?: null | string;
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
    const lowerLine = line.toLowerCase();
    if (lowerLine.startsWith('func:')) {
      const functionName = line.slice(line.indexOf(':') + 1).trim();
      if (!functionName) continue;
      ensureFunctionSlice(functions, functionName);
      currentFunction = null;
      continue;
    }

    if (lowerLine.startsWith('function:')) {
      const functionName = line.slice(line.indexOf(':') + 1).trim();
      if (!functionName) continue;
      currentFunction = ensureFunctionSlice(functions, functionName);
      continue;
    }

    if (lowerLine.startsWith('path:')) {
      const pathValue = line.slice(line.indexOf(':') + 1).trim();
      const lineSeparatorIndex = pathValue.lastIndexOf(':');
      if (lineSeparatorIndex !== -1) {
        const filePath = pathValue.slice(0, lineSeparatorIndex).trim();
        const lineNumber = Number(
          pathValue.slice(lineSeparatorIndex + 1).trim(),
        );
        if (filePath) {
          files.add(filePath);
          if (!firstTargetFile) firstTargetFile = filePath;
          if (Number.isFinite(lineNumber)) pathLines.push(lineNumber);
          if (currentFunction) {
            currentFunction.path = filePath;
            currentFunction.targetLine = lineNumber;
          }
        }
      }
      continue;
    }

    const codeLine = parseNumberedCodeLine(line);
    if (!codeLine) continue;
    const { lineNumber } = codeLine;
    const text = normalizeCodeLine(codeLine.text);
    const row: CodeLocateRow = {
      emphasis: violationLineSet.has(lineNumber),
      line: lineNumber,
      text,
    };
    rows.push(row);
    if (currentFunction) currentFunction.codeRows.push(row);
  }

  if (rows.length === 0 && !firstTargetFile && functions.size === 0)
    return null;

  highlightCodeRows(rows, pathLines);
  const functionSlices = [...functions.values()];
  for (const fn of functionSlices) {
    const targetLine = Number(fn.targetLine);
    highlightCodeRows(
      fn.codeRows,
      Number.isFinite(targetLine) ? [targetLine] : [],
    );
  }

  const codeLines = rows
    .map((row) => (typeof row.line === 'number' ? row.line : Number(row.line)))
    .filter((line) => Number.isFinite(line));
  const targetLines = getCodeLocateTargetLines(
    violationLineSet,
    pathLines,
    codeLines,
  );
  const sliceCount = functionSlices.filter(
    (fn) => fn.codeRows.length > 0,
  ).length;

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

function mergeCodeLocateEvidence(
  next: CodeLocateEvidence | null,
  force = false,
) {
  if (!next) return;
  if (
    !force &&
    ['代码定位与一致性分析', '静态分析数据库'].includes(
      codeLocateEvidence.value?.source || '',
    )
  ) {
    return;
  }
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

function findBestInsight(
  findings: ProtocolStaticAnalysisDatabaseRuleInsight[],
) {
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
  const violationLines = violations.flatMap(
    (violation) => violation.codeLines ?? [],
  );
  const targetFile =
    violations.find((violation) => violation.filename)?.filename || null;
  const keySliceCount = getKeySliceCount(findings, violations, insight.result);

  return parseCodeSnippetToEvidence(insight.codeSnippet || '', {
    keySliceCount,
    resultLabel: insight.resultLabel,
    ruleText: insight.ruleDesc,
    source: '代码定位与一致性分析',
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
  } catch (error: any) {
    console.warn(
      '[workbench] code locate insights unavailable',
      error?.message || error,
    );
  }
}

async function ensureProjectReady(): Promise<boolean> {
  if (!projectConfig.archive) {
    message.warning('请上传源码压缩包');
    return false;
  }
  if (!projectConfig.rules) {
    message.warning('请上传协议规则 JSON');
    return false;
  }
  return true;
}

function commitSetup() {
  if (!projectConfig.archive || !projectConfig.rules) {
    message.warning('请先完成项目设置');
    return;
  }
  stageStatus.setup = 'done';
  stage.value = 'rule_confirm';
  activeStageView.value = 'rule_confirm';
  stageMessage.value = '请选择一条规则后启动自动化分析流程';
}

function backToSetup() {
  if (
    stageStatus.code_locate === 'running' ||
    stageStatus.assert_gen === 'running' ||
    stageStatus.fuzz === 'running'
  ) {
    message.warning('请先停止当前分析流程');
    return;
  }
  stage.value = 'setup';
  activeStageView.value = 'setup';
  stageStatus.setup = 'idle';
  stageMessage.value = '调整项目设置后重新进入分析流程';
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
          const ts = evt.timestamp
            ? new Date(evt.timestamp).toLocaleTimeString()
            : '';
          const stageText = evt.stage ? `(${evt.stage}) ` : '';
          const timeText = ts ? `[${ts}] ` : '';
          staticLogText.value += `${stageText}${timeText}${evt.message}\n`;
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
        if (shouldSkipAfterStaticAnalysis(result)) {
          completePipelineAfterNoStaticViolation(result);
          return;
        }
        pauseBeforeAssertGeneration();
      } else if (snapshot.status === 'failed') {
        clearTimer('static');
        markStageError('code_locate', snapshot.error || '静态分析失败');
      }
    } catch (error: any) {
      if (!isCurrentPipelineRun(runId)) return;
      clearTimer('static');
      markStageError('code_locate', error?.message || '静态分析进度查询失败');
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
    } catch (error: any) {
      if (!isCurrentPipelineRun(runId)) return;
      clearTimer('assert');
      markStageError('assert_gen', error?.message || '断言生成进度查询失败');
    }
  }, 1500);
}

async function runStaticAnalysisStep(runId: number) {
  if (!projectConfig.archive || !projectConfig.rules) {
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
      if (shouldSkipAfterStaticAnalysis(result)) {
        completePipelineAfterNoStaticViolation(result);
        return;
      }
      pauseBeforeAssertGeneration();
    } else if (job.status === 'failed') {
      markStageError('code_locate', job.error || '静态分析失败');
    } else {
      await pollStaticAnalysis(job.jobId, runId);
    }
  } catch (error: any) {
    if (!isCurrentPipelineRun(runId)) return;
    markStageError('code_locate', error?.message || '静态分析启动失败');
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
  const analysisDataPath = staticResult.value?.artifacts?.database;
  if (!analysisDataPath) {
    markStageError('assert_gen', '缺少代码定位与一致性分析结果数据');
    return;
  }
  setStage('assert_gen', 'running', '准备代码定位与一致性分析结果…');
  assertLogText.value = '';
  assertDiffContent.value = '';
  await nextTick();
  if (!isCurrentPipelineRun(runId)) return;
  try {
    stageMessage.value = `使用分析结果数据: ${analysisDataPath}`;
    const job = await runProtocolAssertGeneration({
      codeArchive: projectConfig.archive,
      databasePath: analysisDataPath,
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
  } catch (error: any) {
    if (!isCurrentPipelineRun(runId)) return;
    markStageError('assert_gen', error?.message || '断言生成启动失败');
  }
}

async function confirmAssertGeneration() {
  if (!isAwaitingAssertConfirmation.value) return;
  if (!isCurrentPipelineRun(pipelineRunId)) return;
  isAwaitingAssertConfirmation.value = false;
  await runAssertGenStep(pipelineRunId);
}

function parseStatsLine(line: string) {
  const trimmed = line.trim();
  if (!trimmed) return;
  const aflNetStats = parseAflNetStatsCsv(trimmed);
  if (aflNetStats) {
    applyAflNetStats(aflNetStats);
    return;
  }

  const cycleMatch = trimmed.match(/cycle\D*(\d+)/i);
  if (cycleMatch?.[1]) {
    const val = Number(cycleMatch[1]);
    if (Number.isFinite(val) && val > fuzzStats.cycles) fuzzStats.cycles = val;
  }

  const pathPairMatch = trimmed.match(/path\D*(\d+)\s*\/\s*(\d+)/i);
  if (pathPairMatch?.[1] && pathPairMatch?.[2]) {
    const current = Number(pathPairMatch[1]);
    const total = Number(pathPairMatch[2]);
    if (Number.isFinite(current)) fuzzStats.currentPath = current;
    if (Number.isFinite(total) && total >= fuzzStats.pathsTotal) {
      fuzzStats.pathsTotal = total;
      fuzzStats.paths = total;
    }
  }

  const execMatch = trimmed.match(/exec\D*(\d+(?:\.\d+)?)/i);
  if (execMatch?.[1]) {
    const val = Number(execMatch[1]);
    if (Number.isFinite(val) && val > fuzzStats.executions) {
      fuzzStats.executions = Math.floor(val);
    }
  }
  const pathMatch = trimmed.match(/path\D*(\d+)/i);
  if (pathMatch?.[1]) {
    const val = Number(pathMatch[1]);
    if (!pathPairMatch && Number.isFinite(val) && val > fuzzStats.paths) {
      fuzzStats.paths = val;
      fuzzStats.pathsTotal = Math.max(fuzzStats.pathsTotal, val);
    }
  }
  const pendingMatch = trimmed.match(
    /pending\D*(\d+)(?:\s*\(\s*(\d+)\s*favs?\s*\))?/i,
  );
  if (pendingMatch?.[1]) {
    const val = Number(pendingMatch[1]);
    if (Number.isFinite(val)) fuzzStats.pendingTotal = val;
  }
  if (pendingMatch?.[2]) {
    const val = Number(pendingMatch[2]);
    if (Number.isFinite(val)) fuzzStats.pendingFavs = val;
  }
  const coverageMatch = trimmed.match(
    /(?:coverage|map_size)\D*(\d+(?:\.\d+)?)/i,
  );
  if (coverageMatch?.[1]) {
    const val = Number(coverageMatch[1]);
    if (Number.isFinite(val)) fuzzStats.coverage = val;
  }
  const crashMatch = trimmed.match(/(?:unique_)?crash\D*(\d+)/i);
  if (crashMatch?.[1]) {
    const val = Number(crashMatch[1]);
    if (Number.isFinite(val) && val > fuzzStats.crashes)
      fuzzStats.crashes = val;
  }
  const hangMatch = trimmed.match(/(?:unique_)?hang\D*(\d+)/i);
  if (hangMatch?.[1]) {
    const val = Number(hangMatch[1]);
    if (Number.isFinite(val) && val > fuzzStats.hangs) fuzzStats.hangs = val;
  }
  const speedMatch = trimmed.match(/speed\D*(\d+(?:\.\d+)?)/i);
  if (speedMatch?.[1]) {
    const val = Number(speedMatch[1]);
    if (Number.isFinite(val)) {
      fuzzStats.speed = val;
      fuzzSpeedSeries.value.push(val);
      if (fuzzSpeedSeries.value.length > 60) fuzzSpeedSeries.value.shift();
    }
  }
  const depthMatch = trimmed.match(/(?:max_depth|max\s*depth|depth)\D*(\d+)/i);
  if (depthMatch?.[1]) {
    const val = Number(depthMatch[1]);
    if (Number.isFinite(val) && val > fuzzStats.maxDepth)
      fuzzStats.maxDepth = val;
  }
  const nodesMatch = trimmed.match(/node\D*(\d+)/i);
  if (nodesMatch?.[1]) {
    const val = Number(nodesMatch[1]);
    if (Number.isFinite(val)) fuzzStats.nodes = val;
  }
  const edgesMatch = trimmed.match(/edge\D*(\d+)/i);
  if (edgesMatch?.[1]) {
    const val = Number(edgesMatch[1]);
    if (Number.isFinite(val)) fuzzStats.edges = val;
  }
}

async function readFuzzLogs(options: { runId?: number } = {}) {
  if (!fuzzPollTimer && stage.value !== 'fuzz') return;
  const jobId = fuzzJobId.value;
  if (!jobId) return;
  try {
    const data = await fetchProtocolFuzzingLogs(
      jobId,
      fuzzLogReadPosition.value,
    );
    fuzzJob.value = data.job;
    updateAflNetPocPath(data);
    const jobFailed = data.job?.status === 'failed';
    if (jobFailed && (!options.runId || isCurrentPipelineRun(options.runId))) {
      clearTimer('fuzz');
      clearTimer('elapsed');
      markStageError(
        'fuzz',
        data.job.error || data.job.message || 'AFLNet 启动失败',
      );
    }
    const content: string = data?.content || '';
    const position: number =
      typeof data?.position === 'number'
        ? data.position
        : fuzzLogReadPosition.value;
    if (position > fuzzLogReadPosition.value) {
      fuzzLogReadPosition.value = position;
    }
    if (content) {
      const lines = content.split(/\r?\n/);
      for (const line of lines) {
        if (!line.trim()) continue;
        let level: FuzzLogLevel = 'INFO';
        const lower = line.toLowerCase();
        if (/stats|execs|paths|coverage|cycles|pending|nodes|edges/i.test(line))
          level = 'STATS';
        else if (
          isCrashDiscoveryLine(line) ||
          isFuzzerStartupErrorLine(line) ||
          lower.includes('error')
        )
          level = 'ERROR';
        else if (lower.includes('warn')) level = 'WARN';
        const normalized = jobFailed
          ? {
              level,
              text: withLogTimestamp(stripFuzzLogPrefix(line) || line.trim()),
            }
          : normalizeFuzzLogLine(line, level);
        if (!normalized) continue;
        appendFuzzLog(normalized.text, normalized.level);
        if (
          !jobFailed &&
          stageStatus.fuzz === 'running' &&
          isCrashDiscoveryLine(line)
        ) {
          fuzzStats.crashes = Math.max(fuzzStats.crashes, 1);
        }
        if (!jobFailed && normalized.stats) {
          applyAflNetStats(normalized.stats);
        } else if (!jobFailed && normalized.level === 'STATS') {
          parseStatsLine(line);
        }
      }
    }
    if (data.job?.status === 'failed') return;
    if (await enterResultVerificationAfterCrash()) return;
    if (
      data.job?.status &&
      !['queued', 'running'].includes(data.job.status) &&
      (!options.runId || isCurrentPipelineRun(options.runId))
    ) {
      finishFuzzFromCurrentOutput();
    }
  } catch (error: any) {
    // Non-fatal: keep polling until user stops
    console.warn('[workbench] fetch fuzz logs error', error?.message || error);
  }
}

async function waitForFuzzConfigJob(
  runId: number,
  options?: { debugReplay?: boolean; instrumentedCodeZipPath?: string },
) {
  if (!assertJobId.value && !options?.debugReplay) {
    throw new Error('缺少断言生成任务 ID');
  }
  appendFuzzLog('启动 Fuzz 配置生成 Agent', 'INFO');
  const protocol = options?.debugReplay
    ? undefined
    : getResolvedStaticAnalysisProtocol();
  const configJob = await startProtocolFuzzConfigJob({
    ...(assertJobId.value ? { assertGenerationJobId: assertJobId.value } : {}),
    ...(options?.instrumentedCodeZipPath
      ? { instrumentedCodeZipPath: options.instrumentedCodeZipPath }
      : {}),
    notes: options?.debugReplay
      ? projectConfig.notes || 'Workbench debug replay'
      : projectConfig.notes,
    ...(protocol ? { protocol } : {}),
  });
  fuzzConfigJobId.value = configJob.jobId;
  fuzzConfigLogReadPosition.value = 0;
  stageMessage.value = 'Fuzz 配置生成 Agent 正在构建并验证运行参数…';

  while (isCurrentPipelineRun(runId)) {
    const data = await fetchProtocolFuzzConfigLogs(
      configJob.jobId,
      fuzzConfigLogReadPosition.value,
    );
    const position =
      typeof data.position === 'number'
        ? data.position
        : fuzzConfigLogReadPosition.value;
    if (position > fuzzConfigLogReadPosition.value) {
      fuzzConfigLogReadPosition.value = position;
    }
    if (data.content) {
      for (const line of data.content.split(/\r?\n/)) {
        if (!line.trim()) continue;
        appendFuzzLog(
          `[fuzz-config] ${stripFuzzLogPrefix(line) || line.trim()}`,
          'INFO',
        );
      }
    }
    if (data.job.status === 'completed') {
      appendFuzzLog(
        `Fuzz 配置生成完成: ${data.job.artifacts?.manifestPath || data.job.jobId}`,
        'INFO',
      );
      return data.job;
    }
    if (data.job.status === 'failed') {
      throw new Error(data.job.error || 'Fuzz 配置生成失败');
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error('流水线已取消');
}

async function runFuzzStep(runId: number) {
  if (!isCurrentPipelineRun(runId)) return;
  const artifactPath = assertResult.value?.artifacts?.instrumentedCodeZipPath;
  if (!assertJobId.value || !artifactPath) {
    markStageError('fuzz', '缺少插桩源码压缩包，无法启动模糊测试');
    return;
  }
  setStage('fuzz', 'running', '使用插桩源码包启动 Fuzz…');
  fuzzLogs.value = [];
  aflNetPocPath.value = '';
  fuzzLogReadPosition.value = 0;
  fuzzConfigLogReadPosition.value = 0;
  fuzzConfigJobId.value = null;
  fuzzJobId.value = null;
  fuzzJob.value = null;
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
  await nextTick();
  if (!isCurrentPipelineRun(runId)) return;
  try {
    appendFuzzLog(`使用插桩源码包: ${artifactPath}`, 'INFO');
    const configJob = await waitForFuzzConfigJob(runId);
    if (!isCurrentPipelineRun(runId)) return;
    stageMessage.value = '使用已验证配置启动 AFLNet…';
    const job = await startProtocolFuzzingJob({
      assertGenerationJobId: assertJobId.value,
      fuzzConfigJobId: configJob.jobId,
      notes: projectConfig.notes,
    });
    if (!isCurrentPipelineRun(runId)) return;
    fuzzJobId.value = job.jobId;
    fuzzJob.value = job;
    updateAflNetPocPath(job.artifacts);
    if (job.status === 'failed') {
      markStageError('fuzz', job.error || '模糊测试启动失败');
      return;
    }
    stageMessage.value = '模糊测试运行中，点击"停止"结束';
    void readFuzzLogs({ runId });
    fuzzPollTimer = setInterval(() => {
      void readFuzzLogs({ runId });
    }, 1000);
  } catch (error: any) {
    if (!isCurrentPipelineRun(runId)) return;
    markStageError('fuzz', error?.message || '模糊测试启动失败');
  }
}

async function startFuzzDebugReplay() {
  if (isRunningFuzzDebugReplay()) return;
  pipelineRunId += 1;
  const runId = pipelineRunId;
  clearTransitionTimer(false);
  clearTimer('static');
  clearTimer('assert');
  clearTimer('fuzz');
  clearTimer('elapsed');
  isAwaitingAssertConfirmation.value = false;
  isStopping.value = false;
  errorMessage.value = null;

  for (const s of STAGE_LIST) stageStatus[s.key] = 'idle';
  markStageSkipped('code_locate');
  markStageSkipped('assert_gen');
  setStage('fuzz', 'running', '复用最近插桩源码包启动 Fuzz…');
  startedAt.value = new Date();
  elapsedSeconds.value = 0;
  startElapsedTimer();

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
  fuzzConfigJobId.value = null;
  fuzzConfigLogReadPosition.value = 0;
  fuzzJobId.value = null;
  fuzzJob.value = null;
  aflNetPocPath.value = '';
  fuzzLogs.value = [];
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

  await nextTick();
  if (!isCurrentPipelineRun(runId)) return;

  try {
    appendFuzzLog('正在复用最近一次断言插入产物启动 Fuzz', 'INFO');
    const configJob = await waitForFuzzConfigJob(runId, { debugReplay: true });
    if (!isCurrentPipelineRun(runId)) return;
    const artifactPath =
      configJob.inputs?.instrumentedCodeZipPath ||
      configJob.artifacts?.instrumentedCodeZipPath ||
      '调试插桩源码包';
    appendFuzzLog(`使用插桩源码包: ${artifactPath}`, 'INFO');
    stageMessage.value = '使用调试配置启动 AFLNet…';
    const job = await startProtocolFuzzingDebugJob({
      assertGenerationJobId: configJob.assertGenerationJobId,
      fuzzConfigJobId: configJob.jobId,
      notes: projectConfig.notes || 'Workbench debug replay',
    });
    if (!isCurrentPipelineRun(runId)) return;
    fuzzJobId.value = job.jobId;
    fuzzJob.value = job;
    updateAflNetPocPath(job.artifacts);
    if (job.status === 'failed') {
      markStageError('fuzz', job.error || '模糊测试启动失败');
      return;
    }
    stageMessage.value = '调试 Fuzz 已启动，点击"停止"结束';
    void readFuzzLogs({ runId });
    fuzzPollTimer = setInterval(() => {
      void readFuzzLogs({ runId });
    }, 1000);
  } catch (error: any) {
    if (!isCurrentPipelineRun(runId)) return;
    clearTimer('elapsed');
    markStageError('fuzz', error?.message || '调试 Fuzz 启动失败');
  }
}

function isRunningFuzzDebugReplay() {
  return (
    stageStatus.code_locate === 'running' ||
    stageStatus.assert_gen === 'running' ||
    stageStatus.fuzz === 'running' ||
    isTransitioning.value ||
    isAwaitingAssertConfirmation.value
  );
}

async function runConfiguredPipeline(runId: number) {
  await runStaticAnalysisStep(runId);
}

async function startPipeline(rule: ProtocolExtractRuleItem) {
  if (!(await ensureProjectReady())) return;
  pipelineRunId += 1;
  const runId = pipelineRunId;
  selectedRule.value = rule;
  resetPipelineStageState();
  startedAt.value = new Date();
  elapsedSeconds.value = 0;
  startElapsedTimer();
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
    isAwaitingAssertConfirmation.value = false;
    if (stage.value === 'fuzz' && fuzzJobId.value) {
      try {
        await stopProtocolFuzzingJob(fuzzJobId.value);
      } catch (error: any) {
        console.warn('[workbench] stop fuzz failed', error?.message || error);
      }
      fuzzJob.value = null;
    }
    if (stageStatus.fuzz === 'running') {
      stageStatus.fuzz = 'done';
      stage.value = 'done';
      activeStageView.value = 'done';
      stageStatus.done = 'done';
      appendResultHistoryRecord('stopped');
    } else {
      const interruptedStage = stage.value;
      if (stageStatus.code_locate === 'running')
        stageStatus.code_locate = 'error';
      if (stageStatus.assert_gen === 'running')
        stageStatus.assert_gen = 'error';
      if (stageStatus.fuzz === 'idle') stageStatus.done = 'idle';
      activeStageView.value = interruptedStage;
      errorMessage.value = '分析流程已停止，后续阶段未生成';
    }
    clearTimer('elapsed');
    stageMessage.value = '分析流程已停止';
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
  isAwaitingAssertConfirmation.value = false;
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
  fuzzConfigJobId.value = null;
  fuzzConfigLogReadPosition.value = 0;
  fuzzJobId.value = null;
  fuzzJob.value = null;
  aflNetPocPath.value = '';
  fuzzLogs.value = [];
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
    isAwaitingAssertConfirmation,
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
    fuzzJob,
    fuzzJobId,
    aflNetPocPath,

    // Methods
    commitSetup,
    confirmAssertGeneration,
    backToSetup,
    startPipeline,
    startFuzzDebugReplay,
    stopPipeline,
    resetWorkbench,
    selectStageView,
    canViewStage,
  };
}
