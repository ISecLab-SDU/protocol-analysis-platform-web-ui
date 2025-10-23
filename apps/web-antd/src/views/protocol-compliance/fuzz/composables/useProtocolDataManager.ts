/**
 * 协议数据管理器 - 隔离不同协议的数据和状态
 */

import { ref, reactive, computed } from 'vue';

export type ProtocolType = 'SNMP' | 'RTSP' | 'MQTT';

export interface LogEntry {
  id: string;
  timestamp: string;
  type: 'INFO' | 'ERROR' | 'WARNING' | 'SUCCESS';
  content: string;
  protocol: ProtocolType;
  raw?: any; // 原始数据
}

export interface ProtocolState {
  isRunning: boolean;
  isProcessing: boolean;
  totalRecords: number;
  processedRecords: number;
  logs: LogEntry[];
  stats: Record<string, any>;
}

export function useProtocolDataManager() {
  // 每个协议的独立状态
  const protocolStates = reactive<Record<ProtocolType, ProtocolState>>({
    SNMP: {
      isRunning: false,
      isProcessing: false,
      totalRecords: 0,
      processedRecords: 0,
      logs: [],
      stats: {}
    },
    RTSP: {
      isRunning: false,
      isProcessing: false,
      totalRecords: 0,
      processedRecords: 0,
      logs: [],
      stats: {}
    },
    MQTT: {
      isRunning: false,
      isProcessing: false,
      totalRecords: 0,
      processedRecords: 0,
      logs: [],
      stats: {}
    }
  });

  const currentProtocol = ref<ProtocolType>('SNMP');

  // 获取当前协议状态
  const currentState = computed(() => protocolStates[currentProtocol.value]);

  // 生成唯一ID
  function generateLogId(protocol: ProtocolType): string {
    return `${protocol}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  // 添加日志（协议隔离）
  function addLog(protocol: ProtocolType, logData: Omit<LogEntry, 'id' | 'protocol'>) {
    const log: LogEntry = {
      ...logData,
      id: generateLogId(protocol),
      protocol
    };

    const state = protocolStates[protocol];
    state.logs.push(log);

    // 限制日志数量，避免内存泄漏（保留最新的10000条）
    if (state.logs.length > 10000) {
      state.logs.splice(0, state.logs.length - 10000);
    }

    return log;
  }

  // 批量添加日志
  function addBatchLogs(protocol: ProtocolType, logsData: Array<Omit<LogEntry, 'id' | 'protocol'>>) {
    const logs = logsData.map(logData => ({
      ...logData,
      id: generateLogId(protocol),
      protocol
    }));

    const state = protocolStates[protocol];
    state.logs.push(...logs);

    // 限制日志数量
    if (state.logs.length > 10000) {
      state.logs.splice(0, state.logs.length - 10000);
    }

    return logs;
  }

  // 清空指定协议的日志
  function clearProtocolLogs(protocol: ProtocolType) {
    protocolStates[protocol].logs = [];
  }

  // 清空所有协议的日志
  function clearAllLogs() {
    Object.keys(protocolStates).forEach(protocol => {
      protocolStates[protocol as ProtocolType].logs = [];
    });
  }

  // 更新协议状态
  function updateProtocolState(protocol: ProtocolType, updates: Partial<ProtocolState>) {
    Object.assign(protocolStates[protocol], updates);
  }

  // 切换协议
  function switchProtocol(protocol: ProtocolType) {
    currentProtocol.value = protocol;
  }

  // 获取协议统计信息
  function getProtocolStats(protocol: ProtocolType) {
    const state = protocolStates[protocol];
    const logs = state.logs;
    
    return {
      total: logs.length,
      info: logs.filter(log => log.type === 'INFO').length,
      error: logs.filter(log => log.type === 'ERROR').length,
      warning: logs.filter(log => log.type === 'WARNING').length,
      success: logs.filter(log => log.type === 'SUCCESS').length,
      isRunning: state.isRunning,
      isProcessing: state.isProcessing,
      progress: state.totalRecords > 0 ? Math.round((state.processedRecords / state.totalRecords) * 100) : 0
    };
  }

  // 获取最近的日志
  function getRecentLogs(protocol: ProtocolType, count: number = 100) {
    const logs = protocolStates[protocol].logs;
    return logs.slice(-count);
  }

  // 搜索日志
  function searchLogs(protocol: ProtocolType, keyword: string, type?: LogEntry['type']) {
    const logs = protocolStates[protocol].logs;
    return logs.filter(log => {
      const matchesKeyword = log.content.toLowerCase().includes(keyword.toLowerCase());
      const matchesType = !type || log.type === type;
      return matchesKeyword && matchesType;
    });
  }

  // 导出日志
  function exportLogs(protocol: ProtocolType, format: 'json' | 'txt' = 'txt') {
    const logs = protocolStates[protocol].logs;
    
    if (format === 'json') {
      return JSON.stringify(logs, null, 2);
    } else {
      return logs.map(log => 
        `[${log.timestamp}] [${log.type}] ${log.content}`
      ).join('\n');
    }
  }

  // 实时日志流（用于MQTT等需要实时更新的协议）
  const realtimeStreams = new Map<ProtocolType, {
    buffer: LogEntry[];
    timer: number | null;
    batchSize: number;
    interval: number;
  }>();

  // 开始实时日志流
  function startRealtimeStream(protocol: ProtocolType, options = { batchSize: 50, interval: 100 }) {
    if (realtimeStreams.has(protocol)) {
      stopRealtimeStream(protocol);
    }

    const stream = {
      buffer: [],
      timer: null,
      batchSize: options.batchSize,
      interval: options.interval
    };

    // 定时批量处理缓冲区的日志
    stream.timer = window.setInterval(() => {
      if (stream.buffer.length > 0) {
        const batch = stream.buffer.splice(0, stream.batchSize);
        const state = protocolStates[protocol];
        state.logs.push(...batch);

        // 限制日志数量
        if (state.logs.length > 10000) {
          state.logs.splice(0, state.logs.length - 10000);
        }
      }
    }, stream.interval);

    realtimeStreams.set(protocol, stream);
  }

  // 添加到实时流缓冲区
  function addToRealtimeStream(protocol: ProtocolType, logData: Omit<LogEntry, 'id' | 'protocol'>) {
    const stream = realtimeStreams.get(protocol);
    if (stream) {
      const log: LogEntry = {
        ...logData,
        id: generateLogId(protocol),
        protocol
      };
      stream.buffer.push(log);
    } else {
      // 如果没有启动实时流，直接添加
      addLog(protocol, logData);
    }
  }

  // 停止实时日志流
  function stopRealtimeStream(protocol: ProtocolType) {
    const stream = realtimeStreams.get(protocol);
    if (stream) {
      if (stream.timer) {
        clearInterval(stream.timer);
      }
      // 处理剩余的缓冲区日志
      if (stream.buffer.length > 0) {
        const state = protocolStates[protocol];
        state.logs.push(...stream.buffer);
      }
      realtimeStreams.delete(protocol);
    }
  }

  // 停止所有实时流
  function stopAllRealtimeStreams() {
    realtimeStreams.forEach((_, protocol) => {
      stopRealtimeStream(protocol);
    });
  }

  return {
    // 状态
    protocolStates,
    currentProtocol,
    currentState,

    // 基础操作
    addLog,
    addBatchLogs,
    clearProtocolLogs,
    clearAllLogs,
    updateProtocolState,
    switchProtocol,

    // 查询和统计
    getProtocolStats,
    getRecentLogs,
    searchLogs,
    exportLogs,

    // 实时流
    startRealtimeStream,
    addToRealtimeStream,
    stopRealtimeStream,
    stopAllRealtimeStreams
  };
}
