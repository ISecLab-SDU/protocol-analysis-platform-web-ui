<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import { Card, Empty, Tag } from 'ant-design-vue';
import { IconifyIcon } from '@vben/icons';

import type { ProtocolAssertGenerationResult } from '#/api/protocol-compliance';

interface Props {
  logText: string;
  diffContent: string;
  result: ProtocolAssertGenerationResult | null;
  running: boolean;
}

interface AssertLogLine {
  id: string;
  kind: 'code' | 'diff' | 'normal' | 'success' | 'summary' | 'task';
  phase: string;
  source: string;
  stage: string;
  text: string;
  time: string;
}

interface AssertProgressStep {
  description: string;
  key: string;
  label: string;
  match: (line: AssertLogLine) => boolean;
}

interface RenderedDiffLine {
  id: string;
  text: string;
  type: 'add' | 'context' | 'delete' | 'file' | 'hunk' | 'meta';
}

const props = defineProps<Props>();

const logBodyRef = ref<HTMLElement | null>(null);

const stageStateText = computed(() => {
  if (props.running) return '进行中';
  if (props.result) return '已完成';
  return '等待中';
});

const rawLogLines = computed(() => {
  const lines = props.logText
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.trim().length > 0)
    .map(parseLogLine)
    .filter((line) => !isWaitingLogLine(line));

  return stripInlineDiffPayload(lines);
});

const logLines = computed<AssertLogLine[]>(() => {
  let currentStepIndex = -1;
  const lines: AssertLogLine[] = [];
  for (const line of rawLogLines.value) {
    const matchedStepIndex = findAssertProgressStepIndex(line, currentStepIndex + 1);
    if (matchedStepIndex >= 0) currentStepIndex = matchedStepIndex;
    if (currentStepIndex < 0) continue;
    const currentStep = assertProgressSteps[currentStepIndex]!;
    lines.push({
      ...line,
      phase: currentStep.label,
    });
  }
  return lines;
});

const assertProgress = computed(() => {
  const finished = Boolean(props.result) && !props.running;
  if (finished) {
    return {
      current: assertProgressSteps[assertProgressSteps.length - 1]!,
    };
  }

  const latestLine = logLines.value[logLines.value.length - 1];
  const currentStep = latestLine
    ? assertProgressSteps.find((step) => step.label === latestLine.phase)
    : null;

  if (!currentStep) {
    return {
      current: {
        description: props.running ? '正在等待断言生成阶段起始日志。' : '尚未开始断言生成。',
        key: 'waiting',
        label: props.running ? '等待阶段日志' : '未开始',
      },
    };
  }

  return {
    current: currentStep,
  };
});

const hasContent = computed(() => {
  return Boolean(props.logText || props.diffContent || props.running || props.result);
});

const effectiveDiffContent = computed(() => {
  const rawContent =
    props.diffContent ||
    props.result?.instrumentation?.artifacts?.diffOutput?.content ||
    extractDiffContentFromLog(props.logText);

  return normalizeDiffContent(rawContent);
});

const modifiedFileCount = computed(() => {
  const matches = effectiveDiffContent.value.match(/^diff --git\s+/gm);
  return matches?.length ?? 0;
});

const renderedDiffLines = computed<RenderedDiffLine[]>(() => {
  return effectiveDiffContent.value.split(/\r?\n/).map((text, index) => ({
    id: `${index}-${text}`,
    text,
    type: classifyDiffLine(text),
  }));
});

const assertProgressSteps: AssertProgressStep[] = [
  {
    description: '任务进入队列，后端准备接收源码包、违规数据库和编译指令。',
    key: 'inputs',
    label: '输入接收',
    match: (line) =>
      (line.stage === 'init' && hasLogText(line, 'Preparing assertion generation inputs')) ||
      line.stage === 'inputs',
  },
  {
    description: '创建工作目录，解压源码，挂载 SQLite 违规数据库并写入构建说明。',
    key: 'workspace',
    label: '工作区准备',
    match: (line) =>
      line.stage === 'workspace' ||
      (line.stage === 'workspace-snapshot' && hasLogText(line, 'prepared')),
  },
  {
    description: '启动 ProtocolGuard 断言生成容器，并检查容器内工作区挂载状态。',
    key: 'container-start',
    label: '断言容器启动',
    match: (line) =>
      (line.stage === 'analysis' &&
        (hasLogText(line, 'Launching assertion generation container') ||
          hasLogText(line, 'Starting analysis container'))) ||
      line.stage === 'analysis-debug' ||
      line.stage === 'container',
  },
  {
    description: '在容器内创建 Python 运行环境，构建并安装 assert-generate 工具。',
    key: 'generator-env',
    label: '生成器环境初始化',
    match: (line) =>
      line.stage === 'container-log' &&
      (hasLogText(line, 'Running assertion generation') ||
        hasLogText(line, 'Creating virtual environment') ||
        hasLogText(line, 'Building assert-generate') ||
        hasLogText(line, 'Installed')),
  },
  {
    description: '读取 violations.db 中的违规记录，提取相关函数源码和 AST 上下文。',
    key: 'violation-read',
    label: '违规记录解析',
    match: (line) =>
      line.stage === 'container-log' &&
      (hasLogText(line, 'Reading records from database') ||
        hasLogText(line, 'Reading complete') ||
        hasLogText(line, 'Extracting source code for') ||
        hasLogText(line, 'Processing file:')),
  },
  {
    description: '把规则、违规原因和目标函数上下文写成断言插桩任务 prompt。',
    key: 'task-prompt',
    label: '断言任务生成',
    match: (line) =>
      line.stage === 'container-log' &&
      (hasLogText(line, 'Prompt saved to') ||
        hasLogText(line, 'Processing complete') ||
        hasLogText(line, 'Task list updated') ||
        hasLogText(line, 'Copying assertion tasks')),
  },
  {
    description: '打包断言任务产物并保存运行前后的工作区快照。',
    key: 'assert-results',
    label: '任务产物归档',
    match: (line) =>
      line.stage === 'results' ||
      (line.stage === 'workspace-snapshot' &&
        (hasLogText(line, 'main') || hasLogText(line, 'post-run'))) ||
      (line.stage === 'analysis' &&
        hasLogText(line, 'Assertion generation container completed successfully')),
  },
  {
    description: '准备插桩容器和 Claude 运行配置，加载上一阶段生成的断言任务。',
    key: 'instrumentation-start',
    label: '插桩环境准备',
    match: (line) =>
      line.stage === 'instrumentation' ||
      (line.stage === 'instrumentation-log' &&
        (hasLogText(line, 'Writing Claude settings') ||
          hasLogText(line, 'Loading state from previous assert command') ||
          hasLogText(line, 'Running assertion instrumentation'))),
  },
  {
    description: '初始化临时 Git 仓库，记录插桩前代码基线用于后续 diff 生成。',
    key: 'baseline',
    label: '代码基线捕获',
    match: (line) =>
      line.stage === 'instrumentation-log' &&
      (hasLogText(line, 'Capturing initial codebase state') ||
        hasLogText(line, 'Running git init') ||
        hasLogText(line, 'Initial commit')),
  },
  {
    description: '逐个读取任务 prompt，调用 Claude CLI 将断言辅助函数和 assert 插入源码。',
    key: 'claude-instrumentation',
    label: 'LLM 断言插桩',
    match: (line) =>
      line.stage === 'instrumentation-log' &&
      (hasLogText(line, 'Task 1/') ||
        hasLogText(line, 'Reading prompt from') ||
        hasLogText(line, 'Executing Claude CLI') ||
        hasLogText(line, 'All three changes are in place') ||
        hasLogText(line, '#include <assert.h>') ||
        hasLogText(line, 'assert_related_rule')),
  },
  {
    description: '捕获插桩后的代码状态，生成变更提交和 instrumentation.diff。',
    key: 'diff',
    label: '插桩差异生成',
    match: (line) =>
      line.stage === 'instrumentation-log' &&
      (hasLogText(line, 'Capturing final codebase state') ||
        hasLogText(line, 'Detected') ||
        hasLogText(line, 'Diff saved to') ||
        hasLogText(line, 'CODEBASE CHANGES') ||
        hasLogText(line, 'DIFF OUTPUT') ||
        line.text.startsWith('diff --git')),
  },
  {
    description: '复制插桩结果，确认断言生成与插桩流程全部完成。',
    key: 'completed',
    label: '完成',
    match: (line) =>
      line.stage === 'completed' ||
      (line.stage === 'instrumentation-log' &&
        hasLogText(line, 'Instrumentation completed')),
  },
];

watch(
  () => props.logText,
  async () => {
    await nextTick();
    const target = logBodyRef.value;
    if (!target) return;
    target.scrollTop = target.scrollHeight;
  },
);

function parseLogLine(raw: string, index: number): AssertLogLine {
  let rest = raw.trim();
  let stage = '';
  let time = '';
  let source = '';

  const timeMatch = rest.match(/^\[([^\]]+)\]\s*(.*)$/);
  if (timeMatch?.[1]) {
    time = timeMatch[1];
    rest = timeMatch[2] ?? '';
  }

  const stageMatch = rest.match(/^\(([^)]+)\)\s*(.*)$/);
  if (stageMatch?.[1]) {
    stage = stageMatch[1];
    rest = stageMatch[2] ?? '';
  }

  const sourceMatch = rest.match(/^([^\s:]+(?::[^\s:]+)?):\s*(.*)$/);
  if (sourceMatch?.[1] && shouldExtractSource(rest)) {
    source = sourceMatch[1];
    rest = sourceMatch[2] ?? '';
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

function shouldExtractSource(text: string) {
  return (
    !text.startsWith('INFO:') &&
    !text.startsWith('ERROR:') &&
    !text.startsWith('WARNING:') &&
    !text.startsWith('✓') &&
    !text.startsWith('diff --git') &&
    !/^[+-]{3}\s/.test(text) &&
    !/^@@\s/.test(text)
  );
}

function classifyLogLine(text: string): AssertLogLine['kind'] {
  if (/✓|completed successfully|Success rate/i.test(text)) return 'success';
  if (/Task \d+\/\d+|Prompt saved|Reading prompt/i.test(text)) return 'task';
  if (/EXECUTION SUMMARY|CODEBASE CHANGES|Change Summary|Total tasks/i.test(text)) {
    return 'summary';
  }
  if (/^(diff --git|index |@@ |\+|-{3} |\+{3} )/.test(text)) return 'diff';
  if (/^\s*(static int|#include|#ifdef|assert\(|\+?#include|\+?static int|\+?\s*assert\()/i.test(text)) {
    return 'code';
  }
  return 'normal';
}

function findAssertProgressStepIndex(line: AssertLogLine, startIndex: number) {
  return assertProgressSteps.findIndex((step, index) => {
    return index >= startIndex && step.match(line);
  });
}

function hasLogText(line: AssertLogLine, text: string) {
  return line.text.includes(text);
}

function isWaitingLogLine(line: AssertLogLine) {
  return line.stage === 'queued' || line.text === 'Job queued';
}

function stripInlineDiffPayload(lines: AssertLogLine[]) {
  let inDiffPayload = false;
  return lines.filter((line) => {
    if (line.text.startsWith('diff --git')) {
      inDiffPayload = true;
      return false;
    }

    if (!inDiffPayload) return true;

    if (isDiffPayloadTerminator(line)) {
      inDiffPayload = false;
      return true;
    }

    return false;
  });
}

function isDiffPayloadTerminator(line: AssertLogLine) {
  return (
    line.stage !== 'instrumentation-log' ||
    hasLogText(line, 'Instrumentation completed') ||
    hasLogText(line, 'Copying instrumentation results') ||
    hasLogText(line, 'Assertion generation flow completed')
  );
}

function extractDiffContentFromLog(logText: string) {
  const diffLines: string[] = [];
  let inDiffPayload = false;

  for (const rawLine of logText.split(/\r?\n/)) {
    if (!rawLine.trim()) {
      if (inDiffPayload) diffLines.push('');
      continue;
    }

    const line = parseLogLine(rawLine.trimEnd(), diffLines.length);
    if (line.text.startsWith('diff --git')) {
      inDiffPayload = true;
    }
    if (!inDiffPayload) continue;
    if (isDiffPayloadTerminator(line)) break;
    diffLines.push(line.text);
  }

  return diffLines.join('\n');
}

function normalizeDiffContent(content: string) {
  const normalized = content.trimEnd();
  const diffStartIndex = normalized.search(/^diff --git\s+/m);
  if (diffStartIndex >= 0) return normalized.slice(diffStartIndex).trimEnd();

  const detailedDiffMatch = normalized.match(/^Detailed Diff:\s*$/m);
  if (detailedDiffMatch?.index !== undefined) {
    return normalized.slice(detailedDiffMatch.index + detailedDiffMatch[0].length).trim();
  }

  return normalized;
}

function classifyDiffLine(text: string): RenderedDiffLine['type'] {
  if (text.startsWith('diff --git') || text.startsWith('index ')) return 'meta';
  if (text.startsWith('@@')) return 'hunk';
  if (text.startsWith('--- ') || text.startsWith('+++ ')) return 'file';
  if (text.startsWith('+')) return 'add';
  if (text.startsWith('-')) return 'delete';
  return 'context';
}
</script>

<template>
  <Card class="stage-card assert-stage" :bordered="false">
    <template #title>
      <div class="stage-title">
        <IconifyIcon icon="mdi:shield-plus-outline" />
        <span>断言生成</span>
        <small>{{ stageStateText }}</small>
      </div>
    </template>
    <template #extra>
      <Tag v-if="running" color="processing">进行中</Tag>
      <Tag v-else-if="result" color="success">已完成</Tag>
      <Tag v-else color="default">等待中</Tag>
    </template>

    <div v-if="hasContent" class="assert-container">
      <section class="assert-observe-grid">
        <section class="assert-log-panel">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">实时运行轨迹</span>
              <h3>日志输出</h3>
            </div>
            <Tag :color="running ? 'processing' : 'default'">
              {{ running ? '自动滚动' : `${logLines.length} 行` }}
            </Tag>
          </div>

          <div class="log-progress">
            <div class="log-progress-title">
              <span>当前阶段</span>
              <strong>{{ assertProgress.current.label }}</strong>
            </div>
            <p>{{ assertProgress.current.description }}</p>
          </div>

          <div ref="logBodyRef" class="live-log">
            <div
              v-for="line in logLines"
              :key="line.id"
              class="log-line"
              :class="`log-line--${line.kind}`"
            >
              <span class="log-time">{{ line.time || '--:--:--' }}</span>
              <span class="log-chip log-chip--phase">{{ line.phase }}</span>
              <span v-if="line.stage" class="log-chip">{{ line.stage }}</span>
              <span v-if="line.source" class="log-chip log-chip--source">{{ line.source }}</span>
              <span class="log-text">{{ line.text }}</span>
            </div>
            <div v-if="logLines.length === 0" class="log-empty">
              {{ running ? '等待日志输出...' : '暂无日志输出' }}
            </div>
          </div>
        </section>

        <section class="assert-diff">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">断言生成结果</span>
              <h3>插桩代码差异</h3>
            </div>
            <Tag color="blue">{{ modifiedFileCount }} 个文件</Tag>
          </div>

          <div v-if="effectiveDiffContent" class="diff-wrapper">
            <div
              v-for="line in renderedDiffLines"
              :key="line.id"
              class="diff-line"
              :class="`diff-line--${line.type}`"
            >
              <span class="diff-line-number">{{ line.text ? '' : ' ' }}</span>
              <code>{{ line.text || ' ' }}</code>
            </div>
          </div>
          <Empty
            v-else
            class="diff-empty"
            description="等待生成插桩差异"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
          />
        </section>
      </section>
    </div>

    <Empty v-else description="等待断言生成阶段开始" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
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

.assert-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.assert-observe-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
  gap: 16px;
}

.assert-log-panel,
.assert-diff {
  display: flex;
  flex-direction: column;
  gap: 12px;
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
}

.panel-head h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: #111827;
}

.panel-head > :last-child {
  flex: 0 0 auto;
  color: #1677ff;
}

.panel-kicker {
  display: block;
  margin-bottom: 4px;
  font-size: 13px;
  font-weight: 700;
  color: #64748b;
}

.stage-card :deep(.ant-tag) {
  padding: 1px 8px;
  font-size: 13px;
  line-height: 22px;
  border-radius: 6px;
}

.stage-card :deep(.ant-empty-description) {
  font-size: 14px;
}

.log-progress {
  padding: 12px;
  background: #f7fbff;
  border: 1px solid #d6e9ff;
  border-radius: 8px;
}

.log-progress-title {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: baseline;
}

.log-progress-title span {
  font-size: 13px;
  color: #64748b;
}

.log-progress-title strong {
  font-size: 15px;
  color: #0b5cad;
}

.log-progress p {
  margin: 4px 0 0;
  font-size: 14px;
  line-height: 1.5;
  color: #334155;
  overflow-wrap: anywhere;
}

.live-log {
  height: 360px;
  padding: 10px 0;
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #334155;
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

.log-line--success {
  color: #047857;
  background: #ecfdf5;
}

.log-line--summary {
  color: #0b5cad;
  background: #eef6ff;
}

.log-line--task {
  color: #7c3aed;
  background: #f8f5ff;
}

.log-line--code {
  color: #0f766e;
  background: #f0fdfa;
}

.log-line--diff {
  color: #9a3412;
  background: #fff7ed;
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

.log-chip--phase {
  max-width: 180px;
  font-weight: 700;
  color: #0b5cad;
  background: #e8f2ff;
}

.log-chip--source {
  color: #0b5cad;
  background: #e8f2ff;
}

.log-text {
  min-width: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.log-empty {
  padding: 14px;
  color: #64748b;
}

.diff-wrapper {
  height: 440px;
  min-width: 0;
  padding: 8px 0;
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #334155;
  background: #fbfdff;
  border: 1px solid var(--ant-color-border);
  border-radius: 8px;
}

.diff-line {
  display: grid;
  grid-template-columns: 18px minmax(max-content, 1fr);
  min-width: max-content;
  padding: 1px 12px;
  white-space: pre;
}

.diff-line code {
  padding: 0;
  color: inherit;
  white-space: pre;
  background: transparent;
}

.diff-line-number {
  color: #94a3b8;
  user-select: none;
}

.diff-line--meta {
  font-weight: 700;
  color: #334155;
  background: #f1f5f9;
}

.diff-line--file {
  color: #0f4c81;
  background: #eef6ff;
}

.diff-line--hunk {
  color: #6d28d9;
  background: #f5f3ff;
}

.diff-line--add {
  color: #047857;
  background: #ecfdf5;
}

.diff-line--delete {
  color: #b42318;
  background: #fff1f2;
}

.diff-line--context {
  color: #334155;
}

.diff-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 440px;
  margin: 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

@media (max-width: 960px) {
  .assert-observe-grid {
    grid-template-columns: 1fr;
  }

  .log-line {
    flex-wrap: wrap;
  }

  .log-text {
    flex-basis: 100%;
  }
}
</style>
