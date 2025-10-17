<script lang="ts" setup>
import type { FormInstance, UploadFile, UploadProps } from 'ant-design-vue';
import type { Rule } from 'ant-design-vue/es/form';

import { computed, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

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
  config: null as File | null,
  notes: '',
});

const archiveFileList = ref<UploadFile[]>([]);
const configFileList = ref<UploadFile[]>([]);
const isSubmitting = ref(false);

const formRules: Record<string, Rule[]> = {
  config: [
    {
      message: '请上传 TOML 配置文件',
      required: true,
      trigger: 'change',
    },
  ],
  archive: [
    {
      message: '请上传完整项目压缩包',
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

const hasSelection = computed(
  () => configMeta.value !== null || archiveMeta.value !== null,
);

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

function handleReset() {
  formRef.value?.resetFields();
  archiveFileList.value = [];
  configFileList.value = [];
  formState.archive = null;
  formState.config = null;
  formState.notes = '';
}

async function handleSubmit() {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }

  if (!formState.config || !formState.archive) {
    return;
  }

  isSubmitting.value = true;
  await new Promise((resolve) => setTimeout(resolve, 300));
  isSubmitting.value = false;
  message.success('已保存上传文件，后端对接后即可启动静态分析。');
}
</script>

<template>
  <Page
    description="上传静态分析所需的配置文件与完整源码压缩包。待后端联调完成后，可直接在此页触发分析流程。"
    title="协议静态分析"
  >
    <div class="static-analysis">
      <Card title="流程说明">
        <div class="intro">
          <TypographyParagraph class="intro-text">
            该流程依赖协议配置与完整源码来评估实现与规范的一致性。配置文件采用
            TOML 格式，具体字段定义请参考论文。
          </TypographyParagraph>
          <ul class="guide-list">
            <li>先行准备分析配置（TOML），具体格式请参考论文。</li>
            <li>将待分析项目的完整源码打包为压缩文件，保留原始目录结构。</li>
            <li>可选地填写备注，说明协议版本、提交 SHA 或其他上下文。</li>
          </ul>
          <TypographyText class="placeholder-hint" type="secondary">
            当前页面仅保存上传记录，不会将文件发送至后端。
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
          <FormItem label="分析配置（.toml）" name="config" required>
            <Upload
              :before-upload="handleConfigBeforeUpload"
              :file-list="configFileList"
              :max-count="1"
              :on-remove="handleConfigRemove"
              accept=".toml,text/x-toml,application/toml,text/plain"
            >
              <Button block type="dashed">选择 TOML 配置文件</Button>
            </Upload>
            <p class="upload-helper">
              上传协议静态分析的配置文件。格式请参见论文附录，建议与仓库一并版本管理。
            </p>
          </FormItem>

          <FormItem label="源码压缩包" name="archive" required>
            <Upload
              :before-upload="handleArchiveBeforeUpload"
              :file-list="archiveFileList"
              :max-count="1"
              :on-remove="handleArchiveRemove"
              accept=".zip,.tar,.gz,.tgz,.bz2,.xz,.7z,application/zip,application/x-tar"
            >
              <Button block type="dashed">选择压缩包</Button>
            </Upload>
            <p class="upload-helper">
              压缩包需包含项目完整源码和构建脚本，保持目录结构用于后续离线解析。
            </p>
          </FormItem>

          <FormItem label="备注" name="notes">
            <Input.TextArea
              v-model:value="formState.notes"
              :auto-size="{ minRows: 3, maxRows: 6 }"
              placeholder="可选：说明协议版本、提交记录、运行前提等关键信息"
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
                保存上传
              </Button>
            </Space>
          </FormItem>
        </Form>
      </Card>

      <Card v-if="hasSelection" title="已选文件概览">
        <Descriptions bordered column="1" size="small">
          <Descriptions.Item v-if="configMeta" label="配置文件">
            <div class="file-meta">
              <TypographyText strong>{{ configMeta.name }}</TypographyText>
              <span class="file-detail">大小：{{ configMeta.size }}</span>
              <span class="file-detail">更新：{{ configMeta.updatedAt }}</span>
            </div>
          </Descriptions.Item>
          <Descriptions.Item v-if="archiveMeta" label="源码压缩包">
            <div class="file-meta">
              <TypographyText strong>{{ archiveMeta.name }}</TypographyText>
              <span class="file-detail">大小：{{ archiveMeta.size }}</span>
              <span class="file-detail">更新：{{ archiveMeta.updatedAt }}</span>
            </div>
          </Descriptions.Item>
          <Descriptions.Item label="备注">
            {{ formState.notes.trim() || '未填写' }}
          </Descriptions.Item>
        </Descriptions>
        <TypographyParagraph class="preview-tip" type="secondary">
          文本信息与文件均暂存于浏览器内存，后端联调后可直接复用当前输入。
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

@media (max-width: 768px) {
  .guide-list {
    font-size: 12px;
  }
}
</style>
