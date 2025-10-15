<script lang="ts" setup>
import type { FormInstance, UploadFile, UploadProps } from 'ant-design-vue';
import type { Rule } from 'ant-design-vue/es/form';

import type {
  ProtocolStaticAnalysisComplianceStatus,
  ProtocolStaticAnalysisResult,
} from '#/api';

import { computed, onBeforeUnmount, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { useTimeoutFn } from '@vueuse/core';
import {
  Button,
  Card,
  Descriptions,
  Empty,
  Form,
  FormItem,
  Input,
  message,
  Space,
  Spin,
  Tag,
  Typography,
  Upload,
} from 'ant-design-vue';

import { runProtocolStaticAnalysis } from '#/api';

const TypographyText = Typography.Text;
const TypographyParagraph = Typography.Paragraph;

const remoteApiEnabled =
  import.meta.env.VITE_ENABLE_PROTOCOL_COMPLIANCE_API !== 'false';

type AnalysisPhase = 'completed' | 'idle' | 'processing' | 'uploading';

const formRef = ref<FormInstance>();
const formState = reactive({
  code: null as File | null,
  notes: '',
  rules: null as File | null,
});

const rulesFileList = ref<UploadFile[]>([]);
const codeFileList = ref<UploadFile[]>([]);

const isSubmitting = ref(false);
const analysisResult = ref<null | ProtocolStaticAnalysisResult>(null);
const pendingResult = ref<null | ProtocolStaticAnalysisResult>(null);
const analysisPhase = ref<AnalysisPhase>('idle');
const isWaiting = computed(
  () =>
    analysisPhase.value === 'uploading' || analysisPhase.value === 'processing',
);
const waitingTip = computed(() =>
  analysisPhase.value === 'uploading'
    ? '正在上传分析输入，请稍候...'
    : 'LLM 正在对齐规则与代码，请稍候...',
);
const MIN_PROCESSING_DELAY = 1200;
let processingTimer: null | ReturnType<typeof useTimeoutFn> = null;

const statusMeta: Record<
  ProtocolStaticAnalysisComplianceStatus,
  { color: string; label: string }
> = {
  compliant: {
    color: 'success',
    label: '符合',
  },
  needs_review: {
    color: 'warning',
    label: '需复核',
  },
  non_compliant: {
    color: 'error',
    label: '不符合',
  },
};

const formRules: Record<string, Rule[]> = {
  rules: [
    {
      message: '请上传协议规则 JSON 文件',
      required: true,
      trigger: 'change',
    },
  ],
  code: [
    {
      message: '请上传待分析的代码片段',
      required: true,
      trigger: 'change',
    },
  ],
};

const verdicts = computed(
  () => analysisResult.value?.modelResponse.verdicts ?? [],
);
const summary = computed(
  () => analysisResult.value?.modelResponse.summary ?? null,
);
const metadata = computed(
  () => analysisResult.value?.modelResponse.metadata ?? null,
);
const hasResult = computed(
  () => analysisPhase.value === 'completed' && analysisResult.value !== null,
);

function resetForm() {
  formRef.value?.resetFields();
  formState.rules = null;
  formState.code = null;
  formState.notes = '';
  rulesFileList.value = [];
  codeFileList.value = [];
  formRef.value?.clearValidate?.();
}

const handleRulesBeforeUpload: UploadProps['beforeUpload'] = (file) => {
  const actualFile =
    (file as UploadFile<File>).originFileObj ?? (file as unknown as File);
  rulesFileList.value = [file];
  formState.rules = actualFile;
  formRef.value?.clearValidate?.(['rules']);
  return false;
};

const handleRulesRemove: UploadProps['onRemove'] = () => {
  rulesFileList.value = [];
  formState.rules = null;
  formRef.value?.validateFields?.(['rules']);
  return true;
};

const handleCodeBeforeUpload: UploadProps['beforeUpload'] = (file) => {
  const actualFile =
    (file as UploadFile<File>).originFileObj ?? (file as unknown as File);
  codeFileList.value = [file];
  formState.code = actualFile;
  formRef.value?.clearValidate?.(['code']);
  return false;
};

const handleCodeRemove: UploadProps['onRemove'] = () => {
  codeFileList.value = [];
  formState.code = null;
  formRef.value?.validateFields?.(['code']);
  return true;
};

async function handleSubmit() {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }

  const rulesFile = formState.rules;
  const codeFile = formState.code;
  if (!rulesFile || !codeFile) {
    message.error('请选择要上传的协议规则和代码文件');
    return;
  }

  if (!remoteApiEnabled) {
    message.warning('当前环境未启用协议静态分析接口');
    return;
  }

  isSubmitting.value = true;
  analysisResult.value = null;
  pendingResult.value = null;
  analysisPhase.value = 'uploading';
  processingTimer?.stop();
  processingTimer = null;

  try {
    const result = await runProtocolStaticAnalysis({
      code: codeFile,
      notes: formState.notes.trim() || undefined,
      rules: rulesFile,
    });
    pendingResult.value = result;
    analysisPhase.value = 'processing';
    processingTimer = useTimeoutFn(() => {
      analysisResult.value = pendingResult.value;
      analysisPhase.value = 'completed';
      processingTimer = null;
      message.success('静态分析完成');
    }, MIN_PROCESSING_DELAY);
  } catch (error) {
    console.warn('[protocol-compliance] Failed to run static analysis', error);
    message.error('静态分析失败，请稍后再试');
    analysisPhase.value = 'idle';
    pendingResult.value = null;
  } finally {
    isSubmitting.value = false;
  }
}

function handleDownloadJson() {
  const result = analysisResult.value;
  if (!result) {
    return;
  }
  const jsonContent = JSON.stringify(result.modelResponse, null, 2);
  const blob = new Blob([jsonContent], { type: 'application/json' });
  const url = window.URL.createObjectURL(blob);
  const filename = `${result.inputs.protocolName || 'protocol'}-static-analysis.json`;
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function handleReset() {
  resetForm();
  analysisResult.value = null;
  pendingResult.value = null;
  analysisPhase.value = 'idle';
  processingTimer?.stop();
  processingTimer = null;
}

onBeforeUnmount(() => {
  processingTimer?.stop();
  processingTimer = null;
});
</script>

<template>
  <Page
    description="上传协议规则和对应代码片段，调用 LLM 静态分析模型评估实现是否符合规范。"
    title="LLM 非合规检测"
  >
    <div class="static-analysis">
      <Card>
        <Space
          align="start"
          class="w-full flex-col justify-between md:flex-row"
          size="large"
        >
          <div class="flex flex-col gap-2">
            <p class="intro-text">
              基于 ProtocolGuard 流程，我们会读取上传的规范 JSON
              与代码片段，触发 LLM
              进行一次静态一致性检测，并输出逐条规则的符合情况。
            </p>
            <p class="intro-helper">
              输入文件需手动选择：规则描述（JSON）与代码片段。提交后等待模型返回结果。
            </p>
            <p class="intro-helper">
              模型结果支持在页面上查看，也可以下载原始 JSON 文件以便复核或归档。
            </p>
            <p class="intro-helper">
              当前环境：
              <Tag v-if="remoteApiEnabled" color="blue">Mock 静态分析服务</Tag>
              <Tag v-else color="red">接口未启用</Tag>
            </p>
          </div>
          <Space size="small">
            <Button @click="handleReset">重置</Button>
            <Button
              :disabled="!remoteApiEnabled"
              :loading="isSubmitting"
              type="primary"
              @click="handleSubmit"
            >
              开始分析
            </Button>
          </Space>
        </Space>
      </Card>

      <Card title="提交数据">
        <Form
          ref="formRef"
          :model="formState"
          :rules="formRules"
          layout="vertical"
        >
          <FormItem label="协议规则描述（JSON）" name="rules" required>
            <Upload
              :before-upload="handleRulesBeforeUpload"
              :file-list="rulesFileList"
              :max-count="1"
              :on-remove="handleRulesRemove"
              accept=".json,application/json"
            >
              <Button block>选择 JSON 文件</Button>
            </Upload>
            <p class="upload-helper">
              请选择由规则提取流程导出的结构化
              JSON。文件不会立即上传，仅在提交时发送。
            </p>
          </FormItem>

          <FormItem label="代码片段文件" name="code" required>
            <Upload
              :before-upload="handleCodeBeforeUpload"
              :file-list="codeFileList"
              :max-count="1"
              :on-remove="handleCodeRemove"
            >
              <Button block>选择代码文件</Button>
            </Upload>
            <p class="upload-helper">
              支持任意文本代码文件，例如 .c、.py、.go。请确保与规则描述对应。
            </p>
          </FormItem>

          <FormItem label="备注" name="notes">
            <Input.TextArea
              v-model:value="formState.notes"
              :auto-size="{ minRows: 3, maxRows: 5 }"
              placeholder="可选：说明规则版本、测试场景或重点关注项"
            />
          </FormItem>
        </Form>
      </Card>

      <Card v-if="analysisPhase !== 'idle'" title="分析结果">
        <template #extra>
          <Space v-if="hasResult && summary" size="small">
            <Tag :color="statusMeta[summary.overallStatus].color">
              {{ statusMeta[summary.overallStatus].label }}
            </Tag>
            <Button type="link" @click="handleDownloadJson">下载 JSON</Button>
          </Space>
        </template>

        <div v-if="isWaiting" class="analysis-waiting">
          <Spin size="large" :tip="waitingTip" />
        </div>

        <template v-else-if="hasResult">
          <Descriptions
            bordered
            column="1"
            :label-style="{ minWidth: '120px' }"
            size="small"
          >
            <Descriptions.Item label="协议 / 组件">
              {{ analysisResult?.inputs.protocolName }}
            </Descriptions.Item>
            <Descriptions.Item label="规则文件">
              {{ analysisResult?.inputs.rulesFileName }}
            </Descriptions.Item>
            <Descriptions.Item label="代码文件">
              {{ analysisResult?.inputs.codeFileName }}
            </Descriptions.Item>
            <Descriptions.Item label="规则摘要">
              {{ analysisResult?.inputs.rulesSummary || '未提供' }}
            </Descriptions.Item>
            <Descriptions.Item label="备注">
              {{ analysisResult?.inputs.notes || '无' }}
            </Descriptions.Item>
            <Descriptions.Item label="模型版本">
              {{ metadata?.modelVersion }}
            </Descriptions.Item>
            <Descriptions.Item label="生成时间">
              {{ metadata?.generatedAt }}
            </Descriptions.Item>
            <Descriptions.Item label="耗时">
              {{ analysisResult?.durationMs }} ms
            </Descriptions.Item>
          </Descriptions>

          <div class="verdict-summary" v-if="summary && hasResult">
            <Card size="small">
              <div class="summary-grid">
                <div class="summary-item">
                  <span class="summary-label">符合</span>
                  <span class="summary-value">{{
                    summary.compliantCount
                  }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">不符合</span>
                  <span class="summary-value">{{
                    summary.nonCompliantCount
                  }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">需复核</span>
                  <span class="summary-value">{{
                    summary.needsReviewCount
                  }}</span>
                </div>
              </div>
            </Card>
          </div>

          <div v-if="verdicts.length > 0" class="verdict-list">
            <ol>
              <li v-for="verdict in verdicts" :key="verdict.findingId">
                <Card :body-style="{ padding: '16px' }" size="small">
                  <Space class="w-full justify-between" align="start">
                    <div class="verdict-header">
                      <TypographyText strong>
                        {{ verdict.relatedRule.id }}
                      </TypographyText>
                      <TypographyParagraph class="mb-2" type="secondary">
                        {{ verdict.relatedRule.requirement }}
                      </TypographyParagraph>
                      <div class="verdict-detail">
                        <span class="detail-label">来源：</span>
                        <span>{{ verdict.relatedRule.source }}</span>
                      </div>
                      <div class="verdict-detail">
                        <span class="detail-label">说明：</span>
                        <span>{{ verdict.explanation }}</span>
                      </div>
                      <div class="verdict-detail">
                        <span class="detail-label">位置：</span>
                        <span>
                          {{ verdict.location.file }}
                          <template v-if="verdict.location.function">
                            · {{ verdict.location.function }}
                          </template>
                          <template v-if="verdict.lineRange">
                            · 行 {{ verdict.lineRange[0] }} -
                            {{ verdict.lineRange[1] }}
                          </template>
                        </span>
                      </div>
                      <div class="verdict-detail">
                        <span class="detail-label">信心：</span>
                        <span>{{ verdict.confidence }}</span>
                      </div>
                      <div v-if="verdict.recommendation" class="verdict-detail">
                        <span class="detail-label">建议：</span>
                        <span>{{ verdict.recommendation }}</span>
                      </div>
                    </div>
                    <Tag :color="statusMeta[verdict.compliance].color">
                      {{ statusMeta[verdict.compliance].label }}
                    </Tag>
                  </Space>
                </Card>
              </li>
            </ol>
          </div>
          <Empty v-else description="模型未返回任何判定结果" />
        </template>
      </Card>
    </div>
  </Page>
</template>

<style scoped>
.static-analysis {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.intro-text {
  margin: 0;
  line-height: 1.6;
  color: var(--ant-text-color);
}

.intro-helper {
  margin: 0;
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}

.upload-helper {
  margin-top: 8px;
  margin-bottom: 0;
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}

.verdict-summary {
  margin-top: 16px;
}

.analysis-waiting {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 16px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: center;
  min-width: 90px;
  padding: 8px 12px;
  text-align: center;
}

.summary-label {
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}

.summary-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--ant-text-color);
}

.verdict-list {
  margin-top: 16px;
}

.verdict-list ol {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.verdict-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 720px;
}

.verdict-detail {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 13px;
  color: var(--ant-text-color);
}

.detail-label {
  flex-shrink: 0;
  width: 72px;
  color: var(--ant-text-color-secondary);
  text-align: right;
}

@media (max-width: 768px) {
  .summary-item {
    min-width: 72px;
  }
}
</style>
