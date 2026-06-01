<script setup lang="ts">
import { computed } from 'vue';

import { Card, Empty, Tag } from 'ant-design-vue';
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
    crashes: number;
    cycles: number;
    executions: number;
    hangs: number;
    paths: number;
    speed: number;
  };
}

const props = defineProps<Props>();

const sparkPath = computed(() => {
  if (props.speedSeries.length === 0) return '';
  const max = Math.max(...props.speedSeries, 1);
  const w = 220;
  const h = 72;
  const stepX = w / Math.max(props.speedSeries.length - 1, 1);
  return props.speedSeries
    .map((v, i) => {
      const x = i * stepX;
      const y = h - (v / max) * (h - 10) - 5;
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(' ');
});

const latestPointY = computed(() => {
  if (props.speedSeries.length === 0) return 72;
  const latest = props.speedSeries[props.speedSeries.length - 1] ?? 0;
  const max = Math.max(...props.speedSeries, 1);
  return 72 - (latest / max) * 62 - 5;
});

const errorLogs = computed(() => props.logs.filter((log) => log.level === 'ERROR'));
const warnLogs = computed(() => props.logs.filter((log) => log.level === 'WARN'));

const violationCount = computed(() => props.stats.crashes + errorLogs.value.length);
const warningCount = computed(() => props.stats.hangs + warnLogs.value.length);
const compliantCount = computed(() => {
  if (props.stats.executions <= 0) return 0;
  return violationCount.value === 0 ? 1 : 0;
});
const unknownCount = computed(() => (props.logs.length === 0 ? 1 : 0));

const fuzzerName = computed(() => {
  if (props.protocolType === 'MQTT' && props.implementation === 'SOL') return 'AFLNet';
  if (props.protocolType === 'MQTT') return 'MBFuzzer';
  return 'AFLNet';
});

const resultRows = computed(() => {
  return [...errorLogs.value, ...warnLogs.value].slice(-4).map((log, index) => {
    const seedMatch = log.text.match(/(?:seed|queue|id)[:=_-]?([A-Za-z0-9_.-]+)/i);
    const locationMatch = log.text.match(/([A-Za-z0-9_./-]+\.[ch](?:c|pp)?):(\d+)/i);
    return {
      description: log.text,
      expected: props.rule?.rule || '应满足当前协议规则',
      id: `F-${String(index + 1).padStart(3, '0')}`,
      input: seedMatch?.[1] || '-',
      location: locationMatch ? `${locationMatch[1]}:${locationMatch[2]}` : '-',
      observed: log.level === 'ERROR' ? '异常或崩溃' : '边界行为',
      severity: log.level === 'ERROR' ? 'High' : 'Medium',
      time: props.elapsed,
    };
  });
});
</script>

<template>
  <Card class="stage-card fuzz-stage" :bordered="false">
    <template #title>
      <div class="stage-title">
        <IconifyIcon icon="mdi:radar" />
        <span>验证结果</span>
        <small>当前规则</small>
      </div>
    </template>
    <template #extra>
      <Tag v-if="running" color="processing">运行中</Tag>
      <Tag v-else color="default">已停止</Tag>
    </template>

    <div class="fuzz-layout">
      <section class="validation-panel">
        <div class="result-cards">
          <div class="result-card result-card--danger">
            <IconifyIcon icon="mdi:shield-alert-outline" />
            <div>
              <div class="result-label">发现违规</div>
              <div class="result-value">{{ violationCount }}</div>
            </div>
          </div>
          <div class="result-card result-card--warn">
            <IconifyIcon icon="mdi:alert-outline" />
            <div>
              <div class="result-label">警告</div>
              <div class="result-value">{{ warningCount }}</div>
            </div>
          </div>
          <div class="result-card result-card--ok">
            <IconifyIcon icon="mdi:check-circle-outline" />
            <div>
              <div class="result-label">合规</div>
              <div class="result-value">{{ compliantCount }}</div>
            </div>
          </div>
          <div class="result-card result-card--unknown">
            <IconifyIcon icon="mdi:help-circle-outline" />
            <div>
              <div class="result-label">未判定</div>
              <div class="result-value">{{ unknownCount }}</div>
            </div>
          </div>
        </div>

        <div class="finding-table">
          <table v-if="resultRows.length > 0">
            <thead>
              <tr>
                <th>ID</th>
                <th>严重性</th>
                <th>违规描述</th>
                <th>观测值</th>
                <th>期望约束</th>
                <th>触发输入</th>
                <th>发现位置</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in resultRows" :key="row.id">
                <td>{{ row.id }}</td>
                <td>
                  <span
                    class="severity-pill"
                    :class="row.severity === 'High' ? 'severity-pill--high' : 'severity-pill--medium'"
                  >
                    {{ row.severity }}
                  </span>
                </td>
                <td>{{ row.description }}</td>
                <td>{{ row.observed }}</td>
                <td>{{ row.expected }}</td>
                <td class="mono">{{ row.input }}</td>
                <td class="mono">{{ row.location }}</td>
                <td>{{ row.time }}</td>
              </tr>
            </tbody>
          </table>
          <Empty
            v-else
            description="暂无违规记录，等待模糊测试发现可复现证据"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
          />
        </div>
      </section>

      <aside class="monitor-panel">
        <div class="monitor-title">运行监控</div>
        <dl class="monitor-list">
          <div>
            <dt>Fuzzer</dt>
            <dd>{{ fuzzerName }}</dd>
          </div>
          <div>
            <dt>运行时长</dt>
            <dd>{{ elapsed }}</dd>
          </div>
          <div>
            <dt>执行次数</dt>
            <dd>{{ stats.executions.toLocaleString() }}</dd>
          </div>
          <div>
            <dt>路径数</dt>
            <dd>{{ stats.paths.toLocaleString() }}</dd>
          </div>
          <div>
            <dt>Crash</dt>
            <dd>{{ stats.crashes }}</dd>
          </div>
          <div>
            <dt>Hang</dt>
            <dd>{{ stats.hangs }}</dd>
          </div>
        </dl>

        <div class="speed-chart">
          <svg viewBox="0 0 220 96" class="chart-svg">
            <line x1="0" x2="220" y1="85" y2="85" class="chart-grid" />
            <line x1="0" x2="220" y1="56" y2="56" class="chart-grid" />
            <line x1="0" x2="220" y1="27" y2="27" class="chart-grid" />
            <path v-if="sparkPath" :d="sparkPath" class="chart-line" />
            <circle
              v-if="sparkPath && speedSeries.length > 0"
              cx="216"
              :cy="latestPointY"
              r="3"
              class="chart-dot"
            />
          </svg>
          <div class="chart-caption">
            <span>0</span>
            <span>{{ stats.speed.toFixed(1) }} /s</span>
          </div>
        </div>
      </aside>
    </div>

    <section class="log-panel">
      <div class="log-heading">
        <IconifyIcon icon="mdi:console-line" />
        <span>实时日志</span>
      </div>
      <ProtocolLogViewer :logs="logs" :running="running" />
    </section>
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

.fuzz-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
}

.validation-panel,
.monitor-panel,
.log-panel {
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}

.validation-panel {
  min-width: 0;
  padding: 16px;
}

.result-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.result-card {
  display: flex;
  gap: 12px;
  align-items: center;
  min-height: 72px;
  padding: 14px;
  border: 1px solid transparent;
  border-radius: 8px;
}

.result-card :first-child {
  flex: none;
  font-size: 26px;
}

.result-card--danger {
  color: #dc2626;
  background: #fff5f5;
  border-color: #ffe0e0;
}

.result-card--warn {
  color: #d97706;
  background: #fffaf0;
  border-color: #ffe8b3;
}

.result-card--ok {
  color: #0f9f6e;
  background: #f0fdf4;
  border-color: #c7f3d8;
}

.result-card--unknown {
  color: #334155;
  background: #f8fafc;
  border-color: #e2e8f0;
}

.result-label {
  font-size: 13px;
  font-weight: 600;
}

.result-value {
  margin-top: 2px;
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
}

.finding-table {
  overflow: auto;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}

.finding-table table {
  width: 100%;
  min-width: 860px;
  border-collapse: collapse;
  font-size: 12px;
}

.finding-table th {
  padding: 10px 12px;
  font-weight: 700;
  color: #475569;
  text-align: left;
  white-space: nowrap;
  background: #f8fafc;
  border-bottom: 1px solid var(--ant-color-border-secondary);
}

.finding-table td {
  max-width: 260px;
  padding: 12px;
  overflow: hidden;
  color: #172033;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-bottom: 1px solid var(--ant-color-border-secondary);
}

.finding-table tr:last-child td {
  border-bottom: 0;
}

.severity-pill {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  font-size: 12px;
  font-weight: 700;
  border-radius: 999px;
}

.severity-pill--high {
  color: #e11d48;
  background: #fff1f2;
}

.severity-pill--medium {
  color: #b45309;
  background: #fffbeb;
}

.mono {
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
}

.monitor-panel {
  padding: 18px;
  background: #fff;
}

.monitor-title {
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 700;
}

.monitor-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
}

.monitor-list > div {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.monitor-list dt {
  color: #475569;
}

.monitor-list dd {
  margin: 0;
  font-weight: 700;
  color: #172033;
  text-align: right;
}

.speed-chart {
  margin-top: 18px;
}

.chart-svg {
  width: 100%;
  height: 112px;
}

.chart-grid {
  stroke: #e2e8f0;
  stroke-dasharray: 3 4;
}

.chart-line {
  fill: none;
  stroke: #1677ff;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 3;
}

.chart-dot {
  fill: #1677ff;
}

.chart-caption {
  display: flex;
  justify-content: space-between;
  margin-top: -8px;
  font-size: 12px;
  color: #64748b;
}

.log-panel {
  margin-top: 18px;
  padding: 16px;
}

.log-heading {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
  font-weight: 700;
}

.log-heading :first-child {
  color: #1677ff;
}

@media (max-width: 1200px) {
  .fuzz-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .result-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
