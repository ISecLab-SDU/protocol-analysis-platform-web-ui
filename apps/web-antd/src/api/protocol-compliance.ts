import { useAccessStore } from '@vben/stores';

import { baseRequestClient, requestClient } from './request';

export type ProtocolComplianceTaskStatus =
  | 'completed'
  | 'failed'
  | 'processing'
  | 'queued';

export interface ProtocolComplianceTask {
  completedAt?: string;
  description?: string;
  documentName: string;
  documentSize?: number;
  id: string;
  name: string;
  progress?: number;
  resultDownloadUrl: null | string;
  status: ProtocolComplianceTaskStatus;
  submittedAt: string;
  updatedAt: string;
}

export interface FetchProtocolComplianceTasksParams {
  page?: number;
  pageSize?: number;
  status?: ProtocolComplianceTaskStatus | ProtocolComplianceTaskStatus[];
}

export interface FetchProtocolComplianceTasksResponse {
  items: ProtocolComplianceTask[];
  page: number;
  pageSize: number;
  total: number;
}

export interface CreateProtocolComplianceTaskPayload {
  description?: string;
  document: File;
  name: string;
  tags?: string[];
}

export type ProtocolStaticAnalysisComplianceStatus =
  | 'compliant'
  | 'needs_review'
  | 'non_compliant';

export interface ProtocolStaticAnalysisVerdict {
  category: string;
  compliance: ProtocolStaticAnalysisComplianceStatus;
  confidence: 'high' | 'low' | 'medium';
  explanation: string;
  findingId: string;
  lineRange?: [number, number];
  location: {
    file: string;
    function?: string;
  };
  recommendation?: string;
  relatedRule: {
    id: string;
    requirement: string;
    source: string;
  };
}

export interface ProtocolStaticAnalysisSummary {
  compliantCount: number;
  needsReviewCount: number;
  nonCompliantCount: number;
  notes: string;
  overallStatus: ProtocolStaticAnalysisComplianceStatus;
}

export interface ProtocolStaticAnalysisModelMetadata {
  generatedAt: string;
  modelVersion: string;
  protocol: string;
  ruleSet: string;
}

export interface ProtocolStaticAnalysisModelResponse {
  metadata: ProtocolStaticAnalysisModelMetadata;
  summary: ProtocolStaticAnalysisSummary;
  verdicts: ProtocolStaticAnalysisVerdict[];
}

export interface ProtocolStaticAnalysisResult {
  analysisId: string;
  durationMs: number;
  inputs: {
    codeFileName: string;
    notes: null | string;
    protocolName: string;
    rulesFileName: string;
    rulesSummary: null | string;
  };
  model: string;
  modelResponse: ProtocolStaticAnalysisModelResponse;
  submittedAt: string;
}

export interface RunProtocolStaticAnalysisPayload {
  code: File;
  notes?: string;
  rules: File;
}

const BASE_PATH = '/protocol-compliance/tasks';

export function fetchProtocolComplianceTasks(
  params?: FetchProtocolComplianceTasksParams,
) {
  return requestClient.get<FetchProtocolComplianceTasksResponse>(BASE_PATH, {
    params,
  });
}

export function createProtocolComplianceTask(
  payload: CreateProtocolComplianceTaskPayload,
) {
  const { description, document, name, tags } = payload;
  const formData = new FormData();
  formData.append('file', document);
  formData.append('name', name);
  if (description) {
    formData.append('description', description);
  }
  if (tags?.length) {
    formData.append('tags', JSON.stringify(tags));
  }

  return requestClient.post<ProtocolComplianceTask>(BASE_PATH, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
}

export async function downloadProtocolComplianceTaskResult(taskId: string) {
  const accessStore = useAccessStore();
  const token = accessStore.accessToken;
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = (await baseRequestClient.request(
    `${BASE_PATH}/${taskId}/result`,
    {
      headers,
      method: 'GET',
      responseType: 'blob',
    },
  )) as { data: Blob };
  return response.data;
}

export function runProtocolStaticAnalysis(
  payload: RunProtocolStaticAnalysisPayload,
) {
  const { code, notes, rules } = payload;
  const formData = new FormData();
  formData.append('rules', rules);
  formData.append('code', code);
  if (notes?.trim()) {
    formData.append('notes', notes.trim());
  }

  return requestClient.post<ProtocolStaticAnalysisResult>(
    '/protocol-compliance/static-analysis',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    },
  );
}

// 获取检测结果
export function getDetectionResults(implementationName: string) {
  return requestClient.get(
    `/protocol-compliance/detection-results/${implementationName}`,
  );
}

// 添加历史记录
export function addAnalysisHistory(data: {
  implementationName: string;
  protocolName: string;
}) {
  return requestClient.post('/protocol-compliance/analysis-history', data);
}

// 获取历史记录
export function getAnalysisHistory() {
  return requestClient.get('/protocol-compliance/analysis-history');
}

// 停止进程
export function stopProcess(data: { pid: string | number; protocol: string }) {
  return requestClient.post('/protocol-compliance/stop-process', data);
}

// 停止并清理Docker容器
export function stopAndCleanup(data: { container_id: string; protocol: string }) {
  return requestClient.post('/protocol-compliance/stop-and-cleanup', data);
}

// 写入脚本文件
export function writeScript(data: { content: string; protocol: string }) {
  return requestClient.post('/protocol-compliance/write-script', data);
}

// 执行命令
export function executeCommand(data: { protocol: string }) {
  return requestClient.post('/protocol-compliance/execute-command', data);
}

// 读取日志
export function readLog(data: { protocol: string; lastPosition: number }) {
  return requestClient.post('/protocol-compliance/read-log', data);
}

// 检查状态
export function checkStatus(data: { protocol: string }) {
  return requestClient.post('/protocol-compliance/check-status', data);
}
