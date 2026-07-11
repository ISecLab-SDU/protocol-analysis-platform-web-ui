<script setup lang="ts">
import { computed, ref } from 'vue';

import { Button, Card, Empty, message, Tag } from 'ant-design-vue';
import { IconifyIcon } from '@vben/icons';

import type {
  ProtocolAssertGenerationResult,
  ProtocolExtractRuleItem,
  ProtocolStaticAnalysisResult,
} from '#/api/protocol-compliance';
import { downloadAflNetPoc } from '#/api/protocol-compliance';

import type { CodeLocateEvidence, CodeLocateFunctionSlice } from '../types';

interface FuzzLogEntry {
  id: number;
  level: 'ERROR' | 'INFO' | 'STATS' | 'WARN';
  text: string;
}

interface Props {
  assertDiffContent: string;
  assertResult: ProtocolAssertGenerationResult | null;
  evidence: CodeLocateEvidence | null;
  implementation: string;
  logs: FuzzLogEntry[];
  pocPath?: string;
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

interface RenderedDiffLine {
  id: string;
  text: string;
  type: 'add' | 'context' | 'delete' | 'file' | 'hunk' | 'meta';
}

const props = defineProps<Props>();
const isPocDownloading = ref(false);

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

const evidenceFunctionSlices = computed(() => {
  return (props.evidence?.functions ?? []).filter((fn) => fn.name.trim() && fn.codeRows.length > 0);
});

const effectiveDiffContent = computed(() => {
  const rawContent =
    props.assertDiffContent ||
    props.assertResult?.instrumentation?.artifacts?.diffOutput?.content ||
    '';

  return normalizeDiffContent(rawContent);
});

const changedFileCount = computed(() => {
  const matches = effectiveDiffContent.value.match(/^diff --git\s+/gm);
  return matches?.length ?? 0;
});

const renderedDiffLines = computed<RenderedDiffLine[]>(() => {
  return effectiveDiffContent.value.split(/\r?\n/).map((text, index) => ({
    id: `${index}-${text}`,
    text,
    type: classifyDiffLine(text),
  }));
});

const assertionSummary = computed(() => {
  if (props.assertResult) {
    return `${props.assertResult.assertionCount} 条断言任务，${changedFileCount.value} 个文件发生插桩变更`;
  }
  if (effectiveDiffContent.value) {
    return `${changedFileCount.value} 个文件发生插桩变更`;
  }
  return '等待断言生成模块输出';
});

const crashLogPath = computed(() => {
  if (props.pocPath?.trim()) return props.pocPath.trim();

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

const verificationStatus = computed(() => {
  if (props.stats.crashes > 0) return '已触发崩溃验证';
  return '等待崩溃证据';
});

async function handleDownloadPoc() {
  if (props.stats.crashes <= 0 || isPocDownloading.value) return;

  isPocDownloading.value = true;
  try {
    const blob = await downloadAflNetPoc({
      crashLogPath: crashLogPath.value || undefined,
      implementation: props.implementation,
      protocol: props.protocolType,
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const timestamp = new Date()
      .toISOString()
      .replace(/[:.]/g, '-')
      .slice(0, 19);
    link.href = url;
    link.download = `${props.implementation || 'aflnet'}-poc-${timestamp}.zip`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (err: any) {
    message.error(err?.message || 'POC 下载失败，请检查 AFLNET 输出目录');
  } finally {
    isPocDownloading.value = false;
  }
}

function formatEvidencePath(fn: CodeLocateFunctionSlice) {
  const path = fn.path || props.evidence?.targetFile || '-';
  if (!fn.targetLine || fn.targetLine === '-') return path;
  return `${path}:${fn.targetLine}`;
}

function normalizeDiffContent(content: string) {
  const normalized = content.trimEnd();
  const diffStartIndex = normalized.search(/^diff --git\s+/m);
  if (diffStartIndex >= 0) return normalized.slice(diffStartIndex).trimEnd();

  const detailedDiffMatch = normalized.match(/^Detailed Diff:\s*$/m);
  if (detailedDiffMatch?.index !== undefined) {
    return normalized.slice(detailedDiffMatch.index + detailedDiffMatch[0].length).trim();
  }

  return normalized;
}

function classifyDiffLine(text: string): RenderedDiffLine['type'] {
  if (text.startsWith('diff --git') || text.startsWith('index ')) return 'meta';
  if (text.startsWith('@@')) return 'hunk';
  if (text.startsWith('--- ') || text.startsWith('+++ ')) return 'file';
  if (text.startsWith('+')) return 'add';
  if (text.startsWith('-')) return 'delete';
  return 'context';
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

        <section class="evidence-output-grid">
          <section class="panel panel--functions">
            <div class="panel-head">
              <div>
                <span class="panel-kicker">代码定位结果</span>
                <h3>相关函数源码</h3>
              </div>
              <Tag color="blue">{{ evidenceFunctionSlices.length }} 个函数</Tag>
            </div>

            <div v-if="evidenceFunctionSlices.length > 0" class="function-source-frame">
              <section
                v-for="fn in evidenceFunctionSlices"
                :key="fn.name"
                class="function-source-section"
              >
                <div class="function-source-head">
                  <strong>{{ fn.name }}</strong>
                  <code>{{ formatEvidencePath(fn) }}</code>
                </div>
                <div class="function-source-code">
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
              </section>
            </div>
            <Empty
              v-else
              description="等待生成相关函数源码"
              :image="Empty.PRESENTED_IMAGE_SIMPLE"
            />
          </section>

          <section class="panel panel--assert">
            <div class="panel-head">
              <div>
                <span class="panel-kicker">断言生成结果</span>
                <h3>插桩代码差异</h3>
              </div>
              <Tag :color="assertResult || effectiveDiffContent ? 'success' : 'default'">
                {{ assertionSummary }}
              </Tag>
            </div>
            <div v-if="effectiveDiffContent" class="diff-wrapper">
              <div
                v-for="line in renderedDiffLines"
                :key="line.id"
                class="diff-line"
                :class="`diff-line--${line.type}`"
              >
                <span class="diff-line-number">{{ line.text ? '' : ' ' }}</span>
                <code>{{ line.text || ' ' }}</code>
              </div>
            </div>
            <Empty
              v-else
              class="diff-empty"
              description="等待生成插桩差异"
              :image="Empty.PRESENTED_IMAGE_SIMPLE"
            />
          </section>
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
              <span>POC 输出</span>
              <strong>{{ stats.crashes > 0 ? '已生成可下载 POC 包' : '等待崩溃证据' }}</strong>
            </div>
            <Button
              type="primary"
              :disabled="stats.crashes <= 0 || isPocDownloading"
              :loading="isPocDownloading"
              @click="handleDownloadPoc"
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
  font-size: 18px;
  font-weight: 700;
}

.stage-title :first-child {
  color: #1677ff;
}

.stage-title small {
  font-size: 14px;
  font-weight: 500;
  color: var(--ant-color-text-secondary);
}

.verification-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.verification-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.panel {
  min-width: 0;
  padding: 18px;
  background: #fff;
  border: 1px solid #dbeafe;
  border-radius: 8px;
}

.evidence-output-grid,
.panel--poc {
  grid-column: 1 / -1;
}

.evidence-output-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
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
  font-size: 17px;
  font-weight: 800;
  color: #172033;
}

.panel-kicker {
  display: block;
  margin-bottom: 4px;
  font-size: 13px;
  font-weight: 700;
  color: #64748b;
}

.rule-text,
.reason-text {
  margin: 0;
  font-size: 15px;
  line-height: 1.7;
  color: #334155;
  overflow-wrap: anywhere;
}

.result-stage :deep(.ant-tag) {
  padding: 1px 8px;
  font-size: 13px;
  line-height: 22px;
  border-radius: 6px;
}

.result-stage :deep(.ant-empty-description) {
  font-size: 14px;
}

.function-source-frame {
  min-width: 0;
  height: 440px;
  overflow: hidden;
  overflow-y: auto;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.function-source-section + .function-source-section {
  border-top: 1px solid #dbe4ef;
}

.function-source-head {
  display: grid;
  grid-template-columns: minmax(140px, 0.36fr) minmax(0, 0.64fr);
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 13px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.function-source-head strong,
.function-source-head code {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.function-source-head strong {
  color: #111827;
}

.function-source-head code {
  color: #64748b;
  background: transparent;
}

.function-source-code {
  padding: 10px 0;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 14px;
  line-height: 1.7;
  color: #334155;
  background: #fff;
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

.diff-wrapper {
  min-width: 0;
  height: 440px;
  padding: 8px 0;
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #334155;
  background: #fbfdff;
  border: 1px solid var(--ant-color-border);
  border-radius: 8px;
}

.diff-line {
  display: grid;
  grid-template-columns: 18px minmax(max-content, 1fr);
  min-width: max-content;
  padding: 1px 12px;
  white-space: pre;
}

.diff-line code {
  padding: 0;
  color: inherit;
  white-space: pre;
  background: transparent;
}

.diff-line-number {
  color: #94a3b8;
  user-select: none;
}

.diff-line--meta {
  font-weight: 700;
  color: #334155;
  background: #f1f5f9;
}

.diff-line--file {
  color: #0f4c81;
  background: #eef6ff;
}

.diff-line--hunk {
  color: #6d28d9;
  background: #f5f3ff;
}

.diff-line--add {
  color: #047857;
  background: #ecfdf5;
}

.diff-line--delete {
  color: #b42318;
  background: #fff1f2;
}

.diff-line--context {
  color: #334155;
}

.diff-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 440px;
  margin: 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
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
  font-size: 13px;
  font-weight: 700;
  color: #64748b;
}

.poc-body strong {
  max-width: 780px;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 14px;
  color: #172033;
  white-space: nowrap;
}

@media (max-width: 1024px) {
  .verification-grid,
  .evidence-output-grid {
    grid-template-columns: 1fr;
  }

  .poc-body {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
