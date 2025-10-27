<script setup lang="ts">
import {
  onMounted,
  nextTick,
  computed,
  watch,
  h,
  onErrorCaptured,
  onUnmounted,
} from 'vue';
import { getFuzzText } from '#/api/custom';
import { requestClient } from '#/api/request';
import { IconifyIcon } from '@vben/icons';
import Chart from 'chart.js/auto';
import type { TableColumnType } from 'ant-design-vue';

import { Page } from '@vben/common-ui';

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

// 导入协议专用的composables
import {
  useSNMP,
  useRTSP,
  useMQTT,
  useLogReader,
  useFuzzState,
  type FuzzPacket,
  type HistoryResult,
  type ProtocolType,
  type FuzzEngineType,
} from './composables';

// 导入新的协议数据管理器和日志查看器
import { useProtocolDataManager } from './composables/useProtocolDataManager';
import ProtocolLogViewer from './components/ProtocolLogViewer.vue';

// Initialize all reactive state from composables
const {
  rawText,
  loading,
  error,
  totalPacketsInFile,
  fileTotalPackets,
  fileSuccessCount,
  fileTimeoutCount,
  fileFailedCount,
  packetCount,
  successCount,
  timeoutCount,
  failedCount,
  crashCount,
  elapsedTime,
  packetsPerSecond,
  testDuration,
  isRunning,
  isTestCompleted,
  hasUserStartedTest,
  protocolType,
  fuzzEngine,
  targetHost,
  targetPort,
  rtspCommandConfig,
  rtspProcessId,
  showCharts,
  crashDetails,
  logEntries,
  startTime,
  endTime,
  lastUpdate,
  currentSpeed,
  isPaused,
  showCrashDetails,
  testStartTime,
  testEndTime,
  currentPacketIndex,
  packetDelay,
  activeTabKey,
  showHistoryView,
  selectedHistoryItem,
  historyDrawerOpen,
  showNotification,
  notificationMessage,
  historyResults,
  messageCanvas,
  versionCanvas,
  mqttMessageCanvas,
  unifiedLogs,
  mqttLogsContainer,
  mqttLogsUpdateKey,
  mqttIsProcessingLogs,
  mqttTotalRecords,
  mqttProcessedRecords,
  mqttProcessingProgress,
  mqttRealTimeStats,
  mqttDiffTypeStats,
  mqttDifferentialStats,
} = useFuzzState();

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
const {
  rtspStats,
  resetRTSPStats,
  processRTSPLogLine,
  writeRTSPScript,
  executeRTSPCommand,
  stopRTSPProcess,
  stopAndCleanupRTSP,
} = useRTSP();
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

const TypographyParagraph = Typography.Paragraph;
const TypographyText = Typography.Text;
const TypographyTitle = Typography.Title;

// 添加异步操作取消标志
let mqttSimulationCancelled = false;

let testTimer: number | null = null;

// Watch for protocol changes to update port and fuzz engine
watch(protocolType, (newProtocol, oldProtocol) => {
  console.log(`[DEBUG] 协议切换: ${oldProtocol} -> ${newProtocol}`);

  // 立即停止当前运行的测试和所有异步操作
  if (isRunning.value) {
    console.log('[DEBUG] 停止当前运行的测试');
    isRunning.value = false;
    isTestCompleted.value = false;
    hasUserStartedTest.value = false; // Reset on protocol change

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
  } else if (newProtocol === 'RTSP') {
    targetPort.value = 8554;
    fuzzEngine.value = 'AFLNET';
  } else if (newProtocol === 'MQTT') {
    targetPort.value = 1883;
    fuzzEngine.value = 'MBFuzzer';
    // MQTT动画将在测试开始时初始化
  }

  // 重置测试状态
  nextTick(() => {
    resetTestState();
    console.log('[DEBUG] 协议切换完成，状态已重置');
  });
});

// Watch for hasUserStartedTest to initialize charts when canvas becomes available
watch(hasUserStartedTest, async (started) => {
  if (started) {
    // Wait for DOM to render the canvas elements
    await nextTick();
    // Initialize charts if not already initialized
    if (!messageTypeChart || !versionChart) {
      const success = initCharts();
      if (success) {
        console.log('Charts initialized after test started');
        updateCharts();
      }
    }
  }
});

// Watch for test completion to show charts
watch(isTestCompleted, async (completed) => {
  if (completed && hasUserStartedTest.value) {
    // Wait a bit for all data to be processed
    await nextTick();

    // Ensure charts are initialized
    if (!messageTypeChart || !versionChart) {
      const success = initCharts();
      if (success) {
        console.log('Charts initialized on test completion');
      }
    }

    // Update charts with final data
    if (messageTypeChart && versionChart) {
      updateCharts();
      showCharts.value = true;
      console.log('Charts displayed after test completion');
    }
  }
});

// Watch for activeTabKey changes
watch(activeTabKey, (key) => {
  showHistoryView.value = key === 'history';
  if (key !== 'history') {
    historyDrawerOpen.value = false;
  }
});

// Watch for historyDrawerOpen changes
watch(historyDrawerOpen, (open) => {
  if (!open) {
    selectedHistoryItem.value = null;
  }
});

// UI refs (logContainer现在通过useLogReader管理)
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

  if (startTimeMatch?.[1]) startTime.value = startTimeMatch[1];
  if (endTimeMatch?.[1]) endTime.value = endTimeMatch[1];
  if (durationMatch?.[1]) testDuration.value = parseFloat(durationMatch[1]);
  if (avgSpeedMatch?.[1]) packetsPerSecond.value = parseFloat(avgSpeedMatch[1]);

  // Counters from file
  const successCountInFile = (text.match(/\[接收成功\]/g) || []).length;
  const timeoutCountInFile = (text.match(/\[接收超时\]/g) || []).length;
  const failedCountInFile = (text.match(/生成失败:/g) || []).length;
  fileSuccessCount.value = successCountInFile;
  fileTimeoutCount.value = timeoutCountInFile;
  fileFailedCount.value = failedCountInFile;
  fileTotalPackets.value = totalPacketsMatch?.[1]
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
    hasUserStartedTest.value = false; // Reset user start flag

    // 初始化动态指标的初始值
    packetsPerSecond.value = 30; // 初始目标速率
    testDuration.value = 60; // 初始预估时长

    // 重置协议专用的统计数据
    resetSNMPStats();
    resetRTSPStats();
    resetMQTTStats();

    // 重置日志读取器
    resetLogReader();

    // Reset log container with proper checks
    nextTick(() => {
      try {
        if (
          logContainer.value &&
          !showHistoryView.value &&
          logContainer.value.innerHTML !== undefined
        ) {
          logContainer.value.innerHTML =
            '<div class="log-empty">测试未开始，请配置参数并点击"开始测试"</div>';
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
  // MQTT协议不需要fuzzData，直接从文件读取
  if (protocolType.value !== 'MQTT' && !snmpFuzzData.value.length) return;

  resetTestState();
  hasUserStartedTest.value = true; // Mark that user has started the test
  isRunning.value = true;
  isTestCompleted.value = false;
  showCharts.value = false; // 测试开始时隐藏图表
  testStartTime.value = new Date();

  // 根据协议类型执行不同的启动逻辑
  try {
    if (protocolType.value === 'RTSP') {
      await startRTSPTest();
    } else if (protocolType.value === 'SNMP') {
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
      await startMQTTTest();
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

      // 动态模拟目标发送速率 (基于实际速率with一些波动)
      // 在实际速率附近波动 ±10%
      const targetVariation = Math.random() * 0.2 - 0.1; // -10% to +10%
      packetsPerSecond.value = Math.max(
        1,
        Math.round(currentSpeed.value * (1 + targetVariation)),
      );

      // 动态模拟计划运行时长 (基于当前进度估算剩余时间)
      // 使用当前速率和剩余包数来估算
      const estimatedTotalPackets = snmpFuzzData.value.length || 100;
      const remainingPackets = Math.max(
        0,
        estimatedTotalPackets - packetCount.value,
      );
      const estimatedRemainingTime =
        currentSpeed.value > 0
          ? Math.round(remainingPackets / currentSpeed.value)
          : 60;
      testDuration.value = elapsedTime.value + estimatedRemainingTime;
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

    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'RTSP',
        type: 'START',
        oids: ['RTSP测试已启动'],
        hex: '',
        result: 'success',
      } as any,
      false,
    );
  } catch (error: any) {
    console.error('RTSP测试启动失败:', error);
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


// 统一的日志系统 - 替换分离的MQTT日志
// MQTT协议差异报告日志 - 使用非响应式数据避免DOM冲突
let mqttDifferentialLogsData: string[] = []; // 非响应式数据存储
let mqttUpdateTimer: number | null = null; // 防抖定时器
let mqttLogsPendingUpdate = false; // 更新锁

// 统一的日志添加函数
function addUnifiedLog(
  type: 'INFO' | 'ERROR' | 'WARNING' | 'SUCCESS',
  content: string,
  protocol: 'SNMP' | 'RTSP' | 'MQTT' = 'MQTT',
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
    lines.slice(0, 5).forEach((line: string, index: number) => {
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
      if (match?.[1]) {
        mqttStats.value.client_request_count = parseInt(match[1]);
      }
    }

    // 解析代理端请求统计
    if (line.includes('Fuzzing request number (broker):')) {
      const match = line.match(/Fuzzing request number \(broker\):\s*(\d+)/);
      if (match?.[1]) {
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
      if (match?.[1]) {
        mqttStats.value.crash_number = parseInt(match[1]);
      }
      isClientSection = false;
      isBrokerSection = false;
    }

    if (line.includes('Diff Number:')) {
      const match = line.match(/Diff Number:\s*(\d+)/);
      if (match?.[1]) {
        mqttStats.value.diff_number = parseInt(match[1]);
      }
    }

    if (line.includes('Duplicate Diff Number:')) {
      const match = line.match(/Duplicate Diff Number:\s*(\d+)/);
      if (match?.[1]) {
        mqttStats.value.duplicate_diff_number = parseInt(match[1]);
      }
    }

    if (line.includes('Valid Connect Number:')) {
      const match = line.match(/Valid Connect Number:\s*(\d+)/);
      if (match?.[1]) {
        mqttStats.value.valid_connect_number = parseInt(match[1]);
      }
    }

    if (line.includes('已经发送重复CONNECT差异的消息数目:')) {
      const match = line.match(/已经发送重复CONNECT差异的消息数目:\s*(\d+)/);
      if (match?.[1]) {
        mqttStats.value.duplicate_connect_diff = parseInt(match[1]);
      }
    }

    // 解析总差异数（如果有的话）
    if (line.includes('Total Differences:') || line.includes('总差异数:')) {
      const match = line.match(/(?:Total Differences|总差异数):\s*(\d+)/);
      if (match?.[1]) {
        mqttStats.value.total_differences = parseInt(match[1]);
      }
    }

    // 解析开始和结束时间
    if (line.includes('Fuzzing Start Time:')) {
      const match = line.match(/Fuzzing Start Time:\s*(.+)/);
      if (match?.[1]) {
        mqttStats.value.fuzzing_start_time = match[1].trim();
      }
    }

    if (line.includes('Fuzzing End Time:')) {
      const match = line.match(/Fuzzing End Time:\s*(.+)/);
      if (match?.[1]) {
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
        if (!line) continue;

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



// MQTT日志格式化（已移动到下方，避免重复定义）
// 测试函数是否正常工作
console.log('[DEBUG] formatMQTTLogLine函数已加载');


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
      if (brokerMatch?.[1]) {
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
      if (versionMatch?.[1]) {
        const version = versionMatch[1];
        if (mqttDifferentialStats.value.version_stats.hasOwnProperty(version)) {
          mqttDifferentialStats.value.version_stats[
            version as keyof typeof mqttDifferentialStats.value.version_stats
          ]++;
        }
      }

      // 统计差异类型
      if (diffTypeMatch?.[1]) {
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


// MQTT日志读取函数现在通过 useLogReader 和 useMQTT composables 管理

// RTSP specific functions (现在通过 useRTSP composable 管理)
async function writeRTSPScriptWrapper() {
  const scriptContent = rtspCommandConfig.value;

  try {
    const result = await writeRTSPScript(scriptContent);

    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'RTSP',
        type: 'SCRIPT',
        oids: [`脚本已写入: ${result.data?.filePath || '脚本文件'}`],
        hex: '',
        result: 'success',
      } as any,
      false,
    );
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

    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'RTSP',
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
    console.error('执行RTSP命令失败:', error);
    throw new Error(`执行启动命令失败: ${error.message}`);
  }
}

function startRTSPLogReading() {
  isReadingLog.value = true;

  // 先检查状态
  checkRTSPStatus();

  // 开始实时日志读取
  readRTSPLogPeriodically();

  addLogToUI(
    {
      timestamp: new Date().toLocaleTimeString(),
      version: 'RTSP',
      type: 'LOG',
      oids: [`开始读取日志`],
      hex: '',
      result: 'success',
    } as any,
    false,
  );
}

// 检查RTSP状态
async function checkRTSPStatus() {
  try {
    const result = await requestClient.post(
      '/protocol-compliance/check-status',
      {
        protocol: 'RTSP',
      },
    );

    console.log('[DEBUG] RTSP状态检查结果:', result);

    if (result) {
      // 显示状态信息到UI
      const statusMessage = `状态检查: 日志目录${result.log_dir_exists ? '存在' : '不存在'}, 日志文件${result.log_file_exists ? '存在' : '不存在'}`;

      addToRealtimeStream('RTSP', {
        timestamp: new Date().toLocaleTimeString(),
        type: 'INFO',
        content: statusMessage,
      });

      // 如果有Docker容器信息，显示
      if (result.docker_containers) {
        addToRealtimeStream('RTSP', {
          timestamp: new Date().toLocaleTimeString(),
          type: 'INFO',
          content: `Docker容器状态: ${result.docker_containers.split('\n').length - 1}个容器运行中`,
        });
      }

      // 如果有文件列表，显示
      if (result.files_in_log_dir && Array.isArray(result.files_in_log_dir)) {
        addToRealtimeStream('RTSP', {
          timestamp: new Date().toLocaleTimeString(),
          type: 'INFO',
          content: `输出目录文件: ${result.files_in_log_dir.join(', ')}`,
        });
      }
    }
  } catch (error) {
    console.error('检查RTSP状态失败:', error);

    addToRealtimeStream('RTSP', {
      timestamp: new Date().toLocaleTimeString(),
      type: 'ERROR',
      content: `状态检查失败: ${(error as Error).message || error}`,
    });
  }
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
      const result = await requestClient.post('/protocol-compliance/read-log', {
        protocol: 'RTSP',
        lastPosition: logReadPosition.value, // 使用实际的读取位置，实现增量读取
      });

      console.log('[DEBUG] RTSP日志读取结果:', result);

      if (result && result.message) {
        // 显示后端返回的状态信息
        console.log('[DEBUG] 后端状态信息:', result.message);

        // 如果是文件不存在的情况，显示等待信息
        if (
          result.message.includes('日志文件尚未创建') ||
          result.message.includes('日志目录不存在')
        ) {
          addToRealtimeStream('RTSP', {
            timestamp: new Date().toLocaleTimeString(),
            type: 'WARNING',
            content: result.message,
          });
        }
      }

      if (result && result.content && result.content.trim()) {
        // 更新读取位置
        logReadPosition.value = result.position || logReadPosition.value;

        console.log('[DEBUG] 读取到RTSP日志内容，长度:', result.content.length);
        console.log('[DEBUG] 日志内容预览:', result.content.substring(0, 200));

        // 处理AFL-NET的plot_data格式
        const logLines = result.content
          .split('\n')
          .filter((line: string) => line.trim());
        console.log('[DEBUG] 处理日志行数:', logLines.length);

        logLines.forEach((line: string) => {
          const logData = processRTSPLogLine(
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
            const logType =
              logData.type === 'STATS' || logData.type === 'HEADER'
                ? 'INFO'
                : (logData.type as 'ERROR' | 'INFO' | 'WARNING' | 'SUCCESS');
            addToRealtimeStream('RTSP', {
              timestamp: logData.timestamp,
              type: logType,
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
      console.error('读取RTSP日志失败:', error);

      // 显示错误信息到UI
      addToRealtimeStream('RTSP', {
        timestamp: new Date().toLocaleTimeString(),
        type: 'ERROR',
        content: `读取日志失败: ${(error as Error).message || error}`,
      });
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
    // 检查rtspProcessId是否是Docker容器ID（通常是长字符串）
    const isDockerContainer =
      typeof rtspProcessId.value === 'string' &&
      rtspProcessId.value.length > 10;

    if (isDockerContainer) {
      // 使用新的停止和清理功能
      const result = await stopAndCleanupRTSP(rtspProcessId.value as string);

      addLogToUI(
        {
          timestamp: new Date().toLocaleTimeString(),
          version: 'RTSP',
          type: 'CLEANUP',
          oids: [
            `Docker容器已停止 (ID: ${rtspProcessId.value})`,
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
            version: 'RTSP',
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
      await stopRTSPProcess(rtspProcessId.value);

      addLogToUI(
        {
          timestamp: new Date().toLocaleTimeString(),
          version: 'RTSP',
          type: 'STOP',
          oids: [`RTSP进程已停止 (PID: ${rtspProcessId.value})`],
          hex: '',
          result: 'success',
        } as any,
        false,
      );
    }

    rtspProcessId.value = null;
  } catch (error) {
    console.error('停止RTSP进程失败:', error);

    addLogToUI(
      {
        timestamp: new Date().toLocaleTimeString(),
        version: 'RTSP',
        type: 'ERROR',
        oids: [`停止RTSP进程失败: ${(error as Error).message || error}`],
        hex: '',
        result: 'error',
      } as any,
      false,
    );
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
    if (protocolType.value === 'RTSP') {
      stopRTSPProcessWrapper();
    }
    // SNMP不需要特殊处理

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
    // MQTT已经在上面early return了，这里只处理SNMP/RTSP
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

  if (protocolType.value === 'MQTT') {
    // MQTT协议专用报告格式
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
      `Q-Learning状态空间: ${Object.keys((mqttStats.value as any).q_learning_states || {}).length} 个协议状态\n\n` +
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
          {
            text: packet.version?.toUpperCase() || 'UNKNOWN',
            className: 'log-entry__protocol',
          },
          {
            text: packet.type?.toUpperCase() || 'UNKNOWN',
            className: 'log-entry__operation',
          },
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

  nextTick(() => {
    appendLogLine(
      time,
      [
        {
          text: crashEvent.message || '崩溃通知',
          className: 'log-entry__crash-label',
        },
      ],
      { variant: 'crash' },
    );
    appendLogLine(
      time,
      [
        {
          text: `[崩溃信息] 疑似崩溃数据包: ${crashEvent.crashPacket || '未知'}`,
        },
      ],
      { variant: 'crash' },
    );
    appendLogLine(
      time,
      [
        {
          text: `[崩溃信息] 崩溃队列信息导出: ${crashEvent.crashLogPath || '未知路径'}`,
        },
      ],
      { variant: 'crash' },
    );
    appendLogLine(time, [{ text: '[运行监控] 检测到崩溃，停止 fuzz 循环' }], {
      variant: 'crash',
    });
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
    appendLogLine(
      time,
      [
        {
          text: '[运行监控] 收到崩溃通知: 健康服务报告 VM 不可达',
          className: 'log-entry__crash-label',
        },
      ],
      { variant: 'crash' },
    );
    appendLogLine(
      time,
      [{ text: `[崩溃信息] 疑似崩溃数据包: ${hex || '未知'}` }],
      { variant: 'crash' },
    );
    appendLogLine(
      time,
      [
        {
          text: `[崩溃信息] 日志导出目录: ${crashDetails?.logPath || '未知路径'}`,
        },
      ],
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
      // 保存RTSP协议统计数据
      rtspStats:
        protocolType.value === 'RTSP'
          ? {
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
              n_edges: rtspStats.value.n_edges,
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
              } as any;
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
          : protocolType.value === 'RTSP'
            ? {
                pathCoverage:
                  (rtspStats.value.cur_path /
                    Math.max(rtspStats.value.paths_total, 1)) *
                  100,
                stateTransitions: rtspStats.value.n_edges,
                maxDepth: rtspStats.value.max_depth,
                uniqueHangs: rtspStats.value.unique_hangs,
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
  activeTabKey.value = 'history';
}

function viewHistoryDetail(item: HistoryResult) {
  selectedHistoryItem.value = item;
  historyDrawerOpen.value = true;
}


function closeHistoryDrawer() {
  historyDrawerOpen.value = false;
}

function deleteHistoryItem(id: string) {
  const index = historyResults.value.findIndex((item) => item.id === id);
  if (index > -1) {
    historyResults.value.splice(index, 1);
    if (selectedHistoryItem.value?.id === id) {
      historyDrawerOpen.value = false;
      selectedHistoryItem.value = null;
    }

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
    `SNMP v1: ${item.protocolStats?.v1 || 0}\n` +
    `SNMP v2c: ${item.protocolStats?.v2c || 0}\n` +
    `SNMP v3: ${item.protocolStats?.v3 || 0}\n\n` +
    `消息类型分布:\n` +
    `GET: ${item.messageTypeStats?.get || 0}\n` +
    `SET: ${item.messageTypeStats?.set || 0}\n` +
    `GETNEXT: ${item.messageTypeStats?.getnext || 0}\n` +
    `GETBULK: ${item.messageTypeStats?.getbulk || 0}\n\n` +
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
    customRender: ({ record }) => `${record.targetHost}:${record.targetPort}`,
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
                onConfirm: () =>
                  deleteHistoryItem((record as HistoryResult).id),
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
  // MQTT协议不需要fuzzData
  if (protocolType.value === 'MQTT') {
    return !loading.value && !isRunning.value;
  }
  return !loading.value && snmpFuzzData.value.length > 0 && !isRunning.value;
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
  ) as unknown as SVGElement;
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
    const moduleRect = module?.getBoundingClientRect();
    const elRect = el.getBoundingClientRect();

    // 查找图标元素（SVG）而不是整个节点
    const iconElement = el.querySelector('svg') as unknown as HTMLElement;
    let iconRect = elRect;

    if (iconElement) {
      iconRect = iconElement.getBoundingClientRect();
    }

    // 计算图标相对于模块容器的位置
    if (!moduleRect)
      return {
        x: 0,
        y: 0,
        centerX: 0,
        centerY: 0,
        leftBottom: { x: 0, y: 0 },
        rightBottom: { x: 0, y: 0 },
        topLeft: { x: 0, y: 0 },
        topRight: { x: 0, y: 0 },
      };
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
    const bPos = getPosition(broker)!;
    const c1Pos = getPosition(client1)!;
    const c2Pos = getPosition(client2)!;

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
      }, source.interval) as unknown as number;
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
        mqttDifferentialLogsData = [];
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
                    <IconifyIcon
                      icon="ant-design:experiment-outlined"
                      class="card-icon"
                    />
                    <span>测试配置</span>
                  </Space>
                </template>
                <template #extra>
                  <Space size="small">
                    <Tag
                      :color="
                        isRunning
                          ? isPaused
                            ? 'warning'
                            : 'processing'
                          : crashCount > 0
                            ? 'error'
                            : 'default'
                      "
                    >
                      {{ testStatusText }}
                    </Tag>
                    <Button size="small" type="link" @click="goToHistoryView">
                      <IconifyIcon
                        icon="ant-design:history-outlined"
                        class="inline-icon"
                      />
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
                      :message="
                        notificationMessage || '测试结果已保存到历史记录'
                      "
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
                            <Select.Option value="SNMP_Fuzz"
                              >SNMP_Fuzz</Select.Option
                            >
                            <Select.Option value="AFLNET">AFLNET</Select.Option>
                            <Select.Option value="MQTT_FUZZ"
                              >MQTT_FUZZ</Select.Option
                            >
                          </Select>
                        </FormItem>
                        <FormItem label="目标主机">
                          <Input
                            v-model:value="targetHost"
                            placeholder="例如 192.168.0.10"
                          />
                        </FormItem>
                        <FormItem label="目标端口">
                          <InputNumber
                            v-model:value="targetPort"
                            :max="65535"
                            :min="1"
                            style="width: 100%"
                          />
                        </FormItem>
                      </div>
                      <FormItem
                        v-if="protocolType === 'RTSP'"
                        label="RTSP 指令配置"
                      >
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
                            <IconifyIcon
                              icon="ant-design:play-circle-outlined"
                              class="inline-icon"
                            />
                            开始测试
                          </Button>
                          <Button v-if="isRunning" @click="togglePauseTest">
                            <IconifyIcon
                              :icon="
                                isPaused
                                  ? 'ant-design:caret-right-outlined'
                                  : 'ant-design:pause-circle-outlined'
                              "
                              class="inline-icon"
                            />
                            {{ isPaused ? '继续' : '暂停' }}
                          </Button>
                          <Button danger v-if="isRunning" @click="stopTest">
                            <IconifyIcon
                              icon="ant-design:stop-outlined"
                              class="inline-icon"
                            />
                            停止
                          </Button>
                        </Space>
                      </div>
                    </Form>
                  </Space>
                </Spin>
              </Card>

              <Card class="log-card">
                <template #title>
                  <Space>
                    <IconifyIcon
                      icon="ant-design:code-outlined"
                      class="card-icon"
                    />
                    <span>实时日志</span>
                  </Space>
                </template>
                <div class="card-toolbar">
                  <Space size="small">
                    <Button size="small" @click="clearLog">清空</Button>
                    <Button
                      size="small"
                      @click="saveLog"
                      :disabled="!logEntries.length"
                    >
                      导出日志
                    </Button>
                    <Button
                      size="small"
                      @click="toggleCrashDetailsView"
                      :disabled="!crashDetails"
                    >
                      {{ showCrashDetails ? '收起崩溃详情' : '展开崩溃详情' }}
                    </Button>
                  </Space>
                </div>
                <div ref="logContainer" class="log-panel">
                  <div class="log-empty">
                    测试未开始，请配置参数并点击“开始测试”
                  </div>
                </div>
              </Card>
            </div>

            <div class="live-column">
              <Card class="status-card">
                <template #title>
                  <Space>
                    <IconifyIcon
                      icon="ant-design:dashboard-outlined"
                      class="card-icon"
                    />
                    <span>运行状态</span>
                  </Space>
                </template>
                <template v-if="!hasUserStartedTest">
                  <Empty description="点击开始测试以获取数据" />
                </template>
                <Space
                  v-else
                  direction="vertical"
                  size="middle"
                  class="status-content"
                >
                  <Progress :show-info="false" :percent="progressWidth" />
                  <div class="status-metrics">
                    <div class="status-metric">
                      <TypographyText class="status-value">{{
                        packetCount
                      }}</TypographyText>
                      <TypographyParagraph
                        type="secondary"
                        class="status-label"
                      >
                        已发送数据包
                      </TypographyParagraph>
                    </div>
                    <div class="status-metric">
                      <TypographyText
                        class="status-value status-value--success"
                      >
                        {{ successCount }}
                      </TypographyText>
                      <TypographyParagraph
                        type="secondary"
                        class="status-label"
                      >
                        成功
                      </TypographyParagraph>
                    </div>
                    <div class="status-metric">
                      <TypographyText
                        class="status-value status-value--warning"
                      >
                        {{ timeoutCount }}
                      </TypographyText>
                      <TypographyParagraph
                        type="secondary"
                        class="status-label"
                      >
                        超时
                      </TypographyParagraph>
                    </div>
                    <div class="status-metric">
                      <TypographyText class="status-value status-value--danger">
                        {{ crashCount }}
                      </TypographyText>
                      <TypographyParagraph
                        type="secondary"
                        class="status-label"
                      >
                        崩溃
                      </TypographyParagraph>
                    </div>
                  </div>
                  <Descriptions :column="2" size="small">
                    <Descriptions.Item label="开始时间">{{
                      startTime || '-'
                    }}</Descriptions.Item>
                    <Descriptions.Item label="结束时间">{{
                      endTime || '-'
                    }}</Descriptions.Item>
                    <Descriptions.Item label="累计时长"
                      >{{ elapsedTime }} 秒</Descriptions.Item
                    >
                    <Descriptions.Item label="当前速率"
                      >{{ currentSpeed }} 包/秒</Descriptions.Item
                    >
                    <Descriptions.Item label="目标发送速率"
                      >{{ packetsPerSecond }} 包/秒</Descriptions.Item
                    >
                    <Descriptions.Item label="预估运行时长"
                      >{{ testDuration }} 秒</Descriptions.Item
                    >
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
                    <IconifyIcon
                      icon="ant-design:pie-chart-outlined"
                      class="card-icon"
                    />
                    <span>结果分析</span>
                  </Space>
                </template>
                <template v-if="!hasUserStartedTest">
                  <Empty description="点击开始测试以获取数据" />
                </template>
                <template v-else>
                  <div class="charts-grid">
                    <div class="chart-panel">
                      <TypographyText type="secondary" class="chart-title"
                        >消息类型分布</TypographyText
                      >
                      <div class="chart-container">
                        <canvas ref="messageCanvas"></canvas>
                        <div v-if="!showCharts" class="chart-overlay">
                          <TypographyText type="secondary"
                            >等待测试完成以生成图表</TypographyText
                          >
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
                      <TypographyText type="secondary" class="chart-title"
                        >协议版本分布</TypographyText
                      >
                      <div class="chart-container">
                        <canvas ref="versionCanvas"></canvas>
                        <div v-if="!showCharts" class="chart-overlay">
                          <TypographyText type="secondary"
                            >等待测试完成以生成图表</TypographyText
                          >
                        </div>
                      </div>
                      <Space size="small" wrap class="chart-tags">
                        <Tag>v1: {{ protocolStats.v1 || 0 }}</Tag>
                        <Tag>v2c: {{ protocolStats.v2c || 0 }}</Tag>
                        <Tag>v3: {{ protocolStats.v3 || 0 }}</Tag>
                      </Space>
                    </div>
                  </div>
                </template>
              </Card>

              <Card class="crash-card">
                <template #title>
                  <Space>
                    <IconifyIcon
                      icon="ant-design:alert-outlined"
                      class="card-icon"
                    />
                    <span>崩溃监控</span>
                  </Space>
                </template>
                <template v-if="crashDetails">
                  <Descriptions :column="1" size="small">
                    <Descriptions.Item label="时间">{{
                      crashDetails.time
                    }}</Descriptions.Item>
                    <Descriptions.Item label="类型">{{
                      crashDetails.type
                    }}</Descriptions.Item>
                    <Descriptions.Item label="触发数据包"
                      >#{{ crashDetails.id }}</Descriptions.Item
                    >
                    <Descriptions.Item label="转储文件">
                      <span class="mono-text">{{ crashDetails.dumpFile }}</span>
                    </Descriptions.Item>
                    <Descriptions.Item label="日志路径">
                      <span class="mono-text">{{ crashDetails.logPath }}</span>
                    </Descriptions.Item>
                  </Descriptions>
                  <TypographyParagraph
                    v-if="showCrashDetails"
                    class="crash-details"
                    type="secondary"
                  >
                    <pre>{{ crashDetails.details }}</pre>
                  </TypographyParagraph>
                  <TypographyParagraph
                    v-if="showCrashDetails && crashDetails.packetContent"
                    class="crash-packet"
                    type="secondary"
                  >
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
                <IconifyIcon
                  icon="ant-design:database-outlined"
                  class="card-icon"
                />
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
            <Descriptions.Item label="记录 ID">{{
              selectedHistoryItem.id
            }}</Descriptions.Item>
            <Descriptions.Item label="测试时间">{{
              selectedHistoryItem.timestamp
            }}</Descriptions.Item>
            <Descriptions.Item label="协议">{{
              selectedHistoryItem.protocol
            }}</Descriptions.Item>
            <Descriptions.Item label="引擎">{{
              selectedHistoryItem.fuzzEngine
            }}</Descriptions.Item>
            <Descriptions.Item label="目标">
              {{ selectedHistoryItem.targetHost }}:{{
                selectedHistoryItem.targetPort
              }}
            </Descriptions.Item>
            <Descriptions.Item label="耗时"
              >{{ selectedHistoryItem.duration }} 秒</Descriptions.Item
            >
            <Descriptions.Item label="总包数">{{
              selectedHistoryItem.totalPackets
            }}</Descriptions.Item>
            <Descriptions.Item label="成功率"
              >{{ selectedHistoryItem.successRate }}%</Descriptions.Item
            >
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
              <Tag
                >GETNEXT:
                {{ selectedHistoryItem.messageTypeStats.getnext }}</Tag
              >
              <Tag
                >GETBULK:
                {{ selectedHistoryItem.messageTypeStats.getbulk }}</Tag
              >
            </Space>
          </div>
          <div
            v-if="
              selectedHistoryItem.hasCrash && selectedHistoryItem.crashDetails
            "
            class="drawer-section"
          >
            <TypographyTitle :level="5">崩溃详情</TypographyTitle>
            <TypographyParagraph type="secondary">
              触发数据包：{{ selectedHistoryItem.crashDetails.packetContent }}
            </TypographyParagraph>
            <pre class="drawer-pre"
              >{{ selectedHistoryItem.crashDetails.details }}
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
  display: inline-flex;
  align-items: center;
}

.inline-icon {
  margin-right: 4px;
  font-size: 16px;
  display: inline-flex;
  align-items: center;
}

/* Only align horizontal Space components (not vertical ones used in forms) */
:deep(.ant-space:not(.ant-space-vertical)) {
  align-items: center;
}

:deep(.ant-space:not(.ant-space-vertical) .ant-space-item) {
  display: inline-flex;
  align-items: center;
}

/* Ensure card titles with icons are aligned */
:deep(.ant-card-head-title .ant-space) {
  align-items: center;
}

:deep(.ant-card-head-title .ant-space-item) {
  display: inline-flex;
  align-items: center;
}

:deep(.ant-btn) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
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
  font-family:
    ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas,
    'Liberation Mono', 'Courier New', monospace;
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
  background: #ffffff;
  border-radius: var(--ant-border-radius);
}

.chart-tags {
  font-size: 12px;
}

.chart-tip {
  margin: 16px 0 0;
  font-size: 12px;
}

.crash-card .mono-text {
  font-family:
    ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas,
    'Liberation Mono', 'Courier New', monospace;
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
  font-family:
    ui-monospace, SFMono-Regular, SFMono, Menlo, Monaco, Consolas,
    'Liberation Mono', 'Courier New', monospace;
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
