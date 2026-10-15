import type { ProtocolAnalysisDocument } from '#/api/protocol-compliance';

export function makeAnalysisDocument(): ProtocolAnalysisDocument {
  return {
    format: 'protocolguard.analysis',
    schemaVersion: '1.0',
    analysisId: 'analysis-1',
    generatedAt: '2026-10-15T09:00:00Z',
    producer: { name: 'test', version: '1' },
    protocol: { name: 'MQTT', version: '3.1.1' },
    source: {
      archiveName: 'source.zip',
      treeSha256: 'a'.repeat(64),
      files: [{ path: 'main.c', sha256: 'b'.repeat(64) }],
    },
    results: [
      {
        id: 'result-1',
        rule: {
          id: 'rule-1',
          description: 'Validate input',
          reference: null,
          requestTypes: ['PUBLISH'],
          requestFields: [],
          responseTypes: [],
          responseFields: [],
        },
        verdict: 'non_compliant',
        reason: 'Missing validation',
        locations: [
          {
            id: 'location-1',
            path: 'main.c',
            function: 'main',
            startLine: 1,
            endLine: 1,
            relevantLines: [1],
            code: 'int main(void) { return 0; }\n',
          },
        ],
        context: { codeSlice: null, callGraph: null },
        diagnostics: [],
      },
    ],
    diagnostics: [],
  };
}
