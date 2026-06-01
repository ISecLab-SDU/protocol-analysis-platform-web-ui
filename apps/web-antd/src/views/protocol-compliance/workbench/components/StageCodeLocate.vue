<script setup lang="ts">
import { computed } from 'vue';

import { Card, Empty, Tag } from 'ant-design-vue';
import { IconifyIcon } from '@vben/icons';

import type {
  ProtocolExtractRuleItem,
  ProtocolStaticAnalysisResult,
  ProtocolStaticAnalysisComplianceStatus,
  ProtocolStaticAnalysisVerdict,
} from '#/api/protocol-compliance';

import { normalizeList } from '../utils';

interface Props {
  logHtml: string;
  result: null | ProtocolStaticAnalysisResult;
  rule: null | ProtocolExtractRuleItem;
  running: boolean;
}

const props = defineProps<Props>();

const verdicts = computed(() => props.result?.modelResponse?.verdicts ?? []);
const summary = computed(() => props.result?.modelResponse?.summary ?? null);

const verdictStats = computed(() => {
  if (summary.value) {
    return {
      compliant: summary.value.compliantCount,
      needsReview: summary.value.needsReviewCount,
      nonCompliant: summary.value.nonCompliantCount,
    };
  }
  const stats = { compliant: 0, needsReview: 0, nonCompliant: 0 };
  for (const verdict of verdicts.value) {
    if (verdict.compliance === 'compliant') stats.compliant += 1;
    else if (verdict.compliance === 'needs_review') stats.needsReview += 1;
    else if (verdict.compliance === 'non_compliant') stats.nonCompliant += 1;
  }
  return stats;
});

const primaryVerdict = computed(() => {
  return (
    verdicts.value.find((verdict) => verdict.compliance === 'non_compliant') ??
    verdicts.value.find((verdict) => verdict.compliance === 'needs_review') ??
    verdicts.value[0] ??
    null
  );
});

const ruleText = computed(() => {
  return (
    props.rule?.rule ||
    props.rule?.description ||
    primaryVerdict.value?.relatedRule?.requirement ||
    '等待规则证据输入'
  );
});

const ruleSource = computed(() => {
  return primaryVerdict.value?.relatedRule?.source || '协议规则集';
});

const targetFile = computed(() => {
  return (
    primaryVerdict.value?.location?.file ||
    props.result?.inputs?.codeFileName ||
    '待定位'
  );
});

const targetLine = computed(() => {
  const range = primaryVerdict.value?.lineRange;
  if (!range) return '-';
  return range[0] === range[1] ? String(range[0]) : `${range[0]}-${range[1]}`;
});

const candidateFunctionCount = computed(() => {
  const functions = new Set(
    verdicts.value
      .map((verdict) => verdict.location?.function || verdict.location?.file)
      .filter(Boolean),
  );
  return functions.size || verdicts.value.length;
});

const keySliceCount = computed(() => {
  return verdictStats.value.nonCompliant + verdictStats.value.needsReview;
});

const relatedVariableCount = computed(() => {
  const fields = new Set([
    ...normalizeList(props.rule?.req_fields),
    ...normalizeList(props.rule?.res_fields),
  ]);
  return fields.size;
});

const codeRows = computed(() => {
  const verdict = primaryVerdict.value;
  const lineBase = Array.isArray(verdict?.lineRange) ? verdict.lineRange[0] : 315;
  const statusText = verdict ? complianceLabel(verdict.compliance) : '定位中';
  return [
    { emphasis: false, line: lineBase, text: `// ${ruleSource.value}` },
    { emphasis: false, line: lineBase + 1, text: `target_rule = "${ruleText.value}"` },
    { emphasis: false, line: lineBase + 2, text: `target_file = "${targetFile.value}"` },
    { emphasis: true, line: lineBase + 3, text: `analysis_verdict = "${statusText}"` },
    { emphasis: false, line: lineBase + 4, text: verdict?.explanation || '等待静态分析返回代码上下文...' },
  ];
});

const visibleVerdicts = computed(() => verdicts.value.slice(0, 4));

function complianceLabel(value: ProtocolStaticAnalysisComplianceStatus) {
  if (value === 'compliant') return '合规';
  if (value === 'non_compliant') return '不合规';
  return '待审查';
}

function complianceColor(value: ProtocolStaticAnalysisComplianceStatus) {
  if (value === 'compliant') return 'success';
  if (value === 'non_compliant') return 'error';
  return 'warning';
}

function formatLocation(verdict: ProtocolStaticAnalysisVerdict) {
  const file = verdict.location?.file || '-';
  const fn = verdict.location?.function ? `#${verdict.location.function}` : '';
  if (!verdict.lineRange) return `${file}${fn}`;
  return `${file}:${verdict.lineRange[0]}-${verdict.lineRange[1]}${fn}`;
}
</script>

<template>
  <Card class="stage-card locate-stage" :bordered="false">
    <template #title>
      <div class="stage-title">
        <IconifyIcon icon="mdi:file-search-outline" />
        <span>代码定位</span>
        <small>{{ running ? '进行中' : result ? '已完成' : '等待中' }}</small>
      </div>
    </template>
    <template #extra>
      <Tag v-if="running" color="processing">进行中</Tag>
      <Tag v-else-if="result" color="success">已完成</Tag>
      <Tag v-else color="default">等待中</Tag>
    </template>

    <div v-if="logHtml || running || result" class="locate-layout">
      <aside class="metric-rail">
        <div class="metric-item">
          <span>候选函数</span>
          <strong>{{ candidateFunctionCount }}</strong>
        </div>
        <div class="metric-item">
          <span>关键切片</span>
          <strong>{{ keySliceCount }}</strong>
        </div>
        <div class="metric-item">
          <span>相关变量</span>
          <strong>{{ relatedVariableCount }}</strong>
        </div>
      </aside>

      <section class="code-panel">
        <div class="panel-meta">
          <div>
            <span>目标文件:</span>
            <code>{{ targetFile }}</code>
          </div>
          <div>
            <span>关键位置:</span>
            <code>{{ targetLine }}</code>
          </div>
        </div>

        <div v-if="logHtml && !result" class="log-content" v-html="logHtml || '等待日志输出...'" />
        <div v-else class="code-window">
          <div
            v-for="row in codeRows"
            :key="row.line"
            class="code-row"
            :class="{ 'code-row--emphasis': row.emphasis }"
          >
            <span class="line-no">{{ row.line }}</span>
            <span class="line-text">{{ row.text }}</span>
          </div>
        </div>
      </section>

      <aside class="evidence-panel">
        <div class="evidence-title">
          规则证据
          <span>({{ ruleSource }})</span>
        </div>
        <blockquote>{{ ruleText }}</blockquote>
        <dl class="evidence-list">
          <div>
            <dt>约束类型:</dt>
            <dd>{{ summary?.overallStatus ? complianceLabel(summary.overallStatus) : '待判定' }}</dd>
          </div>
          <div>
            <dt>源数据:</dt>
            <dd>{{ normalizeList(rule?.req_type)[0] || normalizeList(rule?.res_type)[0] || '-' }}</dd>
          </div>
          <div>
            <dt>目标行为:</dt>
            <dd>{{ ruleText }}</dd>
          </div>
        </dl>
      </aside>
    </div>

    <section v-if="result && visibleVerdicts.length > 0" class="verdict-section">
      <div class="verdict-summary">
        <div class="verdict-stat verdict-stat--ok">
          <IconifyIcon icon="mdi:check-circle-outline" />
          <span>合规</span>
          <strong>{{ verdictStats.compliant }}</strong>
        </div>
        <div class="verdict-stat verdict-stat--warn">
          <IconifyIcon icon="mdi:alert-outline" />
          <span>待审查</span>
          <strong>{{ verdictStats.needsReview }}</strong>
        </div>
        <div class="verdict-stat verdict-stat--error">
          <IconifyIcon icon="mdi:close-circle-outline" />
          <span>不合规</span>
          <strong>{{ verdictStats.nonCompliant }}</strong>
        </div>
      </div>

      <div class="verdict-list">
        <article
          v-for="verdict in visibleVerdicts"
          :key="verdict.findingId"
          class="verdict-item"
        >
          <div class="verdict-head">
            <Tag :color="complianceColor(verdict.compliance)">
              {{ complianceLabel(verdict.compliance) }}
            </Tag>
            <code>{{ formatLocation(verdict) }}</code>
          </div>
          <p>{{ verdict.explanation }}</p>
          <p v-if="verdict.recommendation" class="recommendation">
            {{ verdict.recommendation }}
          </p>
        </article>
      </div>
    </section>

    <Empty
      v-else-if="!logHtml && !running && !result"
      description="等待代码定位阶段开始"
      :image="Empty.PRESENTED_IMAGE_SIMPLE"
    />
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

.locate-layout {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr) 360px;
  gap: 18px;
}

.metric-rail,
.code-panel,
.evidence-panel {
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}

.metric-rail {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 18px;
}

.metric-item + .metric-item {
  margin-top: 28px;
}

.metric-item span {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: #64748b;
}

.metric-item strong {
  font-size: 30px;
  line-height: 1;
  color: #0f172a;
}

.code-panel {
  min-width: 0;
  padding: 18px;
}

.panel-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 28px;
  margin-bottom: 14px;
  font-size: 13px;
  color: #475569;
}

.panel-meta code {
  margin-left: 8px;
  color: #172033;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
}

.log-content,
.code-window {
  max-height: 280px;
  padding: 12px 0;
  overflow: auto;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 13px;
  line-height: 1.65;
  color: #334155;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.log-content {
  padding: 12px;
  color: #dbeafe;
  background: #0f172a;
}

.code-row {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  min-height: 28px;
  padding: 0 14px;
}

.code-row--emphasis {
  color: #0b5cad;
  background: #e8f2ff;
}

.line-no {
  color: #94a3b8;
  user-select: none;
}

.line-text {
  min-width: 0;
  overflow-wrap: anywhere;
}

.evidence-panel {
  padding: 18px;
}

.evidence-title {
  margin-bottom: 14px;
  font-size: 16px;
  font-weight: 700;
}

.evidence-title span {
  font-size: 13px;
  color: #64748b;
}

.evidence-panel blockquote {
  margin: 0 0 16px;
  padding: 16px;
  font-size: 14px;
  line-height: 1.65;
  color: #172033;
  background: #f3f7ff;
  border: 1px solid #e2ecff;
  border-left: 4px solid #1677ff;
  border-radius: 8px;
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 0;
  font-size: 13px;
}

.evidence-list > div {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 10px;
}

.evidence-list dt {
  color: #64748b;
}

.evidence-list dd {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
  color: #172033;
}

.verdict-section {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 18px;
  margin-top: 18px;
}

.verdict-summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.verdict-stat {
  display: grid;
  grid-template-columns: 22px 1fr auto;
  gap: 8px;
  align-items: center;
  min-height: 48px;
  padding: 10px 12px;
  border-radius: 8px;
}

.verdict-stat--ok {
  color: #0f9f6e;
  background: #f0fdf4;
}

.verdict-stat--warn {
  color: #d97706;
  background: #fffaf0;
}

.verdict-stat--error {
  color: #dc2626;
  background: #fff5f5;
}

.verdict-stat strong {
  font-size: 20px;
}

.verdict-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.verdict-item {
  min-width: 0;
  padding: 14px;
  background: #fff;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}

.verdict-head {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}

.verdict-head code {
  min-width: 0;
  overflow: hidden;
  color: #334155;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: #f8fafc;
  border-radius: 4px;
}

.verdict-item p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #334155;
}

.verdict-item .recommendation {
  margin-top: 8px;
  color: #0b5cad;
}

@media (max-width: 1280px) {
  .locate-layout {
    grid-template-columns: 160px minmax(0, 1fr);
  }

  .evidence-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 860px) {
  .locate-layout,
  .verdict-section,
  .verdict-list {
    grid-template-columns: 1fr;
  }

  .metric-rail {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .metric-item + .metric-item {
    margin-top: 0;
  }
}
</style>
