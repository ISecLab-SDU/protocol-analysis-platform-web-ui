<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import { Card, Empty, Tag } from 'ant-design-vue';
import { IconifyIcon } from '@vben/icons';

import type {
  ProtocolExtractRuleItem,
  ProtocolStaticAnalysisComplianceStatus,
  ProtocolStaticAnalysisResult,
} from '#/api/protocol-compliance';

import type { CodeLocateEvidence, CodeLocateFunctionSlice } from '../types';
import { normalizeList } from '../utils';

interface Props {
  evidence: CodeLocateEvidence | null;
  logHtml: string;
  logText: string;
  result: null | ProtocolStaticAnalysisResult;
  rule: null | ProtocolExtractRuleItem;
  running: boolean;
}

interface LogLine {
  id: string;
  kind: 'error' | 'function' | 'normal' | 'path' | 'slice' | 'summary';
  source: string;
  stage: string;
  text: string;
  time: string;
}

const props = defineProps<Props>();

const selectedFunctionName = ref('');
const logBodyRef = ref<HTMLElement | null>(null);

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

const evidenceStatus = computed<null | ProtocolStaticAnalysisComplianceStatus>(() => {
  const label = props.evidence?.resultLabel?.toLowerCase() || '';
  if (/no[_\s-]?violation|无违规/.test(label)) return 'compliant';
  if (/violation|违规|不合规/.test(label)) return 'non_compliant';
  if (/合规/.test(label)) return 'compliant';
  if (/unknown|待审查|复核/.test(label)) return 'needs_review';
  return null;
});

const overallStatus = computed<ProtocolStaticAnalysisComplianceStatus>(() => {
  return (
    summary.value?.overallStatus ||
    primaryVerdict.value?.compliance ||
    evidenceStatus.value ||
    'needs_review'
  );
});

const conclusionTitle = computed(() => {
  if (overallStatus.value === 'non_compliant') return '发现协议违规';
  if (overallStatus.value === 'compliant') return '未发现违规';
  return '需要人工复核';
});

const conclusionIcon = computed(() => {
  if (overallStatus.value === 'non_compliant') return 'mdi:close-octagon-outline';
  if (overallStatus.value === 'compliant') return 'mdi:check-decagram-outline';
  return 'mdi:alert-outline';
});

const ruleId = computed(() => {
  const optionId = (props.rule as { id?: string } | null)?.id;
  return (
    primaryVerdict.value?.relatedRule?.id ||
    optionId ||
    ruleText.value.match(/\[(MQTT-[^\]]+)\]/i)?.[1] ||
    '当前规则'
  );
});

const ruleText = computed(() => {
  return (
    props.evidence?.ruleText ||
    props.rule?.rule ||
    props.rule?.description ||
    primaryVerdict.value?.relatedRule?.requirement ||
    '等待规则证据输入'
  );
});

const violationReason = computed(() => {
  return (
    props.evidence?.violationReason ||
    primaryVerdict.value?.explanation ||
    summary.value?.notes ||
    '等待静态分析返回违规原因'
  );
});

const ruleSource = computed(() => {
  return props.evidence?.source || primaryVerdict.value?.relatedRule?.source || '协议规则集';
});

const targetFile = computed(() => {
  return (
    props.evidence?.targetFile ||
    primaryVerdict.value?.location?.file ||
    props.result?.inputs?.codeFileName ||
    '待定位'
  );
});

const targetLine = computed(() => {
  if (props.evidence?.targetLine) return props.evidence.targetLine;
  const range = primaryVerdict.value?.lineRange;
  if (!range) return '-';
  return range[0] === range[1] ? String(range[0]) : `${range[0]}-${range[1]}`;
});

const functionRecords = computed<CodeLocateFunctionSlice[]>(() => {
  const evidenceFunctions = props.evidence?.functions?.filter((fn) => fn.name.trim()) ?? [];
  if (evidenceFunctions.length > 0) return evidenceFunctions;

  const records = new Map<string, CodeLocateFunctionSlice>();
  for (const verdict of verdicts.value) {
    const name = verdict.location?.function || verdict.location?.file;
    if (!name || records.has(name)) continue;
    records.set(name, {
      codeRows: [],
      name,
      path: verdict.location?.file,
      targetLine: verdict.lineRange?.[0],
    });
  }
  return [...records.values()];
});

const selectedFunction = computed(() => {
  return (
    functionRecords.value.find((fn) => fn.name === selectedFunctionName.value) ??
    functionRecords.value[0] ??
    null
  );
});

const candidateFunctionCount = computed(() => {
  if (props.evidence) return props.evidence.candidateFunctionCount;
  return functionRecords.value.length || verdicts.value.length;
});

const keySliceCount = computed(() => {
  if (props.evidence) return props.evidence.keySliceCount;
  return functionRecords.value.filter((fn) => fn.codeRows.length > 0).length ||
    verdictStats.value.nonCompliant + verdictStats.value.needsReview;
});

const relatedVariableCount = computed(() => {
  if (props.evidence) return props.evidence.relatedVariableCount;
  const fields = new Set([
    ...normalizeList(props.rule?.req_fields),
    ...normalizeList(props.rule?.res_fields),
  ]);
  return fields.size;
});

const fallbackCodeRows = computed(() => {
  if (props.evidence?.codeRows.length) return props.evidence.codeRows;
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

const detailRows = computed(() => {
  if (selectedFunction.value) return selectedFunction.value.codeRows;
  if (!props.evidence && !props.result) return [];
  return fallbackCodeRows.value;
});

const detailTitle = computed(() => {
  return selectedFunction.value?.name || primaryVerdict.value?.location?.function || '等待函数切片';
});

const detailPath = computed(() => {
  return selectedFunction.value?.path || targetFile.value;
});

const detailLine = computed(() => {
  return selectedFunction.value?.targetLine || targetLine.value;
});

const evidenceFunctionSlices = computed(() => {
  return functionRecords.value.filter((fn) => fn.codeRows.length > 0);
});

const evidenceRows = computed(() => {
  if (props.evidence?.codeRows.length) return props.evidence.codeRows;
  if (detailRows.value.length > 0) return detailRows.value;
  if (props.result || props.evidence) return fallbackCodeRows.value;
  return [];
});

const stageStateText = computed(() => {
  if (props.running) return '进行中';
  if (props.result || props.evidence) return '已完成';
  return '等待中';
});

const logLines = computed<LogLine[]>(() => {
  const rawLines = props.logText
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.trim().length > 0);
  return rawLines.slice(-220).map(parseLogLine);
});

const hasContent = computed(() => {
  return Boolean(props.logText || props.logHtml || props.running || props.result || props.evidence);
});

watch(
  functionRecords,
  (records) => {
    if (records.length === 0) {
      selectedFunctionName.value = '';
      return;
    }
    if (!records.some((record) => record.name === selectedFunctionName.value)) {
      selectedFunctionName.value = records[0]?.name ?? '';
    }
  },
  { immediate: true },
);

watch(
  () => logLines.value.length,
  async () => {
    await nextTick();
    const target = logBodyRef.value;
    if (!target) return;
    target.scrollTop = target.scrollHeight;
  },
);

function parseLogLine(raw: string, index: number): LogLine {
  let rest = raw.trim();
  let stage = '';
  let time = '';
  let source = '';

  const leadingStage = rest.match(/^\(([^)]+)\)\s*(.*)$/);
  if (leadingStage?.[1]) {
    stage = leadingStage[1];
    rest = leadingStage[2] ?? '';
  }

  const timeMatch = rest.match(/^\[([^\]]+)\]\s*(.*)$/);
  if (timeMatch?.[1]) {
    time = timeMatch[1];
    rest = timeMatch[2] ?? '';
  }

  const inlineStage = rest.match(/^\(([^)]+)\)\s*(.*)$/);
  if (inlineStage?.[1]) {
    stage = stage || inlineStage[1];
    rest = inlineStage[2] ?? '';
  }

  if (!/^(Function|Path|func):|\d+\s+/.test(rest)) {
    const sourceMatch = rest.match(/^([^\s:]+(?::[^\s:]+)?):\s*(.*)$/);
    if (sourceMatch?.[1]) {
      source = sourceMatch[1];
      rest = sourceMatch[2] ?? '';
    }
  }

  return {
    id: `${index}-${raw}`,
    kind: classifyLogLine(rest),
    source,
    stage,
    text: rest || raw,
    time,
  };
}

function classifyLogLine(text: string): LogLine['kind'] {
  if (/error|failed|失败/i.test(text)) return 'error';
  if (/Extracted\s+\d+\s+functions/i.test(text)) return 'summary';
  if (/^func:/i.test(text)) return 'function';
  if (/^Function:/i.test(text)) return 'slice';
  if (/^Path:/i.test(text)) return 'path';
  return 'normal';
}

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

function shortPath(path?: string) {
  if (!path) return '待定位';
  const normalized = path.replaceAll('\\', '/');
  return normalized.split('/').filter(Boolean).pop() || path;
}

function formatFunctionLocation(fn: CodeLocateFunctionSlice) {
  const path = fn.path ? shortPath(fn.path) : targetFile.value;
  if (!fn.targetLine || fn.targetLine === '-') return path;
  return `${path}:${fn.targetLine}`;
}

function formatEvidencePath(fn: CodeLocateFunctionSlice) {
  const path = fn.path || detailPath.value;
  if (!fn.targetLine || fn.targetLine === '-') return path;
  return `${path}:${fn.targetLine}`;
}

function sliceStatus(fn: CodeLocateFunctionSlice) {
  return fn.codeRows.length > 0 ? '已生成切片' : '已发现';
}
</script>

<template>
  <Card class="stage-card locate-stage" :bordered="false">
    <template #title>
      <div class="stage-title">
        <IconifyIcon icon="mdi:file-search-outline" />
        <span>代码定位</span>
        <small>{{ stageStateText }}</small>
      </div>
    </template>
    <template #extra>
      <Tag v-if="running" color="processing">进行中</Tag>
      <Tag v-else-if="result || evidence" color="success">已完成</Tag>
      <Tag v-else color="default">等待中</Tag>
    </template>

    <div v-if="hasContent" class="locate-workspace">
      <section
        v-if="result || evidence"
        class="result-hero"
        :class="`result-hero--${overallStatus}`"
      >
        <div class="result-rail">
          <div class="result-status">
            <IconifyIcon :icon="conclusionIcon" />
            <div>
              <span>检测结论</span>
              <strong>{{ conclusionTitle }}</strong>
            </div>
          </div>

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
        </div>

        <div class="result-body">
          <div class="result-head">
            <div>
              <span class="panel-kicker">代码定位检测阶段结果</span>
              <h3>{{ ruleId }}</h3>
            </div>
            <Tag :color="complianceColor(overallStatus)">
              {{ complianceLabel(overallStatus) }}
            </Tag>
          </div>

          <div class="finding-grid">
            <section class="finding-block finding-block--rule">
              <div class="finding-label">
                <IconifyIcon icon="mdi:clipboard-check-outline" />
                <span>检测规则</span>
              </div>
              <p>{{ ruleText }}</p>
            </section>

            <section class="finding-block finding-block--reason">
              <div class="finding-label">
                <IconifyIcon icon="mdi:alert-circle-outline" />
                <span>违规原因</span>
              </div>
              <p>{{ violationReason }}</p>
            </section>
          </div>

          <section class="evidence-block">
            <div class="evidence-head">
              <div class="finding-label">
                <IconifyIcon icon="mdi:source-branch" />
                <span>判定依据</span>
              </div>
              <Tag color="default">{{ ruleSource }}</Tag>
            </div>

            <div v-if="evidenceFunctionSlices.length > 0" class="evidence-slices">
              <article
                v-for="fn in evidenceFunctionSlices"
                :key="fn.name"
                class="evidence-slice"
              >
                <div class="evidence-slice-head">
                  <span>Function: {{ fn.name }}</span>
                  <code>Path: {{ formatEvidencePath(fn) }}</code>
                </div>
                <div v-if="fn.codeRows.length > 0" class="evidence-code">
                  <div
                    v-for="(row, idx) in fn.codeRows"
                    :key="`${fn.name}-${row.line}-${idx}`"
                    class="code-row"
                    :class="{ 'code-row--emphasis': row.emphasis }"
                  >
                    <span class="line-no">{{ row.line }}</span>
                    <span class="line-text">{{ row.text }}</span>
                  </div>
                </div>
              </article>
            </div>

            <div v-else-if="evidenceRows.length > 0" class="evidence-code">
              <div
                v-for="(row, idx) in evidenceRows"
                :key="`${row.line}-${idx}`"
                class="code-row"
                :class="{ 'code-row--emphasis': row.emphasis }"
              >
                <span class="line-no">{{ row.line }}</span>
                <span class="line-text">{{ row.text }}</span>
              </div>
            </div>

            <Empty
              v-else
              description="等待静态分析返回判定依据"
              :image="Empty.PRESENTED_IMAGE_SIMPLE"
            />
          </section>
        </div>
      </section>

      <section class="summary-strip">
        <div class="summary-item">
          <span>候选函数</span>
          <strong>{{ candidateFunctionCount }}</strong>
        </div>
        <div class="summary-item">
          <span>已生成切片</span>
          <strong>{{ keySliceCount }}</strong>
        </div>
        <div class="summary-item">
          <span>相关变量</span>
          <strong>{{ relatedVariableCount }}</strong>
        </div>
        <div class="summary-rule">
          <span>规则证据</span>
          <p>{{ ruleText }}</p>
        </div>
      </section>

      <section class="observe-grid">
        <section class="live-log-panel">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">实时运行轨迹</span>
              <h3>日志输出</h3>
            </div>
            <Tag :color="running ? 'processing' : 'default'">
              {{ running ? '自动滚动' : `${logLines.length} 行` }}
            </Tag>
          </div>

          <div ref="logBodyRef" class="live-log">
            <div
              v-for="line in logLines"
              :key="line.id"
              class="log-line"
              :class="`log-line--${line.kind}`"
            >
              <span class="log-time">{{ line.time || '--:--:--' }}</span>
              <span v-if="line.stage" class="log-chip">{{ line.stage }}</span>
              <span v-if="line.source" class="log-chip log-chip--source">{{ line.source }}</span>
              <span class="log-text">{{ line.text }}</span>
            </div>
            <div v-if="logLines.length === 0" class="log-empty">
              {{ running ? '等待日志输出...' : '暂无日志输出' }}
            </div>
          </div>
        </section>

        <section class="discovery-panel">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">检测到的相关内容</span>
              <h3>函数发现记录</h3>
            </div>
            <Tag color="blue">{{ functionRecords.length }} 个函数</Tag>
          </div>

          <div v-if="functionRecords.length > 0" class="function-list">
            <button
              v-for="fn in functionRecords"
              :key="fn.name"
              class="function-item"
              :class="{ 'function-item--active': selectedFunction?.name === fn.name }"
              type="button"
              :aria-pressed="selectedFunction?.name === fn.name"
              @click="selectedFunctionName = fn.name"
            >
              <span class="function-main">
                <strong>{{ fn.name }}</strong>
                <small>{{ formatFunctionLocation(fn) }}</small>
              </span>
              <Tag :color="fn.codeRows.length > 0 ? 'success' : 'default'">
                {{ sliceStatus(fn) }}
              </Tag>
            </button>
          </div>
          <Empty
            v-else
            description="等待发现相关函数"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
          />
        </section>
      </section>

      <section class="slice-panel">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">点击函数查看证据</span>
            <h3>{{ detailTitle }}</h3>
          </div>
          <Tag v-if="selectedFunction" :color="detailRows.length > 0 ? 'success' : 'default'">
            {{ detailRows.length > 0 ? '切片已生成' : '等待切片' }}
          </Tag>
        </div>

        <div class="slice-meta">
          <div>
            <span>Path:</span>
            <code>{{ detailPath }}</code>
          </div>
          <div>
            <span>Line:</span>
            <code>{{ detailLine }}</code>
          </div>
          <div>
            <span>Source:</span>
            <code>{{ ruleSource }}{{ evidence?.resultLabel ? ` · ${evidence.resultLabel}` : '' }}</code>
          </div>
        </div>

        <div v-if="detailRows.length > 0" class="code-window">
          <div
            v-for="(row, idx) in detailRows"
            :key="`${row.line}-${idx}`"
            class="code-row"
            :class="{ 'code-row--emphasis': row.emphasis }"
          >
            <span class="line-no">{{ row.line }}</span>
            <span class="line-text">{{ row.text }}</span>
          </div>
        </div>
        <Empty
          v-else
          description="已记录函数名，等待切片日志输出"
          :image="Empty.PRESENTED_IMAGE_SIMPLE"
        />
      </section>
    </div>

    <Empty
      v-else-if="!hasContent"
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

.locate-workspace {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-hero {
  display: grid;
  grid-template-columns: 196px minmax(0, 1fr);
  gap: 18px;
  padding: 18px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-left: 4px solid #f59e0b;
  border-radius: 8px;
  box-shadow: 0 12px 30px rgb(15 23 42 / 6%);
}

.result-hero--compliant {
  border-left-color: #22a06b;
}

.result-hero--needs_review {
  border-left-color: #f59e0b;
}

.result-hero--non_compliant {
  border-left-color: #ef4444;
}

.result-rail {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.result-status {
  display: flex;
  gap: 10px;
  align-items: center;
  min-height: 66px;
  padding: 12px;
  color: #172033;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.result-status > :first-child {
  flex: 0 0 auto;
  font-size: 28px;
  color: #1677ff;
}

.result-hero--compliant .result-status > :first-child {
  color: #22a06b;
}

.result-hero--needs_review .result-status > :first-child {
  color: #d97706;
}

.result-hero--non_compliant .result-status > :first-child {
  color: #ef4444;
}

.result-status span,
.finding-label,
.evidence-head {
  font-size: 12px;
  color: #64748b;
}

.result-status strong {
  display: block;
  margin-top: 2px;
  font-size: 18px;
  color: #111827;
}

.result-body {
  min-width: 0;
}

.result-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.result-head h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: #111827;
}

.finding-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.finding-block,
.evidence-block {
  min-width: 0;
  padding: 14px;
  background: #fbfdff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.finding-label {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 8px;
  font-weight: 700;
}

.finding-label :first-child {
  font-size: 16px;
  color: #1677ff;
}

.finding-block--reason .finding-label :first-child {
  color: #ef4444;
}

.finding-block p {
  margin: 0;
  font-size: 14px;
  line-height: 1.65;
  color: #253044;
  overflow-wrap: anywhere;
}

.evidence-head {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.evidence-slices {
  display: flex;
  max-height: 390px;
  overflow: auto;
  flex-direction: column;
  gap: 10px;
}

.evidence-slice {
  min-width: 0;
  overflow: hidden;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.evidence-slice-head {
  display: grid;
  grid-template-columns: minmax(160px, 0.35fr) minmax(0, 0.65fr);
  gap: 10px;
  padding: 10px 12px;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 12px;
  color: #172033;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.evidence-slice-head span,
.evidence-slice-head code {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.evidence-slice-head code {
  color: #475569;
  background: transparent;
}

.evidence-code {
  max-height: 360px;
  padding: 8px 0;
  overflow: auto;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #334155;
  background: #fff;
}

.evidence-block > .evidence-code {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.summary-strip {
  display: grid;
  grid-template-columns: 150px 150px 150px minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}

.summary-item,
.summary-rule {
  min-width: 0;
  padding: 14px 16px;
  background: #fff;
}

.summary-item + .summary-item,
.summary-rule {
  border-left: 1px solid var(--ant-color-border-secondary);
}

.summary-item span,
.summary-rule span,
.panel-kicker {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  color: #64748b;
}

.summary-item strong {
  font-size: 26px;
  line-height: 1;
  color: #111827;
}

.summary-rule p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  font-size: 13px;
  line-height: 1.55;
  color: #253044;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.observe-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
  gap: 16px;
}

.live-log-panel,
.discovery-panel,
.slice-panel {
  min-width: 0;
  padding: 16px;
  background: #fff;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
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
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.live-log {
  height: 360px;
  padding: 10px 0;
  overflow: auto;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 12px;
  line-height: 1.6;
  background: #fbfdff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.log-line {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  min-height: 26px;
  padding: 3px 12px;
  color: #334155;
}

.log-line--summary {
  color: #0b5cad;
  background: #eef6ff;
}

.log-line--function,
.log-line--slice {
  color: #0f766e;
  background: #f0fdfa;
}

.log-line--path {
  color: #7c3aed;
  background: #f8f5ff;
}

.log-line--error {
  color: #dc2626;
  background: #fff5f5;
}

.log-time {
  flex: 0 0 70px;
  color: #64748b;
  user-select: none;
}

.log-chip {
  flex: 0 0 auto;
  max-width: 130px;
  padding: 0 6px;
  overflow: hidden;
  color: #475569;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: #eef2f7;
  border-radius: 4px;
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
  color: #64748b;
}

.function-list {
  display: flex;
  max-height: 360px;
  overflow: auto;
  flex-direction: column;
  gap: 8px;
}

.function-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  width: 100%;
  min-height: 58px;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.function-item:hover,
.function-item--active {
  background: #f7fbff;
  border-color: #91caff;
}

.function-main {
  min-width: 0;
}

.function-main strong,
.function-main small {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.function-main strong {
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 13px;
  color: #111827;
}

.function-main small {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.slice-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #475569;
}

.slice-meta div {
  min-width: 0;
}

.slice-meta code {
  margin-left: 6px;
  color: #172033;
  overflow-wrap: anywhere;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
}

.code-window {
  max-height: 360px;
  padding: 10px 0;
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

.code-row {
  display: grid;
  grid-template-columns: 62px minmax(0, 1fr);
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
  white-space: pre-wrap;
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

@media (max-width: 1280px) {
  .result-hero,
  .finding-grid {
    grid-template-columns: 1fr;
  }

  .result-rail {
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr);
  }

  .verdict-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .summary-strip {
    grid-template-columns: repeat(3, minmax(120px, 1fr));
  }

  .summary-rule {
    grid-column: 1 / -1;
    border-top: 1px solid var(--ant-color-border-secondary);
    border-left: 0;
  }

  .observe-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .summary-strip,
  .result-rail,
  .verdict-summary,
  .evidence-slice-head {
    grid-template-columns: 1fr;
  }

  .summary-item + .summary-item,
  .summary-rule {
    border-top: 1px solid var(--ant-color-border-secondary);
    border-left: 0;
  }

  .log-line {
    flex-wrap: wrap;
  }

  .log-text {
    flex-basis: 100%;
  }
}
</style>
