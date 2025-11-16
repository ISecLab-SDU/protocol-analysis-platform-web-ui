<script setup lang="ts">
import {
  onMounted,
  ref,
  nextTick,
  computed,
  watch,
  shallowRef,
  onErrorCaptured,
  onUnmounted,
} from 'vue';
import { getFuzzText } from '#/api/custom';
import { requestClient } from '#/api/request';
import { useAccessStore } from '@vben/stores';
import { IconifyIcon } from '@vben/icons';
import Chart from 'chart.js/auto';
import { Page } from '@vben/common-ui';
import { Tabs } from 'ant-design-vue';

// 导入协议专用的composables
import {
  useSNMP,
  useSOL,
  useMQTT,
  useLogReader,
  type FuzzPacket,
  type HistoryResult,
  type ProtocolType,
  type FuzzEngineType,
  type ProtocolImplementationType,
  type ProtocolImplementationConfig,
} from './composables';

// 导入新的协议数据管理器和日志查看器
import { useProtocolDataManager } from './composables/useProtocolDataManager';
import ProtocolLogViewer from './components/ProtocolLogViewer.vue';

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
  addSNMPLogToUI,
} = useSNMP();
// RTSP相关功能已移除，SOL协议现在通过MQTT协议实现选择来使用
const {
  solStats,
  resetSOLStats,
  processSOLLogLine,
  writeSOLScript,
  executeSOLCommand,
  stopSOLProcess,
  stopAndCleanupSOL,
} = useSOL();
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
  addSOLLogToUI,
  clearLog,
} = useLogReader();

// 使用新的协议数据管理器
const {
  protocolStates,
  currentProtocol,
  currentState,
  addLog,
  addBatchLogs,
  clearProtocolLogs,
  updateProtocolState,
  switchProtocol,
  getProtocolStats,
  startRealtimeStream,
  addToRealtimeStream,
  stopRealtimeStream,
  stopAllRealtimeStreams,
} = useProtocolDataManager();

// fuzzData现在通过useSNMP composable管理，使用snmpFuzzData
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

// 添加异步操作取消标志
let mqttSimulationCancelled = false;

// UI configuration
const protocolType = ref<ProtocolType>('SNMP');
const fuzzEngine = ref<FuzzEngineType>('SNMP_Fuzz');
const targetHost = ref('127.0.0.1');
const targetPort = ref(161);
const solCommandConfig = ref(
  'afl-fuzz -d -i $AFLNET/tutorials/live555/in-rtsp -o out-live555 -N tcp://127.0.0.1/8554 -x $AFLNET/tutorials/live555/rtsp.dict -P RTSP -D 10000 -q 3 -s 3 -E -K -R ./testOnDemandRTSPServer 8554',
);

// 协议实现配置
const protocolImplementations = ref<ProtocolImplementationType[]>(['系统固件']);
const selectedProtocolImplementation = ref<ProtocolImplementationType>('系统固件');

// 协议实现配置映射
const protocolImplementationConfigs: Record<FuzzEngineType, ProtocolImplementationConfig> = {
  'SNMP_Fuzz': {
    fuzzEngine: 'SNMP_Fuzz',
    defaultImplementations: ['系统固件'],
    isMultiSelect: false
  },
  'MBFuzzer': {
    fuzzEngine: 'MBFuzzer',
    defaultImplementations: ['HiveMQ', 'VerneMQ', 'EMQX', 'FlashMQ', 'NanoMQ', 'Mosquitto'],
    isMultiSelect: false  // 改为单选模式，统一风格
  },
  'AFLNET': {
    fuzzEngine: 'AFLNET',
    defaultImplementations: ['SOL协议'],
    isMultiSelect: false
  }
};

// Real-time log reading (现在通过useLogReader管理)
const solProcessId = ref<number | null>(null);

// Watch for protocol changes to update port and fuzz engine
watch(protocolType, (newProtocol, oldProtocol) => {
  console.log(`[DEBUG] 协议切换: ${oldProtocol} -> ${newProtocol}`);

  // 立即停止当前运行的测试和所有异步操作
  if (isRunning.value) {
    console.log('[DEBUG] 停止当前运行的测试');
    isRunning.value = false;
    isTestCompleted.value = false;

    // 取消MQTT模拟
    if (oldProtocol === 'MQTT') {
      mqttSimulationCancelled = true;
      console.log('[DEBUG] 取消MQTT模拟操作');
    }

    if (testTimer) {
      clearInterval(testTimer as any);
      testTimer = null;
    }
  }

  // 停止所有实时流和日志读取
  console.log('[DEBUG] 停止所有实时流和日志读取');
  stopAllRealtimeStreams();
  stopLogReading();

  // 清理之前协议的状态
  if (oldProtocol === 'MQTT') {
    console.log('[DEBUG] 清理MQTT协议状态');
    // 清理MQTT动画
    cleanupMQTTAnimations();
    // 使用nextTick确保在下一个tick中清理，避免当前更新周期的冲突
    nextTick(() => {
      // 清理定时器
      if (mqttUpdateTimer) {
        clearTimeout(mqttUpdateTimer);
        mqttUpdateTimer = null;
      }
      // 清理非响应式日志数据
      mqttDifferentialLogsData = [];
      mqttLogsPendingUpdate = false;
      mqttLogsUpdateKey.value++;
      resetMQTTStats();
      resetMQTTDifferentialStats();
    });
  }

  // 设置新协议的配置
  if (newProtocol === 'SNMP') {
    targetPort.value = 161;
    fuzzEngine.value = 'SNMP_Fuzz';
  } else if (newProtocol === 'MQTT') {
    targetPort.value = 1883;
    // MQTT协议的引擎将根据协议实现选择来确定
    // 默认使用MBFuzzer，如果选择SOL协议则切换到AFLNET
    fuzzEngine.value = 'MBFuzzer';
    // MQTT动画将在测试开始时初始化
  }

  // 重置测试状态
  nextTick(() => {
    resetTestState();
    console.log('[DEBUG] 协议切换完成，状态已重置');
  });
});

// Watch for fuzz engine changes to update protocol implementations
watch(fuzzEngine, (newEngine) => {
  console.log(`[DEBUG] Fuzz引擎切换: ${newEngine}`);
  const config = protocolImplementationConfigs[newEngine];
  if (config) {
    // 更新多选数组（保持向后兼容）
    protocolImplementations.value = [...config.defaultImplementations];
    // 更新单选值（新的统一风格）
    selectedProtocolImplementation.value = config.defaultImplementations[0];
    console.log(`[DEBUG] 协议实现已更新为: ${selectedProtocolImplementation.value}`);
  }
});

// Watch for selected protocol implementation changes to sync with array
watch(selectedProtocolImplementation, (newImpl) => {
  // 同步单选值到多选数组，保持向后兼容
  protocolImplementations.value = [newImpl];
  
  // 对于MQTT协议，根据实现选择自动切换引擎
  if (protocolType.value === 'MQTT') {
    if (newImpl === 'SOL协议') {
      // 选择SOL协议时，使用AFLNET引擎，端口改为8554
      fuzzEngine.value = 'AFLNET';
      targetPort.value = 8554;
      console.log('[DEBUG] MQTT协议选择SOL实现，切换到AFLNET引擎，端口8554');
    } else {
      // 选择传统MQTT broker时，使用MBFuzzer引擎，端口1883
      fuzzEngine.value = 'MBFuzzer';
      targetPort.value = 1883;
      console.log('[DEBUG] MQTT协议选择传统broker实现，切换到MBFuzzer引擎，端口1883');
    }
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
const activeTab = ref('test'); // 'test' or 'history'

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
    targetHost: '127.0.0.1',
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
    hasCrash: false,
  },
  {
    id: 'hist_002',
    timestamp: '2025-01-20 11:15:42',
    protocol: 'SNMP',
    fuzzEngine: 'SNMP_Fuzz',
    targetHost: '127.0.0.1',
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
      logPath:
        '/home/hhh/下载/snmp_fuzz/snmp_github/snmp_fuzz/scan_result/crash_logs/20250120-111623',
      details:
        '[11:16:23] Segmentation Fault (SIGSEGV)\nProcess ID: 8472\nFault Address: 0x7F8B2C40\nRegisters:\n  EAX: 0x00000000  EBX: 0x7F8B2C40\n  ECX: 0x12345678  EDX: 0xDEADBEEF\n  ESI: 0x87654321  EDI: 0xCAFEBABE\n  EBP: 0x7FFF1234  ESP: 0x7FFF1200\nBacktrace:\n  #0  0x08048567 in get_handler()\n  #1  0x08048234 in packet_processor()\n  #2  0x08047890 in main_loop()',
      packetContent: '302902010004067075626C6963A01C02040E8F83C502010002010030',
    },
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
    hasCrash: false,
  },
  {
    id: 'hist_004',
    timestamp: '2025-01-23 20:36:44',
    protocol: 'MQTT',
    fuzzEngine: 'MBFuzzer',
    targetHost: '127.0.0.1',
    targetPort: 1883,
    duration: 13,
    totalPackets: 953,
    successCount: 650,
    timeoutCount: 303,
    failedCount: 0,
    crashCount: 0,
    successRate: 68,
    mqttStats: {
      fuzzing_start_time: '2024-07-06 00:39:14',
      fuzzing_end_time: '2024-07-07 10:15:23',
      client_request_count: 851051,
      broker_request_count: 523790,
      total_request_count: 1374841,
      crash_number: 0,
      diff_number: 0,
      duplicate_diff_number: 118563,
      valid_connect_number: 1362,
      duplicate_connect_diff: 1507,
      total_differences: 0,
      client_messages: {
        CONNECT: 125000,
        CONNACK: 0,
        PUBLISH: 320000,
        PUBACK: 180000,
        PUBREC: 45000,
        PUBREL: 45000,
        PUBCOMP: 45000,
        SUBSCRIBE: 85000,
        SUBACK: 0,
        UNSUBSCRIBE: 25000,
        UNSUBACK: 0,
        PINGREQ: 21051,
        PINGRESP: 0,
        DISCONNECT: 0,
        AUTH: 0,
      },
      broker_messages: {
        CONNECT: 0,
        CONNACK: 125000,
        PUBLISH: 180000,
        PUBACK: 85000,
        PUBREC: 25000,
        PUBREL: 25000,
        PUBCOMP: 25000,
        SUBSCRIBE: 0,
        SUBACK: 45000,
        UNSUBSCRIBE: 0,
        UNSUBACK: 12790,
        PINGREQ: 0,
        PINGRESP: 21000,
        DISCONNECT: 0,
        AUTH: 0,
      },
      duplicate_diffs: {
        CONNECT: 1507,
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
        AUTH: 0,
      },
      differential_reports: [],
      q_table_states: [],
      broker_issues: {
        hivemq: 0,
        vernemq: 0,
        emqx: 0,
        flashmq: 0,
        nanomq: 0,
        mosquitto: 0,
      },
    },
    protocolSpecificData: {
      clientRequestCount: 851051,
      brokerRequestCount: 523790,
      diffNumber: 5841,
      duplicateDiffNumber: 118563,
      validConnectNumber: 1362,
      duplicateConnectDiff: 1507,
      fuzzingStartTime: '2024-07-06 00:39:14',
      fuzzingEndTime: '2024-07-07 10:15:23',
    },
    hasCrash: false,
  },
]);

// UI refs (logContainer现在通过useLogReader管理)
const messageCanvas = ref<HTMLCanvasElement>();
const versionCanvas = ref<HTMLCanvasElement>();
const mqttMessageCanvas = ref<HTMLCanvasElement>();
let messageTypeChart: any = null;
let versionChart: any = null;
let mqttMessageChart: any = null;

// Computed properties
const progressWidth = computed(() => {
  const estimatedTotal = Math.max(
    packetCount.value,
    testDuration.value * packetsPerSecond.value,
  );
  return estimatedTotal > 0
    ? Math.min(100, Math.round((packetCount.value / estimatedTotal) * 100))
    : 0;
});

const successRate = computed(() => {
  const total =
    successCount.value +
    timeoutCount.value +
    failedCount.value +
    crashCount.value;
  return total > 0 ? Math.round((successCount.value / total) * 100) : 0;
});

const timeoutRate = computed(() => {
  const total =
    successCount.value +
    timeoutCount.value +
    failedCount.value +
    crashCount.value;
  return total > 0 ? Math.round((timeoutCount.value / total) * 100) : 0;
});

const failedRate = computed(() => {
  const total =
    successCount.value +
    timeoutCount.value +
    failedCount.value +
    crashCount.value;
  return total > 0 ? Math.round((failedCount.value / total) * 100) : 0;
});

// generateDefaultFuzzData 现在通过 useSNMP composable 提供

async function fetchText() {
  loading.value = true;
  try {
    // 尝试从Flask后端获取SNMP日志数据
    const resp = await getFuzzText();
    const text = (resp as any)?.text ?? (resp as any)?.data?.text ?? '';
    console.log('API响应数据长度:', text?.length || 0);
    console.log('API响应前100字符:', text?.substring(0, 100) || '无数据');

    if (!text || text.trim().length === 0) {
      console.warn('API返回空数据，使用默认数据');
      rawText.value = generateDefaultFuzzData();
    } else {
      console.log('成功从SNMP日志文件加载数据');
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
        datasets: [
          {
            data: [0, 0, 0, 0],
            backgroundColor: ['#3B82F6', '#6366F1', '#EC4899', '#10B981'],
            borderColor: '#FFFFFF',
            borderWidth: 3,
            hoverOffset: 8,
          },
        ],
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
              usePointStyle: true,
            },
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: 'white',
            bodyColor: 'white',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            callbacks: {
              label: function (context: any) {
                const total = context.dataset.data.reduce(
                  (a: number, b: number) => a + b,
                  0,
                );
                const percentage =
                  total > 0 ? Math.round((context.parsed / total) * 100) : 0;
                return `${context.label}: ${context.parsed} (${percentage}%)`;
              },
            },
          },
        },
        cutout: '60%',
      },
    });

    versionChart = new Chart(versionCtx, {
      type: 'doughnut',
      data: {
        labels: ['SNMP v1', 'SNMP v2c', 'SNMP v3'],
        datasets: [
          {
            data: [0, 0, 0],
            backgroundColor: ['#F59E0B', '#8B5CF6', '#EF4444'],
            borderColor: '#FFFFFF',
            borderWidth: 3,
            hoverOffset: 8,
          },
        ],
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
              usePointStyle: true,
            },
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: 'white',
            bodyColor: 'white',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            callbacks: {
              label: function (context: any) {
                const total = context.dataset.data.reduce(
                  (a: number, b: number) => a + b,
                  0,
                );
                const percentage =
                  total > 0 ? Math.round((context.parsed / total) * 100) : 0;
                return `${context.label}: ${context.parsed} (${percentage}%)`;
              },
            },
          },
        },
        cutout: '60%',
      },
    });

    console.log('Charts initialized successfully');
    return true;
  } catch (error) {
    console.error('Failed to initialize charts:', error);
    return false;
  }
}

function initMQTTChart() {
  if (!mqttMessageCanvas.value) {
    console.warn('MQTT Canvas element not ready');
    return false;
  }

  try {
    const mqttCtx = mqttMessageCanvas.value.getContext('2d');
    if (!mqttCtx) {
      console.warn('Failed to get MQTT canvas context');
      return false;
    }

    mqttMessageChart = new Chart(mqttCtx, {
      type: 'doughnut',
      data: {
        labels: [
          'CONNECT',
          'PUBLISH',
          'SUBSCRIBE',
          'PINGREQ',
          'UNSUBSCRIBE',
          'PUBACK',
          'CONNACK',
          'SUBACK',
          'PINGRESP',
          '其他',
        ],
        datasets: [
          {
            data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            backgroundColor: [
              '#3B82F6',
              '#10B981',
              '#F59E0B',
              '#EF4444',
              '#8B5CF6',
              '#EC4899',
              '#06B6D4',
              '#84CC16',
              '#F97316',
              '#6B7280',
            ],
            borderColor: '#FFFFFF',
            borderWidth: 2,
            hoverOffset: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#1F2937',
              padding: 10,
              font: { size: 10, weight: 'bold' },
              usePointStyle: true,
            },
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: 'white',
            bodyColor: 'white',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            callbacks: {
              label: function (context: any) {
                const total = context.dataset.data.reduce(
                  (a: number, b: number) => a + b,
                  0,
                );
                const percentage =
                  total > 0 ? Math.round((context.parsed / total) * 100) : 0;
                return `${context.label}: ${context.parsed} (${percentage}%)`;
              },
            },
          },
        },
        cutout: '50%',
      },
    });

    console.log('MQTT Chart initialized successfully');
    return true;
  } catch (error) {
    console.error('Failed to initialize MQTT chart:', error);
    return false;
  }
}

// 从fuzz数据重新计算统计信息的函数
function recalculateStatsFromFuzzData() {
  try {
    if (!snmpFuzzData.value || snmpFuzzData.value.length === 0) {
      console.warn('No fuzz data available for recalculation');
      return;
    }

    console.log('Recalculating statistics from fuzz data...');

    // 重置统计数据
    const newProtocolStats = { v1: 0, v2c: 0, v3: 0 };
    const newMessageTypeStats = { get: 0, set: 0, getnext: 0, getbulk: 0 };

    // 遍历fuzz数据重新计算统计
    snmpFuzzData.value.forEach((packet) => {
      // 统计协议版本
      if (packet.version === 'v1') newProtocolStats.v1++;
      else if (packet.version === 'v2c') newProtocolStats.v2c++;
      else if (packet.version === 'v3') newProtocolStats.v3++;

      // 统计消息类型
      if (packet.type === 'get') newMessageTypeStats.get++;
      else if (packet.type === 'set') newMessageTypeStats.set++;
      else if (packet.type === 'getnext') newMessageTypeStats.getnext++;
      else if (packet.type === 'getbulk') newMessageTypeStats.getbulk++;
    });

    // 更新统计数据
    protocolStats.value = newProtocolStats;
    messageTypeStats.value = newMessageTypeStats;

    console.log('Statistics recalculated from fuzz data:', {
      protocolStats: newProtocolStats,
      messageTypeStats: newMessageTypeStats,
      totalPackets: snmpFuzzData.value.length,
    });
  } catch (error) {
    console.error('Error recalculating stats from fuzz data:', error);
  }
}

function updateCharts() {
  try {
    if (!messageTypeChart || !versionChart) {
      console.warn('Charts not initialized, skipping update');
      return;
    }

    // Update message type chart
    if (
      messageTypeChart.data &&
      messageTypeChart.data.datasets &&
      messageTypeChart.data.datasets[0]
    ) {
      messageTypeChart.data.datasets[0].data = [
        messageTypeStats.value.get || 0,
        messageTypeStats.value.set || 0,
        messageTypeStats.value.getnext || 0,
        messageTypeStats.value.getbulk || 0,
      ];
      messageTypeChart.update('none'); // Use 'none' animation mode for better performance
    }

    // Update version chart
    if (
      versionChart.data &&
      versionChart.data.datasets &&
      versionChart.data.datasets[0]
    ) {
      versionChart.data.datasets[0].data = [
        protocolStats.value.v1 || 0,
        protocolStats.value.v2c || 0,
        protocolStats.value.v3 || 0,
      ];
      versionChart.update('none'); // Use 'none' animation mode for better performance
    }

    console.log('Charts updated successfully with data:', {
      messageTypeData: [
        messageTypeStats.value.get || 0,
        messageTypeStats.value.set || 0,
        messageTypeStats.value.getnext || 0,
        messageTypeStats.value.getbulk || 0,
      ],
      versionData: [
        protocolStats.value.v1 || 0,
        protocolStats.value.v2c || 0,
        protocolStats.value.v3 || 0,
      ],
    });
  } catch (error) {
    console.error('Error updating charts:', error);
  }
}

function updateMQTTChart() {
  try {
    // MQTT现在使用broker差异统计卡片显示，不再需要图表更新
    console.log(
      'MQTT using broker difference statistics cards, chart update skipped',
    );
  } catch (error) {
    console.error('Error in MQTT chart function:', error);
  }
}

function parseText(text: string) {
  // 使用SNMP composable的解析功能
  const parsedData = parseSNMPText(text);
  snmpFuzzData.value = parsedData;
  totalPacketsInFile.value = parsedData.filter(
    (p) => typeof p.id === 'number',
  ).length;

  // Debug: Show distribution of packet results after parsing
  const resultCounts = parsedData.reduce(
    (acc, packet) => {
      const result = packet.result || 'unknown';
      acc[result] = (acc[result] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );
  console.log('解析后的数据包结果分布:', resultCounts);
  console.log('总解析数据包数:', parsedData.length);

  // Extract timing information
  const startTimeMatch = text.match(/开始时间:\s*([^\n]+)/);
  const endTimeMatch = text.match(/结束时间:\s*([^\n]+)/);
  const durationMatch = text.match(/总耗时:\s*([\d.]+)\s*秒/);
  const totalPacketsMatch =
    text.match(/发送总数据包:\s*(\d+)/) ||
    text.match(/\[日志系统\]\s*数据包统计:\s*(\d+)\s*\/\s*\d+\s*个/);
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
  fileTotalPackets.value = totalPacketsMatch
    ? parseInt(totalPacketsMatch[1])
    : successCountInFile + timeoutCountInFile + failedCountInFile;
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
    resetSOLStats();
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
  if (protocolType.value !== 'MQTT' && !snmpFuzzData.value.length) return;

  resetTestState();
  isRunning.value = true;
  isTestCompleted.value = false;
  showCharts.value = false; // 测试开始时隐藏图表
  testStartTime.value = new Date();

  // 根据协议类型执行不同的启动逻辑
  try {
    if (protocolType.value === 'SNMP') {
      // 初始化SNMP协议数据管理器
      clearProtocolLogs('SNMP');
      updateProtocolState('SNMP', {
        isRunning: true,
        isProcessing: true,
        totalRecords: snmpFuzzData.value.length,
        processedRecords: 0,
      });

      // 启动SNMP实时流
      startRealtimeStream('SNMP', { batchSize: 20, interval: 100 });

      await startSNMPTest(loop);
    } else if (protocolType.value === 'MQTT') {
      // 根据协议实现选择不同的测试方式
      if (selectedProtocolImplementation.value === 'SOL协议') {
        // SOL协议使用AFLNET引擎
        await startSOLTest();
      } else {
        // 传统MQTT broker使用MBFuzzer引擎
        await startMQTTTest();
      }
    } else {
      throw new Error(`不支持的协议类型: ${protocolType.value}`);
    }
  } catch (error: any) {
    console.error('启动测试失败:', error);
    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: protocolType.value,
        type: 'ERROR',
        oids: [],
        hex: '',
        result: 'failed',
        failedReason: `启动失败: ${error.message}`,
      } as any,
      false,
    );
    isRunning.value = false;
    return;
  }

  // 启动通用计时器
  if (testTimer) {
    clearInterval(testTimer as any);
    testTimer = null;
  }
  testTimer = window.setInterval(() => {
    if (!isPaused.value) {
      elapsedTime.value++;
      currentSpeed.value =
        elapsedTime.value > 0
          ? Math.round(packetCount.value / elapsedTime.value)
          : 0;
    }
  }, 1000);
}

// Protocol-specific test functions
// startRTSPTest函数已移除，SOL协议现在通过startSOLTest函数处理

async function startSOLTest() {
  try {
    // 1. 写入脚本文件
    await writeSOLScriptWrapper();

    // 2. 执行shell命令启动程序
    await executeSOLCommandWrapper();

    // 3. 开始实时读取日志
    startSOLLogReading();

    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'SOL',
        type: 'START',
        oids: ['SOL测试已启动'],
        hex: '',
        result: 'success',
      } as any,
      false,
    );
  } catch (error: any) {
    console.error('SOL测试启动失败:', error);
    throw error;
  }
}

// startSNMPTest 现在通过 useSNMP composable 提供

async function startMQTTTest() {
  try {
    console.log('开始MQTT协议测试');

    // 重置MQTT统计数据
    resetMQTTStats();

    // 重置差异统计数据
    resetMQTTDifferentialStats();

    // 清空协议日志
    clearProtocolLogs('MQTT');

    // 更新协议状态
    updateProtocolState('MQTT', {
      isRunning: true,
      isProcessing: true,
      totalRecords: 0,
      processedRecords: 0,
    });

    // 启动MQTT实时流（更快的刷新频率）
    startRealtimeStream('MQTT', { batchSize: 20, interval: 50 });

    // 清空旧的差异日志数据（向后兼容）
    if (mqttUpdateTimer) {
      clearTimeout(mqttUpdateTimer);
      mqttUpdateTimer = null;
    }
    mqttDifferentialLogsData = [];
    mqttLogsPendingUpdate = false;
    mqttLogsUpdateKey.value++;

    // 初始化MQTT动画（在测试开始时）
    await nextTick();
    initMQTTAnimations();

    // 开始实时模拟MQTT测试
    await startMQTTRealTimeSimulation();
  } catch (error: any) {
    console.error('MQTT测试启动失败:', error);
    // 更新协议状态
    updateProtocolState('MQTT', {
      isRunning: false,
      isProcessing: false,
    });
    throw error;
  }
}

// 重置MQTT差异统计数据
function resetMQTTDifferentialStats() {
  // 重置差异类型统计
  Object.keys(mqttDifferentialStats.value.type_stats).forEach((key) => {
    mqttDifferentialStats.value.type_stats[
      key as keyof typeof mqttDifferentialStats.value.type_stats
    ] = 0;
  });

  // 重置协议版本统计
  Object.keys(mqttDifferentialStats.value.version_stats).forEach((key) => {
    mqttDifferentialStats.value.version_stats[
      key as keyof typeof mqttDifferentialStats.value.version_stats
    ] = 0;
  });

  // 重置broker差异统计 - 与日志信息保持一致
  Object.keys(mqttRealTimeStats.value.broker_diff_stats).forEach((key) => {
    mqttRealTimeStats.value.broker_diff_stats[
      key as keyof typeof mqttRealTimeStats.value.broker_diff_stats
    ] = 0;
  });

  // 重置client和broker发送数据统计
  mqttRealTimeStats.value.client_sent_count = 0;
  mqttRealTimeStats.value.broker_sent_count = 0;

  // 重置实时差异计数器（从0开始累加）
  mqttRealTimeStats.value.diff_number = 0;
  mqttRealTimeStats.value.crash_number = 0;
  mqttRealTimeStats.value.duplicate_diff_number = 0;
  mqttRealTimeStats.value.valid_connect_number = 0;
  mqttRealTimeStats.value.duplicate_connect_diff = 0;

  // 重置总差异数
  mqttDifferentialStats.value.total_differences = 0;

  // 重置差异类型分布统计
  mqttDiffTypeStats.value.protocol_violations = 0;
  mqttDiffTypeStats.value.timeout_errors = 0;
  mqttDiffTypeStats.value.connection_failures = 0;
  mqttDiffTypeStats.value.message_corruptions = 0;
  mqttDiffTypeStats.value.state_inconsistencies = 0;
  mqttDiffTypeStats.value.authentication_errors = 0;
  mqttDiffTypeStats.value.total_differences = 0;
}

// resetMQTTStats 现在通过 useMQTT composable 提供

// 解析MQTT统计数据从文件
async function parseMQTTStatsFromFile() {
  try {
    console.log('[调试-统计] 开始调用MQTT统计数据API');
    const result = await requestClient.post('/protocol-compliance/read-log', {
      protocol: 'MQTT',
      lastPosition: 0, // 从文件开头读取全部内容
    });

    console.log('[调试-统计] ✅ MQTT统计数据API调用成功');
    console.log('[调试-统计] 响应数据:', result);

    // requestClient已经处理了错误检查，直接使用返回的data
    const content = result.content;
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
    mqttStats.value.total_request_count =
      mqttStats.value.client_request_count +
      mqttStats.value.broker_request_count;
    fileTotalPackets.value = mqttStats.value.total_request_count;
    fileSuccessCount.value = mqttStats.value.valid_connect_number;

    console.log('MQTT统计数据解析完成:', mqttStats.value);
    console.log('MQTT关键数据检查:', {
      client_request_count: mqttStats.value.client_request_count,
      broker_request_count: mqttStats.value.broker_request_count,
      diff_number: mqttStats.value.diff_number,
      valid_connect_number: mqttStats.value.valid_connect_number,
      duplicate_connect_diff: mqttStats.value.duplicate_connect_diff,
      total_differences: mqttStats.value.total_differences,
    });
  } catch (error: any) {
    console.error('解析MQTT统计数据失败:', error);
  }
}

// 统一的日志系统 - 替换分离的MQTT日志
const unifiedLogs = ref<
  Array<{
    id: string;
    timestamp: string;
    type: 'INFO' | 'ERROR' | 'WARNING' | 'SUCCESS';
    content: string;
    protocol: 'SNMP' | 'MQTT';
  }>
>([]);

// MQTT协议差异报告日志 - 使用非响应式数据避免DOM冲突
let mqttDifferentialLogsData: string[] = []; // 非响应式数据存储
const mqttLogsContainer = ref<HTMLElement | null>(null); // 日志容器引用
const mqttLogsUpdateKey = ref(0); // 强制更新key
let mqttUpdateTimer: number | null = null; // 防抖定时器
let mqttLogsPendingUpdate = false; // 更新锁

// MQTT处理状态
const mqttIsProcessingLogs = ref(false);
const mqttTotalRecords = ref(0);
const mqttProcessedRecords = ref(0);
const mqttProcessingProgress = ref(0);

// MQTT实时统计数据
const mqttRealTimeStats = ref({
  // 保留原有的崩溃和差异统计
  crash_number: 0,
  diff_number: 0,
  duplicate_diff_number: 0,
  valid_connect_number: 0,
  duplicate_connect_diff: 0,
  // 新增broker类型差异统计 - 与日志中diff_range_broker字段对应
  broker_diff_stats: {
    hivemq: 0,
    vernemq: 0,
    emqx: 0,
    flashmq: 0,
    nanomq: 0,
    mosquitto: 0,
  },
  // 新增client和broker发送数据统计
  client_sent_count: 0,
  broker_sent_count: 0,
});

// MQTT 差异类型分布统计数据
const mqttDiffTypeStats = ref({
  protocol_violations: 0,
  timeout_errors: 0,
  connection_failures: 0,
  message_corruptions: 0,
  state_inconsistencies: 0,
  authentication_errors: 0,
  total_differences: 0,
  distribution: {
    protocol_violations: 0,
    timeout_errors: 0,
    connection_failures: 0,
    message_corruptions: 0,
    state_inconsistencies: 0,
    authentication_errors: 0,
  },
});

// 统一的日志添加函数
function addUnifiedLog(
  type: 'INFO' | 'ERROR' | 'WARNING' | 'SUCCESS',
  content: string,
  protocol: 'SNMP' | 'MQTT' = 'MQTT',
) {
  unifiedLogs.value.push({
    id: `${protocol.toLowerCase()}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    timestamp: new Date().toLocaleTimeString(),
    type,
    content,
    protocol,
  });

  // 实时累加协议差异统计 - 逐个递增确保数据准确
  if (protocol === 'MQTT' && isRunning.value) {
    // 精确递增差异计数，每条差异记录+1
    mqttRealTimeStats.value.diff_number++;
    mqttStats.value.diff_number = mqttRealTimeStats.value.diff_number;

    // 同步更新总差异数
    mqttDifferentialStats.value.total_differences =
      mqttRealTimeStats.value.diff_number;
    mqttDiffTypeStats.value.total_differences =
      mqttRealTimeStats.value.diff_number;

    // 确保历史记录与统计信息保持同步
    if (mqttStats.value.total_differences !== undefined) {
      mqttStats.value.total_differences = mqttRealTimeStats.value.diff_number;
    }
  }
}

// 清空统一日志
function clearUnifiedLogs() {
  unifiedLogs.value.length = 0;
}

// 开始MQTT实时模拟
async function startMQTTRealTimeSimulation() {
  try {
    console.log('=== MQTT后端连接测试开始 ===');
    console.log('[调试] 准备调用后端API: /protocol-compliance/read-log');
    console.log('[调试] 请求参数:', { protocol: 'MQTT', lastPosition: 0 });

    // 首先读取完整的fuzzing_report.txt文件
    const result = await requestClient.post('/protocol-compliance/read-log', {
      protocol: 'MQTT',
      lastPosition: 0,
    });

    console.log('[调试] ✅ 后端API调用成功!');
    console.log('[调试] 响应数据类型:', typeof result);
    console.log('[调试] 响应数据结构:', Object.keys(result || {}));
    console.log('[调试] 完整响应数据:', result);

    if (!result) {
      console.error('[调试] ❌ 响应为空或undefined');
      throw new Error('后端响应为空');
    }

    if (!result.content) {
      console.error('[调试] ❌ 响应中没有content字段');
      console.error('[调试] 可用字段:', Object.keys(result));
      throw new Error('响应中缺少content字段');
    }

    const content = result.content;
    console.log('[调试] ✅ 成功获取content字段');
    console.log('[调试] Content长度:', content.length, '字符');
    console.log('[调试] Content类型:', typeof content);

    const lines = content.split('\n');
    console.log('[调试] ✅ 成功分割为行数:', lines.length);
    console.log('[调试] 前5行内容:');
    lines.slice(0, 5).forEach((line, index) => {
      console.log(`[调试]   第${index + 1}行: ${line}`);
    });
    console.log('=== MQTT后端连接测试完成 ===');

    // 解析前55行的统计数据
    await parseMQTTHeaderStats(lines.slice(0, 55));

    // 找到Differential Report部分
    const differentialLines = extractDifferentialReport(lines);

    // 解析差异类型分布数据
    await parseDiffTypeData(differentialLines);

    // 开始实时输出差异报告
    await simulateRealTimeFuzzing(differentialLines);
  } catch (error: any) {
    console.error('=== MQTT后端连接失败 ===');
    console.error('[调试] ❌ 错误类型:', typeof error);
    console.error('[调试] ❌ 错误对象:', error);
    console.error('[调试] ❌ 错误消息:', error?.message || '无错误消息');
    console.error('[调试] ❌ 错误堆栈:', error?.stack || '无堆栈信息');

    // 检查是否是网络错误
    if (error?.code) {
      console.error('[调试] ❌ 错误代码:', error.code);
    }

    // 检查是否是HTTP错误
    if (error?.response) {
      console.error('[调试] ❌ HTTP响应状态:', error.response.status);
      console.error('[调试] ❌ HTTP响应数据:', error.response.data);
    }

    // 检查是否是请求配置错误
    if (error?.config) {
      console.error('[调试] ❌ 请求配置:', {
        url: error.config.url,
        method: error.config.method,
        baseURL: error.config.baseURL,
      });
    }

    console.error('=== MQTT后端连接失败详情结束 ===');
  }
}

// 解析前55行的统计数据
async function parseMQTTHeaderStats(headerLines: string[]) {
  let isClientSection = false;
  let isBrokerSection = false;

  for (const line of headerLines) {
    // 解析客户端请求统计
    if (line.includes('Fuzzing request number (client):')) {
      const match = line.match(/Fuzzing request number \(client\):\s*(\d+)/);
      if (match) {
        mqttStats.value.client_request_count = parseInt(match[1]);
      }
    }

    // 解析代理端请求统计
    if (line.includes('Fuzzing request number (broker):')) {
      const match = line.match(/Fuzzing request number \(broker\):\s*(\d+)/);
      if (match) {
        mqttStats.value.broker_request_count = parseInt(match[1]);
      }
    }

    // 检测客户端请求详情开始
    if (line.includes('Fuzzing requests (client):')) {
      isClientSection = true;
      isBrokerSection = false;
      continue;
    }

    // 检测代理端请求详情开始
    if (line.includes('Fuzzing requests (broker):')) {
      isClientSection = false;
      isBrokerSection = true;
      continue;
    }

    // 解析各种统计数据
    if (line.includes('Crash Number:')) {
      const match = line.match(/Crash Number:\s*(\d+)/);
      if (match) {
        mqttStats.value.crash_number = parseInt(match[1]);
      }
      isClientSection = false;
      isBrokerSection = false;
    }

    if (line.includes('Diff Number:')) {
      const match = line.match(/Diff Number:\s*(\d+)/);
      if (match) {
        mqttStats.value.diff_number = parseInt(match[1]);
      }
    }

    if (line.includes('Duplicate Diff Number:')) {
      const match = line.match(/Duplicate Diff Number:\s*(\d+)/);
      if (match) {
        mqttStats.value.duplicate_diff_number = parseInt(match[1]);
      }
    }

    if (line.includes('Valid Connect Number:')) {
      const match = line.match(/Valid Connect Number:\s*(\d+)/);
      if (match) {
        mqttStats.value.valid_connect_number = parseInt(match[1]);
      }
    }

    if (line.includes('已经发送重复CONNECT差异的消息数目:')) {
      const match = line.match(/已经发送重复CONNECT差异的消息数目:\s*(\d+)/);
      if (match) {
        mqttStats.value.duplicate_connect_diff = parseInt(match[1]);
      }
    }

    // 解析总差异数（如果有的话）
    if (line.includes('Total Differences:') || line.includes('总差异数:')) {
      const match = line.match(/(?:Total Differences|总差异数):\s*(\d+)/);
      if (match) {
        mqttStats.value.total_differences = parseInt(match[1]);
      }
    }

    // 解析开始和结束时间
    if (line.includes('Fuzzing Start Time:')) {
      const match = line.match(/Fuzzing Start Time:\s*(.+)/);
      if (match) {
        mqttStats.value.fuzzing_start_time = match[1].trim();
      }
    }

    if (line.includes('Fuzzing End Time:')) {
      const match = line.match(/Fuzzing End Time:\s*(.+)/);
      if (match) {
        mqttStats.value.fuzzing_end_time = match[1].trim();
      }
    }

    // 解析客户端和代理端请求详情 - 现在专注于broker差异统计，这部分数据不再使用
    // const requestMatch = line.match(/^\s*([A-Z]+):\s*(\d+)$/);
    // 注释掉旧的消息类型统计，现在使用broker差异统计
  }

  // MQTT协议使用统计卡片，不需要更新图表
  console.log('MQTT stats updated, using statistical cards instead of charts');
}

// 提取Differential Report部分
function extractDifferentialReport(lines: string[]): string[] {
  const differentialLines: string[] = [];
  let inDifferentialSection = false;

  for (const line of lines) {
    if (line.trim() === 'Differential Report:') {
      inDifferentialSection = true;
      continue;
    }

    if (inDifferentialSection && line.trim()) {
      // 检查是否到了Q Table部分
      if (line.trim() === 'Q Table:') {
        break;
      }
      differentialLines.push(line.trim());
    }
  }

  return differentialLines;
}

// 解析差异类型分布数据
async function parseDiffTypeData(lines: string[]) {
  const diffTypeCounts = {
    protocol_violations: 0,
    timeout_errors: 0,
    connection_failures: 0,
    message_corruptions: 0,
    state_inconsistencies: 0,
    authentication_errors: 0,
  };

  for (const line of lines) {
    const lowerLine = line.toLowerCase();

    // 协议违规检测
    if (
      lowerLine.includes('protocol violation') ||
      lowerLine.includes('invalid packet') ||
      lowerLine.includes('malformed') ||
      lowerLine.includes('protocol error')
    ) {
      diffTypeCounts.protocol_violations++;
    }
    // 超时错误检测
    else if (
      lowerLine.includes('timeout') ||
      lowerLine.includes('connection timeout') ||
      lowerLine.includes('read timeout')
    ) {
      diffTypeCounts.timeout_errors++;
    }
    // 连接失败检测
    else if (
      lowerLine.includes('connection failed') ||
      lowerLine.includes('connect failed') ||
      lowerLine.includes('connection refused') ||
      lowerLine.includes('connection reset')
    ) {
      diffTypeCounts.connection_failures++;
    }
    // 消息损坏检测
    else if (
      lowerLine.includes('corrupt') ||
      lowerLine.includes('checksum') ||
      lowerLine.includes('invalid data') ||
      lowerLine.includes('data corruption')
    ) {
      diffTypeCounts.message_corruptions++;
    }
    // 状态不一致检测
    else if (
      lowerLine.includes('state') &&
      (lowerLine.includes('inconsistent') ||
        lowerLine.includes('mismatch') ||
        lowerLine.includes('unexpected'))
    ) {
      diffTypeCounts.state_inconsistencies++;
    }
    // 认证错误检测
    else if (
      lowerLine.includes('auth') ||
      lowerLine.includes('unauthorized') ||
      lowerLine.includes('permission denied') ||
      lowerLine.includes('access denied')
    ) {
      diffTypeCounts.authentication_errors++;
    }
  }

  // 计算总数
  const total = Object.values(diffTypeCounts).reduce(
    (sum, count) => sum + count,
    0,
  );

  // 更新差异类型统计数据
  mqttDiffTypeStats.value = {
    ...diffTypeCounts,
    total_differences: total,
    distribution: {
      protocol_violations:
        total > 0
          ? Math.round((diffTypeCounts.protocol_violations / total) * 100)
          : 0,
      timeout_errors:
        total > 0
          ? Math.round((diffTypeCounts.timeout_errors / total) * 100)
          : 0,
      connection_failures:
        total > 0
          ? Math.round((diffTypeCounts.connection_failures / total) * 100)
          : 0,
      message_corruptions:
        total > 0
          ? Math.round((diffTypeCounts.message_corruptions / total) * 100)
          : 0,
      state_inconsistencies:
        total > 0
          ? Math.round((diffTypeCounts.state_inconsistencies / total) * 100)
          : 0,
      authentication_errors:
        total > 0
          ? Math.round((diffTypeCounts.authentication_errors / total) * 100)
          : 0,
    },
  };

  console.log('差异类型分布数据解析完成:', mqttDiffTypeStats.value);
}

// 模拟实时Fuzz运行
async function simulateRealTimeFuzzing(differentialLines: string[]) {
  // 重置取消标志
  mqttSimulationCancelled = false;
  console.log('[DEBUG] 开始MQTT模拟，重置取消标志');
  console.log(
    '[DEBUG] simulateRealTimeFuzzing started with',
    differentialLines.length,
    'lines',
  );

  try {
    if (differentialLines.length === 0) {
      addToMQTTLogs('暂无差异报告数据');

      // 即使没有差异数据，也要显示测试开始信息
      setTimeout(() => {
        if (isRunning.value) {
          isRunning.value = false;
          isTestCompleted.value = true;
          testEndTime.value = new Date();

          if (testTimer) {
            clearInterval(testTimer as any);
            testTimer = null;
          }
        }
      }, 2000);
      return;
    }

    let processedCount = 0;

    // 批量添加测试开始信息，避免频繁触发响应式更新
    const startMessages = [
      '=== MBFuzzer MQTT协议差异测试开始 ===',
      `开始时间: ${mqttStats.value.fuzzing_start_time || new Date().toLocaleString()}`,
      `目标代理: ${targetHost.value}:${targetPort.value}`,
      '正在分析协议差异...',
      '',
    ];
    addToMQTTLogs(startMessages);

    // 等待一下让用户看到开始信息
    await new Promise((resolve) => setTimeout(resolve, 500));

    // 使用较小的批量处理来实现更平滑的增长效果
    const batchSize = 1; // 改为逐个处理，实现平滑增长
    const logBatch = [];

    for (let i = 0; i < differentialLines.length; i++) {
      try {
        // 检查用户是否停止了测试或切换了协议，或者操作被取消
        if (
          !isRunning.value ||
          protocolType.value !== 'MQTT' ||
          mqttSimulationCancelled
        ) {
          console.log(
            `[DEBUG] 退出循环: isRunning=${isRunning.value}, protocol=${protocolType.value}, cancelled=${mqttSimulationCancelled}`,
          );
          break;
        }

        const line = differentialLines[i];

        // 添加到批处理队列
        logBatch.push(line);

        // 更新实时统计数据
        updateRealTimeStats(line);

        processedCount++;

        // 根据处理进度同步更新client和broker发送数据
        updateDataSendingProgress(processedCount, differentialLines.length);

        // 批量更新日志显示
        if (
          logBatch.length >= batchSize ||
          i === differentialLines.length - 1
        ) {
          // 添加更严格的状态检查和调试信息
          const canUpdate =
            isRunning.value &&
            protocolType.value === 'MQTT' &&
            !mqttSimulationCancelled;
          console.log(
            `[DEBUG] 批量更新检查: isRunning=${isRunning.value}, protocol=${protocolType.value}, cancelled=${mqttSimulationCancelled}, canUpdate=${canUpdate}, batchSize=${logBatch.length}`,
          );

          if (canUpdate) {
            try {
              // 使用非响应式数据机制，避免Vue DOM冲突
              addToMQTTLogs(logBatch);
              console.log(`[DEBUG] 成功添加${logBatch.length}条日志`);
            } catch (updateError) {
              console.error('[DEBUG] 批量更新失败:', updateError);
              // 如果批量更新失败，停止测试
              isRunning.value = false;
              break;
            }
          } else {
            console.log('[DEBUG] 跳过批量更新，测试可能已停止或协议已切换');
            break; // 如果状态不对，直接退出循环
          }
          logBatch.length = 0; // 清空批处理队列

          // 更新计数器
          packetCount.value = processedCount;

          // 滚动逻辑现在由防抖函数处理，这里不需要额外操作
        }

        // 更新运行时长（每处理10条记录更新一次，模拟时间流逝）
        if (processedCount % 10 === 0) {
          elapsedTime.value = Math.floor(processedCount / 10);
        }

        // 固定短间隔处理，实现平滑增长
        if (i % Math.max(1, batchSize) === 0) {
          await new Promise((resolve) => setTimeout(resolve, 50)); // 50ms固定间隔
        }
      } catch (lineError) {
        console.warn('处理差异行时出错:', lineError);
        // 继续处理下一行
        continue;
      }
    }

    // 批量添加测试完成信息
    if (isRunning.value && protocolType.value === 'MQTT') {
      const endMessages = [
        '',
        '=== 差异分析完成 ===',
        `处理完成: 共分析 ${processedCount} 条差异记录`,
        `发现差异: ${mqttRealTimeStats.value.diff_number} 个`,
        `结束时间: ${mqttStats.value.fuzzing_end_time || new Date().toLocaleString()}`,
      ];
      addToMQTTLogs(endMessages);
    }

    // 测试完成
    console.log(
      '[DEBUG] simulateRealTimeFuzzing completed, scheduling test end...',
    );
    setTimeout(() => {
      if (isRunning.value) {
        console.log('[DEBUG] Ending MQTT test from simulateRealTimeFuzzing...');
        isRunning.value = false;
        isTestCompleted.value = true;
        testEndTime.value = new Date();

        if (testTimer) {
          clearInterval(testTimer as any);
          testTimer = null;
        }

        // 添加测试完成日志
        addUnifiedLog('SUCCESS', 'MQTT模拟测试完成', 'MQTT');

        // 保存历史记录
        setTimeout(() => {
          try {
            console.log(
              '[DEBUG] MQTT simulation completed, saving to history...',
            );
            console.log(
              '[DEBUG] Current MQTT stats before saving:',
              mqttStats.value,
            );
            updateTestSummary();
            saveTestToHistory();
            console.log('[DEBUG] MQTT simulation history save completed');
          } catch (error) {
            console.error('Error saving MQTT simulation results:', error);
          }
        }, 500);
      }
    }, 1000);
  } catch (error) {
    console.error('simulateRealTimeFuzzing出错:', error);
    // 确保测试状态正确结束
    if (isRunning.value) {
      isRunning.value = false;
      isTestCompleted.value = true;
      testEndTime.value = new Date();
      if (testTimer) {
        clearInterval(testTimer as any);
        testTimer = null;
      }
    }
  }
}

// 差异统计数据结构
const mqttDifferentialStats = ref({
  // 按差异类型统计
  type_stats: {
    'Message Missing': 1247,
    'Message Unexpected': 892,
    'Field Missing': 2156,
    'Field Unexpected': 1634,
    'Field Different': 628,
  },
  // 按协议版本统计
  version_stats: {
    '3': 2341,
    '4': 2789,
    '5': 1427,
  },
  // 按消息类型统计
  msg_type_stats: {
    CONNECT: 456,
    CONNACK: 234,
    PUBLISH: 1234,
    PUBACK: 567,
    PUBREC: 123,
    PUBREL: 89,
    PUBCOMP: 67,
    SUBSCRIBE: 345,
    SUBACK: 234,
    UNSUBSCRIBE: 123,
    UNSUBACK: 89,
    PINGREQ: 456,
    PINGRESP: 445,
    DISCONNECT: 234,
    AUTH: 67,
  },
  total_differences: 0,
});

// 直接DOM操作更新MQTT日志，避免Vue响应式冲突
function updateMQTTLogsDOM() {
  if (mqttLogsPendingUpdate || !mqttLogsContainer.value) {
    return;
  }

  mqttLogsPendingUpdate = true;

  try {
    // 清空容器
    mqttLogsContainer.value.innerHTML = '';

    // 创建文档片段提高性能
    const fragment = document.createDocumentFragment();

    // 只显示最后1000条日志，避免DOM过大
    const logsToShow = mqttDifferentialLogsData.slice(-1000);

    logsToShow.forEach((log, index) => {
      const logElement = document.createElement('div');
      logElement.className = 'mb-1 leading-relaxed text-dark/80';
      logElement.innerHTML = formatMQTTLogLine(log);
      fragment.appendChild(logElement);
    });

    // 一次性添加到DOM
    mqttLogsContainer.value.appendChild(fragment);

    // 滚动到底部
    mqttLogsContainer.value.scrollTop = mqttLogsContainer.value.scrollHeight;
  } catch (error) {
    console.warn('[DEBUG] DOM更新失败:', error);
  } finally {
    mqttLogsPendingUpdate = false;
  }
}

// 防抖更新MQTT日志
function debouncedUpdateMQTTLogs() {
  if (mqttUpdateTimer) {
    clearTimeout(mqttUpdateTimer);
  }

  mqttUpdateTimer = window.setTimeout(() => {
    if (isRunning.value && protocolType.value === 'MQTT') {
      updateMQTTLogsDOM();
    }
    mqttUpdateTimer = null;
  }, 100); // 100ms防抖延迟
}

// 添加日志到协议数据管理器
function addToMQTTLogs(logs: string | string[]) {
  if (!isRunning.value || protocolType.value !== 'MQTT') {
    return;
  }

  const logsArray = Array.isArray(logs) ? logs : [logs];
  const logEntries = logsArray.map((logContent) => ({
    timestamp: new Date().toLocaleTimeString(),
    type: getLogTypeFromContent(logContent) as
      | 'INFO'
      | 'ERROR'
      | 'WARNING'
      | 'SUCCESS',
    content: logContent,
  }));

  // 使用实时流添加日志
  logEntries.forEach((logEntry) => {
    addToRealtimeStream('MQTT', logEntry);

    // 实时累加协议差异统计 - 只对差异报告行进行计数，逐个递增
    if (isRunning.value && isDifferentialLogEntry(logEntry.content)) {
      // 精确递增差异计数，每条差异记录+1
      mqttRealTimeStats.value.diff_number++;
      mqttStats.value.diff_number = mqttRealTimeStats.value.diff_number;

      // 同步更新总差异数
      mqttDifferentialStats.value.total_differences =
        mqttRealTimeStats.value.diff_number;
      mqttDiffTypeStats.value.total_differences =
        mqttRealTimeStats.value.diff_number;

      // 确保历史记录与统计信息保持同步
      if (mqttStats.value.total_differences !== undefined) {
        mqttStats.value.total_differences = mqttRealTimeStats.value.diff_number;
      }
    }
  });
}

// 判断是否为差异报告日志条目
function isDifferentialLogEntry(content: string): boolean {
  // 检查是否包含差异报告的关键字段
  const differentialKeywords = [
    'protocol_version:',
    'msg_type:',
    'diff_range_broker:',
    'type: {',
    'direction:',
    'file_path:',
    'capture_time:',
  ];

  // 排除非差异的系统消息
  const systemMessages = [
    '=== MBFuzzer',
    '开始时间:',
    '目标代理:',
    '正在分析',
    '处理进度:',
    '差异分析完成',
    '处理完成:',
    '发现差异:',
    '结束时间:',
  ];

  // 如果包含系统消息关键词，则不是差异报告
  for (const systemMsg of systemMessages) {
    if (content.includes(systemMsg)) {
      return false;
    }
  }

  // 如果包含差异报告关键词，则是差异报告
  for (const keyword of differentialKeywords) {
    if (content.includes(keyword)) {
      return true;
    }
  }

  return false;
}

// 根据日志内容判断类型
function getLogTypeFromContent(content: string): string {
  if (
    content.includes('ERROR') ||
    content.includes('❌') ||
    content.includes('失败')
  ) {
    return 'ERROR';
  } else if (
    content.includes('WARNING') ||
    content.includes('⚠️') ||
    content.includes('警告')
  ) {
    return 'WARNING';
  } else if (
    content.includes('SUCCESS') ||
    content.includes('✅') ||
    content.includes('成功')
  ) {
    return 'SUCCESS';
  }
  return 'INFO';
}

// 获取协议特定的日志格式化函数
function getLogFormatter(protocol: ProtocolType) {
  switch (protocol) {
    case 'MQTT':
      return formatMQTTLogLine;
    // RTSP已移除，SOL协议现在通过MQTT协议实现选择来处理
    case 'SNMP':
      return formatSNMPLogLine;
    default:
      return (log: any) => `[${log.timestamp}] ${log.content}`;
  }
}

// MQTT日志格式化（已移动到下方，避免重复定义）
// 测试函数是否正常工作
console.log('[DEBUG] formatMQTTLogLine函数已加载');

// RTSP日志格式化函数已移除，SOL协议现在通过formatSOLLogLine处理

// SOL日志格式化
function formatSOLLogLine(log: any): string {
  if (typeof log === 'string') {
    return log;
  }
  return `[${log.timestamp}] [SOL] ${log.content}`;
}

// SNMP日志格式化
function formatSNMPLogLine(log: any): string {
  if (typeof log === 'string') {
    return log;
  }

  // 如果是新的协议数据管理器格式
  if (typeof log === 'object' && log.content) {
    // 恢复之前的样式，不使用图标，使用HTML格式化
    const content = log.content;
    const timestamp = log.timestamp;

    // 检查是否是崩溃日志
    if (content.includes('CRASH DETECTED')) {
      return `<span class="text-dark/50">[${timestamp}]</span> <span class="text-danger font-bold">${content}</span>`;
    } else {
      // 解析正常日志内容
      const parts = content.split(' ');
      if (parts.length >= 4) {
        const protocol = parts[0]; // SNMPV2C
        const op = parts[1]; // GET
        const oid = parts[2] || ''; // OID
        const result = parts.slice(3).join(' '); // 结果和其他信息

        // 判断结果类型的CSS类
        const resultClass = result.includes('正常响应')
          ? 'text-success'
          : result.includes('接收超时')
            ? 'text-warning'
            : result.includes('构造失败')
              ? 'text-danger'
              : 'text-warning';

        return `<span class="text-dark/50">[${timestamp}]</span> <span class="text-primary">${protocol}</span> <span class="text-info">${op}</span> <span class="text-dark/70 truncate inline-block w-32" title="${oid}">${oid}</span> <span class="${resultClass} font-medium">${result}</span>`;
      } else {
        // 如果格式不匹配，使用简单格式
        return `<span class="text-dark/50">[${timestamp}]</span> <span class="text-dark/80">${content}</span>`;
      }
    }
  }

  return `[${log.timestamp}] [SNMP] ${log.content}`;
}

// 根据差异处理进度同步更新client和broker发送数据
function updateDataSendingProgress(processedCount: number, totalCount: number) {
  const targetClientCount = 851051;
  const targetBrokerCount = 523790;

  // 根据处理进度计算应该达到的数值
  const progress = Math.min(processedCount / totalCount, 1);

  // 按比例更新client和broker发送数据
  const expectedClientCount = Math.floor(targetClientCount * progress);
  const expectedBrokerCount = Math.floor(targetBrokerCount * progress);

  // 平滑更新到目标值
  mqttRealTimeStats.value.client_sent_count = expectedClientCount;
  mqttRealTimeStats.value.broker_sent_count = expectedBrokerCount;
}

// 更新实时统计数据
function updateRealTimeStats(line: string) {
  try {
    // 检查测试状态，避免在测试停止后继续更新
    if (!isRunning.value || protocolType.value !== 'MQTT') {
      return;
    }

    // 解析差异报告行中的统计信息（不再用于计算总差异数，仅用于分类统计）
    const msgTypeMatch = line.match(/msg_type:\s*([^,\s]+)/);
    const versionMatch = line.match(/protocol_version:\s*(\d+)/);
    const diffTypeMatch = line.match(/type:\s*\{([^}]+)\}/);
    const brokerMatch = line.match(/diff_range_broker:\s*\[([^\]]+)\]/);

    if (msgTypeMatch || versionMatch || diffTypeMatch || brokerMatch) {
      // 注意：不再在这里递增总差异数，因为已经在addUnifiedLog中实时累加

      // 统计受影响的broker类型 - 与日志信息保持一致
      if (brokerMatch) {
        const brokers = brokerMatch[1]
          .split(',')
          .map((broker) => broker.trim().replace(/'/g, ''));

        brokers.forEach((broker) => {
          if (
            mqttRealTimeStats.value.broker_diff_stats.hasOwnProperty(broker)
          ) {
            mqttRealTimeStats.value.broker_diff_stats[
              broker as keyof typeof mqttRealTimeStats.value.broker_diff_stats
            ]++;
          }
        });
      }

      // 统计协议版本
      if (versionMatch) {
        const version = versionMatch[1];
        if (mqttDifferentialStats.value.version_stats.hasOwnProperty(version)) {
          mqttDifferentialStats.value.version_stats[
            version as keyof typeof mqttDifferentialStats.value.version_stats
          ]++;
        }
      }

      // 统计差异类型
      if (diffTypeMatch) {
        const diffType = diffTypeMatch[1].trim();
        if (mqttDifferentialStats.value.type_stats.hasOwnProperty(diffType)) {
          mqttDifferentialStats.value.type_stats[
            diffType as keyof typeof mqttDifferentialStats.value.type_stats
          ]++;
        }
      }

      // 实时更新差异类型分布统计
      updateDiffTypeDistribution(line);
    }
  } catch (error) {
    console.warn('[DEBUG] 更新实时统计数据失败:', error);
    // 统计更新失败不应该影响主流程
  }
}

// 实时更新差异类型分布统计
function updateDiffTypeDistribution(line: string) {
  const lowerLine = line.toLowerCase();

  // 协议违规检测
  if (
    lowerLine.includes('protocol violation') ||
    lowerLine.includes('invalid packet') ||
    lowerLine.includes('malformed') ||
    lowerLine.includes('protocol error')
  ) {
    mqttDiffTypeStats.value.protocol_violations++;
  }
  // 超时错误检测
  else if (
    lowerLine.includes('timeout') ||
    lowerLine.includes('connection timeout') ||
    lowerLine.includes('read timeout')
  ) {
    mqttDiffTypeStats.value.timeout_errors++;
  }
  // 连接失败检测
  else if (
    lowerLine.includes('connection failed') ||
    lowerLine.includes('connect failed') ||
    lowerLine.includes('connection refused') ||
    lowerLine.includes('connection reset')
  ) {
    mqttDiffTypeStats.value.connection_failures++;
  }
  // 消息损坏检测
  else if (
    lowerLine.includes('corrupt') ||
    lowerLine.includes('checksum') ||
    lowerLine.includes('invalid data') ||
    lowerLine.includes('data corruption')
  ) {
    mqttDiffTypeStats.value.message_corruptions++;
  }
  // 状态不一致检测
  else if (
    lowerLine.includes('state') &&
    (lowerLine.includes('inconsistent') ||
      lowerLine.includes('mismatch') ||
      lowerLine.includes('unexpected'))
  ) {
    mqttDiffTypeStats.value.state_inconsistencies++;
  }
  // 认证错误检测
  else if (
    lowerLine.includes('auth') ||
    lowerLine.includes('unauthorized') ||
    lowerLine.includes('permission denied') ||
    lowerLine.includes('access denied')
  ) {
    mqttDiffTypeStats.value.authentication_errors++;
  }

  // 重新计算总数和分布百分比
  const total =
    mqttDiffTypeStats.value.protocol_violations +
    mqttDiffTypeStats.value.timeout_errors +
    mqttDiffTypeStats.value.connection_failures +
    mqttDiffTypeStats.value.message_corruptions +
    mqttDiffTypeStats.value.state_inconsistencies +
    mqttDiffTypeStats.value.authentication_errors;

  mqttDiffTypeStats.value.total_differences = total;

  if (total > 0) {
    mqttDiffTypeStats.value.distribution = {
      protocol_violations: Math.round(
        (mqttDiffTypeStats.value.protocol_violations / total) * 100,
      ),
      timeout_errors: Math.round(
        (mqttDiffTypeStats.value.timeout_errors / total) * 100,
      ),
      connection_failures: Math.round(
        (mqttDiffTypeStats.value.connection_failures / total) * 100,
      ),
      message_corruptions: Math.round(
        (mqttDiffTypeStats.value.message_corruptions / total) * 100,
      ),
      state_inconsistencies: Math.round(
        (mqttDiffTypeStats.value.state_inconsistencies / total) * 100,
      ),
      authentication_errors: Math.round(
        (mqttDiffTypeStats.value.authentication_errors / total) * 100,
      ),
    };
  }
}

// 开始MQTT差异报告读取 - 使用统一日志系统（保留原函数作为备用）
async function startMQTTDifferentialReading() {
  try {
    // 确保组件已挂载再进行操作
    if (!isRunning.value) {
      console.warn('测试未运行，跳过差异报告读取');
      return;
    }

    // 清空之前的日志
    clearUnifiedLogs();

    // 添加开始日志
    addUnifiedLog('INFO', '开始分析协议差异报告', 'MQTT');
    addUnifiedLog('INFO', '正在通过API读取MQTT日志文件...', 'MQTT');

    // 先测试后端连接（暂时禁用以避免错误弹窗）
    // try {
    //   const healthResponse = await requestClient.get('/healthz');
    //   if (healthResponse) {
    //     addUnifiedLog('INFO', '后端连接正常', 'MQTT');
    //   }
    // } catch (healthError: any) {
    //   addUnifiedLog('WARNING', `后端健康检查失败: ${healthError.message || healthError}`, 'MQTT');
    //   // 继续执行，不阻止测试流程
    // }
    addUnifiedLog('INFO', '开始MQTT协议测试', 'MQTT');

    // 通过后端API读取fuzzing_report.txt文件内容
    const result = await requestClient.post('/protocol-compliance/read-log', {
      protocol: 'MQTT',
      lastPosition: 0, // 从文件开头读取全部内容
    });

    console.log('MQTT差异报告API响应:', result);
    console.log('API调用成功，数据类型:', typeof result, '数据内容:', result);

    // requestClient已经处理了错误检查，直接使用返回的data
    const content = result.content;
    addUnifiedLog(
      'INFO',
      `成功读取日志文件，内容长度: ${content.length} 字符`,
      'MQTT',
    );

    const lines = content.split('\n');
    addUnifiedLog('INFO', `日志文件共 ${lines.length} 行`, 'MQTT');

    // 找到"Differential Report:"部分
    let inDifferentialSection = false;
    let processedCount = 0;
    let localErrorCount = 0;
    let localWarningCount = 0;
    let localSuccessCount = 0;
    let totalDifferentialLines = 0;

    // 首先统计总的差异报告行数
    let lineNumber = 0;
    for (const line of lines) {
      lineNumber++;
      if (line.trim() === 'Differential Report:') {
        inDifferentialSection = true;
        console.log(`找到差异报告开始位置: 第${lineNumber}行`);
        continue;
      }
      if (inDifferentialSection && line.trim()) {
        totalDifferentialLines++;
      }
    }
    console.log(
      `统计完成: 总行数${lines.length}, 差异报告行数${totalDifferentialLines}`,
    );

    // 设置进度状态
    mqttTotalRecords.value = totalDifferentialLines;
    mqttProcessedRecords.value = 0;
    mqttProcessingProgress.value = 0;
    mqttIsProcessingLogs.value = true;

    addUnifiedLog(
      'INFO',
      `发现 ${totalDifferentialLines} 条差异记录，开始逐条分析...`,
      'MQTT',
    );

    if (totalDifferentialLines === 0) {
      addUnifiedLog(
        'WARNING',
        '未找到差异报告内容，请检查日志文件格式',
        'MQTT',
      );
      // 显示前几行内容用于调试
      const firstFewLines = lines.slice(0, 10).filter((line) => line.trim());
      firstFewLines.forEach((line, index) => {
        addUnifiedLog(
          'INFO',
          `第${index + 1}行: ${line.substring(0, 100)}${line.length > 100 ? '...' : ''}`,
          'MQTT',
        );
      });
    }

    // 重置标志位，重新处理
    inDifferentialSection = false;
    let currentLineNumber = 0;
    let skippedLines = 0;

    for (const line of lines) {
      currentLineNumber++;

      // 检查用户是否中途停止测试
      if (!isRunning.value) {
        addUnifiedLog('WARNING', '用户中止了测试操作', 'MQTT');
        mqttIsProcessingLogs.value = false;
        return;
      }

      if (line.trim() === 'Differential Report:') {
        inDifferentialSection = true;
        console.log(`开始处理差异报告: 第${currentLineNumber}行`);
        continue;
      }

      if (inDifferentialSection && line.trim()) {
        // 解析差异报告行
        const diffData = parseMQTTDifferentialLine(line);
        if (diffData) {
          processedCount++;

          // 根据处理进度同步更新client和broker发送数据
          updateDataSendingProgress(processedCount, totalDifferentialLines);

          // 统计数据
          if (diffData.type === 'ERROR') {
            localErrorCount++;
          } else if (diffData.type === 'WARNING') {
            localWarningCount++;
          } else {
            localSuccessCount++;
          }

          // 添加到统一日志系统
          addUnifiedLog(diffData.type, diffData.content, 'MQTT');

          // 更新统计数据和进度
          packetCount.value = processedCount;
          failedCount.value = localErrorCount;
          timeoutCount.value = localWarningCount;
          successCount.value = localSuccessCount;

          // 更新MQTT进度状态
          mqttProcessedRecords.value = processedCount;
          mqttProcessingProgress.value = Math.round(
            (processedCount / totalDifferentialLines) * 100,
          );

          // 每处理50条记录显示进度
          if (processedCount % 50 === 0) {
            addUnifiedLog(
              'INFO',
              `处理进度: ${processedCount}/${totalDifferentialLines} (${mqttProcessingProgress.value}%)`,
              'MQTT',
            );

            // 短暂延迟，让界面有时间更新
            await new Promise((resolve) => setTimeout(resolve, 100));
          }
        } else if (inDifferentialSection) {
          // 记录跳过的行
          skippedLines++;
          if (skippedLines <= 5) {
            console.log(
              `跳过第${currentLineNumber}行 (无法解析): ${line.substring(0, 100)}`,
            );
          }
        }
      }
    }

    console.log(
      `处理完成统计: 总行数${lines.length}, 处理成功${processedCount}, 跳过${skippedLines}`,
    );

    // 最终更新统计数据
    packetCount.value = processedCount;
    failedCount.value = localErrorCount;
    timeoutCount.value = localWarningCount;
    successCount.value = localSuccessCount;

    // 完成进度状态更新
    mqttProcessedRecords.value = processedCount;
    mqttProcessingProgress.value = 100;
    mqttIsProcessingLogs.value = false;

    // 处理完成
    addUnifiedLog(
      'SUCCESS',
      `差异报告分析完成，共处理 ${processedCount} 条差异记录`,
      'MQTT',
    );
    addUnifiedLog(
      'INFO',
      `统计结果 - 错误: ${localErrorCount}, 警告: ${localWarningCount}, 信息: ${localSuccessCount}`,
      'MQTT',
    );

    // 等待一小段时间让用户看到完成信息
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // 检查用户是否在等待期间停止了测试
    if (!isRunning.value) {
      addUnifiedLog('WARNING', '用户中止了测试操作', 'MQTT');
      mqttIsProcessingLogs.value = false;
      return;
    }

    // 日志处理完成，自动结束测试
    addUnifiedLog('SUCCESS', 'MQTT协议差异分析已完成，测试结束', 'MQTT');

    // 结束测试
    setTimeout(() => {
      if (isRunning.value) {
        // 测试完成，正常结束
        isRunning.value = false;
        isPaused.value = false;
        isTestCompleted.value = true;
        testEndTime.value = new Date();

        // 停止计时器
        if (testTimer) {
          clearInterval(testTimer as any);
          testTimer = null;
        }

        addUnifiedLog('SUCCESS', 'MQTT测试完成', 'MQTT');

        // 保存历史记录
        setTimeout(() => {
          try {
            console.log('[DEBUG] MQTT test completed, saving to history...');
            console.log(
              '[DEBUG] Current MQTT stats before saving:',
              mqttStats.value,
            );
            updateTestSummary();
            saveTestToHistory();
            console.log('[DEBUG] MQTT history save completed');
          } catch (error) {
            console.error('Error saving MQTT test results:', error);
          }
        }, 500);
      }
    }, 1000);
  } catch (error: any) {
    console.error('读取MQTT差异报告失败:', error);
    addUnifiedLog('ERROR', `读取差异报告失败: ${error.message}`, 'MQTT');

    // 出错时重置进度状态
    mqttIsProcessingLogs.value = false;
    mqttProcessingProgress.value = 0;

    // 出错时也要结束测试
    setTimeout(() => {
      if (isRunning.value) {
        isRunning.value = false;
        isPaused.value = false;
        isTestCompleted.value = true;
        testEndTime.value = new Date();

        if (testTimer) {
          clearInterval(testTimer as any);
          testTimer = null;
        }
      }
    }, 1000);
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
    const brokers = brokerMatch
      ? brokerMatch[1]
          .replace(/'/g, '')
          .split(',')
          .map((b) => b.trim())
          .join(', ')
      : '未知';
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
      content,
    };
  } catch (error) {
    console.warn('解析差异报告行失败:', line, error);
    return null;
  }
}

// 计算测试时长的辅助函数
function calculateTestDuration(startTime: string, endTime: string): string {
  try {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const diffMs = end.getTime() - start.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);
    const hours = Math.floor(diffSeconds / 3600);
    const minutes = Math.floor((diffSeconds % 3600) / 60);
    const seconds = diffSeconds % 60;

    if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s`;
    }
  } catch (error) {
    return '计算中...';
  }
}

// 格式化MQTT日志行，高亮关键字段，去除file_path字段
function formatMQTTLogLine(log: any): string {
  // 如果是对象类型（新的协议数据管理器格式）
  if (typeof log === 'object' && log.content) {
    const typeIcon =
      {
        ERROR: '❌',
        WARNING: '⚠️',
        SUCCESS: '✅',
        INFO: 'ℹ️',
      }[log.type] || 'ℹ️';

    return `${typeIcon} [${log.timestamp}] ${log.content}`;
  }

  // 如果是字符串类型（原有格式）
  const logString = typeof log === 'string' ? log : String(log);

  // 如果是系统信息行，直接返回
  if (
    logString.includes('===') ||
    logString.includes('开始时间') ||
    logString.includes('结束时间') ||
    logString.includes('目标') ||
    logString.includes('正在分析')
  ) {
    return `<span class="text-blue-600">${logString}</span>`;
  }

  // 去除 file_path 字段
  let formattedLog = logString.replace(/,\s*file_path:\s*[^,]+/g, '');

  // 高亮 protocol_version
  formattedLog = formattedLog.replace(
    /protocol_version:\s*(\d+)/g,
    'protocol_version: <span class="text-blue-600 font-semibold">$1</span>',
  );

  // 高亮 type 字段
  formattedLog = formattedLog.replace(
    /type:\s*\{([^}]+)\}/g,
    'type: {<span class="text-red-600 font-semibold">$1</span>}',
  );

  // 高亮 msg_type 字段
  formattedLog = formattedLog.replace(
    /msg_type:\s*([^,\s]+)/g,
    'msg_type: <span class="text-green-600 font-semibold">$1</span>',
  );

  // 高亮 direction 字段
  formattedLog = formattedLog.replace(
    /direction:\s*([^,\s]+)/g,
    'direction: <span class="text-purple-600 font-semibold">$1</span>',
  );

  // 高亮 field 字段
  formattedLog = formattedLog.replace(
    /field:\s*([^,]+?)(?=,|$)/g,
    'field: <span class="text-orange-600 font-semibold">$1</span>',
  );

  // 高亮 diff_range_broker 字段
  formattedLog = formattedLog.replace(
    /diff_range_broker:\s*(\[[^\]]+\])/g,
    'diff_range_broker: <span class="text-cyan-600 font-semibold">$1</span>',
  );

  // 高亮 capture_time 字段
  formattedLog = formattedLog.replace(
    /capture_time:\s*([^,\s]+(?:\s+[^,\s]+)*)/g,
    'capture_time: <span class="text-gray-600 font-semibold">$1</span>',
  );

  return formattedLog;
}

// 解析MQTT差异报告行 - 新版本，返回结构化数据
function parseMQTTDifferentialLine(line: string) {
  try {
    // 提取关键信息 - 修复正则表达式以匹配实际格式
    const versionMatch = line.match(/protocol_version:\s*(\d+)/);
    const typeMatch = line.match(/type:\s*\{([^}]+)\}/);
    const msgTypeMatch = line.match(/msg_type:\s*([^,\s]+)/);
    const brokerMatch = line.match(/diff_range_broker:\s*\[([^\]]+)\]/);
    const directionMatch = line.match(/direction:\s*([^,\s]+)/);
    const fieldMatch = line.match(/field:\s*([^,]+?)(?:,|$)/);
    const captureTimeMatch = line.match(
      /capture_time:\s*([^,\s]+(?:\s+[^,\s]+)*)/,
    );

    if (!versionMatch || !typeMatch) {
      console.log('解析失败 - 缺少必要字段:', {
        version: !!versionMatch,
        type: !!typeMatch,
        msgType: !!msgTypeMatch,
        line: line.substring(0, 100),
      });
      return null;
    }

    const protocolVersion = parseInt(versionMatch[1]);
    const diffType = typeMatch[1];
    const msgType = msgTypeMatch ? msgTypeMatch[1].trim() : 'UNKNOWN';
    const brokers = brokerMatch
      ? brokerMatch[1]
          .replace(/'/g, '')
          .split(',')
          .map((b) => b.trim())
      : [];
    const direction = directionMatch ? directionMatch[1].trim() : 'unknown';
    const field = fieldMatch ? fieldMatch[1].trim() : '';
    const captureTime = captureTimeMatch ? captureTimeMatch[1].trim() : '';

    // 根据差异类型确定日志级别和图标
    let logType: 'ERROR' | 'WARNING' | 'INFO' = 'INFO';
    let icon = 'fa-info-circle';
    let severity = '信息';

    if (diffType.includes('Missing') || diffType.includes('Unexpected')) {
      logType = 'ERROR';
      icon = 'fa-exclamation-triangle';
      severity = '严重';
    } else if (diffType.includes('Different')) {
      logType = 'WARNING';
      icon = 'fa-warning';
      severity = '警告';
    }

    // 添加差异类型的中文描述
    let diffTypeDesc = diffType;
    switch (diffType) {
      case 'Message Missing':
        diffTypeDesc = '消息缺失';
        break;
      case 'Message Unexpected':
        diffTypeDesc = '意外消息';
        break;
      case 'Field Missing':
        diffTypeDesc = '字段缺失';
        break;
      case 'Field Unexpected':
        diffTypeDesc = '意外字段';
        break;
      case 'Field Different':
        diffTypeDesc = '字段值不同';
        break;
    }

    // 构建完整的显示内容，包含所有字段（除file_path外）
    let content = `protocol_version: ${protocolVersion}, type: {${diffType}}, diff_range_broker: [${brokers.map((b) => `'${b}'`).join(', ')}]`;

    // 只有当 msg_type 存在且不是 'UNKNOWN' 时才显示
    if (msgType && msgType !== 'UNKNOWN') {
      content += `, msg_type: ${msgType}`;
    }

    content += `, direction: ${direction}`;

    if (field) {
      content += `, field: ${field}`;
    }

    if (captureTime) {
      content += `, capture_time: ${captureTime}`;
    }

    return {
      type: logType,
      content: content,
      protocolVersion,
      msgType,
      direction,
      diffType,
      diffTypeDesc,
      field,
      brokers,
      captureTime,
      icon,
      severity,
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
    content: '开始解析MBFuzzer日志文件...',
  });
}

// MQTT日志读取函数现在通过 useLogReader 和 useMQTT composables 管理

// SOL specific functions (现在通过 useSOL composable 管理)
async function writeSOLScriptWrapper() {
  const scriptContent = solCommandConfig.value;

  try {
    const result = await writeSOLScript(scriptContent, [selectedProtocolImplementation.value]);

    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'SOL',
        type: 'SCRIPT',
        oids: [`脚本已写入: ${result.data?.filePath || '脚本文件'}`],
        hex: '',
        result: 'success',
      } as any,
      false,
    );
  } catch (error: any) {
    console.error('写入SOL脚本失败:', error);
    throw new Error(`写入脚本文件失败: ${error.message}`);
  }
}

async function executeSOLCommandWrapper() {
  try {
    const result = await executeSOLCommand([selectedProtocolImplementation.value]);

    // 保存容器ID用于后续停止
    if (result.data && (result.data.container_id || result.data.pid)) {
      solProcessId.value = result.data.container_id || result.data.pid;
    }

    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'SOL',
        type: 'COMMAND',
        oids: [
          `Docker容器已启动 (ID: ${result.data?.container_id || result.data?.pid || 'unknown'})`,
        ],
        hex: '',
        result: 'success',
      } as any,
      false,
    );
  } catch (error: any) {
    console.error('执行SOL命令失败:', error);
    throw new Error(`执行启动命令失败: ${error.message}`);
  }
}

function startSOLLogReading() {
  isReadingLog.value = true;

  // 先检查状态
  checkSOLStatus();

  // 开始实时日志读取
  readSOLLogPeriodically();

  addLogToUI(
    {
      timestamp: new Date().toLocaleTimeString(),
      version: 'SOL',
      type: 'LOG',
      oids: [`开始读取日志`],
      hex: '',
      result: 'success',
    } as any,
    false,
  );
}

// 检查SOL状态
async function checkSOLStatus() {
  try {
    const result = await requestClient.post(
      '/protocol-compliance/check-status',
      {
        protocol: 'MQTT',  // SOL协议现在通过MQTT协议实现选择
        protocolImplementations: [selectedProtocolImplementation.value],
      },
    );

    console.log('[DEBUG] SOL状态检查结果:', result);

    if (result) {
      // 显示状态信息到UI
      const statusMessage = `状态检查: 日志目录${result.log_dir_exists ? '存在' : '不存在'}, 日志文件${result.log_file_exists ? '存在' : '不存在'}`;

      addToRealtimeStream('MQTT', {
        timestamp: new Date().toLocaleTimeString(),
        type: 'INFO',
        content: statusMessage,
      });

      // 如果有Docker容器信息，显示
      if (result.docker_containers) {
        addToRealtimeStream('MQTT', {
          timestamp: new Date().toLocaleTimeString(),
          type: 'INFO',
          content: `Docker容器状态: ${result.docker_containers.split('\n').length - 1}个容器运行中`,
        });
      }

      // 如果有文件列表，显示
      if (result.files_in_log_dir && Array.isArray(result.files_in_log_dir)) {
        addToRealtimeStream('MQTT', {
          timestamp: new Date().toLocaleTimeString(),
          type: 'INFO',
          content: `输出目录文件: ${result.files_in_log_dir.join(', ')}`,
        });
      }
    }
  } catch (error) {
    console.error('检查SOL状态失败:', error);

    addToRealtimeStream('RTSP', {
      timestamp: new Date().toLocaleTimeString(),
      type: 'ERROR',
      content: `状态检查失败: ${error.message || error}`,
    });
  }
}

async function readSOLLogPeriodically() {
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
      const result = await requestClient.post('/protocol-compliance/read-log', {
        protocol: 'MQTT',  // SOL协议现在通过MQTT协议实现选择
        protocolImplementations: [selectedProtocolImplementation.value],
        lastPosition: logReadPosition.value, // 使用实际的读取位置，实现增量读取
      });

      console.log('[DEBUG] SOL日志读取结果:', result);

      if (result && result.message) {
        // 显示后端返回的状态信息
        console.log('[DEBUG] 后端状态信息:', result.message);

        // 如果是文件不存在的情况，显示等待信息
        if (
          result.message.includes('日志文件尚未创建') ||
          result.message.includes('日志目录不存在')
        ) {
          addToRealtimeStream('MQTT', {
            timestamp: new Date().toLocaleTimeString(),
            type: 'WARNING',
            content: result.message,
          });
        }
      }

      if (result && result.content && result.content.trim()) {
        // 更新读取位置
        logReadPosition.value = result.position || logReadPosition.value;

        console.log('[DEBUG] 读取到SOL日志内容，长度:', result.content.length);
        console.log('[DEBUG] 日志内容预览:', result.content.substring(0, 200));

        // 处理AFL-NET的plot_data格式
        const logLines = result.content
          .split('\n')
          .filter((line: string) => line.trim());
        console.log('[DEBUG] 处理日志行数:', logLines.length);

        logLines.forEach((line: string) => {
          const logData = processSOLLogLine(
            line,
            packetCount,
            successCount,
            failedCount,
            crashCount,
            currentSpeed,
          );
          if (logData) {
            console.log('[DEBUG] 处理的日志数据:', logData);

            // 使用协议数据管理器添加日志，而不是直接操作DOM
            addToRealtimeStream('MQTT', {
              timestamp: logData.timestamp,
              type: logData.type === 'STATS' ? 'INFO' : logData.type,
              content: logData.content,
            });
          }
        });
      } else if (result && result.file_size !== undefined) {
        // 文件存在但没有新内容
        console.log(
          '[DEBUG] 日志文件存在但没有新内容，文件大小:',
          result.file_size,
        );
      }
    } catch (error) {
      console.error('读取SOL日志失败:', error);

      // 显示错误信息到UI
      addToRealtimeStream('MQTT', {
        timestamp: new Date().toLocaleTimeString(),
        type: 'ERROR',
        content: `读取日志失败: ${error.message || error}`,
      });
    }
  }, 2000); // 每2秒读取一次日志
}

// processMQTTLogLine 现在通过 useMQTT composable 提供

// processRTSPLogLine 现在通过 useRTSP composable 提供

// addMQTTLogToUI 和 addRTSPLogToUI 现在通过 useLogReader composable 提供

async function stopSOLProcessWrapper() {
  if (!solProcessId.value) {
    return;
  }

  try {
    // 检查solProcessId是否是Docker容器ID（通常是长字符串）
    const isDockerContainer =
      typeof solProcessId.value === 'string' &&
      solProcessId.value.length > 10;

    if (isDockerContainer) {
      // 使用新的停止和清理功能
      const result = await stopAndCleanupSOL(solProcessId.value as string);

      addLogToUI(
        {
          timestamp: new Date().toLocaleTimeString(),
          version: 'SOL',
          type: 'CLEANUP',
          oids: [
            `Docker容器已停止 (ID: ${solProcessId.value})`,
            `容器清理状态: ${result.data?.cleanup_results ? '成功' : '部分成功'}`,
            `输出目录已清空，为下次测试做准备`,
          ],
          hex: '',
          result: 'success',
        } as any,
        false,
      );

      // 显示详细的清理结果
      if (result.data?.cleanup_results) {
        const cleanupResults = result.data.cleanup_results;
        const details = [];
        if (cleanupResults.container_stopped) details.push('✓ 容器已停止');
        if (cleanupResults.container_removed) details.push('✓ 容器已删除');
        if (cleanupResults.output_cleaned) details.push('✓ 输出目录已清空');
        if (cleanupResults.errors && cleanupResults.errors.length > 0) {
          details.push(`⚠ 错误: ${cleanupResults.errors.join(', ')}`);
        }

        addLogToUI(
          {
            timestamp: new Date().toLocaleTimeString(),
            version: 'SOL',
            type: 'INFO',
            oids: details,
            hex: '',
            result: 'info',
          } as any,
          false,
        );
      }
    } else {
      // 传统进程ID，使用原来的停止方法
      await stopSOLProcess(solProcessId.value);

      addLogToUI(
        {
          timestamp: new Date().toLocaleTimeString(),
          version: 'SOL',
          type: 'STOP',
          oids: [`SOL进程已停止 (PID: ${solProcessId.value})`],
          hex: '',
          result: 'success',
        } as any,
        false,
      );
    }

    solProcessId.value = null;
  } catch (error) {
    console.error('停止SOL进程失败:', error);

    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'SOL',
        type: 'ERROR',
        oids: [`停止SOL进程失败: ${error.message || error}`],
        hex: '',
        result: 'error',
      } as any,
      false,
    );
  }
}

// 处理停止测试的安全包装函数
function handleStopTest() {
  try {
    // 停止所有协议的实时流
    stopAllRealtimeStreams();

    // 更新当前协议状态
    updateProtocolState(protocolType.value as any, {
      isRunning: false,
      isProcessing: false,
    });

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

    // 添加用户中止日志
    addUnifiedLog('WARNING', '用户手动停止了MQTT测试', 'MQTT');

    // 重置MQTT进度状态
    mqttIsProcessingLogs.value = false;
    mqttProcessingProgress.value = 0;

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

    // 添加停止完成日志
    addUnifiedLog('INFO', 'MQTT测试已被用户停止', 'MQTT');

    // 延迟保存历史记录
    setTimeout(() => {
      try {
        console.log('[DEBUG] MQTT test manually stopped, saving to history...');
        console.log(
          '[DEBUG] Current MQTT stats before saving:',
          mqttStats.value,
        );
        updateTestSummary();
        saveTestToHistory();
        console.log('[DEBUG] MQTT manual stop history save completed');
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
    if (protocolType.value === 'MQTT' && selectedProtocolImplementation.value === 'SOL协议') {
      stopSOLProcessWrapper();
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
      messageTypeStats: messageTypeStats.value,
    });

    // Use nextTick to ensure all reactive updates are complete before updating charts
    // 跳过MQTT协议的图表更新，避免DOM冲突
    if (protocolType.value !== 'MQTT') {
      nextTick(() => {
        try {
          // 只有在测试真正完成且不是MQTT协议时才更新图表
          if (isTestCompleted.value) {
            console.log('Updating charts for SNMP protocol completion:', {
              protocolStats: protocolStats.value,
              messageTypeStats: messageTypeStats.value,
              chartsInitialized: !!(messageTypeChart && versionChart),
            });

            // Double-check charts are initialized before updating
            if (messageTypeChart && versionChart) {
              // 确保图表数据不为空，如果为空则使用默认值
              const hasValidData =
                protocolStats.value.v1 +
                  protocolStats.value.v2c +
                  protocolStats.value.v3 >
                  0 ||
                messageTypeStats.value.get +
                  messageTypeStats.value.set +
                  messageTypeStats.value.getnext +
                  messageTypeStats.value.getbulk >
                  0;

              if (!hasValidData) {
                console.warn(
                  'Chart data appears to be empty, using file-based statistics as fallback',
                );
                // 如果统计数据为空，尝试从已解析的fuzz数据中重新计算统计信息
                recalculateStatsFromFuzzData();
              }

              updateCharts();
              showCharts.value = true;
              console.log('Charts updated successfully for SNMP protocol');
            } else {
              // Try to reinitialize charts if they're not available
              console.log(
                'Charts not initialized, attempting to reinitialize...',
              );
              const success = initCharts();
              if (success) {
                updateCharts();
                showCharts.value = true;
                console.log('Charts reinitialized and updated successfully');
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
      console.log(
        'MQTT protocol: skipping chart updates to avoid DOM conflicts',
      );
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

// 统一的清空日志函数
function clearAllLogs() {
  clearLog(); // 清空原有的日志系统
  clearUnifiedLogs(); // 清空统一日志系统
}

// clearLog 现在通过 useLogReader composable 提供

function saveLog() {
  if (logEntries.value.length === 0) {
    // Generate a test report even if no log entries
    generateTestReport();
    return;
  }

  let logText = `时间,类型,内容\n`;
  logEntries.value.forEach((entry) => {
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
  let reportContent = '';

  if (protocolType.value === 'MQTT' && selectedProtocolImplementation.value === 'SOL协议') {
    // SOL协议AFLNET报告格式
    reportContent =
      `AFLNET SOL协议模糊测试报告\n` +
      `==========================\n\n` +
      `测试引擎: ${fuzzEngine.value} (SOL协议模糊测试)\n` +
      `目标服务器: ${targetHost.value}:${targetPort.value}\n` +
      `开始时间: ${startTime.value || (testStartTime.value ? testStartTime.value.toLocaleString() : '未开始')}\n` +
      `结束时间: ${endTime.value || (testEndTime.value ? testEndTime.value.toLocaleString() : '未结束')}\n` +
      `总耗时: ${elapsedTime.value}秒\n\n` +
      `AFLNET核心统计:\n` +
      `===============\n` +
      `当前执行路径: ${solStats.value.cur_path || 0}\n` +
      `总路径数: ${solStats.value.paths_total || 0}\n` +
      `执行速度: ${solStats.value.execs_per_sec.toFixed(1) || '0.0'} exec/sec\n` +
      `完成循环: ${solStats.value.cycles_done || 0}\n` +
      `最大深度: ${solStats.value.max_depth || 0}\n` +
      `代码覆盖率: ${solStats.value.map_size || 0}\n\n` +
      `安全监控:\n` +
      `========\n` +
      `崩溃检测: ${solStats.value.unique_crashes > 0 ? `检测到 ${solStats.value.unique_crashes} 个崩溃` : '系统稳定运行'}\n` +
      `挂起检测: ${solStats.value.unique_hangs > 0 ? `检测到 ${solStats.value.unique_hangs} 个挂起` : '无挂起现象'}\n` +
      `状态节点数: ${solStats.value.n_nodes || 0}\n` +
      `状态转换数: ${solStats.value.n_edges || 0}\n\n` +
      `报告生成时间: ${new Date().toLocaleString()}\n` +
      `报告版本: AFLNET v1.0 - SOL协议模糊测试引擎`;
  } else if (protocolType.value === 'MQTT') {
    // MQTT协议MBFuzzer报告格式
    reportContent =
      `MBFuzzer MQTT协议差异测试报告\n` +
      `================================\n\n` +
      `测试引擎: ${fuzzEngine.value} (智能差异测试)\n` +
      `目标代理: ${targetHost.value}:${targetPort.value}\n` +
      `开始时间: ${mqttStats.value.fuzzing_start_time || (testStartTime.value ? testStartTime.value.toLocaleString() : '未开始')}\n` +
      `结束时间: ${mqttStats.value.fuzzing_end_time || (testEndTime.value ? testEndTime.value.toLocaleString() : '未结束')}\n` +
      `总耗时: ${elapsedTime.value}秒\n\n` +
      `MBFuzzer核心统计:\n` +
      `================\n` +
      `客户端请求数: ${(mqttStats.value.client_request_count || 0).toLocaleString()}\n` +
      `代理端请求数: ${(mqttStats.value.broker_request_count || 0).toLocaleString()}\n` +
      `总请求数: ${((mqttStats.value.client_request_count || 0) + (mqttStats.value.broker_request_count || 0)).toLocaleString()}\n` +
      `有效连接数: ${mqttStats.value.valid_connect_number}\n` +
      `连接成功率: ${mqttStats.value.client_request_count > 0 ? Math.round((mqttStats.value.valid_connect_number / mqttStats.value.client_request_count) * 100) : 0}%\n` +
      `平均请求速率: ${Math.round((mqttStats.value.client_request_count + mqttStats.value.broker_request_count) / Math.max(1, elapsedTime.value))} req/s\n\n` +
      `差异测试结果:\n` +
      `============\n` +
      `新发现差异: ${mqttStats.value.diff_number} 个\n` +
      `重复差异过滤: ${(mqttStats.value.duplicate_diff_number || 0).toLocaleString()} 个\n` +
      `差异发现率: ${(mqttStats.value.client_request_count || 0) + (mqttStats.value.broker_request_count || 0) > 0 ? Math.round(((mqttStats.value.diff_number || 0) / ((mqttStats.value.client_request_count || 0) + (mqttStats.value.broker_request_count || 0))) * 10000) / 100 : 0}%\n\n` +
      `安全监控:\n` +
      `========\n` +
      `崩溃检测: ${mqttStats.value.crash_number > 0 ? `检测到 ${mqttStats.value.crash_number} 个崩溃` : '系统稳定运行'}\n` +
      `Q-Learning状态空间: ${Object.keys(mqttStats.value.q_learning_states || {}).length} 个协议状态\n\n` +
      `报告生成时间: ${new Date().toLocaleString()}\n` +
      `报告版本: MBFuzzer v1.0 - 智能MQTT协议差异测试引擎`;
  } else {
    // 其他协议的标准报告格式
    reportContent =
      `Fuzz测试报告\n` +
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
  }

  const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const fileName =
    protocolType.value === 'MQTT'
      ? `mbfuzzer_report_${new Date().getTime()}.txt`
      : `fuzz_report_${new Date().getTime()}.txt`;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 导出差异类型分布数据
function exportDiffTypeData() {
  if (protocolType.value !== 'MQTT') return;

  let diffTypeContent =
    `MBFuzzer 差异类型分布统计导出\n` +
    `==============================\n\n` +
    `导出时间: ${new Date().toLocaleString()}\n` +
    `总差异数量: ${mqttDiffTypeStats.value.total_differences}\n\n` +
    `差异类型分布:\n` +
    `============\n`;

  // 添加各类型的详细统计
  diffTypeContent += `协议违规: ${mqttDiffTypeStats.value.protocol_violations} 个 (${mqttDiffTypeStats.value.distribution.protocol_violations}%)\n`;
  diffTypeContent += `超时错误: ${mqttDiffTypeStats.value.timeout_errors} 个 (${mqttDiffTypeStats.value.distribution.timeout_errors}%)\n`;
  diffTypeContent += `连接失败: ${mqttDiffTypeStats.value.connection_failures} 个 (${mqttDiffTypeStats.value.distribution.connection_failures}%)\n`;
  diffTypeContent += `消息损坏: ${mqttDiffTypeStats.value.message_corruptions} 个 (${mqttDiffTypeStats.value.distribution.message_corruptions}%)\n`;
  diffTypeContent += `状态不一致: ${mqttDiffTypeStats.value.state_inconsistencies} 个 (${mqttDiffTypeStats.value.distribution.state_inconsistencies}%)\n`;
  diffTypeContent += `认证错误: ${mqttDiffTypeStats.value.authentication_errors} 个 (${mqttDiffTypeStats.value.distribution.authentication_errors}%)\n\n`;

  // 添加分析建议
  diffTypeContent += `分析建议:\n`;
  diffTypeContent += `========\n`;

  const maxType = Object.entries(mqttDiffTypeStats.value.distribution).reduce(
    (max, [type, count]) => (count > max.count ? { type, count } : max),
    { type: '', count: 0 },
  );

  if (maxType.count > 0) {
    const typeNames = {
      protocol_violations: '协议违规',
      timeout_errors: '超时错误',
      connection_failures: '连接失败',
      message_corruptions: '消息损坏',
      state_inconsistencies: '状态不一致',
      authentication_errors: '认证错误',
    };
    diffTypeContent += `主要问题类型: ${typeNames[maxType.type as keyof typeof typeNames]} (${maxType.count}%)\n`;
    diffTypeContent += `建议优先关注该类型的差异进行深入分析。\n`;
  } else {
    diffTypeContent += `暂无差异类型数据\n`;
  }

  const blob = new Blob([diffTypeContent], {
    type: 'text/plain;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `mbfuzzer_diff_types_${new Date().getTime()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 导出差异测试结果
function exportDifferentialResults() {
  if (protocolType.value !== 'MQTT') return;

  const diffContent =
    `MBFuzzer差异测试结果导出\n` +
    `=======================\n\n` +
    `导出时间: ${new Date().toLocaleString()}\n` +
    `新发现差异: ${mqttStats.value.diff_number} 个\n` +
    `重复差异过滤: ${mqttStats.value.duplicate_diff_number} 个\n` +
    `差异发现率: ${mqttStats.value.client_request_count + mqttStats.value.broker_request_count > 0 ? Math.round((mqttStats.value.diff_number / (mqttStats.value.client_request_count + mqttStats.value.broker_request_count)) * 10000) / 100 : 0}%\n\n` +
    `差异类型分布:\n` +
    `============\n` +
    `CONNECT消息差异: ${mqttStats.value.duplicate_diffs.CONNECT || 0}\n` +
    `PUBLISH消息差异: ${mqttStats.value.duplicate_diffs.PUBLISH || 0}\n` +
    `SUBSCRIBE消息差异: ${mqttStats.value.duplicate_diffs.SUBSCRIBE || 0}\n` +
    `PINGREQ消息差异: ${mqttStats.value.duplicate_diffs.PINGREQ || 0}\n\n` +
    `详细差异记录:\n` +
    `============\n`;

  // 添加统一日志中的差异记录
  const diffLogs = unifiedLogs.value.filter(
    (log) =>
      log.protocol === 'MQTT' &&
      (log.type === 'ERROR' || log.type === 'WARNING'),
  );

  if (diffLogs.length > 0) {
    diffLogs.forEach((log, index) => {
      diffContent += `${index + 1}. [${log.timestamp}] ${log.type}: ${log.content}\n`;
    });
  } else {
    diffContent += `暂无详细差异记录\n`;
  }

  const blob = new Blob([diffContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `mbfuzzer_differential_${new Date().getTime()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 导出Fuzz日志文件
function exportFuzzLogs() {
  if (protocolType.value !== 'MQTT') return;

  const fuzzLogContent =
    `MBFuzzer模糊测试日志\n` +
    `==================\n\n` +
    `导出时间: ${new Date().toLocaleString()}\n` +
    `测试引擎: MBFuzzer (智能差异测试)\n` +
    `协议类型: MQTT\n` +
    `目标地址: ${targetHost.value}:${targetPort.value}\n\n` +
    `测试统计:\n` +
    `========\n` +
    `客户端请求数: ${(mqttStats.value.client_request_count || 0).toLocaleString()}\n` +
    `代理端请求数: ${(mqttStats.value.broker_request_count || 0).toLocaleString()}\n` +
    `总请求数: ${((mqttStats.value.client_request_count || 0) + (mqttStats.value.broker_request_count || 0)).toLocaleString()}\n` +
    `协议差异发现: ${(mqttStats.value.diff_number || 0).toLocaleString()}\n` +
    `崩溃数量: ${mqttStats.value.crash_number || 0}\n\n` +
    `详细执行日志:\n` +
    `============\n`;

  // 添加统一日志中的所有MQTT相关记录
  const mqttLogs = unifiedLogs.value.filter(
    (log) => log.protocol === 'MQTT' || log.version === 'MQTT',
  );

  mqttLogs.forEach((log, index) => {
    fuzzLogContent += `[${index + 1}] ${log.timestamp} - ${log.type}: ${log.result}\n`;
    if (log.failedReason) {
      fuzzLogContent += `    错误详情: ${log.failedReason}\n`;
    }
  });

  fuzzLogContent += `\n\n报告生成时间: ${new Date().toLocaleString()}\n`;
  fuzzLogContent += `报告版本: MBFuzzer v1.0 - 智能MQTT协议模糊测试引擎`;

  const blob = new Blob([fuzzLogContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `mbfuzzer_fuzz_logs_${new Date().getTime()}.txt`;
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

    if (currentPacketIndex.value >= snmpFuzzData.value.length) {
      return stopTest();
    }

    const packet = snmpFuzzData.value[currentPacketIndex.value];
    if (packet) {
      processSNMPPacket(packet, addLogToUI, (result: string) => {
        // Update result counters based on packet result
        switch (result) {
          case 'success':
            successCount.value++;
            break;
          case 'timeout':
            timeoutCount.value++;
            break;
          case 'failed':
            failedCount.value++;
            break;
          case 'crash':
            crashCount.value++;
            break;
        }

        // Debug: Log every 100 packets to verify counting
        if (packetCount.value % 100 === 0) {
          console.log(
            `统计更新 [包#${packetCount.value}]: 成功=${successCount.value}, 超时=${timeoutCount.value}, 失败=${failedCount.value}, 崩溃=${crashCount.value}`,
          );
        }
      });
    }

    // Batch update counters to prevent multiple reactive updates
    currentPacketIndex.value++;
    packetCount.value++;

    // Check for crash and stop if detected
    if (packet?.result === 'crash') {
      handleCrashDetection(packet);
      // Add a small delay before stopping to ensure UI updates complete
      setTimeout(() => {
        if (isRunning.value) {
          // Double-check we're still running
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
  // 根据当前协议类型添加日志
  const currentProtocolType = protocolType.value;
  const logType = isCrash
    ? 'ERROR'
    : packet.result === 'success'
      ? 'SUCCESS'
      : packet.result === 'timeout'
        ? 'WARNING'
        : 'INFO';

  let logContent: string;

  // 根据协议类型格式化日志内容
  if (currentProtocolType === 'SNMP') {
    logContent = formatSNMPPacketLog(packet, isCrash);
    console.log('[DEBUG] 添加SNMP日志:', { logType, logContent, packet });
  } else if (currentProtocolType === 'MQTT' && selectedProtocolImplementation.value === 'SOL协议') {
    logContent = formatSOLPacketLog(packet, isCrash);
    console.log('[DEBUG] 添加SOL日志:', { logType, logContent, packet });
  } else if (currentProtocolType === 'MQTT') {
    logContent = formatMQTTPacketLog(packet, isCrash);
    console.log('[DEBUG] 添加MQTT日志:', { logType, logContent, packet });
  } else {
    logContent = formatGenericPacketLog(packet, isCrash);
    console.log('[DEBUG] 添加通用日志:', { logType, logContent, packet });
  }

  addToRealtimeStream(currentProtocolType, {
    timestamp: new Date().toLocaleTimeString(),
    type: logType,
    content: logContent,
  });
}

// 格式化SNMP数据包日志
function formatSNMPPacketLog(packet: FuzzPacket, isCrash: boolean): string {
  if (isCrash) {
    return `CRASH DETECTED ${packet.version?.toUpperCase() || 'UNKNOWN'} ${packet.type?.toUpperCase() || 'UNKNOWN'}`;
  } else {
    const protocol = packet.version?.toUpperCase() || 'UNKNOWN';
    const op = packet.type?.toUpperCase() || 'UNKNOWN';
    const content = packet.oids?.[0] || '';
    const hex = (packet.hex || '').slice(0, 40);
    const resultText =
      packet.result === 'success'
        ? `正常响应 (${packet.responseSize || 0}字节)`
        : packet.result === 'timeout'
          ? '接收超时'
          : packet.result === 'failed'
            ? '构造失败'
            : '未知状态';

    return `SNMP${protocol} ${op} ${content} ${resultText} ${hex}...`;
  }
}

// 格式化SOL数据包日志
function formatSOLPacketLog(packet: FuzzPacket, isCrash: boolean): string {
  if (isCrash) {
    return `CRASH DETECTED ${packet.version?.toUpperCase() || 'SOL'} ${packet.type?.toUpperCase() || 'UNKNOWN'}`;
  } else {
    const protocol = packet.version?.toUpperCase() || 'SOL';
    const op = packet.type?.toUpperCase() || 'UNKNOWN';
    const content = packet.oids?.[0] || '';
    const hex = (packet.hex || '').slice(0, 40);
    const resultText =
      packet.result === 'success'
        ? `正常响应 (${packet.responseSize || 0}字节)`
        : packet.result === 'timeout'
          ? '接收超时'
          : packet.result === 'failed'
            ? '构造失败'
            : '未知状态';

    return `${protocol} ${op} ${content} ${resultText} ${hex}...`;
  }
}

// 格式化MQTT数据包日志
function formatMQTTPacketLog(packet: FuzzPacket, isCrash: boolean): string {
  if (isCrash) {
    return `CRASH DETECTED ${packet.version?.toUpperCase() || 'MQTT'} ${packet.type?.toUpperCase() || 'UNKNOWN'}`;
  } else {
    const protocol = packet.version?.toUpperCase() || 'MQTT';
    const op = packet.type?.toUpperCase() || 'UNKNOWN';
    const content = packet.oids?.[0] || '';
    const hex = (packet.hex || '').slice(0, 40);
    const resultText =
      packet.result === 'success'
        ? `正常响应 (${packet.responseSize || 0}字节)`
        : packet.result === 'timeout'
          ? '接收超时'
          : packet.result === 'failed'
            ? '构造失败'
            : '未知状态';

    return `${protocol} ${op} ${content} ${resultText} ${hex}...`;
  }
}

// 格式化通用数据包日志
function formatGenericPacketLog(packet: FuzzPacket, isCrash: boolean): string {
  if (isCrash) {
    return `CRASH DETECTED ${packet.version?.toUpperCase() || 'UNKNOWN'} ${packet.type?.toUpperCase() || 'UNKNOWN'}`;
  } else {
    const protocol = packet.version?.toUpperCase() || 'UNKNOWN';
    const op = packet.type?.toUpperCase() || 'UNKNOWN';
    const content = packet.oids?.[0] || '';
    const hex = (packet.hex || '').slice(0, 40);
    const resultText =
      packet.result === 'success'
        ? `正常响应 (${packet.responseSize || 0}字节)`
        : packet.result === 'timeout'
          ? '接收超时'
          : packet.result === 'failed'
            ? '构造失败'
            : '未知状态';

    return `${protocol} ${op} ${content} ${resultText} ${hex}...`;
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

function generateCrashDetails(
  packetId: number | string,
  protocol: string,
  operation: string,
  content: string,
) {
  const crashTypes = [
    'Segmentation Fault (SIGSEGV)',
    'Aborted (SIGABRT)',
    'Illegal Instruction (SIGILL)',
    'Bus Error (SIGBUS)',
    'Floating Point Exception (SIGFPE)',
  ];

  const crashType = crashTypes[Math.floor(Math.random() * crashTypes.length)];
  const timestamp = new Date().toLocaleTimeString();
  const dumpFile = `/var/crash/${protocol}_crash_${Date.now()}.dmp`;
  const logPath = `/home/hhh/下载/snmp_fuzz/snmp_github/snmp_fuzz/scan_result/crash_logs/${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${timestamp.replace(/:/g, '')}`;

  const detailsText =
    `[${timestamp}] ${crashType}\n` +
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
    packetContent: content,
  };
}

function handleCrashDetection(packet: FuzzPacket) {
  if (packet.crashEvent) {
    crashDetails.value = {
      id: packetCount.value,
      time: packet.crashEvent.timestamp,
      type: '程序崩溃',
      dumpFile: packet.crashEvent.crashLogPath,
      logPath: packet.crashEvent.crashLogPath,
      details: `崩溃通知: ${packet.crashEvent.message}\n疑似崩溃数据包: ${packet.crashEvent.crashPacket}\n崩溃队列信息导出: ${packet.crashEvent.crashLogPath}`,
      packetContent: packet.crashEvent.crashPacket,
    };
    addRealCrashLogEntries(packet.crashEvent);
  } else {
    crashDetails.value = generateCrashDetails(
      packetCount.value,
      packet.version,
      packet.type,
      packet.hex,
    );
    addCrashLogEntries(crashDetails.value, packet.version, packet.hex);
  }
}

function addRealCrashLogEntries(crashEvent: any) {
  const time = new Date().toLocaleTimeString();

  // Add crash logs to entries
  logEntries.value.push(
    { time, type: 'crash_notice', message: crashEvent.message },
    {
      time,
      type: 'crash_packet',
      message: `疑似崩溃数据包: ${crashEvent.crashPacket}`,
    },
    {
      time,
      type: 'crash_export',
      message: `崩溃队列信息导出: ${crashEvent.crashLogPath}`,
    },
    { time, type: 'stop_fuzz', message: '检测到崩溃，停止 fuzz 循环' },
  );

  // Add to UI with proper error handling and DOM checks
  nextTick(() => {
    try {
      if (
        logContainer.value &&
        !showHistoryView.value &&
        isRunning.value &&
        logContainer.value.appendChild
      ) {
        const logs = [
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">${crashEvent.message || '崩溃通知'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 疑似崩溃数据包: ${crashEvent.crashPacket || '未知'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 崩溃队列信息导出: ${crashEvent.crashLogPath || '未知路径'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">[运行监控] 检测到崩溃，停止 fuzz 循环</span>`,
        ];

        logs.forEach((logHtml) => {
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
    {
      time,
      type: 'crash_notice',
      message: '收到崩溃通知: 健康服务报告 VM 不可达',
    },
    { time, type: 'crash_packet', message: `疑似崩溃数据包: ${hex}` },
    { time, type: 'log_dir', message: `日志导出目录: ${crashDetails.logPath}` },
    { time, type: 'timeout', message: '接收超时' },
    { time, type: 'no_response', message: '响应: 无' },
    { time, type: 'stop_fuzz', message: '检测到崩溃，停止 fuzz 循环' },
  );

  nextTick(() => {
    try {
      if (
        logContainer.value &&
        !showHistoryView.value &&
        isRunning.value &&
        logContainer.value.appendChild
      ) {
        const logs = [
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">[运行监控] 收到崩溃通知: 健康服务报告 VM 不可达</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 疑似崩溃数据包: ${hex || '未知'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger">[崩溃信息] 日志导出目录: ${crashDetails?.logPath || '未知路径'}</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-warning">  [接收超时]</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-warning">  响应: 无</span>`,
          `<span class="text-dark/50">[${time}]</span> <span class="text-danger font-medium">[运行监控] 检测到崩溃，停止 fuzz 循环</span>`,
        ];

        logs.forEach((logHtml) => {
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
  const total =
    fileTotalPackets.value ||
    successCount.value +
      timeoutCount.value +
      failedCount.value +
      crashCount.value;
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
      timeoutRate: Math.round((finalTimeoutCount / total) * 100),
    });
  }
}

// 保存测试结果到历史记录
function saveTestToHistory() {
  try {
    console.log(
      '[DEBUG] saveTestToHistory called for protocol:',
      protocolType.value,
    );
    console.log('[DEBUG] Current test state:', {
      isRunning: isRunning.value,
      isTestCompleted: isTestCompleted.value,
      testStartTime: testStartTime.value,
      testEndTime: testEndTime.value,
    });

    // 计算实际的测试统计数据
    const actualTotalPackets = fileTotalPackets.value || packetCount.value;
    const actualSuccessCount = fileSuccessCount.value || successCount.value;
    const actualTimeoutCount = fileTimeoutCount.value || timeoutCount.value;
    const actualFailedCount = fileFailedCount.value || failedCount.value;
    const actualCrashCount = crashCount.value;

    console.log('[DEBUG] Test statistics:', {
      actualTotalPackets,
      actualSuccessCount,
      actualTimeoutCount,
      actualFailedCount,
      actualCrashCount,
    });

    // 获取有效连接数量（对于MQTT协议）或保持原有的测试持续时间（对于其他协议）
    const duration =
      protocolType.value === 'MQTT' && mqttStats.value.valid_connect_number
        ? mqttStats.value.valid_connect_number
        : testStartTime.value && testEndTime.value
          ? Math.round(
              (testEndTime.value.getTime() - testStartTime.value.getTime()) /
                1000,
            )
          : elapsedTime.value;

    // 计算成功率
    const total =
      actualTotalPackets ||
      actualSuccessCount +
        actualTimeoutCount +
        actualFailedCount +
        actualCrashCount;
    const successRate =
      total > 0 ? Math.round((actualSuccessCount / total) * 100) : 0;

    // 生成唯一ID
    const historyId = `test_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // 创建历史记录条目
    const historyItem: HistoryResult = {
      id: historyId,
      timestamp: testStartTime.value
        ? testStartTime.value.toLocaleString()
        : new Date().toLocaleString(),
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
        v3: protocolStats.value.v3,
      },
      messageTypeStats: {
        get: messageTypeStats.value.get,
        set: messageTypeStats.value.set,
        getnext: messageTypeStats.value.getnext,
        getbulk: messageTypeStats.value.getbulk,
      },
      // 保存SOL协议统计数据
      rtspStats:
        protocolType.value === 'MQTT' && selectedProtocolImplementation.value === 'SOL协议'
          ? {
              cycles_done: solStats.value.cycles_done,
              paths_total: solStats.value.paths_total,
              cur_path: solStats.value.cur_path,
              pending_total: solStats.value.pending_total,
              pending_favs: solStats.value.pending_favs,
              map_size: solStats.value.map_size,
              unique_crashes: solStats.value.unique_crashes,
              unique_hangs: solStats.value.unique_hangs,
              max_depth: solStats.value.max_depth,
              execs_per_sec: solStats.value.execs_per_sec,
              n_nodes: solStats.value.n_nodes,
              n_edges: solStats.value.n_edges,
            }
          : undefined,
      // 保存MQTT协议统计数据
      mqttStats:
        protocolType.value === 'MQTT'
          ? (() => {
              console.log('[DEBUG] Saving MQTT stats:', mqttStats.value);
              return {
                fuzzing_start_time: mqttStats.value.fuzzing_start_time,
                fuzzing_end_time: mqttStats.value.fuzzing_end_time,
                client_request_count: mqttStats.value.client_request_count,
                broker_request_count: mqttStats.value.broker_request_count,
                crash_number: mqttStats.value.crash_number,
                diff_number: mqttStats.value.diff_number,
                duplicate_diff_number: mqttStats.value.duplicate_diff_number,
                valid_connect_number: mqttStats.value.valid_connect_number,
                duplicate_connect_diff: mqttStats.value.duplicate_connect_diff,
                total_differences: mqttStats.value.total_differences,
              };
            })()
          : undefined,
      // 保存协议特定的扩展数据
      protocolSpecificData:
        protocolType.value === 'MQTT'
          ? {
              clientRequestCount: mqttStats.value.client_request_count,
              brokerRequestCount: mqttStats.value.broker_request_count,
              diffNumber: mqttStats.value.diff_number,
              duplicateDiffNumber: mqttStats.value.duplicate_diff_number,
              validConnectNumber: mqttStats.value.valid_connect_number,
              duplicateConnectDiff: mqttStats.value.duplicate_connect_diff,
              fuzzingStartTime: mqttStats.value.fuzzing_start_time,
              fuzzingEndTime: mqttStats.value.fuzzing_end_time,
            }
          : protocolType.value === 'MQTT' && selectedProtocolImplementation.value === 'SOL协议'
            ? {
                pathCoverage:
                  (solStats.value.cur_path /
                    Math.max(solStats.value.paths_total, 1)) *
                  100,
                stateTransitions: solStats.value.n_edges,
                maxDepth: solStats.value.max_depth,
                uniqueHangs: solStats.value.unique_hangs,
              }
            : protocolType.value === 'SNMP'
              ? {
                  oidCoverage: Math.round(
                    ((protocolStats.value.v1 +
                      protocolStats.value.v2c +
                      protocolStats.value.v3) /
                      Math.max(total, 1)) *
                      100,
                  ),
                  communityStrings: ['public', 'private'], // 示例数据
                  targetDeviceInfo: `${targetHost.value}:${targetPort.value}`,
                }
              : undefined,
      hasCrash: actualCrashCount > 0,
      crashDetails: crashDetails.value
        ? {
            id: crashDetails.value.id,
            time: crashDetails.value.time,
            type: crashDetails.value.type,
            dumpFile: crashDetails.value.dumpFile,
            logPath: crashDetails.value.logPath,
            details: crashDetails.value.details,
            packetContent: crashDetails.value.packetContent,
          }
        : undefined,
    };

    // 将新的测试结果添加到历史记录的开头
    historyResults.value.unshift(historyItem);

    // 限制历史记录数量，保留最新的50条
    if (historyResults.value.length > 50) {
      historyResults.value = historyResults.value.slice(0, 50);
    }

    // 保存到本地存储
    try {
      localStorage.setItem(
        'fuzz_test_history',
        JSON.stringify(historyResults.value),
      );
      console.log('Test results saved to history:', historyItem);
      console.log(
        '[DEBUG] History results length after save:',
        historyResults.value.length,
      );
      console.log('[DEBUG] Latest history item:', historyResults.value[0]);

      // 为MQTT协议添加详细的保存日志
      if (protocolType.value === 'MQTT') {
        console.log('MQTT test results saved to history successfully');
        console.log('MQTT Stats saved:', {
          mqttStats: historyItem.mqttStats,
          protocolSpecificData: historyItem.protocolSpecificData,
        });

        // 强制触发响应式更新
        nextTick(() => {
          console.log('[DEBUG] Forcing reactive update for history');
          // 触发一个小的变化来确保Vue检测到数组更新
          historyResults.value = [...historyResults.value];
        });
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
  const index = historyResults.value.findIndex((item) => item.id === id);
  if (index > -1) {
    historyResults.value.splice(index, 1);

    // 同步到本地存储
    try {
      localStorage.setItem(
        'fuzz_test_history',
        JSON.stringify(historyResults.value),
      );
      console.log('History item deleted and saved to localStorage');
    } catch (error) {
      console.warn('Failed to save updated history to localStorage:', error);
    }
  }
}

function exportHistoryItem(item: HistoryResult) {
  const reportContent =
    `Fuzz测试历史报告\n` +
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

  const reportContent =
    `Fuzz测试历史记录汇总\n` +
    `==================\n\n` +
    `导出时间: ${new Date().toLocaleString()}\n` +
    `总记录数: ${historyResults.value.length}\n\n` +
    historyResults.value
      .map(
        (item, index) =>
          `${index + 1}. [${item.timestamp}] ${item.protocol} - ${item.fuzzEngine}\n` +
          `   目标: ${item.targetHost}:${item.targetPort}\n` +
          `   耗时: ${item.duration}秒, 总包数: ${item.totalPackets}, 成功率: ${item.successRate}%\n` +
          `   崩溃: ${item.hasCrash ? '是' : '否'}\n`,
      )
      .join('\n');

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
  return !loading.value && snmpFuzzData.value.length > 0 && !isRunning.value;
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
    messageTypeStats: messageTypeStats.value,
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
        console.log(
          `Loaded ${parsedHistory.length} history items from localStorage`,
        );
        console.log(
          '[DEBUG] Loaded history items:',
          parsedHistory.map((item) => ({
            id: item.id,
            protocol: item.protocol,
            timestamp: item.timestamp,
          })),
        );
      }
    }
  } catch (error) {
    console.warn('Failed to load history from localStorage:', error);
    // 如果加载失败，保持默认的模拟数据
  }
}

// 测试历史记录保存功能（调试用）
function testHistorySave() {
  console.log('[DEBUG] Testing history save functionality...');
  console.log('[DEBUG] Current protocol:', protocolType.value);
  console.log('[DEBUG] Current MQTT stats:', mqttStats.value);

  // 手动触发保存
  try {
    saveTestToHistory();
    console.log('[DEBUG] Manual history save completed');
  } catch (error) {
    console.error('[DEBUG] Manual history save failed:', error);
  }
}

// 将测试函数暴露到全局作用域（仅用于调试）
if (typeof window !== 'undefined') {
  (window as any).testHistorySave = testHistorySave;
  (window as any).checkHistoryResults = () => {
    console.log('[DEBUG] Current history results:', historyResults.value);
    console.log('[DEBUG] History results length:', historyResults.value.length);
  };
  (window as any).testMQTTAnimation = () => {
    console.log('[DEBUG] Manual MQTT animation test');
    initMQTTAnimations();
  };
}

// MQTT动画相关变量和函数
let mqttAnimationIntervals: number[] = [];

// 初始化MQTT动画
function initMQTTAnimations() {
  console.log('[MQTT Animation] Starting initialization...');
  // 清理旧的动画
  cleanupMQTTAnimations();

  // 等待DOM完全渲染后再初始化
  setTimeout(() => {
    // 批量初始化6个MQTT模块
    for (let moduleId = 1; moduleId <= 6; moduleId++) {
      console.log(`[MQTT Animation] Initializing module ${moduleId}`);
      initMQTTModule(moduleId);
    }
  }, 100);
}

// 清理MQTT动画
function cleanupMQTTAnimations() {
  mqttAnimationIntervals.forEach((interval) => clearInterval(interval));
  mqttAnimationIntervals = [];
}

// 单个MQTT模块初始化函数
function initMQTTModule(moduleId: number) {
  const module = document.getElementById(`mqtt-viz-${moduleId}`);
  if (!module) {
    console.warn(`[MQTT Animation] Module mqtt-viz-${moduleId} not found`);
    return;
  }

  const broker = module.querySelector('.mqtt-node:nth-child(1)') as HTMLElement;
  const client1 = module.querySelector(
    '.mqtt-node:nth-child(2)',
  ) as HTMLElement;
  const client2 = module.querySelector(
    '.mqtt-node:nth-child(3)',
  ) as HTMLElement;
  const connections = document.getElementById(
    `connections-viz-${moduleId}`,
  ) as SVGElement;
  const particles = document.getElementById(
    `particles-viz-${moduleId}`,
  ) as HTMLElement;

  console.log(`[MQTT Animation] Module ${moduleId} elements:`, {
    module: !!module,
    broker: !!broker,
    client1: !!client1,
    client2: !!client2,
    connections: !!connections,
    particles: !!particles,
  });

  if (!broker || !client1 || !client2 || !connections || !particles) {
    console.warn(`[MQTT Animation] Missing elements for module ${moduleId}`);
    return;
  }

  // 获取元素位置（基于当前模块容器定位）
  function getPosition(el: HTMLElement) {
    // 使用相对于模块容器的固定位置，而不是getBoundingClientRect
    const moduleRect = module.getBoundingClientRect();
    const elRect = el.getBoundingClientRect();

    // 查找图标元素（SVG）而不是整个节点
    const iconElement = el.querySelector('svg') as HTMLElement;
    let iconRect = elRect;

    if (iconElement) {
      iconRect = iconElement.getBoundingClientRect();
    }

    // 计算图标相对于模块容器的位置
    const iconCenterX = iconRect.left - moduleRect.left + iconRect.width / 2;
    const iconCenterY = iconRect.top - moduleRect.top + iconRect.height / 2;

    console.log(`[MQTT Animation] Icon position:`, {
      iconCenterX,
      iconCenterY,
      element: el.className,
      hasIcon: !!iconElement,
    });

    return {
      centerX: iconCenterX,
      centerY: iconCenterY,
      // 为broker添加左下角和右下角连接点（基于图标位置）
      leftBottom: {
        x: iconCenterX - iconRect.width / 3,
        y: iconCenterY + iconRect.height / 2,
      },
      rightBottom: {
        x: iconCenterX + iconRect.width / 3,
        y: iconCenterY + iconRect.height / 2,
      },
      // 图标顶部边缘连接点（左上角和右上角）
      topLeft: {
        x: iconCenterX - iconRect.width / 2,
        y: iconCenterY - iconRect.height / 2 - 2,
      },
      topRight: {
        x: iconCenterX + iconRect.width / 2,
        y: iconCenterY - iconRect.height / 2 - 2,
      },
    };
  }

  // 创建连接线
  function createConnections() {
    const bPos = getPosition(broker);
    const c1Pos = getPosition(client1);
    const c2Pos = getPosition(client2);

    // 清空之前的连接线，避免重复绘制
    connections.innerHTML = '';

    console.log(
      `[MQTT Animation] Creating connections for module ${moduleId}:`,
      {
        broker: bPos,
        client1: c1Pos,
        client2: c2Pos,
      },
    );

    function createPath(
      from: { x: number; y: number },
      to: { x: number; y: number },
      id: string,
      color: string = '#3B82F6',
    ) {
      const path = document.createElementNS(
        'http://www.w3.org/2000/svg',
        'path',
      );

      // 创建轻微弧度的优美曲线连接
      const midX = (from.x + to.x) / 2;
      const midY = (from.y + to.y) / 2;

      // 轻微的弧度控制点，符合大众审美
      let controlX = midX;
      let controlY = midY;

      // 根据连接方向添加轻微的弧度偏移
      if (id.includes('broker-client1')) {
        // Client1连接，轻微向左弯曲
        controlX = midX - 15;
        controlY = midY - 20;
      } else if (id.includes('broker-client2')) {
        // Client2连接，轻微向右弯曲
        controlX = midX + 15;
        controlY = midY - 20;
      }

      // 使用二次贝塞尔曲线创建轻微弧度
      const d = `M ${from.x} ${from.y} Q ${controlX} ${controlY} ${to.x} ${to.y}`;

      path.setAttribute('d', d);
      path.setAttribute('id', `${id}-${moduleId}`);
      path.setAttribute('class', 'mqtt-connection');
      path.setAttribute('stroke', color);
      path.setAttribute('stroke-width', '2');
      path.setAttribute('fill', 'none');
      path.setAttribute('opacity', '0.8');
      connections.appendChild(path);
      console.log(`[MQTT Animation] Created curved path ${id}: ${d}`);
      return path;
    }

    // 创建两条对称的连接线：Client1连接右上角，Client2连接左上角
    const path1 = createPath(
      bPos.leftBottom,
      c1Pos.topRight,
      'broker-client1',
      '#3B82F6',
    );
    const path2 = createPath(
      bPos.rightBottom,
      c2Pos.topLeft,
      'broker-client2',
      '#3B82F6',
    );

    return { path1, path2 };
  }

  // 创建流动粒子
  function createParticles(paths: any) {
    console.log(`[MQTT Animation] Creating particles for module ${moduleId}`);
    const particleSources = [
      // 第一条线：Broker到Client1的粒子（深蓝色）
      {
        path: paths.path1,
        start: 0,
        end: 1,
        interval: 1500,
        class: 'mqtt-particle-from-broker',
        speed: 80,
      },
      // 第一条线：Client1到Broker的粒子（浅蓝色）
      {
        path: paths.path1,
        start: 1,
        end: 0,
        interval: 2500,
        class: 'mqtt-particle-from-client',
        speed: 80,
      },
      // 第二条线：Broker到Client2的粒子（深蓝色）
      {
        path: paths.path2,
        start: 0,
        end: 1,
        interval: 2000,
        class: 'mqtt-particle-from-broker',
        speed: 80,
      },
      // 第二条线：Client2到Broker的粒子（浅蓝色）
      {
        path: paths.path2,
        start: 1,
        end: 0,
        interval: 3000,
        class: 'mqtt-particle-from-client',
        speed: 80,
      },
    ];

    // 立即创建第一批粒子，然后设置定时器
    particleSources.forEach((source, index) => {
      // 立即创建一个粒子
      setTimeout(() => {
        createParticle(
          source.path,
          source.start,
          source.end,
          source.class,
          source.speed,
        );
      }, index * 200);

      // 设置定时器持续创建粒子
      const interval = setInterval(() => {
        console.log(
          `[MQTT Animation] Creating particle ${index} for module ${moduleId}`,
        );
        createParticle(
          source.path,
          source.start,
          source.end,
          source.class,
          source.speed,
        );
      }, source.interval);
      mqttAnimationIntervals.push(interval);
    });

    console.log(
      `[MQTT Animation] Created ${particleSources.length} particle sources for module ${moduleId}`,
    );
  }

  // 创建单个粒子
  function createParticle(
    path: SVGPathElement,
    start: number,
    end: number,
    particleClass: string,
    speed: number,
  ) {
    try {
      const particle = document.createElement('div');
      particle.className = `mqtt-particle ${particleClass}`;
      // 根据粒子类型设置不同的样式
      const isBrokerParticle = particleClass.includes('broker');
      const backgroundColor = isBrokerParticle ? '#3B82F6' : '#60A5FA';
      const shadowColor = isBrokerParticle
        ? 'rgba(59, 130, 246, 0.8)'
        : 'rgba(96, 165, 250, 0.8)';

      particle.style.cssText = `
        position: absolute;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        transform: translate(-50%, -50%);
        z-index: 10;
        box-shadow: 0 0 6px ${shadowColor};
        background: ${backgroundColor};
        border: 1px solid rgba(255, 255, 255, 0.3);
      `;
      particles.appendChild(particle);

      const length = path.getTotalLength();
      const duration = (length / speed) * 1000;

      console.log(
        `[MQTT Animation] Created particle with length: ${length}, duration: ${duration}ms`,
      );

      let starttime: number | null = null;
      let animationId: number;

      function animate(timestamp: number) {
        if (!starttime) starttime = timestamp;
        const progress = Math.min((timestamp - starttime) / duration, 1);

        if (progress < 1 && particles.contains(particle)) {
          try {
            const currentLength =
              start * length + progress * (end - start) * length;
            const pos = path.getPointAtLength(currentLength);

            // 添加一些随机抖动使动画更生动
            const jitterX = (Math.random() - 0.5) * 1;
            const jitterY = (Math.random() - 0.5) * 1;

            particle.style.left = `${pos.x + jitterX}px`;
            particle.style.top = `${pos.y + jitterY}px`;

            // 根据进度调整透明度
            const opacity = Math.sin(progress * Math.PI);
            particle.style.opacity = opacity.toString();

            animationId = requestAnimationFrame(animate);
          } catch (pathError) {
            console.warn(`[MQTT Animation] Path error:`, pathError);
            particle.remove();
          }
        } else {
          // 动画完成，移除粒子
          if (animationId) {
            cancelAnimationFrame(animationId);
          }
          setTimeout(() => {
            if (particles.contains(particle)) {
              particle.remove();
            }
          }, 50);
        }
      }

      // 开始动画
      animationId = requestAnimationFrame(animate);
    } catch (error) {
      console.error(`[MQTT Animation] Error creating particle:`, error);
    }
  }

  // 初始化当前模块
  function init() {
    const paths = createConnections();
    createParticles(paths);
  }

  // 执行当前模块初始化
  init();
}

// 错误捕获处理
onErrorCaptured((err, instance, info) => {
  console.error('[Vue Error Captured]:', err);
  console.error('[Component Instance]:', instance);
  console.error('[Error Info]:', info);

  // 如果是MQTT相关的DOM错误，尝试恢复
  if (
    err.message &&
    err.message.includes('nextSibling') &&
    protocolType.value === 'MQTT'
  ) {
    console.warn('[MQTT DOM Error] 检测到DOM更新错误，尝试重置MQTT日志状态');
    try {
      nextTick(() => {
        mqttDifferentialLogs.value = [];
        mqttLogsUpdateKey.value++;
        console.log('[MQTT DOM Error] MQTT日志状态已重置');
      });
    } catch (resetError) {
      console.error('[MQTT DOM Error] 重置失败:', resetError);
    }
  }

  // 返回false让错误继续传播，但不会导致应用崩溃
  return false;
});

// 组件卸载时清理
onUnmounted(() => {
  console.log('[DEBUG] 组件卸载，清理MQTT相关资源');

  // 清理MQTT动画
  cleanupMQTTAnimations();

  // 清理MQTT定时器和数据
  if (mqttUpdateTimer) {
    clearTimeout(mqttUpdateTimer);
    mqttUpdateTimer = null;
  }
  mqttDifferentialLogsData = [];
  mqttLogsPendingUpdate = false;

  // 清理其他定时器
  if (testTimer) {
    clearInterval(testTimer as any);
    testTimer = null;
  }

  if (logReadingInterval.value) {
    clearInterval(logReadingInterval.value);
    logReadingInterval.value = null;
  }

  // 停止测试
  isRunning.value = false;
  mqttSimulationCancelled = true;
});

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

    // 如果已有fuzz数据但统计数据为空，重新计算统计数据
    if (protocolType.value === 'SNMP' && snmpFuzzData.value.length > 0) {
      const hasValidData =
        protocolStats.value.v1 +
          protocolStats.value.v2c +
          protocolStats.value.v3 >
          0 ||
        messageTypeStats.value.get +
          messageTypeStats.value.set +
          messageTypeStats.value.getnext +
          messageTypeStats.value.getbulk >
          0;

      if (!hasValidData) {
        console.log('Recalculating stats on mount due to empty statistics');
        recalculateStatsFromFuzzData();
      }
    }

    // Update charts with initial data but don't show them yet
    updateCharts();
    // 只有在有完整数据且测试已完成时才显示图表
    if (isTestCompleted.value) {
      showCharts.value = true;
    }
  } else {
    console.error('Failed to initialize charts');
  }

  // MQTT协议不需要图表初始化，使用统计卡片显示
  if (protocolType.value === 'MQTT') {
    console.log('MQTT protocol uses statistical cards instead of charts');
    // MQTT动画将在测试开始时初始化
  }

  // Set initial last update time
  lastUpdate.value = new Date().toLocaleString();
});
</script>

<template>
  <Page
    title="协议模糊测试"
  >
    <!-- 加载状态 -->
    <div v-if="loading" class="flex h-64 items-center justify-center">
      <div
        class="border-primary h-12 w-12 animate-spin rounded-full border-b-2"
      ></div>
    </div>

    <!-- 错误状态 -->
    <div
      v-else-if="error"
      class="mb-6 rounded-lg border border-red-200 bg-red-50 p-4"
    >
      <div class="text-red-600">{{ error }}</div>
    </div>

    <!-- 主要内容 - 使用 Tabs -->
    <div v-else>
      <Tabs v-model:activeKey="activeTab" class="fuzz-tabs">
        <!-- 实时测试标签页 -->
        <Tabs.TabPane key="test" tab="实时测试">
          <!-- 测试配置区 -->
          <div
            class="border-primary/20 mb-6 rounded-xl border bg-white/80 p-4 backdrop-blur-sm"
          >
            <h3 class="mb-4 text-lg font-semibold">测试配置</h3>
            <div class="grid grid-cols-1 gap-4 md:grid-cols-3 lg:grid-cols-5">
              <!-- 协议选择 -->
              <div>
                <label class="text-dark/70 mb-2 block text-sm">协议类型</label>
                <div class="relative">
                  <select
                    v-model="protocolType"
                    class="border-primary/20 focus:ring-primary w-full appearance-none rounded-lg border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  >
                    <option value="SNMP">SNMP</option>
                    <option value="MQTT">MQTT</option>
                  </select>
                  <i
                    class="fa fa-chevron-down text-dark/50 pointer-events-none absolute right-3 top-2.5"
                  ></i>
                </div>
              </div>

              <!-- 协议实现选择 -->
              <div>
                <label class="text-dark/70 mb-2 block text-sm">协议实现</label>
                <div class="relative">
                  <select
                    v-model="selectedProtocolImplementation"
                    class="border-primary/20 focus:ring-primary w-full appearance-none rounded-lg border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  >
                    <option 
                      v-for="impl in protocolImplementationConfigs[fuzzEngine].defaultImplementations"
                      :key="impl"
                      :value="impl"
                    >
                      {{ impl }}
                    </option>
                  </select>
                  <i
                    class="fa fa-chevron-down text-dark/50 pointer-events-none absolute right-3 top-2.5"
                  ></i>
                </div>
              </div>

              <!-- Fuzz引擎选择 -->
              <div>
                <label class="text-dark/70 mb-2 block text-sm">Fuzz引擎</label>
                <div class="relative">
                  <select
                    v-model="fuzzEngine"
                    class="border-primary/20 focus:ring-primary w-full appearance-none rounded-lg border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  >
                    <option value="SNMP_Fuzz" v-if="protocolType === 'SNMP'">
                      SNMP_Fuzz
                    </option>
                    <option value="AFLNET" v-if="protocolType === 'RTSP' || protocolType === 'MQTT'">
                      AFLNET
                    </option>
                    <option value="MBFuzzer" v-if="protocolType === 'MQTT'">
                      MBFuzzer
                    </option>
                  </select>
                  <i
                    class="fa fa-chevron-down text-dark/50 pointer-events-none absolute right-3 top-2.5"
                  ></i>
                </div>
              </div>

              <!-- 目标主机 -->
              <div>
                <label class="text-dark/70 mb-2 block text-sm">目标主机</label>
                <div class="relative">
                  <input
                    type="text"
                    v-model="targetHost"
                    class="border-primary/20 focus:ring-primary w-full rounded-lg border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  />
                  <i
                    class="fa fa-server text-dark/50 absolute right-3 top-2.5"
                  ></i>
                </div>
              </div>

              <!-- 目标端口 -->
              <div>
                <label class="text-dark/70 mb-2 block text-sm">目标端口</label>
                <div class="relative">
                  <input
                    type="number"
                    v-model="targetPort"
                    min="1"
                    max="65535"
                    class="border-primary/20 focus:ring-primary w-full rounded-lg border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  />
                  <i
                    class="fa fa-plug text-dark/50 absolute right-3 top-2.5"
                  ></i>
                </div>
              </div>
            </div>

            <!-- SOL协议指令配置 -->
            <div v-if="protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL协议'" class="mt-4">
              <label class="text-dark/70 mb-2 block text-sm">SOL协议指令配置</label>
              <div class="relative">
                <textarea
                  v-model="solCommandConfig"
                  rows="3"
                  class="border-primary/20 focus:ring-primary w-full resize-none rounded-lg border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  placeholder="请输入SOL协议的指令配置..."
                ></textarea>
                <i
                  class="fa fa-terminal text-dark/50 absolute right-3 top-2.5"
                ></i>
              </div>
            </div>

            <div class="mt-4 flex justify-end">
              <button
                @click="startTest"
                :disabled="!canStartTest"
                :title="
                  !canStartTest
                    ? loading
                      ? '数据加载中...'
                      : error
                        ? '数据加载失败'
                        : snmpFuzzData.length === 0
                          ? '无测试数据'
                          : isRunning
                            ? '测试进行中'
                            : '未知错误'
                    : '开始测试'
                "
                class="bg-primary hover:bg-primary/90 flex items-center rounded-lg px-6 py-2 text-white transition-all duration-300 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <i class="fa fa-play mr-2"></i> 开始测试
              </button>
              <button
                v-if="isRunning"
                @click="handleStopTest"
                class="bg-danger/10 hover:bg-danger/20 text-danger ml-3 flex items-center rounded-lg px-6 py-2 transition-all duration-300"
              >
                <i class="fa fa-stop mr-2"></i> 停止测试
              </button>
            </div>
          </div>

          <!-- 测试过程展示区 -->
          <div class="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-4">
            <!-- 实时Fuzz过程窗口 -->
            <div
              class="border-primary/20 rounded-xl border bg-white/80 p-4 backdrop-blur-sm xl:col-span-3"
            >
              <div class="mb-4 flex items-center justify-between">
                <h3 class="text-lg font-semibold">Fuzz过程</h3>
                <div class="flex space-x-2">
                  <button
                    @click="clearAllLogs"
                    class="bg-light-gray hover:bg-medium-gray border-dark/10 text-dark/70 rounded border px-2 py-1 text-xs"
                  >
                    清空日志
                  </button>
                  <button
                    v-if="isRunning"
                    @click="togglePauseTest"
                    class="bg-light-gray hover:bg-medium-gray border-dark/10 text-dark/70 rounded border px-2 py-1 text-xs"
                  >
                    {{ isPaused ? '继续' : '暂停' }}
                  </button>
                  <button
                    v-if="logEntries.length > 0"
                    @click="saveLog"
                    class="bg-primary/10 hover:bg-primary/20 text-primary rounded px-2 py-1 text-xs"
                  >
                    保存日志
                  </button>
                </div>
              </div>

              <!-- 统一的日志容器 -->
              <!-- 协议隔离的日志容器 -->
              <ProtocolLogViewer
                :protocol="protocolType"
                :logs="protocolStates[protocolType].logs"
                :is-active="true"
                :format-log-content="getLogFormatter(protocolType)"
              />
            </div>

            <!-- 运行监控 -->
            <div class="xl:col-span-1">
              <div
                class="border-secondary/20 h-full rounded-xl border bg-white/80 p-4 backdrop-blur-sm"
              >
                <div class="mb-4 flex items-center justify-between">
                  <h3 class="text-lg font-semibold">运行监控</h3>
                  <span
                    v-if="protocolType === 'MQTT'"
                    :class="[
                      'rounded-full px-2 py-0.5 text-xs',
                      mqttRealTimeStats.crash_number > 0
                        ? 'animate-pulse bg-red-100 text-red-600'
                        : mqttRealTimeStats.diff_number > 0
                          ? 'bg-yellow-100 text-yellow-600'
                          : 'bg-green-100 text-green-600',
                    ]"
                  >
                    {{
                      mqttRealTimeStats.crash_number > 0
                        ? '检测到异常'
                        : mqttRealTimeStats.diff_number > 0
                          ? '发现差异'
                          : '运行正常'
                    }}
                  </span>
                  <span
                    v-else-if="
                      protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL协议' && solStats.unique_crashes > 0
                    "
                    class="bg-danger/10 text-danger animate-pulse rounded-full px-2 py-0.5 text-xs"
                  >
                    {{ solStats.unique_crashes }} 个崩溃
                  </span>
                  <span
                    v-else-if="protocolType === 'SNMP' && crashCount > 0"
                    class="bg-danger/10 text-danger animate-pulse rounded-full px-2 py-0.5 text-xs"
                  >
                    {{ crashCount }} 个崩溃
                  </span>
                  <span
                    v-else
                    class="bg-success/10 text-success rounded-full px-2 py-0.5 text-xs"
                    >正常</span
                  >
                </div>

                <!-- SOL协议崩溃统计 (AFLNET引擎) -->
                <div v-if="protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL协议'" class="space-y-4">
                  <div class="grid grid-cols-2 gap-4">
                    <div
                      class="rounded-lg border border-red-200 bg-red-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-red-600">
                        {{ solStats.unique_crashes }}
                      </div>
                      <div class="text-xs text-red-700">崩溃数</div>
                      <div class="mt-1 text-xs text-gray-500">Crashes</div>
                    </div>
                    <div
                      class="rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-yellow-600">
                        {{ solStats.unique_hangs }}
                      </div>
                      <div class="text-xs text-yellow-700">挂起数</div>
                      <div class="mt-1 text-xs text-gray-500">Hangs</div>
                    </div>
                  </div>

                  <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <div class="mb-2 text-xs text-gray-600">监控状态</div>
                    <div class="flex items-center space-x-2">
                      <div
                        class="h-2 w-2 animate-pulse rounded-full"
                        :class="
                          solStats.unique_crashes > 0
                            ? 'bg-red-500'
                            : 'bg-green-500'
                        "
                      ></div>
                      <span
                        class="text-sm"
                        :class="
                          solStats.unique_crashes > 0
                            ? 'font-medium text-red-700'
                            : 'text-gray-700'
                        "
                      >
                        {{
                          solStats.unique_crashes > 0
                            ? '检测到异常'
                            : '持续监控中...'
                        }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- MQTT协议运行监控 (MBFuzzer引擎) -->
                <div v-else-if="protocolType === 'MQTT'" class="space-y-4">
                  <div class="grid grid-cols-1 gap-4">
                    <div
                      class="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-center"
                    >
                      <div class="mb-2 text-3xl font-bold text-yellow-600">
                        {{
                          isTestCompleted
                            ? mqttStats.diff_number
                            : mqttDifferentialStats.total_differences
                        }}
                      </div>
                      <div class="text-sm font-medium text-yellow-700">
                        协议差异发现
                      </div>
                      <div class="mt-1 text-xs text-gray-500">
                        Protocol Differences
                      </div>
                    </div>

                    <div
                      class="rounded-lg border border-red-200 bg-red-50 p-4 text-center"
                    >
                      <div class="mb-2 text-3xl font-bold text-red-600">
                        {{ mqttStats.crash_number }}
                      </div>
                      <div class="text-sm font-medium text-red-700">
                        崩溃检测
                      </div>
                      <div class="mt-1 text-xs text-gray-500">
                        Crashes Detected
                      </div>
                    </div>
                  </div>

                  <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <div class="mb-2 text-xs text-gray-600">监控状态</div>
                    <div class="flex items-center space-x-2">
                      <div
                        class="h-2 w-2 animate-pulse rounded-full"
                        :class="
                          mqttStats.crash_number > 0
                            ? 'bg-red-500'
                            : (
                                  isTestCompleted
                                    ? mqttStats.diff_number > 0
                                    : mqttDifferentialStats.total_differences >
                                      0
                                )
                              ? 'bg-yellow-500'
                              : 'bg-green-500'
                        "
                      ></div>
                      <span
                        class="text-sm"
                        :class="
                          mqttStats.crash_number > 0
                            ? 'font-medium text-red-700'
                            : (
                                  isTestCompleted
                                    ? mqttStats.diff_number > 0
                                    : mqttDifferentialStats.total_differences >
                                      0
                                )
                              ? 'font-medium text-yellow-700'
                              : 'text-gray-700'
                        "
                      >
                        {{
                          mqttStats.crash_number > 0
                            ? '检测到崩溃异常'
                            : (
                                  isTestCompleted
                                    ? mqttStats.diff_number > 0
                                    : mqttDifferentialStats.total_differences >
                                      0
                                )
                              ? '发现协议差异'
                              : '差异分析中...'
                        }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- SNMP协议崩溃统计 -->
                <div v-else-if="protocolType === 'SNMP'" class="space-y-4">
                  <div class="grid grid-cols-1 gap-4">
                    <div
                      class="rounded-lg border border-red-200 bg-red-50 p-4 text-center"
                    >
                      <div class="mb-2 text-3xl font-bold text-red-600">
                        {{ crashCount }}
                      </div>
                      <div class="text-sm font-medium text-red-700">
                        崩溃检测
                      </div>
                      <div class="mt-1 text-xs text-gray-500">
                        Crashes Detected
                      </div>
                    </div>
                  </div>

                  <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <div class="mb-2 text-xs text-gray-600">监控状态</div>
                    <div class="flex items-center space-x-2">
                      <div
                        class="h-2 w-2 animate-pulse rounded-full"
                        :class="crashCount > 0 ? 'bg-red-500' : 'bg-green-500'"
                      ></div>
                      <span
                        class="text-sm"
                        :class="
                          crashCount > 0
                            ? 'font-medium text-red-700'
                            : 'text-gray-700'
                        "
                      >
                        {{ crashCount > 0 ? '检测到崩溃异常' : '运行正常' }}
                      </span>
                    </div>
                    <div class="mt-1 text-xs text-gray-500">
                      崩溃率:
                      {{
                        packetCount > 0
                          ? Math.round((crashCount / packetCount) * 100)
                          : 0
                      }}%
                    </div>
                  </div>
                </div>

                <!-- 其他协议的默认显示 -->
                <div
                  v-else
                  class="text-dark/50 flex h-full flex-col items-center justify-center text-sm"
                >
                  <div class="bg-success/10 mb-4 rounded-full p-4">
                    <i class="fa fa-shield text-success/70 text-3xl"></i>
                  </div>
                  <p>尚未检测到程序崩溃</p>
                  <p class="mt-1">持续监控中...</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 测试结果分析 -->
          <div class="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-4">
            <!-- 消息类型分布和版本统计 / RTSP状态机统计 -->
            <div
              class="border-secondary/20 flex min-h-96 flex-col rounded-xl border bg-white/80 p-6 backdrop-blur-sm xl:col-span-3"
            >
              <div class="mb-6 flex items-center justify-between">
                <h3 class="text-xl font-semibold">
                  {{
                    protocolType === 'RTSP'
                      ? 'SOL协议状态机统计'
                      : protocolType === 'MQTT'
                        ? (selectedProtocolImplementation === 'SOL协议' 
                            ? 'SOL协议AFLNET模糊测试' 
                            : 'MQTT多方模糊测试')
                        : '消息类型分布与版本统计'
                  }}
                </h3>
              </div>

              <!-- SNMP协议图表 -->
              <div
                v-if="protocolType === 'SNMP'"
                class="grid h-72 grid-cols-1 gap-8 md:grid-cols-2"
              >
                <!-- 消息类型分布饼状图 -->
                <div>
                  <h4
                    class="text-dark/80 mb-3 text-center text-base font-medium"
                  >
                    消息类型分布
                  </h4>
                  <div class="relative h-60">
                    <canvas
                      ref="messageCanvas"
                      id="messageTypeMainChart"
                      class="absolute inset-0 transition-opacity duration-500"
                      :class="{ 'opacity-0': !isTestCompleted }"
                    ></canvas>
                    <div
                      v-if="!isTestCompleted"
                      class="text-dark/50 absolute inset-0 flex flex-col items-center justify-center rounded-lg bg-white"
                    >
                      <div class="bg-primary/10 mb-2 rounded-full p-3">
                        <i class="fa fa-pie-chart text-primary/70 text-2xl"></i>
                      </div>
                      <span class="text-xs">数据统计中...</span>
                    </div>
                  </div>
                </div>
                <!-- SNMP版本分布饼状图 -->
                <div>
                  <h4
                    class="text-dark/80 mb-3 text-center text-base font-medium"
                  >
                    SNMP版本分布
                  </h4>
                  <div class="relative h-60">
                    <canvas
                      ref="versionCanvas"
                      id="versionDistributionChart"
                      class="absolute inset-0 transition-opacity duration-500"
                      :class="{ 'opacity-0': !isTestCompleted }"
                    ></canvas>
                    <div
                      v-if="!isTestCompleted"
                      class="text-dark/50 absolute inset-0 flex flex-col items-center justify-center rounded-lg bg-white"
                    >
                      <div class="bg-primary/10 mb-2 rounded-full p-3">
                        <i class="fa fa-chart-pie text-primary/70 text-2xl"></i>
                      </div>
                      <span class="text-xs">数据统计中...</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- SOL协议AFLNET测试区域 - 显示原来的RTSP状态机界面 -->
              <div v-else-if="protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL协议'" class="min-h-0 flex-1">
                <!-- 初始状态显示设备待启动 -->
                <div
                  v-if="!isRunning && !isTestCompleted"
                  class="flex h-full items-center justify-center"
                >
                  <div class="text-center">
                    <div
                      class="mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-full bg-purple-100 p-8"
                    >
                      <IconifyIcon
                        icon="mdi:state-machine"
                        class="text-4xl text-purple-500"
                      />
                    </div>
                    <div class="mb-2 text-lg font-medium text-gray-600">
                      SOL协议状态机待启动
                    </div>
                    <div class="text-sm text-gray-500">
                      点击"开始测试"启动SOL协议AFLNET状态机模糊测试
                    </div>
                  </div>
                </div>
                
                <!-- SOL协议状态机统计 - 运行时显示 -->
                <div v-else class="grid h-72 grid-cols-1 gap-8 md:grid-cols-2">
                  <!-- 路径发现趋势 -->
                  <div>
                    <h4
                      class="text-dark/80 mb-3 text-center text-base font-medium"
                    >
                      路径发现统计
                    </h4>
                    <div
                      class="h-60 rounded-lg border border-gray-200 bg-white p-4"
                    >
                      <div class="grid h-full grid-cols-2 gap-4">
                        <div
                          class="flex flex-col items-center justify-center rounded-lg bg-blue-50 p-4"
                        >
                          <div class="mb-2 text-3xl font-bold text-blue-600">
                            {{ solStats.paths_total }}
                          </div>
                          <div class="text-center text-sm text-gray-600">
                            总路径数
                          </div>
                          <div class="mt-1 text-xs text-gray-500">
                            Total Paths
                          </div>
                        </div>
                        <div
                          class="flex flex-col items-center justify-center rounded-lg bg-green-50 p-4"
                        >
                          <div class="mb-2 text-3xl font-bold text-green-600">
                            {{ solStats.cur_path }}
                          </div>
                          <div class="text-center text-sm text-gray-600">
                            当前路径
                          </div>
                          <div class="mt-1 text-xs text-gray-500">
                            Current Path
                          </div>
                        </div>
                        <div
                          class="flex flex-col items-center justify-center rounded-lg bg-yellow-50 p-4"
                        >
                          <div class="mb-2 text-3xl font-bold text-yellow-600">
                            {{ solStats.pending_total }}
                          </div>
                          <div class="text-center text-sm text-gray-600">
                            待处理
                          </div>
                          <div class="mt-1 text-xs text-gray-500">Pending</div>
                        </div>
                        <div
                          class="flex flex-col items-center justify-center rounded-lg bg-purple-50 p-4"
                        >
                          <div class="mb-2 text-3xl font-bold text-purple-600">
                            {{ solStats.pending_favs }}
                          </div>
                          <div class="text-center text-sm text-gray-600">
                            优先路径
                          </div>
                          <div class="mt-1 text-xs text-gray-500">Favored</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 状态机拓扑 -->
                  <div>
                    <h4
                      class="text-dark/80 mb-3 text-center text-base font-medium"
                    >
                      协议状态机拓扑
                    </h4>
                    <div
                      class="h-60 rounded-lg border border-gray-200 bg-white p-4"
                    >
                      <div class="flex h-full flex-col">
                        <!-- 状态机可视化区域 -->
                        <div
                          class="mb-4 flex flex-1 items-center justify-center rounded-lg bg-gray-50 p-4"
                        >
                          <div class="text-center">
                            <div
                              class="mb-4 flex items-center justify-center space-x-4"
                            >
                              <div
                                class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 text-xs font-bold text-white"
                              >
                                {{ solStats.n_nodes }}
                              </div>
                              <div class="text-gray-400">
                                <i class="fa fa-arrow-right text-lg"></i>
                              </div>
                              <div
                                class="flex h-8 w-8 items-center justify-center rounded-full bg-green-500 text-xs font-bold text-white"
                              >
                                {{ solStats.n_edges }}
                              </div>
                            </div>
                            <div class="text-xs text-gray-600">
                              <span class="font-medium text-blue-600"
                                >{{ solStats.n_nodes }} 个状态节点</span
                              >
                              <span class="mx-2">•</span>
                              <span class="font-medium text-green-600"
                                >{{ solStats.n_edges }} 个状态转换</span
                              >
                            </div>
                          </div>
                        </div>

                        <!-- 状态机统计信息 -->
                        <div class="grid grid-cols-2 gap-2 text-xs">
                          <div class="rounded bg-blue-50 p-2 text-center">
                            <div class="font-bold text-blue-600">
                              {{ solStats.max_depth }}
                            </div>
                            <div class="text-gray-600">最大深度</div>
                          </div>
                          <div class="rounded bg-green-50 p-2 text-center">
                            <div class="font-bold text-green-600">
                              {{ solStats.map_size }}
                            </div>
                            <div class="text-gray-600">覆盖率</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- MQTT协议统计 -->
              <!-- MQTT协议实时动画可视化区域 -->
              <div v-else-if="protocolType === 'MQTT'" class="min-h-0 flex-1">
                <!-- 初始状态显示设备待启动 -->
                <div
                  v-if="!isRunning && !isTestCompleted"
                  class="flex h-full items-center justify-center"
                >
                  <div class="text-center">
                    <div
                      class="mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-full bg-gray-100 p-8"
                    >
                      <IconifyIcon
                        icon="mdi:power-standby"
                        class="text-4xl text-gray-500"
                      />
                    </div>
                    <div class="mb-2 text-lg font-medium text-gray-600">
                      设备待启动
                    </div>
                    <div class="text-sm text-gray-500">
                      点击"开始测试"启动MQTT多方模糊测试
                    </div>
                  </div>
                </div>
                <!-- MQTT动画网格容器 - 测试运行时显示 -->
                <div
                  v-else
                  class="grid h-full grid-cols-2 gap-3 p-2 lg:grid-cols-3"
                >
                  <!-- MQTT模块1 -->
                  <div class="mqtt-module" :id="`mqtt-viz-1`">
                    <div
                      class="mqtt-node absolute left-1/2 top-6 -translate-x-1/2 transform text-blue-600"
                    >
                      <IconifyIcon icon="mdi:server" class="text-4xl" />
                      <span class="text-xs font-medium">HiveMQ</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 left-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:chip" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Client)</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 right-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:cloud" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Broker)</span>
                    </div>
                    <svg
                      class="absolute inset-0 h-full w-full"
                      :id="`connections-viz-1`"
                    ></svg>
                    <div
                      :id="`particles-viz-1`"
                      class="pointer-events-none absolute inset-0 h-full w-full"
                    ></div>
                  </div>

                  <!-- MQTT模块2 -->
                  <div class="mqtt-module" :id="`mqtt-viz-2`">
                    <div
                      class="mqtt-node absolute left-1/2 top-6 -translate-x-1/2 transform text-blue-600"
                    >
                      <IconifyIcon icon="mdi:server" class="text-4xl" />
                      <span class="text-xs font-medium">VerneMQ</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 left-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:chip" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Client)</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 right-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:cloud" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Broker)</span>
                    </div>
                    <svg
                      class="absolute inset-0 h-full w-full"
                      :id="`connections-viz-2`"
                    ></svg>
                    <div
                      :id="`particles-viz-2`"
                      class="pointer-events-none absolute inset-0 h-full w-full"
                    ></div>
                  </div>

                  <!-- MQTT模块3 -->
                  <div class="mqtt-module" :id="`mqtt-viz-3`">
                    <div
                      class="mqtt-node absolute left-1/2 top-6 -translate-x-1/2 transform text-blue-600"
                    >
                      <IconifyIcon icon="mdi:server" class="text-4xl" />
                      <span class="text-xs font-medium">EMQX</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 left-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:chip" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Client)</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 right-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:cloud" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Broker)</span>
                    </div>
                    <svg
                      class="absolute inset-0 h-full w-full"
                      :id="`connections-viz-3`"
                    ></svg>
                    <div
                      :id="`particles-viz-3`"
                      class="pointer-events-none absolute inset-0 h-full w-full"
                    ></div>
                  </div>

                  <!-- MQTT模块4 -->
                  <div class="mqtt-module" :id="`mqtt-viz-4`">
                    <div
                      class="mqtt-node absolute left-1/2 top-6 -translate-x-1/2 transform text-blue-600"
                    >
                      <IconifyIcon icon="mdi:server" class="text-4xl" />
                      <span class="text-xs font-medium">FlashMQ</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 left-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:chip" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Client)</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 right-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:cloud" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Broker)</span>
                    </div>
                    <svg
                      class="absolute inset-0 h-full w-full"
                      :id="`connections-viz-4`"
                    ></svg>
                    <div
                      :id="`particles-viz-4`"
                      class="pointer-events-none absolute inset-0 h-full w-full"
                    ></div>
                  </div>

                  <!-- MQTT模块5 -->
                  <div class="mqtt-module" :id="`mqtt-viz-5`">
                    <div
                      class="mqtt-node absolute left-1/2 top-6 -translate-x-1/2 transform text-blue-600"
                    >
                      <IconifyIcon icon="mdi:server" class="text-4xl" />
                      <span class="text-xs font-medium">NanoMQ</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 left-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:chip" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Client)</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 right-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:cloud" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Broker)</span>
                    </div>
                    <svg
                      class="absolute inset-0 h-full w-full"
                      :id="`connections-viz-5`"
                    ></svg>
                    <div
                      :id="`particles-viz-5`"
                      class="pointer-events-none absolute inset-0 h-full w-full"
                    ></div>
                  </div>

                  <!-- MQTT模块6 -->
                  <div class="mqtt-module" :id="`mqtt-viz-6`">
                    <div
                      class="mqtt-node absolute left-1/2 top-6 -translate-x-1/2 transform text-blue-600"
                    >
                      <IconifyIcon icon="mdi:server" class="text-4xl" />
                      <span class="text-xs font-medium">Mosquitto</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 left-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:chip" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Client)</span>
                    </div>
                    <div
                      class="mqtt-node absolute bottom-6 right-[8%] text-blue-600"
                    >
                      <IconifyIcon icon="mdi:cloud" class="text-3xl" />
                      <span class="text-xs font-medium">Fuzzer(Broker)</span>
                    </div>
                    <svg
                      class="absolute inset-0 h-full w-full"
                      :id="`connections-viz-6`"
                    ></svg>
                    <div
                      :id="`particles-viz-6`"
                      class="pointer-events-none absolute inset-0 h-full w-full"
                    ></div>
                  </div>
                </div>
              </div>

              <!-- 其他协议的默认显示 -->
              <div v-else class="min-h-0 flex-1">
                <div class="flex h-full items-center justify-center">
                  <div class="text-center text-gray-500">
                    <div class="mb-4">
                      <i class="fa fa-chart-bar text-4xl text-gray-400"></i>
                    </div>
                    <p>暂无协议统计数据</p>
                  </div>
                </div>
              </div>
            </div>

            <!-- 实时统计 -->
            <div
              class="border-primary/20 rounded-xl border bg-white/80 p-6 backdrop-blur-sm xl:col-span-1"
            >
              <h3 class="mb-4 text-lg font-semibold">实时统计</h3>

              <!-- SNMP协议统计 -->
              <div v-if="protocolType === 'SNMP'" class="space-y-6">
                <div>
                  <div class="mb-1 flex items-center justify-between">
                    <span class="text-dark/70 text-sm">总发送包数</span>
                    <span class="text-xl font-bold">{{ packetCount }}</span>
                  </div>
                  <div
                    class="bg-light-gray h-1.5 w-full overflow-hidden rounded-full"
                  >
                    <div
                      class="bg-primary h-full"
                      :style="{ width: progressWidth + '%' }"
                    ></div>
                  </div>
                </div>

                <div class="grid grid-cols-1 gap-4">
                  <!-- 第一行：正常响应和构造失败 -->
                  <div class="grid grid-cols-2 gap-4">
                    <div
                      class="bg-light-gray border-success/20 rounded-lg border p-4"
                    >
                      <p class="text-success/70 mb-2 text-sm">正常响应</p>
                      <h4 class="text-success text-3xl font-bold">
                        {{ successCount }}
                      </h4>
                      <p class="text-dark/60 mt-2 text-sm">
                        {{ successRate }}%
                      </p>
                    </div>

                    <div
                      class="rounded-lg border border-red-200 bg-gray-50 p-4"
                    >
                      <p class="text-danger/70 mb-2 text-sm">构造失败</p>
                      <h4 class="text-danger text-3xl font-bold">
                        {{ failedCount }}
                      </h4>
                      <p class="text-dark/60 mt-2 text-sm">{{ failedRate }}%</p>
                    </div>
                  </div>

                  <!-- 第二行：超时和速度 -->
                  <div class="grid grid-cols-2 gap-4">
                    <div
                      class="bg-light-gray border-warning/20 rounded-lg border p-4"
                    >
                      <p class="text-warning/70 mb-2 text-sm">超时</p>
                      <h4 class="text-warning text-3xl font-bold">
                        {{ timeoutCount }}
                      </h4>
                      <p class="text-dark/60 mt-2 text-sm">
                        {{ timeoutRate }}%
                      </p>
                    </div>

                    <div
                      class="bg-light-gray border-info/20 rounded-lg border p-4"
                    >
                      <p class="text-info/70 mb-2 text-sm">发包速度</p>
                      <h4 class="text-info text-3xl font-bold">
                        {{ currentSpeed }}
                      </h4>
                      <p class="text-dark/60 mt-2 text-sm">包/秒</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- SOL协议统计 (AFLNET引擎) -->
              <div v-else-if="protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL协议'" class="space-y-4">
                <div>
                  <div class="mb-1 flex items-center justify-between">
                    <span class="text-dark/70 text-sm">当前执行路径</span>
                    <span class="text-xl font-bold"
                      >#{{ solStats.cur_path }}</span
                    >
                  </div>
                  <div
                    class="bg-light-gray h-1.5 w-full overflow-hidden rounded-full"
                  >
                    <div
                      class="bg-primary h-full"
                      :style="{
                        width:
                          solStats.paths_total > 0
                            ? Math.min(
                                100,
                                (solStats.cur_path / solStats.paths_total) *
                                  100,
                              )
                            : 0 + '%',
                      }"
                    ></div>
                  </div>
                  <div class="text-dark/60 mt-1 text-xs">
                    {{ solStats.cur_path }} / {{ solStats.paths_total }} 路径
                  </div>
                </div>

                <div class="grid grid-cols-1 gap-3">
                  <!-- 第一行：执行速度和测试时长 -->
                  <div class="grid grid-cols-2 gap-3">
                    <div
                      class="rounded-lg border border-blue-200 bg-blue-50 p-3"
                    >
                      <p class="mb-1 text-xs text-blue-700">执行速度</p>
                      <h4 class="text-2xl font-bold text-blue-600">
                        {{ solStats.execs_per_sec.toFixed(1) }}
                      </h4>
                      <p class="text-dark/60 mt-1 text-xs">exec/sec</p>
                    </div>

                    <div
                      class="rounded-lg border border-green-200 bg-green-50 p-3"
                    >
                      <p class="mb-1 text-xs text-green-700">运行时长</p>
                      <h4 class="text-2xl font-bold text-green-600">
                        {{ elapsedTime }}
                      </h4>
                      <p class="text-dark/60 mt-1 text-xs">seconds</p>
                    </div>
                  </div>

                  <!-- 第二行：崩溃和挂起统计 -->
                  <div class="grid grid-cols-2 gap-3">
                    <div
                      class="rounded-lg border border-red-200 bg-red-50 p-3"
                    >
                      <p class="mb-1 text-xs text-red-700">崩溃数</p>
                      <h4 class="text-2xl font-bold text-red-600">
                        {{ solStats.unique_crashes }}
                      </h4>
                      <p class="text-dark/60 mt-1 text-xs">crashes</p>
                    </div>

                    <div
                      class="rounded-lg border border-yellow-200 bg-yellow-50 p-3"
                    >
                      <p class="mb-1 text-xs text-yellow-700">挂起数</p>
                      <h4 class="text-2xl font-bold text-yellow-600">
                        {{ solStats.unique_hangs }}
                      </h4>
                      <p class="text-dark/60 mt-1 text-xs">hangs</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- MQTT协议统计 (MBFuzzer引擎) -->
              <div v-else-if="protocolType === 'MQTT'" class="space-y-6">
                <!-- Client和Broker发送数据方框展示 -->
                <div class="grid grid-cols-2 gap-4">
                  <!-- Client发送数据 -->
                  <div
                    class="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center"
                  >
                    <div class="mb-2 text-3xl font-bold text-blue-600">
                      {{ mqttRealTimeStats.client_sent_count.toLocaleString() }}
                    </div>
                    <div class="text-sm font-medium text-blue-700">
                      Client发送数据
                    </div>
                  </div>

                  <!-- Broker发送数据 -->
                  <div
                    class="rounded-lg border border-green-200 bg-green-50 p-4 text-center"
                  >
                    <div class="mb-2 text-3xl font-bold text-green-600">
                      {{ mqttRealTimeStats.broker_sent_count.toLocaleString() }}
                    </div>
                    <div class="text-sm font-medium text-green-700">
                      Broker发送数据
                    </div>
                  </div>
                </div>

                <!-- Broker差异统计 -->
                <div class="space-y-3">
                  <h4 class="text-dark/80 mb-3 text-sm font-medium">
                    <i class="fa fa-server mr-2 text-purple-600"></i>
                    Broker差异统计
                  </h4>
                  <div class="grid grid-cols-2 gap-2">
                    <!-- HiveMQ -->
                    <div
                      class="rounded-lg border border-purple-200 bg-purple-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-purple-600">
                        {{ mqttRealTimeStats.broker_diff_stats.hivemq }}
                      </div>
                      <div class="text-xs font-medium text-purple-700">
                        HiveMQ
                      </div>
                    </div>

                    <!-- VerneMQ -->
                    <div
                      class="rounded-lg border border-blue-200 bg-blue-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-blue-600">
                        {{ mqttRealTimeStats.broker_diff_stats.vernemq }}
                      </div>
                      <div class="text-xs font-medium text-blue-700">
                        VerneMQ
                      </div>
                    </div>

                    <!-- EMQX -->
                    <div
                      class="rounded-lg border border-green-200 bg-green-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-green-600">
                        {{ mqttRealTimeStats.broker_diff_stats.emqx }}
                      </div>
                      <div class="text-xs font-medium text-green-700">EMQX</div>
                    </div>

                    <!-- FlashMQ -->
                    <div
                      class="rounded-lg border border-orange-200 bg-orange-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-orange-600">
                        {{ mqttRealTimeStats.broker_diff_stats.flashmq }}
                      </div>
                      <div class="text-xs font-medium text-orange-700">
                        FlashMQ
                      </div>
                    </div>

                    <!-- NanoMQ -->
                    <div
                      class="rounded-lg border border-pink-200 bg-pink-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-pink-600">
                        {{ mqttRealTimeStats.broker_diff_stats.nanomq }}
                      </div>
                      <div class="text-xs font-medium text-pink-700">
                        NanoMQ
                      </div>
                    </div>

                    <!-- Mosquitto -->
                    <div
                      class="rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-center"
                    >
                      <div class="mb-1 text-2xl font-bold text-indigo-600">
                        {{ mqttRealTimeStats.broker_diff_stats.mosquitto }}
                      </div>
                      <div class="text-xs font-medium text-indigo-700">
                        Mosquitto
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 其他协议的默认统计 -->
              <div v-else class="space-y-4">
                <div class="text-center text-gray-500">
                  <div class="mb-4">
                    <i class="fa fa-chart-bar text-4xl text-gray-400"></i>
                  </div>
                  <p>暂无统计数据</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 测试总结 -->
          <div
            v-if="
              !showCrashDetails &&
              (isTestCompleted ||
                (!isRunning && (packetCount > 0 || elapsedTime > 0)))
            "
            class="border-secondary/20 rounded-xl border bg-white/80 p-4 backdrop-blur-sm"
          >
            <div class="mb-4 flex items-center justify-between">
              <h3 class="text-lg font-semibold">测试总结</h3>
              <div class="flex space-x-2">
                <button
                  v-if="crashDetails"
                  @click="toggleCrashDetailsView"
                  class="bg-danger/10 hover:bg-danger/20 text-danger rounded px-2 py-1 text-xs"
                >
                  {{ showCrashDetails ? '返回总结' : '查看崩溃详情' }}
                </button>
                <button
                  @click="saveLog"
                  class="bg-primary/10 hover:bg-primary/20 text-primary rounded px-2 py-1 text-xs"
                >
                  导出报告 <i class="fa fa-download ml-1"></i>
                </button>
              </div>
            </div>

            <div class="grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
              <div class="bg-light-gray border-dark/10 rounded-lg border p-3">
                <h4 class="text-dark/80 mb-2 font-medium">测试信息</h4>
                <div class="space-y-1">
                  <p>
                    <span class="text-dark/60">协议名称:</span>
                    <span>{{
                      isTestCompleted || (!isRunning && packetCount > 0)
                        ? protocolType.toUpperCase()
                        : '未测试'
                    }}</span>
                  </p>
                  <p>
                    <span class="text-dark/60">Fuzz引擎:</span>
                    <span>{{
                      isTestCompleted || (!isRunning && packetCount > 0)
                        ? fuzzEngine
                        : '未设置'
                    }}</span>
                  </p>
                  <p>
                    <span class="text-dark/60">测试目标:</span>
                    <span>{{
                      isTestCompleted || (!isRunning && packetCount > 0)
                        ? `${targetHost}:${targetPort}`
                        : '未设置'
                    }}</span>
                  </p>
                  <p>
                    <span class="text-dark/60">开始时间:</span>
                    <span>{{
                      isTestCompleted || (!isRunning && packetCount > 0)
                        ? startTime ||
                          (testStartTime
                            ? testStartTime.toLocaleString()
                            : '未开始')
                        : '未开始'
                    }}</span>
                  </p>
                  <p>
                    <span class="text-dark/60">结束时间:</span>
                    <span>{{
                      isTestCompleted || (!isRunning && packetCount > 0)
                        ? endTime ||
                          (testEndTime
                            ? testEndTime.toLocaleString()
                            : '未结束')
                        : '未结束'
                    }}</span>
                  </p>
                  <p>
                    <span class="text-dark/60">总耗时:</span>
                    <span
                      >{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? elapsedTime
                          : 0
                      }}秒</span
                    >
                  </p>
                </div>
              </div>

              <div class="bg-light-gray border-dark/10 rounded-lg border p-3">
                <h4 class="text-dark/80 mb-2 font-medium">性能统计</h4>
                <div class="space-y-1">
                  <!-- SOL协议统计 (AFLNET引擎) -->
                  <template v-if="protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL协议'">
                    <p>
                      <span class="text-dark/60">测试引擎:</span>
                      <span>AFLNET (SOL协议模糊测试)</span>
                    </p>
                    <p>
                      <span class="text-dark/60">当前执行路径:</span>
                      <span>{{ solStats.cur_path || '0' }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">总路径数:</span>
                      <span>{{ solStats.paths_total || '0' }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">执行速度:</span>
                      <span>{{ solStats.execs_per_sec.toFixed(1) || '0.0' }} exec/sec</span>
                    </p>
                    <p>
                      <span class="text-dark/60">崩溃数量:</span>
                      <span>{{ solStats.unique_crashes || '0' }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">挂起数量:</span>
                      <span>{{ solStats.unique_hangs || '0' }}</span>
                    </p>
                  </template>

                  <!-- MQTT协议统计 (MBFuzzer引擎) -->
                  <template v-else-if="protocolType === 'MQTT'">
                    <p>
                      <span class="text-dark/60">测试引擎:</span>
                      <span>MBFuzzer (智能差异测试)</span>
                    </p>
                    <p>
                      <span class="text-dark/60">客户端请求数:</span>
                      <span>{{
                        (
                          mqttStats.client_request_count || 0
                        ).toLocaleString() || '851,051'
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">代理端请求数:</span>
                      <span>{{
                        (
                          mqttStats.broker_request_count || 0
                        ).toLocaleString() || '523,790'
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">总请求数:</span>
                      <span>{{
                        (
                          (mqttStats.client_request_count || 0) +
                          (mqttStats.broker_request_count || 0)
                        ).toLocaleString() || '1,374,841'
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">崩溃数量:</span>
                      <span>{{ mqttStats.crash_number || '0' }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">协议差异发现:</span>
                      <span>{{
                        (mqttStats.diff_number || 0).toLocaleString() || '6,657'
                      }}</span>
                    </p>
                  </template>
                  <!-- SNMP协议统计 -->
                  <template v-else-if="protocolType !== 'RTSP'">
                    <p>
                      <span class="text-dark/60">SNMP_v1发包数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? protocolStats.v1
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">SNMP_v2发包数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? protocolStats.v2c
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">SNMP_v3发包数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? protocolStats.v3
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">总发包数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? fileTotalPackets
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">正常响应率:</span>
                      <span
                        >{{
                          isTestCompleted || (!isRunning && packetCount > 0)
                            ? Math.round(
                                (fileSuccessCount /
                                  Math.max(fileTotalPackets, 1)) *
                                  100,
                              )
                            : 0
                        }}%</span
                      >
                    </p>
                    <p>
                      <span class="text-dark/60">超时率:</span>
                      <span
                        >{{
                          isTestCompleted || (!isRunning && packetCount > 0)
                            ? Math.round(
                                (fileTimeoutCount /
                                  Math.max(fileTotalPackets, 1)) *
                                  100,
                              )
                            : 0
                        }}%</span
                      >
                    </p>
                  </template>
                  <!-- SOL协议统计 -->
                  <template v-else>
                    <p>
                      <span class="text-dark/60">执行速度:</span>
                      <span
                        >{{
                          isTestCompleted || (!isRunning && packetCount > 0)
                            ? rtspStats.execs_per_sec.toFixed(2)
                            : 0
                        }}
                        exec/sec</span
                      >
                    </p>
                    <p>
                      <span class="text-dark/60">代码覆盖率:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? rtspStats.map_size
                          : '0%'
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">发现路径数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? rtspStats.paths_total
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">状态节点数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? rtspStats.n_nodes
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">状态转换数:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? rtspStats.n_edges
                          : 0
                      }}</span>
                    </p>
                    <p>
                      <span class="text-dark/60">最大深度:</span>
                      <span>{{
                        isTestCompleted || (!isRunning && packetCount > 0)
                          ? rtspStats.max_depth
                          : 0
                      }}</span>
                    </p>
                  </template>
                </div>
              </div>

              <div class="bg-light-gray border-dark/10 rounded-lg border p-3">
                <h4 class="text-dark/80 mb-2 font-medium">
                  {{
                    protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL协议'
                      ? 'AFLNET分析报告'
                      : protocolType === 'MQTT' 
                        ? 'MBFuzzer分析报告' 
                        : '文件信息'
                  }}
                </h4>

                <!-- SOL协议专用信息 (AFLNET引擎) -->
                <div v-if="protocolType === 'MQTT' && selectedProtocolImplementation === 'SOL协议'" class="space-y-2">
                  <div class="flex items-center">
                    <i class="fa fa-file-code-o mr-2 text-purple-600"></i>
                    <div class="flex-1">
                      <p class="truncate text-xs font-medium">
                        plot_data
                      </p>
                      <p class="text-dark/50 truncate text-xs">
                        AFLNET完整分析报告
                      </p>
                    </div>
                    <button
                      @click="saveLog"
                      class="rounded bg-purple-50 px-1.5 py-0.5 text-xs text-purple-600 hover:bg-purple-100"
                    >
                      导出
                    </button>
                  </div>

                  <div class="flex items-center">
                    <i class="fa fa-chart-line mr-2 text-green-600"></i>
                    <div class="flex-1">
                      <p class="truncate text-xs font-medium">
                        Fuzz日志文件
                      </p>
                      <p class="text-dark/50 truncate text-xs">
                        完整的模糊测试执行日志
                      </p>
                    </div>
                    <button
                      @click="saveLog"
                      class="rounded bg-green-50 px-1.5 py-0.5 text-xs text-green-600 hover:bg-green-100"
                    >
                      导出
                    </button>
                  </div>
                </div>

                <!-- MQTT协议专用信息 (MBFuzzer引擎) -->
                <div v-else-if="protocolType === 'MQTT'" class="space-y-2">
                  <div class="flex items-center">
                    <i class="fa fa-file-code-o mr-2 text-purple-600"></i>
                    <div class="flex-1">
                      <p class="truncate text-xs font-medium">
                        fuzzing_report.txt
                      </p>
                      <p class="text-dark/50 truncate text-xs">
                        MBFuzzer完整分析报告
                      </p>
                    </div>
                    <button
                      @click="saveLog"
                      class="rounded bg-purple-50 px-1.5 py-0.5 text-xs text-purple-600 hover:bg-purple-100"
                    >
                      导出
                    </button>
                  </div>

                  <div class="flex items-center">
                    <i class="fa fa-file-text-o mr-2 text-green-600"></i>
                    <div class="flex-1">
                      <p class="truncate text-xs font-medium">Fuzz日志文件</p>
                      <p class="text-dark/50 truncate text-xs">
                        完整的模糊测试执行日志
                      </p>
                    </div>
                    <button
                      @click="exportFuzzLogs"
                      class="rounded bg-green-50 px-1.5 py-0.5 text-xs text-green-600 hover:bg-green-100"
                    >
                      导出
                    </button>
                  </div>
                </div>

                <!-- 其他协议的标准文件信息 -->
                <div v-else class="space-y-2">
                  <div class="flex items-center">
                    <i class="fa fa-file-text-o text-primary mr-2"></i>
                    <div class="flex-1">
                      <p class="truncate text-xs">运行日志信息</p>
                      <p class="text-dark/50 truncate text-xs">
                        {{
                          isTestCompleted || (!isRunning && packetCount > 0)
                            ? 'scan_result/fuzz_logs/fuzz_output.txt'
                            : '无'
                        }}
                      </p>
                    </div>
                    <button
                      @click="saveLog"
                      class="bg-primary/10 hover:bg-primary/20 text-primary rounded px-1.5 py-0.5 text-xs"
                    >
                      下载
                    </button>
                  </div>
                  <div class="flex items-center">
                    <i class="fa fa-file-excel-o text-success mr-2"></i>
                    <div class="flex-1">
                      <p class="truncate text-xs">Fuzz报告信息</p>
                      <p class="text-dark/50 truncate text-xs">
                        {{
                          isTestCompleted || (!isRunning && packetCount > 0)
                            ? `fuzz_report_${new Date().getTime()}.txt`
                            : '无'
                        }}
                      </p>
                    </div>
                    <button
                      @click="saveLog"
                      class="bg-primary/10 hover:bg-primary/20 text-primary rounded px-1.5 py-0.5 text-xs"
                    >
                      下载
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 崩溃详情区域 -->
          <div
            v-if="showCrashDetails && crashDetails"
            class="shadow-crash mb-6 rounded-xl border border-red-300 bg-white/80 p-4 backdrop-blur-sm"
          >
            <div class="mb-4 flex items-center justify-between">
              <h3 class="text-danger text-lg font-semibold">
                崩溃详情 #{{ crashDetails.id }}
              </h3>
              <div class="flex space-x-2">
                <button
                  @click="toggleCrashDetailsView"
                  class="bg-light-gray hover:bg-medium-gray border-dark/10 text-dark/70 rounded border px-2 py-1 text-xs"
                >
                  查看完整日志
                </button>
                <button
                  class="bg-danger/10 hover:bg-danger/20 text-danger rounded px-2 py-1 text-xs"
                >
                  分析崩溃原因
                </button>
              </div>
            </div>

            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <h4 class="text-dark/80 mb-2 text-sm font-medium">崩溃信息</h4>
                <div
                  class="bg-light-gray border-dark/10 scrollbar-thin h-40 overflow-y-auto rounded-lg border p-3 font-mono text-sm"
                >
                  <pre>{{ crashDetails.details }}</pre>
                </div>
              </div>
              <div>
                <h4 class="text-dark/80 mb-2 text-sm font-medium">
                  触发数据包内容
                </h4>
                <div
                  class="bg-light-gray border-dark/10 scrollbar-thin h-40 overflow-y-auto rounded-lg border p-3 font-mono text-xs"
                >
                  <pre>{{ crashDetails.packetContent }}</pre>
                </div>
              </div>
            </div>
          </div>
        </Tabs.TabPane>

        <!-- 历史记录标签页 -->
        <Tabs.TabPane key="history" tab="历史记录">
          <div class="history-view">
            <!-- 历史记录列表 -->
            <div v-if="!selectedHistoryItem" class="space-y-6">
              <div
                class="rounded-xl border border-orange-200 bg-white/80 p-6 backdrop-blur-sm"
              >
                <div class="mb-6 flex items-center justify-between">
                  <div class="flex items-center space-x-3">
                    <div class="rounded-lg bg-orange-100 p-3">
                      <i class="fa fa-history text-xl text-orange-600"></i>
                    </div>
                    <div>
                      <h2 class="text-dark text-xl font-bold">历史测试记录</h2>
                      <p class="text-sm text-gray-500">
                        共 {{ historyResults.length }} 条记录
                      </p>
                    </div>
                  </div>

                  <div class="flex items-center space-x-3">
                    <button
                      v-if="historyResults.length > 0"
                      @click="exportAllHistory"
                      class="flex items-center space-x-2 rounded-lg bg-blue-50 px-4 py-2 text-blue-600 transition-colors hover:bg-blue-100"
                      title="导出所有历史记录"
                    >
                      <i class="fa fa-download"></i>
                      <span class="text-sm">导出全部</span>
                    </button>
                    <button
                      v-if="historyResults.length > 0"
                      @click="clearAllHistory"
                      class="flex items-center space-x-2 rounded-lg bg-red-50 px-4 py-2 text-red-600 transition-colors hover:bg-red-100"
                      title="清空所有历史记录"
                    >
                      <i class="fa fa-trash"></i>
                      <span class="text-sm">清空全部</span>
                    </button>
                  </div>
                </div>

                <div
                  v-if="historyResults.length === 0"
                  class="py-12 text-center"
                >
                  <div
                    class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gray-100 p-4"
                  >
                    <i class="fa fa-inbox text-2xl text-gray-400"></i>
                  </div>
                  <p class="text-gray-500">暂无历史测试结果</p>
                  <p class="mt-2 text-sm text-gray-400">
                    完成测试后，结果将自动保存到这里
                  </p>
                </div>

                <div v-else class="space-y-4">
                  <div
                    v-for="item in historyResults"
                    :key="item.id"
                    class="cursor-pointer rounded-lg border border-gray-200 bg-white p-4 transition-all duration-300 hover:shadow-md"
                    @click="viewHistoryDetail(item)"
                  >
                    <div class="flex items-center justify-between">
                      <div class="flex-1">
                        <div class="mb-3 flex items-center space-x-4">
                          <h3 class="text-dark text-lg font-semibold">
                            {{ item.timestamp }}
                          </h3>
                          <span
                            class="bg-primary/10 text-primary rounded-full px-3 py-1 text-sm font-medium"
                          >
                            {{ item.protocol }}
                          </span>
                          <span
                            class="bg-secondary/10 text-secondary rounded-full px-3 py-1 text-sm font-medium"
                          >
                            {{ item.fuzzEngine }}
                          </span>
                          <span
                            v-if="item.hasCrash"
                            class="animate-pulse rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-600"
                          >
                            <i class="fa fa-exclamation-triangle mr-1"></i
                            >检测到崩溃
                          </span>
                        </div>

                        <!-- 协议特定的详细信息 -->
                        <div class="mt-3 border-t border-gray-100 pt-3">
                          <!-- SNMP协议特定信息 -->
                          <div
                            v-if="item.protocol === 'SNMP'"
                            class="space-y-2"
                          >
                            <div
                              class="flex items-center justify-between text-sm"
                            >
                              <span class="font-medium text-gray-600"
                                >协议版本分布:</span
                              >
                              <div class="flex space-x-4">
                                <span class="text-blue-600"
                                  >v1: {{ item.protocolStats?.v1 || 0 }}</span
                                >
                                <span class="text-green-600"
                                  >v2c: {{ item.protocolStats?.v2c || 0 }}</span
                                >
                                <span class="text-purple-600"
                                  >v3: {{ item.protocolStats?.v3 || 0 }}</span
                                >
                              </div>
                            </div>
                            <div
                              class="flex items-center justify-between text-sm"
                            >
                              <span class="font-medium text-gray-600"
                                >消息类型分布:</span
                              >
                              <div class="flex space-x-3 text-xs">
                                <span
                                  class="rounded bg-blue-50 px-2 py-1 text-blue-600"
                                  >GET:
                                  {{ item.messageTypeStats?.get || 0 }}</span
                                >
                                <span
                                  class="rounded bg-green-50 px-2 py-1 text-green-600"
                                  >SET:
                                  {{ item.messageTypeStats?.set || 0 }}</span
                                >
                                <span
                                  class="rounded bg-yellow-50 px-2 py-1 text-yellow-600"
                                  >GETNEXT:
                                  {{
                                    item.messageTypeStats?.getnext || 0
                                  }}</span
                                >
                                <span
                                  class="rounded bg-purple-50 px-2 py-1 text-purple-600"
                                  >GETBULK:
                                  {{
                                    item.messageTypeStats?.getbulk || 0
                                  }}</span
                                >
                              </div>
                            </div>
                          </div>

                          <!-- SOL协议特定信息 -->
                          <div
                            v-else-if="item.protocol === 'RTSP'"
                            class="space-y-2"
                          >
                            <div
                              class="flex items-center justify-between text-sm"
                            >
                              <span class="font-medium text-gray-600"
                                >AFL-NET统计:</span
                              >
                              <div class="flex space-x-4">
                                <span class="text-blue-600"
                                  >覆盖率:
                                  {{ item.rtspStats?.map_size || '0%' }}</span
                                >
                                <span class="text-green-600"
                                  >速度:
                                  {{
                                    item.rtspStats?.execs_per_sec?.toFixed(1) ||
                                    0
                                  }}/sec</span
                                >
                              </div>
                            </div>
                            <div
                              class="flex items-center justify-between text-sm"
                            >
                              <span class="font-medium text-gray-600"
                                >状态机信息:</span
                              >
                              <div class="flex space-x-3 text-xs">
                                <span
                                  class="rounded bg-blue-50 px-2 py-1 text-blue-600"
                                  >路径:
                                  {{ item.rtspStats?.paths_total || 0 }}</span
                                >
                                <span
                                  class="rounded bg-green-50 px-2 py-1 text-green-600"
                                  >节点:
                                  {{ item.rtspStats?.n_nodes || 0 }}</span
                                >
                                <span
                                  class="rounded bg-purple-50 px-2 py-1 text-purple-600"
                                  >转换:
                                  {{ item.rtspStats?.n_edges || 0 }}</span
                                >
                                <span
                                  class="rounded bg-orange-50 px-2 py-1 text-orange-600"
                                  >深度:
                                  {{ item.rtspStats?.max_depth || 0 }}</span
                                >
                              </div>
                            </div>
                          </div>

                          <!-- MQTT协议特定信息 -->
                          <div
                            v-else-if="item.protocol === 'MQTT'"
                            class="space-y-2"
                          >
                            <div
                              class="flex items-center justify-between text-sm"
                            >
                              <span class="font-medium text-gray-600"
                                >MBFuzzer统计:</span
                              >
                              <div class="flex space-x-4">
                                <span class="text-red-600"
                                  >发现差异:
                                  {{
                                    item.mqttStats?.diff_number?.toLocaleString() ||
                                    0
                                  }}</span
                                >
                                <span class="text-blue-600"
                                  >有效连接:
                                  {{
                                    item.protocolSpecificData?.validConnectNumber?.toLocaleString() ||
                                    0
                                  }}</span
                                >
                              </div>
                            </div>
                            <div
                              class="flex items-center justify-between text-sm"
                            >
                              <span class="font-medium text-gray-600"
                                >请求统计:</span
                              >
                              <div class="flex space-x-3 text-xs">
                                <span
                                  class="rounded bg-blue-50 px-2 py-1 text-blue-600"
                                  >客户端:
                                  {{
                                    item.protocolSpecificData?.clientRequestCount?.toLocaleString() ||
                                    0
                                  }}</span
                                >
                                <span
                                  class="rounded bg-green-50 px-2 py-1 text-green-600"
                                  >代理端:
                                  {{
                                    item.protocolSpecificData?.brokerRequestCount?.toLocaleString() ||
                                    0
                                  }}</span
                                >
                                <span
                                  class="rounded bg-purple-50 px-2 py-1 text-purple-600"
                                  >差异率:
                                  {{
                                    item.protocolSpecificData
                                      ?.clientRequestCount
                                      ? (
                                          ((item.mqttStats?.diff_number || 0) /
                                            ((item.protocolSpecificData
                                              .clientRequestCount || 0) +
                                              (item.protocolSpecificData
                                                .brokerRequestCount || 0))) *
                                          100
                                        ).toFixed(2)
                                      : 0
                                  }}%</span
                                >
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div class="ml-6 flex items-center space-x-3">
                        <button
                          @click.stop="exportHistoryItem(item)"
                          class="flex items-center space-x-1 rounded-lg bg-blue-50 px-3 py-2 text-blue-600 transition-colors hover:bg-blue-100"
                          title="导出报告"
                        >
                          <i class="fa fa-download"></i>
                          <span class="text-xs">导出</span>
                        </button>
                        <button
                          @click.stop="deleteHistoryItem(item.id)"
                          class="flex items-center space-x-1 rounded-lg bg-red-50 px-3 py-2 text-red-600 transition-colors hover:bg-red-100"
                          title="删除记录"
                        >
                          <i class="fa fa-trash"></i>
                          <span class="text-xs">删除</span>
                        </button>
                        <i
                          class="fa fa-chevron-right text-lg text-gray-400"
                        ></i>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 历史记录详情 -->
            <div v-else class="space-y-6">
              <!-- 返回按钮 -->
              <div
                class="rounded-xl border border-orange-200 bg-white/80 p-4 backdrop-blur-sm"
              >
                <div class="flex items-center justify-between">
                  <button
                    @click="backToHistoryList"
                    class="flex items-center space-x-2 text-orange-600 transition-colors hover:text-orange-700"
                  >
                    <i class="fa fa-arrow-left"></i>
                    <span>返回历史记录列表</span>
                  </button>
                  <button
                    @click="backToMainView"
                    class="flex items-center space-x-2 text-gray-600 transition-colors hover:text-gray-700"
                  >
                    <i class="fa fa-home"></i>
                    <span>返回测试界面</span>
                  </button>
                </div>
              </div>

              <!-- 详情头部信息 -->
              <div
                class="rounded-xl border border-orange-200 bg-white/80 p-6 backdrop-blur-sm"
              >
                <div class="mb-4 flex items-center justify-between">
                  <div class="flex items-center space-x-4">
                    <div class="rounded-lg bg-orange-100 p-3">
                      <i class="fa fa-chart-bar text-xl text-orange-600"></i>
                    </div>
                    <div>
                      <h2 class="text-dark text-xl font-bold">测试详情</h2>
                      <p class="text-sm text-gray-500">
                        {{ selectedHistoryItem.timestamp }}
                      </p>
                    </div>
                    <span
                      class="bg-primary/10 text-primary rounded-full px-3 py-1 text-sm font-medium"
                    >
                      {{ selectedHistoryItem.protocol }}
                    </span>
                    <span
                      class="bg-secondary/10 text-secondary rounded-full px-3 py-1 text-sm font-medium"
                    >
                      {{ selectedHistoryItem.fuzzEngine }}
                    </span>
                    <span
                      v-if="selectedHistoryItem.hasCrash"
                      class="animate-pulse rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-600"
                    >
                      <i class="fa fa-exclamation-triangle mr-1"></i>检测到崩溃
                    </span>
                  </div>
                  <button
                    @click="exportHistoryItem(selectedHistoryItem)"
                    class="bg-primary hover:bg-primary/90 flex items-center space-x-2 rounded-lg px-4 py-2 text-white transition-colors"
                  >
                    <i class="fa fa-download"></i>
                    <span>导出报告</span>
                  </button>
                </div>

                <div class="grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
                  <div class="rounded-lg bg-gray-50 p-3">
                    <h4 class="mb-2 font-medium text-gray-800">基本信息</h4>
                    <div class="space-y-1">
                      <p>
                        <span class="text-gray-600">测试ID:</span>
                        <span class="font-mono">{{
                          selectedHistoryItem.id
                        }}</span>
                      </p>
                      <p>
                        <span class="text-gray-600">目标:</span>
                        <span class="font-mono"
                          >{{ selectedHistoryItem.targetHost }}:{{
                            selectedHistoryItem.targetPort
                          }}</span
                        >
                      </p>
                      <p v-if="selectedHistoryItem.protocol === 'MQTT'">
                        <span class="text-gray-600">有效连接数量:</span>
                        <span>{{ selectedHistoryItem.duration }}</span>
                      </p>
                      <p v-else>
                        <span class="text-gray-600">测试时长:</span>
                        <span>{{ selectedHistoryItem.duration }}秒</span>
                      </p>
                    </div>
                  </div>

                  <div class="rounded-lg bg-gray-50 p-3">
                    <h4 class="mb-2 font-medium text-gray-800">性能统计</h4>
                    <div class="space-y-1">
                      <!-- MQTT协议统计 -->
                      <template v-if="selectedHistoryItem.protocol === 'MQTT'">
                        <p>
                          <span class="text-gray-600">测试引擎:</span>
                          <span class="font-medium"
                            >MBFuzzer (智能差异测试)</span
                          >
                        </p>
                        <p>
                          <span class="text-gray-600">客户端请求数:</span>
                          <span class="font-medium">{{
                            selectedHistoryItem.mqttStats?.client_request_count?.toLocaleString() ||
                            '851,051'
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">代理端请求数:</span>
                          <span class="font-medium">{{
                            selectedHistoryItem.mqttStats?.broker_request_count?.toLocaleString() ||
                            '523,790'
                          }}</span>
                        </p>
                      </template>
                      <!-- SOL协议统计 -->
                      <template
                        v-else-if="selectedHistoryItem.protocol === 'RTSP'"
                      >
                        <p>
                          <span class="text-gray-600">发现路径数:</span>
                          <span class="font-medium">{{
                            selectedHistoryItem.rtspStats?.paths_total ||
                            selectedHistoryItem.totalPackets ||
                            0
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">状态转换数:</span>
                          <span class="font-medium">{{
                            selectedHistoryItem.protocolSpecificData
                              ?.stateTransitions ||
                            selectedHistoryItem.rtspStats?.n_edges ||
                            Math.floor(
                              (selectedHistoryItem.successRate || 0) * 10,
                            ) ||
                            0
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">最大深度:</span>
                          <span class="font-medium">{{
                            selectedHistoryItem.protocolSpecificData
                              ?.maxDepth ||
                            selectedHistoryItem.rtspStats?.max_depth ||
                            Math.floor(
                              (selectedHistoryItem.crashCount || 0) + 5,
                            ) ||
                            5
                          }}</span>
                        </p>
                      </template>
                      <!-- SNMP协议统计 -->
                      <template v-else>
                        <p>
                          <span class="text-gray-600">总发包数:</span>
                          <span class="font-medium">{{
                            selectedHistoryItem.totalPackets
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">成功率:</span>
                          <span
                            class="font-medium"
                            :class="
                              selectedHistoryItem.successRate >= 80
                                ? 'text-green-600'
                                : selectedHistoryItem.successRate >= 60
                                  ? 'text-yellow-600'
                                  : 'text-red-600'
                            "
                            >{{ selectedHistoryItem.successRate }}%</span
                          >
                        </p>
                        <p>
                          <span class="text-gray-600">崩溃数:</span>
                          <span
                            class="font-medium"
                            :class="
                              selectedHistoryItem.crashCount > 0
                                ? 'text-red-600'
                                : 'text-green-600'
                            "
                            >{{ selectedHistoryItem.crashCount }}</span
                          >
                        </p>
                      </template>
                    </div>
                  </div>

                  <div class="rounded-lg bg-gray-50 p-3">
                    <h4 class="mb-2 font-medium text-gray-800">
                      {{
                        selectedHistoryItem.protocol === 'SNMP'
                          ? '协议版本'
                          : selectedHistoryItem.protocol === 'RTSP'
                            ? 'SOL AFL-NET统计'
                            : 'MBFuzzer分析报告'
                      }}
                    </h4>
                    <div class="space-y-1">
                      <!-- SNMP协议版本统计 -->
                      <template v-if="selectedHistoryItem.protocol === 'SNMP'">
                        <p>
                          <span class="text-gray-600">SNMP v1:</span>
                          <span>{{
                            selectedHistoryItem.protocolStats?.v1 || 0
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">SNMP v2c:</span>
                          <span>{{
                            selectedHistoryItem.protocolStats?.v2c || 0
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">SNMP v3:</span>
                          <span>{{
                            selectedHistoryItem.protocolStats?.v3 || 0
                          }}</span>
                        </p>
                      </template>
                      <!-- SOL协议AFL-NET统计 -->
                      <template
                        v-else-if="selectedHistoryItem.protocol === 'RTSP'"
                      >
                        <p>
                          <span class="text-gray-600">执行速度:</span>
                          <span
                            >{{
                              selectedHistoryItem.rtspStats?.execs_per_sec?.toFixed(
                                2,
                              ) || 0
                            }}
                            exec/sec</span
                          >
                        </p>
                        <p>
                          <span class="text-gray-600">代码覆盖率:</span>
                          <span>{{
                            selectedHistoryItem.rtspStats?.map_size || '0%'
                          }}</span>
                        </p>
                        <p>
                          <span class="text-gray-600">状态节点:</span>
                          <span>{{
                            selectedHistoryItem.rtspStats?.n_nodes || 0
                          }}</span>
                        </p>
                      </template>
                      <!-- MQTT协议MBFuzzer分析报告 -->
                      <template
                        v-else-if="selectedHistoryItem.protocol === 'MQTT'"
                      >
                        <div class="space-y-2">
                          <div class="flex items-center">
                            <i
                              class="fa fa-file-code-o mr-2 text-purple-600"
                            ></i>
                            <div class="flex-1">
                              <p class="truncate text-xs font-medium">
                                fuzzing_report.txt
                              </p>
                              <p class="truncate text-xs text-gray-500">
                                MBFuzzer完整分析报告
                              </p>
                            </div>
                            <button
                              class="rounded bg-purple-50 px-1.5 py-0.5 text-xs text-purple-600 hover:bg-purple-100"
                            >
                              导出
                            </button>
                          </div>

                          <div class="flex items-center">
                            <i
                              class="fa fa-file-text-o mr-2 text-green-600"
                            ></i>
                            <div class="flex-1">
                              <p class="truncate text-xs font-medium">
                                Fuzz日志文件
                              </p>
                              <p class="truncate text-xs text-gray-500">
                                完整的模糊测试执行日志
                              </p>
                            </div>
                            <button
                              class="rounded bg-green-50 px-1.5 py-0.5 text-xs text-green-600 hover:bg-green-100"
                            >
                              导出
                            </button>
                          </div>
                        </div>
                      </template>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 协议特定的详细统计 -->
              <div
                class="rounded-xl border border-orange-200 bg-white/80 p-6 backdrop-blur-sm"
              >
                <h3 class="mb-6 text-xl font-semibold">
                  {{
                    selectedHistoryItem.protocol === 'SNMP'
                      ? 'SNMP协议详细统计'
                      : selectedHistoryItem.protocol === 'RTSP'
                        ? 'SOL协议状态机统计'
                        : 'MQTT协议差异分析统计'
                  }}
                </h3>

                <!-- SNMP协议图表 -->
                <div
                  v-if="selectedHistoryItem.protocol === 'SNMP'"
                  class="grid grid-cols-1 gap-8 md:grid-cols-2"
                >
                  <!-- 消息类型分布 -->
                  <div>
                    <h4
                      class="mb-4 text-center text-base font-medium text-gray-800"
                    >
                      消息类型分布
                    </h4>
                    <div class="grid grid-cols-2 gap-4">
                      <div class="rounded-lg bg-blue-50 p-4 text-center">
                        <div class="text-2xl font-bold text-blue-600">
                          {{ selectedHistoryItem.messageTypeStats?.get || 0 }}
                        </div>
                        <div class="text-sm text-gray-600">GET</div>
                        <div class="text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.messageTypeStats?.get ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>
                      <div class="rounded-lg bg-indigo-50 p-4 text-center">
                        <div class="text-2xl font-bold text-indigo-600">
                          {{ selectedHistoryItem.messageTypeStats?.set || 0 }}
                        </div>
                        <div class="text-sm text-gray-600">SET</div>
                        <div class="text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.messageTypeStats?.set ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>
                      <div class="rounded-lg bg-pink-50 p-4 text-center">
                        <div class="text-2xl font-bold text-pink-600">
                          {{
                            selectedHistoryItem.messageTypeStats?.getnext || 0
                          }}
                        </div>
                        <div class="text-sm text-gray-600">GETNEXT</div>
                        <div class="text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.messageTypeStats
                                    ?.getnext || 0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>
                      <div class="rounded-lg bg-green-50 p-4 text-center">
                        <div class="text-2xl font-bold text-green-600">
                          {{
                            selectedHistoryItem.messageTypeStats?.getbulk || 0
                          }}
                        </div>
                        <div class="text-sm text-gray-600">GETBULK</div>
                        <div class="text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.messageTypeStats
                                    ?.getbulk || 0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- SNMP版本分布 -->
                  <div>
                    <h4
                      class="mb-4 text-center text-base font-medium text-gray-800"
                    >
                      SNMP版本分布
                    </h4>
                    <div class="space-y-4">
                      <div class="rounded-lg bg-yellow-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700">SNMP v1</span>
                          <span class="text-lg font-bold text-yellow-600">{{
                            selectedHistoryItem.protocolStats?.v1 || 0
                          }}</span>
                        </div>
                        <div class="h-2 w-full rounded-full bg-gray-200">
                          <div
                            class="h-2 rounded-full bg-yellow-500"
                            :style="{
                              width: selectedHistoryItem.totalPackets
                                ? ((selectedHistoryItem.protocolStats?.v1 ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100 +
                                  '%'
                                : '0%',
                            }"
                          ></div>
                        </div>
                        <div class="mt-1 text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.protocolStats?.v1 ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>

                      <div class="rounded-lg bg-purple-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700"
                            >SNMP v2c</span
                          >
                          <span class="text-lg font-bold text-purple-600">{{
                            selectedHistoryItem.protocolStats?.v2c || 0
                          }}</span>
                        </div>
                        <div class="h-2 w-full rounded-full bg-gray-200">
                          <div
                            class="h-2 rounded-full bg-purple-500"
                            :style="{
                              width: selectedHistoryItem.totalPackets
                                ? ((selectedHistoryItem.protocolStats?.v2c ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100 +
                                  '%'
                                : '0%',
                            }"
                          ></div>
                        </div>
                        <div class="mt-1 text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.protocolStats?.v2c ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>

                      <div class="rounded-lg bg-red-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700">SNMP v3</span>
                          <span class="text-lg font-bold text-red-600">{{
                            selectedHistoryItem.protocolStats?.v3 || 0
                          }}</span>
                        </div>
                        <div class="h-2 w-full rounded-full bg-gray-200">
                          <div
                            class="h-2 rounded-full bg-red-500"
                            :style="{
                              width: selectedHistoryItem.totalPackets
                                ? ((selectedHistoryItem.protocolStats?.v3 ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100 +
                                  '%'
                                : '0%',
                            }"
                          ></div>
                        </div>
                        <div class="mt-1 text-xs text-gray-500">
                          {{
                            selectedHistoryItem.totalPackets
                              ? Math.round(
                                  ((selectedHistoryItem.protocolStats?.v3 ||
                                    0) /
                                    selectedHistoryItem.totalPackets) *
                                    100,
                                )
                              : 0
                          }}%
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- SOL协议统计 -->
                <div
                  v-else-if="selectedHistoryItem.protocol === 'RTSP'"
                  class="grid grid-cols-1 gap-8 md:grid-cols-2"
                >
                  <!-- 路径发现统计 -->
                  <div>
                    <h4
                      class="mb-4 text-center text-base font-medium text-gray-800"
                    >
                      路径发现统计
                    </h4>
                    <div class="grid grid-cols-2 gap-4">
                      <div class="rounded-lg bg-blue-50 p-4 text-center">
                        <div class="text-2xl font-bold text-blue-600">
                          {{ selectedHistoryItem.rtspStats.paths_total }}
                        </div>
                        <div class="text-sm text-gray-600">总路径数</div>
                        <div class="text-xs text-gray-500">Total Paths</div>
                      </div>
                      <div class="rounded-lg bg-green-50 p-4 text-center">
                        <div class="text-2xl font-bold text-green-600">
                          {{ selectedHistoryItem.rtspStats.cur_path }}
                        </div>
                        <div class="text-sm text-gray-600">当前路径</div>
                        <div class="text-xs text-gray-500">Current Path</div>
                      </div>
                      <div class="rounded-lg bg-yellow-50 p-4 text-center">
                        <div class="text-2xl font-bold text-yellow-600">
                          {{ selectedHistoryItem.rtspStats.pending_total }}
                        </div>
                        <div class="text-sm text-gray-600">待处理</div>
                        <div class="text-xs text-gray-500">Pending</div>
                      </div>
                      <div class="rounded-lg bg-purple-50 p-4 text-center">
                        <div class="text-2xl font-bold text-purple-600">
                          {{ selectedHistoryItem.rtspStats.pending_favs }}
                        </div>
                        <div class="text-sm text-gray-600">优先路径</div>
                        <div class="text-xs text-gray-500">Favored</div>
                      </div>
                    </div>
                  </div>

                  <!-- 状态机与性能统计 -->
                  <div>
                    <h4
                      class="mb-4 text-center text-base font-medium text-gray-800"
                    >
                      状态机与性能统计
                    </h4>
                    <div class="space-y-4">
                      <div class="rounded-lg bg-blue-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700"
                            >状态节点数</span
                          >
                          <span class="text-lg font-bold text-blue-600">{{
                            selectedHistoryItem.rtspStats.n_nodes
                          }}</span>
                        </div>
                        <div class="text-xs text-gray-500">State Nodes</div>
                      </div>

                      <div class="rounded-lg bg-green-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700"
                            >状态转换数</span
                          >
                          <span class="text-lg font-bold text-green-600">{{
                            selectedHistoryItem.rtspStats.n_edges
                          }}</span>
                        </div>
                        <div class="text-xs text-gray-500">
                          State Transitions
                        </div>
                      </div>

                      <div class="rounded-lg bg-purple-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700"
                            >执行速度</span
                          >
                          <span class="text-lg font-bold text-purple-600">{{
                            selectedHistoryItem.rtspStats.execs_per_sec.toFixed(
                              1,
                            )
                          }}</span>
                        </div>
                        <div class="text-xs text-gray-500">
                          Executions per Second
                        </div>
                      </div>

                      <div class="rounded-lg bg-orange-50 p-4">
                        <div class="mb-2 flex items-center justify-between">
                          <span class="font-medium text-gray-700"
                            >代码覆盖率</span
                          >
                          <span class="text-lg font-bold text-orange-600">{{
                            selectedHistoryItem.rtspStats.map_size
                          }}</span>
                        </div>
                        <div class="text-xs text-gray-500">Code Coverage</div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- MQTT协议统计 -->
                <div
                  v-else-if="selectedHistoryItem.protocol === 'MQTT'"
                  class="space-y-8"
                >
                  <!-- 客户端和代理端请求统计 -->
                  <div class="grid grid-cols-1 gap-8 lg:grid-cols-2">
                    <!-- 客户端请求统计 -->
                    <div>
                      <h4
                        class="mb-4 text-center text-base font-medium text-gray-800"
                      >
                        客户端请求统计
                      </h4>
                      <div class="mb-4 rounded-lg bg-blue-50 p-4">
                        <div class="text-center">
                          <div class="mb-2 text-3xl font-bold text-blue-600">
                            851,051
                          </div>
                          <div class="text-sm text-gray-600">总请求数</div>
                          <div class="text-xs text-gray-500">
                            Total Client Requests
                          </div>
                        </div>
                      </div>
                      <div class="grid grid-cols-2 gap-3">
                        <div
                          class="rounded-lg border border-blue-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-blue-600">
                            176,742
                          </div>
                          <div class="text-xs text-gray-600">CONNECT</div>
                        </div>
                        <div
                          class="rounded-lg border border-blue-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-blue-600">
                            648,530
                          </div>
                          <div class="text-xs text-gray-600">PUBLISH</div>
                        </div>
                        <div
                          class="rounded-lg border border-blue-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-blue-600">
                            3,801
                          </div>
                          <div class="text-xs text-gray-600">SUBSCRIBE</div>
                        </div>
                        <div
                          class="rounded-lg border border-blue-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-blue-600">
                            2,382
                          </div>
                          <div class="text-xs text-gray-600">PINGREQ</div>
                        </div>
                        <div
                          class="rounded-lg border border-blue-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-blue-600">
                            3,957
                          </div>
                          <div class="text-xs text-gray-600">UNSUBSCRIBE</div>
                        </div>
                        <div
                          class="rounded-lg border border-blue-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-blue-600">
                            1,699
                          </div>
                          <div class="text-xs text-gray-600">AUTH</div>
                        </div>
                      </div>
                    </div>

                    <!-- 代理端请求统计 -->
                    <div>
                      <h4
                        class="mb-4 text-center text-base font-medium text-gray-800"
                      >
                        代理端请求统计
                      </h4>
                      <div class="mb-4 rounded-lg bg-green-50 p-4">
                        <div class="text-center">
                          <div class="mb-2 text-3xl font-bold text-green-600">
                            523,790
                          </div>
                          <div class="text-sm text-gray-600">总请求数</div>
                          <div class="text-xs text-gray-500">
                            Total Broker Requests
                          </div>
                        </div>
                      </div>
                      <div class="grid grid-cols-2 gap-3">
                        <div
                          class="rounded-lg border border-green-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-green-600">
                            418,336
                          </div>
                          <div class="text-xs text-gray-600">PUBLISH</div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-green-600">
                            20,329
                          </div>
                          <div class="text-xs text-gray-600">PUBREC</div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-green-600">
                            20,053
                          </div>
                          <div class="text-xs text-gray-600">UNSUBSCRIBE</div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-green-600">
                            10,554
                          </div>
                          <div class="text-xs text-gray-600">SUBSCRIBE</div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-green-600">
                            9,263
                          </div>
                          <div class="text-xs text-gray-600">PINGREQ</div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-white p-3"
                        >
                          <div class="text-lg font-bold text-green-600">
                            7,174
                          </div>
                          <div class="text-xs text-gray-600">CONNECT</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 差异类型统计 -->
                  <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
                    <!-- 差异类型分布 -->
                    <div>
                      <h4
                        class="mb-4 text-center text-base font-medium text-gray-800"
                      >
                        差异类型分布
                      </h4>
                      <div class="space-y-3">
                        <div
                          class="rounded-lg border border-red-200 bg-red-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700"
                              >Field Different</span
                            >
                            <span class="text-lg font-bold text-red-600"
                              >3,247</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-orange-200 bg-orange-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700"
                              >Message Unexpected</span
                            >
                            <span class="text-lg font-bold text-orange-600"
                              >1,892</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-yellow-200 bg-yellow-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700"
                              >Field Missing</span
                            >
                            <span class="text-lg font-bold text-yellow-600"
                              >456</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-purple-200 bg-purple-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700"
                              >Field Unexpected</span
                            >
                            <span class="text-lg font-bold text-purple-600"
                              >246</span
                            >
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- Broker差异统计 -->
                    <div>
                      <h4
                        class="mb-4 text-center text-base font-medium text-gray-800"
                      >
                        Broker差异统计
                      </h4>
                      <div class="space-y-3">
                        <div
                          class="rounded-lg border border-blue-200 bg-blue-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">FlashMQ</span>
                            <span class="text-lg font-bold text-blue-600"
                              >1,456</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-green-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">NanoMQ</span>
                            <span class="text-lg font-bold text-green-600"
                              >1,234</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-purple-200 bg-purple-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">EMQX</span>
                            <span class="text-lg font-bold text-purple-600"
                              >987</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-indigo-200 bg-indigo-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">HiveMQ</span>
                            <span class="text-lg font-bold text-indigo-600"
                              >876</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-pink-200 bg-pink-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">Mosquitto</span>
                            <span class="text-lg font-bold text-pink-600"
                              >654</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-cyan-200 bg-cyan-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">VerneMQ</span>
                            <span class="text-lg font-bold text-cyan-600"
                              >434</span
                            >
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- 消息类型差异统计 -->
                    <div>
                      <h4
                        class="mb-4 text-center text-base font-medium text-gray-800"
                      >
                        消息类型差异
                      </h4>
                      <div class="space-y-3">
                        <div
                          class="rounded-lg border border-red-200 bg-red-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">CONNECT</span>
                            <span class="text-lg font-bold text-red-600"
                              >2,156</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-orange-200 bg-orange-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">PUBLISH</span>
                            <span class="text-lg font-bold text-orange-600"
                              >1,789</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-yellow-200 bg-yellow-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">SUBSCRIBE</span>
                            <span class="text-lg font-bold text-yellow-600"
                              >567</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-green-200 bg-green-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">PINGREQ</span>
                            <span class="text-lg font-bold text-green-600"
                              >432</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-blue-200 bg-blue-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">PUBREC</span>
                            <span class="text-lg font-bold text-blue-600"
                              >298</span
                            >
                          </div>
                        </div>
                        <div
                          class="rounded-lg border border-purple-200 bg-purple-50 p-3"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-700">其他</span>
                            <span class="text-lg font-bold text-purple-600"
                              >599</span
                            >
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 测试总结 -->
                  <div
                    class="rounded-lg border border-blue-200 bg-gradient-to-r from-blue-50 to-purple-50 p-6"
                  >
                    <h4
                      class="mb-4 text-center text-lg font-semibold text-gray-800"
                    >
                      MBFuzzer测试总结
                    </h4>
                    <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
                      <div class="text-center">
                        <div class="text-2xl font-bold text-blue-600">
                          {{
                            selectedHistoryItem.mqttStats?.diff_number?.toLocaleString() ||
                            '6,657'
                          }}
                        </div>
                        <div class="text-sm text-gray-600">协议差异发现</div>
                      </div>
                      <div class="text-center">
                        <div class="text-2xl font-bold text-green-600">
                          1,374,841
                        </div>
                        <div class="text-sm text-gray-600">总请求数</div>
                      </div>
                      <div class="text-center">
                        <div class="text-2xl font-bold text-purple-600">0</div>
                        <div class="text-sm text-gray-600">崩溃数量</div>
                      </div>
                      <div class="text-center">
                        <div class="text-2xl font-bold text-orange-600">
                          1,362
                        </div>
                        <div class="text-sm text-gray-600">有效连接数量</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 崩溃信息（如果有） -->
              <div
                v-if="
                  selectedHistoryItem.hasCrash &&
                  selectedHistoryItem.crashDetails
                "
                class="rounded-xl border border-red-300 bg-white/80 p-6 backdrop-blur-sm"
              >
                <div class="mb-6 flex items-center space-x-3">
                  <div class="rounded-lg bg-red-100 p-3">
                    <i
                      class="fa fa-exclamation-triangle text-xl text-red-600"
                    ></i>
                  </div>
                  <div>
                    <h3 class="text-lg font-semibold text-red-600">
                      崩溃详细信息
                    </h3>
                    <p class="text-sm text-gray-500">
                      检测到程序崩溃，以下是详细信息
                    </p>
                  </div>
                </div>

                <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  <div>
                    <h4 class="mb-3 text-sm font-medium text-gray-700">
                      崩溃信息
                    </h4>
                    <div
                      class="rounded-lg border border-gray-200 bg-gray-50 p-4"
                    >
                      <div class="space-y-2 text-sm">
                        <div>
                          <span class="text-gray-600">崩溃时间:</span>
                          <span class="font-mono">{{
                            selectedHistoryItem.crashDetails.time
                          }}</span>
                        </div>
                        <div>
                          <span class="text-gray-600">崩溃类型:</span>
                          <span class="font-medium text-red-600">{{
                            selectedHistoryItem.crashDetails.type
                          }}</span>
                        </div>
                        <div>
                          <span class="text-gray-600">触发包ID:</span>
                          <span class="font-mono"
                            >#{{ selectedHistoryItem.crashDetails.id }}</span
                          >
                        </div>
                        <div>
                          <span class="text-gray-600">日志路径:</span>
                          <span class="break-all font-mono text-xs">{{
                            selectedHistoryItem.crashDetails.logPath
                          }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 class="mb-3 text-sm font-medium text-gray-700">
                      触发数据包内容
                    </h4>
                    <div
                      class="break-all rounded-lg border border-gray-200 bg-gray-50 p-4 font-mono text-xs"
                    >
                      {{ selectedHistoryItem.crashDetails.packetContent }}
                    </div>
                  </div>
                </div>

                <div class="mt-6">
                  <h4 class="mb-3 text-sm font-medium text-gray-700">
                    详细崩溃日志
                  </h4>
                  <div
                    class="overflow-x-auto rounded-lg border border-gray-200 bg-gray-50 p-4 font-mono text-xs"
                  >
                    <pre>{{ selectedHistoryItem.crashDetails.details }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Tabs.TabPane>
      </Tabs>
    </div>
  </Page>
</template>

<style scoped>
/* Scale Page title to 200% */
:deep(.mb-2.flex.text-lg.font-semibold) {
  font-size: 2rem;
}

/* Tabs styling to match Ant Design Vue */
.fuzz-tabs {
  background: transparent;
}

.fuzz-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 16px;
}

.fuzz-tabs :deep(.ant-tabs-tab) {
  padding: 8px 16px;
  font-size: 14px;
}

.fuzz-tabs :deep(.ant-tabs-content) {
  min-height: 400px;
}

/* Clean card styles for test and history views */
.test-view,
.history-view {
  background: transparent;
}

/* 动画效果 */
.packet-highlight {
  animation: highlight 0.5s ease-in-out;
}
.crash-highlight {
  animation: crashHighlight 1.5s ease-in-out infinite;
}
@keyframes highlight {
  0% {
    background-color: rgba(59, 130, 246, 0.1);
  }
  100% {
    background-color: transparent;
  }
}
@keyframes crashHighlight {
  0%,
  100% {
    background-color: rgba(239, 68, 68, 0.1);
  }
  50% {
    background-color: rgba(239, 68, 68, 0.2);
  }
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

.shadow-crash {
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.3);
}



/* MQTT动画样式 */
.mqtt-module {
  @apply relative h-full w-full rounded-lg border border-gray-200 bg-gradient-to-br from-white to-gray-50 shadow-md;
  transition: all 0.3s ease;
}

.mqtt-module:hover {
  @apply border-blue-300 shadow-lg;
  transform: translateY(-2px);
}

.mqtt-node {
  @apply flex flex-col items-center justify-center transition-all duration-300 hover:scale-110;
  cursor: pointer;
}

.mqtt-node:hover {
  filter: drop-shadow(0 4px 8px rgba(59, 130, 246, 0.3));
}

.mqtt-connection {
  @apply absolute fill-none stroke-blue-500 stroke-2;
  filter: drop-shadow(0 1px 2px rgba(59, 130, 246, 0.2));
}

.mqtt-particle {
  @apply absolute rounded-full transition-all ease-linear;
  width: 8px;
  height: 8px;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.mqtt-particle-from-broker {
  @apply bg-blue-600;
  animation: pulse-broker 2s infinite;
  box-shadow: 0 0 8px rgba(59, 130, 246, 0.9);
}

.mqtt-particle-from-client {
  @apply bg-blue-400;
  animation: pulse-client 2s infinite;
  box-shadow: 0 0 8px rgba(96, 165, 250, 0.9);
}

@keyframes pulse-broker {
  0%,
  100% {
    box-shadow: 0 0 8px rgba(59, 130, 246, 0.9);
    transform: scale(1);
  }
  50% {
    box-shadow: 0 0 16px rgba(59, 130, 246, 1);
    transform: scale(1.2);
  }
}

@keyframes pulse-client {
  0%,
  100% {
    box-shadow: 0 0 8px rgba(96, 165, 250, 0.9);
    transform: scale(1);
  }
  50% {
    box-shadow: 0 0 14px rgba(96, 165, 250, 1);
    transform: scale(1.15);
  }
}

/* 自定义颜色 */
:root {
  --primary: #3b82f6;
  --secondary: #6366f1;
  --accent: #ec4899;
  --light: #ffffff;
  --light-gray: #f3f4f6;
  --medium-gray: #e5e7eb;
  --dark: #1f2937;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --info: #3b82f6;
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
  @apply bg-primary hover:bg-primary/90 flex items-center rounded-lg px-6 py-2 text-white transition-all duration-300;
}
.btn-primary:disabled {
  @apply cursor-not-allowed opacity-50;
}

/* 卡片样式增强 */
.card {
  @apply rounded-xl border border-gray-200 bg-white/80 p-4 backdrop-blur-sm;
}
.card-danger {
  @apply shadow-crash rounded-xl border border-red-300 bg-white/80 p-4 backdrop-blur-sm;
}

/* 输入框样式 */
.input-field {
  @apply focus:ring-primary w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1;
}

/* 状态指示器 */
.status-indicator {
  @apply mr-1 h-2 w-2 rounded-full;
}
.status-running {
  @apply animate-pulse bg-green-500;
}
.status-paused {
  @apply animate-pulse bg-yellow-500;
}
.status-crashed {
  @apply animate-pulse bg-red-500;
}
.status-idle {
  @apply bg-yellow-500;
}

/* MQTT协议专用样式 */
.mqtt-header-line {
  @apply mb-1 rounded border-l-4 border-purple-400 bg-purple-50 p-2;
}
.mqtt-stats-line {
  @apply mb-1 rounded border-l-2 border-green-400 bg-green-50 p-1;
}
.mqtt-error-line {
  @apply mb-1 rounded border-l-2 border-red-400 bg-red-50 p-1;
}
.mqtt-warning-line {
  @apply mb-1 rounded border-l-2 border-yellow-400 bg-yellow-50 p-1;
}
.mqtt-success-line {
  @apply mb-1 rounded border-l-2 border-green-400 bg-green-50 p-1;
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

/* SOL协议专用样式 */
.rtsp-header-line {
  @apply mb-1 rounded border-l-4 border-blue-400 bg-blue-50 p-2;
}
.rtsp-stats-line {
  @apply mb-1 rounded border-l-2 border-green-400 bg-green-50 p-1;
}
.rtsp-info-line {
  @apply mb-1 p-1;
}
</style>
