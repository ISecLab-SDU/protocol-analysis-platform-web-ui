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

export interface ProtocolStaticAnalysisCheck {
  allNoViolation: boolean;
  hasViolation: boolean;
  invalidCount: number;
  invalidRows: Array<{
    reason: string;
    result?: unknown;
    rowId: number;
    ruleDesc?: string | null;
  }>;
  noViolationCount: number;
  shouldSkipDownstream: boolean;
  totalCount: number;
  violationCount: number;
}

export interface ProtocolStaticAnalysisResult {
  analysisId: string;
  artifacts?: {
    config?: string | null;
    database?: string | null;
    logs?: string | null;
    output?: string | null;
    workspace?: string | null;
    workspaceSnapshots?: Array<{ path?: string; stage?: string }>;
  };
  durationMs: number;
  inputs: {
    builderDockerfileName?: string;
    codeFileName: string;
    configFileName?: string;
    notes: null | string;
    protocolName: string;
    rulesFileName: string;
    rulesSummary: null | string;
  };
  model: string;
  modelResponse: ProtocolStaticAnalysisModelResponse;
  staticAnalysisCheck?: ProtocolStaticAnalysisCheck;
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

export type ProtocolViolationHistorySourceType = 'builtin' | 'job';

export interface ProtocolViolationHistoryEntry {
  callGraph?: string | null;
  codeSnippet?: string | null;
  createdAt?: string | null;
  databaseName: string;
  databasePath?: string | null;
  extractedAt?: string | null;
  id: string;
  implementationName: string;
  jobId?: string | null;
  llmRaw?: unknown;
  protocolName: string;
  reason?: string | null;
  result: ProtocolStaticAnalysisRuleResultStatus;
  resultLabel: string;
  ruleDesc: string;
  sourceType: ProtocolViolationHistorySourceType;
  updatedAt?: string | null;
  violations?: ProtocolStaticAnalysisRuleViolationDetail[] | null;
}

export interface FetchProtocolViolationHistoryParams {
  implementation?: string;
  jobLimit?: number;
  protocol?: string;
  result?: ProtocolStaticAnalysisRuleResultStatus;
  timeRange?: 'month' | 'week' | 'year';
}

export interface FetchProtocolViolationHistoryResponse {
  count: number;
  generatedAt: string;
  items: ProtocolViolationHistoryEntry[];
  warnings?: string[];
}

export interface DeleteProtocolViolationHistoryResponse {
  databaseName: string;
  databasePath?: string;
  deleted: boolean;
  id: string;
  warnings?: string[];
}

export interface DeleteProtocolViolationHistoryPayload {
  callGraph?: string | null;
  codeSnippet?: string | null;
  databaseName?: string;
  databasePath?: string | null;
  reason?: string | null;
  ruleDesc?: string;
  violations?: ProtocolStaticAnalysisRuleViolationDetail[] | null;
  workspacePath?: string | null;
}

export interface UpsertProtocolViolationHistoryPayload {
  callGraph?: string;
  codeSnippet?: string;
  databasePath?: string;
  jobId?: string;
  reason: string;
  result: 'violation_found';
  ruleDesc: string;
  violations?: ProtocolStaticAnalysisRuleViolationDetail[];
  workspacePath?: string;
}

export interface UpsertProtocolViolationHistoryResponse {
  databasePath: string;
  id: string;
  result: ProtocolStaticAnalysisRuleResultStatus;
  resultLabel: string;
  ruleDesc: string;
  updated: boolean;
  warnings?: string[];
}

export interface ProtocolDatabaseOverviewSummary {
  analysisRecords: number;
  codeSnippets: number;
  databaseFiles: number;
  implementations: number;
  noViolationRules: number;
  ruleResults: number;
  unknownRules: number;
  violationLocations: number;
  violationRules: number;
}

export interface ProtocolDatabaseOverviewProtocolStats {
  analysisRecords: number;
  codeSnippets: number;
  implementations: number;
  name: string;
  noViolationRules: number;
  ruleResults: number;
  unknownRules: number;
  violationLocations: number;
  violationRules: number;
}

export interface ProtocolDatabaseOverviewImplementationStats
  extends Omit<
    ProtocolDatabaseOverviewProtocolStats,
    'implementations' | 'name'
  > {
  database: string;
  name: string;
  protocol: string;
}

export interface ProtocolDatabaseOverviewFinding {
  implementation: string;
  protocol: string;
  reason?: null | string;
  rule?: null | string;
}

export interface ProtocolDatabaseOverviewStats {
  generatedAt: string;
  implementations: ProtocolDatabaseOverviewImplementationStats[];
  protocols: ProtocolDatabaseOverviewProtocolStats[];
  sourceDirectory: string;
  summary: ProtocolDatabaseOverviewSummary;
  tableTotals: Record<string, number>;
  topFindings: ProtocolDatabaseOverviewFinding[];
  warnings?: string[];
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
  fromEventId?: number,
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

export async function downloadStaticAnalysisDatabase(jobId: string) {
  const accessStore = useAccessStore();
  const token = accessStore.accessToken;
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = (await baseRequestClient.request(
    `/protocol-compliance/static-analysis/${jobId}/artifact/database`,
    {
      headers,
      method: 'GET',
      responseType: 'blob',
    },
  )) as { data: Blob };

  return response.data;
}

export interface DownloadAflNetPocParams {
  crashLogPath?: string;
  implementation: string;
  protocol: string;
}

export interface SnapshotAflNetPocParams extends DownloadAflNetPocParams {}

export interface SnapshotAflNetPocResponse {
  artifactId: string;
  createdAt: string;
  downloadUrl: string;
  fileSize: number;
}

export async function downloadAflNetPoc(params: DownloadAflNetPocParams) {
  const accessStore = useAccessStore();
  const token = accessStore.accessToken;
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const query = new URLSearchParams({
    implementation: params.implementation,
    protocol: params.protocol,
  });
  if (params.crashLogPath) {
    query.set('crashLogPath', params.crashLogPath);
  }

  const response = (await baseRequestClient.request(
    `/protocol-compliance/fuzzing/aflnet-result/download?${query.toString()}`,
    {
      headers,
      method: 'GET',
      responseType: 'blob',
    },
  )) as { data: Blob };

  return response.data;
}

export function snapshotAflNetPoc(params: SnapshotAflNetPocParams) {
  return requestClient.post<SnapshotAflNetPocResponse>(
    '/protocol-compliance/fuzzing/aflnet-result/snapshot',
    params,
  );
}

export async function downloadAflNetPocArtifact(artifactId: string) {
  const accessStore = useAccessStore();
  const token = accessStore.accessToken;
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = (await baseRequestClient.request(
    `/protocol-compliance/fuzzing/aflnet-result/artifacts/${artifactId}/download`,
    {
      headers,
      method: 'GET',
      responseType: 'blob',
    },
  )) as { data: Blob };

  return response.data;
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

export function fetchProtocolViolationHistory(
  params?: FetchProtocolViolationHistoryParams,
) {
  return requestClient.get<FetchProtocolViolationHistoryResponse>(
    '/protocol-compliance/static-analysis/violation-history',
    { params },
  );
}

export function deleteProtocolViolationHistory(
  itemId: string,
  payload?: DeleteProtocolViolationHistoryPayload,
) {
  return requestClient.delete<DeleteProtocolViolationHistoryResponse>(
    `/protocol-compliance/static-analysis/violation-history/${itemId}`,
    payload ? { data: payload } : undefined,
  );
}

export function upsertProtocolViolationHistory(
  payload: UpsertProtocolViolationHistoryPayload,
) {
  return requestClient.post<UpsertProtocolViolationHistoryResponse>(
    '/protocol-compliance/static-analysis/violation-history',
    payload,
  );
}

export function fetchProtocolDatabaseOverview(
  params?: FetchProtocolViolationHistoryParams,
) {
  return requestClient.get<ProtocolDatabaseOverviewStats>(
    '/protocol-compliance/static-analysis/database-overview',
    { params },
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
  databasePath?: null | string;
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
  database?: File;
  databasePath?: string;
  notes?: string;
}

export function runProtocolAssertGeneration(
  payload: RunProtocolAssertGenerationPayload,
) {
  const { buildInstructions, codeArchive, database, databasePath, notes } =
    payload;
  const formData = new FormData();
  formData.append('codeArchive', codeArchive);
  if (databasePath?.trim()) {
    formData.append('databasePath', databasePath.trim());
  } else if (database) {
    formData.append('database', database);
  }
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

export type ProtocolInstrumentationDiffResponse =
  ProtocolInstrumentationDiffOutput;

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
export function stopAndCleanup(data: {
  container_id: string;
  protocol: string;
}) {
  return requestClient.post('/protocol-compliance/stop-and-cleanup', data);
}

// 启动前清理残留容器和输出文件
export function preStartCleanup(data: { protocol: string }) {
  return requestClient.post('/protocol-compliance/pre-start-cleanup', data);
}

// 写入脚本文件
export function writeScript(data: {
  content: string;
  protocol: string;
  protocolImplementations?: string[];
}) {
  return requestClient.post('/protocol-compliance/write-script', data);
}

// 执行命令
export function executeCommand(data: {
  protocol: string;
  protocolImplementations?: string[];
}) {
  return requestClient.post('/protocol-compliance/execute-command', data);
}

// 读取日志
export function readLog(data: {
  lastPosition: number;
  maxLines?: number;
  outputSource?: 'fallback' | 'primary';
  protocol: string;
  protocolImplementations?: string[];
  useFallbackOutput?: boolean;
}) {
  return requestClient.post('/protocol-compliance/read-log', data);
}

// 检查状态
export function checkStatus(data: {
  protocol: string;
  protocolImplementations?: string[];
}) {
  return requestClient.post('/protocol-compliance/check-status', data);
}

export interface RunProtocolExtractPayload {
  apiKey: string;
  protocol: string;
  version: string;
  htmlFile: File;
  filterHeadings?: boolean;
  llmBaseUrl?: string;
}

export interface ProtocolExtractRuleItem {
  description?: string;
  group?: string | null;
  req_fields: string[];
  req_type: string | string[];
  res_fields: string[];
  res_type: string | string[];
  rule: string;
}

export interface RunProtocolExtractResponse {
  protocol: string;
  version: string;
  ruleCount: number;
  rules: ProtocolExtractRuleItem[];
  storeDir: string;
  resultPath: string;
}

export async function runProtocolExtract(payload: RunProtocolExtractPayload) {
  const formData = new FormData();
  formData.append('apiKey', payload.apiKey);
  formData.append('protocol', payload.protocol);
  formData.append('version', payload.version);
  formData.append('htmlFile', payload.htmlFile);
  if (payload.llmBaseUrl?.trim()) {
    formData.append('llmBaseUrl', payload.llmBaseUrl.trim());
  }
  if (payload.filterHeadings) {
    formData.append('filterHeadings', '1');
  }

  // ✅ 发送请求
  const res = await requestClient.post(
    '/protocol-compliance/extract/run',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 10 * 60_000,
    },
  );

  // ✅ 自动兼容各种返回结构
  const data = res?.data ?? res;

  // 兼容数组格式、对象格式、嵌套 data 结构
  const rules = Array.isArray(data)
    ? data
    : Array.isArray(data.rules)
      ? data.rules
      : Array.isArray(data.result)
        ? data.result
        : Array.isArray(data.data?.rules)
          ? data.data.rules
          : [];

  // ✅ 兼容附加字段（若后端没返回则设默认值）
  return {
    rules,
    storeDir: data.storeDir || '',
    resultPath: data.resultPath || '',
    version: data.version || '',
    protocol: data.protocol || payload.protocol,
    ruleCount: rules.length || 0,
  };
}
