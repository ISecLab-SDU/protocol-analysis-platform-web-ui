<script setup lang="ts">
import type { CodeLocateEvidence, CodeLocateFunctionSlice } from '../types';

import type {
  ProtocolExtractRuleItem,
  ProtocolStaticAnalysisResult,
} from '#/api/protocol-compliance';

import { computed } from 'vue';

import { IconifyIcon } from '@vben/icons';

import { Card, Empty, Tag } from 'ant-design-vue';

import StageLiveLogPanel from './StageLiveLogPanel.vue';

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
  kind: 'function' | 'normal' | 'path' | 'slice' | 'summary';
  phase: string;
  source: string;
  stage: string;
  text: string;
  time: string;
}

interface LocateProgressStep {
  description: string;
  key: string;
  label: string;
  match: (line: LogLine) => boolean;
}

const props = defineProps<Props>();

const fallbackLogTimes = new Map<string, string>();

const verdicts = computed(() => props.result?.modelResponse?.verdicts ?? []);
const summary = computed(() => props.result?.modelResponse?.summary ?? null);

const primaryVerdict = computed(() => {
  return (
    verdicts.value.find((verdict) => verdict.compliance === 'non_compliant') ??
    verdicts.value.find((verdict) => verdict.compliance === 'needs_review') ??
    verdicts.value[0] ??
    null
  );
});

const showFinalFinding = computed(() =>
  Boolean(props.result && !props.running),
);

const ruleId = computed(() => {
  const optionId = (props.rule as null | { id?: string })?.id;
  return (
    primaryVerdict.value?.relatedRule?.id ||
    optionId ||
    ruleText.value.match(/\[(MQTT-[^\]]+)\]/i)?.[1] ||
    '当前规则'
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

const violationReason = computed(() => {
  return (
    props.evidence?.violationReason ||
    primaryVerdict.value?.explanation ||
    summary.value?.notes ||
    '等待静态分析返回违规原因'
  );
});

const targetFile = computed(() => {
  return (
    props.evidence?.targetFile ||
    primaryVerdict.value?.location?.file ||
    props.result?.inputs?.codeFileName ||
    '待定位'
  );
});

const functionRecords = computed<CodeLocateFunctionSlice[]>(() => {
  const evidenceFunctions =
    props.evidence?.functions?.filter((fn) => fn.name.trim()) ?? [];
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

const evidenceFunctionSlices = computed(() => {
  return functionRecords.value.filter((fn) => fn.codeRows.length > 0);
});

const stageStateText = computed(() => {
  if (props.running) return '进行中';
  if (props.result || props.evidence) return '已完成';
  return '等待中';
});

const rawLogLines = computed(() => {
  const rawLines = props.logText
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.trim().length > 0);
  return rawLines
    .map((line, index) => parseLogLine(line, index))
    .filter((line) => !isWaitingLogLine(line));
});

const logLines = computed<LogLine[]>(() => {
  let currentStepIndex = -1;
  const lines: LogLine[] = [];
  for (const line of rawLogLines.value) {
    const matchedStepIndex = findLocateProgressStepIndex(
      line,
      currentStepIndex + 1,
    );
    if (matchedStepIndex >= 0) currentStepIndex = matchedStepIndex;
    if (currentStepIndex < 0) continue;
    const currentStep = locateProgressSteps[currentStepIndex]!;
    lines.push({
      ...line,
      phase: currentStep.label,
    });
  }
  return lines;
});

const locateProgressSteps: LocateProgressStep[] = [
  {
    description: '保存上传的源码、规则和配置，准备工作目录。',
    key: 'inputs',
    label: '输入与工作区准备',
    match: (line) =>
      line.stage === 'init' && hasLogText(line, 'Preparing analysis inputs'),
  },
  {
    description: '根据上传的 Dockerfile 构建 builder 镜像。',
    key: 'builder-image',
    label: 'Builder 镜像构建',
    match: (line) =>
      line.stage === 'builder' &&
      hasLogText(line, 'Building builder image from uploaded Dockerfile'),
  },
  {
    description: '运行 builder 容器，配置项目并抽取 LLVM bitcode。',
    key: 'builder-run',
    label: '项目编译与 LLVM 中间表示提取',
    match: (line) =>
      line.stage === 'builder' &&
      (hasLogText(line, 'Running builder container image') ||
        hasLogText(line, 'Starting builder container')),
  },
  {
    description: '检查 program.bc、build_log.txt 等静态分析必需产物。',
    key: 'validation',
    label: '分析产物校验',
    match: (line) =>
      line.stage === 'validation' &&
      hasLogText(line, 'Validating required artefacts exist before analysis'),
  },
  {
    description: '启动 ProtocolGuard 静态分析容器并挂载工作区。',
    key: 'analysis-start',
    label: '启动分析容器',
    match: (line) =>
      line.stage === 'analysis' &&
      (hasLogText(line, 'Launching analysis container image') ||
        hasLogText(line, 'Starting analysis container')),
  },
  {
    description: '执行 LLVM SSA 化、SVF 指针分析和 AST 提取。',
    key: 'preprocess',
    label: 'IR/SVF/AST 预处理',
    match: (line) =>
      hasLogText(line, 'Running mem2reg/loop-mssa preprocessing'),
  },
  {
    description: '生成包相关调用图，定位协议消息入口函数。',
    key: 'callgraph',
    label: '调用图与入口函数定位',
    match: (line) =>
      hasLogText(
        line,
        'Generating packet-related call graph and function summaries',
      ),
  },
  {
    description: '通过 LLM 判断消息处理入口和通用接收函数。',
    key: 'entry-relevance',
    label: '消息入口相关性分析',
    match: (line) =>
      hasLogText(line, 'Collect LLM responses for message handler relevant') ||
      hasLogText(line, 'Collect LLM responses for general receive function'),
  },
  {
    description: '抽取请求字段变量、IR 指令和候选相关函数。',
    key: 'field-analysis',
    label: '字段变量与相关函数分析',
    match: (line) =>
      /Extracted \d+ functions that are related to the message/i.test(
        line.text,
      ) || hasLogText(line, 'Collect LLM responses for request field variable'),
  },
  {
    description: '判断函数是否与当前规则相关，筛出需要补全的函数。',
    key: 'function-relevance',
    label: '函数规则相关性分析',
    match: (line) =>
      hasLogText(line, 'Collect LLM responses for function rule relevant'),
  },
  {
    description: '补全相关函数源码，生成最终代码切片证据。',
    key: 'code-slice',
    label: '相关代码定位',
    match: (line) =>
      hasLogText(line, 'Collect LLM responses for complete code'),
  },
  {
    description: '根据规则与代码证据执行违规一致性分析。',
    key: 'inconsistency',
    label: '违规一致性分析',
    match: (line) => hasLogText(line, 'Starting inconsistency analysis'),
  },
  {
    description: '复制输出、清理日志并收集分析结果。',
    key: 'results',
    label: '结果归档',
    match: (line) =>
      hasLogText(line, 'Copying analysis artifacts to /out') ||
      hasLogText(line, 'Collecting analysis results and metadata'),
  },
  {
    description: '静态分析任务已完成。',
    key: 'completed',
    label: '完成',
    match: (line) =>
      line.stage === 'completed' ||
      hasLogText(line, 'ProtocolGuard job completed successfully') ||
      hasLogText(line, 'Static analysis completed successfully'),
  },
];

const locateProgress = computed(() => {
  const finished =
    Boolean(props.result) || (!props.running && Boolean(props.evidence));
  if (finished) {
    return {
      current: locateProgressSteps[locateProgressSteps.length - 1]!,
    };
  }

  const latestLine = logLines.value[logLines.value.length - 1];
  const currentStep = latestLine
    ? locateProgressSteps.find((step) => step.label === latestLine.phase)
    : null;

  if (!currentStep) {
    return {
      current: {
        description: props.running
          ? '正在等待阶段起始日志。'
          : '尚未开始代码定位。',
        key: 'waiting',
        label: props.running ? '等待阶段日志' : '未开始',
      },
    };
  }

  return {
    current: currentStep,
  };
});

const displayLogLines = computed(() => {
  return logLines.value.map((line) => ({
    ...line,
    time: getDisplayLogTime(line),
  }));
});

const hasContent = computed(() => {
  return Boolean(
    props.logText ||
      props.logHtml ||
      props.running ||
      props.result ||
      props.evidence,
  );
});

function parseLogLine(raw: string, index: number): LogLine {
  let rest = raw.trim();
  let stage = '';
  let time = '';
  let source = '';

  const leadingStage = consumeDelimitedPrefix(rest, '(', ')');
  if (leadingStage) {
    stage = leadingStage.value;
    rest = leadingStage.rest;
  }

  const timeMatch = consumeTimestampPrefix(rest);
  if (timeMatch) {
    time = timeMatch.value;
    rest = timeMatch.rest;
  }

  const inlineStage = consumeDelimitedPrefix(rest, '(', ')');
  if (inlineStage) {
    stage = stage || inlineStage.value;
    rest = inlineStage.rest;
  }

  if (!/^(?:Function|Path|func):|\d+\s+/.test(rest)) {
    const sourcePrefix = consumeSourcePrefix(rest);
    if (sourcePrefix) {
      source = sourcePrefix.value;
      rest = sourcePrefix.rest;
    }
  }

  return {
    id: `${index}-${raw}`,
    kind: classifyLogLine(rest),
    phase: '',
    source,
    stage,
    text: rest || raw,
    time,
  };
}

function consumeDelimitedPrefix(text: string, open: string, close: string) {
  if (!text.startsWith(open)) return null;
  const endIndex = text.indexOf(close, open.length);
  if (endIndex === -1) return null;
  return {
    rest: text.slice(endIndex + close.length).trimStart(),
    value: text.slice(open.length, endIndex),
  };
}

function consumeTimestampPrefix(text: string) {
  const prefix = consumeDelimitedPrefix(text, '[', ']');
  if (!prefix || !isTimestampValue(prefix.value)) return null;
  return prefix;
}

function isTimestampValue(value: string) {
  return (
    /^\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?$/i.test(value) ||
    /^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}/.test(value)
  );
}

function consumeSourcePrefix(text: string) {
  const firstColonIndex = text.indexOf(':');
  if (firstColonIndex <= 0) return null;

  const firstWhitespaceIndex = text.search(/\s/);
  const secondColonIndex = text.indexOf(':', firstColonIndex + 1);
  const delimiterIndex =
    secondColonIndex > 0 &&
    (firstWhitespaceIndex === -1 || secondColonIndex < firstWhitespaceIndex)
      ? secondColonIndex
      : firstColonIndex;
  const value = text.slice(0, delimiterIndex);
  if (/\s/.test(value)) return null;

  return {
    rest: text.slice(delimiterIndex + 1).trimStart(),
    value,
  };
}

function formatCurrentTime() {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}

function getDisplayLogTime(line: LogLine) {
  if (line.time) return line.time;
  const cachedTime = fallbackLogTimes.get(line.id);
  if (cachedTime) return cachedTime;
  const nextTime = formatCurrentTime();
  fallbackLogTimes.set(line.id, nextTime);
  return nextTime;
}

function classifyLogLine(text: string): LogLine['kind'] {
  if (/Extracted\s+\d+\s+functions/i.test(text)) return 'summary';
  if (/^func:/i.test(text)) return 'function';
  if (/^Function:/i.test(text)) return 'slice';
  if (/^Path:/i.test(text)) return 'path';
  return 'normal';
}

function findLocateProgressStepIndex(line: LogLine, startIndex: number) {
  return locateProgressSteps.findIndex((step, index) => {
    return index >= startIndex && step.match(line);
  });
}

function hasLogText(line: LogLine, text: string) {
  return line.text.includes(text);
}

function isWaitingLogLine(line: LogLine) {
  return line.stage === 'queued' || line.text === 'Job queued';
}

function formatEvidencePath(fn: CodeLocateFunctionSlice) {
  const path = fn.path || targetFile.value;
  if (!fn.targetLine || fn.targetLine === '-') return path;
  return `${path}:${fn.targetLine}`;
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
      <section v-if="showFinalFinding" class="result-hero">
        <div class="result-body">
          <div class="finding-grid">
            <section class="finding-block finding-block--rule">
              <div class="finding-label">
                <IconifyIcon icon="mdi:clipboard-check-outline" />
                <span>检测规则对象</span>
              </div>
              <h3>{{ ruleId }}</h3>
              <p>{{ ruleText }}</p>
            </section>

            <section class="finding-block finding-block--reason">
              <div class="finding-label">
                <IconifyIcon icon="mdi:alert-circle-outline" />
                <span>违规原因</span>
              </div>
              <p>{{ violationReason }}</p>
            </section>
          </div>
        </div>
      </section>

      <section class="observe-grid">
        <StageLiveLogPanel
          :lines="displayLogLines"
          :progress="locateProgress.current"
          :running="running"
        />

        <section class="discovery-panel">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">代码定位结果</span>
              <h3>相关函数源码</h3>
            </div>
            <Tag color="blue">{{ evidenceFunctionSlices.length }} 个函数</Tag>
          </div>

          <div
            v-if="evidenceFunctionSlices.length > 0"
            class="function-source-frame"
          >
            <section
              v-for="fn in evidenceFunctionSlices"
              :key="fn.name"
              class="function-source-section"
            >
              <div class="function-source-head">
                <strong>{{ fn.name }}</strong>
                <code>{{ formatEvidencePath(fn) }}</code>
              </div>
              <div class="function-source-code">
                <div
                  v-for="(row, idx) in fn.codeRows"
                  :key="`${fn.name}-${row.line}-${idx}`"
                  class="code-row"
                  :class="{ 'code-row--emphasis': row.emphasis }"
                >
                  <span class="line-no">{{ row.line }}</span>
                  <span class="line-text">{{ row.text }}</span>
                </div>
              </div>
            </section>
          </div>
          <Empty
            v-else
            description="等待生成相关函数源码"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
          />
        </section>
      </section>
    </div>

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
  font-size: 18px;
  font-weight: 700;
}

.stage-title :first-child {
  color: #1677ff;
}

.stage-title small {
  font-size: 14px;
  font-weight: 500;
  color: var(--ant-color-text-secondary);
}

.locate-workspace {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-hero {
  padding: 18px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-left: 4px solid #f59e0b;
  border-radius: 8px;
  box-shadow: 0 12px 30px rgb(15 23 42 / 6%);
}

.finding-label {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #64748b;
}

.result-body {
  min-width: 0;
}

.finding-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 12px;
}

.finding-block {
  min-width: 0;
  padding: 14px;
  background: #fbfdff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.finding-label :first-child {
  font-size: 16px;
  color: #1677ff;
}

.finding-block--reason .finding-label :first-child {
  color: #ef4444;
}

.finding-block h3 {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 800;
  color: #111827;
  overflow-wrap: anywhere;
}

.finding-block p {
  margin: 0;
  font-size: 15px;
  line-height: 1.65;
  color: #253044;
  overflow-wrap: anywhere;
}

.panel-kicker {
  display: block;
  margin-bottom: 4px;
  font-size: 14px;
  font-weight: 700;
  color: #64748b;
}

.observe-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
  gap: 16px;
}

.discovery-panel {
  min-width: 0;
  padding: 18px;
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
  font-size: 17px;
  font-weight: 800;
  color: #111827;
}

.stage-card :deep(.ant-tag) {
  padding: 1px 8px;
  font-size: 14px;
  line-height: 24px;
  border-radius: 6px;
}

.stage-card :deep(.ant-empty-description) {
  font-size: 14px;
}

.function-source-frame {
  min-width: 0;
  height: 440px;
  overflow: hidden;
  overflow-y: auto;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.function-source-section + .function-source-section {
  border-top: 1px solid #dbe4ef;
}

.function-source-head {
  display: grid;
  grid-template-columns: minmax(140px, 0.36fr) minmax(0, 0.64fr);
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 13px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.function-source-head strong,
.function-source-head code {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.function-source-head strong {
  color: #111827;
}

.function-source-head code {
  color: #64748b;
  background: transparent;
}

.function-source-code {
  padding: 10px 0;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 14px;
  line-height: 1.7;
  color: #334155;
  background: #fff;
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

@media (max-width: 1280px) {
  .finding-grid {
    grid-template-columns: 1fr;
  }

  .observe-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .function-source-head {
    grid-template-columns: 1fr;
  }
}
</style>
