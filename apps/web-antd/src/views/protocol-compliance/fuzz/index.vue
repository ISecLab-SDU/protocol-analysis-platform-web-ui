<script setup lang="ts">
import { onMounted, ref, nextTick, computed, watch } from 'vue';
import { getFuzzText } from '#/api/custom';
import Chart from 'chart.js/auto';

// Data state
const rawText = ref('');
const loading = ref(true);
const error = ref<string | null>(null);

// Parsed data
interface FuzzPacket {
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

const fuzzData = ref<FuzzPacket[]>([]);
const totalPacketsInFile = ref(0);
// File-level summary stats parsed from txt
const fileTotalPackets = ref(0);
const fileSuccessCount = ref(0);
const fileTimeoutCount = ref(0);
const fileFailedCount = ref(0);

// Aggregates
const protocolStats = ref({ v1: 0, v2c: 0, v3: 0 });
const messageTypeStats = ref({ get: 0, set: 0, getnext: 0, getbulk: 0 });

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
const protocolType = ref('SNMP');
const fuzzEngine = ref('SNMP_Fuzz');
const targetHost = ref('192.168.102.2');
const targetPort = ref(161);
const rtspCommandConfig = ref('afl-fuzz -d -i $AFLNET/tutorials/live555/in-rtsp -o out-live555 -N tcp://127.0.0.1/8554 -x $AFLNET/tutorials/live555/rtsp.dict -P RTSP -D 10000 -q 3 -s 3 -E -K -R ./testOnDemandRTSPServer 8554');

// Real-time log reading
const isReadingLog = ref(false);
const logReadingInterval = ref<number | null>(null);
const rtspProcessId = ref<number | null>(null);
const logReadPosition = ref(0);

// Watch for protocol changes to update port
watch(protocolType, (newProtocol) => {
  if (newProtocol === 'SNMP') {
    targetPort.value = 161;
  } else if (newProtocol === 'RTSP') {
    targetPort.value = 554;
  } else if (newProtocol === 'MQTT') {
    targetPort.value = 1883;
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

// UI refs
const logContainer = ref<HTMLDivElement | null>(null);
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
  if (!messageTypeChart || !versionChart) return;
  messageTypeChart.data.datasets[0].data = [
    messageTypeStats.value.get || 0,
    messageTypeStats.value.set || 0,
    messageTypeStats.value.getnext || 0,
    messageTypeStats.value.getbulk || 0,
  ];
  messageTypeChart.update();

  versionChart.data.datasets[0].data = [
    protocolStats.value.v1 || 0,
    protocolStats.value.v2c || 0,
    protocolStats.value.v3 || 0,
  ];
  versionChart.update();
}

function parseText(text: string) {
  if (!text || typeof text !== 'string') {
    console.error('Invalid fuzz data format');
    return;
  }

  const lines = text.split('\n');
  console.log('解析文本总行数:', lines.length);
  
  if (lines.length < 5) {
    console.error('Insufficient fuzz data');
    return;
  }

  fuzzData.value = [];
  let currentPacket: FuzzPacket | null = null;
  let localFailedCount = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    const packetMatch = line.match(/^\[(\d+)\]\s+版本=([^,]+),\s+类型=([^,]+)/);
    if (packetMatch) {
      if (currentPacket) fuzzData.value.push(currentPacket);
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
        fuzzData.value.push(currentPacket);
        currentPacket = null;
      } else {
        fuzzData.value.push({ id: failedId, version: 'unknown', type: 'unknown', oids: [], hex: '', result: 'failed', responseSize: 0, timestamp: new Date().toLocaleTimeString(), failed: true, failedReason: line });
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
        const crashEvent = { type: 'crash_notification', message: line, timestamp: new Date().toLocaleTimeString(), crashPacket: '', crashLogPath: '' };
        for (let j = i + 1; j < lines.length && j < i + 30; j++) {
          const nextLine = lines[j].trim();
          if (nextLine.includes('[崩溃信息] 疑似崩溃数据包:')) crashEvent.crashPacket = nextLine.replace('[崩溃信息] 疑似崩溃数据包: ', '');
          else if (nextLine.includes('[崩溃信息] 崩溃队列信息导出:')) crashEvent.crashLogPath = nextLine.replace('[崩溃信息] 崩溃队列信息导出: ', '');
          if (crashEvent.crashPacket && crashEvent.crashLogPath) break;
        }
        fuzzData.value.push({ id: 'crash_event', version: 'crash', type: 'crash', oids: [], hex: crashEvent.crashPacket, result: 'crash', responseSize: 0, timestamp: crashEvent.timestamp, crashEvent, });
        if (currentPacket) { currentPacket.result = 'crash'; (currentPacket as any).crashInfo = line; }
      } else if (line.includes('检测到崩溃')) {
        if (currentPacket) (currentPacket as any).monitorInfo = line;
      }
      continue;
    }
  }

  if (currentPacket) fuzzData.value.push(currentPacket);
  totalPacketsInFile.value = fuzzData.value.filter((p) => typeof p.id === 'number').length;
  
  console.log('解析完成统计:');
  console.log('- 总数据包数:', fuzzData.value.length);
  console.log('- 有效数据包数:', totalPacketsInFile.value);
  console.log('- 失败数据包数:', localFailedCount);

  // Stats line
  const statsLine = (text.match(/^统计:.*$/m) || [])[0];
  if (statsLine) {
    const objMatch = statsLine.match(/统计:\s*(\{[^}]+\})\s*,\s*(\{[^}]+\})/);
    if (objMatch) {
      try {
        const versionJson = objMatch[1].replace(/'/g, '"');
        const typeJson = objMatch[2].replace(/'/g, '"');
        const parsedVersion = JSON.parse(versionJson);
        const parsedType = JSON.parse(typeJson);
        protocolStats.value = { v1: parsedVersion.v1 || 0, v2c: parsedVersion.v2c || 0, v3: parsedVersion.v3 || 0 };
        messageTypeStats.value = { get: parsedType.get || 0, set: parsedType.set || 0, getnext: parsedType.getnext || 0, getbulk: parsedType.getbulk || 0 };
      } catch {}
    }
  }

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
  
  if (logContainer.value) {
    logContainer.value.innerHTML = '';
  }
}

async function startTest() {
  if (!fuzzData.value.length) return;
  
  resetTestState();
  isRunning.value = true;
  isTestCompleted.value = false;
  showCharts.value = false; // Hide charts during test
  testStartTime.value = new Date();
  
  // 根据协议类型执行不同的启动逻辑
  try {
    if (protocolType.value === 'RTSP') {
      await startRTSPTest();
    } else if (protocolType.value === 'SNMP') {
      await startSNMPTest();
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
    await writeRTSPScript();
    
    // 2. 执行shell命令启动程序
    await executeRTSPCommand();
    
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

async function startSNMPTest() {
  // SNMP协议的原有逻辑
  packetDelay.value = 1000 / packetsPerSecond.value;
  loop();
}

async function startMQTTTest() {
  // MQTT协议的启动逻辑（待实现）
  console.log('MQTT test starting...');
  addLogToUI({ 
    timestamp: new Date().toLocaleTimeString(),
    version: 'MQTT',
    type: 'START',
    oids: ['MQTT测试已启动'],
    hex: '',
    result: 'success'
  } as any, false);
}

// RTSP specific functions
async function writeRTSPScript() {
  const scriptContent = rtspCommandConfig.value;
  
  try {
    // 调用后端API写入脚本文件
    const response = await fetch('/api/protocol-compliance/write-script', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content: scriptContent,
        protocol: 'RTSP'
      }),
    });
    
    if (!response.ok) {
      throw new Error(`写入脚本文件失败: ${response.statusText}`);
    }
    
    const result = await response.json();
    
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

async function executeRTSPCommand() {
  try {
    // 调用后端API执行shell命令
    const response = await fetch('/api/protocol-compliance/execute-command', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        protocol: 'RTSP'
      }),
    });
    
    if (!response.ok) {
      throw new Error(`执行命令失败: ${response.statusText}`);
    }
    
    const result = await response.json();
    
    // 保存进程ID用于后续停止
    if (result.data && result.data.pid) {
      rtspProcessId.value = result.data.pid;
    }
    
    addLogToUI({ 
      timestamp: new Date().toLocaleTimeString(),
      version: 'RTSP',
      type: 'COMMAND',
      oids: [`命令已执行 (PID: ${result.data?.pid || 'unknown'})`],
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

// 处理RTSP协议的AFL-NET日志行
function processRTSPLogLine(line: string) {
  const timestamp = new Date().toLocaleTimeString();
  
  // 处理注释行（参数说明）
  if (line.startsWith('#')) {
    addRTSPLogToUI({
      timestamp,
      type: 'HEADER',
      content: line.replace('#', '').trim(),
      isHeader: true
    });
    return;
  }
  
  // 处理数据行
  if (line.includes(',')) {
    const parts = line.split(',').map(part => part.trim());
    if (parts.length >= 13) {
      const [
        unix_time, cycles_done, cur_path, paths_total, pending_total, 
        pending_favs, map_size, unique_crashes, unique_hangs, max_depth, 
        execs_per_sec, n_nodes, n_edges
      ] = parts;
      
      // 格式化显示AFL-NET统计信息
      const formattedContent = `Cycles: ${cycles_done} | Paths: ${cur_path}/${paths_total} | Pending: ${pending_total}(${pending_favs} favs) | Coverage: ${map_size} | Crashes: ${unique_crashes} | Hangs: ${unique_hangs} | Speed: ${execs_per_sec}/sec | Nodes: ${n_nodes} | Edges: ${n_edges}`;
      
      addRTSPLogToUI({
        timestamp,
        type: 'STATS',
        content: formattedContent,
        rawData: {
          cycles_done: parseInt(cycles_done),
          paths_total: parseInt(paths_total),
          cur_path: parseInt(cur_path),
          pending_total: parseInt(pending_total),
          unique_crashes: parseInt(unique_crashes),
          execs_per_sec: parseFloat(execs_per_sec)
        }
      });
      
      // 更新统计信息
      packetCount.value = parseInt(cur_path);
      successCount.value = parseInt(paths_total) - parseInt(pending_total);
      failedCount.value = parseInt(unique_crashes);
      currentSpeed.value = Math.round(parseFloat(execs_per_sec));
    }
  } else {
    // 处理其他类型的日志行
    addRTSPLogToUI({
      timestamp,
      type: 'INFO',
      content: line
    });
  }
}

// RTSP专用的日志显示函数
function addRTSPLogToUI(logData: any) {
  if (!logContainer.value) return;
  
  const div = document.createElement('div');
  
  if (logData.isHeader) {
    // 参数说明行
    div.className = 'rtsp-header-line';
    div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-info font-medium">AFL-NET参数说明:</span> <span class="text-dark/70 text-xs">${logData.content}</span>`;
  } else if (logData.type === 'STATS') {
    // 统计数据行
    div.className = 'rtsp-stats-line';
    div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-success font-medium">AFL-NET统计:</span> <span class="text-dark font-mono text-xs">${logData.content}</span>`;
  } else {
    // 普通信息行
    div.className = 'rtsp-info-line';
    div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-primary">RTSP-AFL:</span> <span class="text-dark/70">${logData.content}</span>`;
  }
  
  logContainer.value.appendChild(div);
  logContainer.value.scrollTop = logContainer.value.scrollHeight;
  
  // 限制日志条目数量
  if (logContainer.value.children.length > 200) {
    logContainer.value.removeChild(logContainer.value.firstChild as any);
  }
}

async function stopRTSPProcess() {
  if (!rtspProcessId.value) {
    return;
  }
  
  try {
    const response = await fetch('/api/protocol-compliance/stop-process', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        pid: rtspProcessId.value,
        protocol: 'RTSP'
      }),
    });
    
    if (response.ok) {
      addLogToUI({ 
        timestamp: new Date().toLocaleTimeString(),
        version: 'RTSP',
        type: 'STOP',
        oids: [`RTSP进程已停止 (PID: ${rtspProcessId.value})`],
        hex: '',
        result: 'success'
      } as any, false);
      
      rtspProcessId.value = null;
    }
  } catch (error) {
    console.error('停止RTSP进程失败:', error);
  }
}

function stopTest() {
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
  
  // 停止RTSP进程
  if (protocolType.value === 'RTSP') {
    stopRTSPProcess();
  }
  
  if (testTimer) { 
    clearInterval(testTimer as any); 
    testTimer = null; 
  }
  
  // Update final statistics
  updateTestSummary();
  
  console.log('Test completed, updating charts:', {
    isTestCompleted: isTestCompleted.value,
    protocolStats: protocolStats.value,
    messageTypeStats: messageTypeStats.value
  });
  
  // Update charts with final data
  nextTick(() => {
    updateCharts();
  });
}

function togglePauseTest() {
  isPaused.value = !isPaused.value;
  if (!isPaused.value && isRunning.value) {
    loop();
  }
}

function clearLog() {
  if (logContainer.value) {
    logContainer.value.innerHTML = '<div class="text-dark/50 italic">测试未开始，请配置参数并点击"开始测试"</div>';
  }
  logEntries.value = [];
}

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
  if (!isRunning.value || isPaused.value) return;
  
  if (currentPacketIndex.value >= fuzzData.value.length) {
    return stopTest();
  }
  
  const packet = fuzzData.value[currentPacketIndex.value];
  if (packet) {
    processPacket(packet);
  }
  
  currentPacketIndex.value++;
  packetCount.value++;
  
  if (packetCount.value === 1 || packetCount.value % 50 === 0 || currentPacketIndex.value >= fuzzData.value.length) {
    updateCharts();
  }
  
  // Check for crash and stop if detected
  if (packet?.result === 'crash') {
    handleCrashDetection(packet);
    // Add a small delay before stopping to ensure UI updates
    setTimeout(() => stopTest(), 100);
    return;
  }
  
  // Continue loop with appropriate delay
  window.setTimeout(() => loop(), packetDelay.value);
}

function processPacket(packet: FuzzPacket) {
  // Update statistics
  if (packet.result === 'success') successCount.value++;
  else if (packet.result === 'timeout') timeoutCount.value++;
  else if (packet.result === 'failed') failedCount.value++;
  else if (packet.result === 'crash') crashCount.value++;
  
  // Add to log entries
  const logEntry = {
    time: packet.timestamp || new Date().toLocaleTimeString(),
    protocol: packet.version,
    operation: packet.type,
    target: `${targetHost.value}:${targetPort.value}`,
    content: packet.oids?.[0] || '',
    result: packet.result,
    hex: packet.hex,
    packetId: packet.id
  };
  logEntries.value.push(logEntry);
  
  // Update UI log (sparse updates for performance)
  if (logContainer.value) {
    if (packet.result !== 'crash' && packetCount.value % 5 === 0) {
      addLogToUI(packet, false);
    } else if (packet.result === 'crash') {
      addLogToUI(packet, true);
    }
  }
}

function addLogToUI(packet: FuzzPacket, isCrash: boolean) {
  if (!logContainer.value) return;
  
  const div = document.createElement('div');
  div.className = isCrash ? 'crash-highlight' : 'packet-highlight';
  
  if (isCrash) {
    div.innerHTML = `<span class="text-dark/50">[${packet.timestamp || ''}]</span> <span class="text-danger font-bold">CRASH DETECTED</span> <span class="text-danger">${packet.version?.toUpperCase()}</span> <span class="text-danger">${packet.type?.toUpperCase()}</span>`;
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
  
  logContainer.value.appendChild(div);
  logContainer.value.scrollTop = logContainer.value.scrollHeight;
  
  // Limit log entries for performance
  if (logContainer.value.children.length > 200) {
    logContainer.value.removeChild(logContainer.value.firstChild as any);
  }
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
  
  // Add to UI
  if (logContainer.value) {
    const logs = [
      `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">${crashEvent.message}</span>`,
      `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 疑似崩溃数据包: ${crashEvent.crashPacket}</span>`,
      `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 崩溃队列信息导出: ${crashEvent.crashLogPath}</span>`,
      `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">[运行监控] 检测到崩溃，停止 fuzz 循环</span>`
    ];
    
    logs.forEach(logHtml => {
      const div = document.createElement('div');
      div.className = 'crash-highlight';
      div.innerHTML = logHtml;
      logContainer.value!.appendChild(div);
    });
    
    logContainer.value.scrollTop = logContainer.value.scrollHeight;
  }
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
  
  if (logContainer.value) {
    const logs = [
      `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">[运行监控] 收到崩溃通知: 健康服务报告 VM 不可达</span>`,
      `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 疑似崩溃数据包: ${hex}</span>`,
      `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 日志导出目录: ${crashDetails.logPath}</span>`,
      `<span class="text-dark/50">[${time}]</span> <span class="text-warning">  [接收超时]</span>`,
      `<span class="text-dark/50">[${time}]</span> <span class="text-warning">  响应: 无</span>`,
      `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">[运行监控] 检测到崩溃，停止 fuzz 循环</span>`
    ];
    
    logs.forEach(logHtml => {
      const div = document.createElement('div');
      div.className = 'crash-highlight';
      div.innerHTML = logHtml;
      logContainer.value!.appendChild(div);
    });
    
    logContainer.value.scrollTop = logContainer.value.scrollHeight;
  }
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

function toggleCrashDetailsView() {
  showCrashDetails.value = !showCrashDetails.value;
}

// Computed properties for button states
const canStartTest = computed(() => {
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

onMounted(async () => {
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
                  <option value="SNMP_Fuzz">SNMP_Fuzz</option>
                  <option value="AFLNET">AFLNET</option>
                  <option value="MQTT_FUZZ">MQTT_FUZZ</option>
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
            <button v-if="isRunning" @click="stopTest" 
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
                <button @click="clearLog" class="text-xs bg-light-gray hover:bg-medium-gray px-2 py-1 rounded border border-dark/10 text-dark/70">
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
              <div class="text-dark/50 italic" v-if="!isRunning && logEntries.length === 0">测试未开始，请配置参数并点击"开始测试"</div>
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
            <div v-else class="bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-secondary/20 shadow-card h-full">
              <div class="flex justify-between items-center mb-4">
                <h3 class="font-semibold text-lg">崩溃监控</h3>
                <span class="bg-success/10 text-success text-xs px-2 py-0.5 rounded-full">正常</span>
              </div>
              <div class="h-full flex flex-col items-center justify-center text-dark/50 text-sm">
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
          <!-- 消息类型分布和版本统计 -->
          <div class="xl:col-span-3 bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-secondary/20 shadow-card">
            <div class="flex justify-between items-center mb-6">
              <h3 class="font-semibold text-xl">消息类型分布与版本统计</h3>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8 h-72">
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
          </div>
          
          <!-- 实时统计 -->
          <div class="xl:col-span-1 bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-primary/20 shadow-card">
            <h3 class="font-semibold text-lg mb-4">实时统计</h3>
            <div class="space-y-6">
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
          </div>
        </div>
        
        <!-- 测试总结 -->
        <div v-if="!showCrashDetails" class="bg-white/80 backdrop-blur-sm rounded-xl p-4 border border-secondary/20 shadow-card">
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
                <p><span class="text-dark/60">协议名称:</span> <span>{{ isTestCompleted ? protocolType.toUpperCase() : '未测试' }}</span></p>
                <p><span class="text-dark/60">Fuzz引擎:</span> <span>{{ isTestCompleted ? fuzzEngine : '未设置' }}</span></p>
                <p><span class="text-dark/60">测试目标:</span> <span>{{ isTestCompleted ? `${targetHost}:${targetPort}` : '未设置' }}</span></p>
                <p><span class="text-dark/60">开始时间:</span> <span>{{ isTestCompleted ? (startTime || (testStartTime ? testStartTime.toLocaleString() : '未开始')) : '未开始' }}</span></p>
                <p><span class="text-dark/60">结束时间:</span> <span>{{ isTestCompleted ? (endTime || (testEndTime ? testEndTime.toLocaleString() : '未结束')) : '未结束' }}</span></p>
                <p><span class="text-dark/60">总耗时:</span> <span>{{ isTestCompleted ? elapsedTime : 0 }}秒</span></p>
              </div>
            </div>
            
            <div class="bg-light-gray rounded-lg p-3 border border-dark/10">
              <h4 class="font-medium mb-2 text-dark/80">性能统计</h4>
              <div class="space-y-1">
                <p><span class="text-dark/60">SNMP_v1发包数:</span> <span>{{ isTestCompleted ? protocolStats.v1 : 0 }}</span></p>
                <p><span class="text-dark/60">SNMP_v2发包数:</span> <span>{{ isTestCompleted ? protocolStats.v2c : 0 }}</span></p>
                <p><span class="text-dark/60">SNMP_v3发包数:</span> <span>{{ isTestCompleted ? protocolStats.v3 : 0 }}</span></p>
                <p><span class="text-dark/60">总发包数:</span> <span>{{ isTestCompleted ? fileTotalPackets : 0 }}</span></p>
                <p><span class="text-dark/60">正常响应率:</span> <span>{{ isTestCompleted ? Math.round((fileSuccessCount / Math.max(fileTotalPackets, 1)) * 100) : 0 }}%</span></p>
                <p><span class="text-dark/60">超时率:</span> <span>{{ isTestCompleted ? Math.round((fileTimeoutCount / Math.max(fileTotalPackets, 1)) * 100) : 0 }}%</span></p>
              </div>
            </div>
            
            <div class="bg-light-gray rounded-lg p-3 border border-dark/10">
              <h4 class="font-medium mb-2 text-dark/80">文件信息</h4>
              <div class="space-y-2">
                <div class="flex items-center">
                  <i class="fa fa-file-text-o text-primary mr-2"></i>
                  <div class="flex-1">
                    <p class="truncate text-xs">运行日志信息</p>
                    <p class="truncate text-xs text-dark/50">{{ isTestCompleted ? 'scan_result/fuzz_logs/fuzz_output.txt' : '无' }}</p>
                  </div>
                  <button @click="saveLog" class="text-xs bg-primary/10 hover:bg-primary/20 text-primary px-1.5 py-0.5 rounded">
                    下载
                  </button>
                </div>
                <div class="flex items-center">
                  <i class="fa fa-file-excel-o text-danger mr-2"></i>
                  <div class="flex-1">
                    <p class="truncate text-xs">崩溃队列信息</p>
                    <p class="truncate text-xs text-dark/50">{{ isTestCompleted ? 'scan_result/crash_logs/20251014-110318' : '无' }}</p>
                  </div>
                  <button @click="saveLog" class="text-xs bg-primary/10 hover:bg-primary/20 text-primary px-1.5 py-0.5 rounded">
                    下载
                  </button>
                </div>
                <div class="flex items-center">
                  <i class="fa fa-file-excel-o text-success mr-2"></i>
                  <div class="flex-1">
                    <p class="truncate text-xs">Fuzz报告信息</p>
                    <p class="truncate text-xs text-dark/50">{{ isTestCompleted ? `fuzz_report_${new Date().getTime()}.txt` : '无' }}</p>
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


