<script lang="ts" setup>
import { ref, reactive, computed, h } from 'vue';
import { Card, Empty, Space, Button, Tag, message, Input, Upload, Spin, Table, Typography, Divider, Select, Tabs } from 'ant-design-vue';
import type { UploadFile, UploadProps, TableColumnType } from 'ant-design-vue';

// -------- 数据类型 --------
type RuleItem = {
  rule: string;
  req_type: string[];
  req_fields: string[];
  res_type: string[];
  res_fields: string[];
  group?: string;
};

type HistoryItem = {
  protocol: string;
  ruleCount: number;
  analysisTime: string;
  categories: string[];
  rules: RuleItem[];
};

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

// -------- 规则分类 --------
const ruleCategories = [
  '安全', '性能', '兼容', '基础', '高级',
  '加密', '认证', '会话管理', '可靠性', '优化',
  '错误处理', '日志', '扩展性', 'QoS', '协议约束'
];

// -------- 工具函数 --------
function normalizeProtocolName(input: string) {
  return input.trim().replace(/\s+/g, '').replace(/[^a-zA-Z0-9._/-]/g, '').toLowerCase();
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
  const isAllowedExt = ['.pdf', '.txt', '.json'].some(ext => file.name.toLowerCase().endsWith(ext));
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

// -------- 开始分析 --------
async function startAnalysis() {
  if (rfcFileList.value.length === 0) {
    message.warning('请先上传 RFC 文件');
    return;
  }
  if (!formData.protocol.replace(/\s/g, '')) {
    message.warning('请输入或选择协议类型');
    return;
  }

  isAnalyzing.value = true;
  analysisCompleted.value = false;
  stagedResults.value = [];

  try {
    await new Promise(resolve => setTimeout(resolve, 1500));
    const normalizedProtocol = normalizeProtocolName(formData.protocol);
    const fileName = `ruleConfig_${normalizedProtocol}.json`;
    const response = await fetch(`/${fileName}`);
    if (!response.ok) throw new Error(`未找到 ${formData.protocol} 对应的规则文件`);

    const rawData = await response.json();
    let rules: RuleItem[] = [];
    if (Array.isArray(rawData)) {
      rules = rawData;
    } else if (typeof rawData === 'object' && rawData !== null) {
      Object.entries(rawData).forEach(([groupName, arr]) => {
        if (Array.isArray(arr)) arr.forEach(rule => rules.push({ ...rule, group: groupName }));
      });
    } else throw new Error('规则文件格式不正确，应为数组或对象类型');

    if (rules.length === 0) throw new Error('未在规则文件中找到任何规则数据');

    stagedResults.value = rules;
    totalItems.value = rules.length;
    analysisCompleted.value = true;

    const now = new Date().toLocaleString();
    historyData.value.unshift({
      protocol: formData.protocol,
      ruleCount: rules.length,
      analysisTime: now,
      categories: randomCategories(),
      rules: rules,
    });

    message.success(`成功加载 ${rules.length} 条规则`);
  } catch (err: any) {
    message.error(`分析失败: ${err.message}`);
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
  activeMenuKey.value = 'analyze';
}

// -------- 表格相关 --------
const selectedGroup = ref<string | null>(null);
const groupList = computed(() => {
  const groups = new Set(stagedResults.value.map(r => r.group).filter(Boolean));
  return Array.from(groups);
});
const filteredResults = computed(() => {
  if (!selectedGroup.value) return stagedResults.value;
  return stagedResults.value.filter(r => r.group === selectedGroup.value);
});
const currentPageData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredResults.value.slice(start, start + pageSize.value);
});

const columns: TableColumnType<RuleItem>[] = [
  { title: '序号', key: 'index', width: 60, customRender: ({ index }) => ((currentPage.value - 1) * pageSize.value + index + 1) },
  { title: '规则描述', dataIndex: 'rule', key: 'rule', width: 400, customRender: ({ text }) => h('div', { style: 'white-space: pre-wrap;' }, text) },
  { title: '协议消息类型', dataIndex: 'req_type', key: 'req_type', width: 140 },
  { title: '请求字段', dataIndex: 'req_fields', key: 'req_fields', width: 220,
    customRender: ({ text }) => Array.isArray(text) ? text.map(f => h(Tag, { color: 'blue', style: 'margin:2px' }, () => f)) : text
  },
  { title: '响应类型', dataIndex: 'res_type', key: 'res_type', width: 140 },
  { title: '响应字段', dataIndex: 'res_fields', key: 'res_fields', width: 220,
    customRender: ({ text }) => Array.isArray(text) ? text.map(f => h(Tag, { color: 'green', style: 'margin:2px' }, () => f)) : text
  },
];

function handleTableChange(pagination: any) {
  currentPage.value = pagination.current;
  pageSize.value = pagination.pageSize;
}
</script>

<template>
  <div class="page-container">
    <Tabs v-model:activeKey="activeMenuKey">
      <Tabs.TabPane key="analyze" tab="规则提取" />
      <Tabs.TabPane key="history" tab="历史记录" />
    </Tabs>

    <!-- 分析页面 -->
    <div v-if="activeMenuKey === 'analyze'" class="main-content">
      <Typography.Paragraph class="step-desc">
        将协议文档分块处理，再通过大模型分析，快速提取规则。
      </Typography.Paragraph>

      <Card class="card-upload">
        <div class="upload-header">
          <Typography.Title level="4" style="margin-bottom:8px;">
            📄 上传 RFC 文件
          </Typography.Title>
          <Typography.Text type="secondary">
            请输入或选择协议类型，然后上传文件进行规则分析
          </Typography.Text>
        </div>

        <div class="upload-row">
          <Select
            v-model:value="formData.protocol"
            show-search
            placeholder="选择或输入协议类型"
            class="input-protocol"
            allow-clear
            :filter-option="(input, option) => option?.value?.toLowerCase().includes(input.toLowerCase())"
          >
            <Select.Option value="CoAP">CoAP</Select.Option>
            <Select.Option value="DHCPv6">DHCPv6</Select.Option>
            <Select.Option value="MQTTv3_1_1">MQTTv3_1_1</Select.Option>
            <Select.Option value="MQTTv5">MQTTv5</Select.Option>
            <Select.Option value="TLSv1_3">TLSv1_3</Select.Option>
            <Select.Option value="FTP">FTP</Select.Option>
          </Select>

          <Upload :file-list="rfcFileList" :before-upload="beforeUploadRFC" :on-remove="removeRFC" :max-count="1">
            <Button type="default" ghost>选择 RFC 文件</Button>
          </Upload>

          <Button type="primary" class="btn-analyze" :loading="isAnalyzing" @click="startAnalysis">
            🚀 开始分析
          </Button>
        </div>

        <div v-if="isAnalyzing" class="spin-overlay">
          <Spin tip="正在分析 RFC 文件..." size="large" />
        </div>
      </Card>

      <Card v-if="analysisCompleted" class="card-result">
        <div class="result-header">
          <Typography.Title level="4">{{ formData.protocol }} 协议规则</Typography.Title>
          <div class="result-tools">
            <Typography.Text>共 {{ totalItems }} 条规则</Typography.Text>
            <Select v-model:value="selectedGroup" allow-clear placeholder="筛选消息组别" class="select-group">
              <Select.Option v-for="g in groupList" :key="g" :value="g">{{ g }}</Select.Option>
            </Select>
            <Button type="primary" @click="downloadAnalysisResult">⬇️ 下载 JSON</Button>
          </div>
        </div>
        <Divider />
        <div v-if="filteredResults.length === 0">
          <Empty description="未找到规则数据" />
        </div>
        <div class="table-wrapper" v-else>
          <Table
            :columns="columns"
            :data-source="currentPageData"
            :pagination="{
              current: currentPage,
              pageSize: pageSize,
              total: filteredResults.length,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: total => `共 ${total} 条规则`
            }"
            :row-key="(record, index) => index"
            @change="handleTableChange"
            bordered
            :scroll="{ x: 'max-content', y: 400 }"
          />
        </div>
      </Card>
    </div>

    <!-- 历史记录页面 -->
    <div v-if="activeMenuKey === 'history'" class="main-content">
      <Card class="card-history">
        <div class="analyzed-protocols">
          <Typography.Text strong>已分析的协议：</Typography.Text>
          <Space size="small" wrap>
            <Tag v-for="item in historyData" :key="item.protocol" color="blue">{{ item.protocol }}</Tag>
          </Space>
        </div>

        <Table
          :columns="[
            {
              title: '协议',
              dataIndex: 'protocol',
              key: 'protocol',
              customRender: ({ text, record }) => h(Tag, { color: 'cyan', style:'cursor:pointer' }, () =>
                h('a', { onClick: () => openFromHistory(record) }, text)
              )
            },
            { title: '规则数量', dataIndex: 'ruleCount', key: 'ruleCount', customRender: ({ text }) => h(Tag, { color: 'green' }, text) },
            { title: '分析时间', dataIndex: 'analysisTime', key: 'analysisTime', customRender: ({ text }) => h(Tag, { color: 'default' }, text) },
            { 
              title: '规则分类', 
              dataIndex: 'categories', 
              key: 'categories', 
              customRender: ({ text }) => text.map((c, idx) => {
                const colors = ['magenta','purple','blue','cyan','green','orange','volcano'];
                return h(Tag, { color: colors[idx % colors.length], style: 'margin-right:4px' }, c)
              })
            }
          ]"
          :data-source="historyData"
          :pagination="{ pageSize: 10, showSizeChanger: true, showQuickJumper: true }"
          :row-key="(record, index) => index"
          bordered
          :scroll="{ x: 'max-content' }"
        />
      </Card>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  min-height: 100vh;
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  font-family: "Segoe UI", "Helvetica Neue", sans-serif;
}

.step-desc {
  font-size: 15px;
  color: #333;
  background: linear-gradient(90deg, #f0f5ff 0%, #f9faff 100%);
  padding: 10px 18px;
  border-radius: 8px;
  text-align: center;
  margin-bottom: 18px;
  font-weight: 500;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-upload, .card-result, .card-history {
  padding: 24px;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.upload-header {
  margin-bottom: 18px;
  text-align: center;
}

.upload-row {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.input-protocol {
  width: 260px;
}

.btn-analyze {
  background: linear-gradient(90deg, #1677ff 0%, #5b9aff 100%);
  border: none;
  transition: all 0.3s;
}
.btn-analyze:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.spin-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255,255,255,0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 8px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.result-tools {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.select-group {
  width: 200px;
}

.table-wrapper {
  max-height: 400px;
  overflow-y: auto;
}

.analyzed-protocols {
  margin-bottom: 12px;
  padding: 8px 0;
}

:deep(.ant-table-cell) {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>

