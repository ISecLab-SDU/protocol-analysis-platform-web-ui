import type { ProtocolExtractRuleItem } from '#/api/protocol-compliance';

export type WorkbenchStage =
  | 'setup'
  | 'rule_confirm'
  | 'code_locate'
  | 'assert_gen'
  | 'fuzz'
  | 'done';

export type StageStatus = 'idle' | 'running' | 'done' | 'error' | 'skipped';

export type ProtocolKind = 'MQTT' | 'SNMP';

export interface CodeLocateRow {
  emphasis?: boolean;
  line: number | string;
  text: string;
}

export interface CodeLocateFunctionSlice {
  codeRows: CodeLocateRow[];
  name: string;
  path?: string;
  targetLine?: number | string;
}

export interface CodeLocateEvidence {
  candidateFunctionCount: number;
  codeRows: CodeLocateRow[];
  functions?: CodeLocateFunctionSlice[];
  keySliceCount: number;
  relatedVariableCount: number;
  resultLabel?: string;
  ruleText?: string;
  source?: string;
  targetFile: string;
  targetLine: string;
  updatedAt?: string;
  violationReason?: string;
}

export type MQTTImplementation =
  | 'SOL'
  | 'HiveMQ'
  | 'VerneMQ'
  | 'EMQX'
  | 'FlashMQ'
  | 'NanoMQ'
  | 'Mosquitto';

export type SNMPImplementation = '系统固件';

export type AnyImplementation = MQTTImplementation | SNMPImplementation;

export interface ProjectConfig {
  archive: File | null;
  rules: File | null;
  buildInstructions: string;
  protocolType: ProtocolKind;
  protocolVersion: string;
  implementation: AnyImplementation;
  targetHost: string;
  targetPort: number;
  notes: string;
  fuzzScript: string;
}

export interface RuleOption extends ProtocolExtractRuleItem {
  id?: string;
  msgType?: string;
}

export const STAGE_LIST: Array<{ key: WorkbenchStage; index: number; title: string }> = [
  { key: 'rule_confirm', index: 1, title: '规则确认' },
  { key: 'code_locate', index: 2, title: '代码定位与一致性分析' },
  { key: 'assert_gen', index: 3, title: '断言生成' },
  { key: 'fuzz', index: 4, title: '模糊测试' },
  { key: 'done', index: 5, title: '结果验证' },
];

export const PROTOCOL_IMPLEMENTATIONS: Record<ProtocolKind, AnyImplementation[]> = {
  MQTT: ['SOL', 'Mosquitto', 'HiveMQ', 'VerneMQ', 'EMQX', 'FlashMQ', 'NanoMQ'],
  SNMP: ['系统固件'],
};

export const DEFAULT_TARGET: Record<ProtocolKind, { host: string; port: number }> = {
  MQTT: { host: 'localhost', port: 1883 },
  SNMP: { host: 'localhost', port: 161 },
};

export function buildDefaultFuzzScript(
  protocolType: ProtocolKind,
  implementation: AnyImplementation,
  targetHost: string,
  targetPort: number,
) {
  if (protocolType === 'MQTT' && implementation === 'SOL') {
    return `# AFL-NET MQTT/SOL fuzzing
HOST=${targetHost}
PORT=${targetPort}
IMPLEMENTATION=${implementation}
DURATION=0
`;
  }

  if (protocolType === 'MQTT') {
    return `# MBFuzzer MQTT broker fuzzing
broker_host=${targetHost}
broker_port=${targetPort}
implementation=${implementation}
`;
  }

  return `# SNMP fuzzing
target_host=${targetHost}
target_port=${targetPort}
`;
}

export const BUILTIN_RULESET_INDEX: Array<{
  key: string;
  protocol: ProtocolKind;
  protocolLabel: string;
  version: string;
  path: string;
}> = [
  {
    key: 'MQTTv3_1_1',
    protocol: 'MQTT',
    protocolLabel: 'MQTT 3.1.1',
    version: '3.1.1',
    path: '/public/ruleConfig_mqttv3_1_1.json',
  },
  {
    key: 'MQTTv5',
    protocol: 'MQTT',
    protocolLabel: 'MQTT 5.0',
    version: '5.0',
    path: '/public/ruleConfig_mqttv5.json',
  },
];
