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

const historyColumns: HistoryColumn[] = [
  { dataIndex: 'jobId', key: 'jobId', title: '任务 ID', width: 220 },
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

function formatFileSize(bytes: null | number | undefined) {
  if (!bytes || bytes <= 0) {
    return '0 B';
  }
  const units = ['B', 'KB', 'MB', 'GB'];
  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** exponent;
  const digits = value >= 10 || exponent === 0 ? 0 : 1;
  return `${value.toFixed(digits)} ${units[exponent]}`;
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

const configMeta = computed(() => {
  const file = formState.config;
  if (!file) {
    return null;
  }
  return {
    name: file.name,
    size: formatFileSize(file.size),
    updatedAt: formatter.format(file.lastModified),
  };
});

const builderMeta = computed(() => {
  const file = formState.builder;
  if (!file) {
    return null;
  }
  return {
    name: file.name,
    size: formatFileSize(file.size),
    updatedAt: formatter.format(file.lastModified),
  };
});

const archiveMeta = computed(() => {
  const file = formState.archive;
  if (!file) {
    return null;
  }
  return {
    name: file.name,
    size: formatFileSize(file.size),
    updatedAt: formatter.format(file.lastModified),
  };
});

const rulesMeta = computed(() => {
  const file = formState.rules;
  if (!file) {
    return null;
  }
  return {
    name: file.name,
    size: formatFileSize(file.size),
    updatedAt: formatter.format(file.lastModified),
  };
});

const hasSelection = computed(() =>
  Boolean(
    configMeta.value ||
      archiveMeta.value ||
      builderMeta.value ||
      rulesMeta.value ||
      formState.notes.trim(),
  ),
);

const analysisSummary = computed(
  () => analysisResult.value?.modelResponse.summary ?? null,
);
const analysisMetadata = computed(
  () => analysisResult.value?.modelResponse.metadata ?? null,
);
const analysisVerdictCount = computed(
  () => analysisResult.value?.modelResponse.verdicts.length ?? 0,
);
const analysisStatusLabel = computed(() => {
  const status = analysisSummary.value?.overallStatus ?? '';
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

function applyProgressSnapshot(snapshot: ProtocolStaticAnalysisJob) {
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

function resetProgressState() {
  stopPolling();
  activeJob.value = null;
  activeJobId.value = null;
  progressLogs.value = [];
  progressError.value = null;
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
  const snapshot = await fetchProtocolStaticAnalysisProgress(jobId);
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
    description="上传源码压缩包、Builder Dockerfile、协议规则 JSON 与分析配置，一键调度 ProtocolGuard Docker 流水线。"
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
                  <Button block type="dashed">选择源码压缩包</Button>
                </Upload>
              </FormItem>

              <FormItem label="Builder Dockerfile" name="builder" required>
                <Upload
                  :before-upload="handleBuilderBeforeUpload"
                  :file-list="builderFileList"
                  :max-count="1"
                  :on-remove="handleBuilderRemove"
                >
                  <Button block type="dashed">选择 Dockerfile</Button>
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
                  <Button block type="dashed">选择规则 JSON</Button>
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
                  <Button block type="dashed">选择配置文件</Button>
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
                <Button @click="handleReset">清空</Button>
                <Button
                  :loading="isSubmitting"
                  type="primary"
                  @click="handleSubmit"
                >
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
              复制日志
            </Button>
          </template>
          <div class="progress-box">
            <Space class="progress-status" wrap>
              <Tag :color="progressStatusColor">{{ progressStatusLabel }}</Tag>
              <span class="progress-message">{{ progressMessage }}</span>
            </Space>
            <div
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

      <Card v-if="analysisResult" title="最新分析结果">
        <Descriptions bordered :column="1" size="small">
          <Descriptions.Item label="整体评估">
            <div class="analysis-overview">
              <span
                class="status-tag"
                :class="[
                  `status-${analysisSummary?.overallStatus ?? 'unknown'}`,
                ]"
              >
                {{ analysisStatusLabel }}
              </span>
              <span class="analysis-detail">
                合规 {{ analysisSummary?.compliantCount ?? 0 }} · 需复核
                {{ analysisSummary?.needsReviewCount ?? 0 }} · 不合规
                {{ analysisSummary?.nonCompliantCount ?? 0 }}
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
              <template v-if="column.key === 'jobId'">
                <TypographyParagraph
                  :copyable="{ text: record.jobId }"
                  :ellipsis="{ rows: 1, tooltip: record.jobId }"
                  class="history-job"
                >
                  {{ record.jobId }}
                </TypographyParagraph>
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
                  <template v-if="historyInsightErrors[record.jobId]">
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
}

.progress-text {
  flex: 1;
  overflow-y: auto;
  min-height: 200px;
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
