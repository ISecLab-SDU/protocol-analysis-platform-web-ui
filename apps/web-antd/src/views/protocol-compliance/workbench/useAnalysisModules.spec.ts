import type { ProtocolStaticAnalysisResult } from '#/api/protocol-compliance';

import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAnalysisModules } from './useAnalysisModules';

const api = vi.hoisted(() => ({
  fetchProtocolAssertGenerationProgress: vi.fn(),
  fetchProtocolAssertGenerationResult: vi.fn(),
  fetchProtocolFuzzConfigLogs: vi.fn(),
  fetchProtocolFuzzingLogs: vi.fn(),
  fetchProtocolInstrumentationDiff: vi.fn(),
  fetchProtocolStaticAnalysisDatabaseInsights: vi.fn(),
  fetchProtocolStaticAnalysisProgress: vi.fn(),
  fetchProtocolStaticAnalysisResult: vi.fn(),
  runProtocolAssertGeneration: vi.fn(),
  runProtocolStaticAnalysis: vi.fn(),
  startProtocolFuzzConfigJob: vi.fn(),
  startProtocolFuzzingJob: vi.fn(),
  stopProtocolFuzzingJob: vi.fn(),
}));

vi.mock('#/api/protocol-compliance', () => api);

const modules = useAnalysisModules();

function makeStaticResult(): ProtocolStaticAnalysisResult {
  return {
    analysisId: 'analysis-1',
    artifacts: {
      database: '/workspace/violations.db',
      workspace: '/workspace',
    },
    durationMs: 1,
    inputs: {
      codeFileName: 'source.zip',
      notes: null,
      protocolName: 'MQTT',
      rulesFileName: 'rules.json',
      rulesSummary: null,
    },
    model: 'test-model',
    modelResponse: {
      metadata: {
        generatedAt: '2026-10-13T00:00:00Z',
        modelVersion: 'test-model',
        protocol: 'MQTT',
        ruleSet: 'test-rules',
      },
      summary: {
        compliantCount: 0,
        needsReviewCount: 0,
        nonCompliantCount: 0,
        notes: '',
        overallStatus: 'compliant',
      },
      verdicts: [],
    },
    submittedAt: '2026-10-13T00:00:00Z',
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  Object.assign(modules.codeLocateInputs, {
    codeArchive: null,
    rulesFile: null,
  });
  Object.assign(modules.codeLocate, {
    error: '',
    evidence: null,
    events: [],
    inputArchive: null,
    job: null,
    logHtml: '',
    logText: '',
    result: null,
    rule: null,
    status: 'idle',
  });
  Object.assign(modules.assertInputs, {
    codeArchive: null,
    databaseFile: null,
    databasePath: '',
  });
  Object.assign(modules.assertGeneration, {
    diffContent: '',
    error: '',
    job: null,
    logText: '',
    result: null,
    status: 'idle',
  });
  Object.assign(modules.fuzz, {
    assertGenerationJobId: '',
    configJob: null,
    elapsedSeconds: 0,
    error: '',
    job: null,
    logs: [],
    pocPath: '',
    speedSeries: [],
    startedAt: null,
    status: 'idle',
  });
  Object.assign(modules.fuzzStats, {
    coverage: 0,
    crashes: 0,
    currentPath: 0,
    cycles: 0,
    edges: 0,
    executions: 0,
    hangs: 0,
    maxDepth: 0,
    nodes: 0,
    paths: 0,
    pathsTotal: 0,
    pendingFavs: 0,
    pendingTotal: 0,
    speed: 0,
  });
  modules.latestAssertGenerationJobId.value = '';
  modules.fuzzInput.assertGenerationJobId = '';
  modules.assertionOutputContexts.clear();
});

describe('independent protocol analysis modules', () => {
  it('runs code location from its own source and confirmed rule inputs', async () => {
    const archive = new File(['source'], 'source.zip');
    const rulesFile = new File(['{}'], 'rules.json', {
      type: 'application/json',
    });
    const rule = {
      group: 'CONNECT',
      req_fields: ['clientId'],
      req_type: 'CONNECT',
      res_fields: ['status'],
      res_type: 'CONNACK',
      rule: 'The client identifier must be present.',
    };
    const result = makeStaticResult();
    modules.codeLocateInputs.codeArchive = archive;
    modules.codeLocateInputs.rulesFile = rulesFile;
    const uploadedDatabase = new File(['database'], 'chosen.db');
    modules.assertInputs.databaseFile = uploadedDatabase;
    api.runProtocolStaticAnalysis.mockResolvedValue({
      events: [],
      jobId: 'static-1',
      result,
      status: 'completed',
    });
    api.fetchProtocolStaticAnalysisDatabaseInsights.mockResolvedValue({
      extractedAt: '2026-10-13T00:00:00Z',
      findings: [],
    });

    await modules.runCodeLocate(rule);

    expect(api.runProtocolStaticAnalysis).toHaveBeenCalledOnce();
    const payload = api.runProtocolStaticAnalysis.mock.calls[0]?.[0];
    expect(payload.codeArchive.name).toBe(archive.name);
    expect(await payload.codeArchive.text()).toBe('source');
    expect(JSON.parse(await payload.rules.text())).toEqual({
      CONNECT: [
        {
          req_fields: ['clientId'],
          req_type: 'CONNECT',
          res_fields: ['status'],
          res_type: 'CONNACK',
          rule: 'The client identifier must be present.',
        },
      ],
    });
    expect(modules.codeLocate.status).toBe('done');
    expect(modules.codeLocate.result).toEqual(result);
    expect(modules.assertInputs.databasePath).toBe('');
    expect(modules.assertInputs.databaseFile).toMatchObject({
      name: 'chosen.db',
    });
  });

  it('stops polling a code-location job when requested', async () => {
    let resolveStaticJob!: (job: {
      events: never[];
      jobId: string;
      status: 'completed';
    }) => void;
    modules.codeLocateInputs.codeArchive = new File(['source'], 'source.zip');
    modules.codeLocateInputs.rulesFile = new File(['{}'], 'rules.json');
    api.runProtocolStaticAnalysis.mockReturnValue(
      new Promise((resolve) => {
        resolveStaticJob = resolve;
      }),
    );

    const runPromise = modules.runCodeLocate({
      req_fields: [],
      req_type: 'CONNECT',
      res_fields: [],
      res_type: 'CONNACK',
      rule: 'A test rule.',
    });
    expect(modules.codeLocate.status).toBe('running');
    modules.stopCodeLocate();
    resolveStaticJob({
      events: [],
      jobId: 'static-stopped',
      status: 'completed',
    });
    await runPromise;

    expect(modules.codeLocate.status).toBe('stopped');
    expect(api.fetchProtocolStaticAnalysisResult).not.toHaveBeenCalled();
  });

  it('shows source evidence from code-location progress logs before completion', async () => {
    modules.codeLocateInputs.codeArchive = new File(['source'], 'source.zip');
    modules.codeLocateInputs.rulesFile = new File(['{}'], 'rules.json');
    api.runProtocolStaticAnalysis.mockResolvedValue({
      events: [
        { id: 1, message: 'Function: parse_connect' },
        { id: 2, message: 'Path: src/protocol.c:42' },
        { id: 3, message: '42 int parse_connect(void)' },
      ],
      jobId: 'static-live-evidence',
      status: 'running',
    });

    const runPromise = modules.runCodeLocate({
      req_fields: [],
      req_type: 'CONNECT',
      res_fields: [],
      res_type: 'CONNACK',
      rule: 'A test rule.',
    });
    await vi.waitFor(() => {
      expect(modules.codeLocate.evidence?.functions?.[0]?.name).toBe(
        'parse_connect',
      );
    });
    expect(modules.codeLocate.evidence?.source).toBe('实时控制台');
    expect(modules.codeLocate.evidence?.functions?.[0]?.codeRows).toEqual([
      expect.objectContaining({ line: 42, text: 'int parse_connect(void)' }),
    ]);
    modules.stopCodeLocate();
    await runPromise;
  });

  it('generates assertions from a supplied prior database output', async () => {
    const codeLocateArchive = new File(['previous source'], 'previous.zip');
    const archive = new File(['source'], 'source.zip');
    const staticResult = makeStaticResult();
    const rule = {
      req_fields: [],
      req_type: 'CONNECT',
      res_fields: [],
      res_type: 'CONNACK',
      rule: 'The client identifier must be present.',
    };
    const evidence = {
      candidateFunctionCount: 1,
      codeRows: [],
      keySliceCount: 1,
      relatedVariableCount: 0,
      targetFile: 'main.c',
      targetLine: '1',
    };
    modules.codeLocateInputs.codeArchive = codeLocateArchive;
    modules.codeLocate.inputArchive = codeLocateArchive;
    modules.codeLocate.result = staticResult;
    modules.codeLocate.rule = rule;
    modules.codeLocate.evidence = evidence;
    modules.assertInputs.codeArchive = archive;
    modules.assertInputs.databasePath = '/analysis/violations.db';
    api.runProtocolAssertGeneration.mockResolvedValue({
      events: [],
      jobId: 'assert-1',
      status: 'completed',
    });
    api.fetchProtocolAssertGenerationResult.mockResolvedValue({
      assertionCount: 2,
      jobId: 'assert-1',
      protocolName: 'MQTT',
    });
    api.fetchProtocolInstrumentationDiff.mockResolvedValue({ content: 'diff' });

    await modules.runAssertGeneration();

    expect(api.runProtocolAssertGeneration).toHaveBeenCalledWith({
      codeArchive: archive,
      databasePath: '/analysis/violations.db',
    });
    expect(modules.assertGeneration.status).toBe('done');
    expect(modules.latestAssertGenerationJobId.value).toBe('assert-1');
    expect(modules.assertionOutputContexts.get('assert-1')).toMatchObject({
      codeLocateResult: null,
      diffContent: 'diff',
      rule: null,
    });

    modules.assertInputs.codeArchive = codeLocateArchive;
    modules.assertInputs.databasePath = '/workspace/violations.db';
    await modules.runAssertGeneration();
    const assertionOutput = modules.assertionOutputContexts.get('assert-1');
    modules.codeLocate.result = makeStaticResult();
    modules.codeLocate.rule = {
      req_fields: [],
      req_type: 'CONNECT',
      res_fields: [],
      res_type: 'CONNACK',
      rule: 'A newer rule.',
    };
    expect(assertionOutput?.codeLocateResult).toEqual(staticResult);
    expect(assertionOutput?.rule).toEqual(rule);
  });

  it('reuses the selected code-location output with its matching source archive', async () => {
    const archive = new File(['prior source'], 'source.zip');
    const databasePath = '/workspace/violations.db';
    const rule = {
      req_fields: [],
      req_type: 'CONNECT',
      res_fields: [],
      res_type: 'CONNACK',
      rule: 'The client identifier must be present.',
    };
    const evidence = {
      candidateFunctionCount: 1,
      codeRows: [],
      keySliceCount: 1,
      relatedVariableCount: 0,
      targetFile: 'main.c',
      targetLine: '1',
    };
    const staticResult = makeStaticResult();
    modules.codeLocate.inputArchive = archive;
    modules.codeLocate.result = staticResult;
    modules.codeLocate.rule = rule;
    modules.codeLocate.evidence = evidence;
    modules.assertInputs.databaseFile = new File(['old db'], 'old.db');
    modules.assertInputs.codeArchive = new File(['other source'], 'other.zip');
    api.runProtocolAssertGeneration.mockResolvedValue({
      events: [],
      jobId: 'assert-latest',
      status: 'completed',
    });
    api.fetchProtocolAssertGenerationResult.mockResolvedValue({
      assertionCount: 1,
      jobId: 'assert-latest',
      protocolName: 'MQTT',
    });
    api.fetchProtocolInstrumentationDiff.mockResolvedValue({ content: 'diff' });

    expect(modules.useLatestCodeLocateOutput()).toBe(true);
    await modules.runAssertGeneration();

    expect(api.runProtocolAssertGeneration).toHaveBeenCalledWith({
      codeArchive: archive,
      databasePath,
    });
    expect(modules.assertionOutputContexts.get('assert-latest')).toMatchObject({
      codeLocateResult: staticResult,
      evidence,
      rule,
    });
  });

  it('restores assertion result and diff context for a prior job ID', async () => {
    modules.fuzzInput.assertGenerationJobId = 'assert-from-history';
    api.fetchProtocolAssertGenerationResult.mockResolvedValue({
      assertionCount: 3,
      jobId: 'assert-from-history',
      protocolName: 'MQTT',
    });
    api.fetchProtocolInstrumentationDiff.mockResolvedValue({
      content: 'historic diff',
    });
    api.startProtocolFuzzConfigJob.mockResolvedValue({
      assertGenerationJobId: 'assert-from-history',
      jobId: 'config-history',
      status: 'completed',
    });
    api.startProtocolFuzzingJob.mockResolvedValue({
      assertGenerationJobId: 'assert-from-history',
      jobId: 'fuzz-history',
      status: 'running',
    });
    api.fetchProtocolFuzzingLogs.mockResolvedValue({
      content: '',
      job: {
        assertGenerationJobId: 'assert-from-history',
        jobId: 'fuzz-history',
        status: 'completed',
      },
      position: 0,
    });

    await modules.runFuzzing();
    await vi.waitFor(() => {
      expect(modules.assertionOutputContexts.has('assert-from-history')).toBe(
        true,
      );
    });

    expect(
      modules.assertionOutputContexts.get('assert-from-history'),
    ).toMatchObject({
      assertResult: {
        assertionCount: 3,
        jobId: 'assert-from-history',
      },
      codeLocateResult: null,
      diffContent: 'historic diff',
      rule: null,
    });
    modules.fuzzInput.assertGenerationJobId = 'a-different-job';
    expect(modules.fuzz.assertGenerationJobId).toBe('assert-from-history');
  });

  it('stops polling an assertion-generation job when requested', async () => {
    let resolveAssertJob!: (job: {
      events: never[];
      jobId: string;
      status: 'completed';
    }) => void;
    modules.assertInputs.codeArchive = new File(['source'], 'source.zip');
    modules.assertInputs.databasePath = '/prior/violations.db';
    api.runProtocolAssertGeneration.mockReturnValue(
      new Promise((resolve) => {
        resolveAssertJob = resolve;
      }),
    );

    const runPromise = modules.runAssertGeneration();
    expect(modules.assertGeneration.status).toBe('running');
    modules.stopAssertGeneration();
    resolveAssertJob({
      events: [],
      jobId: 'assert-stopped',
      status: 'completed',
    });
    await runPromise;

    expect(modules.assertGeneration.status).toBe('stopped');
    expect(api.fetchProtocolAssertGenerationResult).not.toHaveBeenCalled();
  });

  it('starts fuzzing from an assertion task ID without requiring prior UI state', async () => {
    modules.fuzzInput.assertGenerationJobId = 'assert-previous';
    const extraLogs = Array.from(
      { length: 510 },
      (_, index) => `INFO: fuzz log ${index}`,
    ).join('\n');
    api.startProtocolFuzzConfigJob.mockResolvedValue({
      assertGenerationJobId: 'assert-previous',
      jobId: 'config-1',
      status: 'completed',
    });
    api.startProtocolFuzzingJob.mockResolvedValue({
      assertGenerationJobId: 'assert-previous',
      jobId: 'fuzz-1',
      status: 'running',
    });
    api.stopProtocolFuzzingJob.mockResolvedValue({
      assertGenerationJobId: 'assert-previous',
      jobId: 'fuzz-1',
      status: 'stopped',
    });
    api.fetchProtocolFuzzingLogs.mockResolvedValue({
      content: `INFO: AFLNet completed\n1, 3, 7, 10, 4, 1, 20.5, 2, 1, 8, 150.0, 6, 9\nINFO: pending 8 (2 favs), map_size 31.5, max_depth 9, nodes 12, edges 18, speed 99, path 5/20\n${extraLogs}`,
      job: {
        assertGenerationJobId: 'assert-previous',
        artifacts: {},
        jobId: 'fuzz-1',
        status: 'completed',
      },
      outputRoot: '/out/run-1',
      position: 10,
    });

    await modules.runFuzzing();

    expect(api.startProtocolFuzzConfigJob).toHaveBeenCalledWith({
      assertGenerationJobId: 'assert-previous',
    });
    expect(api.startProtocolFuzzingJob).toHaveBeenCalledWith({
      assertGenerationJobId: 'assert-previous',
      fuzzConfigJobId: 'config-1',
    });
    expect(modules.fuzz.status).toBe('crash-found');
    expect(modules.fuzz.pocPath).toBe('/out/run-1');
    expect(modules.fuzz.logs).toHaveLength(500);
    expect(modules.fuzz.logs.at(-1)?.text).toBe('fuzz log 509');
    expect(modules.fuzzStats).toMatchObject({
      coverage: 31.5,
      crashes: 2,
      currentPath: 5,
      cycles: 3,
      edges: 18,
      hangs: 1,
      maxDepth: 9,
      nodes: 12,
      pathsTotal: 20,
      pendingFavs: 2,
      pendingTotal: 8,
      speed: 99,
    });
  });

  it('accepts percentage values in AFL CSV statistics', async () => {
    modules.fuzzInput.assertGenerationJobId = 'assert-percent';
    api.startProtocolFuzzConfigJob.mockResolvedValue({
      assertGenerationJobId: 'assert-percent',
      jobId: 'config-percent',
      status: 'completed',
    });
    api.startProtocolFuzzingJob.mockResolvedValue({
      assertGenerationJobId: 'assert-percent',
      jobId: 'fuzz-percent',
      status: 'running',
    });
    api.fetchProtocolFuzzingLogs.mockResolvedValue({
      content: '1, 3, 7, 10, 4, 1, 20.5%, 2, 1, 8, 150.0, 6, 9',
      job: {
        assertGenerationJobId: 'assert-percent',
        artifacts: {},
        jobId: 'fuzz-percent',
        status: 'completed',
      },
      position: 5,
    });

    await modules.runFuzzing();

    expect(modules.fuzzStats.coverage).toBe(20.5);
    expect(modules.fuzzStats.crashes).toBe(2);
  });

  it('uses a log-file directory instead of an output source label as the POC path', async () => {
    modules.fuzzInput.assertGenerationJobId = 'assert-path';
    api.startProtocolFuzzConfigJob.mockResolvedValue({
      assertGenerationJobId: 'assert-path',
      jobId: 'config-path',
      status: 'completed',
    });
    api.startProtocolFuzzingJob.mockResolvedValue({
      assertGenerationJobId: 'assert-path',
      jobId: 'fuzz-path',
      status: 'running',
    });
    api.fetchProtocolFuzzingLogs.mockResolvedValue({
      content: '',
      job: {
        assertGenerationJobId: 'assert-path',
        artifacts: {},
        jobId: 'fuzz-path',
        status: 'completed',
      },
      logFilePath: '/out/fallback/fuzzer.log',
      outputSource: 'fallback',
      position: 0,
    });

    await modules.runFuzzing();

    expect(modules.fuzz.pocPath).toBe('/out/fallback');
  });

  it('keeps polling after a transient AFL log request failure', async () => {
    modules.fuzzInput.assertGenerationJobId = 'assert-retry';
    api.startProtocolFuzzConfigJob.mockResolvedValue({
      assertGenerationJobId: 'assert-retry',
      jobId: 'config-retry',
      status: 'completed',
    });
    api.startProtocolFuzzingJob.mockResolvedValue({
      assertGenerationJobId: 'assert-retry',
      jobId: 'fuzz-retry',
      status: 'running',
    });
    api.fetchProtocolFuzzingLogs
      .mockRejectedValueOnce(new Error('temporary network error'))
      .mockResolvedValueOnce({
        content: 'INFO: recovered',
        job: {
          assertGenerationJobId: 'assert-retry',
          jobId: 'fuzz-retry',
          status: 'completed',
        },
        position: 12,
      });

    await modules.runFuzzing();

    expect(api.fetchProtocolFuzzingLogs).toHaveBeenCalledTimes(2);
    expect(modules.fuzz.status).toBe('completed');
    expect(modules.fuzz.logs.some((entry) => entry.text === 'recovered')).toBe(
      true,
    );
  });

  it('processes the final in-flight AFL log response after stop', async () => {
    let resolveLogs!: (response: {
      content: string;
      job: {
        assertGenerationJobId: string;
        jobId: string;
        status: 'running';
      };
      outputRoot: string;
      position: number;
    }) => void;
    modules.fuzzInput.assertGenerationJobId = 'assert-stop';
    api.startProtocolFuzzConfigJob.mockResolvedValue({
      assertGenerationJobId: 'assert-stop',
      jobId: 'config-stop',
      status: 'completed',
    });
    api.startProtocolFuzzingJob.mockResolvedValue({
      assertGenerationJobId: 'assert-stop',
      jobId: 'fuzz-stop',
      status: 'running',
    });
    api.stopProtocolFuzzingJob.mockResolvedValue({
      assertGenerationJobId: 'assert-stop',
      jobId: 'fuzz-stop',
      status: 'stopped',
    });
    api.fetchProtocolFuzzingLogs.mockReturnValue(
      new Promise((resolve) => {
        resolveLogs = resolve;
      }),
    );

    const runPromise = modules.runFuzzing();
    await vi.waitFor(() => {
      expect(api.fetchProtocolFuzzingLogs).toHaveBeenCalledOnce();
    });
    const stopPromise = modules.stopFuzzing();
    await vi.waitFor(() => {
      expect(modules.fuzz.status).toBe('stopping');
    });
    expect(modules.isFuzzRunning.value).toBe(true);
    await modules.runFuzzing();
    expect(api.startProtocolFuzzConfigJob).toHaveBeenCalledOnce();
    resolveLogs({
      content: 'STATS: unique_crash 2',
      job: {
        assertGenerationJobId: 'assert-stop',
        jobId: 'fuzz-stop',
        status: 'running',
      },
      outputRoot: '/out/stopped-run',
      position: 20,
    });
    await Promise.all([runPromise, stopPromise]);

    expect(modules.fuzz.status).toBe('stopped');
    expect(modules.fuzzStats.crashes).toBe(2);
    expect(modules.fuzz.pocPath).toBe('/out/stopped-run');
  });

  it('can cancel the fuzz flow while configuration is still starting', async () => {
    let resolveConfigJob!: (job: {
      assertGenerationJobId: string;
      jobId: string;
      status: 'running';
    }) => void;
    modules.fuzzInput.assertGenerationJobId = 'assert-pending';
    api.startProtocolFuzzConfigJob.mockReturnValue(
      new Promise((resolve) => {
        resolveConfigJob = resolve;
      }),
    );

    const runPromise = modules.runFuzzing();
    expect(modules.fuzz.status).toBe('configuring');
    await modules.stopFuzzing();
    expect(modules.fuzz.status).toBe('stopped');

    resolveConfigJob({
      assertGenerationJobId: 'assert-pending',
      jobId: 'config-pending',
      status: 'running',
    });
    await runPromise;

    expect(api.startProtocolFuzzingJob).not.toHaveBeenCalled();
  });

  it('stops a fuzz job whose start response arrives after cancellation', async () => {
    let resolveFuzzJob!: (job: {
      assertGenerationJobId: string;
      jobId: string;
      status: 'running';
    }) => void;
    modules.fuzzInput.assertGenerationJobId = 'assert-start-pending';
    api.startProtocolFuzzConfigJob.mockResolvedValue({
      assertGenerationJobId: 'assert-start-pending',
      jobId: 'config-start-pending',
      status: 'completed',
    });
    api.startProtocolFuzzingJob.mockReturnValue(
      new Promise((resolve) => {
        resolveFuzzJob = resolve;
      }),
    );
    api.stopProtocolFuzzingJob.mockResolvedValue({
      assertGenerationJobId: 'assert-start-pending',
      jobId: 'fuzz-start-pending',
      status: 'stopped',
    });
    api.fetchProtocolFuzzingLogs.mockResolvedValue({
      content: '',
      job: {
        assertGenerationJobId: 'assert-start-pending',
        artifacts: {},
        jobId: 'fuzz-start-pending',
        status: 'stopped',
      },
      position: 0,
    });

    const runPromise = modules.runFuzzing();
    await vi.waitFor(() => {
      expect(api.startProtocolFuzzingJob).toHaveBeenCalledOnce();
    });
    await modules.stopFuzzing();
    expect(modules.fuzz.status).toBe('stopping');
    resolveFuzzJob({
      assertGenerationJobId: 'assert-start-pending',
      jobId: 'fuzz-start-pending',
      status: 'running',
    });
    await runPromise;

    expect(api.stopProtocolFuzzingJob).toHaveBeenCalledWith(
      'fuzz-start-pending',
    );
    expect(modules.fuzz.status).toBe('stopped');
    expect(modules.fuzz.job?.jobId).toBe('fuzz-start-pending');
  });

  it('stops AFLNet and exposes the result after discovering a crash line', async () => {
    modules.fuzzInput.assertGenerationJobId = 'assert-crash';
    api.startProtocolFuzzConfigJob.mockResolvedValue({
      assertGenerationJobId: 'assert-crash',
      jobId: 'config-crash',
      status: 'completed',
    });
    api.startProtocolFuzzingJob.mockResolvedValue({
      assertGenerationJobId: 'assert-crash',
      jobId: 'fuzz-crash',
      status: 'running',
    });
    api.fetchProtocolFuzzingLogs
      .mockResolvedValueOnce({
        content: 'ERROR: Segmentation fault',
        job: {
          assertGenerationJobId: 'assert-crash',
          artifacts: {},
          jobId: 'fuzz-crash',
          status: 'running',
        },
        outputRoot: '/out/crash',
        position: 10,
      })
      .mockResolvedValueOnce({
        content: '',
        job: {
          assertGenerationJobId: 'assert-crash',
          artifacts: {},
          jobId: 'fuzz-crash',
          status: 'stopped',
        },
        outputRoot: '/out/crash',
        position: 10,
      });
    api.stopProtocolFuzzingJob.mockResolvedValue({
      assertGenerationJobId: 'assert-crash',
      jobId: 'fuzz-crash',
      status: 'stopped',
    });

    await modules.runFuzzing();

    expect(api.stopProtocolFuzzingJob).toHaveBeenCalledWith('fuzz-crash');
    expect(modules.fuzzStats.crashes).toBe(1);
    expect(modules.fuzz.status).toBe('crash-found');
    expect(
      modules.fuzz.logs.some((entry) => /Segmentation fault/.test(entry.text)),
    ).toBe(true);
    expect(modules.fuzz.job?.status).toBe('stopped');
  });
});
