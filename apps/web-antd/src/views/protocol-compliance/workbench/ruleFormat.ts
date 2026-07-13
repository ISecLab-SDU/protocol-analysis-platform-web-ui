import type { ProtocolExtractRuleItem } from '#/api/protocol-compliance';

export interface LegacyProtocolRule {
  req_fields: string[];
  req_type: string;
  res_fields: string[];
  res_type: string;
  rule: string;
}

export type LegacyProtocolRulesPayload = Record<string, LegacyProtocolRule[]>;

export function normalizeRuleValues(value: unknown): string[] {
  const values = Array.isArray(value) ? value : [value];
  return [
    ...new Set(
      values
        .filter((item) => item !== null && item !== undefined)
        .map((item) => String(item).trim())
        .filter(Boolean),
    ),
  ];
}

export function buildLegacyRulesPayload(
  rules: ProtocolExtractRuleItem[],
): LegacyProtocolRulesPayload {
  const grouped: LegacyProtocolRulesPayload = {};

  for (const rule of rules) {
    const ruleText = String(rule.rule || rule.description || '').trim();
    if (!ruleText) continue;

    const requestTypes = normalizeRuleValues(rule.req_type);
    const responseTypes = normalizeRuleValues(rule.res_type);
    const requestFields = normalizeRuleValues(rule.req_fields);
    const responseFields = normalizeRuleValues(rule.res_fields);
    const explicitGroup = String(rule.group || '').trim();

    for (const requestType of requestTypes.length > 0 ? requestTypes : ['']) {
      for (const responseType of responseTypes.length > 0
        ? responseTypes
        : ['']) {
        const group = explicitGroup || requestType || responseType || 'DEFAULT';
        (grouped[group] ||= []).push({
          req_fields: requestFields,
          req_type: requestType,
          res_fields: responseFields,
          res_type: responseType,
          rule: ruleText,
        });
      }
    }
  }

  return grouped;
}
