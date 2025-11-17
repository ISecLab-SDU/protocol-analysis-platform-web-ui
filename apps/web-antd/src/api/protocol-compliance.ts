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
  id?: number;
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
  codeFileName?: string | null;
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

export function fetchProtocolStaticAnalysisProgress(
  jobId: string,
  fromEventId: number,
) {
  return requestClient.get<ProtocolStaticAnalysisJob>(
    `/protocol-compliance/static-analysis/${jobId}/progress`,
    {
      params: { fromEventId },
    },
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

export function deleteProtocolStaticAnalysisJob(jobId: string) {
  return requestClient.delete<{ deleted: boolean; jobId: string }>(
    `/protocol-compliance/static-analysis/history/${jobId}`,
  );
}

// Assertion Generation Types and APIs
export type ProtocolAssertGenerationJobStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed';

export interface ProtocolAssertGenerationProgressEvent {
  message: string;
  stage: string;
  timestamp: string;
}

export interface ProtocolAssertGenerationInputInfo {
  buildInstructions?: null | string;
  codeFileName?: string;
  databaseFileName?: string;
  notes?: null | string;
}

export interface ProtocolAssertGenerationArtifactInfo {
  database?: string;
  logs?: string;
  output?: string;
  workspace?: string;
  workspaceSnapshots?: Array<{ stage?: string; path?: string }>;
  zipPath?: string;
}

export interface ProtocolAssertGenerationDockerInfo {
  command?: string[];
  durationMs?: number;
  image?: string;
  logs?: string[];
}

export interface ProtocolInstrumentationDiffOutput {
  available: boolean;
  content?: string | null;
  path?: string | null;
  size?: number;
  truncated?: boolean;
}

export interface ProtocolInstrumentationArtifacts {
  diffFiles?: string[];
  diffOutput?: ProtocolInstrumentationDiffOutput;
  instrumentedCodePath?: string | null;
}

export interface ProtocolInstrumentationDockerInfo {
  command?: string[];
  durationMs?: number;
  image?: string;
}

export interface ProtocolInstrumentationResult {
  artifacts?: ProtocolInstrumentationArtifacts;
  completedAt?: string;
  docker?: ProtocolInstrumentationDockerInfo;
  logs?: string[];
}

export interface ProtocolAssertGenerationResult {
  assertionCount: number;
  artifacts?: ProtocolAssertGenerationArtifactInfo;
  docker?: ProtocolAssertGenerationDockerInfo;
  generatedAt: string;
  inputs?: ProtocolAssertGenerationInputInfo;
  instrumentation?: ProtocolInstrumentationResult;
  jobId: string;
  protocolName: string;
}

export interface ProtocolAssertGenerationJob {
  createdAt: string;
  error?: null | string;
  events: ProtocolAssertGenerationProgressEvent[];
  jobId: string;
  message: string;
  result?: null | ProtocolAssertGenerationResult;
  stage: string;
  status: ProtocolAssertGenerationJobStatus;
  updatedAt: string;
}

export interface RunProtocolAssertGenerationPayload {
  buildInstructions: string;
  codeArchive: File;
  database: File;
  notes?: string;
}

export function runProtocolAssertGeneration(
  payload: RunProtocolAssertGenerationPayload,
) {
  const { buildInstructions, codeArchive, database, notes } = payload;
  const formData = new FormData();
  formData.append('codeArchive', codeArchive);
  formData.append('database', database);
  formData.append('buildInstructions', buildInstructions.trim());
  if (notes?.trim()) {
    formData.append('notes', notes.trim());
  }

  return requestClient.post<ProtocolAssertGenerationJob>(
    '/protocol-compliance/assertion-generation',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    },
  );
}

export function fetchProtocolAssertGenerationProgress(jobId: string) {
  return requestClient.get<ProtocolAssertGenerationJob>(
    `/protocol-compliance/assertion-generation/${jobId}/progress`,
  );
}

export function fetchProtocolAssertGenerationResult(jobId: string) {
  return requestClient.get<ProtocolAssertGenerationResult>(
    `/protocol-compliance/assertion-generation/${jobId}/result`,
  );
}

export type ProtocolInstrumentationDiffResponse = ProtocolInstrumentationDiffOutput;

export function fetchProtocolInstrumentationDiff(jobId: string) {
  return requestClient.get<ProtocolInstrumentationDiffResponse>(
    `/protocol-compliance/assertion-generation/${jobId}/instrumentation-diff`,
  );
}

export async function downloadProtocolAssertGenerationResult(jobId: string) {
  const accessStore = useAccessStore();
  const token = accessStore.accessToken;
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = (await baseRequestClient.request(
    `/protocol-compliance/assertion-generation/${jobId}/download`,
    {
      headers,
      method: 'GET',
      responseType: 'blob',
    },
  )) as { data: Blob };

  return response.data;
}

// Assertion history ------------------------------------------------------

export interface ProtocolAssertionHistoryEntry {
  jobId: string;
  codeFilename?: string | null;
  databaseFilename?: string | null;
  diffPath?: string | null;
  diffFilename?: string | null;
  createdAt: string;
  updatedAt: string;
  source?: string | null;
}

export interface ProtocolAssertionHistoryResponse {
  items: ProtocolAssertionHistoryEntry[];
  limit: number;
  count: number;
}

export function fetchProtocolAssertionHistory(limit = 20) {
  return requestClient.get<ProtocolAssertionHistoryResponse>(
    '/protocol-compliance/assertions/history',
    {
      params: { limit },
    },
  );
}

export async function downloadProtocolAssertionDiff(jobId: string) {
  const accessStore = useAccessStore();
  const token = accessStore.accessToken;
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = (await baseRequestClient.request(
    `/protocol-compliance/assertions/history/${jobId}/diff`,
    {
      headers,
      method: 'GET',
      responseType: 'blob',
    },
  )) as { data: Blob };

  return response.data;
}

// Diff Parsing Types and APIs
export type ProtocolDiffParsingJobStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed';

export interface DiffHunk {
  newLines: number;
  newStart: number;
  oldLines: number;
  oldStart: number;
  lines: Array<{
    content: string;
    type: 'add' | 'delete' | 'normal';
  }>;
}

export interface DiffFile {
  additions: number;
  deletions: number;
  from: string;
  hunks: DiffHunk[];
  to: string;
}

export interface ProtocolDiffParsingResult {
  diffContent: string;
  files: DiffFile[];
  generatedAt: string;
  jobId: string;
  summary: {
    filesChanged: number;
    insertions: number;
    deletions: number;
  };
}

export interface ProtocolDiffParsingProgressEvent {
  message: string;
  percentage: number;
  stage: string;
  timestamp: string;
}

export interface ProtocolDiffParsingJob {
  createdAt: string;
  error?: null | string;
  events: ProtocolDiffParsingProgressEvent[];
  jobId: string;
  message: string;
  parentJobId: string;
  percentage: number;
  result?: null | ProtocolDiffParsingResult;
  stage: string;
  status: ProtocolDiffParsingJobStatus;
  updatedAt: string;
}

export function startProtocolDiffParsing(assertGenerationJobId: string) {
  return requestClient.post<ProtocolDiffParsingJob>(
    `/protocol-compliance/assertion-generation/${assertGenerationJobId}/diff-parsing`,
    {},
  );
}

export function fetchProtocolDiffParsingProgress(
  assertGenerationJobId: string,
  diffParsingJobId: string,
) {
  return requestClient.get<ProtocolDiffParsingJob>(
    `/protocol-compliance/assertion-generation/${assertGenerationJobId}/diff-parsing/${diffParsingJobId}/progress`,
  );
}

export function fetchProtocolDiffParsingResult(
  assertGenerationJobId: string,
  diffParsingJobId: string,
) {
  return requestClient.get<ProtocolDiffParsingResult>(
    `/protocol-compliance/assertion-generation/${assertGenerationJobId}/diff-parsing/${diffParsingJobId}/result`,
  );
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
