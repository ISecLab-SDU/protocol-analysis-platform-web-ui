import { useAccessStore } from '@vben/stores';

import { baseRequestClient, requestClient } from './request';

type ProtocolStaticAnalysisComplianceStatus =
  | 'compliant'
  | 'needs_review'
  | 'non_compliant';

interface ProtocolStaticAnalysisVerdict {
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

interface ProtocolStaticAnalysisSummary {
  compliantCount: number;
  needsReviewCount: number;
  nonCompliantCount: number;
  notes: string;
  overallStatus: ProtocolStaticAnalysisComplianceStatus;
}

interface ProtocolStaticAnalysisModelMetadata {
  generatedAt: string;
  modelVersion: string;
  protocol: string;
  protocolVersion?: string;
  ruleSet: string;
}

interface ProtocolStaticAnalysisModelResponse {
  metadata: ProtocolStaticAnalysisModelMetadata;
  summary: ProtocolStaticAnalysisSummary;
  verdicts: ProtocolStaticAnalysisVerdict[];
}

interface ProtocolStaticAnalysisCheck {
  allNoViolation: boolean;
  hasViolation: boolean;
  invalidCount: number;
  invalidRows: Array<{
    reason: string;
    result?: unknown;
    rowId: number;
    ruleDesc?: null | string;
  }>;
  noViolationCount: number;
  shouldSkipDownstream: boolean;
  totalCount: number;
  violationCount: number;
}

export interface ProtocolStaticAnalysisResult {
  analysisId: string;
  artifacts?: {
    config?: null | string;
    database?: null | string;
    logs?: null | string;
    output?: null | string;
    workspace?: null | string;
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
  builderDockerfile?: File;
  codeArchive: File;
  config?: File;
  notes?: string;
  projectName?: string;
  protocolName?: string;
  protocolVersion?: string;
  rules: File;
}

type ProtocolStaticAnalysisJobStatus =
  | 'completed'
  | 'failed'
  | 'queued'
  | 'running';

export interface ProtocolStaticAnalysisProgressEvent {
  id?: number;
  message: string;
  metadata?: ProtocolAgentProgressMetadata;
  stage: string;
  timestamp: string;
}

export interface ProtocolAgentProgressMetadata {
  activity?:
    | 'command'
    | 'inspect'
    | 'message'
    | 'plan'
    | 'result'
    | 'status'
    | 'thinking'
    | 'tool'
    | 'tool_result'
    | 'write';
  cache_read_tokens?: number;
  cost_usd?: number;
  description?: string;
  duration_ms?: number;
  input_tokens?: number;
  is_error?: boolean;
  model?: string;
  output_tokens?: number;
  primary?: string;
  quiet?: boolean;
  result?: string;
  status?: 'completed' | 'failed' | string;
  tool?: string;
  tool_id?: string;
}

export interface ProtocolStaticAnalysisJob {
  createdAt: string;
  details?: null | Record<string, unknown>;
  error?: null | string;
  events: ProtocolStaticAnalysisProgressEvent[];
  jobId: string;
  message: string;
  result?: null | ProtocolStaticAnalysisResult;
  stage: string;
  status: ProtocolStaticAnalysisJobStatus;
  updatedAt: string;
}

export type ProtocolStaticAnalysisRuleResultStatus =
  | 'no_violation'
  | 'unknown'
  | 'violation_found';

export interface ProtocolStaticAnalysisRuleViolationDetail {
  codeLines?: null | number[];
  filename?: null | string;
  functionName?: null | string;
}

export interface ProtocolStaticAnalysisDatabaseRuleInsight {
  callGraph?: null | string;
  codeSnippet?: null | string;
  llmRaw?: unknown;
  reason?: null | string;
  result: ProtocolStaticAnalysisRuleResultStatus;
  resultLabel: string;
  ruleDesc: string;
  violations?: ProtocolStaticAnalysisRuleViolationDetail[];
}

export interface ProtocolStaticAnalysisDatabaseInsights {
  databasePath?: null | string;
  extractedAt: string;
  findings: ProtocolStaticAnalysisDatabaseRuleInsight[];
  warnings?: string[];
  workspacePath?: null | string;
}

export interface FetchProtocolStaticAnalysisDatabaseInsightsPayload {
  databasePath?: string;
  jobId?: string;
  workspacePath?: string;
}

type ProtocolViolationHistorySourceType = 'builtin' | 'job';

export interface ProtocolViolationHistoryEntry {
  callGraph?: null | string;
  codeSnippet?: null | string;
  createdAt?: null | string;
  databaseName: string;
  databasePath?: null | string;
  extractedAt?: null | string;
  id: string;
  implementationName: string;
  jobId?: null | string;
  llmRaw?: unknown;
  protocolName: string;
  reason?: null | string;
  result: ProtocolStaticAnalysisRuleResultStatus;
  resultLabel: string;
  ruleDesc: string;
  sourceType: ProtocolViolationHistorySourceType;
  updatedAt?: null | string;
  violations?: null | ProtocolStaticAnalysisRuleViolationDetail[];
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
  callGraph?: null | string;
  codeSnippet?: null | string;
  databaseName?: string;
  databasePath?: null | string;
  reason?: null | string;
  ruleDesc?: string;
  violations?: null | ProtocolStaticAnalysisRuleViolationDetail[];
  workspacePath?: null | string;
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

interface ProtocolDatabaseOverviewProtocolStats {
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

interface ProtocolDatabaseOverviewImplementationStats
  extends Omit<
    ProtocolDatabaseOverviewProtocolStats,
    'implementations' | 'name'
  > {
  database: string;
  name: string;
  protocol: string;
}

interface ProtocolDatabaseOverviewFinding {
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

export function runProtocolStaticAnalysis(
  payload: RunProtocolStaticAnalysisPayload,
) {
  const {
    builderDockerfile,
    codeArchive,
    config,
    notes,
    projectName,
    protocolName,
    protocolVersion,
    rules,
  } = payload;
  const formData = new FormData();
  formData.append('codeArchive', codeArchive);
  if (builderDockerfile) {
    formData.append('builderDockerfile', builderDockerfile);
  }
  formData.append('rules', rules);
  if (config) {
    formData.append('config', config);
  }
  if (notes?.trim()) {
    formData.append('notes', notes.trim());
  }
  if (protocolName?.trim()) {
    formData.append('protocolName', protocolName.trim());
  }
  if (protocolVersion?.trim()) {
    formData.append('protocolVersion', protocolVersion.trim());
  }
  if (projectName?.trim()) {
    formData.append('projectName', projectName.trim());
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

export interface DownloadAflNetPocParams {
  crashLogPath?: string;
  implementation?: string;
  protocol?: string;
}

export async function downloadAflNetPoc(params: DownloadAflNetPocParams) {
  const accessStore = useAccessStore();
  const token = accessStore.accessToken;
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const query = new URLSearchParams();
  if (params.implementation) query.set('implementation', params.implementation);
  if (params.protocol) query.set('protocol', params.protocol);
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

export function fetchProtocolDatabaseOverview(
  params?: FetchProtocolViolationHistoryParams,
) {
  return requestClient.get<ProtocolDatabaseOverviewStats>(
    '/protocol-compliance/static-analysis/database-overview',
    { params },
  );
}

// Assertion Generation Types and APIs
type ProtocolAssertGenerationJobStatus =
  | 'completed'
  | 'failed'
  | 'queued'
  | 'running';

export interface ProtocolAssertGenerationProgressEvent {
  message: string;
  metadata?: ProtocolAgentProgressMetadata;
  stage: string;
  timestamp: string;
}

interface ProtocolAssertGenerationInputInfo {
  codeFileName?: string;
  databaseFileName?: string;
  databasePath?: null | string;
  notes?: null | string;
}

interface ProtocolAssertGenerationArtifactInfo {
  database?: string;
  instrumentedCodeZipPath?: string;
  logs?: string;
  output?: string;
  workspace?: string;
  workspaceSnapshots?: Array<{ path?: string; stage?: string }>;
  zipPath?: string;
}

interface ProtocolAssertGenerationDockerInfo {
  command?: string[];
  durationMs?: number;
  image?: string;
  logs?: string[];
}

interface ProtocolInstrumentationDiffOutput {
  available: boolean;
  content?: null | string;
  path?: null | string;
  size?: number;
  truncated?: boolean;
}

interface ProtocolInstrumentationArtifacts {
  diffFiles?: string[];
  diffOutput?: ProtocolInstrumentationDiffOutput;
  instrumentedCodePath?: null | string;
  instrumentedCodeZipPath?: null | string;
}

interface ProtocolInstrumentationDockerInfo {
  command?: string[];
  durationMs?: number;
  image?: string;
}

interface ProtocolInstrumentationResult {
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

export interface AssertionRuntimeSettings {
  agent: 'claude' | 'pi';
  api?: 'anthropic-messages' | 'openai-completions' | 'openai-responses';
  apiKey?: string;
  baseUrl?: string;
  model?: string;
  contextWindow?: number;
  maxTokens?: number;
  maxTurns?: number;
  timeoutSeconds?: number;
}

export interface RunProtocolAssertGenerationPayload {
  runtime?: AssertionRuntimeSettings;
  codeArchive: File;
  database?: File;
  databasePath?: string;
  notes?: string;
}

export function runProtocolAssertGeneration(
  payload: RunProtocolAssertGenerationPayload,
) {
  const { codeArchive, database, databasePath, notes, runtime } = payload;
  const formData = new FormData();
  formData.append('codeArchive', codeArchive);
  if (runtime) formData.append('runtime', JSON.stringify(runtime));
  if (databasePath?.trim()) {
    formData.append('databasePath', databasePath.trim());
  } else if (database) {
    formData.append('database', database);
  }
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

export async function downloadProtocolAssertionArtifact(
  jobId: string,
  artifact: 'instrumented-code' | 'tasks',
) {
  const token = useAccessStore().accessToken;
  const response = (await baseRequestClient.request(
    `/protocol-compliance/assertion-generation/${encodeURIComponent(jobId)}/download?artifact=${artifact}`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      method: 'GET',
      responseType: 'blob',
    },
  )) as { data: Blob };
  return response.data;
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

// Artifact-backed Fuzz Jobs -----------------------------------------------
type ProtocolFuzzingJobStatus =
  | 'completed'
  | 'failed'
  | 'queued'
  | 'running'
  | 'stopped';

export interface StartProtocolFuzzingJobPayload {
  assertGenerationJobId: string;
  fuzzConfigJobId: string;
  notes?: string;
  protocolImplementations?: string[];
}

export interface StartProtocolFuzzingDebugJobPayload {
  assertGenerationJobId?: string;
  fuzzConfigJobId?: string;
  instrumentedCodeZipPath?: string;
  notes?: string;
  protocol?: string;
  protocolImplementations?: string[];
}

export interface ProtocolFuzzingJob {
  artifacts?: {
    fuzzerLogFilePath?: null | string;
    fuzzWorkspacePath?: string;
    instrumentedCodePath?: string;
    instrumentedCodeZipPath?: string;
    isFallbackOutput?: boolean;
    logFilePath?: string;
    outputPath?: string;
    outputRoot?: string;
    outputSource?: string;
    pocPath?: string;
  };
  assertGenerationJobId: string;
  createdAt: string;
  debugSource?: null | string;
  error?: null | string;
  fuzzConfigJobId?: null | string;
  inputs?: {
    instrumentedCodeZipFileName?: string;
    instrumentedCodeZipPath?: string;
  };
  jobId: string;
  message: string;
  notes?: null | string;
  process?: null | {
    command?: string;
    containerId?: null | string;
    pid?: null | string;
  };
  protocol: string;
  protocolImplementations?: string[];
  stage: string;
  status: ProtocolFuzzingJobStatus;
  updatedAt: string;
}

type ProtocolFuzzConfigJobStatus =
  | 'completed'
  | 'failed'
  | 'queued'
  | 'running';

export interface StartProtocolFuzzConfigJobPayload {
  assertGenerationJobId?: string;
  host?: string;
  instrumentedCodeZipPath?: string;
  netSpec?: string;
  notes?: string;
  port?: number;
  protocol?: string;
  protocolImplementations?: string[];
  targetArgs?: string[];
  transport?: string;
}

export interface ProtocolFuzzConfigJob {
  artifacts?: {
    bundlePath?: string;
    envPath?: string;
    eventsPath?: string;
    instrumentedCodePath?: string;
    instrumentedCodeZipPath?: string;
    logFilePath?: string;
    manifestPath?: string;
    outputPath?: string;
    workspacePath?: string;
  };
  assertGenerationJobId: string;
  createdAt: string;
  error?: null | string;
  inputs?: {
    instrumentedCodeZipFileName?: string;
    instrumentedCodeZipPath?: string;
  };
  jobId: string;
  message: string;
  notes?: null | string;
  process?: null | {
    command?: string[];
    pid?: null | number;
    threadName?: string;
  };
  protocol: string;
  protocolImplementations?: string[];
  result?: null | {
    manifest?: Record<string, any>;
    runtimeEnv?: Record<string, string>;
  };
  runtimeOverrides?: {
    host?: string;
    netSpec?: string;
    port?: string;
    targetArgs?: string;
    transport?: string;
  };
  stage: string;
  status: ProtocolFuzzConfigJobStatus;
  updatedAt: string;
}

export interface ProtocolFuzzConfigLogResponse {
  content: string;
  fileSize: number;
  job: ProtocolFuzzConfigJob;
  logFilePath?: string;
  position: number;
}

export function startProtocolFuzzConfigJob(
  payload: StartProtocolFuzzConfigJobPayload,
) {
  return requestClient.post<ProtocolFuzzConfigJob>(
    '/protocol-compliance/fuzzing/config-jobs',
    payload,
  );
}

export function fetchProtocolFuzzConfigLogs(
  jobId: string,
  fromPosition: number,
) {
  return requestClient.get<ProtocolFuzzConfigLogResponse>(
    `/protocol-compliance/fuzzing/config-jobs/${jobId}/logs`,
    {
      params: { fromPosition },
    },
  );
}

export interface ProtocolFuzzingLogResponse {
  content: string;
  fileSize: number;
  fuzzerLogFilePath?: null | string;
  isFallbackOutput?: boolean;
  job: ProtocolFuzzingJob;
  logFilePath?: string;
  outputRoot?: string;
  outputSource?: string;
  pocPath?: string;
  position: number;
}

export function startProtocolFuzzingJob(
  payload: StartProtocolFuzzingJobPayload,
) {
  return requestClient.post<ProtocolFuzzingJob>(
    '/protocol-compliance/fuzzing/jobs',
    payload,
  );
}

export function startProtocolFuzzingDebugJob(
  payload: StartProtocolFuzzingDebugJobPayload,
) {
  return requestClient.post<ProtocolFuzzingJob>(
    '/protocol-compliance/fuzzing/dev/jobs',
    payload,
  );
}

export function fetchProtocolFuzzingLogs(jobId: string, fromPosition: number) {
  return requestClient.get<ProtocolFuzzingLogResponse>(
    `/protocol-compliance/fuzzing/jobs/${jobId}/logs`,
    {
      params: { fromPosition },
    },
  );
}

export function stopProtocolFuzzingJob(jobId: string) {
  return requestClient.post<ProtocolFuzzingJob>(
    `/protocol-compliance/fuzzing/jobs/${jobId}/stop`,
    {},
  );
}

export interface RunProtocolExtractPayload {
  protocol: string;
  version: string;
  htmlFile: File;
  filterHeadings?: boolean;
}

export interface ProtocolExtractRuleItem {
  description?: string;
  group?: null | string;
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
  formData.append('protocol', payload.protocol);
  formData.append('version', payload.version);
  formData.append('htmlFile', payload.htmlFile);
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
  const rules =
    [data, data.rules, data.result, data.data?.rules].find((value) =>
      Array.isArray(value),
    ) ?? [];

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
