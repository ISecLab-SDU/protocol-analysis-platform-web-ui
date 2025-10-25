<script lang="ts" setup>
import type { TableColumnType, UploadFile, UploadProps } from 'ant-design-vue';

import { computed, h, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  Button,
  Card,
  Empty,
  Form,
  FormItem,
  message,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
} from 'ant-design-vue';

// -------- 数据类型 --------
type RuleItem = {
  group?: string;
  req_fields: string[];
  req_type: string[];
  res_fields: string[];
  res_type: string[];
  rule: string;
};

type HistoryItem = {
  analysisTime: string;
  categories: string[];
  protocol: string;
  ruleCount: number;
  rules: RuleItem[];
};

// -------- 历史记录存储 KEY --------
const HISTORY_KEY = 'protocol_analysis_history';

// -------- 状态 --------
const activeMenuKey = ref('analyze');
const isAnalyzing = ref(false);
const analysisCompleted = ref(false);
const stagedResults = ref<RuleItem[]>([]);
const rfcFileList = ref<UploadFile[]>([]);
const formData = reactive({ protocol: '' });
const currentPage = ref(1);
const pageSize = ref(10);
const totalItems = ref(0);
const historyData = ref<HistoryItem[]>([]);

const TypographyParagraph = Typography.Paragraph;
const TypographyText = Typography.Text;

// -------- 规则分类 --------
const ruleCategories = [
  '安全',
  '性能',
  '兼容',
  '基础',
  '高级',
  '加密',
  '认证',
  '会话管理',
  '可靠性',
  '优化',
  '错误处理',
  '日志',
  '扩展性',
  'QoS',
  '协议约束',
];

// -------- 工具函数 --------
function normalizeProtocolName(input: string) {
  return input
    .trim()
    .replaceAll(/\s+/g, '')
    .replaceAll(/[^\w./-]/g, '')
    .toLowerCase();
}

function randomCategories(): string[] {
  const shuffled = [...ruleCategories].sort(() => Math.random() - 0.5);
  const count = Math.floor(Math.random() * 2) + 3;
  return shuffled.slice(0, count);
}

// -------- 上传文件控制 --------
const beforeUploadRFC: UploadProps['beforeUpload'] = (file) => {
  const allowedTypes = ['application/pdf', 'text/plain', 'application/json'];
  const isAllowed = allowedTypes.includes(file.type);
  const isAllowedExt = ['.pdf', '.txt', '.json'].some((ext) =>
    file.name.toLowerCase().endsWith(ext),
  );
  if (!isAllowed && !isAllowedExt) {
    message.error('仅支持上传 PDF、TXT 或 JSON 格式的 RFC 文件');
    return false;
  }
  rfcFileList.value = [file];
  return false;
};

const removeRFC: UploadProps['onRemove'] = () => {
  rfcFileList.value = [];
  return true;
};

// -------- 初始化历史记录 --------
function loadHistoryFromStorage() {
  try {
    const saved = localStorage.getItem(HISTORY_KEY);
    const parsed = saved ? JSON.parse(saved) : [];
    historyData.value = Array.isArray(parsed) ? parsed : [];
  } catch {
    historyData.value = [];
  }
}

// -------- 开始分析 --------
async function startAnalysis() {
  if (rfcFileList.value.length === 0) {
    message.warning('请先上传 RFC 文件');
    return;
  }
  if (!formData.protocol.replaceAll(/\s/g, '')) {
    message.warning('请输入或选择协议类型');
    return;
  }

  isAnalyzing.value = true;
  analysisCompleted.value = false;
  stagedResults.value = [];
  selectedGroup.value = null;
  currentPage.value = 1;

  try {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    const normalizedProtocol = normalizeProtocolName(formData.protocol);
    const fileName = `ruleConfig_${normalizedProtocol}.json`;
    const response = await fetch(`/${fileName}`);
    if (!response.ok)
      throw new Error(`未找到 ${formData.protocol} 对应的规则文件`);

    const rawData = await response.json();
    let rules: RuleItem[] = [];
    if (Array.isArray(rawData)) {
      rules = rawData;
    } else if (typeof rawData === 'object' && rawData !== null) {
      Object.entries(rawData).forEach(([groupName, arr]) => {
        if (Array.isArray(arr))
          arr.forEach((rule) => rules.push({ ...rule, group: groupName }));
      });
    } else throw new Error('规则文件格式不正确，应为数组或对象类型');

    if (rules.length === 0) throw new Error('未在规则文件中找到任何规则数据');

    stagedResults.value = rules;
    totalItems.value = rules.length;
    analysisCompleted.value = true;

    const now = new Date().toLocaleString();
    const newHistory: HistoryItem = {
      protocol: formData.protocol,
      ruleCount: rules.length,
      analysisTime: now,
      categories: randomCategories(),
      rules,
    };

    // 插入历史记录并持久化
    historyData.value.unshift(newHistory);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(historyData.value));

    message.success(`成功加载 ${rules.length} 条规则`);
  } catch (error: any) {
    message.error(`分析失败: ${error.message}`);
  } finally {
    isAnalyzing.value = false;
  }
}

// -------- 下载 JSON --------
function downloadAnalysisResult() {
  if (!analysisCompleted.value || stagedResults.value.length === 0) {
    message.warning('暂无分析结果可下载');
    return;
  }
  const normalizedProtocol = normalizeProtocolName(formData.protocol);
  const fileName = `ruleConfig_${normalizedProtocol}.json`;
  const jsonStr = JSON.stringify(stagedResults.value, null, 2);

  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
  message.success(`分析结果已下载: ${fileName}`);
}

// -------- 历史记录点击协议回到分析页面 --------
function openFromHistory(item: HistoryItem) {
  formData.protocol = item.protocol;
  stagedResults.value = item.rules;
  totalItems.value = item.rules.length;
  analysisCompleted.value = true;
  selectedGroup.value = null;
  currentPage.value = 1;
  activeMenuKey.value = 'analyze';
}

// -------- 表格相关 --------
const selectedGroup = ref<null | string>(null);
const groupList = computed(() => {
  const groups = new Set(
    stagedResults.value.map((r) => r.group).filter(Boolean),
  );
  return [...groups];
});
const filteredResults = computed(() => {
  if (!selectedGroup.value) return stagedResults.value;
  return stagedResults.value.filter((r) => r.group === selectedGroup.value);
});
const currentPageData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredResults.value.slice(start, start + pageSize.value);
});

const columns: TableColumnType<RuleItem>[] = [
  {
    title: '序号',
    key: 'index',
    width: 60,
    customRender: ({ index }) =>
      (currentPage.value - 1) * pageSize.value + index + 1,
  },
  {
    title: '规则描述',
    dataIndex: 'rule',
    key: 'rule',
    width: 400,
    customRender: ({ text }) =>
      h('div', { style: 'white-space: pre-wrap;' }, text),
  },
  { title: '协议消息类型', dataIndex: 'req_type', key: 'req_type', width: 140 },
  {
    title: '请求字段',
    dataIndex: 'req_fields',
    key: 'req_fields',
    width: 220,
    customRender: ({ text }) =>
      Array.isArray(text)
        ? text.map((f) =>
            h(Tag, { color: 'blue', style: 'margin:2px' }, () => f),
          )
        : text,
  },
  { title: '响应类型', dataIndex: 'res_type', key: 'res_type', width: 140 },
  {
    title: '响应字段',
    dataIndex: 'res_fields',
    key: 'res_fields',
    width: 220,
    customRender: ({ text }) =>
      Array.isArray(text)
        ? text.map((f) =>
            h(Tag, { color: 'green', style: 'margin:2px' }, () => f),
          )
        : text,
  },
];

function handleTableChange(pagination: any) {
  currentPage.value = pagination.current;
  pageSize.value = pagination.pageSize;
}

const historyColumns = computed<TableColumnType<HistoryItem>[]>(() => [
  {
    title: '协议',
    dataIndex: 'protocol',
    key: 'protocol',
    customRender: ({ text, record }) =>
      h(
        Tag,
        {
          color: 'cyan',
          style: 'cursor: pointer',
        },
        () =>
          h(
            'a',
            {
              onClick: () => openFromHistory(record as HistoryItem),
            },
            String(text ?? ''),
          ),
      ),
  },
  {
    title: '规则数量',
    dataIndex: 'ruleCount',
    key: 'ruleCount',
    customRender: ({ text }) => h(Tag, { color: 'green' }, String(text ?? '0')),
  },
  {
    title: '分析时间',
    dataIndex: 'analysisTime',
    key: 'analysisTime',
    customRender: ({ text }) =>
      h(Tag, { color: 'default' }, String(text ?? '未知')),
  },
  {
    title: '规则分类',
    dataIndex: 'categories',
    key: 'categories',
    customRender: ({ text }) => {
      const categories = Array.isArray(text) ? text : [];
      const colors = [
        'magenta',
        'purple',
        'blue',
        'cyan',
        'green',
        'orange',
        'volcano',
      ];
      return categories.map((category, index) =>
        h(
          Tag,
          {
            color: colors[index % colors.length],
            key: `${String(category)}-${index}`,
            style: 'margin: 2px',
          },
          () => category,
        ),
      );
    },
  },
]);

// -------- 页面挂载时加载历史记录 --------
onMounted(() => {
  loadHistoryFromStorage();
});
</script>

<template>
  <Page
    description="上传协议类型与 RFC 文件，生成结构化的协议规则供静态分析与后续验证。"
    title="协议规则提取"
  >
    <div class="protocol-extract">
      <Tabs v-model:active-key="activeMenuKey" class="extract-tabs">
        <Tabs.TabPane key="analyze" tab="规则提取">
          <div class="analyze-layout">
            <Card class="form-card">
              <template #title>
                <Space>
                  <IconifyIcon icon="ant-design:cloud-upload-outlined" class="text-lg" />
                  <span>上传协议资料</span>
                </Space>
              </template>
              <Spin :spinning="isAnalyzing" tip="正在分析 RFC 文件...">
                <Form class="extract-form" layout="vertical">
                  <FormItem label="协议类型">
                    <Select
                      v-model:value="formData.protocol"
                      allow-clear
                      class="input-protocol"
                      placeholder="选择或输入协议类型"
                      show-search
                      :filter-option="
                        (input, option) =>
                          option?.value?.toLowerCase().includes(input.toLowerCase())
                      "
                    >
                      <Select.Option value="CoAP">CoAP</Select.Option>
                      <Select.Option value="DHCPv6">DHCPv6</Select.Option>
                      <Select.Option value="MQTTv3_1_1">MQTTv3_1_1</Select.Option>
                      <Select.Option value="MQTTv5">MQTTv5</Select.Option>
                      <Select.Option value="TLSv1_3">TLSv1_3</Select.Option>
                      <Select.Option value="FTP">FTP</Select.Option>
                    </Select>
                  </FormItem>
                  <FormItem label="RFC 文件">
                    <Upload
                      :before-upload="beforeUploadRFC"
                      :file-list="rfcFileList"
                      :max-count="1"
                      :on-remove="removeRFC"
                    >
                      <Button block type="dashed">
                        <IconifyIcon icon="ant-design:file-add-outlined" class="mr-1" />
                        选择 RFC 文件
                      </Button>
                    </Upload>
                  </FormItem>
                  <TypographyParagraph class="form-tip" type="secondary">
                    支持 PDF、TXT 或 JSON 文件，上传内容仅用于本地演示。
                  </TypographyParagraph>
                  <FormItem class="form-actions" :colon="false">
                    <Space>
                      <Button
                        type="primary"
                        :loading="isAnalyzing"
                        @click="startAnalysis"
                      >
                        <IconifyIcon icon="ant-design:play-circle-outlined" class="mr-1" />
                        开始分析
                      </Button>
                    </Space>
                  </FormItem>
                </Form>
              </Spin>
            </Card>
            <Card class="result-card">
              <template #title>
                <Space>
                  <IconifyIcon icon="ant-design:profile-outlined" class="text-lg" />
                  <span>规则预览</span>
                </Space>
              </template>
              <div class="result-toolbar">
                <TypographyText type="secondary">
                  共 {{ totalItems }} 条规则
                  <span v-if="selectedGroup">
                    · 已筛选 {{ filteredResults.length }} 条
                  </span>
                </TypographyText>
                <Space size="small" wrap>
                  <Select
                    v-model:value="selectedGroup"
                    allow-clear
                    class="select-group"
                    :disabled="!analysisCompleted || !groupList.length"
                    placeholder="筛选消息组别"
                  >
                    <Select.Option v-for="g in groupList" :key="g" :value="g">
                      {{ g }}
                    </Select.Option>
                  </Select>
                  <Button
                    :disabled="!analysisCompleted || !stagedResults.length"
                    @click="downloadAnalysisResult"
                  >
                    <IconifyIcon icon="ant-design:download-outlined" class="mr-1" />
                    下载 JSON
                  </Button>
                </Space>
              </div>
              <div
                v-if="analysisCompleted && filteredResults.length"
                class="table-wrapper"
              >
                <Table
                  :columns="columns"
                  :data-source="currentPageData"
                  :pagination="{
                    current: currentPage,
                    pageSize,
                    total: filteredResults.length,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 条规则`,
                  }"
                  :row-key="(record, index) => index"
                  :scroll="{ x: 'max-content', y: 400 }"
                  bordered
                  @change="handleTableChange"
                />
              </div>
              <Empty
                v-else-if="analysisCompleted"
                description="未找到规则数据"
              />
              <TypographyParagraph
                v-else
                class="result-placeholder"
                type="secondary"
              >
                上传协议资料并启动分析后将展示提取到的规则列表。
              </TypographyParagraph>
            </Card>
          </div>
        </Tabs.TabPane>
        <Tabs.TabPane key="history" tab="历史记录">
          <Card class="history-card">
            <template #title>
              <Space>
                <IconifyIcon icon="ant-design:calendar-outlined" class="text-lg" />
                <span>历史记录</span>
              </Space>
            </template>
            <div v-if="historyData.length" class="history-header">
              <TypographyText type="secondary">已分析协议</TypographyText>
              <Space size="small" wrap class="history-protocols">
                <Tag
                  v-for="(item, index) in historyData"
                  :key="`${item.protocol}-${index}`"
                  color="blue"
                >
                  {{ item.protocol }}
                </Tag>
              </Space>
            </div>
            <TypographyParagraph class="history-tip" type="secondary">
              历史数据保存在浏览器本地，方便快速回看最近一次的分析结果。
            </TypographyParagraph>
            <div class="history-table-wrapper">
              <Table
                :columns="historyColumns"
                :data-source="historyData"
                :pagination="{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true,
                }"
                :row-key="(record, index) => index"
                bordered
                :scroll="{ x: 'max-content' }"
              >
                <template #emptyText>
                  <Empty description="暂无历史记录" />
                </template>
              </Table>
            </div>
          </Card>
        </Tabs.TabPane>
      </Tabs>
    </div>
  </Page>
</template>


<style scoped>
.protocol-extract {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.extract-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 16px;
}

.analyze-layout {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 16px;
  align-items: start;
}

.form-card,
.result-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.form-card :deep(.ant-card-body),
.result-card :deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.extract-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.input-protocol {
  width: 100%;
}

.form-tip {
  margin: 0;
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.form-actions {
  margin: 0;
}

.result-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.select-group {
  min-width: 180px;
}

.table-wrapper {
  flex: 1;
  min-height: 240px;
}

.result-placeholder {
  margin: 0;
  font-size: 13px;
}

.history-card :deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.history-protocols {
  display: inline-flex;
  gap: 8px;
  flex-wrap: wrap;
}

.history-tip {
  margin: 0;
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.history-table-wrapper {
  width: 100%;
}

:deep(.ant-table-cell) {
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 1200px) {
  .analyze-layout {
    grid-template-columns: 1fr;
  }
}
</style>
