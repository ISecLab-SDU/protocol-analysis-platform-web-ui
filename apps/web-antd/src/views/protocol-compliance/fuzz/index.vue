<script setup lang="ts">
import { onMounted, ref, nextTick, computed, watch } from 'vue';
import { getFuzzText } from '#/api/custom';
import Chart from 'chart.js/auto';

// 导入协议专用的composables
import { 
  useSNMP, 
  useRTSP, 
  useMQTT, 
  useLogReader,
  type FuzzPacket,
  type HistoryResult,
  type ProtocolType,
  type FuzzEngineType
} from './composables';

// Data state
const rawText = ref('');
const loading = ref(true);
const error = ref<string | null>(null);

// 使用composables中的协议专用逻辑
const { 
  protocolStats, 
  messageTypeStats, 
  fuzzData: snmpFuzzData,
  totalPacketsInFile: snmpTotalPacketsInFile,
  fileTotalPackets: snmpFileTotalPackets,
  fileSuccessCount: snmpFileSuccessCount,
  fileTimeoutCount: snmpFileTimeoutCount,
  fileFailedCount: snmpFileFailedCount,
  resetSNMPStats, 
  generateDefaultFuzzData, 
  parseSNMPText,
  startSNMPTest,
  processSNMPPacket,
  addSNMPLogToUI
} = useSNMP();
const { rtspStats, resetRTSPStats, processRTSPLogLine, writeRTSPScript, executeRTSPCommand, stopRTSPProcess } = useRTSP();
const { mqttStats, resetMQTTStats, processMQTTLogLine } = useMQTT();
const { 
  logContainer, 
  isReadingLog, 
  logReadingInterval, 
  logReadPosition,
  startLogReading, 
  stopLogReading, 
  resetLogReader, 
  addMQTTLogToUI, 
  addRTSPLogToUI, 
  clearLog 
} = useLogReader();

const fuzzData = ref<FuzzPacket[]>([]);
const totalPacketsInFile = ref(0);
// File-level summary stats parsed from txt
const fileTotalPackets = ref(0);
const fileSuccessCount = ref(0);
const fileTimeoutCount = ref(0);
const fileFailedCount = ref(0);

// 协议统计数据现在通过composables管理

// Runtime stats
const packetCount = ref(0);
const successCount = ref(0);
const timeoutCount = ref(0);
const failedCount = ref(0);
const crashCount = ref(0);
const elapsedTime = ref(0);
const packetsPerSecond = ref(30);
const testDuration = ref(60);
const isRunning = ref(false);
const isTestCompleted = ref(false);
let testTimer: number | null = null;

// UI configuration
const protocolType = ref<ProtocolType>('SNMP');
const fuzzEngine = ref<FuzzEngineType>('SNMP_Fuzz');
const targetHost = ref('192.168.102.2');
const targetPort = ref(161);
const rtspCommandConfig = ref('afl-fuzz -d -i $AFLNET/tutorials/live555/in-rtsp -o out-live555 -N tcp://127.0.0.1/8554 -x $AFLNET/tutorials/live555/rtsp.dict -P RTSP -D 10000 -q 3 -s 3 -E -K -R ./testOnDemandRTSPServer 8554');

// Real-time log reading (现在通过useLogReader管理)
const rtspProcessId = ref<number | null>(null);

// Watch for protocol changes to update port and fuzz engine
watch(protocolType, (newProtocol) => {
  if (newProtocol === 'SNMP') {
    targetPort.value = 161;
    fuzzEngine.value = 'SNMP_Fuzz';
  } else if (newProtocol === 'RTSP') {
    targetPort.value = 554;
    fuzzEngine.value = 'AFLNET';
  } else if (newProtocol === 'MQTT') {
    targetPort.value = 1883;
    fuzzEngine.value = 'MBFuzzer';
  }
});
const showCharts = ref(false);
const crashDetails = ref<any>(null);
const logEntries = ref<any[]>([]);
const startTime = ref<string>('');
const endTime = ref<string>('');
const lastUpdate = ref<string>('');
const currentSpeed = ref(0);
const isPaused = ref(false);
const showCrashDetails = ref(false);
const testStartTime = ref<Date | null>(null);
const testEndTime = ref<Date | null>(null);
const currentPacketIndex = ref(0);
const packetDelay = ref(33); // 1000/30 = 33ms for 30 packets/second

// 历史结果相关状态
const showHistoryView = ref(false);
const selectedHistoryItem = ref<any>(null);

// 通知相关状态
const showNotification = ref(false);
const notificationMessage = ref('');

// HistoryResult 接口现在从 composables 导入

// 模拟历史结果数据
const historyResults = ref<HistoryResult[]>([
  {
    id: 'hist_001',
    timestamp: '2025-01-20 14:30:25',
    protocol: 'SNMP',
    fuzzEngine: 'SNMP_Fuzz',
    targetHost: '192.168.102.2',
    targetPort: 161,
    duration: 127,
    totalPackets: 2847,
    successCount: 2156,
    timeoutCount: 542,
    failedCount: 149,
    crashCount: 0,
    successRate: 76,
    protocolStats: { v1: 1203, v2c: 892, v3: 752 },
    messageTypeStats: { get: 1124, set: 678, getnext: 589, getbulk: 456 },
    hasCrash: false
  },
  {
    id: 'hist_002',
    timestamp: '2025-01-20 11:15:42',
    protocol: 'SNMP',
    fuzzEngine: 'SNMP_Fuzz',
    targetHost: '192.168.102.5',
    targetPort: 161,
    duration: 89,
    totalPackets: 1924,
    successCount: 1456,
    timeoutCount: 321,
    failedCount: 89,
    crashCount: 58,
    successRate: 76,
    protocolStats: { v1: 823, v2c: 612, v3: 489 },
    messageTypeStats: { get: 756, set: 445, getnext: 398, getbulk: 325 },
    hasCrash: true,
    crashDetails: {
      id: 1847,
      time: '11:16:23',
      type: 'Segmentation Fault (SIGSEGV)',
      dumpFile: '/var/crash/SNMP_crash_1737360983.dmp',
      logPath: '/home/hhh/下载/snmp_fuzz/snmp_github/snmp_fuzz/scan_result/crash_logs/20250120-111623',
      details: '[11:16:23] Segmentation Fault (SIGSEGV)\nProcess ID: 8472\nFault Address: 0x7F8B2C40\nRegisters:\n  EAX: 0x00000000  EBX: 0x7F8B2C40\n  ECX: 0x12345678  EDX: 0xDEADBEEF\n  ESI: 0x87654321  EDI: 0xCAFEBABE\n  EBP: 0x7FFF1234  ESP: 0x7FFF1200\nBacktrace:\n  #0  0x08048567 in get_handler()\n  #1  0x08048234 in packet_processor()\n  #2  0x08047890 in main_loop()',
      packetContent: '302902010004067075626C6963A01C02040E8F83C502010002010030'
    }
  },
  {
    id: 'hist_003',
    timestamp: '2025-01-19 16:45:18',
    protocol: 'SNMP',
    fuzzEngine: 'AFLNET',
    targetHost: '10.0.0.15',
    targetPort: 161,
    duration: 203,
    totalPackets: 4521,
    successCount: 3892,
    timeoutCount: 456,
    failedCount: 173,
    crashCount: 0,
    successRate: 86,
    protocolStats: { v1: 1789, v2c: 1456, v3: 1276 },
    messageTypeStats: { get: 1823, set: 1124, getnext: 892, getbulk: 682 },
    hasCrash: false
  }
]);

// UI refs (logContainer现在通过useLogReader管理)
const messageCanvas = ref<HTMLCanvasElement>();
const versionCanvas = ref<HTMLCanvasElement>();
let messageTypeChart: any = null;
let versionChart: any = null;

// Computed properties
const progressWidth = computed(() => {
  const estimatedTotal = Math.max(packetCount.value, testDuration.value * packetsPerSecond.value);
  return estimatedTotal > 0 ? Math.min(100, Math.round((packetCount.value / estimatedTotal) * 100)) : 0;
});

const successRate = computed(() => {
  const total = successCount.value + timeoutCount.value + failedCount.value + crashCount.value;
  return total > 0 ? Math.round((successCount.value / total) * 100) : 0;
});

const timeoutRate = computed(() => {
  const total = successCount.value + timeoutCount.value + failedCount.value + crashCount.value;
  return total > 0 ? Math.round((timeoutCount.value / total) * 100) : 0;
});

const failedRate = computed(() => {
  const total = successCount.value + timeoutCount.value + failedCount.value + crashCount.value;
  return total > 0 ? Math.round((failedCount.value / total) * 100) : 0;
});

// generateDefaultFuzzData 现在通过 useSNMP composable 提供

async function fetchText() {
  loading.value = true;
  try {
    const resp = await getFuzzText();
    const text = (resp as any)?.text ?? (resp as any)?.data?.text ?? '';
    console.log('API响应数据长度:', text?.length || 0);
    console.log('API响应前100字符:', text?.substring(0, 100) || '无数据');
    
    if (!text || text.trim().length === 0) {
      console.warn('API返回空数据，使用默认数据');
      rawText.value = generateDefaultFuzzData();
    } else {
      rawText.value = text;
    }
  } catch (e: any) {
    console.error('API调用失败:', e);
    error.value = `API调用失败: ${e?.message || '未知错误'}`;
    rawText.value = generateDefaultFuzzData();
    console.warn('API failed, using default data:', e?.message);
  } finally {
    loading.value = false;
  }
}

function initCharts() {
  if (!messageCanvas.value || !versionCanvas.value) {
    console.warn('Canvas elements not ready');
    return false;
  }

  try {
    const messageCtx = messageCanvas.value.getContext('2d');
    const versionCtx = versionCanvas.value.getContext('2d');
    if (!messageCtx || !versionCtx) {
      console.warn('Failed to get canvas contexts');
      return false;
    }

  messageTypeChart = new Chart(messageCtx, {
    type: 'doughnut',
    data: {
      labels: ['GET', 'SET', 'GETNEXT', 'GETBULK'],
      datasets: [{ 
        data: [0, 0, 0, 0], 
        backgroundColor: ['#3B82F6', '#6366F1', '#EC4899', '#10B981'], 
        borderColor: '#FFFFFF', 
        borderWidth: 3, 
        hoverOffset: 8 
      }],
    },
    options: { 
      responsive: true, 
      maintainAspectRatio: false, 
      plugins: { 
        legend: { 
          position: 'bottom', 
          labels: { 
            color: '#1F2937', 
            padding: 15, 
            font: { size: 12, weight: 'bold' }, 
            usePointStyle: true 
          } 
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: 'white',
          bodyColor: 'white',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1,
          callbacks: {
            label: function(context: any) {
              const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
              const percentage = total > 0 ? Math.round((context.parsed / total) * 100) : 0;
              return `${context.label}: ${context.parsed} (${percentage}%)`;
            }
          }
        }
      }, 
      cutout: '60%' 
    },
  });

    versionChart = new Chart(versionCtx, {
      type: 'doughnut',
      data: { 
        labels: ['SNMP v1', 'SNMP v2c', 'SNMP v3'], 
        datasets: [{ 
          data: [0, 0, 0], 
          backgroundColor: ['#F59E0B', '#8B5CF6', '#EF4444'], 
          borderColor: '#FFFFFF', 
          borderWidth: 3, 
          hoverOffset: 8 
        }] 
      },
      options: { 
        responsive: true, 
        maintainAspectRatio: false, 
        plugins: { 
          legend: { 
            position: 'bottom', 
            labels: { 
              color: '#1F2937', 
              padding: 15, 
              font: { size: 12, weight: 'bold' }, 
              usePointStyle: true 
            } 
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: 'white',
            bodyColor: 'white',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            callbacks: {
              label: function(context: any) {
                const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
                const percentage = total > 0 ? Math.round((context.parsed / total) * 100) : 0;
                return `${context.label}: ${context.parsed} (${percentage}%)`;
              }
            }
          }
        }, 
        cutout: '60%' 
      },
    });
    
    console.log('Charts initialized successfully');
    return true;
  } catch (error) {
    console.error('Failed to initialize charts:', error);
    return false;
  }
}

function updateCharts() {
  try {
    if (!messageTypeChart || !versionChart) {
      console.warn('Charts not initialized, skipping update');
      return;
    }
    
    // Update message type chart
    if (messageTypeChart.data && messageTypeChart.data.datasets && messageTypeChart.data.datasets[0]) {
      messageTypeChart.data.datasets[0].data = [
        messageTypeStats.value.get || 0,
        messageTypeStats.value.set || 0,
        messageTypeStats.value.getnext || 0,
        messageTypeStats.value.getbulk || 0,
      ];
      messageTypeChart.update('none'); // Use 'none' animation mode for better performance
    }

    // Update version chart
    if (versionChart.data && versionChart.data.datasets && versionChart.data.datasets[0]) {
      versionChart.data.datasets[0].data = [
        protocolStats.value.v1 || 0,
        protocolStats.value.v2c || 0,
        protocolStats.value.v3 || 0,
      ];
      versionChart.update('none'); // Use 'none' animation mode for better performance
    }
    
    console.log('Charts updated successfully');
  } catch (error) {
    console.error('Error updating charts:', error);
  }
}

function parseText(text: string) {
  // 使用SNMP composable的解析功能
  const parsedData = parseSNMPText(text);
  fuzzData.value = parsedData;
  totalPacketsInFile.value = parsedData.filter((p) => typeof p.id === 'number').length;
  
  // Extract timing information
  const startTimeMatch = text.match(/开始时间:\s*([^\n]+)/);
  const endTimeMatch = text.match(/结束时间:\s*([^\n]+)/);
  const durationMatch = text.match(/总耗时:\s*([\d.]+)\s*秒/);
  const totalPacketsMatch = text.match(/发送总数据包:\s*(\d+)/) || text.match(/\[日志系统\]\s*数据包统计:\s*(\d+)\s*\/\s*\d+\s*个/);
  const avgSpeedMatch = text.match(/平均发送速率:\s*([\d.]+)\s*包\/秒/);
  
  if (startTimeMatch) startTime.value = startTimeMatch[1];
  if (endTimeMatch) endTime.value = endTimeMatch[1];
  if (durationMatch) testDuration.value = parseFloat(durationMatch[1]);
  if (avgSpeedMatch) packetsPerSecond.value = parseFloat(avgSpeedMatch[1]);

  // Counters from file
  const successCountInFile = (text.match(/\[接收成功\]/g) || []).length;
  const timeoutCountInFile = (text.match(/\[接收超时\]/g) || []).length;
  const failedCountInFile = (text.match(/生成失败:/g) || []).length;
  fileSuccessCount.value = successCountInFile;
  fileTimeoutCount.value = timeoutCountInFile;
  fileFailedCount.value = failedCountInFile;
  fileTotalPackets.value = totalPacketsMatch ? parseInt(totalPacketsMatch[1]) : successCountInFile + timeoutCountInFile + failedCountInFile;
}

function resetTestState() {
  try {
    // Reset all counters in a batch
    packetCount.value = 0;
    successCount.value = 0;
    timeoutCount.value = 0;
    failedCount.value = 0;
    crashCount.value = 0;
    elapsedTime.value = 0;
    currentPacketIndex.value = 0;
    crashDetails.value = null;
    isPaused.value = false;
    showCrashDetails.value = false;
    logEntries.value = [];
    
    // 重置协议专用的统计数据
    resetSNMPStats();
    resetRTSPStats();
    resetMQTTStats();
    
    // 重置日志读取器
    resetLogReader();
    
    // Reset log container with proper checks
    nextTick(() => {
      try {
        clearLog();
      } catch (error) {
        console.warn('Failed to reset log container:', error);
      }
    });
  } catch (error) {
    console.error('Error in resetTestState:', error);
  }
}

async function startTest() {
  // MQTT协议不需要fuzzData，直接从文件读取
  if (protocolType.value !== 'MQTT' && !fuzzData.value.length) return;
  
  resetTestState();
  isRunning.value = true;
  isTestCompleted.value = false;
  showCharts.value = false; // 测试开始时隐藏图表
  testStartTime.value = new Date();
  
  // 根据协议类型执行不同的启动逻辑
  try {
    if (protocolType.value === 'RTSP') {
      await startRTSPTest();
    } else if (protocolType.value === 'SNMP') {
      await startSNMPTest(loop);
    } else if (protocolType.value === 'MQTT') {
      await startMQTTTest();
    } else {
      throw new Error(`不支持的协议类型: ${protocolType.value}`);
    }
  } catch (error: any) {
    console.error('启动测试失败:', error);
    addLogToUI({ 
      timestamp: new Date().toLocaleTimeString(),
      version: protocolType.value,
      type: 'ERROR',
      oids: [],
      hex: '',
      result: 'failed',
      failedReason: `启动失败: ${error.message}`
    } as any, false);
    isRunning.value = false;
    return;
  }
  
  // 启动通用计时器
  if (testTimer) { clearInterval(testTimer as any); testTimer = null; }
  testTimer = window.setInterval(() => { 
    if (!isPaused.value) {
      elapsedTime.value++;
      currentSpeed.value = elapsedTime.value > 0 ? Math.round(packetCount.value / elapsedTime.value) : 0;
    }
  }, 1000);
}

// Protocol-specific test functions
async function startRTSPTest() {
  try {
    // 1. 写入脚本文件
    await writeRTSPScriptWrapper();
    
    // 2. 执行shell命令启动程序
    await executeRTSPCommandWrapper();
    
    // 3. 开始实时读取日志
    startRTSPLogReading();
    
    addLogToUI({ 
      timestamp: new Date().toLocaleTimeString(),
      version: 'RTSP',
      type: 'START',
      oids: ['RTSP测试已启动'],
      hex: '',
      result: 'success'
    } as any, false);
    
  } catch (error: any) {
    console.error('RTSP测试启动失败:', error);
    throw error;
  }
}

// startSNMPTest 现在通过 useSNMP composable 提供

async function startMQTTTest() {
  try {
    // 重置MQTT统计数据
    resetMQTTStats();
    
    // 直接开始模拟MQTT测试过程，不依赖后端API
    addMQTTLogToUI({ 
      timestamp: new Date().toLocaleTimeString(),
      type: 'INFO',
      content: 'MBFuzzer MQTT协议模糊测试已启动'
    });
    
    // 先解析统计数据
    await parseMQTTStatsFromFile();
    
    // 开始读取差异报告
    await startMQTTDifferentialReading();
    
  } catch (error: any) {
    console.error('MQTT测试启动失败:', error);
    throw error;
  }
}

// resetMQTTStats 现在通过 useMQTT composable 提供

// 解析MQTT统计数据从文件
async function parseMQTTStatsFromFile() {
  try {
    const response = await fetch('/apps/backend-flask/protocol_compliance/mbfuzzer_logs/fuzzing_report.txt');
    if (!response.ok) {
      throw new Error('无法读取fuzzing_report.txt文件');
    }
    
    const content = await response.text();
    const lines = content.split('\n');
    
    // 解析统计数据
    for (const line of lines) {
      // 解析客户端请求数
      if (line.includes('Fuzzing request number (client):')) {
        const match = line.match(/Fuzzing request number \(client\):\s*(\d+)/);
        if (match) {
          mqttStats.value.client_request_count = parseInt(match[1]);
        }
      }
      
      // 解析代理端请求数
      if (line.includes('Fuzzing request number (broker):')) {
        const match = line.match(/Fuzzing request number \(broker\):\s*(\d+)/);
        if (match) {
          mqttStats.value.broker_request_count = parseInt(match[1]);
        }
      }
      
      // 解析崩溃数量
      if (line.includes('Crash Number:')) {
        const match = line.match(/Crash Number:\s*(\d+)/);
        if (match) {
          mqttStats.value.crash_number = parseInt(match[1]);
          crashCount.value = mqttStats.value.crash_number;
        }
      }
      
      // 解析差异数量
      if (line.includes('Diff Number:')) {
        const match = line.match(/Diff Number:\s*(\d+)/);
        if (match) {
          mqttStats.value.diff_number = parseInt(match[1]);
        }
      }
      
      // 解析有效连接数
      if (line.includes('Valid Connect Number:')) {
        const match = line.match(/Valid Connect Number:\s*(\d+)/);
        if (match) {
          mqttStats.value.valid_connect_number = parseInt(match[1]);
          successCount.value = parseInt(match[1]);
        }
      }
      
      // 解析开始时间
      if (line.includes('Fuzzing Start Time:')) {
        const match = line.match(/Fuzzing Start Time:\s*(.+)/);
        if (match) {
          mqttStats.value.fuzzing_start_time = match[1].trim();
          startTime.value = match[1].trim();
        }
      }
      
      // 解析结束时间
      if (line.includes('Fuzzing End Time:')) {
        const match = line.match(/Fuzzing End Time:\s*(.+)/);
        if (match) {
          mqttStats.value.fuzzing_end_time = match[1].trim();
          endTime.value = match[1].trim();
        }
      }
    }
    
    // 计算总请求数
    mqttStats.value.total_request_count = mqttStats.value.client_request_count + mqttStats.value.broker_request_count;
    fileTotalPackets.value = mqttStats.value.total_request_count;
    fileSuccessCount.value = mqttStats.value.valid_connect_number;
    
    console.log('MQTT统计数据解析完成:', mqttStats.value);
    
  } catch (error: any) {
    console.error('解析MQTT统计数据失败:', error);
  }
}

// MQTT差异报告数据存储 - 简化版本
const mqttDifferentialLogs = ref<string[]>([]);
const mqttLogCount = ref(0);

// 开始MQTT差异报告读取 - 简化版本，避免DOM冲突
async function startMQTTDifferentialReading() {
  try {
    // 重置状态
    mqttDifferentialLogs.value = [];
    mqttLogCount.value = 0;
    
    // 添加开始日志
    const startTime = new Date().toLocaleTimeString();
    mqttDifferentialLogs.value.push(`[${startTime}] INFO: 开始分析协议差异报告`);
    
    // 直接读取fuzzing_report.txt文件内容
    const response = await fetch('/apps/backend-flask/protocol_compliance/mbfuzzer_logs/fuzzing_report.txt');
    if (!response.ok) {
      throw new Error('无法读取fuzzing_report.txt文件');
    }
    
    const content = await response.text();
    const lines = content.split('\n');
    
    // 找到"Differential Report:"部分
    let inDifferentialSection = false;
    let processedCount = 0;
    let localErrorCount = 0;
    let localWarningCount = 0;
    let localSuccessCount = 0;
    const maxDisplayCount = 50; // 限制显示数量，避免界面过载
    const logBuffer: string[] = []; // 使用缓冲区批量添加
    
    for (const line of lines) {
      if (line.trim() === 'Differential Report:') {
        inDifferentialSection = true;
        continue;
      }
      
      if (inDifferentialSection && line.trim() && processedCount < maxDisplayCount) {
        // 解析差异报告行
        const diffData = parseMQTTDifferentialLine(line);
        if (diffData) {
          processedCount++;
          
          // 统计数据
          if (diffData.type === 'ERROR') {
            localErrorCount++;
          } else if (diffData.type === 'WARNING') {
            localWarningCount++;
          } else {
            localSuccessCount++;
          }
          
          // 创建简单的日志字符串
          const timestamp = new Date().toLocaleTimeString();
          const logLine = `[${timestamp}] ${diffData.type}: ${diffData.content}`;
          logBuffer.push(logLine);
          
          // 每10条批量添加
          if (logBuffer.length >= 10) {
            mqttDifferentialLogs.value.push(...logBuffer);
            logBuffer.length = 0; // 清空缓冲区
            
            // 更新统计数据
            packetCount.value = processedCount;
            failedCount.value = localErrorCount;
            timeoutCount.value = localWarningCount;
            successCount.value = localSuccessCount;
            
            // 短暂延迟
            await new Promise(resolve => setTimeout(resolve, 50));
          }
        }
      }
    }
    
    // 添加剩余的日志
    if (logBuffer.length > 0) {
      mqttDifferentialLogs.value.push(...logBuffer);
    }
    
    // 最终更新统计数据
    packetCount.value = processedCount;
    failedCount.value = localErrorCount;
    timeoutCount.value = localWarningCount;
    successCount.value = localSuccessCount;
    mqttLogCount.value = processedCount;
    
    // 处理完成
    const completeTime = new Date().toLocaleTimeString();
    mqttDifferentialLogs.value.push(`[${completeTime}] SUCCESS: 差异报告分析完成，共处理 ${processedCount} 条差异记录`);
    
    // MQTT测试完成，设置状态
    isRunning.value = false;
    isPaused.value = false;
    isTestCompleted.value = true;
    testEndTime.value = new Date();
    
    // 停止计时器
    if (testTimer) { 
      clearInterval(testTimer as any); 
      testTimer = null; 
    }
    
    // 延迟保存历史记录
    setTimeout(() => {
      try {
        updateTestSummary();
        saveTestToHistory();
      } catch (error) {
        console.error('Error saving MQTT test results:', error);
      }
    }, 500);
    
  } catch (error: any) {
    console.error('读取MQTT差异报告失败:', error);
    const errorTime = new Date().toLocaleTimeString();
    mqttDifferentialLogs.value.push(`[${errorTime}] ERROR: 读取差异报告失败: ${error.message}`);
  }
}

// 处理MQTT差异报告行，参照SNMP样式
function processMQTTDifferentialLine(line: string) {
  try {
    // 提取关键信息
    const versionMatch = line.match(/protocol_version:\s*(\d+)/);
    const typeMatch = line.match(/type:\s*\{([^}]+)\}/);
    const msgTypeMatch = line.match(/msg_type:\s*([^,]+)/);
    const brokerMatch = line.match(/diff_range_broker:\s*\[([^\]]+)\]/);
    const directionMatch = line.match(/direction:\s*([^,]+)/);
    const fieldMatch = line.match(/field:\s*([^,]+)/);
    
    if (!versionMatch || !typeMatch || !msgTypeMatch) {
      return null;
    }
    
    const version = versionMatch[1];
    const diffType = typeMatch[1].trim();
    const msgType = msgTypeMatch[1].trim();
    const brokers = brokerMatch ? brokerMatch[1].replace(/'/g, '').split(',').map(b => b.trim()).join(', ') : '未知';
    const direction = directionMatch ? directionMatch[1].trim() : '未知';
    const field = fieldMatch ? fieldMatch[1].trim() : null;
    
    // 根据差异类型确定严重程度
    let severity: 'INFO' | 'WARNING' | 'ERROR' = 'INFO';
    
    switch (diffType) {
      case 'Message Missing':
      case 'Message Unexpected':
        severity = 'ERROR';
        break;
      case 'Field Different':
      case 'Field Missing':
      case 'Field Unexpected':
        severity = 'WARNING';
        break;
    }
    
    // 构建详细的输出内容，保留完整信息但去掉emoji
    const directionText = direction === 'client' ? '客户端' : '代理端';
    const fieldText = field ? ` 字段: ${field}` : '';
    const content = `[协议差异] MQTT v${version} ${msgType} (${directionText}) | ${diffType}${fieldText} | 受影响代理: ${brokers}`;
    
    return {
      timestamp: new Date().toLocaleTimeString(),
      type: severity,
      content
    };
    
  } catch (error) {
    console.warn('解析差异报告行失败:', line, error);
    return null;
  }
}

// 解析MQTT差异报告行 - 新版本，返回结构化数据
function parseMQTTDifferentialLine(line: string) {
  try {
    // 提取关键信息
    const versionMatch = line.match(/protocol_version:\s*(\d+)/);
    const typeMatch = line.match(/type:\s*\{([^}]+)\}/);
    const msgTypeMatch = line.match(/msg_type:\s*([^,]+)/);
    const brokerMatch = line.match(/diff_range_broker:\s*\[([^\]]+)\]/);
    const directionMatch = line.match(/direction:\s*([^,]+)/);
    const fieldMatch = line.match(/field:\s*([^,]+)/);
    
    if (!versionMatch || !typeMatch || !msgTypeMatch) {
      return null;
    }
    
    const protocolVersion = parseInt(versionMatch[1]);
    const diffType = typeMatch[1];
    const msgType = msgTypeMatch[1].trim();
    const brokers = brokerMatch ? brokerMatch[1].replace(/'/g, '').split(',').map(b => b.trim()) : [];
    const direction = directionMatch ? directionMatch[1].trim() : 'unknown';
    const field = fieldMatch ? fieldMatch[1].trim() : '';
    
    // 根据差异类型确定日志级别
    let logType: 'ERROR' | 'WARNING' | 'INFO' = 'INFO';
    if (diffType.includes('Missing') || diffType.includes('Unexpected')) {
      logType = 'ERROR';
    } else if (diffType.includes('Different')) {
      logType = 'WARNING';
    }
    
    // 构建显示内容
    let content = `MQTT v${protocolVersion} ${msgType} (${direction})`;
    if (field) {
      content += ` - 字段: ${field}`;
    }
    content += ` - 差异类型: ${diffType}`;
    if (brokers.length > 0) {
      content += ` - 影响代理: ${brokers.join(', ')}`;
    }
    
    return {
      type: logType,
      content: content,
      protocolVersion,
      msgType,
      direction,
      diffType,
      field,
      brokers
    };
  } catch (error) {
    console.warn('解析MQTT差异行失败:', error, line);
    return null;
  }
}

// 开始MQTT日志读取（保留原函数以备后用）
async function startMQTTLogReading() {
  // 使用 useLogReader 的 startLogReading 方法
  await startLogReading('MQTT', (line: string) => {
    return processMQTTLogLine(line, packetCount, successCount, crashCount);
  });
  
  // 使用 useLogReader 的 addMQTTLogToUI 函数
  addMQTTLogToUI({
    timestamp: new Date().toLocaleTimeString(),
    type: 'INFO',
    content: '开始解析MBFuzzer日志文件...'
  });
}

// MQTT日志读取函数现在通过 useLogReader 和 useMQTT composables 管理

// RTSP specific functions (现在通过 useRTSP composable 管理)
async function writeRTSPScriptWrapper() {
  const scriptContent = rtspCommandConfig.value;
  
  try {
    const result = await writeRTSPScript(scriptContent);
    
    addLogToUI({ 
      timestamp: new Date().toLocaleTimeString(),
      version: 'RTSP',
      type: 'SCRIPT',
      oids: [`脚本已写入: ${result.data?.filePath || '脚本文件'}`],
      hex: '',
      result: 'success'
    } as any, false);
    
  } catch (error: any) {
    console.error('写入RTSP脚本失败:', error);
    throw new Error(`写入脚本文件失败: ${error.message}`);
  }
}

async function executeRTSPCommandWrapper() {
  try {
    const result = await executeRTSPCommand();
    
    // 保存容器ID用于后续停止
    if (result.data && (result.data.container_id || result.data.pid)) {
      rtspProcessId.value = result.data.container_id || result.data.pid;
    }
    
    addLogToUI({ 
      timestamp: new Date().toLocaleTimeString(),
      version: 'RTSP',
      type: 'COMMAND',
      oids: [`Docker容器已启动 (ID: ${result.data?.container_id || result.data?.pid || 'unknown'})`],
      hex: '',
      result: 'success'
    } as any, false);
    
  } catch (error: any) {
    console.error('执行RTSP命令失败:', error);
    throw new Error(`执行启动命令失败: ${error.message}`);
  }
}

function startRTSPLogReading() {
  isReadingLog.value = true;
  
  // 开始实时日志读取
  readRTSPLogPeriodically();
  
  addLogToUI({ 
    timestamp: new Date().toLocaleTimeString(),
    version: 'RTSP',
    type: 'LOG',
    oids: [`开始读取日志`],
    hex: '',
    result: 'success'
  } as any, false);
}

async function readRTSPLogPeriodically() {
  if (logReadingInterval.value) {
    clearInterval(logReadingInterval.value);
  }
  
  logReadingInterval.value = window.setInterval(async () => {
    if (!isRunning.value || !isReadingLog.value) {
      if (logReadingInterval.value) {
        clearInterval(logReadingInterval.value);
        logReadingInterval.value = null;
      }
      return;
    }
    
    try {
      // 调用后端API读取日志文件
      const response = await fetch('/api/protocol-compliance/read-log', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          protocol: 'RTSP',
          lastPosition: logReadPosition.value // 使用实际的读取位置，实现增量读取
        }),
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.data && result.data.content && result.data.content.trim()) {
          // 更新读取位置
          logReadPosition.value = result.data.position || logReadPosition.value;
          
          // 处理AFL-NET的plot_data格式
          const logLines = result.data.content.split('\n').filter((line: string) => line.trim());
          logLines.forEach((line: string) => {
            processRTSPLogLine(line);
          });
        }
      }
    } catch (error) {
      console.error('读取RTSP日志失败:', error);
    }
  }, 2000); // 每2秒读取一次日志
}

// processMQTTLogLine 现在通过 useMQTT composable 提供

// processRTSPLogLine 现在通过 useRTSP composable 提供

// addMQTTLogToUI 和 addRTSPLogToUI 现在通过 useLogReader composable 提供

async function stopRTSPProcessWrapper() {
  if (!rtspProcessId.value) {
    return;
  }
  
  try {
    await stopRTSPProcess(rtspProcessId.value);
    
    addLogToUI({ 
      timestamp: new Date().toLocaleTimeString(),
      version: 'RTSP',
      type: 'STOP',
      oids: [`RTSP进程已停止 (PID: ${rtspProcessId.value})`],
      hex: '',
      result: 'success'
    } as any, false);
    
    rtspProcessId.value = null;
  } catch (error) {
    console.error('停止RTSP进程失败:', error);
  }
}

// 处理停止测试的安全包装函数
function handleStopTest() {
  try {
    if (protocolType.value === 'MQTT') {
      // MQTT协议使用安全的停止方式
      stopMQTTTest();
    } else {
      // 其他协议使用原来的stopTest
      stopTest();
    }
  } catch (error) {
    console.error('Error in handleStopTest:', error);
  }
}

// MQTT专用的安全停止函数
function stopMQTTTest() {
  try {
    console.log('Stopping MQTT test safely...');
    
    // 直接设置状态，避免DOM操作
    isRunning.value = false;
    isPaused.value = false;
    isTestCompleted.value = true;
    testEndTime.value = new Date();
    
    // 停止计时器
    if (testTimer) { 
      clearInterval(testTimer as any); 
      testTimer = null; 
    }
    
    // 停止日志读取
    isReadingLog.value = false;
    if (logReadingInterval.value) {
      clearInterval(logReadingInterval.value);
      logReadingInterval.value = null;
    }
    
    // 延迟保存历史记录
    setTimeout(() => {
      try {
        updateTestSummary();
        saveTestToHistory();
      } catch (error) {
        console.error('Error saving MQTT test results:', error);
      }
    }, 300);
    
  } catch (error) {
    console.error('Error in stopMQTTTest:', error);
  }
}

function stopTest() {
  try {
    // 如果是MQTT协议，重定向到安全的停止函数
    if (protocolType.value === 'MQTT') {
      console.log('Redirecting MQTT test to safe stop function');
      stopMQTTTest();
      return;
    }
    
    // Set completion state first
    isRunning.value = false;
    isPaused.value = false;
    isTestCompleted.value = true;
    testEndTime.value = new Date();
    
    // 停止日志读取
    isReadingLog.value = false;
    if (logReadingInterval.value) {
      clearInterval(logReadingInterval.value);
      logReadingInterval.value = null;
    }
    
    // 停止协议特定的进程
    if (protocolType.value === 'RTSP') {
      stopRTSPProcessWrapper();
    } else if (protocolType.value === 'MQTT') {
      // MQTT协议的清理工作通过 useLogReader 管理
      stopLogReading();
    }
    
    if (testTimer) { 
      clearInterval(testTimer as any); 
      testTimer = null; 
    }
    
    // Update final statistics
    updateTestSummary();
    
    // Save test results to history
    saveTestToHistory();
    
    console.log('Test completed, updating charts:', {
      isTestCompleted: isTestCompleted.value,
      protocolStats: protocolStats.value,
      messageTypeStats: messageTypeStats.value
    });
    
    // Use nextTick to ensure all reactive updates are complete before updating charts
    // 跳过MQTT协议的图表更新，避免DOM冲突
    if (protocolType.value !== 'MQTT') {
      nextTick(() => {
        try {
          // 只有在测试真正完成且不是MQTT协议时才更新图表
          if (isTestCompleted.value) {
            // Double-check charts are initialized before updating
            if (messageTypeChart && versionChart) {
              updateCharts();
              showCharts.value = true;
            } else {
              // Try to reinitialize charts if they're not available
              console.log('Charts not initialized, attempting to reinitialize...');
              const success = initCharts();
              if (success) {
                updateCharts();
                showCharts.value = true;
              } else {
                console.warn('Failed to reinitialize charts');
              }
            }
          }
        } catch (error) {
          console.error('Error updating charts on test completion:', error);
        }
      });
    } else {
      console.log('MQTT protocol: skipping chart updates to avoid DOM conflicts');
    }
  } catch (error) {
    console.error('Error in stopTest function:', error);
  }
}

function togglePauseTest() {
  isPaused.value = !isPaused.value;
  if (!isPaused.value && isRunning.value) {
    loop();
  }
}

// 本地clearLog函数，同时清空MQTT差异报告
function clearMQTTLogs() {
  mqttDifferentialLogs.value = [];
  mqttLogCount.value = 0;
}

// clearLog 现在通过 useLogReader composable 提供

function saveLog() {
  if (logEntries.value.length === 0) {
    // Generate a test report even if no log entries
    generateTestReport();
    return;
  }
  
  let logText = `时间,类型,内容\n`;
  logEntries.value.forEach(entry => {
    if (entry.type) {
      logText += `${entry.time},${entry.type},${entry.message}\n`;
    } else {
      logText += `${entry.time},${entry.result},${entry.protocol},${entry.operation},${entry.target},${entry.content},${entry.hex}\n`;
    }
  });
  
  const blob = new Blob([logText], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `fuzz_log_${new Date().getTime()}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function generateTestReport() {
  const reportContent = `Fuzz测试报告\n` +
                       `================\n\n` +
                       `协议: ${protocolType.value.toUpperCase()}\n` +
                       `引擎: ${fuzzEngine.value}\n` +
                       `目标: ${targetHost.value}:${targetPort.value}\n` +
                       `开始时间: ${startTime.value || (testStartTime.value ? testStartTime.value.toLocaleString() : '未开始')}\n` +
                       `结束时间: ${endTime.value || (testEndTime.value ? testEndTime.value.toLocaleString() : '未结束')}\n` +
                       `总耗时: ${elapsedTime.value}秒\n\n` +
                       `性能统计:\n` +
                       `SNMP_v1发包数: ${protocolStats.value.v1}\n` +
                       `SNMP_v2发包数: ${protocolStats.value.v2c}\n` +
                       `SNMP_v3发包数: ${protocolStats.value.v3}\n` +
                       `总发包数: ${fileTotalPackets.value}\n` +
                       `正常响应率: ${Math.round((fileSuccessCount.value / Math.max(fileTotalPackets.value, 1)) * 100)}%\n` +
                       `超时率: ${Math.round((fileTimeoutCount.value / Math.max(fileTotalPackets.value, 1)) * 100)}%\n\n` +
                       `崩溃信息: ${crashDetails.value ? '检测到崩溃' : '无崩溃'}\n` +
                       `生成时间: ${new Date().toLocaleString()}`;
  
  const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `fuzz_report_${new Date().getTime()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function loop() {
  try {
    // 检查测试是否应该继续运行
    if (!isRunning.value || isPaused.value || showHistoryView.value) {
      return;
    }
    
    if (currentPacketIndex.value >= fuzzData.value.length) {
      return stopTest();
    }
    
    const packet = fuzzData.value[currentPacketIndex.value];
    if (packet) {
      processSNMPPacket(packet, addLogToUI);
    }
    
    // Batch update counters to prevent multiple reactive updates
    currentPacketIndex.value++;
    packetCount.value++;
    
    // Check for crash and stop if detected
    if (packet?.result === 'crash') {
      handleCrashDetection(packet);
      // Add a small delay before stopping to ensure UI updates complete
      setTimeout(() => {
        if (isRunning.value) { // Double-check we're still running
          stopTest();
        }
      }, 150);
      return;
    }
    
    // Continue loop with appropriate delay, but check again if we should continue
    if (isRunning.value && !isPaused.value && !showHistoryView.value) {
      window.setTimeout(() => {
        // Additional safety check before continuing
        if (isRunning.value && !isPaused.value && !showHistoryView.value) {
          loop();
        }
      }, packetDelay.value);
    }
  } catch (error) {
    console.error('Error in loop function:', error);
    // Stop the test if there's an error to prevent infinite loops
    if (isRunning.value) {
      stopTest();
    }
  }
}

// processPacket 现在通过 useSNMP composable 的 processSNMPPacket 提供

function addLogToUI(packet: FuzzPacket, isCrash: boolean) {
  // 使用 SNMP composable 的 addSNMPLogToUI 函数
  addSNMPLogToUI(packet, isCrash, logContainer.value, showHistoryView.value, isRunning.value);
}

// Crash handling functions
function generateRandomHex(length = 30) {
  const chars = '0123456789ABCDEF';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

function generateCrashDetails(packetId: number | string, protocol: string, operation: string, content: string) {
  const crashTypes = [
    "Segmentation Fault (SIGSEGV)",
    "Aborted (SIGABRT)", 
    "Illegal Instruction (SIGILL)",
    "Bus Error (SIGBUS)",
    "Floating Point Exception (SIGFPE)"
  ];
  
  const crashType = crashTypes[Math.floor(Math.random() * crashTypes.length)];
  const timestamp = new Date().toLocaleTimeString();
  const dumpFile = `/var/crash/${protocol}_crash_${Date.now()}.dmp`;
  const logPath = `/home/hhh/下载/snmp_fuzz/snmp_github/snmp_fuzz/scan_result/crash_logs/${new Date().toISOString().slice(0,10).replace(/-/g,'')}-${timestamp.replace(/:/g,'')}`;
  
  const detailsText = `[${timestamp}] ${crashType}\n` +
                     `Process ID: ${Math.floor(Math.random() * 10000) + 1000}\n` +
                     `Fault Address: 0x${generateRandomHex(8)}\n` +
                     `Registers:\n` +
                     `  EAX: 0x${generateRandomHex(8)}  EBX: 0x${generateRandomHex(8)}\n` +
                     `  ECX: 0x${generateRandomHex(8)}  EDX: 0x${generateRandomHex(8)}\n` +
                     `  ESI: 0x${generateRandomHex(8)}  EDI: 0x${generateRandomHex(8)}\n` +
                     `  EBP: 0x${generateRandomHex(8)}  ESP: 0x${generateRandomHex(8)}\n` +
                     `Backtrace:\n` +
                     `  #0  0x${generateRandomHex(8)} in ${operation}_handler()\n` +
                     `  #1  0x${generateRandomHex(8)} in packet_processor()\n` +
                     `  #2  0x${generateRandomHex(8)} in main_loop()\n`;
  
  return {
    id: packetId,
    time: timestamp,
    type: crashType,
    dumpFile: dumpFile,
    logPath: logPath,
    details: detailsText,
    packetContent: content
  };
}

function handleCrashDetection(packet: FuzzPacket) {
  if (packet.crashEvent) {
    crashDetails.value = {
      id: packetCount.value,
      time: packet.crashEvent.timestamp,
      type: "程序崩溃",
      dumpFile: packet.crashEvent.crashLogPath,
      logPath: packet.crashEvent.crashLogPath,
      details: `崩溃通知: ${packet.crashEvent.message}\n疑似崩溃数据包: ${packet.crashEvent.crashPacket}\n崩溃队列信息导出: ${packet.crashEvent.crashLogPath}`,
      packetContent: packet.crashEvent.crashPacket
    };
    addRealCrashLogEntries(packet.crashEvent);
  } else {
    crashDetails.value = generateCrashDetails(packetCount.value, packet.version, packet.type, packet.hex);
    addCrashLogEntries(crashDetails.value, packet.version, packet.hex);
  }
}

function addRealCrashLogEntries(crashEvent: any) {
  const time = new Date().toLocaleTimeString();
  
  // Add crash logs to entries
  logEntries.value.push(
    { time, type: 'crash_notice', message: crashEvent.message },
    { time, type: 'crash_packet', message: `疑似崩溃数据包: ${crashEvent.crashPacket}` },
    { time, type: 'crash_export', message: `崩溃队列信息导出: ${crashEvent.crashLogPath}` },
    { time, type: 'stop_fuzz', message: '检测到崩溃，停止 fuzz 循环' }
  );
  
  // Add to UI with proper error handling and DOM checks
  nextTick(() => {
    try {
      if (logContainer.value && !showHistoryView.value && isRunning.value && logContainer.value.appendChild) {
        const logs = [
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">${crashEvent.message || '崩溃通知'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 疑似崩溃数据包: ${crashEvent.crashPacket || '未知'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 崩溃队列信息导出: ${crashEvent.crashLogPath || '未知路径'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">[运行监控] 检测到崩溃，停止 fuzz 循环</span>`
        ];
        
        logs.forEach(logHtml => {
          if (logContainer.value && logContainer.value.appendChild) {
            const div = document.createElement('div');
            div.className = 'crash-highlight';
            div.innerHTML = logHtml;
            logContainer.value.appendChild(div);
          }
        });
        
        if (logContainer.value && logContainer.value.scrollTop !== undefined) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight;
        }
      }
    } catch (error) {
      console.warn('Failed to add crash log to UI:', error);
    }
  });
}

function addCrashLogEntries(crashDetails: any, protocol: string, hex: string) {
  const time = new Date().toLocaleTimeString();
  
  logEntries.value.push(
    { time, type: 'crash_notice', message: '收到崩溃通知: 健康服务报告 VM 不可达' },
    { time, type: 'crash_packet', message: `疑似崩溃数据包: ${hex}` },
    { time, type: 'log_dir', message: `日志导出目录: ${crashDetails.logPath}` },
    { time, type: 'timeout', message: '接收超时' },
    { time, type: 'no_response', message: '响应: 无' },
    { time, type: 'stop_fuzz', message: '检测到崩溃，停止 fuzz 循环' }
  );
  
  nextTick(() => {
    try {
      if (logContainer.value && !showHistoryView.value && isRunning.value && logContainer.value.appendChild) {
        const logs = [
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">[运行监控] 收到崩溃通知: 健康服务报告 VM 不可达</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 疑似崩溃数据包: ${hex || '未知'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 日志导出目录: ${crashDetails?.logPath || '未知路径'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-warning">  [接收超时]</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-warning">  响应: 无</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">[运行监控] 检测到崩溃，停止 fuzz 循环</span>`
        ];
        
        logs.forEach(logHtml => {
          if (logContainer.value && logContainer.value.appendChild) {
            const div = document.createElement('div');
            div.className = 'crash-highlight';
            div.innerHTML = logHtml;
            logContainer.value.appendChild(div);
          }
        });
        
        if (logContainer.value && logContainer.value.scrollTop !== undefined) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight;
        }
      }
    } catch (error) {
      console.warn('Failed to add crash log entries to UI:', error);
    }
  });
}

function updateTestSummary() {
  const total = fileTotalPackets.value || (successCount.value + timeoutCount.value + failedCount.value + crashCount.value);
  const successBase = fileSuccessCount.value || successCount.value;
  const timeoutBase = fileTimeoutCount.value || timeoutCount.value;
  
  lastUpdate.value = new Date().toLocaleString();
  
  // Update final statistics display
  if (total > 0) {
    // Use file-based statistics if available, otherwise use runtime statistics
    const finalSuccessCount = fileSuccessCount.value || successCount.value;
    const finalTimeoutCount = fileTimeoutCount.value || timeoutCount.value;
    const finalFailedCount = fileFailedCount.value || failedCount.value;
    
    console.log('Final test summary:', {
      total: fileTotalPackets.value,
      success: finalSuccessCount,
      timeout: finalTimeoutCount,
      failed: finalFailedCount,
      successRate: Math.round((finalSuccessCount / total) * 100),
      timeoutRate: Math.round((finalTimeoutCount / total) * 100)
    });
  }
}

// 保存测试结果到历史记录
function saveTestToHistory() {
  try {
    // 计算实际的测试统计数据
    const actualTotalPackets = fileTotalPackets.value || packetCount.value;
    const actualSuccessCount = fileSuccessCount.value || successCount.value;
    const actualTimeoutCount = fileTimeoutCount.value || timeoutCount.value;
    const actualFailedCount = fileFailedCount.value || failedCount.value;
    const actualCrashCount = crashCount.value;
    
    // 计算测试持续时间
    const duration = testStartTime.value && testEndTime.value 
      ? Math.round((testEndTime.value.getTime() - testStartTime.value.getTime()) / 1000)
      : elapsedTime.value;
    
    // 计算成功率
    const total = actualTotalPackets || (actualSuccessCount + actualTimeoutCount + actualFailedCount + actualCrashCount);
    const successRate = total > 0 ? Math.round((actualSuccessCount / total) * 100) : 0;
    
    // 生成唯一ID
    const historyId = `test_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // 创建历史记录条目
    const historyItem: HistoryResult = {
      id: historyId,
      timestamp: testStartTime.value ? testStartTime.value.toLocaleString() : new Date().toLocaleString(),
      protocol: protocolType.value,
      fuzzEngine: fuzzEngine.value,
      targetHost: targetHost.value,
      targetPort: targetPort.value,
      duration: duration,
      totalPackets: total,
      successCount: actualSuccessCount,
      timeoutCount: actualTimeoutCount,
      failedCount: actualFailedCount,
      crashCount: actualCrashCount,
      successRate: successRate,
      protocolStats: {
        v1: protocolStats.value.v1,
        v2c: protocolStats.value.v2c,
        v3: protocolStats.value.v3
      },
      messageTypeStats: {
        get: messageTypeStats.value.get,
        set: messageTypeStats.value.set,
        getnext: messageTypeStats.value.getnext,
        getbulk: messageTypeStats.value.getbulk
      },
      // 保存RTSP协议统计数据
      rtspStats: protocolType.value === 'RTSP' ? {
        cycles_done: rtspStats.value.cycles_done,
        paths_total: rtspStats.value.paths_total,
        cur_path: rtspStats.value.cur_path,
        pending_total: rtspStats.value.pending_total,
        pending_favs: rtspStats.value.pending_favs,
        map_size: rtspStats.value.map_size,
        unique_crashes: rtspStats.value.unique_crashes,
        unique_hangs: rtspStats.value.unique_hangs,
        max_depth: rtspStats.value.max_depth,
        execs_per_sec: rtspStats.value.execs_per_sec,
        n_nodes: rtspStats.value.n_nodes,
        n_edges: rtspStats.value.n_edges
      } : undefined,
      hasCrash: actualCrashCount > 0,
      crashDetails: crashDetails.value ? {
        id: crashDetails.value.id,
        time: crashDetails.value.time,
        type: crashDetails.value.type,
        dumpFile: crashDetails.value.dumpFile,
        logPath: crashDetails.value.logPath,
        details: crashDetails.value.details,
        packetContent: crashDetails.value.packetContent
      } : undefined
    };
    
    // 将新的测试结果添加到历史记录的开头
    historyResults.value.unshift(historyItem);
    
    // 限制历史记录数量，保留最新的50条
    if (historyResults.value.length > 50) {
      historyResults.value = historyResults.value.slice(0, 50);
    }
    
    // 保存到本地存储
    try {
      localStorage.setItem('fuzz_test_history', JSON.stringify(historyResults.value));
      console.log('Test results saved to history:', historyItem);
      
      // 显示保存成功的通知 - 对MQTT协议使用更安全的方式
      if (protocolType.value === 'MQTT') {
        // MQTT协议使用简单的控制台日志，避免DOM操作
        console.log('MQTT test results saved to history successfully');
      } else {
        showSaveNotification();
      }
    } catch (storageError) {
      console.warn('Failed to save history to localStorage:', storageError);
    }
    
  } catch (error) {
    console.error('Error saving test to history:', error);
  }
}

function toggleCrashDetailsView() {
  showCrashDetails.value = !showCrashDetails.value;
}

// 历史结果相关函数
function goToHistoryView() {
  showHistoryView.value = true;
  selectedHistoryItem.value = null;
}

function backToMainView() {
  showHistoryView.value = false;
  selectedHistoryItem.value = null;
}

function viewHistoryDetail(item: HistoryResult) {
  selectedHistoryItem.value = item;
}

function backToHistoryList() {
  selectedHistoryItem.value = null;
}

function deleteHistoryItem(id: string) {
  const index = historyResults.value.findIndex(item => item.id === id);
  if (index > -1) {
    historyResults.value.splice(index, 1);
    
    // 同步到本地存储
    try {
      localStorage.setItem('fuzz_test_history', JSON.stringify(historyResults.value));
      console.log('History item deleted and saved to localStorage');
    } catch (error) {
      console.warn('Failed to save updated history to localStorage:', error);
    }
  }
}

function exportHistoryItem(item: HistoryResult) {
  const reportContent = `Fuzz测试历史报告\n` +
                       `================\n\n` +
                       `测试ID: ${item.id}\n` +
                       `协议: ${item.protocol}\n` +
                       `引擎: ${item.fuzzEngine}\n` +
                       `目标: ${item.targetHost}:${item.targetPort}\n` +
                       `测试时间: ${item.timestamp}\n` +
                       `总耗时: ${item.duration}秒\n\n` +
                       `性能统计:\n` +
                       `总发包数: ${item.totalPackets}\n` +
                       `正常响应: ${item.successCount} (${item.successRate}%)\n` +
                       `超时: ${item.timeoutCount}\n` +
                       `失败: ${item.failedCount}\n` +
                       `崩溃: ${item.crashCount}\n\n` +
                       `协议版本分布:\n` +
                       `SNMP v1: ${item.protocolStats.v1}\n` +
                       `SNMP v2c: ${item.protocolStats.v2c}\n` +
                       `SNMP v3: ${item.protocolStats.v3}\n\n` +
                       `消息类型分布:\n` +
                       `GET: ${item.messageTypeStats.get}\n` +
                       `SET: ${item.messageTypeStats.set}\n` +
                       `GETNEXT: ${item.messageTypeStats.getnext}\n` +
                       `GETBULK: ${item.messageTypeStats.getbulk}\n\n` +
                       `崩溃信息: ${item.hasCrash ? '检测到崩溃' : '无崩溃'}\n` +
                       `生成时间: ${new Date().toLocaleString()}`;
  
  const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `history_report_${item.id}_${new Date().getTime()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 清空所有历史记录
function clearAllHistory() {
  if (confirm('确定要清空所有历史记录吗？此操作不可撤销。')) {
    historyResults.value = [];
    
    // 同步到本地存储
    try {
      localStorage.removeItem('fuzz_test_history');
      console.log('All history cleared');
    } catch (error) {
      console.warn('Failed to clear history from localStorage:', error);
    }
  }
}

// 导出所有历史记录
function exportAllHistory() {
  if (historyResults.value.length === 0) {
    alert('没有历史记录可导出');
    return;
  }
  
  const reportContent = `Fuzz测试历史记录汇总\n` +
                       `==================\n\n` +
                       `导出时间: ${new Date().toLocaleString()}\n` +
                       `总记录数: ${historyResults.value.length}\n\n` +
                       historyResults.value.map((item, index) => 
                         `${index + 1}. [${item.timestamp}] ${item.protocol} - ${item.fuzzEngine}\n` +
                         `   目标: ${item.targetHost}:${item.targetPort}\n` +
                         `   耗时: ${item.duration}秒, 总包数: ${item.totalPackets}, 成功率: ${item.successRate}%\n` +
                         `   崩溃: ${item.hasCrash ? '是' : '否'}\n`
                       ).join('\n');
  
  const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `fuzz_history_summary_${new Date().getTime()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 显示保存成功通知
function showSaveNotification() {
  try {
    // 使用nextTick确保DOM更新完成
    nextTick(() => {
      notificationMessage.value = '测试结果已保存到历史记录';
      showNotification.value = true;
      
      // 3秒后自动隐藏通知
      setTimeout(() => {
        try {
          showNotification.value = false;
        } catch (error) {
          console.warn('Failed to hide notification:', error);
        }
      }, 3000);
    });
  } catch (error) {
    console.warn('Failed to show notification:', error);
  }
}

// 手动关闭通知
function closeNotification() {
  showNotification.value = false;
}

// Computed properties for button states
const canStartTest = computed(() => {
  // MQTT协议不需要fuzzData
  if (protocolType.value === 'MQTT') {
    return !loading.value && !isRunning.value;
  }
  return !loading.value && 
         fuzzData.value.length > 0 && 
         !isRunning.value;
});

// Debug function for testing
function debugInfo() {
  console.log('Debug Info:', {
    loading: loading.value,
    error: error.value,
    fuzzDataLength: fuzzData.value.length,
    isRunning: isRunning.value,
    canStartTest: canStartTest.value,
    protocolStats: protocolStats.value,
    messageTypeStats: messageTypeStats.value
  });
}

const testStatusText = computed(() => {
  if (isRunning.value) {
    return isPaused.value ? '已暂停' : '运行中';
  }
  if (crashCount.value > 0) {
    return '检测到崩溃';
  }
  return '未开始';
});

const testStatusClass = computed(() => {
  if (isRunning.value) {
    return isPaused.value ? 'text-warning' : 'text-success';
  }
  if (crashCount.value > 0) {
    return 'text-danger';
  }
  return 'text-warning';
});

// 从本地存储加载历史记录
function loadHistoryFromStorage() {
  try {
    const stored = localStorage.getItem('fuzz_test_history');
    if (stored) {
      const parsedHistory = JSON.parse(stored);
      if (Array.isArray(parsedHistory)) {
        historyResults.value = parsedHistory;
        console.log(`Loaded ${parsedHistory.length} history items from localStorage`);
      }
    }
  } catch (error) {
    console.warn('Failed to load history from localStorage:', error);
    // 如果加载失败，保持默认的模拟数据
  }
}

onMounted(async () => {
  // 加载历史记录
  loadHistoryFromStorage();
  
  await fetchText();
  if (rawText.value) {
    parseText(rawText.value);
  }
  
  // Wait for DOM to be fully rendered before initializing charts
  await nextTick();
  
  // Initialize charts - Canvas elements should now always be available
  const success = initCharts();
  if (success) {
    console.log('Charts initialized successfully on mount');
    // Update charts with initial data but don't show them yet
    updateCharts();
    // 只有在有完整数据且测试已完成时才显示图表
    if (isTestCompleted.value) {
      showCharts.value = true;
    }
  } else {
    console.error('Failed to initialize charts');
  }
  
  // Set initial last update time
  lastUpdate.value = new Date().toLocaleString();
});
</script>

<template>
  <div class="bg-light text-dark font-sans min-h-screen flex flex-col">
      <!-- 顶部导航栏 -->
      <header class="bg-white/80 backdrop-blur-md border-b border-primary/20 sticky top-0 z-50 shadow-sm">
        <div class="w-full px-6 py-3 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="bg-primary/10 p-2 rounded-lg">
            <i class="fa fa-bug text-primary text-xl"></i>
          </div>
          <h1 class="text-xl md:text-2xl font-bold text-primary">
            多协议Fuzz测试平台
          </h1>
        </div>
        
        <div class="flex items-center space-x-4">
          <div class="hidden md:flex items-center space-x-1 bg-light-gray rounded-full px-3 py-1 border border-primary/20">
            <span class="text-xs text-primary/70">测试状态:</span>
            <span id="testStatus" :class="['text-xs font-medium flex items-center', testStatusClass]">
              <span :class="['w-2 h-2 rounded-full mr-1', 
                isRunning ? (isPaused ? 'bg-warning animate-pulse' : 'bg-success animate-pulse') : 
                (crashCount > 0 ? 'bg-danger animate-pulse' : 'bg-warning')]"></span>
              {{ testStatusText }}
            </span>
          </div>
          
          <!-- 数据加载状态 -->
          <div v-if="loading" class="flex items-center space-x-1 text-xs text-primary/70">
            <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-primary"></div>
            <span>加载中...</span>
          </div>
          
          <!-- 历史结果按钮 -->
          <button @click="goToHistoryView" class="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg transition-all duration-300 flex items-center space-x-2 shadow-md" title="查看历史结果">
            <i class="fa fa-history"></i>
            <span class="hidden md:inline">历史记录</span>
            <span v-if="historyResults.length > 0" class="bg-white/20 text-xs px-2 py-0.5 rounded-full ml-1">{{ historyResults.length }}</span>
          </button>
          
          <button class="bg-primary/10 hover:bg-primary/20 text-primary p-2 rounded-lg transition-all duration-300">
            <i class="fa fa-cog"></i>
          </button>
        </div>
      </div>
    </header>

      <!-- 主内容区 -->
      <main class="flex-1 w-full px-6 py-6 bg-grid">
      <!-- 加载状态 -->
      <div v-if="loading" class="flex items-center justify-center h-64">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <div class="text-red-600">{{ error }}</div>
      </div>

      <!-- 主要内容 -->
      <div v-else>
        <!-- 实时测试视图 -->
        <div v-if="!showHistoryView">
        
        <!-- 测试配置区 -->
        <div class="bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-primary/20 shadow-card mb-6">
          <h3 class="font-semibold text-lg mb-4">测试配置</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <!-- 协议选择 -->
            <div>
              <label class="block text-sm text-dark/70 mb-2">协议类型</label>
              <div class="relative">
                <select v-model="protocolType" class="w-full bg-white border border-primary/20 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary appearance-none">
                  <option value="SNMP">SNMP</option>
                  <option value="RTSP">RTSP</option>
                  <option value="MQTT">MQTT</option>
                </select>
                <i class="fa fa-chevron-down absolute right-3 top-2.5 text-dark/50 pointer-events-none"></i>
              </div>
            </div>
            
            <!-- Fuzz引擎选择 -->
            <div>
              <label class="block text-sm text-dark/70 mb-2">Fuzz引擎</label>
              <div class="relative">
                <select v-model="fuzzEngine" class="w-full bg-white border border-primary/20 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary appearance-none">
                  <option value="SNMP_Fuzz" v-if="protocolType === 'SNMP'">SNMP_Fuzz</option>
                  <option value="AFLNET" v-if="protocolType === 'RTSP'">AFLNET</option>
                  <option value="MBFuzzer" v-if="protocolType === 'MQTT'">MBFuzzer</option>
                </select>
                <i class="fa fa-chevron-down absolute right-3 top-2.5 text-dark/50 pointer-events-none"></i>
              </div>
            </div>
            
            <!-- 目标主机 -->
            <div>
              <label class="block text-sm text-dark/70 mb-2">目标主机</label>
              <div class="relative">
                <input type="text" v-model="targetHost" 
                      class="w-full bg-white border border-primary/20 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary">
                <i class="fa fa-server absolute right-3 top-2.5 text-dark/50"></i>
              </div>
            </div>
            
            <!-- 目标端口 -->
            <div>
              <label class="block text-sm text-dark/70 mb-2">目标端口</label>
              <div class="relative">
                <input type="number" v-model="targetPort" min="1" max="65535"
                      class="w-full bg-white border border-primary/20 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary">
                <i class="fa fa-plug absolute right-3 top-2.5 text-dark/50"></i>
              </div>
            </div>
          </div>
          
          <!-- RTSP协议指令配置 -->
          <div v-if="protocolType === 'RTSP'" class="mt-4">
            <label class="block text-sm text-dark/70 mb-2">指令配置</label>
            <div class="relative">
              <textarea 
                v-model="rtspCommandConfig" 
                rows="3"
                class="w-full bg-white border border-primary/20 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                placeholder="请输入RTSP协议的指令配置..."
              ></textarea>
              <i class="fa fa-terminal absolute right-3 top-2.5 text-dark/50"></i>
            </div>
          </div>
          
          <div class="mt-4 flex justify-end">
            <button @click="startTest" :disabled="!canStartTest" 
                    :title="!canStartTest ? (
                      loading ? '数据加载中...' : 
                      error ? '数据加载失败' : 
                      fuzzData.length === 0 ? '无测试数据' : 
                      isRunning ? '测试进行中' : '未知错误'
                    ) : '开始测试'" 
                    class="bg-primary hover:bg-primary/90 text-white px-6 py-2 rounded-lg transition-all duration-300 flex items-center disabled:opacity-50 disabled:cursor-not-allowed">
              <i class="fa fa-play mr-2"></i> 开始测试
            </button>
            <button v-if="isRunning" @click="handleStopTest" 
                    class="bg-danger/10 hover:bg-danger/20 text-danger px-6 py-2 rounded-lg transition-all duration-300 flex items-center ml-3">
              <i class="fa fa-stop mr-2"></i> 停止测试
            </button>
          </div>
        </div>
        
        <!-- 测试过程展示区 -->
        <div class="grid grid-cols-1 xl:grid-cols-4 gap-6 mb-6">
          <!-- 实时Fuzz过程窗口 -->
          <div class="xl:col-span-3 bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-primary/20 shadow-card">
            <div class="flex justify-between items-center mb-4">
              <h3 class="font-semibold text-lg">Fuzz过程</h3>
              <div class="flex space-x-2">
                <button @click="() => { clearLog(); clearMQTTLogs(); }" class="text-xs bg-light-gray hover:bg-medium-gray px-2 py-1 rounded border border-dark/10 text-dark/70">
                  清空日志
                </button>
                <button v-if="isRunning" @click="togglePauseTest" class="text-xs bg-light-gray hover:bg-medium-gray px-2 py-1 rounded border border-dark/10 text-dark/70">
                  {{ isPaused ? '继续' : '暂停' }}
                </button>
                <button v-if="logEntries.length > 0" @click="saveLog" class="text-xs bg-primary/10 hover:bg-primary/20 text-primary px-2 py-1 rounded">
                  保存日志
                </button>
              </div>
            </div>
            <div ref="logContainer" class="bg-light-gray rounded-lg border border-dark/10 h-80 overflow-y-auto p-3 font-mono text-xs space-y-1 scrollbar-thin">
              <!-- MQTT差异报告显示 - 简化版本 -->
              <div v-if="protocolType === 'MQTT' && mqttDifferentialLogs.length > 0">
                <div 
                  v-for="(logLine, index) in mqttDifferentialLogs" 
                  :key="`mqtt-log-${index}`"
                  :class="{
                    'text-red-600': logLine.includes('ERROR'),
                    'text-yellow-600': logLine.includes('WARNING'), 
                    'text-green-600': logLine.includes('SUCCESS'),
                    'text-blue-600': logLine.includes('INFO')
                  }"
                  class="mb-1 break-words"
                  v-html="logLine"
                >
                </div>
              </div>
              
              <!-- 默认显示 -->
              <div class="text-dark/50 italic" v-if="!isRunning && logEntries.length === 0 && mqttDifferentialLogs.length === 0">
                测试未开始，请配置参数并点击"开始测试"
              </div>
            </div>
          </div>
          
          <!-- 崩溃监控 -->
          <div class="xl:col-span-1">
            <!-- 崩溃信息 -->
            <div v-if="crashDetails" class="bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-red-300 shadow-crash h-full">
              <div class="flex justify-between items-center mb-4">
                <h3 class="font-semibold text-lg text-danger">检测到程序崩溃</h3>
                <span class="bg-danger/10 text-danger text-xs px-2 py-0.5 rounded-full animate-pulse">紧急</span>
              </div>
              <div class="space-y-4 text-sm">
                <div>
                  <p class="text-xs text-dark/60 mb-1">崩溃时间</p>
                  <p class="font-mono">{{ crashDetails.time }}</p>
                </div>
                <div>
                  <p class="text-xs text-dark/60 mb-1">崩溃类型</p>
                  <p class="text-danger">{{ crashDetails.type }}</p>
                </div>
                <div>
                  <p class="text-xs text-dark/60 mb-1">触发数据包</p>
                  <p class="font-mono">#{{ crashDetails.id }}</p>
                </div>
                <div>
                  <p class="text-xs text-dark/60 mb-1">转储文件</p>
                  <p class="flex items-center">
                    <i class="fa fa-file-excel-o text-danger mr-2"></i>
                    <span class="truncate">{{ crashDetails.dumpFile }}</span>
                    <button class="ml-2 text-xs bg-danger/10 hover:bg-danger/20 text-danger px-1.5 py-0.5 rounded">
                      下载
                    </button>
                  </p>
                </div>
                <div>
                  <p class="text-xs text-dark/60 mb-1">崩溃日志路径</p>
                  <p class="font-mono text-xs truncate">{{ crashDetails.logPath }}</p>
                </div>
              </div>
            </div>
            
            <!-- 崩溃信息占位卡片 -->
            <div v-else class="bg-white/80 backdrop-blur-sm rounded-xl p-4 h-full" 
                 :class="protocolType === 'RTSP' && rtspStats.unique_crashes > 0 ? 'border border-red-300 shadow-crash' : 'border border-secondary/20 shadow-card'">
              <div class="flex justify-between items-center mb-4">
                <h3 class="font-semibold text-lg">崩溃监控</h3>
                <span v-if="protocolType === 'RTSP' && rtspStats.unique_crashes > 0" 
                      class="bg-danger/10 text-danger text-xs px-2 py-0.5 rounded-full animate-pulse">
                  {{ rtspStats.unique_crashes }} 个崩溃
                </span>
                <span v-else class="bg-success/10 text-success text-xs px-2 py-0.5 rounded-full">正常</span>
              </div>
              
              <!-- RTSP协议崩溃统计 -->
              <div v-if="protocolType === 'RTSP'" class="space-y-4">
                <div class="grid grid-cols-2 gap-4">
                  <div class="bg-red-50 rounded-lg p-3 border border-red-200 text-center">
                    <div class="text-2xl font-bold text-red-600 mb-1">{{ rtspStats.unique_crashes }}</div>
                    <div class="text-xs text-red-700">崩溃数</div>
                    <div class="text-xs text-gray-500 mt-1">Crashes</div>
                  </div>
                  <div class="bg-yellow-50 rounded-lg p-3 border border-yellow-200 text-center">
                    <div class="text-2xl font-bold text-yellow-600 mb-1">{{ rtspStats.unique_hangs }}</div>
                    <div class="text-xs text-yellow-700">挂起数</div>
                    <div class="text-xs text-gray-500 mt-1">Hangs</div>
                  </div>
                </div>
                
                <div class="bg-gray-50 rounded-lg p-3 border border-gray-200">
                  <div class="text-xs text-gray-600 mb-2">监控状态</div>
                  <div class="flex items-center space-x-2">
                    <div class="w-2 h-2 rounded-full animate-pulse" 
                         :class="rtspStats.unique_crashes > 0 ? 'bg-red-500' : 'bg-green-500'"></div>
                    <span class="text-sm" 
                          :class="rtspStats.unique_crashes > 0 ? 'text-red-700 font-medium' : 'text-gray-700'">
                      {{ rtspStats.unique_crashes > 0 ? '检测到异常' : '持续监控中...' }}
                    </span>
                  </div>
                </div>
              </div>
              
              <!-- 其他协议的默认显示 -->
              <div v-else class="h-full flex flex-col items-center justify-center text-dark/50 text-sm">
                <div class="bg-success/10 p-4 rounded-full mb-4">
                  <i class="fa fa-shield text-3xl text-success/70"></i>
                </div>
                <p>尚未检测到程序崩溃</p>
                <p class="mt-1">持续监控中...</p>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 测试结果分析 -->
        <div class="grid grid-cols-1 xl:grid-cols-4 gap-6 mb-6">
          <!-- 消息类型分布和版本统计 / RTSP状态机统计 -->
          <div class="xl:col-span-3 bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-secondary/20 shadow-card">
            <div class="flex justify-between items-center mb-6">
              <h3 class="font-semibold text-xl">
                {{ protocolType === 'RTSP' ? 'RTSP协议状态机统计' : 
                   protocolType === 'MQTT' ? 'MQTT协议消息分布与差异分析' : 
                   '消息类型分布与版本统计' }}
              </h3>
            </div>
            
            <!-- SNMP协议图表 -->
            <div v-if="protocolType === 'SNMP'" class="grid grid-cols-1 md:grid-cols-2 gap-8 h-72">
              <!-- 消息类型分布饼状图 -->
              <div>
                <h4 class="text-base font-medium mb-3 text-dark/80 text-center">消息类型分布</h4>
                <div class="h-60 relative">
                  <canvas ref="messageCanvas" id="messageTypeMainChart" class="absolute inset-0 transition-opacity duration-500" :class="{ 'opacity-0': !isTestCompleted }"></canvas>
                  <div v-if="!isTestCompleted" class="absolute inset-0 flex flex-col items-center justify-center text-dark/50 bg-white rounded-lg">
                    <div class="bg-primary/10 p-3 rounded-full mb-2">
                      <i class="fa fa-pie-chart text-2xl text-primary/70"></i>
                    </div>
                    <span class="text-xs">数据统计中...</span>
                  </div>
                </div>
              </div>
              <!-- SNMP版本分布饼状图 -->
              <div>
                <h4 class="text-base font-medium mb-3 text-dark/80 text-center">SNMP版本分布</h4>
                <div class="h-60 relative">
                  <canvas ref="versionCanvas" id="versionDistributionChart" class="absolute inset-0 transition-opacity duration-500" :class="{ 'opacity-0': !isTestCompleted }"></canvas>
                  <div v-if="!isTestCompleted" class="absolute inset-0 flex flex-col items-center justify-center text-dark/50 bg-white rounded-lg">
                    <div class="bg-primary/10 p-3 rounded-full mb-2">
                      <i class="fa fa-chart-pie text-2xl text-primary/70"></i>
                    </div>
                    <span class="text-xs">数据统计中...</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- MQTT协议统计 -->
            <div v-else-if="protocolType === 'MQTT'" class="grid grid-cols-1 md:grid-cols-2 gap-8 h-72">
              <!-- 客户端vs代理端消息分布 -->
              <div>
                <h4 class="text-base font-medium mb-3 text-dark/80 text-center">客户端 vs 代理端消息分布</h4>
                <div class="h-60 bg-white rounded-lg border border-gray-200 p-4">
                  <div class="grid grid-cols-2 gap-4 h-full">
                    <!-- 客户端统计 -->
                    <div class="bg-blue-50 rounded-lg p-4">
                      <h5 class="text-sm font-medium text-blue-700 mb-3 text-center">客户端消息</h5>
                      <div class="space-y-2 text-xs">
                        <div class="flex justify-between">
                          <span>CONNECT:</span>
                          <span class="font-bold text-blue-600">{{ mqttStats.client_messages.CONNECT }}</span>
                        </div>
                        <div class="flex justify-between">
                          <span>PUBLISH:</span>
                          <span class="font-bold text-blue-600">{{ mqttStats.client_messages.PUBLISH }}</span>
                        </div>
                        <div class="flex justify-between">
                          <span>SUBSCRIBE:</span>
                          <span class="font-bold text-blue-600">{{ mqttStats.client_messages.SUBSCRIBE }}</span>
                        </div>
                        <div class="flex justify-between">
                          <span>PINGREQ:</span>
                          <span class="font-bold text-blue-600">{{ mqttStats.client_messages.PINGREQ }}</span>
                        </div>
                        <div class="flex justify-between">
                          <span>其他:</span>
                          <span class="font-bold text-blue-600">{{ 
                            mqttStats.client_messages.CONNACK + mqttStats.client_messages.PUBACK + 
                            mqttStats.client_messages.PUBREC + mqttStats.client_messages.PUBREL + 
                            mqttStats.client_messages.PUBCOMP + mqttStats.client_messages.SUBACK + 
                            mqttStats.client_messages.UNSUBSCRIBE + mqttStats.client_messages.UNSUBACK + 
                            mqttStats.client_messages.PINGRESP + mqttStats.client_messages.DISCONNECT + 
                            mqttStats.client_messages.AUTH 
                          }}</span>
                        </div>
                      </div>
                    </div>
                    
                    <!-- 代理端统计 -->
                    <div class="bg-green-50 rounded-lg p-4">
                      <h5 class="text-sm font-medium text-green-700 mb-3 text-center">代理端消息</h5>
                      <div class="space-y-2 text-xs">
                        <div class="flex justify-between">
                          <span>CONNACK:</span>
                          <span class="font-bold text-green-600">{{ mqttStats.broker_messages.CONNACK }}</span>
                        </div>
                        <div class="flex justify-between">
                          <span>PUBLISH:</span>
                          <span class="font-bold text-green-600">{{ mqttStats.broker_messages.PUBLISH }}</span>
                        </div>
                        <div class="flex justify-between">
                          <span>SUBACK:</span>
                          <span class="font-bold text-green-600">{{ mqttStats.broker_messages.SUBACK }}</span>
                        </div>
                        <div class="flex justify-between">
                          <span>PINGRESP:</span>
                          <span class="font-bold text-green-600">{{ mqttStats.broker_messages.PINGRESP }}</span>
                        </div>
                        <div class="flex justify-between">
                          <span>其他:</span>
                          <span class="font-bold text-green-600">{{ 
                            mqttStats.broker_messages.CONNECT + mqttStats.broker_messages.PUBACK + 
                            mqttStats.broker_messages.PUBREC + mqttStats.broker_messages.PUBREL + 
                            mqttStats.broker_messages.PUBCOMP + mqttStats.broker_messages.SUBSCRIBE + 
                            mqttStats.broker_messages.UNSUBSCRIBE + mqttStats.broker_messages.UNSUBACK + 
                            mqttStats.broker_messages.PINGREQ + mqttStats.broker_messages.DISCONNECT + 
                            mqttStats.broker_messages.AUTH 
                          }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 协议差异分析 -->
              <div>
                <h4 class="text-base font-medium mb-3 text-dark/80 text-center">协议差异分析</h4>
                <div class="h-60 bg-white rounded-lg border border-gray-200 p-4">
                  <div class="space-y-4">
                    <!-- 差异总览 -->
                    <div class="bg-yellow-50 rounded-lg p-3">
                      <div class="flex justify-between items-center mb-2">
                        <span class="text-sm font-medium text-yellow-700">总差异数</span>
                        <span class="text-2xl font-bold text-yellow-600">{{ mqttStats.diff_number }}</span>
                      </div>
                      <div class="text-xs text-gray-600">发现的协议不一致性问题</div>
                    </div>
                    
                    <!-- 重复差异分布 -->
                    <div class="bg-purple-50 rounded-lg p-3">
                      <div class="flex justify-between items-center mb-2">
                        <span class="text-sm font-medium text-purple-700">重复差异</span>
                        <span class="text-2xl font-bold text-purple-600">{{ mqttStats.duplicate_diff_number }}</span>
                      </div>
                      <div class="grid grid-cols-2 gap-2 text-xs mt-2">
                        <div class="flex justify-between">
                          <span>CONNECT:</span>
                          <span class="font-medium">{{ mqttStats.duplicate_diffs.CONNECT }}</span>
                        </div>
                        <div class="flex justify-between">
                          <span>PUBLISH:</span>
                          <span class="font-medium">{{ mqttStats.duplicate_diffs.PUBLISH }}</span>
                        </div>
                        <div class="flex justify-between">
                          <span>PINGREQ:</span>
                          <span class="font-medium">{{ mqttStats.duplicate_diffs.PINGREQ }}</span>
                        </div>
                        <div class="flex justify-between">
                          <span>其他:</span>
                          <span class="font-medium">{{ 
                            mqttStats.duplicate_diffs.SUBSCRIBE + mqttStats.duplicate_diffs.UNSUBSCRIBE + 
                            mqttStats.duplicate_diffs.PUBREL + mqttStats.duplicate_diffs.PUBREC 
                          }}</span>
                        </div>
                      </div>
                    </div>
                    
                    <!-- 测试状态 -->
                    <div class="bg-gray-50 rounded-lg p-3">
                      <div class="text-xs text-gray-600 mb-2">测试状态</div>
                      <div class="flex items-center space-x-2">
                        <div class="w-2 h-2 rounded-full animate-pulse" 
                             :class="mqttStats.crash_number > 0 ? 'bg-red-500' : 'bg-green-500'"></div>
                        <span class="text-sm" 
                              :class="mqttStats.crash_number > 0 ? 'text-red-700 font-medium' : 'text-gray-700'">
                          {{ mqttStats.crash_number > 0 ? '检测到崩溃' : '运行正常' }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- RTSP协议统计 -->
            <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-8 h-72">
              <!-- 路径发现趋势 -->
              <div>
                <h4 class="text-base font-medium mb-3 text-dark/80 text-center">路径发现统计</h4>
                <div class="h-60 bg-white rounded-lg border border-gray-200 p-4">
                  <div class="grid grid-cols-2 gap-4 h-full">
                    <div class="flex flex-col justify-center items-center bg-blue-50 rounded-lg p-4">
                      <div class="text-3xl font-bold text-blue-600 mb-2">{{ rtspStats.paths_total }}</div>
                      <div class="text-sm text-gray-600 text-center">总路径数</div>
                      <div class="text-xs text-gray-500 mt-1">Total Paths</div>
                    </div>
                    <div class="flex flex-col justify-center items-center bg-green-50 rounded-lg p-4">
                      <div class="text-3xl font-bold text-green-600 mb-2">{{ rtspStats.cur_path }}</div>
                      <div class="text-sm text-gray-600 text-center">当前路径</div>
                      <div class="text-xs text-gray-500 mt-1">Current Path</div>
                    </div>
                    <div class="flex flex-col justify-center items-center bg-yellow-50 rounded-lg p-4">
                      <div class="text-3xl font-bold text-yellow-600 mb-2">{{ rtspStats.pending_total }}</div>
                      <div class="text-sm text-gray-600 text-center">待处理</div>
                      <div class="text-xs text-gray-500 mt-1">Pending</div>
                    </div>
                    <div class="flex flex-col justify-center items-center bg-purple-50 rounded-lg p-4">
                      <div class="text-3xl font-bold text-purple-600 mb-2">{{ rtspStats.pending_favs }}</div>
                      <div class="text-sm text-gray-600 text-center">优先路径</div>
                      <div class="text-xs text-gray-500 mt-1">Favored</div>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 状态机拓扑 -->
              <div>
                <h4 class="text-base font-medium mb-3 text-dark/80 text-center">协议状态机拓扑</h4>
                <div class="h-60 bg-white rounded-lg border border-gray-200 p-4">
                  <div class="flex flex-col h-full">
                    <!-- 状态机可视化区域 -->
                    <div class="flex-1 bg-gray-50 rounded-lg p-4 mb-4 flex items-center justify-center">
                      <div class="text-center">
                        <div class="flex items-center justify-center space-x-4 mb-4">
                          <div class="bg-blue-500 w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold">
                            {{ rtspStats.n_nodes }}
                          </div>
                          <div class="text-gray-400">
                            <i class="fa fa-arrow-right text-lg"></i>
                          </div>
                          <div class="bg-green-500 w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold">
                            {{ rtspStats.n_edges }}
                          </div>
                        </div>
                        <div class="text-xs text-gray-600">
                          <span class="text-blue-600 font-medium">{{ rtspStats.n_nodes }} 个状态节点</span>
                          <span class="mx-2">•</span>
                          <span class="text-green-600 font-medium">{{ rtspStats.n_edges }} 个状态转换</span>
                        </div>
                      </div>
                    </div>
                    
                    <!-- 状态机统计信息 -->
                    <div class="grid grid-cols-2 gap-2 text-xs">
                      <div class="bg-blue-50 rounded p-2 text-center">
                        <div class="font-bold text-blue-600">{{ rtspStats.max_depth }}</div>
                        <div class="text-gray-600">最大深度</div>
                      </div>
                      <div class="bg-green-50 rounded p-2 text-center">
                        <div class="font-bold text-green-600">{{ rtspStats.map_size }}</div>
                        <div class="text-gray-600">覆盖率</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 实时统计 -->
          <div class="xl:col-span-1 bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-primary/20 shadow-card">
            <h3 class="font-semibold text-lg mb-4">实时统计</h3>
            
            <!-- SNMP协议统计 -->
            <div v-if="protocolType !== 'RTSP'" class="space-y-6">
              <div>
                <div class="flex justify-between items-center mb-1">
                  <span class="text-sm text-dark/70">总发送包数</span>
                  <span class="text-xl font-bold">{{ packetCount }}</span>
                </div>
                <div class="w-full bg-light-gray rounded-full h-1.5 overflow-hidden">
                  <div class="h-full bg-primary" :style="{ width: progressWidth + '%' }"></div>
                </div>
              </div>
              
              <div class="grid grid-cols-1 gap-4">
                <!-- 第一行：正常响应和构造失败 -->
                <div class="grid grid-cols-2 gap-4">
                  <div class="bg-light-gray rounded-lg p-4 border border-success/20">
                    <p class="text-sm text-success/70 mb-2">正常响应</p>
                    <h4 class="text-3xl font-bold text-success">{{ successCount }}</h4>
                    <p class="text-sm text-dark/60 mt-2">{{ successRate }}%</p>
                  </div>
                  
                  <div class="bg-gray-50 rounded-lg p-4 border border-red-200">
                    <p class="text-sm text-danger/70 mb-2">构造失败</p>
                    <h4 class="text-3xl font-bold text-danger">{{ failedCount }}</h4>
                    <p class="text-sm text-dark/60 mt-2">{{ failedRate }}%</p>
                  </div>
                </div>
                
                <!-- 第二行：超时和速度 -->
                <div class="grid grid-cols-2 gap-4">
                  <div class="bg-light-gray rounded-lg p-4 border border-warning/20">
                    <p class="text-sm text-warning/70 mb-2">超时</p>
                    <h4 class="text-3xl font-bold text-warning">{{ timeoutCount }}</h4>
                    <p class="text-sm text-dark/60 mt-2">{{ timeoutRate }}%</p>
                  </div>
                  
                  <div class="bg-light-gray rounded-lg p-4 border border-info/20">
                    <p class="text-sm text-info/70 mb-2">发包速度</p>
                    <h4 class="text-3xl font-bold text-info">{{ currentSpeed }}</h4>
                    <p class="text-sm text-dark/60 mt-2">包/秒</p>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- MQTT协议统计 -->
            <div v-else-if="protocolType === 'MQTT'" class="space-y-4">
              <div>
                <div class="flex justify-between items-center mb-1">
                  <span class="text-sm text-dark/70">总请求数</span>
                  <span class="text-xl font-bold">{{ mqttStats.client_request_count + mqttStats.broker_request_count }}</span>
                </div>
                <div class="w-full bg-light-gray rounded-full h-1.5 overflow-hidden">
                  <div class="h-full bg-primary" :style="{ width: Math.min(100, (packetCount / Math.max(1, mqttStats.client_request_count + mqttStats.broker_request_count)) * 100) + '%' }"></div>
                </div>
                <div class="text-xs text-dark/60 mt-1">客户端: {{ mqttStats.client_request_count }} | 代理端: {{ mqttStats.broker_request_count }}</div>
              </div>
              
              <div class="grid grid-cols-1 gap-3">
                <!-- 第一行：有效连接和协议差异 -->
                <div class="grid grid-cols-2 gap-3">
                  <div class="bg-green-50 rounded-lg p-3 border border-green-200">
                    <p class="text-xs text-green-700 mb-1">有效连接</p>
                    <h4 class="text-2xl font-bold text-green-600">{{ mqttStats.valid_connect_number }}</h4>
                    <p class="text-xs text-dark/60 mt-1">Valid Connects</p>
                  </div>
                  
                  <div class="bg-yellow-50 rounded-lg p-3 border border-yellow-200">
                    <p class="text-xs text-yellow-700 mb-1">协议差异</p>
                    <h4 class="text-2xl font-bold text-yellow-600">{{ mqttStats.diff_number }}</h4>
                    <p class="text-xs text-dark/60 mt-1">Differences</p>
                  </div>
                </div>
                
                <!-- 第二行：崩溃数和重复差异 -->
                <div class="grid grid-cols-2 gap-3">
                  <div class="bg-red-50 rounded-lg p-3 border border-red-200">
                    <p class="text-xs text-red-700 mb-1">崩溃数量</p>
                    <h4 class="text-2xl font-bold text-red-600">{{ mqttStats.crash_number }}</h4>
                    <p class="text-xs text-dark/60 mt-1">Crashes</p>
                  </div>
                  
                  <div class="bg-purple-50 rounded-lg p-3 border border-purple-200">
                    <p class="text-xs text-purple-700 mb-1">重复差异</p>
                    <h4 class="text-2xl font-bold text-purple-600">{{ mqttStats.duplicate_diff_number }}</h4>
                    <p class="text-xs text-dark/60 mt-1">Duplicates</p>
                  </div>
                </div>
                
                <!-- 第三行：测试时长 -->
                <div class="bg-blue-50 rounded-lg p-3 border border-blue-200">
                  <div class="flex justify-between items-center mb-2">
                    <span class="text-xs text-blue-700">测试时长</span>
                    <span class="text-lg font-bold text-blue-600">{{ elapsedTime }}s</span>
                  </div>
                  <div class="text-xs text-dark/60">
                    {{ mqttStats.fuzzing_start_time ? `开始: ${mqttStats.fuzzing_start_time}` : '未开始' }}
                  </div>
                </div>
              </div>
            </div>
            
            <!-- RTSP协议统计 -->
            <div v-else class="space-y-4">
              <div>
                <div class="flex justify-between items-center mb-1">
                  <span class="text-sm text-dark/70">当前执行路径</span>
                  <span class="text-xl font-bold">#{{ rtspStats.cur_path }}</span>
                </div>
                <div class="w-full bg-light-gray rounded-full h-1.5 overflow-hidden">
                  <div class="h-full bg-primary" :style="{ width: rtspStats.paths_total > 0 ? Math.min(100, (rtspStats.cur_path / rtspStats.paths_total) * 100) : 0 + '%' }"></div>
                </div>
                <div class="text-xs text-dark/60 mt-1">{{ rtspStats.cur_path }} / {{ rtspStats.paths_total }} 路径</div>
              </div>
              
              <div class="grid grid-cols-1 gap-3">
                <!-- 第一行：执行速度和测试时长 -->
                <div class="grid grid-cols-2 gap-3">
                  <div class="bg-blue-50 rounded-lg p-3 border border-blue-200">
                    <p class="text-xs text-blue-700 mb-1">执行速度</p>
                    <h4 class="text-2xl font-bold text-blue-600">{{ rtspStats.execs_per_sec.toFixed(1) }}</h4>
                    <p class="text-xs text-dark/60 mt-1">exec/sec</p>
                  </div>
                  
                  <div class="bg-green-50 rounded-lg p-3 border border-green-200">
                    <p class="text-xs text-green-700 mb-1">运行时长</p>
                    <h4 class="text-2xl font-bold text-green-600">{{ elapsedTime }}</h4>
                    <p class="text-xs text-dark/60 mt-1">seconds</p>
                  </div>
                </div>
                
                <!-- 第二行：循环次数和最大深度 -->
                <div class="grid grid-cols-2 gap-3">
                  <div class="bg-purple-50 rounded-lg p-3 border border-purple-200">
                    <p class="text-xs text-purple-700 mb-1">完成循环</p>
                    <h4 class="text-2xl font-bold text-purple-600">{{ rtspStats.cycles_done }}</h4>
                    <p class="text-xs text-dark/60 mt-1">cycles</p>
                  </div>
                  
                  <div class="bg-indigo-50 rounded-lg p-3 border border-indigo-200">
                    <p class="text-xs text-indigo-700 mb-1">最大深度</p>
                    <h4 class="text-2xl font-bold text-indigo-600">{{ rtspStats.max_depth }}</h4>
                    <p class="text-xs text-dark/60 mt-1">depth</p>
                  </div>
                </div>
                
                <!-- 第三行：代码覆盖率 -->
                <div class="bg-orange-50 rounded-lg p-3 border border-orange-200">
                  <div class="flex justify-between items-center mb-2">
                    <span class="text-xs text-orange-700">代码覆盖率</span>
                    <span class="text-lg font-bold text-orange-600">{{ rtspStats.map_size }}</span>
                  </div>
                  <div class="text-xs text-dark/60">Coverage Bitmap</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 测试总结 -->
        <div v-if="!showCrashDetails && (isTestCompleted || (!isRunning && (packetCount > 0 || elapsedTime > 0)))" class="bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-secondary/20 shadow-card">
            <div class="flex justify-between items-center mb-4">
              <h3 class="font-semibold text-lg">测试总结</h3>
              <div class="flex space-x-2">
                <button v-if="crashDetails" @click="toggleCrashDetailsView" class="text-xs bg-danger/10 hover:bg-danger/20 text-danger px-2 py-1 rounded">
                  {{ showCrashDetails ? '返回总结' : '查看崩溃详情' }}
                </button>
                <button @click="saveLog" class="text-xs bg-primary/10 hover:bg-primary/20 text-primary px-2 py-1 rounded">
                  导出报告 <i class="fa fa-download ml-1"></i>
                </button>
              </div>
            </div>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div class="bg-light-gray rounded-lg p-3 border border-dark/10">
              <h4 class="font-medium mb-2 text-dark/80">测试信息</h4>
              <div class="space-y-1">
                <p><span class="text-dark/60">协议名称:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? protocolType.toUpperCase() : '未测试' }}</span></p>
                <p><span class="text-dark/60">Fuzz引擎:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? fuzzEngine : '未设置' }}</span></p>
                <p><span class="text-dark/60">测试目标:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? `${targetHost}:${targetPort}` : '未设置' }}</span></p>
                <p><span class="text-dark/60">开始时间:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? (startTime || (testStartTime ? testStartTime.toLocaleString() : '未开始')) : '未开始' }}</span></p>
                <p><span class="text-dark/60">结束时间:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? (endTime || (testEndTime ? testEndTime.toLocaleString() : '未结束')) : '未结束' }}</span></p>
                <p><span class="text-dark/60">总耗时:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? elapsedTime : 0 }}秒</span></p>
              </div>
            </div>
            
            <div class="bg-light-gray rounded-lg p-3 border border-dark/10">
              <h4 class="font-medium mb-2 text-dark/80">性能统计</h4>
              <div class="space-y-1">
                <!-- SNMP协议统计 -->
                <template v-if="protocolType !== 'RTSP'">
                  <p><span class="text-dark/60">SNMP_v1发包数:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? protocolStats.v1 : 0 }}</span></p>
                  <p><span class="text-dark/60">SNMP_v2发包数:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? protocolStats.v2c : 0 }}</span></p>
                  <p><span class="text-dark/60">SNMP_v3发包数:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? protocolStats.v3 : 0 }}</span></p>
                  <p><span class="text-dark/60">总发包数:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? fileTotalPackets : 0 }}</span></p>
                  <p><span class="text-dark/60">正常响应率:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? Math.round((fileSuccessCount / Math.max(fileTotalPackets, 1)) * 100) : 0 }}%</span></p>
                  <p><span class="text-dark/60">超时率:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? Math.round((fileTimeoutCount / Math.max(fileTotalPackets, 1)) * 100) : 0 }}%</span></p>
                </template>
                <!-- MQTT协议统计 -->
                <template v-else-if="protocolType === 'MQTT'">
                  <p><span class="text-dark/60">客户端请求数:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? mqttStats.client_request_count : 0 }}</span></p>
                  <p><span class="text-dark/60">代理端请求数:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? mqttStats.broker_request_count : 0 }}</span></p>
                  <p><span class="text-dark/60">有效连接数:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? mqttStats.valid_connect_number : 0 }}</span></p>
                  <p><span class="text-dark/60">协议差异数:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? mqttStats.diff_number : 0 }}</span></p>
                  <p><span class="text-dark/60">重复差异数:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? mqttStats.duplicate_diff_number : 0 }}</span></p>
                  <p><span class="text-dark/60">崩溃数量:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? mqttStats.crash_number : 0 }}</span></p>
                </template>
                <!-- RTSP协议统计 -->
                <template v-else>
                  <p><span class="text-dark/60">执行速度:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? rtspStats.execs_per_sec.toFixed(2) : 0 }} exec/sec</span></p>
                  <p><span class="text-dark/60">代码覆盖率:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? rtspStats.map_size : '0%' }}</span></p>
                  <p><span class="text-dark/60">发现路径数:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? rtspStats.paths_total : 0 }}</span></p>
                  <p><span class="text-dark/60">状态节点数:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? rtspStats.n_nodes : 0 }}</span></p>
                  <p><span class="text-dark/60">状态转换数:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? rtspStats.n_edges : 0 }}</span></p>
                  <p><span class="text-dark/60">最大深度:</span> <span>{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? rtspStats.max_depth : 0 }}</span></p>
                </template>
              </div>
            </div>
            
            <div class="bg-light-gray rounded-lg p-3 border border-dark/10">
              <h4 class="font-medium mb-2 text-dark/80">文件信息</h4>
              <div class="space-y-2">
                <div class="flex items-center">
                  <i class="fa fa-file-text-o text-primary mr-2"></i>
                  <div class="flex-1">
                    <p class="truncate text-xs">运行日志信息</p>
                    <p class="truncate text-xs text-dark/50">{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? 'scan_result/fuzz_logs/fuzz_output.txt' : '无' }}</p>
                  </div>
                  <button @click="saveLog" class="text-xs bg-primary/10 hover:bg-primary/20 text-primary px-1.5 py-0.5 rounded">
                    下载
                  </button>
                </div>
                <div class="flex items-center">
                  <i class="fa fa-file-excel-o text-success mr-2"></i>
                  <div class="flex-1">
                    <p class="truncate text-xs">Fuzz报告信息</p>
                    <p class="truncate text-xs text-dark/50">{{ (isTestCompleted || (!isRunning && packetCount > 0)) ? `fuzz_report_${new Date().getTime()}.txt` : '无' }}</p>
                  </div>
                  <button @click="saveLog" class="text-xs bg-primary/10 hover:bg-primary/20 text-primary px-1.5 py-0.5 rounded">
                    下载
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 崩溃详情区域 -->
        <div v-if="showCrashDetails && crashDetails" class="bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-red-300 shadow-crash mb-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="font-semibold text-lg text-danger">崩溃详情 #{{ crashDetails.id }}</h3>
            <div class="flex space-x-2">
              <button @click="toggleCrashDetailsView" class="text-xs bg-light-gray hover:bg-medium-gray px-2 py-1 rounded border border-dark/10 text-dark/70">
                查看完整日志
              </button>
              <button class="text-xs bg-danger/10 hover:bg-danger/20 text-danger px-2 py-1 rounded">
                分析崩溃原因
              </button>
            </div>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 class="text-sm font-medium mb-2 text-dark/80">崩溃信息</h4>
              <div class="bg-light-gray rounded-lg p-3 border border-dark/10 text-sm font-mono h-40 overflow-y-auto scrollbar-thin">
                <pre>{{ crashDetails.details }}</pre>
              </div>
            </div>
            <div>
              <h4 class="text-sm font-medium mb-2 text-dark/80">触发数据包内容</h4>
              <div class="bg-light-gray rounded-lg p-3 border border-dark/10 text-xs font-mono h-40 overflow-y-auto scrollbar-thin">
                <pre>{{ crashDetails.packetContent }}</pre>
              </div>
            </div>
          </div>
        </div>
        </div>

        <!-- 历史记录视图 -->
        <div v-else>
          <!-- 返回按钮 -->
          <div class="bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-orange-200 shadow-card mb-6">
            <button @click="backToMainView" class="flex items-center space-x-2 text-orange-600 hover:text-orange-700 transition-colors">
              <i class="fa fa-arrow-left"></i>
              <span>返回测试界面</span>
            </button>
          </div>

          <!-- 历史记录列表 -->
          <div v-if="!selectedHistoryItem" class="space-y-6">
            <div class="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-orange-200 shadow-card">
              <div class="flex items-center justify-between mb-6">
                <div class="flex items-center space-x-3">
                  <div class="bg-orange-100 p-3 rounded-lg">
                    <i class="fa fa-history text-orange-600 text-xl"></i>
                  </div>
                  <div>
                    <h2 class="text-xl font-bold text-dark">历史测试记录</h2>
                    <p class="text-sm text-gray-500">共 {{ historyResults.length }} 条记录</p>
                  </div>
                </div>
                
                <div class="flex items-center space-x-3">
                  <button v-if="historyResults.length > 0" @click="exportAllHistory" 
                          class="bg-blue-50 hover:bg-blue-100 text-blue-600 px-4 py-2 rounded-lg transition-colors flex items-center space-x-2"
                          title="导出所有历史记录">
                    <i class="fa fa-download"></i>
                    <span class="text-sm">导出全部</span>
                  </button>
                  <button v-if="historyResults.length > 0" @click="clearAllHistory" 
                          class="bg-red-50 hover:bg-red-100 text-red-600 px-4 py-2 rounded-lg transition-colors flex items-center space-x-2"
                          title="清空所有历史记录">
                    <i class="fa fa-trash"></i>
                    <span class="text-sm">清空全部</span>
                  </button>
                </div>
              </div>

              <div v-if="historyResults.length === 0" class="text-center py-12">
                <div class="bg-gray-100 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                  <i class="fa fa-inbox text-2xl text-gray-400"></i>
                </div>
                <p class="text-gray-500">暂无历史测试结果</p>
                <p class="text-sm text-gray-400 mt-2">完成测试后，结果将自动保存到这里</p>
              </div>
              
              <div v-else class="space-y-4">
                <div v-for="item in historyResults" :key="item.id" 
                     class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-all duration-300 cursor-pointer"
                     @click="viewHistoryDetail(item)">
                  <div class="flex items-center justify-between">
                    <div class="flex-1">
                      <div class="flex items-center space-x-4 mb-3">
                        <h3 class="font-semibold text-lg text-dark">{{ item.timestamp }}</h3>
                        <span class="bg-primary/10 text-primary px-3 py-1 rounded-full text-sm font-medium">
                          {{ item.protocol }}
                        </span>
                        <span class="bg-secondary/10 text-secondary px-3 py-1 rounded-full text-sm font-medium">
                          {{ item.fuzzEngine }}
                        </span>
                        <span v-if="item.hasCrash" class="bg-red-100 text-red-600 px-3 py-1 rounded-full text-sm font-medium animate-pulse">
                          <i class="fa fa-exclamation-triangle mr-1"></i>检测到崩溃
                        </span>
                      </div>
                      
                      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div class="flex items-center space-x-2">
                          <i class="fa fa-server text-gray-400"></i>
                          <span class="text-gray-600">目标:</span>
                          <span class="font-mono">{{ item.targetHost }}:{{ item.targetPort }}</span>
                        </div>
                        <div class="flex items-center space-x-2">
                          <i class="fa fa-clock-o text-gray-400"></i>
                          <span class="text-gray-600">耗时:</span>
                          <span>{{ item.duration }}秒</span>
                        </div>
                        <div class="flex items-center space-x-2">
                          <i class="fa fa-send text-gray-400"></i>
                          <span class="text-gray-600">总包数:</span>
                          <span class="font-medium">{{ item.totalPackets }}</span>
                        </div>
                        <div class="flex items-center space-x-2">
                          <i class="fa fa-check-circle text-gray-400"></i>
                          <span class="text-gray-600">成功率:</span>
                          <span class="font-medium" :class="item.successRate >= 80 ? 'text-green-600' : item.successRate >= 60 ? 'text-yellow-600' : 'text-red-600'">
                            {{ item.successRate }}%
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <div class="flex items-center space-x-3 ml-6">
                      <button @click.stop="exportHistoryItem(item)" 
                              class="bg-blue-50 hover:bg-blue-100 text-blue-600 px-3 py-2 rounded-lg transition-colors flex items-center space-x-1"
                              title="导出报告">
                        <i class="fa fa-download"></i>
                        <span class="text-xs">导出</span>
                      </button>
                      <button @click.stop="deleteHistoryItem(item.id)" 
                              class="bg-red-50 hover:bg-red-100 text-red-600 px-3 py-2 rounded-lg transition-colors flex items-center space-x-1"
                              title="删除记录">
                        <i class="fa fa-trash"></i>
                        <span class="text-xs">删除</span>
                      </button>
                      <i class="fa fa-chevron-right text-gray-400 text-lg"></i>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 历史记录详情 -->
          <div v-else class="space-y-6">
            <!-- 返回按钮 -->
            <div class="bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-orange-200 shadow-card">
              <div class="flex items-center justify-between">
                <button @click="backToHistoryList" class="flex items-center space-x-2 text-orange-600 hover:text-orange-700 transition-colors">
                  <i class="fa fa-arrow-left"></i>
                  <span>返回历史记录列表</span>
                </button>
                <button @click="backToMainView" class="flex items-center space-x-2 text-gray-600 hover:text-gray-700 transition-colors">
                  <i class="fa fa-home"></i>
                  <span>返回测试界面</span>
                </button>
              </div>
            </div>

            <!-- 详情头部信息 -->
            <div class="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-orange-200 shadow-card">
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center space-x-4">
                  <div class="bg-orange-100 p-3 rounded-lg">
                    <i class="fa fa-chart-bar text-orange-600 text-xl"></i>
                  </div>
                  <div>
                    <h2 class="text-xl font-bold text-dark">测试详情</h2>
                    <p class="text-sm text-gray-500">{{ selectedHistoryItem.timestamp }}</p>
                  </div>
                  <span class="bg-primary/10 text-primary px-3 py-1 rounded-full text-sm font-medium">
                    {{ selectedHistoryItem.protocol }}
                  </span>
                  <span class="bg-secondary/10 text-secondary px-3 py-1 rounded-full text-sm font-medium">
                    {{ selectedHistoryItem.fuzzEngine }}
                  </span>
                  <span v-if="selectedHistoryItem.hasCrash" class="bg-red-100 text-red-600 px-3 py-1 rounded-full text-sm font-medium animate-pulse">
                    <i class="fa fa-exclamation-triangle mr-1"></i>检测到崩溃
                  </span>
                </div>
                <button @click="exportHistoryItem(selectedHistoryItem)" 
                        class="bg-primary hover:bg-primary/90 text-white px-4 py-2 rounded-lg transition-colors flex items-center space-x-2">
                  <i class="fa fa-download"></i>
                  <span>导出报告</span>
                </button>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div class="bg-gray-50 rounded-lg p-3">
                  <h4 class="font-medium mb-2 text-gray-800">基本信息</h4>
                  <div class="space-y-1">
                    <p><span class="text-gray-600">测试ID:</span> <span class="font-mono">{{ selectedHistoryItem.id }}</span></p>
                    <p><span class="text-gray-600">目标:</span> <span class="font-mono">{{ selectedHistoryItem.targetHost }}:{{ selectedHistoryItem.targetPort }}</span></p>
                    <p><span class="text-gray-600">测试时长:</span> <span>{{ selectedHistoryItem.duration }}秒</span></p>
                  </div>
                </div>
                
                <div class="bg-gray-50 rounded-lg p-3">
                  <h4 class="font-medium mb-2 text-gray-800">性能统计</h4>
                  <div class="space-y-1">
                    <p><span class="text-gray-600">总发包数:</span> <span class="font-medium">{{ selectedHistoryItem.totalPackets }}</span></p>
                    <p><span class="text-gray-600">成功率:</span> <span class="font-medium" :class="selectedHistoryItem.successRate >= 80 ? 'text-green-600' : selectedHistoryItem.successRate >= 60 ? 'text-yellow-600' : 'text-red-600'">{{ selectedHistoryItem.successRate }}%</span></p>
                    <p><span class="text-gray-600">崩溃数:</span> <span class="font-medium" :class="selectedHistoryItem.crashCount > 0 ? 'text-red-600' : 'text-green-600'">{{ selectedHistoryItem.crashCount }}</span></p>
                  </div>
                </div>

                <div class="bg-gray-50 rounded-lg p-3">
                  <h4 class="font-medium mb-2 text-gray-800">
                    {{ selectedHistoryItem.protocol === 'RTSP' ? 'AFLNET统计' : '协议版本' }}
                  </h4>
                  <div class="space-y-1">
                    <!-- SNMP协议版本统计 -->
                    <template v-if="selectedHistoryItem.protocol !== 'RTSP'">
                      <p><span class="text-gray-600">SNMP v1:</span> <span>{{ selectedHistoryItem.protocolStats.v1 }}</span></p>
                      <p><span class="text-gray-600">SNMP v2c:</span> <span>{{ selectedHistoryItem.protocolStats.v2c }}</span></p>
                      <p><span class="text-gray-600">SNMP v3:</span> <span>{{ selectedHistoryItem.protocolStats.v3 }}</span></p>
                    </template>
                    <!-- RTSP协议AFLNET统计 -->
                    <template v-else-if="selectedHistoryItem.rtspStats">
                      <p><span class="text-gray-600">执行速度:</span> <span>{{ selectedHistoryItem.rtspStats.execs_per_sec.toFixed(2) }} exec/sec</span></p>
                      <p><span class="text-gray-600">代码覆盖率:</span> <span>{{ selectedHistoryItem.rtspStats.map_size }}</span></p>
                      <p><span class="text-gray-600">状态节点:</span> <span>{{ selectedHistoryItem.rtspStats.n_nodes }}</span></p>
                    </template>
                  </div>
                </div>
              </div>
            </div>

            <!-- 测试结果分析（复用现有的图表区域样式） -->
            <div class="grid grid-cols-1 xl:grid-cols-4 gap-6">
              <!-- 实时统计 -->
              <div class="xl:col-span-1 bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-orange-200 shadow-card">
                <h3 class="font-semibold text-lg mb-4">测试结果统计</h3>
                <div class="space-y-6">
                  <div>
                    <div class="flex justify-between items-center mb-1">
                      <span class="text-sm text-gray-700">总发送包数</span>
                      <span class="text-xl font-bold">{{ selectedHistoryItem.totalPackets }}</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                      <div class="h-full bg-orange-500" style="width: 100%"></div>
                    </div>
                  </div>
                  
                  <div class="grid grid-cols-1 gap-4">
                    <div class="grid grid-cols-2 gap-4">
                      <div class="bg-green-50 rounded-lg p-4 border border-green-200">
                        <p class="text-sm text-green-700 mb-2">正常响应</p>
                        <h4 class="text-3xl font-bold text-green-600">{{ selectedHistoryItem.successCount }}</h4>
                        <p class="text-sm text-gray-600 mt-2">{{ selectedHistoryItem.successRate }}%</p>
                      </div>
                      
                      <div class="bg-red-50 rounded-lg p-4 border border-red-200">
                        <p class="text-sm text-red-700 mb-2">失败</p>
                        <h4 class="text-3xl font-bold text-red-600">{{ selectedHistoryItem.failedCount }}</h4>
                        <p class="text-sm text-gray-600 mt-2">{{ Math.round((selectedHistoryItem.failedCount / selectedHistoryItem.totalPackets) * 100) }}%</p>
                      </div>
                    </div>
                    
                    <div class="grid grid-cols-2 gap-4">
                      <div class="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
                        <p class="text-sm text-yellow-700 mb-2">超时</p>
                        <h4 class="text-3xl font-bold text-yellow-600">{{ selectedHistoryItem.timeoutCount }}</h4>
                        <p class="text-sm text-gray-600 mt-2">{{ Math.round((selectedHistoryItem.timeoutCount / selectedHistoryItem.totalPackets) * 100) }}%</p>
                      </div>
                      
                      <div class="bg-red-50 rounded-lg p-4 border border-red-200">
                        <p class="text-sm text-red-700 mb-2">崩溃</p>
                        <h4 class="text-3xl font-bold text-red-600">{{ selectedHistoryItem.crashCount }}</h4>
                        <p class="text-sm text-gray-600 mt-2">{{ Math.round((selectedHistoryItem.crashCount / selectedHistoryItem.totalPackets) * 100) }}%</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 消息类型分布和版本统计 / RTSP状态机统计 -->
              <div class="xl:col-span-3 bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-orange-200 shadow-card">
                <h3 class="font-semibold text-xl mb-6">
                  {{ selectedHistoryItem.protocol === 'RTSP' ? 'RTSP协议状态机统计' : '消息类型分布与版本统计' }}
                </h3>
                
                <!-- SNMP协议图表 -->
                <div v-if="selectedHistoryItem.protocol !== 'RTSP'" class="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <!-- 消息类型分布 -->
                  <div>
                    <h4 class="text-base font-medium mb-4 text-gray-800 text-center">消息类型分布</h4>
                    <div class="grid grid-cols-2 gap-4">
                      <div class="text-center bg-blue-50 rounded-lg p-4">
                        <div class="text-2xl font-bold text-blue-600">{{ selectedHistoryItem.messageTypeStats.get }}</div>
                        <div class="text-sm text-gray-600">GET</div>
                        <div class="text-xs text-gray-500">{{ Math.round((selectedHistoryItem.messageTypeStats.get / selectedHistoryItem.totalPackets) * 100) }}%</div>
                      </div>
                      <div class="text-center bg-indigo-50 rounded-lg p-4">
                        <div class="text-2xl font-bold text-indigo-600">{{ selectedHistoryItem.messageTypeStats.set }}</div>
                        <div class="text-sm text-gray-600">SET</div>
                        <div class="text-xs text-gray-500">{{ Math.round((selectedHistoryItem.messageTypeStats.set / selectedHistoryItem.totalPackets) * 100) }}%</div>
                      </div>
                      <div class="text-center bg-pink-50 rounded-lg p-4">
                        <div class="text-2xl font-bold text-pink-600">{{ selectedHistoryItem.messageTypeStats.getnext }}</div>
                        <div class="text-sm text-gray-600">GETNEXT</div>
                        <div class="text-xs text-gray-500">{{ Math.round((selectedHistoryItem.messageTypeStats.getnext / selectedHistoryItem.totalPackets) * 100) }}%</div>
                      </div>
                      <div class="text-center bg-green-50 rounded-lg p-4">
                        <div class="text-2xl font-bold text-green-600">{{ selectedHistoryItem.messageTypeStats.getbulk }}</div>
                        <div class="text-sm text-gray-600">GETBULK</div>
                        <div class="text-xs text-gray-500">{{ Math.round((selectedHistoryItem.messageTypeStats.getbulk / selectedHistoryItem.totalPackets) * 100) }}%</div>
                      </div>
                    </div>
                  </div>

                  <!-- SNMP版本分布 -->
                  <div>
                    <h4 class="text-base font-medium mb-4 text-gray-800 text-center">SNMP版本分布</h4>
                    <div class="space-y-4">
                      <div class="bg-yellow-50 rounded-lg p-4">
                        <div class="flex justify-between items-center mb-2">
                          <span class="text-gray-700 font-medium">SNMP v1</span>
                          <span class="text-lg font-bold text-yellow-600">{{ selectedHistoryItem.protocolStats.v1 }}</span>
                        </div>
                        <div class="w-full bg-gray-200 rounded-full h-2">
                          <div class="bg-yellow-500 h-2 rounded-full" :style="{ width: (selectedHistoryItem.protocolStats.v1 / selectedHistoryItem.totalPackets * 100) + '%' }"></div>
                        </div>
                        <div class="text-xs text-gray-500 mt-1">{{ Math.round((selectedHistoryItem.protocolStats.v1 / selectedHistoryItem.totalPackets) * 100) }}%</div>
                      </div>
                      
                      <div class="bg-purple-50 rounded-lg p-4">
                        <div class="flex justify-between items-center mb-2">
                          <span class="text-gray-700 font-medium">SNMP v2c</span>
                          <span class="text-lg font-bold text-purple-600">{{ selectedHistoryItem.protocolStats.v2c }}</span>
                        </div>
                        <div class="w-full bg-gray-200 rounded-full h-2">
                          <div class="bg-purple-500 h-2 rounded-full" :style="{ width: (selectedHistoryItem.protocolStats.v2c / selectedHistoryItem.totalPackets * 100) + '%' }"></div>
                        </div>
                        <div class="text-xs text-gray-500 mt-1">{{ Math.round((selectedHistoryItem.protocolStats.v2c / selectedHistoryItem.totalPackets) * 100) }}%</div>
                      </div>
                      
                      <div class="bg-red-50 rounded-lg p-4">
                        <div class="flex justify-between items-center mb-2">
                          <span class="text-gray-700 font-medium">SNMP v3</span>
                          <span class="text-lg font-bold text-red-600">{{ selectedHistoryItem.protocolStats.v3 }}</span>
                        </div>
                        <div class="w-full bg-gray-200 rounded-full h-2">
                          <div class="bg-red-500 h-2 rounded-full" :style="{ width: (selectedHistoryItem.protocolStats.v3 / selectedHistoryItem.totalPackets * 100) + '%' }"></div>
                        </div>
                        <div class="text-xs text-gray-500 mt-1">{{ Math.round((selectedHistoryItem.protocolStats.v3 / selectedHistoryItem.totalPackets) * 100) }}%</div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- RTSP协议统计 -->
                <div v-else-if="selectedHistoryItem.rtspStats" class="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <!-- 路径发现统计 -->
                  <div>
                    <h4 class="text-base font-medium mb-4 text-gray-800 text-center">路径发现统计</h4>
                    <div class="grid grid-cols-2 gap-4">
                      <div class="text-center bg-blue-50 rounded-lg p-4">
                        <div class="text-2xl font-bold text-blue-600">{{ selectedHistoryItem.rtspStats.paths_total }}</div>
                        <div class="text-sm text-gray-600">总路径数</div>
                        <div class="text-xs text-gray-500">Total Paths</div>
                      </div>
                      <div class="text-center bg-green-50 rounded-lg p-4">
                        <div class="text-2xl font-bold text-green-600">{{ selectedHistoryItem.rtspStats.cur_path }}</div>
                        <div class="text-sm text-gray-600">当前路径</div>
                        <div class="text-xs text-gray-500">Current Path</div>
                      </div>
                      <div class="text-center bg-yellow-50 rounded-lg p-4">
                        <div class="text-2xl font-bold text-yellow-600">{{ selectedHistoryItem.rtspStats.pending_total }}</div>
                        <div class="text-sm text-gray-600">待处理</div>
                        <div class="text-xs text-gray-500">Pending</div>
                      </div>
                      <div class="text-center bg-purple-50 rounded-lg p-4">
                        <div class="text-2xl font-bold text-purple-600">{{ selectedHistoryItem.rtspStats.pending_favs }}</div>
                        <div class="text-sm text-gray-600">优先路径</div>
                        <div class="text-xs text-gray-500">Favored</div>
                      </div>
                    </div>
                  </div>

                  <!-- 状态机与性能统计 -->
                  <div>
                    <h4 class="text-base font-medium mb-4 text-gray-800 text-center">状态机与性能统计</h4>
                    <div class="space-y-4">
                      <div class="bg-blue-50 rounded-lg p-4">
                        <div class="flex justify-between items-center mb-2">
                          <span class="text-gray-700 font-medium">状态节点数</span>
                          <span class="text-lg font-bold text-blue-600">{{ selectedHistoryItem.rtspStats.n_nodes }}</span>
                        </div>
                        <div class="text-xs text-gray-500">State Nodes</div>
                      </div>
                      
                      <div class="bg-green-50 rounded-lg p-4">
                        <div class="flex justify-between items-center mb-2">
                          <span class="text-gray-700 font-medium">状态转换数</span>
                          <span class="text-lg font-bold text-green-600">{{ selectedHistoryItem.rtspStats.n_edges }}</span>
                        </div>
                        <div class="text-xs text-gray-500">State Transitions</div>
                      </div>
                      
                      <div class="bg-purple-50 rounded-lg p-4">
                        <div class="flex justify-between items-center mb-2">
                          <span class="text-gray-700 font-medium">执行速度</span>
                          <span class="text-lg font-bold text-purple-600">{{ selectedHistoryItem.rtspStats.execs_per_sec.toFixed(1) }}</span>
                        </div>
                        <div class="text-xs text-gray-500">Executions per Second</div>
                      </div>
                      
                      <div class="bg-orange-50 rounded-lg p-4">
                        <div class="flex justify-between items-center mb-2">
                          <span class="text-gray-700 font-medium">代码覆盖率</span>
                          <span class="text-lg font-bold text-orange-600">{{ selectedHistoryItem.rtspStats.map_size }}</span>
                        </div>
                        <div class="text-xs text-gray-500">Code Coverage</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 崩溃信息（如果有） -->
            <div v-if="selectedHistoryItem.hasCrash && selectedHistoryItem.crashDetails" class="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-red-300 shadow-card">
              <div class="flex items-center space-x-3 mb-6">
                <div class="bg-red-100 p-3 rounded-lg">
                  <i class="fa fa-exclamation-triangle text-red-600 text-xl"></i>
                </div>
                <div>
                  <h3 class="font-semibold text-lg text-red-600">崩溃详细信息</h3>
                  <p class="text-sm text-gray-500">检测到程序崩溃，以下是详细信息</p>
                </div>
              </div>

              <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                  <h4 class="font-medium text-sm text-gray-700 mb-3">崩溃信息</h4>
                  <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <div class="space-y-2 text-sm">
                      <div><span class="text-gray-600">崩溃时间:</span> <span class="font-mono">{{ selectedHistoryItem.crashDetails.time }}</span></div>
                      <div><span class="text-gray-600">崩溃类型:</span> <span class="text-red-600 font-medium">{{ selectedHistoryItem.crashDetails.type }}</span></div>
                      <div><span class="text-gray-600">触发包ID:</span> <span class="font-mono">#{{ selectedHistoryItem.crashDetails.id }}</span></div>
                      <div><span class="text-gray-600">日志路径:</span> <span class="font-mono text-xs break-all">{{ selectedHistoryItem.crashDetails.logPath }}</span></div>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h4 class="font-medium text-sm text-gray-700 mb-3">触发数据包内容</h4>
                  <div class="bg-gray-50 rounded-lg p-4 border border-gray-200 font-mono text-xs break-all">
                    {{ selectedHistoryItem.crashDetails.packetContent }}
                  </div>
                </div>
              </div>

              <div class="mt-6">
                <h4 class="font-medium text-sm text-gray-700 mb-3">详细崩溃日志</h4>
                <div class="bg-gray-50 rounded-lg p-4 border border-gray-200 font-mono text-xs overflow-x-auto">
                  <pre>{{ selectedHistoryItem.crashDetails.details }}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

      <!-- 页脚 -->
      <footer class="bg-white/80 backdrop-blur-md border-t border-primary/20 py-4 mt-6 shadow-sm">
        <div class="w-full px-6 flex flex-col md:flex-row justify-between items-center">
        <div class="text-dark/50 text-sm mb-2 md:mb-0">
          © 2025 多协议Fuzz测试平台 | 最后更新: <span>{{ lastUpdate }}</span>
        </div>
        <div class="flex space-x-4 text-sm text-dark/50">
          <a href="#" class="hover:text-primary transition-colors">帮助文档</a>
          <a href="#" class="hover:text-primary transition-colors">关于我们</a>
          <a href="#" class="hover:text-primary transition-colors">联系支持</a>
        </div>
      </div>
    </footer>

    <!-- 通知组件 -->
    <div v-if="showNotification" class="fixed top-4 right-4 z-50 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg flex items-center space-x-3 animate-slide-in">
      <i class="fa fa-check-circle"></i>
      <span>{{ notificationMessage }}</span>
      <button @click="closeNotification" class="ml-2 text-white hover:text-green-200 transition-colors">
        <i class="fa fa-times"></i>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* 动画效果 */
.packet-highlight {
  animation: highlight 0.5s ease-in-out;
}
.crash-highlight {
  animation: crashHighlight 1.5s ease-in-out infinite;
}
@keyframes highlight { 
  0% { background-color: rgba(59,130,246,0.1); } 
  100% { background-color: transparent; } 
}
@keyframes crashHighlight { 
  0%, 100% { background-color: rgba(239,68,68,0.1);} 
  50% { background-color: rgba(239,68,68,0.2);} 
}
@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
.animate-slide-in {
  animation: slideIn 0.3s ease-out;
}

/* 背景网格效果 */
.bg-grid {
  background-image: 
    linear-gradient(rgba(59, 130, 246, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59, 130, 246, 0.05) 1px, transparent 1px);
  background-size: 20px 20px;
}

/* 滚动条样式 */
.scrollbar-thin {
  scrollbar-width: thin;
}
.scrollbar-thin::-webkit-scrollbar {
  width: 6px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* 阴影效果 */
.shadow-card {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}
.shadow-crash {
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.3);
}

/* 文字阴影 */
.text-shadow {
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* 自定义颜色 */
:root {
  --primary: #3B82F6;
  --secondary: #6366F1;
  --accent: #EC4899;
  --light: #FFFFFF;
  --light-gray: #F3F4F6;
  --medium-gray: #E5E7EB;
  --dark: #1F2937;
  --success: #10B981;
  --warning: #F59E0B;
  --danger: #EF4444;
  --info: #3B82F6;
}

/* 响应式设计增强 */
@media (max-width: 768px) {
  .grid-cols-2 {
    grid-template-columns: 1fr;
  }
  .grid-cols-3 {
    grid-template-columns: 1fr;
  }
  .grid-cols-4 {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .grid-cols-4 {
    grid-template-columns: 1fr;
  }
}

/* 按钮状态增强 */
.btn-primary {
  @apply bg-primary hover:bg-primary/90 text-white px-6 py-2 rounded-lg transition-all duration-300 flex items-center;
}
.btn-primary:disabled {
  @apply opacity-50 cursor-not-allowed;
}

/* 卡片样式增强 */
.card {
  @apply bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-gray-200 shadow-card;
}
.card-danger {
  @apply bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-red-300 shadow-crash;
}

/* 输入框样式 */
.input-field {
  @apply w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary;
}

/* 状态指示器 */
.status-indicator {
  @apply w-2 h-2 rounded-full mr-1;
}
.status-running {
  @apply bg-green-500 animate-pulse;
}
.status-paused {
  @apply bg-yellow-500 animate-pulse;
}
.status-crashed {
  @apply bg-red-500 animate-pulse;
}
.status-idle {
  @apply bg-yellow-500;
}

/* MQTT协议专用样式 */
.mqtt-header-line {
  @apply mb-1 p-2 bg-purple-50 border-l-4 border-purple-400 rounded;
}
.mqtt-stats-line {
  @apply mb-1 p-1 bg-green-50 border-l-2 border-green-400 rounded;
}
.mqtt-error-line {
  @apply mb-1 p-1 bg-red-50 border-l-2 border-red-400 rounded;
}
.mqtt-warning-line {
  @apply mb-1 p-1 bg-yellow-50 border-l-2 border-yellow-400 rounded;
}
.mqtt-success-line {
  @apply mb-1 p-1 bg-green-50 border-l-2 border-green-400 rounded;
}
.mqtt-info-line {
  @apply mb-1 p-1;
}
.mqtt-diff-line {
  @apply mb-2;
}
.mqtt-diff-line .p-3 {
  transition: all 0.2s ease-in-out;
}
.mqtt-diff-line:hover .p-3 {
  transform: translateX(2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* RTSP协议专用样式 */
.rtsp-header-line {
  @apply mb-1 p-2 bg-blue-50 border-l-4 border-blue-400 rounded;
}
.rtsp-stats-line {
  @apply mb-1 p-1 bg-green-50 border-l-2 border-green-400 rounded;
}
.rtsp-info-line {
  @apply mb-1 p-1;
}
</style>


