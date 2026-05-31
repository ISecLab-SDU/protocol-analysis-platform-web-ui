<script setup lang="ts">
import { computed } from 'vue';

import { Card, Tag } from 'ant-design-vue';
import { IconifyIcon } from '@vben/icons';

import ProtocolLogViewer from './ProtocolLogViewer.vue';

interface Props {
  logs: Array<{ id: number; text: string; level: 'INFO' | 'WARN' | 'ERROR' | 'STATS' }>;
  stats: {
    executions: number;
    paths: number;
    crashes: number;
    hangs: number;
    cycles: number;
    speed: number;
  };
  speedSeries: number[];
  running: boolean;
}

defineProps<Props>();

const sparkPath = computed(() => {
  const props = defineProps<Props>();
  if (props.speedSeries.length === 0) return '';
  const max = Math.max(...props.speedSeries, 1);
  const w = 200;
  const h = 60;
  const stepX = w / Math.max(props.speedSeries.length - 1, 1);
  return props.speedSeries
    .map((v, i) => {
      const x = i * stepX;
      const y = h - (v / max) * (h - 6) - 3;
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(' ');
});
</script>

<template>
  <Card title="模糊测试">
    <template #extra>
      <Tag v-if="running" color="processing">运行中</Tag>
      <Tag v-else color="default">已停止</Tag>
    </template>

    <div class="fuzz-container">
      <div class="fuzz-logs">
        <div class="fuzz-title">
          <IconifyIcon icon="mdi:console-line" />
          <span>实时日志</span>
        </div>
        <ProtocolLogViewer :logs="logs" />
      </div>

      <div class="fuzz-stats">
        <div class="fuzz-title">
          <IconifyIcon icon="mdi:chart-box-outline" />
          <span>运行统计</span>
        </div>

        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-label">执行次数</div>
            <div class="stat-value">{{ stats.executions.toLocaleString() }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">路径数</div>
            <div class="stat-value">{{ stats.paths.toLocaleString() }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">崩溃</div>
            <div class="stat-value stat-value--danger">{{ stats.crashes }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">挂起</div>
            <div class="stat-value stat-value--warn">{{ stats.hangs }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">循环</div>
            <div class="stat-value">{{ stats.cycles }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">速度</div>
            <div class="stat-value">{{ stats.speed.toFixed(1) }} /s</div>
          </div>
        </div>

        <div v-if="speedSeries.length > 0" class="speed-chart">
          <div class="chart-label">执行速度趋势</div>
          <svg viewBox="0 0 200 60" class="chart-svg">
            <path :d="sparkPath" class="chart-line" />
          </svg>
        </div>
      </div>
    </div>
  </Card>
</template>

<style scoped>
.fuzz-container {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 20px;
}

.fuzz-logs,
.fuzz-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.fuzz-title {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stat-item {
  padding: 12px;
  background: var(--ant-color-fill-quaternary);
  border-radius: 8px;
}

.stat-label {
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.stat-value {
  margin-top: 4px;
  font-size: 20px;
  font-weight: 600;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.stat-value--danger {
  color: #dc2626;
}

.stat-value--warn {
  color: #d97706;
}

.speed-chart {
  margin-top: 8px;
  padding: 12px;
  background: var(--ant-color-fill-quaternary);
  border-radius: 8px;
}

.chart-label {
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.chart-svg {
  width: 100%;
  height: 60px;
}

.chart-line {
  fill: none;
  stroke: #1677ff;
  stroke-width: 2;
}
</style>
