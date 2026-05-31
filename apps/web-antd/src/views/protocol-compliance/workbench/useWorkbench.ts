import { reactive, ref, computed } from 'vue';
import { message } from 'ant-design-vue';

import type {
  ProtocolAssertGenerationJob,
  ProtocolAssertGenerationResult,
  ProtocolExtractRuleItem,
  ProtocolStaticAnalysisJob,
  ProtocolStaticAnalysisResult,
} from '#/api/protocol-compliance';

import {
  downloadStaticAnalysisDatabase,
  executeCommand,
  fetchProtocolAssertGenerationProgress,
  fetchProtocolAssertGenerationResult,
  fetchProtocolInstrumentationDiff,
  fetchProtocolStaticAnalysisProgress,
  fetchProtocolStaticAnalysisResult,
  readLog,
  runProtocolAssertGeneration,
  runProtocolStaticAnalysis,
  stopAndCleanup,
  stopProcess,
  writeScript,
} from '#/api/protocol-compliance';

import {
  DEFAULT_TARGET,
  type ProjectConfig,
  type StageStatus,
  STAGE_LIST,
  type WorkbenchStage,
} from './types';
import { ansiToHtml } from './utils';

const stage = ref<WorkbenchStage>('setup');
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
const errorMessage = ref<null | string>(null);

const projectConfig = reactive<ProjectConfig>({
  archive: null,
  builder: null,
  config: null,
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

const assertJobId = ref<null | string>(null);
const assertJob = ref<null | ProtocolAssertGenerationJob>(null);
const assertResult = ref<null | ProtocolAssertGenerationResult>(null);
const assertLogText = ref('');
const assertDiffContent = ref('');

const fuzzPid = ref<null | string>(null);
const fuzzContainerId = ref<null | string>(null);
const fuzzLogs = ref<Array<{ id: number; text: string; level: 'INFO' | 'WARN' | 'ERROR' | 'STATS' }>>([]);
const fuzzLogReadPosition = ref(0);
const fuzzStats = reactive({
  executions: 0,
  paths: 0,
  crashes: 0,
  hangs: 0,
  cycles: 0,
  speed: 0,
});
const fuzzSpeedSeries = ref<number[]>([]);

let elapsedTimer: null | ReturnType<typeof setInterval> = null;
let staticPollTimer: null | ReturnType<typeof setInterval> = null;
let assertPollTimer: null | ReturnType<typeof setInterval> = null;
let fuzzPollTimer: null | ReturnType<typeof setInterval> = null;
let fuzzLogIdSeq = 0;

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

function appendFuzzLog(text: string, level: 'INFO' | 'WARN' | 'ERROR' | 'STATS' = 'INFO') {
  const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
  for (const line of lines) {
    fuzzLogIdSeq += 1;
    fuzzLogs.value.push({ id: fuzzLogIdSeq, text: line, level });
  }
  if (fuzzLogs.value.length > 500) {
    fuzzLogs.value.splice(0, fuzzLogs.value.length - 500);
  }
}

function setStage(next: WorkbenchStage, status: StageStatus = 'running', msg?: string) {
  stage.value = next;
  stageStatus[next] = status;
  if (msg) stageMessage.value = msg;
}

function markStageDone(target: WorkbenchStage, msg?: string) {
  stageStatus[target] = 'done';
  if (msg) stageMessage.value = msg;
}

function markStageError(target: WorkbenchStage, msg: string) {
  stageStatus[target] = 'error';
  errorMessage.value = msg;
  stageMessage.value = msg;
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

function buildRulesFile(): File {
  if (!selectedRule.value) {
    throw new Error('未选择规则');
  }
  const grouped: Record<string, ProtocolExtractRuleItem[]> = {};
  const rule = selectedRule.value;
  const msgType =
    (rule as { msgType?: string }).msgType ||
    rule.req_type?.[0] ||
    rule.res_type?.[0] ||
    'DEFAULT';
  grouped[msgType] = [rule];
  const json = JSON.stringify(grouped, null, 2);
  return new File([json], 'rules.json', { type: 'application/json' });
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
  if (!projectConfig.buildInstructions.trim()) {
    message.warning('请填写编译命令');
    return false;
  }
  return true;
}

function commitSetup() {
  if (!projectConfig.archive || !projectConfig.builder || !projectConfig.config) {
    message.warning('请先完成项目设置');
    return;
  }
  if (!projectConfig.buildInstructions.trim()) {
    message.warning('请填写编译命令');
    return;
  }
  stageStatus.setup = 'done';
  stage.value = 'rule_confirm';
  stageMessage.value = '请选择一条规则后启动自动化流水线';
}

function backToSetup() {
  if (stageStatus.code_locate === 'running' || stageStatus.assert_gen === 'running' || stageStatus.fuzz === 'running') {
    message.warning('请先停止当前流水线');
    return;
  }
  stage.value = 'setup';
  stageStatus.setup = 'idle';
  stageMessage.value = '调整项目设置后重新进入流水线';
}

async function pollStaticAnalysis(jobId: string) {
  clearTimer('static');
  staticPollTimer = setInterval(async () => {
    try {
      const snapshot = await fetchProtocolStaticAnalysisProgress(
        jobId,
        staticLastEventId.value || undefined,
      );
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
      }
      if (snapshot.status === 'completed') {
        clearTimer('static');
        const result = await fetchProtocolStaticAnalysisResult(jobId);
        staticResult.value = result;
        markStageDone('code_locate', '代码定位完成，进入断言生成…');
        await runAssertGenStep();
      } else if (snapshot.status === 'failed') {
        clearTimer('static');
        markStageError('code_locate', snapshot.error || '静态分析失败');
      }
    } catch (err: any) {
      clearTimer('static');
      markStageError('code_locate', err?.message || '静态分析进度查询失败');
    }
  }, 1500);
}

async function pollAssertGen(jobId: string) {
  clearTimer('assert');
  assertPollTimer = setInterval(async () => {
    try {
      const snapshot = await fetchProtocolAssertGenerationProgress(jobId);
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
        assertResult.value = result;
        try {
          const diff = await fetchProtocolInstrumentationDiff(jobId);
          assertDiffContent.value = diff?.content || '';
        } catch {
          assertDiffContent.value = '';
        }
        markStageDone('assert_gen', '断言生成完成，开始模糊测试…');
        await runFuzzStep();
      } else if (snapshot.status === 'failed') {
        clearTimer('assert');
        markStageError('assert_gen', snapshot.error || '断言生成失败');
      }
    } catch (err: any) {
      clearTimer('assert');
      markStageError('assert_gen', err?.message || '断言生成进度查询失败');
    }
  }, 1500);
}

async function runStaticAnalysisStep() {
  if (!projectConfig.archive || !projectConfig.builder || !projectConfig.config) {
    markStageError('code_locate', '项目设置不完整');
    return;
  }
  if (!selectedRule.value) {
    markStageError('code_locate', '未选择规则');
    return;
  }
  setStage('code_locate', 'running', '提交静态分析任务…');
  staticLogText.value = '';
  staticLogHtml.value = '';
  staticLastEventId.value = 0;
  try {
    const job = await runProtocolStaticAnalysis({
      codeArchive: projectConfig.archive,
      builderDockerfile: projectConfig.builder,
      config: projectConfig.config,
      rules: buildRulesFile(),
      notes: projectConfig.notes,
    });
    staticJobId.value = job.jobId;
    staticJob.value = job;
    stageMessage.value = '静态分析进行中…';
    if (job.status === 'completed') {
      const result = await fetchProtocolStaticAnalysisResult(job.jobId);
      staticResult.value = result;
      markStageDone('code_locate', '代码定位完成，进入断言生成…');
      await runAssertGenStep();
    } else if (job.status === 'failed') {
      markStageError('code_locate', job.error || '静态分析失败');
    } else {
      await pollStaticAnalysis(job.jobId);
    }
  } catch (err: any) {
    markStageError('code_locate', err?.message || '静态分析启动失败');
  }
}

async function runAssertGenStep() {
  if (!staticJobId.value) {
    markStageError('assert_gen', '缺少静态分析结果，无法生成断言');
    return;
  }
  if (!projectConfig.archive) {
    markStageError('assert_gen', '缺少源码压缩包');
    return;
  }
  setStage('assert_gen', 'running', '从静态分析下载数据库…');
  assertLogText.value = '';
  assertDiffContent.value = '';
  try {
    const blob = await downloadStaticAnalysisDatabase(staticJobId.value);
    const databaseFile = new File([blob], 'analysis.db', {
      type: 'application/octet-stream',
    });
    stageMessage.value = '提交断言生成任务…';
    const job = await runProtocolAssertGeneration({
      codeArchive: projectConfig.archive,
      database: databaseFile,
      buildInstructions: projectConfig.buildInstructions,
      notes: projectConfig.notes,
    });
    assertJobId.value = job.jobId;
    assertJob.value = job;
    stageMessage.value = '断言生成进行中…';
    if (job.status === 'completed') {
      const result = await fetchProtocolAssertGenerationResult(job.jobId);
      assertResult.value = result;
      try {
        const diff = await fetchProtocolInstrumentationDiff(job.jobId);
        assertDiffContent.value = diff?.content || '';
      } catch {
        assertDiffContent.value = '';
      }
      markStageDone('assert_gen', '断言生成完成，开始模糊测试…');
      await runFuzzStep();
    } else if (job.status === 'failed') {
      markStageError('assert_gen', job.error || '断言生成失败');
    } else {
      await pollAssertGen(job.jobId);
    }
  } catch (err: any) {
    markStageError('assert_gen', err?.message || '断言生成启动失败');
  }
}

function parseStatsLine(line: string) {
  const trimmed = line.trim();
  if (!trimmed) return;
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
    if (Number.isFinite(val) && val > fuzzStats.paths) fuzzStats.paths = val;
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
  const cycleMatch = trimmed.match(/cycles?(?:_done)?[^\d]*(\d+)/i);
  if (cycleMatch?.[1]) {
    const val = Number(cycleMatch[1]);
    if (Number.isFinite(val) && val > fuzzStats.cycles) fuzzStats.cycles = val;
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
    const content: string = data?.content || '';
    const position: number = typeof data?.position === 'number' ? data.position : fuzzLogReadPosition.value;
    if (position > fuzzLogReadPosition.value) {
      fuzzLogReadPosition.value = position;
    }
    if (content) {
      const lines = content.split(/\r?\n/);
      for (const line of lines) {
        if (!line.trim()) continue;
        let level: 'INFO' | 'ERROR' | 'WARN' | 'STATS' = 'INFO';
        const lower = line.toLowerCase();
        if (lower.includes('crash') || lower.includes('error') || lower.includes('fatal')) level = 'ERROR';
        else if (lower.includes('warn')) level = 'WARN';
        else if (/stats|execs|paths|coverage|cycles/i.test(line)) level = 'STATS';
        appendFuzzLog(line, level);
        if (level === 'STATS') parseStatsLine(line);
      }
    }
  } catch (err: any) {
    // Non-fatal: keep polling until user stops
    console.warn('[workbench] readLog error', err?.message || err);
  }
}

async function runFuzzStep() {
  setStage('fuzz', 'running', '写入 Fuzz 脚本…');
  fuzzLogs.value = [];
  fuzzLogReadPosition.value = 0;
  Object.assign(fuzzStats, { executions: 0, paths: 0, crashes: 0, hangs: 0, cycles: 0, speed: 0 });
  fuzzSpeedSeries.value = [];
  try {
    const script = buildFuzzScript();
    await writeScript({
      content: script,
      protocol: protocolKindForApi.value,
      protocolImplementations: protocolImplementationsKey.value,
    } as any);
    stageMessage.value = '启动 Fuzzer 容器/进程…';
    const launch: any = await executeCommand({
      protocol: protocolKindForApi.value,
      protocolImplementations: protocolImplementationsKey.value,
    } as any);
    const launchData = launch?.data ?? launch;
    if (launchData?.pid) fuzzPid.value = String(launchData.pid);
    if (launchData?.container_id) fuzzContainerId.value = String(launchData.container_id);
    stageMessage.value = '模糊测试运行中，点击"停止"结束';
    fuzzPollTimer = setInterval(readFuzzLogs, 2000);
  } catch (err: any) {
    markStageError('fuzz', err?.message || '模糊测试启动失败');
  }
}

async function startPipeline(rule: ProtocolExtractRuleItem) {
  if (!(await ensureProjectReady())) return;
  selectedRule.value = rule;
  errorMessage.value = null;
  startedAt.value = new Date();
  elapsedSeconds.value = 0;
  startElapsedTimer();
  stageStatus.rule_confirm = 'done';
  await runStaticAnalysisStep();
}

async function stopPipeline() {
  if (isStopping.value) return;
  isStopping.value = true;
  try {
    clearTimer('static');
    clearTimer('assert');
    clearTimer('fuzz');
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
    stageStatus.done = 'done';
    clearTimer('elapsed');
    stageMessage.value = '流水线已停止';
  } finally {
    isStopping.value = false;
  }
}

function resetWorkbench() {
  clearTimer('static');
  clearTimer('assert');
  clearTimer('fuzz');
  clearTimer('elapsed');
  for (const s of STAGE_LIST) stageStatus[s.key] = 'idle';
  stageStatus.setup = 'idle';
  stage.value = 'setup';
  startedAt.value = null;
  elapsedSeconds.value = 0;
  selectedRule.value = null;
  staticJobId.value = null;
  staticJob.value = null;
  staticResult.value = null;
  staticLogText.value = '';
  staticLogHtml.value = '';
  staticLastEventId.value = 0;
  assertJobId.value = null;
  assertJob.value = null;
  assertResult.value = null;
  assertLogText.value = '';
  assertDiffContent.value = '';
  fuzzPid.value = null;
  fuzzContainerId.value = null;
  fuzzLogs.value = [];
  fuzzLogReadPosition.value = 0;
  Object.assign(fuzzStats, { executions: 0, paths: 0, crashes: 0, hangs: 0, cycles: 0, speed: 0 });
  fuzzSpeedSeries.value = [];
  errorMessage.value = null;
  stageMessage.value = '请先在“项目设置”中上传所需文件';
}

export function useWorkbench() {
  return {
    // State
    stage,
    stageStatus,
    stageMessage,
    elapsedSeconds,
    startedAt,
    isStopping,
    errorMessage,
    projectConfig,
    selectedRule,
    staticJob,
    staticJobId,
    staticResult,
    staticLogHtml,
    assertJob,
    assertJobId,
    assertResult,
    assertLogText,
    assertDiffContent,
    fuzzLogs,
    fuzzStats,
    fuzzSpeedSeries,
    fuzzPid,
    fuzzContainerId,

    // Methods
    commitSetup,
    backToSetup,
    startPipeline,
    stopPipeline,
    resetWorkbench,
  };
}
