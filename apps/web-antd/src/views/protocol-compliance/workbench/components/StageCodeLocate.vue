<script setup lang="ts">
import { computed } from 'vue';

import { Card, Empty, Tag, Button } from 'ant-design-vue';
import { IconifyIcon } from '@vben/icons';

import type { ProtocolStaticAnalysisResult } from '#/api/protocol-compliance';

interface Props {
  logHtml: string;
  result: ProtocolStaticAnalysisResult | null;
  running: boolean;
}

const props = defineProps<Props>();

const verdictStats = computed(() => {
  if (!props.result?.modelResponse?.verdicts) return { compliant: 0, needs_review: 0, non_compliant: 0 };
  const stats = { compliant: 0, needs_review: 0, non_compliant: 0 };
  for (const v of props.result.modelResponse.verdicts) {
    if (v.compliance === 'compliant') stats.compliant++;
    else if (v.compliance === 'needs_review') stats.needs_review++;
    else if (v.compliance === 'non_compliant') stats.non_compliant++;
  }
  return stats;
});

// 模拟代码片段数据（实际应该从后端获取）
const getCodeSnippet = (verdict: any) => {
  const mockCode = `// calculate maximum packet rate
uint22_t max_calc_pps = total_br / (8 * oh);
uint22_t limit_pps = has_smaxpr_ ? smaxpr_ : max_calc;
current_pps_ = std::min(max_calc_pps, limit_pps);
..`;

  return {
    filename: verdict.location.file,
    startLine: verdict.lineRange?.[0] || 315,
    highlightLine: verdict.lineRange?.[0] || 318,
    code: mockCode
  };
};
</script>

<template>
  <div class="code-locate-wrapper">
    <div v-if="result && result.modelResponse?.verdicts?.length" class="code-locate-content">
      <div
        v-for="(verdict, idx) in result.modelResponse.verdicts"
        :key="idx"
        class="code-locate-card"
      >
        <div class="code-locate-header">
          <div class="header-left">
            <IconifyIcon icon="mdi:file-document-outline" class="file-icon" />
            <span class="header-title">代码定位 (进行中)</span>
          </div>
          <Tag
            :color="
              verdict.compliance === 'compliant'
                ? 'success'
                : verdict.compliance === 'non_compliant'
                  ? 'error'
                  : 'warning'
            "
          >
            {{ verdict.compliance === 'compliant' ? '合规' : verdict.compliance === 'non_compliant' ? '不合规' : '待审查' }}
          </Tag>
        </div>

        <div class="code-locate-body">
          <div class="code-stats">
            <div class="stat-title">候选路径</div>
            <div class="stat-value">6</div>
            <div class="stat-title">关键切片</div>
            <div class="stat-value">2</div>
            <div class="stat-title">相关变量</div>
            <div class="stat-value">3</div>
          </div>

          <div class="code-display">
            <div class="code-header">
              <span class="code-file">目标文件: {{ verdict.location.file }}</span>
              <span class="code-location">关键位置: {{ verdict.lineRange?.[0] || 318 }}</span>
            </div>
            <div class="code-snippet">
              <div
                v-for="(line, lineIdx) in getCodeSnippet(verdict).code.split('\n')"
                :key="lineIdx"
                class="code-line"
                :class="{ 'code-line--highlight': getCodeSnippet(verdict).startLine + lineIdx === getCodeSnippet(verdict).highlightLine }"
              >
                <span class="line-number">{{ getCodeSnippet(verdict).startLine + lineIdx }}</span>
                <span class="line-content">{{ line }}</span>
              </div>
            </div>
            <Button type="link" size="small" class="view-context-btn">
              查看代码上下文
            </Button>
          </div>

          <div class="code-evidence">
            <div class="evidence-title">规则证据 ({{ verdict.relatedRule.source }})</div>
            <div class="evidence-content">
              <div class="evidence-item">
                <span class="evidence-label">约束类型:</span>
                <span>{{ verdict.category }}</span>
              </div>
              <div class="evidence-item">
                <span class="evidence-label">源数据:</span>
                <span>{{ verdict.relatedRule.requirement.slice(0, 50) }}...</span>
              </div>
              <div class="evidence-item">
                <span class="evidence-label">目标行为:</span>
                <span>{{ verdict.explanation.slice(0, 50) }}...</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Empty v-else description="等待代码定位阶段开始" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
  </div>
</template>

<style scoped>
.code-locate-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.code-locate-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.code-locate-card {
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 12px;
  overflow: hidden;
}

.code-locate-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--ant-color-fill-quaternary);
  border-bottom: 1px solid var(--ant-color-border-secondary);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-icon {
  font-size: 20px;
  color: var(--ant-primary-color);
}

.header-title {
  font-size: 15px;
  font-weight: 600;
}

.code-locate-body {
  display: grid;
  grid-template-columns: 200px 1fr 300px;
  gap: 20px;
  padding: 20px;
}

.code-stats {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  padding: 16px;
  background: var(--ant-color-fill-quaternary);
  border-radius: 8px;
  height: fit-content;
}

.stat-title {
  font-size: 12px;
  color: var(--ant-text-color-secondary);
  margin-top: 8px;
}

.stat-title:first-child {
  margin-top: 0;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--ant-text-color);
}

.code-display {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.code-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
}

.code-file {
  font-weight: 500;
  color: var(--ant-text-color);
}

.code-location {
  color: var(--ant-text-color-secondary);
}

.code-snippet {
  padding: 16px;
  background: #fafafa;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
  overflow-x: auto;
}

.code-line {
  display: flex;
  gap: 16px;
  padding: 2px 8px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  transition: background-color 0.2s;
}

.code-line--highlight {
  background: #e6f4ff;
  border-left: 3px solid #1677ff;
  padding-left: 5px;
}

.line-number {
  min-width: 40px;
  text-align: right;
  color: #8c8c8c;
  user-select: none;
}

.line-content {
  flex: 1;
  color: #262626;
  white-space: pre;
}

.view-context-btn {
  padding: 0;
  font-size: 13px;
}

.code-evidence {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--ant-color-fill-quaternary);
  border-radius: 8px;
  height: fit-content;
}

.evidence-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ant-text-color);
  margin-bottom: 8px;
}

.evidence-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.evidence-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.evidence-label {
  font-weight: 500;
  color: var(--ant-text-color-secondary);
}

.evidence-item > span:last-child {
  color: var(--ant-text-color);
  line-height: 1.5;
}

</style>
