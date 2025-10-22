/**
 * SNMP协议专用的composable
 * 包含SNMP_Fuzz相关的数据处理和UI逻辑
 */

import { ref, type Ref } from 'vue';
import type { FuzzPacket, SNMPStats, SNMPMessageStats } from './types';

export function useSNMP() {
  // SNMP统计数据
  const protocolStats: Ref<SNMPStats> = ref({ v1: 0, v2c: 0, v3: 0 });
  const messageTypeStats: Ref<SNMPMessageStats> = ref({ get: 0, set: 0, getnext: 0, getbulk: 0 });

  // 重置SNMP统计数据
  function resetSNMPStats() {
    protocolStats.value = { v1: 0, v2c: 0, v3: 0 };
    messageTypeStats.value = { get: 0, set: 0, getnext: 0, getbulk: 0 };
  }

  // 生成默认测试数据
  function generateDefaultFuzzData() {
    return `[1] 版本=v1, 类型=get
选择OIDs=['1.3.6.1.2.1.1.1.0']
报文HEX: 302902010004067075626C6963A01C02040E8F83C502010002010030
[发送尝试] 长度=43 字节
[接收成功] 42 字节
[2] 版本=v2c, 类型=set
选择OIDs=['1.3.6.1.2.1.1.2.0']
报文HEX: 304502010104067075626C6963A03802040E8F83C502010002010030
[发送尝试] 长度=71 字节
[接收超时]
[3] 版本=v3, 类型=getnext
选择OIDs=['1.3.6.1.2.1.1.3.0']
报文HEX: 305502010304067075626C6963A04802040E8F83C502010002010030
[发送尝试] 长度=87 字节
[接收成功] 156 字节
[4] 生成失败: 无效的OID格式
[5] 版本=v1, 类型=getbulk
选择OIDs=['1.3.6.1.2.1.1.4.0']
报文HEX: 306502010004067075626C6963A05802040E8F83C502010002010030
[发送尝试] 长度=103 字节
[运行监控] 收到崩溃通知: 健康服务报告 VM 不可达
[崩溃信息] 疑似崩溃数据包: 306502010004067075626C6963A05802040E8F83C502010002010030
[崩溃信息] 崩溃队列信息导出: /home/hhh/下载/snmp_fuzz/snmp_github/snmp_fuzz/scan_result/crash_logs/20251014-110318
[运行监控] 检测到崩溃，停止 fuzz 循环
统计: {'v1': 3, 'v2c': 1, 'v3': 1}, {'get': 2, 'set': 1, 'getnext': 1, 'getbulk': 1}
开始时间: 2025-01-14 11:03:18
结束时间: 2025-01-14 11:03:25
总耗时: 7.2 秒
发送总数据包: 5
平均发送速率: 0.69 包/秒`;
  }

  // 解析SNMP文本数据
  function parseSNMPText(text: string): FuzzPacket[] {
    if (!text || typeof text !== 'string') {
      console.error('Invalid fuzz data format');
      return [];
    }

    const lines = text.split('\n');
    console.log('解析文本总行数:', lines.length);
    
    if (lines.length < 5) {
      console.error('Insufficient fuzz data');
      return [];
    }

    const fuzzData: FuzzPacket[] = [];
    let currentPacket: FuzzPacket | null = null;
    let localFailedCount = 0;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      const packetMatch = line.match(/^\[(\d+)\]\s+版本=([^,]+),\s+类型=([^,]+)/);
      if (packetMatch) {
        if (currentPacket) fuzzData.push(currentPacket);
        const packetNumber = parseInt(packetMatch[1]);
        
        // 调试信息：每100个包输出一次
        if (packetNumber % 100 === 0 || packetNumber <= 5) {
          console.log(`解析数据包 #${packetNumber}: 版本=${packetMatch[2]}, 类型=${packetMatch[3]}`);
        }
        currentPacket = {
          id: packetNumber,
          version: packetMatch[2],
          type: packetMatch[3],
          oids: [],
          hex: '',
          result: 'unknown',
          responseSize: 0,
          timestamp: new Date().toLocaleTimeString(),
          failed: false,
        };
        continue;
      }

      const failedMatch = line.match(/^\[(\d+)\]\s+生成失败:/);
      if (failedMatch) {
        const failedId = parseInt(failedMatch[1]);
        localFailedCount++;
        if (currentPacket && currentPacket.id === failedId) {
          currentPacket.result = 'failed';
          currentPacket.failed = true;
          currentPacket.failedReason = line;
          currentPacket.timestamp = new Date().toLocaleTimeString();
          fuzzData.push(currentPacket);
          currentPacket = null;
        } else {
          fuzzData.push({ 
            id: failedId, 
            version: 'unknown', 
            type: 'unknown', 
            oids: [], 
            hex: '', 
            result: 'failed', 
            responseSize: 0, 
            timestamp: new Date().toLocaleTimeString(), 
            failed: true, 
            failedReason: line 
          });
        }
        continue;
      }

      if (line.includes('选择OIDs=') && currentPacket) {
        const oidMatch = line.match(/选择OIDs=\[(.*?)\]/);
        if (oidMatch) currentPacket.oids = oidMatch[1].split(',').map((oid) => oid.trim().replace(/'/g, ''));
        continue;
      }

      if (line.includes('报文HEX:') && currentPacket) {
        const hexMatch = line.match(/报文HEX:\s*([A-F0-9]+)/);
        if (hexMatch) currentPacket.hex = hexMatch[1];
        continue;
      }

      if (line.includes('[发送尝试]') && currentPacket) {
        const sizeMatch = line.match(/长度=(\d+)\s*字节/);
        if (sizeMatch) (currentPacket as any).sendSize = parseInt(sizeMatch[1]);
        continue;
      }

      if (line.includes('[接收成功]') && currentPacket) {
        const sizeMatch = line.match(/(\d+)\s*字节/);
        if (sizeMatch) {
          currentPacket.responseSize = parseInt(sizeMatch[1]);
          currentPacket.result = 'success';
        }
        continue;
      }
      
      if (line.includes('[接收超时]') && currentPacket) {
        currentPacket.result = 'timeout';
        continue;
      }

      if (line.includes('[运行监控]')) {
        const isExactCrashNotice = line.includes('[运行监控] 收到崩溃通知: 健康服务报告 VM 不可达');
        if (isExactCrashNotice || line.includes('崩溃通知')) {
          const crashEvent = { 
            type: 'crash_notification', 
            message: line, 
            timestamp: new Date().toLocaleTimeString(), 
            crashPacket: '', 
            crashLogPath: '' 
          };
          
          for (let j = i + 1; j < lines.length && j < i + 30; j++) {
            const nextLine = lines[j].trim();
            if (nextLine.includes('[崩溃信息] 疑似崩溃数据包:')) {
              crashEvent.crashPacket = nextLine.replace('[崩溃信息] 疑似崩溃数据包: ', '');
            } else if (nextLine.includes('[崩溃信息] 崩溃队列信息导出:')) {
              crashEvent.crashLogPath = nextLine.replace('[崩溃信息] 崩溃队列信息导出: ', '');
            }
            if (crashEvent.crashPacket && crashEvent.crashLogPath) break;
          }
          
          fuzzData.push({ 
            id: 'crash_event', 
            version: 'crash', 
            type: 'crash', 
            oids: [], 
            hex: crashEvent.crashPacket, 
            result: 'crash', 
            responseSize: 0, 
            timestamp: crashEvent.timestamp, 
            crashEvent 
          });
          
          if (currentPacket) { 
            currentPacket.result = 'crash'; 
            (currentPacket as any).crashInfo = line; 
          }
        } else if (line.includes('检测到崩溃')) {
          if (currentPacket) (currentPacket as any).monitorInfo = line;
        }
        continue;
      }
    }

    if (currentPacket) fuzzData.push(currentPacket);
    
    console.log('解析完成统计:');
    console.log('- 总数据包数:', fuzzData.length);
    console.log('- 失败数据包数:', localFailedCount);

    // 解析统计信息
    const statsLine = (text.match(/^统计:.*$/m) || [])[0];
    if (statsLine) {
      const objMatch = statsLine.match(/统计:\s*(\{[^}]+\})\s*,\s*(\{[^}]+\})/);
      if (objMatch) {
        try {
          const versionJson = objMatch[1].replace(/'/g, '"');
          const typeJson = objMatch[2].replace(/'/g, '"');
          const parsedVersion = JSON.parse(versionJson);
          const parsedType = JSON.parse(typeJson);
          protocolStats.value = { 
            v1: parsedVersion.v1 || 0, 
            v2c: parsedVersion.v2c || 0, 
            v3: parsedVersion.v3 || 0 
          };
          messageTypeStats.value = { 
            get: parsedType.get || 0, 
            set: parsedType.set || 0, 
            getnext: parsedType.getnext || 0, 
            getbulk: parsedType.getbulk || 0 
          };
        } catch (error) {
          console.warn('解析统计信息失败:', error);
        }
      }
    }

    return fuzzData;
  }

  return {
    protocolStats,
    messageTypeStats,
    resetSNMPStats,
    generateDefaultFuzzData,
    parseSNMPText
  };
}
