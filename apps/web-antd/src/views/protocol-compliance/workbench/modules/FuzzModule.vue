<script setup lang="ts">
import { computed } from 'vue';

import { IconifyIcon } from '@vben/icons';

import { Button, Card, Input, Tag } from 'ant-design-vue';

import StageFuzz from '../components/StageFuzz.vue';
import StageResultVerification from '../components/StageResultVerification.vue';
import { useAnalysisModules } from '../useAnalysisModules';
import { formatDuration } from '../utils';

const {
  assertionOutputContexts,
  fuzz,
  fuzzInput,
  fuzzStats,
  isFuzzRunning,
  latestAssertGenerationJobId,
  runFuzzing,
  stopFuzzing,
} = useAnalysisModules();

const selectedAssertionOutput = computed(
  () =>
    assertionOutputContexts.get(
      fuzz.assertGenerationJobId || fuzzInput.assertGenerationJobId.trim(),
    ) || null,
);

const assertionResult = computed(
  () => selectedAssertionOutput.value?.assertResult || null,
);

const staticResult = computed(
  () => selectedAssertionOutput.value?.codeLocateResult || null,
);

const selectedRule = computed(
  () => selectedAssertionOutput.value?.rule || null,
);

const evidence = computed(
  () => selectedAssertionOutput.value?.evidence || null,
);

const fuzzElapsed = computed(() => formatDuration(fuzz.elapsedSeconds));

function useLatestAssertion() {
  if (latestAssertGenerationJobId.value) {
    fuzzInput.assertGenerationJobId = latestAssertGenerationJobId.value;
  }
}
</script>

<template>
  <div class="analysis-module">
    <header class="module-heading">
      <div>
        <h1>模糊测试</h1>
        <p>选择一个已完成的断言生成任务，单独生成配置并启动 AFLNet。</p>
      </div>
      <Tag
        :color="
          fuzz.status === 'running' ||
          fuzz.status === 'configuring' ||
          fuzz.status === 'stopping'
            ? 'processing'
            : fuzz.status === 'crash-found'
              ? 'error'
              : fuzz.status === 'failed'
                ? 'error'
                : 'default'
        "
      >
        {{
          fuzz.status === 'configuring'
            ? '准备配置'
            : fuzz.status === 'stopping'
              ? '正在停止'
              : fuzz.status === 'running'
                ? '运行中'
                : fuzz.status === 'completed'
                  ? '已完成'
                  : fuzz.status === 'crash-found'
                    ? '发现崩溃'
                    : fuzz.status === 'stopped'
                      ? '已停止'
                      : fuzz.status === 'failed'
                        ? '异常'
                        : '待运行'
        }}
      </Tag>
    </header>

    <Card class="module-card" title="输入">
      <div class="fuzz-input-row">
        <div class="fuzz-input-field">
          <div class="module-input-label">断言生成任务 ID *</div>
          <Input
            v-model:value="fuzzInput.assertGenerationJobId"
            :disabled="isFuzzRunning"
            placeholder="填写断言生成模块的输出任务 ID"
          />
        </div>
        <div class="fuzz-input-actions">
          <Button
            :disabled="!latestAssertGenerationJobId || isFuzzRunning"
            @click="useLatestAssertion"
          >
            使用最近断言输出
          </Button>
          <Button
            type="primary"
            :loading="isFuzzRunning"
            :disabled="isFuzzRunning"
            @click="runFuzzing"
          >
            <template #icon><IconifyIcon icon="mdi:play" /></template>
            生成配置并开始模糊测试
          </Button>
          <Button
            v-if="isFuzzRunning"
            danger
            :loading="fuzz.status === 'stopping'"
            :disabled="fuzz.status === 'stopping'"
            @click="stopFuzzing"
          >
            <template #icon><IconifyIcon icon="mdi:stop" /></template>
            停止
          </Button>
        </div>
      </div>
      <p v-if="assertionResult" class="module-help">
        所选断言输出：{{ assertionResult.jobId }} · 插桩源码包
        {{ assertionResult.artifacts?.instrumentedCodeZipPath || '已生成' }}
      </p>
      <p class="module-help">
        模糊测试只接收断言生成的任务
        ID；协议元数据与运行参数由已完成的断言输出和后端配置生成阶段提供。
      </p>
    </Card>

    <div v-if="fuzz.error" class="module-error" role="alert">
      <IconifyIcon icon="mdi:alert-circle-outline" />
      <span>{{ fuzz.error }}</span>
    </div>

    <StageFuzz
      :elapsed="fuzzElapsed"
      :job="fuzz.job"
      :logs="fuzz.logs"
      :rule="selectedRule"
      :running="fuzz.status === 'running'"
      :speed-series="fuzz.speedSeries"
      :stats="fuzzStats"
    />

    <StageResultVerification
      v-if="fuzz.job && !isFuzzRunning"
      :assert-diff-content="selectedAssertionOutput?.diffContent || ''"
      :assert-result="assertionResult"
      :evidence="evidence"
      :logs="fuzz.logs"
      :poc-path="fuzz.pocPath"
      :rule="selectedRule"
      :static-result="staticResult"
      :stats="fuzzStats"
    />
  </div>
</template>

<style scoped>
.analysis-module {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.module-heading {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
}

.module-heading h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}

.module-heading p,
.module-help {
  margin: 6px 0 0;
  color: var(--ant-text-color-secondary);
}

.module-card {
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}

.fuzz-input-row {
  display: flex;
  gap: 20px;
  align-items: flex-end;
}

.fuzz-input-field {
  flex: 1;
  min-width: 220px;
}

.module-input-label {
  margin-bottom: 8px;
  font-weight: 600;
}

.fuzz-input-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.module-error {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 12px 16px;
  color: #b42318;
  background: #fef3f2;
  border: 1px solid #fecdca;
  border-radius: 8px;
}

@media (max-width: 900px) {
  .fuzz-input-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
