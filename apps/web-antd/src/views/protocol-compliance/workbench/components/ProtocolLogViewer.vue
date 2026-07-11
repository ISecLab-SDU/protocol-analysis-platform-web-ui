<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';

interface LogEntry {
  id: number | string;
  level: 'ERROR' | 'INFO' | 'STATS' | 'WARN';
  text: string;
}

interface Props {
  logs: LogEntry[];
  running?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  running: false,
});

const scrollContainer = ref<HTMLElement>();
const maxDisplayLogs = 500;

const displayLogs = computed(() => {
  if (props.logs.length > maxDisplayLogs) {
    return props.logs.slice(-maxDisplayLogs);
  }
  return props.logs;
});

function scrollToBottom() {
  nextTick(() => {
    if (!scrollContainer.value) return;
    scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight;
  });
}

function getLogClass(level: LogEntry['level']) {
  return {
    'log-row--error': level === 'ERROR',
    'log-row--info': level === 'INFO',
    'log-row--stats': level === 'STATS',
    'log-row--warn': level === 'WARN',
  };
}

function getTimestamp(text: string) {
  return text.match(/\[(\d{2}:\d{2}:\d{2})\]/)?.[1] || '--:--:--';
}

function getPlainLogText(text: string) {
  return text
    .replace(/^[^[]*(?=\[\d{2}:\d{2}:\d{2}\])/, '')
    .replace(/\[\d{2}:\d{2}:\d{2}\]\s*/, '')
    .trim();
}

function getStatsLabel(label: string) {
  const key = label.toLowerCase();
  if (key.includes('cycle')) return '轮次';
  if (key.includes('path')) return '路径';
  if (key.includes('pending')) return '待处理';
  if (key.includes('coverage')) return '覆盖率';
  if (key.includes('crash')) return '崩溃';
  if (key.includes('hang')) return '挂起';
  if (key.includes('speed')) return '速度';
  if (key.includes('node')) return '状态节点';
  if (key.includes('edge')) return '状态转换';
  return label;
}

function getLevelLabel(level: LogEntry['level']) {
  if (level === 'STATS') return '统计';
  if (level === 'ERROR') return '异常';
  if (level === 'WARN') return '告警';
  return '信息';
}

function getStatsItems(text: string) {
  const source = getPlainLogText(text);
  const parts = source
    .split('|')
    .map((part) => part.trim())
    .filter(Boolean);

  return parts
    .map((part) => {
      const match = part.match(/^([^:]+):\s*(.+)$/);
      if (!match) return null;
      const label = match[1].trim();
      const value = match[2].trim();
      const key = label.toLowerCase();
      let tone = 'neutral';
      if (key.includes('crash') || key.includes('崩溃')) tone = 'danger';
      else if (
        key.includes('hang') ||
        key.includes('pending') ||
        key.includes('挂起') ||
        key.includes('待处理')
      )
        tone = 'warn';
      else if (
        key.includes('coverage') ||
        key.includes('speed') ||
        key.includes('覆盖率') ||
        key.includes('执行速度')
      )
        tone = 'success';
      else if (key.includes('path') || key.includes('路径')) tone = 'primary';
      return { label: getStatsLabel(label), tone, value };
    })
    .filter(Boolean) as Array<{ label: string; tone: string; value: string }>;
}

watch(
  () => props.logs.length,
  (newLength, oldLength) => {
    if (newLength > oldLength) scrollToBottom();
  },
);

onMounted(scrollToBottom);
</script>

<template>
  <div class="protocol-log-viewer">
    <div ref="scrollContainer" class="log-scroll">
      <div
        v-for="log in displayLogs"
        :key="log.id"
        class="log-row"
        :class="getLogClass(log.level)"
      >
        <span class="log-time">[{{ getTimestamp(log.text) }}]</span>
        <template
          v-if="log.level === 'STATS' && getStatsItems(log.text).length > 0"
        >
          <span class="log-level">{{ getLevelLabel(log.level) }}</span>
          <span class="log-stats">
            <span
              v-for="item in getStatsItems(log.text)"
              :key="`${log.id}-${item.label}`"
              class="stat-chip"
              :class="`stat-chip--${item.tone}`"
            >
              <span class="stat-chip-label">{{ item.label }}</span>
              <span class="stat-chip-value">{{ item.value }}</span>
            </span>
          </span>
        </template>
        <template v-else>
          <span class="log-level">{{ getLevelLabel(log.level) }}</span>
          <span class="log-text">{{ getPlainLogText(log.text) }}</span>
        </template>
      </div>

      <div v-if="logs.length === 0" class="log-empty">
        <div class="log-empty-icon">--</div>
        <div>{{ running ? '等待日志输出...' : '暂无运行日志' }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.protocol-log-viewer {
  overflow: hidden;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.log-scroll {
  height: 280px;
  padding: 12px;
  overflow-y: auto;
  font-family: var(--font-family);
  font-size: 16px;
  line-height: 1.6;
  background: #fff;
}

.log-row {
  display: grid;
  grid-template-columns: 110px 78px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  padding: 8px 10px;
  color: #334155;
  border-bottom: 1px solid #f1f5f9;
  border-radius: 0;
}

.log-row + .log-row {
  margin-top: 0;
}

.log-time {
  color: #64748b;
  white-space: nowrap;
}

.log-level {
  font-weight: 700;
  color: #1677ff;
  white-space: nowrap;
}

.log-text {
  min-width: 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.log-row--error {
  color: #991b1b;
  background: #fff7f7;
}

.log-row--error .log-level {
  color: #ef4444;
}

.log-row--warn {
  color: #92400e;
  background: #fffbeb;
}

.log-row--warn .log-level {
  color: #d97706;
}

.log-row--stats {
  color: #334155;
  background: #fbfdff;
}

.log-row--stats .log-level {
  color: #0ea5e9;
}

.log-row--info .log-level {
  color: #1677ff;
}

.log-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}

.stat-chip {
  display: inline-flex;
  gap: 5px;
  align-items: center;
  min-height: 26px;
  padding: 3px 9px;
  font-size: 15px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.stat-chip-label {
  color: #64748b;
}

.stat-chip-value {
  font-weight: 800;
  color: #172033;
}

.stat-chip--primary {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.stat-chip--primary .stat-chip-value {
  color: #2563eb;
}

.stat-chip--success {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.stat-chip--success .stat-chip-value {
  color: #16a34a;
}

.stat-chip--warn {
  background: #fffbeb;
  border-color: #fde68a;
}

.stat-chip--warn .stat-chip-value {
  color: #d97706;
}

.stat-chip--danger {
  background: #fff1f2;
  border-color: #fecdd3;
}

.stat-chip--danger .stat-chip-value {
  color: #e11d48;
}

.log-empty {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  justify-content: center;
  min-height: 220px;
  font-size: 15px;
  color: #94a3b8;
}

.log-empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: #cbd5e1;
  border: 1px solid rgb(203 213 225 / 32%);
  border-radius: 50%;
}
</style>
