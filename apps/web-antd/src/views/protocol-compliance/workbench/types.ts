import type { ProtocolExtractRuleItem } from '#/api/protocol-compliance';

export type WorkbenchStage =
  | 'setup'
  | 'rule_confirm'
  | 'code_locate'
  | 'assert_gen'
  | 'fuzz'
  | 'done';

export type StageStatus = 'idle' | 'running' | 'done' | 'error';

export type ProtocolKind = 'MQTT' | 'SNMP';

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
  builder: File | null;
  config: File | null;
  buildInstructions: string;
  protocolType: ProtocolKind;
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
  { key: 'code_locate', index: 2, title: '代码定位' },
  { key: 'assert_gen', index: 3, title: '断言生成' },
  { key: 'fuzz', index: 4, title: '模糊测试' },
  { key: 'done', index: 5, title: '结果验证' },
];

export const PROTOCOL_IMPLEMENTATIONS: Record<ProtocolKind, AnyImplementation[]> = {
  MQTT: ['Mosquitto', 'HiveMQ', 'VerneMQ', 'EMQX', 'FlashMQ', 'NanoMQ', 'SOL'],
  SNMP: ['系统固件'],
};

export const DEFAULT_TARGET: Record<ProtocolKind, { host: string; port: number }> = {
  MQTT: { host: 'localhost', port: 1883 },
  SNMP: { host: 'localhost', port: 161 },
};

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
