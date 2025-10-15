<script setup lang="ts">
import { onMounted, ref, nextTick } from 'vue';
import { getFuzzText } from '#/api/custom';
import Chart from 'chart.js/auto';
import { Button, Card, Space, Spin } from 'ant-design-vue';

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
let testTimer: number | null = null;

// UI refs
const logContainer = ref<HTMLDivElement | null>(null);
let messageTypeChart: any = null;
let versionChart: any = null;

async function fetchText() {
  loading.value = true;
  try {
    const resp = await getFuzzText();
    const text = (resp as any)?.text ?? (resp as any)?.data?.text ?? '';
    rawText.value = text;
  } catch (e: any) {
    error.value = e?.message || '加载失败';
  } finally {
    loading.value = false;
  }
}

function initCharts() {
  const messageCanvas = document.getElementById('messageTypeMainChart') as HTMLCanvasElement | null;
  const versionCanvas = document.getElementById('versionDistributionChart') as HTMLCanvasElement | null;
  if (!messageCanvas || !versionCanvas) return;

  const messageCtx = messageCanvas.getContext('2d');
  const versionCtx = versionCanvas.getContext('2d');
  if (!messageCtx || !versionCtx) return;

  messageTypeChart = new Chart(messageCtx, {
    type: 'doughnut',
    data: {
      labels: ['GET', 'SET', 'GETNEXT', 'GETBULK'],
      datasets: [{ data: [0, 0, 0, 0], backgroundColor: ['#3B82F6', '#6366F1', '#EC4899', '#10B981'], borderColor: '#FFFFFF', borderWidth: 3, hoverOffset: 8 }],
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: '#1F2937', padding: 15, font: { size: 12, weight: 'bold' }, usePointStyle: true } } }, cutout: '60%' },
  });

  versionChart = new Chart(versionCtx, {
    type: 'doughnut',
    data: { labels: ['SNMP v1', 'SNMP v2c', 'SNMP v3'], datasets: [{ data: [0, 0, 0], backgroundColor: ['#F59E0B', '#8B5CF6', '#EF4444'], borderColor: '#FFFFFF', borderWidth: 3, hoverOffset: 8 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: '#1F2937', padding: 15, font: { size: 12, weight: 'bold' }, usePointStyle: true } } }, cutout: '60%' },
  });
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
  const lines = text.split('\n');
  fuzzData.value = [];
  let currentPacket: FuzzPacket | null = null;
  let localFailedCount = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    const packetMatch = line.match(/^\[(\d+)\]\s+版本=([^,]+),\s+类型=([^,]+)/);
    if (packetMatch) {
      if (currentPacket) fuzzData.value.push(currentPacket);
      const packetNumber = parseInt(packetMatch[1]);
      currentPacket = {
        id: packetNumber,
        version: packetMatch[2],
        type: packetMatch[3],
        oids: [],
        hex: '',
        result: 'unknown',
        responseSize: 0,
        timestamp: `${String(Math.floor(packetNumber / 60)).padStart(2, '0')}:${String(packetNumber % 60).padStart(2, '0')}`,
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
        currentPacket.timestamp = `${String(Math.floor(failedId / 60)).padStart(2, '0')}:${String(failedId % 60).padStart(2, '0')}`;
        fuzzData.value.push(currentPacket);
        currentPacket = null;
      } else {
        fuzzData.value.push({ id: failedId, version: 'unknown', type: 'unknown', oids: [], hex: '', result: 'failed', responseSize: 0, timestamp: `${String(Math.floor(failedId / 60)).padStart(2, '0')}:${String(failedId % 60).padStart(2, '0')}`, failed: true, failedReason: line });
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
    } else if (line.includes('[接收超时]') && currentPacket) {
      currentPacket.result = 'timeout';
      continue;
    }

    if (line.includes('[运行监控]')) {
      const isExactCrashNotice = line.includes('[运行监控] 收到崩溃通知: 健康服务报告 VM 不可达');
      if (isExactCrashNotice || line.includes('崩溃通知')) {
        const crashEvent = { type: 'crash_notification', message: line, timestamp: `${String(Math.floor(i / 60)).padStart(2, '0')}:${String(i % 60).padStart(2, '0')}`, crashPacket: '', crashLogPath: '' };
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

  // Counters from file
  const successCountInFile = (text.match(/\[接收成功\]/g) || []).length;
  const timeoutCountInFile = (text.match(/\[接收超时\]/g) || []).length;
  const failedCountInFile = (text.match(/生成失败:/g) || []).length;
  (window as any).fuzzTotalPackets = successCountInFile + timeoutCountInFile + failedCountInFile;
  (window as any).fuzzSuccessCount = successCountInFile;
  (window as any).fuzzTimeoutCount = timeoutCountInFile;
  (window as any).fuzzFailedCount = failedCountInFile;
}

function startTest() {
  if (!fuzzData.value.length) return;
  isRunning.value = true;
  packetCount.value = 0;
  successCount.value = 0;
  timeoutCount.value = 0;
  failedCount.value = 0;
  crashCount.value = 0;
  elapsedTime.value = 0;
  const packetDelay = 1000 / packetsPerSecond.value;
  if (testTimer) { clearInterval(testTimer as any); testTimer = null; }
  testTimer = window.setInterval(() => { elapsedTime.value++; }, 1000);
  loop(packetDelay);
}

function stopTest() {
  isRunning.value = false;
  if (testTimer) { clearInterval(testTimer as any); testTimer = null; }
}

function loop(delay: number) {
  if (!isRunning.value) return;
  const currentIndex = packetCount.value;
  if (currentIndex >= fuzzData.value.length) return stopTest();
  const packet = fuzzData.value[currentIndex];
  if (packet) {
    if (packet.result === 'success') successCount.value++;
    else if (packet.result === 'timeout') timeoutCount.value++;
    else if (packet.result === 'failed') failedCount.value++;
    else if (packet.result === 'crash') crashCount.value++;

    // Append logs sparsely
    if (packet.result !== 'crash' && packetCount.value % 5 === 0 && logContainer.value) {
      const div = document.createElement('div');
      div.className = 'packet-highlight';
      const protocol = packet.version?.toUpperCase?.() || 'UNKNOWN';
      const op = packet.type?.toUpperCase?.() || 'UNKNOWN';
      const time = packet.timestamp || '';
      const content = packet.oids?.[0] || '';
      const hex = (packet.hex || '').slice(0, 40);
      const resultText = packet.result === 'success' ? `正常响应 (${packet.responseSize || 0}字节)` : packet.result === 'timeout' ? '接收超时' : packet.result === 'failed' ? '构造失败' : '未知状态';
      const resultClass = packet.result === 'success' ? 'text-success' : packet.result === 'timeout' ? 'text-warning' : packet.result === 'failed' ? 'text-danger' : 'text-warning';
      div.innerHTML = `<span class="text-dark/50">[${time}]</span> <span class="text-primary">SNMP${protocol}</span> <span class="text-info">${op}</span> <span class="text-dark/70 truncate inline-block w-32" title="${content}">${content}</span> <span class="${resultClass} font-medium">${resultText}</span> <span class="text-dark/40">${hex}...</span>`;
      logContainer.value.appendChild(div);
      logContainer.value.scrollTop = logContainer.value.scrollHeight;
      if (logContainer.value.children.length > 200) logContainer.value.removeChild(logContainer.value.firstChild as any);
    } else if (packet.result === 'crash' && logContainer.value) {
      const div = document.createElement('div');
      div.className = 'crash-highlight';
      div.innerHTML = `<span class="text-dark/50">[${packet.timestamp || ''}]</span> <span class="text-danger font-bold">CRASH DETECTED</span>`;
      logContainer.value.appendChild(div);
      logContainer.value.scrollTop = logContainer.value.scrollHeight;
    }
  }
  packetCount.value++;
  if (packetCount.value === 1 || packetCount.value % 50 === 0 || packetCount.value >= fuzzData.value.length) updateCharts();
  window.setTimeout(() => loop(delay), delay);
}

onMounted(async () => {
  await fetchText();
  if (rawText.value) {
    parseText(rawText.value);
  }
  await nextTick();
  initCharts();
});
</script>

<template>
  <div class="container mx-auto px-4 py-6">
    <Card title="协议模糊测试">
      <template #extra>
        <Space>
          <Button type="primary" @click="startTest" :disabled="!fuzzData.length || isRunning">开始测试</Button>
          <Button danger @click="stopTest" :disabled="!isRunning">停止测试</Button>
        </Space>
      </template>

      <Spin :spinning="loading">
        <div v-if="error" class="text-red-500">{{ error }}</div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div class="lg:col-span-2 bg-white/80 rounded-xl p-4 border border-primary/20 shadow-card">
            <div class="flex justify-between items-center mb-4">
              <h3 class="font-semibold text-lg">Fuzz过程</h3>
              <div class="flex space-x-2">
                <a-button size="small" @click="() => { if (logContainer) logContainer.innerHTML = '' }">清空日志</a-button>
              </div>
            </div>
            <div ref="logContainer" class="bg-light-gray rounded-lg border border-dark/10 h-80 overflow-y-auto p-3 font-mono text-xs space-y-1 scrollbar-thin">
              <div class="text-dark/50 italic" v-if="!isRunning">测试未开始，请点击"开始测试"</div>
            </div>
          </div>

          <div class="lg:col-span-1 bg-white/80 rounded-xl p-6 border border-primary/20 shadow-card">
            <h3 class="font-semibold text-lg mb-4">实时统计</h3>
            <div class="space-y-6">
              <div>
                <div class="flex justify-between items-center mb-1">
                  <span class="text-sm text-dark/70">总发送包数</span>
                  <span class="text-xl font-bold">{{ packetCount }}</span>
                </div>
                <div class="w-full bg-light-gray rounded-full h-1.5 overflow-hidden">
                  <div class="h-full bg-primary" :style="{ width: `${Math.min(100, Math.round((packetCount / Math.max(packetCount, testDuration * packetsPerSecond)) * 100))}%` }"></div>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div class="bg-light-gray rounded-lg p-4 border border-success/20">
                  <p class="text-sm text-success/70 mb-2">正常响应</p>
                  <h4 class="text-3xl font-bold text-success">{{ successCount }}</h4>
                </div>
                <div class="bg-light-gray rounded-lg p-4 border border-danger/20">
                  <p class="text-sm text-danger/70 mb-2">构造失败</p>
                  <h4 class="text-3xl font-bold text-danger">{{ failedCount }}</h4>
                </div>
                <div class="bg-light-gray rounded-lg p-4 border border-warning/20">
                  <p class="text-sm text-warning/70 mb-2">超时</p>
                  <h4 class="text-3xl font-bold text-warning">{{ timeoutCount }}</h4>
                </div>
                <div class="bg-light-gray rounded-lg p-4 border border-info/20">
                  <p class="text-sm text-info/70 mb-2">崩溃</p>
                  <h4 class="text-3xl font-bold text-info">{{ crashCount }}</h4>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div class="lg:col-span-2 bg-white/80 rounded-xl p-6 border border-secondary/20 shadow-card">
            <div class="flex justify-between items-center mb-6">
              <h3 class="font-semibold text-xl">消息类型分布与版本统计</h3>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8 h-72">
              <div>
                <h4 class="text-base font-medium mb-3 text-dark/80 text-center">消息类型分布</h4>
                <div class="h-60">
                  <canvas id="messageTypeMainChart"></canvas>
                </div>
              </div>
              <div>
                <h4 class="text-base font-medium mb-3 text-dark/80 text-center">SNMP版本分布</h4>
                <div class="h-60">
                  <canvas id="versionDistributionChart"></canvas>
                </div>
              </div>
            </div>
          </div>

          <div class="lg:col-span-1 bg-white/80 rounded-xl p-6 border border-primary/20 shadow-card">
            <h3 class="font-semibold text-lg mb-4">测试总结（完成后）</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between"><span>总包数(文件)</span><span>{{ (window as any).fuzzTotalPackets || 0 }}</span></div>
              <div class="flex justify-between"><span>成功</span><span>{{ (window as any).fuzzSuccessCount || 0 }}</span></div>
              <div class="flex justify-between"><span>超时</span><span>{{ (window as any).fuzzTimeoutCount || 0 }}</span></div>
              <div class="flex justify-between"><span>失败</span><span>{{ (window as any).fuzzFailedCount || 0 }}</span></div>
            </div>
          </div>
        </div>
      </Spin>
    </Card>
  </div>
</template>

<style scoped>
.packet-highlight {
  animation: highlight 0.5s ease-in-out;
}
.crash-highlight {
  animation: crashHighlight 1.5s ease-in-out infinite;
}
@keyframes highlight { 0% { background-color: rgba(59,130,246,0.1); } 100% { background-color: transparent; } }
@keyframes crashHighlight { 0%, 100% { background-color: rgba(239,68,68,0.1);} 50% { background-color: rgba(239,68,68,0.2);} }
</style>


