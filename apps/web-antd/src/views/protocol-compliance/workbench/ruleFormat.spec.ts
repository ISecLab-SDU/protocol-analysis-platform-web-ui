import { describe, expect, it } from 'vitest';

import {
  buildLegacyRulesPayload,
  readRuleMetadata,
  validateAnalysisRule,
} from './ruleFormat';

describe('analysis rule metadata', () => {
  it('retains protocol and version from the original grouped document', () => {
    expect(readRuleMetadata({ 'MQTT-3.1.1-rules': [] })).toEqual({
      protocol: 'MQTT',
      protocolVersion: '3.1.1',
    });
    expect(
      readRuleMetadata(
        { protocol: 'mqtt', version: '3.1.1', rules: [] },
        'PUBLISH',
      ),
    ).toEqual({ protocol: 'MQTT', protocolVersion: '3.1.1' });
  });
  it('rejects contradictory metadata and does not infer a protocol from rules.json', () => {
    expect(() =>
      readRuleMetadata({ protocol: 'FTP' }, 'MQTT-3.1.1-rules'),
    ).toThrow('冲突');
    expect(readRuleMetadata({}, 'rules')).toEqual({
      protocol: undefined,
      protocolVersion: undefined,
    });
  });
  it('requires a concrete incoming message before analysis', () => {
    expect(() =>
      validateAnalysisRule({
        rule: 'A topic requirement',
        req_type: '',
        req_fields: [],
        res_type: '',
        res_fields: [],
      }),
    ).toThrow('req_type');
  });
});

describe('buildLegacyRulesPayload', () => {
  it('groups rules and emits scalar message types', () => {
    expect(
      buildLegacyRulesPayload([
        {
          group: 'STOR',
          req_fields: ['command', 'filename'],
          req_type: ['STOR'],
          res_fields: [],
          res_type: [],
          rule: 'STOR must replace an existing file.',
        },
      ]),
    ).toEqual({
      STOR: [
        {
          req_fields: ['command', 'filename'],
          req_type: 'STOR',
          res_fields: [],
          res_type: '',
          rule: 'STOR must replace an existing file.',
        },
      ],
    });
  });

  it('splits multiple message types instead of dropping values', () => {
    expect(
      buildLegacyRulesPayload([
        {
          group: null,
          req_fields: [],
          req_type: ['APPE', 'STOR'],
          res_fields: [],
          res_type: ['150', '250'],
          rule: 'Commands share reply behavior.',
        },
      ]),
    ).toEqual({
      APPE: [
        {
          req_fields: [],
          req_type: 'APPE',
          res_fields: [],
          res_type: '150',
          rule: 'Commands share reply behavior.',
        },
        {
          req_fields: [],
          req_type: 'APPE',
          res_fields: [],
          res_type: '250',
          rule: 'Commands share reply behavior.',
        },
      ],
      STOR: [
        {
          req_fields: [],
          req_type: 'STOR',
          res_fields: [],
          res_type: '150',
          rule: 'Commands share reply behavior.',
        },
        {
          req_fields: [],
          req_type: 'STOR',
          res_fields: [],
          res_type: '250',
          rule: 'Commands share reply behavior.',
        },
      ],
    });
  });
});
