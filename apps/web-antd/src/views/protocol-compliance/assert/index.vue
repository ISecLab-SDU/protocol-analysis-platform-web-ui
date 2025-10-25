<script lang="ts" setup>
import type { FormInstance, UploadFile, UploadProps } from 'ant-design-vue';
import type { Rule } from 'ant-design-vue/es/form';

import type {
  ProtocolAssertGenerationJob,
  ProtocolAssertGenerationProgressEvent,
  ProtocolAssertGenerationResult,
  ProtocolDiffParsingJob,
  ProtocolDiffParsingProgressEvent,
  ProtocolDiffParsingResult,
} from '#/api/protocol-compliance';

import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  Button,
  Card,
  Collapse,
  Descriptions,
  Form,
  FormItem,
  Input,
  message,
  Progress,
  Space,
  Tag,
  Tooltip,
  Typography,
  Upload,
} from 'ant-design-vue';

import {
  fetchProtocolAssertGenerationProgress,
  fetchProtocolAssertGenerationResult,
  runProtocolAssertGeneration,
  downloadProtocolAssertGenerationResult,
  startProtocolDiffParsing,
  fetchProtocolDiffParsingProgress,
  fetchProtocolDiffParsingResult,
} from '#/api/protocol-compliance';

const formRef = ref<FormInstance>();
const formState = reactive({
  archive: null as File | null,
  buildInstructions: '',
  database: null as File | null,
  notes: '',
});

const archiveFileList = ref<UploadFile[]>([]);
const databaseFileList = ref<UploadFile[]>([]);
const isSubmitting = ref(false);
const analysisResult = ref<null | ProtocolAssertGenerationResult>(null);
const activeJob = ref<null | ProtocolAssertGenerationJob>(null);
const activeJobId = ref<null | string>(null);
const progressLogs = ref<string[]>([]);
const progressError = ref<null | string>(null);
const pollingTimer = ref<null | number>(null);

// Diff Parsing State
const activeDiffJob = ref<null | ProtocolDiffParsingJob>(null);
const activeDiffJobId = ref<null | string>(null);
const diffResult = ref<null | ProtocolDiffParsingResult>(null);
const diffPollingTimer = ref<null | number>(null);
const diffProgressLogs = ref<string[]>([]);
const diffProgressError = ref<null | string>(null);
const activeDiffFileKeys = ref<number[]>([]);

const PROGRESS_STATUS_META: Record<
  ProtocolAssertGenerationJob['status'],
  { color: string; label: string }
> = {
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
  queued: { color: 'default', label: '排队中' },
  running: { color: 'processing', label: '运行中' },
};

const DIFF_STATUS_META: Record<
  ProtocolDiffParsingJob['status'],
  { color: string; label: string }
> = {
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
  queued: { color: 'default', label: '排队中' },
  running: { color: 'processing', label: '运行中' },
};

const formRules: Record<string, Rule[]> = {
  archive: [
    {
      message: '请上传完整项目压缩包',
      required: true,
      trigger: 'change',
    },
  ],
  database: [
    {
      message: '请上传 SQLite 数据库文件',
      required: true,
      trigger: 'change',
    },
  ],
  buildInstructions: [
    {
      message: '请填写编译指令',
      required: true,
      trigger: 'blur',
    },
  ],
};

const logFormatter = new Intl.DateTimeFormat(undefined, {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});

const progressStatus = computed<null | ProtocolAssertGenerationJob['status']>(
  () => activeJob.value?.status ?? null,
);

const progressStatusLabel = computed(() => {
  if (!progressStatus.value) {
    return '未开始';
  }
  return PROGRESS_STATUS_META[progressStatus.value].label;
});

const progressStatusColor = computed(() => {
  if (!progressStatus.value) {
    return 'default';
  }
  return PROGRESS_STATUS_META[progressStatus.value].color;
});

const progressMessage = computed(
  () => activeJob.value?.message ?? '等待任务开始',
);

const progressText = computed(() => {
  if (progressLogs.value.length === 0) {
    return '等待任务开始...';
  }
  return progressLogs.value.join('\n');
});

const canCopyProgressLogs = computed(() => progressLogs.value.length > 0);
const canDownloadResult = computed(
  () => progressStatus.value === 'completed' && activeJobId.value,
);

const diffProgressStatus = computed<null | ProtocolDiffParsingJob['status']>(
  () => activeDiffJob.value?.status ?? null,
);

const diffProgressStatusLabel = computed(() => {
  if (!diffProgressStatus.value) {
    return '未开始';
  }
  return DIFF_STATUS_META[diffProgressStatus.value].label;
});

const diffProgressStatusColor = computed(() => {
  if (!diffProgressStatus.value) {
    return 'default';
  }
  return DIFF_STATUS_META[diffProgressStatus.value].color;
});

const diffProgressMessage = computed(
  () => activeDiffJob.value?.message ?? '等待任务开始',
);

const diffProgressPercentage = computed(
  () => activeDiffJob.value?.percentage ?? 0,
);

const progressTextRef = ref<HTMLDivElement>();

watch(progressText, () => {
  nextTick(() => {
    if (progressTextRef.value) {
      progressTextRef.value.scrollTop = progressTextRef.value.scrollHeight;
    }
  });
});

function toProgressLine(event: ProtocolAssertGenerationProgressEvent) {
  const timeLabel = (() => {
    try {
      return logFormatter.format(new Date(event.timestamp));
    } catch {
      return event.timestamp ?? '';
    }
  })();
  const stage = event.stage || 'unknown';
  const messageText = event.message || '';
  return `[${timeLabel}] (${stage}) ${messageText}`;
}

function applyProgressSnapshot(snapshot: ProtocolAssertGenerationJob) {
  activeJob.value = snapshot;
  activeJobId.value = snapshot.jobId;
  progressError.value = snapshot.error ?? null;
  progressLogs.value = snapshot.events?.length
    ? snapshot.events.map((event) => toProgressLine(event))
    : [];
}

function stopPolling() {
  if (pollingTimer.value !== null) {
    window.clearInterval(pollingTimer.value);
    pollingTimer.value = null;
  }
}

function stopDiffPolling() {
  if (diffPollingTimer.value !== null) {
    window.clearInterval(diffPollingTimer.value);
    diffPollingTimer.value = null;
  }
}

function resetProgressState() {
  stopPolling();
  activeJob.value = null;
  activeJobId.value = null;
  progressLogs.value = [];
  progressError.value = null;
}

function resetDiffProgressState() {
  stopDiffPolling();
  activeDiffJob.value = null;
  activeDiffJobId.value = null;
  diffResult.value = null;
  diffProgressLogs.value = [];
  diffProgressError.value = null;
}

async function handleStatusTransition(
  previousStatus: null | ProtocolAssertGenerationJob['status'],
  snapshot: ProtocolAssertGenerationJob,
) {
  if (snapshot.status === 'completed') {
    stopPolling();
    isSubmitting.value = false;
    try {
      const result =
        snapshot.result ??
        (await fetchProtocolAssertGenerationResult(snapshot.jobId));
      analysisResult.value = result;
      if (previousStatus !== 'completed') {
        message.success('断言生成完成');
        // Automatically start diff parsing
        await startDiffParsingWorkflow(snapshot.jobId);
      }
    } catch (error) {
      const messageText =
        error instanceof Error ? error.message : String(error ?? '');
      progressError.value = messageText || '无法获取生成结果';
      if (previousStatus !== 'completed') {
        message.error(`获取断言生成结果失败：${messageText}`);
      }
    }
    return;
  }

  if (snapshot.status === 'failed') {
    stopPolling();
    isSubmitting.value = false;
    analysisResult.value = null;
    const failure =
      snapshot.error ?? snapshot.message ?? '断言生成失败，请查看后台日志';
    if (previousStatus !== 'failed') {
      message.error(failure);
    }
  }
}

async function refreshProgress(jobId: string) {
  const previousStatus = activeJob.value?.status ?? null;
  const snapshot = await fetchProtocolAssertGenerationProgress(jobId);
  applyProgressSnapshot(snapshot);
  await handleStatusTransition(previousStatus, snapshot);
}

function schedulePolling(jobId: string) {
  stopPolling();
  pollingTimer.value = window.setInterval(() => {
    refreshProgress(jobId).catch((error) => {
      progressError.value =
        error instanceof Error ? error.message : String(error ?? '');
    });
  }, 1500);
}

onBeforeUnmount(() => {
  stopPolling();
  stopDiffPolling();
});

async function copyToClipboard(content: string) {
  if (!content) {
    return false;
  }
  try {
    if (
      typeof navigator !== 'undefined' &&
      navigator.clipboard &&
      navigator.clipboard.writeText
    ) {
      await navigator.clipboard.writeText(content);
      return true;
    }
  } catch {
    // Ignore and fall back to execCommand path.
  }
  if (typeof document === 'undefined') {
    return false;
  }
  const textarea = document.createElement('textarea');
  textarea.value = content;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'absolute';
  textarea.style.left = '-9999px';
  document.body.append(textarea);
  textarea.select();
  try {
    return document.execCommand('copy');
  } catch {
    return false;
  } finally {
    textarea.remove();
  }
}

async function handleCopyProgressLogs() {
  if (!canCopyProgressLogs.value) {
    message.info('暂无日志可复制');
    return;
  }
  const copied = await copyToClipboard(progressLogs.value.join('\n'));
  if (copied) {
    message.success('日志已复制到剪贴板');
  } else {
    message.error('复制失败，请手动选择并复制');
  }
}

async function handleDownloadResult() {
  if (!activeJobId.value) {
    message.error('无可用的任务 ID');
    return;
  }
  try {
    const blob = await downloadProtocolAssertGenerationResult(
      activeJobId.value,
    );
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `assertion-generation-${activeJobId.value}.zip`;
    document.body.append(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    message.success('下载成功');
  } catch (error) {
    const messageText =
      error instanceof Error ? error.message : String(error ?? '');
    message.error(`下载失败：${messageText}`);
  }
}

const handleArchiveBeforeUpload: UploadProps['beforeUpload'] = (file) => {
  const actual =
    (file as UploadFile<File>).originFileObj ?? (file as unknown as File);
  archiveFileList.value = [file];
  formState.archive = actual;
  formRef.value?.clearValidate?.(['archive']);
  return false;
};

const handleArchiveRemove: UploadProps['onRemove'] = () => {
  archiveFileList.value = [];
  formState.archive = null;
  formRef.value?.validateFields?.(['archive']);
  return true;
};

const handleDatabaseBeforeUpload: UploadProps['beforeUpload'] = (file) => {
  const actual =
    (file as UploadFile<File>).originFileObj ?? (file as unknown as File);
  databaseFileList.value = [file];
  formState.database = actual;
  formRef.value?.clearValidate?.(['database']);
  return false;
};

const handleDatabaseRemove: UploadProps['onRemove'] = () => {
  databaseFileList.value = [];
  formState.database = null;
  formRef.value?.validateFields?.(['database']);
  return true;
};

function toDiffProgressLine(event: ProtocolDiffParsingProgressEvent) {
  const timeLabel = (() => {
    try {
      return logFormatter.format(new Date(event.timestamp));
    } catch {
      return event.timestamp ?? '';
    }
  })();
  const stage = event.stage || 'unknown';
  const messageText = event.message || '';
  const percentage = event.percentage || 0;
  return `[${timeLabel}] (${stage}) ${messageText} [${percentage}%]`;
}

function applyDiffProgressSnapshot(snapshot: ProtocolDiffParsingJob) {
  activeDiffJob.value = snapshot;
  activeDiffJobId.value = snapshot.jobId;
  diffProgressError.value = snapshot.error ?? null;
  diffProgressLogs.value = snapshot.events?.length
    ? snapshot.events.map((event) => toDiffProgressLine(event))
    : [];
}

async function handleDiffStatusTransition(
  previousStatus: null | ProtocolDiffParsingJob['status'],
  snapshot: ProtocolDiffParsingJob,
) {
  if (snapshot.status === 'completed') {
    stopDiffPolling();
    try {
      const result =
        snapshot.result ??
        (await fetchProtocolDiffParsingResult(
          snapshot.parentJobId,
          snapshot.jobId,
        ));
      diffResult.value = result;
      // Auto-expand first file in diff
      if (result.files.length > 0) {
        activeDiffFileKeys.value = [0];
      }
      if (previousStatus !== 'completed') {
        message.success('差异解析完成');
      }
    } catch (error) {
      const messageText =
        error instanceof Error ? error.message : String(error ?? '');
      diffProgressError.value = messageText || '无法获取解析结果';
      if (previousStatus !== 'completed') {
        message.error(`获取差异解析结果失败：${messageText}`);
      }
    }
    return;
  }

  if (snapshot.status === 'failed') {
    stopDiffPolling();
    diffResult.value = null;
    const failure =
      snapshot.error ?? snapshot.message ?? '差异解析失败，请查看后台日志';
    if (previousStatus !== 'failed') {
      message.error(failure);
    }
  }
}

async function refreshDiffProgress(assertJobId: string, diffJobId: string) {
  const previousStatus = activeDiffJob.value?.status ?? null;
  const snapshot = await fetchProtocolDiffParsingProgress(
    assertJobId,
    diffJobId,
  );
  applyDiffProgressSnapshot(snapshot);
  await handleDiffStatusTransition(previousStatus, snapshot);
}

function scheduleDiffPolling(assertJobId: string, diffJobId: string) {
  stopDiffPolling();
  diffPollingTimer.value = window.setInterval(() => {
    refreshDiffProgress(assertJobId, diffJobId).catch((error) => {
      diffProgressError.value =
        error instanceof Error ? error.message : String(error ?? '');
    });
  }, 1500);
}

async function startDiffParsingWorkflow(assertJobId: string) {
  try {
    resetDiffProgressState();
    const snapshot = await startProtocolDiffParsing(assertJobId);
    applyDiffProgressSnapshot(snapshot);
    await handleDiffStatusTransition(null, snapshot);
    if (snapshot.status === 'queued' || snapshot.status === 'running') {
      scheduleDiffPolling(assertJobId, snapshot.jobId);
    }
  } catch (error) {
    const messageText =
      error instanceof Error ? error.message : String(error ?? '');
    diffProgressError.value = messageText || '差异解析启动失败';
    message.error(`启动差异解析失败：${messageText}`);
  }
}

function handleReset() {
  formRef.value?.resetFields();
  archiveFileList.value = [];
  databaseFileList.value = [];
  formState.archive = null;
  formState.database = null;
  formState.buildInstructions = '';
  formState.notes = '';
  analysisResult.value = null;
  resetProgressState();
  resetDiffProgressState();
}

async function handleSubmit() {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }

  const { archive, buildInstructions, database } = formState;
  if (!archive || !database || !buildInstructions) {
    return;
  }

  resetProgressState();
  isSubmitting.value = true;
  analysisResult.value = null;
  try {
    const snapshot = await runProtocolAssertGeneration({
      buildInstructions,
      codeArchive: archive,
      database,
      notes: formState.notes,
    });
    applyProgressSnapshot(snapshot);
    await handleStatusTransition(null, snapshot);
    if (snapshot.status === 'queued' || snapshot.status === 'running') {
      schedulePolling(snapshot.jobId);
    }
  } catch (error) {
    const messageText =
      error instanceof Error ? error.message : String(error ?? '');
    progressError.value = messageText || '断言生成启动失败';
    message.error(`启动断言生成失败：${messageText}`);
    analysisResult.value = null;
    isSubmitting.value = false;
  } finally {
    if (
      progressStatus.value !== 'queued' &&
      progressStatus.value !== 'running'
    ) {
      isSubmitting.value = false;
    }
  }
}
</script>

<template>
  <Page
    description="上传源码压缩包、SQLite 数据库文件，并提供编译指令，自动生成测试断言以验证协议实现的正确性。"
    title="断言生成"
  >
    <div class="assert-generation">
      <!-- 第一部分：提交和进度 -->
      <div class="layout-grid">
        <Card class="upload-card" title="上传分析材料">
          <Form
            ref="formRef"
            :model="formState"
            :rules="formRules"
            class="compact-form"
            layout="vertical"
          >
            <FormItem label="源码压缩包" name="archive" required>
              <Upload
                :before-upload="handleArchiveBeforeUpload"
                :file-list="archiveFileList"
                :max-count="1"
                :on-remove="handleArchiveRemove"
                accept=".zip,.tar,.gz,.tgz,.bz2,.xz,.7z,application/zip,application/x-tar"
              >
                <Button block type="dashed">
                  <IconifyIcon icon="ant-design:file-outlined" class="mr-1" />
                  选择源码压缩包
                </Button>
              </Upload>
            </FormItem>

            <FormItem label="数据库文件（SQLite）" name="database" required>
              <Upload
                :before-upload="handleDatabaseBeforeUpload"
                :file-list="databaseFileList"
                :max-count="1"
                :on-remove="handleDatabaseRemove"
                accept=".db,.sqlite,.sqlite3,.db3,application/x-sqlite3,application/vnd.sqlite3"
              >
                <Button block type="dashed">
                  <IconifyIcon
                    icon="ant-design:database-outlined"
                    class="mr-1"
                  />
                  选择数据库文件
                </Button>
              </Upload>
            </FormItem>

            <FormItem label="编译指令" name="buildInstructions" required>
              <Input.TextArea
                v-model:value="formState.buildInstructions"
                :auto-size="{ minRows: 3, maxRows: 6 }"
                placeholder="请输入编译指令，例如：make all 或 gcc main.c -o main"
              />
            </FormItem>

            <FormItem label="备注" name="notes">
              <Input.TextArea
                v-model:value="formState.notes"
                :auto-size="{ minRows: 2, maxRows: 4 }"
                placeholder="可选：说明协议版本、提交记录或其他上下文信息"
              />
            </FormItem>

            <FormItem class="form-actions" :colon="false">
              <Space>
                <Button @click="handleReset">
                  <IconifyIcon icon="ant-design:clear-outlined" class="mr-1" />
                  清空
                </Button>
                <Button
                  :loading="isSubmitting"
                  type="primary"
                  @click="handleSubmit"
                >
                  <IconifyIcon
                    v-if="!isSubmitting"
                    icon="ant-design:thunderbolt-outlined"
                    class="mr-1"
                  />
                  开始生成
                </Button>
              </Space>
            </FormItem>
          </Form>
        </Card>

        <Card class="progress-card" title="生成进度">
          <template #extra>
            <Space>
              <Button
                :disabled="!canCopyProgressLogs"
                size="small"
                type="link"
                @click="handleCopyProgressLogs"
              >
                <IconifyIcon icon="ant-design:copy-outlined" class="mr-1" />
                复制日志
              </Button>
              <Button
                :disabled="!canDownloadResult"
                size="small"
                type="link"
                @click="handleDownloadResult"
              >
                <IconifyIcon icon="ant-design:download-outlined" class="mr-1" />
                下载结果
              </Button>
            </Space>
          </template>
          <div class="progress-box">
            <Space class="progress-status" wrap>
              <Tag :color="progressStatusColor">{{ progressStatusLabel }}</Tag>
              <span class="progress-message">{{ progressMessage }}</span>
            </Space>
            <div
              ref="progressTextRef"
              aria-live="polite"
              class="progress-text"
              role="log"
            >
              {{ progressText }}
            </div>
            <p v-if="progressError" class="progress-error">
              {{ progressError }}
            </p>
          </div>
        </Card>
      </div>
      <!-- 结果展示 -->
      <Card v-if="analysisResult">
        <template #title>
          <Space>
            <IconifyIcon
              icon="ant-design:check-circle-outlined"
              class="text-lg"
            />
            <span>生成结果</span>
          </Space>
        </template>
        <Descriptions bordered :column="1" size="small">
          <Descriptions.Item>
            <template #label>
              <Space>
                <IconifyIcon icon="ant-design:number-outlined" />
                <span>任务 ID</span>
              </Space>
            </template>
            {{ activeJobId }}
          </Descriptions.Item>
          <Descriptions.Item>
            <template #label>
              <Space>
                <IconifyIcon icon="ant-design:api-outlined" />
                <span>协议名称</span>
              </Space>
            </template>
            {{ analysisResult.protocolName || '未知' }}
          </Descriptions.Item>
          <Descriptions.Item>
            <template #label>
              <Space>
                <IconifyIcon icon="ant-design:file-text-outlined" />
                <span>生成断言数</span>
              </Space>
            </template>
            {{ analysisResult.assertionCount || 0 }}
          </Descriptions.Item>
          <Descriptions.Item>
            <template #label>
              <Space>
                <IconifyIcon icon="ant-design:clock-circle-outlined" />
                <span>生成时间</span>
              </Space>
            </template>
            {{ analysisResult.generatedAt || '未知' }}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <!-- 差异解析进度 -->
      <Card v-if="activeDiffJob" title="代码差异解析">
        <div class="diff-parsing-progress">
          <Space class="progress-status" wrap>
            <Tag :color="diffProgressStatusColor">{{
              diffProgressStatusLabel
            }}</Tag>
            <span class="progress-message">{{ diffProgressMessage }}</span>
          </Space>
          <Progress
            :percent="diffProgressPercentage"
            :status="
              diffProgressStatus === 'failed'
                ? 'exception'
                : diffProgressStatus === 'completed'
                  ? 'success'
                  : 'active'
            "
            :stroke-color="{
              '0%': '#108ee9',
              '100%': '#87d068',
            }"
          />
          <p v-if="diffProgressError" class="progress-error">
            {{ diffProgressError }}
          </p>
        </div>
      </Card>

      <!-- 差异结果展示 -->
      <Card v-if="diffResult">
        <template #title>
          <Space>
            <IconifyIcon icon="ant-design:diff-outlined" class="text-lg" />
            <span>代码变更</span>
          </Space>
        </template>
        <template #extra>
          <Space>
            <Tooltip title="新增行数">
              <Tag color="success">
                <IconifyIcon icon="ant-design:plus-outlined" class="mr-1" />
                {{ diffResult.summary.insertions }}
              </Tag>
            </Tooltip>
            <Tooltip title="删除行数">
              <Tag color="error">
                <IconifyIcon icon="ant-design:minus-outlined" class="mr-1" />
                {{ diffResult.summary.deletions }}
              </Tag>
            </Tooltip>
            <Tooltip title="修改文件数">
              <Tag color="default">
                <IconifyIcon icon="ant-design:file-outlined" class="mr-1" />
                {{ diffResult.summary.filesChanged }}
              </Tag>
            </Tooltip>
          </Space>
        </template>

        <Collapse
          v-model:active-key="activeDiffFileKeys"
          class="diff-collapse"
          :bordered="false"
        >
          <Collapse.Panel
            v-for="(file, fileIndex) in diffResult.files"
            :key="fileIndex"
            class="diff-file-panel"
          >
            <template #header>
              <div class="diff-file-header-content">
                <Space>
                  <IconifyIcon icon="ant-design:file-text-outlined" />
                  <Typography.Text code class="file-path">
                    {{ file.from }}
                  </Typography.Text>
                  <template v-if="file.from !== file.to">
                    <IconifyIcon
                      icon="ant-design:arrow-right-outlined"
                      class="text-xs"
                    />
                    <Typography.Text code class="file-path">
                      {{ file.to }}
                    </Typography.Text>
                  </template>
                </Space>
                <Space class="file-stats">
                  <Tag v-if="file.additions > 0" color="success" size="small">
                    +{{ file.additions }}
                  </Tag>
                  <Tag v-if="file.deletions > 0" color="error" size="small">
                    -{{ file.deletions }}
                  </Tag>
                </Space>
              </div>
            </template>

            <div class="diff-viewer">
              <div
                v-for="(hunk, hunkIndex) in file.hunks"
                :key="hunkIndex"
                class="diff-hunk"
              >
                <div class="hunk-header">
                  <Typography.Text code class="hunk-info">
                    @@ -{{ hunk.oldStart }},{{ hunk.oldLines }} +{{
                      hunk.newStart
                    }},{{ hunk.newLines }} @@
                  </Typography.Text>
                </div>
                <div class="hunk-content">
                  <div
                    v-for="(line, lineIndex) in hunk.lines"
                    :key="lineIndex"
                    :class="['diff-line', `diff-line-${line.type}`]"
                  >
                    <span class="line-prefix">{{
                      line.type === 'add'
                        ? '+'
                        : line.type === 'delete'
                          ? '-'
                          : ' '
                    }}</span>
                    <Typography.Text class="line-content" :code="false">
                      {{ line.content }}
                    </Typography.Text>
                  </div>
                </div>
              </div>
            </div>
          </Collapse.Panel>
        </Collapse>
      </Card>
    </div>
  </Page>
</template>

<style scoped>
.assert-generation {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.layout-grid {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 16px;
  align-items: stretch;
  flex: 1;
  min-height: 0;
}

.upload-card,
.progress-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 500px;
}

.upload-card :deep(.ant-card-body),
.progress-card :deep(.ant-card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.compact-form {
  font-size: 13px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.form-actions {
  margin-bottom: 0;
  margin-top: 8px;
}

.progress-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.progress-status {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  font-size: 13px;
  margin-bottom: 12px;
}

.progress-message {
  color: var(--ant-text-color-secondary);
}

.progress-text {
  flex: 1;
  overflow-y: auto;
  min-height: 200px;
  max-height: 400px;
  padding: 12px;
  font-family:
    ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas,
    'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.45;
  color: var(--ant-text-color);
  word-break: break-word;
  white-space: pre-wrap;
  background-color: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border);
  border-radius: var(--ant-border-radius);
}

.progress-error {
  margin: 0;
  margin-top: 12px;
  font-size: 12px;
  color: var(--ant-color-error);
}

.video-container {
  width: 100%;
  aspect-ratio: 16 / 9;
  background-color: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border);
  border-radius: var(--ant-border-radius);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.demo-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.description-box {
  height: 100%;
  padding: 8px;
}

.description-title-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.description-title-icon {
  font-size: 20px;
  color: var(--ant-primary-color);
}

.description-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--ant-text-color);
}

.description-content {
  font-size: 13px;
  line-height: 1.6;
  color: var(--ant-text-color-secondary);
}

.description-content p {
  margin-bottom: 16px;
}

.description-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  font-size: 14px;
}

.section-header strong {
  color: var(--ant-text-color);
  font-weight: 600;
}

.workflow-list,
.usage-list {
  margin: 0;
  padding-left: 0;
  list-style: none;
}

.workflow-list li,
.usage-list li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;
  padding: 6px 0;
}

.step-icon,
.usage-icon {
  flex-shrink: 0;
  margin-top: 2px;
  color: var(--ant-primary-color);
  font-size: 14px;
}

.workflow-list li:hover,
.usage-list li:hover {
  color: var(--ant-text-color);
}

@media (max-width: 1200px) {
  .layout-grid {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .upload-card,
  .progress-card {
    min-height: 400px;
  }
}

.diff-parsing-progress {
  padding: 8px 0;
}

.diff-collapse {
  background-color: transparent;
}

.diff-collapse :deep(.ant-collapse-item) {
  border: 1px solid var(--ant-color-border);
  border-radius: var(--ant-border-radius);
  margin-bottom: 12px;
  overflow: hidden;
}

.diff-collapse :deep(.ant-collapse-item:last-child) {
  margin-bottom: 0;
}

.diff-collapse :deep(.ant-collapse-header) {
  padding: 12px 16px !important;
  background-color: var(--ant-color-fill-quaternary);
  align-items: center;
}

.diff-collapse :deep(.ant-collapse-content) {
  border-top: 1px solid var(--ant-color-border);
}

.diff-collapse :deep(.ant-collapse-content-box) {
  padding: 0;
}

.diff-file-header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 24px;
}

.file-stats {
  margin-left: auto;
}

.file-path {
  font-size: 13px;
  max-width: 500px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.diff-viewer {
  background-color: var(--ant-color-bg-container);
  overflow: hidden;
}

.diff-hunk {
  margin: 0;
}

.hunk-header {
  padding: 8px 16px;
  background-color: var(--ant-color-fill-alter);
  border-top: 1px solid var(--ant-color-border);
  border-bottom: 1px solid var(--ant-color-border);
}

.hunk-info {
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.hunk-content {
  margin: 0;
  padding: 0;
}

.diff-line {
  display: flex;
  padding: 0;
  margin: 0;
  line-height: 1.6;
  border-bottom: 1px solid transparent;
  transition: background-color 0.2s;
}

.diff-line:hover {
  filter: brightness(0.98);
}

.diff-line-add {
  background-color: var(--ant-success-color-deprecated-bg);
  border-bottom-color: var(--ant-success-color-deprecated-border);
}

.diff-line-delete {
  background-color: var(--ant-error-color-deprecated-bg);
  border-bottom-color: var(--ant-error-color-deprecated-border);
}

.diff-line-normal {
  background-color: var(--ant-color-bg-container);
}

.line-prefix {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  padding: 4px 8px;
  text-align: center;
  user-select: none;
  flex-shrink: 0;
  font-family:
    ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas,
    'Liberation Mono', 'Courier New', monospace;
  font-size: 13px;
  font-weight: 600;
  background-color: rgba(0, 0, 0, 0.02);
}

.diff-line-add .line-prefix {
  color: var(--ant-success-color);
  background-color: var(--ant-success-color-deprecated-bg);
}

.diff-line-delete .line-prefix {
  color: var(--ant-error-color);
  background-color: var(--ant-error-color-deprecated-bg);
}

.diff-line-normal .line-prefix {
  color: var(--ant-text-color-secondary);
}

.line-content {
  flex: 1;
  padding: 4px 12px;
  overflow-x: auto;
  font-family:
    ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas,
    'Liberation Mono', 'Courier New', monospace;
  font-size: 13px;
  white-space: pre;
  color: var(--ant-text-color);
}

/* Dark theme adjustments */
html[data-theme='dark'] .line-prefix {
  background-color: rgba(255, 255, 255, 0.04);
}

html[data-theme='dark'] .diff-line:hover {
  filter: brightness(1.1);
}
</style>
