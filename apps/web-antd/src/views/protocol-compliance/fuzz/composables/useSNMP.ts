/**
 * SNMP协议专用的composable
 * 包含SNMP_Fuzz相关的数据处理和UI逻辑
 */

import { ref, nextTick, type Ref } from 'vue';
import type { FuzzPacket, SNMPStats, SNMPMessageStats } from './types';

export function useSNMP() {
  // SNMP统计数据
  const protocolStats: Ref<SNMPStats> = ref({ v1: 0, v2c: 0, v3: 0 });
  const messageTypeStats: Ref<SNMPMessageStats> = ref({ get: 0, set: 0, getnext: 0, getbulk: 0 });
  
  // 数据状态
  const fuzzData = ref<FuzzPacket[]>([]);
  const totalPacketsInFile = ref(0);
  const fileTotalPackets = ref(0);
  const fileSuccessCount = ref(0);
  const fileTimeoutCount = ref(0);
  const fileFailedCount = ref(0);

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

    const parsedData: FuzzPacket[] = [];
    let currentPacket: FuzzPacket | null = null;
    let localFailedCount = 0;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      const packetMatch = line.match(/^\[(\d+)\]\s+版本=([^,]+),\s+类型=([^,]+)/);
      if (packetMatch) {
        if (currentPacket) parsedData.push(currentPacket);
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
          parsedData.push(currentPacket);
          currentPacket = null;
        } else {
          parsedData.push({ 
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
          
          parsedData.push({ 
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

    if (currentPacket) parsedData.push(currentPacket);
    
    console.log('解析完成统计:');
    console.log('- 总数据包数:', parsedData.length);
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

    // 更新状态变量
    fuzzData.value = parsedData;
    totalPacketsInFile.value = parsedData.filter((p) => typeof p.id === 'number').length;
    fileTotalPackets.value = parsedData.length;
    fileSuccessCount.value = parsedData.filter(p => p.result === 'success').length;
    fileTimeoutCount.value = parsedData.filter(p => p.result === 'timeout').length;
    fileFailedCount.value = localFailedCount;
    
    return parsedData;
  }

  // 处理SNMP数据包
  function processSNMPPacket(packet: FuzzPacket, addLogToUI: (packet: FuzzPacket, isCrash: boolean) => void, updateCounters?: (result: string) => void) {
    try {
      // Update protocol stats
      if (packet.version === 'v1') protocolStats.value.v1++;
      else if (packet.version === 'v2c') protocolStats.value.v2c++;
      else if (packet.version === 'v3') protocolStats.value.v3++;
      
      // Update message type stats
      if (packet.type === 'get') messageTypeStats.value.get++;
      else if (packet.type === 'set') messageTypeStats.value.set++;
      else if (packet.type === 'getnext') messageTypeStats.value.getnext++;
      else if (packet.type === 'getbulk') messageTypeStats.value.getbulk++;
      
      // Update result counters through callback if provided
      if (updateCounters) {
        updateCounters(packet.result || 'unknown');
      }
      
      // Add to UI log (sparse updates for performance)
      if (packet.result !== 'crash' && Math.random() < 0.1) { // 10% chance to show
        addLogToUI(packet, false);
      } else if (packet.result === 'crash') {
        addLogToUI(packet, true);
      }
    } catch (error) {
      console.warn('Error processing SNMP packet:', error);
    }
  }

  // SNMP专用的日志显示函数
  function addSNMPLogToUI(packet: FuzzPacket, isCrash: boolean, logContainer: HTMLElement | null, showHistoryView: boolean, isRunning: boolean) {
    // 检查DOM元素是否存在且在实时测试视图中
    if (!logContainer || showHistoryView || !isRunning) {
      return;
    }
    
    // Use nextTick to ensure DOM is stable before manipulation
    nextTick(() => {
      try {
        // Double-check DOM element still exists after nextTick
        if (!logContainer || !logContainer.appendChild || showHistoryView || !isRunning) {
          return;
        }
        
        const div = document.createElement('div');
        div.className = isCrash ? 'crash-highlight' : 'packet-highlight';
        
        if (isCrash) {
          div.innerHTML = `<span class="text-dark/50">[${packet.timestamp || ''}]</span> <span class="text-danger font-bold">CRASH DETECTED</span> <span class="text-danger">${packet.version?.toUpperCase() || 'UNKNOWN'}</span> <span class="text-danger">${packet.type?.toUpperCase() || 'UNKNOWN'}</span>`;
        } else {
          const protocol = packet.version?.toUpperCase() || 'UNKNOWN';
          const op = packet.type?.toUpperCase() || 'UNKNOWN';
          const time = packet.timestamp || '';
          const content = packet.oids?.[0] || '';
          const hex = (packet.hex || '').slice(0, 40);
          const resultText = packet.result === 'success' ? `正常响应 (${packet.responseSize || 0}字节)` : 
                            packet.result === 'timeout' ? '接收超时' : 
                            packet.result === 'failed' ? '构造失败' : '未知状态';
          const resultClass = packet.result === 'success' ? 'text-success' : 
                             packet.result === 'timeout' ? 'text-warning' : 
                             packet.result === 'failed' ? 'text-danger' : 'text-warning';
          
          div.innerHTML = `<span class="text-dark/50">[${time}]</span> <span class="text-primary">SNMP${protocol}</span> <span class="text-info">${op}</span> <span class="text-dark/70 truncate inline-block w-32" title="${content}">${content}</span> <span class="${resultClass} font-medium">${resultText}</span> <span class="text-dark/40">${hex}...</span>`;
        }
        
        // Final check before DOM manipulation
        if (logContainer && logContainer.appendChild) {
          logContainer.appendChild(div);
          
          // Safely update scroll position
          if (logContainer.scrollTop !== undefined) {
            logContainer.scrollTop = logContainer.scrollHeight;
          }
          
          // Limit log entries for performance with safe checks
          if (logContainer.children && logContainer.children.length > 200) {
            const firstChild = logContainer.firstChild;
            if (firstChild && logContainer.removeChild) {
              logContainer.removeChild(firstChild);
            }
          }
        }
      } catch (error) {
        console.warn('Failed to add SNMP log to UI:', error);
      }
    });
  }

  // SNMP测试启动函数
  async function startSNMPTest(loop: () => void) {
    // SNMP协议的原有逻辑
    console.log('启动SNMP测试...');
    loop();
  }

  return {
    protocolStats,
    messageTypeStats,
    fuzzData,
    totalPacketsInFile,
    fileTotalPackets,
    fileSuccessCount,
    fileTimeoutCount,
    fileFailedCount,
    resetSNMPStats,
    generateDefaultFuzzData,
    parseSNMPText,
    processSNMPPacket,
    addSNMPLogToUI,
    startSNMPTest
  };
}
