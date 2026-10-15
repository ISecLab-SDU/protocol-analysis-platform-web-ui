<script setup lang="ts">
import type {
  ImpactJob,
  ImpactResult,
  ProtocolAnalysisDocument,
} from '#/api/protocol-compliance';

import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';

import { useElementBounding, useWindowSize } from '@vueuse/core';
import {
  Button,
  Card,
  Collapse,
  CollapsePanel,
  Empty,
  Select,
  Tag,
  Upload,
} from 'ant-design-vue';

import {
  downloadImpactArtifacts,
  fetchImpactHistory,
  fetchImpactProgress,
  fetchImpactResult,
  startImpactAnalysis,
} from '#/api/protocol-compliance';

import {
  eligibleAnalysisResults,
  fetchAnalysisFile,
  readAnalysisDocument,
} from '../analysisExchange';
import StageLiveLogPanel from '../components/StageLiveLogPanel.vue';
import { useAnalysisModules } from '../useAnalysisModules';
import { formatTime } from '../utils';

const { codeLocate } = useAnalysisModules();
const moduleRef = ref<HTMLElement | null>(null);
const { height: viewportHeight } = useWindowSize();
const { top: moduleTop } = useElementBounding(moduleRef, {
  windowScroll: false,
});
const workspaceHeight = computed(
  () => `${Math.max(480, viewportHeight.value - moduleTop.value - 28)}px`,
);
const code = ref<File>();
const analysis = ref<File>();
const analysisMode = ref('source');
const preview = ref<null | ProtocolAnalysisDocument>(null);
const previewError = ref('');
const eligible = computed(() =>
  preview.value ? eligibleAnalysisResults(preview.value) : [],
);
const job = ref<ImpactJob>();
const result = ref<ImpactResult>();
const history = ref<ImpactJob[]>([]);
const error = ref('');
const logs = ref('');
const started = ref(false);
const busy = ref(false);
const loadingJob = ref(false);
const downloading = ref(false);
const loadingLatest = ref(false);
const running = computed(
  () =>
    busy.value ||
    job.value?.status === 'running' ||
    job.value?.status === 'queued',
);
const statusLabels: Record<string, string> = {
  completed: '已完成',
  failed: '异常',
  queued: '排队中',
  running: '进行中',
};
const stateText = computed(() =>
  started.value && job.value ? statusLabels[job.value.status] : '待运行',
);
const stateColor = computed(() => {
  if (running.value) return 'processing';
  if (job.value?.status === 'failed') return 'error';
  if (job.value?.status === 'completed') return 'success';
  return 'default';
});
const historyOptions = computed(() =>
  history.value.map((item) => ({
    value: item.jobId,
    label: `${formatTime(item.createdAt)} · ${statusLabels[item.status]} · ${item.findingCount} 条违规`,
  })),
);
const archiveFileList = computed(() =>
  code.value
    ? [{ name: code.value.name, status: 'done' as const, uid: 'impact-source' }]
    : [],
);
const analysisFileList = computed(() =>
  analysis.value
    ? [
        {
          name: analysis.value.name,
          status: 'done' as const,
          uid: 'impact-analysis',
        },
      ]
    : [],
);
const outcomeLabels: Record<string, string> = {
  SUPPORTED: '确认安全影响',
  UNSUPPORTED_SECURITY: '超出验证范围',
  NON_SECURITY: '未发现安全影响',
  UNCERTAIN: '证据不足',
};
const outcomeColors: Record<string, string> = {
  SUPPORTED: 'error',
  UNSUPPORTED_SECURITY: 'warning',
  NON_SECURITY: 'success',
  UNCERTAIN: 'default',
};
const branchLabels: Record<string, string> = {
  MEMORY_SAFETY: '内存安全',
  ACCESS_CONTROL: '访问控制',
  DATA_PROTECTION: '数据保护',
};
let timer: ReturnType<typeof setTimeout> | undefined;
let generation = 0;
let offset = 0;

watch(analysis, async (file) => {
  preview.value = null;
  previewError.value = '';
  if (!file) return;
  try {
    const document = await readAnalysisDocument(file);
    if (analysis.value === file) preview.value = document;
  } catch (error_) {
    if (analysis.value === file)
      previewError.value =
        error_ instanceof Error ? error_.message : '分析 JSON 无效';
  }
});
function beforeUploadArchive(file: File) {
  code.value = file;
  return false;
}
function beforeUploadAnalysis(file: File) {
  analysis.value = file;
  return false;
}
function removeArchive() {
  code.value = undefined;
  return true;
}
function removeAnalysis() {
  analysis.value = undefined;
  return true;
}
async function useLatestAnalysis() {
  const id = codeLocate.result?.analysisId;
  const archive = codeLocate.inputArchive;
  if (!id || !archive) return;
  loadingLatest.value = true;
  try {
    const file = await fetchAnalysisFile(id);
    analysis.value = file;
    code.value = archive;
  } catch {
    error.value = '最近分析结果加载失败，请重试或上传分析 JSON。';
  } finally {
    loadingLatest.value = false;
  }
}
async function refreshHistory() {
  history.value = await fetchImpactHistory();
}
async function poll(id: string, current: number) {
  try {
    let progress: ImpactJob;
    let received: number;
    do {
      const previousOffset = offset;
      progress = await fetchImpactProgress(id, offset);
      if (current !== generation) return;
      job.value = progress;
      logs.value = (logs.value + (progress.logs || '')).slice(-200_000);
      offset = progress.nextOffset ?? offset;
      received = offset - previousOffset;
    } while (received >= 128 * 1024 && progress.status === 'completed');
    if (progress.status === 'completed') {
      const output = await fetchImpactResult(id);
      if (current !== generation) return;
      result.value = output;
      await refreshHistory();
    } else if (progress.status === 'failed') {
      error.value = '影响分析未完成，请查看执行日志后重试。';
      await refreshHistory();
    } else timer = setTimeout(() => void poll(id, current), 2000);
  } catch {
    if (current === generation)
      error.value = '任务状态加载失败，请重新选择任务重试。';
  } finally {
    if (current === generation) loadingJob.value = false;
  }
}
async function selectJob(id: string) {
  clearTimeout(timer);
  generation += 1;
  offset = 0;
  logs.value = '';
  result.value = undefined;
  error.value = '';
  started.value = true;
  loadingJob.value = true;
  job.value = history.value.find((item) => item.jobId === id);
  await poll(id, generation);
}
function returnToInputs() {
  clearTimeout(timer);
  generation += 1;
  offset = 0;
  started.value = false;
  job.value = undefined;
  result.value = undefined;
  logs.value = '';
  error.value = '';
  loadingJob.value = false;
}
async function start() {
  if (
    !code.value ||
    !analysis.value ||
    !preview.value ||
    eligible.value.length === 0 ||
    running.value
  )
    return;
  busy.value = true;
  error.value = '';
  try {
    const created = await startImpactAnalysis(
      code.value,
      analysis.value,
      analysisMode.value === 'native',
    );
    job.value = created;
    started.value = true;
    history.value = [created, ...history.value];
    await selectJob(created.jobId);
  } catch {
    error.value = '影响分析提交失败，请确认分析 JSON 与源码包匹配后重试。';
  } finally {
    busy.value = false;
  }
}
async function download() {
  if (!job.value) return;
  downloading.value = true;
  try {
    const blob = await downloadImpactArtifacts(job.value.jobId);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `impact-${job.value.jobId}.zip`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch {
    error.value = '评估产物下载失败，请重试。';
  } finally {
    downloading.value = false;
  }
}
const logLines = computed(() => {
  let phase = '锚点规划';
  return logs.value
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0)
    .map((line, index) => {
      if (
        line.includes('submit_collect') ||
        line.includes('submit_propagation') ||
        line.includes('finalize_collect')
      )
        phase = '证据收集';
      if (line.includes('phase1_judge')) phase = '安全评估';
      const match = /^PI_TOOL [^:]+: (.+)$/.exec(line);
      let text = line;
      if (match) {
        try {
          const output = JSON.parse(match[1]!);
          text =
            output.content
              ?.map((block: { text?: string }) => block.text || '')
              .join('\n') || line;
        } catch {
          /* Incomplete log chunks remain readable until the next poll. */
        }
      }
      return { id: String(index), phase, text };
    });
});
const progress = computed(() => {
  if (job.value?.status === 'completed')
    return {
      label: '已完成',
      description: '安全影响评估与阶段证据已生成，可查看结果或下载产物。',
    };
  if (job.value?.status === 'failed')
    return {
      label: '执行异常',
      description: '任务未能完成，请查看日志中的具体原因。',
    };
  return {
    label: logLines.value.at(-1)?.phase || '准备分析',
    description: '依次定位违规行为、收集源到汇证据并评估安全影响。',
  };
});
onMounted(() => {
  void refreshHistory().catch(() => {
    error.value = '历史任务加载失败，请稍后重试。';
  });
});
onBeforeUnmount(() => {
  generation += 1;
  clearTimeout(timer);
});
</script>

<template>
  <div
    ref="moduleRef"
    class="analysis-module"
    :class="{ 'analysis-module--focused': started }"
    :style="{ '--module-workspace-height': workspaceHeight }"
  >
    <header class="module-heading">
      <div>
        <h1>影响分析</h1>
        <p v-if="!started">
          使用匹配的源码包和分析 JSON，评估协议违规行为的安全影响。
        </p>
      </div>
      <div class="module-heading-actions">
        <Button
          v-if="started && !running && !loadingJob"
          size="small"
          @click="returnToInputs"
        >
          返回输入
        </Button>
        <Tag :color="stateColor">{{ stateText }}</Tag>
      </div>
    </header>
    <Card v-if="!started" class="module-card" title="输入">
      <div class="module-input-grid">
        <div class="module-input-field">
          <div class="module-input-label">源码压缩包 *</div>
          <Upload
            accept=".tar,.gz,.tgz,.zip"
            :before-upload="beforeUploadArchive"
            :disabled="running"
            :file-list="archiveFileList"
            @remove="removeArchive"
          >
            <Button :disabled="running">
              <template #icon><IconifyIcon icon="mdi:upload" /></template
              >选择源码压缩包
            </Button>
          </Upload>
        </div>
        <div class="module-input-field">
          <div class="module-input-label">分析结果 JSON *</div>
          <Upload
            accept=".json,application/json"
            :before-upload="beforeUploadAnalysis"
            :disabled="running"
            :file-list="analysisFileList"
            @remove="removeAnalysis"
          >
            <Button :disabled="running">
              <template #icon><IconifyIcon icon="mdi:upload" /></template
              >上传分析 JSON
            </Button>
          </Upload>
          <Button
            :disabled="
              !codeLocate.result?.analysisId ||
              !codeLocate.inputArchive ||
              running
            "
            :loading="loadingLatest"
            @click="useLatestAnalysis"
          >
            使用最近分析结果及源码
          </Button>
          <small class="module-help"
            >提交时将校验源码内容及代码证据是否与分析结果匹配。</small
          >
          <p v-if="previewError" class="input-error" role="alert">
            {{ previewError }}
          </p>
          <div v-if="preview" class="analysis-preview">
            <p>
              {{ preview.protocol.name }} · {{ preview.source.archiveName }}
            </p>
            <p>
              共 {{ preview.results.length }} 条分析结果；可评估
              {{ eligible.length }} 条违规。
            </p>
          </div>
        </div>
        <div class="module-input-field">
          <div class="module-input-label">分析模式</div>
          <Select
            v-model:value="analysisMode"
            aria-label="分析模式"
            :disabled="running"
            :options="[
              { label: '源码分析', value: 'source' },
              { label: '源码与全程序分析', value: 'native' },
            ]"
          />
          <small class="module-help">{{
            analysisMode === 'native'
              ? '需在源码包中提供配对的全程序 .bc 和 .ll 文件。'
              : '基于源码构建影响证据，并在评估中标明分析限制。'
          }}</small>
        </div>
      </div>
    </Card>
    <div v-if="error" class="module-error" role="alert">
      <IconifyIcon icon="mdi:alert-circle-outline" /><span>{{ error }}</span>
    </div>
    <div v-if="!started || result" class="module-actions">
      <Button
        v-if="!started"
        type="primary"
        size="large"
        :loading="busy"
        :disabled="
          !code ||
          !analysis ||
          !preview ||
          !!previewError ||
          eligible.length === 0 ||
          running
        "
        @click="start"
      >
        <template #icon><IconifyIcon icon="mdi:play" /></template>开始影响分析
      </Button>
      <Button v-if="result" :loading="downloading" @click="download">
        <template #icon><IconifyIcon icon="mdi:download" /></template
        >下载评估与阶段证据
      </Button>
      <span v-if="job" class="output-reference"
        >输出任务 ID：{{ job.jobId }}</span
      >
    </div>
    <Card v-if="!started" class="module-card" title="历史任务">
      <div class="module-input-field">
        <div class="module-input-label">影响分析任务</div>
        <Select
          aria-label="历史影响分析任务"
          placeholder="选择已提交的影响分析任务"
          :options="historyOptions"
          :loading="loadingJob"
          :disabled="busy"
          @change="(value) => selectJob(String(value))"
        /><small class="module-help"
          >可查看进行中任务的日志及已完成任务的评估结果。</small
        >
      </div>
    </Card>
    <Card
      v-if="started"
      class="stage-card impact-stage"
      :bordered="false"
      :loading="loadingJob"
    >
      <template #title>
        <div class="stage-title">
          <IconifyIcon icon="mdi:shield-search" /><span>安全影响评估</span
          ><small>{{ stateText }}</small>
        </div>
      </template>
      <template #extra>
        <Tag>
          {{ job?.heavyStaticAnalysis ? '全程序分析' : '源码分析' }}
        </Tag>
      </template>
      <div class="impact-observe-grid">
        <StageLiveLogPanel
          :lines="logLines"
          :progress="progress"
          :running="running"
        />
        <section class="impact-results">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">影响分析结果</span>
              <h3>安全影响判定</h3>
            </div>
            <Tag color="blue">
              {{ result?.results.length ?? job?.findingCount ?? 0 }}
              条违规
            </Tag>
          </div>
          <div v-if="result" class="results-body">
            <article
              v-for="(item, index) in result.results"
              :key="item.resultId"
              class="assessment-item"
            >
              <div class="assessment-heading">
                <h4>违规项 {{ index + 1 }}</h4>
                <Tag
                  :color="outcomeColors[item.assessment.outcome] || 'default'"
                >
                  {{ outcomeLabels[item.assessment.outcome] || '待复核' }}
                </Tag>
              </div>
              <div class="result-reference">结果编号：{{ item.resultId }}</div>
              <h5>影响依据</h5>
              <p class="assessment-reasoning">
                {{ item.assessment.impact_reasoning }}
              </p>
              <Collapse ghost>
                <CollapsePanel
                  v-if="item.assessment.validation_hypothesis"
                  key="hypothesis"
                  header="验证假设"
                >
                  <dl class="evidence-fields">
                    <dt>影响类型</dt>
                    <dd>
                      {{
                        branchLabels[
                          item.assessment.validation_hypothesis.primary_branch
                        ] || '其他安全影响'
                      }}
                    </dd>
                    <dt>受损安全条件</dt>
                    <dd>
                      {{
                        item.assessment.validation_hypothesis.violated_predicate
                      }}
                    </dd>
                    <dt>协议状态准备</dt>
                    <dd>
                      {{
                        item.assessment.validation_hypothesis
                          .required_protocol_state_setup
                      }}
                    </dd>
                    <dt>目标行为</dt>
                    <dd>
                      {{
                        item.assessment.validation_hypothesis.target_observation
                      }}
                    </dd>
                    <dt>后果论证</dt>
                    <dd>
                      {{
                        item.assessment.validation_hypothesis
                          .consequence_argument
                      }}
                    </dd>
                  </dl>
                </CollapsePanel>
                <CollapsePanel
                  v-if="item.assessment.oracle_hints.length > 0"
                  key="oracles"
                  header="验证观测点"
                >
                  <dl
                    v-for="(hint, hintIndex) in item.assessment.oracle_hints"
                    :key="hintIndex"
                    class="evidence-fields"
                  >
                    <dt>代码位置</dt>
                    <dd class="code-location">{{ hint.code_location }}</dd>
                    <dt>目标变量</dt>
                    <dd>{{ hint.target_variable }}</dd>
                    <dt>触发条件</dt>
                    <dd>{{ hint.trigger_condition }}</dd>
                  </dl>
                </CollapsePanel>
              </Collapse>
            </article>
          </div>
          <Empty
            v-else
            class="result-empty"
            :description="
              job?.status === 'failed'
                ? '影响分析未完成'
                : '等待生成安全影响评估'
            "
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
          />
        </section>
      </div>
    </Card>
  </div>
</template>

<style scoped>
.analysis-module {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.analysis-module--focused {
  min-height: var(--module-workspace-height);
}
.module-heading,
.module-card,
.module-error,
.module-actions {
  flex-shrink: 0;
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
.module-heading-actions {
  display: flex;
  gap: 8px;
  align-items: center;
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
.module-input-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}
.module-input-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.module-input-label {
  font-weight: 600;
}
.analysis-preview {
  max-height: 240px;
  overflow: auto;
  overflow-wrap: anywhere;
}
.input-error {
  color: #b42318;
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
.module-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}
.output-reference {
  color: var(--ant-text-color-secondary);
  overflow-wrap: anywhere;
}
.stage-card {
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
  box-shadow: 0 10px 26px rgb(15 23 42 / 4%);
}
.impact-stage {
  flex: 1;
  min-width: 0;
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
.impact-observe-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
  gap: 16px;
}
.impact-results {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  padding: 18px;
  background: #fff;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}
.panel-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}
.panel-head h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: #111827;
}
.panel-head > :last-child {
  flex: 0 0 auto;
}
.panel-kicker {
  display: block;
  margin-bottom: 4px;
  font-size: 14px;
  font-weight: 700;
  color: #64748b;
}
.results-body {
  min-width: 0;
  max-height: 560px;
  overflow: auto;
}
.assessment-item + .assessment-item {
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid var(--ant-color-border-secondary);
}
.assessment-heading {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}
.assessment-heading h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}
.result-reference {
  margin-top: 6px;
  font-size: 12px;
  color: var(--ant-color-text-secondary);
  overflow-wrap: anywhere;
}
h5 {
  margin: 18px 0 8px;
  font-size: 14px;
  font-weight: 600;
}
.assessment-reasoning,
.evidence-fields dd {
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.evidence-fields {
  margin: 0;
}
.evidence-fields + .evidence-fields {
  padding-top: 12px;
  margin-top: 12px;
  border-top: 1px solid var(--ant-color-border-secondary);
}
.evidence-fields dt {
  margin-bottom: 4px;
  font-weight: 600;
}
.evidence-fields dd {
  margin: 0 0 14px;
  color: var(--ant-color-text-secondary);
}
.code-location {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.result-empty {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  margin: 0;
}
.stage-card :deep(.ant-tag) {
  padding: 1px 8px;
  font-size: 14px;
  line-height: 24px;
  border-radius: 6px;
}
@media (min-width: 961px) {
  .analysis-module--focused {
    height: var(--module-workspace-height);
  }
  .impact-stage {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .impact-stage :deep(.ant-card-head) {
    flex-shrink: 0;
  }
  .impact-stage :deep(.ant-card-body) {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 0;
  }
  .impact-observe-grid {
    flex: 1;
    min-height: 0;
  }
  .impact-results,
  .impact-stage :deep(.stage-live-log-panel) {
    min-height: 0;
  }
  .results-body,
  .impact-stage :deep(.live-log) {
    flex: 1;
    min-height: 0;
    height: auto;
    max-height: none;
  }
}
@media (max-width: 960px) {
  .impact-observe-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 760px) {
  .module-input-grid {
    grid-template-columns: 1fr;
  }
  .module-heading {
    flex-wrap: wrap;
  }
}
</style>
