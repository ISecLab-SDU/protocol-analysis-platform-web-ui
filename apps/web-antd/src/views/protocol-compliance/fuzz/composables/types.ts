/**
 * 共享的类型定义
 */

// 基础数据包接口
export interface FuzzPacket {
  id: number | 'crash_event';
  version: string;
  type: string;
  oids: string[];
  hex: string;
  result: 'success' | 'timeout' | 'failed' | 'crash' | 'unknown';
  responseSize?: number;
  timestamp?: string;
  failed?: boolean;
  failedReason?: string;
  crashEvent?: {
    type: string;
    message: string;
    timestamp: string;
    crashPacket: string;
    crashLogPath: string;
  };
}

// 历史结果接口
export interface HistoryResult {
  id: string;
  timestamp: string;
  protocol: string;
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
  protocolStats: {
    v1: number;
    v2c: number;
    v3: number;
  };
  messageTypeStats: {
    get: number;
    set: number;
    getnext: number;
    getbulk: number;
  };
  // RTSP协议专用统计
  rtspStats?: RTSPStats;
  // MQTT协议专用统计
  mqttStats?: MQTTStats;
  hasCrash: boolean;
  crashDetails?: any;
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

// RTSP协议统计
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
  protocol_version: number | null;
  type: string | null;
  field: string | null;
  diff_range_broker: string[];
  msg_type: string | null;
  direction: string | null;
  file_path: string | null;
  capture_time: string | null;
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
  type: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR' | 'HEADER' | 'STATS';
  content: string;
  isHeader?: boolean;
  rawData?: any;
  diffInfo?: MQTTDifferentialReport;
  isDetailedDiff?: boolean; // 标识这是一个详细的差异报告
}

// 协议类型
export type ProtocolType = 'SNMP' | 'RTSP' | 'MQTT';

// Fuzz引擎类型
export type FuzzEngineType = 'SNMP_Fuzz' | 'AFLNET' | 'MBFuzzer';
