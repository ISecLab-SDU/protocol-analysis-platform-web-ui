<script setup lang="ts">
import { computed } from 'vue';

import { Card, Empty, Tag } from 'ant-design-vue';
import { IconifyIcon } from '@vben/icons';

import type { ProtocolStaticAnalysisResult } from '#/api/protocol-compliance';

interface Props {
  logHtml: string;
  result: ProtocolStaticAnalysisResult | null;
  running: boolean;
}

defineProps<Props>();

const verdictStats = computed(() => {
  const props = defineProps<Props>();
  if (!props.result?.verdicts) return { compliant: 0, needs_review: 0, non_compliant: 0 };
  const stats = { compliant: 0, needs_review: 0, non_compliant: 0 };
  for (const v of props.result.verdicts) {
    if (v.verdict === 'compliant') stats.compliant++;
    else if (v.verdict === 'needs_review') stats.needs_review++;
    else if (v.verdict === 'non_compliant') stats.non_compliant++;
  }
  return stats;
});
</script>

<template>
  <Card title="代码定位">
    <template #extra>
      <Tag v-if="running" color="processing">进行中</Tag>
      <Tag v-else-if="result" color="success">已完成</Tag>
      <Tag v-else color="default">等待中</Tag>
    </template>

    <div v-if="logHtml || running" class="locate-container">
      <div class="locate-log">
        <div class="log-title">
          <IconifyIcon icon="mdi:console" />
          <span>分析日志</span>
        </div>
        <div class="log-content" v-html="logHtml || '等待日志输出...'" />
      </div>

      <div v-if="result" class="locate-verdict">
        <div class="verdict-stats">
          <div class="verdict-stat verdict-stat--ok">
            <IconifyIcon icon="mdi:check-circle" />
            <div>
              <div class="verdict-label">合规</div>
              <div class="verdict-value">{{ verdictStats.compliant }}</div>
            </div>
          </div>
          <div class="verdict-stat verdict-stat--warn">
            <IconifyIcon icon="mdi:alert" />
            <div>
              <div class="verdict-label">待审查</div>
              <div class="verdict-value">{{ verdictStats.needs_review }}</div>
            </div>
          </div>
          <div class="verdict-stat verdict-stat--error">
            <IconifyIcon icon="mdi:close-circle" />
            <div>
              <div class="verdict-label">不合规</div>
              <div class="verdict-value">{{ verdictStats.non_compliant }}</div>
            </div>
          </div>
        </div>

        <div v-if="result.verdicts && result.verdicts.length > 0" class="verdict-list">
          <div
            v-for="(v, i) in result.verdicts"
            :key="i"
            class="verdict-item"
          >
            <div class="verdict-header">
              <Tag
                :color="
                  v.verdict === 'compliant'
                    ? 'success'
                    : v.verdict === 'non_compliant'
                      ? 'error'
                      : 'warning'
                "
              >
                {{ v.verdict }}
              </Tag>
              <code class="verdict-file">{{ v.file }}</code>
            </div>
            <div class="verdict-body">
              <div class="verdict-field">
                <span class="verdict-key">行范围:</span>
                <span>{{ v.lineRange }}</span>
              </div>
              <div class="verdict-field">
                <span class="verdict-key">说明:</span>
                <span>{{ v.explanation }}</span>
              </div>
              <div v-if="v.recommendation" class="verdict-field">
                <span class="verdict-key">建议:</span>
                <span>{{ v.recommendation }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Empty v-else description="等待代码定位阶段开始" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
  </Card>
</template>

<style scoped>
.locate-container {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 20px;
}

.locate-log {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-title {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
}

.log-content {
  max-height: 400px;
  padding: 12px;
  overflow-y: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #e2e8f0;
  background: #0f172a;
  border-radius: 8px;
}

.locate-verdict {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.verdict-stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.verdict-stat {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
}

.verdict-stat :first-child {
  font-size: 20px;
}

.verdict-stat--ok {
  color: #16a34a;
  background: rgb(22 163 74 / 10%);
}

.verdict-stat--warn {
  color: #d97706;
  background: rgb(217 119 6 / 10%);
}

.verdict-stat--error {
  color: #dc2626;
  background: rgb(220 38 38 / 10%);
}

.verdict-label {
  font-size: 12px;
}

.verdict-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--ant-text-color);
}

.verdict-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.verdict-item {
  padding: 12px;
  background: var(--ant-color-fill-quaternary);
  border-radius: 8px;
}

.verdict-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.verdict-file {
  padding: 2px 6px;
  font-size: 12px;
  background: var(--ant-color-bg-container);
  border-radius: 4px;
}

.verdict-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
}

.verdict-field {
  display: flex;
  gap: 8px;
}

.verdict-key {
  min-width: 60px;
  font-weight: 500;
  color: var(--ant-text-color-secondary);
}
</style>
