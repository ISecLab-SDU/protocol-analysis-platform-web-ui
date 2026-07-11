<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';

import { Tag } from 'ant-design-vue';

interface StageLiveLogLine {
  id: string;
  kind?: string;
  phase: string;
  source?: string;
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
  const metaSegments = [line.time || '--:--:--', line.phase, line.source]
    .filter(Boolean)
    .map((segment) => `[${segment}]`);
  return `${metaSegments.join(' ')} ${line.text}`.trim();
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
        {{ running ? '自动滚动' : `${lines.length} 行` }}
      </Tag>
    </div>

    <div class="log-progress">
      <div class="log-progress-title">
        <span>当前阶段</span>
        <strong>{{ progress.label }}</strong>
      </div>
      <p>{{ progress.description }}</p>
    </div>

    <div ref="logBodyRef" class="live-log">
      <div
        v-for="line in lines"
        :key="line.id"
        class="log-line"
        :class="line.kind ? `log-line--${line.kind}` : undefined"
      >
        <div class="log-meta">
          <span class="log-time">{{ line.time || '--:--:--' }}</span>
          <span class="log-chip log-chip--phase">{{ line.phase }}</span>
          <span v-if="line.source" class="log-chip log-chip--source">{{
            line.source
          }}</span>
        </div>
        <span class="log-text">{{ line.text }}</span>
      </div>
      <div v-if="lines.length === 0" class="log-empty">
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
  display: grid;
  gap: 4px;
  min-height: 30px;
  padding: 6px 14px;
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

.log-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  min-width: 0;
}

.log-time {
  flex: 0 0 82px;
  color: #64748b;
  user-select: none;
}

.log-chip {
  flex: 0 1 auto;
  max-width: 180px;
  padding: 1px 8px;
  overflow: hidden;
  font-size: 14px;
  line-height: 22px;
  color: #475569;
  text-overflow: ellipsis;
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
  font-size: 15px;
  color: #64748b;
}
</style>
