<script lang="ts" setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  Button,
  Card,
  Empty,
  message,
  Modal,
  Select,
  SelectOption,
  Table,
  Tag,
} from 'ant-design-vue';

type StageKey =
  | 'rule_confirm'
  | 'code_locate'
  | 'assert_generate'
  | 'fuzz'
  | 'verify';

interface StageDef {
  key: StageKey;
  index: number;
  title: string;
}

interface ViolationRow {
  id: string;
  severity: 'high' | 'medium' | 'low';
  description: string;
  observed: string;
  expected: string;
  trigger: string;
  location: string;
  timestamp: string;
}

interface RuleOption {
  id: string;
  expression: string;
  protocol: string;
  rfcRef: string;
  evidence: string;
  constraintType: string;
  source: string;
  behavior: string;
  targetFile: string;
  targetLine: number;
  candidateCount: number;
  sliceCount: number;
  variableCount: number;
  snippet: string;
  highlightLine: number;
  fuzzer: string;
}

const STAGES: StageDef[] = [
  { index: 1, key: 'rule_confirm', title: '规则确认' },
  { index: 2, key: 'code_locate', title: '代码定位' },
  { index: 3, key: 'assert_generate', title: '断言生成' },
  { index: 4, key: 'fuzz', title: '模糊测试' },
  { index: 5, key: 'verify', title: '结果验证' },
];

const STAGE_LABEL: Record<StageKey, string> = {
  rule_confirm: '规则确认',
  code_locate: '代码定位',
  assert_generate: '断言生成',
  fuzz: '模糊测试',
  verify: '结果验证',
};

const RULE_OPTIONS: RuleOption[] = [
  {
    id: 'SDP-MEDIA-001',
    expression: 'packet_rate <= SMAXPR',
    protocol: 'MQTT 3.1.1',
    rfcRef: 'RFC 5104 §3.5.4.2',
    evidence:
      '"The highest feasible packet rate within this region is the minimum of the rate at which the bounding polygon meets the X-axis or the session maximum packet rate (SMAXPR, measured in packets per second) provided by signaling, if any."',
    constraintType: 'range_constraint',
    source: 'smaxpr (SDP)',
    behavior: 'packet_rate <= smaxpr',
    targetFile: 'rate_controller.cc',
    targetLine: 318,
    candidateCount: 6,
    sliceCount: 2,
    variableCount: 3,
    snippet:
      '// calculate maximum packet rate\nuint22_t max_calc_pps = total_br / (8 * oh);\nuint22_t limit_pps = has_smaxpr_ ? smaxpr_ : max_calc;\ncurrent_pps_ = std::min(max_calc_pps, limit_pps);\n..',
    highlightLine: 318,
    fuzzer: 'AFLNet',
  },
  {
    id: 'MQTT-CONN-014',
    expression: 'ClientID length <= 23',
    protocol: 'MQTT 3.1.1',
    rfcRef: 'MQTT-3.1.3-5',
    evidence:
      '"The Server MUST allow ClientIds which are between 1 and 23 UTF-8 encoded bytes in length, and that contain only the characters [...] The Server MAY allow ClientIds that contain more than 23 encoded bytes."',
    constraintType: 'length_constraint',
    source: 'CONNECT.ClientID',
    behavior: 'len(ClientID) ∈ [1, 23]',
    targetFile: 'mqtt_connect.c',
    targetLine: 142,
    candidateCount: 4,
    sliceCount: 3,
    variableCount: 2,
    snippet:
      'int handle_connect(client_t *c, packet_t *p) {\n  uint16_t client_id_len = read_uint16(p);\n  if (client_id_len > 23) {\n    /* MQTT-3.1.3-5: ClientID 长度违规 */',
    highlightLine: 142,
    fuzzer: 'BooFuzz',
  },
  {
    id: 'MQTT-QOS2-027',
    expression: 'PUBREL.PacketIdentifier == PUBREC.PacketIdentifier',
    protocol: 'MQTT 3.1.1',
    rfcRef: 'MQTT-4.3.3-1',
    evidence:
      '"In the QoS 2 delivery protocol, the Sender MUST treat the PUBREL packet [as] a response to the PUBREC packet that carries the same Packet Identifier."',
    constraintType: 'equality_constraint',
    source: 'PUBREL / PUBREC',
    behavior: 'pkt_id(PUBREL) == pkt_id(PUBREC)',
    targetFile: 'qos2_session.c',
    targetLine: 89,
    candidateCount: 5,
    sliceCount: 2,
    variableCount: 4,
    snippet:
      'void on_pubrec(session_t *s, uint16_t pid) {\n  if (s->pending_pubrel.pid != pid) {\n    /* MQTT-4.3.3-1: pid 不匹配 */',
    highlightLine: 89,
    fuzzer: 'AFLNet',
  },
];

const RULE_VIOLATIONS: Record<string, ViolationRow[]> = {
  'SDP-MEDIA-001': [
    {
      id: 'F-001',
      severity: 'high',
      description: 'packet_rate exceeds SMAXPR',
      observed: '1,800 pps',
      expected: '<= 1,200 pps',
      trigger: 'seed_00017.pcap',
      location: 'rate_controller.cc:318',
      timestamp: '2025/05/20 10:31:20',
    },
    {
      id: 'F-002',
      severity: 'high',
      description: 'packet_rate exceeds SMAXPR',
      observed: '1,650 pps',
      expected: '<= 1,200 pps',
      trigger: 'seed_00042.pcap',
      location: 'rate_controller.cc:318',
      timestamp: '2025/05/20 10:32:11',
    },
  ],
  'MQTT-CONN-014': [
    {
      id: 'F-001',
      severity: 'high',
      description: 'ClientID 长度溢出未拒绝',
      observed: '64 bytes',
      expected: '<= 23 bytes',
      trigger: 'seed_00012.pcap',
      location: 'mqtt_connect.c:142',
      timestamp: '2025/05/20 10:34:48',
    },
  ],
  'MQTT-QOS2-027': [],
};

const stageStatus = reactive<Record<StageKey, 'pending' | 'running' | 'done'>>({
  rule_confirm: 'pending',
  code_locate: 'pending',
  assert_generate: 'pending',
  fuzz: 'pending',
  verify: 'pending',
});

const currentStage = ref<StageKey>('rule_confirm');
const selectedRuleId = ref<string>(RULE_OPTIONS[0]!.id);
const isRunning = ref(false);
const elapsedSeconds = ref(0);
const startedAt = ref<Date | null>(null);
const stageMessage = ref('请选择规则后开始自动化流程');

const taskStartTime = ref('--');
const fuzzExecCount = ref(0);
const fuzzPathCount = ref(0);
const fuzzCrash = ref(0);
const fuzzHang = ref(0);
const fuzzSeries = ref<number[]>([]);
const fuzzTimeLabels = ref<string[]>([]);
const violationCount = ref(0);
const warningCount = ref(0);
const compliantCount = ref(0);
const undecidedCount = ref(0);
const violations = ref<ViolationRow[]>([]);

let stageTimer: ReturnType<typeof setTimeout> | null = null;
let elapsedTimer: ReturnType<typeof setInterval> | null = null;
let fuzzTimer: ReturnType<typeof setInterval> | null = null;

const selectedRule = computed<RuleOption>(
  () =>
    RULE_OPTIONS.find((r) => r.id === selectedRuleId.value) ?? RULE_OPTIONS[0]!,
);

const elapsedDisplay = computed(() => {
  const total = elapsedSeconds.value;
  const hh = String(Math.floor(total / 3600)).padStart(2, '0');
  const mm = String(Math.floor((total % 3600) / 60)).padStart(2, '0');
  const ss = String(total % 60).padStart(2, '0');
  return `${hh}:${mm}:${ss}`;
});

const stageReached = (stage: StageKey) => {
  const order = STAGES.map((s) => s.key);
  return order.indexOf(stage) <= order.indexOf(currentStage.value);
};

const stageDone = (stage: StageKey) => stageStatus[stage] === 'done';
const stageActive = (stage: StageKey) => stageStatus[stage] === 'running';

const stageLabelForCard = computed(() => STAGE_LABEL[currentStage.value]);

const codeLines = computed(() => {
  const startLine = selectedRule.value.targetLine - 3;
  return selectedRule.value.snippet
    .split('\n')
    .map((text, i) => ({
      no: startLine + i,
      text,
      highlight: startLine + i === selectedRule.value.highlightLine,
    }));
});

function resetMetrics(rule: RuleOption) {
  fuzzExecCount.value = 0;
  fuzzPathCount.value = 0;
  fuzzCrash.value = 0;
  fuzzHang.value = 0;
  fuzzSeries.value = [];
  fuzzTimeLabels.value = [];
  violations.value = [];
  violationCount.value = 0;
  warningCount.value = 0;
  compliantCount.value = 0;
  undecidedCount.value = 0;
}

function resetAll() {
  for (const stage of STAGES) {
    stageStatus[stage.key] = 'pending';
  }
  currentStage.value = 'rule_confirm';
  elapsedSeconds.value = 0;
  startedAt.value = null;
  taskStartTime.value = '--';
  stageMessage.value = '请选择规则后开始自动化流程';
  resetMetrics(selectedRule.value);
}

function clearTimers() {
  if (stageTimer) {
    clearTimeout(stageTimer);
    stageTimer = null;
  }
  if (elapsedTimer) {
    clearInterval(elapsedTimer);
    elapsedTimer = null;
  }
  if (fuzzTimer) {
    clearInterval(fuzzTimer);
    fuzzTimer = null;
  }
}

function formatNow() {
  const now = new Date();
  const pad = (v: number) => String(v).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}

function startElapsed() {
  startedAt.value = new Date();
  elapsedTimer = setInterval(() => {
    if (!startedAt.value) return;
    elapsedSeconds.value = Math.floor(
      (Date.now() - startedAt.value.getTime()) / 1000,
    );
    fuzzTimeLabels.value =
      fuzzTimeLabels.value.length === 0
        ? []
        : fuzzTimeLabels.value;
  }, 1000);
}

function advanceToStage(key: StageKey) {
  currentStage.value = key;
  stageStatus[key] = 'running';
  stageMessage.value = `${STAGE_LABEL[key]} 进行中…`;
}

function completeStage(key: StageKey) {
  stageStatus[key] = 'done';
}

function startFuzzTicker(rule: RuleOption) {
  const violationPool = RULE_VIOLATIONS[rule.id] ?? [];
  let tick = 0;
  fuzzTimer = setInterval(() => {
    tick += 1;
    fuzzExecCount.value += Math.round(900 + Math.random() * 250);
    fuzzPathCount.value += Math.round(80 + Math.random() * 60);
    fuzzSeries.value.push(fuzzExecCount.value);
    const mm = String(Math.floor(tick / 4)).padStart(2, '0');
    const ss = String((tick * 15) % 60).padStart(2, '0');
    fuzzTimeLabels.value.push(`00:${mm}:${ss}`);
    if (fuzzSeries.value.length > 14) {
      fuzzSeries.value.shift();
      fuzzTimeLabels.value.shift();
    }
    if (violationPool[violationCount.value]) {
      violations.value.push(violationPool[violationCount.value]!);
      violationCount.value = violations.value.length;
    }
  }, 1500);
}

function runPipeline() {
  if (isRunning.value) return;
  const rule = selectedRule.value;
  resetMetrics(rule);
  isRunning.value = true;
  taskStartTime.value = formatNow();
  startElapsed();

  completeStage('rule_confirm');
  advanceToStage('code_locate');
  stageMessage.value = '正在切片候选函数并定位关键位置…';

  stageTimer = setTimeout(() => {
    completeStage('code_locate');
    advanceToStage('assert_generate');
    stageMessage.value = '正在生成合规断言并织入插桩补丁…';

    stageTimer = setTimeout(() => {
      completeStage('assert_generate');
      advanceToStage('fuzz');
      stageMessage.value = `${rule.fuzzer} 模糊测试运行中…`;
      startFuzzTicker(rule);

      stageTimer = setTimeout(() => {
        completeStage('fuzz');
        if (fuzzTimer) {
          clearInterval(fuzzTimer);
          fuzzTimer = null;
        }
        advanceToStage('verify');
        stageMessage.value = '正在比对断言与运行结果，生成结论…';

        stageTimer = setTimeout(() => {
          completeStage('verify');
          stageMessage.value = '自动化流程完成，可导出报告';
          isRunning.value = false;
          const total = violations.value.length;
          violationCount.value = total;
          compliantCount.value = total > 0 ? 0 : 1;
          warningCount.value = 0;
          undecidedCount.value = 0;
          if (elapsedTimer) {
            clearInterval(elapsedTimer);
            elapsedTimer = null;
          }
        }, 4500);
      }, 9000);
    }, 4500);
  }, 4500);
}

function stopPipeline() {
  if (!isRunning.value) {
    resetAll();
    return;
  }
  Modal.confirm({
    title: '停止当前任务？',
    content: '停止后已经收集的中间结果会被保留，但任务将中断。',
    okText: '停止',
    okType: 'danger',
    cancelText: '取消',
    onOk() {
      clearTimers();
      isRunning.value = false;
      stageMessage.value = '任务已手动停止';
      for (const stage of STAGES) {
        if (stageStatus[stage.key] === 'running') {
          stageStatus[stage.key] = 'pending';
        }
      }
    },
  });
}

function exportReport() {
  if (currentStage.value !== 'verify' || stageStatus.verify !== 'done') {
    message.warning('请等待全部阶段完成后再导出');
    return;
  }
  message.success('已生成 ProtocolGuard 分析报告（演示）');
}

function onRuleChange() {
  if (isRunning.value) {
    message.info('任务运行中，切换规则将重置流程');
    clearTimers();
    isRunning.value = false;
  }
  resetAll();
}

watch(currentStage, (val) => {
  if (val === 'fuzz' && fuzzSeries.value.length === 0) {
    fuzzSeries.value = [0];
    fuzzTimeLabels.value = ['00:00:00'];
  }
});

onBeforeUnmount(() => {
  clearTimers();
});

const violationColumns = [
  { title: 'ID', dataIndex: 'id', width: 70 },
  { title: '严重性', dataIndex: 'severity', width: 88 },
  { title: '违规描述', dataIndex: 'description' },
  { title: '观测值', dataIndex: 'observed', width: 110 },
  { title: '期望约束', dataIndex: 'expected', width: 130 },
  { title: '触发输入', dataIndex: 'trigger', width: 140 },
  { title: '发现位置', dataIndex: 'location', width: 160 },
  { title: '时间', dataIndex: 'timestamp', width: 150 },
];

const sparkPath = computed(() => {
  if (fuzzSeries.value.length === 0) return '';
  const max = Math.max(...fuzzSeries.value, 1);
  const w = 280;
  const h = 90;
  const stepX = w / Math.max(fuzzSeries.value.length - 1, 1);
  return fuzzSeries.value
    .map((v, i) => {
      const x = i * stepX;
      const y = h - (v / max) * (h - 6) - 3;
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(' ');
});

const sparkArea = computed(() => {
  if (!sparkPath.value) return '';
  return `${sparkPath.value} L 280 90 L 0 90 Z`;
});

const fuzzMaxLabel = computed(() => {
  const max = Math.max(...fuzzSeries.value, 1);
  if (max >= 1000) return `${(max / 1000).toFixed(1).replace(/\.0$/, '')}k`;
  return String(max);
});
</script>

<template>
  <Page>
    <div class="pg-shell">
      <aside class="pg-sidebar">
        <div class="pg-brand">
          <div class="pg-brand-icon">
            <IconifyIcon icon="mdi:shield-check" />
          </div>
          <div class="pg-brand-text">
            <div class="pg-brand-name">ProtocolGuard</div>
            <div class="pg-brand-sub">工作台</div>
          </div>
        </div>
        <nav class="pg-nav">
          <a class="pg-nav-item pg-nav-item--active">
            <IconifyIcon icon="mdi:view-dashboard-outline" />
            <span>概览</span>
          </a>
          <a class="pg-nav-item">
            <IconifyIcon icon="mdi:format-list-bulleted" />
            <span>规则列表</span>
          </a>
          <a class="pg-nav-item">
            <IconifyIcon icon="mdi:file-document-outline" />
            <span>证据链</span>
          </a>
          <a class="pg-nav-item">
            <IconifyIcon icon="mdi:notebook-outline" />
            <span>日志</span>
          </a>
        </nav>

        <div class="pg-task-card">
          <div class="pg-task-title">当前任务</div>
          <dl class="pg-task-meta">
            <div>
              <dt>项目</dt>
              <dd>MQTT Broker (mosquitto)</dd>
            </div>
            <div>
              <dt>协议版本</dt>
              <dd>{{ selectedRule.protocol }}</dd>
            </div>
            <div>
              <dt>源码包</dt>
              <dd>sol.tar (v2.0.18)</dd>
            </div>
            <div>
              <dt>开始时间</dt>
              <dd>{{ taskStartTime }}</dd>
            </div>
          </dl>
        </div>
      </aside>

      <main class="pg-main">
        <header class="pg-header">
          <div class="pg-header-left">
            <h2 class="pg-task-name">MQTT Broker 分析任务</h2>
            <div class="pg-task-rule">
              <span class="pg-task-label">规则：</span>
              <Tag color="blue">{{ selectedRule.id }}</Tag>
              <code>{{ selectedRule.expression }}</code>
            </div>
          </div>
          <div class="pg-header-right">
            <div class="pg-status" :class="{ 'pg-status--idle': !isRunning }">
              <span class="pg-status-dot" />
              <span>{{ isRunning ? '运行中' : '空闲' }}</span>
            </div>
            <div class="pg-elapsed">{{ elapsedDisplay }}</div>
            <Button danger @click="stopPipeline">
              <template #icon><IconifyIcon icon="mdi:stop-circle" /></template>
              停止
            </Button>
            <Button @click="exportReport">
              <template #icon><IconifyIcon icon="mdi:download" /></template>
              导出报告
            </Button>
            <Select
              v-model:value="selectedRuleId"
              class="pg-rule-switch"
              :disabled="isRunning"
              size="middle"
              @change="onRuleChange"
            >
              <template #suffixIcon>
                <IconifyIcon icon="mdi:chevron-down" />
              </template>
              <SelectOption
                v-for="opt in RULE_OPTIONS"
                :key="opt.id"
                :value="opt.id"
              >
                切换规则 · {{ opt.id }}
              </SelectOption>
            </Select>
            <div class="pg-user">PG</div>
          </div>
        </header>

        <section class="pg-stepper">
          <div
            v-for="(stage, idx) in STAGES"
            :key="stage.key"
            class="pg-step"
            :class="{
              'pg-step--done': stageDone(stage.key),
              'pg-step--active': stageActive(stage.key),
              'pg-step--reached': stageReached(stage.key),
            }"
          >
            <div class="pg-step-circle">
              <IconifyIcon
                v-if="stageDone(stage.key)"
                icon="mdi:check-bold"
              />
              <span v-else>{{ stage.index }}</span>
            </div>
            <div class="pg-step-meta">
              <div class="pg-step-title">{{ stage.title }}</div>
              <div class="pg-step-state">
                <template v-if="stageDone(stage.key)">已完成</template>
                <template v-else-if="stageActive(stage.key)">进行中</template>
                <template v-else-if="stage.key === 'rule_confirm'">
                  待启动
                </template>
                <template v-else>等待中</template>
              </div>
            </div>
            <div v-if="idx < STAGES.length - 1" class="pg-step-arrow">
              <IconifyIcon icon="mdi:arrow-right" />
            </div>
          </div>
        </section>

        <section class="pg-banner">
          <IconifyIcon icon="mdi:information-outline" />
          <span>{{ stageMessage }}</span>
          <Button
            v-if="!isRunning && stageStatus.verify !== 'done'"
            type="primary"
            size="small"
            @click="runPipeline"
          >
            <template #icon><IconifyIcon icon="mdi:play" /></template>
            开始自动化流程
          </Button>
        </section>

        <section class="pg-grid">
          <Card class="pg-card pg-card-locate">
            <template #title>
              <div class="pg-card-title">
                <IconifyIcon icon="mdi:file-tree-outline" />
                <span>代码定位</span>
                <Tag
                  :color="stageActive('code_locate') ? 'processing' : 'default'"
                >
                  {{
                    stageDone('code_locate')
                      ? '已完成'
                      : stageActive('code_locate')
                        ? '进行中'
                        : '等待中'
                  }}
                </Tag>
              </div>
            </template>

            <div v-if="stageReached('code_locate')" class="pg-locate-body">
              <div class="pg-locate-stats">
                <div class="pg-stat">
                  <div class="pg-stat-label">候选函数</div>
                  <div class="pg-stat-value">
                    {{ selectedRule.candidateCount }}
                  </div>
                </div>
                <div class="pg-stat">
                  <div class="pg-stat-label">关键切片</div>
                  <div class="pg-stat-value">{{ selectedRule.sliceCount }}</div>
                </div>
                <div class="pg-stat">
                  <div class="pg-stat-label">相关变量</div>
                  <div class="pg-stat-value">
                    {{ selectedRule.variableCount }}
                  </div>
                </div>
              </div>
              <div class="pg-locate-detail">
                <div class="pg-locate-row">
                  <span class="pg-locate-key">目标文件：</span>
                  <code>{{ selectedRule.targetFile }}</code>
                </div>
                <div class="pg-locate-row">
                  <span class="pg-locate-key">关键位置：</span>
                  <code>{{ selectedRule.targetLine }}</code>
                </div>
                <pre class="pg-snippet"><code><span
                    v-for="line in codeLines"
                    :key="line.no"
                    class="pg-snippet-line"
                    :class="{ 'pg-snippet-line--hl': line.highlight }"
                  ><span class="pg-snippet-no">{{ line.no }}</span>{{ line.text }}
</span></code></pre>
                <a class="pg-link">查看代码上下文 →</a>
              </div>
            </div>
            <Empty
              v-else
              description="等待『代码定位』阶段开始"
              :image="Empty.PRESENTED_IMAGE_SIMPLE"
            />
          </Card>

          <Card class="pg-card pg-card-rule">
            <template #title>
              <div class="pg-card-title">
                <IconifyIcon icon="mdi:bookmark-check-outline" />
                <span>规则证据</span>
                <span class="pg-card-sub">（{{ selectedRule.rfcRef }}）</span>
              </div>
            </template>
            <blockquote class="pg-quote">
              {{ selectedRule.evidence }}
            </blockquote>
            <dl class="pg-kv">
              <div>
                <dt>约束类型</dt>
                <dd>{{ selectedRule.constraintType }}</dd>
              </div>
              <div>
                <dt>源数据</dt>
                <dd>{{ selectedRule.source }}</dd>
              </div>
              <div>
                <dt>目标行为</dt>
                <dd><code>{{ selectedRule.behavior }}</code></dd>
              </div>
            </dl>
          </Card>

          <Card class="pg-card pg-card-results">
            <template #title>
              <div class="pg-card-title">
                <IconifyIcon icon="mdi:flag-outline" />
                <span>验证结果</span>
                <span class="pg-card-sub">（当前规则）</span>
                <Tag
                  :color="stageActive('verify') ? 'processing' : 'default'"
                  class="pg-card-tag"
                >
                  {{
                    stageDone('verify')
                      ? '已完成'
                      : stageActive('verify')
                        ? '进行中'
                        : '等待中'
                  }}
                </Tag>
              </div>
            </template>

            <div class="pg-result-summary">
              <div class="pg-result-tile pg-result-tile--danger">
                <IconifyIcon icon="mdi:shield-alert" />
                <div>
                  <div class="pg-result-label">发现违规</div>
                  <div class="pg-result-value">{{ violationCount }}</div>
                </div>
              </div>
              <div class="pg-result-tile pg-result-tile--warn">
                <IconifyIcon icon="mdi:alert" />
                <div>
                  <div class="pg-result-label">警告</div>
                  <div class="pg-result-value">{{ warningCount }}</div>
                </div>
              </div>
              <div class="pg-result-tile pg-result-tile--ok">
                <IconifyIcon icon="mdi:check-circle" />
                <div>
                  <div class="pg-result-label">合规</div>
                  <div class="pg-result-value">{{ compliantCount }}</div>
                </div>
              </div>
              <div class="pg-result-tile pg-result-tile--muted">
                <IconifyIcon icon="mdi:help-circle-outline" />
                <div>
                  <div class="pg-result-label">未判定</div>
                  <div class="pg-result-value">{{ undecidedCount }}</div>
                </div>
              </div>
            </div>

            <Table
              :columns="violationColumns"
              :data-source="violations"
              :pagination="false"
              size="small"
              row-key="id"
              :locale="{ emptyText: '尚未发现违规' }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.dataIndex === 'severity'">
                  <Tag
                    :color="
                      record.severity === 'high'
                        ? 'red'
                        : record.severity === 'medium'
                          ? 'orange'
                          : 'gold'
                    "
                  >
                    {{
                      record.severity === 'high'
                        ? 'High'
                        : record.severity === 'medium'
                          ? 'Medium'
                          : 'Low'
                    }}
                  </Tag>
                </template>
                <template v-else-if="column.dataIndex === 'trigger'">
                  <a class="pg-link">{{ record.trigger }}</a>
                </template>
              </template>
            </Table>
            <a v-if="violations.length > 0" class="pg-link pg-link-block">
              查看所有违规（{{ violations.length }}）
            </a>
          </Card>

          <Card class="pg-card pg-card-monitor">
            <template #title>
              <div class="pg-card-title">
                <IconifyIcon icon="mdi:chart-timeline-variant" />
                <span>运行监控</span>
              </div>
            </template>
            <dl class="pg-monitor-kv">
              <div>
                <dt>Fuzzer</dt>
                <dd>{{ selectedRule.fuzzer }}</dd>
              </div>
              <div>
                <dt>运行时长</dt>
                <dd>{{ elapsedDisplay }}</dd>
              </div>
              <div>
                <dt>执行次数</dt>
                <dd>{{ fuzzExecCount.toLocaleString() }}</dd>
              </div>
              <div>
                <dt>路径数</dt>
                <dd>{{ fuzzPathCount.toLocaleString() }}</dd>
              </div>
              <div>
                <dt>Crash</dt>
                <dd>{{ fuzzCrash }}</dd>
              </div>
              <div>
                <dt>Hang</dt>
                <dd>{{ fuzzHang }}</dd>
              </div>
            </dl>
            <div class="pg-spark">
              <div class="pg-spark-y">
                <span>{{ fuzzMaxLabel }}</span>
                <span>10k</span>
                <span>5k</span>
                <span>0</span>
              </div>
              <svg viewBox="0 0 280 90" class="pg-spark-svg">
                <path :d="sparkArea" class="pg-spark-area" />
                <path :d="sparkPath" class="pg-spark-line" />
              </svg>
              <div class="pg-spark-x">
                <span
                  v-for="(label, i) in [
                    '00:00',
                    '00:03',
                    '00:06',
                    '00:09',
                    '00:12',
                  ]"
                  :key="i"
                >{{ label }}</span>
              </div>
            </div>
          </Card>
        </section>
      </main>
    </div>
  </Page>
</template>

<style scoped>
.pg-shell {
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: calc(100vh - 120px);
  gap: 16px;
}

.pg-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 12px;
}

.pg-brand {
  display: flex;
  gap: 10px;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--ant-color-border-secondary);
}

.pg-brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  font-size: 20px;
  color: #fff;
  background: linear-gradient(135deg, #1677ff, #4096ff);
  border-radius: 8px;
}

.pg-brand-name {
  font-size: 15px;
  font-weight: 600;
}

.pg-brand-sub {
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.pg-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pg-nav-item {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px 12px;
  font-size: 14px;
  color: var(--ant-text-color);
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.2s;
}

.pg-nav-item:hover {
  background: var(--ant-color-fill-quaternary);
}

.pg-nav-item--active {
  font-weight: 600;
  color: #1677ff;
  background: rgb(22 119 255 / 8%);
}

.pg-task-card {
  margin-top: auto;
  padding: 12px;
  font-size: 12px;
  background: var(--ant-color-fill-quaternary);
  border-radius: 8px;
}

.pg-task-title {
  margin-bottom: 8px;
  font-weight: 600;
  color: var(--ant-text-color);
}

.pg-task-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0;
}

.pg-task-meta > div {
  display: grid;
  grid-template-columns: 64px 1fr;
  gap: 8px;
}

.pg-task-meta dt {
  color: var(--ant-text-color-secondary);
}

.pg-task-meta dd {
  margin: 0;
  color: var(--ant-text-color);
}

.pg-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pg-header {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 12px;
}

.pg-task-name {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.pg-task-rule {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 4px;
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}

.pg-task-rule code {
  padding: 1px 6px;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  background: var(--ant-color-fill-quaternary);
  border-radius: 4px;
}

.pg-header-right {
  display: flex;
  gap: 10px;
  align-items: center;
}

.pg-status {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #16a34a;
  background: rgb(22 163 74 / 12%);
  border-radius: 999px;
}

.pg-status--idle {
  color: var(--ant-text-color-secondary);
  background: var(--ant-color-fill-quaternary);
}

.pg-status-dot {
  width: 6px;
  height: 6px;
  background: currentcolor;
  border-radius: 50%;
}

.pg-elapsed {
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 14px;
  color: var(--ant-text-color);
}

.pg-rule-switch {
  width: 160px;
}

.pg-user {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #1677ff, #69b1ff);
  border-radius: 50%;
}

.pg-stepper {
  display: flex;
  gap: 4px;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 12px;
}

.pg-step {
  display: flex;
  flex: 1 1 0;
  gap: 10px;
  align-items: center;
}

.pg-step-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ant-text-color-secondary);
  background: var(--ant-color-fill-quaternary);
  border-radius: 50%;
}

.pg-step--reached .pg-step-circle {
  color: #fff;
  background: #1677ff;
}

.pg-step--done .pg-step-circle {
  background: #16a34a;
}

.pg-step--active .pg-step-circle {
  box-shadow: 0 0 0 4px rgb(22 119 255 / 15%);
}

.pg-step-meta {
  display: flex;
  flex-direction: column;
}

.pg-step-title {
  font-size: 14px;
  font-weight: 600;
}

.pg-step-state {
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.pg-step--done .pg-step-state {
  color: #16a34a;
}

.pg-step--active .pg-step-state {
  color: #1677ff;
}

.pg-step-arrow {
  margin-left: auto;
  font-size: 18px;
  color: var(--ant-color-border);
}

.pg-banner {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 16px;
  font-size: 13px;
  color: var(--ant-text-color);
  background: rgb(22 119 255 / 6%);
  border: 1px solid rgb(22 119 255 / 18%);
  border-radius: 10px;
}

.pg-banner :first-child {
  font-size: 16px;
  color: #1677ff;
}

.pg-banner button {
  margin-left: auto;
}

.pg-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 16px;
}

.pg-card {
  border-radius: 12px;
}

.pg-card-title {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 15px;
  font-weight: 600;
}

.pg-card-sub {
  font-size: 12px;
  font-weight: 400;
  color: var(--ant-text-color-secondary);
}

.pg-card-tag {
  margin-left: auto;
}

.pg-card-results,
.pg-card-monitor {
  grid-column: auto;
}

.pg-card-results {
  grid-column: 1;
}

.pg-card-monitor {
  grid-column: 2;
}

.pg-locate-body {
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 16px;
}

.pg-locate-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pg-stat {
  padding: 10px 12px;
  background: var(--ant-color-fill-quaternary);
  border-radius: 8px;
}

.pg-stat-label {
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.pg-stat-value {
  font-size: 22px;
  font-weight: 600;
}

.pg-locate-row {
  margin-bottom: 6px;
  font-size: 13px;
}

.pg-locate-key {
  margin-right: 6px;
  color: var(--ant-text-color-secondary);
}

.pg-snippet {
  margin: 8px 0 0;
  padding: 12px;
  overflow-x: auto;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12.5px;
  line-height: 1.6;
  background: #0f172a;
  border-radius: 8px;
}

.pg-snippet code {
  color: #e2e8f0;
}

.pg-snippet-line {
  display: block;
}

.pg-snippet-line--hl {
  background: rgb(22 119 255 / 25%);
}

.pg-snippet-no {
  display: inline-block;
  width: 36px;
  margin-right: 12px;
  color: #64748b;
  user-select: none;
}

.pg-link {
  display: inline-block;
  margin-top: 10px;
  font-size: 13px;
  color: #1677ff;
  cursor: pointer;
}

.pg-link-block {
  display: block;
  margin-top: 12px;
}

.pg-quote {
  margin: 0;
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.65;
  background: rgb(22 119 255 / 6%);
  border-left: 3px solid #1677ff;
  border-radius: 6px;
}

.pg-kv {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 14px 0 0;
}

.pg-kv > div {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 8px;
  font-size: 13px;
}

.pg-kv dt {
  color: var(--ant-text-color-secondary);
}

.pg-kv dd {
  margin: 0;
  color: var(--ant-text-color);
}

.pg-kv code {
  padding: 1px 6px;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  background: var(--ant-color-fill-quaternary);
  border-radius: 4px;
}

.pg-result-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}

.pg-result-tile {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px;
  border-radius: 10px;
}

.pg-result-tile :first-child {
  font-size: 22px;
}

.pg-result-tile--danger {
  color: #dc2626;
  background: rgb(220 38 38 / 8%);
}

.pg-result-tile--warn {
  color: #d97706;
  background: rgb(217 119 6 / 8%);
}

.pg-result-tile--ok {
  color: #16a34a;
  background: rgb(22 163 74 / 8%);
}

.pg-result-tile--muted {
  color: var(--ant-text-color-secondary);
  background: var(--ant-color-fill-quaternary);
}

.pg-result-label {
  font-size: 12px;
}

.pg-result-value {
  font-size: 22px;
  font-weight: 600;
  color: var(--ant-text-color);
}

.pg-monitor-kv {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 16px;
  margin: 0 0 12px;
}

.pg-monitor-kv > div {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.pg-monitor-kv dt {
  color: var(--ant-text-color-secondary);
}

.pg-monitor-kv dd {
  margin: 0;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.pg-spark {
  position: relative;
  display: grid;
  grid-template-columns: 36px 1fr;
  grid-template-rows: 1fr 16px;
  gap: 4px;
  height: 130px;
  padding-top: 4px;
}

.pg-spark-y {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: 11px;
  color: var(--ant-text-color-secondary);
}

.pg-spark-svg {
  grid-column: 2;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.pg-spark-line {
  fill: none;
  stroke: #1677ff;
  stroke-width: 2;
}

.pg-spark-area {
  fill: rgb(22 119 255 / 15%);
  stroke: none;
}

.pg-spark-x {
  display: flex;
  grid-column: 2;
  justify-content: space-between;
  font-size: 11px;
  color: var(--ant-text-color-secondary);
}

@media (max-width: 1280px) {
  .pg-shell {
    grid-template-columns: 200px 1fr;
  }

  .pg-grid {
    grid-template-columns: 1fr;
  }

  .pg-card-results,
  .pg-card-monitor {
    grid-column: auto;
  }
}
</style>
