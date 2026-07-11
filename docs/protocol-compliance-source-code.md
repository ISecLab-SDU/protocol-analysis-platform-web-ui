==================================================================================================== 文件 1: apps/web-antd/src/router/routes/modules/protocol-compliance.ts ====================================================================================================

import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [ { meta: { icon: 'lucide:shield-check', order: 1, title: '协议合规与安全性分析', }, name: 'ProtocolCompliance', path: '/protocol-compliance', children: [ { name: 'ProtocolComplianceExtract', path: '/protocol-compliance/extract', component: () => import('#/views/protocol-compliance/extract/index.vue'), meta: { title: '协议规则提取', }, }, { name: 'ProtocolComplianceStatic', path: '/protocol-compliance/static', component: () => import('#/views/protocol-compliance/static/index.vue'), meta: { title: '协议代码提取', }, }, { name: 'ProtocolComplianceAssert', path: '/protocol-compliance/assert', component: () => import('#/views/protocol-compliance/assert/index.vue'), meta: { title: '合规断言生成', }, }, { name: 'ProtocolComplianceFuzz', path: '/protocol-compliance/fuzz', component: () => import('#/views/protocol-compliance/fuzz/index.vue'), meta: { title: '协议模糊测试', }, }, ], }, ];

export default routes;

==================================================================================================== 文件 2: apps/web-antd/src/api/protocol-compliance.ts ====================================================================================================

import { useAccessStore } from '@vben/stores';

import { baseRequestClient, requestClient } from './request';

export type ProtocolComplianceTaskStatus = | 'completed' | 'failed' | 'processing' | 'queued';

export interface ProtocolComplianceTask { completedAt?: string; description?: string; documentName: string; documentSize?: number; id: string; name: string; progress?: number; resultDownloadUrl: null | string; status: ProtocolComplianceTaskStatus; submittedAt: string; updatedAt: string; }

export interface FetchProtocolComplianceTasksParams { page?: number; pageSize?: number; status?: ProtocolComplianceTaskStatus | ProtocolComplianceTaskStatus[]; }

export interface FetchProtocolComplianceTasksResponse { items: ProtocolComplianceTask[]; page: number; pageSize: number; total: number; }

export interface CreateProtocolComplianceTaskPayload { description?: string; document: File; name: string; tags?: string[]; }

export type ProtocolStaticAnalysisComplianceStatus = | 'compliant' | 'needs_review' | 'non_compliant';

export interface ProtocolStaticAnalysisVerdict { category: string; compliance: ProtocolStaticAnalysisComplianceStatus; confidence: 'high' | 'low' | 'medium'; explanation: string; findingId: string; lineRange?: [number, number]; location: { file: string; function?: string; }; recommendation?: string; relatedRule: { id: string; requirement: string; source: string; }; }

export interface ProtocolStaticAnalysisSummary { compliantCount: number; needsReviewCount: number; nonCompliantCount: number; notes: string; overallStatus: ProtocolStaticAnalysisComplianceStatus; }

export interface ProtocolStaticAnalysisModelMetadata { generatedAt: string; modelVersion: string; protocol: string; protocolVersion?: string; ruleSet: string; }

export interface ProtocolStaticAnalysisModelResponse { metadata: ProtocolStaticAnalysisModelMetadata; summary: ProtocolStaticAnalysisSummary; verdicts: ProtocolStaticAnalysisVerdict[]; }

export interface ProtocolStaticAnalysisResult { analysisId: string; durationMs: number; inputs: { codeFileName: string; notes: null | string; protocolName: string; rulesFileName: string; rulesSummary: null | string; }; model: string; modelResponse: ProtocolStaticAnalysisModelResponse; submittedAt: string; }

export interface RunProtocolStaticAnalysisPayload { builderDockerfile: File; codeArchive: File; config: File; notes?: string; rules: File; }

export type ProtocolStaticAnalysisJobStatus = | 'queued' | 'running' | 'completed' | 'failed';

export interface ProtocolStaticAnalysisProgressEvent { id?: number; message: string; stage: string; timestamp: string; }

export interface ProtocolStaticAnalysisJob { createdAt: string; details?: Record<string, unknown> | null; error?: string | null; events: ProtocolStaticAnalysisProgressEvent[]; jobId: string; message: string; result?: ProtocolStaticAnalysisResult | null; stage: string; status: ProtocolStaticAnalysisJobStatus; updatedAt: string; }

export interface ProtocolStaticAnalysisHistoryEntry { analysisId?: string | null; completedAt?: string | null; configPath?: string | null; codeFileName?: string | null; createdAt: string; databasePath?: string | null; details?: Record<string, unknown> | null; durationMs?: number | null; error?: string | null; jobId: string; logsPath?: string | null; message: string; model?: string | null; modelVersion?: string | null; overallStatus?: ProtocolStaticAnalysisComplianceStatus | null; outputPath?: string | null; protocolName?: string | null; protocolVersion?: string | null; ruleSet?: string | null; rulesFileName?: string | null; stage: string; status: ProtocolStaticAnalysisJobStatus; submittedAt?: string | null; summary?: ProtocolStaticAnalysisSummary | null; updatedAt: string; workspacePath?: string | null; workspaceSnapshots?: { path?: string; stage?: string }[] | null; }

export interface FetchProtocolStaticAnalysisHistoryParams { limit?: number; }

export interface FetchProtocolStaticAnalysisHistoryResponse { count: number; items: ProtocolStaticAnalysisHistoryEntry[]; limit: number; }

export type ProtocolStaticAnalysisRuleResultStatus = | 'violation_found' | 'no_violation' | 'unknown';

export interface ProtocolStaticAnalysisRuleViolationDetail { codeLines?: number[] | null; filename?: string | null; functionName?: string | null; }

export interface ProtocolStaticAnalysisDatabaseRuleInsight { callGraph?: string | null; codeSnippet?: string | null; llmRaw?: unknown; reason?: string | null; result: ProtocolStaticAnalysisRuleResultStatus; resultLabel: string; ruleDesc: string; violations?: ProtocolStaticAnalysisRuleViolationDetail[]; }

export interface ProtocolStaticAnalysisDatabaseInsights { databasePath?: string | null; extractedAt: string; findings: ProtocolStaticAnalysisDatabaseRuleInsight[]; warnings?: string[]; workspacePath?: string | null; }

export interface FetchProtocolStaticAnalysisDatabaseInsightsPayload { databasePath?: string; jobId?: string; workspacePath?: string; }

const BASE_PATH = '/protocol-compliance/tasks';

export function fetchProtocolComplianceTasks( params?: FetchProtocolComplianceTasksParams, ) { return requestClient.get<FetchProtocolComplianceTasksResponse>(BASE_PATH, { params, }); }

export function createProtocolComplianceTask( payload: CreateProtocolComplianceTaskPayload, ) { const { description, document, name, tags } = payload; const formData = new FormData(); formData.append('file', document); formData.append('name', name); if (description) { formData.append('description', description); } if (tags?.length) { formData.append('tags', JSON.stringify(tags)); }

return requestClient.post<ProtocolComplianceTask>(BASE_PATH, formData, { headers: { 'Content-Type': 'multipart/form-data', }, }); }

export async function downloadProtocolComplianceTaskResult(taskId: string) { const accessStore = useAccessStore(); const token = accessStore.accessToken; const headers: Record<string, string> = {}; if (token) { headers.Authorization = `Bearer ${token}`; }

const response = (await baseRequestClient.request( `${BASE_PATH}/${taskId}/result`, { headers, method: 'GET', responseType: 'blob', }, )) as { data: Blob }; return response.data; }

export function runProtocolStaticAnalysis( payload: RunProtocolStaticAnalysisPayload, ) { const { builderDockerfile, codeArchive, config, notes, rules } = payload; const formData = new FormData(); formData.append('codeArchive', codeArchive); formData.append('builderDockerfile', builderDockerfile); formData.append('rules', rules); formData.append('config', config); if (notes?.trim()) { formData.append('notes', notes.trim()); }

return requestClient.post<ProtocolStaticAnalysisJob>( '/protocol-compliance/static-analysis', formData, { headers: { 'Content-Type': 'multipart/form-data', }, }, ); }

export function fetchProtocolStaticAnalysisProgress( jobId: string, fromEventId: number, ) { return requestClient.get<ProtocolStaticAnalysisJob>( `/protocol-compliance/static-analysis/${jobId}/progress`, { params: { fromEventId }, }, ); }

export function fetchProtocolStaticAnalysisResult(jobId: string) { return requestClient.get<ProtocolStaticAnalysisResult>( `/protocol-compliance/static-analysis/${jobId}/result`, ); }

export function fetchProtocolStaticAnalysisHistory( params?: FetchProtocolStaticAnalysisHistoryParams, ) { return requestClient.get<FetchProtocolStaticAnalysisHistoryResponse>( '/protocol-compliance/static-analysis/history', { params }, ); }

export function fetchProtocolStaticAnalysisDatabaseInsights( payload: FetchProtocolStaticAnalysisDatabaseInsightsPayload, ) { return requestClient.post<ProtocolStaticAnalysisDatabaseInsights>( '/protocol-compliance/static-analysis/database-insights', payload, ); }

export function deleteProtocolStaticAnalysisJob(jobId: string) { return requestClient.delete<{ deleted: boolean; jobId: string }>( `/protocol-compliance/static-analysis/history/${jobId}`, ); }

// Assertion Generation Types and APIs export type ProtocolAssertGenerationJobStatus = | 'queued' | 'running' | 'completed' | 'failed';

export interface ProtocolAssertGenerationProgressEvent { message: string; stage: string; timestamp: string; }

export interface ProtocolAssertGenerationInputInfo { buildInstructions?: null | string; codeFileName?: string; databaseFileName?: string; notes?: null | string; }

export interface ProtocolAssertGenerationArtifactInfo { database?: string; logs?: string; output?: string; workspace?: string; workspaceSnapshots?: Array<{ stage?: string; path?: string }>; zipPath?: string; }

export interface ProtocolAssertGenerationDockerInfo { command?: string[]; durationMs?: number; image?: string; logs?: string[]; }

export interface ProtocolInstrumentationDiffOutput { available: boolean; content?: string | null; path?: string | null; size?: number; truncated?: boolean; }

export interface ProtocolInstrumentationArtifacts { diffFiles?: string[]; diffOutput?: ProtocolInstrumentationDiffOutput; instrumentedCodePath?: string | null; }

export interface ProtocolInstrumentationDockerInfo { command?: string[]; durationMs?: number; image?: string; }

export interface ProtocolInstrumentationResult { artifacts?: ProtocolInstrumentationArtifacts; completedAt?: string; docker?: ProtocolInstrumentationDockerInfo; logs?: string[]; }

export interface ProtocolAssertGenerationResult { assertionCount: number; artifacts?: ProtocolAssertGenerationArtifactInfo; docker?: ProtocolAssertGenerationDockerInfo; generatedAt: string; inputs?: ProtocolAssertGenerationInputInfo; instrumentation?: ProtocolInstrumentationResult; jobId: string; protocolName: string; }

export interface ProtocolAssertGenerationJob { createdAt: string; error?: null | string; events: ProtocolAssertGenerationProgressEvent[]; jobId: string; message: string; result?: null | ProtocolAssertGenerationResult; stage: string; status: ProtocolAssertGenerationJobStatus; updatedAt: string; }

export interface RunProtocolAssertGenerationPayload { buildInstructions: string; codeArchive: File; database: File; notes?: string; }

export function runProtocolAssertGeneration( payload: RunProtocolAssertGenerationPayload, ) { const { buildInstructions, codeArchive, database, notes } = payload; const formData = new FormData(); formData.append('codeArchive', codeArchive); formData.append('database', database); formData.append('buildInstructions', buildInstructions.trim()); if (notes?.trim()) { formData.append('notes', notes.trim()); }

return requestClient.post<ProtocolAssertGenerationJob>( '/protocol-compliance/assertion-generation', formData, { headers: { 'Content-Type': 'multipart/form-data', }, }, ); }

export function fetchProtocolAssertGenerationProgress(jobId: string) { return requestClient.get<ProtocolAssertGenerationJob>( `/protocol-compliance/assertion-generation/${jobId}/progress`, ); }

export function fetchProtocolAssertGenerationResult(jobId: string) { return requestClient.get<ProtocolAssertGenerationResult>( `/protocol-compliance/assertion-generation/${jobId}/result`, ); }

export type ProtocolInstrumentationDiffResponse = ProtocolInstrumentationDiffOutput;

export function fetchProtocolInstrumentationDiff(jobId: string) { return requestClient.get<ProtocolInstrumentationDiffResponse>( `/protocol-compliance/assertion-generation/${jobId}/instrumentation-diff`, ); }

export async function downloadProtocolAssertGenerationResult(jobId: string) { const accessStore = useAccessStore(); const token = accessStore.accessToken; const headers: Record<string, string> = {}; if (token) { headers.Authorization = `Bearer ${token}`; }

const response = (await baseRequestClient.request( `/protocol-compliance/assertion-generation/${jobId}/download`, { headers, method: 'GET', responseType: 'blob', }, )) as { data: Blob };

return response.data; }

// Assertion history ------------------------------------------------------

export interface ProtocolAssertionHistoryEntry { jobId: string; codeFilename?: string | null; databaseFilename?: string | null; diffPath?: string | null; diffFilename?: string | null; createdAt: string; updatedAt: string; source?: string | null; }

export interface ProtocolAssertionHistoryResponse { items: ProtocolAssertionHistoryEntry[]; limit: number; count: number; }

export function fetchProtocolAssertionHistory(limit = 20) { return requestClient.get<ProtocolAssertionHistoryResponse>( '/protocol-compliance/assertions/history', { params: { limit }, }, ); }

export async function downloadProtocolAssertionDiff(jobId: string) { const accessStore = useAccessStore(); const token = accessStore.accessToken; const headers: Record<string, string> = {}; if (token) { headers.Authorization = `Bearer ${token}`; }

const response = (await baseRequestClient.request( `/protocol-compliance/assertions/history/${jobId}/diff`, { headers, method: 'GET', responseType: 'blob', }, )) as { data: Blob };

return response.data; }

// Diff Parsing Types and APIs export type ProtocolDiffParsingJobStatus = | 'queued' | 'running' | 'completed' | 'failed';

export interface DiffHunk { newLines: number; newStart: number; oldLines: number; oldStart: number; lines: Array<{ content: string; type: 'add' | 'delete' | 'normal'; }>; }

export interface DiffFile { additions: number; deletions: number; from: string; hunks: DiffHunk[]; to: string; }

export interface ProtocolDiffParsingResult { diffContent: string; files: DiffFile[]; generatedAt: string; jobId: string; summary: { filesChanged: number; insertions: number; deletions: number; }; }

export interface ProtocolDiffParsingProgressEvent { message: string; percentage: number; stage: string; timestamp: string; }

export interface ProtocolDiffParsingJob { createdAt: string; error?: null | string; events: ProtocolDiffParsingProgressEvent[]; jobId: string; message: string; parentJobId: string; percentage: number; result?: null | ProtocolDiffParsingResult; stage: string; status: ProtocolDiffParsingJobStatus; updatedAt: string; }

export function startProtocolDiffParsing(assertGenerationJobId: string) { return requestClient.post<ProtocolDiffParsingJob>( `/protocol-compliance/assertion-generation/${assertGenerationJobId}/diff-parsing`, {}, ); }

export function fetchProtocolDiffParsingProgress( assertGenerationJobId: string, diffParsingJobId: string, ) { return requestClient.get<ProtocolDiffParsingJob>( `/protocol-compliance/assertion-generation/${assertGenerationJobId}/diff-parsing/${diffParsingJobId}/progress`, ); }

export function fetchProtocolDiffParsingResult( assertGenerationJobId: string, diffParsingJobId: string, ) { return requestClient.get<ProtocolDiffParsingResult>( `/protocol-compliance/assertion-generation/${assertGenerationJobId}/diff-parsing/${diffParsingJobId}/result`, ); }

// 停止进程 export function stopProcess(data: { pid: string | number; protocol: string }) { return requestClient.post('/protocol-compliance/stop-process', data); }

// 停止并清理Docker容器export function stopAndCleanup(data: { container_id: string; protocol: string }) { return requestClient.post('/protocol-compliance/stop-and-cleanup', data); }

// 写入脚本文件 export function writeScript(data: { content: string; protocol: string; protocolImplementations?: string[] }) { return requestClient.post('/protocol-compliance/write-script', data); }

// 执行命令 export function executeCommand(data: { protocol: string; protocolImplementations?: string[] }) { return requestClient.post('/protocol-compliance/execute-command', data); }

// 读取日志 export function readLog(data: { protocol: string; lastPosition: number }) { return requestClient.post('/protocol-compliance/read-log', data); }

// 检查状态 export function checkStatus(data: { protocol: string }) { return requestClient.post('/protocol-compliance/check-status', data); }

export interface RunProtocolExtractPayload { apiKey: string; protocol: string; version: string; htmlFile: File; filterHeadings?: boolean; }

export interface ProtocolExtractRuleItem { group?: string | null; req_fields: string[]; req_type: string[]; res_fields: string[]; res_type: string[]; rule: string; }

export interface RunProtocolExtractResponse { protocol: string; version: string; ruleCount: number; rules: ProtocolExtractRuleItem[]; storeDir: string; resultPath: string; }

export async function runProtocolExtract(payload: RunProtocolExtractPayload) { const formData = new FormData(); formData.append('apiKey', payload.apiKey); formData.append('protocol', payload.protocol); formData.append('version', payload.version); formData.append('htmlFile', payload.htmlFile); if (payload.filterHeadings) { formData.append('filterHeadings', '1'); }

// ✅ 发送请求 const res = await requestClient.post( '/protocol-compliance/extract/run', formData, { headers: { 'Content-Type': 'multipart/form-data', }, }, );

// ✅ 自动兼容各种返回结构 const data = res?.data ?? res;

// 兼容数组格式、对象格式、嵌套 data 结构 const rules = Array.isArray(data) ? data : Array.isArray(data.rules) ? data.rules : Array.isArray(data.result) ? data.result : Array.isArray(data.data?.rules) ? data.data.rules : [];

// ✅ 兼容附加字段（若后端没返回则设默认值）return { rules, storeDir: data.storeDir || '', resultPath: data.resultPath || '', version: data.version || '', protocol: data.protocol || payload.protocol, ruleCount: rules.length || 0, }; }

==================================================================================================== 文件 3: apps/web-antd/src/views/protocol-compliance/extract/index.vue ====================================================================================================

<script lang="ts" setup>
import type { TableColumnType, UploadFile, UploadProps } from 'ant-design-vue';
import { computed, h, onMounted, reactive, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import {
  Button,
  Card,
  Empty,
  Form,
  FormItem,
  Input,
  message,
  Select,
  Space,
  Spin,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
  Progress,
  AutoComplete,
  Popconfirm,
  Divider,
} from 'ant-design-vue';
import type { ProtocolExtractRuleItem } from '@/api/protocol-compliance';
import { runProtocolExtract } from '@/api/protocol-compliance';

type RuleItem = ProtocolExtractRuleItem & {
  group?: string | null;
  msgType?: string; // 存储消息类型（如 CONNECT）
};

type HistoryItem = {
  id: string; // 唯一ID，用于删除定位
  analysisTime: string;
  categories: string[];
  protocol: string;
  version?: string;
  ruleCount: number;
  rules: RuleItem[];
  storeDir?: string;
  resultPath?: string;
};

const HISTORY_KEY = 'protocol_analysis_history';

// 全局状态
const activeMenuKey = ref('analyze');
const isAnalyzing = ref(false);
const isLoadingResult = ref(false);
const isUploadingResult = ref(false);
const analysisCompleted = ref(false);
const stagedResults = ref<RuleItem[]>([]);
const rfcFileList = ref<UploadFile[]>([]);
const resultFileList = ref<UploadFile[]>([]);
const selectedResultFile = ref<File | null>(null);
const selectedFile = ref<File | null>(null); // 协议文档上传文件对象
const formData = reactive({
  protocol: '',
  version: '',
  apiKey: '',
  filterHeadings: false,
});
const currentPage = ref(1);
const pageSize = ref(10);
const totalItems = ref(0);
const historyData = ref<HistoryItem[]>([]);
const lastResultMeta = ref<{ storeDir?: string; resultPath?: string } | null>(null);
const analysisProgress = ref(0);
const progressText = ref('准备分析...');
const selectedGroup = ref<null | string>(null);

// 组件别名
const TypographyParagraph = Typography.Paragraph;
const TypographyText = Typography.Text;

// 规则分类列表
const ruleCategories = [
  '安全',
  '性能',
  '兼容',
  '基础',
  '高级',
  '加密',
  '认证',
  '会话管理',
  '可靠性',
  '优化',
  '错误处理',
  '日志',
  '扩展性',
  'QoS',
  '协议约束',
];

// 服务器内置的历史结果（根据 public/pdfs 下实际文件调整）
const BUILTIN_SERVER_RESULTS: Array<{ protocol: string; version: string; path: string }> = [
  { protocol: 'CoAP', version: '1.0', path: '/public/ruleConfig_coap.json' },
  { protocol: 'CoAP', version: '2.0', path: '/public/ruleConfig_CoAP_v2.json' },
  { protocol: 'DHCPv6', version: '1.0', path: '/public/ruleConfig_dhcpv6.json' },
  { protocol: 'MQTTv3_1_1', version: '3.1.1', path: '/public/ruleConfig_mqttv3_1_1.json' },
  { protocol: 'MQTTv5', version: '5.0', path: '/public/ruleConfig_mqttv5.json' },
  { protocol: 'TLSv1_3', version: '1.3', path: '/public/ruleConfig_tlsv1_3.json' },
  { protocol: 'FTP', version: '1.0', path: '/public/ruleConfig_ftp.json' },
];

// 分隔符正则
const SPLIT_PATTERN = /[,;/]|\s+(?:or|and)\s+/gi;

// 生成唯一ID
function generateUniqueId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
}

// 标准化协议名称
function normalizeProtocolName(input: string) {
  return input
    .trim()
    .replaceAll(/\s+/g, '')
    .replaceAll(/[^\w./-]/g, '')
    .toLowerCase();
}

// 标准化版本名称
function normalizeVersionName(input: string) {
  return normalizeProtocolName(input);
}

// 随机生成分类
function randomCategories(): string[] {
  const shuffled = [...ruleCategories].sort(() => Math.random() - 0.5);
  const count = Math.floor(Math.random() * 2) + 3;
  return shuffled.slice(0, count);
}

// 转换为数组
function toArray(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item ?? '').trim())
      .filter((item) => Boolean(item));
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return [];
    const segments = trimmed.split(SPLIT_PATTERN).map((s) => s.trim()).filter(Boolean);
    return [...new Set(segments)];
  }
  return [];
}

// 标准化规则项
function normalizeRuleItem(raw: any, msgType?: string): RuleItem {
  const ruleText =
    typeof raw?.rule === 'string' ? raw.rule.trim() : String(raw?.rule ?? '').trim();
  return {
    rule: ruleText,
    group: raw?.group ?? null,
    msgType: msgType || raw?.msgType || raw?.req_type?.[0] || '',
    req_type: toArray(raw?.req_type),
    req_fields: toArray(raw?.req_fields),
    res_type: toArray(raw?.res_type),
    res_fields: toArray(raw?.res_fields),
  };
}

// 协议文档上传前校验
const beforeUploadRFC: UploadProps['beforeUpload'] = (file) => {
  const allowedTypes = ['text/html', 'application/pdf', 'text/plain', 'application/json'];
  const isAllowed = allowedTypes.includes(file.type);
  const isAllowedExt = ['.html', '.pdf', '.txt', '.json'].some((ext) =>
    file.name.toLowerCase().endsWith(ext),
  );
  if (!isAllowed && !isAllowedExt) {
    message.error('仅支持上传 HTML、PDF、TXT、JSON 格式的协议文档');
    return false;
  }
  const originalFile =
    (file as UploadFile & { originFileObj?: File }).originFileObj ||
    (file as unknown as File);
  selectedFile.value = originalFile;
  rfcFileList.value = [file];
  return false;
};

// 结果文件上传前校验
const beforeUploadResultFile: UploadProps['beforeUpload'] = (file) => {
  const isJson = file.type === 'application/json' || file.name.toLowerCase().endsWith('.json');
  if (!isJson) {
    message.error('请上传 JSON 格式的分析结果文件');
    return false;
  }
  const originalFile =
    (file as UploadFile & { originFileObj?: File }).originFileObj ||
    (file as unknown as File);
  selectedResultFile.value = originalFile;
  resultFileList.value = [file];
  return false;
};

// 移除协议文档
const removeRFC: UploadProps['onRemove'] = () => {
  selectedFile.value = null;
  rfcFileList.value = [];
  return true;
};

// 移除结果文件
const removeResultFile: UploadProps['onRemove'] = () => {
  selectedResultFile.value = null;
  resultFileList.value = [];
  return true;
};

// 保存历史记录到本地存储
function saveHistoryToStorage() {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(historyData.value));
}

// 加载历史记录
function loadHistoryFromStorage() {
  try {
    const saved = localStorage.getItem(HISTORY_KEY);
    const parsed = saved ? JSON.parse(saved) : [];
    if (!Array.isArray(parsed)) {
      historyData.value = [];
      return;
    }
    historyData.value = parsed
      .map((item: any) => {
        const rules = Array.isArray(item?.rules)
          ? item.rules
              .map((rule: any) => normalizeRuleItem(rule, rule.msgType))
              .filter((rule: RuleItem) => rule.rule)
          : [];
        return {
          id: item.id || generateUniqueId(), // 为旧数据补全ID
          analysisTime: String(item?.analysisTime ?? ''),
          categories: Array.isArray(item?.categories) ? item.categories : [],
          protocol: String(item?.protocol ?? ''),
          version: item?.version ? String(item.version) : undefined,
          ruleCount: typeof item?.ruleCount === 'number' ? item.ruleCount : rules.length,
          rules,
          storeDir: item?.storeDir ? String(item.storeDir) : undefined,
          resultPath: item?.resultPath ? String(item.resultPath) : undefined,
        } as HistoryItem;
      })
      .filter((item: HistoryItem) => item.protocol && item.rules.length > 0);
  } catch {
    historyData.value = [];
  }
}

// 预加载服务器上的内置结果，填充到 historyData 和 localStorage
async function preloadServerHistory() {
  for (const item of BUILTIN_SERVER_RESULTS) {
    const key = `${item.protocol}__${item.version}`;

    // 已存在相同协议+版本则跳过
    const exists = historyData.value.some(
      (h) => `${h.protocol}__${h.version}` === key,
    );
    if (exists) continue;

    try {
      const res = await fetch(item.path);
      if (!res.ok) continue;

      let text = await res.text();
      let rawData: any;
      try {
        rawData = JSON.parse(text);
      } catch {
        text = text.replace(/^\uFEFF/, '').trim();
        rawData = JSON.parse(text);
      }

      let rules: RuleItem[] = [];
      if (Array.isArray(rawData)) {
        rules = rawData.map(normalizeRuleItem).filter((r) => r.rule);
      } else if (typeof rawData === 'object' && Array.isArray(rawData.rules)) {
        rules = rawData.rules.map(normalizeRuleItem).filter((r) => r.rule);
      } else if (typeof rawData === 'object' && rawData !== null) {
        Object.entries(rawData).forEach(([msgType, ruleArray]) => {
          if (Array.isArray(ruleArray)) {
            const groupRules = ruleArray
              .map((rawRule: any) => normalizeRuleItem(rawRule, msgType))
              .filter((rule: RuleItem) => rule.rule);
            rules = [...rules, ...groupRules];
          }
        });
      }

      if (!rules.length) continue;

      lastResultMeta.value = {
        storeDir: item.path.substring(0, item.path.lastIndexOf('/')),
        resultPath: item.path,
      };

      addToHistory(rules, item.protocol, item.version);
    } catch (e) {
      console.error('预加载服务器历史失败：', item.path, e);
    }
  }
}

// 单条删除历史记录
function deleteHistoryItem(id: string) {
  historyData.value = historyData.value.filter((item) => item.id !== id);
  saveHistoryToStorage();
  message.success('历史记录删除成功');
}

// 清空全部历史记录
function clearAllHistory() {
  historyData.value = [];
  localStorage.removeItem(HISTORY_KEY);
  message.success('全部历史记录已清空');
}

// 开始分析协议文档
async function startAnalysis() {
  const uploadFile = selectedFile.value;
  const protocol = formData.protocol.trim();
  const version = formData.version.trim();
  const apiKey = formData.apiKey.trim();

  if (!uploadFile) {
    message.warning('请先上传协议文档 (HTML/PDF/TXT/JSON)');
    return;
  }
  if (!protocol) {
    message.warning('请输入或选择协议类型');
    return;
  }
  if (!version) {
    message.warning('请输入协议版本');
    return;
  }
  if (!apiKey) {
    message.warning('请输入 DeepSeek API 密钥');
    return;
  }

  isAnalyzing.value = true;
  analysisCompleted.value = false;
  stagedResults.value = [];
  selectedGroup.value = null;
  currentPage.value = 1;
  lastResultMeta.value = null;
  analysisProgress.value = 0;
  progressText.value = '准备分析...';

  const progressInterval = setInterval(() => {
    if (analysisProgress.value < 90) {
      analysisProgress.value += Math.floor(Math.random() * 10) + 5;
      if (analysisProgress.value > 30 && analysisProgress.value < 60) {
        progressText.value = '正在提取协议规则...';
      } else if (analysisProgress.value >= 60) {
        progressText.value = '正在整理规则数据...';
      }
    }
  }, 500);

  try {
    const response = await runProtocolExtract({
      apiKey,
      protocol,
      version,
      htmlFile: uploadFile,
      filterHeadings: formData.filterHeadings,
    });

    clearInterval(progressInterval);
    analysisProgress.value = 100;
    progressText.value = '分析完成！';

    const rulesData = response.rules || response.data?.rules || [];
    const rules = Array.isArray(rulesData)
      ? rulesData.map(normalizeRuleItem).filter((rule) => rule.rule)
      : [];

    if (rules.length === 0) {
      throw new Error('分析流程完成，但未生成任何规则');
    }

    stagedResults.value = rules;
    totalItems.value = rules.length;
    analysisCompleted.value = true;
    lastResultMeta.value = {
      storeDir:
        response.storeDir ||
        response.data?.storeDir ||
        `project_store/${normalizeProtocolName(protocol)}_${normalizeVersionName(
          version,
        )}`,
      resultPath:
        response.resultPath ||
        response.data?.resultPath ||
        `project_store/${normalizeProtocolName(protocol)}_${normalizeVersionName(
          version,
        )}/rules.json`,
    };

    addToHistory(rules, protocol, version);
    message.success(`分析成功，提取到 ${rules.length} 条规则`);
  } catch (error: any) {
    clearInterval(progressInterval);
    analysisProgress.value = 0;
    progressText.value = '分析失败';

    const details = error?.response?.data?.details;
    let detailMessage = error?.response?.data?.message || error?.message || '未知错误';
    if (details) {
      if (typeof details === 'string') {
        detailMessage = details;
      } else if (typeof details === 'object') {
        if (typeof details.message === 'string' && details.message.trim()) {
          detailMessage = details.message;
        } else if (Array.isArray(details.stderr) && details.stderr.length) {
          detailMessage = details.stderr.join('\n');
        } else if (Array.isArray(details.stdout) && details.stdout.length) {
          detailMessage = details.stdout.join('\n');
        } else {
          detailMessage = JSON.stringify(details);
        }
      }
    }
    console.error('分析失败', error);
    message.error(`分析失败: ${detailMessage}`);
  } finally {
    isAnalyzing.value = false;
  }
}

// 导入结果文件
async function uploadAndSaveResult() {
  const protocol = formData.protocol.trim();
  const version = formData.version.trim();
  const resultFile = selectedResultFile.value;

  if (!resultFile) {
    message.warning('请先上传 JSON 格式的分析结果文件');
    return;
  }
  if (!protocol) {
    message.warning('请输入或选择协议类型');
    return;
  }
  if (!version) {
    message.warning('请输入协议版本');
    return;
  }

  isUploadingResult.value = true;
  analysisCompleted.value = false;
  stagedResults.value = [];
  selectedGroup.value = null;
  currentPage.value = 1;
  lastResultMeta.value = null;

  try {
    // 读取文件
    const reader = new FileReader();
    const fileContent = await new Promise<string>((resolve, reject) => {
      reader.onload = (e) => {
        const result = e.target?.result;
        if (typeof result === 'string') {
          resolve(result);
        } else {
          reject(new Error('文件读取结果不是字符串'));
        }
      };
      reader.onerror = (err) => reject(new Error(`文件读取失败：${err.message}`));
      reader.onabort = () => reject(new Error('文件读取被中止'));
      reader.readAsText(resultFile);
    });

    // 解析JSON
    let rawData: any;
    try {
      rawData = JSON.parse(fileContent);
    } catch (jsonErr) {
      const cleanedText = fileContent.replace(/^\uFEFF/, '').trim();
      try {
        rawData = JSON.parse(cleanedText);
      } catch (err) {
        throw new Error(`JSON格式错误：${(err as Error).message}`);
      }
    }

    // 处理3种格式
    let rules: RuleItem[] = [];
    if (Array.isArray(rawData)) {
      rules = rawData.map(normalizeRuleItem).filter((rule) => rule.rule);
      console.log('识别到直接数组格式，共解析', rules.length, '条规则');
    } else if (typeof rawData === 'object' && Array.isArray(rawData.rules)) {
      rules = rawData.rules.map(normalizeRuleItem).filter((rule) => rule.rule);
      console.log('识别到 rules 嵌套格式，共解析', rules.length, '条规则');
    } else if (typeof rawData === 'object' && rawData !== null) {
      Object.entries(rawData).forEach(([msgType, ruleArray]) => {
        if (Array.isArray(ruleArray)) {
          const groupRules = ruleArray
            .map((rawRule: any) => normalizeRuleItem(rawRule, msgType))
            .filter((rule: RuleItem) => rule.rule);
          rules = [...rules, ...groupRules];
        }
      });
      console.log('识别到按消息类型分组格式，共解析', rules.length, '条规则');
    }

    if (rules.length === 0) {
      throw new Error('上传的文件中未包含有效规则（请检查JSON格式是否正确）');
    }

    // 显示结果
    stagedResults.value = rules;
    totalItems.value = rules.length;
    analysisCompleted.value = true;
    lastResultMeta.value = {
      storeDir: `uploaded_results/${normalizeProtocolName(
        protocol,
      )}_${normalizeVersionName(version)}`,
      resultPath: `${normalizeProtocolName(protocol)}_${normalizeVersionName(
        version,
      )}_uploaded.json`,
    };

    // 去重添加历史
    const isDuplicate = historyData.value.some(
      (item) => item.protocol === protocol && item.version === version,
    );
    if (!isDuplicate) {
      addToHistory(rules, protocol, version);
    }

    // 清空上传状态
    resultFileList.value = [];
    selectedResultFile.value = null;

    message.success(
      `成功导入 ${protocol} ${version} 的分析结果，共 ${rules.length} 条规则（已存入历史记录）`,
    );
  } catch (error: any) {
    let errorMsg = '';
    if (error.message.includes('JSON格式错误')) {
      errorMsg = `JSON文件格式错误，请检查文件内容`;
    } else if (error.message.includes('未包含有效规则')) {
      errorMsg = `上传的文件中未找到有效规则（支持格式：直接数组、{rules:[]}、{消息类型:[]}）`;
    } else if (error.message.includes('文件读取')) {
      errorMsg = `文件读取失败：${error.message}`;
    } else {
      errorMsg = `导入失败：${error.message}`;
    }
    message.error(errorMsg);
    console.error('导入分析结果失败：', error);
  } finally {
    isUploadingResult.value = false;
  }
}

// 加载本地结果文件（包含 /pdfs 下静态结果）
async function loadExistingResult() {
  const protocol = formData.protocol.trim();
  const version = formData.version.trim();

  if (!protocol) {
    message.warning('请输入或选择协议类型');
    return;
  }
  if (!version) {
    message.warning('请输入协议版本');
    return;
  }

  isLoadingResult.value = true;
  analysisCompleted.value = false;
  stagedResults.value = [];
  selectedGroup.value = null;
  currentPage.value = 1;
  lastResultMeta.value = null;

  try {
    const normalizedProtocol = normalizeProtocolName(protocol);
    const normalizedVersion = normalizeVersionName(version);

    const possiblePaths = [
      `project_store/${normalizedProtocol}_${normalizedVersion}/rules.json`,
      `project_store/${normalizedProtocol}/${normalizedVersion}/rules.json`,
      `results/${normalizedProtocol}_${normalizedVersion}.json`,
      `static/results/${normalizedProtocol}_${normalizedVersion}.json`,
      `${normalizedProtocol}_${normalizedVersion}_rules.json`,
      // 新增：public/pdfs 下的静态结果
      `/public/ruleConfig_${normalizedProtocol}_${normalizedVersion}.json`,
      `/public/ruleConfig_${normalizedProtocol}.json`,
    ];

    let rawResponseText = '';
    let successPath = '';
    let response: Response | null = null;

    // 尝试所有路径
    for (const path of possiblePaths) {
      try {
        response = await fetch(path);
        if (response.ok) {
          successPath = path;
          rawResponseText = await response.text();
          break;
        }
      } catch {
        continue;
      }
    }

    if (!successPath) {
      throw new Error(`未找到 ${protocol} ${version} 的结果文件`);
    }

    // 解析JSON
    let rawData: any;
    try {
      rawData = JSON.parse(rawResponseText);
    } catch {
      const cleanedText = rawResponseText.replace(/^\uFEFF/, '').trim();
      rawData = JSON.parse(cleanedText);
    }

    // 处理3种格式
    let rules: RuleItem[] = [];
    if (Array.isArray(rawData)) {
      rules = rawData.map(normalizeRuleItem).filter((rule) => rule.rule);
    } else if (typeof rawData === 'object' && Array.isArray(rawData.rules)) {
      rules = rawData.rules.map(normalizeRuleItem).filter((rule) => rule.rule);
    } else if (typeof rawData === 'object' && rawData !== null) {
      Object.entries(rawData).forEach(([msgType, ruleArray]) => {
        if (Array.isArray(ruleArray)) {
          const groupRules = ruleArray
            .map((rawRule: any) => normalizeRuleItem(rawRule, msgType))
            .filter((rule: RuleItem) => rule.rule);
          rules = [...rules, ...groupRules];
        }
      });
    }

    if (rules.length === 0) {
      throw new Error(`文件 ${successPath} 中未包含有效规则`);
    }

    // 显示结果
    stagedResults.value = rules;
    totalItems.value = rules.length;
    analysisCompleted.value = true;
    lastResultMeta.value = {
      storeDir: successPath.substring(0, successPath.lastIndexOf('/')),
      resultPath: successPath,
    };

    // 去重添加历史
    const isDuplicate = historyData.value.some(
      (item) => item.protocol === protocol && item.version === version,
    );
    if (!isDuplicate) {
      addToHistory(rules, protocol, version);
    }

    message.success(`成功加载 ${protocol} ${version} 的本地结果，共 ${rules.length} 条规则`);
  } catch (error: any) {
    let errorMsg = '';
    if (error.message.includes('未找到')) {
      errorMsg = `未找到 ${protocol} ${version} 的分析结果，请先上传文件或导入结果`;
    } else if (error.message.includes('未包含有效规则')) {
      errorMsg = `结果文件中未找到有效规则`;
    } else if (error.message.includes('JSON格式错误')) {
      errorMsg = `JSON文件格式错误，请检查文件内容`;
    } else {
      errorMsg = `加载失败：${error.message}`;
    }
    message.error(errorMsg);
    console.error('加载本地结果失败：', error);
  } finally {
    isLoadingResult.value = false;
  }
}

// 添加到历史记录
function addToHistory(rules: RuleItem[], protocol: string, version: string) {
  const now = new Date().toLocaleString();
  const newHistory: HistoryItem = {
    id: generateUniqueId(),
    protocol,
    version,
    ruleCount: rules.length,
    analysisTime: now,
    categories: randomCategories(),
    rules,
    storeDir: lastResultMeta.value?.storeDir,
    resultPath: lastResultMeta.value?.resultPath,
  };

  // 去重
  historyData.value = historyData.value.filter(
    (item) => !(item.protocol === protocol && item.version === version),
  );
  historyData.value.unshift(newHistory);
  historyData.value = historyData.value.slice(0, 20); // 最多保留20条
  saveHistoryToStorage();
}

// 下载结果
function downloadAnalysisResult() {
  if (!analysisCompleted.value || stagedResults.value.length === 0) {
    message.warning('暂无分析结果可下载');
    return;
  }
  const normalizedProtocol = normalizeProtocolName(formData.protocol || 'protocol');
  const normalizedVersion = normalizeVersionName(formData.version || 'v');
  const fileName = `ruleConfig_${normalizedProtocol}_${normalizedVersion}.json`;

  // 按消息类型分组
  const groupedRules: Record<string, RuleItem[]> = {};
  stagedResults.value.forEach((rule) => {
    const msgType = rule.msgType || 'default';
    if (!groupedRules[msgType]) {
      groupedRules[msgType] = [];
    }
    const { msgType: _, ...ruleWithoutMsgType } = rule;
    groupedRules[msgType].push(ruleWithoutMsgType);
  });

  const jsonStr = JSON.stringify(groupedRules, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
  message.success(`分析结果已下载：${fileName}`);
}

// 从历史记录打开
function openFromHistory(item: HistoryItem) {
  formData.protocol = item.protocol;
  formData.version = item.version ?? '';
  stagedResults.value = item.rules ?? [];
  totalItems.value = stagedResults.value.length;
  analysisCompleted.value = stagedResults.value.length > 0;
  selectedGroup.value = null;
  currentPage.value = 1;
  activeMenuKey.value = 'analyze';
  lastResultMeta.value = {
    storeDir: item.storeDir,
    resultPath: item.resultPath,
  };
}

// 计算属性：分组列表（按消息类型）
const groupList = computed(() => {
  const groups = new Set(
    stagedResults.value
      .map((r) => r.msgType)
      .filter((group): group is string => Boolean(group)),
  );
  return [...groups];
});

// 计算属性：筛选后的结果
const filteredResults = computed(() => {
  if (!selectedGroup.value) return stagedResults.value;
  return stagedResults.value.filter((r) => r.msgType === selectedGroup.value);
});

// 计算属性：当前页数据
const currentPageData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredResults.value.slice(start, start + pageSize.value);
});

// 渲染标签列表
const renderTagList = (value: unknown, color: string) => {
  const items = toArray(value);
  if (!items.length) {
    return h('span', { class: 'table-empty' }, '-');
  }
  return h(
    Space,
    { size: 'small', wrap: true },
    items.map((item, index) =>
      h(
        Tag,
        {
          color: color,
          key: `tag-${index}`,
          style: { margin: '2px' },
        },
        () => item.trim(),
      ),
    ),
  );
};

// 结果表格列定义
const columns: TableColumnType<RuleItem>[] = [
  {
    title: '序号',
    key: 'index',
    width: 60,
    customRender: ({ index }) => (currentPage.value - 1) * pageSize.value + index + 1,
  },
  {
    title: '消息类型',
    dataIndex: 'msgType',
    key: 'msgType',
    width: 120,
    customRender: ({ text }) => {
      const validText = String(text ?? '未知').trim();
      return h(Tag, { color: 'blue' }, validText);
    },
  },
  {
    title: '规则描述',
    dataIndex: 'rule',
    key: 'rule',
    width: 420,
    customRender: ({ text }) => {
      const validText = String(text ?? '').trim();
      return h(
        'div',
        {
          style: 'white-space: pre-wrap; word-break: break-word; line-height: 1.5;',
        },
        validText,
      );
    },
  },
  {
    title: '协议消息类型',
    dataIndex: 'req_type',
    key: 'req_type',
    width: 180,
    customRender: ({ text }) => renderTagList(text, 'purple'),
  },
  {
    title: '请求字段',
    dataIndex: 'req_fields',
    key: 'req_fields',
    width: 220,
    customRender: ({ text }) => renderTagList(text, 'blue'),
  },
  {
    title: '响应类型',
    dataIndex: 'res_type',
    key: 'res_type',
    width: 180,
    customRender: ({ text }) => renderTagList(text, 'orange'),
  },
  {
    title: '响应字段',
    dataIndex: 'res_fields',
    key: 'res_fields',
    width: 220,
    customRender: ({ text }) => renderTagList(text, 'green'),
  },
];

// 表格分页变化
function handleTableChange(pagination: any) {
  currentPage.value = pagination.current;
  pageSize.value = pagination.pageSize;
}

// 历史记录表格列定义
const historyColumns = computed<TableColumnType<HistoryItem>[]>(() => [
  {
    title: '协议',
    dataIndex: 'protocol',
    key: 'protocol',
    customRender: ({ record }) => {
      const item = record as HistoryItem;
      const protocolLabel = item.protocol ?? '';
      const versionLabel = item.version ? `(${item.version})` : '';
      return h(Tag, { color: 'cyan' }, `${protocolLabel}${versionLabel}`);
    },
  },
  {
    title: '规则数量',
    dataIndex: 'ruleCount',
    key: 'ruleCount',
    customRender: ({ text }) => h(Tag, { color: 'green' }, String(text ?? '0')),
  },
  {
    title: '分析时间',
    dataIndex: 'analysisTime',
    key: 'analysisTime',
  },
  {
    title: '操作',
    key: 'action',
    width: 120,
    align: 'center',
    customRender: ({ record }) => {
      const item = record as HistoryItem;
      return h(
        Popconfirm,
        {
          title: '确定要删除这条记录吗？',
          okText: '确定',
          cancelText: '取消',
          onConfirm: () => deleteHistoryItem(item.id),
          placement: 'top',
        },
        {
          default: () =>
            h(
              Button,
              { type: 'text', danger: true, size: 'small' },
              '删除',
            ),
        },
      );
    },
  },
]);

// 挂载时：先加载本地缓存，再预加载服务器内置结果
onMounted(async () => {
  loadHistoryFromStorage();
  await preloadServerHistory();
});
</script>

<template>
  <Page title="协议规则提取">
    <div class="protocol-extract">
      <Tabs v-model:active-key="activeMenuKey" class="extract-tabs">
        <!-- 规则提取标签页 -->
        <Tabs.TabPane key="analyze" tab="规则提取">
          <div class="analyze-layout">
            <Card class="form-card">
              <template #title>
                <Space>
                  <IconifyIcon icon="ant-design:cloud-upload-outlined" class="text-lg" />
                  <span>协议分析 / 结果导入</span>
                </Space>
              </template>
              <Spin
                :spinning="isAnalyzing || isLoadingResult || isUploadingResult"
                :tip="
                  isAnalyzing
                    ? '正在执行协议分析...'
                    : isLoadingResult
                    ? '正在读取本地结果...'
                    : '正在导入结果文件...'
                "
              >
                <Form class="extract-form" layout="vertical">
                  <!-- 基础信息 -->
                  <FormItem label="协议类型">
                    <AutoComplete
                      v-model:value="formData.protocol"
                      allow-clear
                      class="input-protocol"
                      placeholder="选择或输入协议类型（如 MQTTv5）"
                      :options="[
                        { value: 'CoAP' },
                        { value: 'DHCPv6' },
                        { value: 'MQTTv3_1_1' },
                        { value: 'MQTTv5' },
                        { value: 'TLSv1_3' },
                        { value: 'FTP' },
                      ]"
                    />
                  </FormItem>
                  <FormItem label="协议版本">
                    <Input
                      v-model:value="formData.version"
                      placeholder="请输入协议版本（如 1.0）"
                    />
                  </FormItem>

                  <!-- 功能一：上传协议文档分析 -->
                  <div
                    style="
                      margin: 16px 0;
                      padding: 16px;
                      border: 1px dashed #e8e8e8;
                      border-radius: 4px;
                    "
                  >
                    <TypographyText strong>功能一：上传协议文档，自动分析</TypographyText>
                    <FormItem label="DeepSeek API 密钥" style="margin-top: 8px">
                      <Input.Password
                        v-model:value="formData.apiKey"
                        autocomplete="off"
                        placeholder="分析需要调用API，必填"
                      />
                    </FormItem>
                    <FormItem label="上传协议文档">
                      <Upload
                        :file-list="rfcFileList"
                        :before-upload="beforeUploadRFC"
                        :on-remove="removeRFC"
                        accept=".html,.pdf,.txt,.json"
                        style="width: 100%"
                      >
                        <Button block type="dashed">
                          <IconifyIcon icon="ant-design:file-add-outlined" class="mr-1" />
                          选择协议文档（支持 HTML/PDF/TXT/JSON）
                        </Button>
                      </Upload>
                    </FormItem>
                    <FormItem label="启用目录筛选" value-prop-name="checked">
                      <Switch v-model:checked="formData.filterHeadings" />
                    </FormItem>
                    <Button
                      type="primary"
                      :loading="isAnalyzing"
                      @click="startAnalysis"
                      style="margin-top: 8px"
                    >
                      <IconifyIcon icon="ant-design:play-circle-outlined" class="mr-1" />
                      开始分析（生成结果并存储）
                    </Button>
                  </div>

                  <!-- 功能二：上传结果文件导入 -->
                  <div
                    style="
                      margin: 16px 0;
                      padding: 16px;
                      border: 1px dashed #e8e8e8;
                      border-radius: 4px;
                    "
                  >
                    <TypographyText strong
                      >功能二：上传已有结果文件，直接导入</TypographyText
                    >
                    <TypographyParagraph type="secondary" style="margin: 8px 0">
                      已提前生成分析结果JSON文件？直接上传导入，无需重复分析（无需API密钥）
                      <br />支持3种JSON格式：1. 直接数组 [{...}] 2. { "rules": [...] } 3. 按消息类型分组 {
                      "CONNECT": [...], ... }
                    </TypographyParagraph>
                    <FormItem label="上传分析结果文件">
                      <Upload
                        :file-list="resultFileList"
                        :before-upload="beforeUploadResultFile"
                        :on-remove="removeResultFile"
                        accept=".json"
                        style="width: 100%"
                      >
                        <Button block type="dashed">
                          <IconifyIcon icon="ant-design:upload-outlined" class="mr-1" />
                          选择JSON格式的结果文件
                        </Button>
                      </Upload>
                      <TypographyText
                        type="secondary"
                        style="font-size: 12px; margin-top: 8px; display: block"
                      >
                        已选文件：{{ resultFileList[0]?.name || '无' }}
                      </TypographyText>
                    </FormItem>
                    <Button
                      type="default"
                      :loading="isUploadingResult"
                      @click="uploadAndSaveResult"
                      style="margin-top: 8px; background: #1890ff; color: white"
                    >
                      <IconifyIcon icon="ant-design:save-outlined" class="mr-1" />
                      导入结果并存储到历史记录
                    </Button>
                  </div>

                  <!-- 功能三：加载本地结果 -->
                  <div
                    style="
                      margin: 16px 0;
                      padding: 16px;
                      border: 1px dashed #e8e8e8;
                      border-radius: 4px;
                    "
                  >
                    <TypographyText strong
                      >功能三：加载本地已存结果，快速查看</TypographyText
                    >
                    <TypographyParagraph type="secondary" style="margin: 8px 0">
                      项目中已存在结果文件？直接输入协议名和版本，快速加载（无需上传文件）
                    </TypographyParagraph>
                    <Button
                      type="default"
                      :loading="isLoadingResult"
                      @click="loadExistingResult"
                      style="margin-top: 8px"
                    >
                      <IconifyIcon icon="ant-design:folder-open-outlined" class="mr-1" />
                      加载本地结果（自动查找文件）
                    </Button>
                  </div>

                  <TypographyParagraph class="form-tip" type="secondary">
                    提示：所有生成/导入的结果都会自动存入历史记录，可在「历史记录」标签页查看。
                    <br />如果操作失败，请打开浏览器控制台（F12）查看具体错误信息。
                  </TypographyParagraph>
                </Form>
              </Spin>
            </Card>

            <!-- 结果预览卡片 -->
            <Card class="result-card">
              <template #title>
                <Space>
                  <IconifyIcon icon="ant-design:profile-outlined" class="text-lg" />
                  <span>规则预览</span>
                </Space>
              </template>
              <div class="result-toolbar">
                <TypographyText type="secondary">
                  共 {{ totalItems }} 条规则
                  <span v-if="selectedGroup">· 已筛选 {{ filteredResults.length }} 条</span>
                </TypographyText>
                <Space size="small" wrap>
                  <Select
                    v-model:value="selectedGroup"
                    allow-clear
                    class="select-group"
                    :disabled="!analysisCompleted || !groupList.length"
                    placeholder="按消息类型筛选（如 CONNECT）"
                  >
                    <Select.Option v-for="g in groupList" :key="`group-${g}`" :value="g">
                      {{ g }}
                    </Select.Option>
                  </Select>
                  <Button
                    :disabled="!analysisCompleted || !stagedResults.length"
                    @click="downloadAnalysisResult"
                  >
                    <IconifyIcon icon="ant-design:download-outlined" class="mr-1" />
                    下载 JSON（按消息类型分组）
                  </Button>
                </Space>
              </div>
              <TypographyParagraph
                v-if="analysisCompleted && lastResultMeta"
                class="result-meta"
                type="secondary"
              >
                结果来源：{{ lastResultMeta.resultPath || '未知' }}
                <span v-if="lastResultMeta.storeDir"
                  >（存储目录：{{ lastResultMeta.storeDir }}）</span
                >
              </TypographyParagraph>
              <div v-if="analysisCompleted && filteredResults.length" class="table-wrapper">
                <Table
                  :columns="columns"
                  :data-source="currentPageData"
                  :pagination="{
                    current: currentPage,
                    pageSize,
                    total: filteredResults.length,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 条规则`,
                  }"
                  :row-key="(record, index) => `row-${index}`"
                  :scroll="{ x: 'max-content', y: 400 }"
                  bordered
                  @change="handleTableChange"
                />
              </div>
              <Empty v-else-if="analysisCompleted" description="未找到规则数据" />
              <TypographyParagraph v-else class="result-placeholder" type="secondary">
                请选择功能生成/导入规则，或加载本地已有结果。
              </TypographyParagraph>
            </Card>
          </div>
        </Tabs.TabPane>

        <!-- 历史记录标签页 -->
        <Tabs.TabPane key="history" tab="历史记录">
          <Card class="history-card">
            <template #title>
              <Space
                style="width: 100%; justify-content: space-between; align-items: center"
              >
                <Space>
                  <IconifyIcon icon="ant-design:calendar-outlined" class="text-lg" />
                  <span>历史记录（自动存储所有结果）</span>
                </Space>
                <!-- 清空全部按钮 -->
                <Popconfirm
                  title="确定要清空全部历史记录吗？此操作不可恢复！"
                  ok-text="确定"
                  cancel-text="取消"
                  ok-type="danger"
                  @confirm="clearAllHistory"
                  placement="right"
                >
                  <Button type="primary" danger size="small">
                    <IconifyIcon icon="ant-design:delete-outlined" class="mr-1" />
                    清空全部
                  </Button>
                </Popconfirm>
              </Space>
            </template>

            <Divider />

            <div v-if="historyData.length" class="history-header">
              <TypographyText type="secondary">已存储的分析结果：</TypographyText>
              <Space size="small" wrap class="history-protocols">
                <Tag
                  v-for="(item, index) in historyData"
                  :key="`history-tag-${index}`"
                  color="blue"
                  :style="{ cursor: 'pointer' }"
                  @click="openFromHistory(item)"
                >
                  {{ item.protocol }}({{ item.version }}) - {{ item.ruleCount }}条
                </Tag>
              </Space>
            </div>

            <TypographyParagraph class="history-tip" type="secondary">
              包含：上传文档分析、导入结果文件、加载本地结果的所有记录，点击标签可快速查看。
            </TypographyParagraph>

            <div class="history-table-wrapper" v-if="historyData.length">
              <Table
                :columns="historyColumns"
                :data-source="historyData"
                :pagination="{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total) => `共 ${total} 条记录`,
                }"
                :row-key="(item) => item.id"
                bordered
                :scroll="{ x: 'max-content' }"
                :custom-row="
                  (record) => ({
                    onClick: () => openFromHistory(record as HistoryItem),
                  })
                "
              />
            </div>

            <Empty v-else description="暂无历史记录" style="margin: 32px 0" />
          </Card>
        </Tabs.TabPane>
      </Tabs>
    </div>

  </Page>
</template>

<style scoped>
:deep(.mb-2.flex.text-lg.font-semibold) {
  font-size: 2rem;
}

.protocol-extract {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100vh;
  height: auto;
  overflow-y: auto;
  padding-bottom: 24px;
}

.extract-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 16px;
}

.analyze-layout {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 16px;
  align-items: start;
}

.form-card,
.result-card {
  display: flex;
  flex-direction: column;
  height: auto;
}

.extract-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-protocol {
  width: 100%;
}

.form-tip {
  margin: 8px 0;
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.result-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 16px 0;
}

.select-group {
  min-width: 180px;
}

.table-wrapper {
  flex: 1;
  min-height: 400px;
}

.result-placeholder {
  margin: 32px 0;
  font-size: 13px;
  text-align: center;
}

.result-meta {
  margin: 8px 0;
  font-size: 12px;
}

.history-card :deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  flex-wrap: wrap;
}

.history-protocols {
  display: inline-flex;
  flex-wrap: wrap;
  width: 100%;
  gap: 8px;
}

.history-tip {
  margin: 8px 0;
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.history-table-wrapper {
  width: 100%;
  margin-top: 8px;
}

:deep(.ant-table-cell) {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
}

.table-empty {
  color: var(--ant-text-color-secondary);
}

/* 适配移动端 */
@media (max-width: 1200px) {
  .analyze-layout {
    grid-template-columns: 1fr;
  }
}
</style>

==================================================================================================== 文件 4: apps/web-antd/src/views/protocol-compliance/static/index.vue ====================================================================================================

<script lang="ts" setup>
import type { FormInstance, UploadFile, UploadProps } from 'ant-design-vue';
import type { Rule } from 'ant-design-vue/es/form';

import type {
  ProtocolStaticAnalysisDatabaseInsights,
  FetchProtocolStaticAnalysisDatabaseInsightsPayload,
  ProtocolStaticAnalysisHistoryEntry,
  ProtocolStaticAnalysisJob,
  ProtocolStaticAnalysisProgressEvent,
  ProtocolStaticAnalysisResult,
  ProtocolStaticAnalysisRuleResultStatus,
} from '#/api/protocol-compliance';

import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  Button,
  Card,
  Descriptions,
  Divider,
  Drawer,
  Form,
  FormItem,
  Input,
  message,
  Popconfirm,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
} from 'ant-design-vue';

import {
  deleteProtocolStaticAnalysisJob,
  fetchProtocolStaticAnalysisDatabaseInsights,
  fetchProtocolStaticAnalysisProgress,
  fetchProtocolStaticAnalysisResult,
  fetchProtocolStaticAnalysisHistory,
  runProtocolStaticAnalysis,
} from '#/api/protocol-compliance';

const TypographyParagraph = Typography.Paragraph;
const TypographyText = Typography.Text;

const formRef = ref<FormInstance>();
const formState = reactive({
  archive: null as File | null,
  builder: null as File | null,
  config: null as File | null,
  rules: null as File | null,
  notes: '',
});

const archiveFileList = ref<UploadFile[]>([]);
const builderFileList = ref<UploadFile[]>([]);
const configFileList = ref<UploadFile[]>([]);
const rulesFileList = ref<UploadFile[]>([]);
const isSubmitting = ref(false);
const analysisResult = ref<null | ProtocolStaticAnalysisResult>(null);
const activeJob = ref<null | ProtocolStaticAnalysisJob>(null);
const activeJobId = ref<null | string>(null);
const progressLogs = ref<string[]>([]);
const progressError = ref<null | string>(null);
const pollingTimer = ref<null | number>(null);
const lastEventId = ref<number>(0);

const PROGRESS_STATUS_META: Record<
  ProtocolStaticAnalysisJob['status'],
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
  builder: [
    {
      message: '请上传 Builder Dockerfile',
      required: true,
      trigger: 'change',
    },
  ],
  config: [
    {
      message: '请上传 TOML 配置文件',
      required: true,
      trigger: 'change',
    },
  ],
  rules: [
    {
      message: '请上传协议规则 JSON 文件',
      required: true,
      trigger: 'change',
    },
  ],
};

const formatter = new Intl.DateTimeFormat(undefined, {
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  month: '2-digit',
  year: 'numeric',
});

const logFormatter = new Intl.DateTimeFormat(undefined, {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});

const STATUS_LABELS: Record<string, string> = {
  compliant: '合规',
  needs_review: '需复核',
  non_compliant: '发现问题',
};

const RULE_RESULT_META: Record<
  ProtocolStaticAnalysisRuleResultStatus,
  { color: string; label: string }
> = {
  no_violation: { color: 'success', label: '未发现违规' },
  unknown: { color: 'default', label: '未判定' },
  violation_found: { color: 'error', label: '发现违规' },
};

interface HistoryInsightSummary {
  noViolation: number;
  total: number;
  unknown: number;
  violation: number;
}

interface HistoryColumn {
  dataIndex: string;
  key: string;
  title: string;
  width?: number;
}

const HISTORY_DEFAULT_LIMIT = 50;
const PROGRESS_LOGS_MAX_LINES = 2000;

const historyColumns: HistoryColumn[] = [
  { dataIndex: 'codeFileName', key: 'codeFileName', title: '压缩包名称', width: 220 },
  { dataIndex: 'status', key: 'status', title: '任务状态', width: 120 },
  {
    dataIndex: 'overallStatus',
    key: 'overallStatus',
    title: '整体判定',
    width: 140,
  },
  { dataIndex: 'protocolName', key: 'protocol', title: '协议', width: 160 },
  {
    dataIndex: 'ruleInsights',
    key: 'ruleInsights',
    title: '规则检测结果',
  },
  { dataIndex: 'updatedAt', key: 'updatedAt', title: '更新时间', width: 180 },
  { dataIndex: 'actions', key: 'actions', title: '操作', width: 100 },
];

const historyItems = ref<ProtocolStaticAnalysisHistoryEntry[]>([]);
const historyLoading = ref(false);
const historyError = ref<null | string>(null);
const historyInsightsLoading = ref(false);
const historyInsights = ref<
  Record<string, ProtocolStaticAnalysisDatabaseInsights>
>({});
const historyInsightSummaries = ref<Record<string, HistoryInsightSummary>>({});
const historyInsightErrors = ref<Record<string, string>>({});
const historyInsightDebug = ref<
  Record<
    string,
    {
      payload: FetchProtocolStaticAnalysisDatabaseInsightsPayload & {
        jobId: string;
      };
      responseData?: unknown;
      status?: number;
      statusText?: string;
    }
  >
>({});
const historyDetailVisible = ref(false);
const historyDetailJobId = ref<null | string>(null);

const hasHistory = computed(() => historyItems.value.length > 0);
const historyDetailRecord = computed(() => {
  if (!historyDetailJobId.value) {
    return null;
  }
  return (
    historyItems.value.find(
      (entry) => entry.jobId === historyDetailJobId.value,
    ) ?? null
  );
});
const historyDetailInsight = computed(() =>
  historyDetailJobId.value
    ? (historyInsights.value[historyDetailJobId.value] ?? null)
    : null,
);
const historyDetailError = computed(() => {
  if (!historyDetailJobId.value) {
    return null;
  }
  return historyInsightErrors.value[historyDetailJobId.value] ?? null;
});
const historyDetailDebug = computed(() => {
  if (!historyDetailJobId.value) {
    return null;
  }
  return historyInsightDebug.value[historyDetailJobId.value] ?? null;
});
const historyDetailTitle = computed(() => {
  const record = historyDetailRecord.value;
  if (!record) {
    return '规则检测详情';
  }
  const protocolSegments: string[] = [];
  if (record.protocolName) {
    protocolSegments.push(record.protocolName);
  }
  if (record.protocolVersion) {
    protocolSegments.push(record.protocolVersion);
  }
  const protocolLabel = protocolSegments.length
    ? protocolSegments.join(' · ')
    : '未知协议';
  return `规则检测详情｜${protocolLabel}`;
});

watch(historyDetailVisible, (visible) => {
  if (!visible) {
    historyDetailJobId.value = null;
  }
});

function resetHistoryInsights() {
  historyInsights.value = {};
  historyInsightSummaries.value = {};
  historyInsightErrors.value = {};
  historyInsightDebug.value = {};
}

function buildInsightSummary(
  insight: ProtocolStaticAnalysisDatabaseInsights,
): HistoryInsightSummary {
  const summary: HistoryInsightSummary = {
    noViolation: 0,
    total: insight.findings.length,
    unknown: 0,
    violation: 0,
  };
  insight.findings.forEach((finding) => {
    if (finding.result === 'violation_found') {
      summary.violation += 1;
      return;
    }
    if (finding.result === 'no_violation') {
      summary.noViolation += 1;
      return;
    }
    summary.unknown += 1;
  });
  return summary;
}

function resolveRuleResultMeta(status: unknown) {
  if (typeof status !== 'string') {
    return null;
  }
  return (
    RULE_RESULT_META[status as ProtocolStaticAnalysisRuleResultStatus] ?? null
  );
}

function formatDebugJson(source: unknown) {
  if (source === null || source === undefined) {
    return '';
  }
  if (typeof source === 'string') {
    return source;
  }
  try {
    return JSON.stringify(source, null, 2);
  } catch {
    return String(source);
  }
}

function resolveRequestErrorDetail(error: unknown) {
  const result: {
    message: string;
    responseData?: unknown;
    status?: number;
    statusText?: string;
  } = {
    message: '读取数据库内容失败',
  };
  if (!error || typeof error !== 'object') {
    return result;
  }
  const source = error as Record<string, unknown>;
  const response = source.response as Record<string, unknown> | undefined;
  const status = (response?.status ?? response?.code) as number | undefined;
  const statusText = response?.statusText as string | undefined;
  const responseData = response?.data;
  const rawMessage =
    (typeof source.message === 'string' && source.message) || undefined;
  const detailParts: string[] = [];
  if (typeof status === 'number') {
    detailParts.push(`HTTP ${status}`);
  }
  if (statusText) {
    detailParts.push(statusText);
  }
  const dataMessage =
    (responseData &&
      typeof responseData === 'object' &&
      ('error' in responseData
        ? String((responseData as Record<string, unknown>).error)
        : 'message' in responseData
          ? String((responseData as Record<string, unknown>).message)
          : null)) ||
    null;
  if (typeof dataMessage === 'string' && dataMessage) {
    detailParts.push(dataMessage);
  }
  if (!detailParts.length && rawMessage) {
    detailParts.push(rawMessage);
  }
  if (detailParts.length) {
    result.message = `请求失败：${detailParts.join(' / ')}`;
  }
  if (!detailParts.length && error instanceof Error && error.message) {
    result.message = error.message;
  }
  if (typeof status === 'number') {
    result.status = status;
  }
  if (statusText) {
    result.statusText = statusText;
  }
  if (responseData !== undefined) {
    result.responseData = responseData;
  }
  return result;
}

async function loadInsightsForHistory(
  entries: ProtocolStaticAnalysisHistoryEntry[],
  options: { silent?: boolean } = {},
) {
  resetHistoryInsights();
  if (!entries.length) {
    historyInsightsLoading.value = false;
    return;
  }
  const { silent = false } = options;
  historyInsightsLoading.value = true;
  try {
    for (const entry of entries) {
      // 跳过正在运行中、排队中或已失败的任务
      if (
        entry.status === 'running' ||
        entry.status === 'queued' ||
        entry.status === 'failed'
      ) {
        console.info(
          `[StaticAnalysis][History] 跳过状态为 ${entry.status} 的任务`,
          { jobId: entry.jobId },
        );
        continue;
      }

      const payload: FetchProtocolStaticAnalysisDatabaseInsightsPayload & {
        jobId: string;
      } = {
        databasePath: entry.databasePath ?? undefined,
        jobId: entry.jobId,
        workspacePath: entry.workspacePath ?? undefined,
      };
      const referencePath = entry.databasePath ?? entry.workspacePath ?? null;
      if (!referencePath) {
        historyInsightErrors.value[entry.jobId] = '缺少数据库路径';
        historyInsightDebug.value[entry.jobId] = {
          payload,
        };
        console.warn(
          '[StaticAnalysis][History] 跳过数据库解析，缺少路径',
          payload,
        );
        continue;
      }
      console.info('[StaticAnalysis][History] 请求数据库详情', payload);
      try {
        const insight =
          await fetchProtocolStaticAnalysisDatabaseInsights(payload);
        historyInsights.value[entry.jobId] = insight;
        historyInsightSummaries.value[entry.jobId] =
          buildInsightSummary(insight);
        historyInsightDebug.value[entry.jobId] = {
          payload,
        };
        console.info('[StaticAnalysis][History] 成功解析数据库详情', {
          jobId: entry.jobId,
          summary: historyInsightSummaries.value[entry.jobId],
        });
      } catch (error) {
        const messageText =
          error instanceof Error ? error.message : String(error ?? '');
        const detail = resolveRequestErrorDetail(error);
        historyInsightErrors.value[entry.jobId] =
          detail.message || messageText || '读取数据库内容失败';
        historyInsightDebug.value[entry.jobId] = {
          payload,
          responseData: detail.responseData,
          status: detail.status,
          statusText: detail.statusText,
        };
        console.error('[StaticAnalysis][History] 解析数据库详情失败', {
          jobId: entry.jobId,
          payload,
          error: detail,
        });
        if (!silent && !historyError.value) {
          historyError.value = '部分历史记录解析失败';
        }
      }
    }
  } finally {
    historyInsightsLoading.value = false;
  }
}

function openHistoryDetail(jobId: string) {
  historyDetailJobId.value = jobId;
  historyDetailVisible.value = true;
}

function resolveHistoryOverallStatus(
  record: ProtocolStaticAnalysisHistoryEntry | Record<string, unknown>,
) {
  const status = (record as ProtocolStaticAnalysisHistoryEntry).status;
  // 对于运行中、排队中或失败的任务，不显示整体判定
  if (status === 'running' || status === 'queued' || status === 'failed') {
    return null;
  }

  const summary = historyInsightSummaries.value[record.jobId as string];
  if (summary) {
    if (summary.violation > 0) {
      return 'non_compliant';
    }
    if (summary.unknown > 0) {
      return 'needs_review';
    }
    if (summary.total > 0) {
      return 'compliant';
    }
  }
  const original = (record as ProtocolStaticAnalysisHistoryEntry).overallStatus;
  return typeof original === 'string' && original ? original : null;
}

function resolveHistoryOverallLabel(
  record: ProtocolStaticAnalysisHistoryEntry | Record<string, unknown>,
) {
  const status = resolveHistoryOverallStatus(record);
  if (!status) {
    return null;
  }
  return STATUS_LABELS[status] ?? status;
}

async function loadHistory(options: { silent?: boolean } = {}) {
  if (historyLoading.value) {
    return;
  }
  const { silent = false } = options;
  historyLoading.value = true;
  historyError.value = null;
  resetHistoryInsights();
  try {
    const response = await fetchProtocolStaticAnalysisHistory({
      limit: HISTORY_DEFAULT_LIMIT,
    });
    const items = response.items ?? [];
    historyItems.value = items;
    await loadInsightsForHistory(items, { silent });
  } catch (error) {
    const messageText =
      error instanceof Error ? error.message : String(error ?? '');
    historyError.value = messageText || '加载历史记录失败';
    if (!silent) {
      message.error(`加载历史记录失败：${messageText}`);
    }
  } finally {
    historyLoading.value = false;
    if (
      historyDetailJobId.value &&
      !historyItems.value.find(
        (entry) => entry.jobId === historyDetailJobId.value,
      )
    ) {
      historyDetailVisible.value = false;
      historyDetailJobId.value = null;
    }
  }
}

async function handleRefreshHistory() {
  await loadHistory();
}

async function handleDeleteHistory(jobId: string) {
  try {
    await deleteProtocolStaticAnalysisJob(jobId);
    message.success('删除成功');
    await loadHistory({ silent: true });
  } catch (error) {
    const messageText =
      error instanceof Error ? error.message : String(error ?? '');
    message.error(`删除失败：${messageText}`);
  }
}

function resolveHistoryValue(
  record: ProtocolStaticAnalysisHistoryEntry | Record<string, unknown>,
  key: unknown,
) {
  if (typeof key !== 'string') {
    return '-';
  }
  const source = record as Record<string, unknown>;
  const candidate = source[key];
  if (candidate === undefined || candidate === null || candidate === '') {
    return '-';
  }
  return candidate;
}

function resolveJobStatusMeta(status: unknown) {
  if (typeof status !== 'string') {
    return null;
  }
  const key = status as ProtocolStaticAnalysisJob['status'];
  return PROGRESS_STATUS_META[key] ?? null;
}

const ANSI_STANDARD_COLORS = [
  '#000000', // black
  '#AA0000', // red
  '#00AA00', // green
  '#AA5500', // yellow/brown
  '#0000AA', // blue
  '#AA00AA', // magenta
  '#00AAAA', // cyan
  '#AAAAAA', // light gray
] as const;

const ANSI_BRIGHT_COLORS = [
  '#555555', // bright black (gray)
  '#FF5555', // bright red
  '#55FF55', // bright green
  '#FFFF55', // bright yellow
  '#5555FF', // bright blue
  '#FF55FF', // bright magenta
  '#55FFFF', // bright cyan
  '#FFFFFF', // bright white
] as const;

const ANSI_ESCAPE_PATTERN = /\u001B\[(\d{1,3}(?:;\d{1,3})*)m/g;

interface AnsiStyleState {
  color: null | string;
  backgroundColor: null | string;
  bold: boolean;
  italic: boolean;
  underline: boolean;
  strikethrough: boolean;
  dim: boolean;
  conceal: boolean;
}

const defaultAnsiStyleState: AnsiStyleState = {
  backgroundColor: null,
  bold: false,
  color: null,
  conceal: false,
  dim: false,
  italic: false,
  strikethrough: false,
  underline: false,
};

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function clampRgbComponent(value: number) {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, Math.min(255, Math.round(value)));
}

function toHexComponent(value: number) {
  return clampRgbComponent(value).toString(16).padStart(2, '0');
}

function rgbToHex(r: number, g: number, b: number) {
  return `#${toHexComponent(r)}${toHexComponent(g)}${toHexComponent(b)}`;
}

function ansi256ToHex(index: number): null | string {
  if (index >= 0 && index <= 7) {
    return ANSI_STANDARD_COLORS[index] ?? null;
  }
  if (index >= 8 && index <= 15) {
    return ANSI_BRIGHT_COLORS[index - 8] ?? null;
  }
  if (index >= 16 && index <= 231) {
    const base = index - 16;
    const r = Math.floor(base / 36);
    const g = Math.floor((base % 36) / 6);
    const b = base % 6;
    const resolve = (component: number) =>
      component === 0 ? 0 : component * 40 + 55;
    return rgbToHex(resolve(r), resolve(g), resolve(b));
  }
  if (index >= 232 && index <= 255) {
    const gray = 8 + (index - 232) * 10;
    return rgbToHex(gray, gray, gray);
  }
  return null;
}

function buildStyleString(state: AnsiStyleState) {
  const declarations: string[] = [];
  if (state.conceal) {
    declarations.push('color: transparent', 'text-shadow: none');
  } else if (state.color) {
    declarations.push(`color: ${state.color}`);
  }
  if (state.backgroundColor) {
    declarations.push(`background-color: ${state.backgroundColor}`);
  }
  if (state.bold) {
    declarations.push('font-weight: 600');
  }
  if (state.italic) {
    declarations.push('font-style: italic');
  }
  const decorations: string[] = [];
  if (state.underline) {
    decorations.push('underline');
  }
  if (state.strikethrough) {
    decorations.push('line-through');
  }
  if (decorations.length > 0) {
    declarations.push(`text-decoration: ${decorations.join(' ')}`);
  }
  if (state.dim) {
    declarations.push('opacity: 0.75');
  }
  return declarations.join('; ');
}

function hasAnsiStyle(state: AnsiStyleState) {
  return Boolean(
    state.conceal ||
      state.color ||
      state.backgroundColor ||
      state.bold ||
      state.italic ||
      state.underline ||
      state.strikethrough ||
      state.dim,
  );
}

function resetAnsiState(target: AnsiStyleState) {
  Object.assign(target, defaultAnsiStyleState);
}

function applyAnsiCodes(state: AnsiStyleState, codes: number[]) {
  if (codes.length === 0) {
    resetAnsiState(state);
    return;
  }
  for (let i = 0; i < codes.length; i += 1) {
    const codeRaw = codes[i];
    if (!Number.isFinite(codeRaw)) {
      continue;
    }
    const code = Number(codeRaw);
    switch (code) {
      case 0: {
        resetAnsiState(state);
        break;
      }
      case 1: {
        state.bold = true;
        state.dim = false;
        break;
      }
      case 2: {
        state.dim = true;
        state.bold = false;
        break;
      }
      case 3: {
        state.italic = true;
        break;
      }
      case 4:
      case 21: {
        state.underline = true;
        break;
      }
      case 5:
      case 6: {
        // Blink/rapid-blink -> ignore for now.
        break;
      }
      case 7: {
        // Inverse not supported; ignore.
        break;
      }
      case 8: {
        state.conceal = true;
        break;
      }
      case 9: {
        state.strikethrough = true;
        break;
      }
      case 22: {
        state.bold = false;
        state.dim = false;
        break;
      }
      case 23: {
        state.italic = false;
        break;
      }
      case 24: {
        state.underline = false;
        break;
      }
      case 27: {
        // Positive image (inverse off) – no-op for now.
        break;
      }
      case 28: {
        state.conceal = false;
        break;
      }
      case 29: {
        state.strikethrough = false;
        break;
      }
      case 39: {
        state.color = null;
        state.conceal = false;
        break;
      }
      case 49: {
        state.backgroundColor = null;
        break;
      }
      default: {
        if (code >= 30 && code <= 37) {
          state.color = ANSI_STANDARD_COLORS[code - 30] ?? null;
          state.conceal = false;
          break;
        }
        if (code >= 40 && code <= 47) {
          state.backgroundColor = ANSI_STANDARD_COLORS[code - 40] ?? null;
          break;
        }
        if (code >= 90 && code <= 97) {
          state.color = ANSI_BRIGHT_COLORS[code - 90] ?? null;
          state.conceal = false;
          break;
        }
        if (code >= 100 && code <= 107) {
          state.backgroundColor = ANSI_BRIGHT_COLORS[code - 100] ?? null;
          break;
        }
        if (code === 38 || code === 48) {
          const isForeground = code === 38;
          const mode = codes[i + 1];
          if (mode === 2 && codes.length >= i + 5) {
            const r = clampRgbComponent(Number(codes[i + 2]));
            const g = clampRgbComponent(Number(codes[i + 3]));
            const b = clampRgbComponent(Number(codes[i + 4]));
            const color = rgbToHex(r, g, b);
            if (isForeground) {
              state.color = color;
              state.conceal = false;
            } else {
              state.backgroundColor = color;
            }
            i += 4;
            break;
          }
          if (mode === 5 && codes.length >= i + 3) {
            const paletteIndex = Number(codes[i + 2]);
            const color = Number.isFinite(paletteIndex)
              ? ansi256ToHex(paletteIndex)
              : null;
            if (color) {
              if (isForeground) {
                state.color = color;
                state.conceal = false;
              } else {
                state.backgroundColor = color;
              }
            }
            i += 2;
            break;
          }
        }
        break;
      }
    }
  }
}

function ansiToHtml(raw: string) {
  if (!raw) {
    return '';
  }
  const normalized = raw
    .replaceAll('\r\n', '\n')
    .replaceAll('\r', '\n')
    // Remove non-SGR escape sequences (cursor movement, erase, etc.).
    .replaceAll(/\u001B\[[0-9;?]*[A-HJKSTfnisu]/g, '')
    // Remove OSC sequences.
    .replaceAll(/\u001B\][^\u0007]*(?:\u0007|\u001B\\)/g, '');

  let result = '';
  let lastIndex = 0;
  const state: AnsiStyleState = { ...defaultAnsiStyleState };
  let hasOpenSpan = false;

  const appendSegment = (segment: string) => {
    if (!segment) {
      return;
    }
    const escaped = escapeHtml(segment).replaceAll('\n', '<br/>');
    result += escaped;
  };

  let match: null | RegExpExecArray;
  while ((match = ANSI_ESCAPE_PATTERN.exec(normalized)) !== null) {
    appendSegment(normalized.slice(lastIndex, match.index));
    lastIndex = match.index + match[0].length;

    const codeText = match[1] ?? '';
    const codeParts = codeText
      .split(';')
      .map((value) => (value === '' ? 0 : Number(value)));
    applyAnsiCodes(state, codeParts);

    if (hasOpenSpan) {
      result += '</span>';
      hasOpenSpan = false;
    }
    if (hasAnsiStyle(state)) {
      result += `<span style="${buildStyleString(state)}">`;
      hasOpenSpan = true;
    }
  }

  appendSegment(normalized.slice(lastIndex));

  if (hasOpenSpan) {
    result += '</span>';
  }

  return result;
}

function formatIsoDate(value: null | string | undefined) {
  if (!value) {
    return '未知';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return formatter.format(parsed);
}

const analysisSummary = computed(
  () => analysisResult.value?.modelResponse.summary ?? null,
);
const analysisMetadata = computed(
  () => analysisResult.value?.modelResponse.metadata ?? null,
);
const analysisVerdictCount = computed(
  () => analysisResult.value?.modelResponse.verdicts.length ?? 0,
);

// 基于数据库 insights 计算真实的整体状态
const analysisRealOverallStatus = computed(() => {
  if (!activeJobId.value) {
    return analysisSummary.value?.overallStatus ?? null;
  }
  const insight = historyInsights.value[activeJobId.value];
  if (!insight) {
    return analysisSummary.value?.overallStatus ?? null;
  }
  const summary = historyInsightSummaries.value[activeJobId.value];
  if (!summary) {
    return analysisSummary.value?.overallStatus ?? null;
  }
  if (summary.violation > 0) {
    return 'non_compliant';
  }
  if (summary.unknown > 0) {
    return 'needs_review';
  }
  if (summary.total > 0) {
    return 'compliant';
  }
  return analysisSummary.value?.overallStatus ?? null;
});

// 基于数据库 insights 计算真实的统计数字
const analysisRealCounts = computed(() => {
  if (!activeJobId.value) {
    return {
      compliant: analysisSummary.value?.compliantCount ?? 0,
      needsReview: analysisSummary.value?.needsReviewCount ?? 0,
      nonCompliant: analysisSummary.value?.nonCompliantCount ?? 0,
    };
  }
  const summary = historyInsightSummaries.value[activeJobId.value];
  if (!summary) {
    return {
      compliant: analysisSummary.value?.compliantCount ?? 0,
      needsReview: analysisSummary.value?.needsReviewCount ?? 0,
      nonCompliant: analysisSummary.value?.nonCompliantCount ?? 0,
    };
  }
  return {
    compliant: summary.noViolation,
    needsReview: summary.unknown,
    nonCompliant: summary.violation,
  };
});

const analysisStatusLabel = computed(() => {
  const status = analysisRealOverallStatus.value ?? '';
  if (!status) {
    return '未知';
  }
  return STATUS_LABELS[status] ?? status;
});

const progressStatus = computed<null | ProtocolStaticAnalysisJob['status']>(
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

const progressHtml = computed(() => ansiToHtml(progressText.value));
const canCopyProgressLogs = computed(() => progressLogs.value.length > 0);

const progressTextRef = ref<HTMLDivElement>();

watch(progressText, () => {
  nextTick(() => {
    if (progressTextRef.value) {
      progressTextRef.value.scrollTop = progressTextRef.value.scrollHeight;
    }
  });
});

function toProgressLine(event: ProtocolStaticAnalysisProgressEvent) {
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

/**
 * Trim log array to enforce FIFO limit and facilitate garbage collection.
 * Returns a new array with only the most recent lines.
 */
function trimProgressLogs(logs: string[]): string[] {
  if (logs.length <= PROGRESS_LOGS_MAX_LINES) {
    return logs;
  }
  // Keep only the most recent PROGRESS_LOGS_MAX_LINES lines
  // Use slice to create a new array, allowing old references to be GC'd
  return logs.slice(-PROGRESS_LOGS_MAX_LINES);
}

function applyProgressSnapshot(snapshot: ProtocolStaticAnalysisJob) {
  activeJob.value = snapshot;
  activeJobId.value = snapshot.jobId;
  progressError.value = snapshot.error ?? null;

  // Map events to log lines
  const newLogs = snapshot.events?.length
    ? snapshot.events.map((event) => toProgressLine(event))
    : [];

  // Always append new logs (incremental updates only)
  if (newLogs.length > 0) {
    progressLogs.value = trimProgressLogs([...progressLogs.value, ...newLogs]);
  }

  // Track the last event ID for next incremental request
  if (snapshot.events?.length) {
    const lastEvent = snapshot.events.at(-1);
    if (lastEvent?.id !== undefined) {
      lastEventId.value = lastEvent.id;
    }
  }
}

function stopPolling() {
  if (pollingTimer.value !== null) {
    window.clearInterval(pollingTimer.value);
    pollingTimer.value = null;
  }
}

function resetProgressState() {
  stopPolling();
  activeJob.value = null;
  activeJobId.value = null;
  // Create new empty array to help garbage collection
  progressLogs.value = [];
  progressError.value = null;
  lastEventId.value = 0;
}

async function handleStatusTransition(
  previousStatus: null | ProtocolStaticAnalysisJob['status'],
  snapshot: ProtocolStaticAnalysisJob,
) {
  if (snapshot.status === 'completed') {
    stopPolling();
    isSubmitting.value = false;
    try {
      const result =
        snapshot.result ??
        (await fetchProtocolStaticAnalysisResult(snapshot.jobId));
      analysisResult.value = result;
      const overallStatus = result.modelResponse.summary.overallStatus;
      const label = STATUS_LABELS[overallStatus] ?? overallStatus ?? '完成';
      if (previousStatus !== 'completed') {
        message.success(`静态分析完成，整体评估：${label}`);
      }
    } catch (error) {
      const messageText =
        error instanceof Error ? error.message : String(error ?? '');
      progressError.value = messageText || '无法获取分析结果';
      if (previousStatus !== 'completed') {
        message.error(`获取静态分析结果失败：${messageText}`);
      }
    }
    await loadHistory({ silent: true });
    return;
  }

  if (snapshot.status === 'failed') {
    stopPolling();
    isSubmitting.value = false;
    analysisResult.value = null;
    const failure =
      snapshot.error ?? snapshot.message ?? '静态分析失败，请查看后台日志';
    if (previousStatus !== 'failed') {
      message.error(failure);
    }
    await loadHistory({ silent: true });
  }
}

async function refreshProgress(jobId: string) {
  const previousStatus = activeJob.value?.status ?? null;
  
  // Always use incremental updates (fromEventId)
  const snapshot = await fetchProtocolStaticAnalysisProgress(
    jobId,
    lastEventId.value,
  );
  
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
});

onMounted(() => {
  void loadHistory({ silent: true });
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

const handleBuilderBeforeUpload: UploadProps['beforeUpload'] = (file) => {
  const actual =
    (file as UploadFile<File>).originFileObj ?? (file as unknown as File);
  builderFileList.value = [file];
  formState.builder = actual;
  formRef.value?.clearValidate?.(['builder']);
  return false;
};

const handleBuilderRemove: UploadProps['onRemove'] = () => {
  builderFileList.value = [];
  formState.builder = null;
  formRef.value?.validateFields?.(['builder']);
  return true;
};

const handleConfigBeforeUpload: UploadProps['beforeUpload'] = (file) => {
  const actual =
    (file as UploadFile<File>).originFileObj ?? (file as unknown as File);
  configFileList.value = [file];
  formState.config = actual;
  formRef.value?.clearValidate?.(['config']);
  return false;
};

const handleConfigRemove: UploadProps['onRemove'] = () => {
  configFileList.value = [];
  formState.config = null;
  formRef.value?.validateFields?.(['config']);
  return true;
};

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

const handleRulesBeforeUpload: UploadProps['beforeUpload'] = (file) => {
  const actual =
    (file as UploadFile<File>).originFileObj ?? (file as unknown as File);
  rulesFileList.value = [file];
  formState.rules = actual;
  formRef.value?.clearValidate?.(['rules']);
  return false;
};

const handleRulesRemove: UploadProps['onRemove'] = () => {
  rulesFileList.value = [];
  formState.rules = null;
  formRef.value?.validateFields?.(['rules']);
  return true;
};

function handleReset() {
  formRef.value?.resetFields();
  archiveFileList.value = [];
  builderFileList.value = [];
  configFileList.value = [];
  rulesFileList.value = [];
  formState.archive = null;
  formState.builder = null;
  formState.config = null;
  formState.rules = null;
  formState.notes = '';
  analysisResult.value = null;
  resetProgressState();
}

async function handleSubmit() {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }

  const { archive, builder, config, rules } = formState;
  if (!archive || !builder || !config || !rules) {
    return;
  }

  resetProgressState();
  isSubmitting.value = true;
  analysisResult.value = null;
  try {
    const snapshot = await runProtocolStaticAnalysis({
      builderDockerfile: builder,
      codeArchive: archive,
      config,
      notes: formState.notes,
      rules,
    });
    applyProgressSnapshot(snapshot);
    await loadHistory({ silent: true });
    await handleStatusTransition(null, snapshot);
    if (snapshot.status === 'queued' || snapshot.status === 'running') {
      schedulePolling(snapshot.jobId);
    }
  } catch (error) {
    const messageText =
      error instanceof Error ? error.message : String(error ?? '');
    progressError.value = messageText || '静态分析启动失败';
    message.error(`启动静态分析失败：${messageText}`);
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
    title="协议静态分析"
  >
    <div class="static-analysis">
      <!-- 主工作区域 -->
      <div class="layout-grid">
        <Card class="upload-card" title="上传分析材料">
          <Form
            ref="formRef"
            :model="formState"
            :rules="formRules"
            class="compact-form"
            layout="vertical"
          >
            <div class="form-grid">
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

              <FormItem label="Builder Dockerfile" name="builder" required>
                <Upload
                  :before-upload="handleBuilderBeforeUpload"
                  :file-list="builderFileList"
                  :max-count="1"
                  :on-remove="handleBuilderRemove"
                >
                  <Button block type="dashed">
                    <IconifyIcon icon="ant-design:docker-outlined" class="mr-1" />
                    选择 Dockerfile
                  </Button>
                </Upload>
              </FormItem>

              <FormItem label="协议规则（JSON）" name="rules" required>
                <Upload
                  :before-upload="handleRulesBeforeUpload"
                  :file-list="rulesFileList"
                  :max-count="1"
                  :on-remove="handleRulesRemove"
                  accept=".json,.JSON,application/json,text/json"
                >
                  <Button block type="dashed">
                    <IconifyIcon icon="ant-design:file-text-outlined" class="mr-1" />
                    选择规则 JSON
                  </Button>
                </Upload>
              </FormItem>

              <FormItem label="分析配置（TOML）" name="config" required>
                <Upload
                  :before-upload="handleConfigBeforeUpload"
                  :file-list="configFileList"
                  :max-count="1"
                  :on-remove="handleConfigRemove"
                  accept=".toml,.TOML,text/toml,text/x-toml,application/toml,text/plain"
                >
                  <Button block type="dashed">
                    <IconifyIcon icon="ant-design:setting-outlined" class="mr-1" />
                    选择配置文件
                  </Button>
                </Upload>
              </FormItem>
            </div>

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
                    icon="ant-design:play-circle-outlined"
                    class="mr-1"
                  />
                  启动分析
                </Button>
              </Space>
            </FormItem>
          </Form>
        </Card>

        <Card class="progress-card" title="分析进度">
          <template #extra>
            <Button
              :disabled="!canCopyProgressLogs"
              size="small"
              type="link"
              @click="handleCopyProgressLogs"
            >
              <IconifyIcon icon="ant-design:copy-outlined" class="mr-1" />
              复制日志
            </Button>
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
              v-html="progressHtml"
            ></div>
            <p v-if="progressError" class="progress-error">
              {{ progressError }}
            </p>
          </div>
        </Card>
      </div>

      <Card v-if="analysisResult">
        <template #title>
          <Space>
            <IconifyIcon
              icon="ant-design:check-circle-outlined"
              class="text-lg"
            />
            <span>最新分析结果</span>
          </Space>
        </template>
        <Descriptions bordered :column="1" size="small">
          <Descriptions.Item label="整体评估">
            <div class="analysis-overview">
              <span
                class="status-tag"
                :class="[`status-${analysisRealOverallStatus ?? 'unknown'}`]"
              >
                {{ analysisStatusLabel }}
              </span>
              <span class="analysis-detail">
                合规 {{ analysisRealCounts.compliant }} · 需复核
                {{ analysisRealCounts.needsReview }} · 不合规
                {{ analysisRealCounts.nonCompliant }}
              </span>
            </div>
          </Descriptions.Item>
          <Descriptions.Item v-if="analysisMetadata" label="协议信息">
            {{ analysisMetadata.protocol }}
            {{ analysisMetadata.protocolVersion || '' }} ｜ 规则集：
            {{ analysisMetadata.ruleSet }}
          </Descriptions.Item>
          <Descriptions.Item label="生成时间">
            {{ formatIsoDate(analysisMetadata?.generatedAt) }}
          </Descriptions.Item>
          <Descriptions.Item label="判定条目">
            共 {{ analysisVerdictCount }} 条
          </Descriptions.Item>
        </Descriptions>
        <TypographyParagraph
          v-if="analysisSummary?.notes"
          class="preview-tip"
          type="secondary"
        >
          {{ analysisSummary?.notes }}
        </TypographyParagraph>
      </Card>

      <Drawer
        v-model:open="historyDetailVisible"
        :title="historyDetailTitle"
        :width="720"
        class="history-detail-drawer"
        destroy-on-close
        placement="right"
      >
        <template v-if="historyDetailRecord">
          <TypographyParagraph class="history-detail-meta" type="secondary">
            任务 ID：{{ historyDetailRecord?.jobId }}
          </TypographyParagraph>
          <TypographyParagraph
            v-if="
              historyDetailInsight?.workspacePath ||
              historyDetailRecord?.workspacePath
            "
            :ellipsis="{
              rows: 1,
              tooltip:
                historyDetailInsight?.workspacePath ||
                historyDetailRecord?.workspacePath,
            }"
            class="history-detail-meta"
            type="secondary"
          >
            工作目录：
            {{
              historyDetailInsight?.workspacePath ||
              historyDetailRecord?.workspacePath
            }}
          </TypographyParagraph>
          <TypographyParagraph
            v-if="historyDetailInsight?.databasePath"
            :ellipsis="{
              rows: 1,
              tooltip: historyDetailInsight?.databasePath,
            }"
            class="history-detail-meta"
            type="secondary"
          >
            数据库：{{ historyDetailInsight?.databasePath }}
          </TypographyParagraph>
          <TypographyParagraph
            v-if="historyDetailInsight?.extractedAt"
            class="history-detail-meta"
            type="secondary"
          >
            提取时间：{{ formatIsoDate(historyDetailInsight?.extractedAt) }}
          </TypographyParagraph>
          <TypographyParagraph
            v-if="historyDetailError"
            class="history-detail-error"
            type="danger"
          >
            {{ historyDetailError }}
          </TypographyParagraph>
          <TypographyParagraph
            v-if="historyDetailDebug?.status"
            class="history-detail-meta"
            type="secondary"
          >
            响应状态：HTTP {{ historyDetailDebug?.status }}
            {{ historyDetailDebug?.statusText || '' }}
          </TypographyParagraph>
          <pre v-if="historyDetailDebug?.payload" class="history-detail-debug"
            >{{ formatDebugJson(historyDetailDebug?.payload) }}
          </pre>
          <pre
            v-if="historyDetailDebug?.responseData"
            class="history-detail-debug"
            >{{ formatDebugJson(historyDetailDebug?.responseData) }}
          </pre>
          <TypographyParagraph
            v-if="historyDetailInsight?.warnings?.length"
            class="history-detail-warning"
            type="warning"
          >
            {{ historyDetailInsight?.warnings?.[0] }}
          </TypographyParagraph>
          <template v-if="historyDetailInsight?.findings?.length">
            <div
              v-for="(finding, index) in historyDetailInsight?.findings"
              :key="`${finding.ruleDesc}-${index}`"
              class="history-detail-item"
            >
              <div class="history-detail-header">
                <TypographyText class="history-detail-rule" strong>
                  {{ finding.ruleDesc }}
                </TypographyText>
                <Tag
                  :color="
                    resolveRuleResultMeta(finding.result)?.color ?? 'default'
                  "
                >
                  {{
                    resolveRuleResultMeta(finding.result)?.label ??
                    finding.resultLabel
                  }}
                </Tag>
              </div>
              <TypographyParagraph
                v-if="finding.reason"
                class="history-detail-reason"
              >
                {{ finding.reason }}
              </TypographyParagraph>
              <ul
                v-if="finding.violations?.length"
                class="history-detail-violations"
              >
                <li
                  v-for="(violation, violationIndex) in finding.violations"
                  :key="violationIndex"
                >
                  <span v-if="violation.filename">
                    {{ violation.filename }}
                  </span>
                  <span v-if="violation.functionName">
                    · {{ violation.functionName }}
                  </span>
                  <span v-if="violation.codeLines?.length">
                    · 行 {{ violation.codeLines.join(', ') }}
                  </span>
                </li>
              </ul>
              <div v-if="finding.codeSnippet" class="history-detail-snippet">
                <pre>{{ finding.codeSnippet }}</pre>
              </div>
              <div v-if="finding.llmRaw" class="history-detail-raw">
                <pre>{{ formatDebugJson(finding.llmRaw) }}</pre>
              </div>
              <Divider
                v-if="
                  historyDetailInsight?.findings &&
                  index < historyDetailInsight.findings.length - 1
                "
              />
            </div>
          </template>
          <template v-else-if="historyInsightsLoading">
            <TypographyParagraph type="secondary">
              正在从数据库解析规则详情...
            </TypographyParagraph>
          </template>
          <template v-else>
            <TypographyParagraph type="secondary">
              暂无可展示的数据。
            </TypographyParagraph>
          </template>
        </template>
        <template v-else>
          <TypographyParagraph type="secondary">
            请选择历史记录查看详情。
          </TypographyParagraph>
        </template>
      </Drawer>

      <!-- 历史记录区域 -->
      <Card class="history-card" title="历史记录">
        <template #extra>
          <Button
            :loading="historyLoading"
            size="small"
            type="link"
            @click="handleRefreshHistory"
          >
            <IconifyIcon
              v-if="!historyLoading"
              icon="ant-design:reload-outlined"
              class="mr-1"
            />
            刷新
          </Button>
        </template>
        <TypographyParagraph
          v-if="historyError && !historyLoading"
          class="history-error"
          type="danger"
        >
          {{ historyError }}
        </TypographyParagraph>
        <TypographyParagraph
          v-else-if="!historyLoading && !hasHistory"
          class="history-tip"
          type="secondary"
        >
          暂无历史记录，提交任务后会显示最近的运行记录。
        </TypographyParagraph>
        <TypographyParagraph v-else class="history-tip" type="secondary">
          历史数据取自任务工作区中的 SQLite 结果数据库，可查看各规则的判定摘要。
        </TypographyParagraph>
        <div class="history-table-wrapper">
          <Table
            :columns="historyColumns"
            :data-source="historyItems"
            :loading="historyLoading"
            :pagination="false"
            :scroll="{ x: 'max-content' }"
            class="history-table"
            row-key="jobId"
            size="small"
          >
            <template #emptyText>
              <span v-if="historyLoading">正在加载历史记录...</span>
              <span v-else-if="historyError">{{ historyError }}</span>
              <span v-else>暂无历史记录</span>
            </template>
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'codeFileName'">
                <TypographyParagraph
                  v-if="record.codeFileName"
                  :copyable="{ text: record.codeFileName }"
                  :ellipsis="{ rows: 1, tooltip: record.codeFileName }"
                  class="history-job"
                >
                  {{ record.codeFileName }}
                </TypographyParagraph>
                <div v-else class="history-job">
                  <TypographyParagraph
                    :copyable="{ text: record.jobId }"
                    :ellipsis="{ rows: 1, tooltip: record.jobId }"
                    class="history-job-fallback"
                  >
                    {{ record.jobId }}
                  </TypographyParagraph>
                  <TypographyParagraph
                    class="history-job-meta"
                    type="secondary"
                  >
                    (任务 ID)
                  </TypographyParagraph>
                </div>
              </template>
              <template v-else-if="column.key === 'status'">
                <Tag
                  :color="
                    resolveJobStatusMeta(record.status)?.color ?? 'default'
                  "
                >
                  {{
                    resolveJobStatusMeta(record.status)?.label ?? record.status
                  }}
                </Tag>
              </template>
              <template v-else-if="column.key === 'overallStatus'">
                <span
                  v-if="resolveHistoryOverallStatus(record)"
                  class="status-tag"
                  :class="[`status-${resolveHistoryOverallStatus(record)}`]"
                >
                  {{ resolveHistoryOverallLabel(record) }}
                </span>
                <span v-else>-</span>
              </template>
              <template v-else-if="column.key === 'protocol'">
                <span v-if="record.protocolName">
                  {{ record.protocolName }}
                  <template v-if="record.protocolVersion">
                    ({{ record.protocolVersion }})
                  </template>
                </span>
                <span v-else>-</span>
              </template>
              <template v-else-if="column.key === 'ruleInsights'">
                <div class="history-insight">
                  <template
                    v-if="
                      record.status === 'running' || record.status === 'queued'
                    "
                  >
                    <span class="history-insight-loading">
                      {{ record.status === 'running' ? '分析中…' : '排队中…' }}
                    </span>
                  </template>
                  <template v-else-if="record.status === 'failed'">
                    <span class="history-insight-loading"> 任务失败 </span>
                  </template>
                  <template v-else-if="historyInsightErrors[record.jobId]">
                    <TypographyParagraph
                      class="history-insight-error"
                      type="danger"
                    >
                      {{ historyInsightErrors[record.jobId] }}
                    </TypographyParagraph>
                    <TypographyParagraph
                      v-if="historyInsightDebug[record.jobId]?.status"
                      class="history-insight-meta"
                      type="secondary"
                    >
                      响应状态：HTTP
                      {{ historyInsightDebug[record.jobId]?.status }}
                      {{
                        historyInsightDebug[record.jobId]?.statusText
                          ? `(${historyInsightDebug[record.jobId]?.statusText})`
                          : ''
                      }}
                    </TypographyParagraph>
                    <TypographyParagraph
                      v-if="record.workspacePath"
                      class="history-insight-meta"
                      type="secondary"
                    >
                      工作目录：{{ record.workspacePath }}
                    </TypographyParagraph>
                    <pre
                      v-if="historyInsightDebug[record.jobId]?.payload"
                      class="history-insight-debug"
                      >{{
                        formatDebugJson(
                          historyInsightDebug[record.jobId]?.payload,
                        )
                      }}
                    </pre>
                    <pre
                      v-if="historyInsightDebug[record.jobId]?.responseData"
                      class="history-insight-debug"
                      >{{
                        formatDebugJson(
                          historyInsightDebug[record.jobId]?.responseData,
                        )
                      }}
                    </pre>
                  </template>
                  <template v-else-if="historyInsights[record.jobId]">
                    <div class="history-insight-summary">
                      <span class="history-insight-counts">
                        <span
                          class="history-insight-count history-insight-count--violation"
                        >
                          违规
                          {{
                            historyInsightSummaries[record.jobId]?.violation ??
                            0
                          }}
                        </span>
                        <span class="history-insight-count">
                          合规
                          {{
                            historyInsightSummaries[record.jobId]
                              ?.noViolation ?? 0
                          }}
                        </span>
                        <span class="history-insight-count">
                          未判定
                          {{
                            historyInsightSummaries[record.jobId]?.unknown ?? 0
                          }}
                        </span>
                      </span>
                      <Button
                        size="small"
                        type="link"
                        @click="openHistoryDetail(record.jobId)"
                      >
                        查看详情
                      </Button>
                    </div>
                    <TypographyParagraph
                      v-if="historyInsights[record.jobId]?.warnings?.length"
                      class="history-insight-warning"
                      type="warning"
                    >
                      {{ historyInsights[record.jobId]?.warnings?.[0] }}
                    </TypographyParagraph>
                    <TypographyParagraph
                      v-if="historyInsights[record.jobId]?.workspacePath"
                      class="history-insight-meta"
                      type="secondary"
                    >
                      工作目录：{{
                        historyInsights[record.jobId]?.workspacePath
                      }}
                    </TypographyParagraph>
                    <TypographyParagraph
                      v-else-if="record.workspacePath"
                      class="history-insight-meta"
                      type="secondary"
                    >
                      工作目录：{{ record.workspacePath }}
                    </TypographyParagraph>
                  </template>
                  <template v-else>
                    <span class="history-insight-loading">
                      {{ historyInsightsLoading ? '解析中…' : '暂无数据' }}
                    </span>
                  </template>
                </div>
              </template>
              <template v-else-if="column.key === 'updatedAt'">
                {{ formatIsoDate(record.completedAt ?? record.updatedAt) }}
              </template>
              <template v-else-if="column.key === 'actions'">
                <Popconfirm
                  cancel-text="取消"
                  ok-text="确定"
                  title="确定要删除这条历史记录吗？"
                  @confirm="handleDeleteHistory(record.jobId)"
                >
                  <Button danger size="small" type="link"> 删除 </Button>
                </Popconfirm>
              </template>
              <template v-else>
                {{ resolveHistoryValue(record, column.dataIndex) }}
              </template>
            </template>
          </Table>
        </div>
      </Card>
    </div>

  </Page>
</template>

<style scoped>
/* Scale Page title to 200% */
:deep(.mb-2.flex.text-lg.font-semibold) {
  font-size: 2rem;
}

.static-analysis {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.history-table-wrapper {
  max-height: 300px;
  overflow-y: auto;
  margin-top: 8px;
}

.history-job-meta {
  margin: 0;
  font-size: 12px;
}

.history-job-fallback {
  margin-bottom: 0;
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
  min-height: 600px;
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

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 16px;
}

.progress-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.progress-text {
  flex: 1;
  overflow-y: auto;
}

.progress-text {
  flex: 1;
  overflow-y: auto;
  min-height: 200px;
  max-height: 500px;
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

  .form-grid {
    grid-template-columns: 1fr;
  }

  .history-table-wrapper {
    max-height: 250px;
  }
}

.form-actions {
  margin-bottom: 0;
  margin-top: 8px;
}

.file-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-detail {
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.progress-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
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
  max-height: 500px;
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

.progress-text span {
  white-space: pre-wrap;
}

.progress-text br {
  line-height: inherit;
}

.progress-error {
  margin: 0;
  font-size: 12px;
  color: var(--ant-color-error);
}

.preview-tip {
  margin-top: 12px;
  margin-bottom: 0;
  font-size: 12px;
}

.analysis-overview {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.status-tag {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 999px;
}

.status-compliant {
  color: #52c41a;
  background-color: rgb(82 196 26 / 15%);
}

.status-needs_review {
  color: #fa8c16;
  background-color: rgb(250 140 22 / 15%);
}

.status-non_compliant {
  color: #f5222d;
  background-color: rgb(245 34 45 / 15%);
}

.status-unknown {
  color: #8c8c8c;
  background-color: rgb(140 140 140 / 15%);
}

.analysis-detail {
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}

.history-tip {
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.history-error {
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--ant-color-error);
}

.history-table {
  margin-top: 8px;
}

.history-insight {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.history-insight-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.history-insight-counts {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.history-insight-count {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}

.history-insight-count--violation {
  color: var(--ant-color-error);
}

.history-insight-loading {
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.history-insight-warning,
.history-insight-error {
  margin: 0;
  font-size: 12px;
}

.history-insight-meta {
  margin: 0;
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.history-insight-debug {
  margin: 4px 0;
  padding: 8px;
  overflow-x: auto;
  font-family:
    ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas,
    'Liberation Mono', 'Courier New', monospace;
  font-size: 11px;
  line-height: 1.5;
  color: var(--ant-text-color-secondary);
  background-color: var(--ant-color-bg-container);
  border: 1px dashed var(--ant-color-border);
  border-radius: var(--ant-border-radius-sm);
}

.history-detail-drawer .ant-drawer-body {
  padding-top: 12px;
}

.history-detail-meta {
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.history-detail-warning {
  margin-bottom: 16px;
  font-size: 12px;
}

.history-detail-error {
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--ant-color-error);
}

.history-detail-debug {
  margin: 8px 0;
  padding: 10px;
  overflow-x: auto;
  font-family:
    ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas,
    'Liberation Mono', 'Courier New', monospace;
  font-size: 11px;
  line-height: 1.5;
  color: var(--ant-text-color-secondary);
  background-color: var(--ant-color-bg-container);
  border: 1px dashed var(--ant-color-border);
  border-radius: var(--ant-border-radius-sm);
}

.history-detail-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.history-detail-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.history-detail-rule {
  flex: 1;
  min-width: 0;
}

.history-detail-reason {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
}

.history-detail-violations {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.history-detail-violations li {
  margin-bottom: 4px;
}

.history-detail-snippet {
  margin: 0;
}

.history-detail-snippet pre {
  margin: 0;
  padding: 12px;
  overflow-x: auto;
  font-family:
    ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas,
    'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.45;
  color: var(--ant-text-color);
  background-color: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border);
  border-radius: var(--ant-border-radius-sm);
}

.history-detail-raw {
  margin: 0;
}

.history-detail-raw pre {
  margin: 0;
  padding: 12px;
  overflow-x: auto;
  font-family:
    ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas,
    'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.45;
  color: var(--ant-text-color);
  background-color: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border);
  border-radius: var(--ant-border-radius-sm);
}

.history-job {
  margin-bottom: 0;
  font-family:
    ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas,
    'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
}

@media (max-width: 768px) {
  .guide-list {
    font-size: 12px;
  }
}

@media (min-width: 768px) {
  .analysis-overview {
    flex-direction: row;
    align-items: center;
  }
}
</style>

==================================================================================================== 文件 5: apps/web-antd/src/views/protocol-compliance/static/index.ts ====================================================================================================

<script lang="ts" setup>
import type { UploadFile, UploadProps } from 'ant-design-vue';

import { computed, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';

import {
  Button,
  Card,
  Divider,
  Empty,
  Form,
  FormItem,
  Input,
  message,
  Select,
  SelectOption,
  Space,
  Table,
  TabPane,
  Tabs,
  Tag,
  Upload,
} from 'ant-design-vue';

import {
  addAnalysisHistory,
  getAnalysisHistory,
  getDetectionResults,
} from '#/api/protocol-compliance';

// 类型定义
interface DetectionResult {
  id: number;
  rule_desc: string;
  code_snippet: string;
  llm_response: { reason: string; result: string };
}

interface HistoryRecord {
  id: string;
  implementationName: string;
  protocolName: string;
  statistics: {
    noResult: number;
    noViolations: number;
    total: number;
    violations: number;
  };
  createdAt: string;
}

// 路由与标题
const route = useRoute();
const title = computed(() => String(route.meta?.title ?? '静态规则分析'));

// 标签页状态
const activeTab = ref('input');

// 文件列表状态
const rulesFileList = ref<UploadFile[]>([]);
const sourceCodeFileList = ref<UploadFile[]>([]);

// 表单数据
const formData = reactive({
  protocolName: '',
  implementationName: '',
  rulesFile: null as File | null,
  sourceCodeFile: null as File | null,
  selectedModel: '',
});
const formLoading = ref(false);

// 检测结果状态
const detectionResults = ref<DetectionResult[]>([]);
const detectionLoading = ref(false);

// 历史记录状态
const historyRecords = ref<HistoryRecord[]>([]);
const historyLoading = ref(false);

// 上传文件控制
const beforeUploadRules: UploadProps['beforeUpload'] = (file) => {
  rulesFileList.value = [file];
  formData.rulesFile =
    (file as UploadFile<File>).originFileObj ?? (file as any as File);
  return false;
};
const removeRules: UploadProps['onRemove'] = () => {
  rulesFileList.value = [];
  formData.rulesFile = null;
  return true;
};

const beforeUploadSourceCode: UploadProps['beforeUpload'] = (file) => {
  sourceCodeFileList.value = [file];
  formData.sourceCodeFile =
    (file as UploadFile<File>).originFileObj ?? (file as any as File);
  return false;
};
const removeSourceCode: UploadProps['onRemove'] = () => {
  sourceCodeFileList.value = [];
  formData.sourceCodeFile = null;
  return true;
};

// 是否可以开始分析
const canStartAnalysis = computed(() => {
  return !!(
    formData.protocolName &&
    formData.implementationName &&
    formData.rulesFile &&
    formData.sourceCodeFile &&
    formData.selectedModel
  );
});

// 表格列定义
const detectionColumns = [
  { title: '序号', key: 'index', width: 60 },
  {
    title: '原始规则',
    dataIndex: 'rule_desc',
    key: 'rule_desc',
    width: '25%',
    ellipsis: true,
  },
  {
    title: '代码切片',
    dataIndex: 'code_snippet',
    key: 'code_snippet',
    width: '35%',
  },
  {
    title: '分析结果',
    dataIndex: 'llm_response',
    key: 'llm_response',
    width: '40%',
  },
];

const historyColumns = [
  { title: '序号', key: 'index', width: 60 },
  {
    title: '协议实现',
    dataIndex: 'implementationName',
    key: 'implementationName',
    width: '25%',
  },
  {
    title: '协议类型',
    dataIndex: 'protocolName',
    key: 'protocolName',
    width: '20%',
  },
  { title: '分析结果', key: 'statistics', width: '55%' },
];

// 开始分析
async function handleStartAnalysis() {
  if (!formData.protocolName || !formData.implementationName) {
    message.error('请填写协议名称和协议实现名称');
    return;
  }
  if (!formData.rulesFile || !formData.sourceCodeFile) {
    message.error('请上传规则文件和源代码文件');
    return;
  }
  if (!formData.selectedModel) {
    message.error('请选择大模型');
    return;
  }

  formLoading.value = true;
  try {
    message.loading('正在分析结果，请稍候...', 0);
    await new Promise((resolve) => setTimeout(resolve, 5000));
    message.destroy();

    const response = await getDetectionResults(formData.implementationName);
    detectionResults.value = response.items;

    await addAnalysisHistory({
      implementationName: formData.implementationName,
      protocolName: formData.protocolName,
    });

    activeTab.value = 'detection';
    message.success('分析完成');
  } catch (error: any) {
    message.destroy();
    message.error(error.message || '加载失败');
  } finally {
    formLoading.value = false;
  }
}

// 加载历史记录
async function loadHistory() {
  historyLoading.value = true;
  try {
    const response = await getAnalysisHistory();
    historyRecords.value = response.items;
  } catch {
    message.error('加载历史记录失败');
  } finally {
    historyLoading.value = false;
  }
}

// 查看历史记录详情
async function viewHistoryDetail(record: HistoryRecord) {
  formData.implementationName = record.implementationName;
  formData.protocolName = record.protocolName;
  detectionLoading.value = true;
  try {
    const response = await getDetectionResults(record.implementationName);
    detectionResults.value = response.items;
    activeTab.value = 'detection';
  } catch {
    message.error('加载失败');
  } finally {
    detectionLoading.value = false;
  }
}

// 结果状态颜色
function getResultColor(result: string): string {
  const lowerResult = result.toLowerCase();
  if (lowerResult.includes('no violation')) return 'green';
  if (lowerResult.includes('violation')) return 'red';
  return 'orange';
}

// 结果状态文本
function getResultText(result: string): string {
  const lowerResult = result.toLowerCase();
  if (lowerResult.includes('no violation')) return '✓ 符合规则';
  if (lowerResult.includes('violation')) return '✗ 违反规则';
  return '⚠ 需要审查';
}

// 标签页切换
function handleTabChange(key: string) {
  if (key === 'history') loadHistory();
}

// 检测结果统计
const detectionStatistics = computed(() => {
  const total = detectionResults.value.length;
  let violations = 0;
  let noViolations = 0;
  let noResult = 0;

  detectionResults.value.forEach((item) => {
    const res = item.llm_response.result.toLowerCase();
    if (res.includes('violation')) violations++;
    else if (res.includes('no violation')) noViolations++;
    else noResult++;
  });

  return { total, violations, noViolations, noResult };
});
</script>

<template>
  <div class="static-analysis-page">
    <div class="page-header">
      <h1>{{ title }}</h1>
      <p>协议合规性静态分析 - 上传文件并输入协议信息查看分析结果</p>
    </div>

    <Card>
      <Tabs v-model:active-key="activeTab" @change="handleTabChange">
        <!-- 输入标签页 -->
        <TabPane key="input" tab="输入协议信息">
          <Form
            :model="formData"
            layout="vertical"
            style="max-width: 800px; margin: 0 auto"
          >
            <!-- 协议+规则 -->
            <div style="display: flex; flex-wrap: wrap; gap: 16px">
              <FormItem label="协议名称" style="flex: 1">
                <Input
                  v-model:value="formData.protocolName"
                  placeholder="输入协议名称"
                  list="protocol-options"
                />
                <datalist id="protocol-options">
                  <option value="CoAP"></option>
                  <option value="DHCPv6"></option>
                  <option value="MQTTv3_1_1"></option>
                  <option value="MQTTv5"></option>
                  <option value="TLSv1_3"></option>
                  <option value="FTP"></option>
                </datalist>
              </FormItem>

              <FormItem label="规则文件" style="flex: 1">
                <Upload
                  :file-list="rulesFileList"
                  :before-upload="beforeUploadRules"
                  :on-remove="removeRules"
                  :max-count="1"
                >
                  <Button block>选择规则文件</Button>
                </Upload>
              </FormItem>
            </div>

            <!-- 协议实现+源代码 -->
            <div
              style="
                display: flex;
                flex-wrap: wrap;
                gap: 16px;
                margin-top: 16px;
              "
            >
              <FormItem label="协议实现名称" style="flex: 1">
                <Input
                  v-model:value="formData.implementationName"
                  placeholder="输入协议实现名称"
                />
              </FormItem>

              <FormItem label="协议源代码实现" style="flex: 1">
                <Upload
                  :file-list="sourceCodeFileList"
                  :before-upload="beforeUploadSourceCode"
                  :on-remove="removeSourceCode"
                  :max-count="1"
                >
                  <Button block>选择源代码文件</Button>
                </Upload>
              </FormItem>
            </div>

            <!-- 大模型选择 -->
            <div
              style="
                display: flex;
                flex-wrap: wrap;
                gap: 16px;
                margin-top: 16px;
              "
            >
              <FormItem label="选择大模型" style="flex: 1">
                <Select
                  v-model:value="formData.selectedModel"
                  placeholder="请选择大模型"
                >
                  <SelectOption value="GPT-4-32k">GPT-4 32k</SelectOption>
                  <SelectOption value="GPT-4-0613">GPT-4 0613</SelectOption>
                  <SelectOption value="GPT-3.5-turbo">
                    GPT-3.5 Turbo
                  </SelectOption>
                  <SelectOption value="Claude-2">Claude 2</SelectOption>
                  <SelectOption value="LLaMA-2-13B">LLaMA 2 13B</SelectOption>
                  <SelectOption value="MPT-7B">MPT-7B</SelectOption>
                  <SelectOption value="Gemini-1">Gemini 1</SelectOption>
                  <SelectOption value="PaLM-2">PaLM 2</SelectOption>
                  <SelectOption value="Falcon-40B">Falcon 40B</SelectOption>
                  <SelectOption value="Vicuna-13B">Vicuna 13B</SelectOption>
                </Select>
              </FormItem>
            </div>

            <FormItem style="margin-top: 24px">
              <Button
                type="primary"
                :loading="formLoading"
                :disabled="!canStartAnalysis"
                @click="handleStartAnalysis"
                block
              >
                开始分析
              </Button>
            </FormItem>
          </Form>
        </TabPane>

        <!-- 检测结果标签页 -->
        <TabPane key="detection" tab="代码切片与检测">
          <div v-if="detectionResults.length === 0">
            <Empty description="暂无检测结果,请先输入协议信息" />
          </div>

          <div v-else>
            <!-- 统计信息 -->
            <div style="margin-bottom: 16px">
              <Space>
                <span>总数: {{ detectionStatistics.total }}</span>
                <Tag color="red">
                  违规: {{ detectionStatistics.violations }}
                </Tag>
                <Tag color="green">
                  符合: {{ detectionStatistics.noViolations }}
                </Tag>
                <Tag color="orange">
                  待定: {{ detectionStatistics.noResult }}
                </Tag>
              </Space>
            </div>

            <!-- 表格 -->
            <Table
              :columns="detectionColumns"
              :data-source="detectionResults"
              :loading="detectionLoading"
              :pagination="{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条记录`,
              }"
              :scroll="{ x: 1200 }"
            >
              <template #bodyCell="{ column, record, index }">
                <template v-if="column.key === 'index'">
                  {{ index + 1 }}
                </template>
                <template v-else-if="column.key === 'code_snippet'">
                  <pre class="code-snippet">{{ record.code_snippet }}</pre>
                </template>
                <template v-else-if="column.key === 'llm_response'">
                  <div class="analysis-result">
                    <Tag :color="getResultColor(record.llm_response.result)">
                      {{ getResultText(record.llm_response.result) }}
                    </Tag>
                    <Divider style="margin: 8px 0" />
                    <div class="reason-text">
                      <strong>详细说明:</strong>
                      <p>{{ record.llm_response.reason }}</p>
                    </div>
                  </div>
                </template>
              </template>
            </Table>
          </div>
        </TabPane>

        <!-- 历史记录标签页 -->
        <TabPane key="history" tab="历史记录">
          <Table
            :columns="historyColumns"
            :data-source="historyRecords"
            :loading="historyLoading"
            :pagination="{
              pageSize: 10,
              showTotal: (total) => `共 ${total} 条记录`,
            }"
          >
            <template #bodyCell="{ column, record, index }">
              <template v-if="column.key === 'index'">
                {{ index + 1 }}
              </template>
              <template v-else-if="column.key === 'implementationName'">
                <a @click="viewHistoryDetail(record)">{{
                  record.implementationName
                }}</a>
              </template>
              <template v-else-if="column.key === 'statistics'">
                <Space>
                  <span>总数: {{ record.statistics.total }}</span>
                  <Tag color="red">
                    违规: {{ record.statistics.violations }}
                  </Tag>
                  <Tag color="green">
                    符合: {{ record.statistics.noViolations }}
                  </Tag>
                  <Tag color="orange">
                    待定: {{ record.statistics.noResult }}
                  </Tag>
                </Space>
              </template>
            </template>
          </Table>
        </TabPane>
      </Tabs>
    </Card>

  </div>
</template>

<style scoped>
.static-analysis-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.page-header p {
  margin: 8px 0 0;
  color: rgb(0 0 0 / 65%);
}

.code-snippet {
  max-height: 200px;
  padding: 8px;
  margin: 0;
  overflow-y: auto;
  font-family: 'Fira Code', Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  word-break: break-all;
  white-space: pre-wrap;
  background: #f5f5f5;
  border-radius: 4px;
}

.analysis-result {
  padding: 8px 0;
}

.reason-text {
  margin-top: 8px;
}

.reason-text p {
  margin: 4px 0;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}
</style>

==================================================================================================== 文件 6: apps/web-antd/src/views/protocol-compliance/assert/index.vue ====================================================================================================

<script lang="ts" setup>
import type { FormInstance, UploadFile, UploadProps } from 'ant-design-vue';
import type { Rule } from 'ant-design-vue/es/form';

import type {
  ProtocolAssertGenerationJob,
  ProtocolAssertGenerationProgressEvent,
  ProtocolAssertGenerationResult,
  ProtocolDiffParsingJob,
  ProtocolDiffParsingResult,
  ProtocolInstrumentationDiffResponse,
  ProtocolAssertionHistoryEntry,
} from '#/api/protocol-compliance';

import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import '@git-diff-view/vue/styles/diff-view.css';
import { DiffView, DiffModeEnum } from '@git-diff-view/vue';

import {
  Alert,
  Button,
  Card,
  Collapse,
  Drawer,
  Descriptions,
  Empty,
  Form,
  FormItem,
  Input,
  message,
  List,
  Progress,
  Result,
  Skeleton,
  Space,
  Tag,
  Tooltip,
  Typography,
  Upload,
  ListItem,
  ListItemMeta,
} from 'ant-design-vue';

import {
  fetchProtocolAssertGenerationProgress,
  fetchProtocolAssertGenerationResult,
  fetchProtocolInstrumentationDiff,
  runProtocolAssertGeneration,
  downloadProtocolAssertGenerationResult,
  fetchProtocolAssertionHistory,
  downloadProtocolAssertionDiff,
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

// Instrumentation diff state
const instrumentationDiff = ref<null | ProtocolInstrumentationDiffResponse>(null);
const instrumentationDiffLoading = ref(false);
const instrumentationDiffError = ref<null | string>(null);

// Assertion history
const assertionHistory = ref<ProtocolAssertionHistoryEntry[]>([]);
const assertionHistoryLoading = ref(false);
const assertionHistoryError = ref<null | string>(null);
const historyDrawerOpen = ref(false);
const historyActiveEntry = ref<ProtocolAssertionHistoryEntry | null>(null);
const historyDiffContent = ref<string | null>(null);
const historyDiffLoading = ref(false);
const historyDiffError = ref<null | string>(null);

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

const instrumentationResult = computed(
  () => analysisResult.value?.instrumentation ?? null,
);

const canRequestInstrumentationDiff = computed(
  () => progressStatus.value === 'completed' && !!activeJobId.value,
);

const instrumentationDiffStatusLabel = computed(() => {
  if (!instrumentationResult.value) {
    return '未执行';
  }
  if (instrumentationDiff.value?.content) {
    return '已加载';
  }
  if (instrumentationDiff.value?.available) {
    return '可下载';
  }
  return '待生成';
});

const instrumentationDiffStatusColor = computed(() => {
  if (!instrumentationResult.value) {
    return 'default';
  }
  if (instrumentationDiff.value?.content) {
    return 'success';
  }
  if (instrumentationDiff.value?.available) {
    return 'processing';
  }
  return 'default';
});

const instrumentationDiffFilename = computed(() => {
  const path = instrumentationDiff.value?.path;
  if (!path) {
    return 'instrumentation.diff';
  }
  const segments = path.split('/').filter(Boolean);
  return segments.length ? segments[segments.length - 1] : path;
});

const instrumentationDiffSizeLabel = computed(() => {
  const size = instrumentationDiff.value?.size;
  if (!size || Number.isNaN(size)) {
    return null;
  }
  return formatBytes(size);
});

const instrumentationDiffViewData = computed(() => {
  const diffContent = instrumentationDiff.value?.content;
  if (!diffContent) {
    return null;
  }
  const trimmed = extractUnifiedDiffBody(diffContent);
  if (!trimmed) {
    return null;
  }
  const label = instrumentationDiffFilename.value;
  return {
    oldFile: {
      fileName: label,
    },
    newFile: {
      fileName: label,
    },
    hunks: [trimmed],
  };
});

// Transform diff data for @git-diff-view/vue
const transformedDiffFiles = computed(() => {
  if (!diffResult.value) return [];

  return diffResult.value.files.map((file) => {
    // Build a complete unified diff string for each file
    const fileHeader = `--- ${file.from}\n+++ ${file.to}`;

    const hunksText = file.hunks
      .map((hunk) => {
        const header = `@@ -${hunk.oldStart},${hunk.oldLines} +${hunk.newStart},${hunk.newLines} @@`;
        const lines = hunk.lines.map((line) => {
          const prefix =
            line.type === 'add' ? '+' : line.type === 'delete' ? '-' : ' ';
          return prefix + line.content;
        });
        return [header, ...lines].join('\n');
      })
      .join('\n');

    const completeDiff = `${fileHeader}\n${hunksText}`;

    return {
      oldFile: {
        fileName: file.from,
      },
      newFile: {
        fileName: file.to,
      },
      hunks: [completeDiff.trim()],
    };
  });
});

function formatDateTime(input?: string | null) {
  if (!input) return '';
  try {
    return new Date(input).toLocaleString();
  } catch {
    return input;
  }
}

function formatBytes(input: number, fractionDigits = 1) {
  if (!Number.isFinite(input) || input <= 0) {
    return `${input || 0} B`;
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const base = Math.floor(Math.log(input) / Math.log(1024));
  const unit = units[Math.min(base, units.length - 1)];
  const value = input / 1024 ** Math.min(base, units.length - 1);
  return `${value.toFixed(fractionDigits)} ${unit}`;
}

function blobToText(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}

function extractUnifiedDiffBody(diffText: string): string | null {
  const normalized = diffText.replace(/\r\n/g, '\n');
  const lines = normalized.split('\n');
  const startIndex = lines.findIndex((line) => {
    const trimmed = line.trimStart();
    return (
      trimmed.startsWith('diff --git') ||
      trimmed.startsWith('--- ') ||
      trimmed.startsWith('+++ ') ||
      trimmed.startsWith('@@ ')
    );
  });

  const diffLines = startIndex >= 0 ? lines.slice(startIndex) : lines;
  const body = diffLines.join('\n').trim();
  return body.length ? body : null;
}

function buildDiffViewDataList(diffText: string) {
  const normalized = diffText.replace(/\r\n/g, '\n');
  const lines = normalized.split('\n');
  const files: Array<{ header: string; body: string[] }> = [];

  let current: string[] = [];
  for (const line of lines) {
    if (line.startsWith('diff --git ')) {
      if (current.length > 0) {
        files.push({ header: current[0] || '', body: current.slice(1) });
      }
      current = [line];
    } else {
      current.push(line);
    }
  }
  if (current.length > 0) {
    files.push({ header: current[0] || '', body: current.slice(1) });
  }

  const fallBack = extractUnifiedDiffBody(diffText);
  if (!files.length && fallBack) {
    const label = 'instrumentation.diff';
    return [
      {
        oldFile: { fileName: label },
        newFile: { fileName: label },
        hunks: [fallBack],
      },
    ];
  }

  return files
    .map((entry, index) => {
      const headerParts = entry.header.split(' ');
      const oldName = headerParts[2]?.replace(/^a\//, '') || `file-${index}`;
      const newName = headerParts[3]?.replace(/^b\//, '') || oldName;
      const section = [entry.header, ...entry.body].join('\n').trim();
      const body = extractUnifiedDiffBody(section);
      if (!body) {
        return null;
      }
      return {
        oldFile: { fileName: oldName || newName },
        newFile: { fileName: newName || oldName },
        hunks: [body],
      };
    })
    .filter(Boolean);
}

const progressTextRef = ref<HTMLDivElement>();

watch(progressText, () => {
  nextTick(() => {
    if (progressTextRef.value) {
      progressTextRef.value.scrollTop = progressTextRef.value.scrollHeight;
    }
  });
});

watch(
  () => analysisResult.value?.instrumentation?.artifacts?.diffOutput,
  (diffOutput) => {
    if (!diffOutput) {
      instrumentationDiff.value = null;
      instrumentationDiffError.value = null;
      return;
    }
    instrumentationDiff.value = diffOutput;
    instrumentationDiffError.value = null;
  },
  { immediate: true },
);

watch(
  () => progressStatus.value,
  (status, previous) => {
    if (status === 'completed' && previous !== 'completed') {
      loadAssertionHistory(300);
    }
  },
);

onMounted(() => {
  loadAssertionHistory();
});

const historyDiffViewData = computed(() => {
  if (!historyDiffContent.value) {
    return null;
  }
  const list = buildDiffViewDataList(historyDiffContent.value);
  return list && list.length ? list : null;
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

async function handleFetchInstrumentationDiff() {
  if (!activeJobId.value) {
    return;
  }
  instrumentationDiffLoading.value = true;
  instrumentationDiffError.value = null;
  try {
    const diffPayload = await fetchProtocolInstrumentationDiff(
      activeJobId.value,
    );
    instrumentationDiff.value = diffPayload;
    if (!diffPayload?.content) {
      instrumentationDiffError.value = '后端未返回 diff 内容';
    } else {
      message.success('已获取最新 Instrumentation diff');
    }
  } catch (error) {
    const messageText =
      error instanceof Error ? error.message : String(error ?? '');
    instrumentationDiffError.value = messageText || '无法获取 diff 文件';
    message.error(`获取 Instrumentation diff 失败：${messageText}`);
  } finally {
    instrumentationDiffLoading.value = false;
  }
}

async function loadAssertionHistory(delay = 0) {
  assertionHistoryLoading.value = true;
  assertionHistoryError.value = null;
  try {
    if (delay) {
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
    const response = await fetchProtocolAssertionHistory(20);
    assertionHistory.value = response.items ?? [];
  } catch (error) {
    const messageText =
      error instanceof Error ? error.message : String(error ?? '');
    assertionHistoryError.value = messageText || '无法加载历史记录';
  } finally {
    assertionHistoryLoading.value = false;
  }
}

async function openHistoryEntry(record: ProtocolAssertionHistoryEntry) {
  historyActiveEntry.value = record;
  historyDrawerOpen.value = true;
  historyDiffContent.value = null;
  historyDiffError.value = null;
  if (!record?.jobId) {
    historyDiffError.value = '缺少任务标识';
    return;
  }
  historyDiffLoading.value = true;
  try {
    const blob = await downloadProtocolAssertionDiff(record.jobId);
    const text = await blobToText(blob);
    historyDiffContent.value = text || null;
    if (!text) {
      historyDiffError.value = 'Diff 文件为空或无法解析';
    }
  } catch (error) {
    const messageText =
      error instanceof Error ? error.message : String(error ?? '');
    historyDiffError.value = messageText || '无法加载 Diff 内容';
  } finally {
    historyDiffLoading.value = false;
  }
}

function closeHistoryDrawer() {
  historyDrawerOpen.value = false;
  historyActiveEntry.value = null;
  historyDiffContent.value = null;
  historyDiffError.value = null;
}

async function handleDownloadHistoryDiff(jobId: string, fallbackName?: string) {
  try {
    const blob = await downloadProtocolAssertionDiff(jobId);
    const filename = fallbackName || `${jobId}.diff`;
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    const messageText =
      error instanceof Error ? error.message : String(error ?? '');
    message.error(`下载 Diff 失败：${messageText}`);
  }
}

function resetProgressState() {
  stopPolling();
  activeJob.value = null;
  activeJobId.value = null;
  progressLogs.value = [];
  progressError.value = null;
  resetInstrumentationDiffState();
}

function resetDiffProgressState() {
  stopDiffPolling();
  activeDiffJob.value = null;
  activeDiffJobId.value = null;
  diffResult.value = null;
  diffProgressLogs.value = [];
  diffProgressError.value = null;
}

function resetInstrumentationDiffState() {
  instrumentationDiff.value = null;
  instrumentationDiffError.value = null;
  instrumentationDiffLoading.value = false;
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
    resetInstrumentationDiffState();
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

        <Card class="history-card" title="生成历史">
          <template #extra>
            <Space>
              <Button
                :loading="assertionHistoryLoading"
                size="small"
                type="link"
                @click="loadAssertionHistory"
              >
                <IconifyIcon icon="ant-design:reload-outlined" class="mr-1" />
                刷新
              </Button>
            </Space>
          </template>
          <Alert
            v-if="assertionHistoryError"
            class="mb-3"
            show-icon
            type="error"
            :message="assertionHistoryError"
          />
          <template v-if="assertionHistoryLoading">
            <Skeleton active :paragraph="{ rows: 4 }" />
          </template>
          <template v-else-if="!assertionHistory.length">
            <Result
              class="history-empty"
              :icon="() => null"
              sub-title="暂无历史记录"
              title=" "
            />
          </template>
          <List
            v-else
            class="history-list"
            item-layout="horizontal"
            :data-source="assertionHistory"
          >
            <template #renderItem="{ item }">
              <ListItem
                class="history-list-item"
                @click="openHistoryEntry(item)"
              >
                <ListItemMeta>
                  <template #title>
                    <Typography.Text strong>
                      {{ item.diffFilename || item.diffPath || 'Diff 文件' }}
                    </Typography.Text>
                  </template>
                  <template #description>
                    <Space split="·" wrap>
                      <span>{{ item.codeFilename || '未记录源代码包' }}</span>
                      <span>{{ formatDateTime(item.createdAt) || '未知时间' }}</span>
                    </Space>
                  </template>
                </ListItemMeta>
                <div class="history-actions">
                  <Button
                    :disabled="!item.jobId"
                    size="small"
                    type="text"
                    @click.stop="handleDownloadHistoryDiff(item.jobId, item.diffFilename)"
                  >
                    下载
                  </Button>
                </div>
              </ListItem>
            </template>
          </List>
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

      <Card
        v-if="analysisResult"
        class="instrumentation-card"
      >
        <template #title>
          <Space>
            <IconifyIcon icon="ant-design:diff-outlined" class="text-lg" />
            <span>Instrumentation 变更</span>
          </Space>
        </template>
        <template #extra>
          <Space>
            <Tag :color="instrumentationDiffStatusColor">
              {{ instrumentationDiffStatusLabel }}
            </Tag>
            <Button
              :disabled="!canRequestInstrumentationDiff"
              :loading="instrumentationDiffLoading"
              size="small"
              type="link"
              @click="handleFetchInstrumentationDiff"
            >
              <IconifyIcon icon="ant-design:reload-outlined" class="mr-1" />
              获取最新 Diff
            </Button>
          </Space>
        </template>
        <div class="instrumentation-meta">
          <Space direction="vertical" size="small">
            <Typography.Text type="secondary">
              完成时间：{{ instrumentationResult?.completedAt || '未知' }}
            </Typography.Text>
            <Typography.Text>
              <span>文件： </span>
              <Typography.Text code>
                {{ instrumentationDiff?.path || 'instrumentation.diff' }}
              </Typography.Text>
              <span v-if="instrumentationDiffSizeLabel" class="ml-2 text-xs">
                ({{ instrumentationDiffSizeLabel }})
              </span>
            </Typography.Text>
            <Typography.Text
              v-if="instrumentationDiff?.truncated"
              type="warning"
            >
              Diff 内容较大，当前展示已截断
            </Typography.Text>
          </Space>
        </div>
        <Alert
          v-if="instrumentationDiffError"
          class="mb-3"
          show-icon
          type="error"
          :message="instrumentationDiffError"
        />
        <div class="instrumentation-diff-wrapper">
          <div
            v-if="instrumentationDiffLoading"
            class="instrumentation-diff-placeholder"
          >
            正在拉取 diff 内容...
          </div>
          <div
            v-else-if="instrumentationDiffViewData"
            class="instrumentation-diff-view"
          >
            <DiffView
              :data="instrumentationDiffViewData"
              :diff-view-mode="DiffModeEnum.Unified"
              :diff-view-highlight="true"
              :diff-view-theme="'light'"
              :diff-view-font-size="13"
            />
          </div>
          <Empty
            v-else
            description="暂未获取 Instrumentation diff"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
          />
        </div>
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
            :stroke-width="4"
            stroke-color="#1890ff"
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

            <div class="diff-viewer-container">
              <DiffView
                :data="transformedDiffFiles[fileIndex]"
                :diff-view-mode="DiffModeEnum.Unified"
                :diff-view-highlight="true"
                :diff-view-theme="'light'"
                :diff-view-font-size="13"
              />
            </div>
          </Collapse.Panel>
        </Collapse>
      </Card>
    </div>

    <Drawer
      v-model:open="historyDrawerOpen"
      :width="860"
      class="history-detail-drawer"
      destroy-on-close
      placement="right"
      @close="closeHistoryDrawer"
    >
      <template #title>
        <Space>
          <IconifyIcon icon="ant-design:diff-outlined" class="text-lg" />
          <span>历史记录详情</span>
        </Space>
      </template>
      <template v-if="historyActiveEntry">
        <div class="history-detail-meta">
          <Typography.Text type="secondary">
            源码包：{{ historyActiveEntry.codeFilename || '未记录' }}
          </Typography.Text>
          <Typography.Text type="secondary">
            时间：{{ formatDateTime(historyActiveEntry.createdAt) || '未知' }}
          </Typography.Text>
        </div>
        <div class="history-detail-actions">
          <Button
            :disabled="!historyActiveEntry.jobId"
            size="small"
            type="link"
            @click="handleDownloadHistoryDiff(historyActiveEntry.jobId!, historyActiveEntry.diffFilename)"
          >
            下载 Diff
          </Button>
        </div>
        <Alert
          v-if="historyDiffError"
          class="mb-3"
          show-icon
          type="error"
          :message="historyDiffError"
        />
        <div class="history-detail-diff">
          <div v-if="historyDiffLoading" class="instrumentation-diff-placeholder">
            正在加载历史 Diff ...
          </div>
          <div v-else-if="historyDiffViewData?.length" class="instrumentation-diff-view">
            <DiffView
              v-for="(diff, idx) in historyDiffViewData"
              :key="idx"
              :data="diff"
              :diff-view-mode="DiffModeEnum.Unified"
              :diff-view-highlight="true"
              :diff-view-theme="'light'"
              :diff-view-font-size="13"
              class="mb-4"
            />
          </div>
          <Empty
            v-else
            description="未获取到 Diff 内容"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
          />
        </div>
      </template>
      <template v-else>
        <Result sub-title="请选择一条历史记录查看详情" title=" " />
      </template>
    </Drawer>

  </Page>
</template>

<style scoped>
/* Scale Page title to 200% */
:deep(.mb-2.flex.text-lg.font-semibold) {
  font-size: 2rem;
}

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

.history-card {
  grid-column: 1 / -1;
}

.history-list {
  margin-top: 8px;
}

.history-list-item {
  cursor: pointer;
  transition: background-color 0.2s ease;
  padding: 12px 0;
}

.history-list-item:hover {
  background-color: var(--ant-color-fill-secondary);
}

.history-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-empty {
  padding: 16px 0;
}

.history-detail-drawer :deep(.ant-drawer-body) {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-detail-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.history-detail-actions {
  display: flex;
  justify-content: flex-start;
  gap: 8px;
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
  display: flex;
  flex-direction: column;
  overflow: visible;
  /* Ensure the content doesn't visually collide with the card header */
  margin-top: 16px;
  /* Provide consistent spacing between the status row and the log area */
  gap: 16px;
}

.progress-status {
  /* Use block-level flex so subsequent sections always render beneath it */
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 13px;
  /* Spacing is handled by parent gap; avoid double-spacing here */
  margin-bottom: 0;
  flex-shrink: 0;
}

.progress-message {
  color: var(--ant-text-color-secondary);
}

.progress-text {
  overflow-y: auto;
  height: 300px;
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

.instrumentation-card {
  margin-top: 8px;
}

.instrumentation-meta {
  padding: 8px 0 12px;
}

.instrumentation-diff-wrapper {
  min-height: 160px;
  border: 1px solid var(--ant-color-border);
  border-radius: var(--ant-border-radius);
  padding: 12px;
  background-color: var(--ant-color-fill-quaternary);
}

.instrumentation-diff-placeholder {
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}

.instrumentation-diff-view {
  overflow-x: auto;
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

.diff-viewer-container {
  background-color: var(--ant-color-bg-container);
  overflow: hidden;
}
</style>

==================================================================================================== 文件 7: apps/web-antd/src/views/protocol-compliance/fuzz/index.vue ====================================================================================================

<script setup lang="ts">
import {
  onMounted,
  ref,
  nextTick,
  computed,
  watch,
  shallowRef,
  onErrorCaptured,
  onUnmounted,
} from 'vue';
import { getFuzzText } from '#/api/custom';
import { requestClient } from '#/api/request';
import { useAccessStore } from '@vben/stores';
import { IconifyIcon } from '@vben/icons';
import Chart from 'chart.js/auto';
import { Page } from '@vben/common-ui';
import { Tabs } from 'ant-design-vue';

// 导入协议专用的composables
import {
  useSNMP,
  useSOL,
  useMQTT,
  useLogReader,
  type FuzzPacket,
  type HistoryResult,
  type ProtocolType,
  type FuzzEngineType,
  type ProtocolImplementationType,
  type ProtocolImplementationConfig,
} from './composables';

// 导入新的协议数据管理器和日志查看器
import { useProtocolDataManager } from './composables/useProtocolDataManager';
import ProtocolLogViewer from './components/ProtocolLogViewer.vue';

// Data state
const rawText = ref('');
const loading = ref(true);
const error = ref<string | null>(null);

// 使用composables中的协议专用逻辑
const {
  protocolStats,
  messageTypeStats,
  fuzzData: snmpFuzzData,
  totalPacketsInFile: snmpTotalPacketsInFile,
  fileTotalPackets: snmpFileTotalPackets,
  fileSuccessCount: snmpFileSuccessCount,
  fileTimeoutCount: snmpFileTimeoutCount,
  fileFailedCount: snmpFileFailedCount,
  resetSNMPStats,
  generateDefaultFuzzData,
  parseSNMPText,
  startSNMPTest,
  processSNMPPacket,
  addSNMPLogToUI,
} = useSNMP();
// RTSP相关功能已移除，SOL现在通过MQTT协议实现选择来使用
const {
  solStats,
  resetSOLStats,
  processSOLLogLine,
  writeSOLScript,
  executeSOLCommand,
  stopSOLProcess,
  preStartCleanupSOL,
  stopSOLContainer,
  stopAndCleanupSOL,
} = useSOL();
const { mqttStats, resetMQTTStats, processMQTTLogLine } = useMQTT();
const {
  logContainer,
  isReadingLog,
  logReadingInterval,
  logReadPosition,
  startLogReading,
  stopLogReading,
  resetLogReader,
  addMQTTLogToUI,
  addSOLLogToUI,
  clearLog,
} = useLogReader();

// 使用新的协议数据管理器
const {
  protocolStates,
  currentProtocol,
  currentState,
  addLog,
  addBatchLogs,
  clearProtocolLogs,
  updateProtocolState,
  switchProtocol,
  getProtocolStats,
  startRealtimeStream,
  addToRealtimeStream,
  stopRealtimeStream,
  stopAllRealtimeStreams,
} = useProtocolDataManager();

// fuzzData现在通过useSNMP composable管理，使用snmpFuzzData
const totalPacketsInFile = ref(0);
// File-level summary stats parsed from txt
const fileTotalPackets = ref(0);
const fileSuccessCount = ref(0);
const fileTimeoutCount = ref(0);
const fileFailedCount = ref(0);

// 协议统计数据现在通过composables管理

// Runtime stats
const packetCount = ref(0);
const successCount = ref(0);
const timeoutCount = ref(0);
const failedCount = ref(0);
const crashCount = ref(0);
const elapsedTime = ref(0);
const packetsPerSecond = ref(30);
const testDuration = ref(60);
const isRunning = ref(false);
const isTestCompleted = ref(false);
let testTimer: number | null = null;

// 添加异步操作取消标志
let mqttSimulationCancelled = false;

// UI configuration
const protocolType = ref<ProtocolType>('MQTT');
const fuzzEngine = ref<FuzzEngineType>('AFLNET');
const targetHost = ref('127.0.0.1');
const targetPort = ref(8883);
const solCommandConfig = ref(
  'afl-fuzz -d -i /home/下载/ProtocolGuard/seeds -o /home/下载/output -N tcp://127.0.0.1/8883 -P MQTT -D 10000 -q 3 -s 3 -E -K -R  -m none -t 3000+ ./sol_instrumented 8883',
);

// 协议实现配置
const protocolImplementations = ref<ProtocolImplementationType[]>(['SOL']);
const selectedProtocolImplementation = ref<ProtocolImplementationType>('SOL');

// 协议实现配置映射
const protocolImplementationConfigs: Record<FuzzEngineType, ProtocolImplementationConfig> = {
  'SNMP_Fuzz': {
    fuzzEngine: 'SNMP_Fuzz',
    defaultImplementations: ['系统固件'],
    isMultiSelect: false
  },
  'MBFuzzer': {
    fuzzEngine: 'MBFuzzer',
    defaultImplementations: ['HiveMQ', 'VerneMQ', 'EMQX', 'FlashMQ', 'NanoMQ', 'Mosquitto'],
    isMultiSelect: false  // 改为单选模式，统一风格
  },
  'AFLNET': {
    fuzzEngine: 'AFLNET',
    defaultImplementations: ['SOL'],
    isMultiSelect: false
  }
};

// Real-time log reading (现在通过useLogReader管理)
const solProcessId = ref<number | null>(null);

// Watch for protocol changes to update port and fuzz engine
watch(protocolType, (newProtocol, oldProtocol) => {
  console.log(`[DEBUG] 协议切换: ${oldProtocol} -> ${newProtocol}`);

  // 立即停止当前运行的测试和所有异步操作
  if (isRunning.value) {
    console.log('[DEBUG] 停止当前运行的测试');
    isRunning.value = false;
    isTestCompleted.value = false;

    // 取消MQTT模拟
    if (oldProtocol === 'MQTT') {
      mqttSimulationCancelled = true;
      console.log('[DEBUG] 取消MQTT模拟操作');
    }

    if (testTimer) {
      clearInterval(testTimer as any);
      testTimer = null;
    }
  }

  // 停止所有实时流和日志读取
  console.log('[DEBUG] 停止所有实时流和日志读取');
  stopAllRealtimeStreams();
  stopLogReading();

  // 清理之前协议的状态
  if (oldProtocol === 'MQTT') {
    console.log('[DEBUG] 清理MQTT协议状态');
    // 清理MQTT动画
    cleanupMQTTAnimations();
    // 使用nextTick确保在下一个tick中清理，避免当前更新周期的冲突
    nextTick(() => {
      // 清理定时器
      if (mqttUpdateTimer) {
        clearTimeout(mqttUpdateTimer);
        mqttUpdateTimer = null;
      }
      // 清理非响应式日志数据
      mqttDifferentialLogsData = [];
      mqttLogsPendingUpdate = false;
      mqttLogsUpdateKey.value++;
      resetMQTTStats();
      resetMQTTDifferentialStats();
    });
  }

  // 设置新协议的配置
  if (newProtocol === 'SNMP') {
    targetPort.value = 161;
    fuzzEngine.value = 'SNMP_Fuzz';
  } else if (newProtocol === 'MQTT') {
    targetPort.value = 1883;
    // MQTT协议的引擎将根据协议实现选择来确定
    // 默认使用MBFuzzer，如果选择SOL则切换到AFLNET
    fuzzEngine.value = 'MBFuzzer';
    // MQTT动画将在测试开始时初始化
  }

  // 重置测试状态
  nextTick(() => {
    resetTestState();
    console.log('[DEBUG] 协议切换完成，状态已重置');
  });
});

// Watch for fuzz engine changes to update protocol implementations
watch(fuzzEngine, (newEngine) => {
  console.log(`[DEBUG] Fuzz引擎切换: ${newEngine}`);
  const config = protocolImplementationConfigs[newEngine];
  if (config) {
    // 更新多选数组（保持向后兼容）
    protocolImplementations.value = [...config.defaultImplementations];
    // 更新单选值（新的统一风格）
    selectedProtocolImplementation.value = config.defaultImplementations[0];
    console.log(`[DEBUG] 协议实现已更新为: ${selectedProtocolImplementation.value}`);
  }
  // 注意：现在使用统一历史记录存储，不需要根据引擎切换重新加载
});

// Watch for selected protocol implementation changes to sync with array
watch(selectedProtocolImplementation, (newImpl) => {
  console.log('[DEBUG] ========== 协议实现变更监听器触发 ==========');
  console.log('[DEBUG] 新的协议实现:', newImpl);
  console.log('[DEBUG] 当前协议类型:', protocolType.value);
  console.log('[DEBUG] 当前Fuzz引擎:', fuzzEngine.value);
  
  // 同步单选值到多选数组，保持向后兼容
  protocolImplementations.value = [newImpl];
  
  // 对于MQTT协议，根据实现选择自动切换引擎
  if (protocolType.value === 'MQTT') {
    if (newImpl === 'SOL') {
      // 选择SOL时，使用AFLNET引擎，端口改为8883
      console.log('[DEBUG] 检测到SOL实现，准备切换到AFLNET引擎');
      fuzzEngine.value = 'AFLNET';
      targetPort.value = 8883;
      console.log('[DEBUG] MQTT协议选择SOL实现，切换到AFLNET引擎，端口8883');
      console.log('[DEBUG] 切换后 - fuzzEngine.value:', fuzzEngine.value);
      console.log('[DEBUG] 切换后 - targetPort.value:', targetPort.value);
    } else {
      // 选择传统MQTT broker时，使用MBFuzzer引擎，端口1883
      console.log('[DEBUG] 检测到传统MQTT broker实现，准备切换到MBFuzzer引擎');
      fuzzEngine.value = 'MBFuzzer';
      targetPort.value = 1883;
      console.log('[DEBUG] MQTT协议选择传统broker实现，切换到MBFuzzer引擎，端口1883');
      console.log('[DEBUG] 切换后 - fuzzEngine.value:', fuzzEngine.value);
      console.log('[DEBUG] 切换后 - targetPort.value:', targetPort.value);
    }
  }
  console.log('[DEBUG] ========== 协议实现变更监听器结束 ==========');
});
const showCharts = ref(false);
const crashDetails = ref<any>(null);
const logEntries = ref<any[]>([]);
const startTime = ref<string>('');
const endTime = ref<string>('');
const lastUpdate = ref<string>('');
const currentSpeed = ref(0);
const isPaused = ref(false);
const showCrashDetails = ref(false);
const testStartTime = ref<Date | null>(null);
const testEndTime = ref<Date | null>(null);
const currentPacketIndex = ref(0);
const packetDelay = ref(33); // 1000/30 = 33ms for 30 packets/second

// 历史结果相关状态
const showHistoryView = ref(false);
const selectedHistoryItem = ref<any>(null);
const activeTab = ref('test'); // 'test' or 'history'

// 通知相关状态
const showNotification = ref(false);
const notificationMessage = ref('');

// HistoryResult 接口现在从 composables 导入

// 模拟历史结果数据
const historyResults = ref<HistoryResult[]>([
  {
    id: 'hist_001',
    timestamp: '2025-01-20 14:30:25',
    protocol: 'SNMP',
    fuzzEngine: 'SNMP_Fuzz',
    targetHost: '127.0.0.1',
    targetPort: 161,
    duration: 127,
    totalPackets: 2847,
    successCount: 2156,
    timeoutCount: 542,
    failedCount: 149,
    crashCount: 0,
    successRate: 76,
    protocolStats: { v1: 1203, v2c: 892, v3: 752 },
    messageTypeStats: { get: 1124, set: 678, getnext: 589, getbulk: 456 },
    hasCrash: false,
  },
  {
    id: 'hist_002',
    timestamp: '2025-01-20 11:15:42',
    protocol: 'SNMP',
    fuzzEngine: 'SNMP_Fuzz',
    targetHost: '127.0.0.1',
    targetPort: 161,
    duration: 89,
    totalPackets: 1924,
    successCount: 1456,
    timeoutCount: 321,
    failedCount: 89,
    crashCount: 58,
    successRate: 76,
    protocolStats: { v1: 823, v2c: 612, v3: 489 },
    messageTypeStats: { get: 756, set: 445, getnext: 398, getbulk: 325 },
    hasCrash: true,
    crashDetails: {
      id: 1847,
      time: '11:16:23',
      type: 'Segmentation Fault (SIGSEGV)',
      dumpFile: '/var/crash/SNMP_crash_1737360983.dmp',
      logPath:
        '/home/hhh/下载/snmp_fuzz/snmp_github/snmp_fuzz/scan_result/crash_logs/20250120-111623',
      details:
        '[11:16:23] Segmentation Fault (SIGSEGV)\nProcess ID: 8472\nFault Address: 0x7F8B2C40\nRegisters:\n  EAX: 0x00000000  EBX: 0x7F8B2C40\n  ECX: 0x12345678  EDX: 0xDEADBEEF\n  ESI: 0x87654321  EDI: 0xCAFEBABE\n  EBP: 0x7FFF1234  ESP: 0x7FFF1200\nBacktrace:\n  #0  0x08048567 in get_handler()\n  #1  0x08048234 in packet_processor()\n  #2  0x08047890 in main_loop()',
      packetContent: '302902010004067075626C6963A01C02040E8F83C502010002010030',
    },
  },
  {
    id: 'hist_003',
    timestamp: '2025-01-19 16:45:18',
    protocol: 'SNMP',
    fuzzEngine: 'AFLNET',
    targetHost: '10.0.0.15',
    targetPort: 161,
    duration: 203,
    totalPackets: 4521,
    successCount: 3892,
    timeoutCount: 456,
    failedCount: 173,
    crashCount: 0,
    successRate: 86,
    protocolStats: { v1: 1789, v2c: 1456, v3: 1276 },
    messageTypeStats: { get: 1823, set: 1124, getnext: 892, getbulk: 682 },
    hasCrash: false,
  },
  {
    id: 'hist_004',
    timestamp: '2025-01-23 20:36:44',
    protocol: 'MQTT',
    fuzzEngine: 'MBFuzzer',
    targetHost: '127.0.0.1',
    targetPort: 1883,
    duration: 13,
    totalPackets: 953,
    successCount: 650,
    timeoutCount: 303,
    failedCount: 0,
    crashCount: 0,
    successRate: 68,
    mqttStats: {
      fuzzing_start_time: '2024-07-06 00:39:14',
      fuzzing_end_time: '2024-07-07 10:15:23',
      client_request_count: 851051,
      broker_request_count: 523790,
      total_request_count: 1374841,
      crash_number: 0,
      diff_number: 0,
      duplicate_diff_number: 118563,
      valid_connect_number: 1362,
      duplicate_connect_diff: 1507,
      total_differences: 0,
      client_messages: {
        CONNECT: 125000,
        CONNACK: 0,
        PUBLISH: 320000,
        PUBACK: 180000,
        PUBREC: 45000,
        PUBREL: 45000,
        PUBCOMP: 45000,
        SUBSCRIBE: 85000,
        SUBACK: 0,
        UNSUBSCRIBE: 25000,
        UNSUBACK: 0,
        PINGREQ: 21051,
        PINGRESP: 0,
        DISCONNECT: 0,
        AUTH: 0,
      },
      broker_messages: {
        CONNECT: 0,
        CONNACK: 125000,
        PUBLISH: 180000,
        PUBACK: 85000,
        PUBREC: 25000,
        PUBREL: 25000,
        PUBCOMP: 25000,
        SUBSCRIBE: 0,
        SUBACK: 45000,
        UNSUBSCRIBE: 0,
        UNSUBACK: 12790,
        PINGREQ: 0,
        PINGRESP: 21000,
        DISCONNECT: 0,
        AUTH: 0,
      },
      duplicate_diffs: {
        CONNECT: 1507,
        CONNACK: 0,
        PUBLISH: 0,
        PUBACK: 0,
        PUBREC: 0,
        PUBREL: 0,
        PUBCOMP: 0,
        SUBSCRIBE: 0,
        SUBACK: 0,
        UNSUBSCRIBE: 0,
        UNSUBACK: 0,
        PINGREQ: 0,
        PINGRESP: 0,
        DISCONNECT: 0,
        AUTH: 0,
      },
      differential_reports: [],
      q_table_states: [],
      broker_issues: {
        hivemq: 0,
        vernemq: 0,
        emqx: 0,
        flashmq: 0,
        nanomq: 0,
        mosquitto: 0,
      },
    },
    protocolSpecificData: {
      clientRequestCount: 851051,
      brokerRequestCount: 523790,
      diffNumber: 5841,
      duplicateDiffNumber: 118563,
      validConnectNumber: 1362,
      duplicateConnectDiff: 1507,
      fuzzingStartTime: '2024-07-06 00:39:14',
      fuzzingEndTime: '2024-07-07 10:15:23',
    },
    hasCrash: false,
  },
]);

// UI refs (logContainer现在通过useLogReader管理)
const messageCanvas = ref<HTMLCanvasElement>();
const versionCanvas = ref<HTMLCanvasElement>();
const mqttMessageCanvas = ref<HTMLCanvasElement>();
let messageTypeChart: any = null;
let versionChart: any = null;
let mqttMessageChart: any = null;

// Computed properties
const progressWidth = computed(() => {
  const estimatedTotal = Math.max(
    packetCount.value,
    testDuration.value * packetsPerSecond.value,
  );
  return estimatedTotal > 0
    ? Math.min(100, Math.round((packetCount.value / estimatedTotal) * 100))
    : 0;
});

const successRate = computed(() => {
  const total =
    successCount.value +
    timeoutCount.value +
    failedCount.value +
    crashCount.value;
  return total > 0 ? Math.round((successCount.value / total) * 100) : 0;
});

const timeoutRate = computed(() => {
  const total =
    successCount.value +
    timeoutCount.value +
    failedCount.value +
    crashCount.value;
  return total > 0 ? Math.round((timeoutCount.value / total) * 100) : 0;
});

const failedRate = computed(() => {
  const total =
    successCount.value +
    timeoutCount.value +
    failedCount.value +
    crashCount.value;
  return total > 0 ? Math.round((failedCount.value / total) * 100) : 0;
});

// generateDefaultFuzzData 现在通过 useSNMP composable 提供

async function fetchText() {
  loading.value = true;
  try {
    // 尝试从Flask后端获取SNMP日志数据
    const resp = await getFuzzText();
    const text = (resp as any)?.text ?? (resp as any)?.data?.text ?? '';
    console.log('API响应数据长度:', text?.length || 0);
    console.log('API响应前100字符:', text?.substring(0, 100) || '无数据');

    if (!text || text.trim().length === 0) {
      console.warn('API返回空数据，使用默认数据');
      rawText.value = generateDefaultFuzzData();
    } else {
      console.log('成功从SNMP日志文件加载数据');
      rawText.value = text;
    }
  } catch (e: any) {
    console.error('API调用失败:', e);
    error.value = `API调用失败: ${e?.message || '未知错误'}`;
    rawText.value = generateDefaultFuzzData();
    console.warn('API failed, using default data:', e?.message);
  } finally {
    loading.value = false;
  }
}

function initCharts() {
  if (!messageCanvas.value || !versionCanvas.value) {
    console.warn('Canvas elements not ready');
    return false;
  }

  try {
    const messageCtx = messageCanvas.value.getContext('2d');
    const versionCtx = versionCanvas.value.getContext('2d');
    if (!messageCtx || !versionCtx) {
      console.warn('Failed to get canvas contexts');
      return false;
    }

    messageTypeChart = new Chart(messageCtx, {
      type: 'doughnut',
      data: {
        labels: ['GET', 'SET', 'GETNEXT', 'GETBULK'],
        datasets: [
          {
            data: [0, 0, 0, 0],
            backgroundColor: ['#3B82F6', '#6366F1', '#EC4899', '#10B981'],
            borderColor: '#FFFFFF',
            borderWidth: 3,
            hoverOffset: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#1F2937',
              padding: 15,
              font: { size: 12, weight: 'bold' },
              usePointStyle: true,
            },
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: 'white',
            bodyColor: 'white',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            callbacks: {
              label: function (context: any) {
                const total = context.dataset.data.reduce(
                  (a: number, b: number) => a + b,
                  0,
                );
                const percentage =
                  total > 0 ? Math.round((context.parsed / total) * 100) : 0;
                return `${context.label}: ${context.parsed} (${percentage}%)`;
              },
            },
          },
        },
        cutout: '60%',
      },
    });

    versionChart = new Chart(versionCtx, {
      type: 'doughnut',
      data: {
        labels: ['SNMP v1', 'SNMP v2c', 'SNMP v3'],
        datasets: [
          {
            data: [0, 0, 0],
            backgroundColor: ['#F59E0B', '#8B5CF6', '#EF4444'],
            borderColor: '#FFFFFF',
            borderWidth: 3,
            hoverOffset: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#1F2937',
              padding: 15,
              font: { size: 12, weight: 'bold' },
              usePointStyle: true,
            },
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: 'white',
            bodyColor: 'white',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            callbacks: {
              label: function (context: any) {
                const total = context.dataset.data.reduce(
                  (a: number, b: number) => a + b,
                  0,
                );
                const percentage =
                  total > 0 ? Math.round((context.parsed / total) * 100) : 0;
                return `${context.label}: ${context.parsed} (${percentage}%)`;
              },
            },
          },
        },
        cutout: '60%',
      },
    });

    console.log('Charts initialized successfully');
    return true;
  } catch (error) {
    console.error('Failed to initialize charts:', error);
    return false;
  }
}

function initMQTTChart() {
  if (!mqttMessageCanvas.value) {
    console.warn('MQTT Canvas element not ready');
    return false;
  }

  try {
    const mqttCtx = mqttMessageCanvas.value.getContext('2d');
    if (!mqttCtx) {
      console.warn('Failed to get MQTT canvas context');
      return false;
    }

    mqttMessageChart = new Chart(mqttCtx, {
      type: 'doughnut',
      data: {
        labels: [
          'CONNECT',
          'PUBLISH',
          'SUBSCRIBE',
          'PINGREQ',
          'UNSUBSCRIBE',
          'PUBACK',
          'CONNACK',
          'SUBACK',
          'PINGRESP',
          '其他',
        ],
        datasets: [
          {
            data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            backgroundColor: [
              '#3B82F6',
              '#10B981',
              '#F59E0B',
              '#EF4444',
              '#8B5CF6',
              '#EC4899',
              '#06B6D4',
              '#84CC16',
              '#F97316',
              '#6B7280',
            ],
            borderColor: '#FFFFFF',
            borderWidth: 2,
            hoverOffset: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#1F2937',
              padding: 10,
              font: { size: 10, weight: 'bold' },
              usePointStyle: true,
            },
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: 'white',
            bodyColor: 'white',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            callbacks: {
              label: function (context: any) {
                const total = context.dataset.data.reduce(
                  (a: number, b: number) => a + b,
                  0,
                );
                const percentage =
                  total > 0 ? Math.round((context.parsed / total) * 100) : 0;
                return `${context.label}: ${context.parsed} (${percentage}%)`;
              },
            },
          },
        },
        cutout: '50%',
      },
    });

    console.log('MQTT Chart initialized successfully');
    return true;
  } catch (error) {
    console.error('Failed to initialize MQTT chart:', error);
    return false;
  }
}

// 从fuzz数据重新计算统计信息的函数
function recalculateStatsFromFuzzData() {
  try {
    if (!snmpFuzzData.value || snmpFuzzData.value.length === 0) {
      console.warn('No fuzz data available for recalculation');
      return;
    }

    console.log('Recalculating statistics from fuzz data...');

    // 重置统计数据
    const newProtocolStats = { v1: 0, v2c: 0, v3: 0 };
    const newMessageTypeStats = { get: 0, set: 0, getnext: 0, getbulk: 0 };

    // 遍历fuzz数据重新计算统计
    snmpFuzzData.value.forEach((packet) => {
      // 统计协议版本
      if (packet.version === 'v1') newProtocolStats.v1++;
      else if (packet.version === 'v2c') newProtocolStats.v2c++;
      else if (packet.version === 'v3') newProtocolStats.v3++;

      // 统计消息类型
      if (packet.type === 'get') newMessageTypeStats.get++;
      else if (packet.type === 'set') newMessageTypeStats.set++;
      else if (packet.type === 'getnext') newMessageTypeStats.getnext++;
      else if (packet.type === 'getbulk') newMessageTypeStats.getbulk++;
    });

    // 更新统计数据
    protocolStats.value = newProtocolStats;
    messageTypeStats.value = newMessageTypeStats;

    console.log('Statistics recalculated from fuzz data:', {
      protocolStats: newProtocolStats,
      messageTypeStats: newMessageTypeStats,
      totalPackets: snmpFuzzData.value.length,
    });
  } catch (error) {
    console.error('Error recalculating stats from fuzz data:', error);
  }
}

function updateCharts() {
  try {
    if (!messageTypeChart || !versionChart) {
      console.warn('Charts not initialized, skipping update');
      return;
    }

    // Update message type chart
    if (
      messageTypeChart.data &&
      messageTypeChart.data.datasets &&
      messageTypeChart.data.datasets[0]
    ) {
      messageTypeChart.data.datasets[0].data = [
        messageTypeStats.value.get || 0,
        messageTypeStats.value.set || 0,
        messageTypeStats.value.getnext || 0,
        messageTypeStats.value.getbulk || 0,
      ];
      messageTypeChart.update('none'); // Use 'none' animation mode for better performance
    }

    // Update version chart
    if (
      versionChart.data &&
      versionChart.data.datasets &&
      versionChart.data.datasets[0]
    ) {
      versionChart.data.datasets[0].data = [
        protocolStats.value.v1 || 0,
        protocolStats.value.v2c || 0,
        protocolStats.value.v3 || 0,
      ];
      versionChart.update('none'); // Use 'none' animation mode for better performance
    }

    console.log('Charts updated successfully with data:', {
      messageTypeData: [
        messageTypeStats.value.get || 0,
        messageTypeStats.value.set || 0,
        messageTypeStats.value.getnext || 0,
        messageTypeStats.value.getbulk || 0,
      ],
      versionData: [
        protocolStats.value.v1 || 0,
        protocolStats.value.v2c || 0,
        protocolStats.value.v3 || 0,
      ],
    });
  } catch (error) {
    console.error('Error updating charts:', error);
  }
}

function updateMQTTChart() {
  try {
    // MQTT现在使用broker差异统计卡片显示，不再需要图表更新
    console.log(
      'MQTT using broker difference statistics cards, chart update skipped',
    );
  } catch (error) {
    console.error('Error in MQTT chart function:', error);
  }
}

function parseText(text: string) {
  // 使用SNMP composable的解析功能
  const parsedData = parseSNMPText(text);
  snmpFuzzData.value = parsedData;
  totalPacketsInFile.value = parsedData.filter(
    (p) => typeof p.id === 'number',
  ).length;

  // Debug: Show distribution of packet results after parsing
  const resultCounts = parsedData.reduce(
    (acc, packet) => {
      const result = packet.result || 'unknown';
      acc[result] = (acc[result] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );
  console.log('解析后的数据包结果分布:', resultCounts);
  console.log('总解析数据包数:', parsedData.length);

  // Extract timing information
  const startTimeMatch = text.match(/开始时间:\s*([^\n]+)/);
  const endTimeMatch = text.match(/结束时间:\s*([^\n]+)/);
  const durationMatch = text.match(/总耗时:\s*([\d.]+)\s*秒/);
  const totalPacketsMatch =
    text.match(/发送总数据包:\s*(\d+)/) ||
    text.match(/\[日志系统\]\s*数据包统计:\s*(\d+)\s*\/\s*\d+\s*个/);
  const avgSpeedMatch = text.match(/平均发送速率:\s*([\d.]+)\s*包\/秒/);

  if (startTimeMatch) startTime.value = startTimeMatch[1];
  if (endTimeMatch) endTime.value = endTimeMatch[1];
  if (durationMatch) testDuration.value = parseFloat(durationMatch[1]);
  if (avgSpeedMatch) packetsPerSecond.value = parseFloat(avgSpeedMatch[1]);

  // Counters from file
  const successCountInFile = (text.match(/\[接收成功\]/g) || []).length;
  const timeoutCountInFile = (text.match(/\[接收超时\]/g) || []).length;
  const failedCountInFile = (text.match(/生成失败:/g) || []).length;
  fileSuccessCount.value = successCountInFile;
  fileTimeoutCount.value = timeoutCountInFile;
  fileFailedCount.value = failedCountInFile;
  fileTotalPackets.value = totalPacketsMatch
    ? parseInt(totalPacketsMatch[1])
    : successCountInFile + timeoutCountInFile + failedCountInFile;
}

function resetTestState() {
  try {
    // Reset all counters in a batch
    packetCount.value = 0;
    successCount.value = 0;
    timeoutCount.value = 0;
    failedCount.value = 0;
    crashCount.value = 0;
    elapsedTime.value = 0;
    currentPacketIndex.value = 0;
    crashDetails.value = null;
    isPaused.value = false;
    showCrashDetails.value = false;
    logEntries.value = [];

    // 重置协议专用的统计数据
    resetSNMPStats();
    resetSOLStats();
    resetMQTTStats();

    // 重置日志读取器
    resetLogReader();

    // Reset log container with proper checks
    nextTick(() => {
      try {
        clearLog();
      } catch (error) {
        console.warn('Failed to reset log container:', error);
      }
    });
  } catch (error) {
    console.error('Error in resetTestState:', error);
  }
}

async function startTest() {
  // MQTT协议不需要fuzzData，直接从文件读取
  if (protocolType.value !== 'MQTT' && !snmpFuzzData.value.length) return;

  resetTestState();
  isRunning.value = true;
  isTestCompleted.value = false;
  showCharts.value = false; // 测试开始时隐藏图表
  testStartTime.value = new Date();

  // 根据协议类型执行不同的启动逻辑
  try {
    if (protocolType.value === 'SNMP') {
      // 初始化SNMP协议数据管理器
      clearProtocolLogs('SNMP');
      updateProtocolState('SNMP', {
        isRunning: true,
        isProcessing: true,
        totalRecords: snmpFuzzData.value.length,
        processedRecords: 0,
      });

      // 启动SNMP实时流
      startRealtimeStream('SNMP', { batchSize: 20, interval: 100 });

      await startSNMPTest(loop);
    } else if (protocolType.value === 'MQTT') {
      // 根据协议实现选择不同的测试方式
      console.log('[DEBUG] ========== MQTT测试启动 ==========');
      console.log('[DEBUG] 当前协议实现:', selectedProtocolImplementation.value);
      console.log('[DEBUG] 当前Fuzz引擎:', fuzzEngine.value);
      console.log('[DEBUG] 当前目标端口:', targetPort.value);
      
      if (selectedProtocolImplementation.value === 'SOL') {
        // SOL使用AFLNET引擎
        console.log('[DEBUG] 启动SOL测试 (AFLNET引擎)');
        await startSOLTest();
      } else {
        // 传统MQTT broker使用MBFuzzer引擎
        await startMQTTTest();
      }
    } else {
      throw new Error(`不支持的协议类型: ${protocolType.value}`);
    }
  } catch (error: any) {
    console.error('启动测试失败:', error);
    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: protocolType.value,
        type: 'ERROR',
        oids: [],
        hex: '',
        result: 'failed',
        failedReason: `启动失败: ${error.message}`,
      } as any,
      false,
    );
    isRunning.value = false;
    return;
  }

  // 启动通用计时器
  if (testTimer) {
    clearInterval(testTimer as any);
    testTimer = null;
  }
  testTimer = window.setInterval(() => {
    if (!isPaused.value) {
      elapsedTime.value++;
      currentSpeed.value =
        elapsedTime.value > 0
          ? Math.round(packetCount.value / elapsedTime.value)
          : 0;
    }
  }, 1000);
}

// Protocol-specific test functions
// startRTSPTest函数已移除，SOL现在通过startSOLTest函数处理

async function startSOLTest() {
  console.log('[DEBUG] ========== startSOLTest 被调用 ==========');
  
  try {
    // 1. 启动前清理：停止现有容器并清理输出文件
    console.log('[DEBUG] 执行启动前清理...');
    
    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'SOL',
        type: 'CLEANUP',
        oids: ['正在清理之前的测试环境...'],
        hex: '',
        result: 'info',
      } as any,
      false,
    );

    const cleanupResult = await preStartCleanupSOL();
    const responseData = cleanupResult.data || cleanupResult;
    
    console.log('[DEBUG] 启动前清理完成:', responseData);
    
    if (responseData?.cleanup_results) {
      const results = responseData.cleanup_results;
      const cleanupMessages = [];
      
      if (results.containers_stopped > 0) {
        cleanupMessages.push(`✓ 已停止 ${results.containers_stopped} 个容器`);
      }
      if (results.containers_removed > 0) {
        cleanupMessages.push(`✓ 已删除 ${results.containers_removed} 个容器`);
      }
      if (results.output_cleaned) {
        cleanupMessages.push(`✓ 输出目录已清理`);
      }
      if (results.errors && results.errors.length > 0) {
        cleanupMessages.push(`⚠ 部分清理失败: ${results.errors.length} 个错误`);
      }
      
      if (cleanupMessages.length === 0) {
        cleanupMessages.push('✓ 环境已就绪，无需清理');
      }

      addLogToUI(
        {
          timestamp: new Date().toLocaleTimeString(),
          version: 'SOL',
          type: 'CLEANUP',
          oids: cleanupMessages,
          hex: '',
          result: 'success',
        } as any,
        false,
      );
    }

    // 2. 写入脚本文件
    console.log('[DEBUG] 写入脚本文件...');
    await writeSOLScriptWrapper();

    // 3. 执行shell命令启动程序
    console.log('[DEBUG] 启动Docker容器...');
    await executeSOLCommandWrapper();

    // 4. 开始实时读取日志
    console.log('[DEBUG] 开始日志读取...');
    startSOLLogReading();

    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'SOL',
        type: 'START',
        oids: ['SOL测试已启动，输出文件将在测试结束后保留供查看'],
        hex: '',
        result: 'success',
      } as any,
      false,
    );
  } catch (error: any) {
    console.error('[DEBUG] SOL测试启动失败:', error);
    
    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'SOL',
        type: 'ERROR',
        oids: [`启动失败: ${error.message || error}`],
        hex: '',
        result: 'error',
      } as any,
      false,
    );
    
    throw error;
  }
}

// startSNMPTest 现在通过 useSNMP composable 提供

async function startMQTTTest() {
  try {
    console.log('开始MQTT协议测试');

    // 重置MQTT统计数据
    resetMQTTStats();

    // 重置差异统计数据
    resetMQTTDifferentialStats();

    // 清空协议日志
    clearProtocolLogs('MQTT');

    // 更新协议状态
    updateProtocolState('MQTT', {
      isRunning: true,
      isProcessing: true,
      totalRecords: 0,
      processedRecords: 0,
    });

    // 启动MQTT实时流（更快的刷新频率）
    startRealtimeStream('MQTT', { batchSize: 20, interval: 50 });

    // 清空旧的差异日志数据（向后兼容）
    if (mqttUpdateTimer) {
      clearTimeout(mqttUpdateTimer);
      mqttUpdateTimer = null;
    }
    mqttDifferentialLogsData = [];
    mqttLogsPendingUpdate = false;
    mqttLogsUpdateKey.value++;

    // 初始化MQTT动画（在测试开始时）
    await nextTick();
    initMQTTAnimations();

    // 开始实时模拟MQTT测试
    await startMQTTRealTimeSimulation();
  } catch (error: any) {
    console.error('MQTT测试启动失败:', error);
    // 更新协议状态
    updateProtocolState('MQTT', {
      isRunning: false,
      isProcessing: false,
    });
    throw error;
  }
}

// 重置MQTT差异统计数据
function resetMQTTDifferentialStats() {
  // 重置差异类型统计
  Object.keys(mqttDifferentialStats.value.type_stats).forEach((key) => {
    mqttDifferentialStats.value.type_stats[
      key as keyof typeof mqttDifferentialStats.value.type_stats
    ] = 0;
  });

  // 重置协议版本统计
  Object.keys(mqttDifferentialStats.value.version_stats).forEach((key) => {
    mqttDifferentialStats.value.version_stats[
      key as keyof typeof mqttDifferentialStats.value.version_stats
    ] = 0;
  });

  // 重置broker差异统计 - 与日志信息保持一致
  Object.keys(mqttRealTimeStats.value.broker_diff_stats).forEach((key) => {
    mqttRealTimeStats.value.broker_diff_stats[
      key as keyof typeof mqttRealTimeStats.value.broker_diff_stats
    ] = 0;
  });

  // 重置client和broker发送数据统计
  mqttRealTimeStats.value.client_sent_count = 0;
  mqttRealTimeStats.value.broker_sent_count = 0;

  // 重置实时差异计数器（从0开始累加）
  mqttRealTimeStats.value.diff_number = 0;
  mqttRealTimeStats.value.crash_number = 0;
  mqttRealTimeStats.value.duplicate_diff_number = 0;
  mqttRealTimeStats.value.valid_connect_number = 0;
  mqttRealTimeStats.value.duplicate_connect_diff = 0;

  // 重置总差异数
  mqttDifferentialStats.value.total_differences = 0;

  // 重置差异类型分布统计
  mqttDiffTypeStats.value.protocol_violations = 0;
  mqttDiffTypeStats.value.timeout_errors = 0;
  mqttDiffTypeStats.value.connection_failures = 0;
  mqttDiffTypeStats.value.message_corruptions = 0;
  mqttDiffTypeStats.value.state_inconsistencies = 0;
  mqttDiffTypeStats.value.authentication_errors = 0;
  mqttDiffTypeStats.value.total_differences = 0;
}

// resetMQTTStats 现在通过 useMQTT composable 提供

// 解析MQTT统计数据从文件
async function parseMQTTStatsFromFile() {
  try {
    console.log('[调试-统计] 开始调用MQTT统计数据API');
    const result = await requestClient.post('/protocol-compliance/read-log', {
      protocol: 'MQTT',
      lastPosition: 0, // 从文件开头读取全部内容
    });

    console.log('[调试-统计] ✅ MQTT统计数据API调用成功');
    console.log('[调试-统计] 响应数据:', result);

    // requestClient已经处理了错误检查，直接使用返回的data
    const content = result.content;
    const lines = content.split('\n');

    // 解析统计数据
    for (const line of lines) {
      // 解析客户端请求数
      if (line.includes('Fuzzing request number (client):')) {
        const match = line.match(/Fuzzing request number \(client\):\s*(\d+)/);
        if (match) {
          mqttStats.value.client_request_count = parseInt(match[1]);
        }
      }

      // 解析代理端请求数
      if (line.includes('Fuzzing request number (broker):')) {
        const match = line.match(/Fuzzing request number \(broker\):\s*(\d+)/);
        if (match) {
          mqttStats.value.broker_request_count = parseInt(match[1]);
        }
      }

      // 解析崩溃数量
      if (line.includes('Crash Number:')) {
        const match = line.match(/Crash Number:\s*(\d+)/);
        if (match) {
          mqttStats.value.crash_number = parseInt(match[1]);
          crashCount.value = mqttStats.value.crash_number;
        }
      }

      // 解析差异数量
      if (line.includes('Diff Number:')) {
        const match = line.match(/Diff Number:\s*(\d+)/);
        if (match) {
          mqttStats.value.diff_number = parseInt(match[1]);
        }
      }

      // 解析有效连接数
      if (line.includes('Valid Connect Number:')) {
        const match = line.match(/Valid Connect Number:\s*(\d+)/);
        if (match) {
          mqttStats.value.valid_connect_number = parseInt(match[1]);
          successCount.value = parseInt(match[1]);
        }
      }

      // 解析开始时间
      if (line.includes('Fuzzing Start Time:')) {
        const match = line.match(/Fuzzing Start Time:\s*(.+)/);
        if (match) {
          mqttStats.value.fuzzing_start_time = match[1].trim();
          startTime.value = match[1].trim();
        }
      }

      // 解析结束时间
      if (line.includes('Fuzzing End Time:')) {
        const match = line.match(/Fuzzing End Time:\s*(.+)/);
        if (match) {
          mqttStats.value.fuzzing_end_time = match[1].trim();
          endTime.value = match[1].trim();
        }
      }
    }

    // 计算总请求数
    mqttStats.value.total_request_count =
      mqttStats.value.client_request_count +
      mqttStats.value.broker_request_count;
    fileTotalPackets.value = mqttStats.value.total_request_count;
    fileSuccessCount.value = mqttStats.value.valid_connect_number;

    console.log('MQTT统计数据解析完成:', mqttStats.value);
    console.log('MQTT关键数据检查:', {
      client_request_count: mqttStats.value.client_request_count,
      broker_request_count: mqttStats.value.broker_request_count,
      diff_number: mqttStats.value.diff_number,
      valid_connect_number: mqttStats.value.valid_connect_number,
      duplicate_connect_diff: mqttStats.value.duplicate_connect_diff,
      total_differences: mqttStats.value.total_differences,
    });
  } catch (error: any) {
    console.error('解析MQTT统计数据失败:', error);
  }
}

// 统一的日志系统 - 替换分离的MQTT日志
const unifiedLogs = ref<
  Array<{
    id: string;
    timestamp: string;
    type: 'INFO' | 'ERROR' | 'WARNING' | 'SUCCESS';
    content: string;
    protocol: 'SNMP' | 'MQTT';
  }>
>([]);

// MQTT协议差异报告日志 - 使用非响应式数据避免DOM冲突
let mqttDifferentialLogsData: string[] = []; // 非响应式数据存储
const mqttLogsContainer = ref<HTMLElement | null>(null); // 日志容器引用
const mqttLogsUpdateKey = ref(0); // 强制更新key
let mqttUpdateTimer: number | null = null; // 防抖定时器
let mqttLogsPendingUpdate = false; // 更新锁

// MQTT处理状态
const mqttIsProcessingLogs = ref(false);
const mqttTotalRecords = ref(0);
const mqttProcessedRecords = ref(0);
const mqttProcessingProgress = ref(0);

// MQTT实时统计数据
const mqttRealTimeStats = ref({
  // 保留原有的崩溃和差异统计
  crash_number: 0,
  diff_number: 0,
  duplicate_diff_number: 0,
  valid_connect_number: 0,
  duplicate_connect_diff: 0,
  // 新增broker类型差异统计 - 与日志中diff_range_broker字段对应
  broker_diff_stats: {
    hivemq: 0,
    vernemq: 0,
    emqx: 0,
    flashmq: 0,
    nanomq: 0,
    mosquitto: 0,
  },
  // 新增client和broker发送数据统计
  client_sent_count: 0,
  broker_sent_count: 0,
});

// MQTT 差异类型分布统计数据
const mqttDiffTypeStats = ref({
  protocol_violations: 0,
  timeout_errors: 0,
  connection_failures: 0,
  message_corruptions: 0,
  state_inconsistencies: 0,
  authentication_errors: 0,
  total_differences: 0,
  distribution: {
    protocol_violations: 0,
    timeout_errors: 0,
    connection_failures: 0,
    message_corruptions: 0,
    state_inconsistencies: 0,
    authentication_errors: 0,
  },
});

// 统一的日志添加函数
function addUnifiedLog(
  type: 'INFO' | 'ERROR' | 'WARNING' | 'SUCCESS',
  content: string,
  protocol: 'SNMP' | 'MQTT' = 'MQTT',
) {
  unifiedLogs.value.push({
    id: `${protocol.toLowerCase()}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    timestamp: new Date().toLocaleTimeString(),
    type,
    content,
    protocol,
  });

  // 实时累加协议差异统计 - 逐个递增确保数据准确
  if (protocol === 'MQTT' && isRunning.value) {
    // 精确递增差异计数，每条差异记录+1
    mqttRealTimeStats.value.diff_number++;
    mqttStats.value.diff_number = mqttRealTimeStats.value.diff_number;

    // 同步更新总差异数
    mqttDifferentialStats.value.total_differences =
      mqttRealTimeStats.value.diff_number;
    mqttDiffTypeStats.value.total_differences =
      mqttRealTimeStats.value.diff_number;

    // 确保历史记录与统计信息保持同步
    if (mqttStats.value.total_differences !== undefined) {
      mqttStats.value.total_differences = mqttRealTimeStats.value.diff_number;
    }
  }
}

// 清空统一日志
function clearUnifiedLogs() {
  unifiedLogs.value.length = 0;
}

// 开始MQTT实时模拟
async function startMQTTRealTimeSimulation() {
  try {
    console.log('=== MQTT后端连接测试开始 ===');
    console.log('[调试] 准备调用后端API: /protocol-compliance/read-log');
    console.log('[调试] 请求参数:', { protocol: 'MQTT', lastPosition: 0 });

    // 首先读取完整的fuzzing_report.txt文件
    const result = await requestClient.post('/protocol-compliance/read-log', {
      protocol: 'MQTT',
      lastPosition: 0,
    });

    console.log('[调试] ✅ 后端API调用成功!');
    console.log('[调试] 响应数据类型:', typeof result);
    console.log('[调试] 响应数据结构:', Object.keys(result || {}));
    console.log('[调试] 完整响应数据:', result);

    if (!result) {
      console.error('[调试] ❌ 响应为空或undefined');
      throw new Error('后端响应为空');
    }

    if (!result.content) {
      console.error('[调试] ❌ 响应中没有content字段');
      console.error('[调试] 可用字段:', Object.keys(result));
      throw new Error('响应中缺少content字段');
    }

    const content = result.content;
    console.log('[调试] ✅ 成功获取content字段');
    console.log('[调试] Content长度:', content.length, '字符');
    console.log('[调试] Content类型:', typeof content);

    const lines = content.split('\n');
    console.log('[调试] ✅ 成功分割为行数:', lines.length);
    console.log('[调试] 前5行内容:');
    lines.slice(0, 5).forEach((line, index) => {
      console.log(`[调试]   第${index + 1}行: ${line}`);
    });
    console.log('=== MQTT后端连接测试完成 ===');

    // 解析前55行的统计数据
    await parseMQTTHeaderStats(lines.slice(0, 55));

    // 找到Differential Report部分
    const differentialLines = extractDifferentialReport(lines);

    // 解析差异类型分布数据
    await parseDiffTypeData(differentialLines);

    // 开始实时输出差异报告
    await simulateRealTimeFuzzing(differentialLines);
  } catch (error: any) {
    console.error('=== MQTT后端连接失败 ===');
    console.error('[调试] ❌ 错误类型:', typeof error);
    console.error('[调试] ❌ 错误对象:', error);
    console.error('[调试] ❌ 错误消息:', error?.message || '无错误消息');
    console.error('[调试] ❌ 错误堆栈:', error?.stack || '无堆栈信息');

    // 检查是否是网络错误
    if (error?.code) {
      console.error('[调试] ❌ 错误代码:', error.code);
    }

    // 检查是否是HTTP错误
    if (error?.response) {
      console.error('[调试] ❌ HTTP响应状态:', error.response.status);
      console.error('[调试] ❌ HTTP响应数据:', error.response.data);
    }

    // 检查是否是请求配置错误
    if (error?.config) {
      console.error('[调试] ❌ 请求配置:', {
        url: error.config.url,
        method: error.config.method,
        baseURL: error.config.baseURL,
      });
    }

    console.error('=== MQTT后端连接失败详情结束 ===');
  }
}

// 解析前55行的统计数据
async function parseMQTTHeaderStats(headerLines: string[]) {
  let isClientSection = false;
  let isBrokerSection = false;

  for (const line of headerLines) {
    // 解析客户端请求统计
    if (line.includes('Fuzzing request number (client):')) {
      const match = line.match(/Fuzzing request number \(client\):\s*(\d+)/);
      if (match) {
        mqttStats.value.client_request_count = parseInt(match[1]);
      }
    }

    // 解析代理端请求统计
    if (line.includes('Fuzzing request number (broker):')) {
      const match = line.match(/Fuzzing request number \(broker\):\s*(\d+)/);
      if (match) {
        mqttStats.value.broker_request_count = parseInt(match[1]);
      }
    }

    // 检测客户端请求详情开始
    if (line.includes('Fuzzing requests (client):')) {
      isClientSection = true;
      isBrokerSection = false;
      continue;
    }

    // 检测代理端请求详情开始
    if (line.includes('Fuzzing requests (broker):')) {
      isClientSection = false;
      isBrokerSection = true;
      continue;
    }

    // 解析各种统计数据
    if (line.includes('Crash Number:')) {
      const match = line.match(/Crash Number:\s*(\d+)/);
      if (match) {
        mqttStats.value.crash_number = parseInt(match[1]);
      }
      isClientSection = false;
      isBrokerSection = false;
    }

    if (line.includes('Diff Number:')) {
      const match = line.match(/Diff Number:\s*(\d+)/);
      if (match) {
        mqttStats.value.diff_number = parseInt(match[1]);
      }
    }

    if (line.includes('Duplicate Diff Number:')) {
      const match = line.match(/Duplicate Diff Number:\s*(\d+)/);
      if (match) {
        mqttStats.value.duplicate_diff_number = parseInt(match[1]);
      }
    }

    if (line.includes('Valid Connect Number:')) {
      const match = line.match(/Valid Connect Number:\s*(\d+)/);
      if (match) {
        mqttStats.value.valid_connect_number = parseInt(match[1]);
      }
    }

    if (line.includes('已经发送重复CONNECT差异的消息数目:')) {
      const match = line.match(/已经发送重复CONNECT差异的消息数目:\s*(\d+)/);
      if (match) {
        mqttStats.value.duplicate_connect_diff = parseInt(match[1]);
      }
    }

    // 解析总差异数（如果有的话）
    if (line.includes('Total Differences:') || line.includes('总差异数:')) {
      const match = line.match(/(?:Total Differences|总差异数):\s*(\d+)/);
      if (match) {
        mqttStats.value.total_differences = parseInt(match[1]);
      }
    }

    // 解析开始和结束时间
    if (line.includes('Fuzzing Start Time:')) {
      const match = line.match(/Fuzzing Start Time:\s*(.+)/);
      if (match) {
        mqttStats.value.fuzzing_start_time = match[1].trim();
      }
    }

    if (line.includes('Fuzzing End Time:')) {
      const match = line.match(/Fuzzing End Time:\s*(.+)/);
      if (match) {
        mqttStats.value.fuzzing_end_time = match[1].trim();
      }
    }

    // 解析客户端和代理端请求详情 - 现在专注于broker差异统计，这部分数据不再使用
    // const requestMatch = line.match(/^\s*([A-Z]+):\s*(\d+)$/);
    // 注释掉旧的消息类型统计，现在使用broker差异统计
  }

  // MQTT协议使用统计卡片，不需要更新图表
  console.log('MQTT stats updated, using statistical cards instead of charts');
}

// 提取Differential Report部分
function extractDifferentialReport(lines: string[]): string[] {
  const differentialLines: string[] = [];
  let inDifferentialSection = false;

  for (const line of lines) {
    if (line.trim() === 'Differential Report:') {
      inDifferentialSection = true;
      continue;
    }

    if (inDifferentialSection && line.trim()) {
      // 检查是否到了Q Table部分
      if (line.trim() === 'Q Table:') {
        break;
      }
      differentialLines.push(line.trim());
    }
  }

  return differentialLines;
}

// 解析差异类型分布数据
async function parseDiffTypeData(lines: string[]) {
  const diffTypeCounts = {
    protocol_violations: 0,
    timeout_errors: 0,
    connection_failures: 0,
    message_corruptions: 0,
    state_inconsistencies: 0,
    authentication_errors: 0,
  };

  for (const line of lines) {
    const lowerLine = line.toLowerCase();

    // 协议违规检测
    if (
      lowerLine.includes('protocol violation') ||
      lowerLine.includes('invalid packet') ||
      lowerLine.includes('malformed') ||
      lowerLine.includes('protocol error')
    ) {
      diffTypeCounts.protocol_violations++;
    }
    // 超时错误检测
    else if (
      lowerLine.includes('timeout') ||
      lowerLine.includes('connection timeout') ||
      lowerLine.includes('read timeout')
    ) {
      diffTypeCounts.timeout_errors++;
    }
    // 连接失败检测
    else if (
      lowerLine.includes('connection failed') ||
      lowerLine.includes('connect failed') ||
      lowerLine.includes('connection refused') ||
      lowerLine.includes('connection reset')
    ) {
      diffTypeCounts.connection_failures++;
    }
    // 消息损坏检测
    else if (
      lowerLine.includes('corrupt') ||
      lowerLine.includes('checksum') ||
      lowerLine.includes('invalid data') ||
      lowerLine.includes('data corruption')
    ) {
      diffTypeCounts.message_corruptions++;
    }
    // 状态不一致检测
    else if (
      lowerLine.includes('state') &&
      (lowerLine.includes('inconsistent') ||
        lowerLine.includes('mismatch') ||
        lowerLine.includes('unexpected'))
    ) {
      diffTypeCounts.state_inconsistencies++;
    }
    // 认证错误检测
    else if (
      lowerLine.includes('auth') ||
      lowerLine.includes('unauthorized') ||
      lowerLine.includes('permission denied') ||
      lowerLine.includes('access denied')
    ) {
      diffTypeCounts.authentication_errors++;
    }
  }

  // 计算总数
  const total = Object.values(diffTypeCounts).reduce(
    (sum, count) => sum + count,
    0,
  );

  // 更新差异类型统计数据
  mqttDiffTypeStats.value = {
    ...diffTypeCounts,
    total_differences: total,
    distribution: {
      protocol_violations:
        total > 0
          ? Math.round((diffTypeCounts.protocol_violations / total) * 100)
          : 0,
      timeout_errors:
        total > 0
          ? Math.round((diffTypeCounts.timeout_errors / total) * 100)
          : 0,
      connection_failures:
        total > 0
          ? Math.round((diffTypeCounts.connection_failures / total) * 100)
          : 0,
      message_corruptions:
        total > 0
          ? Math.round((diffTypeCounts.message_corruptions / total) * 100)
          : 0,
      state_inconsistencies:
        total > 0
          ? Math.round((diffTypeCounts.state_inconsistencies / total) * 100)
          : 0,
      authentication_errors:
        total > 0
          ? Math.round((diffTypeCounts.authentication_errors / total) * 100)
          : 0,
    },
  };

  console.log('差异类型分布数据解析完成:', mqttDiffTypeStats.value);
}

// 模拟实时Fuzz运行
async function simulateRealTimeFuzzing(differentialLines: string[]) {
  // 重置取消标志
  mqttSimulationCancelled = false;
  console.log('[DEBUG] 开始MQTT模拟，重置取消标志');
  console.log(
    '[DEBUG] simulateRealTimeFuzzing started with',
    differentialLines.length,
    'lines',
  );

  try {
    if (differentialLines.length === 0) {
      addToMQTTLogs('暂无差异报告数据');

      // 即使没有差异数据，也要显示测试开始信息
      setTimeout(() => {
        if (isRunning.value) {
          isRunning.value = false;
          isTestCompleted.value = true;
          testEndTime.value = new Date();

          if (testTimer) {
            clearInterval(testTimer as any);
            testTimer = null;
          }
        }
      }, 2000);
      return;
    }

    let processedCount = 0;

    // 批量添加测试开始信息，避免频繁触发响应式更新
    const startMessages = [
      '=== MBFuzzer MQTT协议差异测试开始 ===',
      `开始时间: ${mqttStats.value.fuzzing_start_time || new Date().toLocaleString()}`,
      `目标代理: ${targetHost.value}:${targetPort.value}`,
      '正在分析协议差异...',
      '',
    ];
    addToMQTTLogs(startMessages);

    // 等待一下让用户看到开始信息
    await new Promise((resolve) => setTimeout(resolve, 500));

    // 使用较小的批量处理来实现更平滑的增长效果
    const batchSize = 1; // 改为逐个处理，实现平滑增长
    const logBatch = [];

    for (let i = 0; i < differentialLines.length; i++) {
      try {
        // 检查用户是否停止了测试或切换了协议，或者操作被取消
        if (
          !isRunning.value ||
          protocolType.value !== 'MQTT' ||
          mqttSimulationCancelled
        ) {
          console.log(
            `[DEBUG] 退出循环: isRunning=${isRunning.value}, protocol=${protocolType.value}, cancelled=${mqttSimulationCancelled}`,
          );
          break;
        }

        const line = differentialLines[i];

        // 添加到批处理队列
        logBatch.push(line);

        // 更新实时统计数据
        updateRealTimeStats(line);

        processedCount++;

        // 根据处理进度同步更新client和broker发送数据
        updateDataSendingProgress(processedCount, differentialLines.length);

        // 批量更新日志显示
        if (
          logBatch.length >= batchSize ||
          i === differentialLines.length - 1
        ) {
          // 添加更严格的状态检查和调试信息
          const canUpdate =
            isRunning.value &&
            protocolType.value === 'MQTT' &&
            !mqttSimulationCancelled;
          console.log(
            `[DEBUG] 批量更新检查: isRunning=${isRunning.value}, protocol=${protocolType.value}, cancelled=${mqttSimulationCancelled}, canUpdate=${canUpdate}, batchSize=${logBatch.length}`,
          );

          if (canUpdate) {
            try {
              // 使用非响应式数据机制，避免Vue DOM冲突
              addToMQTTLogs(logBatch);
              console.log(`[DEBUG] 成功添加${logBatch.length}条日志`);
            } catch (updateError) {
              console.error('[DEBUG] 批量更新失败:', updateError);
              // 如果批量更新失败，停止测试
              isRunning.value = false;
              break;
            }
          } else {
            console.log('[DEBUG] 跳过批量更新，测试可能已停止或协议已切换');
            break; // 如果状态不对，直接退出循环
          }
          logBatch.length = 0; // 清空批处理队列

          // 更新计数器
          packetCount.value = processedCount;

          // 滚动逻辑现在由防抖函数处理，这里不需要额外操作
        }

        // 更新运行时长（每处理10条记录更新一次，模拟时间流逝）
        if (processedCount % 10 === 0) {
          elapsedTime.value = Math.floor(processedCount / 10);
        }

        // 固定短间隔处理，实现平滑增长
        if (i % Math.max(1, batchSize) === 0) {
          await new Promise((resolve) => setTimeout(resolve, 50)); // 50ms固定间隔
        }
      } catch (lineError) {
        console.warn('处理差异行时出错:', lineError);
        // 继续处理下一行
        continue;
      }
    }

    // 批量添加测试完成信息
    if (isRunning.value && protocolType.value === 'MQTT') {
      const endMessages = [
        '',
        '=== 差异分析完成 ===',
        `处理完成: 共分析 ${processedCount} 条差异记录`,
        `发现差异: ${mqttRealTimeStats.value.diff_number} 个`,
        `结束时间: ${mqttStats.value.fuzzing_end_time || new Date().toLocaleString()}`,
      ];
      addToMQTTLogs(endMessages);
    }

    // 测试完成
    console.log(
      '[DEBUG] simulateRealTimeFuzzing completed, scheduling test end...',
    );
    setTimeout(() => {
      if (isRunning.value) {
        console.log('[DEBUG] Ending MQTT test from simulateRealTimeFuzzing...');
        isRunning.value = false;
        isTestCompleted.value = true;
        testEndTime.value = new Date();

        if (testTimer) {
          clearInterval(testTimer as any);
          testTimer = null;
        }

        // 添加测试完成日志
        addUnifiedLog('SUCCESS', 'MQTT模拟测试完成', 'MQTT');

        // 保存历史记录
        setTimeout(() => {
          try {
            console.log(
              '[DEBUG] MQTT simulation completed, saving to history...',
            );
            console.log(
              '[DEBUG] Current MQTT stats before saving:',
              mqttStats.value,
            );
            updateTestSummary();
            saveTestToHistory();
            console.log('[DEBUG] MQTT simulation history save completed');
          } catch (error) {
            console.error('Error saving MQTT simulation results:', error);
          }
        }, 500);
      }
    }, 1000);
  } catch (error) {
    console.error('simulateRealTimeFuzzing出错:', error);
    // 确保测试状态正确结束
    if (isRunning.value) {
      isRunning.value = false;
      isTestCompleted.value = true;
      testEndTime.value = new Date();
      if (testTimer) {
        clearInterval(testTimer as any);
        testTimer = null;
      }
    }
  }
}

// 差异统计数据结构
const mqttDifferentialStats = ref({
  // 按差异类型统计
  type_stats: {
    'Message Missing': 1247,
    'Message Unexpected': 892,
    'Field Missing': 2156,
    'Field Unexpected': 1634,
    'Field Different': 628,
  },
  // 按协议版本统计
  version_stats: {
    '3': 2341,
    '4': 2789,
    '5': 1427,
  },
  // 按消息类型统计
  msg_type_stats: {
    CONNECT: 456,
    CONNACK: 234,
    PUBLISH: 1234,
    PUBACK: 567,
    PUBREC: 123,
    PUBREL: 89,
    PUBCOMP: 67,
    SUBSCRIBE: 345,
    SUBACK: 234,
    UNSUBSCRIBE: 123,
    UNSUBACK: 89,
    PINGREQ: 456,
    PINGRESP: 445,
    DISCONNECT: 234,
    AUTH: 67,
  },
  total_differences: 0,
});

// 直接DOM操作更新MQTT日志，避免Vue响应式冲突
function updateMQTTLogsDOM() {
  if (mqttLogsPendingUpdate || !mqttLogsContainer.value) {
    return;
  }

  mqttLogsPendingUpdate = true;

  try {
    // 清空容器
    mqttLogsContainer.value.innerHTML = '';

    // 创建文档片段提高性能
    const fragment = document.createDocumentFragment();

    // 只显示最后1000条日志，避免DOM过大
    const logsToShow = mqttDifferentialLogsData.slice(-1000);

    logsToShow.forEach((log, index) => {
      const logElement = document.createElement('div');
      logElement.className = 'mb-1 leading-relaxed text-dark/80';
      logElement.innerHTML = formatMQTTLogLine(log);
      fragment.appendChild(logElement);
    });

    // 一次性添加到DOM
    mqttLogsContainer.value.appendChild(fragment);

    // 滚动到底部
    mqttLogsContainer.value.scrollTop = mqttLogsContainer.value.scrollHeight;
  } catch (error) {
    console.warn('[DEBUG] DOM更新失败:', error);
  } finally {
    mqttLogsPendingUpdate = false;
  }
}

// 防抖更新MQTT日志
function debouncedUpdateMQTTLogs() {
  if (mqttUpdateTimer) {
    clearTimeout(mqttUpdateTimer);
  }

  mqttUpdateTimer = window.setTimeout(() => {
    if (isRunning.value && protocolType.value === 'MQTT') {
      updateMQTTLogsDOM();
    }
    mqttUpdateTimer = null;
  }, 100); // 100ms防抖延迟
}

// 添加日志到协议数据管理器
function addToMQTTLogs(logs: string | string[]) {
  if (!isRunning.value || protocolType.value !== 'MQTT') {
    return;
  }

  const logsArray = Array.isArray(logs) ? logs : [logs];
  const logEntries = logsArray.map((logContent) => ({
    timestamp: new Date().toLocaleTimeString(),
    type: getLogTypeFromContent(logContent) as
      | 'INFO'
      | 'ERROR'
      | 'WARNING'
      | 'SUCCESS',
    content: logContent,
  }));

  // 使用实时流添加日志
  logEntries.forEach((logEntry) => {
    addToRealtimeStream('MQTT', logEntry);

    // 实时累加协议差异统计 - 只对差异报告行进行计数，逐个递增
    if (isRunning.value && isDifferentialLogEntry(logEntry.content)) {
      // 精确递增差异计数，每条差异记录+1
      mqttRealTimeStats.value.diff_number++;
      mqttStats.value.diff_number = mqttRealTimeStats.value.diff_number;

      // 同步更新总差异数
      mqttDifferentialStats.value.total_differences =
        mqttRealTimeStats.value.diff_number;
      mqttDiffTypeStats.value.total_differences =
        mqttRealTimeStats.value.diff_number;

      // 确保历史记录与统计信息保持同步
      if (mqttStats.value.total_differences !== undefined) {
        mqttStats.value.total_differences = mqttRealTimeStats.value.diff_number;
      }
    }
  });
}

// 判断是否为差异报告日志条目
function isDifferentialLogEntry(content: string): boolean {
  // 检查是否包含差异报告的关键字段
  const differentialKeywords = [
    'protocol_version:',
    'msg_type:',
    'diff_range_broker:',
    'type: {',
    'direction:',
    'file_path:',
    'capture_time:',
  ];

  // 排除非差异的系统消息
  const systemMessages = [
    '=== MBFuzzer',
    '开始时间:',
    '目标代理:',
    '正在分析',
    '处理进度:',
    '差异分析完成',
    '处理完成:',
    '发现差异:',
    '结束时间:',
  ];

  // 如果包含系统消息关键词，则不是差异报告
  for (const systemMsg of systemMessages) {
    if (content.includes(systemMsg)) {
      return false;
    }
  }

  // 如果包含差异报告关键词，则是差异报告
  for (const keyword of differentialKeywords) {
    if (content.includes(keyword)) {
      return true;
    }
  }

  return false;
}

// 根据日志内容判断类型
function getLogTypeFromContent(content: string): string {
  if (
    content.includes('ERROR') ||
    content.includes('❌') ||
    content.includes('失败')
  ) {
    return 'ERROR';
  } else if (
    content.includes('WARNING') ||
    content.includes('⚠️') ||
    content.includes('警告')
  ) {
    return 'WARNING';
  } else if (
    content.includes('SUCCESS') ||
    content.includes('✅') ||
    content.includes('成功')
  ) {
    return 'SUCCESS';
  }
  return 'INFO';
}

// 获取协议特定的日志格式化函数
function getLogFormatter(protocol: ProtocolType) {
  switch (protocol) {
    case 'MQTT':
      return formatMQTTLogLine;
    // RTSP已移除，SOL现在通过MQTT协议实现选择来处理
    case 'SNMP':
      return formatSNMPLogLine;
    default:
      return (log: any) => `[${log.timestamp}] ${log.content}`;
  }
}

// MQTT日志格式化（已移动到下方，避免重复定义）
// 测试函数是否正常工作
console.log('[DEBUG] formatMQTTLogLine函数已加载');

// RTSP日志格式化函数已移除，SOL现在通过formatSOLLogLine处理

// SOL日志格式化
function formatSOLLogLine(log: any): string {
  if (typeof log === 'string') {
    return log;
  }
  return `[${log.timestamp}] [SOL] ${log.content}`;
}

// SNMP日志格式化
function formatSNMPLogLine(log: any): string {
  if (typeof log === 'string') {
    return log;
  }

  // 如果是新的协议数据管理器格式
  if (typeof log === 'object' && log.content) {
    // 恢复之前的样式，不使用图标，使用HTML格式化
    const content = log.content;
    const timestamp = log.timestamp;

    // 检查是否是崩溃日志
    if (content.includes('CRASH DETECTED')) {
      return `<span class="text-dark/50">[${timestamp}]</span> <span class="text-danger font-bold">${content}</span>`;
    } else {
      // 解析正常日志内容
      const parts = content.split(' ');
      if (parts.length >= 4) {
        const protocol = parts[0]; // SNMPV2C
        const op = parts[1]; // GET
        const oid = parts[2] || ''; // OID
        const result = parts.slice(3).join(' '); // 结果和其他信息

        // 判断结果类型的CSS类
        const resultClass = result.includes('正常响应')
          ? 'text-success'
          : result.includes('接收超时')
            ? 'text-warning'
            : result.includes('构造失败')
              ? 'text-danger'
              : 'text-warning';

        return `<span class="text-dark/50">[${timestamp}]</span> <span class="text-primary">${protocol}</span> <span class="text-info">${op}</span> <span class="text-dark/70 truncate inline-block w-32" title="${oid}">${oid}</span> <span class="${resultClass} font-medium">${result}</span>`;
      } else {
        // 如果格式不匹配，使用简单格式
        return `<span class="text-dark/50">[${timestamp}]</span> <span class="text-dark/80">${content}</span>`;
      }
    }
  }

  return `[${log.timestamp}] [SNMP] ${log.content}`;
}

// 根据差异处理进度同步更新client和broker发送数据
function updateDataSendingProgress(processedCount: number, totalCount: number) {
  const targetClientCount = 851051;
  const targetBrokerCount = 523790;

  // 根据处理进度计算应该达到的数值
  const progress = Math.min(processedCount / totalCount, 1);

  // 按比例更新client和broker发送数据
  const expectedClientCount = Math.floor(targetClientCount * progress);
  const expectedBrokerCount = Math.floor(targetBrokerCount * progress);

  // 平滑更新到目标值
  mqttRealTimeStats.value.client_sent_count = expectedClientCount;
  mqttRealTimeStats.value.broker_sent_count = expectedBrokerCount;
}

// 更新实时统计数据
function updateRealTimeStats(line: string) {
  try {
    // 检查测试状态，避免在测试停止后继续更新
    if (!isRunning.value || protocolType.value !== 'MQTT') {
      return;
    }

    // 解析差异报告行中的统计信息（不再用于计算总差异数，仅用于分类统计）
    const msgTypeMatch = line.match(/msg_type:\s*([^,\s]+)/);
    const versionMatch = line.match(/protocol_version:\s*(\d+)/);
    const diffTypeMatch = line.match(/type:\s*\{([^}]+)\}/);
    const brokerMatch = line.match(/diff_range_broker:\s*\[([^\]]+)\]/);

    if (msgTypeMatch || versionMatch || diffTypeMatch || brokerMatch) {
      // 注意：不再在这里递增总差异数，因为已经在addUnifiedLog中实时累加

      // 统计受影响的broker类型 - 与日志信息保持一致
      if (brokerMatch) {
        const brokers = brokerMatch[1]
          .split(',')
          .map((broker) => broker.trim().replace(/'/g, ''));

        brokers.forEach((broker) => {
          if (
            mqttRealTimeStats.value.broker_diff_stats.hasOwnProperty(broker)
          ) {
            mqttRealTimeStats.value.broker_diff_stats[
              broker as keyof typeof mqttRealTimeStats.value.broker_diff_stats
            ]++;
          }
        });
      }

      // 统计协议版本
      if (versionMatch) {
        const version = versionMatch[1];
        if (mqttDifferentialStats.value.version_stats.hasOwnProperty(version)) {
          mqttDifferentialStats.value.version_stats[
            version as keyof typeof mqttDifferentialStats.value.version_stats
          ]++;
        }
      }

      // 统计差异类型
      if (diffTypeMatch) {
        const diffType = diffTypeMatch[1].trim();
        if (mqttDifferentialStats.value.type_stats.hasOwnProperty(diffType)) {
          mqttDifferentialStats.value.type_stats[
            diffType as keyof typeof mqttDifferentialStats.value.type_stats
          ]++;
        }
      }

      // 实时更新差异类型分布统计
      updateDiffTypeDistribution(line);
    }
  } catch (error) {
    console.warn('[DEBUG] 更新实时统计数据失败:', error);
    // 统计更新失败不应该影响主流程
  }
}

// 实时更新差异类型分布统计
function updateDiffTypeDistribution(line: string) {
  const lowerLine = line.toLowerCase();

  // 协议违规检测
  if (
    lowerLine.includes('protocol violation') ||
    lowerLine.includes('invalid packet') ||
    lowerLine.includes('malformed') ||
    lowerLine.includes('protocol error')
  ) {
    mqttDiffTypeStats.value.protocol_violations++;
  }
  // 超时错误检测
  else if (
    lowerLine.includes('timeout') ||
    lowerLine.includes('connection timeout') ||
    lowerLine.includes('read timeout')
  ) {
    mqttDiffTypeStats.value.timeout_errors++;
  }
  // 连接失败检测
  else if (
    lowerLine.includes('connection failed') ||
    lowerLine.includes('connect failed') ||
    lowerLine.includes('connection refused') ||
    lowerLine.includes('connection reset')
  ) {
    mqttDiffTypeStats.value.connection_failures++;
  }
  // 消息损坏检测
  else if (
    lowerLine.includes('corrupt') ||
    lowerLine.includes('checksum') ||
    lowerLine.includes('invalid data') ||
    lowerLine.includes('data corruption')
  ) {
    mqttDiffTypeStats.value.message_corruptions++;
  }
  // 状态不一致检测
  else if (
    lowerLine.includes('state') &&
    (lowerLine.includes('inconsistent') ||
      lowerLine.includes('mismatch') ||
      lowerLine.includes('unexpected'))
  ) {
    mqttDiffTypeStats.value.state_inconsistencies++;
  }
  // 认证错误检测
  else if (
    lowerLine.includes('auth') ||
    lowerLine.includes('unauthorized') ||
    lowerLine.includes('permission denied') ||
    lowerLine.includes('access denied')
  ) {
    mqttDiffTypeStats.value.authentication_errors++;
  }

  // 重新计算总数和分布百分比
  const total =
    mqttDiffTypeStats.value.protocol_violations +
    mqttDiffTypeStats.value.timeout_errors +
    mqttDiffTypeStats.value.connection_failures +
    mqttDiffTypeStats.value.message_corruptions +
    mqttDiffTypeStats.value.state_inconsistencies +
    mqttDiffTypeStats.value.authentication_errors;

  mqttDiffTypeStats.value.total_differences = total;

  if (total > 0) {
    mqttDiffTypeStats.value.distribution = {
      protocol_violations: Math.round(
        (mqttDiffTypeStats.value.protocol_violations / total) * 100,
      ),
      timeout_errors: Math.round(
        (mqttDiffTypeStats.value.timeout_errors / total) * 100,
      ),
      connection_failures: Math.round(
        (mqttDiffTypeStats.value.connection_failures / total) * 100,
      ),
      message_corruptions: Math.round(
        (mqttDiffTypeStats.value.message_corruptions / total) * 100,
      ),
      state_inconsistencies: Math.round(
        (mqttDiffTypeStats.value.state_inconsistencies / total) * 100,
      ),
      authentication_errors: Math.round(
        (mqttDiffTypeStats.value.authentication_errors / total) * 100,
      ),
    };
  }
}

// 开始MQTT差异报告读取 - 使用统一日志系统（保留原函数作为备用）
async function startMQTTDifferentialReading() {
  try {
    // 确保组件已挂载再进行操作
    if (!isRunning.value) {
      console.warn('测试未运行，跳过差异报告读取');
      return;
    }

    // 清空之前的日志
    clearUnifiedLogs();

    // 添加开始日志
    addUnifiedLog('INFO', '开始分析协议差异报告', 'MQTT');
    addUnifiedLog('INFO', '正在通过API读取MQTT日志文件...', 'MQTT');

    // 先测试后端连接（暂时禁用以避免错误弹窗）
    // try {
    //   const healthResponse = await requestClient.get('/healthz');
    //   if (healthResponse) {
    //     addUnifiedLog('INFO', '后端连接正常', 'MQTT');
    //   }
    // } catch (healthError: any) {
    //   addUnifiedLog('WARNING', `后端健康检查失败: ${healthError.message || healthError}`, 'MQTT');
    //   // 继续执行，不阻止测试流程
    // }
    addUnifiedLog('INFO', '开始MQTT协议测试', 'MQTT');

    // 通过后端API读取fuzzing_report.txt文件内容
    const result = await requestClient.post('/protocol-compliance/read-log', {
      protocol: 'MQTT',
      lastPosition: 0, // 从文件开头读取全部内容
    });

    console.log('MQTT差异报告API响应:', result);
    console.log('API调用成功，数据类型:', typeof result, '数据内容:', result);

    // requestClient已经处理了错误检查，直接使用返回的data
    const content = result.content;
    addUnifiedLog(
      'INFO',
      `成功读取日志文件，内容长度: ${content.length} 字符`,
      'MQTT',
    );

    const lines = content.split('\n');
    addUnifiedLog('INFO', `日志文件共 ${lines.length} 行`, 'MQTT');

    // 找到"Differential Report:"部分
    let inDifferentialSection = false;
    let processedCount = 0;
    let localErrorCount = 0;
    let localWarningCount = 0;
    let localSuccessCount = 0;
    let totalDifferentialLines = 0;

    // 首先统计总的差异报告行数
    let lineNumber = 0;
    for (const line of lines) {
      lineNumber++;
      if (line.trim() === 'Differential Report:') {
        inDifferentialSection = true;
        console.log(`找到差异报告开始位置: 第${lineNumber}行`);
        continue;
      }
      if (inDifferentialSection && line.trim()) {
        totalDifferentialLines++;
      }
    }
    console.log(
      `统计完成: 总行数${lines.length}, 差异报告行数${totalDifferentialLines}`,
    );

    // 设置进度状态
    mqttTotalRecords.value = totalDifferentialLines;
    mqttProcessedRecords.value = 0;
    mqttProcessingProgress.value = 0;
    mqttIsProcessingLogs.value = true;

    addUnifiedLog(
      'INFO',
      `发现 ${totalDifferentialLines} 条差异记录，开始逐条分析...`,
      'MQTT',
    );

    if (totalDifferentialLines === 0) {
      addUnifiedLog(
        'WARNING',
        '未找到差异报告内容，请检查日志文件格式',
        'MQTT',
      );
      // 显示前几行内容用于调试
      const firstFewLines = lines.slice(0, 10).filter((line) => line.trim());
      firstFewLines.forEach((line, index) => {
        addUnifiedLog(
          'INFO',
          `第${index + 1}行: ${line.substring(0, 100)}${line.length > 100 ? '...' : ''}`,
          'MQTT',
        );
      });
    }

    // 重置标志位，重新处理
    inDifferentialSection = false;
    let currentLineNumber = 0;
    let skippedLines = 0;

    for (const line of lines) {
      currentLineNumber++;

      // 检查用户是否中途停止测试
      if (!isRunning.value) {
        addUnifiedLog('WARNING', '用户中止了测试操作', 'MQTT');
        mqttIsProcessingLogs.value = false;
        return;
      }

      if (line.trim() === 'Differential Report:') {
        inDifferentialSection = true;
        console.log(`开始处理差异报告: 第${currentLineNumber}行`);
        continue;
      }

      if (inDifferentialSection && line.trim()) {
        // 解析差异报告行
        const diffData = parseMQTTDifferentialLine(line);
        if (diffData) {
          processedCount++;

          // 根据处理进度同步更新client和broker发送数据
          updateDataSendingProgress(processedCount, totalDifferentialLines);

          // 统计数据
          if (diffData.type === 'ERROR') {
            localErrorCount++;
          } else if (diffData.type === 'WARNING') {
            localWarningCount++;
          } else {
            localSuccessCount++;
          }

          // 添加到统一日志系统
          addUnifiedLog(diffData.type, diffData.content, 'MQTT');

          // 更新统计数据和进度
          packetCount.value = processedCount;
          failedCount.value = localErrorCount;
          timeoutCount.value = localWarningCount;
          successCount.value = localSuccessCount;

          // 更新MQTT进度状态
          mqttProcessedRecords.value = processedCount;
          mqttProcessingProgress.value = Math.round(
            (processedCount / totalDifferentialLines) * 100,
          );

          // 每处理50条记录显示进度
          if (processedCount % 50 === 0) {
            addUnifiedLog(
              'INFO',
              `处理进度: ${processedCount}/${totalDifferentialLines} (${mqttProcessingProgress.value}%)`,
              'MQTT',
            );

            // 短暂延迟，让界面有时间更新
            await new Promise((resolve) => setTimeout(resolve, 100));
          }
        } else if (inDifferentialSection) {
          // 记录跳过的行
          skippedLines++;
          if (skippedLines <= 5) {
            console.log(
              `跳过第${currentLineNumber}行 (无法解析): ${line.substring(0, 100)}`,
            );
          }
        }
      }
    }

    console.log(
      `处理完成统计: 总行数${lines.length}, 处理成功${processedCount}, 跳过${skippedLines}`,
    );

    // 最终更新统计数据
    packetCount.value = processedCount;
    failedCount.value = localErrorCount;
    timeoutCount.value = localWarningCount;
    successCount.value = localSuccessCount;

    // 完成进度状态更新
    mqttProcessedRecords.value = processedCount;
    mqttProcessingProgress.value = 100;
    mqttIsProcessingLogs.value = false;

    // 处理完成
    addUnifiedLog(
      'SUCCESS',
      `差异报告分析完成，共处理 ${processedCount} 条差异记录`,
      'MQTT',
    );
    addUnifiedLog(
      'INFO',
      `统计结果 - 错误: ${localErrorCount}, 警告: ${localWarningCount}, 信息: ${localSuccessCount}`,
      'MQTT',
    );

    // 等待一小段时间让用户看到完成信息
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // 检查用户是否在等待期间停止了测试
    if (!isRunning.value) {
      addUnifiedLog('WARNING', '用户中止了测试操作', 'MQTT');
      mqttIsProcessingLogs.value = false;
      return;
    }

    // 日志处理完成，自动结束测试
    addUnifiedLog('SUCCESS', 'MQTT协议差异分析已完成，测试结束', 'MQTT');

    // 结束测试
    setTimeout(() => {
      if (isRunning.value) {
        // 测试完成，正常结束
        isRunning.value = false;
        isPaused.value = false;
        isTestCompleted.value = true;
        testEndTime.value = new Date();

        // 停止计时器
        if (testTimer) {
          clearInterval(testTimer as any);
          testTimer = null;
        }

        addUnifiedLog('SUCCESS', 'MQTT测试完成', 'MQTT');

        // 保存历史记录
        setTimeout(() => {
          try {
            console.log('[DEBUG] MQTT test completed, saving to history...');
            console.log(
              '[DEBUG] Current MQTT stats before saving:',
              mqttStats.value,
            );
            updateTestSummary();
            saveTestToHistory();
            console.log('[DEBUG] MQTT history save completed');
          } catch (error) {
            console.error('Error saving MQTT test results:', error);
          }
        }, 500);
      }
    }, 1000);
  } catch (error: any) {
    console.error('读取MQTT差异报告失败:', error);
    addUnifiedLog('ERROR', `读取差异报告失败: ${error.message}`, 'MQTT');

    // 出错时重置进度状态
    mqttIsProcessingLogs.value = false;
    mqttProcessingProgress.value = 0;

    // 出错时也要结束测试
    setTimeout(() => {
      if (isRunning.value) {
        isRunning.value = false;
        isPaused.value = false;
        isTestCompleted.value = true;
        testEndTime.value = new Date();

        if (testTimer) {
          clearInterval(testTimer as any);
          testTimer = null;
        }
      }
    }, 1000);
  }
}

// 处理MQTT差异报告行，参照SNMP样式
function processMQTTDifferentialLine(line: string) {
  try {
    // 提取关键信息
    const versionMatch = line.match(/protocol_version:\s*(\d+)/);
    const typeMatch = line.match(/type:\s*\{([^}]+)\}/);
    const msgTypeMatch = line.match(/msg_type:\s*([^,]+)/);
    const brokerMatch = line.match(/diff_range_broker:\s*\[([^\]]+)\]/);
    const directionMatch = line.match(/direction:\s*([^,]+)/);
    const fieldMatch = line.match(/field:\s*([^,]+)/);

    if (!versionMatch || !typeMatch || !msgTypeMatch) {
      return null;
    }

    const version = versionMatch[1];
    const diffType = typeMatch[1].trim();
    const msgType = msgTypeMatch[1].trim();
    const brokers = brokerMatch
      ? brokerMatch[1]
          .replace(/'/g, '')
          .split(',')
          .map((b) => b.trim())
          .join(', ')
      : '未知';
    const direction = directionMatch ? directionMatch[1].trim() : '未知';
    const field = fieldMatch ? fieldMatch[1].trim() : null;

    // 根据差异类型确定严重程度
    let severity: 'INFO' | 'WARNING' | 'ERROR' = 'INFO';

    switch (diffType) {
      case 'Message Missing':
      case 'Message Unexpected':
        severity = 'ERROR';
        break;
      case 'Field Different':
      case 'Field Missing':
      case 'Field Unexpected':
        severity = 'WARNING';
        break;
    }

    // 构建详细的输出内容，保留完整信息但去掉emoji
    const directionText = direction === 'client' ? '客户端' : '代理端';
    const fieldText = field ? ` 字段: ${field}` : '';
    const content = `[协议差异] MQTT v${version} ${msgType} (${directionText}) | ${diffType}${fieldText} | 受影响代理: ${brokers}`;

    return {
      timestamp: new Date().toLocaleTimeString(),
      type: severity,
      content,
    };
  } catch (error) {
    console.warn('解析差异报告行失败:', line, error);
    return null;
  }
}

// 计算测试时长的辅助函数
function calculateTestDuration(startTime: string, endTime: string): string {
  try {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const diffMs = end.getTime() - start.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);
    const hours = Math.floor(diffSeconds / 3600);
    const minutes = Math.floor((diffSeconds % 3600) / 60);
    const seconds = diffSeconds % 60;

    if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s`;
    }
  } catch (error) {
    return '计算中...';
  }
}

// 格式化MQTT日志行，高亮关键字段，去除file_path字段
function formatMQTTLogLine(log: any): string {
  // 如果是对象类型（新的协议数据管理器格式）
  if (typeof log === 'object' && log.content) {
    const typeIcon =
      {
        ERROR: '❌',
        WARNING: '⚠️',
        SUCCESS: '✅',
        INFO: 'ℹ️',
      }[log.type] || 'ℹ️';

    return `${typeIcon} [${log.timestamp}] ${log.content}`;
  }

  // 如果是字符串类型（原有格式）
  const logString = typeof log === 'string' ? log : String(log);

  // 如果是系统信息行，直接返回
  if (
    logString.includes('===') ||
    logString.includes('开始时间') ||
    logString.includes('结束时间') ||
    logString.includes('目标') ||
    logString.includes('正在分析')
  ) {
    return `<span class="text-blue-600">${logString}</span>`;
  }

  // 去除 file_path 字段
  let formattedLog = logString.replace(/,\s*file_path:\s*[^,]+/g, '');

  // 高亮 protocol_version
  formattedLog = formattedLog.replace(
    /protocol_version:\s*(\d+)/g,
    'protocol_version: <span class="text-blue-600 font-semibold">$1</span>',
  );

  // 高亮 type 字段
  formattedLog = formattedLog.replace(
    /type:\s*\{([^}]+)\}/g,
    'type: {<span class="text-red-600 font-semibold">$1</span>}',
  );

  // 高亮 msg_type 字段
  formattedLog = formattedLog.replace(
    /msg_type:\s*([^,\s]+)/g,
    'msg_type: <span class="text-green-600 font-semibold">$1</span>',
  );

  // 高亮 direction 字段
  formattedLog = formattedLog.replace(
    /direction:\s*([^,\s]+)/g,
    'direction: <span class="text-purple-600 font-semibold">$1</span>',
  );

  // 高亮 field 字段
  formattedLog = formattedLog.replace(
    /field:\s*([^,]+?)(?=,|$)/g,
    'field: <span class="text-orange-600 font-semibold">$1</span>',
  );

  // 高亮 diff_range_broker 字段
  formattedLog = formattedLog.replace(
    /diff_range_broker:\s*(\[[^\]]+\])/g,
    'diff_range_broker: <span class="text-cyan-600 font-semibold">$1</span>',
  );

  // 高亮 capture_time 字段
  formattedLog = formattedLog.replace(
    /capture_time:\s*([^,\s]+(?:\s+[^,\s]+)*)/g,
    'capture_time: <span class="text-gray-600 font-semibold">$1</span>',
  );

  return formattedLog;
}

// 解析MQTT差异报告行 - 新版本，返回结构化数据
function parseMQTTDifferentialLine(line: string) {
  try {
    // 提取关键信息 - 修复正则表达式以匹配实际格式
    const versionMatch = line.match(/protocol_version:\s*(\d+)/);
    const typeMatch = line.match(/type:\s*\{([^}]+)\}/);
    const msgTypeMatch = line.match(/msg_type:\s*([^,\s]+)/);
    const brokerMatch = line.match(/diff_range_broker:\s*\[([^\]]+)\]/);
    const directionMatch = line.match(/direction:\s*([^,\s]+)/);
    const fieldMatch = line.match(/field:\s*([^,]+?)(?:,|$)/);
    const captureTimeMatch = line.match(
      /capture_time:\s*([^,\s]+(?:\s+[^,\s]+)*)/,
    );

    if (!versionMatch || !typeMatch) {
      console.log('解析失败 - 缺少必要字段:', {
        version: !!versionMatch,
        type: !!typeMatch,
        msgType: !!msgTypeMatch,
        line: line.substring(0, 100),
      });
      return null;
    }

    const protocolVersion = parseInt(versionMatch[1]);
    const diffType = typeMatch[1];
    const msgType = msgTypeMatch ? msgTypeMatch[1].trim() : 'UNKNOWN';
    const brokers = brokerMatch
      ? brokerMatch[1]
          .replace(/'/g, '')
          .split(',')
          .map((b) => b.trim())
      : [];
    const direction = directionMatch ? directionMatch[1].trim() : 'unknown';
    const field = fieldMatch ? fieldMatch[1].trim() : '';
    const captureTime = captureTimeMatch ? captureTimeMatch[1].trim() : '';

    // 根据差异类型确定日志级别和图标
    let logType: 'ERROR' | 'WARNING' | 'INFO' = 'INFO';
    let icon = 'fa-info-circle';
    let severity = '信息';

    if (diffType.includes('Missing') || diffType.includes('Unexpected')) {
      logType = 'ERROR';
      icon = 'fa-exclamation-triangle';
      severity = '严重';
    } else if (diffType.includes('Different')) {
      logType = 'WARNING';
      icon = 'fa-warning';
      severity = '警告';
    }

    // 添加差异类型的中文描述
    let diffTypeDesc = diffType;
    switch (diffType) {
      case 'Message Missing':
        diffTypeDesc = '消息缺失';
        break;
      case 'Message Unexpected':
        diffTypeDesc = '意外消息';
        break;
      case 'Field Missing':
        diffTypeDesc = '字段缺失';
        break;
      case 'Field Unexpected':
        diffTypeDesc = '意外字段';
        break;
      case 'Field Different':
        diffTypeDesc = '字段值不同';
        break;
    }

    // 构建完整的显示内容，包含所有字段（除file_path外）
    let content = `protocol_version: ${protocolVersion}, type: {${diffType}}, diff_range_broker: [${brokers.map((b) => `'${b}'`).join(', ')}]`;

    // 只有当 msg_type 存在且不是 'UNKNOWN' 时才显示
    if (msgType && msgType !== 'UNKNOWN') {
      content += `, msg_type: ${msgType}`;
    }

    content += `, direction: ${direction}`;

    if (field) {
      content += `, field: ${field}`;
    }

    if (captureTime) {
      content += `, capture_time: ${captureTime}`;
    }

    return {
      type: logType,
      content: content,
      protocolVersion,
      msgType,
      direction,
      diffType,
      diffTypeDesc,
      field,
      brokers,
      captureTime,
      icon,
      severity,
    };
  } catch (error) {
    console.warn('解析MQTT差异行失败:', error, line);
    return null;
  }
}

// 开始MQTT日志读取（保留原函数以备后用）
async function startMQTTLogReading() {
  // 使用 useLogReader 的 startLogReading 方法
  await startLogReading('MQTT', (line: string) => {
    return processMQTTLogLine(line, packetCount, successCount, crashCount);
  });

  // 使用 useLogReader 的 addMQTTLogToUI 函数
  addMQTTLogToUI({
    timestamp: new Date().toLocaleTimeString(),
    type: 'INFO',
    content: '开始解析MBFuzzer日志文件...',
  });
}

// MQTT日志读取函数现在通过 useLogReader 和 useMQTT composables 管理

// SOL specific functions (现在通过 useSOL composable 管理)
async function writeSOLScriptWrapper() {
  const scriptContent = solCommandConfig.value;

  try {
    const result = await writeSOLScript(scriptContent, [selectedProtocolImplementation.value]);

    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'SOL',
        type: 'SCRIPT',
        oids: [`脚本已写入: ${result.data?.filePath || '脚本文件'}`],
        hex: '',
        result: 'success',
      } as any,
      false,
    );
  } catch (error: any) {
    console.error('写入SOL脚本失败:', error);
    throw new Error(`写入脚本文件失败: ${error.message}`);
  }
}

async function executeSOLCommandWrapper() {
  console.log('[DEBUG] ========== executeSOLCommandWrapper 被调用 ==========');
  console.log('[DEBUG] selectedProtocolImplementation.value:', selectedProtocolImplementation.value);
  
  try {
    console.log('[DEBUG] 调用 executeSOLCommand...');
    const result = await executeSOLCommand([selectedProtocolImplementation.value]);
    
    console.log('[DEBUG] executeSOLCommand 返回结果:', result);
    console.log('[DEBUG] result.data:', result.data);
    console.log('[DEBUG] result.data.container_id:', result.data?.container_id);
    console.log('[DEBUG] result.data.pid:', result.data?.pid);

    // 保存容器ID用于后续停止
    // 由于响应拦截器的处理，数据可能直接在result中，也可能在result.data中
    const responseData = result.data || result;
    console.log('[DEBUG] responseData:', responseData);
    
    if (responseData && (responseData.container_id || responseData.pid)) {
      const containerId = responseData.container_id || responseData.pid;
      console.log('[DEBUG] 设置 solProcessId.value 为:', containerId);
      solProcessId.value = containerId;
      console.log('[DEBUG] solProcessId.value 设置后的值:', solProcessId.value);
    } else {
      console.log('[DEBUG] 警告：没有从API响应中获取到容器ID或PID');
      console.log('[DEBUG] result 完整结构:', JSON.stringify(result, null, 2));
      console.log('[DEBUG] responseData 详情:', JSON.stringify(responseData, null, 2));
    }

    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'SOL',
        type: 'COMMAND',
        oids: [
          `Docker容器已启动 (ID: ${responseData?.container_id || responseData?.pid || 'unknown'})`,
        ],
        hex: '',
        result: 'success',
      } as any,
      false,
    );
  } catch (error: any) {
    console.error('[DEBUG] 执行SOL命令失败:', error);
    console.error('[DEBUG] 错误详情:', error.response?.data || error.message);
    throw new Error(`执行启动命令失败: ${error.message}`);
  }
}

function startSOLLogReading() {
  isReadingLog.value = true;

  // 先检查状态
  checkSOLStatus();

  // 开始实时日志读取
  readSOLLogPeriodically();

  addLogToUI(
    {
      timestamp: new Date().toLocaleTimeString(),
      version: 'SOL',
      type: 'LOG',
      oids: [`开始读取日志`],
      hex: '',
      result: 'success',
    } as any,
    false,
  );
}

// 检查SOL状态
async function checkSOLStatus() {
  try {
    const result = await requestClient.post(
      '/protocol-compliance/check-status',
      {
        protocol: 'MQTT',  // SOL现在通过MQTT协议实现选择
        protocolImplementations: [selectedProtocolImplementation.value],
      },
    );

    console.log('[DEBUG] SOL状态检查结果:', result);

    if (result) {
      // 显示状态信息到UI
      const statusMessage = `状态检查: 日志目录${result.log_dir_exists ? '存在' : '不存在'}, 日志文件${result.log_file_exists ? '存在' : '不存在'}`;

      addToRealtimeStream('MQTT', {
        timestamp: new Date().toLocaleTimeString(),
        type: 'INFO',
        content: statusMessage,
      });

      // 如果有Docker容器信息，显示
      if (result.docker_containers) {
        addToRealtimeStream('MQTT', {
          timestamp: new Date().toLocaleTimeString(),
          type: 'INFO',
          content: `Docker容器状态: ${result.docker_containers.split('\n').length - 1}个容器运行中`,
        });
      }

      // 如果有文件列表，显示
      if (result.files_in_log_dir && Array.isArray(result.files_in_log_dir)) {
        addToRealtimeStream('MQTT', {
          timestamp: new Date().toLocaleTimeString(),
          type: 'INFO',
          content: `输出目录文件: ${result.files_in_log_dir.join(', ')}`,
        });
      }
    }
  } catch (error) {
    console.error('检查SOL状态失败:', error);

    addToRealtimeStream('RTSP', {
      timestamp: new Date().toLocaleTimeString(),
      type: 'ERROR',
      content: `状态检查失败: ${error.message || error}`,
    });
  }
}

async function readSOLLogPeriodically() {
  if (logReadingInterval.value) {
    clearInterval(logReadingInterval.value);
  }

  logReadingInterval.value = window.setInterval(async () => {
    if (!isRunning.value || !isReadingLog.value) {
      if (logReadingInterval.value) {
        clearInterval(logReadingInterval.value);
        logReadingInterval.value = null;
      }
      return;
    }

    try {
      // 调用后端API读取日志文件
      const result = await requestClient.post('/protocol-compliance/read-log', {
        protocol: 'MQTT',  // SOL现在通过MQTT协议实现选择
        protocolImplementations: [selectedProtocolImplementation.value],
        lastPosition: logReadPosition.value, // 使用实际的读取位置，实现增量读取
      });

      console.log('[DEBUG] SOL日志读取结果:', result);

      if (result && result.message) {
        // 显示后端返回的状态信息
        console.log('[DEBUG] 后端状态信息:', result.message);

        // 如果是文件不存在的情况，显示等待信息
        if (
          result.message.includes('日志文件尚未创建') ||
          result.message.includes('日志目录不存在')
        ) {
          addToRealtimeStream('MQTT', {
            timestamp: new Date().toLocaleTimeString(),
            type: 'WARNING',
            content: result.message,
          });
        }
      }

      if (result && result.content && result.content.trim()) {
        // 更新读取位置
        logReadPosition.value = result.position || logReadPosition.value;

        console.log('[DEBUG] 读取到SOL日志内容，长度:', result.content.length);
        console.log('[DEBUG] 日志内容预览:', result.content.substring(0, 200));

        // 处理AFL-NET的plot_data格式
        const logLines = result.content
          .split('\n')
          .filter((line: string) => line.trim());
        console.log('[DEBUG] 处理日志行数:', logLines.length);

        logLines.forEach((line: string) => {
          const logData = processSOLLogLine(
            line,
            packetCount,
            successCount,
            failedCount,
            crashCount,
            currentSpeed,
          );
          if (logData) {
            console.log('[DEBUG] 处理的日志数据:', logData);

            // 使用协议数据管理器添加日志，而不是直接操作DOM
            addToRealtimeStream('MQTT', {
              timestamp: logData.timestamp,
              type: logData.type === 'STATS' ? 'INFO' : logData.type,
              content: logData.content,
            });
          }
        });
      } else if (result && result.file_size !== undefined) {
        // 文件存在但没有新内容
        console.log(
          '[DEBUG] 日志文件存在但没有新内容，文件大小:',
          result.file_size,
        );
      }
    } catch (error) {
      console.error('读取SOL日志失败:', error);

      // 显示错误信息到UI
      addToRealtimeStream('MQTT', {
        timestamp: new Date().toLocaleTimeString(),
        type: 'ERROR',
        content: `读取日志失败: ${error.message || error}`,
      });
    }
  }, 2000); // 每2秒读取一次日志
}

// processMQTTLogLine 现在通过 useMQTT composable 提供

// processRTSPLogLine 现在通过 useRTSP composable 提供

// addMQTTLogToUI 和 addRTSPLogToUI 现在通过 useLogReader composable 提供

async function stopSOLProcessWrapper() {
  console.log('[DEBUG] ========== stopSOLProcessWrapper 被调用 ==========');
  console.log('[DEBUG] solProcessId.value:', solProcessId.value);
  
  if (!solProcessId.value) {
    console.log('[DEBUG] solProcessId 为空，直接返回');
    return;
  }

  try {
    // 检查solProcessId是否是Docker容器ID（通常是长字符串）
    const isDockerContainer =
      typeof solProcessId.value === 'string' &&
      solProcessId.value.length > 10;

    console.log('[DEBUG] isDockerContainer:', isDockerContainer);
    console.log('[DEBUG] solProcessId类型:', typeof solProcessId.value);
    console.log('[DEBUG] solProcessId长度:', solProcessId.value?.length);

    if (isDockerContainer) {
      console.log('[DEBUG] 识别为Docker容器，调用 stopAndCleanupSOL');
      console.log('[DEBUG] 传递的容器ID:', solProcessId.value);
      
      // 显示停止进度提示
      addLogToUI(
        {
          timestamp: new Date().toLocaleTimeString(),
          version: 'SOL',
          type: 'INFO',
          oids: ['正在停止Docker容器，请稍候...'],
          hex: '',
          result: 'info',
        } as any,
        false,
      );
      
      try {
        // 使用新的停止和清理功能
        const result = await stopAndCleanupSOL(solProcessId.value as string);
        
        console.log('[DEBUG] stopAndCleanupSOL 返回结果:', result);

        addLogToUI(
          {
            timestamp: new Date().toLocaleTimeString(),
            version: 'SOL',
            type: 'STOP',
            oids: [
              `Docker容器已停止 (ID: ${solProcessId.value})`,
              `容器状态: ${result.data?.stop_results ? '已停止' : '部分停止'}`,
              `输出文件已保留，可在 /home/lab426_system/ProtocolGuardOutPut 查看结果`,
            ],
            hex: '',
            result: 'success',
          } as any,
          false,
        );

        // 显示详细的停止结果
        const responseData = result.data || result;
        if (responseData?.stop_results) {
          const stopResults = responseData.stop_results;
          const details = [];
          if (stopResults.container_stopped) details.push('✓ 容器已停止');
          if (stopResults.container_removed) details.push('✓ 容器已删除');
          details.push('✓ 输出文件已保留供查看');
          if (stopResults.errors && stopResults.errors.length > 0) {
            details.push(`⚠ 错误: ${stopResults.errors.join(', ')}`);
          }

          addLogToUI(
            {
              timestamp: new Date().toLocaleTimeString(),
              version: 'SOL',
              type: 'INFO',
              oids: details,
              hex: '',
              result: 'info',
            } as any,
            false,
          );
        }
      } catch (timeoutError: any) {
        console.error('[DEBUG] 停止容器操作超时或失败:', timeoutError);
        
        // 检查是否是超时错误
        if (timeoutError.message?.includes('timeout') || timeoutError.code === 'ECONNABORTED') {
          addLogToUI(
            {
              timestamp: new Date().toLocaleTimeString(),
              version: 'SOL',
              type: 'WARNING',
              oids: [
                '停止操作超时，但容器可能已经停止',
                '请手动检查Docker容器状态：docker ps',
                '如需强制清理，请重新启动测试'
              ],
              hex: '',
              result: 'warning',
            } as any,
            false,
          );
        } else {
          addLogToUI(
            {
              timestamp: new Date().toLocaleTimeString(),
              version: 'SOL',
              type: 'ERROR',
              oids: [`停止容器失败: ${timeoutError.message || timeoutError}`],
              hex: '',
              result: 'error',
            } as any,
            false,
          );
        }
      }
    } else {
      // 传统进程ID，使用原来的停止方法
      await stopSOLProcess(solProcessId.value);

      addLogToUI(
        {
          timestamp: new Date().toLocaleTimeString(),
          version: 'SOL',
          type: 'STOP',
          oids: [`SOL进程已停止 (PID: ${solProcessId.value})`],
          hex: '',
          result: 'success',
        } as any,
        false,
      );
    }

    solProcessId.value = null;
  } catch (error) {
    console.error('停止SOL进程失败:', error);

    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'SOL',
        type: 'ERROR',
        oids: [`停止SOL进程失败: ${error.message || error}`],
        hex: '',
        result: 'error',
      } as any,
      false,
    );
  }
}

// 手动验证Docker容器状态的辅助函数
async function checkDockerContainerStatus() {
  console.log('[DEBUG] ========== checkDockerContainerStatus 被调用 ==========');
  
  try {
    // 这里可以添加一个API调用来检查Docker容器状态
    // 或者提供用户手动验证的指导
    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'SOL',
        type: 'INFO',
        oids: [
          '手动验证Docker容器状态：',
          '1. 打开终端执行：docker ps',
          '2. 检查是否还有protocolguard容器运行',
          '3. 如有遗留容器，执行：docker rm -f [容器ID]'
        ],
        hex: '',
        result: 'info',
      } as any,
      false,
    );
  } catch (error) {
    console.error('检查Docker状态失败:', error);
  }
}

// 处理停止测试的安全包装函数
function handleStopTest() {
  console.log('[DEBUG] ========== handleStopTest 被调用 (停止按钮点击) ==========');
  console.log('[DEBUG] 当前协议类型:', protocolType.value);
  console.log('[DEBUG] 当前协议实现:', selectedProtocolImplementation.value);
  console.log('[DEBUG] 当前运行状态:', isRunning.value);
  console.log('[DEBUG] 当前solProcessId:', solProcessId.value);
  
  try {
    // 停止所有协议的实时流
    console.log('[DEBUG] 停止所有实时流...');
    stopAllRealtimeStreams();

    // 更新当前协议状态
    console.log('[DEBUG] 更新协议状态...');
    updateProtocolState(protocolType.value as any, {
      isRunning: false,
      isProcessing: false,
    });

    if (protocolType.value === 'MQTT') {
      console.log('[DEBUG] 检测到MQTT协议，调用 stopMQTTTest');
      // MQTT协议使用安全的停止方式
      stopMQTTTest();
    } else {
      console.log('[DEBUG] 非MQTT协议，调用 stopTest');
      // 其他协议使用原来的stopTest
      stopTest();
    }
  } catch (error) {
    console.error('[DEBUG] handleStopTest 执行出错:', error);
  }
}

// MQTT专用的安全停止函数
function stopMQTTTest() {
  console.log('[DEBUG] ========== stopMQTTTest 被调用 ==========');
  console.log('[DEBUG] selectedProtocolImplementation.value:', selectedProtocolImplementation.value);
  
  try {
    console.log('[DEBUG] 开始安全停止MQTT测试...');

    // 添加用户中止日志
    addUnifiedLog('WARNING', '用户手动停止了MQTT测试', 'MQTT');

    // 重置MQTT进度状态
    mqttIsProcessingLogs.value = false;
    mqttProcessingProgress.value = 0;

    // 直接设置状态，避免DOM操作
    isRunning.value = false;
    isPaused.value = false;
    isTestCompleted.value = true;
    testEndTime.value = new Date();

    // 停止计时器
    if (testTimer) {
      clearInterval(testTimer as any);
      testTimer = null;
    }

    // 停止日志读取
    isReadingLog.value = false;
    if (logReadingInterval.value) {
      clearInterval(logReadingInterval.value);
      logReadingInterval.value = null;
    }
    
    // 检查是否是SOL实现，如果是则需要停止Docker容器
    console.log('[DEBUG] 检查是否需要停止SOL Docker容器...');
    console.log('[DEBUG] selectedProtocolImplementation.value === SOL:', selectedProtocolImplementation.value === 'SOL');
    
    if (selectedProtocolImplementation.value === 'SOL') {
      console.log('[DEBUG] 检测到SOL实现，调用 stopSOLProcessWrapper');
      stopSOLProcessWrapper();
    } else {
      console.log('[DEBUG] 非SOL实现，跳过Docker容器停止');
    }

    // 添加停止完成日志
    addUnifiedLog('INFO', 'MQTT测试已被用户停止', 'MQTT');

    // 延迟保存历史记录
    setTimeout(() => {
      try {
        console.log('[DEBUG] MQTT test manually stopped, saving to history...');
        console.log(
          '[DEBUG] Current MQTT stats before saving:',
          mqttStats.value,
        );
        updateTestSummary();
        saveTestToHistory();
        console.log('[DEBUG] MQTT manual stop history save completed');
      } catch (error) {
        console.error('Error saving MQTT test results:', error);
      }
    }, 300);
  } catch (error) {
    console.error('Error in stopMQTTTest:', error);
  }
}

function stopTest() {
  console.log('[DEBUG] ========== stopTest 被调用 ==========');
  console.log('[DEBUG] protocolType.value:', protocolType.value);
  console.log('[DEBUG] selectedProtocolImplementation.value:', selectedProtocolImplementation.value);
  
  try {
    // 如果是MQTT协议，重定向到安全的停止函数
    if (protocolType.value === 'MQTT') {
      console.log('[DEBUG] 检测到MQTT协议，重定向到 stopMQTTTest');
      stopMQTTTest();
      return;
    }

    // Set completion state first
    isRunning.value = false;
    isPaused.value = false;
    isTestCompleted.value = true;
    testEndTime.value = new Date();

    // 停止日志读取
    isReadingLog.value = false;
    if (logReadingInterval.value) {
      clearInterval(logReadingInterval.value);
      logReadingInterval.value = null;
    }

    // 停止协议特定的进程
    console.log('[DEBUG] 检查是否需要停止SOL进程...');
    console.log('[DEBUG] 条件1 - protocolType === MQTT:', protocolType.value === 'MQTT');
    console.log('[DEBUG] 条件2 - selectedProtocolImplementation === SOL:', selectedProtocolImplementation.value === 'SOL');
    
    if (protocolType.value === 'MQTT' && selectedProtocolImplementation.value === 'SOL') {
      console.log('[DEBUG] 满足SOL条件，调用 stopSOLProcessWrapper');
      stopSOLProcessWrapper();
    } else if (protocolType.value === 'MQTT') {
      console.log('[DEBUG] MQTT协议但非SOL实现，调用 stopLogReading');
      // MQTT协议的清理工作通过 useLogReader 管理
      stopLogReading();
    } else {
      console.log('[DEBUG] 非MQTT协议，跳过特殊停止逻辑');
    }

    if (testTimer) {
      clearInterval(testTimer as any);
      testTimer = null;
    }

    // Update final statistics
    updateTestSummary();

    // Save test results to history
    saveTestToHistory();

    console.log('Test completed, updating charts:', {
      isTestCompleted: isTestCompleted.value,
      protocolStats: protocolStats.value,
      messageTypeStats: messageTypeStats.value,
    });

    // Use nextTick to ensure all reactive updates are complete before updating charts
    // 跳过MQTT协议的图表更新，避免DOM冲突
    if (protocolType.value !== 'MQTT') {
      nextTick(() => {
        try {
          // 只有在测试真正完成且不是MQTT协议时才更新图表
          if (isTestCompleted.value) {
            console.log('Updating charts for SNMP protocol completion:', {
              protocolStats: protocolStats.value,
              messageTypeStats: messageTypeStats.value,
              chartsInitialized: !!(messageTypeChart && versionChart),
            });

            // Double-check charts are initialized before updating
            if (messageTypeChart && versionChart) {
              // 确保图表数据不为空，如果为空则使用默认值
              const hasValidData =
                protocolStats.value.v1 +
                  protocolStats.value.v2c +
                  protocolStats.value.v3 >
                  0 ||
                messageTypeStats.value.get +
                  messageTypeStats.value.set +
                  messageTypeStats.value.getnext +
                  messageTypeStats.value.getbulk >
                  0;

              if (!hasValidData) {
                console.warn(
                  'Chart data appears to be empty, using file-based statistics as fallback',
                );
                // 如果统计数据为空，尝试从已解析的fuzz数据中重新计算统计信息
                recalculateStatsFromFuzzData();
              }

              updateCharts();
              showCharts.value = true;
              console.log('Charts updated successfully for SNMP protocol');
            } else {
              // Try to reinitialize charts if they're not available
              console.log(
                'Charts not initialized, attempting to reinitialize...',
              );
              const success = initCharts();
              if (success) {
                updateCharts();
                showCharts.value = true;
                console.log('Charts reinitialized and updated successfully');
              } else {
                console.warn('Failed to reinitialize charts');
              }
            }
          }
        } catch (error) {
          console.error('Error updating charts on test completion:', error);
        }
      });
    } else {
      console.log(
        'MQTT protocol: skipping chart updates to avoid DOM conflicts',
      );
    }
  } catch (error) {
    console.error('Error in stopTest function:', error);
  }
}

function togglePauseTest() {
  isPaused.value = !isPaused.value;
  if (!isPaused.value && isRunning.value) {
    loop();
  }
}

// 统一的清空日志函数
function clearAllLogs() {
  clearLog(); // 清空原有的日志系统
  clearUnifiedLogs(); // 清空统一日志系统
}

// clearLog 现在通过 useLogReader composable 提供

function saveLog() {
  if (logEntries.value.length === 0) {
    // Generate a test report even if no log entries
    generateTestReport();
    return;
  }

  let logText = `时间,类型,内容\n`;
  logEntries.value.forEach((entry) => {
    if (entry.type) {
      logText += `${entry.time},${entry.type},${entry.message}\n`;
    } else {
      logText += `${entry.time},${entry.result},${entry.protocol},${entry.operation},${entry.target},${entry.content},${entry.hex}\n`;
    }
  });

  const blob = new Blob([logText], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `fuzz_log_${new Date().getTime()}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function generateTestReport() {
  let reportContent = '';

  if (protocolType.value === 'MQTT' && fuzzEngine.value === 'AFLNET') {
    // AFLNET引擎报告格式（SOL实现）
    reportContent =
      `AFLNET SOL模糊测试报告\n` +
      `==========================\n\n` +
      `测试引擎: ${fuzzEngine.value}\n` +
      `目标服务器: ${targetHost.value}:${targetPort.value}\n` +
      `开始时间: ${startTime.value || (testStartTime.value ? testStartTime.value.toLocaleString() : '未开始')}\n` +
      `结束时间: ${endTime.value || (testEndTime.value ? testEndTime.value.toLocaleString() : '未结束')}\n` +
      `总耗时: ${elapsedTime.value}秒\n\n` +
      `AFLNET核心统计:\n` +
      `===============\n` +
      `当前执行路径: ${solStats.value.cur_path || 0}\n` +
      `总路径数: ${solStats.value.paths_total || 0}\n` +
      `执行速度: ${solStats.value.execs_per_sec.toFixed(1) || '0.0'} exec/sec\n` +
      `完成循环: ${solStats.value.cycles_done || 0}\n` +
      `最大深度: ${solStats.value.max_depth || 0}\n` +
      `代码覆盖率: ${solStats.value.map_size || 0}\n\n` +
      `安全监控:\n` +
      `========\n` +
      `崩溃检测: ${solStats.value.unique_crashes > 0 ? `检测到 ${solStats.value.unique_crashes} 个崩溃` : '系统稳定运行'}\n` +
      `挂起检测: ${solStats.value.unique_hangs > 0 ? `检测到 ${solStats.value.unique_hangs} 个挂起` : '无挂起现象'}\n` +
      `状态节点数: ${solStats.value.n_nodes || 0}\n` +
      `状态转换数: ${solStats.value.n_edges || 0}\n\n` +
      `报告生成时间: ${new Date().toLocaleString()}\n` +
      `报告版本: AFLNET v1.0 - SOL模糊测试引擎`;
  } else if (protocolType.value === 'MQTT' && fuzzEngine.value === 'MBFuzzer') {
    // MBFuzzer引擎报告格式（传统MQTT broker）
    reportContent =
      `MBFuzzer MQTT协议差异测试报告\n` +
      `================================\n\n` +
      `测试引擎: ${fuzzEngine.value} (智能差异测试)\n` +
      `目标代理: ${targetHost.value}:${targetPort.value}\n` +
      `开始时间: ${mqttStats.value.fuzzing_start_time || (testStartTime.value ? testStartTime.value.toLocaleString() : '未开始')}\n` +
      `结束时间: ${mqttStats.value.fuzzing_end_time || (testEndTime.value ? testEndTime.value.toLocaleString() : '未结束')}\n` +
      `总耗时: ${elapsedTime.value}秒\n\n` +
      `MBFuzzer核心统计:\n` +
      `================\n` +
      `客户端请求数: ${(mqttStats.value.client_request_count || 0).toLocaleString()}\n` +
      `代理端请求数: ${(mqttStats.value.broker_request_count || 0).toLocaleString()}\n` +
      `总请求数: ${((mqttStats.value.client_request_count || 0) + (mqttStats.value.broker_request_count || 0)).toLocaleString()}\n` +
      `有效连接数: ${mqttStats.value.valid_connect_number}\n` +
      `连接成功率: ${mqttStats.value.client_request_count > 0 ? Math.round((mqttStats.value.valid_connect_number / mqttStats.value.client_request_count) * 100) : 0}%\n` +
      `平均请求速率: ${Math.round((mqttStats.value.client_request_count + mqttStats.value.broker_request_count) / Math.max(1, elapsedTime.value))} req/s\n\n` +
      `差异测试结果:\n` +
      `============\n` +
      `新发现差异: ${mqttStats.value.diff_number} 个\n` +
      `重复差异过滤: ${(mqttStats.value.duplicate_diff_number || 0).toLocaleString()} 个\n` +
      `差异发现率: ${(mqttStats.value.client_request_count || 0) + (mqttStats.value.broker_request_count || 0) > 0 ? Math.round(((mqttStats.value.diff_number || 0) / ((mqttStats.value.client_request_count || 0) + (mqttStats.value.broker_request_count || 0))) * 10000) / 100 : 0}%\n\n` +
      `安全监控:\n` +
      `========\n` +
      `崩溃检测: ${mqttStats.value.crash_number > 0 ? `检测到 ${mqttStats.value.crash_number} 个崩溃` : '系统稳定运行'}\n` +
      `Q-Learning状态空间: ${Object.keys(mqttStats.value.q_learning_states || {}).length} 个协议状态\n\n` +
      `报告生成时间: ${new Date().toLocaleString()}\n` +
      `报告版本: MBFuzzer v1.0 - 智能MQTT协议差异测试引擎`;
  } else {
    // 其他协议的标准报告格式
    reportContent =
      `Fuzz测试报告\n` +
      `================\n\n` +
      `协议: ${protocolType.value.toUpperCase()}\n` +
      `引擎: ${fuzzEngine.value}\n` +
      `目标: ${targetHost.value}:${targetPort.value}\n` +
      `开始时间: ${startTime.value || (testStartTime.value ? testStartTime.value.toLocaleString() : '未开始')}\n` +
      `结束时间: ${endTime.value || (testEndTime.value ? testEndTime.value.toLocaleString() : '未结束')}\n` +
      `总耗时: ${elapsedTime.value}秒\n\n` +
      `性能统计:\n` +
      `SNMP_v1发包数: ${protocolStats.value.v1}\n` +
      `SNMP_v2发包数: ${protocolStats.value.v2c}\n` +
      `SNMP_v3发包数: ${protocolStats.value.v3}\n` +
      `总发包数: ${fileTotalPackets.value}\n` +
      `正常响应率: ${Math.round((fileSuccessCount.value / Math.max(fileTotalPackets.value, 1)) * 100)}%\n` +
      `超时率: ${Math.round((fileTimeoutCount.value / Math.max(fileTotalPackets.value, 1)) * 100)}%\n\n` +
      `崩溃信息: ${crashDetails.value ? '检测到崩溃' : '无崩溃'}\n` +
      `生成时间: ${new Date().toLocaleString()}`;
  }

  const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const fileName =
    protocolType.value === 'MQTT'
      ? `mbfuzzer_report_${new Date().getTime()}.txt`
      : `fuzz_report_${new Date().getTime()}.txt`;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 导出差异类型分布数据
function exportDiffTypeData() {
  if (protocolType.value !== 'MQTT') return;

  let diffTypeContent =
    `${fuzzEngine.value} 差异类型分布统计导出\n` +
    `==============================\n\n` +
    `导出时间: ${new Date().toLocaleString()}\n` +
    `总差异数量: ${mqttDiffTypeStats.value.total_differences}\n\n` +
    `差异类型分布:\n` +
    `============\n`;

  // 添加各类型的详细统计
  diffTypeContent += `协议违规: ${mqttDiffTypeStats.value.protocol_violations} 个 (${mqttDiffTypeStats.value.distribution.protocol_violations}%)\n`;
  diffTypeContent += `超时错误: ${mqttDiffTypeStats.value.timeout_errors} 个 (${mqttDiffTypeStats.value.distribution.timeout_errors}%)\n`;
  diffTypeContent += `连接失败: ${mqttDiffTypeStats.value.connection_failures} 个 (${mqttDiffTypeStats.value.distribution.connection_failures}%)\n`;
  diffTypeContent += `消息损坏: ${mqttDiffTypeStats.value.message_corruptions} 个 (${mqttDiffTypeStats.value.distribution.message_corruptions}%)\n`;
  diffTypeContent += `状态不一致: ${mqttDiffTypeStats.value.state_inconsistencies} 个 (${mqttDiffTypeStats.value.distribution.state_inconsistencies}%)\n`;
  diffTypeContent += `认证错误: ${mqttDiffTypeStats.value.authentication_errors} 个 (${mqttDiffTypeStats.value.distribution.authentication_errors}%)\n\n`;

  // 添加分析建议
  diffTypeContent += `分析建议:\n`;
  diffTypeContent += `========\n`;

  const maxType = Object.entries(mqttDiffTypeStats.value.distribution).reduce(
    (max, [type, count]) => (count > max.count ? { type, count } : max),
    { type: '', count: 0 },
  );

  if (maxType.count > 0) {
    const typeNames = {
      protocol_violations: '协议违规',
      timeout_errors: '超时错误',
      connection_failures: '连接失败',
      message_corruptions: '消息损坏',
      state_inconsistencies: '状态不一致',
      authentication_errors: '认证错误',
    };
    diffTypeContent += `主要问题类型: ${typeNames[maxType.type as keyof typeof typeNames]} (${maxType.count}%)\n`;
    diffTypeContent += `建议优先关注该类型的差异进行深入分析。\n`;
  } else {
    diffTypeContent += `暂无差异类型数据\n`;
  }

  const blob = new Blob([diffTypeContent], {
    type: 'text/plain;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `mbfuzzer_diff_types_${new Date().getTime()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 导出差异测试结果
function exportDifferentialResults() {
  if (protocolType.value !== 'MQTT') return;

  const diffContent =
    `${fuzzEngine.value}差异测试结果导出\n` +
    `=======================\n\n` +
    `导出时间: ${new Date().toLocaleString()}\n` +
    `新发现差异: ${mqttStats.value.diff_number} 个\n` +
    `重复差异过滤: ${mqttStats.value.duplicate_diff_number} 个\n` +
    `差异发现率: ${mqttStats.value.client_request_count + mqttStats.value.broker_request_count > 0 ? Math.round((mqttStats.value.diff_number / (mqttStats.value.client_request_count + mqttStats.value.broker_request_count)) * 10000) / 100 : 0}%\n\n` +
    `差异类型分布:\n` +
    `============\n` +
    `CONNECT消息差异: ${mqttStats.value.duplicate_diffs.CONNECT || 0}\n` +
    `PUBLISH消息差异: ${mqttStats.value.duplicate_diffs.PUBLISH || 0}\n` +
    `SUBSCRIBE消息差异: ${mqttStats.value.duplicate_diffs.SUBSCRIBE || 0}\n` +
    `PINGREQ消息差异: ${mqttStats.value.duplicate_diffs.PINGREQ || 0}\n\n` +
    `详细差异记录:\n` +
    `============\n`;

  // 添加统一日志中的差异记录
  const diffLogs = unifiedLogs.value.filter(
    (log) =>
      log.protocol === 'MQTT' &&
      (log.type === 'ERROR' || log.type === 'WARNING'),
  );

  if (diffLogs.length > 0) {
    diffLogs.forEach((log, index) => {
      diffContent += `${index + 1}. [${log.timestamp}] ${log.type}: ${log.content}\n`;
    });
  } else {
    diffContent += `暂无详细差异记录\n`;
  }

  const blob = new Blob([diffContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `mbfuzzer_differential_${new Date().getTime()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 导出Fuzz日志文件
function exportFuzzLogs() {
  if (protocolType.value !== 'MQTT') return;

  const fuzzLogContent =
    `MBFuzzer模糊测试日志\n` +
    `==================\n\n` +
    `导出时间: ${new Date().toLocaleString()}\n` +
    `测试引擎: MBFuzzer (智能差异测试)\n` +
    `协议类型: MQTT\n` +
    `目标地址: ${targetHost.value}:${targetPort.value}\n\n` +
    `测试统计:\n` +
    `========\n` +
    `客户端请求数: ${(mqttStats.value.client_request_count || 0).toLocaleString()}\n` +
    `代理端请求数: ${(mqttStats.value.broker_request_count || 0).toLocaleString()}\n` +
    `总请求数: ${((mqttStats.value.client_request_count || 0) + (mqttStats.value.broker_request_count || 0)).toLocaleString()}\n` +
    `协议差异发现: ${(mqttStats.value.diff_number || 0).toLocaleString()}\n` +
    `崩溃数量: ${mqttStats.value.crash_number || 0}\n\n` +
    `详细执行日志:\n` +
    `============\n`;

  // 添加统一日志中的所有MQTT相关记录
  const mqttLogs = unifiedLogs.value.filter(
    (log) => log.protocol === 'MQTT' || log.version === 'MQTT',
  );

  mqttLogs.forEach((log, index) => {
    fuzzLogContent += `[${index + 1}] ${log.timestamp} - ${log.type}: ${log.result}\n`;
    if (log.failedReason) {
      fuzzLogContent += `    错误详情: ${log.failedReason}\n`;
    }
  });

  fuzzLogContent += `\n\n报告生成时间: ${new Date().toLocaleString()}\n`;
  fuzzLogContent += `报告版本: MBFuzzer v1.0 - 智能MQTT协议模糊测试引擎`;

  const blob = new Blob([fuzzLogContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `mbfuzzer_fuzz_logs_${new Date().getTime()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function loop() {
  try {
    // 检查测试是否应该继续运行
    if (!isRunning.value || isPaused.value || showHistoryView.value) {
      return;
    }

    if (currentPacketIndex.value >= snmpFuzzData.value.length) {
      return stopTest();
    }

    const packet = snmpFuzzData.value[currentPacketIndex.value];
    if (packet) {
      processSNMPPacket(packet, addLogToUI, (result: string) => {
        // Update result counters based on packet result
        switch (result) {
          case 'success':
            successCount.value++;
            break;
          case 'timeout':
            timeoutCount.value++;
            break;
          case 'failed':
            failedCount.value++;
            break;
          case 'crash':
            crashCount.value++;
            break;
        }

        // Debug: Log every 100 packets to verify counting
        if (packetCount.value % 100 === 0) {
          console.log(
            `统计更新 [包#${packetCount.value}]: 成功=${successCount.value}, 超时=${timeoutCount.value}, 失败=${failedCount.value}, 崩溃=${crashCount.value}`,
          );
        }
      });
    }

    // Batch update counters to prevent multiple reactive updates
    currentPacketIndex.value++;
    packetCount.value++;

    // Check for crash and stop if detected
    if (packet?.result === 'crash') {
      handleCrashDetection(packet);
      // Add a small delay before stopping to ensure UI updates complete
      setTimeout(() => {
        if (isRunning.value) {
          // Double-check we're still running
          stopTest();
        }
      }, 150);
      return;
    }

    // Continue loop with appropriate delay, but check again if we should continue
    if (isRunning.value && !isPaused.value && !showHistoryView.value) {
      window.setTimeout(() => {
        // Additional safety check before continuing
        if (isRunning.value && !isPaused.value && !showHistoryView.value) {
          loop();
        }
      }, packetDelay.value);
    }
  } catch (error) {
    console.error('Error in loop function:', error);
    // Stop the test if there's an error to prevent infinite loops
    if (isRunning.value) {
      stopTest();
    }
  }
}

// processPacket 现在通过 useSNMP composable 的 processSNMPPacket 提供

function addLogToUI(packet: FuzzPacket, isCrash: boolean) {
  // 根据当前协议类型添加日志
  const currentProtocolType = protocolType.value;
  const logType = isCrash
    ? 'ERROR'
    : packet.result === 'success'
      ? 'SUCCESS'
      : packet.result === 'timeout'
        ? 'WARNING'
        : 'INFO';

  let logContent: string;

  // 根据协议类型格式化日志内容
  if (currentProtocolType === 'SNMP') {
    logContent = formatSNMPPacketLog(packet, isCrash);
    console.log('[DEBUG] 添加SNMP日志:', { logType, logContent, packet });
  } else if (currentProtocolType === 'MQTT' && selectedProtocolImplementation.value === 'SOL') {
    logContent = formatSOLPacketLog(packet, isCrash);
    console.log('[DEBUG] 添加SOL日志:', { logType, logContent, packet });
  } else if (currentProtocolType === 'MQTT') {
    logContent = formatMQTTPacketLog(packet, isCrash);
    console.log('[DEBUG] 添加MQTT日志:', { logType, logContent, packet });
  } else {
    logContent = formatGenericPacketLog(packet, isCrash);
    console.log('[DEBUG] 添加通用日志:', { logType, logContent, packet });
  }

  addToRealtimeStream(currentProtocolType, {
    timestamp: new Date().toLocaleTimeString(),
    type: logType,
    content: logContent,
  });
}

// 格式化SNMP数据包日志
function formatSNMPPacketLog(packet: FuzzPacket, isCrash: boolean): string {
  if (isCrash) {
    return `CRASH DETECTED ${packet.version?.toUpperCase() || 'UNKNOWN'} ${packet.type?.toUpperCase() || 'UNKNOWN'}`;
  } else {
    const protocol = packet.version?.toUpperCase() || 'UNKNOWN';
    const op = packet.type?.toUpperCase() || 'UNKNOWN';
    const content = packet.oids?.[0] || '';
    const hex = (packet.hex || '').slice(0, 40);
    const resultText =
      packet.result === 'success'
        ? `正常响应 (${packet.responseSize || 0}字节)`
        : packet.result === 'timeout'
          ? '接收超时'
          : packet.result === 'failed'
            ? '构造失败'
            : '未知状态';

    return `SNMP${protocol} ${op} ${content} ${resultText} ${hex}...`;
  }
}

// 格式化SOL数据包日志
function formatSOLPacketLog(packet: FuzzPacket, isCrash: boolean): string {
  if (isCrash) {
    return `CRASH DETECTED ${packet.version?.toUpperCase() || 'SOL'} ${packet.type?.toUpperCase() || 'UNKNOWN'}`;
  } else {
    const protocol = packet.version?.toUpperCase() || 'SOL';
    const op = packet.type?.toUpperCase() || 'UNKNOWN';
    const content = packet.oids?.[0] || '';
    const hex = (packet.hex || '').slice(0, 40);
    const resultText =
      packet.result === 'success'
        ? `正常响应 (${packet.responseSize || 0}字节)`
        : packet.result === 'timeout'
          ? '接收超时'
          : packet.result === 'failed'
            ? '构造失败'
            : '未知状态';

    return `${protocol} ${op} ${content} ${resultText} ${hex}...`;
  }
}

// 格式化MQTT数据包日志
function formatMQTTPacketLog(packet: FuzzPacket, isCrash: boolean): string {
  if (isCrash) {
    return `CRASH DETECTED ${packet.version?.toUpperCase() || 'MQTT'} ${packet.type?.toUpperCase() || 'UNKNOWN'}`;
  } else {
    const protocol = packet.version?.toUpperCase() || 'MQTT';
    const op = packet.type?.toUpperCase() || 'UNKNOWN';
    const content = packet.oids?.[0] || '';
    const hex = (packet.hex || '').slice(0, 40);
    const resultText =
      packet.result === 'success'
        ? `正常响应 (${packet.responseSize || 0}字节)`
        : packet.result === 'timeout'
          ? '接收超时'
          : packet.result === 'failed'
            ? '构造失败'
            : '未知状态';

    return `${protocol} ${op} ${content} ${resultText} ${hex}...`;
  }
}

// 格式化通用数据包日志
function formatGenericPacketLog(packet: FuzzPacket, isCrash: boolean): string {
  if (isCrash) {
    return `CRASH DETECTED ${packet.version?.toUpperCase() || 'UNKNOWN'} ${packet.type?.toUpperCase() || 'UNKNOWN'}`;
  } else {
    const protocol = packet.version?.toUpperCase() || 'UNKNOWN';
    const op = packet.type?.toUpperCase() || 'UNKNOWN';
    const content = packet.oids?.[0] || '';
    const hex = (packet.hex || '').slice(0, 40);
    const resultText =
      packet.result === 'success'
        ? `正常响应 (${packet.responseSize || 0}字节)`
        : packet.result === 'timeout'
          ? '接收超时'
          : packet.result === 'failed'
            ? '构造失败'
            : '未知状态';

    return `${protocol} ${op} ${content} ${resultText} ${hex}...`;
  }
}

// Crash handling functions
function generateRandomHex(length = 30) {
  const chars = '0123456789ABCDEF';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

function generateCrashDetails(
  packetId: number | string,
  protocol: string,
  operation: string,
  content: string,
) {
  const crashTypes = [
    'Segmentation Fault (SIGSEGV)',
    'Aborted (SIGABRT)',
    'Illegal Instruction (SIGILL)',
    'Bus Error (SIGBUS)',
    'Floating Point Exception (SIGFPE)',
  ];

  const crashType = crashTypes[Math.floor(Math.random() * crashTypes.length)];
  const timestamp = new Date().toLocaleTimeString();
  const dumpFile = `/var/crash/${protocol}_crash_${Date.now()}.dmp`;
  const logPath = `/home/hhh/下载/snmp_fuzz/snmp_github/snmp_fuzz/scan_result/crash_logs/${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${timestamp.replace(/:/g, '')}`;

  const detailsText =
    `[${timestamp}] ${crashType}\n` +
    `Process ID: ${Math.floor(Math.random() * 10000) + 1000}\n` +
    `Fault Address: 0x${generateRandomHex(8)}\n` +
    `Registers:\n` +
    `  EAX: 0x${generateRandomHex(8)}  EBX: 0x${generateRandomHex(8)}\n` +
    `  ECX: 0x${generateRandomHex(8)}  EDX: 0x${generateRandomHex(8)}\n` +
    `  ESI: 0x${generateRandomHex(8)}  EDI: 0x${generateRandomHex(8)}\n` +
    `  EBP: 0x${generateRandomHex(8)}  ESP: 0x${generateRandomHex(8)}\n` +
    `Backtrace:\n` +
    `  #0  0x${generateRandomHex(8)} in ${operation}_handler()\n` +
    `  #1  0x${generateRandomHex(8)} in packet_processor()\n` +
    `  #2  0x${generateRandomHex(8)} in main_loop()\n`;

  return {
    id: packetId,
    time: timestamp,
    type: crashType,
    dumpFile: dumpFile,
    logPath: logPath,
    details: detailsText,
    packetContent: content,
  };
}

function handleCrashDetection(packet: FuzzPacket) {
  if (packet.crashEvent) {
    crashDetails.value = {
      id: packetCount.value,
      time: packet.crashEvent.timestamp,
      type: '程序崩溃',
      dumpFile: packet.crashEvent.crashLogPath,
      logPath: packet.crashEvent.crashLogPath,
      details: `崩溃通知: ${packet.crashEvent.message}\n疑似崩溃数据包: ${packet.crashEvent.crashPacket}\n崩溃队列信息导出: ${packet.crashEvent.crashLogPath}`,
      packetContent: packet.crashEvent.crashPacket,
    };
    addRealCrashLogEntries(packet.crashEvent);
  } else {
    crashDetails.value = generateCrashDetails(
      packetCount.value,
      packet.version,
      packet.type,
      packet.hex,
    );
    addCrashLogEntries(crashDetails.value, packet.version, packet.hex);
  }
}

function addRealCrashLogEntries(crashEvent: any) {
  const time = new Date().toLocaleTimeString();

  // Add crash logs to entries
  logEntries.value.push(
    { time, type: 'crash_notice', message: crashEvent.message },
    {
      time,
      type: 'crash_packet',
      message: `疑似崩溃数据包: ${crashEvent.crashPacket}`,
    },
    {
      time,
      type: 'crash_export',
      message: `崩溃队列信息导出: ${crashEvent.crashLogPath}`,
    },
    { time, type: 'stop_fuzz', message: '检测到崩溃，停止 fuzz 循环' },
  );

  // Add to UI with proper error handling and DOM checks
  nextTick(() => {
    try {
      if (
        logContainer.value &&
        !showHistoryView.value &&
        isRunning.value &&
        logContainer.value.appendChild
      ) {
        const logs = [
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">${crashEvent.message || '崩溃通知'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 疑似崩溃数据包: ${crashEvent.crashPacket || '未知'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 崩溃队列信息导出: ${crashEvent.crashLogPath || '未知路径'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">[运行监控] 检测到崩溃，停止 fuzz 循环</span>`,
        ];

        logs.forEach((logHtml) => {
          if (logContainer.value && logContainer.value.appendChild) {
            const div = document.createElement('div');
            div.className = 'crash-highlight';
            div.innerHTML = logHtml;
            logContainer.value.appendChild(div);
          }
        });

        if (logContainer.value && logContainer.value.scrollTop !== undefined) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight;
        }
      }
    } catch (error) {
      console.warn('Failed to add crash log to UI:', error);
    }
  });
}

function addCrashLogEntries(crashDetails: any, protocol: string, hex: string) {
  const time = new Date().toLocaleTimeString();

  logEntries.value.push(
    {
      time,
      type: 'crash_notice',
      message: '收到崩溃通知: 健康服务报告 VM 不可达',
    },
    { time, type: 'crash_packet', message: `疑似崩溃数据包: ${hex}` },
    { time, type: 'log_dir', message: `日志导出目录: ${crashDetails.logPath}` },
    { time, type: 'timeout', message: '接收超时' },
    { time, type: 'no_response', message: '响应: 无' },
    { time, type: 'stop_fuzz', message: '检测到崩溃，停止 fuzz 循环' },
  );

  nextTick(() => {
    try {
      if (
        logContainer.value &&
        !showHistoryView.value &&
        isRunning.value &&
        logContainer.value.appendChild
      ) {
        const logs = [
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">[运行监控] 收到崩溃通知: 健康服务报告 VM 不可达</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 疑似崩溃数据包: ${hex || '未知'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 日志导出目录: ${crashDetails?.logPath || '未知路径'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-warning">  [接收超时]</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-warning">  响应: 无</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">[运行监控] 检测到崩溃，停止 fuzz 循环</span>`,
        ];

        logs.forEach((logHtml) => {
          if (logContainer.value && logContainer.value.appendChild) {
            const div = document.createElement('div');
            div.className = 'crash-highlight';
            div.innerHTML = logHtml;
            logContainer.value.appendChild(div);
          }
        });

        if (logContainer.value && logContainer.value.scrollTop !== undefined) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight;
        }
      }
    } catch (error) {
      console.warn('Failed to add crash log entries to UI:', error);
    }
  });
}

function updateTestSummary() {
  const total =
    fileTotalPackets.value ||
    successCount.value +
      timeoutCount.value +
      failedCount.value +
      crashCount.value;
  const successBase = fileSuccessCount.value || successCount.value;
  const timeoutBase = fileTimeoutCount.value || timeoutCount.value;

  lastUpdate.value = new Date().toLocaleString();

  // Update final statistics display
  if (total > 0) {
    // Use file-based statistics if available, otherwise use runtime statistics
    const finalSuccessCount = fileSuccessCount.value || successCount.value;
    const finalTimeoutCount = fileTimeoutCount.value || timeoutCount.value;
    const finalFailedCount = fileFailedCount.value || failedCount.value;

    console.log('Final test summary:', {
      total: fileTotalPackets.value,
      success: finalSuccessCount,
      timeout: finalTimeoutCount,
      failed: finalFailedCount,
      successRate: Math.round((finalSuccessCount / total) * 100),
      timeoutRate: Math.round((finalTimeoutCount / total) * 100),
    });
  }
}

// 保存测试结果到历史记录
function saveTestToHistory() {
  try {
    console.log(
      '[DEBUG] saveTestToHistory called for protocol:',
      protocolType.value,
    );
    console.log('[DEBUG] Current test state:', {
      isRunning: isRunning.value,
      isTestCompleted: isTestCompleted.value,
      testStartTime: testStartTime.value,
      testEndTime: testEndTime.value,
    });

    // 计算实际的测试统计数据
    const actualTotalPackets = fileTotalPackets.value || packetCount.value;
    const actualSuccessCount = fileSuccessCount.value || successCount.value;
    const actualTimeoutCount = fileTimeoutCount.value || timeoutCount.value;
    const actualFailedCount = fileFailedCount.value || failedCount.value;
    const actualCrashCount = crashCount.value;

    console.log('[DEBUG] Test statistics:', {
      actualTotalPackets,
      actualSuccessCount,
      actualTimeoutCount,
      actualFailedCount,
      actualCrashCount,
    });

    // 获取有效连接数量（对于MQTT协议）或保持原有的测试持续时间（对于其他协议）
    const duration =
      protocolType.value === 'MQTT' && mqttStats.value.valid_connect_number
        ? mqttStats.value.valid_connect_number
        : testStartTime.value && testEndTime.value
          ? Math.round(
              (testEndTime.value.getTime() - testStartTime.value.getTime()) /
                1000,
            )
          : elapsedTime.value;

    // 计算成功率
    const total =
      actualTotalPackets ||
      actualSuccessCount +
        actualTimeoutCount +
        actualFailedCount +
        actualCrashCount;
    const successRate =
      total > 0 ? Math.round((actualSuccessCount / total) * 100) : 0;

    // 生成唯一ID
    const historyId = `test_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // 创建历史记录条目
    const historyItem: HistoryResult = {
      id: historyId,
      timestamp: testStartTime.value
        ? testStartTime.value.toLocaleString()
        : new Date().toLocaleString(),
      protocol: protocolType.value,
      fuzzEngine: fuzzEngine.value,
      targetHost: targetHost.value,
      targetPort: targetPort.value,
      duration: duration,
      totalPackets: total,
      successCount: actualSuccessCount,
      timeoutCount: actualTimeoutCount,
      failedCount: actualFailedCount,
      crashCount: actualCrashCount,
      successRate: successRate,
      protocolStats: {
        v1: protocolStats.value.v1,
        v2c: protocolStats.value.v2c,
        v3: protocolStats.value.v3,
      },
      messageTypeStats: {
        get: messageTypeStats.value.get,
        set: messageTypeStats.value.set,
        getnext: messageTypeStats.value.getnext,
        getbulk: messageTypeStats.value.getbulk,
      },
      // 保存SOL统计数据
      rtspStats:
        protocolType.value === 'MQTT' && selectedProtocolImplementation.value === 'SOL'
          ? {
              cycles_done: solStats.value.cycles_done,
              paths_total: solStats.value.paths_total,
              cur_path: solStats.value.cur_path,
              pending_total: solStats.value.pending_total,
              pending_favs: solStats.value.pending_favs,
              map_size: solStats.value.map_size,
              unique_crashes: solStats.value.unique_crashes,
              unique_hangs: solStats.value.unique_hangs,
              max_depth: solStats.value.max_depth,
              execs_per_sec: solStats.value.execs_per_sec,
              n_nodes: solStats.value.n_nodes,
              n_edges: solStats.value.n_edges,
            }
          : undefined,
      // 保存MQTT协议统计数据
      mqttStats:
        protocolType.value === 'MQTT'
          ? (() => {
              console.log('[DEBUG] Saving MQTT stats:', mqttStats.value);
              return {
                fuzzing_start_time: mqttStats.value.fuzzing_start_time,
                fuzzing_end_time: mqttStats.value.fuzzing_end_time,
                client_request_count: mqttStats.value.client_request_count,
                broker_request_count: mqttStats.value.broker_request_count,
                crash_number: mqttStats.value.crash_number,
                diff_number: mqttStats.value.diff_number,
                duplicate_diff_number: mqttStats.value.duplicate_diff_number,
                valid_connect_number: mqttStats.value.valid_connect_number,
                duplicate_connect_diff: mqttStats.value.duplicate_connect_diff,
                total_differences: mqttStats.value.total_differences,
              };
            })()
          : undefined,
      // 保存协议特定的扩展数据
      protocolSpecificData:
        protocolType.value === 'MQTT'
          ? {
              clientRequestCount: mqttStats.value.client_request_count,
              brokerRequestCount: mqttStats.value.broker_request_count,
              diffNumber: mqttStats.value.diff_number,
              duplicateDiffNumber: mqttStats.value.duplicate_diff_number,
              validConnectNumber: mqttStats.value.valid_connect_number,
              duplicateConnectDiff: mqttStats.value.duplicate_connect_diff,
              fuzzingStartTime: mqttStats.value.fuzzing_start_time,
              fuzzingEndTime: mqttStats.value.fuzzing_end_time,
            }
          : protocolType.value === 'MQTT' && selectedProtocolImplementation.value === 'SOL'
            ? {
                pathCoverage:
                  (solStats.value.cur_path /
                    Math.max(solStats.value.paths_total, 1)) *
                  100,
                stateTransitions: solStats.value.n_edges,
                maxDepth: solStats.value.max_depth,
                uniqueHangs: solStats.value.unique_hangs,
              }
            : protocolType.value === 'SNMP'
              ? {
                  oidCoverage: Math.round(
                    ((protocolStats.value.v1 +
                      protocolStats.value.v2c +
                      protocolStats.value.v3) /
                      Math.max(total, 1)) *
                      100,
                  ),
                  communityStrings: ['public', 'private'], // 示例数据
                  targetDeviceInfo: `${targetHost.value}:${targetPort.value}`,
                }
              : undefined,
      hasCrash: actualCrashCount > 0,
      crashDetails: crashDetails.value
        ? {
            id: crashDetails.value.id,
            time: crashDetails.value.time,
            type: crashDetails.value.type,
            dumpFile: crashDetails.value.dumpFile,
            logPath: crashDetails.value.logPath,
            details: crashDetails.value.details,
            packetContent: crashDetails.value.packetContent,
          }
        : undefined,
    };

    // 将新的测试结果添加到历史记录的开头
    historyResults.value.unshift(historyItem);

    // 按时间戳重新排序，确保顺序正确
    historyResults.value.sort((a, b) => {
      const dateA = new Date(a.timestamp);
      const dateB = new Date(b.timestamp);
      return dateB.getTime() - dateA.getTime(); // 降序排列（最新的在前）
    });

    // 限制历史记录数量，保留最新的50条
    if (historyResults.value.length > 50) {
      historyResults.value = historyResults.value.slice(0, 50);
    }

    // 保存到本地存储（统一存储所有引擎的历史记录）
    try {
      const storageKey = 'fuzz_test_history_unified';
      localStorage.setItem(
        storageKey,
        JSON.stringify(historyResults.value),
      );
      console.log(`Test results saved to unified history for engine ${fuzzEngine.value}:`, historyItem);
      console.log(
        '[DEBUG] History results length after save:',
        historyResults.value.length,
      );
      console.log('[DEBUG] Latest history item:', historyResults.value[0]);

      // 为MQTT协议添加详细的保存日志
      if (protocolType.value === 'MQTT') {
        console.log('MQTT test results saved to history successfully');
        console.log('MQTT Stats saved:', {
          mqttStats: historyItem.mqttStats,
          protocolSpecificData: historyItem.protocolSpecificData,
        });

        // 强制触发响应式更新
        nextTick(() => {
          console.log('[DEBUG] Forcing reactive update for history');
          // 触发一个小的变化来确保Vue检测到数组更新
          historyResults.value = [...historyResults.value];
        });
      } else {
        showSaveNotification();
      }
    } catch (storageError) {
      console.warn('Failed to save history to localStorage:', storageError);
    }
  } catch (error) {
    console.error('Error saving test to history:', error);
  }
}

function toggleCrashDetailsView() {
  showCrashDetails.value = !showCrashDetails.value;
}

// 历史结果相关函数
function goToHistoryView() {
  showHistoryView.value = true;
  selectedHistoryItem.value = null;
}

function backToMainView() {
  showHistoryView.value = false;
  selectedHistoryItem.value = null;
}

function viewHistoryDetail(item: HistoryResult) {
  selectedHistoryItem.value = item;
}

function backToHistoryList() {
  selectedHistoryItem.value = null;
}

function deleteHistoryItem(id: string) {
  const index = historyResults.value.findIndex((item) => item.id === id);
  if (index > -1) {
    historyResults.value.splice(index, 1);

    // 同步到本地存储（统一存储）
    try {
      const storageKey = 'fuzz_test_history_unified';
      localStorage.setItem(
        storageKey,
        JSON.stringify(historyResults.value),
      );
      console.log('History item deleted and saved to unified localStorage');
    } catch (error) {
      console.warn('Failed to save updated history to localStorage:', error);
    }
  }
}

function exportHistoryItem(item: HistoryResult) {
  const reportContent =
    `Fuzz测试历史报告\n` +
    `================\n\n` +
    `测试ID: ${item.id}\n` +
    `协议: ${item.protocol}\n` +
    `引擎: ${item.fuzzEngine}\n` +
    `目标: ${item.targetHost}:${item.targetPort}\n` +
    `测试时间: ${item.timestamp}\n` +
    `总耗时: ${item.duration}秒\n\n` +
    `性能统计:\n` +
    `总发包数: ${item.totalPackets}\n` +
    `正常响应: ${item.successCount} (${item.successRate}%)\n` +
    `超时: ${item.timeoutCount}\n` +
    `失败: ${item.failedCount}\n` +
    `崩溃: ${item.crashCount}\n\n` +
    `协议版本分布:\n` +
    `SNMP v1: ${item.protocolStats.v1}\n` +
    `SNMP v2c: ${item.protocolStats.v2c}\n` +
    `SNMP v3: ${item.protocolStats.v3}\n\n` +
    `消息类型分布:\n` +
    `GET: ${item.messageTypeStats.get}\n` +
    `SET: ${item.messageTypeStats.set}\n` +
    `GETNEXT: ${item.messageTypeStats.getnext}\n` +
    `GETBULK: ${item.messageTypeStats.getbulk}\n\n` +
    `崩溃信息: ${item.hasCrash ? '检测到崩溃' : '无崩溃'}\n` +
    `生成时间: ${new Date().toLocaleString()}`;

  const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `history_report_${item.id}_${new Date().getTime()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 清空所有历史记录
function clearAllHistory() {
  if (confirm('确定要清空所有历史记录吗？此操作不可撤销。')) {
    historyResults.value = [];

    // 同步到本地存储（清空统一存储）
    try {
      const storageKey = 'fuzz_test_history_unified';
      localStorage.removeItem(storageKey);
      console.log(`All history cleared for engine ${fuzzEngine.value}`);
    } catch (error) {
      console.warn('Failed to clear history from localStorage:', error);
    }
  }
}

// 导出所有历史记录
function exportAllHistory() {
  if (historyResults.value.length === 0) {
    alert('没有历史记录可导出');
    return;
  }

  const reportContent =
    `Fuzz测试历史记录汇总\n` +
    `==================\n\n` +
    `导出时间: ${new Date().toLocaleString()}\n` +
    `总记录数: ${historyResults.value.length}\n\n` +
    historyResults.value
      .map(
        (item, index) =>
          `${index + 1}. [${item.timestamp}] ${item.protocol} - ${item.fuzzEngine}\n` +
          `   目标: ${item.targetHost}:${item.targetPort}\n` +
          `   耗时: ${item.duration}秒, 总包数: ${item.totalPackets}, 成功率: ${item.successRate}%\n` +
          `   崩溃: ${item.hasCrash ? '是' : '否'}\n`,
      )
      .join('\n');

  const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `fuzz_history_summary_${new Date().getTime()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 显示保存成功通知
function showSaveNotification() {
  try {
    // 使用nextTick确保DOM更新完成
    nextTick(() => {
      notificationMessage.value = '测试结果已保存到历史记录';
      showNotification.value = true;

      // 3秒后自动隐藏通知
      setTimeout(() => {
        try {
          showNotification.value = false;
        } catch (error) {
          console.warn('Failed to hide notification:', error);
        }
      }, 3000);
    });
  } catch (error) {
    console.warn('Failed to show notification:', error);
  }
}

// 手动关闭通知
function closeNotification() {
  showNotification.value = false;
}

// Computed properties for button states
const canStartTest = computed(() => {
  // MQTT协议不需要fuzzData
  if (protocolType.value === 'MQTT') {
    return !loading.value && !isRunning.value;
  }
  return !loading.value && snmpFuzzData.value.length > 0 && !isRunning.value;
});

// Debug function for testing
function debugInfo() {
  console.log('Debug Info:', {
    loading: loading.value,
    error: error.value,
    fuzzDataLength: fuzzData.value.length,
    isRunning: isRunning.value,
    canStartTest: canStartTest.value,
    protocolStats: protocolStats.value,
    messageTypeStats: messageTypeStats.value,
  });
}

const testStatusText = computed(() => {
  if (isRunning.value) {
    return isPaused.value ? '已暂停' : '运行中';
  }
  if (crashCount.value > 0) {
    return '检测到崩溃';
  }
  return '未开始';
});

const testStatusClass = computed(() => {
  if (isRunning.value) {
    return isPaused.value ? 'text-warning' : 'text-success';
  }
  if (crashCount.value > 0) {
    return 'text-danger';
  }
  return 'text-warning';
});

// 迁移旧的历史记录到新的统一格式
function migrateOldHistoryFormat() {
  try {
    // 检查是否已经有统一格式的历史记录
    const unifiedHistory = localStorage.getItem('fuzz_test_history_unified');
    if (unifiedHistory) {
      console.log('[DEBUG] 统一格式历史记录已存在，跳过迁移');
      return;
    }

    // 收集所有旧格式的历史记录
    const allHistory: any[] = [];
    
    // 1. 迁移最原始的格式
    const oldHistory = localStorage.getItem('fuzz_test_history');
    if (oldHistory) {
      const parsedHistory = JSON.parse(oldHistory);
      if (Array.isArray(parsedHistory)) {
        console.log(`[DEBUG] 发现原始格式历史记录 ${parsedHistory.length} 条`);
        allHistory.push(...parsedHistory);
        localStorage.removeItem('fuzz_test_history');
      }
    }
    
    // 2. 迁移按引擎分类的格式
    const engines = ['MBFuzzer', 'AFLNET', 'SNMP_Fuzz'];
    engines.forEach(engine => {
      const storageKey = `fuzz_test_history_${engine}`;
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        try {
          const parsedHistory = JSON.parse(stored);
          if (Array.isArray(parsedHistory)) {
            console.log(`[DEBUG] 发现 ${engine} 引擎历史记录 ${parsedHistory.length} 条`);
            allHistory.push(...parsedHistory);
          }
        } catch (error) {
          console.warn(`Failed to parse history for engine ${engine}:`, error);
        }
        // 删除旧的分类存储
        localStorage.removeItem(storageKey);
      }
    });
    
    if (allHistory.length > 0) {
      // 确保每条记录都有正确的引擎信息
      allHistory.forEach(item => {
        if (!item.fuzzEngine) {
          // 智能推断引擎类型
          if (item.protocol === 'MQTT') {
            // 检查是否有SOL相关的统计数据
            if (item.rtspStats || (item.protocolSpecificData && (
              item.protocolSpecificData.pathCoverage !== undefined ||
              item.protocolSpecificData.stateTransitions !== undefined ||
              item.protocolSpecificData.maxDepth !== undefined
            ))) {
              item.fuzzEngine = 'AFLNET';
            } else {
              item.fuzzEngine = 'MBFuzzer';
            }
          } else if (item.protocol === 'SNMP') {
            item.fuzzEngine = 'SNMP_Fuzz';
          } else {
            item.fuzzEngine = 'MBFuzzer'; // 默认
          }
        }
      });
      
      // 按时间戳排序，最新的在前面
      const sortedHistory = allHistory.sort((a, b) => {
        const dateA = new Date(a.timestamp);
        const dateB = new Date(b.timestamp);
        return dateB.getTime() - dateA.getTime();
      });
      
      // 保存到统一存储
      localStorage.setItem('fuzz_test_history_unified', JSON.stringify(sortedHistory));
      console.log(`[DEBUG] 迁移完成，合并 ${sortedHistory.length} 条历史记录到统一存储`);
    }
  } catch (error) {
    console.warn('Failed to migrate old history format:', error);
  }
}

// 从本地存储加载历史记录
function loadHistoryFromStorage() {
  try {
    // 首次运行时尝试迁移旧格式
    migrateOldHistoryFormat();
    
    // 加载统一的历史记录（包含所有引擎类型）
    const storageKey = 'fuzz_test_history_unified';
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      const parsedHistory = JSON.parse(stored);
      if (Array.isArray(parsedHistory)) {
        // 按时间戳排序，最新的在前面
        const sortedHistory = parsedHistory.sort((a, b) => {
          // 将时间戳字符串转换为Date对象进行比较
          const dateA = new Date(a.timestamp);
          const dateB = new Date(b.timestamp);
          return dateB.getTime() - dateA.getTime(); // 降序排列（最新的在前）
        });
        historyResults.value = sortedHistory;
        console.log(
          `Loaded ${parsedHistory.length} unified history items from localStorage`,
        );
        console.log(
          '[DEBUG] Loaded history items:',
          parsedHistory.map((item) => ({
            id: item.id,
            protocol: item.protocol,
            fuzzEngine: item.fuzzEngine,
            timestamp: item.timestamp,
          })),
        );
      }
    } else {
      // 如果没有找到历史记录，清空当前显示
      historyResults.value = [];
      console.log('No unified history found, starting fresh');
    }
  } catch (error) {
    console.warn('Failed to load history from localStorage:', error);
    // 如果加载失败，清空历史记录
    historyResults.value = [];
  }
}

// 测试历史记录保存功能（调试用）
function testHistorySave() {
  console.log('[DEBUG] Testing history save functionality...');
  console.log('[DEBUG] Current protocol:', protocolType.value);
  console.log('[DEBUG] Current MQTT stats:', mqttStats.value);

  // 手动触发保存
  try {
    saveTestToHistory();
    console.log('[DEBUG] Manual history save completed');
  } catch (error) {
    console.error('[DEBUG] Manual history save failed:', error);
  }
}

// 重新整理统一历史记录（调试用）
function reclassifyAllHistory() {
  console.log('[DEBUG] 开始重新整理统一历史记录...');
  
  // 重新加载并排序统一历史记录
  const storageKey = 'fuzz_test_history_unified';
  const stored = localStorage.getItem(storageKey);
  
  if (stored) {
    try {
      const parsedHistory = JSON.parse(stored);
      if (Array.isArray(parsedHistory)) {
        // 确保每条记录都有正确的引擎信息
        parsedHistory.forEach(item => {
          if (!item.fuzzEngine) {
            // 智能推断引擎类型
            if (item.protocol === 'MQTT') {
              // 检查是否有SOL相关的统计数据
              if (item.rtspStats || (item.protocolSpecificData && (
                item.protocolSpecificData.pathCoverage !== undefined ||
                item.protocolSpecificData.stateTransitions !== undefined ||
                item.protocolSpecificData.maxDepth !== undefined
              ))) {
                item.fuzzEngine = 'AFLNET';
              } else {
                item.fuzzEngine = 'MBFuzzer';
              }
            } else if (item.protocol === 'SNMP') {
              item.fuzzEngine = 'SNMP_Fuzz';
            } else {
              item.fuzzEngine = 'MBFuzzer'; // 默认
            }
          }
        });
        
        // 按时间戳排序，最新的在前面
        const sortedHistory = parsedHistory.sort((a, b) => {
          const dateA = new Date(a.timestamp);
          const dateB = new Date(b.timestamp);
          return dateB.getTime() - dateA.getTime();
        });
        
        // 保存回统一存储
        localStorage.setItem(storageKey, JSON.stringify(sortedHistory));
        console.log(`[DEBUG] 重新整理完成，共 ${sortedHistory.length} 条统一历史记录`);
        
        // 重新加载历史记录
        loadHistoryFromStorage();
      }
    } catch (error) {
      console.warn('Failed to reclassify unified history:', error);
    }
  } else {
    console.log('[DEBUG] 没有找到统一历史记录');
  }
}

// 将测试函数暴露到全局作用域（仅用于调试）
if (typeof window !== 'undefined') {
  (window as any).testHistorySave = testHistorySave;
  (window as any).checkHistoryResults = () => {
    console.log('[DEBUG] Current history results:', historyResults.value);
    console.log('[DEBUG] History results length:', historyResults.value.length);
  };
  (window as any).reclassifyAllHistory = reclassifyAllHistory;
  (window as any).forceUnifyHistory = () => {
    // 强制迁移分类历史记录到统一存储
    localStorage.removeItem('fuzz_test_history_unified');
    migrateOldHistoryFormat();
    loadHistoryFromStorage();
    console.log('[DEBUG] 强制统一历史记录完成');
  };
  (window as any).testMQTTAnimation = () => {
    console.log('[DEBUG] Manual MQTT animation test');
    initMQTTAnimations();
  };
}

// MQTT动画相关变量和函数
let mqttAnimationIntervals: number[] = [];

// 初始化MQTT动画
function initMQTTAnimations() {
  console.log('[MQTT Animation] Starting initialization...');
  // 清理旧的动画
  cleanupMQTTAnimations();

  // 等待DOM完全渲染后再初始化
  setTimeout(() => {
    // 批量初始化6个MQTT模块
    for (let moduleId = 1; moduleId <= 6; moduleId++) {
      console.log(`[MQTT Animation] Initializing module ${moduleId}`);
      initMQTTModule(moduleId);
    }
  }, 100);
}

// 清理MQTT动画
function cleanupMQTTAnimations() {
  mqttAnimationIntervals.forEach((interval) => clearInterval(interval));
  mqttAnimationIntervals = [];
}

// 单个MQTT模块初始化函数
function initMQTTModule(moduleId: number) {
  const module = document.getElementById(`mqtt-viz-${moduleId}`);
  if (!module) {
    console.warn(`[MQTT Animation] Module mqtt-viz-${moduleId} not found`);
    return;
  }

  const broker = module.querySelector('.mqtt-node:nth-child(1)') as HTMLElement;
  const client1 = module.querySelector(
    '.mqtt-node:nth-child(2)',
  ) as HTMLElement;
  const client2 = module.querySelector(
    '.mqtt-node:nth-child(3)',
  ) as HTMLElement;
  const connections = document.getElementById(
    `connections-viz-${moduleId}`,
  ) as SVGElement;
  const particles = document.getElementById(
    `particles-viz-${moduleId}`,
  ) as HTMLElement;

  console.log(`[MQTT Animation] Module ${moduleId} elements:`, {
    module: !!module,
    broker: !!broker,
    client1: !!client1,
    client2: !!client2,
    connections: !!connections,
    particles: !!particles,
  });

  if (!broker || !client1 || !client2 || !connections || !particles) {
    console.warn(`[MQTT Animation] Missing elements for module ${moduleId}`);
    return;
  }

  // 获取元素位置（基于当前模块容器定位）
  function getPosition(el: HTMLElement) {
    // 使用相对于模块容器的固定位置，而不是getBoundingClientRect
    const moduleRect = module.getBoundingClientRect();
    const elRect = el.getBoundingClientRect();

    // 查找图标元素（SVG）而不是整个节点
    const iconElement = el.querySelector('svg') as HTMLElement;
    let iconRect = elRect;

    if (iconElement) {
      iconRect = iconElement.getBoundingClientRect();
    }

    // 计算图标相对于模块容器的位置
    const iconCenterX = iconRect.left - moduleRect.left + iconRect.width / 2;
    const iconCenterY = iconRect.top - moduleRect.top + iconRect.height / 2;

    console.log(`[MQTT Animation] Icon position:`, {
      iconCenterX,
      iconCenterY,
      element: el.className,
      hasIcon: !!iconElement,
    });

    return {
      centerX: iconCenterX,
      centerY: iconCenterY,
      // 为broker添加左下角和右下角连接点（基于图标位置）
      leftBottom: {
        x: iconCenterX - iconRect.width / 3,
        y: iconCenterY + iconRect.height / 2,
      },
      rightBottom: {
        x: iconCenterX + iconRect.width / 3,
        y: iconCenterY + iconRect.height / 2,
      },
      // 图标顶部边缘连接点（左上角和右上角）
      topLeft: {
        x: iconCenterX - iconRect.width / 2,
        y: iconCenterY - iconRect.height / 2 - 2,
      },
      topRight: {
        x: iconCenterX + iconRect.width / 2,
        y: iconCenterY - iconRect.height / 2 - 2,
      },
    };
  }

  // 创建连接线
  function createConnections() {
    const bPos = getPosition(broker);
    const c1Pos = getPosition(client1);
    const c2Pos = getPosition(client2);

    // 清空之前的连接线，避免重复绘制
    connections.innerHTML = '';

    console.log(
      `[MQTT Animation] Creating connections for module ${moduleId}:`,
      {
        broker: bPos,
        client1: c1Pos,
        client2: c2Pos,
      },
    );

    function createPath(
      from: { x: number; y: number },
      to: { x: number; y: number },
      id: string,
      color: string = '#3B82F6',
    ) {
      const path = document.createElementNS(
        'http://www.w3.org/2000/svg',
        'path',
      );

      // 创建轻微弧度的优美曲线连接
      const midX = (from.x + to.x) / 2;
      const midY = (from.y + to.y) / 2;

      // 轻微的弧度控制点，符合大众审美
      let controlX = midX;
      let controlY = midY;

      // 根据连接方向添加轻微的弧度偏移
      if (id.includes('broker-client1')) {
        // Client1连接，轻微向左弯曲
        controlX = midX - 15;
        controlY = midY - 20;
      } else if (id.includes('broker-client2')) {
        // Client2连接，轻微向右弯曲
        controlX = midX + 15;
        controlY = midY - 20;
      }

      // 使用二次贝塞尔曲线创建轻微弧度
      const d = `M ${from.x} ${from.y} Q ${controlX} ${controlY} ${to.x} ${to.y}`;

      path.setAttribute('d', d);
      path.setAttribute('id', `${id}-${moduleId}`);
      path.setAttribute('class', 'mqtt-connection');
      path.setAttribute('stroke', color);
      path.setAttribute('stroke-width', '2');
      path.setAttribute('fill', 'none');
      path.setAttribute('opacity', '0.8');
      connections.appendChild(path);
      console.log(`[MQTT Animation] Created curved path ${id}: ${d}`);
      return path;
    }

    // 创建两条对称的连接线：Client1连接右上角，Client2连接左上角
    const path1 = createPath(
      bPos.leftBottom,
      c1Pos.topRight,
      'broker-client1',
      '#3B82F6',
    );
    const path2 = createPath(
      bPos.rightBottom,
      c2Pos.topLeft,
      'broker-client2',
      '#3B82F6',
    );

    return { path1, path2 };
  }

  // 创建流动粒子
  function createParticles(paths: any) {
    console.log(`[MQTT Animation] Creating particles for module ${moduleId}`);
    const particleSources = [
      // 第一条线：Broker到Client1的粒子（深蓝色）
      {
        path: paths.path1,
        start: 0,
        end: 1,
        interval: 1500,
        class: 'mqtt-particle-from-broker',
        speed: 80,
      },
      // 第一条线：Client1到Broker的粒子（浅蓝色）
      {
        path: paths.path1,
        start: 1,
        end: 0,
        interval: 2500,
        class: 'mqtt-particle-from-client',
        speed: 80,
      },
      // 第二条线：Broker到Client2的粒子（深蓝色）
      {
        path: paths.path2,
        start: 0,
        end: 1,
        interval: 2000,
        class: 'mqtt-particle-from-broker',
        speed: 80,
      },
      // 第二条线：Client2到Broker的粒子（浅蓝色）
      {
        path: paths.path2,
        start: 1,
        end: 0,
        interval: 3000,
        class: 'mqtt-particle-from-client',
        speed: 80,
      },
    ];

    // 立即创建第一批粒子，然后设置定时器
    particleSources.forEach((source, index) => {
      // 立即创建一个粒子
      setTimeout(() => {
        createParticle(
          source.path,
          source.start,
          source.end,
          source.class,
          source.speed,
        );
      }, index * 200);

      // 设置定时器持续创建粒子
      const interval = setInterval(() => {
        console.log(
          `[MQTT Animation] Creating particle ${index} for module ${moduleId}`,
        );
        createParticle(
          source.path,
          source.start,
          source.end,
          source.class,
          source.speed,
        );
      }, source.interval);
      mqttAnimationIntervals.push(interval);
    });

    console.log(
      `[MQTT Animation] Created ${particleSources.length} particle sources for module ${moduleId}`,
    );
  }

  // 创建单个粒子
  function createParticle(
    path: SVGPathElement,
    start: number,
    end: number,
    particleClass: string,
    speed: number,
  ) {
    try {
      const particle = document.createElement('div');
      particle.className = `mqtt-particle ${particleClass}`;
      // 根据粒子类型设置不同的样式
      const isBrokerParticle = particleClass.includes('broker');
      const backgroundColor = isBrokerParticle ? '#3B82F6' : '#60A5FA';
      const shadowColor = isBrokerParticle
        ? 'rgba(59, 130, 246, 0.8)'
        : 'rgba(96, 165, 250, 0.8)';

      particle.style.cssText = `
        position: absolute;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        transform: translate(-50%, -50%);
        z-index: 10;
        box-shadow: 0 0 6px ${shadowColor};
        background: ${backgroundColor};
        border: 1px solid rgba(255, 255, 255, 0.3);
      `;
      particles.appendChild(particle);

      const length = path.getTotalLength();
      const duration = (length / speed) * 1000;

      console.log(
        `[MQTT Animation] Created particle with length: ${length}, duration: ${duration}ms`,
      );

      let starttime: number | null = null;
      let animationId: number;

      function animate(timestamp: number) {
        if (!starttime) starttime = timestamp;
        const progress = Math.min((timestamp - starttime) / duration, 1);

        if (progress < 1 && particles.contains(particle)) {
          try {
            const currentLength =
              start * length + progress * (end - start) * length;
            const pos = path.getPointAtLength(currentLength);

            // 添加一些随机抖动使动画更生动
            const jitterX = (Math.random() - 0.5) * 1;
            const jitterY = (Math.random() - 0.5) * 1;

            particle.style.left = `${pos.x + jitterX}px`;
            particle.style.top = `${pos.y + jitterY}px`;

            // 根据进度调整透明度
            const opacity = Math.sin(progress * Math.PI);
            particle.style.opacity = opacity.toString();

            animationId = requestAnimationFrame(animate);
          } catch (pathError) {
            console.warn(`[MQTT Animation] Path error:`, pathError);
            particle.remove();
          }
        } else {
          // 动画完成，移除粒子
          if (animationId) {
            cancelAnimationFrame(animationId);
          }
          setTimeout(() => {
            if (particles.contains(particle)) {
              particle.remove();
            }
          }, 50);
        }
      }

      // 开始动画
      animationId = requestAnimationFrame(animate);
    } catch (error) {
      console.error(`[MQTT Animation] Error creating particle:`, error);
    }
  }

  // 初始化当前模块
  function init() {
    const paths = createConnections();
    createParticles(paths);
  }

  // 执行当前模块初始化
  init();
}

// 错误捕获处理
onErrorCaptured((err, instance, info) => {
  console.error('[Vue Error Captured]:', err);
  console.error('[Component Instance]:', instance);
  console.error('[Error Info]:', info);

  // 如果是MQTT相关的DOM错误，尝试恢复
  if (
    err.message &&
    err.message.includes('nextSibling') &&
    protocolType.value === 'MQTT'
  ) {
    console.warn('[MQTT DOM Error] 检测到DOM更新错误，尝试重置MQTT日志状态');
    try {
      nextTick(() => {
        mqttDifferentialLogs.value = [];
        mqttLogsUpdateKey.value++;
        console.log('[MQTT DOM Error] MQTT日志状态已重置');
      });
    } catch (resetError) {
      console.error('[MQTT DOM Error] 重置失败:', resetError);
    }
  }

  // 返回false让错误继续传播，但不会导致应用崩溃
  return false;
});

// 组件卸载时清理
onUnmounted(() => {
  console.log('[DEBUG] 组件卸载，清理MQTT相关资源');

  // 清理MQTT动画
  cleanupMQTTAnimations();

  // 清理MQTT定时器和数据
  if (mqttUpdateTimer) {
    clearTimeout(mqttUpdateTimer);
    mqttUpdateTimer = null;
  }
  mqttDifferentialLogsData = [];
  mqttLogsPendingUpdate = false;

  // 清理其他定时器
  if (testTimer) {
    clearInterval(testTimer as any);
    testTimer = null;
  }

  if (logReadingInterval.value) {
    clearInterval(logReadingInterval.value);
    logReadingInterval.value = null;
  }

  // 停止测试
  isRunning.value = false;
  mqttSimulationCancelled = true;
});

onMounted(async () => {
  // 加载历史记录
  loadHistoryFromStorage();

  await fetchText();
  if (rawText.value) {
    parseText(rawText.value);
  }

  // Wait for DOM to be fully rendered before initializing charts
  await nextTick();

  // Initialize charts - Canvas elements should now always be available
  const success = initCharts();
  if (success) {
    console.log('Charts initialized successfully on mount');

    // 如果已有fuzz数据但统计数据为空，重新计算统计数据
    if (protocolType.value === 'SNMP' && snmpFuzzData.value.length > 0) {
      const hasValidData =
        protocolStats.value.v1 +
          protocolStats.value.v2c +
          protocolStats.value.v3 >
          0 ||
        messageTypeStats.value.get +
          messageTypeStats.value.set +
          messageTypeStats.value.getnext +
          messageTypeStats.value.getbulk >
          0;

      if (!hasValidData) {
        console.log('Recalculating stats on mount due to empty statistics');
        recalculateStatsFromFuzzData();
      }
    }

    // Update charts with initial data but don't show them yet
    updateCharts();
    // 只有在有完整数据且测试已完成时才显示图表
    if (isTestCompleted.value) {
      showCharts.value = true;
    }
  } else {
    console.error('Failed to initialize charts');
  }

  // MQTT协议不需要图表初始化，使用统计卡片显示
  if (protocolType.value === 'MQTT') {
    console.log('MQTT protocol uses statistical cards instead of charts');
    // 初始化MQTT协议实现选项
    const config = protocolImplementationConfigs[fuzzEngine.value];
    if (config) {
      protocolImplementations.value = config.defaultImplementations;
      console.log('[DEBUG] 初始化MQTT协议实现选项:', protocolImplementations.value);
      console.log('[DEBUG] 当前选择的实现:', selectedProtocolImplementation.value);
      console.log('[DEBUG] 当前引擎:', fuzzEngine.value);
    }
    // MQTT动画将在测试开始时初始化
  }

  // Set initial last update time
  lastUpdate.value = new Date().toLocaleString();
});
</script>

<template>
  <Page
    title="协议模糊测试"
  >
    <!-- 加载状态 -->
    <div v-if="loading" class="flex h-64 items-center justify-center">
      <div
        class="border-primary h-12 w-12 animate-spin rounded-full border-b-2"
      ></div>
    </div>

    <!-- 错误状态 -->
    <div
      v-else-if="error"
      class="mb-6 rounded-lg border border-red-200 bg-red-50 p-4"
    >
      <div class="text-red-600">{{ error }}</div>
    </div>

    <!-- 主要内容 - 使用 Tabs -->
    <div v-else>
      <Tabs v-model:activeKey="activeTab" class="fuzz-tabs">
        <!-- 实时测试标签页 -->
        <Tabs.TabPane key="test" tab="实时测试">
          <!-- 测试配置区 -->
          <div
            class="border-primary/20 mb-6 rounded-xl border bg-white/80 p-4 backdrop-blur-sm"
          >
            <h3 class="mb-4 text-lg font-semibold">测试配置</h3>
            <div class="grid grid-cols-1 gap-4 md:grid-cols-3 lg:grid-cols-5">
              <!-- 协议选择 -->
              <div>
                <label class="text-dark/70 mb-2 block text-sm">协议类型</label>
                <div class="relative">
                  <select
                    v-model="protocolType"
                    class="border-primary/20 focus:ring-primary w-full appearance-none rounded-lg border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  >
                    <option value="SNMP">SNMP</option>
                    <option value="MQTT">MQTT</option>
                  </select>
                  <i
                    class="fa fa-chevron-down text-dark/50 pointer-events-none absolute right-3 top-2.5"
                  ></i>
                </div>
              </div>

              <!-- Fuzz引擎选择 -->
              <div>
                <label class="text-dark/70 mb-2 block text-sm">Fuzz引擎</label>
                <div class="relative">
                  <select
                    v-model="fuzzEngine"
                    class="border-primary/20 focus:ring-primary w-full appearance-none rounded-lg border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  >
                    <option value="SNMP_Fuzz" v-if="protocolType === 'SNMP'">
                      SNMP_Fuzz
                    </option>
                    <option value="AFLNET" v-if="protocolType === 'RTSP' || protocolType === 'MQTT'">
                      AFLNET
                    </option>
                    <option value="MBFuzzer" v-if="protocolType === 'MQTT'">
                      MBFuzzer
                    </option>
                  </select>
                  <i
                    class="fa fa-chevron-down text-dark/50 pointer-events-none absolute right-3 top-2.5"
                  ></i>
                </div>
              </div>

              <!-- 协议实现选择 -->
              <div>
                <label class="text-dark/70 mb-2 block text-sm">协议实现</label>
                <div class="relative">
                  <select
                    v-model="selectedProtocolImplementation"
                    class="border-primary/20 focus:ring-primary w-full appearance-none rounded-lg border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  >
                    <option
                      v-for="impl in protocolImplementationConfigs[fuzzEngine].defaultImplementations"
                      :key="impl"
                      :value="impl"
                    >
                      {{ impl }}
                    </option>
                  </select>
                  <i
                    class="fa fa-chevron-down text-dark/50 pointer-events-none absolute right-3 top-2.5"
                  ></i>
                </div>
              </div>

              <!-- 目标主机 -->
              <div>
                <label class="text-dark/70 mb-2 block text-sm">目标主机</label>
                <div class="relative">
                  <input
                    type="text"
                    v-model="targetHost"
                    class="border-primary/20 focus:ring-primary w-full rounded-lg border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  />
                  <i
                    class="fa fa-server text-dark/50 absolute right-3 top-2.5"
                  ></i>
                </div>
              </div>

              <!-- 目标端口 -->
              <div>
                <label class="text-dark/70 mb-2 block text-sm">目标端口</label>
                <div class="relative">
                  <input
                    type="number"
                    v-model="targetPort"
                    min="1"
                    max="65535"
                    class="border-primary/20 focus:ring-primary w-full rounded-lg border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  />
                  <i
                    class="fa fa-plug text-dark/50 absolute right-3 top-2.5"
                  ></i>
                </div>
              </div>
            </div>

            <!-- 指令配置 -->
            <div v-if="protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL'" class="mt-4">
              <label class="text-dark/70 mb-2 block text-sm">指令配置</label>
              <div class="relative">
                <textarea
                  v-model="solCommandConfig"
                  rows="3"
                  class="border-primary/20 focus:ring-primary w-full resize-none rounded-lg border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  placeholder="请输入SOL的指令配置..."
                ></textarea>
                <i
                  class="fa fa-terminal text-dark/50 absolute right-3 top-2.5"
                ></i>
              </div>
            </div>

            <div class="mt-4 flex justify-end">
              <button
                @click="startTest"
                :disabled="!canStartTest"
                :title="
                  !canStartTest
                    ? loading
                      ? '数据加载中...'
                      : error
                        ? '数据加载失败'
                        : snmpFuzzData.length === 0
                          ? '无测试数据'
                          : isRunning
                            ? '测试进行中'
                            : '未知错误'
                    : '开始测试'
                "
                class="bg-primary hover:bg-primary/90 flex items-center rounded-lg px-6 py-2 text-white transition-all duration-300 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <i class="fa fa-play mr-2"></i> 开始测试
              </button>
              <button
                v-if="isRunning"
                @click="handleStopTest"
                class="bg-danger/10 hover:bg-danger/20 text-danger ml-3 flex items-center rounded-lg px-6 py-2 transition-all duration-300"
              >
                <i class="fa fa-stop mr-2"></i> 停止测试
              </button>
            </div>
          </div>

          <!-- 测试过程展示区 -->
          <div class="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-4">
            <!-- 实时Fuzz过程窗口 -->
            <div
              class="border-primary/20 rounded-xl border bg-white/80 p-4 backdrop-blur-sm xl:col-span-3"
            >
              <div class="mb-4 flex items-center justify-between">
                <h3 class="text-lg font-semibold">Fuzz过程</h3>
                <div class="flex space-x-2">
                  <button
                    @click="clearAllLogs"
                    class="bg-light-gray hover:bg-medium-gray border-dark/10 text-dark/70 rounded border px-2 py-1 text-xs"
                  >
                    清空日志
                  </button>
                  <button
                    v-if="isRunning"
                    @click="togglePauseTest"
                    class="bg-light-gray hover:bg-medium-gray border-dark/10 text-dark/70 rounded border px-2 py-1 text-xs"
                  >
                    {{ isPaused ? '继续' : '暂停' }}
                  </button>
                  <button
                    v-if="logEntries.length > 0"
                    @click="saveLog"
                    class="bg-primary/10 hover:bg-primary/20 text-primary rounded px-2 py-1 text-xs"
                  >
                    保存日志
                  </button>
                </div>
              </div>

              <!-- 统一的日志容器 -->
              <!-- 协议隔离的日志容器 -->
              <ProtocolLogViewer
                :protocol="protocolType"
                :logs="protocolStates[protocolType].logs"
                :is-active="true"
                :format-log-content="getLogFormatter(protocolType)"
              />
            </div>

            <!-- 运行监控 -->
            <div class="xl:col-span-1">
              <div
                class="border-secondary/20 h-full rounded-xl border bg-white/80 p-4 backdrop-blur-sm"
              >
                <div class="mb-4 flex items-center justify-between">
                  <h3 class="text-lg font-semibold">运行监控</h3>
                  <span
                    v-if="protocolType === 'MQTT'"
                    :class="[
                      'rounded-full px-2 py-0.5 text-xs',
                      !isRunning
                        ? 'bg-gray-100 text-gray-600'
                        : mqttRealTimeStats.crash_number > 0
                          ? 'animate-pulse bg-red-100 text-red-600'
                          : mqttRealTimeStats.diff_number > 0
                            ? 'bg-yellow-100 text-yellow-600'
                            : 'bg-green-100 text-green-600',
                    ]"
                  >
                    {{
                      !isRunning
                        ? '待启动'
                        : mqttRealTimeStats.crash_number > 0
                          ? '检测到异常'
                          : mqttRealTimeStats.diff_number > 0
                            ? '发现差异'
                            : '运行正常'
                    }}
                  </span>
                  <span
                    v-else-if="
                      protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL' && solStats.unique_crashes > 0
                    "
                    class="bg-danger/10 text-danger animate-pulse rounded-full px-2 py-0.5 text-xs"
                  >
                    {{ solStats.unique_crashes }} 个崩溃
                  </span>
                  <span
                    v-else-if="protocolType === 'SNMP' && crashCount > 0"
                    class="bg-danger/10 text-danger animate-pulse rounded-full px-2 py-0.5 text-xs"
                  >
                    {{ crashCount }} 个崩溃
                  </span>
                  <span
                    v-else
                    :class="[
                      'rounded-full px-2 py-0.5 text-xs',
                      !isRunning
                        ? 'bg-gray-100 text-gray-600'
                        : 'bg-success/10 text-success'
                    ]"
                  >
                    {{ !isRunning ? '待启动' : '正常' }}
                  </span>
                </div>

                <!-- SOL崩溃统计 (AFLNET引擎) -->
                <div v-if="protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL'" class="space-y-4">
                  <div class="grid grid-cols-2 gap-4">
                    <div
                      class="rounded-lg border border-red-200 bg-red-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-red-600">
                        {{ solStats.unique_crashes }}
                      </div>
                      <div class="text-xs text-red-700">崩溃数</div>
                      <div class="mt-1 text-xs text-gray-500">Crashes</div>
                    </div>
                    <div
                      class="rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-yellow-600">
                        {{ solStats.unique_hangs }}
                      </div>
                      <div class="text-xs text-yellow-700">挂起数</div>
                      <div class="mt-1 text-xs text-gray-500">Hangs</div>
                    </div>
                  </div>

                  <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <div class="mb-2 text-xs text-gray-600">监控状态</div>
                    <div class="flex items-center space-x-2">
                      <div
                        class="h-2 w-2 rounded-full"
                        :class="
                          !isRunning
                            ? 'bg-gray-400'
                            : solStats.unique_crashes > 0
                              ? 'animate-pulse bg-red-500'
                              : 'animate-pulse bg-green-500'
                        "
                      ></div>
                      <span
                        class="text-sm"
                        :class="
                          !isRunning
                            ? 'text-gray-600'
                            : solStats.unique_crashes > 0
                              ? 'font-medium text-red-700'
                              : 'text-gray-700'
                        "
                      >
                        {{
                          !isRunning
                            ? '待启动'
                            : solStats.unique_crashes > 0
                              ? '检测到异常'
                              : '持续监控中...'
                        }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- MQTT协议运行监控 (MBFuzzer引擎) -->
                <div v-else-if="protocolType === 'MQTT'" class="space-y-4">
                  <div class="grid grid-cols-1 gap-4">
                    <div
                      class="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-center"
                    >
                      <div class="mb-2 text-3xl font-bold text-yellow-600">
                        {{
                          isTestCompleted
                            ? mqttStats.diff_number
                            : mqttDifferentialStats.total_differences
                        }}
                      </div>
                      <div class="text-sm font-medium text-yellow-700">
                        协议差异发现
                      </div>
                      <div class="mt-1 text-xs text-gray-500">
                        Protocol Differences
                      </div>
                    </div>

                    <div
                      class="rounded-lg border border-red-200 bg-red-50 p-4 text-center"
                    >
                      <div class="mb-2 text-3xl font-bold text-red-600">
                        {{ mqttStats.crash_number }}
                      </div>
                      <div class="text-sm font-medium text-red-700">
                        崩溃检测
                      </div>
                      <div class="mt-1 text-xs text-gray-500">
                        Crashes Detected
                      </div>
                    </div>
                  </div>

                  <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <div class="mb-2 text-xs text-gray-600">监控状态</div>
                    <div class="flex items-center space-x-2">
                      <div
                        class="h-2 w-2 rounded-full"
                        :class="
                          !isRunning
                            ? 'bg-gray-400'
                            : mqttStats.crash_number > 0
                              ? 'animate-pulse bg-red-500'
                              : (
                                    isTestCompleted
                                      ? mqttStats.diff_number > 0
                                      : mqttDifferentialStats.total_differences >
                                        0
                                  )
                                ? 'animate-pulse bg-yellow-500'
                                : 'animate-pulse bg-green-500'
                        "
                      ></div>
                      <span
                        class="text-sm"
                        :class="
                          !isRunning
                            ? 'text-gray-600'
                            : mqttStats.crash_number > 0
                              ? 'font-medium text-red-700'
                              : (
                                    isTestCompleted
                                      ? mqttStats.diff_number > 0
                                      : mqttDifferentialStats.total_differences >
                                        0
                                  )
                                ? 'font-medium text-yellow-700'
                                : 'text-gray-700'
                        "
                      >
                        {{
                          !isRunning
                            ? '待启动'
                            : mqttStats.crash_number > 0
                              ? '检测到崩溃异常'
                              : (
                                    isTestCompleted
                                      ? mqttStats.diff_number > 0
                                      : mqttDifferentialStats.total_differences >
                                        0
                                  )
                                ? '发现协议差异'
                                : '差异分析中...'
                        }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- SNMP协议崩溃统计 -->
                <div v-else-if="protocolType === 'SNMP'" class="space-y-4">
                  <div class="grid grid-cols-1 gap-4">
                    <div
                      class="rounded-lg border border-red-200 bg-red-50 p-4 text-center"
                    >
                      <div class="mb-2 text-3xl font-bold text-red-600">
                        {{ crashCount }}
                      </div>
                      <div class="text-sm font-medium text-red-700">
                        崩溃检测
                      </div>
                      <div class="mt-1 text-xs text-gray-500">
                        Crashes Detected
                      </div>
                    </div>
                  </div>

                  <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <div class="mb-2 text-xs text-gray-600">监控状态</div>
                    <div class="flex items-center space-x-2">
                      <div
                        class="h-2 w-2 rounded-full"
                        :class="
                          !isRunning
                            ? 'bg-gray-400'
                            : crashCount > 0
                              ? 'animate-pulse bg-red-500'
                              : 'animate-pulse bg-green-500'
                        "
                      ></div>
                      <span
                        class="text-sm"
                        :class="
                          !isRunning
                            ? 'text-gray-600'
                            : crashCount > 0
                              ? 'font-medium text-red-700'
                              : 'text-gray-700'
                        "
                      >
                        {{
                          !isRunning
                            ? '待启动'
                            : crashCount > 0
                              ? '检测到崩溃异常'
                              : '运行正常'
                        }}
                      </span>
                    </div>
                    <div class="mt-1 text-xs text-gray-500">
                      崩溃率:
                      {{
                        packetCount > 0
                          ? Math.round((crashCount / packetCount) * 100)
                          : 0
                      }}%
                    </div>
                  </div>
                </div>

                <!-- 其他协议的默认显示 -->
                <div
                  v-else
                  class="text-dark/50 flex h-full flex-col items-center justify-center text-sm"
                >
                  <div class="bg-success/10 mb-4 rounded-full p-4">
                    <i class="fa fa-shield text-success/70 text-3xl"></i>
                  </div>
                  <p>{{ !isRunning ? '尚未启动测试' : '尚未检测到程序崩溃' }}</p>
                  <p class="mt-1">{{ !isRunning ? '待启动' : '持续监控中...' }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 测试结果分析 -->
          <div class="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-4">
            <!-- 消息类型分布和版本统计 / RTSP状态机统计 -->
            <div
              class="border-secondary/20 flex min-h-96 flex-col rounded-xl border bg-white/80 p-6 backdrop-blur-sm xl:col-span-3"
            >
              <div class="mb-6 flex items-center justify-between">
                <h3 class="text-xl font-semibold">
                  {{
                    protocolType === 'RTSP'
                      ? 'SOL状态机统计'
                      : protocolType === 'MQTT'
                        ? (selectedProtocolImplementation === 'SOL'
                            ? 'SOLAFLNET模糊测试'
                            : 'MQTT多方模糊测试')
                        : '消息类型分布与版本统计'
                  }}
                </h3>
              </div>

              <!-- SNMP协议图表 -->
              <div
                v-if="protocolType === 'SNMP'"
                class="grid h-72 grid-cols-1 gap-8 md:grid-cols-2"
              >
                <!-- 消息类型分布饼状图 -->
                <div>
                  <h4
                    class="text-dark/80 mb-3 text-center text-base font-medium"
                  >
                    消息类型分布
                  </h4>
                  <div class="relative h-60">
                    <canvas
                      ref="messageCanvas"
                      id="messageTypeMainChart"
                      class="absolute inset-0 transition-opacity duration-500"
                      :class="{ 'opacity-0': !isTestCompleted }"
                    ></canvas>
                    <div
                      v-if="!isTestCompleted"
                      class="text-dark/50 absolute inset-0 flex flex-col items-center justify-center rounded-lg bg-white"
                    >
                      <div class="bg-primary/10 mb-2 rounded-full p-3">
                        <i class="fa fa-pie-chart text-primary/70 text-2xl"></i>
                      </div>
                      <span class="text-xs">数据统计中...</span>
                    </div>
                  </div>
                </div>
                <!-- SNMP版本分布饼状图 -->
                <div>
                  <h4
                    class="text-dark/80 mb-3 text-center text-base font-medium"
                  >
                    SNMP版本分布
                  </h4>
                  <div class="relative h-60">
                    <canvas
                      ref="versionCanvas"
                      id="versionDistributionChart"
                      class="absolute inset-0 transition-opacity duration-500"
                      :class="{ 'opacity-0': !isTestCompleted }"
                    ></canvas>
                    <div
                      v-if="!isTestCompleted"
                      class="text-dark/50 absolute inset-0 flex flex-col items-center justify-center rounded-lg bg-white"
                    >
                      <div class="bg-primary/10 mb-2 rounded-full p-3">
                        <i class="fa fa-chart-pie text-primary/70 text-2xl"></i>
                      </div>
                      <span class="text-xs">数据统计中...</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- SOLAFLNET测试区域 - 显示原来的RTSP状态机界面 -->
              <div v-else-if="protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL'" class="min-h-0 flex-1">
                <!-- 初始状态显示设备待启动 -->
                <div
                  v-if="!isRunning && !isTestCompleted"
                  class="flex h-full items-center justify-center"
                >
                  <div class="text-center">
                    <div
                      class="mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-full bg-purple-100 p-8"
                    >
                      <IconifyIcon
                        icon="mdi:state-machine"
                        class="text-4xl text-purple-500"
                      />
                    </div>
                    <div class="mb-2 text-lg font-medium text-gray-600">
                      SOL状态机待启动
                    </div>
                    <div class="text-sm text-gray-500">
                      点击"开始测试"启动SOLAFLNET状态机模糊测试
                    </div>
                  </div>
                </div>

                <!-- SOL状态机统计 - 运行时显示 -->
                <div v-else class="grid h-72 grid-cols-1 gap-8 md:grid-cols-2">
                  <!-- 路径发现趋势 -->
                  <div>
                    <h4
                      class="text-dark/80 mb-3 text-center text-base font-medium"
                    >
                      路径发现统计
                    </h4>
                    <div
                      class="h-60 rounded-lg border border-gray-200 bg-white p-4"
                    >
                      <div class="grid h-full grid-cols-2 gap-4">
                        <div
                          class="flex flex-col items-center justify-center rounded-lg bg-blue-50 p-4"
                        >
                          <div class="mb-2 text-3xl font-bold text-blue-600">
                            {{ solStats.paths_total }}
                          </div>
                          <div class="text-center text-sm text-gray-600">
                            总路径数
                          </div>
                          <div class="mt-1 text-xs text-gray-500">
                            Total Paths
                          </div>
                        </div>
                        <div
                          class="flex flex-col items-center justify-center rounded-lg bg-green-50 p-4"
                        >
                          <div class="mb-2 text-3xl font-bold text-green-600">
                            {{ solStats.cur_path }}
                          </div>
                          <div class="text-center text-sm text-gray-600">
                            当前路径
                          </div>
                          <div class="mt-1 text-xs text-gray-500">
                            Current Path
                          </div>
                        </div>
                        <div
                          class="flex flex-col items-center justify-center rounded-lg bg-yellow-50 p-4"
                        >
                          <div class="mb-2 text-3xl font-bold text-yellow-600">
                            {{ solStats.pending_total }}
                          </div>
                          <div class="text-center text-sm text-gray-600">
                            待处理
                          </div>
                          <div class="mt-1 text-xs text-gray-500">Pending</div>
                        </div>
                        <div
                          class="flex flex-col items-center justify-center rounded-lg bg-purple-50 p-4"
                        >
                          <div class="mb-2 text-3xl font-bold text-purple-600">
                            {{ solStats.pending_favs }}
                          </div>
                          <div class="text-center text-sm text-gray-600">
                            优先路径
                          </div>
                          <div class="mt-1 text-xs text-gray-500">Favored</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 状态机拓扑 -->
                  <div>
                    <h4
                      class="text-dark/80 mb-3 text-center text-base font-medium"
                    >
                      协议状态机拓扑
                    </h4>
                    <div
                      class="h-60 rounded-lg border border-gray-200 bg-white p-4"
                    >
                      <div class="flex h-full flex-col">
                        <!-- 状态机可视化区域 -->
                        <div
                          class="mb-4 flex flex-1 items-center justify-center rounded-lg bg-gray-50 p-4"
                        >
                          <div class="text-center">
                            <div
                              class="mb-4 flex items-center justify-center space-x-4"
                            >
                              <div
                                class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 text-xs font-bold text-white"
                              >
                                {{ solStats.n_nodes }}
                              </div>
                              <div class="text-gray-400">
                                <i class="fa fa-arrow-right text-lg"></i>
                              </div>
                              <div
                                class="flex h-8 w-8 items-center justify-center rounded-full bg-green-500 text-xs font-bold text-white"
                              >
                                {{ solStats.n_edges }}
                              </div>
                            </div>
                            <div class="text-xs text-gray-600">
                              <span class="font-medium text-blue-600"
                                >{{ solStats.n_nodes }} 个状态节点</span
                              >
                              <span class="mx-2">•</span>
                              <span class="font-medium text-green-600"
                                >{{ solStats.n_edges }} 个状态转换</span
                              >
                            </div>
                          </div>
                        </div>

                        <!-- 状态机统计信息 -->
                        <div class="grid grid-cols-2 gap-2 text-xs">
                          <div class="rounded bg-blue-50 p-2 text-center">
                            <div class="font-bold text-blue-600">
                              {{ solStats.max_depth }}
                            </div>
                            <div class="text-gray-600">最大深度</div>
                          </div>
                          <div class="rounded bg-green-50 p-2 text-center">
                            <div class="font-bold text-green-600">
                              {{ solStats.map_size }}
                            </div>
                            <div class="text-gray-600">覆盖率</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- MQTT协议统计 -->
              <!-- MQTT协议实时动画可视化区域 -->
              <div v-else-if="protocolType === 'MQTT'" class="min-h-0 flex-1">
                <!-- 初始状态显示设备待启动 -->
                <div
                  v-if="!isRunning && !isTestCompleted"
                  class="flex h-full items-center justify-center"
                >
                  <div class="text-center">
                    <div
                      class="mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-full bg-gray-100 p-8"
                    >
                      <IconifyIcon
                        icon="mdi:power-standby"
                        class="text-4xl text-gray-500"
                      />
                    </div>
                    <div class="mb-2 text-lg font-medium text-gray-600">
                      设备待启动
                    </div>
                    <div class="text-sm text-gray-500">
                      点击"开始测试"启动MQTT多方模糊测试
                    </div>
                  </div>
                </div>
                <!-- MQTT动画网格容器 - 测试运行时显示 -->
                <div
                  v-else
                  class="grid h-full grid-cols-2 gap-3 p-2 lg:grid-cols-3"
                >
                  <!-- MQTT模块1 -->
                  <div class="mqtt-module" :id="`mqtt-viz-1`">
                    <div
                      class="mqtt-node absolute left-1/2 top-6 -translate-x-1/2 transform text-blue-600"
                    >
                      <IconifyIcon icon="mdi:server" class="text-4xl" />
                      <span class="text-xs font-medium">HiveMQ</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 left-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:chip" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Client)</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 right-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:cloud" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Broker)</span>
                    </div>
                    <svg
                      class="absolute inset-0 h-full w-full"
                      :id="`connections-viz-1`"
                    ></svg>
                    <div
                      :id="`particles-viz-1`"
                      class="pointer-events-none absolute inset-0 h-full w-full"
                    ></div>
                  </div>

                  <!-- MQTT模块2 -->
                  <div class="mqtt-module" :id="`mqtt-viz-2`">
                    <div
                      class="mqtt-node absolute left-1/2 top-6 -translate-x-1/2 transform text-blue-600"
                    >
                      <IconifyIcon icon="mdi:server" class="text-4xl" />
                      <span class="text-xs font-medium">VerneMQ</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 left-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:chip" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Client)</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 right-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:cloud" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Broker)</span>
                    </div>
                    <svg
                      class="absolute inset-0 h-full w-full"
                      :id="`connections-viz-2`"
                    ></svg>
                    <div
                      :id="`particles-viz-2`"
                      class="pointer-events-none absolute inset-0 h-full w-full"
                    ></div>
                  </div>

                  <!-- MQTT模块3 -->
                  <div class="mqtt-module" :id="`mqtt-viz-3`">
                    <div
                      class="mqtt-node absolute left-1/2 top-6 -translate-x-1/2 transform text-blue-600"
                    >
                      <IconifyIcon icon="mdi:server" class="text-4xl" />
                      <span class="text-xs font-medium">EMQX</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 left-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:chip" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Client)</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 right-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:cloud" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Broker)</span>
                    </div>
                    <svg
                      class="absolute inset-0 h-full w-full"
                      :id="`connections-viz-3`"
                    ></svg>
                    <div
                      :id="`particles-viz-3`"
                      class="pointer-events-none absolute inset-0 h-full w-full"
                    ></div>
                  </div>

                  <!-- MQTT模块4 -->
                  <div class="mqtt-module" :id="`mqtt-viz-4`">
                    <div
                      class="mqtt-node absolute left-1/2 top-6 -translate-x-1/2 transform text-blue-600"
                    >
                      <IconifyIcon icon="mdi:server" class="text-4xl" />
                      <span class="text-xs font-medium">FlashMQ</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 left-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:chip" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Client)</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 right-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:cloud" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Broker)</span>
                    </div>
                    <svg
                      class="absolute inset-0 h-full w-full"
                      :id="`connections-viz-4`"
                    ></svg>
                    <div
                      :id="`particles-viz-4`"
                      class="pointer-events-none absolute inset-0 h-full w-full"
                    ></div>
                  </div>

                  <!-- MQTT模块5 -->
                  <div class="mqtt-module" :id="`mqtt-viz-5`">
                    <div
                      class="mqtt-node absolute left-1/2 top-6 -translate-x-1/2 transform text-blue-600"
                    >
                      <IconifyIcon icon="mdi:server" class="text-4xl" />
                      <span class="text-xs font-medium">NanoMQ</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 left-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:chip" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Client)</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 right-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:cloud" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Broker)</span>
                    </div>
                    <svg
                      class="absolute inset-0 h-full w-full"
                      :id="`connections-viz-5`"
                    ></svg>
                    <div
                      :id="`particles-viz-5`"
                      class="pointer-events-none absolute inset-0 h-full w-full"
                    ></div>
                  </div>

                  <!-- MQTT模块6 -->
                  <div class="mqtt-module" :id="`mqtt-viz-6`">
                    <div
                      class="mqtt-node absolute left-1/2 top-6 -translate-x-1/2 transform text-blue-600"
                    >
                      <IconifyIcon icon="mdi:server" class="text-4xl" />
                      <span class="text-xs font-medium">Mosquitto</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 left-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:chip" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Client)</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 right-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:cloud" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Broker)</span>
                    </div>
                    <svg
                      class="absolute inset-0 h-full w-full"
                      :id="`connections-viz-6`"
                    ></svg>
                    <div
                      :id="`particles-viz-6`"
                      class="pointer-events-none absolute inset-0 h-full w-full"
                    ></div>
                  </div>
                </div>
              </div>

              <!-- 其他协议的默认显示 -->
              <div v-else class="min-h-0 flex-1">
                <div class="flex h-full items-center justify-center">
                  <div class="text-center text-gray-500">
                    <div class="mb-4">
                      <i class="fa fa-chart-bar text-4xl text-gray-400"></i>
                    </div>
                    <p>暂无协议统计数据</p>
                  </div>
                </div>
              </div>
            </div>

            <!-- 实时统计 -->
            <div
              class="border-primary/20 rounded-xl border bg-white/80 p-6 backdrop-blur-sm xl:col-span-1"
            >
              <h3 class="mb-4 text-lg font-semibold">实时统计</h3>

              <!-- SNMP协议统计 -->
              <div v-if="protocolType === 'SNMP'" class="space-y-6">
                <div>
                  <div class="mb-1 flex items-center justify-between">
                    <span class="text-dark/70 text-sm">总发送包数</span>
                    <span class="text-xl font-bold">{{ packetCount }}</span>
                  </div>
                  <div
                    class="bg-light-gray h-1.5 w-full overflow-hidden rounded-full"
                  >
                    <div
                      class="bg-primary h-full"
                      :style="{ width: progressWidth + '%' }"
                    ></div>
                  </div>
                </div>

                <div class="grid grid-cols-1 gap-4">
                  <!-- 第一行：正常响应和构造失败 -->
                  <div class="grid grid-cols-2 gap-4">
                    <div
                      class="bg-light-gray border-success/20 rounded-lg border p-4"
                    >
                      <p class="text-success/70 mb-2 text-sm">正常响应</p>
                      <h4 class="text-success text-3xl font-bold">
                        {{ successCount }}
                      </h4>
                      <p class="text-dark/60 mt-2 text-sm">
                        {{ successRate }}%
                      </p>
                    </div>

                    <div
                      class="rounded-lg border border-red-200 bg-gray-50 p-4"
                    >
                      <p class="text-danger/70 mb-2 text-sm">构造失败</p>
                      <h4 class="text-danger text-3xl font-bold">
                        {{ failedCount }}
                      </h4>
                      <p class="text-dark/60 mt-2 text-sm">{{ failedRate }}%</p>
                    </div>
                  </div>

                  <!-- 第二行：超时和速度 -->
                  <div class="grid grid-cols-2 gap-4">
                    <div
                      class="bg-light-gray border-warning/20 rounded-lg border p-4"
                    >
                      <p class="text-warning/70 mb-2 text-sm">超时</p>
                      <h4 class="text-warning text-3xl font-bold">
                        {{ timeoutCount }}
                      </h4>
                      <p class="text-dark/60 mt-2 text-sm">
                        {{ timeoutRate }}%
                      </p>
                    </div>

                    <div
                      class="bg-light-gray border-info/20 rounded-lg border p-4"
                    >
                      <p class="text-info/70 mb-2 text-sm">发包速度</p>
                      <h4 class="text-info text-3xl font-bold">
                        {{ currentSpeed }}
                      </h4>
                      <p class="text-dark/60 mt-2 text-sm">包/秒</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- SOL统计 (AFLNET引擎) -->
              <div v-else-if="protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL'" class="space-y-4">
                <div>
                  <div class="mb-1 flex items-center justify-between">
                    <span class="text-dark/70 text-sm">当前执行路径</span>
                    <span class="text-xl font-bold"
                      >#{{ solStats.cur_path }}</span
                    >
                  </div>
                  <div
                    class="bg-light-gray h-1.5 w-full overflow-hidden rounded-full"
                  >
                    <div
                      class="bg-primary h-full"
                      :style="{
                        width:
                          solStats.paths_total > 0
                            ? Math.min(
                                100,
                                (solStats.cur_path / solStats.paths_total) *
                                  100,
                              )
                            : 0 + '%',
                      }"
                    ></div>
                  </div>
                  <div class="text-dark/60 mt-1 text-xs">
                    {{ solStats.cur_path }} / {{ solStats.paths_total }} 路径
                  </div>
                </div>

                <div class="grid grid-cols-1 gap-3">
                  <!-- 第一行：执行速度和测试时长 -->
                  <div class="grid grid-cols-2 gap-3">
                    <div
                      class="rounded-lg border border-blue-200 bg-blue-50 p-3"
                    >
                      <p class="mb-1 text-xs text-blue-700">执行速度</p>
                      <h4 class="text-2xl font-bold text-blue-600">
                        {{ solStats.execs_per_sec.toFixed(1) }}
                      </h4>
                      <p class="text-dark/60 mt-1 text-xs">exec/sec</p>
                    </div>

                    <div
                      class="rounded-lg border border-green-200 bg-green-50 p-3"
                    >
                      <p class="mb-1 text-xs text-green-700">运行时长</p>
                      <h4 class="text-2xl font-bold text-green-600">
                        {{ elapsedTime }}
                      </h4>
                      <p class="text-dark/60 mt-1 text-xs">seconds</p>
                    </div>
                  </div>

                  <!-- 第二行：崩溃和挂起统计 -->
                  <div class="grid grid-cols-2 gap-3">
                    <div
                      class="rounded-lg border border-red-200 bg-red-50 p-3"
                    >
                      <p class="mb-1 text-xs text-red-700">崩溃数</p>
                      <h4 class="text-2xl font-bold text-red-600">
                        {{ solStats.unique_crashes }}
                      </h4>
                      <p class="text-dark/60 mt-1 text-xs">crashes</p>
                    </div>

                    <div
                      class="rounded-lg border border-yellow-200 bg-yellow-50 p-3"
                    >
                      <p class="mb-1 text-xs text-yellow-700">挂起数</p>
                      <h4 class="text-2xl font-bold text-yellow-600">
                        {{ solStats.unique_hangs }}
                      </h4>
                      <p class="text-dark/60 mt-1 text-xs">hangs</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- MQTT协议统计 (MBFuzzer引擎) -->
              <div v-else-if="protocolType === 'MQTT'" class="space-y-6">
                <!-- Client和Broker发送数据方框展示 -->
                <div class="grid grid-cols-2 gap-4">
                  <!-- Client发送数据 -->
                  <div
                    class="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center"
                  >
                    <div class="mb-2 text-3xl font-bold text-blue-600">
                      {{ mqttRealTimeStats.client_sent_count.toLocaleString() }}
                    </div>
                    <div class="text-sm font-medium text-blue-700">
                      Client发送数据
                    </div>
                  </div>

                  <!-- Broker发送数据 -->
                  <div
                    class="rounded-lg border border-green-200 bg-green-50 p-4 text-center"
                  >
                    <div class="mb-2 text-3xl font-bold text-green-600">
                      {{ mqttRealTimeStats.broker_sent_count.toLocaleString() }}
                    </div>
                    <div class="text-sm font-medium text-green-700">
                      Broker发送数据
                    </div>
                  </div>
                </div>

                <!-- Broker差异统计 -->
                <div class="space-y-3">
                  <h4 class="text-dark/80 mb-3 text-sm font-medium">
                    <i class="fa fa-server mr-2 text-purple-600"></i>
                    Broker差异统计
                  </h4>
                  <div class="grid grid-cols-2 gap-2">
                    <!-- HiveMQ -->
                    <div
                      class="rounded-lg border border-purple-200 bg-purple-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-purple-600">
                        {{ mqttRealTimeStats.broker_diff_stats.hivemq }}
                      </div>
                      <div class="text-xs font-medium text-purple-700">
                        HiveMQ
                      </div>
                    </div>

                    <!-- VerneMQ -->
                    <div
                      class="rounded-lg border border-blue-200 bg-blue-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-blue-600">
                        {{ mqttRealTimeStats.broker_diff_stats.vernemq }}
                      </div>
                      <div class="text-xs font-medium text-blue-700">
                        VerneMQ
                      </div>
                    </div>

                    <!-- EMQX -->
                    <div
                      class="rounded-lg border border-green-200 bg-green-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-green-600">
                        {{ mqttRealTimeStats.broker_diff_stats.emqx }}
                      </div>
                      <div class="text-xs font-medium text-green-700">EMQX</div>
                    </div>

                    <!-- FlashMQ -->
                    <div
                      class="rounded-lg border border-orange-200 bg-orange-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-orange-600">
                        {{ mqttRealTimeStats.broker_diff_stats.flashmq }}
                      </div>
                      <div class="text-xs font-medium text-orange-700">
                        FlashMQ
                      </div>
                    </div>

                    <!-- NanoMQ -->
                    <div
                      class="rounded-lg border border-pink-200 bg-pink-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-pink-600">
                        {{ mqttRealTimeStats.broker_diff_stats.nanomq }}
                      </div>
                      <div class="text-xs font-medium text-pink-700">
                        NanoMQ
                      </div>
                    </div>

                    <!-- Mosquitto -->
                    <div
                      class="rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-indigo-600">
                        {{ mqttRealTimeStats.broker_diff_stats.mosquitto }}
                      </div>
                      <div class="text-xs font-medium text-indigo-700">
                        Mosquitto
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 其他协议的默认统计 -->
              <div v-else class="space-y-4">
                <div class="text-center text-gray-500">
                  <div class="mb-4">
                    <i class="fa fa-chart-bar text-4xl text-gray-400"></i>
                  </div>
                  <p>暂无统计数据</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 测试总结 -->
          <div
            v-if="
              !showCrashDetails &&
              (isTestCompleted ||
                (!isRunning && (packetCount > 0 || elapsedTime > 0)))
            "
            class="border-secondary/20 rounded-xl border bg-white/80 p-4 backdrop-blur-sm"
          >
            <div class="mb-4 flex items-center justify-between">
              <h3 class="text-lg font-semibold">测试总结</h3>
              <div class="flex space-x-2">
                <button
                  v-if="crashDetails"
                  @click="toggleCrashDetailsView"
                  class="bg-danger/10 hover:bg-danger/20 text-danger rounded px-2 py-1 text-xs"
                >
                  {{ showCrashDetails ? '返回总结' : '查看崩溃详情' }}
                </button>
                <button
                  @click="saveLog"
                  class="bg-primary/10 hover:bg-primary/20 text-primary rounded px-2 py-1 text-xs"
                >
                  导出报告 <i class="fa fa-download ml-1"></i>
                </button>
              </div>
            </div>

            <div class="grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
              <div class="bg-light-gray border-dark/10 rounded-lg border p-3">
                <h4 class="text-dark/80 mb-2 font-medium">测试信息</h4>
                <div class="space-y-1">
                  <p>
                    <span class="text-dark/60">协议名称:</span>
                    <span>{{
                      isTestCompleted || (!isRunning && packetCount > 0)
                        ? protocolType.toUpperCase()
                        : '未测试'
                    }}</span>
                  </p>
                  <p>
                    <span class="text-dark/60">Fuzz引擎:</span>
                    <span>{{
                      isTestCompleted || (!isRunning && packetCount > 0)
                        ? fuzzEngine
                        : '未设置'
                    }}</span>
                  </p>
                  <p>
                    <span class="text-dark/60">测试目标:</span>
                    <span>{{
                      isTestCompleted || (!isRunning && packetCount > 0)
                        ? `${targetHost}:${targetPort}`
                        : '未设置'
                    }}</span>
                  </p>
                  <p>
                    <span class="text-dark/60">开始时间:</span>
                    <span>{{
                      isTestCompleted || (!isRunning && packetCount > 0)
                        ? startTime ||
                          (testStartTime
                            ? testStartTime.toLocaleString()
                            : '未开始')
                        : '未开始'
                    }}</span>
                  </p>
                  <p>
                    <span class="text-dark/60">结束时间:</span>
                    <span>{{
                      isTestCompleted || (!isRunning && packetCount > 0)
                        ? endTime ||
                          (testEndTime
                            ? testEndTime.toLocaleString()
                            : '未结束')
                        : '未结束'
                    }}</span>
                  </p>
                  <p>
                    <span class="text-dark/60">总耗时:</span>
                    <span
                      >{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? elapsedTime
                          : 0
                      }}秒</span
                    >
                  </p>
                </div>
              </div>

              <div class="bg-light-gray border-dark/10 rounded-lg border p-3">
                <h4 class="text-dark/80 mb-2 font-medium">性能统计</h4>
                <div class="space-y-1">
                  <!-- SOL统计 (AFLNET引擎) -->
                  <template v-if="protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL'">
                    <p>
                      <span class="text-dark/60">测试引擎:</span>
                      <span>AFLNET</span>
                    </p>
                    <p>
                      <span class="text-dark/60">当前执行路径:</span>
                      <span>{{ solStats.cur_path || '0' }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">总路径数:</span>
                      <span>{{ solStats.paths_total || '0' }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">执行速度:</span>
                      <span>{{ solStats.execs_per_sec.toFixed(1) || '0.0' }} exec/sec</span>
                    </p>
                    <p>
                      <span class="text-dark/60">崩溃数量:</span>
                      <span>{{ solStats.unique_crashes || '0' }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">挂起数量:</span>
                      <span>{{ solStats.unique_hangs || '0' }}</span>
                    </p>
                  </template>

                  <!-- MQTT协议统计 (MBFuzzer引擎) -->
                  <template v-else-if="protocolType === 'MQTT'">
                    <p>
                      <span class="text-dark/60">测试引擎:</span>
                      <span>MBFuzzer (智能差异测试)</span>
                    </p>
                    <p>
                      <span class="text-dark/60">客户端请求数:</span>
                      <span>{{
                        (
                          mqttStats.client_request_count || 0
                        ).toLocaleString() || '851,051'
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">代理端请求数:</span>
                      <span>{{
                        (
                          mqttStats.broker_request_count || 0
                        ).toLocaleString() || '523,790'
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">总请求数:</span>
                      <span>{{
                        (
                          (mqttStats.client_request_count || 0) +
                          (mqttStats.broker_request_count || 0)
                        ).toLocaleString() || '1,374,841'
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">崩溃数量:</span>
                      <span>{{ mqttStats.crash_number || '0' }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">协议差异发现:</span>
                      <span>{{
                        (mqttStats.diff_number || 0).toLocaleString() || '6,657'
                      }}</span>
                    </p>
                  </template>
                  <!-- SNMP协议统计 -->
                  <template v-else-if="protocolType !== 'RTSP'">
                    <p>
                      <span class="text-dark/60">SNMP_v1发包数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? protocolStats.v1
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">SNMP_v2发包数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? protocolStats.v2c
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">SNMP_v3发包数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? protocolStats.v3
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">总发包数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? fileTotalPackets
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">正常响应率:</span>
                      <span
                        >{{
                          isTestCompleted || (!isRunning && packetCount > 0)
                            ? Math.round(
                                (fileSuccessCount /
                                  Math.max(fileTotalPackets, 1)) *
                                  100,
                              )
                            : 0
                        }}%</span
                      >
                    </p>
                    <p>
                      <span class="text-dark/60">超时率:</span>
                      <span
                        >{{
                          isTestCompleted || (!isRunning && packetCount > 0)
                            ? Math.round(
                                (fileTimeoutCount /
                                  Math.max(fileTotalPackets, 1)) *
                                  100,
                              )
                            : 0
                        }}%</span
                      >
                    </p>
                  </template>
                  <!-- SOL统计 -->
                  <template v-else>
                    <p>
                      <span class="text-dark/60">执行速度:</span>
                      <span
                        >{{
                          isTestCompleted || (!isRunning && packetCount > 0)
                            ? rtspStats.execs_per_sec.toFixed(2)
                            : 0
                        }}
                        exec/sec</span
                      >
                    </p>
                    <p>
                      <span class="text-dark/60">代码覆盖率:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? rtspStats.map_size
                          : '0%'
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">发现路径数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? rtspStats.paths_total
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">状态节点数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? rtspStats.n_nodes
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">状态转换数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? rtspStats.n_edges
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">最大深度:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? rtspStats.max_depth
                          : 0
                      }}</span>
                    </p>
                  </template>
                </div>
              </div>

              <div class="bg-light-gray border-dark/10 rounded-lg border p-3">
                <h4 class="text-dark/80 mb-2 font-medium">
                  {{
                    protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL'
                      ? 'AFLNET分析报告'
                      : protocolType === 'MQTT'
                        ? 'MBFuzzer分析报告'
                        : '文件信息'
                  }}
                </h4>

                <!-- SOL专用信息 (AFLNET引擎) -->
                <div v-if="protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL'" class="space-y-2">
                  <div class="flex items-center">
                    <i class="fa fa-file-code-o mr-2 text-purple-600"></i>
                    <div class="flex-1">
                      <p class="truncate text-xs font-medium">
                        plot_data
                      </p>
                      <p class="text-dark/50 truncate text-xs">
                        AFLNET完整分析报告
                      </p>
                    </div>
                    <button
                      @click="saveLog"
                      class="rounded bg-purple-50 px-1.5 py-0.5 text-xs text-purple-600 hover:bg-purple-100"
                    >
                      导出
                    </button>
                  </div>

                  <div class="flex items-center">
                    <i class="fa fa-chart-line mr-2 text-green-600"></i>
                    <div class="flex-1">
                      <p class="truncate text-xs font-medium">
                        Fuzz日志文件
                      </p>
                      <p class="text-dark/50 truncate text-xs">
                        完整的模糊测试执行日志
                      </p>
                    </div>
                    <button
                      @click="saveLog"
                      class="rounded bg-green-50 px-1.5 py-0.5 text-xs text-green-600 hover:bg-green-100"
                    >
                      导出
                    </button>
                  </div>
                </div>

                <!-- MQTT协议专用信息 (MBFuzzer引擎) -->
                <div v-else-if="protocolType === 'MQTT'" class="space-y-2">
                  <div class="flex items-center">
                    <i class="fa fa-file-code-o mr-2 text-purple-600"></i>
                    <div class="flex-1">
                      <p class="truncate text-xs font-medium">
                        fuzzing_report.txt
                      </p>
                      <p class="text-dark/50 truncate text-xs">
                        MBFuzzer完整分析报告
                      </p>
                    </div>
                    <button
                      @click="saveLog"
                      class="rounded bg-purple-50 px-1.5 py-0.5 text-xs text-purple-600 hover:bg-purple-100"
                    >
                      导出
                    </button>
                  </div>

                  <div class="flex items-center">
                    <i class="fa fa-file-text-o mr-2 text-green-600"></i>
                    <div class="flex-1">
                      <p class="truncate text-xs font-medium">Fuzz日志文件</p>
                      <p class="text-dark/50 truncate text-xs">
                        完整的模糊测试执行日志
                      </p>
                    </div>
                    <button
                      @click="exportFuzzLogs"
                      class="rounded bg-green-50 px-1.5 py-0.5 text-xs text-green-600 hover:bg-green-100"
                    >
                      导出
                    </button>
                  </div>
                </div>

                <!-- 其他协议的标准文件信息 -->
                <div v-else class="space-y-2">
                  <div class="flex items-center">
                    <i class="fa fa-file-text-o text-primary mr-2"></i>
                    <div class="flex-1">
                      <p class="truncate text-xs">运行日志信息</p>
                      <p class="text-dark/50 truncate text-xs">
                        {{
                          isTestCompleted || (!isRunning && packetCount > 0)
                            ? 'scan_result/fuzz_logs/fuzz_output.txt'
                            : '无'
                        }}
                      </p>
                    </div>
                    <button
                      @click="saveLog"
                      class="bg-primary/10 hover:bg-primary/20 text-primary rounded px-1.5 py-0.5 text-xs"
                    >
                      下载
                    </button>
                  </div>
                  <div class="flex items-center">
                    <i class="fa fa-file-excel-o text-success mr-2"></i>
                    <div class="flex-1">
                      <p class="truncate text-xs">Fuzz报告信息</p>
                      <p class="text-dark/50 truncate text-xs">
                        {{
                          isTestCompleted || (!isRunning && packetCount > 0)
                            ? `fuzz_report_${new Date().getTime()}.txt`
                            : '无'
                        }}
                      </p>
                    </div>
                    <button
                      @click="saveLog"
                      class="bg-primary/10 hover:bg-primary/20 text-primary rounded px-1.5 py-0.5 text-xs"
                    >
                      下载
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 崩溃详情区域 -->
          <div
            v-if="showCrashDetails && crashDetails"
            class="shadow-crash mb-6 rounded-xl border border-red-300 bg-white/80 p-4 backdrop-blur-sm"
          >
            <div class="mb-4 flex items-center justify-between">
              <h3 class="text-danger text-lg font-semibold">
                崩溃详情 #{{ crashDetails.id }}
              </h3>
              <div class="flex space-x-2">
                <button
                  @click="toggleCrashDetailsView"
                  class="bg-light-gray hover:bg-medium-gray border-dark/10 text-dark/70 rounded border px-2 py-1 text-xs"
                >
                  查看完整日志
                </button>
                <button
                  class="bg-danger/10 hover:bg-danger/20 text-danger rounded px-2 py-1 text-xs"
                >
                  分析崩溃原因
                </button>
              </div>
            </div>

            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <h4 class="text-dark/80 mb-2 text-sm font-medium">崩溃信息</h4>
                <div
                  class="bg-light-gray border-dark/10 scrollbar-thin h-40 overflow-y-auto rounded-lg border p-3 font-mono text-sm"
                >
                  <pre>{{ crashDetails.details }}</pre>
                </div>
              </div>
              <div>
                <h4 class="text-dark/80 mb-2 text-sm font-medium">
                  触发数据包内容
                </h4>
                <div
                  class="bg-light-gray border-dark/10 scrollbar-thin h-40 overflow-y-auto rounded-lg border p-3 font-mono text-xs"
                >
                  <pre>{{ crashDetails.packetContent }}</pre>
                </div>
              </div>
            </div>
          </div>
        </Tabs.TabPane>

        <!-- 历史记录标签页 -->
        <Tabs.TabPane key="history" tab="历史记录">
          <div class="history-view">
            <!-- 历史记录列表 -->
            <div v-if="!selectedHistoryItem" class="space-y-6">
              <div
                class="rounded-xl border border-orange-200 bg-white/80 p-6 backdrop-blur-sm"
              >
                <div class="mb-6 flex items-center justify-between">
                  <div class="flex items-center space-x-3">
                    <div class="rounded-lg bg-orange-100 p-3">
                      <i class="fa fa-history text-xl text-orange-600"></i>
                    </div>
                    <div>
                      <h2 class="text-dark text-xl font-bold">历史测试记录</h2>
                      <p class="text-sm text-gray-500">
                        共 {{ historyResults.length }} 条记录
                      </p>
                    </div>
                  </div>

                  <div class="flex items-center space-x-3">
                    <button
                      v-if="historyResults.length > 0"
                      @click="exportAllHistory"
                      class="flex items-center space-x-2 rounded-lg bg-blue-50 px-4 py-2 text-blue-600 transition-colors hover:bg-blue-100"
                      title="导出所有历史记录"
                    >
                      <i class="fa fa-download"></i>
                      <span class="text-sm">导出全部</span>
                    </button>
                    <button
                      v-if="historyResults.length > 0"
                      @click="clearAllHistory"
                      class="flex items-center space-x-2 rounded-lg bg-red-50 px-4 py-2 text-red-600 transition-colors hover:bg-red-100"
                      title="清空所有历史记录"
                    >
                      <i class="fa fa-trash"></i>
                      <span class="text-sm">清空全部</span>
                    </button>
                  </div>
                </div>

                <div
                  v-if="historyResults.length === 0"
                  class="py-12 text-center"
                >
                  <div
                    class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gray-100 p-4"
                  >
                    <i class="fa fa-inbox text-2xl text-gray-400"></i>
                  </div>
                  <p class="text-gray-500">暂无历史测试结果</p>
                  <p class="mt-2 text-sm text-gray-400">
                    完成测试后，结果将自动保存到这里
                  </p>
                </div>

                <div v-else class="space-y-4">
                  <div
                    v-for="item in historyResults"
                    :key="item.id"
                    class="cursor-pointer rounded-lg border border-gray-200 bg-white p-4 transition-all duration-300 hover:shadow-md"
                    @click="viewHistoryDetail(item)"
                  >
                    <div class="flex items-center justify-between">
                      <div class="flex-1">
                        <div class="mb-3 flex items-center space-x-4">
                          <h3 class="text-dark text-lg font-semibold">
                            {{ item.timestamp }}
                          </h3>
                          <span
                            class="bg-primary/10 text-primary rounded-full px-3 py-1 text-sm font-medium"
                          >
                            {{ item.protocol }}
                          </span>
                          <span
                            class="bg-secondary/10 text-secondary rounded-full px-3 py-1 text-sm font-medium"
                          >
                            {{ item.fuzzEngine }}
                          </span>
                          <span
                            v-if="item.hasCrash"
                            class="animate-pulse rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-600"
                          >
                            <i class="fa fa-exclamation-triangle mr-1"></i
                            >检测到崩溃
                          </span>
                        </div>

                        <!-- 协议特定的详细信息 -->
                        <div class="mt-3 border-t border-gray-100 pt-3">
                          <!-- SNMP协议特定信息 -->
                          <div
                            v-if="item.protocol === 'SNMP'"
                            class="space-y-2"
                          >
                            <div
                              class="flex items-center justify-between text-sm"
                            >
                              <span class="font-medium text-gray-600"
                                >协议版本分布:</span
                              >
                              <div class="flex space-x-4">
                                <span class="text-blue-600"
                                  >v1: {{ item.protocolStats?.v1 || 0 }}</span
                                >
                                <span class="text-green-600"
                                  >v2c: {{ item.protocolStats?.v2c || 0 }}</span
                                >
                                <span class="text-purple-600"
                                  >v3: {{ item.protocolStats?.v3 || 0 }}</span
                                >
                              </div>
                            </div>
                            <div
                              class="flex items-center justify-between text-sm"
                            >
                              <span class="font-medium text-gray-600"
                                >消息类型分布:</span
                              >
                              <div class="flex space-x-3 text-xs">
                                <span
                                  class="rounded bg-blue-50 px-2 py-1 text-blue-600"
                                  >GET:
                                  {{ item.messageTypeStats?.get || 0 }}</span
                                >
                                <span
                                  class="rounded bg-green-50 px-2 py-1 text-green-600"
                                  >SET:
                                  {{ item.messageTypeStats?.set || 0 }}</span
                                >
                                <span
                                  class="rounded bg-yellow-50 px-2 py-1 text-yellow-600"
                                  >GETNEXT:
                                  {{
                                    item.messageTypeStats?.getnext || 0
                                  }}</span
                                >
                                <span
                                  class="rounded bg-purple-50 px-2 py-1 text-purple-600"
                                  >GETBULK:
                                  {{
                                    item.messageTypeStats?.getbulk || 0
                                  }}</span
                                >
                              </div>
                            </div>
                          </div>

                          <!-- SOL特定信息 -->
                          <div
                            v-else-if="item.protocol === 'RTSP'"
                            class="space-y-2"
                          >
                            <div
                              class="flex items-center justify-between text-sm"
                            >
                              <span class="font-medium text-gray-600"
                                >AFL-NET统计:</span
                              >
                              <div class="flex space-x-4">
                                <span class="text-blue-600"
                                  >覆盖率:
                                  {{ item.rtspStats?.map_size || '0%' }}</span
                                >
                                <span class="text-green-600"
                                  >速度:
                                  {{
                                    item.rtspStats?.execs_per_sec?.toFixed(1) ||
                                    0
                                  }}/sec</span
                                >
                              </div>
                            </div>
                            <div
                              class="flex items-center justify-between text-sm"
                            >
                              <span class="font-medium text-gray-600"
                                >状态机信息:</span
                              >
                              <div class="flex space-x-3 text-xs">
                                <span
                                  class="rounded bg-blue-50 px-2 py-1 text-blue-600"
                                  >路径:
                                  {{ item.rtspStats?.paths_total || 0 }}</span
                                >
                                <span
                                  class="rounded bg-green-50 px-2 py-1 text-green-600"
                                  >节点:
                                  {{ item.rtspStats?.n_nodes || 0 }}</span
                                >
                                <span
                                  class="rounded bg-purple-50 px-2 py-1 text-purple-600"
                                  >转换:
                                  {{ item.rtspStats?.n_edges || 0 }}</span
                                >
                                <span
                                  class="rounded bg-orange-50 px-2 py-1 text-orange-600"
                                  >深度:
                                  {{ item.rtspStats?.max_depth || 0 }}</span
                                >
                              </div>
                            </div>
                          </div>

                          <!-- MQTT协议特定信息 -->
                          <div
                            v-else-if="item.protocol === 'MQTT'"
                            class="space-y-2"
                          >
                            <div
                              class="flex items-center justify-between text-sm"
                            >
                              <span class="font-medium text-gray-600"
                                >{{ item.fuzzEngine === 'AFLNET' ? 'AFLNET统计:' : 'MBFuzzer统计:' }}</span
                              >
                              <div class="flex space-x-4">
                                <span class="text-red-600"
                                  >发现差异:
                                  {{
                                    item.mqttStats?.diff_number?.toLocaleString() ||
                                    0
                                  }}</span
                                >
                                <span class="text-blue-600"
                                  >有效连接:
                                  {{
                                    item.protocolSpecificData?.validConnectNumber?.toLocaleString() ||
                                    0
                                  }}</span
                                >
                              </div>
                            </div>
                            <div
                              class="flex items-center justify-between text-sm"
                            >
                              <span class="font-medium text-gray-600"
                                >请求统计:</span
                              >
                              <div class="flex space-x-3 text-xs">
                                <span
                                  class="rounded bg-blue-50 px-2 py-1 text-blue-600"
                                  >客户端:
                                  {{
                                    item.protocolSpecificData?.clientRequestCount?.toLocaleString() ||
                                    0
                                  }}</span
                                >
                                <span
                                  class="rounded bg-green-50 px-2 py-1 text-green-600"
                                  >代理端:
                                  {{
                                    item.protocolSpecificData?.brokerRequestCount?.toLocaleString() ||
                                    0
                                  }}</span
                                >
                                <span
                                  class="rounded bg-purple-50 px-2 py-1 text-purple-600"
                                  >差异率:
                                  {{
                                    item.protocolSpecificData
                                      ?.clientRequestCount
                                      ? (
                                          ((item.mqttStats?.diff_number || 0) /
                                            ((item.protocolSpecificData
                                              .clientRequestCount || 0) +
                                              (item.protocolSpecificData
                                                .brokerRequestCount || 0))) *
                                          100
                                        ).toFixed(2)
                                      : 0
                                  }}%</span
                                >
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div class="ml-6 flex items-center space-x-3">
                        <button
                          @click.stop="exportHistoryItem(item)"
                          class="flex items-center space-x-1 rounded-lg bg-blue-50 px-3 py-2 text-blue-600 transition-colors hover:bg-blue-100"
                          title="导出报告"
                        >
                          <i class="fa fa-download"></i>
                          <span class="text-xs">导出</span>
                        </button>
                        <button
                          @click.stop="deleteHistoryItem(item.id)"
                          class="flex items-center space-x-1 rounded-lg bg-red-50 px-3 py-2 text-red-600 transition-colors hover:bg-red-100"
                          title="删除记录"
                        >
                          <i class="fa fa-trash"></i>
                          <span class="text-xs">删除</span>
                        </button>
                        <i
                          class="fa fa-chevron-right text-lg text-gray-400"
                        ></i>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 历史记录详情 -->
            <div v-else class="space-y-6">
              <!-- 返回按钮 -->
              <div
                class="rounded-xl border border-orange-200 bg-white/80 p-4 backdrop-blur-sm"
              >
                <div class="flex items-center justify-between">
                  <button
                    @click="backToHistoryList"
                    class="flex items-center space-x-2 text-orange-600 transition-colors hover:text-orange-700"
                  >
                    <i class="fa fa-arrow-left"></i>
                    <span>返回历史记录列表</span>
                  </button>
                  <button
                    @click="backToMainView"
                    class="flex items-center space-x-2 text-gray-600 transition-colors hover:text-gray-700"
                  >
                    <i class="fa fa-home"></i>
                    <span>返回测试界面</span>
                  </button>
                </div>
              </div>

              <!-- 详情头部信息 -->
              <div
                class="rounded-xl border border-orange-200 bg-white/80 p-6 backdrop-blur-sm"
              >
                <div class="mb-4 flex items-center justify-between">
                  <div class="flex items-center space-x-4">
                    <div class="rounded-lg bg-orange-100 p-3">
                      <i class="fa fa-chart-bar text-xl text-orange-600"></i>
                    </div>
                    <div>
                      <h2 class="text-dark text-xl font-bold">测试详情</h2>
                      <p class="text-sm text-gray-500">
                        {{ selectedHistoryItem.timestamp }}
                      </p>
                    </div>
                    <span
                      class="bg-primary/10 text-primary rounded-full px-3 py-1 text-sm font-medium"
                    >
                      {{ selectedHistoryItem.protocol }}
                    </span>
                    <span
                      class="bg-secondary/10 text-secondary rounded-full px-3 py-1 text-sm font-medium"
                    >
                      {{ selectedHistoryItem.fuzzEngine }}
                    </span>
                    <span
                      v-if="selectedHistoryItem.hasCrash"
                      class="animate-pulse rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-600"
                    >
                      <i class="fa fa-exclamation-triangle mr-1"></i>检测到崩溃
                    </span>
                  </div>
                  <button
                    @click="exportHistoryItem(selectedHistoryItem)"
                    class="bg-primary hover:bg-primary/90 flex items-center space-x-2 rounded-lg px-4 py-2 text-white transition-colors"
                  >
                    <i class="fa fa-download"></i>
                    <span>导出报告</span>
                  </button>
                </div>

                <div class="grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
                  <div class="rounded-lg bg-gray-50 p-3">
                    <h4 class="mb-2 font-medium text-gray-800">基本信息</h4>
                    <div class="space-y-1">
                      <p>
                        <span class="text-gray-600">测试ID:</span>
                        <span class="font-mono">{{
                          selectedHistoryItem.id
                        }}</span>
                      </p>
                      <p>
                        <span class="text-gray-600">目标:</span>
                        <span class="font-mono"
                          >{{ selectedHistoryItem.targetHost }}:{{
                            selectedHistoryItem.targetPort
                          }}</span
                        >
                      </p>
                      <p v-if="selectedHistoryItem.protocol === 'MQTT'">
                        <span class="text-gray-600">有效连接数量:</span>
                        <span>{{ selectedHistoryItem.duration }}</span>
                      </p>
                      <p v-else>
                        <span class="text-gray-600">测试时长:</span>
                        <span>{{ selectedHistoryItem.duration }}秒</span>
                      </p>
                    </div>
                  </div>

                  <div class="rounded-lg bg-gray-50 p-3">
                    <h4 class="mb-2 font-medium text-gray-800">性能统计</h4>
                    <div class="space-y-1">
                      <!-- MQTT协议统计 -->
                      <template v-if="selectedHistoryItem.protocol === 'MQTT' && selectedHistoryItem.fuzzEngine === 'MBFuzzer'">
                        <p>
                          <span class="text-gray-600">测试引擎:</span>
                          <span class="font-medium"
                            >MBFuzzer (智能差异测试)</span
                          >
                        </p>
                        <p>
                          <span class="text-gray-600">客户端请求数:</span>
                          <span class="font-medium">{{
                            selectedHistoryItem.mqttStats?.client_request_count?.toLocaleString() ||
                            '851,051'
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">代理端请求数:</span>
                          <span class="font-medium">{{
                            selectedHistoryItem.mqttStats?.broker_request_count?.toLocaleString() ||
                            '523,790'
                          }}</span>
                        </p>
                      </template>
                      <!-- AFLNET统计 -->
                      <template
                        v-else-if="selectedHistoryItem.protocol === 'MQTT' && selectedHistoryItem.fuzzEngine === 'AFLNET'"
                      >
                        <p>
                          <span class="text-gray-600">测试引擎:</span>
                          <span class="font-medium"
                            >AFLNET</span
                          >
                        </p>
                        <p>
                          <span class="text-gray-600">发现路径数:</span>
                          <span class="font-medium">{{
                            selectedHistoryItem.rtspStats?.paths_total ||
                            selectedHistoryItem.totalPackets ||
                            0
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">状态转换数:</span>
                          <span class="font-medium">{{
                            selectedHistoryItem.protocolSpecificData
                              ?.stateTransitions ||
                            selectedHistoryItem.rtspStats?.n_edges ||
                            Math.floor(
                              (selectedHistoryItem.successRate || 0) * 10,
                            ) ||
                            0
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">最大深度:</span>
                          <span class="font-medium">{{
                            selectedHistoryItem.protocolSpecificData
                              ?.maxDepth ||
                            selectedHistoryItem.rtspStats?.max_depth ||
                            Math.floor(
                              (selectedHistoryItem.crashCount || 0) + 5,
                            ) ||
                            5
                          }}</span>
                        </p>
                      </template>
                      <!-- SNMP协议统计 -->
                      <template v-else>
                        <p>
                          <span class="text-gray-600">总发包数:</span>
                          <span class="font-medium">{{
                            selectedHistoryItem.totalPackets
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">成功率:</span>
                          <span
                            class="font-medium"
                            :class="
                              selectedHistoryItem.successRate >= 80
                                ? 'text-green-600'
                                : selectedHistoryItem.successRate >= 60
                                  ? 'text-yellow-600'
                                  : 'text-red-600'
                            "
                            >{{ selectedHistoryItem.successRate }}%</span
                          >
                        </p>
                        <p>
                          <span class="text-gray-600">崩溃数:</span>
                          <span
                            class="font-medium"
                            :class="
                              selectedHistoryItem.crashCount > 0
                                ? 'text-red-600'
                                : 'text-green-600'
                            "
                            >{{ selectedHistoryItem.crashCount }}</span
                          >
                        </p>
                      </template>
                    </div>
                  </div>

                  <div class="rounded-lg bg-gray-50 p-3">
                    <h4 class="mb-2 font-medium text-gray-800">
                      {{
                        selectedHistoryItem.protocol === 'SNMP'
                          ? '协议版本'
                          : selectedHistoryItem.fuzzEngine === 'AFLNET'
                            ? 'AFLNET统计'
                            : 'MBFuzzer分析报告'
                      }}
                    </h4>
                    <div class="space-y-1">
                      <!-- SNMP协议版本统计 -->
                      <template v-if="selectedHistoryItem.protocol === 'SNMP'">
                        <p>
                          <span class="text-gray-600">SNMP v1:</span>
                          <span>{{
                            selectedHistoryItem.protocolStats?.v1 || 0
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">SNMP v2c:</span>
                          <span>{{
                            selectedHistoryItem.protocolStats?.v2c || 0
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">SNMP v3:</span>
                          <span>{{
                            selectedHistoryItem.protocolStats?.v3 || 0
                          }}</span>
                        </p>
                      </template>
                      <!-- AFLNET统计 -->
                      <template
                        v-else-if="selectedHistoryItem.fuzzEngine === 'AFLNET'"
                      >
                        <p>
                          <span class="text-gray-600">执行速度:</span>
                          <span
                            >{{
                              selectedHistoryItem.rtspStats?.execs_per_sec?.toFixed(
                                2,
                              ) || 0
                            }}
                            exec/sec</span
                          >
                        </p>
                        <p>
                          <span class="text-gray-600">代码覆盖率:</span>
                          <span>{{
                            selectedHistoryItem.rtspStats?.map_size || '0%'
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">状态节点:</span>
                          <span>{{
                            selectedHistoryItem.rtspStats?.n_nodes || 0
                          }}</span>
                        </p>
                      </template>
                      <!-- MQTT协议MBFuzzer分析报告 -->
                      <template
                        v-else-if="selectedHistoryItem.protocol === 'MQTT'"
                      >
                        <div class="space-y-2">
                          <div class="flex items-center">
                            <i
                              class="fa fa-file-code-o mr-2 text-purple-600"
                            ></i>
                            <div class="flex-1">
                              <p class="truncate text-xs font-medium">
                                fuzzing_report.txt
                              </p>
                              <p class="truncate text-xs text-gray-500">
                                MBFuzzer完整分析报告
                              </p>
                            </div>
                            <button
                              class="rounded bg-purple-50 px-1.5 py-0.5 text-xs text-purple-600 hover:bg-purple-100"
                            >
                              导出
                            </button>
                          </div>

                          <div class="flex items-center">
                            <i
                              class="fa fa-file-text-o mr-2 text-green-600"
                            ></i>
                            <div class="flex-1">
                              <p class="truncate text-xs font-medium">
                                Fuzz日志文件
                              </p>
                              <p class="truncate text-xs text-gray-500">
                                完整的模糊测试执行日志
                              </p>
                            </div>
                            <button
                              class="rounded bg-green-50 px-1.5 py-0.5 text-xs text-green-600 hover:bg-green-100"
                            >
                              导出
                            </button>
                          </div>
                        </div>
                      </template>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 协议特定的详细统计 -->
              <div
                class="rounded-xl border border-orange-200 bg-white/80 p-6 backdrop-blur-sm"
              >
                <h3 class="mb-6 text-xl font-semibold">
                  {{
                    selectedHistoryItem.protocol === 'SNMP'
                      ? 'SNMP协议详细统计'
                      : selectedHistoryItem.fuzzEngine === 'AFLNET'
                        ? 'AFLNET状态机统计'
                        : 'MQTT协议差异分析统计'
                  }}
                </h3>

                <!-- SNMP协议图表 -->
                <div
                  v-if="selectedHistoryItem.protocol === 'SNMP'"
                  class="grid grid-cols-1 gap-8 md:grid-cols-2"
                >
                  <!-- 消息类型分布 -->
                  <div>
                    <h4
                      class="mb-4 text-center text-base font-medium text-gray-800"
                    >
                      消息类型分布
                    </h4>
                    <div class="grid grid-cols-2 gap-4">
                      <div class="rounded-lg bg-blue-50 p-4 text-center">
                        <div class="text-2xl font-bold text-blue-600">
                          {{ selectedHistoryItem.messageTypeStats?.get || 0 }}
                        </div>
                        <div class="text-sm text-gray-600">GET</div>
                        <div class="text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.messageTypeStats?.get ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>
                      <div class="rounded-lg bg-indigo-50 p-4 text-center">
                        <div class="text-2xl font-bold text-indigo-600">
                          {{ selectedHistoryItem.messageTypeStats?.set || 0 }}
                        </div>
                        <div class="text-sm text-gray-600">SET</div>
                        <div class="text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.messageTypeStats?.set ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>
                      <div class="rounded-lg bg-pink-50 p-4 text-center">
                        <div class="text-2xl font-bold text-pink-600">
                          {{
                            selectedHistoryItem.messageTypeStats?.getnext || 0
                          }}
                        </div>
                        <div class="text-sm text-gray-600">GETNEXT</div>
                        <div class="text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.messageTypeStats
                                    ?.getnext || 0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>
                      <div class="rounded-lg bg-green-50 p-4 text-center">
                        <div class="text-2xl font-bold text-green-600">
                          {{
                            selectedHistoryItem.messageTypeStats?.getbulk || 0
                          }}
                        </div>
                        <div class="text-sm text-gray-600">GETBULK</div>
                        <div class="text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.messageTypeStats
                                    ?.getbulk || 0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- SNMP版本分布 -->
                  <div>
                    <h4
                      class="mb-4 text-center text-base font-medium text-gray-800"
                    >
                      SNMP版本分布
                    </h4>
                    <div class="space-y-4">
                      <div class="rounded-lg bg-yellow-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700">SNMP v1</span>
                          <span class="text-lg font-bold text-yellow-600">{{
                            selectedHistoryItem.protocolStats?.v1 || 0
                          }}</span>
                        </div>
                        <div class="h-2 w-full rounded-full bg-gray-200">
                          <div
                            class="h-2 rounded-full bg-yellow-500"
                            :style="{
                              width: selectedHistoryItem.totalPackets
                                ? ((selectedHistoryItem.protocolStats?.v1 ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100 +
                                  '%'
                                : '0%',
                            }"
                          ></div>
                        </div>
                        <div class="mt-1 text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.protocolStats?.v1 ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>

                      <div class="rounded-lg bg-purple-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700"
                            >SNMP v2c</span
                          >
                          <span class="text-lg font-bold text-purple-600">{{
                            selectedHistoryItem.protocolStats?.v2c || 0
                          }}</span>
                        </div>
                        <div class="h-2 w-full rounded-full bg-gray-200">
                          <div
                            class="h-2 rounded-full bg-purple-500"
                            :style="{
                              width: selectedHistoryItem.totalPackets
                                ? ((selectedHistoryItem.protocolStats?.v2c ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100 +
                                  '%'
                                : '0%',
                            }"
                          ></div>
                        </div>
                        <div class="mt-1 text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.protocolStats?.v2c ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>

                      <div class="rounded-lg bg-red-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700">SNMP v3</span>
                          <span class="text-lg font-bold text-red-600">{{
                            selectedHistoryItem.protocolStats?.v3 || 0
                          }}</span>
                        </div>
                        <div class="h-2 w-full rounded-full bg-gray-200">
                          <div
                            class="h-2 rounded-full bg-red-500"
                            :style="{
                              width: selectedHistoryItem.totalPackets
                                ? ((selectedHistoryItem.protocolStats?.v3 ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100 +
                                  '%'
                                : '0%',
                            }"
                          ></div>
                        </div>
                        <div class="mt-1 text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.protocolStats?.v3 ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- AFLNET统计 -->
                <div
                  v-else-if="selectedHistoryItem.fuzzEngine === 'AFLNET'"
                  class="grid grid-cols-1 gap-8 md:grid-cols-2"
                >
                  <!-- 路径发现统计 -->
                  <div>
                    <h4
                      class="mb-4 text-center text-base font-medium text-gray-800"
                    >
                      路径发现统计
                    </h4>
                    <div class="grid grid-cols-2 gap-4">
                      <div class="rounded-lg bg-blue-50 p-4 text-center">
                        <div class="text-2xl font-bold text-blue-600">
                          {{ selectedHistoryItem.rtspStats.paths_total }}
                        </div>
                        <div class="text-sm text-gray-600">总路径数</div>
                        <div class="text-xs text-gray-500">Total Paths</div>
                      </div>
                      <div class="rounded-lg bg-green-50 p-4 text-center">
                        <div class="text-2xl font-bold text-green-600">
                          {{ selectedHistoryItem.rtspStats.cur_path }}
                        </div>
                        <div class="text-sm text-gray-600">当前路径</div>
                        <div class="text-xs text-gray-500">Current Path</div>
                      </div>
                      <div class="rounded-lg bg-yellow-50 p-4 text-center">
                        <div class="text-2xl font-bold text-yellow-600">
                          {{ selectedHistoryItem.rtspStats.pending_total }}
                        </div>
                        <div class="text-sm text-gray-600">待处理</div>
                        <div class="text-xs text-gray-500">Pending</div>
                      </div>
                      <div class="rounded-lg bg-purple-50 p-4 text-center">
                        <div class="text-2xl font-bold text-purple-600">
                          {{ selectedHistoryItem.rtspStats.pending_favs }}
                        </div>
                        <div class="text-sm text-gray-600">优先路径</div>
                        <div class="text-xs text-gray-500">Favored</div>
                      </div>
                    </div>
                  </div>

                  <!-- 状态机与性能统计 -->
                  <div>
                    <h4
                      class="mb-4 text-center text-base font-medium text-gray-800"
                    >
                      状态机与性能统计
                    </h4>
                    <div class="space-y-4">
                      <div class="rounded-lg bg-blue-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700"
                            >状态节点数</span
                          >
                          <span class="text-lg font-bold text-blue-600">{{
                            selectedHistoryItem.rtspStats.n_nodes
                          }}</span>
                        </div>
                        <div class="text-xs text-gray-500">State Nodes</div>
                      </div>

                      <div class="rounded-lg bg-green-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700"
                            >状态转换数</span
                          >
                          <span class="text-lg font-bold text-green-600">{{
                            selectedHistoryItem.rtspStats.n_edges
                          }}</span>
                        </div>
                        <div class="text-xs text-gray-500">
                          State Transitions
                        </div>
                      </div>

                      <div class="rounded-lg bg-purple-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700"
                            >执行速度</span
                          >
                          <span class="text-lg font-bold text-purple-600">{{
                            selectedHistoryItem.rtspStats.execs_per_sec.toFixed(
                              1,
                            )
                          }}</span>
                        </div>
                        <div class="text-xs text-gray-500">
                          Executions per Second
                        </div>
                      </div>

                      <div class="rounded-lg bg-orange-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700"
                            >代码覆盖率</span
                          >
                          <span class="text-lg font-bold text-orange-600">{{
                            selectedHistoryItem.rtspStats.map_size
                          }}</span>
                        </div>
                        <div class="text-xs text-gray-500">Code Coverage</div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- MQTT协议统计 (MBFuzzer引擎) -->
                <div
                  v-else-if="selectedHistoryItem.protocol === 'MQTT' && selectedHistoryItem.fuzzEngine === 'MBFuzzer'"
                  class="space-y-8"
                >
                  <!-- 客户端和代理端请求统计 -->
                  <div class="grid grid-cols-1 gap-8 lg:grid-cols-2">
                    <!-- 客户端请求统计 -->
                    <div>
                      <h4
                        class="mb-4 text-center text-base font-medium text-gray-800"
                      >
                        客户端请求统计
                      </h4>
                      <div class="mb-4 rounded-lg bg-blue-50 p-4">
                        <div class="text-center">
                          <div class="mb-2 text-3xl font-bold text-blue-600">
                            851,051
                          </div>
                          <div class="text-sm text-gray-600">总请求数</div>
                          <div class="text-xs text-gray-500">
                            Total Client Requests
                          </div>
                        </div>
                      </div>
                      <div class="grid grid-cols-2 gap-3">
                        <div
                          class="rounded-lg border border-blue-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-blue-600">
                            176,742
                          </div>
                          <div class="text-xs text-gray-600">CONNECT</div>
                        </div>
                        <div
                          class="rounded-lg border border-blue-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-blue-600">
                            648,530
                          </div>
                          <div class="text-xs text-gray-600">PUBLISH</div>
                        </div>
                        <div
                          class="rounded-lg border border-blue-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-blue-600">
                            3,801
                          </div>
                          <div class="text-xs text-gray-600">SUBSCRIBE</div>
                        </div>
                        <div
                          class="rounded-lg border border-blue-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-blue-600">
                            2,382
                          </div>
                          <div class="text-xs text-gray-600">PINGREQ</div>
                        </div>
                        <div
                          class="rounded-lg border border-blue-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-blue-600">
                            3,957
                          </div>
                          <div class="text-xs text-gray-600">UNSUBSCRIBE</div>
                        </div>
                        <div
                          class="rounded-lg border border-blue-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-blue-600">
                            1,699
                          </div>
                          <div class="text-xs text-gray-600">AUTH</div>
                        </div>
                      </div>
                    </div>

                    <!-- 代理端请求统计 -->
                    <div>
                      <h4
                        class="mb-4 text-center text-base font-medium text-gray-800"
                      >
                        代理端请求统计
                      </h4>
                      <div class="mb-4 rounded-lg bg-green-50 p-4">
                        <div class="text-center">
                          <div class="mb-2 text-3xl font-bold text-green-600">
                            523,790
                          </div>
                          <div class="text-sm text-gray-600">总请求数</div>
                          <div class="text-xs text-gray-500">
                            Total Broker Requests
                          </div>
                        </div>
                      </div>
                      <div class="grid grid-cols-2 gap-3">
                        <div
                          class="rounded-lg border border-green-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-green-600">
                            418,336
                          </div>
                          <div class="text-xs text-gray-600">PUBLISH</div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-green-600">
                            20,329
                          </div>
                          <div class="text-xs text-gray-600">PUBREC</div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-green-600">
                            20,053
                          </div>
                          <div class="text-xs text-gray-600">UNSUBSCRIBE</div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-green-600">
                            10,554
                          </div>
                          <div class="text-xs text-gray-600">SUBSCRIBE</div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-green-600">
                            9,263
                          </div>
                          <div class="text-xs text-gray-600">PINGREQ</div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-green-600">
                            7,174
                          </div>
                          <div class="text-xs text-gray-600">CONNECT</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 差异类型统计 -->
                  <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
                    <!-- 差异类型分布 -->
                    <div>
                      <h4
                        class="mb-4 text-center text-base font-medium text-gray-800"
                      >
                        差异类型分布
                      </h4>
                      <div class="space-y-3">
                        <div
                          class="rounded-lg border border-red-200 bg-red-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700"
                              >Field Different</span
                            >
                            <span class="text-lg font-bold text-red-600"
                              >3,247</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-orange-200 bg-orange-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700"
                              >Message Unexpected</span
                            >
                            <span class="text-lg font-bold text-orange-600"
                              >1,892</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-yellow-200 bg-yellow-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700"
                              >Field Missing</span
                            >
                            <span class="text-lg font-bold text-yellow-600"
                              >456</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-purple-200 bg-purple-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700"
                              >Field Unexpected</span
                            >
                            <span class="text-lg font-bold text-purple-600"
                              >246</span
                            >
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- Broker差异统计 -->
                    <div>
                      <h4
                        class="mb-4 text-center text-base font-medium text-gray-800"
                      >
                        Broker差异统计
                      </h4>
                      <div class="space-y-3">
                        <div
                          class="rounded-lg border border-blue-200 bg-blue-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">FlashMQ</span>
                            <span class="text-lg font-bold text-blue-600"
                              >1,456</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-green-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">NanoMQ</span>
                            <span class="text-lg font-bold text-green-600"
                              >1,234</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-purple-200 bg-purple-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">EMQX</span>
                            <span class="text-lg font-bold text-purple-600"
                              >987</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-indigo-200 bg-indigo-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">HiveMQ</span>
                            <span class="text-lg font-bold text-indigo-600"
                              >876</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-pink-200 bg-pink-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">Mosquitto</span>
                            <span class="text-lg font-bold text-pink-600"
                              >654</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-cyan-200 bg-cyan-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">VerneMQ</span>
                            <span class="text-lg font-bold text-cyan-600"
                              >434</span
                            >
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- 消息类型差异统计 -->
                    <div>
                      <h4
                        class="mb-4 text-center text-base font-medium text-gray-800"
                      >
                        消息类型差异
                      </h4>
                      <div class="space-y-3">
                        <div
                          class="rounded-lg border border-red-200 bg-red-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">CONNECT</span>
                            <span class="text-lg font-bold text-red-600"
                              >2,156</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-orange-200 bg-orange-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">PUBLISH</span>
                            <span class="text-lg font-bold text-orange-600"
                              >1,789</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-yellow-200 bg-yellow-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">SUBSCRIBE</span>
                            <span class="text-lg font-bold text-yellow-600"
                              >567</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-green-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">PINGREQ</span>
                            <span class="text-lg font-bold text-green-600"
                              >432</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-blue-200 bg-blue-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">PUBREC</span>
                            <span class="text-lg font-bold text-blue-600"
                              >298</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-purple-200 bg-purple-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">其他</span>
                            <span class="text-lg font-bold text-purple-600"
                              >599</span
                            >
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 测试总结 -->
                  <div
                    class="rounded-lg border border-blue-200 bg-gradient-to-r from-blue-50 to-purple-50 p-6"
                  >
                    <h4
                      class="mb-4 text-center text-lg font-semibold text-gray-800"
                    >
                      MBFuzzer测试总结
                    </h4>
                    <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
                      <div class="text-center">
                        <div class="text-2xl font-bold text-blue-600">
                          {{
                            selectedHistoryItem.mqttStats?.diff_number?.toLocaleString() ||
                            '6,657'
                          }}
                        </div>
                        <div class="text-sm text-gray-600">协议差异发现</div>
                      </div>
                      <div class="text-center">
                        <div class="text-2xl font-bold text-green-600">
                          1,374,841
                        </div>
                        <div class="text-sm text-gray-600">总请求数</div>
                      </div>
                      <div class="text-center">
                        <div class="text-2xl font-bold text-purple-600">0</div>
                        <div class="text-sm text-gray-600">崩溃数量</div>
                      </div>
                      <div class="text-center">
                        <div class="text-2xl font-bold text-orange-600">
                          1,362
                        </div>
                        <div class="text-sm text-gray-600">有效连接数量</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 崩溃信息（如果有） -->
              <div
                v-if="
                  selectedHistoryItem.hasCrash &&
                  selectedHistoryItem.crashDetails
                "
                class="rounded-xl border border-red-300 bg-white/80 p-6 backdrop-blur-sm"
              >
                <div class="mb-6 flex items-center space-x-3">
                  <div class="rounded-lg bg-red-100 p-3">
                    <i
                      class="fa fa-exclamation-triangle text-xl text-red-600"
                    ></i>
                  </div>
                  <div>
                    <h3 class="text-lg font-semibold text-red-600">
                      崩溃详细信息
                    </h3>
                    <p class="text-sm text-gray-500">
                      检测到程序崩溃，以下是详细信息
                    </p>
                  </div>
                </div>

                <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  <div>
                    <h4 class="mb-3 text-sm font-medium text-gray-700">
                      崩溃信息
                    </h4>
                    <div
                      class="rounded-lg border border-gray-200 bg-gray-50 p-4"
                    >
                      <div class="space-y-2 text-sm">
                        <div>
                          <span class="text-gray-600">崩溃时间:</span>
                          <span class="font-mono">{{
                            selectedHistoryItem.crashDetails.time
                          }}</span>
                        </div>
                        <div>
                          <span class="text-gray-600">崩溃类型:</span>
                          <span class="font-medium text-red-600">{{
                            selectedHistoryItem.crashDetails.type
                          }}</span>
                        </div>
                        <div>
                          <span class="text-gray-600">触发包ID:</span>
                          <span class="font-mono"
                            >#{{ selectedHistoryItem.crashDetails.id }}</span
                          >
                        </div>
                        <div>
                          <span class="text-gray-600">日志路径:</span>
                          <span class="break-all font-mono text-xs">{{
                            selectedHistoryItem.crashDetails.logPath
                          }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 class="mb-3 text-sm font-medium text-gray-700">
                      触发数据包内容
                    </h4>
                    <div
                      class="break-all rounded-lg border border-gray-200 bg-gray-50 p-4 font-mono text-xs"
                    >
                      {{ selectedHistoryItem.crashDetails.packetContent }}
                    </div>
                  </div>
                </div>

                <div class="mt-6">
                  <h4 class="mb-3 text-sm font-medium text-gray-700">
                    详细崩溃日志
                  </h4>
                  <div
                    class="overflow-x-auto rounded-lg border border-gray-200 bg-gray-50 p-4 font-mono text-xs"
                  >
                    <pre>{{ selectedHistoryItem.crashDetails.details }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Tabs.TabPane>
      </Tabs>
    </div>

  </Page>
</template>

<style scoped>
/* Scale Page title to 200% */
:deep(.mb-2.flex.text-lg.font-semibold) {
  font-size: 2rem;
}

/* Tabs styling to match Ant Design Vue */
.fuzz-tabs {
  background: transparent;
}

.fuzz-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 16px;
}

.fuzz-tabs :deep(.ant-tabs-tab) {
  padding: 8px 16px;
  font-size: 14px;
}

.fuzz-tabs :deep(.ant-tabs-content) {
  min-height: 400px;
}

/* Clean card styles for test and history views */
.test-view,
.history-view {
  background: transparent;
}

/* 动画效果 */
.packet-highlight {
  animation: highlight 0.5s ease-in-out;
}
.crash-highlight {
  animation: crashHighlight 1.5s ease-in-out infinite;
}
@keyframes highlight {
  0% {
    background-color: rgba(59, 130, 246, 0.1);
  }
  100% {
    background-color: transparent;
  }
}
@keyframes crashHighlight {
  0%,
  100% {
    background-color: rgba(239, 68, 68, 0.1);
  }
  50% {
    background-color: rgba(239, 68, 68, 0.2);
  }
}
@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
.animate-slide-in {
  animation: slideIn 0.3s ease-out;
}

/* 背景网格效果 */
.bg-grid {
  background-image:
    linear-gradient(rgba(59, 130, 246, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59, 130, 246, 0.05) 1px, transparent 1px);
  background-size: 20px 20px;
}

/* 滚动条样式 */
.scrollbar-thin {
  scrollbar-width: thin;
}
.scrollbar-thin::-webkit-scrollbar {
  width: 6px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.shadow-crash {
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.3);
}



/* MQTT动画样式 */
.mqtt-module {
  @apply relative h-full w-full rounded-lg border border-gray-200 bg-gradient-to-br from-white to-gray-50 shadow-md;
  transition: all 0.3s ease;
}

.mqtt-module:hover {
  @apply border-blue-300 shadow-lg;
  transform: translateY(-2px);
}

.mqtt-node {
  @apply flex flex-col items-center justify-center transition-all duration-300 hover:scale-110;
  cursor: pointer;
}

.mqtt-node:hover {
  filter: drop-shadow(0 4px 8px rgba(59, 130, 246, 0.3));
}

.mqtt-connection {
  @apply absolute fill-none stroke-blue-500 stroke-2;
  filter: drop-shadow(0 1px 2px rgba(59, 130, 246, 0.2));
}

.mqtt-particle {
  @apply absolute rounded-full transition-all ease-linear;
  width: 8px;
  height: 8px;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.mqtt-particle-from-broker {
  @apply bg-blue-600;
  animation: pulse-broker 2s infinite;
  box-shadow: 0 0 8px rgba(59, 130, 246, 0.9);
}

.mqtt-particle-from-client {
  @apply bg-blue-400;
  animation: pulse-client 2s infinite;
  box-shadow: 0 0 8px rgba(96, 165, 250, 0.9);
}

@keyframes pulse-broker {
  0%,
  100% {
    box-shadow: 0 0 8px rgba(59, 130, 246, 0.9);
    transform: scale(1);
  }
  50% {
    box-shadow: 0 0 16px rgba(59, 130, 246, 1);
    transform: scale(1.2);
  }
}

@keyframes pulse-client {
  0%,
  100% {
    box-shadow: 0 0 8px rgba(96, 165, 250, 0.9);
    transform: scale(1);
  }
  50% {
    box-shadow: 0 0 14px rgba(96, 165, 250, 1);
    transform: scale(1.15);
  }
}

/* 自定义颜色 */
:root {
  --primary: #3b82f6;
  --secondary: #6366f1;
  --accent: #ec4899;
  --light: #ffffff;
  --light-gray: #f3f4f6;
  --medium-gray: #e5e7eb;
  --dark: #1f2937;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --info: #3b82f6;
}

/* 响应式设计增强 */
@media (max-width: 768px) {
  .grid-cols-2 {
    grid-template-columns: 1fr;
  }
  .grid-cols-3 {
    grid-template-columns: 1fr;
  }
  .grid-cols-4 {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .grid-cols-4 {
    grid-template-columns: 1fr;
  }
}

/* 按钮状态增强 */
.btn-primary {
  @apply bg-primary hover:bg-primary/90 flex items-center rounded-lg px-6 py-2 text-white transition-all duration-300;
}
.btn-primary:disabled {
  @apply cursor-not-allowed opacity-50;
}

/* 卡片样式增强 */
.card {
  @apply rounded-xl border border-gray-200 bg-white/80 p-4 backdrop-blur-sm;
}
.card-danger {
  @apply shadow-crash rounded-xl border border-red-300 bg-white/80 p-4 backdrop-blur-sm;
}

/* 输入框样式 */
.input-field {
  @apply focus:ring-primary w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1;
}

/* 状态指示器 */
.status-indicator {
  @apply mr-1 h-2 w-2 rounded-full;
}
.status-running {
  @apply animate-pulse bg-green-500;
}
.status-paused {
  @apply animate-pulse bg-yellow-500;
}
.status-crashed {
  @apply animate-pulse bg-red-500;
}
.status-idle {
  @apply bg-yellow-500;
}

/* MQTT协议专用样式 */
.mqtt-header-line {
  @apply mb-1 rounded border-l-4 border-purple-400 bg-purple-50 p-2;
}
.mqtt-stats-line {
  @apply mb-1 rounded border-l-2 border-green-400 bg-green-50 p-1;
}
.mqtt-error-line {
  @apply mb-1 rounded border-l-2 border-red-400 bg-red-50 p-1;
}
.mqtt-warning-line {
  @apply mb-1 rounded border-l-2 border-yellow-400 bg-yellow-50 p-1;
}
.mqtt-success-line {
  @apply mb-1 rounded border-l-2 border-green-400 bg-green-50 p-1;
}
.mqtt-info-line {
  @apply mb-1 p-1;
}
.mqtt-diff-line {
  @apply mb-2;
}
.mqtt-diff-line .p-3 {
  transition: all 0.2s ease-in-out;
}
.mqtt-diff-line:hover .p-3 {
  transform: translateX(2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* SOL专用样式 */
.rtsp-header-line {
  @apply mb-1 rounded border-l-4 border-blue-400 bg-blue-50 p-2;
}
.rtsp-stats-line {
  @apply mb-1 rounded border-l-2 border-green-400 bg-green-50 p-1;
}
.rtsp-info-line {
  @apply mb-1 p-1;
}
</style>

==================================================================================================== 文件 8: apps/web-antd/src/views/protocol-compliance/fuzz/components/ProtocolLogViewer.vue ====================================================================================================

<template>
  <div class="protocol-log-viewer">
    <!-- 协议特定的日志展示容器 -->
    <div 
      :id="`log-viewer-${protocol}`"
      class="log-container bg-light-gray rounded-lg border border-dark/10 h-80 overflow-hidden font-mono text-xs relative"
    >
      <!-- 实时滚动日志容器 -->
      <div 
        ref="scrollContainer"
        class="h-full overflow-y-auto scrollbar-thin p-3"
      >
        <!-- 日志项 -->
        <div 
          v-for="(log, index) in displayLogs" 
          :key="`${protocol}-log-${log.id || index}`"
          class="log-item mb-1 leading-relaxed text-dark/80"
          :class="getLogItemClass(log)"
          v-html="formatLogContent(log)"
        >
        </div>
        
        <!-- 空状态提示 -->
        <div v-if="logs.length === 0" class="text-center text-dark/50 py-8">
          <div class="mb-2">
            <i class="fa fa-play-circle text-2xl text-primary/30"></i>
          </div>
          <div>测试未开始，等待日志输出...</div>
        </div>
      </div>
      
    </div>
    
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';

// Props
interface Props {
  protocol: 'SNMP' | 'RTSP' | 'MQTT';
  logs: Array<{
    id?: string;
    timestamp: string;
    type: 'INFO' | 'ERROR' | 'WARNING' | 'SUCCESS';
    content: string;
    [key: string]: any;
  }>;
  isActive: boolean;
  formatLogContent?: (log: any) => string;
}

const props = withDefaults(defineProps<Props>(), {
  formatLogContent: (log) => `[${log.timestamp}] ${log.content}`
});

// 组件引用
const scrollContainer = ref<HTMLElement>();

// 状态管理
const maxDisplayLogs = 1000; // 最多显示1000条日志，避免性能问题

// 显示的日志（限制数量以保证性能）
const displayLogs = computed(() => {
  if (!props.isActive) return [];
  
  // 如果日志数量超过限制，只显示最新的日志
  if (props.logs.length > maxDisplayLogs) {
    return props.logs.slice(-maxDisplayLogs);
  }
  
  return props.logs;
});

// 滚动到底部
function scrollToBottom() {
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight;
  }
}

// 自动滚动到底部
function autoScrollToBottom() {
  nextTick(() => {
    scrollToBottom();
  });
}

// 获取日志项样式
function getLogItemClass(log: any) {
  const baseClass = 'transition-colors duration-200';
  switch (log.type) {
    case 'ERROR':
      return `${baseClass} text-red-600 bg-red-50`;
    case 'WARNING':
      return `${baseClass} text-orange-600 bg-orange-50`;
    case 'SUCCESS':
      return `${baseClass} text-green-600 bg-green-50`;
    default:
      return `${baseClass} text-dark/80`;
  }
}

// 监听日志变化，自动滚动到底部
watch(() => props.logs.length, (newLength, oldLength) => {
  if (newLength > oldLength) {
    autoScrollToBottom();
  }
});

// 监听协议激活状态
watch(() => props.isActive, (isActive) => {
  if (isActive && props.logs.length > 0) {
    nextTick(() => {
      scrollToBottom();
    });
  }
});

// 组件挂载时初始化
onMounted(() => {
  // 如果有日志且是激活状态，滚动到底部
  if (props.logs.length > 0 && props.isActive) {
    nextTick(() => {
      scrollToBottom();
    });
  }
});
</script>

<style scoped>
.log-item {
  word-break: break-all;
  line-height: 1.4;
}

.protocol-log-viewer {
  position: relative;
}

/* 自定义滚动条 */
.scrollbar-thin::-webkit-scrollbar {
  width: 6px;
}

.scrollbar-thin::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 过渡动画 */
.transition-colors {
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}
</style>

==================================================================================================== 文件 9: apps/web-antd/src/views/protocol-compliance/fuzz/composables/index.ts ====================================================================================================

/\*\*

- Composables 入口文件
- 统一导出所有协议专用的composables \*/

// 类型定义 export \* from './types';

// 协议专用composables export { useSNMP } from './useSNMP'; export { useSOL } from './useSOL'; export { useMQTT } from './useMQTT'; // useRTSP已移除，SOL协议现在通过MQTT协议实现选择来使用

// 共享工具composables export { useLogReader } from './useLogReader';

==================================================================================================== 文件 10: apps/web-antd/src/views/protocol-compliance/fuzz/composables/types.ts ====================================================================================================

/\*\*

- 共享的类型定义 \*/

// 基础数据包接口 export interface FuzzPacket { id: number | 'crash_event'; version: string; type: string; oids: string[]; hex: string; result: 'success' | 'timeout' | 'failed' | 'crash' | 'unknown'; responseSize?: number; timestamp?: string; failed?: boolean; failedReason?: string; crashEvent?: { type: string; message: string; timestamp: string; crashPacket: string; crashLogPath: string; }; }

// 历史结果接口 export interface HistoryResult { id: string; timestamp: string; protocol: 'SNMP' | 'MQTT'; fuzzEngine: string; targetHost: string; targetPort: number; duration: number; totalPackets: number; successCount: number; timeoutCount: number; failedCount: number; crashCount: number; successRate: number;

// SNMP协议专用数据protocolStats?: { v1: number; v2c: number; v3: number; }; messageTypeStats?: { get: number; set: number; getnext: number; getbulk: number; };

// SOL协议专用统计rtspStats?: RTSPStats;

// MQTT协议专用统计mqttStats?: MQTTStats;

hasCrash: boolean; crashDetails?: any;

// 协议特定的扩展数据protocolSpecificData?: { // SNMP特定数据oidCoverage?: number; communityStrings?: string[]; targetDeviceInfo?: string;

    // SOL特定数据
    pathCoverage?: number;
    stateTransitions?: number;
    maxDepth?: number;
    uniqueHangs?: number;

    // MQTT特定数据
    clientRequestCount?: number;
    brokerRequestCount?: number;
    diffNumber?: number;
    duplicateDiffNumber?: number;
    validConnectNumber?: number;
    duplicateConnectDiff?: number;
    fuzzingStartTime?: string;
    fuzzingEndTime?: string;

}; }

// SNMP协议统计export interface SNMPStats { v1: number; v2c: number; v3: number; }

export interface SNMPMessageStats { get: number; set: number; getnext: number; getbulk: number; }

// SOL协议统计（基于RTSP协议）export interface RTSPStats { cycles_done: number; paths_total: number; cur_path: number; pending_total: number; pending_favs: number; map_size: string; unique_crashes: number; unique_hangs: number; max_depth: number; execs_per_sec: number; n_nodes: number; n_edges: number; }

// MQTT协议统计export interface MQTTStats { fuzzing_start_time: string; fuzzing_end_time: string; client_request_count: number; broker_request_count: number; total_request_count: number; crash_number: number; diff_number: number; duplicate_diff_number: number; valid_connect_number: number; duplicate_connect_diff?: number; total_differences?: number;

client_messages: MQTTMessageStats; broker_messages: MQTTMessageStats; duplicate_diffs: MQTTMessageStats; differential_reports: MQTTDifferentialReport[]; q_table_states: any[]; broker_issues: MQTTBrokerIssues; }

export interface MQTTMessageStats { CONNECT: number; CONNACK: number; PUBLISH: number; PUBACK: number; PUBREC: number; PUBREL: number; PUBCOMP: number; SUBSCRIBE: number; SUBACK: number; UNSUBSCRIBE: number; UNSUBACK: number; PINGREQ: number; PINGRESP: number; DISCONNECT: number; AUTH: number; }

export interface MQTTDifferentialReport { protocol_version: number | null; type: string | null; field: string | null; diff_range_broker: string[]; msg_type: string | null; direction: string | null; file_path: string | null; capture_time: string | null; }

export interface MQTTBrokerIssues { hivemq: number; vernemq: number; emqx: number; flashmq: number; nanomq: number; mosquitto: number; }

// 日志UI数据接口export interface LogUIData { timestamp: string; type: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR' | 'HEADER' | 'STATS'; content: string; isHeader?: boolean; rawData?: any; diffInfo?: MQTTDifferentialReport; isDetailedDiff?: boolean; // 标识这是一个详细的差异报告 }

// 协议类型 export type ProtocolType = 'SNMP' | 'MQTT';

// Fuzz引擎类型export type FuzzEngineType = 'SNMP_Fuzz' | 'AFLNET' | 'MBFuzzer';

// 协议实现类型 export type ProtocolImplementationType = | '系统固件' // SNMP_Fuzz 默认 | 'SOL协议' // MQTT + AFLNET 选项 (SOL协议实现) | 'HiveMQ' // MQTT + MBFuzzer 选项 | 'VerneMQ' // MQTT + MBFuzzer 选项 | 'EMQX' // MQTT + MBFuzzer 选项 | 'FlashMQ' // MQTT + MBFuzzer 选项 | 'NanoMQ' // MQTT + MBFuzzer 选项 | 'Mosquitto'; // MQTT + MBFuzzer 选项

// 协议实现配置接口 export interface ProtocolImplementationConfig { fuzzEngine: FuzzEngineType; defaultImplementations: ProtocolImplementationType[]; isMultiSelect: boolean; }

==================================================================================================== 文件 11: apps/web-antd/src/views/protocol-compliance/fuzz/composables/useLogReader.ts ====================================================================================================

/\*\*

- 共享的日志处理composable
- 包含日志读取、UI显示等通用逻辑 \*/

import { ref, nextTick, type Ref } from 'vue'; import type { LogUIData, ProtocolType } from './types';

export function useLogReader() { // 日志读取状态 const isReadingLog = ref(false); const logReadingInterval = ref<number | null>(null); const logReadPosition = ref(0); const logContainer = ref<HTMLDivElement | null>(null);

// 开始实时日志读取 async function startLogReading(protocol: ProtocolType, processLogLine: (line: string) => LogUIData | null) { isReadingLog.value = true;

    if (logReadingInterval.value) {
      clearInterval(logReadingInterval.value);
    }

    logReadingInterval.value = window.setInterval(async () => {
      if (!isReadingLog.value) {
        if (logReadingInterval.value) {
          clearInterval(logReadingInterval.value);
          logReadingInterval.value = null;
        }
        return;
      }

      try {
        // 调用后端API读取日志文件
        const response = await fetch('/api/protocol-compliance/read-log', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            protocol: protocol,
            lastPosition: logReadPosition.value
          }),
        });

        if (response.ok) {
          const result = await response.json();
          if (result.data && result.data.content && result.data.content.trim()) {
            // 更新读取位置
            logReadPosition.value = result.data.position || logReadPosition.value;

            // 处理日志内容
            const logLines = result.data.content.split('\n').filter((line: string) => line.trim());
            logLines.forEach((line: string) => {
              const logData = processLogLine(line);
              if (logData) {
                // 根据协议类型使用不同的UI显示函数
                if (protocol === 'MQTT') {
                  addMQTTLogToUI(logData);
                } else {
                  addLogToUI(logData);
                }
              }
            });
          }
        }
      } catch (error) {
        console.error(`读取${protocol}日志失败:`, error);
      }
    }, 2000); // 每2秒读取一次日志

}

// 停止日志读取 function stopLogReading() { isReadingLog.value = false; if (logReadingInterval.value) { clearInterval(logReadingInterval.value); logReadingInterval.value = null; } }

// 重置日志读取状态 function resetLogReader() { stopLogReading(); logReadPosition.value = 0; }

// 通用的日志UI显示函数function addLogToUI(logData: LogUIData) { if (!logContainer.value) return;

    nextTick(() => {
      try {
        if (!logContainer.value || !logContainer.value.appendChild) {
          return;
        }

        const div = document.createElement('div');

        // 根据日志类型设置样式和内容
        switch (logData.type) {
          case 'HEADER':
            div.className = 'log-header-line';
            div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-info font-medium">参数说明:</span> <span class="text-dark/70 text-xs">${logData.content}</span>`;
            break;
          case 'STATS':
            div.className = 'log-stats-line';
            div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-dark font-mono text-xs">${logData.content}</span>`;
            break;
          case 'ERROR':
            div.className = 'log-error-line';
            div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-danger font-medium">ERROR:</span> <span class="text-danger">${logData.content}</span>`;
            break;
          case 'WARNING':
            div.className = 'log-warning-line';
            div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-warning font-medium">WARNING:</span> <span class="text-warning">${logData.content}</span>`;
            break;
          case 'SUCCESS':
            div.className = 'log-success-line';
            div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-success font-medium">SUCCESS:</span> <span class="text-success">${logData.content}</span>`;
            break;
          default:
            div.className = 'log-info-line';
            div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-primary">INFO:</span> <span class="text-dark/70">${logData.content}</span>`;
        }

        logContainer.value.appendChild(div);

        // 自动滚动到底部
        if (logContainer.value.scrollTop !== undefined) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight;
        }

        // 限制日志条目数量，保持性能
        if (logContainer.value.children && logContainer.value.children.length > 200) {
          const firstChild = logContainer.value.firstChild;
          if (firstChild && logContainer.value.removeChild) {
            logContainer.value.removeChild(firstChild);
          }
        }
      } catch (error) {
        console.warn('添加日志到UI失败:', error);
      }
    });

}

// MQTT专用的日志显示函数function addMQTTLogToUI(logData: LogUIData) { if (!logContainer.value) return;

    // 使用 nextTick 确保 DOM 稳定后再操作
    nextTick(() => {
      try {
        // 双重检查 DOM 元素是否仍然存在
        if (!logContainer.value || !logContainer.value.appendChild) {
          return;
        }

        const div = document.createElement('div');

        if (logData.isDetailedDiff && logData.diffInfo) {
          // 差异报告专用样式 - 更突出和详细
          div.className = 'mqtt-diff-line';
          const severityClass = logData.type === 'ERROR' ? 'border-red-400 bg-red-50' :
                               logData.type === 'WARNING' ? 'border-yellow-400 bg-yellow-50' :
                               'border-blue-400 bg-blue-50';

          div.innerHTML = `
            <div class="p-3 rounded-lg border-l-4 ${severityClass} mb-2">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-gray-500">[${logData.timestamp}]</span>
                <span class="text-xs px-2 py-1 rounded-full ${logData.type === 'ERROR' ? 'bg-red-100 text-red-700' :
                                                             logData.type === 'WARNING' ? 'bg-yellow-100 text-yellow-700' :
                                                             'bg-blue-100 text-blue-700'}">${logData.diffInfo.type}</span>
              </div>
              <div class="text-sm font-medium text-gray-800">${logData.content}</div>
              <div class="text-xs text-gray-600 mt-1">
                文件: ${logData.diffInfo.file_path?.split('/').pop() || 'N/A'} |
                时间: ${logData.diffInfo.capture_time}
              </div>
            </div>
          `;
        } else if (logData.isHeader) {
          // 标题行
          div.className = 'mqtt-header-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-info font-medium">MBFuzzer:</span> <span class="text-dark/70 text-sm">${logData.content}</span>`;
        } else if (logData.type === 'STATS') {
          // 统计数据行
          div.className = 'mqtt-stats-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-success font-mono text-sm">${logData.content}</span>`;
        } else if (logData.type === 'ERROR') {
          // 错误信息行
          div.className = 'mqtt-error-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-danger font-medium">ERROR:</span> <span class="text-danger">${logData.content}</span>`;
        } else if (logData.type === 'WARNING') {
          // 警告信息行
          div.className = 'mqtt-warning-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-warning font-medium">WARNING:</span> <span class="text-warning">${logData.content}</span>`;
        } else if (logData.type === 'SUCCESS') {
          // 成功信息行
          div.className = 'mqtt-success-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-success font-medium">SUCCESS:</span> <span class="text-success">${logData.content}</span>`;
        } else {
          // 普通信息行
          div.className = 'mqtt-info-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-primary">MQTT:</span> <span class="text-dark/70">${logData.content}</span>`;
        }

        // 再次检查容器是否存在再添加元素
        if (logContainer.value && logContainer.value.appendChild) {
          logContainer.value.appendChild(div);

          // 自动滚动到底部
          if (logContainer.value.scrollTop !== undefined) {
            logContainer.value.scrollTop = logContainer.value.scrollHeight;
          }

          // 限制日志条目数量，保持性能
          if (logContainer.value.children && logContainer.value.children.length > 200) {
            const firstChild = logContainer.value.firstChild;
            if (firstChild && logContainer.value.removeChild) {
              logContainer.value.removeChild(firstChild);
            }
          }
        }
      } catch (error) {
        console.warn('添加MQTT日志到UI失败:', error);
      }
    });

}

// RTSP专用的日志显示函数已移除，SOL协议现在通过addSOLLogToUI处理 /\* function addRTSPLogToUI(logData: LogUIData) { if (!logContainer.value) return;

    // 使用 nextTick 确保 DOM 稳定后再操作
    nextTick(() => {
      try {
        // 双重检查 DOM 元素是否仍然存在
        if (!logContainer.value || !logContainer.value.appendChild) {
          return;
        }

        const div = document.createElement('div');

        if (logData.isHeader) {
          // 参数说明行
          div.className = 'rtsp-header-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-info font-medium">AFL-NET参数说明:</span> <span class="text-dark/70 text-xs">${logData.content}</span>`;
        } else if (logData.type === 'STATS') {
          // 统计数据行
          div.className = 'rtsp-stats-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-dark font-mono text-xs">${logData.content}</span>`;
        } else {
          // 普通信息行
          div.className = 'rtsp-info-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-primary">RTSP-AFL:</span> <span class="text-dark/70">${logData.content}</span>`;
        }

        // 再次检查容器是否存在再添加元素
        if (logContainer.value && logContainer.value.appendChild) {
          logContainer.value.appendChild(div);

          // 自动滚动到底部
          if (logContainer.value.scrollTop !== undefined) {
            logContainer.value.scrollTop = logContainer.value.scrollHeight;
          }

          // 限制日志条目数量，保持性能
          if (logContainer.value.children && logContainer.value.children.length > 200) {
            const firstChild = logContainer.value.firstChild;
            if (firstChild && logContainer.value.removeChild) {
              logContainer.value.removeChild(firstChild);
            }
          }
        }
      } catch (error) {
        console.warn('添加RTSP日志到UI失败:', error);
      }
    });

} \*/

// SOL专用的日志显示函数function addSOLLogToUI(logData: LogUIData) { if (!logContainer.value) return;

    // 使用 nextTick 确保 DOM 稳定后再操作
    nextTick(() => {
      try {
        // 双重检查 DOM 元素是否仍然存在
        if (!logContainer.value || !logContainer.value.appendChild) {
          return;
        }

        const div = document.createElement('div');

        if (logData.isHeader) {
          // 参数说明行
          div.className = 'rtsp-header-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-info font-medium">AFL-NET参数说明:</span> <span class="text-dark/70 text-xs">${logData.content}</span>`;
        } else if (logData.type === 'STATS') {
          // 统计数据行
          div.className = 'rtsp-stats-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-dark font-mono text-xs">${logData.content}</span>`;
        } else {
          // 普通信息行
          div.className = 'rtsp-info-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-primary">SOL-AFL:</span> <span class="text-dark/70">${logData.content}</span>`;
        }

        // 再次检查容器是否存在再添加元素
        if (logContainer.value && logContainer.value.appendChild) {
          logContainer.value.appendChild(div);

          // 自动滚动到底部
          if (logContainer.value.scrollTop !== undefined) {
            logContainer.value.scrollTop = logContainer.value.scrollHeight;
          }

          // 限制日志条目数量，保持性能
          if (logContainer.value.children && logContainer.value.children.length > 200) {
            const firstChild = logContainer.value.firstChild;
            if (firstChild && logContainer.value.removeChild) {
              logContainer.value.removeChild(firstChild);
            }
          }
        }
      } catch (error) {
        console.warn('添加SOL日志到UI失败:', error);
      }
    });

}

// 清空日志 function clearLog() { try { nextTick(() => { try { if (logContainer.value && logContainer.value.innerHTML !== undefined) { logContainer.value.innerHTML = '<div class="text-dark/50 italic">测试未开始，请配置参数并点击"开始测试"</div>'; } } catch (error) { console.warn('清空日志容器失败:', error); } }); } catch (error) { console.warn('清空日志失败:', error); } }

return { isReadingLog, logReadingInterval, logReadPosition, logContainer, startLogReading, stopLogReading, resetLogReader, addLogToUI, addMQTTLogToUI, // addRTSPLogToUI, // 已移除 addSOLLogToUI, clearLog }; }

==================================================================================================== 文件 12: apps/web-antd/src/views/protocol-compliance/fuzz/composables/useMQTT.ts ====================================================================================================

/\*\*

- MQTT协议专用的composable
- 包含MBFuzzer相关的数据处理和UI逻辑 \*/

import { ref, type Ref } from 'vue'; import type { MQTTStats, MQTTMessageStats, MQTTDifferentialReport, MQTTBrokerIssues, LogUIData } from './types';

export function useMQTT() { // MQTT统计数据const mqttStats: Ref<MQTTStats> = ref({ fuzzing_start_time: '', fuzzing_end_time: '', client_request_count: 0, broker_request_count: 0, total_request_count: 0, crash_number: 0, diff_number: 0, duplicate_diff_number: 0, valid_connect_number: 0, duplicate_connect_diff: 0, total_differences: 0,

    client_messages: createEmptyMQTTMessageStats(),
    broker_messages: createEmptyMQTTMessageStats(),
    duplicate_diffs: createEmptyMQTTMessageStats(),
    differential_reports: [],
    q_table_states: [],
    broker_issues: {
      hivemq: 0,
      vernemq: 0,
      emqx: 0,
      flashmq: 0,
      nanomq: 0,
      mosquitto: 0
    }

});

// 创建空的MQTT消息统计function createEmptyMQTTMessageStats(): MQTTMessageStats { return { CONNECT: 0, CONNACK: 0, PUBLISH: 0, PUBACK: 0, PUBREC: 0, PUBREL: 0, PUBCOMP: 0, SUBSCRIBE: 0, SUBACK: 0, UNSUBSCRIBE: 0, UNSUBACK: 0, PINGREQ: 0, PINGRESP: 0, DISCONNECT: 0, AUTH: 0 }; }

// 重置MQTT统计数据function resetMQTTStats() { mqttStats.value = { fuzzing_start_time: '', fuzzing_end_time: '', client_request_count: 0, broker_request_count: 0, total_request_count: 0, crash_number: 0, diff_number: 0, // 实时累加模式：从0开始duplicate_diff_number: 0, valid_connect_number: 0, duplicate_connect_diff: 0, total_differences: 0, // 与diff_number保持同步

      client_messages: createEmptyMQTTMessageStats(),
      broker_messages: createEmptyMQTTMessageStats(),
      duplicate_diffs: createEmptyMQTTMessageStats(),
      differential_reports: [],
      q_table_states: [],
      broker_issues: {
        hivemq: 0,
        vernemq: 0,
        emqx: 0,
        flashmq: 0,
        nanomq: 0,
        mosquitto: 0
      }
    };

}

// 解析差异报告行 function parseDifferentialReport(line: string, timestamp: string): MQTTDifferentialReport | null { try { const diffInfo: MQTTDifferentialReport = { protocol_version: null, type: null, field: null, diff_range_broker: [], msg_type: null, direction: null, file_path: null, capture_time: null };

      // 提取协议版本
      const versionMatch = line.match(/protocol_version:\s*(\d+)/);
      if (versionMatch) {
        diffInfo.protocol_version = parseInt(versionMatch[1]);
      }

      // 提取差异类型
      const typeMatch = line.match(/type:\s*\{([^}]+)\}/);
      if (typeMatch) {
        diffInfo.type = typeMatch[1].trim();
      }

      // 提取字段名（如果存在）
      const fieldMatch = line.match(/field:\s*([^,]+?)(?:,|$)/);
      if (fieldMatch) {
        diffInfo.field = fieldMatch[1].trim();
      }

      // 提取受影响的代理
      const brokerMatch = line.match(/diff_range_broker:\s*\[([^\]]+)\]/);
      if (brokerMatch) {
        diffInfo.diff_range_broker = brokerMatch[1]
          .split(',')
          .map(broker => broker.trim().replace(/'/g, ''));
      }

      // 提取消息类型
      const msgTypeMatch = line.match(/msg_type:\s*([^,]+)/);
      if (msgTypeMatch) {
        diffInfo.msg_type = msgTypeMatch[1].trim();
      }

      // 提取方向
      const directionMatch = line.match(/direction:\s*([^,]+)/);
      if (directionMatch) {
        diffInfo.direction = directionMatch[1].trim();
      }

      // 提取捕获时间
      const timeMatch = line.match(/capture_time:\s*([^,\s]+(?:\s+[^,\s]+)*)/);
      if (timeMatch) {
        diffInfo.capture_time = timeMatch[1].trim();
      }

      // 添加到差异报告列表
      mqttStats.value.differential_reports.push(diffInfo);

      // 更新代理问题统计
      diffInfo.diff_range_broker.forEach(broker => {
        if (mqttStats.value.broker_issues.hasOwnProperty(broker)) {
          (mqttStats.value.broker_issues as any)[broker]++;
        }
      });

      return diffInfo;

    } catch (error) {
      console.warn('解析差异报告失败:', line, error);
      return null;
    }

}

// 根据差异类型确定严重程度 function getDiffSeverityType(diffType: string): LogUIData['type'] { switch (diffType) { case 'Message Unexpected': case 'Message Missing': return 'ERROR'; // 消息级别差异，严重 case 'Field Different': case 'Field Missing': case 'Field Unexpected': return 'WARNING'; // 字段级别差异，中等 default: return 'INFO'; } }

// 根据差异类型获取图标 function getTypeIcon(diffType: string): string { switch (diffType) { case 'Message Unexpected': return '⚠️'; // 意外消息 case 'Message Missing': return '❌'; // 缺失消息 case 'Field Different': return '🔄'; // 字段差异 case 'Field Missing': return '🚫'; // 缺失字段 case 'Field Unexpected': return '❗'; // 意外字段 default: return '🔍'; // 一般差异 } }

// 处理MQTT协议的MBFuzzer日志行function processMQTTLogLine(line: string, packetCount: Ref<number>, successCount: Ref<number>, crashCount: Ref<number>) { const timestamp = new Date().toLocaleTimeString();

    try {
      // 优先处理差异报告 - 这是Fuzz过程的核心输出
      if (line.includes('protocol_version:') && (line.includes('type: {') || line.includes('field:'))) {
        const diffInfo = parseDifferentialReport(line, timestamp);
        if (diffInfo) {
          const brokerList = diffInfo.diff_range_broker.join(', ');
          const fieldInfo = diffInfo.field ? ` → ${diffInfo.field}` : '';
          const directionIcon = diffInfo.direction === 'client' ? '📤' : '📥';
          const typeIcon = getTypeIcon(diffInfo.type || '');

          // 构建更直观的差异描述
          let content = '';
          switch (diffInfo.type) {
            case 'Message Unexpected':
              content = `${typeIcon} 【协议差异】意外消息: ${diffInfo.msg_type} ${directionIcon} | 代理: ${brokerList} | MQTT v${diffInfo.protocol_version}`;
              break;
            case 'Message Missing':
              content = `${typeIcon} 【协议差异】缺失消息: ${diffInfo.msg_type} ${directionIcon} | 代理: ${brokerList} | MQTT v${diffInfo.protocol_version}`;
              break;
            case 'Field Different':
              content = `${typeIcon} 【协议差异】字段差异: ${diffInfo.msg_type}${fieldInfo} ${directionIcon} | 代理: ${brokerList} | MQTT v${diffInfo.protocol_version}`;
              break;
            case 'Field Missing':
              content = `${typeIcon} 【协议差异】缺失字段: ${diffInfo.msg_type}${fieldInfo} ${directionIcon} | 代理: ${brokerList} | MQTT v${diffInfo.protocol_version}`;
              break;
            case 'Field Unexpected':
              content = `${typeIcon} 【协议差异】意外字段: ${diffInfo.msg_type}${fieldInfo} ${directionIcon} | 代理: ${brokerList} | MQTT v${diffInfo.protocol_version}`;
              break;
            default:
              content = `${typeIcon} 【协议差异】${diffInfo.type}${fieldInfo} | ${diffInfo.msg_type} ${directionIcon} | 代理: ${brokerList} | MQTT v${diffInfo.protocol_version}`;
          }

          return {
            timestamp,
            type: getDiffSeverityType(diffInfo.type || ''),
            content,
            diffInfo,
            isDetailedDiff: true
          } as LogUIData;
        }
        return null;
      }

      // 解析基本统计信息（静默处理，不显示在Fuzz过程中）
      if (line.includes('Fuzzing Start Time:')) {
        const match = line.match(/Fuzzing Start Time:\s*(.+)/);
        if (match) {
          mqttStats.value.fuzzing_start_time = match[1].trim();
          // 只在开始时显示一次简单消息
          if (!mqttStats.value.fuzzing_end_time) {
            return {
              timestamp,
              type: 'INFO',
              content: `🚀 MBFuzzer 开始MQTT协议模糊测试...`
            } as LogUIData;
          }
        }
        return null;
      }

      if (line.includes('Fuzzing End Time:')) {
        const match = line.match(/Fuzzing End Time:\s*(.+)/);
        if (match) {
          mqttStats.value.fuzzing_end_time = match[1].trim();
          return {
            timestamp,
            type: 'SUCCESS',
            content: `✅ MBFuzzer 测试完成，正在生成测试总结...`
          } as LogUIData;
        }
        return null;
      }

      // 解析请求数量统计（静默处理，不在fuzz过程中显示）
      if (line.includes('Fuzzing request number (client):')) {
        const match = line.match(/Fuzzing request number \(client\):\s*(\d+)/);
        if (match) {
          mqttStats.value.client_request_count = parseInt(match[1]);
          packetCount.value = mqttStats.value.client_request_count + mqttStats.value.broker_request_count;
        }
        return null; // 静默处理，不显示
      }

      if (line.includes('Fuzzing request number (broker):')) {
        const match = line.match(/Fuzzing request number \(broker\):\s*(\d+)/);
        if (match) {
          mqttStats.value.broker_request_count = parseInt(match[1]);
          packetCount.value = mqttStats.value.client_request_count + mqttStats.value.broker_request_count;
        }
        return null; // 静默处理，不显示
      }

      // 解析消息类型统计（静默处理）
      const messageMatch = line.match(/^\s*([A-Z]+):\s*(\d+)/);
      if (messageMatch) {
        const [, messageType, count] = messageMatch;
        const countNum = parseInt(count);

        if (mqttStats.value.client_messages.hasOwnProperty(messageType)) {
          // 简单的启发式判断：如果客户端统计还是0，则认为是客户端数据
          if (mqttStats.value.client_messages[messageType as keyof MQTTMessageStats] === 0 &&
              mqttStats.value.broker_messages[messageType as keyof MQTTMessageStats] === 0) {
            (mqttStats.value.client_messages as any)[messageType] = countNum;
          } else if (mqttStats.value.broker_messages[messageType as keyof MQTTMessageStats] === 0) {
            (mqttStats.value.broker_messages as any)[messageType] = countNum;
          }
        }
        return null;
      }

      // 解析崩溃和差异统计（静默处理，不在fuzz过程中显示）
      if (line.includes('Crash Number:')) {
        const match = line.match(/Crash Number:\s*(\d+)/);
        if (match) {
          mqttStats.value.crash_number = parseInt(match[1]);
          crashCount.value = mqttStats.value.crash_number;
        }
        return null; // 静默处理，不显示
      }

      if (line.includes('Diff Number:')) {
        // 注意：不再从日志解析diff_number，改为实时累加模式
        // diff_number现在由addUnifiedLog函数实时递增
        return null; // 静默处理，不显示
      }

      if (line.includes('Valid Connect Number:')) {
        const match = line.match(/Valid Connect Number:\s*(\d+)/);
        if (match) {
          mqttStats.value.valid_connect_number = parseInt(match[1]);
          successCount.value = parseInt(match[1]);
        }
        return null; // 静默处理，不显示
      }

    } catch (error) {
      console.warn('解析MQTT日志行失败:', line, error);
    }

    return null;

}

return { mqttStats, resetMQTTStats, parseDifferentialReport, getDiffSeverityType, processMQTTLogLine, createEmptyMQTTMessageStats }; }

==================================================================================================== 文件 13: apps/web-antd/src/views/protocol-compliance/fuzz/composables/useProtocolDataManager.ts ====================================================================================================

/\*\*

- 协议数据管理器 - 隔离不同协议的数据和状态 \*/

import { ref, reactive, computed } from 'vue';

export type ProtocolType = 'SNMP' | 'MQTT';

export interface LogEntry { id: string; timestamp: string; type: 'INFO' | 'ERROR' | 'WARNING' | 'SUCCESS'; content: string; protocol: ProtocolType; raw?: any; // 原始数据 }

export interface ProtocolState { isRunning: boolean; isProcessing: boolean; totalRecords: number; processedRecords: number; logs: LogEntry[]; stats: Record<string, any>; }

export function useProtocolDataManager() { // 每个协议的独立状态 const protocolStates = reactive<Record<ProtocolType, ProtocolState>>({ SNMP: { isRunning: false, isProcessing: false, totalRecords: 0, processedRecords: 0, logs: [], stats: {} }, RTSP: { isRunning: false, isProcessing: false, totalRecords: 0, processedRecords: 0, logs: [], stats: {} }, MQTT: { isRunning: false, isProcessing: false, totalRecords: 0, processedRecords: 0, logs: [], stats: {} } });

const currentProtocol = ref<ProtocolType>('SNMP');

// 获取当前协议状态 const currentState = computed(() => protocolStates[currentProtocol.value]);

// 生成唯一ID function generateLogId(protocol: ProtocolType): string { return `${protocol}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`; }

// 添加日志（协议隔离）function addLog(protocol: ProtocolType, logData: Omit<LogEntry, 'id' | 'protocol'>) { const log: LogEntry = { ...logData, id: generateLogId(protocol), protocol };

    const state = protocolStates[protocol];
    state.logs.push(log);

    // 限制日志数量，避免内存泄漏（保留最新的10000条）
    if (state.logs.length > 10000) {
      state.logs.splice(0, state.logs.length - 10000);
    }

    return log;

}

// 批量添加日志 function addBatchLogs(protocol: ProtocolType, logsData: Array<Omit<LogEntry, 'id' | 'protocol'>>) { const logs = logsData.map(logData => ({ ...logData, id: generateLogId(protocol), protocol }));

    const state = protocolStates[protocol];
    state.logs.push(...logs);

    // 限制日志数量
    if (state.logs.length > 10000) {
      state.logs.splice(0, state.logs.length - 10000);
    }

    return logs;

}

// 清空指定协议的日志 function clearProtocolLogs(protocol: ProtocolType) { protocolStates[protocol].logs = []; }

// 清空所有协议的日志 function clearAllLogs() { Object.keys(protocolStates).forEach(protocol => { protocolStates[protocol as ProtocolType].logs = []; }); }

// 更新协议状态 function updateProtocolState(protocol: ProtocolType, updates: Partial<ProtocolState>) { Object.assign(protocolStates[protocol], updates); }

// 切换协议 function switchProtocol(protocol: ProtocolType) { currentProtocol.value = protocol; }

// 获取协议统计信息 function getProtocolStats(protocol: ProtocolType) { const state = protocolStates[protocol]; const logs = state.logs;

    return {
      total: logs.length,
      info: logs.filter(log => log.type === 'INFO').length,
      error: logs.filter(log => log.type === 'ERROR').length,
      warning: logs.filter(log => log.type === 'WARNING').length,
      success: logs.filter(log => log.type === 'SUCCESS').length,
      isRunning: state.isRunning,
      isProcessing: state.isProcessing,
      progress: state.totalRecords > 0 ? Math.round((state.processedRecords / state.totalRecords) * 100) : 0
    };

}

// 获取最近的日志 function getRecentLogs(protocol: ProtocolType, count: number = 100) { const logs = protocolStates[protocol].logs; return logs.slice(-count); }

// 搜索日志 function searchLogs(protocol: ProtocolType, keyword: string, type?: LogEntry['type']) { const logs = protocolStates[protocol].logs; return logs.filter(log => { const matchesKeyword = log.content.toLowerCase().includes(keyword.toLowerCase()); const matchesType = !type || log.type === type; return matchesKeyword && matchesType; }); }

// 导出日志 function exportLogs(protocol: ProtocolType, format: 'json' | 'txt' = 'txt') { const logs = protocolStates[protocol].logs;

    if (format === 'json') {
      return JSON.stringify(logs, null, 2);
    } else {
      return logs.map(log =>
        `[${log.timestamp}] [${log.type}] ${log.content}`
      ).join('\n');
    }

}

// 实时日志流（用于MQTT等需要实时更新的协议）const realtimeStreams = new Map<ProtocolType, { buffer: LogEntry[]; timer: number | null; batchSize: number; interval: number; }>();

// 开始实时日志流 function startRealtimeStream(protocol: ProtocolType, options = { batchSize: 20, interval: 50 }) { if (realtimeStreams.has(protocol)) { stopRealtimeStream(protocol); }

    const stream = {
      buffer: [],
      timer: null,
      batchSize: options.batchSize,
      interval: options.interval
    };

    // 定时批量处理缓冲区的日志
    stream.timer = window.setInterval(() => {
      if (stream.buffer.length > 0) {
        const batch = stream.buffer.splice(0, stream.batchSize);
        const state = protocolStates[protocol];
        state.logs.push(...batch);

        // 限制日志数量
        if (state.logs.length > 10000) {
          state.logs.splice(0, state.logs.length - 10000);
        }
      }
    }, stream.interval);

    realtimeStreams.set(protocol, stream);

}

// 添加到实时流缓冲区 function addToRealtimeStream(protocol: ProtocolType, logData: Omit<LogEntry, 'id' | 'protocol'>) { const stream = realtimeStreams.get(protocol); if (stream) { const log: LogEntry = { ...logData, id: generateLogId(protocol), protocol }; stream.buffer.push(log); } else { // 如果没有启动实时流，直接添加 addLog(protocol, logData); } }

// 停止实时日志流 function stopRealtimeStream(protocol: ProtocolType) { const stream = realtimeStreams.get(protocol); if (stream) { if (stream.timer) { clearInterval(stream.timer); } // 处理剩余的缓冲区日志 if (stream.buffer.length > 0) { const state = protocolStates[protocol]; state.logs.push(...stream.buffer); } realtimeStreams.delete(protocol); } }

// 停止所有实时流 function stopAllRealtimeStreams() { realtimeStreams.forEach((\_, protocol) => { stopRealtimeStream(protocol); }); }

return { // 状态 protocolStates, currentProtocol, currentState,

    // 基础操作
    addLog,
    addBatchLogs,
    clearProtocolLogs,
    clearAllLogs,
    updateProtocolState,
    switchProtocol,

    // 查询和统计
    getProtocolStats,
    getRecentLogs,
    searchLogs,
    exportLogs,

    // 实时流
    startRealtimeStream,
    addToRealtimeStream,
    stopRealtimeStream,
    stopAllRealtimeStreams

}; }

==================================================================================================== 文件 14: apps/web-antd/src/views/protocol-compliance/fuzz/composables/useSNMP.ts ====================================================================================================

/\*\*

- SNMP协议专用的composable
- 包含SNMP_Fuzz相关的数据处理和UI逻辑 \*/

import { ref, nextTick, type Ref } from 'vue'; import type { FuzzPacket, SNMPStats, SNMPMessageStats } from './types';

export function useSNMP() { // SNMP统计数据const protocolStats: Ref<SNMPStats> = ref({ v1: 0, v2c: 0, v3: 0 }); const messageTypeStats: Ref<SNMPMessageStats> = ref({ get: 0, set: 0, getnext: 0, getbulk: 0 });

// 数据状态 const fuzzData = ref<FuzzPacket[]>([]); const totalPacketsInFile = ref(0); const fileTotalPackets = ref(0); const fileSuccessCount = ref(0); const fileTimeoutCount = ref(0); const fileFailedCount = ref(0);

// 重置SNMP统计数据function resetSNMPStats() { protocolStats.value = { v1: 0, v2c: 0, v3: 0 }; messageTypeStats.value = { get: 0, set: 0, getnext: 0, getbulk: 0 }; }

// 生成默认测试数据 function generateDefaultFuzzData() { return `[1] 版本=v1, 类型=get 选择OIDs=['1.3.6.1.2.1.1.1.0'] 报文HEX: 302902010004067075626C6963A01C02040E8F83C502010002010030 [发送尝试] 长度=43 字节 [接收成功] 42 字节 [2] 版本=v2c, 类型=set 选择OIDs=['1.3.6.1.2.1.1.2.0'] 报文HEX: 304502010104067075626C6963A03802040E8F83C502010002010030 [发送尝试] 长度=71 字节 [接收超时] [3] 版本=v3, 类型=getnext 选择OIDs=['1.3.6.1.2.1.1.3.0'] 报文HEX: 305502010304067075626C6963A04802040E8F83C502010002010030 [发送尝试] 长度=87 字节 [接收成功] 156 字节 [4] 生成失败: 无效的OID格式 [5] 版本=v1, 类型=getbulk 选择OIDs=['1.3.6.1.2.1.1.4.0'] 报文HEX: 306502010004067075626C6963A05802040E8F83C502010002010030 [发送尝试] 长度=103 字节 [运行监控] 收到崩溃通知: 健康服务报告 VM 不可达 [崩溃信息] 疑似崩溃数据包: 306502010004067075626C6963A05802040E8F83C502010002010030 [崩溃信息] 崩溃队列信息导出: /home/hhh/下载/snmp_fuzz/snmp_github/snmp_fuzz/scan_result/crash_logs/20251014-110318 [运行监控] 检测到崩溃，停止 fuzz 循环 统计: {'v1': 3, 'v2c': 1, 'v3': 1}, {'get': 2, 'set': 1, 'getnext': 1, 'getbulk': 1} 开始时间: 2025-01-14 11:03:18 结束时间: 2025-01-14 11:03:25 总耗时: 7.2 秒 发送总数据包: 5 平均发送速率: 0.69 包/秒`; }

// 解析SNMP文本数据function parseSNMPText(text: string): FuzzPacket[] { if (!text || typeof text !== 'string') { console.error('Invalid fuzz data format'); return []; }

    const lines = text.split('\n');
    console.log('解析文本总行数:', lines.length);

    if (lines.length < 5) {
      console.error('Insufficient fuzz data');
      return [];
    }

    const parsedData: FuzzPacket[] = [];
    let currentPacket: FuzzPacket | null = null;
    let localFailedCount = 0;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      const packetMatch = line.match(/^\[(\d+)\]\s+版本=([^,]+),\s+类型=([^,]+)/);
      if (packetMatch) {
        if (currentPacket) parsedData.push(currentPacket);
        const packetNumber = parseInt(packetMatch[1]);

        // 调试信息：每100个包输出一次
        if (packetNumber % 100 === 0 || packetNumber <= 5) {
          console.log(`解析数据包 #${packetNumber}: 版本=${packetMatch[2]}, 类型=${packetMatch[3]}`);
        }
        currentPacket = {
          id: packetNumber,
          version: packetMatch[2],
          type: packetMatch[3],
          oids: [],
          hex: '',
          result: 'unknown',
          responseSize: 0,
          timestamp: new Date().toLocaleTimeString(),
          failed: false,
        };
        continue;
      }

      const failedMatch = line.match(/^\[(\d+)\]\s+生成失败:/);
      if (failedMatch) {
        const failedId = parseInt(failedMatch[1]);
        localFailedCount++;
        if (currentPacket && currentPacket.id === failedId) {
          currentPacket.result = 'failed';
          currentPacket.failed = true;
          currentPacket.failedReason = line;
          currentPacket.timestamp = new Date().toLocaleTimeString();
          parsedData.push(currentPacket);
          currentPacket = null;
        } else {
          parsedData.push({
            id: failedId,
            version: 'unknown',
            type: 'unknown',
            oids: [],
            hex: '',
            result: 'failed',
            responseSize: 0,
            timestamp: new Date().toLocaleTimeString(),
            failed: true,
            failedReason: line
          });
        }
        continue;
      }

      if (line.includes('选择OIDs=') && currentPacket) {
        const oidMatch = line.match(/选择OIDs=\[(.*?)\]/);
        if (oidMatch) currentPacket.oids = oidMatch[1].split(',').map((oid) => oid.trim().replace(/'/g, ''));
        continue;
      }

      if (line.includes('报文HEX:') && currentPacket) {
        const hexMatch = line.match(/报文HEX:\s*([A-F0-9]+)/);
        if (hexMatch) currentPacket.hex = hexMatch[1];
        continue;
      }

      if (line.includes('[发送尝试]') && currentPacket) {
        const sizeMatch = line.match(/长度=(\d+)\s*字节/);
        if (sizeMatch) (currentPacket as any).sendSize = parseInt(sizeMatch[1]);
        continue;
      }

      if (line.includes('[接收成功]') && currentPacket) {
        const sizeMatch = line.match(/(\d+)\s*字节/);
        if (sizeMatch) {
          currentPacket.responseSize = parseInt(sizeMatch[1]);
          currentPacket.result = 'success';
        }
        continue;
      }

      if (line.includes('[接收超时]') && currentPacket) {
        currentPacket.result = 'timeout';
        continue;
      }

      if (line.includes('[运行监控]')) {
        const isExactCrashNotice = line.includes('[运行监控] 收到崩溃通知: 健康服务报告 VM 不可达');
        if (isExactCrashNotice || line.includes('崩溃通知')) {
          const crashEvent = {
            type: 'crash_notification',
            message: line,
            timestamp: new Date().toLocaleTimeString(),
            crashPacket: '',
            crashLogPath: ''
          };

          for (let j = i + 1; j < lines.length && j < i + 30; j++) {
            const nextLine = lines[j].trim();
            if (nextLine.includes('[崩溃信息] 疑似崩溃数据包:')) {
              crashEvent.crashPacket = nextLine.replace('[崩溃信息] 疑似崩溃数据包: ', '');
            } else if (nextLine.includes('[崩溃信息] 崩溃队列信息导出:')) {
              crashEvent.crashLogPath = nextLine.replace('[崩溃信息] 崩溃队列信息导出: ', '');
            }
            if (crashEvent.crashPacket && crashEvent.crashLogPath) break;
          }

          parsedData.push({
            id: 'crash_event',
            version: 'crash',
            type: 'crash',
            oids: [],
            hex: crashEvent.crashPacket,
            result: 'crash',
            responseSize: 0,
            timestamp: crashEvent.timestamp,
            crashEvent
          });

          if (currentPacket) {
            currentPacket.result = 'crash';
            (currentPacket as any).crashInfo = line;
          }
        } else if (line.includes('检测到崩溃')) {
          if (currentPacket) (currentPacket as any).monitorInfo = line;
        }
        continue;
      }
    }

    if (currentPacket) parsedData.push(currentPacket);

    console.log('解析完成统计:');
    console.log('- 总数据包数:', parsedData.length);
    console.log('- 失败数据包数:', localFailedCount);

    // 解析统计信息
    const statsLine = (text.match(/^统计:.*$/m) || [])[0];
    if (statsLine) {
      const objMatch = statsLine.match(/统计:\s*(\{[^}]+\})\s*,\s*(\{[^}]+\})/);
      if (objMatch) {
        try {
          const versionJson = objMatch[1].replace(/'/g, '"');
          const typeJson = objMatch[2].replace(/'/g, '"');
          const parsedVersion = JSON.parse(versionJson);
          const parsedType = JSON.parse(typeJson);
          protocolStats.value = {
            v1: parsedVersion.v1 || 0,
            v2c: parsedVersion.v2c || 0,
            v3: parsedVersion.v3 || 0
          };
          messageTypeStats.value = {
            get: parsedType.get || 0,
            set: parsedType.set || 0,
            getnext: parsedType.getnext || 0,
            getbulk: parsedType.getbulk || 0
          };
        } catch (error) {
          console.warn('解析统计信息失败:', error);
        }
      }
    }

    // 更新状态变量
    fuzzData.value = parsedData;
    totalPacketsInFile.value = parsedData.filter((p) => typeof p.id === 'number').length;
    fileTotalPackets.value = parsedData.length;
    fileSuccessCount.value = parsedData.filter(p => p.result === 'success').length;
    fileTimeoutCount.value = parsedData.filter(p => p.result === 'timeout').length;
    fileFailedCount.value = localFailedCount;

    return parsedData;

}

// 处理SNMP数据包function processSNMPPacket(packet: FuzzPacket, addLogToUI: (packet: FuzzPacket, isCrash: boolean) => void, updateCounters?: (result: string) => void) { try { // Update protocol stats if (packet.version === 'v1') protocolStats.value.v1++; else if (packet.version === 'v2c') protocolStats.value.v2c++; else if (packet.version === 'v3') protocolStats.value.v3++;

      // Update message type stats
      if (packet.type === 'get') messageTypeStats.value.get++;
      else if (packet.type === 'set') messageTypeStats.value.set++;
      else if (packet.type === 'getnext') messageTypeStats.value.getnext++;
      else if (packet.type === 'getbulk') messageTypeStats.value.getbulk++;

      // Update result counters through callback if provided
      if (updateCounters) {
        updateCounters(packet.result || 'unknown');
      }

      // Add to UI log (sparse updates for performance)
      if (packet.result !== 'crash' && Math.random() < 0.1) { // 10% chance to show
        addLogToUI(packet, false);
      } else if (packet.result === 'crash') {
        addLogToUI(packet, true);
      }
    } catch (error) {
      console.warn('Error processing SNMP packet:', error);
    }

}

// SNMP专用的日志显示函数function addSNMPLogToUI(packet: FuzzPacket, isCrash: boolean, logContainer: HTMLElement | null, showHistoryView: boolean, isRunning: boolean) { // 检查DOM元素是否存在且在实时测试视图中if (!logContainer || showHistoryView || !isRunning) { return; }

    // Use nextTick to ensure DOM is stable before manipulation
    nextTick(() => {
      try {
        // Double-check DOM element still exists after nextTick
        if (!logContainer || !logContainer.appendChild || showHistoryView || !isRunning) {
          return;
        }

        const div = document.createElement('div');
        div.className = isCrash ? 'crash-highlight' : 'packet-highlight';

        if (isCrash) {
          div.innerHTML = `<span class="text-dark/50">[${packet.timestamp || ''}]</span> <span class="text-danger font-bold">CRASH DETECTED</span> <span class="text-danger">${packet.version?.toUpperCase() || 'UNKNOWN'}</span> <span class="text-danger">${packet.type?.toUpperCase() || 'UNKNOWN'}</span>`;
        } else {
          const protocol = packet.version?.toUpperCase() || 'UNKNOWN';
          const op = packet.type?.toUpperCase() || 'UNKNOWN';
          const time = packet.timestamp || '';
          const content = packet.oids?.[0] || '';
          const hex = (packet.hex || '').slice(0, 40);
          const resultText = packet.result === 'success' ? `正常响应 (${packet.responseSize || 0}字节)` :
                            packet.result === 'timeout' ? '接收超时' :
                            packet.result === 'failed' ? '构造失败' : '未知状态';
          const resultClass = packet.result === 'success' ? 'text-success' :
                             packet.result === 'timeout' ? 'text-warning' :
                             packet.result === 'failed' ? 'text-danger' : 'text-warning';

          div.innerHTML = `<span class="text-dark/50">[${time}]</span> <span class="text-primary">SNMP${protocol}</span> <span class="text-info">${op}</span> <span class="text-dark/70 truncate inline-block w-32" title="${content}">${content}</span> <span class="${resultClass} font-medium">${resultText}</span> <span class="text-dark/40">${hex}...</span>`;
        }

        // Final check before DOM manipulation
        if (logContainer && logContainer.appendChild) {
          logContainer.appendChild(div);

          // Safely update scroll position
          if (logContainer.scrollTop !== undefined) {
            logContainer.scrollTop = logContainer.scrollHeight;
          }

          // Limit log entries for performance with safe checks
          if (logContainer.children && logContainer.children.length > 200) {
            const firstChild = logContainer.firstChild;
            if (firstChild && logContainer.removeChild) {
              logContainer.removeChild(firstChild);
            }
          }
        }
      } catch (error) {
        console.warn('Failed to add SNMP log to UI:', error);
      }
    });

}

// SNMP测试启动函数async function startSNMPTest(loop: () => void) { // SNMP协议的原有逻辑console.log('启动SNMP测试...'); loop(); }

return { protocolStats, messageTypeStats, fuzzData, totalPacketsInFile, fileTotalPackets, fileSuccessCount, fileTimeoutCount, fileFailedCount, resetSNMPStats, generateDefaultFuzzData, parseSNMPText, processSNMPPacket, addSNMPLogToUI, startSNMPTest }; }

==================================================================================================== 文件 15: apps/web-antd/src/views/protocol-compliance/fuzz/composables/useSOL.ts ====================================================================================================

/\*\*

- SOL协议专用的composable
- 包含AFLNET相关的数据处理和UI逻辑 \*/

import { ref, type Ref } from 'vue'; import type { RTSPStats, LogUIData } from './types'; import { requestClient, dockerRequestClient } from '#/api/request';

export function useSOL() { // SOL统计数据const solStats: Ref<RTSPStats> = ref({ cycles_done: 0, paths_total: 0, cur_path: 0, pending_total: 0, pending_favs: 0, map_size: '0%', unique_crashes: 0, unique_hangs: 0, max_depth: 0, execs_per_sec: 0, n_nodes: 0, n_edges: 0 });

// 重置SOL统计数据function resetSOLStats() { solStats.value = { cycles_done: 0, paths_total: 0, cur_path: 0, pending_total: 0, pending_favs: 0, map_size: '0%', unique_crashes: 0, unique_hangs: 0, max_depth: 0, execs_per_sec: 0, n_nodes: 0, n_edges: 0 }; }

// 处理SOL协议的AFL-NET日志行function processSOLLogLine(line: string, packetCount: Ref<number>, successCount: Ref<number>, failedCount: Ref<number>, crashCount: Ref<number>, currentSpeed: Ref<number>) { const timestamp = new Date().toLocaleTimeString();

    // 处理注释行（参数说明）
    if (line.startsWith('#')) {
      return {
        timestamp,
        type: 'HEADER',
        content: line.replace('#', '').trim(),
        isHeader: true
      } as LogUIData;
    }

    // 处理数据行
    if (line.includes(',')) {
      const parts = line.split(',').map(part => part.trim());
      if (parts.length >= 13) {
        const [
          unix_time, cycles_done, cur_path, paths_total, pending_total,
          pending_favs, map_size, unique_crashes, unique_hangs, max_depth,
          execs_per_sec, n_nodes, n_edges
        ] = parts;

        // 格式化显示AFL-NET统计信息
        const formattedContent = `Cycles: ${cycles_done} | Paths: ${cur_path}/${paths_total} | Pending: ${pending_total}(${pending_favs} favs) | Coverage: ${map_size} | Crashes: ${unique_crashes} | Hangs: ${unique_hangs} | Speed: ${execs_per_sec}/sec | Nodes: ${n_nodes} | Edges: ${n_edges}`;

        // 更新SOL统计信息
        solStats.value = {
          cycles_done: parseInt(cycles_done),
          paths_total: parseInt(paths_total),
          cur_path: parseInt(cur_path),
          pending_total: parseInt(pending_total),
          pending_favs: parseInt(pending_favs),
          map_size: map_size,
          unique_crashes: parseInt(unique_crashes),
          unique_hangs: parseInt(unique_hangs),
          max_depth: parseInt(max_depth),
          execs_per_sec: parseFloat(execs_per_sec),
          n_nodes: parseInt(n_nodes),
          n_edges: parseInt(n_edges)
        };

        // 更新通用统计信息
        packetCount.value = parseInt(cur_path);
        successCount.value = parseInt(paths_total) - parseInt(pending_total);
        failedCount.value = parseInt(unique_crashes);
        crashCount.value = parseInt(unique_crashes);
        currentSpeed.value = Math.round(parseFloat(execs_per_sec));

        return {
          timestamp,
          type: 'STATS',
          content: formattedContent,
          rawData: {
            cycles_done: parseInt(cycles_done),
            paths_total: parseInt(paths_total),
            cur_path: parseInt(cur_path),
            pending_total: parseInt(pending_total),
            unique_crashes: parseInt(unique_crashes),
            execs_per_sec: parseFloat(execs_per_sec)
          }
        } as LogUIData;
      }
    } else {
      // 处理其他类型的日志行
      return {
        timestamp,
        type: 'INFO',
        content: line
      } as LogUIData;
    }

    return null;

}

// 写入SOL脚本文件async function writeSOLScript(scriptContent: string, protocolImplementations?: string[]) { try { const result = await requestClient.post('/protocol-compliance/write-script', { content: scriptContent, protocol: 'MQTT', // SOL协议现在通过MQTT协议实现选择protocolImplementations: protocolImplementations || [] }); return result;

    } catch (error: any) {
      console.error('写入SOL脚本失败:', error);
      throw new Error(`写入脚本文件失败: ${error.message}`);
    }

}

// 执行SOL命令async function executeSOLCommand(protocolImplementations?: string[]) { console.log('[DEBUG] ========== executeSOLCommand 被调用 =========='); console.log('[DEBUG] protocolImplementations:', protocolImplementations);

    try {
      const requestData = {
        protocol: 'MQTT',  // SOL协议现在通过MQTT协议实现选择
        protocolImplementations: protocolImplementations || []
      };

      console.log('[DEBUG] 发送请求到 /protocol-compliance/execute-command');
      console.log('[DEBUG] 请求数据:', requestData);

      const result = await dockerRequestClient.post('/protocol-compliance/execute-command', requestData);

      console.log('[DEBUG] API响应成功:', result);

      // 由于响应拦截器的处理，数据可能直接在result中，也可能在result.data中
      const responseData = result.data || result;
      console.log('[DEBUG] 响应数据结构:', {
        status: result.status,
        data: result.data,
        responseData: responseData,
        hasContainerId: !!responseData?.container_id,
        hasPid: !!responseData?.pid
      });

      return result;

    } catch (error: any) {
      console.error('[DEBUG] 执行SOL命令失败:', error);
      console.error('[DEBUG] 错误详情:', error.response?.data || error.message);
      throw new Error(`执行启动命令失败: ${error.message}`);
    }

}

// 停止SOL进程async function stopSOLProcess(processId: string | number) { if (!processId) { return; }

    try {
      const result = await requestClient.post('/protocol-compliance/stop-process', {
        pid: processId,
        protocol: 'RTSP'  // 保持协议标识符为RTSP
      });
      return result;
    } catch (error) {
      console.error('停止SOL进程失败:', error);
      throw error;
    }

}

// 启动前清理：停止现有容器并清理输出文件 async function preStartCleanupSOL() { console.log('[DEBUG] ========== preStartCleanupSOL 被调用 ==========');

    try {
      const requestData = {
        protocol: 'MQTT'  // SOL协议通过MQTT协议实现选择
      };

      console.log('[DEBUG] 发送请求到 /protocol-compliance/pre-start-cleanup');
      console.log('[DEBUG] 请求数据:', requestData);

      const result = await dockerRequestClient.post('/protocol-compliance/pre-start-cleanup', requestData);

      console.log('[DEBUG] 启动前清理API响应成功:', result);
      return result;
    } catch (error) {
      console.error('[DEBUG] 启动前清理失败:', error);
      console.error('[DEBUG] 错误详情:', error.response?.data || error.message);
      throw error;
    }

}

// 停止SOL Docker容器（不清理输出文件）async function stopSOLContainer(containerId: string) { console.log('[DEBUG] ========== stopSOLContainer 被调用 =========='); console.log('[DEBUG] 传入的容器ID:', containerId);

    if (!containerId) {
      console.log('[DEBUG] 容器ID为空，直接返回');
      return;
    }

    try {
      const requestData = {
        container_id: containerId,
        protocol: 'RTSP'  // 保持协议标识符为RTSP
      };

      console.log('[DEBUG] 发送请求到 /protocol-compliance/stop-and-cleanup');
      console.log('[DEBUG] 请求数据:', requestData);

      const result = await dockerRequestClient.post('/protocol-compliance/stop-and-cleanup', requestData);

      console.log('[DEBUG] 停止容器API响应成功:', result);
      return result;
    } catch (error) {
      console.error('[DEBUG] 停止SOL容器失败:', error);
      console.error('[DEBUG] 错误详情:', error.response?.data || error.message);
      throw error;
    }

}

// 兼容性函数：保持原有的stopAndCleanupSOL接口async function stopAndCleanupSOL(containerId: string) { return stopSOLContainer(containerId); }

return { solStats, resetSOLStats, processSOLLogLine, writeSOLScript, executeSOLCommand, stopSOLProcess, preStartCleanupSOL, stopSOLContainer, stopAndCleanupSOL }; }

==================================================================================================== 文件 16: apps/backend-flask/protocol_compliance/**init**.py ====================================================================================================

[空文件]

==================================================================================================== 文件 17: apps/backend-flask/protocol_compliance/routes.py ====================================================================================================

"""Flask blueprints for the protocol compliance domain."""

from **future** import annotations

import contextlib import json import logging import os import re import sqlite3 import subprocess import threading import uuid from datetime import datetime, timezone from pathlib import Path from typing import Any, Dict, Iterable, List, Optional, cast

import toml from flask import Blueprint, make_response, request, send_file from werkzeug.datastructures import FileStorage

try: from ..utils.auth import verify_access_token from ..utils.responses import ( error_response, make_error_payload, paginate, success_response, unauthorized, ) except ImportError: from utils.auth import verify_access_token from utils.responses import ( error_response, make_error_payload, paginate, success_response, unauthorized, ) from .analysis import ( delete_static_analysis_job, extract_protocol_version, get_static_analysis_job, get_static_analysis_result, list_static_analysis_history, normalize_protocol_name, submit_static_analysis_job, try_extract_rules_summary, ) from .assertion import ( get_assertion_history_diff_path, get_assertion_history_entry, get_assert_generation_job, get_assert_generation_result, get_assert_generation_zip_path, submit_assert_generation_job, submit_diff_parsing_job, get_diff_parsing_job, get_diff_parsing_result, list_assertion_history, ) from .store import STORE, TaskStatus from .pipeline_runner import ( PipelineExecutionError, PipelineResultNotFoundError, run_protocol_pipeline, )

LOGGER = logging.getLogger(**name**)

bp = Blueprint("protocol_compliance", **name**, url_prefix="/api/protocol-compliance")

# Authentication -------------------------------------------------------------

def \_ensure_authenticated(): user = verify_access_token(request.headers.get("Authorization")) if not user: return None, unauthorized() return user, None

# Helpers -------------------------------------------------------------------

def \_to_int(value: Optional[str], fallback: int) -> int: try: parsed = int(value) except (TypeError, ValueError): return fallback return parsed if parsed > 0 else fallback

def \_normalize_status(raw: Optional[Iterable[str]]) -> Optional[list[TaskStatus]]: if not raw: return None statuses: set[TaskStatus] = set() allowed: set[TaskStatus] = {"completed", "failed", "processing", "queued"}

    for item in raw:
        if not item:
            continue
        segments = [segment.strip() for segment in item.split(",")]
        for segment in segments:
            if segment in allowed:
                statuses.add(segment)  # type: ignore[arg-type]

    return list(statuses) if statuses else None

def \_parse_tags(raw: Optional[str]) -> Optional[list[str]]: if not raw: return None try: parsed = json.loads(raw) except json.JSONDecodeError: return None if isinstance(parsed, list): tags = [item for item in parsed if isinstance(item, str)] return tags or None return None

def \_read_upload(upload: FileStorage) -> tuple[str, Optional[bytes]]: filename = upload.filename or "upload.bin" data = upload.read() if upload else None if upload: with contextlib.suppress(Exception): upload.stream.seek(0) return filename, data

def \_extract_protocol_metadata_from_config( raw: Optional[bytes], source_label: str ) -> tuple[Optional[str], Optional[str]]: if not raw: LOGGER.debug("Config payload %s is empty; skipping protocol metadata extraction", source_label) return None, None try: text = raw.decode("utf-8") except UnicodeDecodeError as exc: LOGGER.warning("Failed to decode %s as UTF-8 while extracting protocol metadata: %s", source_label, exc) return None, None try: parsed = toml.loads(text) except toml.TomlDecodeError as exc: LOGGER.warning("Failed to parse %s as TOML while extracting protocol metadata: %s", source_label, exc) return None, None

    project = parsed.get("project")
    if isinstance(project, dict):
        raw_name = project.get("protocol_name") or project.get("protocol")
        raw_version = project.get("protocol_version") or project.get("version")
        name = raw_name.strip() if isinstance(raw_name, str) else None
        version = raw_version.strip() if isinstance(raw_version, str) else None
        return (name or None, version or None)

    LOGGER.debug(
        "Config %s does not define a [project] section when extracting protocol metadata", source_label
    )
    return None, None

def \_collect_exception_details(exc: Exception, \*, max_logs: int = 40) -> dict: details = {"message": str(exc)} extra = getattr(exc, "details", None) if isinstance(extra, dict) and extra: details.update(extra)

    logs = getattr(exc, "logs", None)
    if isinstance(logs, list) and logs:
        details["logs"] = logs[-max_logs:]

    excerpt = getattr(exc, "log_excerpt", None)
    if excerpt and "logExcerpt" not in details:
        details["logExcerpt"] = excerpt

    return details

# Routes --------------------------------------------------------------------

@bp.route("/extract/run", methods=["POST"]) def run*protocol_extract(): *, error = \_ensure_authenticated() if error: return error

    html_upload = request.files.get("htmlFile")
    if not isinstance(html_upload, FileStorage):
        return make_response(error_response("请上传协议 HTML 文件"), 400)

    api_key = (request.form.get("apiKey") or "").strip()
    protocol = (request.form.get("protocol") or "").strip()
    version = (request.form.get("version") or "").strip()
    filter_flag = (request.form.get("filterHeadings") or "").strip().lower()
    filter_headings = filter_flag in {"1", "true", "yes", "on"}

    try:
        result = run_protocol_pipeline(
            api_key=api_key,
            protocol=protocol,
            version=version,
            html_upload=html_upload,
            filter_headings=filter_headings,
        )
    except ValueError as exc:
        payload = make_error_payload("参数错误", details=str(exc))
        return make_response(payload, 400)
    except FileNotFoundError as exc:
        payload = make_error_payload("流程未准备就绪", details=str(exc))
        return make_response(payload, 500)
    except PipelineResultNotFoundError as exc:
        detail = {"message": str(exc)}
        payload = make_error_payload("未找到分析结果文件", details=detail)
        return make_response(payload, 500)
    except PipelineExecutionError as exc:
        detail = {
            "stdout": (exc.stdout or "").splitlines()[-40:] or None,
            "stderr": (exc.stderr or "").splitlines()[-40:] or None,
        }
        payload = make_error_payload("协议分析执行失败", details=detail)
        return make_response(payload, 500)

    payload = success_response(
        {
            "protocol": result.protocol,
            "version": result.version,
            "ruleCount": len(result.rules),
            "rules": [
                {
                    "rule": item.rule,
                    "req_type": item.req_type,
                    "req_fields": item.req_fields,
                    "res_type": item.res_type,
                    "res_fields": item.res_fields,
                    "group": item.group,
                }
                for item in result.rules
            ],
            "storeDir": str(result.store_dir),
            "resultPath": str(result.result_path),
        }
    )
    return make_response(payload, 200)

@bp.route("/tasks", methods=["GET"]) def list*tasks(): *, error = \_ensure_authenticated() if error: return error

    page = _to_int(request.args.get("page"), 1)
    page_size = min(_to_int(request.args.get("pageSize"), 20), 50)
    status = _normalize_status(request.args.getlist("status"))

    tasks = STORE.list_tasks(status=status)
    paged, total = paginate(tasks, page, page_size)

    base_url = request.url_root.rstrip("/")
    items = [STORE.serialize_task(task, base_url) for task in paged]

    if page > 1 and not items and total > 0:
        payload = error_response("Requested page exceeds available data")
        return make_response(payload, 400)

    payload = success_response(
        {
            "items": items,
            "page": page,
            "pageSize": page_size,
            "total": total,
        }
    )
    return payload

@bp.route("/tasks", methods=["POST"]) def create*task(): *, error = \_ensure_authenticated() if error: return error

    if "file" not in request.files and not request.files:
        payload = error_response("请上传协议文档")
        return make_response(payload, 400)

    document_name: Optional[str] = None
    document_size: Optional[int] = None

    for upload in request.files.values():
        if not isinstance(upload, FileStorage):
            continue
        document_name = upload.filename
        data = upload.read()
        document_size = len(data) if data else None
        upload.stream.seek(0)
        break

    if not document_name:
        payload = error_response("缺少协议文档，请重新上传")
        return make_response(payload, 400)

    description = request.form.get("description", "").strip() or None
    name = (
        request.form.get("name", "").strip()
        or _strip_extension(document_name)
        or "协议任务"
    )
    tags = _parse_tags(request.form.get("tags"))

    task = STORE.create_task(
        name=name,
        document_name=document_name,
        document_size=document_size,
        description=description,
        tags=tags,
    )

    base_url = request.url_root.rstrip("/")
    payload = success_response(STORE.serialize_task(task, base_url))
    return payload

@bp.route("/tasks/<task*id>/result", methods=["GET"]) def download_result(task_id: str): *, error = \_ensure_authenticated() if error: return error

    task = STORE.get_task(task_id)
    if not task:
        return make_response(error_response("未找到指定任务"), 404)

    if task.status != "completed" or not task.result_payload:
        return make_response(
            error_response("任务尚未完成，暂不可下载结果"), 409
        )

    content = json.dumps(task.result_payload, ensure_ascii=False, indent=2)
    base_name = re.sub(r"\s+", "-", task.name or task.document_name)
    file_name = f"{base_name}-rules.json"

    response = make_response(content)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response

@bp.route("/static-analysis", methods=["POST"]) def static*analysis(): *, error = \_ensure_authenticated() if error: return error

    if not request.files:
        return make_response(
            error_response("请上传源码、Builder Dockerfile、协议规则和配置文件"), 400
        )

    uploads_map = {
        "codeArchive": request.files.get("codeArchive"),
        "builderDockerfile": request.files.get("builderDockerfile"),
        "rules": request.files.get("rules"),
        "config": request.files.get("config"),
    }

    missing = [
        key for key, value in uploads_map.items() if not isinstance(value, FileStorage)
    ]
    if missing:
        labels = {
            "codeArchive": "源码压缩包",
            "builderDockerfile": "Builder Dockerfile",
            "rules": "协议规则 JSON",
            "config": "分析配置 TOML",
        }
        readable = "、".join(labels.get(item, item) for item in missing)
        return make_response(
            error_response(f"请上传完整文件：{readable}"), 400
        )

    code_upload = cast(FileStorage, uploads_map["codeArchive"])
    builder_upload = cast(FileStorage, uploads_map["builderDockerfile"])
    rules_upload = cast(FileStorage, uploads_map["rules"])
    config_upload = cast(FileStorage, uploads_map["config"])

    code_name, code_data = _read_upload(code_upload)
    builder_name, builder_data = _read_upload(builder_upload)
    rules_name, rules_data = _read_upload(rules_upload)
    config_name, config_data = _read_upload(config_upload)

    if code_data is None or builder_data is None or config_data is None or rules_data is None:
        return make_response(error_response("上传的文件内容为空，请重新上传"), 400)

    parsed_rules = None
    if rules_data:
        try:
            parsed_rules = json.loads(rules_data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            parsed_rules = None

    config_protocol_name, config_protocol_version = _extract_protocol_metadata_from_config(config_data, config_name)

    rules_protocol_fallback = normalize_protocol_name(parsed_rules, _strip_extension(rules_name))
    protocol_name = config_protocol_name or rules_protocol_fallback
    if config_protocol_name:
        LOGGER.info(
            "Static analysis protocol resolved from config %s: %s",
            config_name,
            config_protocol_name,
        )
    else:
        LOGGER.info(
            "Static analysis protocol falling back to %s (config %s missing protocol_name)",
            rules_protocol_fallback,
            config_name,
        )

    rules_version_fallback = extract_protocol_version(parsed_rules, None)
    protocol_version = config_protocol_version or rules_version_fallback
    if config_protocol_version:
        LOGGER.info(
            "Static analysis protocol version resolved from config %s: %s",
            config_name,
            config_protocol_version,
        )
    elif rules_version_fallback:
        LOGGER.info(
            "Static analysis protocol version falling back to %s (config %s missing protocol_version)",
            rules_version_fallback,
            config_name,
        )
    rules_summary = try_extract_rules_summary(parsed_rules)
    notes = request.form.get("notes")

    snapshot = submit_static_analysis_job(
        code_payload=(code_name, code_data),
        builder_payload=(builder_name, builder_data),
        config_payload=(config_name, config_data),
        rules_payload=(rules_name, rules_data),
        notes=notes,
        protocol_name=protocol_name,
        protocol_version=protocol_version,
        rules_summary=rules_summary,
    )
    return make_response(success_response(snapshot), 202)

@bp.route("/static-analysis/history", methods=["GET"]) def static*analysis_history(): *, error = \_ensure_authenticated() if error: return error

    limit = _to_int(request.args.get("limit"), 50)
    limit = max(1, min(limit, 200))
    history = list_static_analysis_history(limit=limit)
    payload = success_response({"items": history, "limit": limit, "count": len(history)})
    return make_response(payload, 200)

@bp.route("/static-analysis/history/<job*id>", methods=["DELETE"]) def delete_static_analysis_history(job_id: str): """Delete a static analysis job from the history.""" *, error = \_ensure_authenticated() if error: return error

    if not job_id or not isinstance(job_id, str):
        return make_response(error_response("无效的任务 ID"), 400)

    try:
        deleted = delete_static_analysis_job(job_id)
        if not deleted:
            return make_response(error_response("任务不存在"), 404)
        return make_response(success_response({"jobId": job_id, "deleted": True}), 200)
    except Exception as exc:
        LOGGER.error("Failed to delete static analysis job %s: %s", job_id, exc)
        return make_response(error_response(f"删除失败：{str(exc)}"), 500)

@bp.route("/assertions/history", methods=["GET"]) def assertion*history(): *, error = \_ensure_authenticated() if error: return error

    limit = _to_int(request.args.get("limit"), 50)
    limit = max(1, min(limit, 200))
    items = list_assertion_history(limit=limit)
    payload = {"items": items, "limit": limit, "count": len(items)}
    return make_response(success_response(payload), 200)

@bp.route("/assertions/history/<job*id>", methods=["GET"]) def assertion_history_entry(job_id: str): *, error = \_ensure_authenticated() if error: return error

    entry = get_assertion_history_entry(job_id)
    if not entry:
        return make_response(error_response("历史记录不存在"), 404)
    return make_response(success_response(entry), 200)

@bp.route("/assertions/history/<job*id>/diff", methods=["GET"]) def download_assertion_diff(job_id: str): *, error = \_ensure_authenticated() if error: return error

    diff_path = get_assertion_history_diff_path(job_id)
    if not diff_path:
        return make_response(error_response("Diff 文件不存在"), 404)
    return send_file(diff_path, as_attachment=True, download_name=diff_path.name)

def \_expand_path(raw: Optional[str]) -> Optional[Path]: if not raw or not isinstance(raw, str): return None try: return Path(raw).expanduser() except (OSError, ValueError): return None

def \_find_sqlite_file( database_path: Optional[str], workspace_path: Optional[str], ) -> tuple[Optional[Path], list[str]]: """Resolve the SQLite database path, collecting warnings.""" warnings: list[str] = []

    candidate = _expand_path(database_path)
    if candidate and candidate.is_file():
        return candidate, warnings
    if candidate and not candidate.exists():
        warnings.append(f"指定的数据库路径不存在：{candidate}")

    workspace = _expand_path(workspace_path)
    if workspace:
        if workspace.is_dir():
            matches = sorted(workspace.glob("sqlite_*.db"))
            if matches:
                return matches[0], warnings
            warnings.append(
                f"在工作目录 {workspace} 中未找到 sqlite_*.db 文件"
            )
        else:
            warnings.append(f"工作目录不存在或不可访问：{workspace}")

    return None, warnings

def \_parse_llm_response(payload: Any) -> Dict[str, Any]: if isinstance(payload, str): payload = payload.strip() if not payload or payload.lower() == "null": return {} try: decoded = json.loads(payload) except json.JSONDecodeError: return {"raw": payload} payload = decoded if isinstance(payload, dict): return payload return {}

def \_classify_rule_result(llm_payload: Dict[str, Any]) -> tuple[str, str]: result_text = str(llm_payload.get("result") or "").lower() if "violation" in result_text and "no violation" not in result_text: return "violation_found", "发现违规" if "no violation" in result_text: return "no_violation", "未发现违规" return "unknown", "未判定"

@bp.route("/static-analysis/database-insights", methods=["POST"]) def static*analysis_database_insights(): *, error = \_ensure_authenticated() if error: return error

    payload = request.get_json(silent=True)
    if payload is None:
        return make_response(
            error_response("请求体必须为 JSON 对象"),
            400,
        )
    if not isinstance(payload, dict):
        return make_response(
            error_response("请求体必须为 JSON 对象"),
            400,
        )

    job_id = payload.get("jobId")
    database_path_raw = cast(Optional[str], payload.get("databasePath"))
    workspace_path_raw = cast(Optional[str], payload.get("workspacePath"))

    LOGGER.info(
        "Static analysis database insights requested",
        extra={
            "jobId": job_id,
            "databasePath": database_path_raw,
            "workspacePath": workspace_path_raw,
        },
    )

    resolved_path, warnings = _find_sqlite_file(database_path_raw, workspace_path_raw)
    if not resolved_path:
        detail = {
            "jobId": job_id,
            "databasePath": database_path_raw,
            "workspacePath": workspace_path_raw,
            "warnings": warnings or None,
        }
        LOGGER.warning(
            f"Unable to resolve SQLite database for static analysis insights: databasePath={database_path_raw!r}, workspacePath={workspace_path_raw!r}",
            extra=detail,
        )
        return make_response(
            error_response("未找到静态分析结果数据库文件", detail),
            404,
        )

    LOGGER.info(
        "Resolved static analysis database file",
        extra={
            "jobId": job_id,
            "databasePath": str(resolved_path),
            "workspacePath": workspace_path_raw,
        },
    )

    try:
        conn = sqlite3.connect(resolved_path)
    except sqlite3.Error as exc:
        detail = {
            "jobId": job_id,
            "databasePath": str(resolved_path),
            "exception": exc.__class__.__name__,
            "args": [str(item) for item in exc.args],
        }
        LOGGER.exception(
            "Failed to open SQLite database for static analysis insights",
            extra=detail,
        )
        return make_response(
            error_response("无法打开静态分析结果数据库", detail),
            500,
        )

    conn.row_factory = sqlite3.Row

    query = (
        "SELECT rule_desc, code_snippet, call_graph, llm_response "
        "FROM rule_code_snippet"
    )
    try:
        cursor = conn.execute(query)
        rows = cursor.fetchall()
    except sqlite3.Error as exc:
        detail = {
            "jobId": job_id,
            "databasePath": str(resolved_path),
            "exception": exc.__class__.__name__,
            "args": [str(item) for item in exc.args],
            "query": query,
        }
        LOGGER.exception(
            "Failed to query rule_code_snippet from SQLite database",
            extra=detail,
        )
        conn.close()
        return make_response(
            error_response("读取静态分析规则结果失败", detail),
            500,
        )

    findings: List[Dict[str, Any]] = []
    parsing_warnings: List[str] = []

    for row in rows:
        rule_desc = row["rule_desc"]
        code_snippet = row["code_snippet"]
        call_graph = row["call_graph"]
        raw_llm_response = row["llm_response"]

        llm_payload = _parse_llm_response(raw_llm_response)
        result_status, result_label = _classify_rule_result(llm_payload)

        reason = llm_payload.get("reason")
        if isinstance(reason, str):
            reason = reason.strip()
        elif reason is not None:
            reason = json.dumps(reason, ensure_ascii=False)

        violations_payload = llm_payload.get("violations")
        violations: List[Dict[str, Any]] = []
        if isinstance(violations_payload, list):
            for entry in violations_payload:
                if not isinstance(entry, dict):
                    continue
                code_lines = entry.get("code_lines") or entry.get("codeLines")
                if isinstance(code_lines, list):
                    lines = []
                    for item in code_lines:
                        try:
                            lines.append(int(item))
                        except (TypeError, ValueError):
                            continue
                    code_lines = lines or None
                else:
                    code_lines = None
                violations.append(
                    {
                        "filename": entry.get("filename"),
                        "functionName": entry.get("function_name") or entry.get("functionName"),
                        "codeLines": code_lines,
                    }
                )

        findings.append(
            {
                "ruleDesc": rule_desc,
                "codeSnippet": code_snippet,
                "callGraph": call_graph,
                "llmRaw": raw_llm_response,
                "reason": reason,
                "result": result_status,
                "resultLabel": result_label,
                "violations": violations or None,
            }
        )

        if not llm_payload and raw_llm_response:
            parsing_warnings.append(
                f"规则[{rule_desc}]的 LLM 结果无法解析为 JSON，已返回原始字符串"
            )

    conn.close()

    response_payload: Dict[str, Any] = {
        "databasePath": str(resolved_path),
        "workspacePath": workspace_path_raw,
        "extractedAt": datetime.now(timezone.utc).isoformat(),
        "findings": findings,
    }
    all_warnings = warnings + parsing_warnings
    if all_warnings:
        response_payload["warnings"] = all_warnings

    LOGGER.info(
        "Static analysis database insights resolved",
        extra={
            "jobId": job_id,
            "databasePath": str(resolved_path),
            "findings": len(findings),
            "warnings": all_warnings,
        },
    )

    return make_response(success_response(response_payload), 200)

@bp.route("/static-analysis/<job*id>/progress", methods=["GET"]) def static_analysis_progress(job_id: str): *, error = \_ensure_authenticated() if error: return error

    # Support incremental event fetching via fromEventId query parameter
    from_event_id_raw = request.args.get("fromEventId")
    from_event_id: Optional[int] = None
    if from_event_id_raw is not None:
        try:
            from_event_id = int(from_event_id_raw)
        except (TypeError, ValueError):
            LOGGER.warning(
                "Invalid fromEventId parameter: %s (job_id=%s)",
                from_event_id_raw,
                job_id,
            )
            # Continue with full snapshot if parameter is invalid

    snapshot = get_static_analysis_job(job_id, from_event_id=from_event_id)
    if not snapshot:
        return make_response(error_response("未找到静态分析任务"), 404)
    return make_response(success_response(snapshot), 200)

@bp.route("/static-analysis/<job*id>/result", methods=["GET"]) def static_analysis_result(job_id: str): *, error = \_ensure_authenticated() if error: return error

    result = get_static_analysis_result(job_id)
    if result is None:
        snapshot = get_static_analysis_job(job_id)
        if not snapshot:
            return make_response(error_response("未找到静态分析任务"), 404)
        status = snapshot.get("status")
        return make_response(
            error_response("静态分析任务尚未完成", {"status": status}),
            409,
        )
    return make_response(success_response(result), 200)

@bp.route("/assertion-generation", methods=["POST"]) def assertion*generation(): *, error = \_ensure_authenticated() if error: return error

    if not request.files:
        return make_response(error_response("请上传源码压缩包和违规数据库"), 400)

    uploads_map = {
        "codeArchive": request.files.get("codeArchive"),
        "database": request.files.get("database"),
    }

    missing = [key for key, value in uploads_map.items() if not isinstance(value, FileStorage)]
    if missing:
        labels = {
            "codeArchive": "源码压缩包",
            "database": "违规数据库文件",
        }
        readable = "、".join(labels.get(item, item) for item in missing)
        return make_response(error_response(f"请上传完整文件：{readable}"), 400)

    code_upload = cast(FileStorage, uploads_map["codeArchive"])
    database_upload = cast(FileStorage, uploads_map["database"])

    code_name, code_data = _read_upload(code_upload)
    database_name, database_data = _read_upload(database_upload)

    if not code_data or not database_data:
        return make_response(error_response("上传的文件内容为空，请重新上传"), 400)

    build_instructions_raw = request.form.get("buildInstructions", "")
    notes = request.form.get("notes")

    LOGGER.info(
        "Assertion generation job requested",
        extra={
            "codeArchive": code_name,
            "database": database_name,
            "hasBuildInstructions": bool(build_instructions_raw.strip()),
            "notesLength": len(notes.strip()) if isinstance(notes, str) else 0,
        },
    )

    snapshot = submit_assert_generation_job(
        code_payload=(code_name, code_data),
        database_payload=(database_name, database_data),
        build_instructions=build_instructions_raw,
        notes=notes,
    )
    return make_response(success_response(snapshot), 202)

@bp.route("/assertion-generation/<job*id>/progress", methods=["GET"]) def assertion_generation_progress(job_id: str): *, error = \_ensure_authenticated() if error: return error

    snapshot = get_assert_generation_job(job_id)
    if not snapshot:
        return make_response(error_response("未找到断言生成任务"), 404)
    return make_response(success_response(snapshot), 200)

@bp.route("/assertion-generation/<job*id>/result", methods=["GET"]) def assertion_generation_result(job_id: str): *, error = \_ensure_authenticated() if error: return error

    result = get_assert_generation_result(job_id)
    if result is None:
        snapshot = get_assert_generation_job(job_id)
        if not snapshot:
            return make_response(error_response("未找到断言生成任务"), 404)
        status = snapshot.get("status")
        return make_response(
            error_response("断言生成任务尚未完成", {"status": status}),
            409,
        )
    return make_response(success_response(result), 200)

@bp.route("/assertion-generation/<job*id>/download", methods=["GET"]) def assertion_generation_download(job_id: str): *, error = \_ensure_authenticated() if error: return error

    snapshot = get_assert_generation_job(job_id)
    if not snapshot:
        return make_response(error_response("未找到断言生成任务"), 404)

    if snapshot.get("status") != "completed":
        return make_response(
            error_response("断言生成任务尚未完成", {"status": snapshot.get("status")}),
            409,
        )

    zip_path = get_assert_generation_zip_path(job_id)
    if not zip_path:
        return make_response(error_response("未找到断言生成结果压缩包"), 404)

    download_name = f"assertion-generation-{job_id}.zip"
    return send_file(
        zip_path,
        mimetype="application/zip",
        as_attachment=True,
        download_name=download_name,
        max_age=0,
    )

@bp.route("/assertion-generation/<job*id>/instrumentation-diff", methods=["GET"]) def assertion_generation_instrumentation_diff(job_id: str): """Fetch the instrumentation diff for a completed assertion generation job.""" *, error = \_ensure_authenticated() if error: return error

    result = get_assert_generation_result(job_id)
    if result is None:
        snapshot = get_assert_generation_job(job_id)
        if not snapshot:
            return make_response(error_response("未找到断言生成任务"), 404)
        status = snapshot.get("status")
        return make_response(
            error_response("断言生成任务尚未完成", {"status": status}),
            409,
        )

    # Extract instrumentation diff from result
    instrumentation = result.get("instrumentation")
    if not instrumentation or not isinstance(instrumentation, dict):
        return make_response(error_response("未找到 instrumentation 数据"), 404)

    artifacts = instrumentation.get("artifacts")
    if not artifacts or not isinstance(artifacts, dict):
        return make_response(error_response("未找到 instrumentation artifacts"), 404)

    diff_output = artifacts.get("diffOutput")
    if not diff_output or not isinstance(diff_output, dict):
        return make_response(error_response("未找到 instrumentation diff 输出"), 404)

    return make_response(success_response(diff_output), 200)

# Diff Parsing Routes -----------------------------------------------------------

@bp.route("/assertion-generation/<assert*job_id>/diff-parsing", methods=["POST"]) def start_diff_parsing(assert_job_id: str): """Start diff parsing for a completed assertion generation job.""" *, error = \_ensure_authenticated() if error: return error

    # Verify the parent assertion generation job exists
    assert_snapshot = get_assert_generation_job(assert_job_id)
    if not assert_snapshot:
        return make_response(error_response("未找到断言生成任务"), 404)

    if assert_snapshot.get("status") != "completed":
        return make_response(
            error_response(
                "断言生成任务尚未完成，无法开始差异解析",
                {"status": assert_snapshot.get("status")},
            ),
            409,
        )

    LOGGER.info(
        "Diff parsing job requested",
        extra={
            "parentJobId": assert_job_id,
        },
    )

    snapshot = submit_diff_parsing_job(assert_job_id)
    return make_response(success_response(snapshot), 202)

@bp.route( "/assertion-generation/<assert*job_id>/diff-parsing/<diff_job_id>/progress", methods=["GET"], ) def diff_parsing_progress(assert_job_id: str, diff_job_id: str): """Get progress of a diff parsing job.""" *, error = \_ensure_authenticated() if error: return error

    snapshot = get_diff_parsing_job(diff_job_id)
    if not snapshot:
        return make_response(error_response("未找到差异解析任务"), 404)

    # Verify the parent job ID matches
    if snapshot.get("parentJobId") != assert_job_id:
        return make_response(
            error_response("差异解析任务与指定的断言生成任务不匹配"),
            400,
        )

    return make_response(success_response(snapshot), 200)

@bp.route( "/assertion-generation/<assert*job_id>/diff-parsing/<diff_job_id>/result", methods=["GET"], ) def diff_parsing_result(assert_job_id: str, diff_job_id: str): """Get result of a completed diff parsing job.""" *, error = \_ensure_authenticated() if error: return error

    result = get_diff_parsing_result(diff_job_id)
    if result is None:
        snapshot = get_diff_parsing_job(diff_job_id)
        if not snapshot:
            return make_response(error_response("未找到差异解析任务"), 404)

        # Verify the parent job ID matches
        if snapshot.get("parentJobId") != assert_job_id:
            return make_response(
                error_response("差异解析任务与指定的断言生成任务不匹配"),
                400,
            )

        status = snapshot.get("status")
        return make_response(
            error_response("差异解析任务尚未完成", {"status": status}),
            409,
        )

    return make_response(success_response(result), 200)

def \_strip_extension(filename: str) -> str: if "." not in filename: return filename return filename.rsplit(".", 1)[0]

# Protocol Specific Routes -------------------------------------------------

# SOL配置 - ProtocolGuard配置

RTSP_CONFIG = { "script_path": None, # 不再需要脚本文件 "shell_command": "docker run -d --privileged -v /home/lab426_system/ProtocolGuardOutPut:/out/fuzz-output protocolguard:latest fuzz", # ProtocolGuard启动命令（使用-d后台运行，移除--rm和-it）"log_file_path": "/home/lab426_system/ProtocolGuardOutPut/plot_data" # ProtocolGuard日志文件路径 }

# MQTT协议配置 - MBFuzzer相关路径

MQTT_CONFIG = { "log_file_path": os.path.join(os.path.dirname(**file**), "mbfuzzer_logs", "fuzzing_report.txt"), # MBFuzzer日志文件路径 "shell_command": "echo 'MBFuzzer模拟运行 - 传统MQTT broker模糊测试'", # MBFuzzer启动命令（临时模拟）"output_dir": os.path.join(os.path.dirname(**file**), "mbfuzzer_logs") # MBFuzzer输出目录 }

# SNMP协议配置 - SNMP Fuzzer相关路径

SNMP_CONFIG = { "log_file_path": os.path.join(os.path.dirname(**file**), "snmpfuzzer_logs", "fuzz_output.txt"), # SNMP Fuzzer日志文件路径 "shell_command": "echo 'SNMP Fuzzer模拟运行'", # SNMP Fuzzer启动命令（临时模拟）"output_dir": os.path.join(os.path.dirname(**file**), "snmpfuzzer_logs") # SNMP Fuzzer输出目录 }

@bp.route("/write-script", methods=["POST"]) def write*script(): """写入脚本文件到指定路径""" *, error = \_ensure_authenticated() if error: return error

    data = request.get_json()
    if not data:
        return make_response(error_response("请求数据不能为空"), 400)

    content = data.get("content")
    protocol = data.get("protocol", "UNKNOWN")
    protocol_implementations = data.get("protocolImplementations", [])

    if not content:
        return make_response(error_response("脚本内容不能为空"), 400)

    # 根据协议获取配置
    if protocol == "RTSP":
        # SOL使用ProtocolGuard，不需要脚本文件，直接返回成功
        return success_response({
            "message": f"SOL不需要脚本文件，直接启动docker即可生成日志",
            "filePath": "N/A",
            "size": 0
        })
    elif protocol == "MQTT":
        # MQTT协议暂时不需要脚本文件，直接返回成功
        return success_response({
            "message": f"{protocol}协议不需要脚本文件",
            "filePath": "N/A",
            "size": 0
        })
    else:
        return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)

    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 写入文件（覆盖模式）
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 如果是shell脚本，设置执行权限
        if file_path.endswith('.sh'):
            os.chmod(file_path, 0o755)

        return success_response({
            "message": f"{protocol}脚本文件写入成功",
            "filePath": file_path,
            "size": len(content.encode('utf-8'))
        })

    except Exception as e:
        return make_response(error_response(f"写入文件失败: {str(e)}"), 500)

@bp.route("/execute-command", methods=["POST"]) def execute_command(): """执行shell命令启动程序""" print(f"[DEBUG] ========== execute-command API被调用 ==========")

    _, error = _ensure_authenticated()
    if error:
        print(f"[DEBUG] 认证失败: {error}")
        return error

    data = request.get_json()
    print(f"[DEBUG] 接收到的请求数据: {data}")

    if not data:
        print(f"[DEBUG] 请求数据为空")
        return make_response(error_response("请求数据不能为空"), 400)

    protocol = data.get("protocol", "UNKNOWN")
    protocol_implementations = data.get("protocolImplementations", [])

    print(f"[DEBUG] 解析参数 - 协议: {protocol}, 实现: {protocol_implementations}")

    # 根据协议获取配置
    if protocol == "MQTT":
        # MQTT协议支持双引擎配置
        if protocol_implementations and "SOL" in protocol_implementations:
            # SOL使用AFLNET引擎 (原RTSP配置)
            command = RTSP_CONFIG["shell_command"]
            print(f"[DEBUG] MQTT协议使用SOL实现(AFLNET引擎): {protocol_implementations}")
        else:
            # 传统MQTT broker使用MBFuzzer引擎
            command = MQTT_CONFIG["shell_command"]
            print(f"[DEBUG] MQTT协议使用传统broker实现(MBFuzzer引擎): {protocol_implementations}")
            # 这里可以根据选择的broker实现来调整MBFuzzer的配置
            # 例如：为不同的broker设置不同的测试参数
            if protocol_implementations:
                implementations_str = ",".join(protocol_implementations)
                # 可以将实现信息传递给MBFuzzer作为参数
                command = f"{command} --brokers={implementations_str}"
    elif protocol == "SNMP":
        command = SNMP_CONFIG["shell_command"]
        # SNMP协议实现信息记录到日志
        if protocol_implementations:
            print(f"[DEBUG] SNMP协议实现: {protocol_implementations}")
    else:
        return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)

    try:
        print(f"[DEBUG] 执行命令: {command}")  # 调试日志

        # 对于SOL的ProtocolGuard，使用后台运行方式
        # 检查是否是SOL实现（MQTT协议 + SOL实现 或者 原RTSP协议）
        is_sol_protocol = (protocol == "RTSP") or (protocol == "MQTT" and protocol_implementations and "SOL" in protocol_implementations)

        if is_sol_protocol:
            # ProtocolGuard需要在后台运行，因为它是长时间运行的fuzzing任务
            # 直接执行docker命令并获取容器ID
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30  # 30秒超时
                )

                if result.returncode == 0:
                    container_id = result.stdout.strip()
                    if container_id and len(container_id) >= 12:  # Docker容器ID至少12位
                        protocol_name = "SOL" if protocol == "MQTT" else protocol
                        print(f"[DEBUG] {protocol_name} ProtocolGuard启动成功，容器ID: {container_id}")

                        # 验证容器是否真的在运行
                        import time
                        time.sleep(2)
                        check_result = subprocess.run(
                            f"docker ps -q --filter id={container_id}",
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )

                        if check_result.returncode == 0 and check_result.stdout.strip():
                            response_data = {
                                "message": f"{protocol_name} ProtocolGuard启动成功，正在后台运行fuzzing任务",
                                "command": command,
                                "pid": None,  # Docker容器没有直接的PID
                                "container_id": container_id
                            }
                            print(f"[DEBUG] 返回成功响应: {response_data}")
                            return success_response(response_data)
                        else:
                            return make_response(error_response(f"容器启动后立即停止，请检查Docker镜像和配置"), 500)
                    else:
                        error_msg = result.stderr.strip() if result.stderr.strip() else "无法获取有效的容器ID"
                        print(f"[DEBUG] ProtocolGuard启动失败: {error_msg}")
                        return make_response(error_response(f"ProtocolGuard启动失败: {error_msg}"), 500)
                else:
                    error_msg = result.stderr.strip() if result.stderr.strip() else "Docker命令执行失败"
                    print(f"[DEBUG] ProtocolGuard启动失败: {error_msg}")
                    return make_response(error_response(f"ProtocolGuard启动失败: {error_msg}"), 500)

            except subprocess.TimeoutExpired:
                return make_response(error_response("Docker容器启动超时"), 500)
            except Exception as e:
                print(f"[DEBUG] ProtocolGuard启动异常: {str(e)}")
                return make_response(error_response(f"ProtocolGuard启动异常: {str(e)}"), 500)
        else:
            # 其他协议使用原来的方式
            result = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30  # 30秒超时
            )

            print(f"[DEBUG] 命令返回码: {result.returncode}")  # 调试日志

            if result.returncode == 0:
                # 命令执行成功
                print(f"[DEBUG] 命令执行成功")
                print(f"[DEBUG] stdout: {result.stdout}")

                # 对于docker run -d，成功的话stdout通常包含容器ID
                container_id = result.stdout.strip() if result.stdout.strip() else "unknown"

                return success_response({
                    "message": f"{protocol}命令执行成功",
                    "command": command,
                    "container_id": container_id,
                    "pid": "docker_container"  # Docker容器没有传统意义的PID
                })
            else:
                # 命令执行失败
                error_msg = result.stderr.strip() if result.stderr.strip() else "未知错误"
                print(f"[DEBUG] 命令执行失败: {error_msg}")
                return make_response(error_response(f"命令执行失败: {error_msg}"), 500)

    except subprocess.TimeoutExpired:
        print(f"[DEBUG] 命令执行超时")
        return make_response(error_response("命令执行超时"), 500)
    except Exception as e:
        print(f"[DEBUG] 异常: {str(e)}")  # 调试日志
        return make_response(error_response(f"执行命令失败: {str(e)}"), 500)

@bp.route("/read-log", methods=["POST"]) def read*log(): """实时读取日志文件内容""" *, error = \_ensure_authenticated() if error: return error

    data = request.get_json()
    if not data:
        return make_response(error_response("请求数据不能为空"), 400)

    protocol = data.get("protocol", "UNKNOWN")
    last_position = data.get("lastPosition", 0)

    # 根据协议获取配置
    protocol_implementations = data.get("protocolImplementations", [])

    if protocol == "MQTT":
        # MQTT协议支持双引擎配置
        if protocol_implementations and "SOL" in protocol_implementations:
            # SOL使用AFLNET引擎日志路径 (原RTSP配置)
            file_path = RTSP_CONFIG["log_file_path"]
            print(f"[DEBUG] MQTT协议使用SOL实现，读取AFLNET日志: {file_path}")
        else:
            # 传统MQTT broker使用MBFuzzer引擎日志路径
            file_path = MQTT_CONFIG["log_file_path"]
            print(f"[DEBUG] MQTT协议使用传统broker实现，读取MBFuzzer日志: {file_path}")
    elif protocol == "SNMP":
        file_path = SNMP_CONFIG["log_file_path"]
    else:
        return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)

    try:
        print(f"[DEBUG] 尝试读取{protocol}日志文件: {file_path}")
        print(f"[DEBUG] 上次读取位置: {last_position}")

        # 检查目录是否存在
        log_dir = os.path.dirname(file_path)
        if not os.path.exists(log_dir):
            print(f"[DEBUG] 日志目录不存在: {log_dir}")
            return success_response({
                "content": "",
                "position": last_position,
                "message": f"日志目录不存在: {log_dir}"
            })

        # 列出目录中的文件
        try:
            files_in_dir = os.listdir(log_dir)
            print(f"[DEBUG] 日志目录中的文件: {files_in_dir}")
        except Exception as e:
            print(f"[DEBUG] 无法列出目录文件: {e}")

        if not os.path.exists(file_path):
            print(f"[DEBUG] 日志文件不存在: {file_path}")
            return success_response({
                "content": "",
                "position": last_position,
                "message": f"日志文件尚未创建: {file_path}"
            })

        # 获取文件信息
        file_stat = os.stat(file_path)
        file_size = file_stat.st_size
        print(f"[DEBUG] 日志文件大小: {file_size} 字节")

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # 移动到上次读取的位置
            f.seek(last_position)

            # 读取新内容
            new_content = f.read()

            # 获取当前位置
            current_position = f.tell()

        print(f"[DEBUG] 读取到新内容长度: {len(new_content)} 字符")
        print(f"[DEBUG] 新的读取位置: {current_position}")

        if new_content:
            print(f"[DEBUG] 新内容预览: {new_content[:200]}...")

        return success_response({
            "content": new_content,
            "position": current_position,
            "protocol": protocol,
            "file_size": file_size,
            "message": f"成功读取{len(new_content)}字符，文件大小{file_size}字节"
        })

    except Exception as e:
        print(f"[DEBUG] 读取日志文件异常: {e}")
        return make_response(error_response(f"读取日志文件失败: {str(e)}"), 500)

@bp.route("/check-status", methods=["POST"]) def check*status(): """检查协议测试状态和文件系统""" *, error = \_ensure_authenticated() if error: return error

    data = request.get_json()
    if not data:
        return make_response(error_response("请求数据不能为空"), 400)

    protocol = data.get("protocol", "UNKNOWN")

    try:
        status_info = {
            "protocol": protocol,
            "timestamp": datetime.now().isoformat()
        }

        if protocol == "MQTT":
            # MQTT协议支持双引擎配置，需要检查协议实现
            protocol_implementations = data.get("protocolImplementations", [])

            if protocol_implementations and "SOL" in protocol_implementations:
                # 检查SOL相关状态 (使用AFLNET引擎)
                log_file_path = RTSP_CONFIG["log_file_path"]
                status_info["engine"] = "AFLNET"
                status_info["implementation"] = "SOL"
            else:
                # 检查传统MQTT broker状态 (使用MBFuzzer引擎)
                log_file_path = MQTT_CONFIG["log_file_path"]
                status_info["engine"] = "MBFuzzer"
                status_info["implementation"] = protocol_implementations

            log_dir = os.path.dirname(log_file_path)

            # 检查目录和文件状态
            status_info.update({
                "log_file_path": log_file_path,
                "log_dir": log_dir,
                "log_dir_exists": os.path.exists(log_dir),
                "log_file_exists": os.path.exists(log_file_path)
            })

            # 如果目录存在，列出文件
            if os.path.exists(log_dir):
                try:
                    files = os.listdir(log_dir)
                    status_info["files_in_log_dir"] = files
                except Exception as e:
                    status_info["files_in_log_dir"] = f"无法列出文件: {e}"

            # 如果日志文件存在，获取文件信息
            if os.path.exists(log_file_path):
                file_stat = os.stat(log_file_path)
                status_info.update({
                    "log_file_size": file_stat.st_size,
                    "log_file_mtime": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                })

            # 检查Docker容器状态
            try:
                result = subprocess.run(
                    "docker ps --format 'table {{.ID}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    status_info["docker_containers"] = result.stdout
                else:
                    status_info["docker_error"] = result.stderr

            except Exception as e:
                status_info["docker_error"] = str(e)

        print(f"[DEBUG] 状态检查结果: {status_info}")

        return success_response(status_info)

    except Exception as e:
        print(f"[DEBUG] 状态检查异常: {e}")
        return make_response(error_response(f"状态检查失败: {str(e)}"), 500)

@bp.route("/stop-process", methods=["POST"]) def stop*process(): """停止指定进程""" *, error = \_ensure_authenticated() if error: return error

    data = request.get_json()
    if not data:
        return make_response(error_response("请求数据不能为空"), 400)

    pid = data.get("pid")
    protocol = data.get("protocol", "UNKNOWN")

    if not pid:
        return make_response(error_response("进程ID不能为空"), 400)

    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=True)
        else:  # Unix/Linux
            os.killpg(os.getpgid(pid), 9)

        return success_response({
            "message": f"{protocol}进程停止成功",
            "pid": pid
        })

    except subprocess.CalledProcessError:
        return make_response(error_response(f"进程 {pid} 不存在或已停止"), 404)
    except Exception as e:
        return make_response(error_response(f"停止进程失败: {str(e)}"), 500)

@bp.route("/pre-start-cleanup", methods=["POST"]) def pre_start_cleanup(): """启动前清理：停止现有容器并清理输出文件""" print(f"[DEBUG] ========== 启动前清理API被调用 ==========")

    _, error = _ensure_authenticated()
    if error:
        print(f"[DEBUG] 认证失败: {error}")
        return error

    data = request.get_json()
    print(f"[DEBUG] 接收到的请求数据: {data}")

    if not data:
        print(f"[DEBUG] 请求数据为空")
        return make_response(error_response("请求数据不能为空"), 400)

    protocol = data.get("protocol", "UNKNOWN")

    print(f"[DEBUG] 解析参数 - 协议: {protocol}")

    cleanup_results = {
        "containers_stopped": 0,
        "containers_removed": 0,
        "output_cleaned": False,
        "errors": []
    }

    try:
        print(f"[DEBUG] 开始启动前清理 - 协议: {protocol}")

        # 1. 查找并停止所有相关的Docker容器
        if protocol == "RTSP" or protocol == "MQTT":
            # 查找protocolguard容器
            find_result = subprocess.run(
                "docker ps -q --filter ancestor=protocolguard:latest",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if find_result.returncode == 0 and find_result.stdout.strip():
                container_ids = find_result.stdout.strip().split('\n')
                print(f"[DEBUG] 找到 {len(container_ids)} 个运行中的protocolguard容器")

                for container_id in container_ids:
                    if container_id:
                        try:
                            # 停止容器
                            stop_result = subprocess.run(
                                f"docker stop {container_id}",
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                timeout=30
                            )

                            if stop_result.returncode == 0:
                                cleanup_results["containers_stopped"] += 1
                                print(f"[DEBUG] 容器停止成功: {container_id}")

                                # 删除容器
                                remove_result = subprocess.run(
                                    f"docker rm {container_id}",
                                    shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    timeout=30
                                )

                                if remove_result.returncode == 0:
                                    cleanup_results["containers_removed"] += 1
                                    print(f"[DEBUG] 容器删除成功: {container_id}")
                                else:
                                    error_msg = remove_result.stderr.strip() or "删除容器失败"
                                    cleanup_results["errors"].append(f"删除容器失败 {container_id}: {error_msg}")
                            else:
                                error_msg = stop_result.stderr.strip() or "停止容器失败"
                                cleanup_results["errors"].append(f"停止容器失败 {container_id}: {error_msg}")

                        except subprocess.TimeoutExpired:
                            cleanup_results["errors"].append(f"操作容器超时: {container_id}")
                        except Exception as e:
                            cleanup_results["errors"].append(f"操作容器异常 {container_id}: {str(e)}")
            else:
                print(f"[DEBUG] 没有找到运行中的protocolguard容器")

        # 2. 清理输出文件夹
        if protocol == "RTSP" or protocol == "MQTT":
            output_dir = os.path.dirname(RTSP_CONFIG["log_file_path"])

            # Linux安全检查：防止删除系统重要目录
            dangerous_paths = ['/', '/home', '/usr', '/var', '/etc', '/bin', '/sbin', '/lib', '/opt']
            if output_dir in dangerous_paths or len(output_dir.strip()) < 5:
                cleanup_results["errors"].append(f"拒绝清理危险路径: {output_dir}")
                print(f"[DEBUG] 安全检查失败，拒绝清理: {output_dir}")
            else:
                try:
                    if os.path.exists(output_dir):
                        import shutil

                        # 删除output目录下的所有文件和子目录，但保留目录本身
                        cleaned_items = []
                        failed_items = []

                        for item in os.listdir(output_dir):
                            item_path = os.path.join(output_dir, item)
                            try:
                                if os.path.isdir(item_path):
                                    shutil.rmtree(item_path)
                                else:
                                    os.remove(item_path)
                                cleaned_items.append(item)
                            except Exception as e:
                                failed_items.append(f"{item}: {str(e)}")

                        if cleaned_items:
                            cleanup_results["output_cleaned"] = True
                            print(f"[DEBUG] 输出目录清理成功，删除了 {len(cleaned_items)} 个项目")

                        if failed_items:
                            cleanup_results["errors"].extend([f"清理失败: {item}" for item in failed_items])
                    else:
                        print(f"[DEBUG] 输出目录不存在: {output_dir}")
                        cleanup_results["output_cleaned"] = True  # 目录不存在也算清理成功

                except Exception as e:
                    cleanup_results["errors"].append(f"清理输出目录异常: {str(e)}")
                    print(f"[DEBUG] 清理输出目录异常: {e}")

        print(f"[DEBUG] 启动前清理完成: {cleanup_results}")

        return success_response({
            "message": f"启动前清理完成",
            "cleanup_results": cleanup_results
        })

    except Exception as e:
        print(f"[DEBUG] 启动前清理异常: {e}")
        cleanup_results["errors"].append(f"清理过程异常: {str(e)}")

        return success_response({
            "message": f"启动前清理部分完成",
            "cleanup_results": cleanup_results
        })

@bp.route("/stop-and-cleanup", methods=["POST"]) def stop_and_cleanup(): """停止Docker容器并清理输出文件""" print(f"[DEBUG] ========== 停止和清理API被调用 ==========")

    _, error = _ensure_authenticated()
    if error:
        print(f"[DEBUG] 认证失败: {error}")
        return error

    data = request.get_json()
    print(f"[DEBUG] 接收到的请求数据: {data}")

    if not data:
        print(f"[DEBUG] 请求数据为空")
        return make_response(error_response("请求数据不能为空"), 400)

    container_id = data.get("container_id")
    protocol = data.get("protocol", "UNKNOWN")

    print(f"[DEBUG] 解析参数 - 容器ID: {container_id}, 协议: {protocol}")

    if not container_id:
        print(f"[DEBUG] 容器ID为空")
        return make_response(error_response("容器ID不能为空"), 400)

    stop_results = {
        "container_stopped": False,
        "container_removed": False,
        "errors": []
    }

    try:
        print(f"[DEBUG] 开始停止和清理{protocol}容器: {container_id}")

        # 首先检查容器是否存在
        check_result = subprocess.run(
            f"docker ps -a -q --filter id={container_id}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if check_result.returncode == 0 and check_result.stdout.strip():
            print(f"[DEBUG] 找到容器: {check_result.stdout.strip()}")
        else:
            print(f"[DEBUG] 容器不存在或查找失败: {check_result.stderr}")
            stop_results["errors"].append(f"容器不存在: {container_id}")

        # 检查容器是否正在运行
        running_check = subprocess.run(
            f"docker ps -q --filter id={container_id}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if running_check.returncode == 0 and running_check.stdout.strip():
            print(f"[DEBUG] 容器正在运行，需要停止: {running_check.stdout.strip()}")
        else:
            print(f"[DEBUG] 容器未在运行或已停止")

        # 1. 停止Docker容器（使用更短的超时时间）
        try:
            stop_result = subprocess.run(
                f"docker stop -t 10 {container_id}",  # 给容器10秒时间优雅停止
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15  # 总超时时间15秒
            )

            if stop_result.returncode == 0:
                stop_results["container_stopped"] = True
                print(f"[DEBUG] 容器停止成功: {container_id}")
            else:
                error_msg = stop_result.stderr.strip() or "停止容器失败"
                stop_results["errors"].append(f"停止容器失败: {error_msg}")
                print(f"[DEBUG] 停止容器失败: {error_msg}")

        except subprocess.TimeoutExpired:
            stop_results["errors"].append("停止容器超时")
            print(f"[DEBUG] 停止容器超时")
        except Exception as e:
            stop_results["errors"].append(f"停止容器异常: {str(e)}")
            print(f"[DEBUG] 停止容器异常: {e}")

        # 2. 删除Docker容器
        try:
            remove_result = subprocess.run(
                f"docker rm -f {container_id}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10  # 删除操作通常很快
            )

            if remove_result.returncode == 0:
                stop_results["container_removed"] = True
                print(f"[DEBUG] 容器删除成功: {container_id}")
            else:
                error_msg = remove_result.stderr.strip() or "删除容器失败"
                stop_results["errors"].append(f"删除容器失败: {error_msg}")
                print(f"[DEBUG] 删除容器失败: {error_msg}")

        except subprocess.TimeoutExpired:
            stop_results["errors"].append("删除容器超时")
            print(f"[DEBUG] 删除容器超时")
        except Exception as e:
            stop_results["errors"].append(f"删除容器异常: {str(e)}")
            print(f"[DEBUG] 删除容器异常: {e}")

        print(f"[DEBUG] 容器停止完成: {stop_results}")

        # 构建响应消息
        success_count = sum([
            stop_results["container_stopped"],
            stop_results["container_removed"]
        ])

        if success_count == 2:
            message = f"{protocol}容器已完全停止，输出文件已保留供查看"
        elif success_count > 0:
            message = f"{protocol}容器部分停止完成 ({success_count}/2)，输出文件已保留"
        else:
            message = f"{protocol}容器停止失败"

        return success_response({
            "message": message,
            "container_id": container_id,
            "protocol": protocol,
            "stop_results": stop_results
        })

    except Exception as e:
        print(f"[DEBUG] 停止过程异常: {e}")
        stop_results["errors"].append(f"停止过程异常: {str(e)}")

        return success_response({
            "message": f"{protocol}容器停止部分完成",
            "container_id": container_id,
            "protocol": protocol,
            "stop_results": stop_results
        })

# Detection Results Routes ------------------------------------------------------

@bp.route("/detection-results/<implementation*name>", methods=["GET"]) def get_detection_results(implementation_name: str): """获取指定协议实现的检测结果""" *, error = \_ensure_authenticated() if error: return error

    # 数据库文件路径
    db_path = os.path.join(
        os.path.dirname(__file__),
        "databases",
        f"sqlite_{implementation_name}.db"
    )

    # 检查文件是否存在
    if not os.path.exists(db_path):
        return make_response(
            error_response(f"未找到协议实现 '{implementation_name}' 的数据库文件"),
            404
        )

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 从 rule_code_snippet 表读取数据
        cursor.execute("""
            SELECT rule_desc, code_snippet, llm_response
            FROM rule_code_snippet
        """)

        rows = cursor.fetchall()
        items = []

        for idx, row in enumerate(rows):
            # 解析 JSON 格式的 llm_response
            llm_response = {}
            if row['llm_response']:
                try:
                    llm_response = json.loads(row['llm_response'])
                except json.JSONDecodeError:
                    llm_response = {'result': 'error', 'reason': '解析失败'}

            items.append({
                'id': idx + 1,  # 使用索引作为 id
                'rule_desc': row['rule_desc'],
                'code_snippet': row['code_snippet'],
                'llm_response': llm_response
            })

        conn.close()
        return success_response({'items': items})

    except sqlite3.Error as e:
        return make_response(
            error_response(f"数据库读取错误: {str(e)}"),
            500
        )

@bp.route("/available-implementations", methods=["GET"]) def list*available_implementations(): """获取所有可用的协议实现列表""" *, error = \_ensure_authenticated() if error: return error

    db_dir = os.path.join(os.path.dirname(__file__), "databases")

    if not os.path.exists(db_dir):
        return success_response({'items': []})

    # 扫描目录中的所有 .db 文件
    implementations = []
    for filename in os.listdir(db_dir):
        if filename.startswith("sqlite_") and filename.endswith(".db"):
            # 提取实现名称（去掉 sqlite_ 前缀和 .db 后缀）
            impl_name = filename[7:-3]
            implementations.append(impl_name)

    return success_response({'items': implementations})

@bp.route("/analysis-history", methods=["GET"]) def get*analysis_history(): """获取历史记录""" *, error = \_ensure_authenticated() if error: return error

    history_file = os.path.join(os.path.dirname(__file__), "query_history.json")

    if not os.path.exists(history_file):
        return success_response({'items': []})

    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        return success_response({'items': history})
    except (json.JSONDecodeError, IOError) as e:
        return make_response(
            error_response(f"读取历史记录失败: {str(e)}"),
            500
        )

@bp.route("/analysis-history", methods=["POST"]) def add*analysis_history(): """添加历史记录""" *, error = \_ensure_authenticated() if error: return error

    data = request.get_json()
    implementation_name = data.get('implementationName')
    protocol_name = data.get('protocolName')

    if not implementation_name or not protocol_name:
        return make_response(
            error_response("缺少必要参数"),
            400
        )

    # 读取数据库统计信息
    db_path = os.path.join(
        os.path.dirname(__file__),
        "databases",
        f"sqlite_{implementation_name}.db"
    )

    statistics = {'total': 0, 'violations': 0, 'noViolations': 0, 'noResult': 0}

    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 从 rule_code_snippet 表读取
            cursor.execute("SELECT llm_response FROM rule_code_snippet")
            rows = cursor.fetchall()

            statistics['total'] = len(rows)
            for row in rows:
                if row[0]:
                    try:
                        response = json.loads(row[0])
                        result = response.get('result', '').lower()
                        if 'no violation' in result:
                            statistics['noViolations'] += 1
                        elif 'violation' in result:
                            statistics['violations'] += 1
                        else:
                            statistics['noResult'] += 1
                    except json.JSONDecodeError:
                        statistics['noResult'] += 1

            conn.close()
        except sqlite3.Error:
            pass

    # 保存历史记录
    history_file = os.path.join(os.path.dirname(__file__), "query_history.json")
    history = []

    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = []

    history.insert(0, {
        'id': str(uuid.uuid4()),
        'implementationName': implementation_name,
        'protocolName': protocol_name,
        'statistics': statistics,
        'createdAt': datetime.now().isoformat()
    })

    # 只保留最近 50 条记录
    history = history[:50]

    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except IOError as e:
        return make_response(
            error_response(f"保存历史记录失败: {str(e)}"),
            500
        )

    return success_response({'message': '已添加到历史记录'})

==================================================================================================== 文件 18: apps/backend-flask/protocol_compliance/pipeline_runner.py ====================================================================================================

"""Utilities for invoking the stand-alone protocol extraction pipeline."""

from **future** import annotations

import contextlib import json import re import subprocess import sys import uuid from dataclasses import dataclass from pathlib import Path from typing import TYPE_CHECKING, Any, Iterable, Sequence

if TYPE_CHECKING: # 仅在类型检查时导入 from werkzeug.datastructures import FileStorage # type: ignore[import] else: # pragma: no cover - 运行时用宽松类型，避免依赖缺失 FileStorage = Any # type: ignore[assignment]

class PipelineExecutionError(RuntimeError): """Raised when the protocol pipeline exits with a non-zero status."""

    def __init__(self, message: str, *, stdout: str | None = None, stderr: str | None = None):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr

class PipelineResultNotFoundError(RuntimeError): """Raised when the pipeline finishes but the expected result file is missing."""

REPO_ROOT = Path(**file**).resolve().parents[3] PIPELINE_ROOT = (REPO_ROOT / "protocolProject-1").resolve() STORAGE_ROOT = PIPELINE_ROOT / "project_store" UPLOAD_ROOT = PIPELINE_ROOT / "uploads"

UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

@dataclass(slots=True) class PipelineRuleItem: rule: str req_type: list[str] req_fields: list[str] res_type: list[str] res_fields: list[str] group: str | None = None

@dataclass(slots=True) class PipelineResult: protocol: str version: str store_dir: Path result_path: Path rules: list[PipelineRuleItem]

\_TOKEN_SPLIT_RE = re.compile(r"\s*(?:,|;|/|\bor\b|\band\b)\s*", re.IGNORECASE)

def \_ensure_pipeline_root() -> None: if not PIPELINE_ROOT.exists(): raise FileNotFoundError(f"pipeline root does not exist: {PIPELINE_ROOT}")

def _sanitize_segment(value: str, fallback: str) -> str: stripped = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()) stripped = stripped.strip("-") return stripped or fallback

def \_save_upload(upload: FileStorage) -> Path: filename = upload.filename or "protocol-document.html" suffix = Path(filename).suffix or ".html" token = uuid.uuid4().hex safe_name = \_sanitize_segment(Path(filename).stem, "protocol") target = UPLOAD_ROOT / f"{safe_name}-{token}{suffix}" upload.save(target) return target

def \_normalize_list(values: Iterable[str]) -> list[str]: normalized: list[str] = [] for value in values: stripped = value.strip() if not stripped: continue normalized.append(stripped) return normalized

def \_ensure_list(payload: object) -> list[str]: if payload is None: return [] if isinstance(payload, list): return \_normalize_list(str(item) for item in payload if item is not None) if isinstance(payload, str): if not payload.strip(): return [] tokens = [segment for segment in _TOKEN_SPLIT_RE.split(payload) if segment] return \_normalize_list(tokens) or [payload.strip()] return []

def \_load_rules(result_path: Path) -> list[PipelineRuleItem]: try: payload = json.loads(result_path.read_text(encoding="utf-8")) except json.JSONDecodeError as exc: raise PipelineResultNotFoundError( f"无法解析规则文件 {result_path}: {exc}" ) from exc

    records: Sequence[dict] | dict
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        # Some pipelines produce a mapping of group -> list
        items: list[dict] = []
        for group_name, group_rules in payload.items():
            if not isinstance(group_rules, list):
                continue
            for rule in group_rules:
                if isinstance(rule, dict):
                    rule = {**rule, "group": group_name}
                    items.append(rule)
        records = items
    else:
        raise PipelineResultNotFoundError(f"规则文件格式不受支持: {type(payload)!r}")

    rule_items: list[PipelineRuleItem] = []
    for entry in records:
        if not isinstance(entry, dict):
            continue
        rule_text = str(entry.get("rule") or "").strip()
        if not rule_text:
            continue
        item = PipelineRuleItem(
            rule=rule_text,
            req_type=_ensure_list(entry.get("req_type")),
            req_fields=_ensure_list(entry.get("req_fields")),
            res_type=_ensure_list(entry.get("res_type")),
            res_fields=_ensure_list(entry.get("res_fields")),
            group=str(entry.get("group")).strip() if entry.get("group") else None,
        )
        rule_items.append(item)
    return rule_items

def _resolve_result_path(protocol: str, version: str) -> tuple[Path, Path]: normalized_protocol = protocol.lower().strip() normalized_version = version.replace(".", "_").replace(" ", "_").strip() store_dir = STORAGE_ROOT / f"{normalized_protocol}_{normalized_version}" if not store_dir.exists(): raise PipelineResultNotFoundError(f"未找到存储目录: {store_dir}")

    candidates = [
        store_dir / "ruleDir" / "processed_results.json",
        store_dir / "processed_results.json",
    ]

    # Include pattern-based fallbacks (processed_results*.json)
    candidates.extend(sorted(store_dir.glob("ruleDir/processed_results*.json"), reverse=True))
    candidates.extend(sorted(store_dir.glob("processed_results*.json"), reverse=True))

    for candidate in candidates:
        if candidate.is_file():
            return store_dir, candidate

    raise PipelineResultNotFoundError(f"未在 {store_dir} 中找到 processed_results.json 文件")

def \_build_command( api_key: str, protocol: str, version: str, html_path: Path, \*, filter_headings: bool, ) -> list[str]: command = [ sys.executable, "main.py", "--apikey", api_key, "--protocol", protocol, "--version", version, "--html-file", str(html_path), ] if filter_headings: command.append("--filter_headings") return command

def run_protocol_pipeline( \*, api_key: str, protocol: str, version: str, html_upload: FileStorage, filter_headings: bool = False, ) -> PipelineResult: """Execute the protocol extraction pipeline and load its results."""

    _ensure_pipeline_root()

    protocol = protocol.strip()
    version = version.strip()
    if not protocol:
        raise ValueError("protocol 不能为空")
    if not version:
        raise ValueError("version 不能为空")
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("API 密钥不能为空")

    saved_path = _save_upload(html_upload)

    command = _build_command(
        api_key,
        protocol,
        version,
        saved_path,
        filter_headings=filter_headings,
    )

    try:
        subprocess.run(
            command,
            cwd=str(PIPELINE_ROOT),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - interactive error handling
        raise PipelineExecutionError(
            "协议分析流程执行失败",
            stdout=exc.stdout,
            stderr=exc.stderr,
        ) from exc
    finally:
        # 删除临时文件，忽略失败
        with contextlib.suppress(Exception):
            saved_path.unlink()

    # 解析结果
    store_dir, result_path = _resolve_result_path(protocol, version)
    rules = _load_rules(result_path)

    return PipelineResult(
        protocol=protocol,
        version=version,
        store_dir=store_dir,
        result_path=result_path,
        rules=rules,
    )

def \_ensure_pipeline_dependencies() -> None: """Placeholder to keep backwards compatibility; dependencies需手动安装。""" return

==================================================================================================== 文件 19: apps/backend-flask/protocol_compliance/analysis.py ====================================================================================================

"""Static analysis helpers and ProtocolGuard Docker integration."""

from **future** import annotations

import logging import random import threading import uuid from dataclasses import dataclass, field from datetime import datetime, timezone from functools import lru_cache from io import BytesIO from typing import BinaryIO, Callable, Dict, List, Literal, Optional

from .docker_runner import ( ProtocolGuardDockerError, ProtocolGuardDockerRunner, ProtocolGuardDockerSettings, ProtocolGuardExecutionError, ProtocolGuardNotAvailableError, ) from .state_repository import analysis_state_repository

LOGGER = logging.getLogger(**name**)

ComplianceStatus = str # 'compliant' | 'needs_review' | 'non_compliant'

def \_now_iso() -> str: return datetime.now(timezone.utc).isoformat()

AnalysisJobStatus = Literal["queued", "running", "completed", "failed"]

@dataclass class AnalysisProgressEvent: timestamp: str stage: str message: str event_id: Optional[int] = None # Event ID from database, None for in-memory events

@dataclass class AnalysisProgressState: job_id: str status: AnalysisJobStatus stage: str message: str created_at: str updated_at: str events: List[AnalysisProgressEvent] = field(default_factory=list) result: Optional[Dict[str, object]] = None error: Optional[str] = None details: Optional[Dict[str, object]] = None

class AnalysisProgressRegistry: """Track live progress for static analysis jobs."""

    def __init__(self) -> None:
        self._states: Dict[str, AnalysisProgressState] = {}
        self._lock = threading.Lock()
        self._repository = analysis_state_repository

    def create_job(self) -> AnalysisProgressState:
        job_id = str(uuid.uuid4())
        now = _now_iso()
        state = AnalysisProgressState(
            job_id=job_id,
            status="queued",
            stage="queued",
            message="Job queued",
            created_at=now,
            updated_at=now,
        )
        state.events.append(AnalysisProgressEvent(timestamp=now, stage="queued", message="Job queued"))
        with self._lock:
            self._states[job_id] = state
        self._repository.record_progress(
            job_id=job_id,
            status=state.status,
            stage=state.stage,
            message=state.message,
            created_at=now,
            updated_at=now,
        )
        self._repository.add_event(job_id=job_id, timestamp=now, stage="queued", message="Job queued")
        return state

    def mark_running(self, job_id: str, stage: str, message: str) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "running"
            self._append_event(state, stage, message)

    def append_event(self, job_id: str, stage: str, message: str) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            self._append_event(state, stage, message)

    def complete(self, job_id: str, result: Dict[str, object]) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "completed"
            state.result = result
            self._append_event(state, "completed", "Static analysis completed successfully")
            self._repository.record_completion(
                job_id=state.job_id,
                status=state.status,
                stage=state.stage,
                message=state.message,
                updated_at=state.updated_at,
                result=result,
            )

    def fail(
        self,
        job_id: str,
        stage: str,
        message: str,
        *,
        error: Optional[str] = None,
        details: Optional[Dict[str, object]] = None,
    ) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "failed"
            state.error = error or message
            state.details = details
            self._append_event(state, stage, message)
            self._repository.record_failure(
                job_id=state.job_id,
                status=state.status,
                stage=state.stage,
                message=state.message,
                updated_at=state.updated_at,
                error=state.error,
                details=state.details,
            )

    def snapshot(
        self,
        job_id: str,
        from_event_id: Optional[int] = None,
    ) -> Optional[Dict[str, object]]:
        """
        Return snapshot of job state with incremental events.

        Always fetches events from database (which have IDs).
        If from_event_id is provided, only return events after that ID.
        If from_event_id is None, return all events from database.
        """
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return None
            state_copy = AnalysisProgressState(
                job_id=state.job_id,
                status=state.status,
                stage=state.stage,
                message=state.message,
                created_at=state.created_at,
                updated_at=state.updated_at,
                events=list(state.events),
                result=state.result,
                error=state.error,
                details=state.details.copy() if state.details else None,
            )

        # Always fetch events from database (they have IDs)
        db_events = self._repository.fetch_events(
            job_id=job_id,
            from_event_id=from_event_id,
        )
        events_list = [
            {
                "id": event["id"],
                "timestamp": event["timestamp"],
                "stage": event["stage"],
                "message": event["message"],
            }
            for event in db_events
        ]

        return {
            "jobId": state_copy.job_id,
            "status": state_copy.status,
            "stage": state_copy.stage,
            "message": state_copy.message,
            "createdAt": state_copy.created_at,
            "updatedAt": state_copy.updated_at,
            "events": events_list,
            "result": state_copy.result,
            "error": state_copy.error,
            "details": state_copy.details,
        }

    def _append_event(self, state: AnalysisProgressState, stage: str, message: str) -> None:
        timestamp = _now_iso()
        state.stage = stage
        state.message = message
        state.updated_at = timestamp
        state.events.append(AnalysisProgressEvent(timestamp=timestamp, stage=stage, message=message))
        self._repository.record_progress(
            job_id=state.job_id,
            status=state.status,
            stage=state.stage,
            message=state.message,
            updated_at=timestamp,
        )
        self._repository.add_event(job_id=state.job_id, timestamp=timestamp, stage=stage, message=message)

    def make_callback(self, job_id: str) -> Callable[[str, str, str], None]:
        def callback(_job_id: str, stage: str, message: str) -> None:
            # Ignore mismatched job ids to keep callback tolerant.
            target_id = job_id or _job_id
            self.append_event(target_id, stage, message)

        return callback

PROGRESS_REGISTRY = AnalysisProgressRegistry()

def build*mock_analysis( \*, code_file_name: str, rules_file_name: str, protocol_name: str, notes: Optional[str], rules_summary: Optional[str], ) -> Dict[str, object]: findings = [\_build_finding(code_file_name) for * in range(random.randint(4, 6))] counts = {"compliant": 0, "needs_review": 0, "non_compliant": 0} for finding in findings: counts[finding["compliance"]] += 1

    if counts["non_compliant"]:
        overall_status: ComplianceStatus = "non_compliant"
    elif counts["needs_review"]:
        overall_status = "needs_review"
    else:
        overall_status = "compliant"

    now = _now_iso()

    return {
        "analysisId": str(uuid.uuid4()),
        "durationMs": random.randint(1800, 4200),
        "inputs": {
            "codeFileName": code_file_name,
            "notes": notes or None,
            "protocolName": protocol_name,
            "rulesFileName": rules_file_name,
            "rulesSummary": rules_summary or None,
        },
        "model": "protocol-guard-static-preview",
        "modelResponse": {
            "metadata": {
                "generatedAt": now,
                "modelVersion": "protocol-guard-llm-2024-10",
                "protocol": protocol_name,
                "ruleSet": rules_file_name,
            },
            "summary": {
                "compliantCount": counts["compliant"],
                "needsReviewCount": counts["needs_review"],
                "nonCompliantCount": counts["non_compliant"],
                "notes": notes
                or "本次静态检测通过 ProtocolGuard 原型进行（Mock 数据）。",
                "overallStatus": overall_status,
            },
            "verdicts": findings,
        },
        "submittedAt": now,
    }

def normalize_protocol_name(parsed_rules: Optional[dict], fallback: str) -> str: if not parsed_rules or not isinstance(parsed_rules, dict): return fallback for key in ("protocol", "protocolName", "title", "name"): value = parsed_rules.get(key) if isinstance(value, str): return value return fallback

def extract_protocol_version(parsed_rules: Optional[dict], fallback: Optional[str] = None) -> Optional[str]: if not parsed_rules or not isinstance(parsed_rules, dict): return fallback for key in ("protocolVersion", "version", "protocol_version"): value = parsed_rules.get(key) if isinstance(value, str) and value.strip(): return value return fallback

def try_extract_rules_summary(parsed_rules: Optional[dict]) -> Optional[str]: if not parsed_rules or not isinstance(parsed_rules, dict): return None candidate = parsed_rules.get("summary") or parsed_rules.get("description") if isinstance(candidate, str): return candidate rules = parsed_rules.get("rules") if isinstance(rules, list) and rules: first = rules[0] if isinstance(first, dict) and "requirement" in first: return f"包含 {len(rules)} 条规则，示例：{first.get('requirement')}" return None

def \_build_finding(code_file_name: str) -> Dict[str, object]: compliance = random.choice(["compliant", "needs_review", "non_compliant"]) line_start = random.randint(12, 320) line_end = line_start + random.randint(2, 14) recommendation = ( \_random_sentence(12, 18) if compliance == "non_compliant" else None )

    return {
        "category": random.choice(["状态机约束", "消息字段校验", "握手流程", "错误处理"]),
        "compliance": compliance,
        "confidence": random.choice(["low", "medium", "high"]),
        "explanation": _random_paragraph(),
        "findingId": str(uuid.uuid4()),
        "lineRange": [line_start, line_end],
        "location": {
            "file": code_file_name,
            "function": random.choice(
                ["handle_handshake", "process_record", "validate_request", "dispatch_message"]
            ),
        },
        "recommendation": recommendation,
        "relatedRule": {
            "id": f"RULE-{random.randint(101, 999)}",
            "requirement": _random_sentence(10, 18),
            "source": f"RFC {random.randint(1000, 8999)} Section {random.randint(1, 6)}.{random.randint(1, 9)}",
        },
    }

def \_random_sentence(min_words: int = 8, max_words: int = 18) -> str: word_count = random.randint(min_words, max_words) words = random.choices(\_WORD_BANK, k=word_count) return " ".join(words)

def _random_paragraph(sentences: int = 1) -> str: return " ".join(\_random_sentence(8, 15) for _ in range(sentences))

\_WORD_BANK = [ "协议", "握手", "报文", "验证", "状态", "同步", "密钥", "交换", "流程", "校验", "加密", "套件", "确认", "策略", "超时", "重传", "检测", "结果", "安全", "约束", "分析", "规则", "字段", "覆盖", "路径", "机制", ]

# Docker integration ------------------------------------------------------------

class AnalysisError(RuntimeError): """Base error for ProtocolGuard analysis orchestration."""

class AnalysisNotReadyError(AnalysisError): """Raised when Docker integration is enabled but not available."""

class AnalysisExecutionError(AnalysisError): """Raised when the Docker pipeline fails."""

    def __init__(
        self,
        message: str,
        *,
        logs: Optional[list[str]] = None,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message)
        self.logs = logs or []
        self.details = details or {}

@lru_cache(maxsize=1) def \_docker_settings() -> ProtocolGuardDockerSettings: return ProtocolGuardDockerSettings.from_env()

def run_static_analysis( \*, code_stream: BinaryIO, code_file_name: str, builder_stream: BinaryIO, builder_file_name: str, config_stream: BinaryIO, config_file_name: str, rules_stream: BinaryIO, rules_file_name: str, notes: Optional[str], protocol_name: str, protocol_version: Optional[str], rules_summary: Optional[str], job_id: Optional[str] = None, progress_callback: Optional[Callable[[str, str, str], None]] = None, ) -> Dict[str, object]: """Dispatch static analysis either via Docker or the mock generator.""" job_identifier = job_id or str(uuid.uuid4()) settings = \_docker_settings() if not settings.enabled: LOGGER.debug("ProtocolGuard Docker disabled; returning mock analysis.") if progress_callback: progress_callback(job_identifier, "mock", "Generating mock analysis response") return build_mock_analysis( code_file_name=code_file_name, rules_file_name=rules_file_name, protocol_name=protocol_name, notes=notes, rules_summary=rules_summary, )

    try:
        runner = ProtocolGuardDockerRunner(settings)
    except ProtocolGuardNotAvailableError as exc:
        raise AnalysisNotReadyError(str(exc)) from exc

    try:
        return runner.run_static_analysis(
            code_stream=code_stream,
            code_filename=code_file_name,
            builder_stream=builder_stream,
            builder_filename=builder_file_name,
            config_stream=config_stream,
            config_filename=config_file_name,
            rules_stream=rules_stream,
            rules_filename=rules_file_name,
            notes=notes,
            protocol_name=protocol_name,
            protocol_version=protocol_version,
            rules_summary=rules_summary,
            job_id=job_identifier,
            progress_callback=progress_callback,
        )
    except ProtocolGuardExecutionError as exc:
        LOGGER.error(
            "ProtocolGuard analysis execution failed (image=%s, status=%s): %s",
            getattr(exc, "image", None),
            getattr(exc, "status", None),
            exc,
        )
        raise AnalysisExecutionError(
            str(exc),
            logs=getattr(exc, "logs", []),
            details={
                "status": getattr(exc, "status", None),
                "image": getattr(exc, "image", None),
                "logExcerpt": getattr(exc, "log_excerpt", None),
            },
        ) from exc
    except ProtocolGuardDockerError as exc:
        LOGGER.error("ProtocolGuard Docker error: %s", exc)
        raise AnalysisError(str(exc)) from exc

def submit_static_analysis_job( \*, code_payload: tuple[str, bytes], builder_payload: tuple[str, bytes], config_payload: tuple[str, bytes], rules_payload: tuple[str, bytes], notes: Optional[str], protocol_name: str, protocol_version: Optional[str], rules_summary: Optional[str], ) -> Dict[str, object]: """Launch static analysis asynchronously and return the initial job snapshot.""" state = PROGRESS_REGISTRY.create_job() job_id = state.job_id

    def _run_job() -> None:
        PROGRESS_REGISTRY.mark_running(job_id, "init", "Preparing analysis inputs")
        progress_callback = PROGRESS_REGISTRY.make_callback(job_id)
        progress_callback(job_id, "inputs", "Persisting uploaded artefacts")
        try:
            code_name, code_bytes = code_payload
            builder_name, builder_bytes = builder_payload
            config_name, config_bytes = config_payload
            rules_name, rules_bytes = rules_payload

            result = run_static_analysis(
                code_stream=BytesIO(code_bytes),
                code_file_name=code_name,
                builder_stream=BytesIO(builder_bytes),
                builder_file_name=builder_name,
                config_stream=BytesIO(config_bytes),
                config_file_name=config_name,
                rules_stream=BytesIO(rules_bytes),
                rules_file_name=rules_name,
                notes=notes,
                protocol_name=protocol_name,
                protocol_version=protocol_version,
                rules_summary=rules_summary,
                job_id=job_id,
                progress_callback=progress_callback,
            )
            PROGRESS_REGISTRY.complete(job_id, result)
        except AnalysisExecutionError as exc:
            details = exc.details if isinstance(exc.details, dict) else {}
            if exc.logs:
                details = {**details, "logs": list(exc.logs)}
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Static analysis execution failed",
                error=str(exc),
                details=details,
            )
        except AnalysisNotReadyError as exc:
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Static analysis backend is not ready",
                error=str(exc),
            )
        except AnalysisError as exc:
            PROGRESS_REGISTRY.fail(job_id, "error", "Static analysis service error", error=str(exc))
        except Exception as exc:  # pragma: no cover - defensive guard
            LOGGER.exception("Static analysis job %s encountered an unexpected error", job_id)
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Unexpected static analysis failure",
                error=str(exc),
            )

    worker = threading.Thread(target=_run_job, name=f"static-analysis-{job_id[:8]}", daemon=True)
    worker.start()
    snapshot = PROGRESS_REGISTRY.snapshot(job_id)
    assert snapshot is not None
    return snapshot

def get_static_analysis_job( job_id: str, from_event_id: Optional[int] = None, ) -> Optional[Dict[str, object]]: """ Return the current snapshot for a running static analysis job.

    If from_event_id is provided, only return events after that ID (incremental update).
    Otherwise, return full snapshot with all events.
    """
    return PROGRESS_REGISTRY.snapshot(job_id, from_event_id=from_event_id)

def get_static_analysis_result(job_id: str) -> Optional[Dict[str, object]]: """Return the final static analysis result if the job completed.""" snapshot = PROGRESS_REGISTRY.snapshot(job_id) if not snapshot: return None if snapshot.get("status") != "completed": return None result = snapshot.get("result") if isinstance(result, dict): return result return None

def list_static_analysis_history(limit: int = 50) -> List[Dict[str, object]]: """Return persisted static analysis job history entries.""" entries = analysis_state_repository.fetch_jobs(limit=limit) history: List[Dict[str, object]] = [] for entry in entries: result = entry.get("result") result_dict = result if isinstance(result, dict) else None model_response = result_dict.get("modelResponse") if isinstance(result_dict, dict) else None metadata = model_response.get("metadata") if isinstance(model_response, dict) else None summary = model_response.get("summary") if isinstance(model_response, dict) else None inputs = result_dict.get("inputs") if isinstance(result_dict, dict) else None

        protocol = None
        protocol_version = None
        rule_set = None
        model_version = None
        summary_payload = summary if isinstance(summary, dict) else None
        overall_status = None

        if isinstance(metadata, dict):
            protocol = metadata.get("protocol")
            protocol_version = metadata.get("protocolVersion")
            rule_set = metadata.get("ruleSet")
            model_version = metadata.get("modelVersion")
        if summary_payload:
            overall_status = summary_payload.get("overallStatus")

        duration_ms = result_dict.get("durationMs") if result_dict else None
        submitted_at = result_dict.get("submittedAt") if result_dict else None
        analysis_id = result_dict.get("analysisId") if result_dict else None
        model_name = result_dict.get("model") if result_dict else None

        code_file_name = None
        rules_file_name = None
        protocol_input_name = None
        if isinstance(inputs, dict):
            code_file_name = inputs.get("codeFileName")
            rules_file_name = inputs.get("rulesFileName")
            protocol_input_name = inputs.get("protocolName")
            if protocol is None:
                protocol = protocol_input_name

        snapshots = entry.get("workspace_snapshots")
        if isinstance(snapshots, list):
            workspace_snapshots = [item for item in snapshots if isinstance(item, dict)]
        else:
            workspace_snapshots = []

        history.append(
            {
                "jobId": entry.get("job_id"),
                "status": entry.get("status"),
                "stage": entry.get("stage"),
                "message": entry.get("message"),
                "workspacePath": entry.get("workspace_path"),
                "outputPath": entry.get("output_path"),
                "configPath": entry.get("config_path"),
                "logsPath": entry.get("logs_path"),
                "databasePath": entry.get("database_path"),
                "createdAt": entry.get("created_at"),
                "updatedAt": entry.get("updated_at"),
                "completedAt": entry.get("completed_at"),
                "error": entry.get("error"),
                "details": entry.get("details"),
                "analysisId": analysis_id,
                "model": model_name,
                "modelVersion": model_version,
                "durationMs": duration_ms,
                "submittedAt": submitted_at,
                "protocolName": protocol,
                "protocolVersion": protocol_version,
                "ruleSet": rule_set,
                "overallStatus": overall_status,
                "summary": summary_payload,
                "codeFileName": code_file_name,
                "rulesFileName": rules_file_name,
                "workspaceSnapshots": workspace_snapshots,
            }
        )
    return history

def delete_static_analysis_job(job_id: str) -> bool: """Delete a static analysis job from the database.

    Returns True if the job was deleted, False if it didn't exist.
    Raises an exception if the deletion failed.
    """
    return analysis_state_repository.delete_job(job_id)

==================================================================================================== 文件 20: apps/backend-flask/protocol_compliance/assertion.py ====================================================================================================

"""Assertion generation helpers and Docker orchestration glue.

Adds a follow-up Instrumentation operation after successful Assert generation. Also validates required environment variables for the instrumentation step. """

from **future** import annotations

import os import difflib import logging import re import threading import time import uuid from dataclasses import dataclass, field from datetime import datetime, timezone from functools import lru_cache from io import BytesIO from pathlib import Path from typing import BinaryIO, Callable, Dict, List, Optional, Tuple

from .assertion_history_repository import ASSERTION_HISTORY_REPOSITORY from .docker_runner import ( ProtocolGuardDockerError, ProtocolGuardDockerRunner, ProtocolGuardDockerSettings, ProtocolGuardExecutionError, ProtocolGuardNotAvailableError, )

LOGGER = logging.getLogger(**name**)

def \_now_iso() -> str: return datetime.now(timezone.utc).isoformat()

AssertGenerationJobStatus = str # Literal['queued', 'running', 'completed', 'failed']

@dataclass class AssertGenerationProgressEvent: timestamp: str stage: str message: str

@dataclass class AssertGenerationProgressState: job_id: str status: AssertGenerationJobStatus stage: str message: str created_at: str updated_at: str events: List[AssertGenerationProgressEvent] = field(default_factory=list) result: Optional[Dict[str, object]] = None error: Optional[str] = None details: Optional[Dict[str, object]] = None

class AssertGenerationError(RuntimeError): """Base error for assertion generation orchestration."""

class AssertGenerationNotReadyError(AssertGenerationError): """Raised when Docker integration is disabled or unavailable."""

class AssertGenerationExecutionError(AssertGenerationError): """Raised when the assertion generation container fails."""

    def __init__(
        self,
        message: str,
        *,
        logs: Optional[List[str]] = None,
        details: Optional[Dict[str, object]] = None,
    ) -> None:
        super().__init__(message)
        self.logs = logs or []
        self.details = details or {}

class AssertGenerationProgressRegistry: """Track live progress for assertion generation jobs."""

    def __init__(self) -> None:
        self._states: Dict[str, AssertGenerationProgressState] = {}
        self._lock = threading.Lock()

    def create_job(self) -> AssertGenerationProgressState:
        job_id = str(uuid.uuid4())
        now = _now_iso()
        state = AssertGenerationProgressState(
            job_id=job_id,
            status="queued",
            stage="queued",
            message="Job queued",
            created_at=now,
            updated_at=now,
        )
        state.events.append(
            AssertGenerationProgressEvent(timestamp=now, stage="queued", message="Job queued")
        )
        with self._lock:
            self._states[job_id] = state
        return state

    def mark_running(self, job_id: str, stage: str, message: str) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "running"
            self._append_event(state, stage, message)

    def append_event(self, job_id: str, stage: str, message: str) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            self._append_event(state, stage, message)

    def complete(self, job_id: str, result: Dict[str, object]) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "completed"
            state.result = result
            self._append_event(state, "completed", "Assertion generation completed successfully")

    def fail(
        self,
        job_id: str,
        stage: str,
        message: str,
        *,
        error: Optional[str] = None,
        details: Optional[Dict[str, object]] = None,
    ) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "failed"
            state.error = error or message
            state.details = details
            self._append_event(state, stage, message)

    def snapshot(self, job_id: str) -> Optional[Dict[str, object]]:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return None
            state_copy = AssertGenerationProgressState(
                job_id=state.job_id,
                status=state.status,
                stage=state.stage,
                message=state.message,
                created_at=state.created_at,
                updated_at=state.updated_at,
                events=list(state.events),
                result=state.result,
                error=state.error,
                details=state.details.copy() if state.details else None,
            )

        return {
            "jobId": state_copy.job_id,
            "status": state_copy.status,
            "stage": state_copy.stage,
            "message": state_copy.message,
            "createdAt": state_copy.created_at,
            "updatedAt": state_copy.updated_at,
            "events": [
                {"timestamp": event.timestamp, "stage": event.stage, "message": event.message}
                for event in state_copy.events
            ],
            "result": state_copy.result,
            "error": state_copy.error,
            "details": state_copy.details,
        }

    def make_callback(self, job_id: str) -> Callable[[str, str, str], None]:
        def callback(_job_id: str, stage: str, message: str) -> None:
            target_id = job_id or _job_id
            safe_stage = stage or "progress"
            safe_message = message or ""
            self.append_event(target_id, safe_stage, safe_message)

        return callback

    def _append_event(
        self,
        state: AssertGenerationProgressState,
        stage: str,
        message: str,
    ) -> None:
        timestamp = _now_iso()
        state.stage = stage or state.stage
        state.message = message or state.message
        state.updated_at = timestamp
        state.events.append(
            AssertGenerationProgressEvent(timestamp=timestamp, stage=stage or state.stage, message=message)
        )

PROGRESS_REGISTRY = AssertGenerationProgressRegistry()

# ----------------------------------------------------------------------------

# Environment setup for instrumentation

# ----------------------------------------------------------------------------

REQUIRED_INSTRUMENTATION_ENVS = ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "OPENAI_API_KEY", "OPENAI_BASE_URL") INSTRUMENTATION_DIFF_FILENAME = "instrumentation.diff" INSTRUMENTATION_DIFF_MAX_PREVIEW_BYTES = 512 \* 1024 # 512 KiB safety cap

def _ensure_env_passthrough_for_instrumentation() -> None: """Ensure ANTHROPIC_\* vars are forwarded into analysis containers.

    The Docker runner forwards variables listed in PG_ENV_VARS. Update it to
    include the required ANTHROPIC_* keys before settings are materialized.
    """
    existing = os.environ.get("PG_ENV_VARS", "")
    parts = [p.strip() for p in existing.split(",") if p.strip()]
    changed = False
    for key in REQUIRED_INSTRUMENTATION_ENVS:
        if key not in parts:
            parts.append(key)
            changed = True
    if changed:
        os.environ["PG_ENV_VARS"] = ",".join(parts)

def \_ensure_keep_artifacts_enabled() -> None: """Keep artefacts so the follow-up instrumentation can reuse /workspace.

    Assert emits state under /workspace which instrumentation consumes.
    """
    os.environ.setdefault("PG_KEEP_ARTIFACTS", "1")

def \_assert_required_instrumentation_env() -> None: """Validate ANTHROPIC envs exist; raise if missing.

    This check protects the instrumentation step. We do not eagerly exit the
    whole service on import; instead, fail fast when instrumentation runs.
    """
    missing = [name for name in REQUIRED_INSTRUMENTATION_ENVS if not os.environ.get(name)]
    if missing:
        raise AssertGenerationNotReadyError(
            "Missing required environment variables for instrumentation: " + ", ".join(missing)
        )

# Apply environment adjustments before docker settings are cached

\_ensure_env_passthrough_for_instrumentation() \_ensure_keep_artifacts_enabled()

@lru_cache(maxsize=1) def \_docker_settings() -> ProtocolGuardDockerSettings: return ProtocolGuardDockerSettings.from_env()

def run_assert_generation( \*, code_stream: BinaryIO, code_file_name: str, database_stream: BinaryIO, database_file_name: str, build_instructions: Optional[str], notes: Optional[str], job_id: Optional[str] = None, progress_callback: Optional[Callable[[str, str, str], None]] = None, ) -> Dict[str, object]: """Dispatch assertion generation via Docker followed by instrumentation.

    On success, triggers an instrumentation container using the same workspace
    and merges its artefacts into the returned result under the "instrumentation"
    key.
    """

    job_identifier = job_id or str(uuid.uuid4())
    settings = _docker_settings()
    if not settings.enabled:
        raise AssertGenerationNotReadyError("ProtocolGuard Docker integration is disabled")

    try:
        runner = ProtocolGuardDockerRunner(settings)
    except ProtocolGuardNotAvailableError as exc:
        raise AssertGenerationNotReadyError(str(exc)) from exc

    try:
        base_result = runner.run_assert_generation(
            code_stream=code_stream,
            code_filename=code_file_name,
            database_stream=database_stream,
            database_filename=database_file_name,
            build_instructions=build_instructions,
            notes=notes,
            job_id=job_identifier,
            progress_callback=progress_callback,
        )
        # Follow-up: run instrumentation using the prepared workspace/output.
        try:
            if progress_callback:
                progress_callback(job_identifier, "instrumentation", "Preparing instrumentation environment")
            _assert_required_instrumentation_env()

            # Resolve workspace and output mounts from assertion result
            artifacts = base_result.get("artifacts") if isinstance(base_result, dict) else None
            workspace_dir = Path(artifacts.get("workspace")) if isinstance(artifacts, dict) else None
            output_dir = Path(artifacts.get("output")) if isinstance(artifacts, dict) else None

            if not workspace_dir or not output_dir:
                raise AssertGenerationError("Assertion step did not return workspace/output artefacts")
            if not workspace_dir.exists() or not output_dir.exists():
                raise AssertGenerationError("Workspace or output directory missing before instrumentation")

            if progress_callback:
                progress_callback(job_identifier, "instrumentation", "Launching instrumentation container")

            instr_details = _run_instrumentation_container(
                image=_docker_settings().analysis_image,
                network=_docker_settings().network,
                workspace=workspace_dir,
                output=output_dir,
                extra_args=(["--limit", str(limit_env)] if (limit_env := os.environ.get("PG_INSTRUMENTATION_LIMIT")) else None),
                job_id=job_identifier,
                progress_callback=progress_callback,
            )

            # Merge instrumentation details into the base result
            if isinstance(base_result, dict):
                base_result["instrumentation"] = instr_details
            _record_assertion_history_entry(
                job_id=job_identifier,
                code_filename=code_file_name,
                database_filename=database_file_name,
                instrumentation_details=instr_details,
            )
            if progress_callback:
                progress_callback(job_identifier, "instrumentation", "Instrumentation completed successfully")
        except AssertGenerationError:
            raise
        except Exception as exc:
            raise AssertGenerationError(f"Instrumentation step failed: {exc}") from exc
        return base_result
    except ProtocolGuardExecutionError as exc:
        details: Dict[str, object] = {
            "image": getattr(exc, "image", None),
            "status": getattr(exc, "status", None),
        }
        if exc.log_excerpt:
            details["logExcerpt"] = exc.log_excerpt
        raise AssertGenerationExecutionError(
            str(exc),
            logs=list(getattr(exc, "logs", []) or []),
            details=details,
        ) from exc
    except ProtocolGuardDockerError as exc:
        raise AssertGenerationError(str(exc)) from exc

def \_run_instrumentation_container( \*, image: str, network: Optional[str], workspace: Path, output: Path, extra_args: Optional[List[str]] = None, job_id: Optional[str] = None, progress_callback: Optional[Callable[[str, str, str], None]] = None, ) -> Dict[str, object]: """Run the ProtocolGuard instrumentation container and collect results.

    Uses the same image as assertion generation. Mounts the given workspace as
    /workspace and the output dir as /out. Requires ANTHROPIC_* env variables.
    """
    start_ts = time.time()
    command: List[str] = [
        "instrumentation",
        "--target-dir",
        "/workspace",
    ]
    args = list(extra_args or [])

    def _find_flag_value(tokens: List[str], flag: str) -> Optional[str]:
        for idx, token in enumerate(tokens):
            if token == flag and idx + 1 < len(tokens):
                return tokens[idx + 1]
        return None

    def _resolve_diff_output_path(value: Optional[str]) -> Optional[Path]:
        if not value:
            return None
        diff_path = Path(value)
        if diff_path.is_absolute():
            try:
                relative = diff_path.relative_to("/out")
            except ValueError:
                LOGGER.warning(
                    "Diff output path %s is outside /out; using file name within host output directory",
                    diff_path,
                )
                return (output / diff_path.name).resolve()
            return (output / relative).resolve()
        return (output / diff_path).resolve()

    # Always enforce a default limit for testing if not provided explicitly.
    has_limit = False
    for idx, token in enumerate(args):
        if token == "--limit":
            has_limit = True
            break
    if not has_limit:
        args.extend(["--limit", "1"])

    diff_output_arg = _find_flag_value(args, "--diff-output")
    if not diff_output_arg:
        diff_output_arg = f"/out/{INSTRUMENTATION_DIFF_FILENAME}"
        args.extend(["--diff-output", diff_output_arg])

    command.extend(args)
    diff_host_path = _resolve_diff_output_path(diff_output_arg)

    def _emit(stage: str, message: str) -> None:
        LOGGER.info("[job %s][%s] %s", job_id or "-", stage, message)
        if progress_callback:
            try:
                progress_callback(job_id or "", stage, message)
            except Exception:  # pragma: no cover - defensive
                LOGGER.debug("Progress callback failed during instrumentation for job %s", job_id, exc_info=True)

    # Build environment forwarded to the container
    env = {
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
        "ANTHROPIC_BASE_URL": os.environ.get("ANTHROPIC_BASE_URL", ""),
    }

    # Prefer Docker SDK; fall back to CLI if unavailable
    try:
        import docker  # type: ignore
        from docker.errors import DockerException  # type: ignore

        client = docker.from_env()
        _emit("instrumentation", f"Starting instrumentation container (image={image}, command={' '.join(command)})")
        container = client.containers.run(
            image=image,
            command=command,
            volumes={
                str(workspace.resolve()): {"bind": "/workspace", "mode": "rw"},
                str(output.resolve()): {"bind": "/out", "mode": "rw"},
            },
            environment=env,
            detach=True,
            remove=True,
            stdout=True,
            stderr=True,
            network=network,
        )

        logs: List[str] = []
        for chunk in container.logs(stream=True, follow=True):
            line = chunk.decode("utf-8", errors="replace").rstrip()
            logs.append(line)
            if line:
                display = line if len(line) <= 2000 else f"{line[:2000]}..."
                _emit("instrumentation-log", display)

        result = container.wait()
        status = int(result.get("StatusCode", 1))
        if status != 0:
            excerpt = "\n".join(logs[-40:]) if logs else None
            raise AssertGenerationExecutionError(
                f"Instrumentation container exited with status {status}",
                logs=logs,
                details={"logExcerpt": excerpt, "image": image, "status": status},
            )
    except ModuleNotFoundError:
        # Use docker CLI as a fallback
        _emit("instrumentation", "Docker SDK not available; falling back to docker CLI for instrumentation")
        import subprocess

        cli_cmd = [
            "docker",
            "run",
            "--rm",
            "-e",
            f"ANTHROPIC_API_KEY={env['ANTHROPIC_API_KEY']}",
            "-e",
            f"ANTHROPIC_BASE_URL={env['ANTHROPIC_BASE_URL']}",
            "-v",
            f"{str(workspace.resolve())}:/workspace",
            "-v",
            f"{str(output.resolve())}:/out",
        ]
        if network:
            cli_cmd.extend(["--network", network])
        cli_cmd.append(image)
        cli_cmd.extend(command)

        _emit("instrumentation", f"Running via docker CLI: {' '.join(cli_cmd)}")
        process = subprocess.Popen(cli_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        logs = []  # type: ignore[redeclared]
        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip()
            logs.append(line)
            if line:
                display = line if len(line) <= 2000 else f"{line[:2000]}..."
                _emit("instrumentation-log", display)
        status = process.wait()
        if status != 0:
            excerpt = "\n".join(logs[-40:]) if logs else None
            raise AssertGenerationExecutionError(
                f"Instrumentation container exited with status {status}",
                logs=logs,
                details={"logExcerpt": excerpt, "image": image, "status": status},
            )
    except Exception as exc:
        # Normalize docker-related errors
        raise AssertGenerationError(f"Failed to run instrumentation container: {exc}") from exc

    duration_ms = int((time.time() - start_ts) * 1000)

    # Gather artefacts from /out
    instrumented_code = output / "instrumented_code"
    diff_files = sorted([str(p) for p in output.glob("*.diff") if p.is_file()])
    diff_output_info: Dict[str, object] = {
        "path": str(diff_host_path) if diff_host_path else None,
        "available": False,
    }
    if diff_host_path and diff_host_path.exists():
        diff_size = diff_host_path.stat().st_size
        diff_preview: Optional[str] = None
        truncated = False
        try:
            diff_preview = diff_host_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # pragma: no cover - best effort
            LOGGER.warning("Failed to read instrumentation diff file %s: %s", diff_host_path, exc)
        else:
            if len(diff_preview) > INSTRUMENTATION_DIFF_MAX_PREVIEW_BYTES:
                diff_preview = diff_preview[:INSTRUMENTATION_DIFF_MAX_PREVIEW_BYTES]
                truncated = True
        diff_output_info.update(
            {
                "available": True,
                "size": diff_size,
                "content": diff_preview,
                "truncated": truncated,
            }
        )

    details: Dict[str, object] = {
        "docker": {
            "image": image,
            "command": list(command),
            "durationMs": duration_ms,
        },
        "artifacts": {
            "instrumentedCodePath": str(instrumented_code) if instrumented_code.exists() else None,
            "diffFiles": diff_files or [],
            "diffOutput": diff_output_info,
        },
        "logs": logs,
        "completedAt": _now_iso(),
    }

    return details

def submit_assert_generation_job( \*, code_payload: Tuple[str, bytes], database_payload: Tuple[str, bytes], build_instructions: Optional[str], notes: Optional[str], ) -> Dict[str, object]: """Launch assertion generation asynchronously and return initial snapshot."""

    state = PROGRESS_REGISTRY.create_job()
    job_id = state.job_id

    def _run_job() -> None:
        PROGRESS_REGISTRY.mark_running(job_id, "init", "Preparing assertion generation inputs")
        progress_callback = PROGRESS_REGISTRY.make_callback(job_id)
        progress_callback(job_id, "inputs", "Persisting uploaded artefacts")

        try:
            code_name, code_bytes = code_payload
            database_name, database_bytes = database_payload

            result = run_assert_generation(
                code_stream=BytesIO(code_bytes),
                code_file_name=code_name,
                database_stream=BytesIO(database_bytes),
                database_file_name=database_name,
                build_instructions=build_instructions,
                notes=notes,
                job_id=job_id,
                progress_callback=progress_callback,
            )
            PROGRESS_REGISTRY.complete(job_id, result)
        except AssertGenerationExecutionError as exc:
            details = exc.details.copy()
            if exc.logs:
                details["logs"] = list(exc.logs)
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Assertion generation execution failed",
                error=str(exc),
                details=details or None,
            )
        except AssertGenerationNotReadyError as exc:
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Assertion generation backend is not ready",
                error=str(exc),
            )
        except AssertGenerationError as exc:
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Assertion generation service error",
                error=str(exc),
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            LOGGER.exception("Assertion generation job %s encountered an unexpected error", job_id)
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Unexpected assertion generation failure",
                error=str(exc),
            )

    worker = threading.Thread(target=_run_job, name=f"assert-generation-{job_id[:8]}", daemon=True)
    worker.start()
    snapshot = PROGRESS_REGISTRY.snapshot(job_id)
    assert snapshot is not None
    return snapshot

def get_assert_generation_job(job_id: str) -> Optional[Dict[str, object]]: return PROGRESS_REGISTRY.snapshot(job_id)

def get_assert_generation_result(job_id: str) -> Optional[Dict[str, object]]: snapshot = PROGRESS_REGISTRY.snapshot(job_id) if not snapshot: return None if snapshot.get("status") != "completed": return None result = snapshot.get("result") if isinstance(result, dict): return result return None

def get_assert_generation_zip_path(job_id: str) -> Optional[Path]: snapshot = PROGRESS_REGISTRY.snapshot(job_id) if not snapshot: return None result = snapshot.get("result") if not isinstance(result, dict): return None artifacts = result.get("artifacts") if not isinstance(artifacts, dict): return None raw_zip = artifacts.get("zipPath") if not raw_zip: return None zip_path = Path(raw_zip) if not zip_path.exists(): return None return zip_path

def \_record_assertion_history_entry( \*, job_id: str, code_filename: str, database_filename: str, instrumentation_details: Dict[str, object], ) -> None: artifacts = instrumentation_details.get("artifacts") if isinstance(instrumentation_details, dict) else None if not isinstance(artifacts, dict): return diff_output = artifacts.get("diffOutput") if not isinstance(diff_output, dict): return raw_path = diff_output.get("path") if not isinstance(raw_path, str) or not raw_path: return diff_path = Path(raw_path) if not diff_path.exists(): LOGGER.warning("Instrumentation diff file %s missing for job %s", diff_path, job_id) return try: ASSERTION_HISTORY_REPOSITORY.record_job( job_id=job_id, diff_source_path=diff_path, code_filename=code_filename, database_filename=database_filename, ) except Exception as exc: # pragma: no cover - persistence best effort LOGGER.warning("Failed to persist assertion history for job %s: %s", job_id, exc)

def list_assertion_history(limit: int = 50) -> List[Dict[str, object]]: return ASSERTION_HISTORY_REPOSITORY.list_history(limit=limit)

def get_assertion_history_entry(job_id: str) -> Optional[Dict[str, object]]: return ASSERTION_HISTORY_REPOSITORY.get_entry(job_id)

def get_assertion_history_diff_path(job_id: str) -> Optional[Path]: return ASSERTION_HISTORY_REPOSITORY.resolve_diff_path(job_id)

# ============================================================================

# Diff Parsing Workflow

# ============================================================================

DiffParsingJobStatus = str # Literal['queued', 'running', 'completed', 'failed']

@dataclass class DiffParsingProgressEvent: timestamp: str stage: str message: str percentage: int

@dataclass class DiffParsingProgressState: job_id: str parent_job_id: str status: DiffParsingJobStatus stage: str message: str percentage: int created_at: str updated_at: str events: List[DiffParsingProgressEvent] = field(default_factory=list) result: Optional[Dict[str, object]] = None error: Optional[str] = None

class DiffParsingProgressRegistry: """Track live progress for diff parsing jobs."""

    def __init__(self) -> None:
        self._states: Dict[str, DiffParsingProgressState] = {}
        self._lock = threading.Lock()

    def create_job(self, parent_job_id: str) -> DiffParsingProgressState:
        job_id = str(uuid.uuid4())
        now = _now_iso()
        state = DiffParsingProgressState(
            job_id=job_id,
            parent_job_id=parent_job_id,
            status="queued",
            stage="queued",
            message="Diff parsing queued",
            percentage=0,
            created_at=now,
            updated_at=now,
        )
        state.events.append(
            DiffParsingProgressEvent(
                timestamp=now,
                stage="queued",
                message="Diff parsing queued",
                percentage=0,
            )
        )
        with self._lock:
            self._states[job_id] = state
        return state

    def mark_running(self, job_id: str, stage: str, message: str, percentage: int) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "running"
            self._append_event(state, stage, message, percentage)

    def append_event(self, job_id: str, stage: str, message: str, percentage: int) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            self._append_event(state, stage, message, percentage)

    def complete(self, job_id: str, result: Dict[str, object]) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "completed"
            state.result = result
            self._append_event(state, "completed", "Diff parsing completed successfully", 100)

    def fail(
        self,
        job_id: str,
        stage: str,
        message: str,
        *,
        error: Optional[str] = None,
    ) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "failed"
            state.error = error or message
            self._append_event(state, stage, message, state.percentage)

    def snapshot(self, job_id: str) -> Optional[Dict[str, object]]:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return None
            state_copy = DiffParsingProgressState(
                job_id=state.job_id,
                parent_job_id=state.parent_job_id,
                status=state.status,
                stage=state.stage,
                message=state.message,
                percentage=state.percentage,
                created_at=state.created_at,
                updated_at=state.updated_at,
                events=list(state.events),
                result=state.result,
                error=state.error,
            )

        return {
            "jobId": state_copy.job_id,
            "parentJobId": state_copy.parent_job_id,
            "status": state_copy.status,
            "stage": state_copy.stage,
            "message": state_copy.message,
            "percentage": state_copy.percentage,
            "createdAt": state_copy.created_at,
            "updatedAt": state_copy.updated_at,
            "events": [
                {
                    "timestamp": event.timestamp,
                    "stage": event.stage,
                    "message": event.message,
                    "percentage": event.percentage,
                }
                for event in state_copy.events
            ],
            "result": state_copy.result,
            "error": state_copy.error,
        }

    def _append_event(
        self,
        state: DiffParsingProgressState,
        stage: str,
        message: str,
        percentage: int,
    ) -> None:
        timestamp = _now_iso()
        state.stage = stage or state.stage
        state.message = message or state.message
        state.percentage = max(0, min(100, percentage))
        state.updated_at = timestamp
        state.events.append(
            DiffParsingProgressEvent(
                timestamp=timestamp,
                stage=stage or state.stage,
                message=message,
                percentage=state.percentage,
            )
        )

DIFF_PARSING_REGISTRY = DiffParsingProgressRegistry()

def \_generate_mock_diff() -> Dict[str, object]: """Generate a realistic mock diff for demonstration purposes."""

    # Mock diff content as a string
    diff_content = """diff --git a/src/protocol/tls_handler.c b/src/protocol/tls_handler.c

index 1a2b3c4..5d6e7f8 100644 --- a/src/protocol/tls_handler.c +++ b/src/protocol/tls_handler.c @@ -45,7 +45,7 @@ int verify_certificate(SSL *ssl, const char *hostname) { X509 \*cert = SSL_get_peer_certificate(ssl);

     if (!cert) {

-        fprintf(stderr, "No certificate presented\\n");

*        log_error("No certificate presented by peer");
         return -1;
  }

@@ -67,12 +67,18 @@ int tls_handshake(connection_t \*conn) { return -1; }

- // Set verification mode
- SSL_set_verify(conn->ssl, SSL_VERIFY_PEER, NULL);

* // Set strict verification mode with callback
* SSL_set_verify(conn->ssl, SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT, verify_callback);
*
* // Set minimum TLS version to 1.2
* SSL_set_min_proto_version(conn->ssl, TLS1_2_VERSION);

  // Perform handshake int ret = SSL_do_handshake(conn->ssl); if (ret != 1) {

*        int ssl_error = SSL_get_error(conn->ssl, ret);
*        log_error("TLS handshake failed with error code: %d", ssl_error);
*        ERR_print_errors_fp(stderr);
         return -1;
  }

diff --git a/src/protocol/assertions.c b/src/protocol/assertions.c new file mode 100644 index 0000000..9a8b7c1 --- /dev/null +++ b/src/protocol/assertions.c @@ -0,0 +1,52 @@ +#include "assertions.h" +#include <assert.h> +#include <string.h>

- +/\*\*
- - Assert that TLS version is at least 1.2
- */ +void assert_min_tls_version(SSL *ssl) {
- int version = SSL_version(ssl);
- assert(version >= TLS1_2_VERSION && "TLS version must be at least 1.2"); +}
- +/\*\*
- - Assert that certificate verification succeeded
- */ +void assert_certificate_verified(SSL *ssl) {
- long verify_result = SSL_get_verify_result(ssl);
- assert(verify_result == X509_V_OK && "Certificate verification must succeed"); +}
- +/\*\*
- - Assert that cipher suite is secure
- */ +void assert_secure_cipher(SSL *ssl) {
- const SSL_CIPHER \*cipher = SSL_get_current_cipher(ssl);
- assert(cipher != NULL && "Cipher suite must be negotiated");
-
- const char \*cipher_name = SSL_CIPHER_get_name(cipher);
- // Ensure no weak ciphers (NULL, EXPORT, DES, MD5, etc.)
- assert(strstr(cipher_name, "NULL") == NULL && "NULL cipher not allowed");
- assert(strstr(cipher_name, "EXPORT") == NULL && "EXPORT cipher not allowed");
- assert(strstr(cipher_name, "DES") == NULL && "DES cipher not allowed");
- assert(strstr(cipher_name, "MD5") == NULL && "MD5 cipher not allowed"); +}
- +/\*\*
- - Assert that peer certificate is present
- */ +void assert_peer_certificate_present(SSL *ssl) {
- X509 \*cert = SSL_get_peer_certificate(ssl);
- assert(cert != NULL && "Peer certificate must be present");
- X509_free(cert); +}
- +/\*\*
- - Run all TLS protocol assertions
- */ +void run_tls_assertions(SSL *ssl) {
- assert_min_tls_version(ssl);
- assert_certificate_verified(ssl);
- assert_secure_cipher(ssl);
- assert_peer_certificate_present(ssl); +} diff --git a/tests/test_tls_protocol.c b/tests/test_tls_protocol.c index a1b2c3d..e4f5g6h 100644 --- a/tests/test_tls_protocol.c +++ b/tests/test_tls_protocol.c @@ -15,6 +15,7 @@ #include "../src/protocol/tls_handler.h" +#include "../src/protocol/assertions.h" #include "test_helpers.h"

void test_basic_handshake() { @@ -28,7 +29,12 @@ void test_basic_handshake() {

     int result = tls_handshake(&conn);
     assert(result == 0);

-
- // Run protocol compliance assertions
- run_tls_assertions(conn.ssl);
-     cleanup_connection(&conn);
- printf("✓ Basic handshake test passed\\n"); }

void test_certificate_verification() { """

    # Parse diff into structured format
    files = [
        {
            "from": "src/protocol/tls_handler.c",
            "to": "src/protocol/tls_handler.c",
            "additions": 7,
            "deletions": 2,
            "hunks": [
                {
                    "oldStart": 45,
                    "oldLines": 7,
                    "newStart": 45,
                    "newLines": 7,
                    "lines": [
                        {"type": "normal", "content": "    X509 *cert = SSL_get_peer_certificate(ssl);"},
                        {"type": "normal", "content": "    "},
                        {"type": "normal", "content": "    if (!cert) {"},
                        {"type": "delete", "content": '        fprintf(stderr, "No certificate presented\\n");'},
                        {"type": "add", "content": '        log_error("No certificate presented by peer");'},
                        {"type": "normal", "content": "        return -1;"},
                        {"type": "normal", "content": "    }"},
                    ],
                },
                {
                    "oldStart": 67,
                    "oldLines": 12,
                    "newStart": 67,
                    "newLines": 18,
                    "lines": [
                        {"type": "normal", "content": "        return -1;"},
                        {"type": "normal", "content": "    }"},
                        {"type": "normal", "content": "    "},
                        {"type": "delete", "content": "    // Set verification mode"},
                        {"type": "delete", "content": "    SSL_set_verify(conn->ssl, SSL_VERIFY_PEER, NULL);"},
                        {"type": "add", "content": "    // Set strict verification mode with callback"},
                        {"type": "add", "content": "    SSL_set_verify(conn->ssl, SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT, verify_callback);"},
                        {"type": "add", "content": "    "},
                        {"type": "add", "content": "    // Set minimum TLS version to 1.2"},
                        {"type": "add", "content": "    SSL_set_min_proto_version(conn->ssl, TLS1_2_VERSION);"},
                        {"type": "normal", "content": "    "},
                        {"type": "normal", "content": "    // Perform handshake"},
                        {"type": "normal", "content": "    int ret = SSL_do_handshake(conn->ssl);"},
                        {"type": "normal", "content": "    if (ret != 1) {"},
                        {"type": "add", "content": "        int ssl_error = SSL_get_error(conn->ssl, ret);"},
                        {"type": "add", "content": '        log_error("TLS handshake failed with error code: %d", ssl_error);'},
                        {"type": "add", "content": "        ERR_print_errors_fp(stderr);"},
                        {"type": "normal", "content": "        return -1;"},
                        {"type": "normal", "content": "    }"},
                    ],
                },
            ],
        },
        {
            "from": "src/protocol/assertions.c",
            "to": "src/protocol/assertions.c",
            "additions": 52,
            "deletions": 0,
            "hunks": [
                {
                    "oldStart": 0,
                    "oldLines": 0,
                    "newStart": 1,
                    "newLines": 52,
                    "lines": [
                        {"type": "add", "content": '#include "assertions.h"'},
                        {"type": "add", "content": "#include <assert.h>"},
                        {"type": "add", "content": "#include <string.h>"},
                        {"type": "add", "content": ""},
                        {"type": "add", "content": "/**"},
                        {"type": "add", "content": " * Assert that TLS version is at least 1.2"},
                        {"type": "add", "content": " */"},
                        {"type": "add", "content": "void assert_min_tls_version(SSL *ssl) {"},
                        {"type": "add", "content": "    int version = SSL_version(ssl);"},
                        {"type": "add", "content": '    assert(version >= TLS1_2_VERSION && "TLS version must be at least 1.2");'},
                        {"type": "add", "content": "}"},
                        {"type": "add", "content": ""},
                        {"type": "add", "content": "/**"},
                        {"type": "add", "content": " * Assert that certificate verification succeeded"},
                        {"type": "add", "content": " */"},
                        {"type": "add", "content": "void assert_certificate_verified(SSL *ssl) {"},
                        {"type": "add", "content": "    long verify_result = SSL_get_verify_result(ssl);"},
                        {"type": "add", "content": '    assert(verify_result == X509_V_OK && "Certificate verification must succeed");'},
                        {"type": "add", "content": "}"},
                    ],
                },
            ],
        },
        {
            "from": "tests/test_tls_protocol.c",
            "to": "tests/test_tls_protocol.c",
            "additions": 6,
            "deletions": 0,
            "hunks": [
                {
                    "oldStart": 15,
                    "oldLines": 6,
                    "newStart": 15,
                    "newLines": 7,
                    "lines": [
                        {"type": "normal", "content": " "},
                        {"type": "normal", "content": '#include "../src/protocol/tls_handler.h"'},
                        {"type": "add", "content": '#include "../src/protocol/assertions.h"'},
                        {"type": "normal", "content": '#include "test_helpers.h"'},
                        {"type": "normal", "content": ""},
                        {"type": "normal", "content": "void test_basic_handshake() {"},
                    ],
                },
                {
                    "oldStart": 28,
                    "oldLines": 7,
                    "newStart": 29,
                    "newLines": 12,
                    "lines": [
                        {"type": "normal", "content": "    "},
                        {"type": "normal", "content": "    int result = tls_handshake(&conn);"},
                        {"type": "normal", "content": "    assert(result == 0);"},
                        {"type": "add", "content": "    "},
                        {"type": "add", "content": "    // Run protocol compliance assertions"},
                        {"type": "add", "content": "    run_tls_assertions(conn.ssl);"},
                        {"type": "add", "content": "    "},
                        {"type": "normal", "content": "    cleanup_connection(&conn);"},
                        {"type": "add", "content": '    printf("✓ Basic handshake test passed\\n");'},
                        {"type": "normal", "content": "}"},
                        {"type": "normal", "content": ""},
                        {"type": "normal", "content": "void test_certificate_verification() {"},
                    ],
                },
            ],
        },
    ]

    total_insertions = sum(f["additions"] for f in files)
    total_deletions = sum(f["deletions"] for f in files)

    return {
        "jobId": str(uuid.uuid4()),
        "diffContent": diff_content,
        "files": files,
        "summary": {
            "filesChanged": len(files),
            "insertions": total_insertions,
            "deletions": total_deletions,
        },
        "generatedAt": _now_iso(),
    }

# ============================================================================

# Patch File Reading & Matching

# ============================================================================

# Define the path to the assert-mock directory

# From: /home/xinrui/GitHub/vue-vben-admin/apps/backend-flask/protocol_compliance/assertion.py

# To: /home/xinrui/GitHub/assert-mock

ASSERT_MOCK_DIR = Path(**file**).parent.parent.parent.parent.parent / "assert-mock"

# Available patch files

AVAILABLE_PATCH_FILES = [ "wolfssl_assertion.patch", "uftp_assertion.patch", "tlse_assertion.patch", "tinymqtt_assertion.patch", "sol_assertion_changes.patch", "pure_ftpd_assertion.patch", "ndhs_assertion.patch", "mosquitto_assertion.patch", "libcoap_assertion.patch", "freecoap_assertion.patch", ]

def extract_protocol_name_from_database(database_filename: str) -> str: """ Extract protocol name from database filename. Examples: sqlite_wolfssl.db -> wolfssl sqlite_mosquitto.db -> mosquitto violations.db -> violations """ # Remove .db extension name = database_filename.replace(".db", "")

    # Remove sqlite_ prefix if present
    if name.startswith("sqlite_"):
        name = name[7:]  # len("sqlite_") = 7

    return name.lower()

def find_best_matching_patch_file(protocol_name: str, available_files: List[str]) -> Optional[str]: """ Find the best matching patch file using string similarity. Returns the filename with the highest similarity score, or None if no good match. """ if not protocol_name or not available_files: return None

    protocol_name_lower = protocol_name.lower()
    best_match = None
    best_score = 0.0

    for filename in available_files:
        # Extract the base name from the patch file (e.g., "wolfssl" from "wolfssl_assertion.patch")
        base_name = filename.replace("_assertion.patch", "").replace("_assertion_changes.patch", "")

        # Calculate similarity using SequenceMatcher
        similarity = difflib.SequenceMatcher(None, protocol_name_lower, base_name.lower()).ratio()

        if similarity > best_score:
            best_score = similarity
            best_match = filename

    # Only return a match if similarity is above 0.5 (50%)
    if best_score >= 0.5:
        LOGGER.info(
            "Matched protocol '%s' to patch file '%s' with similarity %.2f",
            protocol_name,
            best_match,
            best_score,
        )
        return best_match

    LOGGER.warning(
        "No good match found for protocol '%s'. Best match was '%s' with similarity %.2f",
        protocol_name,
        best_match,
        best_score,
    )
    return None

def parse_unified_diff(patch_content: str) -> Dict[str, object]: """ Parse a unified diff patch file into structured format. Returns a dictionary with 'diffContent', 'files', and 'summary'. """ files = [] current_file = None current_hunk = None

    lines = patch_content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Match file header: diff --git a/... b/...
        if line.startswith('diff --git'):
            # Save previous file if exists
            if current_file and current_hunk:
                current_file["hunks"].append(current_hunk)
                files.append(current_file)

            # Extract filenames
            match = re.search(r'a/(.*?)\s+b/(.*?)$', line)
            if match:
                current_file = {
                    "from": match.group(1),
                    "to": match.group(2),
                    "additions": 0,
                    "deletions": 0,
                    "hunks": []
                }
            current_hunk = None

        # Match old file: --- a/...
        elif line.startswith('---'):
            if current_file is None:
                match = re.search(r'---\s+a/(.*?)$', line)
                if match:
                    current_file = {
                        "from": match.group(1),
                        "to": "",
                        "additions": 0,
                        "deletions": 0,
                        "hunks": []
                    }

        # Match new file: +++ b/...
        elif line.startswith('+++'):
            if current_file:
                match = re.search(r'\+\+\+\s+b/(.*?)$', line)
                if match:
                    current_file["to"] = match.group(1)

        # Match hunk header: @@ -old_start,old_lines +new_start,new_lines @@
        elif line.startswith('@@'):
            # Save previous hunk if exists
            if current_hunk:
                current_file["hunks"].append(current_hunk)

            match = re.search(r'@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@', line)
            if match:
                old_start = int(match.group(1))
                old_lines = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_lines = int(match.group(4)) if match.group(4) else 1

                current_hunk = {
                    "oldStart": old_start,
                    "oldLines": old_lines,
                    "newStart": new_start,
                    "newLines": new_lines,
                    "lines": []
                }

        # Match diff content lines
        elif current_hunk is not None:
            if line.startswith('+') and not line.startswith('+++'):
                current_hunk["lines"].append({"type": "add", "content": line[1:]})
                current_file["additions"] += 1
            elif line.startswith('-') and not line.startswith('---'):
                current_hunk["lines"].append({"type": "delete", "content": line[1:]})
                current_file["deletions"] += 1
            elif line.startswith(' '):
                current_hunk["lines"].append({"type": "normal", "content": line[1:]})
            elif line.startswith('\\'):
                # Handle "\ No newline at end of file"
                pass
            else:
                # Context line without leading space (treat as normal)
                current_hunk["lines"].append({"type": "normal", "content": line})

        i += 1

    # Save last file and hunk
    if current_file:
        if current_hunk:
            current_file["hunks"].append(current_hunk)
        files.append(current_file)

    # Calculate summary
    total_files = len(files)
    total_insertions = sum(f["additions"] for f in files)
    total_deletions = sum(f["deletions"] for f in files)

    return {
        "diffContent": patch_content,
        "files": files,
        "summary": {
            "filesChanged": total_files,
            "insertions": total_insertions,
            "deletions": total_deletions,
        },
    }

def load_patch_from_database_name(database_filename: str) -> Optional[Dict[str, object]]: """ Load and parse a patch file based on the database filename. Returns parsed diff structure or None if no matching patch found. """ # Extract protocol name from database filename protocol_name = extract_protocol_name_from_database(database_filename) LOGGER.info("Extracted protocol name '%s' from database '%s'", protocol_name, database_filename)

    # Find best matching patch file
    patch_filename = find_best_matching_patch_file(protocol_name, AVAILABLE_PATCH_FILES)
    if not patch_filename:
        LOGGER.warning("No matching patch file found for protocol '%s'", protocol_name)
        return None

    # Construct full path to patch file
    patch_path = ASSERT_MOCK_DIR / patch_filename

    # Check if file exists
    if not patch_path.exists():
        LOGGER.error("Patch file not found at path: %s", patch_path)
        return None

    # Read patch file
    try:
        with open(patch_path, 'r', encoding='utf-8') as f:
            patch_content = f.read()

        LOGGER.info("Successfully read patch file: %s (%d bytes)", patch_filename, len(patch_content))

        # Parse the patch file
        parsed_diff = parse_unified_diff(patch_content)
        LOGGER.info(
            "Parsed patch: %d files, %d insertions, %d deletions",
            parsed_diff["summary"]["filesChanged"],
            parsed_diff["summary"]["insertions"],
            parsed_diff["summary"]["deletions"],
        )

        return parsed_diff
    except Exception as e:
        LOGGER.exception("Error reading or parsing patch file %s: %s", patch_path, e)
        return None

def submit_diff_parsing_job(parent_job_id: str) -> Dict[str, object]: """Launch diff parsing asynchronously and return initial snapshot."""

    state = DIFF_PARSING_REGISTRY.create_job(parent_job_id)
    job_id = state.job_id

    def _run_job() -> None:
        try:
            # Retrieve the parent assertion generation job to get database filename
            DIFF_PARSING_REGISTRY.mark_running(job_id, "init", "Starting diff parsing", 0)
            time.sleep(1)

            DIFF_PARSING_REGISTRY.append_event(job_id, "load", "Loading assertion generation metadata", 10)
            parent_snapshot = get_assert_generation_job(parent_job_id)

            database_filename = None
            if parent_snapshot:
                result = parent_snapshot.get("result")
                if isinstance(result, dict):
                    inputs = result.get("inputs")
                    if isinstance(inputs, dict):
                        database_filename = inputs.get("databaseFileName")

            if not database_filename:
                LOGGER.warning(
                    "Could not extract database filename from parent job %s, using fallback mock data",
                    parent_job_id
                )
                database_filename = "violations.db"  # Fallback

            LOGGER.info("Diff parsing job %s: database filename = %s", job_id, database_filename)

            # Try to load patch file from assert-mock directory
            DIFF_PARSING_REGISTRY.append_event(job_id, "match", "Matching database to patch file", 20)
            time.sleep(1)

            parsed_diff = load_patch_from_database_name(database_filename)

            if parsed_diff:
                LOGGER.info("Successfully loaded real patch file for database: %s", database_filename)
                DIFF_PARSING_REGISTRY.append_event(job_id, "parse", "Parsing unified diff format", 40)
                time.sleep(1)
                DIFF_PARSING_REGISTRY.append_event(job_id, "struct", "Building diff structure", 60)
                time.sleep(1)
                DIFF_PARSING_REGISTRY.append_event(job_id, "validate", "Validating diff hunks", 80)
                time.sleep(1)
                DIFF_PARSING_REGISTRY.append_event(job_id, "finalize", "Finalizing results", 95)
                time.sleep(0.5)

                # Add metadata to the result
                result = parsed_diff.copy()
                result["jobId"] = job_id
                result["generatedAt"] = _now_iso()
                result["metadata"] = {
                    "databaseFileName": database_filename,
                    "source": "patch_file"
                }
            else:
                # Fallback to mock data if no patch file found
                LOGGER.warning("No patch file found for database %s, using mock data", database_filename)
                DIFF_PARSING_REGISTRY.append_event(job_id, "fallback", "Using mock diff data", 50)
                time.sleep(2)
                DIFF_PARSING_REGISTRY.append_event(job_id, "finalize", "Finalizing mock results", 90)
                time.sleep(1)

                result = _generate_mock_diff()
                result["metadata"] = {
                    "databaseFileName": database_filename,
                    "source": "mock_data"
                }

            DIFF_PARSING_REGISTRY.complete(job_id, result)

        except Exception as exc:  # pragma: no cover
            LOGGER.exception("Diff parsing job %s encountered an error", job_id)
            DIFF_PARSING_REGISTRY.fail(
                job_id,
                "error",
                "Diff parsing failed",
                error=str(exc),
            )

    worker = threading.Thread(target=_run_job, name=f"diff-parsing-{job_id[:8]}", daemon=True)
    worker.start()
    snapshot = DIFF_PARSING_REGISTRY.snapshot(job_id)
    assert snapshot is not None
    return snapshot

def get_diff_parsing_job(job_id: str) -> Optional[Dict[str, object]]: return DIFF_PARSING_REGISTRY.snapshot(job_id)

def get_diff_parsing_result(job_id: str) -> Optional[Dict[str, object]]: snapshot = DIFF_PARSING_REGISTRY.snapshot(job_id) if not snapshot: return None if snapshot.get("status") != "completed": return None result = snapshot.get("result") if isinstance(result, dict): return result return None

==================================================================================================== 文件 21: apps/backend-flask/protocol_compliance/assertion_history_repository.py ====================================================================================================

"""SQLite-backed history store for instrumentation diff artefacts."""

from **future** import annotations

import logging import os import shutil import sqlite3 import threading from contextlib import contextmanager from dataclasses import dataclass from datetime import datetime, timezone from pathlib import Path from typing import Dict, Iterator, List, Optional

LOGGER = logging.getLogger(**name**)

def \_now_iso() -> str: return datetime.now(timezone.utc).isoformat()

def \_default_state_directory() -> Path: raw_dir = os.environ.get("PROTOCOLGUARD_STATE_DIR") if raw_dir: try: return Path(raw_dir).expanduser().resolve() except (OSError, RuntimeError): LOGGER.warning("Invalid PROTOCOLGUARD_STATE_DIR %s; using package \_state directory", raw_dir) return Path(**file**).resolve().parent / "\_state"

def \_default_db_path() -> Path: raw_name = os.environ.get("ASSERT_HISTORY_DB_NAME", "assertion_history.sqlite3") return (\_default_state_directory() / raw_name).resolve()

def \_default_storage_dir() -> Path: raw_dir = os.environ.get("ASSERT_HISTORY_STORAGE_DIR") if raw_dir: try: return Path(raw_dir).expanduser().resolve() except (OSError, RuntimeError): LOGGER.warning("Invalid ASSERT_HISTORY_STORAGE_DIR %s; falling back to default location", raw_dir) return (\_default_state_directory() / "assertion_history").resolve()

@dataclass class AssertionHistoryEntry: job_id: str code_filename: Optional[str] database_filename: Optional[str] diff_path: Optional[str] diff_filename: Optional[str] created_at: str updated_at: str source: str

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "jobId": self.job_id,
            "codeFilename": self.code_filename,
            "databaseFilename": self.database_filename,
            "diffPath": self.diff_path,
            "diffFilename": self.diff_filename,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "source": self.source,
        }

class AssertionHistoryRepository: """Persist instrumentation diff metadata for later retrieval."""

    def __init__(
        self,
        *,
        db_path: Optional[Path] = None,
        storage_dir: Optional[Path] = None,
    ) -> None:
        self._db_path = (db_path or _default_db_path()).resolve()
        self._storage_dir = (storage_dir or _default_storage_dir()).resolve()
        self._lock = threading.Lock()
        self._initialized = False

    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def storage_dir(self) -> Path:
        return self._storage_dir

    def record_job(
        self,
        *,
        job_id: str,
        diff_source_path: Path,
        code_filename: Optional[str],
        database_filename: Optional[str],
        created_at: Optional[str] = None,
        source: str = "auto",
        copy_diff: bool = True,
    ) -> Optional[Path]:
        """Copy the diff file into storage and persist metadata."""

        if not job_id:
            raise ValueError("job_id is required")
        if not diff_source_path:
            raise ValueError("diff_source_path is required")

        if not diff_source_path.exists():
            LOGGER.warning("Diff file %s missing while recording job %s", diff_source_path, job_id)
            diff_storage_path: Optional[Path] = None
        else:
            diff_storage_path = (
                self._persist_diff_file(job_id, diff_source_path) if copy_diff else diff_source_path.resolve()
            )

        timestamp = created_at or _now_iso()
        self._upsert_entry(
            job_id=job_id,
            code_filename=code_filename,
            database_filename=database_filename,
            diff_path=str(diff_storage_path) if diff_storage_path else None,
            diff_filename=diff_source_path.name,
            created_at=timestamp,
            updated_at=timestamp,
            source=source or "auto",
        )
        return diff_storage_path

    def insert_manual_entry(
        self,
        *,
        job_id: str,
        diff_file: Path,
        code_filename: Optional[str],
        database_filename: Optional[str],
        created_at: Optional[str] = None,
        copy_diff: bool = True,
    ) -> Optional[Path]:
        """Helper for manual seeding via Python scripts."""

        return self.record_job(
            job_id=job_id,
            diff_source_path=diff_file,
            code_filename=code_filename,
            database_filename=database_filename,
            created_at=created_at,
            source="manual",
            copy_diff=copy_diff,
        )

    def list_history(self, *, limit: int = 50) -> List[Dict[str, Optional[str]]]:
        """Return the newest history entries."""

        limit = max(1, min(limit, 500))
        self._ensure_initialized()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT job_id, code_filename, database_filename, diff_path, diff_filename, created_at, updated_at, source
                FROM assertion_history
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_entry(row).as_dict() for row in rows]

    def get_entry(self, job_id: str) -> Optional[Dict[str, Optional[str]]]:
        if not job_id:
            return None
        self._ensure_initialized()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT job_id, code_filename, database_filename, diff_path, diff_filename, created_at, updated_at, source
                FROM assertion_history
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_entry(row).as_dict()

    def resolve_diff_path(self, job_id: str) -> Optional[Path]:
        entry = self.get_entry(job_id)
        if not entry:
            return None
        raw_path = entry.get("diffPath")
        if not raw_path:
            return None
        path = Path(raw_path)
        return path if path.exists() else None

    # Internal helpers -----------------------------------------------------

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assertion_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL UNIQUE,
                        code_filename TEXT,
                        database_filename TEXT,
                        diff_path TEXT,
                        diff_filename TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        source TEXT NOT NULL DEFAULT 'auto'
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_assertion_history_job ON assertion_history(job_id)")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_assertion_history_created ON assertion_history(created_at DESC)"
                )
            self._initialized = True

    def _upsert_entry(
        self,
        *,
        job_id: str,
        code_filename: Optional[str],
        database_filename: Optional[str],
        diff_path: Optional[str],
        diff_filename: Optional[str],
        created_at: str,
        updated_at: str,
        source: str,
    ) -> None:
        self._ensure_initialized()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO assertion_history (
                    job_id,
                    code_filename,
                    database_filename,
                    diff_path,
                    diff_filename,
                    created_at,
                    updated_at,
                    source
                )
                VALUES (:job_id, :code_filename, :database_filename, :diff_path, :diff_filename, :created_at, :updated_at, :source)
                ON CONFLICT(job_id) DO UPDATE SET
                    code_filename = excluded.code_filename,
                    database_filename = excluded.database_filename,
                    diff_path = excluded.diff_path,
                    diff_filename = excluded.diff_filename,
                    updated_at = excluded.updated_at,
                    source = excluded.source
                """,
                {
                    "job_id": job_id,
                    "code_filename": code_filename,
                    "database_filename": database_filename,
                    "diff_path": diff_path,
                    "diff_filename": diff_filename,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "source": source,
                },
            )
            conn.commit()

    def _persist_diff_file(self, job_id: str, source_path: Path) -> Path:
        self._ensure_initialized()
        target_dir = self._storage_dir / job_id
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / source_path.name
        try:
            shutil.copy2(source_path, destination)
        except OSError as exc:
            LOGGER.error("Failed to copy diff file %s -> %s: %s", source_path, destination, exc)
            raise
        return destination.resolve()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self._ensure_initialized()
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> AssertionHistoryEntry:
        return AssertionHistoryEntry(
            job_id=row["job_id"],
            code_filename=row["code_filename"],
            database_filename=row["database_filename"],
            diff_path=row["diff_path"],
            diff_filename=row["diff_filename"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            source=row["source"],
        )

ASSERTION_HISTORY_REPOSITORY = AssertionHistoryRepository()

==================================================================================================== 文件 22: apps/backend-flask/protocol_compliance/assertion_history_util.py ====================================================================================================

"""CLI helper to manually seed assertion history records.

Usage examples: python -m protocol_compliance.assertion_history_util \
 --diff-file ./instrumentation.diff \
 --job-id manual-001 \
 --code-filename sample.tar.gz \
 --database-filename sqlite_sample.db """

from **future** import annotations

import argparse import sys import uuid from pathlib import Path from typing import Optional

# Support running as a module or as a standalone script.

try: # noqa: SIM105 - explicit guard for script execution from .assertion_history_repository import AssertionHistoryRepository, ASSERTION_HISTORY_REPOSITORY except Exception: # pragma: no cover - fallback for direct execution import sys from pathlib import Path

    CURRENT_DIR = Path(__file__).resolve().parent
    PACKAGE_ROOT = CURRENT_DIR.parent
    if str(PACKAGE_ROOT) not in sys.path:
        sys.path.insert(0, str(PACKAGE_ROOT))
    from protocol_compliance.assertion_history_repository import (  # type: ignore
        AssertionHistoryRepository,
        ASSERTION_HISTORY_REPOSITORY,
    )

def \_positive_int(value: str) -> int: parsed = int(value) if parsed < 1: raise argparse.ArgumentTypeError("limit must be >= 1") return parsed

def \_resolve_repo(db_path: Optional[str], storage_dir: Optional[str]) -> AssertionHistoryRepository: if not db_path and not storage_dir: return ASSERTION_HISTORY_REPOSITORY db = Path(db_path).expanduser() if db_path else None storage = Path(storage_dir).expanduser() if storage_dir else None return AssertionHistoryRepository(db_path=db, storage_dir=storage)

def seed_history( \*, diff_file: Path, job_id: str, code_filename: Optional[str], database_filename: Optional[str], created_at: Optional[str], copy_diff: bool, db_path: Optional[str], storage_dir: Optional[str], ) -> Path: repo = \_resolve_repo(db_path, storage_dir) return repo.insert_manual_entry( job_id=job_id, diff_file=diff_file, code_filename=code_filename, database_filename=database_filename, created_at=created_at, copy_diff=copy_diff, )

def main(argv: Optional[list[str]] = None) -> int: parser = argparse.ArgumentParser(description="Seed assertion history with a manual record") parser.add_argument( "--diff-file", required=True, help="Path to the instrumentation diff file to record", ) parser.add_argument( "--job-id", default=None, help="Job ID to record (default: random UUID)", ) parser.add_argument( "--code-filename", default=None, help="Original code archive filename to store alongside the record", ) parser.add_argument( "--database-filename", default=None, help="Original SQLite filename to store alongside the record", ) parser.add_argument( "--created-at", default=None, help="ISO8601 timestamp for record creation (default: now, UTC)", ) parser.add_argument( "--no-copy", action="store_true", help="Do not copy diff into history storage; reference the source file directly", ) parser.add_argument( "--db-path", default=None, help="Override database path (default: ASSERT_HISTORY_DB_NAME within PROTOCOLGUARD_STATE_DIR)", ) parser.add_argument( "--storage-dir", default=None, help="Override diff storage directory (default: assertion_history under PROTOCOLGUARD_STATE_DIR)", )

    parsed = parser.parse_args(argv)

    diff_file = Path(parsed.diff_file).expanduser().resolve()
    if not diff_file.exists():
        parser.error(f"Diff file does not exist: {diff_file}")

    job_id = parsed.job_id or str(uuid.uuid4())
    try:
        destination = seed_history(
            diff_file=diff_file,
            job_id=job_id,
            code_filename=parsed.code_filename,
            database_filename=parsed.database_filename,
            created_at=parsed.created_at,
            copy_diff=not parsed.no_copy,
            db_path=parsed.db_path,
            storage_dir=parsed.storage_dir,
        )
    except Exception as exc:  # pragma: no cover - CLI helper
        parser.error(str(exc))
        return 1

    print(f"Recorded job {job_id}")
    if destination:
        print(f"Diff stored at: {destination}")
    return 0

if **name** == "**main**": # pragma: no cover - CLI entrypoint sys.exit(main())

==================================================================================================== 文件 23: apps/backend-flask/protocol_compliance/state_repository.py ====================================================================================================

"""SQLite-backed persistence for ProtocolGuard static analysis jobs."""

from **future** import annotations

import json import logging import os import sqlite3 import threading from contextlib import contextmanager, suppress from pathlib import Path from typing import Any, List, Mapping, Optional, Sequence

LOGGER = logging.getLogger(**name**)

def \_default_state_directory() -> Path: raw_dir = os.environ.get("PROTOCOLGUARD_STATE_DIR") if raw_dir: try: base_dir = Path(raw_dir).expanduser().resolve() except (OSError, RuntimeError): LOGGER.warning("Invalid PROTOCOLGUARD_STATE_DIR %s; falling back to package directory", raw_dir) base_dir = Path(**file**).resolve().parent / "\_state" else: base_dir = Path(**file**).resolve().parent / "\_state" return base_dir

def \_default_db_path() -> Path: raw_name = os.environ.get("PROTOCOLGUARD_STATE_DB_NAME", "analysis_state.sqlite3") base_dir = \_default_state_directory() return (base_dir / raw_name).resolve()

def \_normalize_path(value: Optional[Any]) -> Optional[str]: if isinstance(value, (str, Path)): try: return str(Path(value).expanduser().resolve()) except (OSError, RuntimeError): return str(value) return None

def \_dump_json(value: Optional[Any]) -> Optional[str]: if value is None: return None try: return json.dumps(value, ensure_ascii=False, separators=(",", ":")) except (TypeError, ValueError) as exc: LOGGER.warning("Failed to serialize JSON payload for persistence: %s", exc) return None

def \_load_json(value: Optional[str]) -> Optional[Any]: if not value: return None try: return json.loads(value) except (TypeError, ValueError) as exc: LOGGER.warning("Failed to deserialize JSON payload from persistence: %s", exc) return None

class AnalysisStateRepository: """Persist static analysis job metadata and artefact locations."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = Path(db_path).resolve() if db_path else _default_db_path()
        self._lock = threading.Lock()
        self._initialized = False

    @property
    def db_path(self) -> Path:
        return self._db_path

    def record_progress(
        self,
        *,
        job_id: str,
        status: str,
        stage: str,
        message: str,
        updated_at: str,
        created_at: Optional[str] = None,
    ) -> None:
        payload = {
            "job_id": job_id,
            "status": status,
            "stage": stage,
            "message": message,
            "workspace_path": None,
            "output_path": None,
            "config_path": None,
            "logs_path": None,
            "database_path": None,
            "result_json": None,
            "error_text": None,
            "details_json": None,
            "docker_logs_json": None,
            "workspace_snapshots_json": None,
            "created_at": created_at or updated_at,
            "updated_at": updated_at,
            "completed_at": None,
        }
        self._upsert(payload)

    def record_completion(
        self,
        *,
        job_id: str,
        status: str,
        stage: str,
        message: str,
        updated_at: str,
        result: Mapping[str, Any],
    ) -> None:
        artifacts = result.get("artifacts") if isinstance(result, Mapping) else None
        workspace_path = None
        output_path = None
        config_path = None
        logs_path = None
        database_path = None
        workspace_snapshots: Optional[Sequence[Mapping[str, Any]]] = None

        if isinstance(artifacts, Mapping):
            workspace_path = _normalize_path(artifacts.get("workspace"))
            output_path = _normalize_path(artifacts.get("output"))
            config_path = _normalize_path(artifacts.get("config"))
            logs_path = _normalize_path(artifacts.get("logs"))
            database_path = _normalize_path(artifacts.get("database"))
            snapshots = artifacts.get("workspaceSnapshots")
            if isinstance(snapshots, Sequence):
                workspace_snapshots = [entry for entry in snapshots if isinstance(entry, Mapping)]  # type: ignore[arg-type]

        payload = {
            "job_id": job_id,
            "status": status,
            "stage": stage,
            "message": message,
            "workspace_path": workspace_path,
            "output_path": output_path,
            "config_path": config_path,
            "logs_path": logs_path,
            "database_path": database_path,
            "result_json": _dump_json(result),
            "error_text": None,
            "details_json": None,
            "docker_logs_json": None,
            "workspace_snapshots_json": _dump_json(workspace_snapshots),
            "created_at": updated_at,
            "updated_at": updated_at,
            "completed_at": updated_at,
        }
        self._upsert(payload)

    def record_failure(
        self,
        *,
        job_id: str,
        status: str,
        stage: str,
        message: str,
        updated_at: str,
        error: Optional[str],
        details: Optional[Mapping[str, Any]],
    ) -> None:
        payload = {
            "job_id": job_id,
            "status": status,
            "stage": stage,
            "message": message,
            "workspace_path": None,
            "output_path": None,
            "config_path": None,
            "logs_path": None,
            "database_path": None,
            "result_json": None,
            "error_text": error or message,
            "details_json": _dump_json(details),
            "docker_logs_json": None,
            "workspace_snapshots_json": None,
            "created_at": updated_at,
            "updated_at": updated_at,
            "completed_at": None,
        }
        self._upsert(payload)

    def add_event(self, *, job_id: str, timestamp: str, stage: str, message: str) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO analysis_job_events (job_id, timestamp, stage, message)
                    VALUES (:job_id, :timestamp, :stage, :message)
                    """,
                    {
                        "job_id": job_id,
                        "timestamp": timestamp,
                        "stage": stage,
                        "message": message,
                    },
                )
        except sqlite3.DatabaseError as exc:
            LOGGER.warning("Failed to persist analysis job event for %s: %s", job_id, exc)

    def fetch_events(
        self,
        *,
        job_id: str,
        from_event_id: Optional[int] = None,
    ) -> List[dict[str, Any]]:
        """Fetch events for a job, optionally from a specific event ID onwards."""
        self._ensure_initialized()
        if from_event_id is None:
            query = """
                SELECT id, timestamp, stage, message
                FROM analysis_job_events
                WHERE job_id = ?
                ORDER BY id ASC
            """
            params = (job_id,)
        else:
            query = """
                SELECT id, timestamp, stage, message
                FROM analysis_job_events
                WHERE job_id = ? AND id > ?
                ORDER BY id ASC
            """
            params = (job_id, from_event_id)

        connection: Optional[sqlite3.Connection] = None
        try:
            connection = sqlite3.connect(self._db_path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON;")
            rows = connection.execute(query, params).fetchall()
        except sqlite3.DatabaseError as exc:
            LOGGER.warning("Failed to fetch events for job %s: %s", job_id, exc)
            return []
        finally:
            if connection is not None:
                with suppress(Exception):
                    connection.close()

        events: List[dict[str, Any]] = []
        for row in rows:
            events.append(
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "stage": row["stage"],
                    "message": row["message"],
                }
            )
        return events

    def fetch_jobs(self, *, limit: int = 50) -> List[dict[str, Any]]:
        self._ensure_initialized()
        query = (
            """
            SELECT
                job_id,
                status,
                stage,
                message,
                workspace_path,
                output_path,
                config_path,
                logs_path,
                database_path,
                result_json,
                error_text,
                details_json,
                docker_logs_json,
                workspace_snapshots_json,
                created_at,
                updated_at,
                completed_at
            FROM analysis_jobs
            ORDER BY COALESCE(completed_at, updated_at, created_at) DESC
            """
        )
        params: tuple[Any, ...]
        if limit and limit > 0:
            query += " LIMIT ?"
            params = (int(limit),)
        else:
            params = tuple()

        connection: Optional[sqlite3.Connection] = None
        try:
            connection = sqlite3.connect(self._db_path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON;")
            rows = connection.execute(query, params).fetchall()
        except sqlite3.DatabaseError as exc:
            LOGGER.warning("Failed to read analysis job history: %s", exc)
            return []
        finally:
            if connection is not None:
                with suppress(Exception):
                    connection.close()

        history: List[dict[str, Any]] = []
        for row in rows:
            history.append(
                {
                    "job_id": row["job_id"],
                    "status": row["status"],
                    "stage": row["stage"],
                    "message": row["message"],
                    "workspace_path": row["workspace_path"],
                    "output_path": row["output_path"],
                    "config_path": row["config_path"],
                    "logs_path": row["logs_path"],
                    "database_path": row["database_path"],
                    "result": _load_json(row["result_json"]),
                    "error": row["error_text"],
                    "details": _load_json(row["details_json"]),
                    "docker_logs": _load_json(row["docker_logs_json"]),
                    "workspace_snapshots": _load_json(row["workspace_snapshots_json"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "completed_at": row["completed_at"],
                }
            )
        return history

    def delete_job(self, job_id: str) -> bool:
        """Delete a job and its events from the database.

        Returns True if the job was deleted, False if it didn't exist.
        """
        self._ensure_initialized()
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "DELETE FROM analysis_jobs WHERE job_id = ?",
                    (job_id,)
                )
                return cursor.rowcount > 0
        except sqlite3.DatabaseError as exc:
            LOGGER.error("Failed to delete analysis job %s: %s", job_id, exc)
            raise

    def _ensure_initialized(self) -> None:
        if self._initialized and self._db_path.exists():
            return
        with self._lock:
            if self._initialized and self._db_path.exists():
                return
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("PRAGMA foreign_keys = ON;")
                    conn.executescript(
                        """
                        CREATE TABLE IF NOT EXISTS analysis_jobs (
                            job_id TEXT PRIMARY KEY,
                            status TEXT NOT NULL,
                            stage TEXT NOT NULL,
                            message TEXT NOT NULL,
                            workspace_path TEXT,
                            output_path TEXT,
                            config_path TEXT,
                            logs_path TEXT,
                            database_path TEXT,
                            result_json TEXT,
                            error_text TEXT,
                            details_json TEXT,
                            docker_logs_json TEXT,
                            workspace_snapshots_json TEXT,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            completed_at TEXT
                        );

                        CREATE TABLE IF NOT EXISTS analysis_job_events (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            job_id TEXT NOT NULL,
                            timestamp TEXT NOT NULL,
                            stage TEXT NOT NULL,
                            message TEXT NOT NULL,
                            FOREIGN KEY(job_id) REFERENCES analysis_jobs(job_id) ON DELETE CASCADE
                        );
                        """
                    )
                    conn.commit()
            except sqlite3.DatabaseError as exc:
                LOGGER.error("Unable to initialize analysis state database at %s: %s", self._db_path, exc)
            self._initialized = True

    @contextmanager
    def _connect(self):
        self._ensure_initialized()
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
            conn.commit()
        except sqlite3.DatabaseError:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _upsert(self, payload: Mapping[str, Optional[Any]]) -> None:
        self._ensure_initialized()
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO analysis_jobs (
                        job_id,
                        status,
                        stage,
                        message,
                        workspace_path,
                        output_path,
                        config_path,
                        logs_path,
                        database_path,
                        result_json,
                        error_text,
                        details_json,
                        docker_logs_json,
                        workspace_snapshots_json,
                        created_at,
                        updated_at,
                        completed_at
                    ) VALUES (
                        :job_id,
                        :status,
                        :stage,
                        :message,
                        :workspace_path,
                        :output_path,
                        :config_path,
                        :logs_path,
                        :database_path,
                        :result_json,
                        :error_text,
                        :details_json,
                        :docker_logs_json,
                        :workspace_snapshots_json,
                        :created_at,
                        :updated_at,
                        :completed_at
                    )
                    ON CONFLICT(job_id) DO UPDATE SET
                        status = excluded.status,
                        stage = excluded.stage,
                        message = excluded.message,
                        workspace_path = COALESCE(excluded.workspace_path, analysis_jobs.workspace_path),
                        output_path = COALESCE(excluded.output_path, analysis_jobs.output_path),
                        config_path = COALESCE(excluded.config_path, analysis_jobs.config_path),
                        logs_path = COALESCE(excluded.logs_path, analysis_jobs.logs_path),
                        database_path = COALESCE(excluded.database_path, analysis_jobs.database_path),
                        result_json = COALESCE(excluded.result_json, analysis_jobs.result_json),
                        error_text = COALESCE(excluded.error_text, analysis_jobs.error_text),
                        details_json = COALESCE(excluded.details_json, analysis_jobs.details_json),
                        docker_logs_json = COALESCE(excluded.docker_logs_json, analysis_jobs.docker_logs_json),
                        workspace_snapshots_json = COALESCE(excluded.workspace_snapshots_json, analysis_jobs.workspace_snapshots_json),
                        updated_at = excluded.updated_at,
                        completed_at = COALESCE(excluded.completed_at, analysis_jobs.completed_at)
                    """,
                    payload,
                )
        except sqlite3.DatabaseError as exc:
            LOGGER.warning("Failed to persist analysis job state for %s: %s", payload.get("job_id"), exc)

def \_create_repository() -> AnalysisStateRepository: return AnalysisStateRepository()

analysis_state_repository = \_create_repository()

==================================================================================================== 文件 24: apps/backend-flask/protocol_compliance/store.py ====================================================================================================

"""In-memory Protocol Compliance task store with lifecycle simulation."""

from **future** import annotations

import random import threading import uuid from dataclasses import dataclass from datetime import datetime, timezone from typing import Dict, Iterable, List, Literal, Optional

TaskStatus = Literal["completed", "failed", "processing", "queued"]

def \_now_iso() -> str: return datetime.now(timezone.utc).isoformat()

@dataclass class ProtocolComplianceTask: id: str name: str document_name: str document_size: Optional[int] description: Optional[str] tags: Optional[List[str]] status: TaskStatus progress: int submitted_at: str updated_at: str completed_at: Optional[str] = None result_payload: Optional[Dict[str, object]] = None

class TaskStore: """Maintain protocol compliance tasks and simulate async progression."""

    def __init__(self) -> None:
        self._tasks: List[ProtocolComplianceTask] = []
        self._lock = threading.Lock()
        self._timers: Dict[str, List[threading.Timer]] = {}

    def create_task(
        self,
        *,
        name: str,
        document_name: str,
        document_size: Optional[int],
        description: Optional[str],
        tags: Optional[List[str]],
    ) -> ProtocolComplianceTask:
        now = _now_iso()
        task = ProtocolComplianceTask(
            id=str(uuid.uuid4()),
            name=name,
            document_name=document_name,
            document_size=document_size,
            description=description,
            tags=tags if tags else None,
            status="queued",
            progress=18,
            submitted_at=now,
            updated_at=now,
        )
        with self._lock:
            self._tasks.insert(0, task)
            if len(self._tasks) > 50:
                excess = self._tasks[50:]
                self._tasks = self._tasks[:50]
                for removed in excess:
                    self._clear_task_timers(removed.id)

        self._plan_lifecycle(task)
        return task

    def list_tasks(self, *, status: Optional[Iterable[TaskStatus]] = None) -> List[ProtocolComplianceTask]:
        with self._lock:
            tasks = list(self._tasks)

        if status:
            status_set = set(status)
            tasks = [task for task in tasks if task.status in status_set]

        tasks.sort(key=lambda item: item.submitted_at, reverse=True)
        return tasks

    def get_task(self, task_id: str) -> Optional[ProtocolComplianceTask]:
        with self._lock:
            for task in self._tasks:
                if task.id == task_id:
                    return task
        return None

    def serialize_task(self, task: ProtocolComplianceTask, base_url: str) -> Dict[str, object]:
        result_download_url: Optional[str]
        if task.status == "completed":
            result_download_url = f"{base_url.rstrip('/')}/api/protocol-compliance/tasks/{task.id}/result"
        else:
            result_download_url = None

        return {
            "id": task.id,
            "name": task.name,
            "documentName": task.document_name,
            "documentSize": task.document_size,
            "description": task.description,
            "tags": task.tags,
            "status": task.status,
            "progress": task.progress,
            "submittedAt": task.submitted_at,
            "updatedAt": task.updated_at,
            "completedAt": task.completed_at,
            "resultDownloadUrl": result_download_url,
        }

    # Internal helpers -------------------------------------------------

    def _plan_lifecycle(self, task: ProtocolComplianceTask) -> None:
        plan = [
            (0.6, {"progress": 35, "status": "processing"}),
            (1.6, {"progress": 68}),
            (2.8, {"progress": 85}),
            (4.2, {"progress": 100, "status": "completed", "completed": True}),
        ]

        for delay, patch in plan:
            timer = threading.Timer(delay, self._apply_patch, args=(task.id, patch))
            timer.daemon = True
            timer.start()
            self._register_timer(task.id, timer)

    def _register_timer(self, task_id: str, timer: threading.Timer) -> None:
        with self._lock:
            self._timers.setdefault(task_id, []).append(timer)

    def _clear_task_timers(self, task_id: str) -> None:
        timers = self._timers.pop(task_id, [])
        for timer in timers:
            timer.cancel()

    def _apply_patch(self, task_id: str, patch: Dict[str, object]) -> None:
        with self._lock:
            target = next((task for task in self._tasks if task.id == task_id), None)
            if not target:
                return

            now = _now_iso()
            target.progress = int(patch.get("progress", target.progress))
            target.status = patch.get("status", target.status)  # type: ignore[assignment]
            target.updated_at = now

            if patch.get("completed"):
                target.completed_at = now
                target.status = "completed"  # type: ignore[assignment]
                target.result_payload = self._build_result_payload(target)
                self._clear_task_timers(task_id)

    def _build_result_payload(self, task: ProtocolComplianceTask) -> Dict[str, object]:
        def random_rule() -> Dict[str, str]:
            action = random.choice(
                [
                    "验证握手报文结构",
                    "检查密钥交换流程",
                    "验证状态同步",
                    "校验加密套件协商",
                    "确认超时重传策略",
                ]
            )
            reference = f"RFC {random.randint(1000, 9000)}.{random.randint(1, 9)}"
            requirement = _random_sentence()
            return {"action": action, "reference": reference, "requirement": requirement}

        def random_finding() -> Dict[str, object]:
            description = _random_sentence(10, 22)
            section = f"{random.randint(1, 7)}.{random.randint(1, 9)}"
            severity = random.choice(["low", "medium", "high"])
            return {"description": description, "section": section, "severity": severity}

        rules = [random_rule() for _ in range(random.randint(4, 8))]
        findings = [random_finding() for _ in range(random.randint(1, 3))]

        return {
            "complianceSummary": {
                "criticalFindings": findings,
                "docTitle": task.name or task.document_name,
                "extractedAt": _now_iso(),
                "overview": _random_paragraph(),
            },
            "metadata": {
                "documentName": task.document_name,
                "documentSize": task.document_size,
                "taskId": task.id,
                "uploadedAt": task.submitted_at,
            },
            "protocolRules": rules,
            "tags": task.tags or [],
        }

def \_random_sentence(min_words: int = 8, max_words: int = 18) -> str: word_count = random.randint(min_words, max_words) words = random.choices(\_WORD_BANK, k=word_count) sentence = " ".join(words).capitalize() + "。" return sentence

def _random_paragraph(sentences: int = 3) -> str: return " ".join(\_random_sentence(8, 15) for _ in range(sentences))

\_WORD_BANK = [ "协议", "握手", "报文", "验证", "状态", "同步", "密钥", "交换", "流程", "校验", "加密", "套件", "确认", "策略", "超时", "重传", "检测", "结果", "安全", "约束", "分析", "规则", "字段", "覆盖", "路径", "机制", ]

STORE = TaskStore()

==================================================================================================== 文件 25: apps/backend-flask/protocol_compliance/docker_runner.py ====================================================================================================

"""Compatibility shim for ProtocolGuard Docker runner internals.

The heavy lifting now lives in `protocol_compliance._docker_runner` to keep the public import path stable for callers using `protocol_compliance.docker_runner`. """

from .\_docker_runner import ( ArtifactLayout, DEFAULT_CONFIG_PACKET_TYPES, ProtocolGuardDockerError, ProtocolGuardDockerRunner, ProtocolGuardDockerSettings, ProtocolGuardExecutionError, ProtocolGuardNotAvailableError, )

**all** = [ "ArtifactLayout", "DEFAULT_CONFIG_PACKET_TYPES", "ProtocolGuardDockerError", "ProtocolGuardDockerRunner", "ProtocolGuardDockerSettings", "ProtocolGuardExecutionError", "ProtocolGuardNotAvailableError", ]

==================================================================================================== 文件 26: apps/backend-flask/protocol_compliance/\_docker_runner/**init**.py ====================================================================================================

"""Docker orchestration helpers for ProtocolGuard static analysis."""

from .config import ArtifactLayout, DEFAULT_CONFIG_PACKET_TYPES, ProtocolGuardDockerSettings from .errors import ProtocolGuardDockerError, ProtocolGuardExecutionError, ProtocolGuardNotAvailableError from .runner import ProtocolGuardDockerRunner

**all** = [ "ArtifactLayout", "DEFAULT_CONFIG_PACKET_TYPES", "ProtocolGuardDockerError", "ProtocolGuardExecutionError", "ProtocolGuardNotAvailableError", "ProtocolGuardDockerRunner", "ProtocolGuardDockerSettings", ]

==================================================================================================== 文件 27: apps/backend-flask/protocol_compliance/\_docker_runner/config.py ====================================================================================================

"""Configuration helpers for ProtocolGuard Docker integration."""

from **future** import annotations

import os import shlex import tempfile from dataclasses import dataclass from pathlib import Path from typing import Dict, List, Optional, Sequence, Tuple

**all** = [ "ArtifactLayout", "DEFAULT_CONFIG_PACKET_TYPES", "ProtocolGuardDockerSettings", "_default_runtime_root", "_ensure_directory", "_env_bool", "_env_int", "_split_env_list", ]

def \_env_bool(name: str, default: bool = False) -> bool: raw = os.environ.get(name) if raw is None: return default return raw.strip().lower() in {"1", "true", "yes", "on"}

def \_env_int(name: str, default: Optional[int] = None) -> Optional[int]: raw = os.environ.get(name) if raw is None or not raw.strip(): return default try: return int(raw) except ValueError: return default

def \_split_env_list(name: str, default: Sequence[str] = ()) -> Tuple[str, ...]: raw = os.environ.get(name) if not raw: return tuple(default) items = [item.strip() for item in raw.split(",")] return tuple(item for item in items if item)

def \_default_runtime_root() -> Path: base = os.environ.get("PG_RUNTIME_ROOT") if base: return Path(base).expanduser().resolve() return Path(tempfile.gettempdir()) / "protocolguard"

def \_ensure_directory(path: Path) -> Path: path.mkdir(parents=True, exist_ok=True) return path

@dataclass(frozen=True) class ArtifactLayout: """Relative paths inside the workspace for expected ProtocolGuard artefacts."""

    bitcode: Path = Path("program.bc")
    build_log: Path = Path("build_log.txt")
    wpa_report: Path = Path("ffp.txt")
    packet_callgraph: Path = Path("callgraph_report.txt")
    function_summary: Path = Path("function_arg_summary.txt")
    database: Path = Path("database")
    rule_config: Path = Path("inputs/rules.json")
    original_ir: Path = Path("program.ll")
    binary_path: Path = Path("program")

    @classmethod
    def from_env(cls) -> "ArtifactLayout":
        def pick(name: str, default: Path) -> Path:
            value = os.environ.get(name)
            if not value:
                return default
            return Path(value)

        return cls(
            bitcode=pick("PG_ARTIFACT_BITCODE", cls.bitcode),
            build_log=pick("PG_ARTIFACT_BUILD_LOG", cls.build_log),
            wpa_report=pick("PG_ARTIFACT_WPA_REPORT", cls.wpa_report),
            packet_callgraph=pick("PG_ARTIFACT_PACKET_REPORT", cls.packet_callgraph),
            function_summary=pick("PG_ARTIFACT_FUNCTION_SUMMARY", cls.function_summary),
            database=pick("PG_ARTIFACT_DATABASE_DIR", cls.database),
            rule_config=pick("PG_ARTIFACT_RULE_CONFIG", cls.rule_config),
            original_ir=pick("PG_ARTIFACT_ORIGINAL_IR", cls.original_ir),
            binary_path=pick("PG_ARTIFACT_BINARY_PATH", cls.binary_path),
        )

DEFAULT_CONFIG_PACKET_TYPES: Dict[str, List[str]] = { "mqtt_packet_type": [ "CONNECT", "CONNACK", "PUBLISH", "PUBACK", "PUBREC", "PUBREL", "PUBCOMP", "SUBSCRIBE", "SUBACK", "UNSUBSCRIBE", "UNSUBACK", "PINGREQ", "PINGRESP", "DISCONNECT", "AUTH", ], "dhcpv6_packet_type": [ "DHCP6_SOLICIT", "DHCP6_ADVERTISE", "DHCP6_REQUEST", "DHCP6_REPLY", "DHCP6_CONFIRM", "DHCP6_RELEASE", "DHCP6_DECLINE", "DHCP6_RENEW", "DHCP6_REBIND", "DHCP6_IREQ", "DHCP6_RECONFIGURE", "DHCP6_RELAYFORW", "DHCP6_RELAYREPL", ], "coap_packet_type": [ "CONFIRMABLE", "NON_CONFIRMABLE", "ACKNOWLEDGEMENT", "RESET", ], "ftp_packet_type": [ "USER", "PASS", "ACCT", "REIN", "QUIT", "PORT", "PASV", "TYPE", "STRU", "MODE", "RETR", "STOR", "APPE", "DELE", "RNFR", "RNTO", "ABOR", "CWD", "CDUP", "PWD", "MKD", "RMD", "LIST", "NLST", "SYST", "STAT", "FEAT", "HELP", "NOOP", "ALLO", "REST", "MLST", "MLSD", "OPTS", "EPSV", "EPRT", "AUTH", "ADAT", "CCC", "CONF", "ENC", "MIC", "PBSZ", "PROT", ], "tls13_message_type": [ "CLIENT_HELLO", "SERVER_HELLO", "NEW_SESSION_TICKET", "END_OF_EARLY_DATA", "ENCRYPTED_EXTENSIONS", "CERTIFICATE", "CERTIFICATE_REQUEST", "CERTIFICATE_VERIFY", "FINISHED", "KEY_UPDATE", "HELLO_RETRY_REQUEST", ], }

@dataclass(frozen=True) class ProtocolGuardDockerSettings: """Runtime configuration for the Docker integration."""

    enabled: bool
    analysis_image: str
    analysis_command: Tuple[str, ...]
    workspace_root: Path
    output_root: Path
    config_root: Path
    template_workspace: Optional[Path]
    env_passthrough: Tuple[str, ...]
    artifacts: ArtifactLayout
    builder_image: Optional[str]
    builder_command: Optional[Tuple[str, ...]]
    keep_builder_images: bool
    keep_artifacts: bool
    analysis_timeout: Optional[int]
    network: Optional[str]
    project_name: str
    default_protocol_name: str
    default_protocol_version: str
    llm_model_r1: str
    llm_model_v3: str
    llm_query_repeat: int
    llm_query_max_attempts: int
    llm_violation_repeat_times: int
    debug_code_slice_mode: int

    @classmethod
    def from_env(cls) -> "ProtocolGuardDockerSettings":
        enabled = _env_bool("PG_DOCKER_ENABLED", default=True)
        analysis_image = os.environ.get("PG_ANALYSIS_IMAGE", "protocolguard:latest")
        builder_image = os.environ.get("PG_BUILDER_IMAGE") or None

        def parse_command(env_name: str, default: str) -> Tuple[str, ...]:
            raw = os.environ.get(env_name)
            if raw:
                return tuple(shlex.split(raw))
            return tuple(shlex.split(default))

        analysis_command = parse_command("PG_ANALYSIS_COMMAND", "static")
        builder_command_env = os.environ.get("PG_BUILDER_COMMAND")
        builder_command = tuple(shlex.split(builder_command_env)) if builder_command_env else None

        runtime_root = _default_runtime_root()
        workspace_root = Path(os.environ.get("PG_WORKSPACE_ROOT", runtime_root / "workspaces")).expanduser()
        output_root = Path(os.environ.get("PG_OUTPUT_ROOT", runtime_root / "outputs")).expanduser()
        config_root = Path(os.environ.get("PG_CONFIG_ROOT", runtime_root / "configs")).expanduser()

        template_workspace_raw = os.environ.get("PG_TEMPLATE_WORKSPACE")
        template_workspace = Path(template_workspace_raw).expanduser() if template_workspace_raw else None

        env_passthrough = _split_env_list("PG_ENV_VARS", ("OPENAI_API_KEY",))
        artifacts = ArtifactLayout.from_env()
        keep_artifacts = _env_bool("PG_KEEP_ARTIFACTS", default=False)
        keep_builder_images = _env_bool("PG_KEEP_BUILDER_IMAGES", default=False)
        analysis_timeout = _env_int("PG_ANALYSIS_TIMEOUT_SECONDS", None)
        network = os.environ.get("PG_DOCKER_NETWORK") or None

        project_name = os.environ.get("PG_PROJECT_NAME", "protocolguard-project")
        default_protocol_name = os.environ.get("PG_PROTOCOL_NAME", "MQTT")
        default_protocol_version = os.environ.get("PG_PROTOCOL_VERSION", "5")

        llm_model_r1 = os.environ.get("PG_LLM_MODEL_R1", "deepseek-ai/DeepSeek-R1-0528")
        llm_model_v3 = os.environ.get("PG_LLM_MODEL_V3", "deepseek-ai/DeepSeek-V3-0324")
        llm_query_repeat = _env_int("PG_LLM_QUERY_REPEAT", 1) or 1
        llm_query_max_attempts = _env_int("PG_LLM_QUERY_MAX_ATTEMPTS", 10) or 10
        llm_violation_repeat_times = _env_int("PG_LLM_VIOLATION_REPEAT", 3) or 3
        debug_code_slice_mode = _env_int("PG_DEBUG_CODE_SLICE_MODE", 0) or 0

        return cls(
            enabled=enabled,
            analysis_image=analysis_image,
            analysis_command=analysis_command,
            workspace_root=workspace_root,
            output_root=output_root,
            config_root=config_root,
            template_workspace=template_workspace,
            env_passthrough=env_passthrough,
            artifacts=artifacts,
            builder_image=builder_image,
            builder_command=builder_command,
            keep_builder_images=keep_builder_images,
            keep_artifacts=keep_artifacts,
            analysis_timeout=analysis_timeout,
            network=network,
            project_name=project_name,
            default_protocol_name=default_protocol_name,
            default_protocol_version=default_protocol_version,
            llm_model_r1=llm_model_r1,
            llm_model_v3=llm_model_v3,
            llm_query_repeat=llm_query_repeat,
            llm_query_max_attempts=llm_query_max_attempts,
            llm_violation_repeat_times=llm_violation_repeat_times,
            debug_code_slice_mode=debug_code_slice_mode,
        )

==================================================================================================== 文件 28: apps/backend-flask/protocol_compliance/\_docker_runner/errors.py ====================================================================================================

"""Error types for ProtocolGuard Docker integration."""

from **future** import annotations

from typing import List, Optional

**all** = [ "ProtocolGuardDockerError", "ProtocolGuardExecutionError", "ProtocolGuardNotAvailableError", ]

class ProtocolGuardDockerError(RuntimeError): """Base exception for Docker integration errors."""

class ProtocolGuardNotAvailableError(ProtocolGuardDockerError): """Raised when Docker SDK or engine is unavailable."""

class ProtocolGuardExecutionError(ProtocolGuardDockerError): """Raised when the container exits with a non-zero status."""

    def __init__(
        self,
        message: str,
        *,
        logs: Optional[List[str]] = None,
        log_excerpt: Optional[str] = None,
        image: Optional[str] = None,
        status: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.logs = logs or []
        self.log_excerpt = log_excerpt
        self.image = image
        self.status = status

==================================================================================================== 文件 29: apps/backend-flask/protocol_compliance/\_docker_runner/job.py ====================================================================================================

"""Filesystem helpers for ProtocolGuard Docker jobs."""

from **future** import annotations

from dataclasses import dataclass from pathlib import Path

**all** = ["JobPaths"]

@dataclass class JobPaths: job_id: str workspace: Path output: Path config_dir: Path config_file: Path log_file: Path

==================================================================================================== 文件 30: apps/backend-flask/protocol_compliance/\_docker_runner/runner.py ====================================================================================================

"""High-level runner that coordinates ProtocolGuard Docker workloads."""

from **future** import annotations

import contextlib import json import logging import os import shlex import shutil import socket import subprocess import sqlite3 import textwrap import tarfile import time import uuid import zipfile from copy import deepcopy from datetime import datetime, timezone from pathlib import Path from typing import BinaryIO, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import toml

from .config import DEFAULT_CONFIG_PACKET_TYPES, ProtocolGuardDockerSettings, \_ensure_directory, \_env_int from .errors import ProtocolGuardDockerError, ProtocolGuardExecutionError, ProtocolGuardNotAvailableError from .job import JobPaths

try: # pragma: no cover - optional dependency import docker from docker.errors import DockerException, ImageNotFound except ModuleNotFoundError: # pragma: no cover - optional dependency docker = None # type: ignore DockerException = RuntimeError # type: ignore ImageNotFound = RuntimeError # type: ignore

LOGGER = logging.getLogger(**name**)

class ProtocolGuardDockerRunner: """High-level runner that coordinates builder + analysis containers."""

    def __init__(self, settings: ProtocolGuardDockerSettings) -> None:
        self._settings = settings
        if not settings.enabled:
            raise ProtocolGuardNotAvailableError("ProtocolGuard Docker integration is disabled")
        if docker is None:
            raise ProtocolGuardNotAvailableError("python -m pip install docker is required for Docker integration")
        try:
            self._client = docker.from_env()
        except DockerException as exc:  # pragma: no cover - requires docker engine
            raise ProtocolGuardNotAvailableError(f"Unable to connect to Docker engine: {exc}") from exc
        self._progress_callback: Optional[Callable[[str, str, str], None]] = None
        self._current_workspace_snapshots: List[Dict[str, str]] = []

    def _log_step(
        self,
        job_paths: JobPaths,
        stage: str,
        message: str,
        *,
        level: int = logging.INFO,
    ) -> None:
        LOGGER.log(level, "[job %s][%s] %s", job_paths.job_id, stage, message)
        if self._progress_callback:
            try:
                self._progress_callback(job_paths.job_id, stage, message)
            except Exception:  # pragma: no cover - defensive
                LOGGER.debug("Progress callback failed for job %s", job_paths.job_id, exc_info=True)

    # Public API -----------------------------------------------------------------

    def run_static_analysis(
        self,
        *,
        code_stream: BinaryIO,
        code_filename: str,
        builder_stream: BinaryIO,
        builder_filename: str,
        config_stream: BinaryIO,
        config_filename: str,
        rules_stream: BinaryIO,
        rules_filename: str,
        notes: Optional[str],
        protocol_name: Optional[str],
        protocol_version: Optional[str],
        rules_summary: Optional[str],
        job_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
    ) -> Dict[str, object]:
        """Execute the ProtocolGuard static workflow and return a structured response."""
        start = time.time()
        job_id = job_id or str(uuid.uuid4())
        job_paths = self._prepare_job_paths(job_id)
        self._progress_callback = progress_callback
        self._current_workspace_snapshots = []

        self._log_step(job_paths, "init", "Starting ProtocolGuard static analysis job")

        built_builder_image: Optional[str] = None

        try:
            self._log_step(job_paths, "workspace", "Staging workspace directories")
            self._stage_workspace(job_paths)
            self._ensure_workspace_structure(job_paths)
            self._log_step(job_paths, "workspace", "Workspace directories prepared")

            uploads_dir = job_paths.workspace / "uploads"
            code_filename_real = code_filename or "source-archive"
            code_path = self._write_stream(uploads_dir / code_filename_real, code_stream)
            rules_filename_real = rules_filename or self._settings.artifacts.rule_config.name
            builder_filename_real = builder_filename or "Dockerfile"
            config_filename_real = config_filename or "config.toml"

            project_dir = job_paths.workspace / "project"
            self._log_step(job_paths, "workspace", "Preparing project directory for source archive")
            self._reset_directory(project_dir)
            self._extract_archive(code_path, project_dir)
            if not any(project_dir.iterdir()):
                raise ProtocolGuardDockerError(
                    "Source archive did not contain any files. Please verify the uploaded archive."
                )
            self._log_step(job_paths, "workspace", "Source archive extracted")

            dockerfile_path = project_dir / builder_filename_real
            self._log_step(job_paths, "inputs", "Writing builder Dockerfile to workspace")
            self._write_stream(dockerfile_path, builder_stream)

            builder_image = None
            if builder_stream:
                self._log_step(job_paths, "builder", "Building builder image from uploaded Dockerfile")
                builder_image = self._build_builder_image(
                    job_paths=job_paths,
                    context_dir=project_dir,
                    dockerfile_path=dockerfile_path,
                )
                built_builder_image = builder_image
            elif self._settings.builder_image:
                self._log_step(job_paths, "builder", "Using default builder image from environment")
                builder_image = self._settings.builder_image
            else:
                raise ProtocolGuardDockerError(
                    "Builder Dockerfile not provided and no default builder image configured."
                )

            rules_path = self._stage_rules_file(job_paths, rules_stream)
            LOGGER.debug("Staged code archive at %s, project at %s, rules at %s", code_path, project_dir, rules_path)

            self._log_step(job_paths, "config", "Loading and preparing config file")
            config_data = self._load_config(config_stream, config_filename)
            prepared_config = self._prepare_config(
                config_data=config_data,
                job_paths=job_paths,
                protocol_name=protocol_name,
                protocol_version=protocol_version,
            )
            self._write_config(job_paths.config_file, prepared_config)
            self._log_step(job_paths, "config", "Config file written to workspace")

            if builder_image:
                self._log_step(job_paths, "builder", f"Running builder container image {builder_image}")
                self._run_builder(
                    job_paths,
                    image=builder_image,
                    command=self._settings.builder_command,
                )
                self._log_step(job_paths, "builder", "Builder container completed")

            self._log_step(job_paths, "validation", "Validating required artefacts exist before analysis")
            self._validate_required_inputs(job_paths)
            self._log_step(job_paths, "validation", "All required artefacts present")

            self._log_step(
                job_paths,
                "analysis",
                f"Launching analysis container image {self._settings.analysis_image}",
            )
            logs = self._run_analysis(job_paths, command=self._settings.analysis_command)
            self._log_step(job_paths, "analysis", "Analysis container completed successfully")

            self._log_step(job_paths, "results", "Collecting analysis results and metadata")
            result = self._collect_results(
                job_paths=job_paths,
                start_time=start,
                code_filename=Path(code_filename_real).name,
                builder_filename=Path(builder_filename_real).name,
                config_filename=Path(config_filename_real).name,
                notes=notes,
                rules_summary=rules_summary,
                rules_filename=Path(rules_filename_real).name,
                protocol_name=protocol_name,
                protocol_version=protocol_version,
                docker_logs=logs,
                workspace_snapshots=self._current_workspace_snapshots,
            )
            self._log_step(job_paths, "results", "ProtocolGuard job completed successfully")
            return result
        except Exception:
            self._log_step(job_paths, "error", "ProtocolGuard job failed", level=logging.ERROR)
            LOGGER.exception("ProtocolGuard job %s failed", job_id)
            raise
        finally:
            self._progress_callback = None
            self._current_workspace_snapshots = []
            if built_builder_image:
                if self._settings.keep_builder_images:
                    self._log_step(
                        job_paths,
                        "cleanup",
                        f"Retaining builder image {built_builder_image} for Docker cache reuse",
                    )
                else:
                    self._log_step(job_paths, "cleanup", f"Removing temporary builder image {built_builder_image}")
                    self._remove_builder_image(built_builder_image)
            if not self._settings.keep_artifacts:
                self._log_step(job_paths, "cleanup", "Cleaning up workspace artefacts")
                self._cleanup_job(job_paths)

    def run_assert_generation(
        self,
        *,
        code_stream: BinaryIO,
        code_filename: str,
        database_stream: BinaryIO,
        database_filename: str,
        build_instructions: Optional[str],
        notes: Optional[str],
        job_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
    ) -> Dict[str, object]:
        """Execute the ProtocolGuard assertion generation workflow."""

        start = time.time()
        job_id = job_id or str(uuid.uuid4())
        job_paths = self._prepare_job_paths(job_id)
        self._progress_callback = progress_callback
        self._current_workspace_snapshots = []

        self._log_step(job_paths, "init", "Starting ProtocolGuard assertion generation job")

        if not build_instructions or not build_instructions.strip():
            raise ProtocolGuardDockerError("Build instructions are required for assertion generation")

        command = ["assert", "--compile-command", build_instructions.strip()]

        try:
            self._log_step(job_paths, "workspace", "Preparing workspace directories")
            self._reset_directory(job_paths.workspace)
            self._stage_workspace(job_paths)

            uploads_dir = job_paths.workspace / "uploads"
            project_dir = job_paths.workspace / "project"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            project_dir.mkdir(parents=True, exist_ok=True)

            code_filename_real = code_filename or "source-archive"
            self._log_step(job_paths, "workspace", "Persisting uploaded source archive")
            code_path = self._write_stream(uploads_dir / code_filename_real, code_stream)

            self._log_step(job_paths, "workspace", "Extracting source archive into /workspace/project")
            self._reset_directory(project_dir)
            self._extract_archive(code_path, project_dir)
            if not any(project_dir.iterdir()):
                raise ProtocolGuardDockerError(
                    "Source archive did not contain any files. Please verify the uploaded archive."
                )
            self._log_step(job_paths, "workspace", "Source archive extracted into project directory")

            database_filename_real = database_filename or "violations.db"
            database_destination = job_paths.workspace / "violations.db"
            self._log_step(job_paths, "workspace", "Staging SQLite database as /workspace/violations.db")
            self._write_stream(database_destination, database_stream)
            if not database_destination.exists() or database_destination.stat().st_size == 0:
                raise ProtocolGuardDockerError("Uploaded database file is empty. Please verify the input.")

            build_instructions_text = build_instructions.strip() if build_instructions else ""
            if build_instructions_text:
                instructions_path = job_paths.workspace / "build_instructions.txt"
                instructions_path.write_text(build_instructions_text, encoding="utf-8")
                self._log_step(job_paths, "workspace", "Build instructions written to build_instructions.txt")
            else:
                self._log_step(job_paths, "workspace", "No build instructions provided; skipping file write")

            notes_text = notes.strip() if notes else ""
            if notes_text:
                notes_path = job_paths.workspace / "notes.txt"
                notes_path.write_text(notes_text, encoding="utf-8")
                self._log_step(job_paths, "workspace", "Notes written to notes.txt")

            self._snapshot_workspace(job_paths, stage="prepared")

            self._log_step(
                job_paths,
                "analysis",
                f"Launching assertion generation container image {self._settings.analysis_image}",
            )
            logs = self._run_analysis(job_paths, command=command)
            self._log_step(job_paths, "analysis", "Assertion generation container completed successfully")

            assert_tasks_dir = job_paths.output / "assert_tasks"
            if not assert_tasks_dir.exists() or not assert_tasks_dir.is_dir():
                raise ProtocolGuardExecutionError(
                    "Assertion generation completed but assert_tasks directory was not found in /out.",
                    logs=logs,
                    image=self._settings.analysis_image,
                    status=0,
                )

            zip_destination = job_paths.output / "assert_tasks.zip"
            self._log_step(job_paths, "results", "Packaging assert_tasks artefacts into ZIP archive")
            self._zip_directory(assert_tasks_dir, zip_destination)

            self._snapshot_workspace(job_paths, stage="post-run")

            workspace_snapshots = [dict(snapshot) for snapshot in self._current_workspace_snapshots]
            duration_ms = int((time.time() - start) * 1000)
            now_iso = datetime.now(timezone.utc).isoformat()
            assertion_count = self._count_files(assert_tasks_dir)
            protocol_name = self._settings.default_protocol_name

            result: Dict[str, object] = {
                "jobId": job_paths.job_id,
                "generatedAt": now_iso,
                "assertionCount": assertion_count,
                "protocolName": protocol_name,
                "inputs": {
                    "codeFileName": Path(code_filename_real).name,
                    "databaseFileName": Path(database_filename_real).name,
                    "buildInstructions": build_instructions_text or None,
                    "notes": notes_text or None,
                },
                "artifacts": {
                    "workspace": str(job_paths.workspace),
                    "output": str(job_paths.output),
                    "logs": str(job_paths.log_file),
                    "zipPath": str(zip_destination),
                    "database": str(database_destination),
                    "workspaceSnapshots": workspace_snapshots,
                },
                "docker": {
                    "image": self._settings.analysis_image,
                    "command": list(command),
                    "logs": logs,
                    "durationMs": duration_ms,
                },
            }

            self._log_step(job_paths, "results", "Assertion generation completed successfully")
            return result
        except Exception:
            self._log_step(job_paths, "error", "Assertion generation job failed", level=logging.ERROR)
            LOGGER.exception("ProtocolGuard assertion generation job %s failed", job_id)
            raise
        finally:
            self._progress_callback = None
            self._current_workspace_snapshots = []
            if not self._settings.keep_artifacts:
                self._log_step(job_paths, "cleanup", "Cleaning up workspace artefacts")
                self._cleanup_job(job_paths)

    # Workspace preparation ------------------------------------------------------

    def _prepare_job_paths(self, job_id: str) -> JobPaths:
        workspace = _ensure_directory((self._settings.workspace_root / job_id).resolve())
        output = _ensure_directory((self._settings.output_root / job_id).resolve())
        config_dir = _ensure_directory((self._settings.config_root / job_id).resolve())
        config_file = config_dir / "config.toml"
        log_file = output / "analysis.log"
        return JobPaths(
            job_id=job_id,
            workspace=workspace,
            output=output,
            config_dir=config_dir,
            config_file=config_file,
            log_file=log_file,
        )

    def _stage_workspace(self, job_paths: JobPaths) -> None:
        if self._settings.template_workspace:
            LOGGER.debug(
                "Seeding workspace %s from template %s",
                job_paths.workspace,
                self._settings.template_workspace,
            )
            self._copy_tree(self._settings.template_workspace, job_paths.workspace)

    def _copy_tree(self, source: Path, destination: Path) -> None:
        if not source.exists():
            LOGGER.warning("Template workspace %s does not exist; skipping copy", source)
            return
        for item in source.iterdir():
            dest_path = destination / item.name
            if item.is_dir():
                shutil.copytree(item, dest_path, dirs_exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_path)

    def _write_stream(self, destination: Path, stream: BinaryIO) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(Exception):
            stream.seek(0)
        with destination.open("wb") as handle:
            shutil.copyfileobj(stream, handle)
        return destination

    def _reset_directory(self, target: Path) -> None:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

    def _ensure_workspace_structure(self, job_paths: JobPaths) -> None:
        workspace = job_paths.workspace
        artifacts = self._settings.artifacts
        for relative in (
            artifacts.bitcode,
            artifacts.build_log,
            artifacts.wpa_report,
            artifacts.packet_callgraph,
            artifacts.function_summary,
            artifacts.rule_config,
        ):
            (workspace / relative).parent.mkdir(parents=True, exist_ok=True)
        database_dir = workspace / artifacts.database
        database_dir.mkdir(parents=True, exist_ok=True)

    def _extract_archive(self, archive: Path, destination: Path) -> None:
        if tarfile.is_tarfile(archive):
            with tarfile.open(archive, "r:*") as tar:
                self._safe_extract_tar(tar, destination)
            return
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive, "r") as zip_file:
                self._safe_extract_zip(zip_file, destination)
            return
        shutil.copy2(archive, destination / archive.name)

    def _safe_extract_tar(self, tar_obj: tarfile.TarFile, destination: Path) -> None:
        for member in tar_obj.getmembers():
            member_path = destination / member.name
            if not self._is_within_directory(destination, member_path):
                raise ProtocolGuardDockerError(
                    f"Tar archive contains unsafe path traversal entry: {member.name}"
                )
        tar_obj.extractall(destination)

    def _safe_extract_zip(self, zip_obj: zipfile.ZipFile, destination: Path) -> None:
        for member in zip_obj.namelist():
            member_path = destination / member
            if not self._is_within_directory(destination, member_path):
                raise ProtocolGuardDockerError(
                    f"Zip archive contains unsafe path traversal entry: {member}"
                )
        zip_obj.extractall(destination)

    def _is_within_directory(self, base: Path, target: Path) -> bool:
        try:
            target.resolve(strict=False).relative_to(base.resolve(strict=False))
            return True
        except ValueError:
            return False

    def _stage_rules_file(self, job_paths: JobPaths, stream: BinaryIO) -> Path:
        rules_path = job_paths.workspace / self._settings.artifacts.rule_config
        return self._write_stream(rules_path, stream)

    def _load_config(self, stream: BinaryIO, filename: str) -> Dict[str, object]:
        with contextlib.suppress(Exception):
            stream.seek(0)
        raw = stream.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProtocolGuardDockerError(
                f"Configuration file {filename!r} must be UTF-8 encoded."
            ) from exc
        try:
            data = toml.loads(text)
        except toml.TomlDecodeError as exc:
            raise ProtocolGuardDockerError(
                f"Failed to parse configuration file {filename!r}: {exc}"
            ) from exc
        return data

    def _prepare_config(
        self,
        *,
        config_data: Dict[str, object],
        job_paths: JobPaths,
        protocol_name: Optional[str],
        protocol_version: Optional[str],
    ) -> Dict[str, object]:
        data: Dict[str, object] = deepcopy(config_data)
        artifacts = self._settings.artifacts
        protocol = protocol_name or self._settings.default_protocol_name
        version = protocol_version or self._settings.default_protocol_version
        workspace_prefix = "/workspace"

        def container_path(relative: Path) -> str:
            rel = relative.as_posix()
            if rel in ("", "."):
                return workspace_prefix
            return f"{workspace_prefix}/{rel}"

        project_section = dict(data.get("project") or {})
        project_section["project_name"] = project_section.get("project_name") or self._settings.project_name
        project_section["project_path"] = f"{workspace_prefix}/project"
        project_section["protocol_name"] = protocol
        project_section["protocol_version"] = version
        project_section["bitcode_path"] = container_path(artifacts.bitcode)
        project_section["binary_path"] = container_path(artifacts.binary_path)
        project_section["build_log_path"] = container_path(artifacts.build_log)
        project_section["original_llvm_ir_path"] = container_path(artifacts.original_ir)
        project_section["packet_related_callgraph_path"] = container_path(artifacts.packet_callgraph)
        project_section["function_arg_path"] = container_path(artifacts.function_summary)
        project_section["rule_path"] = container_path(artifacts.rule_config)
        data["project"] = project_section

        database_section = dict(data.get("database") or {})
        database_section["path"] = container_path(artifacts.database)
        data["database"] = database_section

        wpa_section = dict(data.get("wpa") or {})
        wpa_section["path"] = container_path(artifacts.wpa_report)
        data["wpa"] = wpa_section

        debug_section = dict(data.get("debug") or {})
        debug_section["code_slice_replace_mode"] = self._settings.debug_code_slice_mode
        debug_section["log_print"] = _env_int("PG_DEBUG_LOG_PRINT", 0) or 0
        data["debug"] = debug_section

        config_section = dict(data.get("config") or {})
        for key, values in DEFAULT_CONFIG_PACKET_TYPES.items():
            config_section.setdefault(key, list(values))
        data["config"] = config_section

        return data

    def _build_builder_image(
        self,
        *,
        job_paths: JobPaths,
        context_dir: Path,
        dockerfile_path: Path,
    ) -> str:
        try:
            dockerfile_rel = dockerfile_path.relative_to(context_dir)
        except ValueError as exc:
            raise ProtocolGuardDockerError(
                f"Builder Dockerfile {dockerfile_path} must reside within the uploaded project directory."
            ) from exc

        tag = f"protocolguard-builder:{job_paths.job_id}"
        self._log_step(
            job_paths,
            "builder",
            f"Using docker CLI (BuildKit) for builder image (tag={tag}, context={context_dir}, dockerfile={dockerfile_rel})",
        )

        proxy_url = self._detect_builder_proxy()
        if proxy_url:
            self._log_step(
                job_paths,
                "proxy",
                f"✓ Proxy detected and will be configured: {proxy_url}",
            )
        else:
            self._log_step(
                job_paths,
                "proxy",
                "✗ No proxy detected on port 63333 - building without proxy",
            )
        try:
            return self._build_builder_image_with_cli(
                job_paths=job_paths,
                context_dir=context_dir,
                dockerfile_rel=dockerfile_rel,
                tag=tag,
                proxy_url=proxy_url,
            )
        except ProtocolGuardDockerError:
            raise

    def _build_builder_image_with_cli(
        self,
        *,
        job_paths: JobPaths,
        context_dir: Path,
        dockerfile_rel: Path,
        tag: str,
        proxy_url: Optional[str] = None,
    ) -> str:
        env = {str(k): str(v) for k, v in os.environ.items()}
        env.setdefault("DOCKER_BUILDKIT", "1")
        env.setdefault("BUILDKIT_PROGRESS", "plain")

        # Type 4: Proxy provided by the SHELL when Docker process runs
        # Set proxy environment variables if port 63333 is responsive
        if proxy_url:
            self._log_step(
                job_paths,
                "proxy",
                f"[Type 4] Setting shell proxy environment (HTTP_PROXY, HTTPS_PROXY, http_proxy, https_proxy) = {proxy_url}",
            )
            for proxy_var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                env.setdefault(proxy_var, proxy_url)
        command = [
            "docker",
            "build",
            "--progress=plain",
            "--file",
            str(dockerfile_rel),
            "--tag",
            tag,
        ]
        if proxy_url:
            self._log_step(
                job_paths,
                "proxy",
                f"[Type 1] Setting Docker CLI build-args (HTTP_PROXY, HTTPS_PROXY, http_proxy, https_proxy) = {proxy_url}",
            )
            command.append("--network=host")
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                command.extend(["--build-arg", f"{key}={proxy_url}"])

        # Log comprehensive proxy status summary
        proxy_summary = self._build_proxy_summary(proxy_url)
        self._log_step(job_paths, "proxy", f"Proxy Configuration Summary:\n{proxy_summary}")

        command.append(".")
        self._log_step(job_paths, "builder", f"Retrying builder image {tag} using docker CLI with BuildKit enabled")
        try:
            process = subprocess.Popen(
                command,
                cwd=str(context_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                text=True,
            )
        except OSError as exc:
            raise ProtocolGuardDockerError(f"Failed to invoke docker CLI for builder image build: {exc}") from exc

        assert process.stdout is not None
        with job_paths.log_file.open("a", encoding="utf-8") as log_file:
            try:
                for line in process.stdout:
                    text = line.rstrip()
                    if text:
                        log_file.write(text + "\n")
                        self._log_step(job_paths, "builder-log", text)
            finally:
                process.stdout.close()
        exit_code = process.wait()
        if exit_code != 0:
            raise ProtocolGuardDockerError(
                f"Docker CLI build failed for builder image {tag} with exit code {exit_code}."
            )
        self._log_step(job_paths, "builder", f"docker CLI build completed for {tag}")
        return tag

    @staticmethod
    def _detect_builder_proxy(host: str = "127.0.0.1", port: int = 63333, timeout: float = 0.5) -> Optional[str]:
        """
        Detect if a proxy is available on the specified port.
        This checks port 63333 by default for proxy availability.
        """
        LOGGER.info("🔍 Checking for proxy availability on %s:%s (timeout=%.1fs)", host, port, timeout)
        try:
            with contextlib.closing(socket.create_connection((host, port), timeout=timeout)):
                proxy_url = f"http://{host}:{port}"
                LOGGER.info("✓ Proxy is RESPONSIVE on %s:%s → Will use: %s", host, port, proxy_url)
                return proxy_url
        except OSError as exc:
            LOGGER.info("✗ Proxy is NOT responsive on %s:%s → Building WITHOUT proxy (reason: %s)", host, port, exc)
            return None

    @staticmethod
    def _build_proxy_summary(proxy_url: Optional[str]) -> str:
        """
        Build a human-readable summary of Docker proxy configuration status.
        Explains which of the 4 proxy types are configured.
        """
        if proxy_url:
            return textwrap.dedent(f"""\
                ┌─────────────────────────────────────────────────────────────┐
                │ Docker Proxy Configuration Status (Port 63333 RESPONSIVE)  │
                ├─────────────────────────────────────────────────────────────┤
                │ [Type 1] Docker CLI Build Args      : ✓ ENABLED ({proxy_url})
                │ [Type 2] Docker Daemon Config       : ⊗ NOT CONFIGURABLE
                │ [Type 3] Inside Container Proxy     : ⊗ NOT SET (Dockerfile only)
                │ [Type 4] Shell Environment Proxy    : ✓ ENABLED ({proxy_url})
                └─────────────────────────────────────────────────────────────┘
                """).strip()
        else:
            return textwrap.dedent("""\
                ┌─────────────────────────────────────────────────────────────┐
                │ Docker Proxy Configuration Status (Port 63333 NOT DETECTED)│
                ├─────────────────────────────────────────────────────────────┤
                │ [Type 1] Docker CLI Build Args      : ✗ DISABLED
                │ [Type 2] Docker Daemon Config       : ⊗ NOT CONFIGURABLE
                │ [Type 3] Inside Container Proxy     : ⊗ NOT SET (Dockerfile only)
                │ [Type 4] Shell Environment Proxy    : ✗ DISABLED
                └─────────────────────────────────────────────────────────────┘
                """).strip()

    def _remove_builder_image(self, tag: str) -> None:
        if not tag or docker is None:
            return
        try:
            self._client.images.remove(tag, force=True)
            LOGGER.debug("Removed temporary builder image %s", tag)
        except DockerException as exc:
            LOGGER.warning("Failed to remove builder image %s: %s", tag, exc)

    # Container orchestration ----------------------------------------------------

    def _build_volumes(self, job_paths: JobPaths, *, include_config: bool) -> Mapping[str, Mapping[str, str]]:
        volumes: Dict[str, Dict[str, str]] = {
            str(job_paths.workspace): {"bind": "/workspace", "mode": "rw"},
            str(job_paths.output): {"bind": "/out", "mode": "rw"},
        }
        if include_config:
            volumes[str(job_paths.config_dir)] = {"bind": "/config", "mode": "ro"}
        return volumes

    def _build_environment(self) -> Dict[str, str]:
        env: Dict[str, str] = {}
        for name in self._settings.env_passthrough:
            value = os.environ.get(name)
            if value is not None:
                env[name] = value
        return env

    def _snapshot_workspace(self, job_paths: JobPaths, *, stage: str) -> Optional[Path]:
        slug = f"{stage}-{uuid.uuid4().hex[:8]}"
        snapshot_root = _ensure_directory(
            (self._settings.output_root / "_workspace_snapshots" / job_paths.job_id).resolve()
        )
        destination = snapshot_root / slug
        try:
            shutil.copytree(job_paths.workspace, destination)
        except Exception as exc:  # pragma: no cover - defensive
            self._log_step(
                job_paths,
                "workspace-snapshot",
                f"Failed to capture workspace snapshot for stage {stage}: {exc}",
                level=logging.WARNING,
            )
            return None

        self._log_step(
            job_paths,
            "workspace-snapshot",
            f"Workspace snapshot for stage {stage} stored at {destination}",
        )
        self._current_workspace_snapshots.append({"stage": stage, "path": str(destination)})
        return destination

    def _run_builder(
        self,
        job_paths: JobPaths,
        *,
        image: str,
        command: Optional[Sequence[str]] = None,
    ) -> None:
        if not image:
            raise ProtocolGuardDockerError("Builder image is required to execute the ProtocolGuard pipeline.")
        self._log_step(
            job_paths,
            "builder",
            f"Starting builder container (image={image}, command={' '.join(command) if command else '<default>'})",
        )
        self._run_container(
            job_paths=job_paths,
            image=image,
            command=command,
            volumes=self._build_volumes(job_paths, include_config=False),
            environment=self._build_environment(),
            log_destination=job_paths.log_file,
        )
        self._snapshot_workspace(job_paths, stage="builder")

    def _run_analysis(self, job_paths: JobPaths, *, command: Sequence[str]) -> List[str]:
        command_display = " ".join(command) if command else "<default>"
        self._log_step(
            job_paths,
            "analysis",
            f"Starting analysis container (image={self._settings.analysis_image}, command={command_display})",
        )
        volumes = self._build_volumes(job_paths, include_config=True)
        environment = self._build_environment()

        self._inspect_analysis_workspace(job_paths, volumes=volumes, environment=environment)
        logs = self._run_container(
            image=self._settings.analysis_image,
            command=command,
            job_paths=job_paths,
            volumes=volumes,
            environment=environment,
            log_destination=job_paths.log_file,
            timeout=self._settings.analysis_timeout,
        )
        self._snapshot_workspace(job_paths, stage="main")
        return logs

    def _inspect_analysis_workspace(
        self,
        job_paths: JobPaths,
        *,
        volumes: Mapping[str, Mapping[str, str]],
        environment: Mapping[str, str],
    ) -> None:
        preview_command = textwrap.dedent(
            """\
            set -eu
            echo '[pg-debug] ===== workspace mount inspection ====='
            echo '[pg-debug] container pwd: ' "$(pwd)"
            if [ -d /workspace ]; then
              echo '[pg-debug] ls -al /workspace'
              ls -al /workspace
              echo '[pg-debug] tree -a -L 2 /workspace'
              tree -a -L 2 /workspace || (echo '[pg-debug] tree failed - falling back to find'; find /workspace -maxdepth 2 -mindepth 1 -print || true)
            else
              echo '[pg-debug] /workspace directory missing'
            fi
            """
        ).strip()

        try:
            image_details = self._client.images.get(self._settings.analysis_image)
        except ImageNotFound:
            self._log_step(
                job_paths,
                "analysis-debug",
                f"Skipping workspace inspection: analysis image {self._settings.analysis_image} not found locally",
                level=logging.WARNING,
            )
            return
        except DockerException as exc:  # pragma: no cover - requires docker engine
            self._log_step(
                job_paths,
                "analysis-debug",
                f"Failed to resolve analysis image {self._settings.analysis_image}: {exc}",
                level=logging.WARNING,
            )
            return

        # Prefer the tagged reference for readability; fall back to image ID.
        image_reference = self._settings.analysis_image or image_details.id
        # Some Docker SDK versions are finicky about entrypoint types; try robust fallbacks.
        run_attempts = [
            {"entrypoint": ["/bin/sh", "-lc"], "command": [preview_command]},
            {"entrypoint": ["bash", "-lc"], "command": [preview_command]},
            {"entrypoint": "/bin/sh", "command": ["-c", preview_command]},
        ]

        last_error: Optional[Exception] = None
        for attempt in run_attempts:
            try:
                output = self._client.containers.run(
                    image=image_reference,
                    entrypoint=attempt["entrypoint"],
                    command=attempt["command"],
                    volumes=volumes,
                    environment=environment,
                    stdout=True,
                    stderr=True,
                    remove=True,
                    network=self._settings.network,
                )
                break
            except DockerException as exc:  # pragma: no cover - requires docker engine
                last_error = exc
                continue
        else:
            # All attempts failed; log the last error and continue without inspection.
            self._log_step(
                job_paths,
                "analysis-debug",
                f"Failed to inspect /workspace mount before analysis: {last_error}",
                level=logging.WARNING,
            )
            return

        if not output:
            self._log_step(job_paths, "analysis-debug", "Workspace inspection produced no output")
            return

        if isinstance(output, bytes):
            lines = output.decode("utf-8", errors="replace").splitlines()
        else:
            lines = str(output).splitlines()

        with job_paths.log_file.open("a", encoding="utf-8") as log_file:
            for raw_line in lines:
                line = raw_line.rstrip()
                if not line:
                    continue
                log_file.write(line + "\n")
                display_line = line if len(line) <= 2000 else f"{line[:2000]}..."
                self._log_step(job_paths, "analysis-debug", display_line)

    def _run_container(
        self,
        *,
        job_paths: JobPaths,
        image: str,
        command: Optional[Sequence[str]],
        volumes: Mapping[str, Mapping[str, str]],
        environment: Mapping[str, str],
        log_destination: Path,
        timeout: Optional[int] = None,
    ) -> List[str]:
        if not volumes:
            raise ProtocolGuardDockerError("No volumes specified for container execution")
        try:
            container = self._client.containers.run(
                image=image,
                command=list(command) if command else None,
                volumes=volumes,
                environment=environment,
                detach=True,
                remove=True,
                stdout=True,
                stderr=True,
                network=self._settings.network,
            )
        except DockerException as exc:  # pragma: no cover - requires docker engine
            raise ProtocolGuardDockerError(f"Failed to start container {image}: {exc}") from exc
        self._log_step(job_paths, "container", f"Container {container.id[:12]} started for image {image}")

        logs: List[str] = []
        with log_destination.open("a", encoding="utf-8") as log_file:
            for chunk in container.logs(stream=True, follow=True):
                line = chunk.decode("utf-8", errors="replace").rstrip()
                log_file.write(line + "\n")
                logs.append(line)
                if line:
                    display_line = line if len(line) <= 2000 else f"{line[:2000]}..."
                    self._log_step(
                        job_paths,
                        "container-log",
                        f"{image}: {display_line}",
                    )

        try:
            result = container.wait(timeout=timeout)
        except DockerException as exc:  # pragma: no cover - requires docker engine
            container.remove(force=True)
            raise ProtocolGuardDockerError(f"Failed waiting for container exit: {exc}") from exc

        status = result.get("StatusCode", 1)
        if status != 0:
            excerpt = "\n".join(logs[-40:]) if logs else None
            self._log_step(
                job_paths,
                "container",
                f"Container for image {image} exited with status {status}",
                level=logging.ERROR,
            )
            raise ProtocolGuardExecutionError(
                f"Container {image} exited with status {status}",
                logs=logs,
                log_excerpt=excerpt,
                image=image,
                status=status,
            )
        self._log_step(job_paths, "container", f"Container for image {image} exited cleanly")
        return logs

    # Validation ----------------------------------------------------------------

    def _validate_required_inputs(self, job_paths: JobPaths) -> None:
        workspace = job_paths.workspace
        artefacts = {
            "bitcode": workspace / self._settings.artifacts.bitcode,
            "build log": workspace / self._settings.artifacts.build_log,
        }
        missing = [label for label, path in artefacts.items() if not path.exists()]
        self._log_step(job_paths, "container", f"Validating required artefacts: {str(artefacts)}")
        if missing:
            raise ProtocolGuardDockerError(
                f"Missing required artefacts before analysis: {', '.join(missing)}"
            )

    # Config generation ----------------------------------------------------------

    def _build_config(
        self,
        *,
        job_paths: JobPaths,
        rules_path: Path,
        protocol_name: Optional[str],
        protocol_version: Optional[str],
    ) -> Dict[str, object]:
        workspace = job_paths.workspace
        artifacts = self._settings.artifacts
        protocol = protocol_name or self._settings.default_protocol_name
        version = protocol_version or self._settings.default_protocol_version
        project_name = self._settings.project_name

        database_path = workspace / artifacts.database

        config: Dict[str, object] = {
            "wpa": {
                "path": str((workspace / artifacts.wpa_report).resolve()),
            },
            "database": {
                "path": str(database_path.resolve()),
            },
            "llm": {
                "llm_api_platform": os.environ.get("PG_LLM_API_BASE", "https://example.com/v1/chat/completions"),
                "llm_model_deepseek_v3": self._settings.llm_model_v3,
                "llm_model_deepseek_r1": self._settings.llm_model_r1,
                "llm_query_repeat_times": self._settings.llm_query_repeat,
                "llm_query_max_attempts": self._settings.llm_query_max_attempts,
                "llm_violation_repeat_times": self._settings.llm_violation_repeat_times,
                "llm_multithread": _env_int("PG_LLM_MAX_THREADS", 32) or 32,
            },
            "project": {
                "project_path": str(workspace.resolve()),
                "packet_related_callgraph_path": str((workspace / artifacts.packet_callgraph).resolve()),
                "function_arg_path": str((workspace / artifacts.function_summary).resolve()),
                "rule_path": str(rules_path.resolve()),
                "protocol_name": protocol,
                "protocol_version": version,
                "project_name": project_name,
                "original_llvm_ir_path": str((workspace / artifacts.original_ir).resolve()),
                "binary_path": str((workspace / artifacts.binary_path).resolve()),
                "bitcode_path": str((workspace / artifacts.bitcode).resolve()),
                "build_log_path": str((workspace / artifacts.build_log).resolve()),
            },
            "debug": {
                "code_slice_replace_mode": self._settings.debug_code_slice_mode,
                "log_print": _env_int("PG_DEBUG_LOG_PRINT", 0) or 0,
            },
            "config": {key: list(values) for key, values in DEFAULT_CONFIG_PACKET_TYPES.items()},
        }
        return config

    def _write_config(self, destination: Path, config_data: Mapping[str, object]) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as handle:
            toml.dump(config_data, handle)

    # Result collation -----------------------------------------------------------

    def _collect_results(
        self,
        *,
        job_paths: JobPaths,
        start_time: float,
        code_filename: str,
        builder_filename: str,
        config_filename: str,
        notes: Optional[str],
        rules_summary: Optional[str],
        rules_filename: str,
        protocol_name: Optional[str],
        protocol_version: Optional[str],
        docker_logs: List[str],
        workspace_snapshots: Sequence[Mapping[str, str]],
    ) -> Dict[str, object]:
        end = time.time()
        protocol = protocol_name or self._settings.default_protocol_name
        version = protocol_version or self._settings.default_protocol_version

        db_path = self._find_database(job_paths)
        findings, summary_counts = self._extract_findings(db_path, protocol, version)

        if not findings:
            raise ProtocolGuardExecutionError(
                "ProtocolGuard analysis completed but no findings were produced",
                logs=docker_logs,
            )

        overall_status = self._determine_overall_status(summary_counts)
        now_iso = datetime.now(timezone.utc).isoformat()

        summary_notes = notes or rules_summary or "ProtocolGuard static analysis completed via Docker integration."

        result: Dict[str, object] = {
            "analysisId": job_paths.job_id,
            "durationMs": int((end - start_time) * 1000),
            "inputs": {
                "codeFileName": code_filename,
                "builderDockerfileName": builder_filename,
                "configFileName": config_filename,
                "notes": notes or None,
                "protocolName": protocol,
                "rulesFileName": rules_filename,
                "rulesSummary": rules_summary or None,
            },
            "model": self._settings.analysis_image,
            "modelResponse": {
                "metadata": {
                    "generatedAt": now_iso,
                    "modelVersion": self._settings.analysis_image,
                    "protocol": protocol,
                    "ruleSet": rules_filename,
                    "protocolVersion": version,
                },
                "summary": {
                    "compliantCount": summary_counts["compliant"],
                    "needsReviewCount": summary_counts["needs_review"],
                    "nonCompliantCount": summary_counts["non_compliant"],
                    "notes": summary_notes,
                    "overallStatus": overall_status,
                },
                "verdicts": findings,
            },
            "submittedAt": now_iso,
            "artifacts": {
                "workspace": str(job_paths.workspace),
                "output": str(job_paths.output),
                "config": str(job_paths.config_file),
                "logs": str(job_paths.log_file),
                "database": str(db_path) if db_path else None,
                "workspaceSnapshots": [dict(snapshot) for snapshot in workspace_snapshots],
            },
        }
        return result

    def _find_database(self, job_paths: JobPaths) -> Optional[Path]:
        candidates = list(job_paths.output.rglob("*.db"))
        if not candidates:
            candidates = list(job_paths.workspace.rglob("*.db"))
        if not candidates:
            return None
        return candidates[0]

    def _zip_directory(self, source: Path, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        root_parent = source.parent
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for folder_path, dirnames, filenames in os.walk(source):
                folder = Path(folder_path)
                rel_dir = folder.relative_to(root_parent).as_posix()
                zip_file.writestr(f"{rel_dir}/", "")
                for filename in filenames:
                    abs_path = folder / filename
                    arcname = abs_path.relative_to(root_parent).as_posix()
                    zip_file.write(abs_path, arcname)
        return destination

    def _count_files(self, directory: Path) -> int:
        return sum(1 for path in directory.rglob("*") if path.is_file())

    def _extract_findings(
        self,
        db_path: Optional[Path],
        protocol_name: str,
        protocol_version: str,
    ) -> Tuple[List[Dict[str, object]], Dict[str, int]]:
        findings: List[Dict[str, object]] = []
        counts = {"compliant": 0, "needs_review": 0, "non_compliant": 0}

        if db_path is None or not db_path.exists():
            LOGGER.warning("No SQLite database found in analysis outputs")
            return findings, counts

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT rowid, rule_desc, llm_response FROM rule_code_snippet")
            except sqlite3.DatabaseError as exc:
                LOGGER.warning("Unable to query rule_code_snippet table: %s", exc)
                return findings, counts

            rows = cursor.fetchall()

        for index, (row_id, rule_desc, llm_response) in enumerate(rows, start=1):
            compliance, rule_findings = self._parse_llm_response(
                llm_response,
                rule_desc,
                protocol_name,
                protocol_version,
                index,
            )
            counts[compliance] += 1
            findings.extend(rule_findings)

        return findings, counts

    def _parse_llm_response(
        self,
        llm_response: Optional[str],
        rule_desc: str,
        protocol_name: str,
        protocol_version: str,
        index: int,
    ) -> Tuple[str, List[Dict[str, object]]]:
        compliance = "needs_review"
        verdicts: List[Dict[str, object]] = []

        if not llm_response:
            LOGGER.debug("Empty LLM response for rule %s", rule_desc)
            return compliance, verdicts

        try:
            payload = json.loads(llm_response)
        except json.JSONDecodeError:
            LOGGER.warning("Failed to decode LLM response for rule %s", rule_desc)
            return compliance, verdicts

        result = str(payload.get("result", "")).lower()
        reason = str(payload.get("reason", "")).strip()
        violations = payload.get("violations")

        if "violation" in result:
            compliance = "non_compliant"
        elif "no violation" in result:
            compliance = "compliant"
        else:
            compliance = "needs_review"

        if isinstance(violations, list) and violations:
            for violation in violations:
                verdicts.append(
                    self._build_verdict_entry(
                        compliance=compliance,
                        reason=reason,
                        violation=violation,
                        rule_desc=rule_desc,
                        protocol_name=protocol_name,
                        protocol_version=protocol_version,
                        index=index,
                    )
                )
        else:
            verdicts.append(
                self._build_verdict_entry(
                    compliance=compliance,
                    reason=reason,
                    violation=None,
                    rule_desc=rule_desc,
                    protocol_name=protocol_name,
                    protocol_version=protocol_version,
                    index=index,
                )
            )

        return compliance, verdicts

    def _build_verdict_entry(
        self,
        *,
        compliance: str,
        reason: str,
        violation: Optional[Mapping[str, object]],
        rule_desc: str,
        protocol_name: str,
        protocol_version: str,
        index: int,
    ) -> Dict[str, object]:
        line_range: Optional[List[int]] = None
        location_file: Optional[str] = None
        location_function: Optional[str] = None

        if violation and isinstance(violation, Mapping):
            lines = violation.get("code_lines")
            if isinstance(lines, list) and lines:
                numeric = [int(line) for line in lines if isinstance(line, (int, float))]
                if numeric:
                    line_range = [min(numeric), max(numeric)]
            file_name = violation.get("filename")
            if isinstance(file_name, str):
                location_file = file_name
            function_name = violation.get("function_name")
            if isinstance(function_name, str):
                location_function = function_name

        verdict = {
            "category": "LLM Rule Compliance",
            "compliance": compliance,
            "confidence": "medium",
            "explanation": reason or "ProtocolGuard did not provide additional context.",
            "findingId": str(uuid.uuid4()),
            "location": {
                "file": location_file or "",
                "function": location_function or None,
            },
            "recommendation": None,
            "relatedRule": {
                "id": f"RULE-{index:03d}",
                "requirement": rule_desc,
                "source": f"{protocol_name} {protocol_version}".strip(),
            },
        }
        if line_range:
            verdict["lineRange"] = line_range
        return verdict

    def _determine_overall_status(self, counts: Mapping[str, int]) -> str:
        if counts.get("non_compliant", 0):
            return "non_compliant"
        if counts.get("needs_review", 0):
            return "needs_review"
        return "compliant"

    # Cleanup -------------------------------------------------------------------

    def _cleanup_job(self, job_paths: JobPaths) -> None:
        for path in (job_paths.workspace, job_paths.output, job_paths.config_dir):
            with contextlib.suppress(Exception):
                shutil.rmtree(path)
