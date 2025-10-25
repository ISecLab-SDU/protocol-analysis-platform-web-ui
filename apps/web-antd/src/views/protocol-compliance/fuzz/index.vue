<script setup lang="ts">
import { onMounted, ref, nextTick, computed, watch, h } from 'vue';
import { getFuzzText } from '#/api/custom';
import Chart from 'chart.js/auto';
import type { TableColumnType } from 'ant-design-vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  Alert,
  Button,
  Card,
  Descriptions,
  Drawer,
  Empty,
  Form,
  FormItem,
  Input,
  InputNumber,
  Popconfirm,
  Progress,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'ant-design-vue';

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

const TypographyParagraph = Typography.Paragraph;
const TypographyText = Typography.Text;
const TypographyTitle = Typography.Title;

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

// 历史结果相关状态
const activeTabKey = ref<'live' | 'history'>('live');
const showHistoryView = ref(false);
const selectedHistoryItem = ref<any>(null);
const historyDrawerOpen = ref(false);

watch(activeTabKey, (key) => {
  showHistoryView.value = key === 'history';
  if (key !== 'history') {
    historyDrawerOpen.value = false;
  }
});

watch(historyDrawerOpen, (open) => {
  if (!open) {
    selectedHistoryItem.value = null;
  }
});

// 通知相关状态
const showNotification = ref(false);
const notificationMessage = ref('');

// 历史结果数据接口
interface HistoryResult {
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
  hasCrash: boolean;
  crashDetails?: any;
}

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
    
    // Reset log container with proper checks
    nextTick(() => {
      try {
        if (logContainer.value && !showHistoryView.value && logContainer.value.innerHTML !== undefined) {
          logContainer.value.innerHTML = '<div class="log-empty">测试未开始，请配置参数并点击“开始测试”</div>';
        }
      } catch (error) {
        console.warn('Failed to reset log container:', error);
      }
    });
  } catch (error) {
    console.error('Error in resetTestState:', error);
  }
}

async function startTest() {
  if (!fuzzData.value.length) return;
  
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
  if (!logContainer.value || showHistoryView.value) {
    return;
  }

  const timestamp = logData.timestamp || new Date().toLocaleTimeString();

  if (logData.isHeader) {
    appendLogLine(
      timestamp,
      [
        { text: 'AFL-NET', className: 'log-entry__protocol' },
        { text: logData.content, className: 'log-entry__summary' },
      ],
      { variant: 'warning' },
    );
    return;
  }

  if (logData.type === 'STATS') {
    appendLogLine(
      timestamp,
      [
        { text: 'AFL-NET', className: 'log-entry__protocol' },
        { text: logData.content, className: 'log-entry__summary' },
      ],
    );
    return;
  }

  appendLogLine(
    timestamp,
    [
      { text: 'RTSP-AFL', className: 'log-entry__protocol' },
      { text: logData.content },
    ],
  );
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
  try {
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
    
    // Save test results to history
    saveTestToHistory();
    
    console.log('Test completed, updating charts:', {
      isTestCompleted: isTestCompleted.value,
      protocolStats: protocolStats.value,
      messageTypeStats: messageTypeStats.value
    });
    
    // Use nextTick to ensure all reactive updates are complete before updating charts
    nextTick(() => {
      try {
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
      } catch (error) {
        console.error('Error updating charts on test completion:', error);
      }
    });
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

function clearLog() {
  try {
    logEntries.value = [];
    
    nextTick(() => {
      try {
        if (logContainer.value && !showHistoryView.value && logContainer.value.innerHTML !== undefined) {
          logContainer.value.innerHTML = '<div class="log-empty">测试未开始，请配置参数并点击“开始测试”</div>';
        }
      } catch (error) {
        console.warn('Failed to clear log container:', error);
      }
    });
  } catch (error) {
    console.warn('Failed to clear log:', error);
  }
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
      processPacket(packet);
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

function processPacket(packet: FuzzPacket) {
  try {
    // Update statistics in a batch to prevent multiple reactive updates
    const updates = {
      success: packet.result === 'success' ? 1 : 0,
      timeout: packet.result === 'timeout' ? 1 : 0,
      failed: packet.result === 'failed' ? 1 : 0,
      crash: packet.result === 'crash' ? 1 : 0
    };
    
    // Batch update all counters at once
    successCount.value += updates.success;
    timeoutCount.value += updates.timeout;
    failedCount.value += updates.failed;
    crashCount.value += updates.crash;
    
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
    
    // Update UI log with proper null checks (sparse updates for performance)
    if (isRunning.value && !showHistoryView.value && logContainer.value && logContainer.value.appendChild) {
      if (packet.result !== 'crash' && packetCount.value % 5 === 0) {
        addLogToUI(packet, false);
      } else if (packet.result === 'crash') {
        addLogToUI(packet, true);
      }
    }
  } catch (error) {
    console.warn('Error processing packet:', error);
  }
}

function appendLogLine(
  timestamp: string,
  segments: Array<{ text: string; className?: string }>,
  options: { variant?: 'crash' | 'warning' } = {},
) {
  if (!logContainer.value || showHistoryView.value) {
    return;
  }
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  if (options.variant === 'crash') {
    entry.classList.add('log-entry--crash');
  } else if (options.variant === 'warning') {
    entry.classList.add('log-entry--warning');
  }

  const timeEl = document.createElement('span');
  timeEl.className = 'log-entry__time';
  timeEl.textContent = `[${timestamp}]`;
  entry.appendChild(timeEl);

  segments
    .filter((segment) => segment.text)
    .forEach((segment) => {
      const span = document.createElement('span');
      span.className = segment.className
        ? `log-entry__segment ${segment.className}`
        : 'log-entry__segment';
      span.textContent = segment.text;
      entry.appendChild(span);
    });

  logContainer.value.appendChild(entry);
  logContainer.value.scrollTop = logContainer.value.scrollHeight;

  if (logContainer.value.children.length > 200) {
    logContainer.value.removeChild(logContainer.value.firstChild as Element);
  }
}

function addLogToUI(packet: FuzzPacket, isCrash: boolean) {
  if (!isRunning.value || showHistoryView.value) {
    return;
  }

  nextTick(() => {
    if (!isRunning.value || showHistoryView.value || !logContainer.value) {
      return;
    }

    const timestamp = packet.timestamp || new Date().toLocaleTimeString();

    if (isCrash) {
      appendLogLine(
        timestamp,
        [
          { text: '检测到崩溃', className: 'log-entry__crash-label' },
          { text: packet.version?.toUpperCase() || 'UNKNOWN', className: 'log-entry__protocol' },
          { text: packet.type?.toUpperCase() || 'UNKNOWN', className: 'log-entry__operation' },
        ],
        { variant: 'crash' },
      );
      return;
    }

    const protocol = packet.version?.toUpperCase() || 'UNKNOWN';
    const operation = packet.type?.toUpperCase() || 'UNKNOWN';
    const content = packet.oids?.[0] || '';
    const hex = (packet.hex || '').slice(0, 40);

    const resultMeta: Record<
      FuzzPacket['result'],
      { label: string; className: string }
    > = {
      success: {
        label: `正常响应 (${packet.responseSize || 0}字节)`,
        className: 'log-entry__result--success',
      },
      timeout: { label: '接收超时', className: 'log-entry__result--warning' },
      failed: { label: '构造失败', className: 'log-entry__result--danger' },
      crash: { label: '检测到崩溃', className: 'log-entry__result--danger' },
      unknown: { label: '未知状态', className: 'log-entry__result--warning' },
    };

    const { label: resultText, className: resultClass } =
      resultMeta[packet.result] || resultMeta.unknown;

    appendLogLine(timestamp, [
      { text: protocol, className: 'log-entry__protocol' },
      { text: operation, className: 'log-entry__operation' },
      { text: content, className: 'log-entry__summary' },
      {
        text: resultText,
        className: `log-entry__result ${resultClass}`,
      },
      {
        text: hex ? `${hex}...` : '',
        className: 'log-entry__hex',
      },
    ]);
  });
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
  
  nextTick(() => {
    appendLogLine(
      time,
      [{ text: crashEvent.message || '崩溃通知', className: 'log-entry__crash-label' }],
      { variant: 'crash' },
    );
    appendLogLine(
      time,
      [{ text: `[崩溃信息] 疑似崩溃数据包: ${crashEvent.crashPacket || '未知'}` }],
      { variant: 'crash' },
    );
    appendLogLine(
      time,
      [{ text: `[崩溃信息] 崩溃队列信息导出: ${crashEvent.crashLogPath || '未知路径'}` }],
      { variant: 'crash' },
    );
    appendLogLine(
      time,
      [{ text: '[运行监控] 检测到崩溃，停止 fuzz 循环' }],
      { variant: 'crash' },
    );
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
    appendLogLine(
      time,
      [{ text: '[运行监控] 收到崩溃通知: 健康服务报告 VM 不可达', className: 'log-entry__crash-label' }],
      { variant: 'crash' },
    );
    appendLogLine(
      time,
      [{ text: `[崩溃信息] 疑似崩溃数据包: ${hex || '未知'}` }],
      { variant: 'crash' },
    );
    appendLogLine(
      time,
      [{ text: `[崩溃信息] 日志导出目录: ${crashDetails?.logPath || '未知路径'}` }],
      { variant: 'crash' },
    );
    appendLogLine(time, [{ text: '[接收超时]' }], { variant: 'warning' });
    appendLogLine(time, [{ text: '响应: 无' }], { variant: 'warning' });
    appendLogLine(time, [{ text: '[运行监控] 检测到崩溃，停止 fuzz 循环' }], {
      variant: 'crash',
    });
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
      
      // 显示保存成功的通知
      showSaveNotification();
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
  activeTabKey.value = 'history';
}

function backToMainView() {
  activeTabKey.value = 'live';
}

function viewHistoryDetail(item: HistoryResult) {
  selectedHistoryItem.value = item;
  historyDrawerOpen.value = true;
}

function backToHistoryList() {
  selectedHistoryItem.value = null;
  historyDrawerOpen.value = false;
}

function closeHistoryDrawer() {
  historyDrawerOpen.value = false;
}

function deleteHistoryItem(id: string) {
  const index = historyResults.value.findIndex(item => item.id === id);
  if (index > -1) {
    historyResults.value.splice(index, 1);
    if (selectedHistoryItem.value?.id === id) {
      historyDrawerOpen.value = false;
      selectedHistoryItem.value = null;
    }
    
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
    historyDrawerOpen.value = false;
    selectedHistoryItem.value = null;
    
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
  notificationMessage.value = '测试结果已保存到历史记录';
  showNotification.value = true;
  
  // 3秒后自动隐藏通知
  setTimeout(() => {
    showNotification.value = false;
  }, 3000);
}

// 手动关闭通知
function closeNotification() {
  showNotification.value = false;
}

function dismissError() {
  error.value = null;
}

const historyColumns = computed<TableColumnType<HistoryResult>[]>(() => [
  {
    title: '测试时间',
    dataIndex: 'timestamp',
    key: 'timestamp',
    width: 180,
  },
  {
    title: '协议',
    dataIndex: 'protocol',
    key: 'protocol',
    width: 100,
    customRender: ({ text }) =>
      h(Tag, { color: 'blue' }, () => String(text ?? '未知')),
  },
  {
    title: '引擎',
    dataIndex: 'fuzzEngine',
    key: 'fuzzEngine',
    width: 110,
    customRender: ({ text }) =>
      h(Tag, { color: 'cyan' }, () => String(text ?? '未知')),
  },
  {
    title: '目标',
    key: 'target',
    customRender: ({ record }) =>
      `${record.targetHost}:${record.targetPort}`,
  },
  {
    title: '总包数',
    dataIndex: 'totalPackets',
    key: 'totalPackets',
    width: 100,
  },
  {
    title: '成功率',
    dataIndex: 'successRate',
    key: 'successRate',
    width: 100,
    customRender: ({ text }) => `${text}%`,
  },
  {
    title: '耗时(秒)',
    dataIndex: 'duration',
    key: 'duration',
    width: 110,
  },
  {
    title: '崩溃',
    dataIndex: 'hasCrash',
    key: 'hasCrash',
    width: 90,
    customRender: ({ record }) =>
      record.hasCrash
        ? h(Tag, { color: 'error' }, () => '是')
        : h(Tag, { color: 'success' }, () => '否'),
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    customRender: ({ record }) =>
      h(
        Space,
        { size: 'small' },
        {
          default: () => [
            h(
              Button,
              {
                type: 'link',
                size: 'small',
                onClick: () => viewHistoryDetail(record as HistoryResult),
              },
              { default: () => '查看' },
            ),
            h(
              Button,
              {
                type: 'link',
                size: 'small',
                onClick: () => exportHistoryItem(record as HistoryResult),
              },
              { default: () => '导出' },
            ),
            h(
              Popconfirm,
              {
                title: '确定删除这条记录吗？',
                okText: '删除',
                cancelText: '取消',
                onConfirm: () => deleteHistoryItem((record as HistoryResult).id),
              },
              {
                default: () =>
                  h(
                    Button,
                    { type: 'link', size: 'small', danger: true },
                    { default: () => '删除' },
                  ),
              },
            ),
          ],
        },
      ),
  },
]);

// Computed properties for button states
const canStartTest = computed(() => {
  return !loading.value && 
         fuzzData.value.length > 0 && 
         !isRunning.value;
});

const testStatusText = computed(() => {
  if (isRunning.value) {
    return isPaused.value ? '已暂停' : '运行中';
  }
  if (crashCount.value > 0) {
    return '检测到崩溃';
  }
  return '未开始';
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
  <Page
    description="调度多协议模糊测试任务，监控运行状态并收集崩溃线索。"
    title="模糊测试"
  >
    <div class="fuzz-view">
      <Tabs v-model:active-key="activeTabKey" class="fuzz-tabs">
        <Tabs.TabPane key="live" tab="实时测试">
          <div class="live-layout">
            <div class="live-column">
              <Card class="config-card">
                <template #title>
                  <Space>
                    <IconifyIcon icon="ant-design:experiment-outlined" class="card-icon" />
                    <span>测试配置</span>
                  </Space>
                </template>
                <template #extra>
                  <Space size="small">
                    <Tag
                      :color="isRunning ? (isPaused ? 'warning' : 'processing') : crashCount > 0 ? 'error' : 'default'"
                    >
                      {{ testStatusText }}
                    </Tag>
                    <Button size="small" type="link" @click="goToHistoryView">
                      <IconifyIcon icon="ant-design:history-outlined" class="inline-icon" />
                      历史记录
                    </Button>
                  </Space>
                </template>
                <Spin :spinning="loading">
                  <Space direction="vertical" size="middle" class="config-body">
                    <Alert
                      v-if="error"
                      :message="error"
                      show-icon
                      type="error"
                      closable
                      @close="dismissError"
                    />
                    <Alert
                      v-if="showNotification"
                      :message="notificationMessage || '测试结果已保存到历史记录'"
                      show-icon
                      type="success"
                      closable
                      @close="closeNotification"
                    />
                    <Form layout="vertical" class="config-form">
                      <div class="config-grid">
                        <FormItem label="协议类型">
                          <Select v-model:value="protocolType">
                            <Select.Option value="SNMP">SNMP</Select.Option>
                            <Select.Option value="RTSP">RTSP</Select.Option>
                            <Select.Option value="MQTT">MQTT</Select.Option>
                          </Select>
                        </FormItem>
                        <FormItem label="Fuzz 引擎">
                          <Select v-model:value="fuzzEngine">
                            <Select.Option value="SNMP_Fuzz">SNMP_Fuzz</Select.Option>
                            <Select.Option value="AFLNET">AFLNET</Select.Option>
                            <Select.Option value="MQTT_FUZZ">MQTT_FUZZ</Select.Option>
                          </Select>
                        </FormItem>
                        <FormItem label="目标主机">
                          <Input v-model:value="targetHost" placeholder="例如 192.168.0.10" />
                        </FormItem>
                        <FormItem label="目标端口">
                          <InputNumber
                            v-model:value="targetPort"
                            :max="65535"
                            :min="1"
                            style="width: 100%;"
                          />
                        </FormItem>
                        <FormItem label="目标发送速率 (包/秒)">
                          <InputNumber
                            v-model:value="packetsPerSecond"
                            :min="1"
                            :step="1"
                            style="width: 100%;"
                          />
                        </FormItem>
                        <FormItem label="计划运行时长 (秒)">
                          <InputNumber
                            v-model:value="testDuration"
                            :min="10"
                            :step="10"
                            style="width: 100%;"
                          />
                        </FormItem>
                      </div>
                      <FormItem v-if="protocolType === 'RTSP'" label="RTSP 指令配置">
                        <Input.TextArea
                          v-model:value="rtspCommandConfig"
                          :rows="3"
                          placeholder="请输入 RTSP 协议的 AFLNET 启动指令"
                        />
                      </FormItem>
                      <div class="config-actions">
                        <TypographyText type="secondary">
                          最近更新：{{ lastUpdate || '未运行' }}
                        </TypographyText>
                        <Space>
                          <Button
                            type="primary"
                            :disabled="!canStartTest"
                            :loading="isRunning && !isPaused"
                            @click="startTest"
                          >
                            <IconifyIcon icon="ant-design:play-circle-outlined" class="inline-icon" />
                            开始测试
                          </Button>
                          <Button
                            v-if="isRunning"
                            @click="togglePauseTest"
                          >
                            <IconifyIcon
                              :icon="isPaused ? 'ant-design:caret-right-outlined' : 'ant-design:pause-circle-outlined'"
                              class="inline-icon"
                            />
                            {{ isPaused ? '继续' : '暂停' }}
                          </Button>
                          <Button
                            danger
                            v-if="isRunning"
                            @click="stopTest"
                          >
                            <IconifyIcon icon="ant-design:stop-outlined" class="inline-icon" />
                            停止
                          </Button>
                        </Space>
                      </div>
                    </Form>
                    <TypographyParagraph class="config-tip" type="secondary">
                      上传的测试数据仅用于前端演示，可在后端替换为真实 AFLNET/AFL++ 运行结果。
                    </TypographyParagraph>
                  </Space>
                </Spin>
              </Card>

              <Card class="log-card">
                <template #title>
                  <Space>
                    <IconifyIcon icon="ant-design:code-outlined" class="card-icon" />
                    <span>实时日志</span>
                  </Space>
                </template>
                <div class="card-toolbar">
                  <Space size="small">
                    <Button size="small" @click="clearLog">清空</Button>
                    <Button size="small" @click="saveLog" :disabled="!logEntries.length">
                      导出日志
                    </Button>
                    <Button size="small" @click="toggleCrashDetailsView" :disabled="!crashDetails">
                      {{ showCrashDetails ? '收起崩溃详情' : '展开崩溃详情' }}
                    </Button>
                  </Space>
                </div>
                <div ref="logContainer" class="log-panel">
                  <div class="log-empty">测试未开始，请配置参数并点击“开始测试”</div>
                </div>
              </Card>
            </div>

            <div class="live-column">
              <Card class="status-card">
                <template #title>
                  <Space>
                    <IconifyIcon icon="ant-design:dashboard-outlined" class="card-icon" />
                    <span>运行状态</span>
                  </Space>
                </template>
                <Space direction="vertical" size="middle" class="status-content">
                  <Progress :show-info="false" :percent="progressWidth" />
                  <div class="status-metrics">
                    <div class="status-metric">
                      <TypographyText class="status-value">{{ packetCount }}</TypographyText>
                      <TypographyParagraph type="secondary" class="status-label">
                        已发送数据包
                      </TypographyParagraph>
                    </div>
                    <div class="status-metric">
                      <TypographyText class="status-value status-value--success">
                        {{ successCount }}
                      </TypographyText>
                      <TypographyParagraph type="secondary" class="status-label">
                        成功
                      </TypographyParagraph>
                    </div>
                    <div class="status-metric">
                      <TypographyText class="status-value status-value--warning">
                        {{ timeoutCount }}
                      </TypographyText>
                      <TypographyParagraph type="secondary" class="status-label">
                        超时
                      </TypographyParagraph>
                    </div>
                    <div class="status-metric">
                      <TypographyText class="status-value status-value--danger">
                        {{ crashCount }}
                      </TypographyText>
                      <TypographyParagraph type="secondary" class="status-label">
                        崩溃
                      </TypographyParagraph>
                    </div>
                  </div>
                  <Descriptions :column="2" size="small">
                    <Descriptions.Item label="开始时间">{{ startTime || '-' }}</Descriptions.Item>
                    <Descriptions.Item label="结束时间">{{ endTime || '-' }}</Descriptions.Item>
                    <Descriptions.Item label="累计时长">{{ elapsedTime }} 秒</Descriptions.Item>
                    <Descriptions.Item label="当前速率">{{ currentSpeed }} 包/秒</Descriptions.Item>
                    <Descriptions.Item label="计划时长">{{ testDuration }} 秒</Descriptions.Item>
                  </Descriptions>
                  <div class="status-rates">
                    <div>
                      <TypographyText type="secondary">成功率</TypographyText>
                      <TypographyText class="status-rate status-rate--success">
                        {{ successRate }}%
                      </TypographyText>
                    </div>
                    <div>
                      <TypographyText type="secondary">超时率</TypographyText>
                      <TypographyText class="status-rate status-rate--warning">
                        {{ timeoutRate }}%
                      </TypographyText>
                    </div>
                    <div>
                      <TypographyText type="secondary">失败率</TypographyText>
                      <TypographyText class="status-rate status-rate--danger">
                        {{ failedRate }}%
                      </TypographyText>
                    </div>
                  </div>
                </Space>
              </Card>

              <Card class="charts-card">
                <template #title>
                  <Space>
                    <IconifyIcon icon="ant-design:pie-chart-outlined" class="card-icon" />
                    <span>结果分析</span>
                  </Space>
                </template>
                <div class="charts-grid">
                  <div class="chart-panel">
                    <TypographyText type="secondary" class="chart-title">消息类型分布</TypographyText>
                    <div class="chart-container">
                      <canvas ref="messageCanvas"></canvas>
                      <div v-if="!showCharts" class="chart-overlay">
                        <TypographyText type="secondary">等待测试完成以生成图表</TypographyText>
                      </div>
                    </div>
                    <Space size="small" wrap class="chart-tags">
                      <Tag>GET: {{ messageTypeStats.get || 0 }}</Tag>
                      <Tag>SET: {{ messageTypeStats.set || 0 }}</Tag>
                      <Tag>GETNEXT: {{ messageTypeStats.getnext || 0 }}</Tag>
                      <Tag>GETBULK: {{ messageTypeStats.getbulk || 0 }}</Tag>
                    </Space>
                  </div>
                  <div class="chart-panel">
                    <TypographyText type="secondary" class="chart-title">协议版本分布</TypographyText>
                    <div class="chart-container">
                      <canvas ref="versionCanvas"></canvas>
                      <div v-if="!showCharts" class="chart-overlay">
                        <TypographyText type="secondary">等待测试完成以生成图表</TypographyText>
                      </div>
                    </div>
                    <Space size="small" wrap class="chart-tags">
                      <Tag>v1: {{ protocolStats.v1 || 0 }}</Tag>
                      <Tag>v2c: {{ protocolStats.v2c || 0 }}</Tag>
                      <Tag>v3: {{ protocolStats.v3 || 0 }}</Tag>
                    </Space>
                  </div>
                </div>
                <TypographyParagraph type="secondary" class="chart-tip">
                  文件统计：共 {{ fileTotalPackets }} 条 · 成功 {{ fileSuccessCount }} · 超时
                  {{ fileTimeoutCount }} · 失败 {{ fileFailedCount }}
                </TypographyParagraph>
              </Card>

              <Card class="crash-card">
                <template #title>
                  <Space>
                    <IconifyIcon icon="ant-design:alert-outlined" class="card-icon" />
                    <span>崩溃监控</span>
                  </Space>
                </template>
                <template v-if="crashDetails">
                  <Descriptions :column="1" size="small">
                    <Descriptions.Item label="时间">{{ crashDetails.time }}</Descriptions.Item>
                    <Descriptions.Item label="类型">{{ crashDetails.type }}</Descriptions.Item>
                    <Descriptions.Item label="触发数据包">#{{ crashDetails.id }}</Descriptions.Item>
                    <Descriptions.Item label="转储文件">
                      <span class="mono-text">{{ crashDetails.dumpFile }}</span>
                    </Descriptions.Item>
                    <Descriptions.Item label="日志路径">
                      <span class="mono-text">{{ crashDetails.logPath }}</span>
                    </Descriptions.Item>
                  </Descriptions>
                  <TypographyParagraph v-if="showCrashDetails" class="crash-details" type="secondary">
                    <pre>{{ crashDetails.details }}</pre>
                  </TypographyParagraph>
                  <TypographyParagraph v-if="showCrashDetails && crashDetails.packetContent" class="crash-packet" type="secondary">
                    <pre>{{ crashDetails.packetContent }}</pre>
                  </TypographyParagraph>
                </template>
                <template v-else>
                  <Empty description="尚未检测到崩溃" />
                </template>
              </Card>
            </div>
          </div>
        </Tabs.TabPane>

        <Tabs.TabPane key="history" tab="历史记录">
          <Card class="history-card">
            <template #title>
              <Space>
                <IconifyIcon icon="ant-design:database-outlined" class="card-icon" />
                <span>历史结果</span>
              </Space>
            </template>
            <div class="history-toolbar">
              <Space size="small">
                <Button
                  ghost
                  type="primary"
                  :disabled="!historyResults.length"
                  @click="exportAllHistory"
                >
                  导出全部
                </Button>
                <Button
                  danger
                  :disabled="!historyResults.length"
                  @click="clearAllHistory"
                >
                  清空全部
                </Button>
              </Space>
            </div>
            <Table
              :columns="historyColumns"
              :data-source="historyResults"
              :pagination="{ pageSize: 8, showSizeChanger: true }"
              :row-key="(record) => record.id"
              class="history-table"
              size="middle"
            >
              <template #emptyText>
                <Empty description="暂无历史记录" />
              </template>
            </Table>
          </Card>
        </Tabs.TabPane>
      </Tabs>

      <Drawer
        v-model:open="historyDrawerOpen"
        class="history-drawer"
        destroy-on-close
        placement="right"
        title="历史记录详情"
        width="580"
        @close="closeHistoryDrawer"
      >
        <template v-if="selectedHistoryItem">
          <Descriptions :column="1" size="small" bordered>
            <Descriptions.Item label="记录 ID">{{ selectedHistoryItem.id }}</Descriptions.Item>
            <Descriptions.Item label="测试时间">{{ selectedHistoryItem.timestamp }}</Descriptions.Item>
            <Descriptions.Item label="协议">{{ selectedHistoryItem.protocol }}</Descriptions.Item>
            <Descriptions.Item label="引擎">{{ selectedHistoryItem.fuzzEngine }}</Descriptions.Item>
            <Descriptions.Item label="目标">
              {{ selectedHistoryItem.targetHost }}:{{ selectedHistoryItem.targetPort }}
            </Descriptions.Item>
            <Descriptions.Item label="耗时">{{ selectedHistoryItem.duration }} 秒</Descriptions.Item>
            <Descriptions.Item label="总包数">{{ selectedHistoryItem.totalPackets }}</Descriptions.Item>
            <Descriptions.Item label="成功率">{{ selectedHistoryItem.successRate }}%</Descriptions.Item>
            <Descriptions.Item label="崩溃">
              <Tag :color="selectedHistoryItem.hasCrash ? 'error' : 'success'">
                {{ selectedHistoryItem.hasCrash ? '检测到崩溃' : '无' }}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
          <div class="drawer-section">
            <TypographyTitle :level="5">版本分布</TypographyTitle>
            <Space size="small" wrap>
              <Tag>v1: {{ selectedHistoryItem.protocolStats.v1 }}</Tag>
              <Tag>v2c: {{ selectedHistoryItem.protocolStats.v2c }}</Tag>
              <Tag>v3: {{ selectedHistoryItem.protocolStats.v3 }}</Tag>
            </Space>
          </div>
          <div class="drawer-section">
            <TypographyTitle :level="5">消息类型分布</TypographyTitle>
            <Space size="small" wrap>
              <Tag>GET: {{ selectedHistoryItem.messageTypeStats.get }}</Tag>
              <Tag>SET: {{ selectedHistoryItem.messageTypeStats.set }}</Tag>
              <Tag>GETNEXT: {{ selectedHistoryItem.messageTypeStats.getnext }}</Tag>
              <Tag>GETBULK: {{ selectedHistoryItem.messageTypeStats.getbulk }}</Tag>
            </Space>
          </div>
          <div v-if="selectedHistoryItem.hasCrash && selectedHistoryItem.crashDetails" class="drawer-section">
            <TypographyTitle :level="5">崩溃详情</TypographyTitle>
            <TypographyParagraph type="secondary">
              触发数据包：{{ selectedHistoryItem.crashDetails.packetContent }}
            </TypographyParagraph>
            <pre class="drawer-pre">
{{ selectedHistoryItem.crashDetails.details }}
            </pre>
          </div>
        </template>
        <template v-else>
          <Empty description="请选择历史记录查看详细信息" />
        </template>
      </Drawer>
    </div>
  </Page>
</template>


<style scoped>
.fuzz-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.fuzz-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 16px;
}

.live-layout {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  align-items: start;
}

.live-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-icon {
  font-size: 18px;
  color: var(--ant-primary-color);
}

.inline-icon {
  margin-right: 4px;
  font-size: 16px;
}

.config-body {
  width: 100%;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.config-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-tip {
  margin: 0;
  font-size: 12px;
}

.card-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.log-panel {
  min-height: 260px;
  max-height: 360px;
  overflow-y: auto;
  padding: 12px;
  background-color: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border);
  border-radius: var(--ant-border-radius);
  font-family: ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
}

.log-empty {
  color: var(--ant-color-text-tertiary);
  font-style: italic;
}

.log-entry {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px dashed var(--ant-color-border-secondary);
}

.log-entry:last-child {
  border-bottom: none;
}

.log-entry--crash {
  border-bottom-color: var(--ant-color-error);
}

.log-entry--warning {
  border-bottom-color: var(--ant-color-warning);
}

.log-entry__time {
  color: var(--ant-color-text-tertiary);
}

.log-entry__segment {
  color: var(--ant-color-text);
}

.log-entry__protocol {
  color: var(--ant-primary-color);
  font-weight: 500;
}

.log-entry__operation {
  color: var(--ant-color-text-secondary);
}

.log-entry__summary {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-entry__result {
  font-weight: 500;
}

.log-entry__result--success {
  color: var(--ant-color-success);
}

.log-entry__result--warning {
  color: var(--ant-color-warning);
}

.log-entry__result--danger {
  color: var(--ant-color-error);
}

.log-entry__hex {
  color: var(--ant-color-text-quaternary);
}

.status-content {
  width: 100%;
}

.status-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.status-metric {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.status-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--ant-color-text);
}

.status-value--success {
  color: var(--ant-color-success);
}

.status-value--warning {
  color: var(--ant-color-warning);
}

.status-value--danger {
  color: var(--ant-color-error);
}

.status-label {
  margin: 0;
  font-size: 12px;
}

.status-rates {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.status-rate {
  display: block;
  font-size: 18px;
  font-weight: 600;
}

.status-rate--success {
  color: var(--ant-color-success);
}

.status-rate--warning {
  color: var(--ant-color-warning);
}

.status-rate--danger {
  color: var(--ant-color-error);
}

.charts-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chart-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chart-title {
  display: block;
  font-size: 13px;
}

.chart-container {
  position: relative;
  height: 220px;
  background-color: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border);
  border-radius: var(--ant-border-radius);
  padding: 12px;
}

.chart-container canvas {
  width: 100%;
  height: 100%;
}

.chart-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.85));
  border-radius: var(--ant-border-radius);
}

.chart-tags {
  font-size: 12px;
}

.chart-tip {
  margin: 0;
  font-size: 12px;
}

.crash-card .mono-text {
  font-family: ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.crash-details,
.crash-packet {
  margin: 12px 0 0;
  font-size: 12px;
  padding: 12px;
  background-color: var(--ant-color-fill-tertiary);
  border-radius: var(--ant-border-radius);
}

.crash-details pre,
.crash-packet pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.history-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.history-table :deep(.ant-table-cell) {
  white-space: nowrap;
}

.drawer-section {
  margin-top: 16px;
}

.drawer-pre {
  margin: 12px 0 0;
  padding: 12px;
  background-color: var(--ant-color-fill-tertiary);
  border-radius: var(--ant-border-radius);
  font-family: ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 1280px) {
  .live-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .config-grid {
    grid-template-columns: 1fr;
  }

  .status-metrics,
  .status-rates,
  .charts-grid {
    grid-template-columns: 1fr;
  }

  .history-toolbar {
    justify-content: flex-start;
  }
}
</style>
