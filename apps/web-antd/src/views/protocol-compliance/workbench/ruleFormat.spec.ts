import { describe, expect, it } from 'vitest';

import { buildLegacyRulesPayload } from './ruleFormat';

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
