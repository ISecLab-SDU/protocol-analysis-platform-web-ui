/**
 * 共享的类型定义
 */

// 基础数据包接口
export interface FuzzPacket {
  id: 'crash_event' | number;
  version: string;
  type: string;
  oids: string[];
  hex: string;
  result: 'crash' | 'failed' | 'success' | 'timeout' | 'unknown';
  responseSize?: number;
  timestamp?: string;
  failed?: boolean;
  failedReason?: string;
  crashEvent?: {
    crashLogPath: string;
    crashPacket: string;
    message: string;
    timestamp: string;
    type: string;
  };
}

// 历史结果接口
export interface HistoryResult {
  id: string;
  timestamp: string;
  protocol: 'MQTT' | 'SNMP';
  fuzzEngine: string;
  targetHost: string;
  targetPort: number;
  duration: number;
  totalPackets: number;
  successCount: number;
  timeoutCount: number;
  failedCount: number;
  crashCount: number;
  successRate: number;

  // SNMP协议专用数据
  protocolStats?: {
    v1: number;
    v2c: number;
    v3: number;
  };
  messageTypeStats?: {
    get: number;
    getbulk: number;
    getnext: number;
    set: number;
  };

  // SOL协议专用统计
  rtspStats?: RTSPStats;

  // MQTT协议专用统计
  mqttStats?: MQTTStats;

  hasCrash: boolean;
  crashDetails?: any;

  // 协议特定的扩展数据
  protocolSpecificData?: {
    brokerRequestCount?: number;
    // MQTT特定数据
    clientRequestCount?: number;
    communityStrings?: string[];

    diffNumber?: number;
    duplicateConnectDiff?: number;
    duplicateDiffNumber?: number;
    fuzzingEndTime?: string;

    fuzzingStartTime?: string;
    maxDepth?: number;
    // SNMP特定数据
    oidCoverage?: number;
    // SOL特定数据
    pathCoverage?: number;
    stateTransitions?: number;
    targetDeviceInfo?: string;
    uniqueHangs?: number;
    validConnectNumber?: number;
  };
}

// SNMP协议统计
export interface SNMPStats {
  v1: number;
  v2c: number;
  v3: number;
}

export interface SNMPMessageStats {
  get: number;
  set: number;
  getnext: number;
  getbulk: number;
}

// SOL协议统计（基于RTSP协议）
export interface RTSPStats {
  cycles_done: number;
  paths_total: number;
  cur_path: number;
  pending_total: number;
  pending_favs: number;
  map_size: string;
  unique_crashes: number;
  unique_hangs: number;
  max_depth: number;
  execs_per_sec: number;
  n_nodes: number;
  n_edges: number;
}

// MQTT协议统计
export interface MQTTStats {
  fuzzing_start_time: string;
  fuzzing_end_time: string;
  client_request_count: number;
  broker_request_count: number;
  total_request_count: number;
  crash_number: number;
  diff_number: number;
  duplicate_diff_number: number;
  valid_connect_number: number;
  duplicate_connect_diff?: number;
  total_differences?: number;

  client_messages: MQTTMessageStats;
  broker_messages: MQTTMessageStats;
  duplicate_diffs: MQTTMessageStats;
  differential_reports: MQTTDifferentialReport[];
  q_table_states: any[];
  broker_issues: MQTTBrokerIssues;
}

export interface MQTTMessageStats {
  CONNECT: number;
  CONNACK: number;
  PUBLISH: number;
  PUBACK: number;
  PUBREC: number;
  PUBREL: number;
  PUBCOMP: number;
  SUBSCRIBE: number;
  SUBACK: number;
  UNSUBSCRIBE: number;
  UNSUBACK: number;
  PINGREQ: number;
  PINGRESP: number;
  DISCONNECT: number;
  AUTH: number;
}

export interface MQTTDifferentialReport {
  protocol_version: null | number;
  type: null | string;
  field: null | string;
  diff_range_broker: string[];
  msg_type: null | string;
  direction: null | string;
  file_path: null | string;
  capture_time: null | string;
}

export interface MQTTBrokerIssues {
  hivemq: number;
  vernemq: number;
  emqx: number;
  flashmq: number;
  nanomq: number;
  mosquitto: number;
}

// 日志UI数据接口
export interface LogUIData {
  timestamp: string;
  type: 'ERROR' | 'HEADER' | 'INFO' | 'STATS' | 'SUCCESS' | 'WARNING';
  content: string;
  isHeader?: boolean;
  rawData?: any;
  diffInfo?: MQTTDifferentialReport;
  isDetailedDiff?: boolean; // 标识这是一个详细的差异报告
}

// 协议类型
export type ProtocolType = 'MQTT' | 'SNMP';

// Fuzz引擎类型
export type FuzzEngineType = 'AFLNET' | 'MBFuzzer' | 'SNMP_Fuzz';

// 协议实现类型
export type ProtocolImplementationType =
  | 'EMQX' // MQTT + MBFuzzer 选项
  | 'FlashMQ' // MQTT + MBFuzzer 选项
  | 'HiveMQ' // MQTT + MBFuzzer 选项
  | 'Mosquitto' // MQTT + MBFuzzer 选项
  | 'NanoMQ' // MQTT + MBFuzzer 选项
  | 'SOL协议' // MQTT + AFLNET 选项 (SOL协议实现)
  | 'VerneMQ' // MQTT + MBFuzzer 选项
  | '系统固件'; // SNMP_Fuzz 默认

// 协议实现配置接口
export interface ProtocolImplementationConfig {
  fuzzEngine: FuzzEngineType;
  defaultImplementations: ProtocolImplementationType[];
  isMultiSelect: boolean;
}
