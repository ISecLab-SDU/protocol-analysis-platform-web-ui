<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import { Button, Card, Empty, Tag } from 'ant-design-vue';
import { IconifyIcon } from '@vben/icons';

import type {
  ProtocolExtractRuleItem,
  ProtocolStaticAnalysisComplianceStatus,
  ProtocolStaticAnalysisResult,
  ProtocolStaticAnalysisVerdict,
} from '#/api/protocol-compliance';

import type { CodeLocateEvidence, CodeLocateFunctionSlice } from '../types';
import { normalizeList } from '../utils';

interface Props {
  evidence: CodeLocateEvidence | null;
  logHtml: string;
  logText: string;
  result: null | ProtocolStaticAnalysisResult;
  rule: null | ProtocolExtractRuleItem;
  running: boolean;
}

interface LogLine {
  id: string;
  group: PipelineStageKey | 'other';
  isKey: boolean;
  isNoise: boolean;
  kind: 'error' | 'function' | 'normal' | 'path' | 'slice' | 'summary';
  raw: string;
  source: string;
  stage: string;
  text: string;
  time: string;
  timestampMs?: number;
}

const props = defineProps<Props>();

const selectedFunctionName = ref('');
const logBodyRef = ref<HTMLElement | null>(null);
const rawLogsExpanded = ref(false);
const selectedLogGroup = ref<PipelineStageKey | 'all'>('all');
const keyLogsOnly = ref(true);

type PipelineStageKey =
  | 'analysis'
  | 'build'
  | 'compile'
  | 'prepare'
  | 'results'
  | 'validate';

interface PipelineStep {
  description: string;
  key: PipelineStageKey;
  stageAliases: string[];
  title: string;
}

const PIPELINE_STEPS: PipelineStep[] = [
  {
    description: '接收任务并整理源码、规则和配置文件',
    key: 'prepare',
    stageAliases: ['queued', 'init', 'inputs', 'workspace'],
    title: '准备分析任务',
  },
  {
    description: '构建隔离的 Docker 分析环境，配置网络代理和依赖',
    key: 'build',
    stageAliases: ['proxy', 'builder', 'builder-log'],
    title: '构建分析环境',
  },
  {
    description: '运行 Builder 容器，把目标项目编译成可分析产物',
    key: 'compile',
    stageAliases: ['container', 'container-log', 'workspace-snapshot'],
    title: '编译目标项目',
  },
  {
    description: '确认 bitcode、数据库、规则配置等输入已经就绪',
    key: 'validate',
    stageAliases: ['validation'],
    title: '校验分析产物',
  },
  {
    description: '执行规则匹配、函数定位和不一致性分析',
    key: 'analysis',
    stageAliases: ['analysis', 'analysis-debug'],
    title: '运行静态分析',
  },
  {
    description: '收集数据库、JSON 结果、日志和工作区快照',
    key: 'results',
    stageAliases: ['results', 'completed'],
    title: '生成分析结果',
  },
];

const STAGE_TO_GROUP = PIPELINE_STEPS.reduce(
  (acc, step) => {
    for (const stage of step.stageAliases) acc[stage] = step.key;
    return acc;
  },
  {} as Record<string, PipelineStageKey>,
);

const INSIGHT_PATTERNS = [
  /match-pass completed/i,
  /Inconsistency analysis completed/i,
  /JSON outputs/i,
  /database files after run/i,
  /All required artefacts/i,
  /Container .*started/i,
];

const IMPORTANT_LOG_PATTERNS = [
  /started/i,
  /completed/i,
  /failed/i,
  /error/i,
  /warning/i,
  /Building/i,
  /Running/i,
  /Launching/i,
  /Validating/i,
  /All required/i,
  /match-pass/i,
  /Inconsistency/i,
  /JSON outputs/i,
  /database files/i,
  /Copying analysis artifacts/i,
  /Container .*started/i,
  /exited cleanly/i,
];

const verdicts = computed(() => props.result?.modelResponse?.verdicts ?? []);
const summary = computed(() => props.result?.modelResponse?.summary ?? null);

const verdictStats = computed(() => {
  if (summary.value) {
    return {
      compliant: summary.value.compliantCount,
      needsReview: summary.value.needsReviewCount,
      nonCompliant: summary.value.nonCompliantCount,
    };
  }
  const stats = { compliant: 0, needsReview: 0, nonCompliant: 0 };
  for (const verdict of verdicts.value) {
    if (verdict.compliance === 'compliant') stats.compliant += 1;
    else if (verdict.compliance === 'needs_review') stats.needsReview += 1;
    else if (verdict.compliance === 'non_compliant') stats.nonCompliant += 1;
  }
  return stats;
});

const primaryVerdict = computed(() => {
  return (
    verdicts.value.find((verdict) => verdict.compliance === 'non_compliant') ??
    verdicts.value.find((verdict) => verdict.compliance === 'needs_review') ??
    verdicts.value[0] ??
    null
  );
});

const ruleText = computed(() => {
  return (
    props.evidence?.ruleText ||
    props.rule?.rule ||
    props.rule?.description ||
    primaryVerdict.value?.relatedRule?.requirement ||
    '等待规则证据输入'
  );
});

const ruleSource = computed(() => {
  return props.evidence?.source || primaryVerdict.value?.relatedRule?.source || '协议规则集';
});

const targetFile = computed(() => {
  return (
    props.evidence?.targetFile ||
    primaryVerdict.value?.location?.file ||
    props.result?.inputs?.codeFileName ||
    '待定位'
  );
});

const targetLine = computed(() => {
  if (props.evidence?.targetLine) return props.evidence.targetLine;
  const range = primaryVerdict.value?.lineRange;
  if (!range) return '-';
  return range[0] === range[1] ? String(range[0]) : `${range[0]}-${range[1]}`;
});

const functionRecords = computed<CodeLocateFunctionSlice[]>(() => {
  const evidenceFunctions = props.evidence?.functions?.filter((fn) => fn.name.trim()) ?? [];
  if (evidenceFunctions.length > 0) return evidenceFunctions;

  const records = new Map<string, CodeLocateFunctionSlice>();
  for (const verdict of verdicts.value) {
    const name = verdict.location?.function || verdict.location?.file;
    if (!name || records.has(name)) continue;
    records.set(name, {
      codeRows: [],
      name,
      path: verdict.location?.file,
      targetLine: verdict.lineRange?.[0],
    });
  }
  return [...records.values()];
});

const selectedFunction = computed(() => {
  return (
    functionRecords.value.find((fn) => fn.name === selectedFunctionName.value) ??
    functionRecords.value[0] ??
    null
  );
});

const candidateFunctionCount = computed(() => {
  if (props.evidence) return props.evidence.candidateFunctionCount;
  return functionRecords.value.length || verdicts.value.length;
});

const keySliceCount = computed(() => {
  if (props.evidence) return props.evidence.keySliceCount;
  return functionRecords.value.filter((fn) => fn.codeRows.length > 0).length ||
    verdictStats.value.nonCompliant + verdictStats.value.needsReview;
});

const relatedVariableCount = computed(() => {
  if (props.evidence) return props.evidence.relatedVariableCount;
  const fields = new Set([
    ...normalizeList(props.rule?.req_fields),
    ...normalizeList(props.rule?.res_fields),
  ]);
  return fields.size;
});

const fallbackCodeRows = computed(() => {
  if (props.evidence?.codeRows.length) return props.evidence.codeRows;
  const verdict = primaryVerdict.value;
  const lineBase = Array.isArray(verdict?.lineRange) ? verdict.lineRange[0] : 315;
  const statusText = verdict ? complianceLabel(verdict.compliance) : '定位中';
  return [
    { emphasis: false, line: lineBase, text: `// ${ruleSource.value}` },
    { emphasis: false, line: lineBase + 1, text: `target_rule = "${ruleText.value}"` },
    { emphasis: false, line: lineBase + 2, text: `target_file = "${targetFile.value}"` },
    { emphasis: true, line: lineBase + 3, text: `analysis_verdict = "${statusText}"` },
    { emphasis: false, line: lineBase + 4, text: verdict?.explanation || '等待静态分析返回代码上下文...' },
  ];
});

const detailRows = computed(() => {
  if (selectedFunction.value) return selectedFunction.value.codeRows;
  if (!props.evidence && !props.result) return [];
  return fallbackCodeRows.value;
});

const detailTitle = computed(() => {
  return selectedFunction.value?.name || primaryVerdict.value?.location?.function || '等待函数切片';
});

const detailPath = computed(() => {
  return selectedFunction.value?.path || targetFile.value;
});

const detailLine = computed(() => {
  return selectedFunction.value?.targetLine || targetLine.value;
});

const visibleVerdicts = computed(() => verdicts.value.slice(0, 4));

const stageStateText = computed(() => {
  if (props.running) return '进行中';
  if (props.result || props.evidence) return '已完成';
  return '等待中';
});

const logLines = computed<LogLine[]>(() => {
  const rawLines = props.logText
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.trim().length > 0);
  return rawLines.map(parseLogLine);
});

const customerLogLines = computed(() => {
  return logLines.value.filter((line) => line.isKey && !line.isNoise).slice(-80);
});

const technicalLogLines = computed(() => {
  return logLines.value
    .filter((line) => {
      if (selectedLogGroup.value !== 'all' && line.group !== selectedLogGroup.value) {
        return false;
      }
      if (keyLogsOnly.value && !line.isKey) return false;
      return true;
    })
    .slice(rawLogsExpanded.value ? -500 : -160);
});

const pipelineSummaries = computed(() => {
  const lastCompletedIndex = hasCompletedEvent.value
    ? PIPELINE_STEPS.length - 1
    : Math.max(
        -1,
        ...PIPELINE_STEPS.map((step, index) =>
          logLines.value.some((line) => line.group === step.key) ? index - 1 : -1,
        ),
      );
  const currentIndex = currentPipelineIndex.value;

  return PIPELINE_STEPS.map((step, index) => {
    const lines = logLines.value.filter((line) => line.group === step.key);
    const keyLines = lines.filter((line) => line.isKey && !line.isNoise);
    const hasError = lines.some((line) => line.kind === 'error');
    let status: 'done' | 'error' | 'idle' | 'running' = 'idle';
    if (hasError) status = 'error';
    else if (props.result || hasCompletedEvent.value || index <= lastCompletedIndex) status = 'done';
    else if (index === currentIndex) status = 'running';
    else if (lines.length > 0 && index < currentIndex) status = 'done';

    return {
      ...step,
      duration: formatStageDuration(lines),
      lastLine: keyLines.at(-1) ?? lines.at(-1) ?? null,
      lineCount: lines.length,
      status,
    };
  });
});

const hasCompletedEvent = computed(() => {
  return Boolean(
    props.result ||
      logLines.value.some(
        (line) =>
          line.stage === 'completed' ||
          /completed successfully|job completed successfully/i.test(line.text),
      ),
  );
});

const currentPipelineIndex = computed(() => {
  for (let index = logLines.value.length - 1; index >= 0; index -= 1) {
    const group = logLines.value[index]?.group;
    if (!group || group === 'other') continue;
    const stepIndex = PIPELINE_STEPS.findIndex((step) => step.key === group);
    if (stepIndex >= 0) return stepIndex;
  }
  return props.running ? 0 : -1;
});

const currentPipelineStep = computed(() => {
  if (props.result || hasCompletedEvent.value) return PIPELINE_STEPS.at(-1) ?? null;
  return PIPELINE_STEPS[currentPipelineIndex.value] ?? null;
});

const pipelineProgress = computed(() => {
  if (props.result || hasCompletedEvent.value) return 100;
  const currentIndex = currentPipelineIndex.value;
  if (currentIndex < 0) return 0;
  const completedWeight = currentIndex;
  const runningWeight = props.running ? 0.55 : 0.2;
  return Math.min(96, Math.round(((completedWeight + runningWeight) / PIPELINE_STEPS.length) * 100));
});

const currentActionText = computed(() => {
  const lastKeyLine = [...customerLogLines.value].reverse().find((line) => line.text);
  if (lastKeyLine) return humanizeLogText(lastKeyLine);
  if (currentPipelineStep.value) return currentPipelineStep.value.description;
  return props.running ? '等待分析任务输出进度' : '等待代码定位阶段开始';
});

const dashboardMetrics = computed(() => {
  const functions = new Set<string>();
  let directorySnapshots = 0;
  let databaseInfo = '';
  let jsonOutputs = '';
  let containerId = '';
  let builderImage = '';

  for (const line of logLines.value) {
    const functionMatch = line.text.match(/^Function:\s*(.+)$/i);
    if (functionMatch?.[1]) functions.add(functionMatch[1].trim());

    if (line.isNoise && line.group === 'compile') directorySnapshots += 1;

    const databaseMatch = line.text.match(/database files after run:\s*(\d+)(?:\s*\(size=([^)]+)\))?/i);
    if (databaseMatch?.[1]) {
      databaseInfo = `${databaseMatch[1]} 个数据库${databaseMatch[2] ? ` / ${databaseMatch[2]}` : ''}`;
    }

    const jsonMatch = line.text.match(/JSON outputs:\s*(\d+)/i);
    if (jsonMatch?.[1]) jsonOutputs = `${jsonMatch[1]} 个 JSON 输出`;

    const containerMatch = line.text.match(/Container\s+([a-f0-9]{8,})\s+started/i);
    if (containerMatch?.[1]) containerId = containerMatch[1].slice(0, 12);

    const imageMatch =
      line.text.match(/image[=\s]([^\s,]+)/i) ||
      line.text.match(/tag=([^,\s]+)/i) ||
      line.text.match(/naming to docker\.io\/library\/([^\s]+)/i);
    if (imageMatch?.[1]) builderImage = imageMatch[1];
  }

  const functionTotal = candidateFunctionCount.value || functions.size;
  return [
    { label: '阶段进度', value: `${pipelineProgress.value}%` },
    { label: '候选函数', value: String(functionTotal) },
    { label: '分析产物', value: databaseInfo || jsonOutputs || '生成中' },
    { label: '容器证据', value: containerId || shortEvidence(builderImage) || '待捕获' },
    { label: '降噪日志', value: directorySnapshots > 0 ? `${directorySnapshots} 行已折叠` : '无噪声' },
  ];
});

const insightEvents = computed(() => {
  const events = customerLogLines.value
    .filter((line) => {
      return (
        line.kind === 'function' ||
        line.kind === 'path' ||
        matchesAny(line.text, INSIGHT_PATTERNS)
      );
    })
    .slice(-8);
  return events;
});

const hasContent = computed(() => {
  return Boolean(props.logText || props.logHtml || props.running || props.result || props.evidence);
});

watch(
  functionRecords,
  (records) => {
    if (records.length === 0) {
      selectedFunctionName.value = '';
      return;
    }
    if (!records.some((record) => record.name === selectedFunctionName.value)) {
      selectedFunctionName.value = records[0]?.name ?? '';
    }
  },
  { immediate: true },
);

watch(
  () => logLines.value.length,
  async () => {
    await nextTick();
    const target = logBodyRef.value;
    if (!target) return;
    target.scrollTop = target.scrollHeight;
  },
);

function parseLogLine(raw: string, index: number): LogLine {
  let rest = raw.trim();
  let stage = '';
  let time = '';
  let source = '';

  const leadingStage = rest.match(/^\(([^)]+)\)\s*(.*)$/);
  if (leadingStage?.[1]) {
    stage = leadingStage[1];
    rest = leadingStage[2] ?? '';
  }

  const timeMatch = rest.match(/^\[([^\]]+)\]\s*(.*)$/);
  if (timeMatch?.[1]) {
    time = timeMatch[1];
    rest = timeMatch[2] ?? '';
  }

  const inlineStage = rest.match(/^\(([^)]+)\)\s*(.*)$/);
  if (inlineStage?.[1]) {
    stage = stage || inlineStage[1];
    rest = inlineStage[2] ?? '';
  }

  if (!/^(Function|Path|func):|\d+\s+/.test(rest)) {
    const sourceMatch = rest.match(/^([^\s:]+(?::[^\s:]+)?):\s*(.*)$/);
    if (sourceMatch?.[1]) {
      source = sourceMatch[1];
      rest = sourceMatch[2] ?? '';
    }
  }
  const kind = classifyLogLine(rest);
  const group = resolveLogGroup(stage, rest);
  const isNoise = isNoisyLogLine(stage, rest);

  return {
    group,
    id: `${index}-${raw}`,
    isKey: kind !== 'normal' || isKeyLogLine(stage, rest),
    isNoise,
    kind,
    raw,
    source,
    stage,
    text: rest || raw,
    time,
    timestampMs: parseLogTime(time),
  };
}

function classifyLogLine(text: string): LogLine['kind'] {
  if (/error|failed|失败/i.test(text)) return 'error';
  if (/Extracted\s+\d+\s+functions/i.test(text)) return 'summary';
  if (/^func:/i.test(text)) return 'function';
  if (/^Function:/i.test(text)) return 'slice';
  if (/^Path:/i.test(text)) return 'path';
  return 'normal';
}

function inferGroupFromText(text: string): PipelineStageKey | 'other' {
  if (/docker|buildkit|build definition|build args|proxy/i.test(text)) return 'build';
  if (/container|workspace|bitcode|compile|database files after run/i.test(text)) return 'compile';
  if (/validating|required artefacts/i.test(text)) return 'validate';
  if (/analysis|match-pass|inconsistency/i.test(text)) return 'analysis';
  if (/collecting|completed|json outputs|artifacts/i.test(text)) return 'results';
  return 'other';
}

function resolveLogGroup(stage: string, text: string): LogLine['group'] {
  if (
    /^Function:|^Path:|match-pass|database files after run|Starting inconsistency|OPENAI_API_KEY|Inconsistency analysis/i.test(
      text,
    )
  ) {
    return 'analysis';
  }
  if (/Copying analysis artifacts|Cleaning up empty log files|JSON outputs/i.test(text)) {
    return 'results';
  }
  return STAGE_TO_GROUP[stage] ?? inferGroupFromText(text);
}

function isKeyLogLine(stage: string, text: string) {
  const primaryStages = [
    'queued',
    'init',
    'inputs',
    'workspace',
    'builder',
    'proxy',
    'container',
    'validation',
    'analysis',
    'results',
    'completed',
  ];
  if (primaryStages.includes(stage)) {
    return true;
  }
  return matchesAny(text, IMPORTANT_LOG_PATTERNS);
}

function matchesAny(text: string, patterns: RegExp[]) {
  return patterns.some((pattern) => pattern.test(text));
}

function isNoisyLogLine(stage: string, text: string) {
  if (stage !== 'container-log' && stage !== 'builder-log' && stage !== 'analysis-debug') return false;
  if (/^#\d+\s/.test(text)) return !/DONE|ERROR|CACHED|exporting|naming/i.test(text);
  if (/^(\||`|[-\s])+/.test(text)) return true;
  if (/^\d+\s+/.test(text)) return false;
  if (/^(Function|Path):/i.test(text)) return false;
  if (/match-pass|Inconsistency|JSON outputs|database files|Copying analysis artifacts/i.test(text)) return false;
  return stage === 'analysis-debug';
}

function parseLogTime(value: string) {
  if (!value) return undefined;
  const iso = Date.parse(value);
  if (Number.isFinite(iso)) return iso;
  const match = value.match(/^(\d{1,2}):(\d{2}):(\d{2})$/);
  if (!match) return undefined;
  const [, hour, minute, second] = match;
  return Number(hour) * 3_600_000 + Number(minute) * 60_000 + Number(second) * 1000;
}

function formatStageDuration(lines: LogLine[]) {
  const times = lines
    .map((line) => line.timestampMs)
    .filter((value): value is number => typeof value === 'number');
  if (times.length < 2) return '-';
  const durationSeconds = Math.max(0, Math.round((times.at(-1)! - times[0]!) / 1000));
  if (durationSeconds < 60) return `${durationSeconds}s`;
  return `${Math.floor(durationSeconds / 60)}m ${durationSeconds % 60}s`;
}

function humanizeLogText(line: LogLine) {
  const text = line.text;
  if (/Building builder image/i.test(text)) return '正在构建隔离分析环境';
  if (/Source archive extracted/i.test(text)) return '源码已解压，正在准备工作区';
  if (/Running builder container|Container .*started/i.test(text)) return 'Builder 容器已启动，正在编译目标项目';
  if (/All required artefacts present/i.test(text)) return '分析所需产物已通过校验';
  if (/Launching analysis container/i.test(text)) return '正在启动静态分析容器';
  if (/match-pass completed/i.test(text)) return '规则匹配完成，已生成候选数据库';
  if (/Starting inconsistency analysis/i.test(text)) return '正在进行不一致性分析';
  if (/Inconsistency analysis completed/i.test(text)) return '不一致性分析完成，正在汇总结果';
  if (/ProtocolGuard job completed|Static analysis completed/i.test(text)) return '静态分析完成，结果已生成';
  return text;
}

function pipelineTitle(group: LogLine['group'], fallback?: string) {
  return PIPELINE_STEPS.find((step) => step.key === group)?.title || fallback || '事件';
}

function shortEvidence(value?: string) {
  if (!value) return '';
  if (value.length <= 28) return value;
  return `${value.slice(0, 25)}...`;
}

function complianceLabel(value: ProtocolStaticAnalysisComplianceStatus) {
  if (value === 'compliant') return '合规';
  if (value === 'non_compliant') return '不合规';
  return '待审查';
}

function complianceColor(value: ProtocolStaticAnalysisComplianceStatus) {
  if (value === 'compliant') return 'success';
  if (value === 'non_compliant') return 'error';
  return 'warning';
}

function formatLocation(verdict: ProtocolStaticAnalysisVerdict) {
  const file = verdict.location?.file || '-';
  const fn = verdict.location?.function ? `#${verdict.location.function}` : '';
  if (!verdict.lineRange) return `${file}${fn}`;
  return `${file}:${verdict.lineRange[0]}-${verdict.lineRange[1]}${fn}`;
}

function shortPath(path?: string) {
  if (!path) return '待定位';
  const normalized = path.replaceAll('\\', '/');
  return normalized.split('/').filter(Boolean).pop() || path;
}

function formatFunctionLocation(fn: CodeLocateFunctionSlice) {
  const path = fn.path ? shortPath(fn.path) : targetFile.value;
  if (!fn.targetLine || fn.targetLine === '-') return path;
  return `${path}:${fn.targetLine}`;
}

function sliceStatus(fn: CodeLocateFunctionSlice) {
  return fn.codeRows.length > 0 ? '已生成切片' : '已发现';
}
</script>

<template>
  <Card class="stage-card locate-stage" :bordered="false">
    <template #title>
      <div class="stage-title">
        <IconifyIcon icon="mdi:file-search-outline" />
        <span>代码定位</span>
        <small>{{ stageStateText }}</small>
      </div>
    </template>
    <template #extra>
      <Tag v-if="running" color="processing">进行中</Tag>
      <Tag v-else-if="result || evidence" color="success">已完成</Tag>
      <Tag v-else color="default">等待中</Tag>
    </template>

    <div v-if="hasContent" class="locate-workspace">
      <section class="pipeline-dashboard">
        <div class="pipeline-overview">
          <div class="pipeline-copy">
            <span class="panel-kicker">甲方视角主流程</span>
            <h3>{{ currentPipelineStep?.title || '等待分析任务' }}</h3>
            <p>{{ currentActionText }}</p>
          </div>
          <div class="progress-ring" :style="{ '--progress': `${pipelineProgress}%` }">
            <strong>{{ pipelineProgress }}%</strong>
            <span>总进度</span>
          </div>
        </div>

        <div class="metric-grid">
          <div v-for="metric in dashboardMetrics" :key="metric.label" class="metric-item">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
          </div>
        </div>
      </section>

      <section class="pipeline-timeline">
        <article
          v-for="(item, idx) in pipelineSummaries"
          :key="item.key"
          class="pipeline-step"
          :class="`pipeline-step--${item.status}`"
        >
          <div class="pipeline-index">
            <IconifyIcon v-if="item.status === 'done'" icon="mdi:check" />
            <IconifyIcon v-else-if="item.status === 'error'" icon="mdi:close" />
            <span v-else>{{ idx + 1 }}</span>
          </div>
          <div class="pipeline-step-copy">
            <div class="pipeline-step-head">
              <strong>{{ item.title }}</strong>
              <Tag
                :color="
                  item.status === 'done'
                    ? 'success'
                    : item.status === 'running'
                      ? 'processing'
                      : item.status === 'error'
                        ? 'error'
                        : 'default'
                "
              >
                {{
                  item.status === 'done'
                    ? '已完成'
                    : item.status === 'running'
                      ? '进行中'
                      : item.status === 'error'
                        ? '异常'
                        : '等待中'
                }}
              </Tag>
            </div>
            <p>{{ item.description }}</p>
            <small>
              {{ item.lineCount > 0 ? `${item.lineCount} 条事件` : '尚未开始' }}
              <span v-if="item.duration !== '-'"> · 耗时 {{ item.duration }}</span>
            </small>
            <code v-if="item.lastLine">{{ humanizeLogText(item.lastLine) }}</code>
          </div>
        </article>
      </section>

      <section class="summary-strip">
        <div class="summary-item">
          <span>候选函数</span>
          <strong>{{ candidateFunctionCount }}</strong>
        </div>
        <div class="summary-item">
          <span>已生成切片</span>
          <strong>{{ keySliceCount }}</strong>
        </div>
        <div class="summary-item">
          <span>相关变量</span>
          <strong>{{ relatedVariableCount }}</strong>
        </div>
        <div class="summary-rule">
          <span>规则证据</span>
          <p>{{ ruleText }}</p>
        </div>
      </section>

      <section class="observe-grid">
        <section class="live-log-panel">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">过程叙事</span>
              <h3>关键事件</h3>
            </div>
            <Tag :color="running ? 'processing' : 'default'">
              {{ running ? '自动滚动' : `${customerLogLines.length} 条` }}
            </Tag>
          </div>

          <div ref="logBodyRef" class="live-log">
            <div
              v-for="line in customerLogLines"
              :key="line.id"
              class="log-line"
              :class="`log-line--${line.kind}`"
            >
              <span class="log-time">{{ line.time || '--:--:--' }}</span>
              <span v-if="line.stage" class="log-chip">{{ line.stage }}</span>
              <span v-if="line.source" class="log-chip log-chip--source">{{ line.source }}</span>
              <span class="log-text">{{ humanizeLogText(line) }}</span>
            </div>
            <div v-if="customerLogLines.length === 0" class="log-empty">
              {{ running ? '等待日志输出...' : '暂无日志输出' }}
            </div>
          </div>
        </section>

        <section class="discovery-panel">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">检测到的相关内容</span>
              <h3>函数发现记录</h3>
            </div>
            <Tag color="blue">{{ functionRecords.length }} 个函数</Tag>
          </div>

          <div v-if="functionRecords.length > 0" class="function-list">
            <button
              v-for="fn in functionRecords"
              :key="fn.name"
              class="function-item"
              :class="{ 'function-item--active': selectedFunction?.name === fn.name }"
              type="button"
              :aria-pressed="selectedFunction?.name === fn.name"
              @click="selectedFunctionName = fn.name"
            >
              <span class="function-main">
                <strong>{{ fn.name }}</strong>
                <small>{{ formatFunctionLocation(fn) }}</small>
              </span>
              <Tag :color="fn.codeRows.length > 0 ? 'success' : 'default'">
                {{ sliceStatus(fn) }}
              </Tag>
            </button>
          </div>
          <Empty
            v-else
            description="等待发现相关函数"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
          />
        </section>
      </section>

      <section class="insight-panel">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">技术证据视角</span>
            <h3>关键发现</h3>
          </div>
          <Tag color="blue">{{ insightEvents.length }} 条证据</Tag>
        </div>
        <div v-if="insightEvents.length > 0" class="insight-list">
          <article
            v-for="event in insightEvents"
            :key="event.id"
            class="insight-item"
            :class="`insight-item--${event.kind}`"
          >
            <span>{{ event.time || '--:--:--' }}</span>
            <strong>{{ pipelineTitle(event.group, event.stage) }}</strong>
            <p>{{ humanizeLogText(event) }}</p>
          </article>
        </div>
        <Empty
          v-else
          description="等待提取关键证据"
          :image="Empty.PRESENTED_IMAGE_SIMPLE"
        />
      </section>

      <section class="slice-panel">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">点击函数查看证据</span>
            <h3>{{ detailTitle }}</h3>
          </div>
          <Tag v-if="selectedFunction" :color="detailRows.length > 0 ? 'success' : 'default'">
            {{ detailRows.length > 0 ? '切片已生成' : '等待切片' }}
          </Tag>
        </div>

        <div class="slice-meta">
          <div>
            <span>Path:</span>
            <code>{{ detailPath }}</code>
          </div>
          <div>
            <span>Line:</span>
            <code>{{ detailLine }}</code>
          </div>
          <div>
            <span>Source:</span>
            <code>{{ ruleSource }}{{ evidence?.resultLabel ? ` · ${evidence.resultLabel}` : '' }}</code>
          </div>
        </div>

        <div v-if="detailRows.length > 0" class="code-window">
          <div
            v-for="(row, idx) in detailRows"
            :key="`${row.line}-${idx}`"
            class="code-row"
            :class="{ 'code-row--emphasis': row.emphasis }"
          >
            <span class="line-no">{{ row.line }}</span>
            <span class="line-text">{{ row.text }}</span>
          </div>
        </div>
        <Empty
          v-else
          description="已记录函数名，等待切片日志输出"
          :image="Empty.PRESENTED_IMAGE_SIMPLE"
        />
      </section>

      <section v-if="summary || rule" class="rule-panel">
        <div class="rule-title">
          <IconifyIcon icon="mdi:shield-search-outline" />
          <span>规则判定</span>
        </div>
        <dl class="rule-list">
          <div>
            <dt>约束类型:</dt>
            <dd>{{ summary?.overallStatus ? complianceLabel(summary.overallStatus) : '待判定' }}</dd>
          </div>
          <div>
            <dt>源数据:</dt>
            <dd>{{ normalizeList(rule?.req_type)[0] || normalizeList(rule?.res_type)[0] || '-' }}</dd>
          </div>
          <div>
            <dt>目标行为:</dt>
            <dd>{{ ruleText }}</dd>
          </div>
        </dl>
      </section>

      <section class="technical-log-panel">
        <div class="panel-head technical-log-head">
          <div>
            <span class="panel-kicker">工程排障视角</span>
            <h3>技术日志</h3>
          </div>
          <div class="technical-actions">
            <select v-model="selectedLogGroup" class="log-filter" aria-label="选择日志阶段">
              <option value="all">全部阶段</option>
              <option v-for="step in PIPELINE_STEPS" :key="step.key" :value="step.key">
                {{ step.title }}
              </option>
            </select>
            <Button size="small" @click="keyLogsOnly = !keyLogsOnly">
              {{ keyLogsOnly ? '显示全部' : '只看关键' }}
            </Button>
            <Button size="small" @click="rawLogsExpanded = !rawLogsExpanded">
              {{ rawLogsExpanded ? '收起日志' : '展开更多' }}
            </Button>
          </div>
        </div>
        <div class="technical-note">
          已默认隐藏目录树、普通文件清单和 debug 噪声；完整原始消息仍保留在下方列表中。
        </div>
        <div class="technical-log">
          <div
            v-for="line in technicalLogLines"
            :key="line.id"
            class="log-line"
            :class="[`log-line--${line.kind}`, { 'log-line--noise': line.isNoise }]"
          >
            <span class="log-time">{{ line.time || '--:--:--' }}</span>
            <span v-if="line.stage" class="log-chip">{{ line.stage }}</span>
            <span v-if="line.source" class="log-chip log-chip--source">{{ line.source }}</span>
            <span class="log-text">{{ rawLogsExpanded ? line.raw : line.text }}</span>
          </div>
          <div v-if="technicalLogLines.length === 0" class="log-empty">
            当前筛选条件下暂无日志
          </div>
        </div>
      </section>
    </div>

    <section v-if="result && visibleVerdicts.length > 0" class="verdict-section">
      <div class="verdict-summary">
        <div class="verdict-stat verdict-stat--ok">
          <IconifyIcon icon="mdi:check-circle-outline" />
          <span>合规</span>
          <strong>{{ verdictStats.compliant }}</strong>
        </div>
        <div class="verdict-stat verdict-stat--warn">
          <IconifyIcon icon="mdi:alert-outline" />
          <span>待审查</span>
          <strong>{{ verdictStats.needsReview }}</strong>
        </div>
        <div class="verdict-stat verdict-stat--error">
          <IconifyIcon icon="mdi:close-circle-outline" />
          <span>不合规</span>
          <strong>{{ verdictStats.nonCompliant }}</strong>
        </div>
      </div>

      <div class="verdict-list">
        <article
          v-for="verdict in visibleVerdicts"
          :key="verdict.findingId"
          class="verdict-item"
        >
          <div class="verdict-head">
            <Tag :color="complianceColor(verdict.compliance)">
              {{ complianceLabel(verdict.compliance) }}
            </Tag>
            <code>{{ formatLocation(verdict) }}</code>
          </div>
          <p>{{ verdict.explanation }}</p>
          <p v-if="verdict.recommendation" class="recommendation">
            {{ verdict.recommendation }}
          </p>
        </article>
      </div>
    </section>

    <Empty
      v-else-if="!hasContent"
      description="等待代码定位阶段开始"
      :image="Empty.PRESENTED_IMAGE_SIMPLE"
    />
  </Card>
</template>

<style scoped>
.stage-card {
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
  box-shadow: 0 10px 26px rgb(15 23 42 / 4%);
}

.stage-title {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 16px;
  font-weight: 700;
}

.stage-title :first-child {
  color: #1677ff;
}

.stage-title small {
  font-size: 13px;
  font-weight: 500;
  color: var(--ant-color-text-secondary);
}

.locate-workspace {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pipeline-dashboard {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(420px, 0.85fr);
  gap: 16px;
  padding: 16px;
  background: #fff;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}

.pipeline-overview {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 118px;
  gap: 18px;
  align-items: center;
  min-width: 0;
}

.pipeline-copy {
  min-width: 0;
}

.pipeline-copy h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: #111827;
}

.pipeline-copy p {
  margin: 8px 0 0;
  overflow-wrap: anywhere;
  font-size: 14px;
  line-height: 1.6;
  color: #334155;
}

.progress-ring {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 108px;
  height: 108px;
  background:
    radial-gradient(circle at center, #fff 58%, transparent 59%),
    conic-gradient(#1677ff var(--progress), #e2e8f0 0);
  border-radius: 50%;
}

.progress-ring strong {
  font-size: 24px;
  line-height: 1;
  color: #111827;
}

.progress-ring span {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  align-items: stretch;
}

.metric-item {
  min-width: 0;
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.metric-item span,
.metric-item strong {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-item span {
  margin-bottom: 6px;
  font-size: 12px;
  color: #64748b;
}

.metric-item strong {
  font-size: 15px;
  color: #172033;
}

.pipeline-timeline {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.pipeline-step {
  position: relative;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  min-width: 0;
  padding: 14px;
  background: #fff;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}

.pipeline-step--running {
  border-color: #91caff;
  box-shadow: 0 0 0 2px rgb(22 119 255 / 8%);
}

.pipeline-step--done .pipeline-index {
  color: #fff;
  background: #0f9f6e;
}

.pipeline-step--running .pipeline-index {
  color: #fff;
  background: #1677ff;
}

.pipeline-step--error .pipeline-index {
  color: #fff;
  background: #dc2626;
}

.pipeline-index {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  font-weight: 700;
  color: #475569;
  background: #f1f5f9;
  border-radius: 50%;
}

.pipeline-step-copy {
  min-width: 0;
}

.pipeline-step-head {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
}

.pipeline-step-head strong {
  min-width: 0;
  overflow: hidden;
  font-size: 14px;
  color: #111827;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pipeline-step-copy p {
  display: -webkit-box;
  min-height: 38px;
  margin: 8px 0 6px;
  overflow: hidden;
  font-size: 12px;
  line-height: 1.55;
  color: #475569;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.pipeline-step-copy small {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: #64748b;
}

.pipeline-step-copy code {
  display: block;
  min-width: 0;
  overflow: hidden;
  font-size: 12px;
  color: #0b5cad;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: #eef6ff;
  border-radius: 4px;
}

.summary-strip {
  display: grid;
  grid-template-columns: 150px 150px 150px minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}

.summary-item,
.summary-rule {
  min-width: 0;
  padding: 14px 16px;
  background: #fff;
}

.summary-item + .summary-item,
.summary-rule {
  border-left: 1px solid var(--ant-color-border-secondary);
}

.summary-item span,
.summary-rule span,
.panel-kicker {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  color: #64748b;
}

.summary-item strong {
  font-size: 26px;
  line-height: 1;
  color: #111827;
}

.summary-rule p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  font-size: 13px;
  line-height: 1.55;
  color: #253044;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.observe-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
  gap: 16px;
}

.live-log-panel,
.discovery-panel,
.insight-panel,
.slice-panel,
.rule-panel,
.technical-log-panel {
  min-width: 0;
  padding: 16px;
  background: #fff;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}

.panel-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.panel-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.live-log {
  height: 360px;
  padding: 10px 0;
  overflow: auto;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 12px;
  line-height: 1.6;
  background: #fbfdff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.technical-log {
  max-height: 360px;
  padding: 10px 0;
  overflow: auto;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 12px;
  line-height: 1.6;
  background: #fbfdff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.log-line {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  min-height: 26px;
  padding: 3px 12px;
  color: #334155;
}

.log-line--summary {
  color: #0b5cad;
  background: #eef6ff;
}

.log-line--function,
.log-line--slice {
  color: #0f766e;
  background: #f0fdfa;
}

.log-line--path {
  color: #7c3aed;
  background: #f8f5ff;
}

.log-line--error {
  color: #dc2626;
  background: #fff5f5;
}

.log-line--noise {
  color: #94a3b8;
}

.log-time {
  flex: 0 0 70px;
  color: #64748b;
  user-select: none;
}

.log-chip {
  flex: 0 0 auto;
  max-width: 130px;
  padding: 0 6px;
  overflow: hidden;
  color: #475569;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: #eef2f7;
  border-radius: 4px;
}

.log-chip--source {
  color: #0b5cad;
  background: #e8f2ff;
}

.log-text {
  min-width: 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.log-empty {
  padding: 14px;
  color: #64748b;
}

.insight-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.insight-item {
  min-width: 0;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.insight-item--function,
.insight-item--slice {
  background: #f0fdfa;
  border-color: #99f6e4;
}

.insight-item--path {
  background: #f8f5ff;
  border-color: #ddd6fe;
}

.insight-item span,
.insight-item strong {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.insight-item span {
  margin-bottom: 4px;
  font-size: 12px;
  color: #64748b;
}

.insight-item strong {
  font-size: 13px;
  color: #111827;
}

.insight-item p {
  display: -webkit-box;
  margin: 8px 0 0;
  overflow: hidden;
  font-size: 13px;
  line-height: 1.5;
  color: #334155;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.technical-log-head {
  align-items: center;
}

.technical-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.log-filter {
  height: 24px;
  max-width: 150px;
  padding: 0 8px;
  font-size: 12px;
  color: #334155;
  background: #fff;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
}

.technical-note {
  margin-bottom: 10px;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.function-list {
  display: flex;
  max-height: 360px;
  overflow: auto;
  flex-direction: column;
  gap: 8px;
}

.function-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  width: 100%;
  min-height: 58px;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.function-item:hover,
.function-item--active {
  background: #f7fbff;
  border-color: #91caff;
}

.function-main {
  min-width: 0;
}

.function-main strong,
.function-main small {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.function-main strong {
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 13px;
  color: #111827;
}

.function-main small {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.slice-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #475569;
}

.slice-meta div {
  min-width: 0;
}

.slice-meta code {
  margin-left: 6px;
  color: #172033;
  overflow-wrap: anywhere;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
}

.code-window {
  max-height: 360px;
  padding: 10px 0;
  overflow: auto;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 13px;
  line-height: 1.65;
  color: #334155;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.code-row {
  display: grid;
  grid-template-columns: 62px minmax(0, 1fr);
  min-height: 28px;
  padding: 0 14px;
}

.code-row--emphasis {
  color: #0b5cad;
  background: #e8f2ff;
}

.line-no {
  color: #94a3b8;
  user-select: none;
}

.line-text {
  min-width: 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.rule-panel {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.rule-title {
  display: flex;
  gap: 8px;
  align-items: center;
  font-weight: 700;
  color: #172033;
}

.rule-title :first-child {
  color: #1677ff;
}

.rule-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
  font-size: 13px;
}

.rule-list > div {
  min-width: 0;
}

.rule-list dt {
  margin-bottom: 4px;
  color: #64748b;
}

.rule-list dd {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
  color: #172033;
}

.verdict-section {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 18px;
  margin-top: 18px;
}

.verdict-summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.verdict-stat {
  display: grid;
  grid-template-columns: 22px 1fr auto;
  gap: 8px;
  align-items: center;
  min-height: 48px;
  padding: 10px 12px;
  border-radius: 8px;
}

.verdict-stat--ok {
  color: #0f9f6e;
  background: #f0fdf4;
}

.verdict-stat--warn {
  color: #d97706;
  background: #fffaf0;
}

.verdict-stat--error {
  color: #dc2626;
  background: #fff5f5;
}

.verdict-stat strong {
  font-size: 20px;
}

.verdict-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.verdict-item {
  min-width: 0;
  padding: 14px;
  background: #fff;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}

.verdict-head {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}

.verdict-head code {
  min-width: 0;
  overflow: hidden;
  color: #334155;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: #f8fafc;
  border-radius: 4px;
}

.verdict-item p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #334155;
}

.verdict-item .recommendation {
  margin-top: 8px;
  color: #0b5cad;
}

@media (max-width: 1280px) {
  .pipeline-dashboard,
  .pipeline-timeline {
    grid-template-columns: 1fr;
  }

  .metric-grid,
  .insight-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .summary-strip {
    grid-template-columns: repeat(3, minmax(120px, 1fr));
  }

  .summary-rule {
    grid-column: 1 / -1;
    border-top: 1px solid var(--ant-color-border-secondary);
    border-left: 0;
  }

  .observe-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .summary-strip,
  .metric-grid,
  .pipeline-overview,
  .verdict-section,
  .verdict-list,
  .insight-list,
  .rule-panel,
  .rule-list {
    grid-template-columns: 1fr;
  }

  .progress-ring {
    justify-self: start;
  }

  .technical-log-head {
    align-items: flex-start;
  }

  .technical-actions {
    justify-content: flex-start;
    width: 100%;
  }

  .summary-item + .summary-item,
  .summary-rule {
    border-top: 1px solid var(--ant-color-border-secondary);
    border-left: 0;
  }

  .log-line {
    flex-wrap: wrap;
  }

  .log-text {
    flex-basis: 100%;
  }
}
</style>
