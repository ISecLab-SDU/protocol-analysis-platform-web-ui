<script lang="ts" setup>
import type { UploadFile, UploadProps } from 'ant-design-vue';

import { computed, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';

import {
  Button,
  Card,
  Divider,
  Empty,
  Form,
  FormItem,
  Input,
  message,
  Select,
  SelectOption,
  Space,
  Table,
  TabPane,
  Tabs,
  Tag,
  Upload,
} from 'ant-design-vue';

import {
  addAnalysisHistory,
  getAnalysisHistory,
  getDetectionResults,
} from '#/api/protocol-compliance';

// 类型定义
interface DetectionResult {
  id: number;
  rule_desc: string;
  code_snippet: string;
  llm_response: { reason: string; result: string };
}

interface HistoryRecord {
  id: string;
  implementationName: string;
  protocolName: string;
  statistics: {
    noResult: number;
    noViolations: number;
    total: number;
    violations: number;
  };
  createdAt: string;
}

// 路由与标题
const route = useRoute();
const title = computed(() => String(route.meta?.title ?? '静态规则分析'));

// 标签页状态
const activeTab = ref('input');

// 文件列表状态
const rulesFileList = ref<UploadFile[]>([]);
const sourceCodeFileList = ref<UploadFile[]>([]);

// 表单数据
const formData = reactive({
  protocolName: '',
  implementationName: '',
  rulesFile: null as File | null,
  sourceCodeFile: null as File | null,
  selectedModel: '',
});
const formLoading = ref(false);

// 检测结果状态
const detectionResults = ref<DetectionResult[]>([]);
const detectionLoading = ref(false);

// 历史记录状态
const historyRecords = ref<HistoryRecord[]>([]);
const historyLoading = ref(false);

// 上传文件控制
const beforeUploadRules: UploadProps['beforeUpload'] = (file) => {
  rulesFileList.value = [file];
  formData.rulesFile =
    (file as UploadFile<File>).originFileObj ?? (file as any as File);
  return false;
};
const removeRules: UploadProps['onRemove'] = () => {
  rulesFileList.value = [];
  formData.rulesFile = null;
  return true;
};

const beforeUploadSourceCode: UploadProps['beforeUpload'] = (file) => {
  sourceCodeFileList.value = [file];
  formData.sourceCodeFile =
    (file as UploadFile<File>).originFileObj ?? (file as any as File);
  return false;
};
const removeSourceCode: UploadProps['onRemove'] = () => {
  sourceCodeFileList.value = [];
  formData.sourceCodeFile = null;
  return true;
};

// 是否可以开始分析
const canStartAnalysis = computed(() => {
  return !!(
    formData.protocolName &&
    formData.implementationName &&
    formData.rulesFile &&
    formData.sourceCodeFile &&
    formData.selectedModel
  );
});

// 表格列定义
const detectionColumns = [
  { title: '序号', key: 'index', width: 60 },
  {
    title: '原始规则',
    dataIndex: 'rule_desc',
    key: 'rule_desc',
    width: '25%',
    ellipsis: true,
  },
  {
    title: '代码切片',
    dataIndex: 'code_snippet',
    key: 'code_snippet',
    width: '35%',
  },
  {
    title: '分析结果',
    dataIndex: 'llm_response',
    key: 'llm_response',
    width: '40%',
  },
];

const historyColumns = [
  { title: '序号', key: 'index', width: 60 },
  {
    title: '协议实现',
    dataIndex: 'implementationName',
    key: 'implementationName',
    width: '25%',
  },
  {
    title: '协议类型',
    dataIndex: 'protocolName',
    key: 'protocolName',
    width: '20%',
  },
  { title: '分析结果', key: 'statistics', width: '55%' },
];

// 开始分析
async function handleStartAnalysis() {
  if (!formData.protocolName || !formData.implementationName) {
    message.error('请填写协议名称和协议实现名称');
    return;
  }
  if (!formData.rulesFile || !formData.sourceCodeFile) {
    message.error('请上传规则文件和源代码文件');
    return;
  }
  if (!formData.selectedModel) {
    message.error('请选择大模型');
    return;
  }

  formLoading.value = true;
  try {
    message.loading('正在分析结果，请稍候...', 0);
    await new Promise((resolve) => setTimeout(resolve, 5000));
    message.destroy();

    const response = await getDetectionResults(formData.implementationName);
    detectionResults.value = response.items;

    await addAnalysisHistory({
      implementationName: formData.implementationName,
      protocolName: formData.protocolName,
    });

    activeTab.value = 'detection';
    message.success('分析完成');
  } catch (error: any) {
    message.destroy();
    message.error(error.message || '加载失败');
  } finally {
    formLoading.value = false;
  }
}

// 加载历史记录
async function loadHistory() {
  historyLoading.value = true;
  try {
    const response = await getAnalysisHistory();
    historyRecords.value = response.items;
  } catch {
    message.error('加载历史记录失败');
  } finally {
    historyLoading.value = false;
  }
}

// 查看历史记录详情
async function viewHistoryDetail(record: HistoryRecord) {
  formData.implementationName = record.implementationName;
  formData.protocolName = record.protocolName;
  detectionLoading.value = true;
  try {
    const response = await getDetectionResults(record.implementationName);
    detectionResults.value = response.items;
    activeTab.value = 'detection';
  } catch {
    message.error('加载失败');
  } finally {
    detectionLoading.value = false;
  }
}

// 结果状态颜色
function getResultColor(result: string): string {
  const lowerResult = result.toLowerCase();
  if (lowerResult.includes('no violation')) return 'green';
  if (lowerResult.includes('violation')) return 'red';
  return 'orange';
}

// 结果状态文本
function getResultText(result: string): string {
  const lowerResult = result.toLowerCase();
  if (lowerResult.includes('no violation')) return '✓ 符合规则';
  if (lowerResult.includes('violation')) return '✗ 违反规则';
  return '⚠ 需要审查';
}

// 标签页切换
function handleTabChange(key: string) {
  if (key === 'history') loadHistory();
}

// 检测结果统计
const detectionStatistics = computed(() => {
  const total = detectionResults.value.length;
  let violations = 0;
  let noViolations = 0;
  let noResult = 0;

  detectionResults.value.forEach((item) => {
    const res = item.llm_response.result.toLowerCase();
    if (res.includes('violation')) violations++;
    else if (res.includes('no violation')) noViolations++;
    else noResult++;
  });

  return { total, violations, noViolations, noResult };
});
</script>

<template>
  <div class="static-analysis-page">
    <div class="page-header">
      <h1>{{ title }}</h1>
      <p>协议合规性静态分析 - 上传文件并输入协议信息查看分析结果</p>
    </div>

    <Card>
      <Tabs v-model:active-key="activeTab" @change="handleTabChange">
        <!-- 输入标签页 -->
        <TabPane key="input" tab="输入协议信息">
          <Form
            :model="formData"
            layout="vertical"
            style="max-width: 800px; margin: 0 auto"
          >
            <!-- 协议+规则 -->
            <div style="display: flex; flex-wrap: wrap; gap: 16px">
              <FormItem label="协议名称" style="flex: 1">
                <Input
                  v-model:value="formData.protocolName"
                  placeholder="输入协议名称"
                  list="protocol-options"
                />
                <datalist id="protocol-options">
                  <option value="CoAP"></option>
                  <option value="DHCPv6"></option>
                  <option value="MQTTv3_1_1"></option>
                  <option value="MQTTv5"></option>
                  <option value="TLSv1_3"></option>
                  <option value="FTP"></option>
                </datalist>
              </FormItem>

              <FormItem label="规则文件" style="flex: 1">
                <Upload
                  :file-list="rulesFileList"
                  :before-upload="beforeUploadRules"
                  :on-remove="removeRules"
                  :max-count="1"
                >
                  <Button block>选择规则文件</Button>
                </Upload>
              </FormItem>
            </div>

            <!-- 协议实现+源代码 -->
            <div
              style="
                display: flex;
                flex-wrap: wrap;
                gap: 16px;
                margin-top: 16px;
              "
            >
              <FormItem label="协议实现名称" style="flex: 1">
                <Input
                  v-model:value="formData.implementationName"
                  placeholder="输入协议实现名称"
                />
              </FormItem>

              <FormItem label="协议源代码实现" style="flex: 1">
                <Upload
                  :file-list="sourceCodeFileList"
                  :before-upload="beforeUploadSourceCode"
                  :on-remove="removeSourceCode"
                  :max-count="1"
                >
                  <Button block>选择源代码文件</Button>
                </Upload>
              </FormItem>
            </div>

            <!-- 大模型选择 -->
            <div
              style="
                display: flex;
                flex-wrap: wrap;
                gap: 16px;
                margin-top: 16px;
              "
            >
              <FormItem label="选择大模型" style="flex: 1">
                <Select
                  v-model:value="formData.selectedModel"
                  placeholder="请选择大模型"
                >
                  <SelectOption value="GPT-4-32k">GPT-4 32k</SelectOption>
                  <SelectOption value="GPT-4-0613">GPT-4 0613</SelectOption>
                  <SelectOption value="GPT-3.5-turbo">
                    GPT-3.5 Turbo
                  </SelectOption>
                  <SelectOption value="Claude-2">Claude 2</SelectOption>
                  <SelectOption value="LLaMA-2-13B">LLaMA 2 13B</SelectOption>
                  <SelectOption value="MPT-7B">MPT-7B</SelectOption>
                  <SelectOption value="Gemini-1">Gemini 1</SelectOption>
                  <SelectOption value="PaLM-2">PaLM 2</SelectOption>
                  <SelectOption value="Falcon-40B">Falcon 40B</SelectOption>
                  <SelectOption value="Vicuna-13B">Vicuna 13B</SelectOption>
                </Select>
              </FormItem>
            </div>

            <FormItem style="margin-top: 24px">
              <Button
                type="primary"
                :loading="formLoading"
                :disabled="!canStartAnalysis"
                @click="handleStartAnalysis"
                block
              >
                开始分析
              </Button>
            </FormItem>
          </Form>
        </TabPane>

        <!-- 检测结果标签页 -->
        <TabPane key="detection" tab="代码切片与检测">
          <div v-if="detectionResults.length === 0">
            <Empty description="暂无检测结果,请先输入协议信息" />
          </div>

          <div v-else>
            <!-- 统计信息 -->
            <div style="margin-bottom: 16px">
              <Space>
                <span>总数: {{ detectionStatistics.total }}</span>
                <Tag color="red">
                  违规: {{ detectionStatistics.violations }}
                </Tag>
                <Tag color="green">
                  符合: {{ detectionStatistics.noViolations }}
                </Tag>
                <Tag color="orange">
                  待定: {{ detectionStatistics.noResult }}
                </Tag>
              </Space>
            </div>

            <!-- 表格 -->
            <Table
              :columns="detectionColumns"
              :data-source="detectionResults"
              :loading="detectionLoading"
              :pagination="{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条记录`,
              }"
              :scroll="{ x: 1200 }"
            >
              <template #bodyCell="{ column, record, index }">
                <template v-if="column.key === 'index'">
                  {{ index + 1 }}
                </template>
                <template v-else-if="column.key === 'code_snippet'">
                  <pre class="code-snippet">{{ record.code_snippet }}</pre>
                </template>
                <template v-else-if="column.key === 'llm_response'">
                  <div class="analysis-result">
                    <Tag :color="getResultColor(record.llm_response.result)">
                      {{ getResultText(record.llm_response.result) }}
                    </Tag>
                    <Divider style="margin: 8px 0" />
                    <div class="reason-text">
                      <strong>详细说明:</strong>
                      <p>{{ record.llm_response.reason }}</p>
                    </div>
                  </div>
                </template>
              </template>
            </Table>
          </div>
        </TabPane>

        <!-- 历史记录标签页 -->
        <TabPane key="history" tab="历史记录">
          <Table
            :columns="historyColumns"
            :data-source="historyRecords"
            :loading="historyLoading"
            :pagination="{
              pageSize: 10,
              showTotal: (total) => `共 ${total} 条记录`,
            }"
          >
            <template #bodyCell="{ column, record, index }">
              <template v-if="column.key === 'index'">
                {{ index + 1 }}
              </template>
              <template v-else-if="column.key === 'implementationName'">
                <a @click="viewHistoryDetail(record)">{{
                  record.implementationName
                }}</a>
              </template>
              <template v-else-if="column.key === 'statistics'">
                <Space>
                  <span>总数: {{ record.statistics.total }}</span>
                  <Tag color="red">
                    违规: {{ record.statistics.violations }}
                  </Tag>
                  <Tag color="green">
                    符合: {{ record.statistics.noViolations }}
                  </Tag>
                  <Tag color="orange">
                    待定: {{ record.statistics.noResult }}
                  </Tag>
                </Space>
              </template>
            </template>
          </Table>
        </TabPane>
      </Tabs>
    </Card>
  </div>
</template>

<style scoped>
.static-analysis-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.page-header p {
  margin: 8px 0 0;
  color: rgb(0 0 0 / 65%);
}

.code-snippet {
  max-height: 200px;
  padding: 8px;
  margin: 0;
  overflow-y: auto;
  font-family: 'Fira Code', Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  word-break: break-all;
  white-space: pre-wrap;
  background: #f5f5f5;
  border-radius: 4px;
}

.analysis-result {
  padding: 8px 0;
}

.reason-text {
  margin-top: 8px;
}

.reason-text p {
  margin: 4px 0;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}
</style>
