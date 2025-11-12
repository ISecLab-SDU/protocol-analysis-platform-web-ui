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
  Input,
  message,
  Select,
  Space,
  Spin,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
  Progress,
  AutoComplete,
} from 'ant-design-vue';
import type { ProtocolExtractRuleItem } from '@/api/protocol-compliance';
import { runProtocolExtract } from '@/api/protocol-compliance';

type RuleItem = ProtocolExtractRuleItem & {
  group?: string | null;
};

type HistoryItem = {
  analysisTime: string;
  categories: string[];
  protocol: string;
  version?: string;
  ruleCount: number;
  rules: RuleItem[];
  storeDir?: string;
  resultPath?: string;
};

const HISTORY_KEY = 'protocol_analysis_history';

const activeMenuKey = ref('analyze');
const isAnalyzing = ref(false);
const analysisCompleted = ref(false);
const stagedResults = ref<RuleItem[]>([]);
const rfcFileList = ref<UploadFile[]>([]);
const selectedFile = ref<File | null>(null);
const formData = reactive({
  protocol: '',
  version: '',
  apiKey: '',
  filterHeadings: false,
});
const currentPage = ref(1);
const pageSize = ref(10);
const totalItems = ref(0);
const historyData = ref<HistoryItem[]>([]);
const lastResultMeta = ref<{ storeDir?: string; resultPath?: string } | null>(null);
const analysisProgress = ref(0);
const progressText = ref('准备分析...');

const TypographyParagraph = Typography.Paragraph;
const TypographyText = Typography.Text;

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

const SPLIT_PATTERN = /[,;/]|(?:\bor\b)|(?:\band\b)/gi;

function normalizeProtocolName(input: string) {
  return input
    .trim()
    .replaceAll(/\s+/g, '')
    .replaceAll(/[^\w./-]/g, '')
    .toLowerCase();
}

function normalizeVersionName(input: string) {
  return normalizeProtocolName(input);
}

function randomCategories(): string[] {
  const shuffled = [...ruleCategories].sort(() => Math.random() - 0.5);
  const count = Math.floor(Math.random() * 2) + 3;
  return shuffled.slice(0, count);
}

function toArray(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item ?? '').trim())
      .filter((item) => Boolean(item));
  }
  if (typeof value === 'string') {
    if (!value.trim()) return [];
    const segments = value
      .split(SPLIT_PATTERN)
      .map((segment) => segment.trim())
      .filter((segment) => Boolean(segment));
    return segments.length ? segments : [value.trim()];
  }
  return [];
}

function normalizeRuleItem(raw: any): RuleItem {
  const ruleText = typeof raw?.rule === 'string' ? raw.rule.trim() : String(raw?.rule ?? '').trim();
  return {
    rule: ruleText,
    group: raw?.group ?? null,
    req_type: toArray(raw?.req_type),
    req_fields: toArray(raw?.req_fields),
    res_type: toArray(raw?.res_type),
    res_fields: toArray(raw?.res_fields),
  };
}

const beforeUploadRFC: UploadProps['beforeUpload'] = (file) => {
  const allowedTypes = ['text/html', 'application/pdf', 'text/plain', 'application/json'];
  const isAllowed = allowedTypes.includes(file.type);
  const isAllowedExt = ['.html', '.pdf', '.txt', '.json'].some((ext) =>
    file.name.toLowerCase().endsWith(ext),
  );
  if (!isAllowed && !isAllowedExt) {
    message.error('仅支持上传 HTML、PDF、TXT 或 JSON 格式的协议文档');
    return false;
  }
  const originalFile = (file as UploadFile & { originFileObj?: File }).originFileObj;
  selectedFile.value = originalFile ?? ((file as unknown) as File);
  rfcFileList.value = [file];
  return false;
};

const removeRFC: UploadProps['onRemove'] = () => {
  selectedFile.value = null;
  rfcFileList.value = [];
  return true;
};

function loadHistoryFromStorage() {
  try {
    const saved = localStorage.getItem(HISTORY_KEY);
    const parsed = saved ? JSON.parse(saved) : [];
    if (!Array.isArray(parsed)) {
      historyData.value = [];
      return;
    }
    historyData.value = parsed
      .map((item: any) => {
        const rules = Array.isArray(item?.rules)
          ? item.rules
              .map(normalizeRuleItem)
              .filter((rule) => rule.rule)
          : [];
        return {
          analysisTime: String(item?.analysisTime ?? ''),
          categories: Array.isArray(item?.categories) ? item.categories : [],
          protocol: String(item?.protocol ?? ''),
          version: item?.version ? String(item.version) : undefined,
          ruleCount: typeof item?.ruleCount === 'number' ? item.ruleCount : rules.length,
          rules,
          storeDir: item?.storeDir ? String(item.storeDir) : undefined,
          resultPath: item?.resultPath ? String(item.resultPath) : undefined,
        } as HistoryItem;
      })
      .filter((item: HistoryItem) => item.protocol && item.rules.length > 0);
  } catch {
    historyData.value = [];
  }
}

async function startAnalysis() {
  const uploadFile = selectedFile.value;
  const protocol = formData.protocol.trim();
  const version = formData.version.trim();
  const apiKey = formData.apiKey.trim();

  if (!uploadFile) {
    message.warning('请先上传协议文档 (HTML/PDF/TXT/JSON)');
    return;
  }
  if (!protocol) {
    message.warning('请输入或选择协议类型');
    return;
  }
  if (!version) {
    message.warning('请输入协议版本');
    return;
  }
  if (!apiKey) {
    message.warning('请输入 DeepSeek API 密钥');
    return;
  }

  isAnalyzing.value = true;
  analysisCompleted.value = false;
  stagedResults.value = [];
  selectedGroup.value = null;
  currentPage.value = 1;
  lastResultMeta.value = null;
  analysisProgress.value = 0;
  progressText.value = '准备分析...';

  const progressInterval = setInterval(() => {
    if (analysisProgress.value < 90) {
      analysisProgress.value += Math.floor(Math.random() * 10) + 5;
      if (analysisProgress.value > 30 && analysisProgress.value < 60) {
        progressText.value = '正在提取协议规则...';
      } else if (analysisProgress.value >= 60) {
        progressText.value = '正在整理规则数据...';
      }
    }
  }, 500);

  try {
    const response = await runProtocolExtract({
      apiKey,
      protocol,
      version,
      htmlFile: uploadFile,
      filterHeadings: formData.filterHeadings,
    });

    clearInterval(progressInterval);
    analysisProgress.value = 100;
    progressText.value = '分析完成！';

    const rules = Array.isArray(response.rules)
      ? response.rules.map(normalizeRuleItem).filter((rule) => rule.rule)
      : [];

    if (rules.length === 0) {
      throw new Error('分析流程完成，但未生成任何规则');
    }

    stagedResults.value = rules;
    totalItems.value = rules.length;
    analysisCompleted.value = true;
    lastResultMeta.value = {
      storeDir: response.storeDir,
      resultPath: response.resultPath,
    };

    const now = new Date().toLocaleString();
    const newHistory: HistoryItem = {
      protocol,
      version: response.version,
      ruleCount: rules.length,
      analysisTime: now,
      categories: randomCategories(),
      rules,
      storeDir: response.storeDir,
      resultPath: response.resultPath,
    };

    historyData.value.unshift(newHistory);
    historyData.value = historyData.value.slice(0, 20);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(historyData.value));

    message.success(`分析成功，提取到 ${rules.length} 条规则`);
  } catch (error: any) {
    clearInterval(progressInterval);
    analysisProgress.value = 0;
    progressText.value = '分析失败';

    const details = error?.response?.data?.details;
    let detailMessage = error?.response?.data?.message || error?.message || '未知错误';
    if (details) {
      if (typeof details === 'string') {
        detailMessage = details;
      } else if (typeof details === 'object') {
        if (typeof details.message === 'string' && details.message.trim()) {
          detailMessage = details.message;
        } else if (Array.isArray(details.stderr) && details.stderr.length) {
          detailMessage = details.stderr.join('\n');
        } else if (Array.isArray(details.stdout) && details.stdout.length) {
          detailMessage = details.stdout.join('\n');
        } else {
          detailMessage = JSON.stringify(details);
        }
      }
    }
    console.error('分析失败', error);
    message.error(`分析失败: ${detailMessage}`);
  } finally {
    isAnalyzing.value = false;
  }
}

function downloadAnalysisResult() {
  if (!analysisCompleted.value || stagedResults.value.length === 0) {
    message.warning('暂无分析结果可下载');
    return;
  }
  const normalizedProtocol = normalizeProtocolName(formData.protocol || 'protocol');
  const normalizedVersion = normalizeVersionName(formData.version || 'v');
  const fileName = `ruleConfig_${normalizedProtocol}_${normalizedVersion}.json`;
  const jsonStr = JSON.stringify(stagedResults.value, null, 2);

  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
  message.success(`分析结果已下载：${fileName}`);
}

function openFromHistory(item: HistoryItem) {
  formData.protocol = item.protocol;
  formData.version = item.version ?? '';
  stagedResults.value = item.rules ?? [];
  totalItems.value = stagedResults.value.length;
  analysisCompleted.value = stagedResults.value.length > 0;
  selectedGroup.value = null;
  currentPage.value = 1;
  activeMenuKey.value = 'analyze';
  lastResultMeta.value = {
    storeDir: item.storeDir,
    resultPath: item.resultPath,
  };
}

const selectedGroup = ref<null | string>(null);
const groupList = computed(() => {
  const groups = new Set(
    stagedResults.value.map((r) => r.group).filter((group): group is string => Boolean(group)),
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

// 修复：简化标签渲染逻辑，避免无效字符
const renderTagList = (value: unknown, color: string) => {
  const items = Array.isArray(value) ? (value as string[]) : [];
  if (!items.length) {
    return h('span', { class: 'table-empty' }, '-');
  }
  // 过滤无效字符
  const validItems = items.map(item => item.replace(/[^\x20-\x7E\u4E00-\u9FA5]/g, ''))
    .filter(item => item.trim());
  
  return h(
    Space,
    { size: 'small', wrap: true },
    validItems.map((item, index) =>
      h(
        Tag,
        {
          color: color,
          key: `tag-${index}`, // 修复：使用简单有序key
          style: { margin: '2px' }
        },
        () => item
      )
    )
  );
};

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
    width: 420,
    customRender: ({ text }) => {
      // 过滤规则描述中的无效字符
      const validText = String(text ?? '').replace(/[^\x20-\x7E\u4E00-\u9FA5]/g, '');
      return h('div', { style: 'white-space: pre-wrap;' }, validText);
    },
  },
  {
    title: '协议消息类型',
    dataIndex: 'req_type',
    key: 'req_type',
    width: 180,
    customRender: ({ text }) => renderTagList(text, 'purple'),
  },
  {
    title: '请求字段',
    dataIndex: 'req_fields',
    key: 'req_fields',
    width: 220,
    customRender: ({ text }) => renderTagList(text, 'blue'),
  },
  {
    title: '响应类型',
    dataIndex: 'res_type',
    key: 'res_type',
    width: 180,
    customRender: ({ text }) => renderTagList(text, 'orange'),
  },
  {
    title: '响应字段',
    dataIndex: 'res_fields',
    key: 'res_fields',
    width: 220,
    customRender: ({ text }) => renderTagList(text, 'green'),
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
    customRender: ({ record }) => {
      const item = record as HistoryItem;
      const protocolLabel = item.protocol ?? '';
      const versionLabel = item.version ? `(${item.version})` : '';
      // 过滤无效字符
      const validProtocol = protocolLabel.replace(/[^\x20-\x7E\u4E00-\u9FA5]/g, '');
      const validVersion = versionLabel.replace(/[^\x20-\x7E\u4E00-\u9FA5]/g, '');
      
      return h(
        Tag,
        {
          color: 'cyan',
          style: { cursor: 'pointer' },
          onClick: () => openFromHistory(item)
        },
        () => `${validProtocol}${validVersion}`
      );
    },
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
    customRender: ({ text }) => {
      const validText = String(text ?? '未知').replace(/[^\x20-\x7E\u4E00-\u9FA5]/g, '');
      return h(Tag, { color: 'default' }, validText);
    },
  },
  {
    title: '规则分类',
    dataIndex: 'categories',
    key: 'categories',
    customRender: ({ text }) => {
      const categories = Array.isArray(text) ? text : [];
      const colors = ['magenta', 'purple', 'blue', 'cyan', 'green', 'orange', 'volcano'];
      // 过滤无效字符并去重
      const validCategories = Array.from(new Set(
        categories.map(cat => cat.replace(/[^\x20-\x7E\u4E00-\u9FA5]/g, ''))
          .filter(cat => cat.trim())
      ));
      
      return validCategories.map((category, index) =>
        h(
          Tag,
          {
            color: colors[index % colors.length],
            key: `category-${index}`, // 修复：使用简单有序key
            style: { margin: '2px' }
          },
          () => category
        )
      );
    },
  },
]);

onMounted(() => {
  loadHistoryFromStorage();
});
</script>

<template>
  <Page title="协议规则提取">
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
              <Spin :spinning="isAnalyzing" tip="正在执行协议规则提取...">
                <Form class="extract-form" layout="vertical">
                  <FormItem label="协议类型">
                    <AutoComplete
                      v-model:value="formData.protocol"
                      allow-clear
                      class="input-protocol"
                      placeholder="选择或输入协议类型"
                      :options="[
                        { value: 'CoAP' },
                        { value: 'DHCPv6' },
                        { value: 'MQTTv3_1_1' },
                        { value: 'MQTTv5' },
                        { value: 'TLSv1_3' },
                        { value: 'FTP' }
                      ]"
                    />
                  </FormItem>
                  <FormItem label="协议版本">
                    <Input
                      v-model:value="formData.version"
                      placeholder="请输入协议版本，如 4 或 1.1"
                    />
                  </FormItem>
                  <FormItem label="DeepSeek API 密钥">
                    <Input.Password
                      v-model:value="formData.apiKey"
                      autocomplete="off"
                      placeholder="用于调用 DeepSeek 的 API 密钥"
                    />
                  </FormItem>
                  <FormItem label="协议文档">
                    <Upload
                      :before-upload="beforeUploadRFC"
                      :file-list="rfcFileList"
                      :max-count="1"
                      :on-remove="removeRFC"
                    >
                      <Button block type="dashed">
                        <IconifyIcon icon="ant-design:file-add-outlined" class="mr-1" />
                        选择协议文档
                      </Button>
                    </Upload>
                  </FormItem>
                  <FormItem label="启用目录筛选">
                    <Switch v-model:checked="formData.filterHeadings" />
                  </FormItem>
                  <TypographyParagraph class="form-tip" type="secondary">
                    支持 HTML、PDF、TXT、JSON 文档，建议上传已预处理的 HTML 文件。所有内容仅用于本地演示。
                  </TypographyParagraph>
                  
                  <FormItem v-if="isAnalyzing" :colon="false">
                    <div class="analysis-progress">
                      <TypographyText type="secondary" class="progress-text">{{ progressText }}</TypographyText>
                      <Progress 
                        :percent="analysisProgress" 
                        :status="analysisCompleted ? 'success' : 'active'"
                        :stroke-width="8"
                      />
                    </div>
                  </FormItem>

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
                  <span v-if="selectedGroup">· 已筛选 {{ filteredResults.length }} 条</span>
                </TypographyText>
                <Space size="small" wrap>
                  <Select
                    v-model:value="selectedGroup"
                    allow-clear
                    class="select-group"
                    :disabled="!analysisCompleted || !groupList.length"
                    placeholder="筛选消息组别"
                  >
                    <Select.Option v-for="g in groupList" :key="`group-${g}`" :value="g">
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
              <TypographyParagraph
                v-if="analysisCompleted && lastResultMeta"
                class="result-meta"
                type="secondary"
              >
                结果文件路径：{{ lastResultMeta.resultPath || '未知' }}
                <span v-if="lastResultMeta.storeDir">（存储目录：{{ lastResultMeta.storeDir }}）</span>
              </TypographyParagraph>
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
                  :row-key="(record, index) => `row-${index}`"
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
                  :key="`history-tag-${index}`"
                  color="blue"
                >
                  {{ item.version ? `${item.protocol}(${item.version})` : item.protocol }}
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
                :row-key="(record, index) => `history-row-${index}`"
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
:deep(.mb-2.flex.text-lg.font-semibold) {
  font-size: 2.25rem;
}

.protocol-extract {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100vh; /* ✅ 不再用 height: 100% */
  height: auto;
  overflow-y: auto;  /* ✅ 可滚动 */
  padding-bottom: 24px; /* ✅ 防止底部被截断 */
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

.form-card,
.result-card {
  display: flex;
  flex-direction: column;
  height: auto; /* ✅ 防止锁死高度 */
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

.analysis-progress {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}

.progress-text {
  font-size: 13px;
}

:deep(.ant-progress) {
  width: 100%;
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

.result-meta {
  margin: 0;
  font-size: 12px;
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

.table-empty {
  color: var(--ant-text-color-secondary);
}

@media (max-width: 1200px) {
  .analyze-layout {
    grid-template-columns: 1fr;
  }
}
</style>
