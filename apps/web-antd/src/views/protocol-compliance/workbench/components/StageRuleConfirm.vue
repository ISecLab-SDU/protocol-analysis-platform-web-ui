<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { Button, Card, Empty, message, Table, Tag } from 'ant-design-vue';
import { IconifyIcon } from '@vben/icons';

import type { ProtocolExtractRuleItem } from '#/api/protocol-compliance';

import type { ProtocolKind, RuleOption } from '../types';
import { BUILTIN_RULESET_INDEX } from '../types';
import { normalizeList } from '../utils';

interface Props {
  protocolType: ProtocolKind;
  disabled?: boolean;
}

interface Emits {
  (e: 'start', rule: ProtocolExtractRuleItem): void;
  (e: 'back'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const loading = ref(false);
const rules = ref<RuleOption[]>([]);
const selectedRowKeys = ref<string[]>([]);

const columns = [
  { title: '消息类型', dataIndex: 'msgType', width: 120 },
  { title: '规则描述', dataIndex: 'rule', ellipsis: true },
  { title: '请求字段', dataIndex: 'req_type', width: 200 },
  { title: '响应字段', dataIndex: 'res_type', width: 200 },
];

const selectedRule = computed(() => {
  if (selectedRowKeys.value.length === 0) return null;
  return rules.value.find((r) => r.id === selectedRowKeys.value[0]) ?? null;
});

async function loadRules() {
  loading.value = true;
  try {
    const entry = BUILTIN_RULESET_INDEX.find((e) => e.protocol === props.protocolType);
    if (!entry) {
      message.error(`未找到 ${props.protocolType} 的内置规则集`);
      return;
    }
    const response = await fetch(entry.path);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const flatRules: RuleOption[] = [];
    for (const [msgType, ruleList] of Object.entries(data)) {
      if (Array.isArray(ruleList)) {
        for (const rule of ruleList) {
          flatRules.push({
            ...rule,
            id: `${msgType}-${flatRules.length}`,
            msgType,
          });
        }
      }
    }
    rules.value = flatRules;
    if (flatRules.length > 0) {
      selectedRowKeys.value = [flatRules[0]!.id!];
    }
  } catch (err: any) {
    message.error(`加载规则失败: ${err?.message || err}`);
  } finally {
    loading.value = false;
  }
}

function onStart() {
  if (!selectedRule.value) {
    message.warning('请先选择一条规则');
    return;
  }
  emit('start', selectedRule.value);
}

function onSelectionChange(keys: Array<number | string>) {
  selectedRowKeys.value = keys.map(String);
}

onMounted(() => {
  loadRules();
});
</script>

<template>
  <Card class="stage-card" title="规则确认">
    <template #extra>
      <Button size="small" @click="emit('back')">
        <template #icon><IconifyIcon icon="mdi:arrow-left" /></template>
        返回设置
      </Button>
    </template>

    <div v-if="rules.length > 0" class="rule-info">
      <Tag color="blue">{{ protocolType }}</Tag>
      <span class="rule-count">共 {{ rules.length }} 条规则</span>
    </div>

    <Table
      :columns="columns"
      :data-source="rules"
      :loading="loading"
      :pagination="{ pageSize: 10 }"
      :row-selection="{
        type: 'radio',
        selectedRowKeys,
        onChange: onSelectionChange,
      }"
      row-key="id"
      size="small"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'req_type'">
          <Tag v-for="(field, i) in normalizeList(record.req_type)" :key="i" color="green">
            {{ field }}
          </Tag>
        </template>
        <template v-else-if="column.dataIndex === 'res_type'">
          <Tag v-for="(field, i) in normalizeList(record.res_type)" :key="i" color="orange">
            {{ field }}
          </Tag>
        </template>
      </template>
    </Table>

    <Empty v-if="!loading && rules.length === 0" description="未找到规则" />

    <div class="rule-actions">
      <Button
        type="primary"
        size="large"
        :disabled="!selectedRule || disabled"
        @click="onStart"
      >
        <template #icon><IconifyIcon icon="mdi:play" /></template>
        确认并启动流水线
      </Button>
    </div>
  </Card>
</template>

<style scoped>
.stage-card {
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
  box-shadow: 0 10px 26px rgb(15 23 42 / 4%);
}

.rule-info {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.rule-count {
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}

.rule-actions {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--ant-color-border-secondary);
}
</style>
