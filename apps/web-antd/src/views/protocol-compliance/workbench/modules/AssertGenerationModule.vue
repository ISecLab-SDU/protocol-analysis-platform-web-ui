<script setup lang="ts">
import type { ProtocolAnalysisDocument } from '#/api/protocol-compliance';

import { computed, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';

import { useElementBounding, useWindowSize } from '@vueuse/core';
import { Button, Card, message, Tag, Upload } from 'ant-design-vue';

import { downloadProtocolAssertionArtifact } from '#/api/protocol-compliance';

import {
  eligibleAnalysisResults,
  readAnalysisDocument,
} from '../analysisExchange';
import StageAssertGen from '../components/StageAssertGen.vue';
import { useAnalysisModules } from '../useAnalysisModules';

const {
  assertGeneration,
  assertInputs,
  codeLocate,
  resetAssertGenerationOutput,
  runAssertGeneration,
  stopAssertGeneration,
  useLatestCodeLocateOutput,
} = useAnalysisModules();

const moduleRef = ref<HTMLElement | null>(null);
const { height: viewportHeight } = useWindowSize();
const { top: moduleTop } = useElementBounding(moduleRef, {
  windowScroll: false,
});
const workspaceHeight = computed(
  () => `${Math.max(480, viewportHeight.value - moduleTop.value - 28)}px`,
);

const downloading = ref(false);
async function downloadArtifact(artifact: 'instrumented-code' | 'tasks') {
  const jobId = assertGeneration.result?.jobId;
  if (!jobId) return;
  downloading.value = true;
  try {
    const blob = await downloadProtocolAssertionArtifact(jobId, artifact);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `assertion-${jobId}-${artifact}.zip`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch {
    message.error('产物下载失败，请重试');
  } finally {
    downloading.value = false;
  }
}

const archiveFileList = computed(() =>
  assertInputs.codeArchive
    ? [
        {
          name: assertInputs.codeArchive.name,
          status: 'done' as const,
          uid: 'code-archive',
        },
      ]
    : [],
);

const analysisFile = computed(
  () => assertInputs.analysisDocument || assertInputs.databaseFile,
);
const databaseFileList = computed(() =>
  analysisFile.value
    ? [
        {
          name: analysisFile.value.name,
          status: 'done' as const,
          uid: 'analysis-document',
        },
      ]
    : [],
);
const preview = ref<null | ProtocolAnalysisDocument>(null);
const previewError = ref('');
const eligible = computed(() =>
  preview.value ? eligibleAnalysisResults(preview.value) : [],
);
const excluded = computed(
  () => preview.value?.results.filter((r) => !eligible.value.includes(r)) || [],
);
watch(
  () => assertInputs.analysisDocument,
  async (file) => {
    preview.value = null;
    previewError.value = '';
    if (!file) return;
    try {
      const document = await readAnalysisDocument(file);
      if (assertInputs.analysisDocument === file) preview.value = document;
    } catch (error) {
      if (assertInputs.analysisDocument === file)
        previewError.value =
          error instanceof Error ? error.message : '分析 JSON 无效';
    }
  },
  { immediate: true },
);
const latestAnalysisId = computed(() => codeLocate.result?.analysisId || '');

function beforeUploadArchive(file: File) {
  assertInputs.codeArchive = file;
  return false;
}

function beforeUploadDatabase(file: File) {
  assertInputs.analysisDocument = file.name.toLowerCase().endsWith('.json')
    ? file
    : null;
  assertInputs.databaseFile = assertInputs.analysisDocument ? null : file;
  assertInputs.databasePath = '';
  return false;
}

function removeArchive() {
  assertInputs.codeArchive = null;
  return true;
}

function removeDatabase() {
  assertInputs.analysisDocument = null;
  assertInputs.databaseFile = null;
  return true;
}

async function selectLatestDatabase() {
  await useLatestCodeLocateOutput();
}
</script>

<template>
  <div
    ref="moduleRef"
    class="analysis-module"
    :class="{ 'analysis-module--focused': assertGeneration.started }"
    :style="{ '--module-workspace-height': workspaceHeight }"
  >
    <header class="module-heading">
      <div>
        <h1>断言生成</h1>
        <p v-if="!assertGeneration.started">
          使用匹配的源码包和分析 JSON，单独生成断言与插桩产物。
        </p>
      </div>
      <div class="module-heading-actions">
        <Button
          v-if="
            assertGeneration.started && assertGeneration.status !== 'running'
          "
          size="small"
          @click="resetAssertGenerationOutput"
        >
          返回输入
        </Button>
        <Button
          v-if="assertGeneration.status === 'running'"
          danger
          size="small"
          @click="stopAssertGeneration"
        >
          <template #icon><IconifyIcon icon="mdi:stop" /></template>
          停止
        </Button>
        <Tag
          :color="
            assertGeneration.status === 'running' ? 'processing' : 'default'
          "
        >
          {{
            assertGeneration.status === 'running'
              ? '进行中'
              : assertGeneration.status === 'done'
                ? '已完成'
                : assertGeneration.status === 'stopped'
                  ? '已停止'
                  : assertGeneration.status === 'error'
                    ? '异常'
                    : '待运行'
          }}
        </Tag>
      </div>
    </header>

    <Card v-if="!assertGeneration.started" class="module-card" title="输入">
      <div class="module-input-grid">
        <div class="module-input-field">
          <div class="module-input-label">源码压缩包 *</div>
          <Upload
            :before-upload="beforeUploadArchive"
            :disabled="assertGeneration.status === 'running'"
            :file-list="archiveFileList"
            @remove="removeArchive"
          >
            <Button :disabled="assertGeneration.status === 'running'">
              <template #icon><IconifyIcon icon="mdi:upload" /></template>
              选择源码压缩包
            </Button>
          </Upload>
        </div>

        <div class="module-input-field">
          <div class="module-input-label">分析结果 JSON *</div>
          <Upload
            accept=".json,application/json,.db,.sqlite,.sqlite3"
            :before-upload="beforeUploadDatabase"
            :disabled="assertGeneration.status === 'running'"
            :file-list="databaseFileList"
            @remove="removeDatabase"
          >
            <Button :disabled="assertGeneration.status === 'running'">
              <template #icon><IconifyIcon icon="mdi:upload" /></template>
              上传分析 JSON
            </Button>
          </Upload>
          <Button
            :disabled="
              !latestAnalysisId ||
              !codeLocate.inputArchive ||
              assertGeneration.status === 'running'
            "
            @click="selectLatestDatabase"
          >
            使用最近分析结果及源码
          </Button>
          <small class="module-help"
            >也支持具有可验证来源的旧版数据库；推荐使用分析 JSON。</small
          >
          <p v-if="previewError" role="alert">{{ previewError }}</p>
          <div v-if="preview" class="analysis-preview">
            <p>
              {{ preview.protocol.name }} · {{ preview.source.archiveName }}
            </p>
            <p>
              共 {{ preview.results.length }} 条分析结果；可生成断言
              {{ eligible.length }} 条，排除 {{ excluded.length }} 条。
            </p>
            <p v-for="(diagnostic, index) in preview.diagnostics" :key="index">
              {{ diagnostic.message }}
            </p>
            <ul v-if="excluded.length > 0">
              <li v-for="result in excluded" :key="result.id">
                {{ result.rule.description }}：{{
                  result.diagnostics.map((d) => d.message).join('；') ||
                  (result.verdict === 'compliant'
                    ? '未发现违规'
                    : result.verdict === 'needs_review'
                      ? '需要复核'
                      : '缺少已验证的代码位置')
                }}
              </li>
            </ul>
            <small>提交时将校验源码内容及代码证据是否与分析结果匹配。</small>
          </div>
        </div>
      </div>
    </Card>

    <div v-if="assertGeneration.error" class="module-error" role="alert">
      <IconifyIcon icon="mdi:alert-circle-outline" />
      <span>{{ assertGeneration.error }}</span>
    </div>

    <div
      v-if="!assertGeneration.started || assertGeneration.result"
      class="module-actions"
    >
      <Button
        v-if="!assertGeneration.started"
        type="primary"
        size="large"
        :loading="assertGeneration.status === 'running'"
        :disabled="
          assertGeneration.status === 'running' ||
          !!previewError ||
          (!!assertInputs.analysisDocument &&
            (!preview || eligible.length === 0))
        "
        @click="runAssertGeneration"
      >
        <template #icon><IconifyIcon icon="mdi:play" /></template>
        开始断言生成
      </Button>
      <Button
        v-if="assertGeneration.result?.artifacts?.zipPath"
        :loading="downloading"
        @click="downloadArtifact('tasks')"
      >
        下载断言任务
      </Button>
      <Button
        v-if="assertGeneration.result?.artifacts?.instrumentedCodeZipPath"
        :loading="downloading"
        @click="downloadArtifact('instrumented-code')"
      >
        下载插桩源码
      </Button>
      <span v-if="assertGeneration.result" class="output-reference">
        输出任务 ID：{{ assertGeneration.result.jobId }}
      </span>
    </div>

    <StageAssertGen
      v-if="assertGeneration.started"
      class="module-assert-stage"
      focused
      :events="assertGeneration.job?.events"
      :log-text="assertGeneration.logText"
      :diff-content="assertGeneration.diffContent"
      :result="assertGeneration.result"
      :running="assertGeneration.status === 'running'"
    />
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

.module-assert-stage {
  flex: 1;
  min-width: 0;
}

@media (min-width: 961px) {
  .analysis-module--focused {
    height: var(--module-workspace-height);
  }
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

.database-path-row {
  display: flex;
  gap: 8px;
  align-items: center;
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

@media (max-width: 760px) {
  .module-input-grid {
    grid-template-columns: 1fr;
  }

  .analysis-preview {
    max-height: 240px;
    overflow: auto;
    overflow-wrap: anywhere;
  }

  .database-path-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
