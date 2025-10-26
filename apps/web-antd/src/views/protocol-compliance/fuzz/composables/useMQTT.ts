/**
 * MQTT协议专用的composable
 * 包含MBFuzzer相关的数据处理和UI逻辑
 */

import { ref, type Ref } from 'vue';
import type { 
  MQTTStats, 
  MQTTMessageStats, 
  MQTTDifferentialReport, 
  MQTTBrokerIssues,
  LogUIData 
} from './types';

export function useMQTT() {
  // MQTT统计数据
  const mqttStats: Ref<MQTTStats> = ref({
    fuzzing_start_time: '',
    fuzzing_end_time: '',
    client_request_count: 0,
    broker_request_count: 0,
    total_request_count: 0,
    crash_number: 0,
    diff_number: 0,
    duplicate_diff_number: 0,
    valid_connect_number: 0,
    duplicate_connect_diff: 0,
    total_differences: 0,
    
    client_messages: createEmptyMQTTMessageStats(),
    broker_messages: createEmptyMQTTMessageStats(),
    duplicate_diffs: createEmptyMQTTMessageStats(),
    differential_reports: [],
    q_table_states: [],
    broker_issues: {
      hivemq: 0,
      vernemq: 0,
      emqx: 0,
      flashmq: 0,
      nanomq: 0,
      mosquitto: 0
    }
  });

  // 创建空的MQTT消息统计
  function createEmptyMQTTMessageStats(): MQTTMessageStats {
    return {
      CONNECT: 0,
      CONNACK: 0,
      PUBLISH: 0,
      PUBACK: 0,
      PUBREC: 0,
      PUBREL: 0,
      PUBCOMP: 0,
      SUBSCRIBE: 0,
      SUBACK: 0,
      UNSUBSCRIBE: 0,
      UNSUBACK: 0,
      PINGREQ: 0,
      PINGRESP: 0,
      DISCONNECT: 0,
      AUTH: 0
    };
  }

  // 重置MQTT统计数据
  function resetMQTTStats() {
    mqttStats.value = {
      fuzzing_start_time: '',
      fuzzing_end_time: '',
      client_request_count: 0,
      broker_request_count: 0,
      total_request_count: 0,
      crash_number: 0,
      diff_number: 0, // 实时累加模式：从0开始
      duplicate_diff_number: 0,
      valid_connect_number: 0,
      duplicate_connect_diff: 0,
      total_differences: 0, // 与diff_number保持同步
      
      client_messages: createEmptyMQTTMessageStats(),
      broker_messages: createEmptyMQTTMessageStats(),
      duplicate_diffs: createEmptyMQTTMessageStats(),
      differential_reports: [],
      q_table_states: [],
      broker_issues: {
        hivemq: 0,
        vernemq: 0,
        emqx: 0,
        flashmq: 0,
        nanomq: 0,
        mosquitto: 0
      }
    };
  }

  // 解析差异报告行
  function parseDifferentialReport(line: string, timestamp: string): MQTTDifferentialReport | null {
    try {
      const diffInfo: MQTTDifferentialReport = {
        protocol_version: null,
        type: null,
        field: null,
        diff_range_broker: [],
        msg_type: null,
        direction: null,
        file_path: null,
        capture_time: null
      };
      
      // 提取协议版本
      const versionMatch = line.match(/protocol_version:\s*(\d+)/);
      if (versionMatch) {
        diffInfo.protocol_version = parseInt(versionMatch[1]);
      }
      
      // 提取差异类型
      const typeMatch = line.match(/type:\s*\{([^}]+)\}/);
      if (typeMatch) {
        diffInfo.type = typeMatch[1].trim();
      }
      
      // 提取字段名（如果存在）
      const fieldMatch = line.match(/field:\s*([^,]+?)(?:,|$)/);
      if (fieldMatch) {
        diffInfo.field = fieldMatch[1].trim();
      }
      
      // 提取受影响的代理
      const brokerMatch = line.match(/diff_range_broker:\s*\[([^\]]+)\]/);
      if (brokerMatch) {
        diffInfo.diff_range_broker = brokerMatch[1]
          .split(',')
          .map(broker => broker.trim().replace(/'/g, ''));
      }
      
      // 提取消息类型
      const msgTypeMatch = line.match(/msg_type:\s*([^,]+)/);
      if (msgTypeMatch) {
        diffInfo.msg_type = msgTypeMatch[1].trim();
      }
      
      // 提取方向
      const directionMatch = line.match(/direction:\s*([^,]+)/);
      if (directionMatch) {
        diffInfo.direction = directionMatch[1].trim();
      }
      
      // 提取捕获时间
      const timeMatch = line.match(/capture_time:\s*([^,\s]+(?:\s+[^,\s]+)*)/);
      if (timeMatch) {
        diffInfo.capture_time = timeMatch[1].trim();
      }
      
      // 添加到差异报告列表
      mqttStats.value.differential_reports.push(diffInfo);
      
      // 更新代理问题统计
      diffInfo.diff_range_broker.forEach(broker => {
        if (mqttStats.value.broker_issues.hasOwnProperty(broker)) {
          (mqttStats.value.broker_issues as any)[broker]++;
        }
      });
      
      return diffInfo;
      
    } catch (error) {
      console.warn('解析差异报告失败:', line, error);
      return null;
    }
  }

  // 根据差异类型确定严重程度
  function getDiffSeverityType(diffType: string): LogUIData['type'] {
    switch (diffType) {
      case 'Message Unexpected':
      case 'Message Missing':
        return 'ERROR';  // 消息级别差异，严重
      case 'Field Different':
      case 'Field Missing':
      case 'Field Unexpected':
        return 'WARNING'; // 字段级别差异，中等
      default:
        return 'INFO';
    }
  }

  // 根据差异类型获取图标
  function getTypeIcon(diffType: string): string {
    switch (diffType) {
      case 'Message Unexpected':
        return '⚠️';  // 意外消息
      case 'Message Missing':
        return '❌';  // 缺失消息
      case 'Field Different':
        return '🔄';  // 字段差异
      case 'Field Missing':
        return '🚫';  // 缺失字段
      case 'Field Unexpected':
        return '❗';  // 意外字段
      default:
        return '🔍';  // 一般差异
    }
  }

  // 处理MQTT协议的MBFuzzer日志行
  function processMQTTLogLine(line: string, packetCount: Ref<number>, successCount: Ref<number>, crashCount: Ref<number>) {
    const timestamp = new Date().toLocaleTimeString();
    
    try {
      // 优先处理差异报告 - 这是Fuzz过程的核心输出
      if (line.includes('protocol_version:') && (line.includes('type: {') || line.includes('field:'))) {
        const diffInfo = parseDifferentialReport(line, timestamp);
        if (diffInfo) {
          const brokerList = diffInfo.diff_range_broker.join(', ');
          const fieldInfo = diffInfo.field ? ` → ${diffInfo.field}` : '';
          const directionIcon = diffInfo.direction === 'client' ? '📤' : '📥';
          const typeIcon = getTypeIcon(diffInfo.type || '');
          
          // 构建更直观的差异描述
          let content = '';
          switch (diffInfo.type) {
            case 'Message Unexpected':
              content = `${typeIcon} 【协议差异】意外消息: ${diffInfo.msg_type} ${directionIcon} | 代理: ${brokerList} | MQTT v${diffInfo.protocol_version}`;
              break;
            case 'Message Missing':
              content = `${typeIcon} 【协议差异】缺失消息: ${diffInfo.msg_type} ${directionIcon} | 代理: ${brokerList} | MQTT v${diffInfo.protocol_version}`;
              break;
            case 'Field Different':
              content = `${typeIcon} 【协议差异】字段差异: ${diffInfo.msg_type}${fieldInfo} ${directionIcon} | 代理: ${brokerList} | MQTT v${diffInfo.protocol_version}`;
              break;
            case 'Field Missing':
              content = `${typeIcon} 【协议差异】缺失字段: ${diffInfo.msg_type}${fieldInfo} ${directionIcon} | 代理: ${brokerList} | MQTT v${diffInfo.protocol_version}`;
              break;
            case 'Field Unexpected':
              content = `${typeIcon} 【协议差异】意外字段: ${diffInfo.msg_type}${fieldInfo} ${directionIcon} | 代理: ${brokerList} | MQTT v${diffInfo.protocol_version}`;
              break;
            default:
              content = `${typeIcon} 【协议差异】${diffInfo.type}${fieldInfo} | ${diffInfo.msg_type} ${directionIcon} | 代理: ${brokerList} | MQTT v${diffInfo.protocol_version}`;
          }
          
          return {
            timestamp,
            type: getDiffSeverityType(diffInfo.type || ''),
            content,
            diffInfo,
            isDetailedDiff: true
          } as LogUIData;
        }
        return null;
      }
      
      // 解析基本统计信息（静默处理，不显示在Fuzz过程中）
      if (line.includes('Fuzzing Start Time:')) {
        const match = line.match(/Fuzzing Start Time:\s*(.+)/);
        if (match) {
          mqttStats.value.fuzzing_start_time = match[1].trim();
          // 只在开始时显示一次简单消息
          if (!mqttStats.value.fuzzing_end_time) {
            return {
              timestamp,
              type: 'INFO',
              content: `🚀 MBFuzzer 开始MQTT协议模糊测试...`
            } as LogUIData;
          }
        }
        return null;
      }
      
      if (line.includes('Fuzzing End Time:')) {
        const match = line.match(/Fuzzing End Time:\s*(.+)/);
        if (match) {
          mqttStats.value.fuzzing_end_time = match[1].trim();
          return {
            timestamp,
            type: 'SUCCESS',
            content: `✅ MBFuzzer 测试完成，正在生成测试总结...`
          } as LogUIData;
        }
        return null;
      }
      
      // 解析请求数量统计（静默处理，不在fuzz过程中显示）
      if (line.includes('Fuzzing request number (client):')) {
        const match = line.match(/Fuzzing request number \(client\):\s*(\d+)/);
        if (match) {
          mqttStats.value.client_request_count = parseInt(match[1]);
          packetCount.value = mqttStats.value.client_request_count + mqttStats.value.broker_request_count;
        }
        return null; // 静默处理，不显示
      }
      
      if (line.includes('Fuzzing request number (broker):')) {
        const match = line.match(/Fuzzing request number \(broker\):\s*(\d+)/);
        if (match) {
          mqttStats.value.broker_request_count = parseInt(match[1]);
          packetCount.value = mqttStats.value.client_request_count + mqttStats.value.broker_request_count;
        }
        return null; // 静默处理，不显示
      }
      
      // 解析消息类型统计（静默处理）
      const messageMatch = line.match(/^\s*([A-Z]+):\s*(\d+)/);
      if (messageMatch) {
        const [, messageType, count] = messageMatch;
        const countNum = parseInt(count);
        
        if (mqttStats.value.client_messages.hasOwnProperty(messageType)) {
          // 简单的启发式判断：如果客户端统计还是0，则认为是客户端数据
          if (mqttStats.value.client_messages[messageType as keyof MQTTMessageStats] === 0 && 
              mqttStats.value.broker_messages[messageType as keyof MQTTMessageStats] === 0) {
            (mqttStats.value.client_messages as any)[messageType] = countNum;
          } else if (mqttStats.value.broker_messages[messageType as keyof MQTTMessageStats] === 0) {
            (mqttStats.value.broker_messages as any)[messageType] = countNum;
          }
        }
        return null;
      }
      
      // 解析崩溃和差异统计（静默处理，不在fuzz过程中显示）
      if (line.includes('Crash Number:')) {
        const match = line.match(/Crash Number:\s*(\d+)/);
        if (match) {
          mqttStats.value.crash_number = parseInt(match[1]);
          crashCount.value = mqttStats.value.crash_number;
        }
        return null; // 静默处理，不显示
      }
      
      if (line.includes('Diff Number:')) {
        // 注意：不再从日志解析diff_number，改为实时累加模式
        // diff_number现在由addUnifiedLog函数实时递增
        return null; // 静默处理，不显示
      }
      
      if (line.includes('Valid Connect Number:')) {
        const match = line.match(/Valid Connect Number:\s*(\d+)/);
        if (match) {
          mqttStats.value.valid_connect_number = parseInt(match[1]);
          successCount.value = parseInt(match[1]);
        }
        return null; // 静默处理，不显示
      }
      
    } catch (error) {
      console.warn('解析MQTT日志行失败:', line, error);
    }
    
    return null;
  }

  return {
    mqttStats,
    resetMQTTStats,
    parseDifferentialReport,
    getDiffSeverityType,
    processMQTTLogLine,
    createEmptyMQTTMessageStats
  };
}
