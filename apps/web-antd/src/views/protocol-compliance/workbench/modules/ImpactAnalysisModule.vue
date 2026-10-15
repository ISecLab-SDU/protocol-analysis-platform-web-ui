<script setup lang="ts">
import type { ImpactJob, ImpactResult } from '#/api/protocol-compliance';

import { onBeforeUnmount, onMounted, ref } from 'vue';

import { Alert, Button, Select, Tag } from 'ant-design-vue';

import {
  downloadImpactArtifacts,
  fetchImpactHistory,
  fetchImpactProgress,
  fetchImpactResult,
  startImpactAnalysis,
} from '#/api/protocol-compliance';

const code = ref<File>();
const analysisMode = ref('source');
const analysis = ref<File>();
const job = ref<ImpactJob>();
const result = ref<ImpactResult>();
const history = ref<ImpactJob[]>([]);
const error = ref('');
const logs = ref('');
const busy = ref(false);
let timer: ReturnType<typeof setTimeout> | undefined;
let generation = 0;
let offset = 0;
function fileChanged(event: Event, kind: 'analysis' | 'code') {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (kind === 'code') code.value = file;
  else analysis.value = file;
}
async function refreshHistory() {
  history.value = await fetchImpactHistory();
}
async function poll(id: string, current: number) {
  try {
    const progress = await fetchImpactProgress(id, offset);
    if (current !== generation) return;
    job.value = progress;
    logs.value += progress.logs || '';
    logs.value = logs.value.slice(-200_000);
    offset = progress.nextOffset || offset;
    if (progress.status === 'completed') {
      result.value = await fetchImpactResult(id);
      await refreshHistory();
    } else if (progress.status === 'failed') {
      error.value = progress.message;
      await refreshHistory();
    } else timer = setTimeout(() => void poll(id, current), 2000);
  } catch (error_) {
    if (current === generation) error.value = String(error_);
  }
}
async function selectJob(id: string) {
  clearTimeout(timer);
  generation += 1;
  offset = 0;
  logs.value = '';
  result.value = undefined;
  error.value = '';
  await poll(id, generation);
}
async function start() {
  if (!code.value || !analysis.value) return;
  busy.value = true;
  error.value = '';
  try {
    const created = await startImpactAnalysis(
      code.value,
      analysis.value,
      analysisMode.value === 'native',
    );
    job.value = created;
    await refreshHistory();
    await selectJob(created.jobId);
  } catch (error_) {
    error.value = String(error_);
  } finally {
    busy.value = false;
  }
}
async function download() {
  if (!job.value) return;
  try {
    const blob = await downloadImpactArtifacts(job.value.jobId);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `impact-${job.value.jobId}.zip`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error_) {
    error.value = String(error_);
  }
}
onMounted(() => {
  void refreshHistory().catch((error_) => {
    error.value = String(error_);
  });
});
onBeforeUnmount(() => {
  generation += 1;
  clearTimeout(timer);
});
</script>

<template>
  <div class="impact-analysis">
    <header>
      <h1>Impact Analysis</h1>
      <p>
        ProtoXploit Phase 1 · Planning → Evidence collection → Security
        assessment
      </p>
    </header>
    <Alert
      type="info"
      show-icon
      message="上传 ProtocolGuard 分析 JSON 和匹配的源码包。使用服务器现有 Pi / LLM 配置评估影响。源码分析会明确记录证据限制；LLVM / SVF 分析需要源码包中有配对的全程序 .bc 和 .ll 文件。"
    />
    <label
      >分析模式
      <Select
        v-model:value="analysisMode"
        aria-label="分析模式"
        :options="[
          { label: '源码分析', value: 'source' },
          { label: '源码 + LLVM / SVF 全程序分析', value: 'native' },
        ]"
      />
    </label>
    <div class="impact-inputs">
      <label
        >分析结果 JSON<input
          type="file"
          accept=".json"
          @change="fileChanged($event, 'analysis')"
      /></label>
      <label
        >源码包<input
          type="file"
          accept=".tar,.gz,.tgz,.zip"
          @change="fileChanged($event, 'code')"
      /></label>
      <Button
        type="primary"
        :loading="busy"
        :disabled="
          !code ||
          !analysis ||
          job?.status === 'running' ||
          job?.status === 'queued'
        "
        @click="start"
      >
        开始影响分析
      </Button>
    </div>
    <Select
      aria-label="Impact analysis history"
      placeholder="历史影响分析任务"
      :value="job?.jobId"
      :options="
        history.map((item) => ({
          value: item.jobId,
          label: `${item.createdAt} · ${item.status} · ${item.analysisId}`,
        }))
      "
      @change="(value) => selectJob(String(value))"
    />
    <Alert v-if="error" type="error" show-icon :message="error" />
    <div v-if="job">
      <Tag>{{ job.status }}</Tag
      ><Tag>{{ job.heavyStaticAnalysis ? 'LLVM / SVF' : '源码分析' }}</Tag>
      {{ job.message }} <code>{{ job.jobId }}</code>
    </div>
    <section
      v-for="item in result?.results"
      :key="item.resultId"
      class="impact-result"
    >
      <h2>
        {{ item.resultId }} <Tag>{{ item.assessment.outcome }}</Tag>
      </h2>
      <p>{{ item.assessment.impact_reasoning }}</p>
      <details v-if="item.assessment.validation_hypothesis">
        <summary>Validation hypothesis</summary>
        <pre>{{
          JSON.stringify(item.assessment.validation_hypothesis, null, 2)
        }}</pre>
      </details>
      <details v-if="item.assessment.oracle_hints.length > 0">
        <summary>Oracle hints</summary>
        <pre>{{ JSON.stringify(item.assessment.oracle_hints, null, 2) }}</pre>
      </details>
    </section>
    <Button v-if="result" @click="download">下载评估与阶段证据</Button>
    <details v-if="logs">
      <summary>执行日志</summary>
      <pre class="impact-logs">{{ logs }}</pre>
    </details>
  </div>
</template>

<style scoped>
.impact-analysis {
  display: grid;
  gap: 18px;
}
h1 {
  font-size: 24px;
  font-weight: 700;
}
.impact-inputs {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: 20px;
}
label {
  display: grid;
  gap: 8px;
}
.impact-result {
  padding: 20px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}
h2 {
  margin-bottom: 12px;
  font-weight: 600;
}
p,
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.impact-logs {
  max-height: 480px;
  overflow: auto;
  padding: 16px;
  background: #f1f5f9;
}
</style>
