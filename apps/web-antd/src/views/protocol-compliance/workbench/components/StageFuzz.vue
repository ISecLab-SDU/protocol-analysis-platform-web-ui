<script setup lang="ts">
import { computed } from 'vue';

import { Card, Tag } from 'ant-design-vue';
import { IconifyIcon } from '@vben/icons';

import type { ProtocolExtractRuleItem } from '#/api/protocol-compliance';

import ProtocolLogViewer from './ProtocolLogViewer.vue';

interface LogEntry {
  id: number;
  level: 'ERROR' | 'INFO' | 'STATS' | 'WARN';
  text: string;
}

interface Props {
  elapsed: string;
  implementation: string;
  logs: LogEntry[];
  protocolType: string;
  rule: null | ProtocolExtractRuleItem;
  running: boolean;
  speedSeries: number[];
  stats: {
    coverage?: number;
    crashes: number;
    currentPath?: number;
    cycles: number;
    edges?: number;
    executions: number;
    hangs: number;
    maxDepth?: number;
    nodes?: number;
    paths: number;
    pathsTotal?: number;
    pendingFavs?: number;
    pendingTotal?: number;
    speed: number;
  };
}

const props = defineProps<Props>();

const fuzzerName = computed(() => {
  if (props.protocolType === 'MQTT' && props.implementation === 'SOL') return 'SOLAFLNET';
  if (props.protocolType === 'MQTT') return 'MBFuzzer';
  return 'AFLNet';
});

const totalPaths = computed(() => props.stats.pathsTotal || props.stats.paths || 0);
const currentPath = computed(() => props.stats.currentPath || 0);
const pendingTotal = computed(() => props.stats.pendingTotal ?? Math.max(totalPaths.value - currentPath.value, 0));
const pendingFavs = computed(() => props.stats.pendingFavs ?? 0);
const coverage = computed(() => props.stats.coverage ?? 0);
const nodes = computed(() => props.stats.nodes ?? 0);
const edges = computed(() => props.stats.edges ?? 0);
const maxDepth = computed(() => props.stats.maxDepth ?? 0);
const maxDepthDisplay = computed(() => (maxDepth.value > 0 ? String(maxDepth.value) : '-'));

const latestStatsLine = computed(() => {
  return [...props.logs].reverse().find((log) => log.level === 'STATS')?.text || '';
});

const logCaption = computed(() => {
  if (latestStatsLine.value) return `正在同步 ${fuzzerName.value} 状态、路径和异常统计`;
  return '等待 Fuzzer 输出运行状态';
});

const pathProgress = computed(() => {
  if (totalPaths.value <= 0) return 0;
  return Math.min(100, Math.round((currentPath.value / totalPaths.value) * 100));
});

const monitorStatusText = computed(() => {
  if (props.running) return '运行中';
  if (props.logs.length > 0) return '已停止';
  return '待启动';
});

function formatNumber(value: number) {
  return Math.trunc(value).toLocaleString();
}

function formatRate(value: number) {
  return value.toFixed(1);
}
</script>

<template>
  <Card class="stage-card fuzz-stage" :bordered="false">
    <template #title>
      <div class="stage-title">
        <IconifyIcon icon="mdi:radar" />
        <span>模糊测试阶段</span>
        <small>{{ fuzzerName }}</small>
      </div>
    </template>
    <template #extra>
      <Tag v-if="running" color="processing">运行中</Tag>
      <Tag v-else color="default">待启动</Tag>
    </template>

    <div class="fuzz-dashboard">
      <section class="panel panel--logs">
        <div class="panel-header">
          <div>
            <h3>测试过程日志</h3>
            <p>{{ logCaption }}</p>
          </div>
        </div>
        <ProtocolLogViewer :logs="logs" :running="running" />
      </section>

      <aside class="panel panel--monitor">
        <div class="panel-header panel-header--compact">
          <h3>运行监控</h3>
          <Tag :color="running ? 'processing' : 'default'">{{ monitorStatusText }}</Tag>
        </div>

        <div class="alert-metrics">
          <div class="metric-tile metric-tile--danger">
            <strong>{{ formatNumber(stats.crashes) }}</strong>
            <span>崩溃数</span>
            <small>Crashes</small>
          </div>
          <div class="metric-tile metric-tile--warn">
            <strong>{{ formatNumber(stats.hangs) }}</strong>
            <span>挂起数</span>
            <small>Hangs</small>
          </div>
        </div>

        <div class="status-card">
          <span>监控状态</span>
          <strong>{{ monitorStatusText }}</strong>
        </div>
      </aside>

      <section class="panel panel--sol">
        <div class="panel-header">
          <div>
            <h3>{{ fuzzerName }} 模糊测试</h3>
            <p>{{ rule?.rule || '基于当前协议约束持续发现异常路径' }}</p>
          </div>
        </div>

        <div class="sol-grid">
          <div class="overview-card overview-card--blue">
            <strong>{{ formatNumber(totalPaths) }}</strong>
            <span>总路径数</span>
            <small>Total Paths</small>
          </div>
          <div class="overview-card overview-card--green">
            <strong>{{ formatNumber(currentPath) }}</strong>
            <span>当前路径</span>
            <small>Current Path</small>
          </div>
          <div class="overview-card overview-card--gold">
            <strong>{{ formatNumber(pendingTotal) }}</strong>
            <span>待处理</span>
            <small>Pending</small>
          </div>
          <div class="overview-card overview-card--purple">
            <strong>{{ formatNumber(pendingFavs) }}</strong>
            <span>优先路径</span>
            <small>Favored</small>
          </div>
        </div>

        <div class="topology-card">
          <div class="topology-title">协议状态机拓扑</div>
          <div class="topology-body">
            <div class="topology-node topology-node--primary">{{ nodes }}</div>
            <div class="topology-line"></div>
            <div class="topology-node topology-node--success">{{ edges }}</div>
          </div>
          <div class="topology-caption">{{ nodes }} 个状态节点 · {{ edges }} 个状态转换</div>
          <div class="topology-footer">
            <div>
              <strong>{{ maxDepthDisplay }}</strong>
              <span>最大深度</span>
            </div>
            <div>
              <strong>{{ coverage.toFixed(2) }}%</strong>
              <span>覆盖率</span>
            </div>
          </div>
        </div>
      </section>

      <aside class="panel panel--realtime">
        <div class="panel-header">
          <div>
            <h3>实时统计</h3>
            <p>当前执行路径</p>
          </div>
          <strong class="path-index">#{{ currentPath || '-' }}</strong>
        </div>

        <div class="progress-copy">{{ currentPath }} / {{ totalPaths }} 路径</div>
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${pathProgress}%` }"></div>
        </div>

        <div class="runtime-grid">
          <div class="runtime-tile runtime-tile--blue">
            <span>执行速度</span>
            <strong>{{ formatRate(stats.speed) }}</strong>
            <small>exec/sec</small>
          </div>
          <div class="runtime-tile runtime-tile--green">
            <span>运行时长</span>
            <strong>{{ elapsed }}</strong>
            <small>Duration</small>
          </div>
          <div class="runtime-tile runtime-tile--danger">
            <span>崩溃数</span>
            <strong>{{ formatNumber(stats.crashes) }}</strong>
            <small>crashes</small>
          </div>
          <div class="runtime-tile runtime-tile--gold">
            <span>挂起数</span>
            <strong>{{ formatNumber(stats.hangs) }}</strong>
            <small>hangs</small>
          </div>
        </div>
      </aside>
    </div>
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

.fuzz-dashboard {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
}

.panel {
  min-width: 0;
  padding: 18px;
  background: #fff;
  border: 1px solid #dbeafe;
  border-radius: 8px;
}

.panel-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.panel-header--compact {
  align-items: center;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #172033;
}

.panel-header p {
  margin: 6px 0 0;
  font-size: 12px;
  color: #64748b;
}

.panel--logs :deep(.log-scroll) {
  height: 300px;
}

.alert-metrics,
.sol-grid,
.runtime-grid {
  display: grid;
  gap: 12px;
}

.alert-metrics {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.metric-tile,
.overview-card,
.runtime-tile {
  min-width: 0;
  border: 1px solid transparent;
  border-radius: 8px;
}

.metric-tile {
  min-height: 96px;
  padding: 18px 14px;
  text-align: center;
}

.metric-tile strong,
.overview-card strong,
.runtime-tile strong {
  display: block;
  overflow: hidden;
  font-weight: 900;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-tile strong {
  font-size: 30px;
}

.metric-tile span,
.overview-card span,
.runtime-tile span {
  display: block;
  margin-top: 8px;
  font-size: 13px;
  color: #475569;
}

.metric-tile small,
.overview-card small,
.runtime-tile small {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.metric-tile--danger,
.runtime-tile--danger {
  background: #fff5f7;
  border-color: #fecdd3;
}

.metric-tile--danger strong,
.runtime-tile--danger strong {
  color: #e11d48;
}

.metric-tile--warn {
  background: #fffbeb;
  border-color: #fde68a;
}

.metric-tile--warn strong {
  color: #d69e2e;
}

.status-card {
  display: grid;
  gap: 6px;
  padding: 16px;
  margin-top: 18px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.status-card strong {
  color: #172033;
}

.panel--sol {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 1fr);
  gap: 18px;
}

.panel--sol .panel-header {
  grid-column: 1 / -1;
  margin-bottom: 0;
}

.sol-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.overview-card {
  min-height: 104px;
  padding: 20px 16px;
  text-align: center;
}

.overview-card strong {
  font-size: 32px;
}

.overview-card--blue {
  background: #eff6ff;
  border-color: #dbeafe;
}

.runtime-tile--blue {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.overview-card--blue strong,
.runtime-tile--blue strong {
  color: #2563eb;
}

.overview-card--green,
.runtime-tile--green {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.overview-card--green strong,
.runtime-tile--green strong {
  color: #22c55e;
}

.overview-card--gold,
.runtime-tile--gold {
  background: #fffbeb;
  border-color: #fde68a;
}

.overview-card--gold strong,
.runtime-tile--gold strong {
  color: #d69e2e;
}

.overview-card--purple {
  background: #faf5ff;
  border-color: #e9d5ff;
}

.overview-card--purple strong {
  color: #9333ea;
}

.topology-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 220px;
  padding: 18px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.topology-title {
  font-size: 14px;
  font-weight: 700;
  color: #475569;
  text-align: center;
}

.topology-body {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 96px;
  margin-top: 10px;
  background: #f8fafc;
  border-radius: 8px;
}

.topology-node {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  font-weight: 900;
  color: #fff;
  border-radius: 999px;
}

.topology-node--primary {
  background: #3b82f6;
}

.topology-node--success {
  background: #4ade80;
}

.topology-line {
  width: 52px;
  height: 2px;
  background: #cbd5e1;
}

.topology-caption {
  margin-top: 8px;
  font-size: 12px;
  color: #2563eb;
  text-align: center;
}

.topology-footer {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.topology-footer > div {
  padding: 10px;
  text-align: center;
  background: #f8fafc;
  border-radius: 6px;
}

.topology-footer strong {
  display: block;
  font-size: 14px;
  color: #2563eb;
}

.topology-footer span {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.path-index {
  font-size: 18px;
  color: #475569;
}

.progress-copy {
  margin-bottom: 10px;
  font-size: 13px;
  color: #64748b;
}

.progress-track {
  height: 8px;
  overflow: hidden;
  background: #e5e7eb;
  border-radius: 999px;
}

.progress-fill {
  height: 100%;
  background: #2563eb;
  border-radius: inherit;
  transition: width 180ms ease;
}

.runtime-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 20px;
}

.runtime-tile {
  min-height: 92px;
  padding: 14px;
}

.runtime-tile strong {
  margin-top: 8px;
  font-size: 26px;
}

@media (max-width: 1280px) {
  .fuzz-dashboard {
    grid-template-columns: 1fr;
  }

  .panel--sol {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .alert-metrics,
  .runtime-grid,
  .sol-grid,
  .topology-footer {
    grid-template-columns: 1fr;
  }

  .panel {
    padding: 14px;
  }
}
</style>
