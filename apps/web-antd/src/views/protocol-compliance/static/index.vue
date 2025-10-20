<script lang="ts" setup>
import type { FormInstance, UploadFile, UploadProps } from 'ant-design-vue';
import type { Rule } from 'ant-design-vue/es/form';

import { computed, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import type { ProtocolStaticAnalysisResult } from '@/api/protocol-compliance';
import { runProtocolStaticAnalysis } from '@/api/protocol-compliance';

import {
  Button,
  Card,
  Descriptions,
  Form,
  FormItem,
  Input,
  message,
  Space,
  Typography,
  Upload,
} from 'ant-design-vue';

const TypographyParagraph = Typography.Paragraph;
const TypographyText = Typography.Text;

const formRef = ref<FormInstance>();
const formState = reactive({
  archive: null as File | null,
  builder: null as File | null,
  config: null as File | null,
  rules: null as File | null,
  notes: '',
});

const archiveFileList = ref<UploadFile[]>([]);
const builderFileList = ref<UploadFile[]>([]);
const configFileList = ref<UploadFile[]>([]);
const rulesFileList = ref<UploadFile[]>([]);
const isSubmitting = ref(false);
const analysisResult = ref<ProtocolStaticAnalysisResult | null>(null);

const formRules: Record<string, Rule[]> = {
  archive: [
    {
      message: '请上传完整项目压缩包',
      required: true,
      trigger: 'change',
    },
  ],
  builder: [
    {
      message: '请上传 Builder Dockerfile',
      required: true,
      trigger: 'change',
    },
  ],
  config: [
    {
      message: '请上传 TOML 配置文件',
      required: true,
      trigger: 'change',
    },
  ],
  rules: [
    {
      message: '请上传协议规则 JSON 文件',
      required: true,
      trigger: 'change',
    },
  ],
};

const formatter = new Intl.DateTimeFormat(undefined, {
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  month: '2-digit',
  year: 'numeric',
});

const STATUS_LABELS: Record<string, string> = {
  compliant: '合规',
  needs_review: '需复核',
  non_compliant: '发现问题',
};

function formatFileSize(bytes: null | number | undefined) {
  if (!bytes || bytes <= 0) {
    return '0 B';
  }
  const units = ['B', 'KB', 'MB', 'GB'];
  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** exponent;
  const digits = value >= 10 || exponent === 0 ? 0 : 1;
  return `${value.toFixed(digits)} ${units[exponent]}`;
}

function formatIsoDate(value: string | undefined | null) {
  if (!value) {
    return '未知';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return formatter.format(parsed);
}

const configMeta = computed(() => {
  const file = formState.config;
  if (!file) {
    return null;
  }
  return {
    name: file.name,
    size: formatFileSize(file.size),
    updatedAt: formatter.format(file.lastModified),
  };
});

const builderMeta = computed(() => {
  const file = formState.builder;
  if (!file) {
    return null;
  }
  return {
    name: file.name,
    size: formatFileSize(file.size),
    updatedAt: formatter.format(file.lastModified),
  };
});

const archiveMeta = computed(() => {
  const file = formState.archive;
  if (!file) {
    return null;
  }
  return {
    name: file.name,
    size: formatFileSize(file.size),
    updatedAt: formatter.format(file.lastModified),
  };
});

const rulesMeta = computed(() => {
  const file = formState.rules;
  if (!file) {
    return null;
  }
  return {
    name: file.name,
    size: formatFileSize(file.size),
    updatedAt: formatter.format(file.lastModified),
  };
});

const hasSelection = computed(
  () =>
    Boolean(
      configMeta.value ||
        archiveMeta.value ||
        builderMeta.value ||
        rulesMeta.value ||
        formState.notes.trim(),
    ),
);

const analysisSummary = computed(
  () => analysisResult.value?.modelResponse.summary ?? null,
);
const analysisMetadata = computed(
  () => analysisResult.value?.modelResponse.metadata ?? null,
);
const analysisVerdictCount = computed(
  () => analysisResult.value?.modelResponse.verdicts.length ?? 0,
);
const analysisStatusLabel = computed(() => {
  const status = analysisSummary.value?.overallStatus ?? '';
  if (!status) {
    return '未知';
  }
  return STATUS_LABELS[status] ?? status;
});

const handleBuilderBeforeUpload: UploadProps['beforeUpload'] = (file) => {
  const actual =
    (file as UploadFile<File>).originFileObj ?? (file as unknown as File);
  builderFileList.value = [file];
  formState.builder = actual;
  formRef.value?.clearValidate?.(['builder']);
  return false;
};

const handleBuilderRemove: UploadProps['onRemove'] = () => {
  builderFileList.value = [];
  formState.builder = null;
  formRef.value?.validateFields?.(['builder']);
  return true;
};

const handleConfigBeforeUpload: UploadProps['beforeUpload'] = (file) => {
  const actual =
    (file as UploadFile<File>).originFileObj ?? (file as unknown as File);
  configFileList.value = [file];
  formState.config = actual;
  formRef.value?.clearValidate?.(['config']);
  return false;
};

const handleConfigRemove: UploadProps['onRemove'] = () => {
  configFileList.value = [];
  formState.config = null;
  formRef.value?.validateFields?.(['config']);
  return true;
};

const handleArchiveBeforeUpload: UploadProps['beforeUpload'] = (file) => {
  const actual =
    (file as UploadFile<File>).originFileObj ?? (file as unknown as File);
  archiveFileList.value = [file];
  formState.archive = actual;
  formRef.value?.clearValidate?.(['archive']);
  return false;
};

const handleArchiveRemove: UploadProps['onRemove'] = () => {
  archiveFileList.value = [];
  formState.archive = null;
  formRef.value?.validateFields?.(['archive']);
  return true;
};

const handleRulesBeforeUpload: UploadProps['beforeUpload'] = (file) => {
  const actual =
    (file as UploadFile<File>).originFileObj ?? (file as unknown as File);
  rulesFileList.value = [file];
  formState.rules = actual;
  formRef.value?.clearValidate?.(['rules']);
  return false;
};

const handleRulesRemove: UploadProps['onRemove'] = () => {
  rulesFileList.value = [];
  formState.rules = null;
  formRef.value?.validateFields?.(['rules']);
  return true;
};

function handleReset() {
  formRef.value?.resetFields();
  archiveFileList.value = [];
  builderFileList.value = [];
  configFileList.value = [];
  rulesFileList.value = [];
  formState.archive = null;
  formState.builder = null;
  formState.config = null;
  formState.rules = null;
  formState.notes = '';
  analysisResult.value = null;
}

async function handleSubmit() {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }

  const { archive, builder, config, rules } = formState;
  if (!archive || !builder || !config || !rules) {
    return;
  }

  isSubmitting.value = true;
  analysisResult.value = null;
  try {
    const result = await runProtocolStaticAnalysis({
      builderDockerfile: builder,
      codeArchive: archive,
      config,
      notes: formState.notes,
      rules,
    });
    analysisResult.value = result;

    const overallStatus = result.modelResponse.summary.overallStatus;
    const label = STATUS_LABELS[overallStatus] ?? overallStatus ?? '完成';
    message.success(`静态分析完成，整体评估：${label}`);
  } catch (error) {
    analysisResult.value = null;
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <Page
    description="上传源码压缩包、Builder Dockerfile、协议规则 JSON 与分析配置，一键调度 ProtocolGuard Docker 流水线。"
    title="协议静态分析"
  >
    <div class="static-analysis">
      <Card title="流程说明">
        <div class="intro">
          <TypographyParagraph class="intro-text">
            该流程会在可信环境内串联 ProtocolGuard 的 Builder / Main 双容器。
            请提前确认上传的 artefacts 与论文示例结构保持一致。
          </TypographyParagraph>
          <ul class="guide-list">
            <li>准备协议规则提取结果（JSON）与静态分析配置（TOML）。</li>
            <li>提供完整源码压缩包以及用于构建 Builder 镜像的 Dockerfile。</li>
            <li>可选填写备注，记录协议版本、提交 SHA 或其他上下文信息。</li>
          </ul>
          <TypographyText class="placeholder-hint" type="secondary">
            所有文件会直接挂载到容器内部执行分析，请勿上传未经脱敏的敏感数据。
          </TypographyText>
        </div>
      </Card>

      <Card title="上传分析材料">
        <Form
          ref="formRef"
          :model="formState"
          :rules="formRules"
          colon
          layout="vertical"
        >
          <FormItem label="源码压缩包" name="archive" required>
            <Upload
              :before-upload="handleArchiveBeforeUpload"
              :file-list="archiveFileList"
              :max-count="1"
              :on-remove="handleArchiveRemove"
              accept=".zip,.tar,.gz,.tgz,.bz2,.xz,.7z,application/zip,application/x-tar"
            >
              <Button block type="dashed">选择源码压缩包</Button>
            </Upload>
            <p class="upload-helper">
              压缩包需包含项目完整源码及其构建脚本，保持目录结构以便 Builder 复现编译过程。
            </p>
          </FormItem>

          <FormItem label="Builder Dockerfile" name="builder" required>
            <Upload
              :before-upload="handleBuilderBeforeUpload"
              :file-list="builderFileList"
              :max-count="1"
              :on-remove="handleBuilderRemove"
              accept=".Dockerfile,.dockerfile,.txt,.yaml,.yml,.cfg,.conf,text/plain,text/x-dockerfile,application/x-dockerfile,application/x-yaml,text/yaml,application/octet-stream"
            >
              <Button block type="dashed">选择 Dockerfile</Button>
            </Upload>
            <p class="upload-helper">
              Dockerfile 需可独立构建出 Builder 镜像，并在容器运行时写出 <code>program.bc</code> 等必需 artefact。
            </p>
          </FormItem>

          <FormItem label="协议规则（JSON）" name="rules" required>
            <Upload
              :before-upload="handleRulesBeforeUpload"
              :file-list="rulesFileList"
              :max-count="1"
              :on-remove="handleRulesRemove"
              accept=".json,.JSON,application/json,text/json"
            >
              <Button block type="dashed">选择规则 JSON</Button>
            </Upload>
            <p class="upload-helper">
              上传上一阶段规则抽取的输出（例如 MQTTv5.json），用于驱动 LLM 切片与一致性检测。
            </p>
          </FormItem>

          <FormItem label="分析配置（.toml）" name="config" required>
            <Upload
              :before-upload="handleConfigBeforeUpload"
              :file-list="configFileList"
              :max-count="1"
              :on-remove="handleConfigRemove"
              accept=".toml,.TOML,text/toml,text/x-toml,application/toml,text/plain"
            >
              <Button block type="dashed">选择配置文件</Button>
            </Upload>
            <p class="upload-helper">
              配置文件将被注入容器的 <code>/config</code>，我们会自动重写路径指向当前任务工作目录。
            </p>
          </FormItem>

          <FormItem label="备注" name="notes">
            <Input.TextArea
              v-model:value="formState.notes"
              :auto-size="{ minRows: 3, maxRows: 6 }"
              placeholder="可选：说明协议版本、提交记录或其他上下文信息"
            />
          </FormItem>

          <FormItem class="form-actions" :colon="false">
            <Space>
              <Button @click="handleReset">清空</Button>
              <Button
                :loading="isSubmitting"
                type="primary"
                @click="handleSubmit"
              >
                启动分析
              </Button>
            </Space>
          </FormItem>
        </Form>
      </Card>

      <Card v-if="hasSelection" title="已选文件概览">
        <Descriptions bordered column="1" size="small">
          <Descriptions.Item v-if="archiveMeta" label="源码压缩包">
            <div class="file-meta">
              <TypographyText strong>{{ archiveMeta.name }}</TypographyText>
              <span class="file-detail">大小：{{ archiveMeta.size }}</span>
              <span class="file-detail">更新：{{ archiveMeta.updatedAt }}</span>
            </div>
          </Descriptions.Item>
          <Descriptions.Item v-if="builderMeta" label="Builder Dockerfile">
            <div class="file-meta">
              <TypographyText strong>{{ builderMeta.name }}</TypographyText>
              <span class="file-detail">大小：{{ builderMeta.size }}</span>
              <span class="file-detail">更新：{{ builderMeta.updatedAt }}</span>
            </div>
          </Descriptions.Item>
          <Descriptions.Item v-if="rulesMeta" label="协议规则 (JSON)">
            <div class="file-meta">
              <TypographyText strong>{{ rulesMeta.name }}</TypographyText>
              <span class="file-detail">大小：{{ rulesMeta.size }}</span>
              <span class="file-detail">更新：{{ rulesMeta.updatedAt }}</span>
            </div>
          </Descriptions.Item>
          <Descriptions.Item v-if="configMeta" label="分析配置 (TOML)">
            <div class="file-meta">
              <TypographyText strong>{{ configMeta.name }}</TypographyText>
              <span class="file-detail">大小：{{ configMeta.size }}</span>
              <span class="file-detail">更新：{{ configMeta.updatedAt }}</span>
            </div>
          </Descriptions.Item>
          <Descriptions.Item label="备注">
            {{ formState.notes.trim() || '未填写' }}
          </Descriptions.Item>
        </Descriptions>
        <TypographyParagraph class="preview-tip" type="secondary">
          上传后即会发送至后端容器，请确认内容无误再启动分析。
        </TypographyParagraph>
      </Card>

      <Card v-if="analysisResult" title="最新分析结果">
        <Descriptions bordered column="1" size="small">
          <Descriptions.Item label="整体评估">
            <div class="analysis-overview">
              <span
                :class="['status-tag', `status-${analysisSummary?.overallStatus ?? 'unknown'}`]"
              >
                {{ analysisStatusLabel }}
              </span>
              <span class="analysis-detail">
                合规 {{ analysisSummary?.compliantCount ?? 0 }} · 需复核
                {{ analysisSummary?.needsReviewCount ?? 0 }} · 不合规
                {{ analysisSummary?.nonCompliantCount ?? 0 }}
              </span>
            </div>
          </Descriptions.Item>
          <Descriptions.Item v-if="analysisMetadata" label="协议信息">
            {{ analysisMetadata.protocol }}
            {{ analysisMetadata.protocolVersion || '' }} ｜ 规则集：
            {{ analysisMetadata.ruleSet }}
          </Descriptions.Item>
          <Descriptions.Item label="生成时间">
            {{ formatIsoDate(analysisMetadata?.generatedAt) }}
          </Descriptions.Item>
          <Descriptions.Item label="判定条目">
            共 {{ analysisVerdictCount }} 条
          </Descriptions.Item>
        </Descriptions>
        <TypographyParagraph
          v-if="analysisSummary?.notes"
          class="preview-tip"
          type="secondary"
        >
          {{ analysisSummary?.notes }}
        </TypographyParagraph>
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

.intro {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.intro-text {
  margin: 0;
  line-height: 1.6;
}

.guide-list {
  padding-left: 20px;
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--ant-text-color);
}

.placeholder-hint {
  font-size: 13px;
}

.upload-helper {
  margin-top: 8px;
  margin-bottom: 0;
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}

.form-actions {
  margin-bottom: 0;
}

.file-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-detail {
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.preview-tip {
  margin-top: 12px;
  margin-bottom: 0;
  font-size: 12px;
}

.analysis-overview {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.status-tag {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.status-compliant {
  background-color: rgba(82, 196, 26, 0.15);
  color: #52c41a;
}

.status-needs_review {
  background-color: rgba(250, 140, 22, 0.15);
  color: #fa8c16;
}

.status-non_compliant {
  background-color: rgba(245, 34, 45, 0.15);
  color: #f5222d;
}

.status-unknown {
  background-color: rgba(140, 140, 140, 0.15);
  color: #8c8c8c;
}

.analysis-detail {
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}

@media (max-width: 768px) {
  .guide-list {
    font-size: 12px;
  }
}

@media (min-width: 768px) {
  .analysis-overview {
    flex-direction: row;
    align-items: center;
  }
}
</style>
