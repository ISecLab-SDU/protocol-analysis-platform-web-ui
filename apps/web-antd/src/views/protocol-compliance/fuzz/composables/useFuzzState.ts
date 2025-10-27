import { ref } from 'vue';
import type { ProtocolType, FuzzEngineType, HistoryResult } from './types';

/**
 * Composable to manage all reactive state (refs) for the Fuzz Testing component
 * Organizes refs by functional category to improve maintainability
 */
export function useFuzzState() {
  // ============================================================
  // DATA STATE
  // ============================================================
  const rawText = ref<string>('');
  const loading = ref<boolean>(true);
  const error = ref<string | null>(null);

  // ============================================================
  // FILE-LEVEL SUMMARY STATS
  // ============================================================
  const totalPacketsInFile = ref<number>(0);
  const fileTotalPackets = ref<number>(0);
  const fileSuccessCount = ref<number>(0);
  const fileTimeoutCount = ref<number>(0);
  const fileFailedCount = ref<number>(0);

  // ============================================================
  // RUNTIME STATS
  // ============================================================
  const packetCount = ref<number>(0);
  const successCount = ref<number>(0);
  const timeoutCount = ref<number>(0);
  const failedCount = ref<number>(0);
  const crashCount = ref<number>(0);
  const elapsedTime = ref<number>(0);
  const packetsPerSecond = ref<number>(30);
  const testDuration = ref<number>(60);
  const isRunning = ref<boolean>(false);
  const isTestCompleted = ref<boolean>(false);
  const hasUserStartedTest = ref<boolean>(false); // Track if user has clicked "Start Test"

  // ============================================================
  // UI CONFIGURATION
  // ============================================================
  const protocolType = ref<ProtocolType>('SNMP');
  const fuzzEngine = ref<FuzzEngineType>('SNMP_Fuzz');
  const targetHost = ref<string>('127.0.0.1');
  const targetPort = ref<number>(161);
  const rtspCommandConfig = ref<string>(
    'afl-fuzz -d -i $AFLNET/tutorials/live555/in-rtsp -o out-live555 -N tcp://127.0.0.1/8554 -x $AFLNET/tutorials/live555/rtsp.dict -P RTSP -D 10000 -q 3 -s 3 -E -K -R ./testOnDemandRTSPServer 8554',
  );

  // ============================================================
  // LOGGER REFS
  // ============================================================
  const rtspProcessId = ref<number | string | null>(null);

  // ============================================================
  // CHART & DISPLAY REFS
  // ============================================================
  const showCharts = ref<boolean>(false);
  const crashDetails = ref<any>(null);
  const logEntries = ref<any[]>([]);
  const startTime = ref<string>('');
  const endTime = ref<string>('');
  const lastUpdate = ref<string>('');
  const currentSpeed = ref<number>(0);
  const isPaused = ref<boolean>(false);
  const showCrashDetails = ref<boolean>(false);
  const testStartTime = ref<Date | null>(null);
  const testEndTime = ref<Date | null>(null);
  const currentPacketIndex = ref<number>(0);
  const packetDelay = ref<number>(33); // 1000/30 = 33ms for 30 packets/second

  // ============================================================
  // HISTORY & NOTIFICATION REFS
  // ============================================================
  const activeTabKey = ref<'live' | 'history'>('live');
  const showHistoryView = ref<boolean>(false);
  const selectedHistoryItem = ref<any>(null);
  const historyDrawerOpen = ref<boolean>(false);
  const showNotification = ref<boolean>(false);
  const notificationMessage = ref<string>('');
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
        packetContent:
          '302902010004067075626C6963A01C02040E8F83C502010002010030',
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

  // ============================================================
  // CANVAS REFS
  // ============================================================
  const messageCanvas = ref<HTMLCanvasElement>();
  const versionCanvas = ref<HTMLCanvasElement>();
  const mqttMessageCanvas = ref<HTMLCanvasElement>();

  // ============================================================
  // MQTT-SPECIFIC REFS
  // ============================================================
  const unifiedLogs = ref<
    Array<{
      id: string;
      timestamp: string;
      type: 'INFO' | 'ERROR' | 'WARNING' | 'SUCCESS';
      content: string;
      protocol: 'SNMP' | 'RTSP' | 'MQTT';
    }>
  >([]);

  const mqttLogsContainer = ref<HTMLElement | null>(null); // 日志容器引用
  const mqttLogsUpdateKey = ref<number>(0); // 强制更新key

  // MQTT处理状态
  const mqttIsProcessingLogs = ref<boolean>(false);
  const mqttTotalRecords = ref<number>(0);
  const mqttProcessedRecords = ref<number>(0);
  const mqttProcessingProgress = ref<number>(0);

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

  // MQTT差异报告统计
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

  return {
    // Data state
    rawText,
    loading,
    error,

    // File-level stats
    totalPacketsInFile,
    fileTotalPackets,
    fileSuccessCount,
    fileTimeoutCount,
    fileFailedCount,

    // Runtime stats
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

    // UI configuration
    protocolType,
    fuzzEngine,
    targetHost,
    targetPort,
    rtspCommandConfig,

    // Logger refs
    rtspProcessId,

    // Chart & display refs
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

    // History & notification refs
    activeTabKey,
    showHistoryView,
    selectedHistoryItem,
    historyDrawerOpen,
    showNotification,
    notificationMessage,
    historyResults,

    // Canvas refs
    messageCanvas,
    versionCanvas,
    mqttMessageCanvas,

    // MQTT-specific refs
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
  };
}
