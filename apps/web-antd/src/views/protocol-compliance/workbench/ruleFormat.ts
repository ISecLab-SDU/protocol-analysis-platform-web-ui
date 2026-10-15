import type { ProtocolExtractRuleItem } from '#/api/protocol-compliance';

interface LegacyProtocolRule {
  req_fields: string[];
  req_type: string;
  res_fields: string[];
  res_type: string;
  rule: string;
}

export type LegacyProtocolRulesPayload = Record<string, LegacyProtocolRule[]>;

export function readRuleMetadata(
  data: Record<string, unknown>,
  group?: string,
) {
  const groups = group
    ? [group]
    : Object.keys(
        data.rules && typeof data.rules === 'object' ? data.rules : data,
      );
  const protocols = new Set<string>();
  const versions = new Set<string>();
  const aliases: Record<string, string> = {
    mqtt: 'MQTT',
    ftp: 'FTP',
    coap: 'CoAP',
    dhcp: 'DHCP',
    dhcpv4: 'DHCP',
    dhcpv6: 'DHCP',
    tls: 'TLS1.3',
    'tls1.3': 'TLS1.3',
  };
  for (const key of ['protocol', 'protocolName']) {
    const value = data[key];
    if (value === undefined || value === null) continue;
    if (typeof value !== 'string') throw new Error(`${key} 必须是字符串`);
    const normalized = value.trim().toLowerCase();
    if (['', 'auto', 'unknown'].includes(normalized)) continue;
    const protocol = aliases[normalized];
    if (!protocol) throw new Error(`不支持的协议：${value}`);
    protocols.add(protocol);
    if (['dhcpv4', 'dhcpv6'].includes(normalized))
      versions.add(normalized.slice(-1));
  }
  for (const key of ['protocolVersion', 'protocol_version', 'version']) {
    const value = data[key];
    if (value === undefined || value === null) continue;
    if (typeof value !== 'string') throw new Error(`${key} 必须是字符串`);
    if (value.trim()) versions.add(value.trim());
  }
  for (const name of groups) {
    const match =
      /^(MQTT|FTP|CoAP|DHCP|TLS1\.3)(?:[-_ ]v?(\d+(?:\.\d+)*))?(?:[-_ ]rules)?$/i.exec(
        name,
      );
    if (match?.[1]) {
      const protocol = aliases[match[1].toLowerCase()];
      if (protocol) protocols.add(protocol);
      if (match[2]) versions.add(match[2]);
    }
  }
  if (protocols.size > 1 || versions.size > 1)
    throw new Error('规则文件中的协议或版本信息存在冲突');
  return { protocol: [...protocols][0], protocolVersion: [...versions][0] };
}

export function validateAnalysisRule(rule: ProtocolExtractRuleItem) {
  if (!String(rule.rule || rule.description || '').trim())
    throw new Error('规则描述不能为空');
  if (normalizeRuleValues(rule.req_type).length === 0)
    throw new Error(
      '当前规则缺少 req_type，请在规则 JSON 中指定输入消息类型后重新上传',
    );
  if (
    normalizeRuleValues(rule.res_fields).length > 0 &&
    normalizeRuleValues(rule.res_type).length === 0
  )
    throw new Error('响应字段 res_fields 需要对应的响应消息类型 res_type');
}

function normalizeRuleValues(value: unknown): string[] {
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
