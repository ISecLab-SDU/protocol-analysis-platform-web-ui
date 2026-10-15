import type {
  CodeLocateEvidence,
  CodeLocateFunctionSlice,
  CodeLocateRow,
} from './types';

import type {
  ProtocolAssertGenerationJob,
  ProtocolAssertGenerationResult,
  ProtocolExtractRuleItem,
  ProtocolFuzzConfigJob,
  ProtocolFuzzingJob,
  ProtocolStaticAnalysisDatabaseRuleInsight,
  ProtocolStaticAnalysisJob,
  ProtocolStaticAnalysisProgressEvent,
  ProtocolStaticAnalysisResult,
} from '#/api/protocol-compliance';

import { computed, reactive, ref } from 'vue';

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
  startProtocolFuzzingJob,
  stopProtocolFuzzingJob,
} from '#/api/protocol-compliance';

import { buildLegacyRulesPayload } from './ruleFormat';
import { ansiToHtml, normalizeList } from './utils';

type ModuleStatus = 'done' | 'error' | 'idle' | 'running' | 'stopped';
type FuzzLogLevel = 'ERROR' | 'INFO' | 'STATS' | 'WARN';

interface FuzzLogEntry {
  id: number;
  level: FuzzLogLevel;
  text: string;
}

const codeLocateInputs = reactive({
  codeArchive: null as File | null,
  rulesFile: null as File | null,
});

const codeLocate = reactive({
  error: '',
  evidence: null as CodeLocateEvidence | null,
  events: [] as ProtocolStaticAnalysisProgressEvent[],
  inputArchive: null as File | null,
  job: null as null | ProtocolStaticAnalysisJob,
  logHtml: '',
  logText: '',
  result: null as null | ProtocolStaticAnalysisResult,
  rule: null as null | ProtocolExtractRuleItem,
  status: 'idle' as ModuleStatus,
});

const assertInputs = reactive({
  agent: 'pi' as const,
  api: 'openai-completions' as
    | 'anthropic-messages'
    | 'openai-completions'
    | 'openai-responses',
  apiKey: '',
  baseUrl: '',
  model: '',

  codeArchive: null as File | null,
  databaseFile: null as File | null,
  databasePath: '',
});

const assertGeneration = reactive({
  diffContent: '',
  error: '',
  job: null as null | ProtocolAssertGenerationJob,
  logText: '',
  result: null as null | ProtocolAssertGenerationResult,
  status: 'idle' as ModuleStatus,
});

const latestAssertGenerationJobId = ref('');

interface AssertionOutputContext {
  assertResult: ProtocolAssertGenerationResult;
  codeLocateResult: null | ProtocolStaticAnalysisResult;
  diffContent: string;
  evidence: CodeLocateEvidence | null;
  rule: null | ProtocolExtractRuleItem;
}

const assertionOutputContexts = reactive(
  new Map<string, AssertionOutputContext>(),
);

const fuzzInput = reactive({
  assertGenerationJobId: '',
});

const fuzzStats = reactive({
  coverage: 0,
  crashes: 0,
  currentPath: 0,
  cycles: 0,
  edges: 0,
  executions: 0,
  hangs: 0,
  maxDepth: 0,
  nodes: 0,
  paths: 0,
  pathsTotal: 0,
  pendingFavs: 0,
  pendingTotal: 0,
  speed: 0,
});

const fuzz = reactive({
  assertGenerationJobId: '',
  configJob: null as null | ProtocolFuzzConfigJob,
  elapsedSeconds: 0,
  error: '',
  job: null as null | ProtocolFuzzingJob,
  logs: [] as FuzzLogEntry[],
  pocPath: '',
  speedSeries: [] as number[],
  startedAt: null as Date | null,
  status: 'idle' as
    | 'completed'
    | 'configuring'
    | 'crash-found'
    | 'failed'
    | 'idle'
    | 'running'
    | 'stopped'
    | 'stopping',
});

const isFuzzRunning = computed(
  () =>
    fuzz.status === 'configuring' ||
    fuzz.status === 'running' ||
    fuzz.status === 'stopping',
);

let codeLocateRunId = 0;
let assertionRunId = 0;
let fuzzRunId = 0;
let fuzzStartPendingRunId: null | number = null;
let fuzzStopRequestedRunId: null | number = null;
let fuzzLogId = 0;

function isStoppedPendingFuzzStart(runId: number) {
  return fuzz.status === 'stopping' && fuzzRunId === runId + 1;
}
let fuzzLogPosition = 0;
let fuzzConfigLogPosition = 0;
let fuzzLogRequestFinished: null | Promise<void> = null;
let fuzzElapsedTimer: null | ReturnType<typeof setInterval> = null;

function delay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

function getErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) return error.message;
  if (typeof error === 'string' && error) return error;
  return fallback;
}

function buildSelectedRuleFile(rule: ProtocolExtractRuleItem) {
  const payload = buildLegacyRulesPayload([rule]);
  return new File([JSON.stringify(payload, null, 2)], 'rules.json', {
    type: 'application/json',
  });
}

function relatedVariableCount(rule: null | ProtocolExtractRuleItem) {
  if (!rule) return 0;
  return new Set([
    ...normalizeList(rule.req_fields),
    ...normalizeList(rule.res_fields),
  ]).size;
}

function shortPath(path: string) {
  const normalized = path.trim().replaceAll('\\', '/');
  return normalized.split('/').findLast(Boolean) || normalized;
}

function formatLineRange(lines: number[]) {
  const unique = [...new Set(lines)].sort((left, right) => left - right);
  const first = unique[0];
  const last = unique.at(-1);
  if (first === undefined || last === undefined) return '-';
  return first === last ? String(first) : `${first}-${last}`;
}

function parseCodeLocateEvidence(
  insight: ProtocolStaticAnalysisDatabaseRuleInsight,
  findings: ProtocolStaticAnalysisDatabaseRuleInsight[],
  rule: null | ProtocolExtractRuleItem,
  source = '代码定位与一致性分析',
): CodeLocateEvidence {
  const functions = new Map<string, CodeLocateFunctionSlice>();
  const rows: CodeLocateRow[] = [];
  const pathLines: number[] = [];
  const violations = insight.violations || [];
  const violationLines = new Set(
    violations.flatMap((violation) => violation.codeLines || []),
  );
  const firstViolationPath =
    violations.find((violation) => violation.filename)?.filename || '';
  let targetFile = firstViolationPath;
  let currentFunction: CodeLocateFunctionSlice | null = null;

  const ensureFunction = (name: string) => {
    const normalized = name.trim();
    const existing = functions.get(normalized);
    if (existing) return existing;
    const next: CodeLocateFunctionSlice = { codeRows: [], name: normalized };
    functions.set(normalized, next);
    return next;
  };

  for (const rawLine of (insight.codeSnippet || '').split(/\r?\n/)) {
    const line = rawLine
      .replace(/^\([^)]+\)\s*/, '')
      .replace(/^.*:\s+(?=(Function:|Path:|func:|\d+\s+))/i, '');
    const lowerLine = line.toLowerCase();
    if (lowerLine.startsWith('func:')) {
      const name = line.slice(line.indexOf(':') + 1).trim();
      if (name) ensureFunction(name);
      currentFunction = null;
      continue;
    }
    if (lowerLine.startsWith('function:')) {
      const name = line.slice(line.indexOf(':') + 1).trim();
      currentFunction = name ? ensureFunction(name) : null;
      continue;
    }
    if (lowerLine.startsWith('path:')) {
      const pathValue = line.slice(line.indexOf(':') + 1).trim();
      const separator = pathValue.lastIndexOf(':');
      if (separator !== -1) {
        const filePath = pathValue.slice(0, separator).trim();
        const lineNumber = Number(pathValue.slice(separator + 1).trim());
        if (filePath) {
          targetFile ||= filePath;
          if (Number.isFinite(lineNumber)) pathLines.push(lineNumber);
          if (currentFunction) {
            currentFunction.path = filePath;
            currentFunction.targetLine = lineNumber;
          }
        }
      }
      continue;
    }

    const trimmedLine = line.trimStart();
    let digitEnd = 0;
    while (
      digitEnd < trimmedLine.length &&
      /\d/.test(trimmedLine.charAt(digitEnd))
    ) {
      digitEnd += 1;
    }
    if (digitEnd === 0 || digitEnd > 7) continue;
    const separator = trimmedLine[digitEnd];
    if (separator !== undefined && !/\s/.test(separator)) continue;
    const lineNumber = Number(trimmedLine.slice(0, digitEnd));
    const row: CodeLocateRow = {
      emphasis: violationLines.has(lineNumber),
      line: lineNumber,
      text: trimmedLine.slice(digitEnd).trimStart(),
    };
    rows.push(row);
    currentFunction?.codeRows.push(row);
  }

  const highlight = (sourceRows: CodeLocateRow[], preferredLines: number[]) => {
    if (sourceRows.length === 0 || sourceRows.some((row) => row.emphasis))
      return;
    const preferred = preferredLines.find((line) =>
      sourceRows.some((row) => Number(row.line) === line),
    );
    const targetLine = preferred ?? Number(sourceRows[0]?.line);
    const targetRow =
      sourceRows.find((row) => Number(row.line) === targetLine) ||
      sourceRows[0];
    if (targetRow) targetRow.emphasis = true;
  };

  highlight(rows, pathLines);
  const functionSlices = [...functions.values()];
  for (const fn of functionSlices) {
    const targetLine = Number(fn.targetLine);
    highlight(fn.codeRows, Number.isFinite(targetLine) ? [targetLine] : []);
  }
  const actionableFindingCount = findings.filter(
    (finding) => finding.result !== 'no_violation',
  ).length;
  let keySliceCount = 0;
  if (actionableFindingCount > 0) keySliceCount = actionableFindingCount;
  else if (violations.length > 0) keySliceCount = violations.length;
  else if (insight.result !== 'no_violation') keySliceCount = 1;
  let targetLines: number[];
  if (violationLines.size > 0) targetLines = [...violationLines];
  else if (pathLines.length > 0) targetLines = pathLines;
  else targetLines = rows.map((row) => Number(row.line));
  let candidateFunctionCount = functions.size;
  if (candidateFunctionCount === 0) candidateFunctionCount = 1;

  return {
    candidateFunctionCount,
    codeRows: rows,
    functions: functionSlices,
    keySliceCount,
    relatedVariableCount: relatedVariableCount(rule),
    resultLabel: insight.resultLabel,
    ruleText: insight.ruleDesc || rule?.rule || rule?.description,
    source,
    targetFile: shortPath(targetFile) || '待定位',
    targetLine: formatLineRange(targetLines),
    updatedAt: new Date().toISOString(),
    violationReason: insight.reason || undefined,
  };
}

async function loadCodeLocateEvidence(
  jobId: string,
  rule: ProtocolExtractRuleItem,
) {
  const result = codeLocate.result;
  const insights = await fetchProtocolStaticAnalysisDatabaseInsights({
    databasePath: result?.artifacts?.database || undefined,
    jobId,
    workspacePath: result?.artifacts?.workspace || undefined,
  });
  const findings = insights.findings || [];
  const selectedRuleText = (rule.rule || rule.description || '').trim();
  const insight =
    findings.find((finding) => {
      const description = finding.ruleDesc?.trim() || '';
      return (
        description.includes(selectedRuleText) ||
        selectedRuleText.includes(description)
      );
    }) ||
    findings.find((finding) => finding.result === 'violation_found') ||
    findings.find((finding) => finding.result === 'unknown') ||
    findings[0];
  if (insight)
    codeLocate.evidence = parseCodeLocateEvidence(insight, findings, rule);
}

async function loadAssertionOutputContext(jobId: string) {
  const normalizedJobId = jobId.trim();
  if (!normalizedJobId) return null;
  const existing = assertionOutputContexts.get(normalizedJobId);
  if (existing) return existing;

  const assertResult =
    await fetchProtocolAssertGenerationResult(normalizedJobId);
  if (typeof assertResult?.jobId !== 'string') {
    throw new TypeError('未找到断言生成结果');
  }
  let diffContent = '';
  try {
    const diff = await fetchProtocolInstrumentationDiff(normalizedJobId);
    diffContent = diff?.content || '';
  } catch {
    diffContent = '';
  }

  const context: AssertionOutputContext = {
    assertResult,
    codeLocateResult: null,
    diffContent,
    evidence: null,
    rule: null,
  };
  const latestContext = assertionOutputContexts.get(normalizedJobId);
  if (latestContext) return latestContext;
  assertionOutputContexts.set(normalizedJobId, context);
  return context;
}

function appendStaticEvents(
  events: ProtocolStaticAnalysisProgressEvent[],
  lastEventId: { value: number },
) {
  for (const event of events) {
    const eventId = event.id;
    if (typeof eventId === 'number' && eventId <= lastEventId.value) continue;
    codeLocate.events.push(event);
    const timestamp = event.timestamp
      ? new Date(event.timestamp).toLocaleTimeString()
      : '';
    const stage = event.stage ? `(${event.stage}) ` : '';
    codeLocate.logText += `${stage}${timestamp ? `[${timestamp}] ` : ''}${event.message}\n`;
    if (typeof eventId === 'number') lastEventId.value = eventId;
  }
  if (codeLocate.logText.trim()) {
    const insight: ProtocolStaticAnalysisDatabaseRuleInsight = {
      codeSnippet: codeLocate.logText,
      result: 'unknown',
      resultLabel: '实时进度',
      ruleDesc:
        codeLocate.rule?.rule || codeLocate.rule?.description || '实时代码证据',
    };
    const evidence = parseCodeLocateEvidence(
      insight,
      [],
      codeLocate.rule,
      '实时控制台',
    );
    if (
      evidence.codeRows.length > 0 ||
      (evidence.functions?.length ?? 0) > 0 ||
      evidence.targetFile !== '待定位'
    ) {
      codeLocate.evidence = evidence;
    }
  }
  codeLocate.logHtml = ansiToHtml(codeLocate.logText);
}

async function completeCodeLocateJob(
  jobId: string,
  runId: number,
  snapshot?: ProtocolStaticAnalysisJob,
) {
  if (runId !== codeLocateRunId) return;
  const result =
    snapshot?.result || (await fetchProtocolStaticAnalysisResult(jobId));
  if (runId !== codeLocateRunId) return;
  codeLocate.result = result;
  codeLocate.job = snapshot || codeLocate.job;
  if (codeLocate.rule) {
    try {
      await loadCodeLocateEvidence(jobId, codeLocate.rule);
    } catch (error) {
      console.warn(
        '[analysis-modules] code locate evidence unavailable',
        error,
      );
    }
  }
  if (runId !== codeLocateRunId) return;
  codeLocate.status = 'done';
  const databasePath = result.artifacts?.database;
  if (
    databasePath &&
    !assertInputs.databasePath &&
    !assertInputs.databaseFile
  ) {
    assertInputs.databasePath = databasePath;
  }
}

async function pollCodeLocateJob(
  jobId: string,
  runId: number,
  lastEventId: { value: number },
) {
  while (true) {
    if (runId !== codeLocateRunId) return;
    await delay(1500);
    if (runId !== codeLocateRunId) return;
    const snapshot = await fetchProtocolStaticAnalysisProgress(
      jobId,
      lastEventId.value || undefined,
    );
    if (runId !== codeLocateRunId) return;
    codeLocate.job = snapshot;
    appendStaticEvents(snapshot.events || [], lastEventId);
    if (snapshot.status === 'completed') {
      await completeCodeLocateJob(jobId, runId, snapshot);
      return;
    }
    if (snapshot.status === 'failed') {
      codeLocate.status = 'error';
      codeLocate.error = snapshot.error || '代码定位与一致性分析失败';
      return;
    }
  }
}

async function runCodeLocate(rule: ProtocolExtractRuleItem) {
  if (!codeLocateInputs.codeArchive || !codeLocateInputs.rulesFile) {
    codeLocate.status = 'error';
    codeLocate.error = '请先上传源码压缩包和协议规则 JSON';
    return;
  }

  codeLocateRunId += 1;
  const runId = codeLocateRunId;
  codeLocate.status = 'running';
  codeLocate.error = '';
  codeLocate.events = [];
  codeLocate.logText = '';
  codeLocate.logHtml = '';
  codeLocate.result = null;
  codeLocate.evidence = null;
  codeLocate.rule = rule;
  codeLocate.inputArchive = codeLocateInputs.codeArchive;
  codeLocate.job = null;

  try {
    const job = await runProtocolStaticAnalysis({
      codeArchive: codeLocateInputs.codeArchive,
      rules: buildSelectedRuleFile(rule),
    });
    if (runId !== codeLocateRunId) return;
    codeLocate.job = job;
    const lastEventId = { value: 0 };
    appendStaticEvents(job.events || [], lastEventId);
    if (job.status === 'completed') {
      await completeCodeLocateJob(job.jobId, runId, job);
    } else if (job.status === 'failed') {
      codeLocate.status = 'error';
      codeLocate.error = job.error || '代码定位与一致性分析失败';
    } else {
      await pollCodeLocateJob(job.jobId, runId, lastEventId);
    }
  } catch (error) {
    if (runId !== codeLocateRunId) return;
    codeLocate.status = 'error';
    codeLocate.error = getErrorMessage(error, '代码定位与一致性分析启动失败');
  }
}

function stopCodeLocate() {
  if (codeLocate.status !== 'running') return;
  codeLocateRunId += 1;
  codeLocate.status = 'stopped';
  codeLocate.error = '已停止此模块的进度查询；已提交的服务端任务可能继续运行';
}

function resetCodeLocateOutput() {
  codeLocateRunId += 1;
  const previousDatabasePath = codeLocate.result?.artifacts?.database;
  codeLocate.error = '';
  codeLocate.events = [];
  codeLocate.job = null;
  codeLocate.inputArchive = null;
  codeLocate.logHtml = '';
  codeLocate.logText = '';
  codeLocate.result = null;
  codeLocate.evidence = null;
  codeLocate.rule = null;
  codeLocate.status = 'idle';
  if (previousDatabasePath === assertInputs.databasePath) {
    assertInputs.databasePath = '';
  }
}

function applyAssertEvents(job: ProtocolAssertGenerationJob) {
  assertGeneration.job = job;
  assertGeneration.logText = (job.events || [])
    .map((event) => {
      const timestamp = event.timestamp
        ? new Date(event.timestamp).toLocaleTimeString()
        : '';
      const stage = event.stage ? `(${event.stage}) ` : '';
      return `${timestamp ? `[${timestamp}] ` : ''}${stage}${event.message}`;
    })
    .join('\n');
}

async function completeAssertGeneration(
  jobId: string,
  runId: number,
  context: Omit<AssertionOutputContext, 'assertResult' | 'diffContent'>,
) {
  if (runId !== assertionRunId) return;
  const result = await fetchProtocolAssertGenerationResult(jobId);
  if (runId !== assertionRunId) return;
  assertGeneration.result = result;
  let diffContent = '';
  try {
    const diff = await fetchProtocolInstrumentationDiff(jobId);
    if (runId !== assertionRunId) return;
    diffContent = diff?.content || '';
  } catch {
    if (runId !== assertionRunId) return;
    diffContent = '';
  }
  if (runId !== assertionRunId) return;
  assertGeneration.diffContent = diffContent;
  assertionOutputContexts.set(jobId, {
    ...context,
    assertResult: result,
    diffContent,
  });
  latestAssertGenerationJobId.value = jobId;
  fuzzInput.assertGenerationJobId = jobId;
  assertGeneration.status = 'done';
}

async function pollAssertGeneration(
  jobId: string,
  runId: number,
  context: Omit<AssertionOutputContext, 'assertResult' | 'diffContent'>,
) {
  while (true) {
    if (runId !== assertionRunId) return;
    await delay(1500);
    if (runId !== assertionRunId) return;
    const snapshot = await fetchProtocolAssertGenerationProgress(jobId);
    if (runId !== assertionRunId) return;
    applyAssertEvents(snapshot);
    if (snapshot.status === 'completed') {
      await completeAssertGeneration(jobId, runId, context);
      return;
    }
    if (snapshot.status === 'failed') {
      assertGeneration.status = 'error';
      assertGeneration.error = snapshot.error || '断言生成失败';
      return;
    }
  }
}

async function runAssertGeneration() {
  const archive = assertInputs.codeArchive;
  const databasePath = assertInputs.databasePath.trim();
  const databaseFile = assertInputs.databaseFile;
  if (!archive) {
    assertGeneration.status = 'error';
    assertGeneration.error = '请上传源码压缩包';
    return;
  }
  if (!databasePath && !databaseFile) {
    assertGeneration.status = 'error';
    assertGeneration.error =
      '请选择代码定位结果数据库，或上传之前生成的数据库文件';
    return;
  }

  const codeLocateResult = codeLocate.result;
  const matchedCodeLocateOutput = Boolean(
    !databaseFile &&
      databasePath &&
      databasePath === codeLocateResult?.artifacts?.database &&
      archive === codeLocate.inputArchive,
  );
  const outputContext = {
    codeLocateResult: matchedCodeLocateOutput ? codeLocateResult : null,
    evidence: matchedCodeLocateOutput ? codeLocate.evidence : null,
    rule: matchedCodeLocateOutput ? codeLocate.rule : null,
  };

  assertionRunId += 1;
  const runId = assertionRunId;
  assertGeneration.status = 'running';
  assertGeneration.error = '';
  assertGeneration.job = null;
  assertGeneration.result = null;
  assertGeneration.diffContent = '';
  assertGeneration.logText = '';

  try {
    const payload: {
      codeArchive: File;
      database?: File;
      databasePath?: string;
      runtime: import('#/api/protocol-compliance').AssertionRuntimeSettings;
    } = {
      runtime: {
        agent: assertInputs.agent,
        api: assertInputs.api,
        model: assertInputs.model.trim(),
        baseUrl: assertInputs.baseUrl.trim(),
        apiKey: assertInputs.apiKey.trim(),
      },
      codeArchive: archive,
    };
    if (databasePath) payload.databasePath = databasePath;
    else if (databaseFile) payload.database = databaseFile;
    const job = await runProtocolAssertGeneration(payload);
    if (runId !== assertionRunId) return;
    applyAssertEvents(job);
    if (job.status === 'completed') {
      await completeAssertGeneration(job.jobId, runId, outputContext);
    } else if (job.status === 'failed') {
      assertGeneration.status = 'error';
      assertGeneration.error = job.error || '断言生成失败';
    } else {
      await pollAssertGeneration(job.jobId, runId, outputContext);
    }
  } catch (error) {
    if (runId !== assertionRunId) return;
    assertGeneration.status = 'error';
    assertGeneration.error = getErrorMessage(error, '断言生成启动失败');
  }
}

function stopAssertGeneration() {
  if (assertGeneration.status !== 'running') return;
  assertionRunId += 1;
  assertGeneration.status = 'stopped';
  assertGeneration.error =
    '已停止此模块的进度查询；已提交的服务端任务可能继续运行';
}

function useLatestCodeLocateOutput() {
  const databasePath = codeLocate.result?.artifacts?.database;
  if (!databasePath || !codeLocate.inputArchive) return false;
  assertInputs.codeArchive = codeLocate.inputArchive;
  assertInputs.databaseFile = null;
  assertInputs.databasePath = databasePath;
  return true;
}

function resetFuzzStats() {
  Object.assign(fuzzStats, {
    coverage: 0,
    crashes: 0,
    currentPath: 0,
    cycles: 0,
    edges: 0,
    executions: 0,
    hangs: 0,
    maxDepth: 0,
    nodes: 0,
    paths: 0,
    pathsTotal: 0,
    pendingFavs: 0,
    pendingTotal: 0,
    speed: 0,
  });
  fuzz.speedSeries = [];
}

function parseFuzzStatsLine(line: string) {
  const source = line
    .trim()
    .replace(/^\[plot_data\]\s*/i, '')
    .replace(/^\[\d{2}:\d{2}:\d{2}\]\s*/, '')
    .replace(/^(?:INFO|STATS|WARN|ERROR)[:\s]+/i, '')
    .replace(/^#\s*/, '');
  const values = source.split(',').map((value) => value.trim());
  if (
    values.length < 10 ||
    !values.every((value) => /^-?\d+(?:\.\d+)?%?$/.test(value))
  ) {
    return false;
  }

  const hasPendingFavsColumn = values.length >= 11;
  const hasExtendedTopologyColumns = values.length >= 13;
  const index = 1;
  const numberAt = (position: number) =>
    Number(values[position]?.replace(/%$/, ''));
  const currentPath = numberAt(2);
  const pathsTotal = numberAt(3);
  const pendingTotal = numberAt(4);
  const pendingFavs = hasPendingFavsColumn ? numberAt(5) : 0;
  const coverage = numberAt(hasPendingFavsColumn ? 6 : 5);
  const crashes = numberAt(hasPendingFavsColumn ? 7 : 6);
  const hangs = numberAt(hasPendingFavsColumn ? 8 : 7);
  const maxDepth = numberAt(hasPendingFavsColumn ? 9 : 8);
  const speed = numberAt(hasPendingFavsColumn ? 10 : 9);
  const nodes = numberAt(hasExtendedTopologyColumns ? 11 : 2);
  const edges = numberAt(hasExtendedTopologyColumns ? 12 : 3);
  const cycles = numberAt(index);
  if (
    ![
      currentPath,
      pathsTotal,
      pendingTotal,
      pendingFavs,
      coverage,
      crashes,
      hangs,
      maxDepth,
      speed,
      nodes,
      edges,
      cycles,
    ].every((value) => Number.isFinite(value))
  ) {
    return false;
  }

  Object.assign(fuzzStats, {
    coverage,
    crashes,
    currentPath,
    cycles,
    edges,
    hangs,
    maxDepth,
    nodes,
    paths: pathsTotal,
    pathsTotal,
    pendingFavs,
    pendingTotal,
    speed,
  });
  fuzz.speedSeries.push(speed);
  if (fuzz.speedSeries.length > 60) fuzz.speedSeries.shift();
  return true;
}

function appendFuzzLogEntry(level: FuzzLogLevel, text: string) {
  fuzz.logs.push({ id: ++fuzzLogId, level, text });
  if (fuzz.logs.length > 500) {
    fuzz.logs.splice(0, fuzz.logs.length - 500);
  }
}

function appendFuzzLog(line: string, fallbackLevel: FuzzLogLevel = 'INFO') {
  const trimmed = line.trim();
  if (!trimmed) return;
  const prefix = trimmed.match(/^(ERROR|INFO|STATS|WARN)\b/i)?.[1];
  const level = (prefix?.toUpperCase() as FuzzLogLevel) || fallbackLevel;
  const text = prefix
    ? trimmed.slice(prefix.length).replace(/^[\s:]+/, '') || trimmed
    : trimmed;
  if (parseFuzzStatsLine(text)) {
    appendFuzzLogEntry('STATS', text);
    return;
  }

  const crashMatch = text.match(/(?:unique_)?crash\D*(\d+)/i);
  if (crashMatch?.[1])
    fuzzStats.crashes = Math.max(fuzzStats.crashes, Number(crashMatch[1]));
  const hangMatch = text.match(/(?:unique_)?hang\D*(\d+)/i);
  if (hangMatch?.[1])
    fuzzStats.hangs = Math.max(fuzzStats.hangs, Number(hangMatch[1]));
  if (isCrashDiscoveryLine(text)) {
    fuzzStats.crashes = Math.max(fuzzStats.crashes, 1);
    appendFuzzLogEntry('ERROR', text);
    return;
  }
  const speedMatch = text.match(/speed\D*(\d+(?:\.\d+)?)/i);
  if (speedMatch?.[1]) fuzzStats.speed = Number(speedMatch[1]);
  const pathMatch = text.match(/path\D*(\d+)\s*\/\s*(\d+)/i);
  if (pathMatch?.[1] && pathMatch?.[2]) {
    fuzzStats.currentPath = Number(pathMatch[1]);
    fuzzStats.paths = Number(pathMatch[2]);
    fuzzStats.pathsTotal = Number(pathMatch[2]);
  }

  const pendingMatch = text.match(
    /pending\D*(\d+)(?:\s*\(\s*(\d+)\s*favs?\s*\))?/i,
  );
  if (pendingMatch?.[1]) fuzzStats.pendingTotal = Number(pendingMatch[1]);
  if (pendingMatch?.[2]) fuzzStats.pendingFavs = Number(pendingMatch[2]);
  const coverageMatch = text.match(/(?:coverage|map_size)\D*(\d+(?:\.\d+)?)/i);
  if (coverageMatch?.[1]) fuzzStats.coverage = Number(coverageMatch[1]);
  const maxDepthMatch = text.match(/(?:max_depth|max\s*depth|depth)\D*(\d+)/i);
  if (maxDepthMatch?.[1]) {
    fuzzStats.maxDepth = Math.max(fuzzStats.maxDepth, Number(maxDepthMatch[1]));
  }
  const nodesMatch = text.match(/node\D*(\d+)/i);
  if (nodesMatch?.[1]) fuzzStats.nodes = Number(nodesMatch[1]);
  const edgesMatch = text.match(/edge\D*(\d+)/i);
  if (edgesMatch?.[1]) fuzzStats.edges = Number(edgesMatch[1]);
  const executionsMatch = text.match(/exec\D*(\d+(?:\.\d+)?)/i);
  if (executionsMatch?.[1]) {
    fuzzStats.executions = Math.max(
      fuzzStats.executions,
      Math.floor(Number(executionsMatch[1])),
    );
  }
  appendFuzzLogEntry(level, text);
}

function isFuzzerStartupErrorLine(line: string) {
  return /PROGRAM ABORT|PG_FUZZ_INSTRUMENTED_CODE_DIR|cannot infer how to build or launch|Seed corpus directory|Target binary not found|AFLNet startup failed/i.test(
    line,
  );
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

function appendFuzzLogContent(content: string) {
  for (const line of content.split(/\r?\n/)) appendFuzzLog(line);
}

function updateFuzzElapsed() {
  if (!fuzz.startedAt) return;
  fuzz.elapsedSeconds = Math.floor(
    (Date.now() - fuzz.startedAt.getTime()) / 1000,
  );
}

function clearFuzzElapsedTimer() {
  if (fuzzElapsedTimer) {
    clearInterval(fuzzElapsedTimer);
    fuzzElapsedTimer = null;
  }
}

async function waitForFuzzConfig(jobId: string, runId: number) {
  fuzzConfigLogPosition = 0;
  while (true) {
    if (runId !== fuzzRunId) return null;
    const data = await fetchProtocolFuzzConfigLogs(
      jobId,
      fuzzConfigLogPosition,
    );
    if (runId !== fuzzRunId) return null;
    fuzz.configJob = data.job;
    if (typeof data.position === 'number')
      fuzzConfigLogPosition = data.position;
    if (data.content) appendFuzzLogContent(data.content);
    if (data.job.status === 'completed') return data.job;
    if (data.job.status === 'failed') {
      throw new Error(data.job.error || 'Fuzz 配置生成失败');
    }
    await delay(1000);
  }
}

async function pollFuzzJob(jobId: string, runId: number, resetPosition = true) {
  if (resetPosition) fuzzLogPosition = 0;
  while (true) {
    if (runId !== fuzzRunId) return;
    let data: Awaited<ReturnType<typeof fetchProtocolFuzzingLogs>>;
    let releaseRequest!: () => void;
    const requestFinished = new Promise<void>((resolve) => {
      releaseRequest = resolve;
    });
    fuzzLogRequestFinished = requestFinished;
    try {
      try {
        data = await fetchProtocolFuzzingLogs(jobId, fuzzLogPosition);
      } catch (error) {
        if (runId !== fuzzRunId) return;
        console.warn(
          '[analysis-modules] fetch fuzz logs error',
          getErrorMessage(error, 'Fuzz 日志读取失败'),
        );
        await delay(1000);
        continue;
      }
    } finally {
      if (fuzzLogRequestFinished === requestFinished) {
        fuzzLogRequestFinished = null;
      }
      releaseRequest();
    }
    const isFinalStopPoll =
      runId !== fuzzRunId &&
      (fuzz.status === 'stopping' || fuzz.status === 'stopped') &&
      data.job.jobId === fuzz.job?.jobId;
    if (runId !== fuzzRunId && !isFinalStopPoll) return;
    if (!isFinalStopPoll) fuzz.job = data.job;
    if (typeof data.position === 'number') fuzzLogPosition = data.position;
    updateFuzzPocPath(data);
    if (data.content) appendFuzzLogContent(data.content);

    if (isFinalStopPoll) return;
    if (data.job.status === 'failed') {
      fuzz.status = 'failed';
      fuzz.error = data.job.error || '模糊测试失败';
      clearFuzzElapsedTimer();
      return;
    }
    if (
      runId === fuzzRunId &&
      fuzz.status === 'running' &&
      fuzzStats.crashes > 0
    ) {
      await stopFuzzingAfterCrash(runId);
      return;
    }
    if (data.job.status === 'stopped') {
      fuzz.status = 'stopped';
      clearFuzzElapsedTimer();
      return;
    }
    if (data.job.status !== 'queued' && data.job.status !== 'running') {
      fuzz.status = 'completed';
      clearFuzzElapsedTimer();
      return;
    }
    await delay(1000);
  }
}

async function stopFuzzingAfterCrash(runId: number) {
  if (
    runId !== fuzzRunId ||
    fuzz.status !== 'running' ||
    fuzzStats.crashes <= 0
  ) {
    return;
  }

  const jobId = fuzz.job?.jobId;
  if (!jobId) return;
  fuzzRunId += 1;
  const stoppedRunId = fuzzRunId;
  fuzz.status = 'crash-found';
  clearFuzzElapsedTimer();
  appendFuzzLog('检测到崩溃，正在停止 Fuzzer 并汇总运行产物', 'ERROR');

  const isCurrentCrashResult = () =>
    fuzzRunId === stoppedRunId &&
    fuzz.status === 'crash-found' &&
    fuzz.job?.jobId === jobId;

  try {
    const stoppedJob = await stopProtocolFuzzingJob(jobId);
    if (!isCurrentCrashResult()) return;
    fuzz.job = stoppedJob;
    const data = await fetchProtocolFuzzingLogs(jobId, fuzzLogPosition);
    if (!isCurrentCrashResult()) return;
    fuzz.job = data.job;
    if (typeof data.position === 'number') fuzzLogPosition = data.position;
    updateFuzzPocPath(data);
    if (data.content) appendFuzzLogContent(data.content);
  } catch (error) {
    if (!isCurrentCrashResult()) return;
    appendFuzzLog(
      `停止 Fuzzer 或读取最终日志失败: ${getErrorMessage(error, '未知错误')}`,
      'WARN',
    );
  }
}

async function runFuzzing() {
  if (isFuzzRunning.value) return;
  const assertGenerationJobId = fuzzInput.assertGenerationJobId.trim();
  if (!assertGenerationJobId) {
    fuzz.status = 'failed';
    fuzz.error = '请填写断言生成模块产出的任务 ID';
    return;
  }

  fuzzRunId += 1;
  const runId = fuzzRunId;
  fuzz.assertGenerationJobId = assertGenerationJobId;
  fuzzStartPendingRunId = null;
  fuzzStopRequestedRunId = null;
  clearFuzzElapsedTimer();
  fuzz.status = 'configuring';
  fuzz.error = '';
  fuzz.logs = [];
  fuzz.job = null;
  fuzz.configJob = null;
  fuzz.pocPath = '';
  fuzz.startedAt = new Date();
  fuzz.elapsedSeconds = 0;
  fuzzLogId = 0;
  resetFuzzStats();
  fuzzElapsedTimer = setInterval(updateFuzzElapsed, 1000);

  try {
    appendFuzzLog(`使用断言生成任务: ${assertGenerationJobId}`);
    void loadAssertionOutputContext(assertGenerationJobId).catch((error) => {
      if (runId !== fuzzRunId) return;
      appendFuzzLog(
        `未能恢复断言历史结果: ${getErrorMessage(error, '未知错误')}`,
        'WARN',
      );
    });
    const configJob = await startProtocolFuzzConfigJob({
      assertGenerationJobId,
    });
    if (runId !== fuzzRunId) return;
    fuzz.configJob = configJob;
    const completedConfigJob =
      configJob.status === 'completed'
        ? configJob
        : await waitForFuzzConfig(configJob.jobId, runId);
    if (!completedConfigJob || runId !== fuzzRunId) return;
    if (completedConfigJob.status === 'failed') {
      throw new Error(completedConfigJob.error || 'Fuzz 配置生成失败');
    }

    fuzzStartPendingRunId = runId;
    let job: ProtocolFuzzingJob;
    try {
      job = await startProtocolFuzzingJob({
        assertGenerationJobId,
        fuzzConfigJobId: completedConfigJob.jobId,
      });
    } finally {
      if (fuzzStartPendingRunId === runId) fuzzStartPendingRunId = null;
    }
    if (runId !== fuzzRunId) {
      if (fuzzStopRequestedRunId === runId) {
        await stopLateStartedFuzzJob(job, runId);
      }
      return;
    }
    fuzz.job = job;
    updateFuzzPocPath(job);
    fuzz.status = 'running';
    if (job.status === 'failed') {
      fuzz.status = 'failed';
      fuzz.error = job.error || '模糊测试启动失败';
      clearFuzzElapsedTimer();
      return;
    }
    await pollFuzzJob(job.jobId, runId);
  } catch (error) {
    if (runId !== fuzzRunId) {
      if (fuzzStopRequestedRunId === runId) {
        fuzzStopRequestedRunId = null;
        if (isStoppedPendingFuzzStart(runId)) {
          fuzz.status = 'stopped';
          fuzz.error = '未能确认模糊测试任务是否已启动';
          clearFuzzElapsedTimer();
        }
      }
      return;
    }
    fuzz.status = 'failed';
    fuzz.error = getErrorMessage(error, '模糊测试启动失败');
    clearFuzzElapsedTimer();
  }
}

async function stopLateStartedFuzzJob(job: ProtocolFuzzingJob, runId: number) {
  if (fuzzStopRequestedRunId !== runId) return;
  const jobId = job.jobId;
  const stoppedRunId = runId + 1;
  const isCurrentStopRequest = () =>
    fuzzRunId === stoppedRunId && fuzz.status === 'stopping';
  if (!isCurrentStopRequest()) return;
  fuzz.job = job;
  updateFuzzPocPath(job);
  try {
    const stoppedJob = await stopProtocolFuzzingJob(jobId);
    if (!isCurrentStopRequest()) return;
    fuzz.job = stoppedJob;
    try {
      const data = await fetchProtocolFuzzingLogs(jobId, fuzzLogPosition);
      if (!isCurrentStopRequest()) return;
      fuzz.job = data.job;
      if (typeof data.position === 'number') fuzzLogPosition = data.position;
      updateFuzzPocPath(data);
      if (data.content) appendFuzzLogContent(data.content);
    } catch (error) {
      if (!isCurrentStopRequest()) return;
      appendFuzzLog(
        `停止后读取最终日志失败: ${getErrorMessage(error, '未知错误')}`,
        'WARN',
      );
    }
    if (!isCurrentStopRequest()) return;
    fuzz.status = 'stopped';
    clearFuzzElapsedTimer();
  } catch (error) {
    if (!isCurrentStopRequest()) return;
    appendFuzzLog(
      `停止刚启动的 Fuzzer 任务失败: ${getErrorMessage(error, '未知错误')}`,
      'WARN',
    );
    fuzz.error = '停止模糊测试失败';
    fuzz.status = 'running';
    fuzzRunId += 1;
    const resumedRunId = fuzzRunId;
    fuzzElapsedTimer = setInterval(updateFuzzElapsed, 1000);
    void pollFuzzJob(jobId, resumedRunId, false);
  } finally {
    if (fuzzStopRequestedRunId === runId) fuzzStopRequestedRunId = null;
  }
}

function updateFuzzPocPath(data: {
  artifacts?: ProtocolFuzzingJob['artifacts'];
  job?: ProtocolFuzzingJob;
  log_file_path?: null | string;
  logFilePath?: null | string;
  output_root?: string;
  output_source?: string;
  outputRoot?: string;
  outputSource?: string;
  poc_path?: string;
  pocPath?: string;
}) {
  const nextPath =
    data.pocPath ||
    data.poc_path ||
    data.job?.artifacts?.pocPath ||
    data.artifacts?.pocPath ||
    data.outputRoot ||
    data.output_root ||
    data.job?.artifacts?.outputRoot ||
    data.artifacts?.outputRoot ||
    data.job?.artifacts?.outputPath ||
    data.artifacts?.outputPath ||
    '';
  if (typeof nextPath === 'string' && nextPath.trim()) {
    fuzz.pocPath = nextPath.trim();
    return;
  }

  const logFilePath =
    data.logFilePath ||
    data.log_file_path ||
    data.job?.artifacts?.logFilePath ||
    data.artifacts?.logFilePath;
  if (typeof logFilePath !== 'string' || !logFilePath.trim()) return;
  const normalizedPath = logFilePath.trim();
  const logDir = normalizedPath.replace(/[/\\][^/\\]*$/, '');
  if (logDir && logDir !== normalizedPath) fuzz.pocPath = logDir;
}

async function stopFuzzing() {
  if (fuzz.status === 'configuring') {
    const runId = fuzzRunId;
    if (fuzzStartPendingRunId === runId) {
      fuzzStopRequestedRunId = runId;
    }
    fuzzRunId += 1;
    clearFuzzElapsedTimer();
    fuzz.status = fuzzStartPendingRunId === runId ? 'stopping' : 'stopped';
    return;
  }
  if (fuzz.status !== 'running' || !fuzz.job?.jobId) return;
  const jobId = fuzz.job.jobId;
  fuzzRunId += 1;
  const stopRunId = fuzzRunId;
  fuzz.status = 'stopping';

  const isCurrentStopRequest = () =>
    fuzzRunId === stopRunId &&
    fuzz.status === 'stopping' &&
    fuzz.job?.jobId === jobId;

  try {
    const job = await stopProtocolFuzzingJob(jobId);
    if (!isCurrentStopRequest()) return;
    fuzz.job = job;
    const pendingLogRequest = fuzzLogRequestFinished;
    if (pendingLogRequest) {
      await pendingLogRequest;
    } else {
      try {
        const data = await fetchProtocolFuzzingLogs(jobId, fuzzLogPosition);
        if (!isCurrentStopRequest()) return;
        fuzz.job = data.job;
        if (typeof data.position === 'number') fuzzLogPosition = data.position;
        updateFuzzPocPath(data);
        if (data.content) appendFuzzLogContent(data.content);
      } catch (error) {
        if (!isCurrentStopRequest()) return;
        appendFuzzLog(
          `停止后读取最终日志失败: ${getErrorMessage(error, '未知错误')}`,
          'WARN',
        );
      }
    }
    if (!isCurrentStopRequest()) return;
    fuzz.status = 'stopped';
    clearFuzzElapsedTimer();
  } catch (error) {
    if (!isCurrentStopRequest()) return;
    fuzz.error = getErrorMessage(error, '停止模糊测试失败');
    fuzz.status = 'running';
    fuzzRunId += 1;
    const resumedRunId = fuzzRunId;
    void pollFuzzJob(jobId, resumedRunId, false);
  }
}

export function useAnalysisModules() {
  return {
    assertGeneration,
    assertInputs,
    codeLocate,
    fuzz,
    fuzzInput,
    fuzzStats,
    isFuzzRunning,
    latestAssertGenerationJobId,
    runAssertGeneration,
    runCodeLocate,
    runFuzzing,
    resetCodeLocateOutput,
    assertionOutputContexts,
    codeLocateInputs,
    loadAssertionOutputContext,
    stopFuzzing,
    stopAssertGeneration,
    stopCodeLocate,
    useLatestCodeLocateOutput,
  };
}
