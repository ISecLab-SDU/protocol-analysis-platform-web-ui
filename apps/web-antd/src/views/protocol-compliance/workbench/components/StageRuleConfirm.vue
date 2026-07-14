<script setup lang="ts">
import type { RuleOption } from '../types';

import type { ProtocolExtractRuleItem } from '#/api/protocol-compliance';

import { computed, reactive, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';

import { Button, Card, Empty, message, Table, Tag } from 'ant-design-vue';

import { normalizeList } from '../utils';

interface Props {
  rulesFile?: File | null;
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
const pagination = reactive({
  current: 1,
  pageSize: 100,
  pageSizeOptions: ['10', '20', '50', '100'],
  showSizeChanger: true,
});

const columns = [
  { title: '消息类型', dataIndex: 'msgType', width: 120 },
  { title: '规则描述', dataIndex: 'rule', ellipsis: true },
  { title: '请求字段', dataIndex: 'req_type', width: 200 },
  { title: '响应字段', dataIndex: 'res_type', width: 200 },
];

function resolveMessageType(rule: any, fallback: string) {
  return (
    rule?.group ||
    normalizeList(rule?.req_type)[0] ||
    normalizeList(rule?.res_type)[0] ||
    fallback
  );
}

function normalizeRulesPayload(data: any, sourceLabel: string) {
  const entries: any[] = [];

  if (Array.isArray(data)) {
    entries.push(
      ...data.map((rule) => ({
        rule,
        msgType: resolveMessageType(rule, sourceLabel),
      })),
    );
  } else if (Array.isArray(data?.rules)) {
    entries.push(
      ...data.rules.map((rule: any) => ({
        rule,
        msgType: resolveMessageType(rule, sourceLabel),
      })),
    );
  } else if (Array.isArray(data?.data?.rules)) {
    entries.push(
      ...data.data.rules.map((rule: any) => ({
        rule,
        msgType: resolveMessageType(rule, sourceLabel),
      })),
    );
  } else if (data && typeof data === 'object') {
    for (const [msgType, ruleList] of Object.entries(data)) {
      if (Array.isArray(ruleList)) {
        entries.push(...ruleList.map((rule) => ({ rule, msgType })));
      }
    }
  }

  return entries
    .filter(({ rule }) => rule && typeof rule === 'object')
    .map(({ rule, msgType }, index) => ({
      ...rule,
      group: rule.group || msgType,
      id: `${msgType}-${index}`,
      msgType,
      req_fields: normalizeList(rule.req_fields),
      req_type: rule.req_type ?? [],
      res_fields: normalizeList(rule.res_fields),
      res_type: rule.res_type ?? [],
      rule: String(
        rule.rule || rule.requirement || rule.description || '',
      ).trim(),
    }))
    .filter((rule) => rule.rule);
}

const selectedRule = computed(() => {
  if (selectedRowKeys.value.length === 0) return null;
  return rules.value.find((r) => r.id === selectedRowKeys.value[0]) ?? null;
});

async function loadRules() {
  loading.value = true;
  try {
    let data: any;
    let sourceLabel = 'UPLOADED';
    if (props.rulesFile) {
      data = JSON.parse(await props.rulesFile.text());
      sourceLabel = props.rulesFile.name.replace(/\.json$/i, '') || sourceLabel;
    } else return;

    const flatRules: RuleOption[] = normalizeRulesPayload(data, sourceLabel);
    rules.value = flatRules;
    const lastRule = flatRules.at(-1);
    pagination.current = lastRule
      ? Math.ceil(flatRules.length / pagination.pageSize)
      : 1;
    selectedRowKeys.value = lastRule ? [lastRule.id!] : [];
  } catch (error: any) {
    message.error(`加载规则失败: ${error?.message || error}`);
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

function onTableChange(nextPagination: {
  current?: number;
  pageSize?: number;
}) {
  pagination.current = nextPagination.current ?? pagination.current;
  pagination.pageSize = nextPagination.pageSize ?? pagination.pageSize;
}

watch(() => props.rulesFile, loadRules, { immediate: true });
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
      <Tag color="blue">{{ rulesFile?.name }}</Tag>
      <span class="rule-count">共 {{ rules.length }} 条规则</span>
    </div>

    <Table
      :columns="columns"
      :data-source="rules"
      :loading="loading"
      :pagination="pagination"
      :row-selection="{
        type: 'radio',
        selectedRowKeys,
        onChange: onSelectionChange,
      }"
      row-key="id"
      size="small"
      @change="onTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'req_type'">
          <Tag
            v-for="(field, i) in normalizeList(record.req_type)"
            :key="i"
            color="green"
          >
            {{ field }}
          </Tag>
        </template>
        <template v-else-if="column.dataIndex === 'res_type'">
          <Tag
            v-for="(field, i) in normalizeList(record.res_type)"
            :key="i"
            color="orange"
          >
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
        确认并启动自动化分析流程
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
  font-size: 14px;
  color: var(--ant-text-color-secondary);
}

.stage-card :deep(.ant-card-head-title) {
  font-size: 18px;
}

.stage-card :deep(.ant-tag) {
  padding: 1px 8px;
  font-size: 13px;
  line-height: 22px;
  border-radius: 6px;
}

.stage-card :deep(.ant-table) {
  font-size: 14px;
}

.stage-card :deep(.ant-empty-description) {
  font-size: 14px;
}

.rule-actions {
  padding-top: 20px;
  margin-top: 20px;
  border-top: 1px solid var(--ant-color-border-secondary);
}
</style>
