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
  protocolVersion?: string;
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
  builderDockerfile: File;
  codeArchive: File;
  config: File;
  notes?: string;
  rules: File;
}

export type ProtocolStaticAnalysisJobStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed';

export interface ProtocolStaticAnalysisProgressEvent {
  message: string;
  stage: string;
  timestamp: string;
}

export interface ProtocolStaticAnalysisJob {
  createdAt: string;
  details?: Record<string, unknown> | null;
  error?: string | null;
  events: ProtocolStaticAnalysisProgressEvent[];
  jobId: string;
  message: string;
  result?: ProtocolStaticAnalysisResult | null;
  stage: string;
  status: ProtocolStaticAnalysisJobStatus;
  updatedAt: string;
}

export interface ProtocolStaticAnalysisHistoryEntry {
  analysisId?: string | null;
  completedAt?: string | null;
  configPath?: string | null;
  createdAt: string;
  databasePath?: string | null;
  details?: Record<string, unknown> | null;
  durationMs?: number | null;
  error?: string | null;
  jobId: string;
  logsPath?: string | null;
  message: string;
  model?: string | null;
  modelVersion?: string | null;
  overallStatus?: ProtocolStaticAnalysisComplianceStatus | null;
  outputPath?: string | null;
  protocolName?: string | null;
  protocolVersion?: string | null;
  ruleSet?: string | null;
  rulesFileName?: string | null;
  stage: string;
  status: ProtocolStaticAnalysisJobStatus;
  submittedAt?: string | null;
  summary?: ProtocolStaticAnalysisSummary | null;
  updatedAt: string;
  workspacePath?: string | null;
  workspaceSnapshots?: { path?: string; stage?: string }[] | null;
}

export interface FetchProtocolStaticAnalysisHistoryParams {
  limit?: number;
}

export interface FetchProtocolStaticAnalysisHistoryResponse {
  count: number;
  items: ProtocolStaticAnalysisHistoryEntry[];
  limit: number;
}

export type ProtocolStaticAnalysisRuleResultStatus =
  | 'violation_found'
  | 'no_violation'
  | 'unknown';

export interface ProtocolStaticAnalysisRuleViolationDetail {
  codeLines?: number[] | null;
  filename?: string | null;
  functionName?: string | null;
}

export interface ProtocolStaticAnalysisDatabaseRuleInsight {
  callGraph?: string | null;
  codeSnippet?: string | null;
  llmRaw?: unknown;
  reason?: string | null;
  result: ProtocolStaticAnalysisRuleResultStatus;
  resultLabel: string;
  ruleDesc: string;
  violations?: ProtocolStaticAnalysisRuleViolationDetail[];
}

export interface ProtocolStaticAnalysisDatabaseInsights {
  databasePath?: string | null;
  extractedAt: string;
  findings: ProtocolStaticAnalysisDatabaseRuleInsight[];
  warnings?: string[];
  workspacePath?: string | null;
}

export interface FetchProtocolStaticAnalysisDatabaseInsightsPayload {
  databasePath?: string;
  jobId?: string;
  workspacePath?: string;
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
  const { builderDockerfile, codeArchive, config, notes, rules } = payload;
  const formData = new FormData();
  formData.append('codeArchive', codeArchive);
  formData.append('builderDockerfile', builderDockerfile);
  formData.append('rules', rules);
  formData.append('config', config);
  if (notes?.trim()) {
    formData.append('notes', notes.trim());
  }

  return requestClient.post<ProtocolStaticAnalysisJob>(
    '/protocol-compliance/static-analysis',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    },
  );
}

export function fetchProtocolStaticAnalysisProgress(jobId: string) {
  return requestClient.get<ProtocolStaticAnalysisJob>(
    `/protocol-compliance/static-analysis/${jobId}/progress`,
  );
}

export function fetchProtocolStaticAnalysisResult(jobId: string) {
  return requestClient.get<ProtocolStaticAnalysisResult>(
    `/protocol-compliance/static-analysis/${jobId}/result`,
  );
}

export function fetchProtocolStaticAnalysisHistory(
  params?: FetchProtocolStaticAnalysisHistoryParams,
) {
  return requestClient.get<FetchProtocolStaticAnalysisHistoryResponse>(
    '/protocol-compliance/static-analysis/history',
    { params },
  );
}

export function fetchProtocolStaticAnalysisDatabaseInsights(
  payload: FetchProtocolStaticAnalysisDatabaseInsightsPayload,
) {
  return requestClient.post<ProtocolStaticAnalysisDatabaseInsights>(
    '/protocol-compliance/static-analysis/database-insights',
    payload,
  );
}
