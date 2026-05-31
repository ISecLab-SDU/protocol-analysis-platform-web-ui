<script setup lang="ts">
import { DiffFile } from '@git-diff-view/vue';
import '@git-diff-view/vue/styles/diff-view.css';

import { Card, Empty, Tag } from 'ant-design-vue';
import { IconifyIcon } from '@vben/icons';

import type { ProtocolAssertGenerationResult } from '#/api/protocol-compliance';

interface Props {
  logText: string;
  diffContent: string;
  result: ProtocolAssertGenerationResult | null;
  running: boolean;
}

defineProps<Props>();
</script>

<template>
  <Card title="断言生成">
    <template #extra>
      <Tag v-if="running" color="processing">进行中</Tag>
      <Tag v-else-if="result" color="success">已完成</Tag>
      <Tag v-else color="default">等待中</Tag>
    </template>

    <div v-if="logText || running" class="assert-container">
      <div class="assert-log">
        <div class="log-title">
          <IconifyIcon icon="mdi:text-box-outline" />
          <span>生成日志</span>
        </div>
        <div class="log-content">
          <div v-for="(line, i) in logText.split('\n').filter(l => l.trim())" :key="i" class="log-line">
            {{ line }}
          </div>
          <div v-if="!logText && running" class="log-line">等待日志输出...</div>
        </div>
      </div>

      <div v-if="diffContent" class="assert-diff">
        <div class="diff-title">
          <IconifyIcon icon="mdi:file-compare" />
          <span>插桩差异</span>
        </div>
        <div class="diff-wrapper">
          <DiffFile :diff-file="{ fileName: 'instrumentation.diff', fileContent: diffContent }" />
        </div>
      </div>
    </div>

    <Empty v-else description="等待断言生成阶段开始" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
  </Card>
</template>

<style scoped>
.assert-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.assert-log {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-title,
.diff-title {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
}

.log-content {
  max-height: 300px;
  padding: 12px;
  overflow-y: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #e2e8f0;
  background: #0f172a;
  border-radius: 8px;
}

.log-line {
  white-space: pre-wrap;
  word-break: break-word;
}

.assert-diff {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.diff-wrapper {
  max-height: 500px;
  overflow: auto;
  border: 1px solid var(--ant-color-border);
  border-radius: 8px;
}
</style>
