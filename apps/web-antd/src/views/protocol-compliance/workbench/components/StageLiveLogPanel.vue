<script setup lang="ts">
import type { ProtocolAgentProgressMetadata } from '#/api/protocol-compliance';

import { computed, nextTick, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';

import { Tag } from 'ant-design-vue';

interface StageLiveLogLine {
  id: string;
  kind?: string;
  metadata?: ProtocolAgentProgressMetadata;
  phase: string;
  stage?: string;
  text: string;
  time?: string;
}

interface StageLiveLogProgress {
  description: string;
  label: string;
}

interface DisplayLogLine extends StageLiveLogLine {
  groupCategory?: string;
  groupLines?: StageLiveLogLine[];
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
  props.lines.filter((line) => !line.metadata?.quiet),
);

const displayLines = computed(() => {
  const entries: DisplayLogLine[] = [];
  let outputGroup: DisplayLogLine | undefined;
  for (const line of props.lines) {
    const category = outputCategory(line);
    if (category) {
      if (
        outputGroup?.groupCategory === category &&
        outputGroup.stage === line.stage &&
        outputGroup?.phase === line.phase
      ) {
        outputGroup.groupLines?.push(line);
      } else {
        outputGroup = { ...line, groupCategory: category, groupLines: [line] };
        entries.push(outputGroup);
      }
    } else {
      outputGroup = undefined;
      if (!line.metadata?.quiet) entries.push(line);
    }
  }
  return entries;
});

// Builder file previews, inventories and other tagged output share the same
// envelope. Group by its category, never by timestamp or arbitrary text similarity.
function outputCategory(line: StageLiveLogLine) {
  if (
    line.metadata?.quiet ||
    line.metadata?.is_error ||
    line.metadata?.status ||
    (line.metadata?.activity && line.metadata.activity !== 'status') ||
    (line.kind && !['info', 'normal'].includes(line.kind))
  )
    return undefined;
  const category = /^\[pg-builder\]\[([^\]\r\n]+)\](?: |$)/.exec(
    line.text,
  )?.[1];
  // The builder's ordinary lifecycle logger puts an ISO timestamp in this slot.
  if (!category || /^\d{4}-\d{2}-\d{2}T/.test(category)) return undefined;
  return category;
}

function outputText(line: StageLiveLogLine) {
  return displayText(line.text.replace(/^\[pg-builder\]\[[^\]\r\n]+\] ?/, ''));
}

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

function isAgentLine(line: StageLiveLogLine) {
  return Boolean(line.metadata?.activity);
}

function agentLineKind(line: StageLiveLogLine) {
  if (line.metadata?.is_error || line.metadata?.status === 'failed')
    return 'error';
  const activity = line.metadata?.activity;
  if (activity === 'tool_result') return 'observation';
  if (
    activity === 'command' ||
    activity === 'inspect' ||
    activity === 'write' ||
    activity === 'message' ||
    activity === 'thinking' ||
    activity === 'result'
  )
    return activity;
  return 'status';
}

function agentIcon(line: StageLiveLogLine) {
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
  }[agentLineKind(line)];
}

function agentLabel(line: StageLiveLogLine) {
  const kind = agentLineKind(line);
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

function agentPrimaryText(line: StageLiveLogLine) {
  if (line.metadata?.primary) return line.metadata.primary;
  if (
    line.metadata?.activity === 'thinking' ||
    line.metadata?.activity === 'tool_result'
  )
    return displayText(line.text);
  return displayText(line.text.replace(/^[a-z]+:\s*/i, ''));
}

function agentDescription(line: StageLiveLogLine) {
  return displayText(line.metadata?.description || '');
}

function resultMetrics(line: StageLiveLogLine) {
  const metadata = line.metadata ?? {};
  const model = metadata.model;
  const metrics: Array<{ label: string; value: string }> = [];
  if (model) metrics.push({ label: '模型', value: displayText(model) });
  if (typeof metadata.duration_ms === 'number') {
    metrics.push({
      label: '耗时',
      value: formatDuration(metadata.duration_ms),
    });
  }
  if (typeof metadata.cost_usd === 'number') {
    metrics.push({ label: '费用', value: `$${metadata.cost_usd.toFixed(4)}` });
  }
  if (typeof metadata.input_tokens === 'number') {
    metrics.push({ label: '输入', value: formatCount(metadata.input_tokens) });
  }
  if (typeof metadata.output_tokens === 'number') {
    metrics.push({ label: '输出', value: formatCount(metadata.output_tokens) });
  }
  if (typeof metadata.cache_read_tokens === 'number') {
    metrics.push({
      label: '缓存命中',
      value: formatCount(metadata.cache_read_tokens),
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
        v-for="line in displayLines"
        :key="line.id"
        class="log-line"
        :class="[
          line.kind ? `log-line--${line.kind}` : undefined,
          line.groupLines
            ? 'output-line'
            : isAgentLine(line)
              ? `agent-line agent-line--${agentLineKind(line)}`
              : undefined,
        ]"
      >
        <details v-if="line.groupLines" class="output-group">
          <summary>
            <span class="log-chip log-chip--phase">{{
              displayText(line.phase)
            }}</span>
            <strong
              >{{ line.groupCategory }} ·
              {{ line.groupLines.length }} 条记录</strong
            >
            <time>{{ line.time || '--:--:--' }}</time>
            <time v-if="line.groupLines.at(-1)?.time !== line.time"
              >– {{ line.groupLines.at(-1)?.time || '--:--:--' }}</time
            >
          </summary>
          <div
            class="output-lines"
            tabindex="0"
            :aria-label="`${line.groupCategory} 输出`"
          >
            <div v-for="entry in line.groupLines" :key="entry.id">
              <time>{{ entry.time || '--:--:--' }}</time>
              {{ outputText(entry) }}
            </div>
          </div>
        </details>
        <template v-else-if="isAgentLine(line)">
          <div class="agent-rail" aria-hidden="true">
            <IconifyIcon :icon="agentIcon(line)" />
          </div>
          <div class="agent-event">
            <div class="agent-event-head">
              <strong>{{ agentLabel(line) }}</strong>
              <span class="log-chip log-chip--phase">{{
                displayText(line.phase)
              }}</span>
              <span v-if="line.metadata?.tool" class="agent-tool">{{
                line.metadata.tool
              }}</span>
              <time>{{ line.time || '--:--:--' }}</time>
            </div>
            <p
              v-if="agentLineKind(line) !== 'result'"
              class="agent-primary"
              :class="{
                'agent-primary--code': ['command', 'inspect', 'write'].includes(
                  agentLineKind(line),
                ),
              }"
            >
              {{ agentPrimaryText(line) }}
            </p>
            <p v-if="agentDescription(line)" class="agent-description">
              {{ agentDescription(line) }}
            </p>
            <template v-if="agentLineKind(line) === 'result'">
              <div class="agent-metrics">
                <div v-for="metric in resultMetrics(line)" :key="metric.label">
                  <span>{{ metric.label }}</span>
                  <strong>{{ metric.value }}</strong>
                </div>
              </div>
              <p v-if="line.metadata?.result" class="agent-result-text">
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

.agent-line {
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

.output-line {
  display: block;
  min-height: 30px;
  padding: 6px 14px;
}

.output-group summary {
  cursor: pointer;
}

.output-group summary strong {
  margin: 0 8px;
  font-size: 14px;
}

.output-group time {
  font-size: 12px;
  color: #778399;
}

.output-lines {
  max-height: 240px;
  padding: 8px;
  margin-top: 6px;
  overflow: auto;
  font-size: 13px;
  white-space: pre-wrap;
  background: #f5f7fa;
  border-radius: 4px;
}

.agent-line:last-child {
  border-bottom: 0;
}

.agent-rail {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  font-size: 17px;
  color: #245e8f;
  background: #eaf4fb;
  border-radius: 6px;
}

.agent-line--command .agent-rail {
  color: #166534;
  background: #eaf7ef;
}

.agent-line--inspect .agent-rail,
.agent-line--write .agent-rail {
  color: #6d4c12;
  background: #fff6da;
}

.agent-line--message .agent-rail,
.agent-line--result .agent-rail {
  color: #6941a5;
  background: #f3edfb;
}

.agent-line--thinking {
  background: #fffef9;
}

.agent-line--thinking .agent-rail {
  color: #7a5d0b;
  background: #fff4c2;
}

.agent-line--thinking .agent-primary {
  padding: 7px 9px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 13px;
  line-height: 1.6;
  color: #5f5538;
  background: #fffaf0;
  border-left: 3px solid #d6b54c;
  border-radius: 0 4px 4px 0;
}

.agent-line--error .agent-rail {
  color: #b42318;
  background: #ffebe9;
}

.agent-event {
  min-width: 0;
}

.agent-event-head {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 8px;
  align-items: center;
  min-height: 28px;
}

.agent-event-head strong {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  color: #172033;
}

.agent-event-head time {
  margin-left: auto;
  font-size: 12px;
  color: #778399;
}

.agent-tool {
  padding: 0 6px;
  font-size: 12px;
  line-height: 20px;
  color: #4a5568;
  background: #f0f3f7;
  border-radius: 4px;
}

.agent-primary,
.agent-description,
.agent-result-text {
  margin: 3px 0 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.agent-primary {
  color: #344054;
}

.agent-primary--code {
  padding: 7px 9px;
  font-size: 13px;
  line-height: 1.5;
  color: #1f2937;
  background: #f5f7fa;
  border-left: 3px solid #8fa6ba;
  border-radius: 0 4px 4px 0;
}

.agent-description {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 13px;
  color: #667085;
}

.agent-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: 1px;
  margin-top: 6px;
  overflow: hidden;
  background: #dfe5ec;
  border: 1px solid #dfe5ec;
  border-radius: 6px;
}

.agent-metrics > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  padding: 7px 9px;
  background: #f8fafc;
}

.agent-metrics span {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 11px;
  color: #667085;
}

.agent-metrics strong {
  overflow: hidden;
  font-size: 13px;
  color: #27364a;
  text-overflow: ellipsis;
}

.agent-result-text {
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
