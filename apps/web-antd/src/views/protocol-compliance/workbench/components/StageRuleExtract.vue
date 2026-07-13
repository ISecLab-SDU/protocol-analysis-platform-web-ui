<script setup lang="ts">
import type {
  ProtocolExtractRuleItem,
  RunProtocolExtractResponse,
} from '#/api/protocol-compliance';

import { computed, reactive, ref } from 'vue';

import { IconifyIcon } from '@vben/icons';

import {
  Button,
  Card,
  Checkbox,
  Empty,
  Input,
  message,
  Progress,
  Tag,
  Upload,
} from 'ant-design-vue';

import { runProtocolExtract } from '#/api/protocol-compliance';

interface Props {
  disabled?: boolean;
  protocolType: string;
  rulesFile?: File | null;
}

interface Emits {
  (e: 'applyRules', file: File): void;
  (e: 'goWorkbench'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const DEFAULT_LLM_BASE_URL = 'https://api.deepseek.com';

const form = reactive({
  apiKey: '',
  filterHeadings: true,
  htmlFile: null as File | null,
  llmBaseUrl: DEFAULT_LLM_BASE_URL,
  protocol: props.protocolType || 'MQTT',
  version: defaultProtocolVersion(props.protocolType),
});

const extracting = ref(false);
const errorMessage = ref('');
const extractResult = ref<null | RunProtocolExtractResponse>(null);

const uploadedHtmlFileList = computed(() =>
  form.htmlFile
    ? [{ name: form.htmlFile.name, status: 'done' as const, uid: 'html-doc' }]
    : [],
);

const extractedRules = computed(() => extractResult.value?.rules || []);
const previewRules = computed(() => extractedRules.value.slice(0, 5));
const hasResult = computed(() => Boolean(extractResult.value));

const resultFileName = computed(() => {
  const protocol = normalizeFileSegment(
    extractResult.value?.protocol || form.protocol,
    'protocol',
  );
  const version = normalizeFileSegment(
    extractResult.value?.version || form.version,
    'version',
  );
  return `${protocol}-${version}-rules.json`;
});

const resultJsonText = computed(() => {
  if (!extractResult.value) return '';
  return JSON.stringify(extractResult.value.rules, null, 2);
});

function defaultProtocolVersion(protocol: string) {
  if (protocol === 'MQTT') return '3.1.1';
  if (protocol === 'SNMP') return '2c';
  return '';
}

function normalizeFileSegment(value: string, fallback: string) {
  const normalized = value
    .trim()
    .replaceAll(/[^\w.-]+/g, '-')
    .replaceAll(/^-+|-+$/g, '');
  return normalized || fallback;
}

function beforeUpload(file: File) {
  const lowerName = file.name.toLowerCase();
  if (!lowerName.endsWith('.html') && !lowerName.endsWith('.htm')) {
    message.warning('请上传 HTML 格式的协议文档');
    return false;
  }

  form.htmlFile = file;
  clearResult();
  return false;
}

function removeHtmlFile() {
  form.htmlFile = null;
  clearResult();
  return true;
}

function clearResult() {
  extractResult.value = null;
  errorMessage.value = '';
}

function formatExtractErrorDetails(details: unknown) {
  if (typeof details === 'string') return details;
  if (details && typeof details === 'object') {
    const payload = details as {
      message?: unknown;
      stderr?: unknown;
      stdout?: unknown;
    };
    const messageText =
      typeof payload.message === 'string' ? payload.message : '';
    const stderrText = formatProcessOutput(payload.stderr);
    const stdoutText = formatProcessOutput(payload.stdout);
    return (
      [messageText, stderrText, stdoutText].filter(Boolean).join('\n') ||
      JSON.stringify(details)
    );
  }
  return '';
}

function formatProcessOutput(output: unknown) {
  if (Array.isArray(output)) {
    return output
      .map((line) => String(line || '').trim())
      .filter(Boolean)
      .slice(-8)
      .join('\n');
  }
  return typeof output === 'string' ? output.trim() : '';
}

function readErrorMessage(error: unknown) {
  if (!error || typeof error !== 'object') return '';
  const payload = error as {
    message?: unknown;
    response?: {
      data?: { details?: unknown; error?: unknown; message?: unknown };
    };
  };
  const data = payload.response?.data;
  const detail = formatExtractErrorDetails(data?.details);
  return (
    detail ||
    (typeof data?.error === 'string' ? data.error : '') ||
    (typeof data?.message === 'string' ? data.message : '') ||
    (typeof payload.message === 'string' ? payload.message : '')
  );
}

function validateForm() {
  if (!form.protocol.trim()) {
    message.warning('请填写协议名');
    return false;
  }
  if (!form.version.trim()) {
    message.warning('请填写版本名');
    return false;
  }
  if (!form.apiKey.trim()) {
    message.warning('请填写 API Key');
    return false;
  }
  if (!form.llmBaseUrl.trim()) {
    message.warning('请填写模型接口地址');
    return false;
  }
  if (!/^https?:\/\//i.test(form.llmBaseUrl.trim())) {
    message.warning('模型接口地址需要以 http:// 或 https:// 开头');
    return false;
  }
  if (!form.htmlFile) {
    message.warning('请上传 HTML 协议文档');
    return false;
  }
  return true;
}

async function handleExtract() {
  if (extracting.value || props.disabled) return;
  if (!validateForm() || !form.htmlFile) return;

  extracting.value = true;
  errorMessage.value = '';
  extractResult.value = null;

  try {
    const result = await runProtocolExtract({
      apiKey: form.apiKey.trim(),
      filterHeadings: form.filterHeadings,
      htmlFile: form.htmlFile,
      llmBaseUrl: form.llmBaseUrl.trim(),
      protocol: form.protocol.trim(),
      version: form.version.trim(),
    });
    extractResult.value = result;
    if (result.rules.length > 0) {
      message.success(`规则提取完成，共生成 ${result.rules.length} 条规则`);
    } else {
      message.warning('规则提取完成，但未解析到规则');
    }
  } catch (error) {
    errorMessage.value = readErrorMessage(error) || '规则提取失败';
  } finally {
    extracting.value = false;
  }
}

function downloadRulesJson() {
  if (!resultJsonText.value) return;
  const blob = new Blob([resultJsonText.value], {
    type: 'application/json;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = resultFileName.value;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function applyRulesToWorkbench() {
  if (!resultJsonText.value) return;
  const file = new File([resultJsonText.value], resultFileName.value, {
    type: 'application/json',
  });
  emit('applyRules', file);
}

function normalizeRuleField(value: unknown) {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item || '').trim())
      .filter(Boolean)
      .join(' / ');
  }
  if (typeof value === 'string') return value.trim();
  return '';
}

function ruleTypeText(rule: ProtocolExtractRuleItem) {
  const requestType = normalizeRuleField(rule.req_type);
  const responseType = normalizeRuleField(rule.res_type);
  return [requestType, responseType].filter(Boolean).join(' -> ') || '通用规则';
}
</script>

<template>
  <Card class="extract-card" :bordered="false">
    <template #title>
      <div class="extract-title">
        <IconifyIcon icon="mdi:file-document-edit-outline" />
        <span>规则提取</span>
      </div>
    </template>
    <template #extra>
      <Tag color="blue">HTML -> JSON</Tag>
    </template>

    <div class="extract-grid">
      <section class="extract-panel extract-panel--form">
        <header class="panel-head">
          <div>
            <h2>提取参数</h2>
            <p>协议文档、协议版本与模型访问参数</p>
          </div>
        </header>

        <div class="extract-form-grid">
          <label class="form-field">
            <span>协议名 *</span>
            <Input
              v-model:value="form.protocol"
              :disabled="extracting || disabled"
              placeholder="MQTT"
              @change="clearResult"
            />
          </label>

          <label class="form-field">
            <span>版本名 *</span>
            <Input
              v-model:value="form.version"
              :disabled="extracting || disabled"
              placeholder="3.1.1"
              @change="clearResult"
            />
          </label>

          <label class="form-field form-field--wide">
            <span>API Key *</span>
            <Input
              v-model:value="form.apiKey"
              :disabled="extracting || disabled"
              placeholder="sk-..."
              type="password"
            />
          </label>

          <label class="form-field form-field--wide">
            <span>模型接口地址 *</span>
            <Input
              v-model:value="form.llmBaseUrl"
              :disabled="extracting || disabled"
              placeholder="https://api.deepseek.com"
              @change="clearResult"
            />
          </label>

          <div class="form-field form-field--wide">
            <span>HTML 协议文档 *</span>
            <Upload
              :before-upload="beforeUpload"
              :disabled="extracting || disabled"
              :file-list="uploadedHtmlFileList"
              accept=".html,.htm,text/html"
              @remove="removeHtmlFile"
            >
              <Button :disabled="extracting || disabled">
                <template #icon>
                  <IconifyIcon icon="mdi:upload" />
                </template>
                选择 HTML 文件
              </Button>
            </Upload>
          </div>

          <div class="form-field form-field--wide form-field--inline">
            <Checkbox
              v-model:checked="form.filterHeadings"
              :disabled="extracting || disabled"
              @change="clearResult"
            >
              筛选目录标题
            </Checkbox>
          </div>
        </div>

        <footer class="extract-actions">
          <Button
            size="large"
            type="primary"
            :disabled="disabled"
            :loading="extracting"
            @click="handleExtract"
          >
            <template #icon>
              <IconifyIcon icon="mdi:play" />
            </template>
            开始提取
          </Button>
          <Button size="large" @click="emit('goWorkbench')">
            <template #icon>
              <IconifyIcon icon="mdi:briefcase-outline" />
            </template>
            返回工作台
          </Button>
        </footer>
      </section>

      <aside class="extract-panel extract-panel--status">
        <header class="panel-head">
          <div>
            <h2>协议规则输出</h2>
            <p>可下载并填入项目设置</p>
          </div>
          <Tag
            :color="
              hasResult ? 'success' : extracting ? 'processing' : 'default'
            "
          >
            {{ hasResult ? '已生成' : extracting ? '提取中' : '待生成' }}
          </Tag>
        </header>

        <Progress
          v-if="extracting || hasResult"
          :percent="extracting ? 68 : 100"
          :status="extracting ? 'active' : 'success'"
        />

        <div class="output-metrics">
          <div class="output-metric">
            <span>规则数量</span>
            <strong>{{ extractedRules.length }}</strong>
          </div>
          <div class="output-metric">
            <span>当前输入</span>
            <strong>{{ rulesFile?.name || '-' }}</strong>
          </div>
        </div>

        <section v-if="errorMessage" class="extract-error">
          <IconifyIcon icon="mdi:alert-circle-outline" />
          <span>{{ errorMessage }}</span>
        </section>

        <section v-if="hasResult" class="output-box">
          <div class="output-file">
            <IconifyIcon icon="mdi:file-code-outline" />
            <div>
              <strong>{{ resultFileName }}</strong>
              <span>{{
                extractResult?.storeDir || '结果已在浏览器中生成'
              }}</span>
            </div>
          </div>
          <div class="output-actions">
            <Button type="primary" @click="downloadRulesJson">
              <template #icon>
                <IconifyIcon icon="mdi:download" />
              </template>
              下载 JSON
            </Button>
            <Button @click="applyRulesToWorkbench">
              <template #icon>
                <IconifyIcon icon="mdi:import" />
              </template>
              填入项目设置
            </Button>
          </div>
        </section>

        <Empty
          v-else-if="!extracting && !errorMessage"
          description="暂无提取结果"
        />
      </aside>
    </div>

    <section v-if="hasResult" class="rule-preview">
      <header class="panel-head">
        <div>
          <h2>规则预览</h2>
          <p>展示前 {{ previewRules.length }} 条规则</p>
        </div>
      </header>

      <div class="rule-preview-list">
        <article
          v-for="(rule, index) in previewRules"
          :key="`${rule.rule}-${index}`"
          class="rule-preview-item"
        >
          <Tag color="blue">{{ rule.group || ruleTypeText(rule) }}</Tag>
          <p>{{ rule.rule }}</p>
        </article>
      </div>
    </section>
  </Card>
</template>

<style scoped>
.extract-card {
  min-height: 100%;
  background: transparent;
}

.extract-card :deep(.ant-card-body) {
  padding: 0;
}

.extract-title {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 22px;
  font-weight: 850;
  color: #101b36;
}

.extract-title :first-child {
  font-size: 26px;
  color: #1677ff;
}

.extract-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 18px;
}

.extract-panel,
.rule-preview {
  background: #fff;
  border: 1px solid #e7edf5;
  border-radius: 8px;
  box-shadow: 0 8px 22px rgb(15 23 42 / 4%);
}

.extract-panel {
  padding: 22px 24px;
}

.panel-head {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.panel-head h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: #172033;
  letter-spacing: 0;
}

.panel-head p {
  margin: 6px 0 0;
  font-size: 14px;
  color: #64748b;
}

.extract-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 24px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  margin: 0;
}

.form-field > span {
  font-size: 15px;
  font-weight: 700;
  color: #172033;
}

.form-field--wide {
  grid-column: 1 / -1;
}

.form-field--inline {
  flex-direction: row;
  align-items: center;
}

.extract-card :deep(.ant-input),
.extract-card :deep(.ant-btn) {
  border-radius: 6px;
}

.extract-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding-top: 22px;
  margin-top: 22px;
  border-top: 1px solid #e7edf5;
}

.extract-panel--status {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.output-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0;
}

.output-metric {
  min-width: 0;
  padding: 14px;
  background: #f7fbff;
  border: 1px solid #dcecff;
  border-radius: 8px;
}

.output-metric span {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: #64748b;
}

.output-metric strong {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 18px;
  font-weight: 850;
  color: #101b36;
  white-space: nowrap;
}

.extract-error {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px;
  margin-bottom: 16px;
  font-size: 14px;
  line-height: 1.7;
  color: #991b1b;
  background: #fff7f7;
  border: 1px solid #fecaca;
  border-radius: 8px;
}

.extract-error :first-child {
  flex: 0 0 auto;
  margin-top: 2px;
  font-size: 18px;
}

.output-box {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  background: #f8fbff;
  border: 1px solid #dbeafe;
  border-radius: 8px;
}

.output-file {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  min-width: 0;
}

.output-file > svg {
  flex: 0 0 auto;
  margin-top: 2px;
  font-size: 24px;
  color: #1677ff;
}

.output-file div {
  min-width: 0;
}

.output-file strong,
.output-file span {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.output-file strong {
  font-size: 15px;
  font-weight: 800;
  color: #172033;
}

.output-file span {
  margin-top: 4px;
  font-size: 13px;
  color: #64748b;
}

.output-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.rule-preview {
  padding: 22px 24px;
  margin-top: 18px;
}

.rule-preview-list {
  display: grid;
  gap: 12px;
}

.rule-preview-item {
  padding: 14px;
  background: #fbfdff;
  border: 1px solid #e7edf5;
  border-radius: 8px;
}

.rule-preview-item p {
  margin: 10px 0 0;
  font-size: 14px;
  line-height: 1.7;
  color: #334155;
}

@media (max-width: 1180px) {
  .extract-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .extract-panel,
  .rule-preview {
    padding: 16px;
  }

  .extract-form-grid,
  .output-metrics {
    grid-template-columns: 1fr;
  }

  .panel-head {
    flex-direction: column;
  }
}
</style>
