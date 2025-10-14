<script lang="ts" setup>
import type { FormInstance, UploadFile, UploadProps } from 'ant-design-vue';

import type {
  ProtocolComplianceTask,
  ProtocolComplianceTaskStatus,
} from '#/api';

import {
  computed,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue';

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

type TaskItem = ProtocolComplianceTask & {
  isMock?: boolean;
  progress?: number;
  resultPayload?: Record<string, unknown>;
};

const STORAGE_KEY = 'protocol-compliance-task-queue';
const remoteApiEnabled =
  import.meta.env.VITE_ENABLE_PROTOCOL_COMPLIANCE_API === 'true';

const tasks = ref<TaskItem[]>([]);
const isLoadingTasks = ref(false);
const isModalOpen = ref(false);
const isSubmitting = ref(false);

const formRef = ref<FormInstance>();
const formState = reactive({
  description: '',
  name: '',
});

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

const mockTimers = new Map<string, number[]>();

const isUsingMockQueue = computed(() => !remoteApiEnabled);

function registerTimer(taskId: string, timer: number) {
  const queue = mockTimers.get(taskId) ?? [];
  queue.push(timer);
  mockTimers.set(taskId, queue);
}

function clearTaskTimers(taskId: string) {
  const timers = mockTimers.get(taskId);
  if (!timers) {
    return;
  }
  timers.forEach((timer) => {
    window.clearTimeout(timer);
  });
  mockTimers.delete(taskId);
}

function updateTask(taskId: string, patch: Partial<TaskItem>) {
  tasks.value = tasks.value.map((task) =>
    task.id === taskId
      ? {
          ...task,
          ...patch,
        }
      : task,
  );
}

function buildMockResultPayload(task: TaskItem) {
  return {
    complianceSummary: {
      criticalFindings: [
        {
          description: '握手阶段缺少重传策略。',
          section: '4.2',
          severity: 'high',
        },
      ],
      docTitle: task.documentName,
      extractedAt: new Date().toISOString(),
      overview: '解析结果基于文档内容模拟生成，请在真实后端可用后替换。',
    },
    metadata: {
      taskId: task.id,
      uploadedAt: task.submittedAt,
    },
    protocolRules: [
      {
        action: '验证握手报文结构',
        reference: 'RFC Example 1.1',
        requirement: '客户端在握手阶段必须提供带签名的 ClientHello 消息。',
      },
      {
        action: '校验状态同步',
        reference: 'RFC Example 2.4',
        requirement: '服务端在进入数据阶段前需要返回 Session Ticket。',
      },
    ],
  };
}

function simulateTaskProcessing(task: TaskItem) {
  if (!isUsingMockQueue.value) {
    return;
  }

  const updateMoments = [
    { delay: 600, progress: 30 },
    { delay: 1200, progress: 65 },
    { delay: 1800, progress: 90 },
  ];

  updateMoments.forEach(({ delay, progress }) => {
    const timer = window.setTimeout(() => {
      updateTask(task.id, {
        progress,
        status: 'processing',
        updatedAt: new Date().toISOString(),
      });
    }, delay);
    registerTimer(task.id, timer);
  });

  const completeTimer = window.setTimeout(() => {
    const completedAt = new Date().toISOString();
    const currentTask = tasks.value.find((item) => item.id === task.id) ?? task;
    updateTask(task.id, {
      completedAt,
      progress: 100,
      resultPayload: buildMockResultPayload(currentTask),
      status: 'completed',
      updatedAt: completedAt,
    });
    clearTaskTimers(task.id);
  }, 2600);
  registerTimer(task.id, completeTimer);
}

function resetForm() {
  formRef.value?.resetFields();
  formState.name = '';
  formState.description = '';
  fileList.value = [];
  selectedUploadFile.value = null;
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
  return false;
};

const handleRemoveFile: UploadProps['onRemove'] = () => {
  selectedUploadFile.value = null;
  fileList.value = [];
  return true;
};

function restoreTasksFromStorage() {
  if (remoteApiEnabled || typeof window === 'undefined') {
    return;
  }
  try {
    const cachedRaw = window.localStorage.getItem(STORAGE_KEY);
    if (!cachedRaw) {
      return;
    }
    const parsed = JSON.parse(cachedRaw) as TaskItem[];
    tasks.value = parsed;
  } catch (error) {
    console.warn('[protocol-compliance] Failed to restore cached tasks', error);
  }
}

function persistTasks() {
  if (remoteApiEnabled || typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks.value));
  } catch (error) {
    console.warn('[protocol-compliance] Failed to persist tasks', error);
  }
}

async function loadTasksFromBackend() {
  if (!remoteApiEnabled) {
    return;
  }
  isLoadingTasks.value = true;
  try {
    const response = await fetchProtocolComplianceTasks({
      page: 1,
      pageSize: 20,
    });
    tasks.value = response.items;
  } catch (error) {
    console.warn('[protocol-compliance] Failed to fetch tasks', error);
  } finally {
    isLoadingTasks.value = false;
  }
}

async function handleSubmitTask() {
  if (!formState.name.trim()) {
    message.error('请输入任务名称');
    return;
  }

  if (!selectedUploadFile.value) {
    message.error('请上传需要解析的协议文档');
    return;
  }

  const documentFile = selectedUploadFile.value.originFileObj;
  if (!documentFile) {
    message.error('获取上传文件内容失败，请重新选择文档');
    return;
  }

  isSubmitting.value = true;
  const now = new Date().toISOString();

  try {
    if (remoteApiEnabled) {
      const createdTask = await createProtocolComplianceTask({
        description: formState.description.trim() || undefined,
        document: documentFile,
        name: formState.name.trim(),
      });
      tasks.value = [createdTask, ...tasks.value];
      message.success('任务已提交至解析队列');
    } else {
      const newTask: TaskItem = {
        completedAt: undefined,
        description: formState.description.trim(),
        documentName: selectedUploadFile.value.name,
        id: `mock-${Date.now()}`,
        isMock: true,
        progress: 20,
        status: 'processing',
        submittedAt: now,
        updatedAt: now,
      };
      tasks.value = [newTask, ...tasks.value];
      message.success('任务已加入解析队列（模拟）');
      simulateTaskProcessing(newTask);
    }
    persistTasks();
    isModalOpen.value = false;
    resetForm();
  } catch (error) {
    console.warn('[protocol-compliance] Failed to create task', error);
  } finally {
    isSubmitting.value = false;
  }
}

async function handleDownloadResult(task: TaskItem) {
  if (task.status !== 'completed') {
    message.info('解析尚未完成，暂不可下载结果');
    return;
  }

  if (task.resultPayload) {
    const blob = new Blob([JSON.stringify(task.resultPayload, null, 2)], {
      type: 'application/json',
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    const filename = `${getBaseFileName(task.documentName)}-rules.json`;
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    return;
  }

  if (task.resultDownloadUrl) {
    window.open(task.resultDownloadUrl, '_blank');
    return;
  }

  if (!remoteApiEnabled) {
    message.warning('未找到可下载的结果，请稍后重试');
    return;
  }

  try {
    const blob = await downloadProtocolComplianceTaskResult(task.id);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    const filename = `${getBaseFileName(task.documentName)}-rules.json`;
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

function handleModalCancel() {
  isModalOpen.value = false;
  resetForm();
}

function handleRefreshQueue() {
  if (remoteApiEnabled) {
    loadTasksFromBackend();
    return;
  }
  persistTasks();
  message.success('队列状态已刷新');
}

function openCreateTaskModal() {
  isModalOpen.value = true;
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
    loadTasksFromBackend();
  } else {
    restoreTasksFromStorage();
  }
});

onBeforeUnmount(() => {
  mockTimers.forEach((timers) => {
    timers.forEach((timer) => {
      window.clearTimeout(timer);
    });
  });
  mockTimers.clear();
});

if (!remoteApiEnabled) {
  watch(
    tasks,
    () => {
      persistTasks();
    },
    { deep: true },
  );
}
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
              <Tag v-if="isUsingMockQueue" color="blue">本地模拟队列</Tag>
              <Tag v-else color="green">远程后端</Tag>
            </p>
          </div>

          <Space>
            <Button
              :loading="isLoadingTasks"
              :type="isUsingMockQueue ? 'default' : 'primary'"
              @click="handleRefreshQueue"
            >
              刷新队列
            </Button>
            <Button type="primary" @click="openCreateTaskModal">
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
                :title="task.documentName"
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
                    v-if="task.status === 'processing'"
                    :percent="task.progress ?? 40"
                    :show-info="false"
                    status="active"
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
      <Form ref="formRef" :model="formState" layout="vertical">
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
