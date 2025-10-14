<script lang="ts" setup>
import type { FormInstance, UploadFile, UploadProps } from 'ant-design-vue';
import type { Rule } from 'ant-design-vue/es/form';

import type {
  ProtocolComplianceTask,
  ProtocolComplianceTaskStatus,
} from '#/api';

import { onBeforeUnmount, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Empty,
  Form,
  FormItem,
  Input,
  message,
  Modal,
  Progress,
  Space,
  Tag,
  Upload,
} from 'ant-design-vue';

import {
  createProtocolComplianceTask,
  downloadProtocolComplianceTaskResult,
  fetchProtocolComplianceTasks,
} from '#/api';

const remoteApiEnabled =
  import.meta.env.VITE_ENABLE_PROTOCOL_COMPLIANCE_API !== 'false';

const tasks = ref<ProtocolComplianceTask[]>([]);
const isLoadingTasks = ref(false);
const isModalOpen = ref(false);
const isSubmitting = ref(false);
const lastFetchError = ref<null | string>(null);

const formRef = ref<FormInstance>();
const formState = reactive({
  description: '',
  document: null as File | null,
  name: '',
});

const formRules: Record<string, Rule[]> = {
  name: [
    {
      message: '请输入任务名称',
      required: true,
      trigger: 'blur',
    },
  ],
  document: [
    {
      message: '请上传需要解析的协议文档',
      required: true,
      trigger: 'change',
    },
  ],
};

const fileList = ref<UploadFile[]>([]);
const selectedUploadFile = ref<null | UploadFile>(null);

const statusMeta: Record<
  ProtocolComplianceTaskStatus,
  { color: string; label: string }
> = {
  completed: {
    color: 'success',
    label: '解析完成',
  },
  failed: {
    color: 'error',
    label: '解析失败',
  },
  processing: {
    color: 'processing',
    label: '解析中',
  },
  queued: {
    color: 'default',
    label: '等待中',
  },
};

let pollingTimer: null | number = null;

async function loadTasks(options?: { silently?: boolean }) {
  if (!remoteApiEnabled) {
    return;
  }
  if (!options?.silently) {
    isLoadingTasks.value = true;
    lastFetchError.value = null;
  }
  try {
    const response = await fetchProtocolComplianceTasks({
      page: 1,
      pageSize: 50,
    });
    tasks.value = response.items;
  } catch (error) {
    console.warn('[protocol-compliance] Failed to fetch tasks', error);
    lastFetchError.value = '加载任务队列失败，请稍后重试。';
    if (!options?.silently) {
      message.error(lastFetchError.value);
    }
  } finally {
    if (!options?.silently) {
      isLoadingTasks.value = false;
    }
  }
}

function startPolling() {
  if (!remoteApiEnabled || pollingTimer !== null) {
    return;
  }
  pollingTimer = window.setInterval(() => {
    loadTasks({ silently: true });
  }, 5000);
}

function stopPolling() {
  if (pollingTimer !== null) {
    window.clearInterval(pollingTimer);
    pollingTimer = null;
  }
}

function resetForm() {
  formRef.value?.resetFields();
  formState.name = '';
  formState.description = '';
  formState.document = null;
  fileList.value = [];
  selectedUploadFile.value = null;
  formRef.value?.clearValidate?.();
}

function getBaseFileName(fileName: string) {
  const index = fileName.lastIndexOf('.');
  if (index === -1) {
    return fileName;
  }
  return fileName.slice(0, index);
}

const handleBeforeUpload: UploadProps['beforeUpload'] = (file) => {
  selectedUploadFile.value = file;
  fileList.value = [file];
  if (!formState.name) {
    formState.name = getBaseFileName(file.name);
  }
  const actualFile =
    (file as UploadFile<File>).originFileObj ?? (file as unknown as File);
  formState.document = actualFile;
  formRef.value?.clearValidate?.(['document']);
  return false;
};

const handleRemoveFile: UploadProps['onRemove'] = () => {
  selectedUploadFile.value = null;
  fileList.value = [];
  formState.document = null;
  formRef.value?.validateFields?.(['document']);
  return true;
};

function handleModalCancel() {
  isModalOpen.value = false;
  resetForm();
}

function handleRefreshQueue() {
  if (!remoteApiEnabled) {
    message.warning('当前环境未启用协议解析服务');
    return;
  }
  loadTasks();
}

function openCreateTaskModal() {
  if (!remoteApiEnabled) {
    message.warning('当前环境未启用协议解析服务');
    return;
  }
  isModalOpen.value = true;
}

async function handleSubmitTask() {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }

  const documentFile = formState.document;
  if (!documentFile) {
    message.error('获取上传文件内容失败，请重新选择文档');
    return;
  }

  if (!remoteApiEnabled) {
    message.warning('当前环境未启用协议解析服务');
    return;
  }

  isSubmitting.value = true;
  try {
    const createdTask = await createProtocolComplianceTask({
      description: formState.description.trim() || undefined,
      document: documentFile,
      name: formState.name.trim(),
    });
    message.success('任务已提交至解析队列');
    isModalOpen.value = false;
    resetForm();
    tasks.value = [
      createdTask,
      ...tasks.value.filter((task) => task.id !== createdTask.id),
    ];
    loadTasks({ silently: true });
  } catch (error) {
    console.warn('[protocol-compliance] Failed to create task', error);
    message.error('提交任务失败，请稍后再试');
  } finally {
    isSubmitting.value = false;
  }
}

async function handleDownloadResult(task: ProtocolComplianceTask) {
  if (task.status !== 'completed') {
    message.info('解析尚未完成，暂不可下载结果');
    return;
  }

  try {
    const blob = await downloadProtocolComplianceTaskResult(task.id);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    const filename = `${getBaseFileName(
      task.name || task.documentName,
    )}-rules.json`;
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.warn('[protocol-compliance] Failed to download result', error);
    message.error('下载失败，请稍后再试');
  }
}

function formatDateTime(value?: string) {
  if (!value) {
    return '-';
  }
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      month: '2-digit',
      second: '2-digit',
      year: 'numeric',
    }).format(new Date(value));
  } catch (error) {
    console.warn('[protocol-compliance] Failed to format date', error);
    return value;
  }
}

onMounted(() => {
  if (remoteApiEnabled) {
    loadTasks();
    startPolling();
  } else {
    message.warning('协议解析接口未启用，暂无法创建任务');
  }
});

onBeforeUnmount(() => {
  stopPolling();
});
</script>

<template>
  <Page
    description="上传协议规范文档，等待解析完成后即可下载提取的规则数据。"
    title="协议规则提取"
  >
    <div class="flex flex-col gap-4">
      <Card>
        <Space class="w-full justify-between" direction="horizontal">
          <div class="flex flex-col gap-2">
            <p class="intro-text">
              将协议文档交给系统解析后，我们会提取关键版本、握手流程、状态机等规则信息。解析完成后，可以下载结构化的
              JSON 文件用于后续编排或测试。
            </p>
            <p class="intro-helper">
              当前环境使用：
              <Tag v-if="remoteApiEnabled" color="blue">Mock 接口服务</Tag>
              <Tag v-else color="red">解析接口未启用</Tag>
            </p>
            <p v-if="lastFetchError" class="intro-helper text-danger">
              {{ lastFetchError }}
            </p>
          </div>

          <Space>
            <Button
              :disabled="!remoteApiEnabled"
              :loading="isLoadingTasks"
              @click="handleRefreshQueue"
            >
              刷新队列
            </Button>
            <Button
              :disabled="!remoteApiEnabled"
              type="primary"
              @click="openCreateTaskModal"
            >
              新建任务
            </Button>
          </Space>
        </Space>
      </Card>

      <Card title="任务队列">
        <template #extra>
          <span class="text-secondary"> 共 {{ tasks.length }} 个任务 </span>
        </template>
        <div v-if="tasks.length === 0" class="py-12">
          <Empty description="当前队列为空，点击“新建任务”开始上传协议文档。" />
        </div>
        <ol v-else class="task-queue">
          <li v-for="(task, index) in tasks" :key="task.id">
            <div class="task-item">
              <span class="task-item__number">{{ index + 1 }}.</span>
              <Card
                :body-style="{ padding: '16px' }"
                :title="task.name || task.documentName"
                class="task-item__content"
                size="small"
              >
                <template #extra>
                  <Space size="small">
                    <Tag :color="statusMeta[task.status].color">
                      {{ statusMeta[task.status].label }}
                    </Tag>
                    <Button
                      v-if="task.status === 'completed'"
                      size="small"
                      type="link"
                      @click="handleDownloadResult(task)"
                    >
                      下载 JSON
                    </Button>
                  </Space>
                </template>

                <div class="task-item__details">
                  <p class="text-secondary mb-1">
                    关联文档：{{ task.documentName }}
                  </p>
                  <p class="text-secondary mb-1">
                    提交时间：{{ formatDateTime(task.submittedAt) }}
                  </p>
                  <p class="text-secondary mb-1">
                    最近更新：{{ formatDateTime(task.updatedAt) }}
                  </p>
                  <p
                    v-if="task.description"
                    class="mb-2 text-sm leading-relaxed text-[var(--ant-text-color)]"
                  >
                    {{ task.description }}
                  </p>

                  <Progress
                    v-if="
                      task.status === 'processing' || task.status === 'queued'
                    "
                    :percent="task.progress ?? 0"
                    :show-info="false"
                    :status="task.status === 'processing' ? 'active' : 'normal'"
                    :stroke-width="6"
                  />
                  <p v-if="task.status === 'failed'" class="text-danger mb-0">
                    解析失败，可稍后重新提交任务。
                  </p>
                </div>
              </Card>
            </div>
          </li>
        </ol>
      </Card>
    </div>

    <Modal
      v-model:open="isModalOpen"
      :confirm-loading="isSubmitting"
      title="创建解析任务"
      :width="520"
      @cancel="handleModalCancel"
      @ok="handleSubmitTask"
    >
      <Form
        ref="formRef"
        :model="formState"
        :rules="formRules"
        layout="vertical"
      >
        <FormItem label="任务名称" name="name" required>
          <Input
            v-model:value="formState.name"
            placeholder="例如：TLS 1.3 协议（RFC 8446）"
          />
        </FormItem>
        <FormItem label="任务说明" name="description">
          <Input.TextArea
            v-model:value="formState.description"
            :auto-size="{ maxRows: 5, minRows: 3 }"
            placeholder="可选：补充协议版本、关注点等信息"
          />
        </FormItem>
        <FormItem label="上传协议文档" name="document" required>
          <Upload
            :before-upload="handleBeforeUpload"
            :file-list="fileList"
            :max-count="1"
            :on-remove="handleRemoveFile"
          >
            <Button block>选择文档</Button>
          </Upload>
          <p class="upload-helper">
            支持 PDF、Markdown、TXT 等文本格式。文件将在提交任务时上传。
          </p>
        </FormItem>
      </Form>
    </Modal>
  </Page>
</template>

<style scoped>
.intro-text {
  margin: 0;
  line-height: 1.6;
  color: var(--ant-text-color);
}

.intro-helper {
  margin: 0;
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}

.task-queue {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0;
  margin: 0;
  list-style: none;
}

.task-item {
  display: flex;
  gap: 1rem;
  align-items: stretch;
}

.task-item__number {
  min-width: 24px;
  font-weight: 600;
  color: var(--ant-color-primary);
  text-align: right;
}

.task-item__content {
  flex: 1;
}

.task-item__details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.text-secondary {
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}

.text-danger {
  color: var(--ant-color-error);
}

.upload-helper {
  margin-top: 8px;
  margin-bottom: 0;
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}

@media (max-width: 768px) {
  .task-item {
    flex-direction: column;
  }

  .task-item__number {
    text-align: left;
  }

  .task-item__content {
    width: 100%;
  }

  .intro-text {
    font-size: 14px;
  }
}
</style>
