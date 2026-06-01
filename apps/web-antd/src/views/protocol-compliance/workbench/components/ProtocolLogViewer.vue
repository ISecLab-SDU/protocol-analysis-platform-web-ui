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
        <span class="log-level">{{ log.level }}</span>
        <span class="log-text">{{ log.text }}</span>
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
  background: #0f172a;
  border: 1px solid rgb(15 23 42 / 8%);
  border-radius: 8px;
}

.log-scroll {
  height: 280px;
  padding: 12px;
  overflow-y: auto;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 12px;
  line-height: 1.55;
}

.log-row {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 10px;
  padding: 3px 6px;
  color: #dbeafe;
  border-radius: 4px;
}

.log-row + .log-row {
  margin-top: 2px;
}

.log-level {
  font-weight: 700;
  color: #93c5fd;
}

.log-text {
  min-width: 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.log-row--error {
  color: #fecaca;
  background: rgb(248 113 113 / 12%);
}

.log-row--error .log-level {
  color: #fca5a5;
}

.log-row--warn {
  color: #fde68a;
  background: rgb(245 158 11 / 12%);
}

.log-row--warn .log-level {
  color: #fbbf24;
}

.log-row--stats {
  color: #bbf7d0;
}

.log-row--stats .log-level {
  color: #86efac;
}

.log-row--info .log-level {
  color: #93c5fd;
}

.log-empty {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  justify-content: center;
  min-height: 220px;
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
