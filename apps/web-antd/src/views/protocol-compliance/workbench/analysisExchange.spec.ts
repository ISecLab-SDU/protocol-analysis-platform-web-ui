import { beforeEach, describe, expect, it, vi } from 'vitest';

import { makeAnalysisDocument } from './analysisExchange.fixture';

const api = vi.hoisted(() => ({ downloadProtocolAnalysisDocument: vi.fn() }));
vi.mock('#/api/protocol-compliance', () => api);

beforeEach(() => {
  vi.resetModules();
  vi.restoreAllMocks();
  api.downloadProtocolAnalysisDocument.mockReset();
  sessionStorage.clear();
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test');
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  api.downloadProtocolAnalysisDocument.mockResolvedValue(
    new Blob([JSON.stringify(makeAnalysisDocument())]),
  );
});

describe('portable analysis download', () => {
  it('initiates one automatic download and deduplicates concurrent/completed notifications', async () => {
    const { downloadAnalysisDocument } = await import('./analysisExchange');
    await Promise.all([
      downloadAnalysisDocument('job-1', true),
      downloadAnalysisDocument('job-1', true),
    ]);
    await downloadAnalysisDocument('job-1', true);
    expect(api.downloadProtocolAnalysisDocument).toHaveBeenCalledTimes(1);
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalledTimes(1);
    expect(document.querySelector('a[download]')).toBeNull();
  });

  it('deduplicates after module reload while allowing repeated manual downloads', async () => {
    sessionStorage.setItem(
      'protocolguard.analysis-download:job-1',
      'attempted',
    );
    const { downloadAnalysisDocument } = await import('./analysisExchange');
    await downloadAnalysisDocument('job-1', true);
    expect(api.downloadProtocolAnalysisDocument).not.toHaveBeenCalled();
    await downloadAnalysisDocument('job-1');
    await downloadAnalysisDocument('job-1');
    expect(api.downloadProtocolAnalysisDocument).toHaveBeenCalledTimes(2);
  });

  it('keeps export errors separate and permits manual retries', async () => {
    api.downloadProtocolAnalysisDocument.mockRejectedValueOnce(
      new Error('network unavailable'),
    );
    const { analysisDownloads, downloadAnalysisDocument } = await import(
      './analysisExchange'
    );
    expect(await downloadAnalysisDocument('job-failed', true)).toBe(false);
    expect(analysisDownloads['job-failed']?.error).toContain('分析已完成');
    expect(await downloadAnalysisDocument('job-failed')).toBe(true);
    expect(analysisDownloads['job-failed']).toMatchObject({
      error: '',
      pending: false,
    });
  });

  it('exports documents containing no violations without filtering results', async () => {
    const document = makeAnalysisDocument();
    const result = document.results[0];
    if (!result) throw new Error('Missing test result');
    result.verdict = 'compliant';
    api.downloadProtocolAnalysisDocument.mockResolvedValue(
      new Blob([JSON.stringify(document)]),
    );
    const { downloadAnalysisDocument, fetchAnalysisFile } = await import(
      './analysisExchange'
    );
    expect(await downloadAnalysisDocument('compliant', true)).toBe(true);
    const file = await fetchAnalysisFile('compliant');
    expect(JSON.parse(await file.text())).toEqual(document);
  });

  it('excludes inconclusive and blocked evidence from preview without losing results', async () => {
    const { eligibleAnalysisResults, readAnalysisDocument } = await import(
      './analysisExchange'
    );
    const document = makeAnalysisDocument();
    expect(eligibleAnalysisResults(document)).toHaveLength(1);
    const result = document.results[0];
    if (!result) throw new Error('Missing test result');
    result.diagnostics.push({
      code: 'unresolved',
      severity: 'blocking',
      message: 'Source unavailable',
    });
    expect(eligibleAnalysisResults(document)).toHaveLength(0);
    const file = new File([JSON.stringify(document)], 'analysis.json');
    const imported = await readAnalysisDocument(file);
    expect(imported.results).toHaveLength(1);
    document.schemaVersion = '2.0';
    await expect(
      readAnalysisDocument(new File([JSON.stringify(document)], 'bad.json')),
    ).rejects.toThrow('版本 1');
  });
  it('rejects malformed nested preview data with an actionable error', async () => {
    const { readAnalysisDocument } = await import('./analysisExchange');
    const invalid = makeAnalysisDocument();
    const malformed = {
      ...invalid,
      results: [{ verdict: 'non_compliant', locations: [{}], diagnostics: [] }],
    };
    for (const payload of [null, {}, malformed]) {
      await expect(
        readAnalysisDocument(new File([JSON.stringify(payload)], 'bad.json')),
      ).rejects.toThrow('版本 1');
    }
  });
});
