import type { ProtocolAnalysisDocument } from '#/api/protocol-compliance';

import { reactive } from 'vue';

import { downloadProtocolAnalysisDocument } from '#/api/protocol-compliance';

export const analysisDownloads = reactive<
  Record<string, { error: string; pending: boolean }>
>({});
const attempted = new Set<string>();
const inFlight = new Map<string, Promise<boolean>>();

export function eligibleAnalysisResults(document: ProtocolAnalysisDocument) {
  const blocked = new Set(
    document.diagnostics
      .filter((d) => d.severity === 'blocking')
      .map((d) => d.resultId),
  );
  if (blocked.has(undefined)) return [];
  return document.results.filter(
    (r) =>
      r.verdict === 'non_compliant' &&
      r.locations.length > 0 &&
      !blocked.has(r.id) &&
      !r.diagnostics.some((d) => d.severity === 'blocking'),
  );
}

export async function readAnalysisDocument(
  file: File,
): Promise<ProtocolAnalysisDocument> {
  const invalid = () =>
    new Error('请选择有效的 ProtocolGuard 分析 JSON（版本 1）');
  let document: ProtocolAnalysisDocument;
  try {
    document = JSON.parse(await file.text()) as ProtocolAnalysisDocument;
    const strings = (value: unknown): value is string[] =>
      Array.isArray(value) && value.every((item) => typeof item === 'string');
    const diagnostics = (value: unknown) =>
      Array.isArray(value) &&
      value.every(
        (item) =>
          item &&
          typeof item.code === 'string' &&
          typeof item.message === 'string' &&
          ['blocking', 'warning'].includes(item.severity),
      );
    if (
      !document ||
      document.format !== 'protocolguard.analysis' ||
      !/^1\.\d+$/.test(document.schemaVersion) ||
      typeof document.protocol?.name !== 'string' ||
      typeof document.source?.archiveName !== 'string' ||
      typeof document.source.treeSha256 !== 'string' ||
      !Array.isArray(document.results) ||
      !diagnostics(document.diagnostics)
    )
      throw invalid();
    for (const result of document.results) {
      if (
        !result ||
        typeof result.id !== 'string' ||
        typeof result.rule?.description !== 'string' ||
        !['compliant', 'needs_review', 'non_compliant'].includes(
          result.verdict,
        ) ||
        !strings(result.rule.requestTypes) ||
        !strings(result.rule.requestFields) ||
        !strings(result.rule.responseTypes) ||
        !strings(result.rule.responseFields) ||
        !result.context ||
        !diagnostics(result.diagnostics) ||
        !Array.isArray(result.locations) ||
        !result.locations.every(
          (location) =>
            location &&
            typeof location.path === 'string' &&
            typeof location.code === 'string' &&
            Number.isInteger(location.startLine) &&
            Number.isInteger(location.endLine) &&
            Array.isArray(location.relevantLines),
        )
      )
        throw invalid();
    }
    eligibleAnalysisResults(document);
  } catch {
    throw invalid();
  }
  // Preview validation is advisory; the server validates the full schema, evidence and source.
  return document;
}

export async function fetchAnalysisFile(jobId: string) {
  const blob = await downloadProtocolAnalysisDocument(jobId);
  return new File([blob], `analysis-${jobId}.json`, {
    type: 'application/json',
  });
}

export function downloadAnalysisDocument(
  jobId: string,
  automatic = false,
): Promise<boolean> {
  const existing = inFlight.get(jobId);
  if (existing) return existing;
  const key = `protocolguard.analysis-download:${jobId}`;
  if (automatic) {
    let stored = false;
    try {
      stored = sessionStorage.getItem(key) === 'attempted';
    } catch {
      /* Storage may be disabled. */
    }
    if (attempted.has(jobId) || stored) return Promise.resolve(false);
    attempted.add(jobId);
    try {
      sessionStorage.setItem(key, 'attempted');
    } catch {
      /* In-memory deduplication remains active. */
    }
  }
  const state = reactive({ error: '', pending: true });
  analysisDownloads[jobId] = state;
  const operation = (async () => {
    try {
      const file = await fetchAnalysisFile(jobId);
      const url = URL.createObjectURL(file);
      const link = document.createElement('a');
      link.href = url;
      link.download = file.name;
      document.body.append(link);
      try {
        link.click();
      } finally {
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
      return true;
    } catch {
      state.error =
        '分析已完成；JSON 下载未能启动，请点击“下载分析 JSON”重试。';
      return false;
    } finally {
      state.pending = false;
      inFlight.delete(jobId);
    }
  })();
  inFlight.set(jobId, operation);
  return operation;
}
