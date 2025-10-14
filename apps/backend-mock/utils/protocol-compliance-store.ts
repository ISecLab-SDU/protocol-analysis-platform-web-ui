import { faker } from '@faker-js/faker';

export type ProtocolComplianceTaskStatus =
  | 'completed'
  | 'failed'
  | 'processing'
  | 'queued';

export interface ProtocolComplianceTaskInternal {
  completedAt?: string;
  description?: string;
  documentName: string;
  documentSize?: number;
  id: string;
  name: string;
  progress: number;
  status: ProtocolComplianceTaskStatus;
  submittedAt: string;
  tags?: string[];
  updatedAt: string;
  resultPayload?: Record<string, unknown>;
}

export interface CreateProtocolComplianceTaskInput {
  description?: string;
  documentName: string;
  documentSize?: number;
  name: string;
  tags?: string[];
}

const tasks: ProtocolComplianceTaskInternal[] = [];
const taskTimers = new Map<string, NodeJS.Timeout[]>();

function registerTimer(taskId: string, timer: NodeJS.Timeout) {
  const existing = taskTimers.get(taskId) ?? [];
  existing.push(timer);
  taskTimers.set(taskId, existing);
}

function clearTaskTimers(taskId: string) {
  const timers = taskTimers.get(taskId);
  if (!timers) {
    return;
  }
  timers.forEach((timer) => clearTimeout(timer));
  taskTimers.delete(taskId);
}

function updateTask(
  taskId: string,
  patch: Partial<ProtocolComplianceTaskInternal>,
) {
  const idx = tasks.findIndex((task) => task.id === taskId);
  if (idx === -1) {
    return null;
  }
  const now = new Date().toISOString();
  const current = tasks[idx];
  const next: ProtocolComplianceTaskInternal = {
    ...current,
    ...patch,
    updatedAt: patch.updatedAt ?? now,
  };
  tasks[idx] = next;
  return next;
}

function buildResultPayload(task: ProtocolComplianceTaskInternal) {
  const rules = Array.from(
    { length: faker.number.int({ min: 4, max: 8 }) },
    () => ({
      action: faker.helpers.arrayElement([
        '验证握手报文结构',
        '检查密钥交换流程',
        '验证状态同步',
        '校验加密套件协商',
        '确认超时重传策略',
      ]),
      reference: `RFC ${faker.number.int({ min: 1000, max: 9000 })}.${faker.number.int({ min: 1, max: 9 })}`,
      requirement: faker.lorem.sentence({ min: 8, max: 18 }),
    }),
  );

  const criticalFindings = Array.from(
    { length: faker.number.int({ min: 1, max: 3 }) },
    () => ({
      description: faker.lorem.sentence({ min: 10, max: 22 }),
      section: `${faker.number.int({ min: 1, max: 7 })}.${faker.number.int({ min: 1, max: 9 })}`,
      severity: faker.helpers.arrayElement(['low', 'medium', 'high']),
    }),
  );

  return {
    complianceSummary: {
      criticalFindings,
      docTitle: task.name || task.documentName,
      extractedAt: new Date().toISOString(),
      overview: faker.lorem.paragraph(),
    },
    metadata: {
      documentName: task.documentName,
      documentSize: task.documentSize ?? null,
      taskId: task.id,
      uploadedAt: task.submittedAt,
    },
    protocolRules: rules,
    tags: task.tags ?? [],
  };
}

function planTaskLifecycle(task: ProtocolComplianceTaskInternal) {
  const lifecyclePlan: Array<{
    delay: number;
    onExecute?: (updatedTask: ProtocolComplianceTaskInternal) => void;
    patch: Partial<ProtocolComplianceTaskInternal>;
  }> = [
    {
      delay: 600,
      patch: {
        progress: 35,
        status: 'processing',
      },
    },
    {
      delay: 1600,
      patch: {
        progress: 68,
      },
    },
    {
      delay: 2800,
      patch: {
        progress: 85,
      },
    },
    {
      delay: 4200,
      patch: {
        completedAt: new Date().toISOString(),
        progress: 100,
        status: 'completed',
      },
      onExecute: (updatedTask) => {
        updateTask(updatedTask.id, {
          resultPayload: buildResultPayload(updatedTask),
        });
        clearTaskTimers(updatedTask.id);
      },
    },
  ];

  lifecyclePlan.forEach(({ delay, patch, onExecute }) => {
    const timer = setTimeout(() => {
      const updated = updateTask(task.id, patch);
      if (updated && onExecute) {
        onExecute(updated);
      }
    }, delay);
    registerTimer(task.id, timer);
  });
}

export function createProtocolComplianceTask(
  input: CreateProtocolComplianceTaskInput,
) {
  const now = new Date().toISOString();
  const task: ProtocolComplianceTaskInternal = {
    completedAt: undefined,
    description: input.description?.trim() || undefined,
    documentName: input.documentName,
    documentSize: input.documentSize,
    id: faker.string.uuid(),
    name: input.name.trim(),
    progress: 18,
    status: 'queued',
    submittedAt: now,
    tags: input.tags?.length ? input.tags : undefined,
    updatedAt: now,
  };
  tasks.unshift(task);
  if (tasks.length > 50) {
    const removed = tasks.splice(50);
    removed.forEach((removedTask) => clearTaskTimers(removedTask.id));
  }
  planTaskLifecycle(task);
  return task;
}

export function listProtocolComplianceTasks(options?: {
  status?: ProtocolComplianceTaskStatus[];
}) {
  const statusFilter = options?.status;
  const filtered = statusFilter?.length
    ? tasks.filter((task) => statusFilter.includes(task.status))
    : tasks;

  return [...filtered].sort((a, b) => {
    return (
      new Date(b.submittedAt).getTime() - new Date(a.submittedAt).getTime()
    );
  });
}

export function getProtocolComplianceTask(taskId: string) {
  return tasks.find((task) => task.id === taskId) ?? null;
}

export interface ProtocolComplianceTaskResponse
  extends Omit<ProtocolComplianceTaskInternal, 'resultPayload'> {
  resultDownloadUrl: null | string;
}

export function serializeProtocolComplianceTask(
  task: ProtocolComplianceTaskInternal,
  baseUrl: URL,
): ProtocolComplianceTaskResponse {
  const resultPath = `/api/protocol-compliance/tasks/${task.id}/result`;
  const resultDownloadUrl =
    task.status === 'completed'
      ? new URL(resultPath, baseUrl.origin).toString()
      : null;
  const { resultPayload: _payload, ...rest } = task;
  return {
    ...rest,
    resultDownloadUrl,
  };
}
