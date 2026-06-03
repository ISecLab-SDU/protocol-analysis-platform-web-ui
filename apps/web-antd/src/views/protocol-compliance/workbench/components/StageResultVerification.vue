<script setup lang="ts">
import { computed } from 'vue';

import { Button, Card, Empty, Tag } from 'ant-design-vue';
import { IconifyIcon } from '@vben/icons';

import type {
  ProtocolAssertGenerationResult,
  ProtocolExtractRuleItem,
  ProtocolStaticAnalysisResult,
} from '#/api/protocol-compliance';

import type { CodeLocateEvidence, CodeLocateFunctionSlice } from '../types';

interface FuzzLogEntry {
  id: number;
  level: 'ERROR' | 'INFO' | 'STATS' | 'WARN';
  text: string;
}

interface Props {
  assertDiffContent: string;
  assertResult: ProtocolAssertGenerationResult | null;
  elapsed: string;
  evidence: CodeLocateEvidence | null;
  implementation: string;
  logs: FuzzLogEntry[];
  protocolType: string;
  rule: null | ProtocolExtractRuleItem;
  staticResult: null | ProtocolStaticAnalysisResult;
  stats: {
    crashes: number;
    executions: number;
    hangs: number;
    paths: number;
    speed: number;
  };
}

interface RelatedFunctionView {
  file: string;
  line: string;
  name: string;
}

const props = defineProps<Props>();

const verdicts = computed(() => props.staticResult?.modelResponse?.verdicts ?? []);
const primaryVerdict = computed(() => {
  return (
    verdicts.value.find((verdict) => verdict.compliance === 'non_compliant') ??
    verdicts.value.find((verdict) => verdict.compliance === 'needs_review') ??
    verdicts.value[0] ??
    null
  );
});

const ruleDescription = computed(() => {
  return (
    props.evidence?.ruleText ||
    props.rule?.rule ||
    props.rule?.description ||
    primaryVerdict.value?.relatedRule?.requirement ||
    '等待规则描述'
  );
});

const violationReason = computed(() => {
  return (
    props.evidence?.violationReason ||
    primaryVerdict.value?.explanation ||
    props.staticResult?.modelResponse?.summary?.notes ||
    '已发现崩溃，等待代码定位模块补充违规原因'
  );
});

const relatedFunctions = computed<RelatedFunctionView[]>(() => {
  const fromEvidence = buildFunctionsFromEvidence(props.evidence?.functions ?? []);
  if (fromEvidence.length > 0) return fromEvidence;

  const records = new Map<string, RelatedFunctionView>();
  for (const verdict of verdicts.value) {
    const name = verdict.location?.function || verdict.location?.file;
    if (!name || records.has(name)) continue;
    records.set(name, {
      file: verdict.location?.file || props.evidence?.targetFile || '-',
      line: verdict.lineRange?.length ? verdict.lineRange.join('-') : '-',
      name,
    });
  }
  return [...records.values()];
});

const assertionLines = computed(() => {
  return props.assertDiffContent
    .split(/\r?\n/)
    .filter((line) => {
      if (!line.startsWith('+') || line.startsWith('+++')) return false;
      return /assert\s*\(|assert_related_rule|#include\s+<assert\.h>|static\s+int/i.test(line);
    })
    .map((line) => line.slice(1).trimEnd())
    .filter(Boolean)
    .slice(0, 8);
});

const changedFileCount = computed(() => {
  const matches = props.assertDiffContent.match(/^diff --git\s+/gm);
  return matches?.length ?? 0;
});

const assertionSummary = computed(() => {
  if (props.assertResult) {
    return `${props.assertResult.assertionCount} 条断言任务，${changedFileCount.value} 个文件发生插桩变更`;
  }
  if (props.assertDiffContent) {
    return `${changedFileCount.value} 个文件发生插桩变更`;
  }
  return '等待断言生成模块输出';
});

const crashLogPath = computed(() => {
  for (const log of props.logs) {
    const text = log.text;
    const cnMatch = text.match(/崩溃队列信息导出[:：]\s*(.+)$/);
    if (cnMatch?.[1]) return cnMatch[1].trim();

    const aflMatch = text.match(/(?:crash(?:es)?|queue|poc)[^:：]*[:：]\s*(\/\S+)/i);
    if (aflMatch?.[1]) return aflMatch[1].trim();
  }
  return '';
});

const fuzzerName = computed(() => {
  if (props.protocolType === 'MQTT' && props.implementation === 'SOL') return 'AFLNET';
  if (props.protocolType === 'MQTT') return 'MBFuzzer';
  return 'AFLNET';
});

const pocDownloadHref = computed(() => {
  const apiBase = import.meta.env.VITE_GLOB_API_URL || '/api';
  const params = new URLSearchParams({
    implementation: props.implementation,
    protocol: props.protocolType,
  });
  if (crashLogPath.value) params.set('crashLogPath', crashLogPath.value);
  return `${apiBase}/protocol-compliance/fuzzing/aflnet-result/download?${params.toString()}`;
});

const verificationStatus = computed(() => {
  if (props.stats.crashes > 0) return '已触发崩溃验证';
  return '等待崩溃证据';
});

function buildFunctionsFromEvidence(functions: CodeLocateFunctionSlice[]) {
  return functions
    .filter((fn) => fn.name.trim())
    .map((fn) => ({
      file: fn.path || props.evidence?.targetFile || '-',
      line: fn.targetLine ? String(fn.targetLine) : props.evidence?.targetLine || '-',
      name: fn.name,
    }));
}

function formatNumber(value: number) {
  return value.toLocaleString();
}
</script>

<template>
  <Card class="stage-card result-stage" :bordered="false">
    <template #title>
      <div class="stage-title">
        <IconifyIcon icon="mdi:clipboard-check-outline" />
        <span>结果验证</span>
        <small>{{ verificationStatus }}</small>
      </div>
    </template>
    <template #extra>
      <Tag :color="stats.crashes > 0 ? 'error' : 'default'">
        {{ stats.crashes > 0 ? '发现崩溃' : '等待结果' }}
      </Tag>
    </template>

    <div class="verification-layout">
      <section class="summary-band">
        <div class="summary-tile summary-tile--danger">
          <strong>{{ formatNumber(stats.crashes) }}</strong>
          <span>崩溃数</span>
        </div>
        <div class="summary-tile summary-tile--warn">
          <strong>{{ formatNumber(stats.hangs) }}</strong>
          <span>挂起数</span>
        </div>
        <div class="summary-tile summary-tile--blue">
          <strong>{{ formatNumber(stats.paths) }}</strong>
          <span>覆盖路径</span>
        </div>
        <div class="summary-tile summary-tile--green">
          <strong>{{ elapsed }}</strong>
          <span>运行时长</span>
        </div>
      </section>

      <section class="verification-grid">
        <section class="panel panel--rule">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">规则描述</span>
              <h3>触发规则</h3>
            </div>
            <Tag color="blue">{{ protocolType }}</Tag>
          </div>
          <p class="rule-text">{{ ruleDescription }}</p>
        </section>

        <section class="panel panel--reason">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">违规原因</span>
              <h3>定位结论</h3>
            </div>
            <Tag :color="evidence ? 'success' : 'default'">
              {{ evidence ? '代码定位已接入' : '待定位补充' }}
            </Tag>
          </div>
          <p class="reason-text">{{ violationReason }}</p>
        </section>

        <section class="panel panel--functions">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">相关函数</span>
              <h3>代码定位输出</h3>
            </div>
            <Tag color="blue">{{ relatedFunctions.length }} 个函数</Tag>
          </div>
          <div v-if="relatedFunctions.length > 0" class="function-list">
            <div v-for="fn in relatedFunctions" :key="`${fn.file}:${fn.name}`" class="function-row">
              <div class="function-icon">
                <IconifyIcon icon="mdi:function-variant" />
              </div>
              <div>
                <strong>{{ fn.name }}</strong>
                <span>{{ fn.file }}:{{ fn.line }}</span>
              </div>
            </div>
          </div>
          <Empty
            v-else
            description="等待代码定位输出相关函数"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
          />
        </section>

        <section class="panel panel--assert">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">代码插断言生成</span>
              <h3>插桩摘要</h3>
            </div>
            <Tag :color="assertResult || assertDiffContent ? 'success' : 'default'">
              {{ assertionSummary }}
            </Tag>
          </div>
          <div v-if="assertionLines.length > 0" class="assert-lines">
            <code v-for="line in assertionLines" :key="line">{{ line }}</code>
          </div>
          <Empty
            v-else
            description="等待断言生成模块输出插桩差异"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
          />
        </section>

        <section class="panel panel--poc">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">POC</span>
              <h3>{{ fuzzerName }} 运行结果</h3>
            </div>
            <Tag :color="stats.crashes > 0 ? 'error' : 'default'">
              {{ stats.crashes > 0 ? '可下载' : '未生成' }}
            </Tag>
          </div>
          <div class="poc-body">
            <div>
              <span>崩溃队列</span>
              <strong>{{ crashLogPath || '等待后端返回 AFLNET 输出路径' }}</strong>
            </div>
            <Button
              type="primary"
              :disabled="stats.crashes <= 0"
              :href="pocDownloadHref"
              target="_blank"
            >
              <template #icon><IconifyIcon icon="mdi:download" /></template>
              下载 POC
            </Button>
          </div>
        </section>
      </section>
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

.verification-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-band {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-tile {
  min-width: 0;
  min-height: 92px;
  padding: 16px;
  text-align: center;
  border: 1px solid transparent;
  border-radius: 8px;
}

.summary-tile strong {
  display: block;
  overflow: hidden;
  font-size: 28px;
  font-weight: 900;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-tile span {
  display: block;
  margin-top: 8px;
  font-size: 13px;
  color: #475569;
}

.summary-tile--danger {
  background: #fff5f7;
  border-color: #fecdd3;
}

.summary-tile--danger strong {
  color: #e11d48;
}

.summary-tile--warn {
  background: #fffbeb;
  border-color: #fde68a;
}

.summary-tile--warn strong {
  color: #d69e2e;
}

.summary-tile--blue {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.summary-tile--blue strong {
  color: #2563eb;
}

.summary-tile--green {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.summary-tile--green strong {
  color: #16a34a;
}

.verification-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 0.85fr);
  gap: 16px;
}

.panel {
  min-width: 0;
  padding: 16px;
  background: #fff;
  border: 1px solid #dbeafe;
  border-radius: 8px;
}

.panel--assert,
.panel--functions,
.panel--poc {
  grid-column: 1 / -1;
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
  font-size: 15px;
  font-weight: 800;
  color: #172033;
}

.panel-kicker {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  color: #64748b;
}

.rule-text,
.reason-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #334155;
  overflow-wrap: anywhere;
}

.function-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.function-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  min-width: 0;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.function-icon {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 30px;
  height: 30px;
  color: #1677ff;
  background: #eff6ff;
  border-radius: 8px;
}

.function-row strong,
.function-row span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.function-row strong {
  font-size: 14px;
  color: #111827;
}

.function-row span {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.assert-lines {
  display: grid;
  gap: 6px;
  padding: 12px;
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #0f172a;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.assert-lines code {
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.poc-body {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
}

.poc-body span,
.poc-body strong {
  display: block;
}

.poc-body span {
  font-size: 12px;
  color: #64748b;
}

.poc-body strong {
  max-width: 780px;
  margin-top: 4px;
  overflow: hidden;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  color: #172033;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1024px) {
  .summary-band,
  .verification-grid,
  .function-list {
    grid-template-columns: 1fr;
  }

  .poc-body {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
