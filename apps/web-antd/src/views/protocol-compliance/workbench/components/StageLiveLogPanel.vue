<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';

import { Tag } from 'ant-design-vue';

interface StageLiveLogLine {
  id: string;
  kind?: string;
  metadata?: Record<string, any>;
  phase: string;
  stage?: string;
  text: string;
  time?: string;
}

interface StageLiveLogProgress {
  description: string;
  label: string;
}

interface Props {
  emptyIdleText?: string;
  emptyRunningText?: string;
  lines: StageLiveLogLine[];
  progress: StageLiveLogProgress;
  running: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  emptyIdleText: '暂无日志输出',
  emptyRunningText: '等待日志输出...',
});

const logBodyRef = ref<HTMLElement | null>(null);

const visibleLines = computed(() =>
  props.lines.filter(
    (line) =>
      !isAssistantTurnNoise(line) && !isSuccessfulToolResultUserMessage(line),
  ),
);

defineExpose({
  getAllLogText,
});

watch(
  () => props.lines,
  async () => {
    await nextTick();
    const target = logBodyRef.value;
    if (!target) return;
    target.scrollTop = target.scrollHeight;
  },
  { deep: true },
);

function getAllLogText() {
  return props.lines.map((line) => formatLogLineForCopy(line)).join('\n');
}

function formatLogLineForCopy(line: StageLiveLogLine) {
  const metaSegments = [line.time || '--:--:--', displayText(line.phase)]
    .filter(Boolean)
    .map((segment) => `[${segment}]`);
  return `${metaSegments.join(' ')} ${displayText(line.text)}`.trim();
}

function displayText(value: string) {
  return value.replaceAll(/claude/gi, 'Agent');
}

function isClaudeLine(line: StageLiveLogLine) {
  return line.stage?.startsWith('claude-');
}

function isAssistantTurnNoise(line: StageLiveLogLine) {
  return (
    line.stage === 'claude-status' &&
    line.metadata?.sdk_message_type === 'AssistantMessage'
  );
}

function isSuccessfulToolResultUserMessage(line: StageLiveLogLine) {
  if (!isToolResultUserMessage(line)) return false;
  return !isToolResultError(line);
}

function isToolResultUserMessage(line: StageLiveLogLine) {
  return (
    line.metadata?.sdk_message_type === 'UserMessage' ||
    line.text.trimStart().startsWith('UserMessage(content=[ToolResultBlock(')
  );
}

function isToolResultError(line: StageLiveLogLine) {
  return (
    line.metadata?.is_error === true ||
    line.text.includes('is_error=True') ||
    line.text.includes("tool_use_result='Error:")
  );
}

function isThinkingLine(line: StageLiveLogLine) {
  return (
    line.stage === 'claude-thinking' ||
    line.metadata?.sdk_message_type === 'ThinkingBlock' ||
    line.text.trimStart().startsWith('ThinkingBlock(thinking=')
  );
}

function claudeLineKind(line: StageLiveLogLine) {
  if (line.metadata?.is_error || line.metadata?.status === 'failed') {
    return 'error';
  }
  if (isToolResultError(line)) return 'error';
  if (isThinkingLine(line)) return 'thinking';
  if (line.metadata?.sdk_message_type === 'ResultMessage') return 'result';
  if (line.stage === 'claude-command') return 'command';
  if (line.stage === 'claude-inspect') return 'inspect';
  if (line.stage === 'claude-write') return 'write';
  if (line.stage === 'claude-message') return 'message';
  if (line.stage === 'claude-observation') return 'observation';
  return 'status';
}

function claudeIcon(line: StageLiveLogLine) {
  return {
    command: 'mdi:console-line',
    error: 'mdi:alert-circle-outline',
    inspect: 'mdi:file-search-outline',
    message: 'mdi:message-text-outline',
    observation: 'mdi:check-circle-outline',
    result: 'mdi:chart-box-outline',
    status: 'mdi:creation-outline',
    thinking: 'mdi:head-cog-outline',
    write: 'mdi:file-edit-outline',
  }[claudeLineKind(line)];
}

function claudeLabel(line: StageLiveLogLine) {
  const kind = claudeLineKind(line);
  if (kind === 'command') return '执行命令';
  if (kind === 'inspect') return '查看文件';
  if (kind === 'write') return '修改文件';
  if (kind === 'message') return 'Agent 回复';
  if (kind === 'thinking') return 'Agent 思考';
  if (kind === 'observation') return '工具结果';
  if (kind === 'result')
    return line.metadata?.status === 'failed' ? '运行失败' : '运行完成';
  if (kind === 'error') return '执行异常';
  return 'Agent 状态';
}

function claudePrimaryText(line: StageLiveLogLine) {
  if (isThinkingLine(line)) {
    return displayText(
      extractReprStringField(line.text, 'thinking') || line.text,
    );
  }
  if (isToolResultError(line)) {
    return displayText(
      extractReprStringField(line.text, 'content') || line.text,
    );
  }
  const input = line.metadata?.tool_input;
  if (line.metadata?.tool === 'Bash' && typeof input?.command === 'string') {
    return input.command;
  }
  if (typeof input?.file_path === 'string') return input.file_path;
  if (typeof input?.path === 'string') return input.path;
  return displayText(line.text.replace(/^[a-z]+:\s*/i, ''));
}

function extractReprStringField(text: string, field: string) {
  const marker = `${field}=`;
  const markerIndex = text.lastIndexOf(marker);
  if (markerIndex === -1) return '';
  const start = markerIndex + marker.length;
  const quote = text[start];
  if (quote !== "'" && quote !== '"') return '';

  let value = '';
  for (let index = start + 1; index < text.length; index += 1) {
    const character = text[index];
    if (character === quote) return value;
    if (character !== '\\') {
      value += character;
      continue;
    }
    const escaped = text[index + 1];
    if (escaped === undefined) break;
    value += { n: '\n', r: '\r', t: '\t' }[escaped] ?? escaped;
    index += 1;
  }
  const truncatedValue = value.trimEnd();
  if (!truncatedValue) return '';
  return truncatedValue.endsWith('...')
    ? truncatedValue
    : `${truncatedValue}...`;
}

function claudeDescription(line: StageLiveLogLine) {
  const description = line.metadata?.tool_input?.description;
  return typeof description === 'string' ? displayText(description) : '';
}

function resultMetrics(line: StageLiveLogLine) {
  const metadata = line.metadata ?? {};
  const usage = metadata.usage ?? {};
  const modelUsageEntries = Object.entries(metadata.model_usage ?? {});
  const modelUsage = modelUsageEntries[0]?.[1] as
    | Record<string, number>
    | undefined;
  const model = metadata.model ?? modelUsageEntries[0]?.[0];
  const metrics: Array<{ label: string; value: string }> = [];
  if (model) metrics.push({ label: '模型', value: displayText(model) });
  if (typeof metadata.duration_ms === 'number') {
    metrics.push({
      label: '耗时',
      value: formatDuration(metadata.duration_ms),
    });
  }
  if (typeof modelUsage?.costUSD === 'number') {
    metrics.push({ label: '费用', value: `$${modelUsage.costUSD.toFixed(4)}` });
  }
  if (typeof usage.input_tokens === 'number') {
    metrics.push({ label: '输入', value: formatCount(usage.input_tokens) });
  }
  if (typeof usage.output_tokens === 'number') {
    metrics.push({ label: '输出', value: formatCount(usage.output_tokens) });
  }
  if (typeof usage.cache_read_input_tokens === 'number') {
    metrics.push({
      label: '缓存命中',
      value: formatCount(usage.cache_read_input_tokens),
    });
  }
  return metrics;
}

function formatDuration(milliseconds: number) {
  if (milliseconds < 1000) return `${milliseconds} ms`;
  const seconds = Math.round(milliseconds / 1000);
  if (seconds < 60) return `${seconds} 秒`;
  return `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`;
}

function formatCount(value: number) {
  return new Intl.NumberFormat('zh-CN', { notation: 'compact' }).format(value);
}
</script>

<template>
  <section class="stage-live-log-panel">
    <div class="panel-head">
      <div>
        <span class="panel-kicker">实时运行轨迹</span>
        <h3>日志输出</h3>
      </div>
      <Tag :color="running ? 'processing' : 'default'">
        {{ running ? '自动滚动' : `${visibleLines.length} 行` }}
      </Tag>
    </div>

    <div class="log-progress">
      <div class="log-progress-title">
        <span>当前阶段</span>
        <strong>{{ displayText(progress.label) }}</strong>
      </div>
      <p>{{ displayText(progress.description) }}</p>
    </div>

    <div ref="logBodyRef" class="live-log">
      <div
        v-for="line in visibleLines"
        :key="line.id"
        class="log-line"
        :class="[
          line.kind ? `log-line--${line.kind}` : undefined,
          isClaudeLine(line)
            ? `claude-line claude-line--${claudeLineKind(line)}`
            : undefined,
        ]"
      >
        <template v-if="isClaudeLine(line)">
          <div class="claude-rail" aria-hidden="true">
            <IconifyIcon :icon="claudeIcon(line)" />
          </div>
          <div class="claude-event">
            <div class="claude-event-head">
              <strong>{{ claudeLabel(line) }}</strong>
              <span class="log-chip log-chip--phase">{{
                displayText(line.phase)
              }}</span>
              <span v-if="line.metadata?.tool" class="claude-tool">{{
                line.metadata.tool
              }}</span>
              <time>{{ line.time || '--:--:--' }}</time>
            </div>
            <p
              v-if="claudeLineKind(line) !== 'result'"
              class="claude-primary"
              :class="{
                'claude-primary--code': [
                  'command',
                  'inspect',
                  'write',
                ].includes(claudeLineKind(line)),
              }"
            >
              {{ claudePrimaryText(line) }}
            </p>
            <p v-if="claudeDescription(line)" class="claude-description">
              {{ claudeDescription(line) }}
            </p>
            <template v-if="claudeLineKind(line) === 'result'">
              <div class="claude-metrics">
                <div v-for="metric in resultMetrics(line)" :key="metric.label">
                  <span>{{ metric.label }}</span>
                  <strong>{{ metric.value }}</strong>
                </div>
              </div>
              <p v-if="line.metadata?.result" class="claude-result-text">
                {{ displayText(line.metadata.result) }}
              </p>
            </template>
          </div>
        </template>
        <template v-else>
          <span class="log-time">{{ line.time || '--:--:--' }}</span>
          <span class="log-chip log-chip--phase">{{
            displayText(line.phase)
          }}</span>
          <span class="log-text">{{ displayText(line.text) }}</span>
        </template>
      </div>
      <div v-if="visibleLines.length === 0" class="log-empty">
        {{ running ? emptyRunningText : emptyIdleText }}
      </div>
    </div>
  </section>
</template>

<style scoped>
.stage-live-log-panel {
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
  font-size: 14px;
  font-weight: 700;
  color: #64748b;
}

.stage-live-log-panel :deep(.ant-tag) {
  padding: 1px 8px;
  font-size: 14px;
  line-height: 24px;
  border-radius: 6px;
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
  font-size: 14px;
  color: #64748b;
}

.log-progress-title strong {
  font-size: 16px;
  color: #0b5cad;
}

.log-progress p {
  margin: 4px 0 0;
  font-size: 15px;
  line-height: 1.5;
  color: #334155;
  overflow-wrap: anywhere;
}

.live-log {
  height: 360px;
  padding: 10px 0;
  overflow: auto;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 15px;
  line-height: 1.7;
  color: #334155;
  background: #fbfdff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.log-line {
  min-height: 30px;
  padding: 6px 14px;
  color: #334155;
  overflow-wrap: anywhere;
}

.claude-line {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 10px;
  min-height: 54px;
  padding-top: 9px;
  padding-bottom: 9px;
  font-family: inherit;
  background: #fff;
  border-bottom: 1px solid #e8edf3;
}

.claude-line:last-child {
  border-bottom: 0;
}

.claude-rail {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  font-size: 17px;
  color: #245e8f;
  background: #eaf4fb;
  border-radius: 6px;
}

.claude-line--command .claude-rail {
  color: #166534;
  background: #eaf7ef;
}

.claude-line--inspect .claude-rail,
.claude-line--write .claude-rail {
  color: #6d4c12;
  background: #fff6da;
}

.claude-line--message .claude-rail,
.claude-line--result .claude-rail {
  color: #6941a5;
  background: #f3edfb;
}

.claude-line--thinking {
  background: #fffef9;
}

.claude-line--thinking .claude-rail {
  color: #7a5d0b;
  background: #fff4c2;
}

.claude-line--thinking .claude-primary {
  padding: 7px 9px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 13px;
  line-height: 1.6;
  color: #5f5538;
  background: #fffaf0;
  border-left: 3px solid #d6b54c;
  border-radius: 0 4px 4px 0;
}

.claude-line--error .claude-rail {
  color: #b42318;
  background: #ffebe9;
}

.claude-event {
  min-width: 0;
}

.claude-event-head {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 8px;
  align-items: center;
  min-height: 28px;
}

.claude-event-head strong {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  color: #172033;
}

.claude-event-head time {
  margin-left: auto;
  font-size: 12px;
  color: #778399;
}

.claude-tool {
  padding: 0 6px;
  font-size: 12px;
  line-height: 20px;
  color: #4a5568;
  background: #f0f3f7;
  border-radius: 4px;
}

.claude-primary,
.claude-description,
.claude-result-text {
  margin: 3px 0 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.claude-primary {
  color: #344054;
}

.claude-primary--code {
  padding: 7px 9px;
  font-size: 13px;
  line-height: 1.5;
  color: #1f2937;
  background: #f5f7fa;
  border-left: 3px solid #8fa6ba;
  border-radius: 0 4px 4px 0;
}

.claude-description {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 13px;
  color: #667085;
}

.claude-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: 1px;
  margin-top: 6px;
  overflow: hidden;
  background: #dfe5ec;
  border: 1px solid #dfe5ec;
  border-radius: 6px;
}

.claude-metrics > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  padding: 7px 9px;
  background: #f8fafc;
}

.claude-metrics span {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 11px;
  color: #667085;
}

.claude-metrics strong {
  overflow: hidden;
  font-size: 13px;
  color: #27364a;
  text-overflow: ellipsis;
}

.claude-result-text {
  max-height: 160px;
  padding-right: 6px;
  margin-top: 9px;
  overflow: auto;
  line-height: 1.55;
  color: #344054;
}

.log-line--success {
  color: #047857;
  background: #ecfdf5;
}

.log-line--summary {
  color: #0b5cad;
  background: #eef6ff;
}

.log-line--task,
.log-line--path {
  color: #7c3aed;
  background: #f8f5ff;
}

.log-line--code,
.log-line--function,
.log-line--slice {
  color: #0f766e;
  background: #f0fdfa;
}

.log-line--diff {
  color: #9a3412;
  background: #fff7ed;
}

.log-time {
  display: inline-block;
  width: 82px;
  vertical-align: middle;
  color: #64748b;
  user-select: none;
}

.log-line > * + * {
  margin-left: 8px;
}

.log-chip {
  display: inline-block;
  max-width: 180px;
  padding: 1px 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  line-height: 22px;
  vertical-align: middle;
  color: #475569;
  white-space: nowrap;
  background: #eef2f7;
  border-radius: 4px;
}

.log-chip--phase {
  max-width: 260px;
  font-weight: 700;
  color: #0b5cad;
  background: #e8f2ff;
}

.log-text {
  min-width: 0;
  vertical-align: middle;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.log-empty {
  padding: 14px;
  font-size: 15px;
  color: #64748b;
}
</style>
