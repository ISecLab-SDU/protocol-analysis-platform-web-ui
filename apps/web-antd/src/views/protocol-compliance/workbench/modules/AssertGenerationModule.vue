<script setup lang="ts">
import { computed, ref } from 'vue';

import { IconifyIcon } from '@vben/icons';

import {
  Button,
  Card,
  Input,
  message,
  Select,
  Tag,
  Upload,
} from 'ant-design-vue';

import { downloadProtocolAssertionArtifact } from '#/api/protocol-compliance';

import StageAssertGen from '../components/StageAssertGen.vue';
import { useAnalysisModules } from '../useAnalysisModules';

const {
  assertGeneration,
  assertInputs,
  codeLocate,
  runAssertGeneration,
  stopAssertGeneration,
  useLatestCodeLocateOutput,
} = useAnalysisModules();

const downloading = ref(false);
async function downloadArtifact(artifact: 'instrumented-code' | 'tasks') {
  const jobId = assertGeneration.result?.jobId;
  if (!jobId) return;
  downloading.value = true;
  try {
    const blob = await downloadProtocolAssertionArtifact(jobId, artifact);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `assertion-${jobId}-${artifact}.zip`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch {
    message.error('产物下载失败，请重试');
  } finally {
    downloading.value = false;
  }
}

const archiveFileList = computed(() =>
  assertInputs.codeArchive
    ? [
        {
          name: assertInputs.codeArchive.name,
          status: 'done' as const,
          uid: 'code-archive',
        },
      ]
    : [],
);

const databaseFileList = computed(() =>
  assertInputs.databaseFile
    ? [
        {
          name: assertInputs.databaseFile.name,
          status: 'done' as const,
          uid: 'analysis-database',
        },
      ]
    : [],
);

const latestDatabasePath = computed(
  () => codeLocate.result?.artifacts?.database || '',
);

function beforeUploadArchive(file: File) {
  assertInputs.codeArchive = file;
  return false;
}

function beforeUploadDatabase(file: File) {
  assertInputs.databaseFile = file;
  assertInputs.databasePath = '';
  return false;
}

function removeArchive() {
  assertInputs.codeArchive = null;
  return true;
}

function removeDatabase() {
  assertInputs.databaseFile = null;
  return true;
}

function updateDatabasePath(value: string) {
  assertInputs.databasePath = value;
  if (value.trim()) assertInputs.databaseFile = null;
}

function selectLatestDatabase() {
  useLatestCodeLocateOutput();
}
</script>

<template>
  <div class="analysis-module">
    <header class="module-heading">
      <div>
        <h1>断言生成</h1>
        <p>使用源码包和已有的代码定位数据库，单独生成断言与插桩产物。</p>
      </div>
      <div class="module-heading-actions">
        <Button
          v-if="assertGeneration.status === 'running'"
          danger
          size="small"
          @click="stopAssertGeneration"
        >
          <template #icon><IconifyIcon icon="mdi:stop" /></template>
          停止
        </Button>
        <Tag
          :color="
            assertGeneration.status === 'running' ? 'processing' : 'default'
          "
        >
          {{
            assertGeneration.status === 'running'
              ? '进行中'
              : assertGeneration.status === 'done'
                ? '已完成'
                : assertGeneration.status === 'stopped'
                  ? '已停止'
                  : assertGeneration.status === 'error'
                    ? '异常'
                    : '待运行'
          }}
        </Tag>
      </div>
    </header>

    <Card class="module-card" title="输入">
      <div class="module-input-grid">
        <div class="module-input-field">
          <div class="module-input-label">源码压缩包 *</div>
          <Upload
            :before-upload="beforeUploadArchive"
            :disabled="assertGeneration.status === 'running'"
            :file-list="archiveFileList"
            @remove="removeArchive"
          >
            <Button :disabled="assertGeneration.status === 'running'">
              <template #icon><IconifyIcon icon="mdi:upload" /></template>
              选择源码压缩包
            </Button>
          </Upload>
        </div>

        <div class="module-input-field">
          <div class="module-input-label">代码定位结果数据库 *</div>
          <Upload
            accept=".db,.sqlite,.sqlite3,application/octet-stream"
            :before-upload="beforeUploadDatabase"
            :disabled="assertGeneration.status === 'running'"
            :file-list="databaseFileList"
            @remove="removeDatabase"
          >
            <Button :disabled="assertGeneration.status === 'running'">
              <template #icon><IconifyIcon icon="mdi:upload" /></template>
              上传数据库文件
            </Button>
          </Upload>
          <div class="database-path-row">
            <Input
              :value="assertInputs.databasePath"
              :disabled="assertGeneration.status === 'running'"
              placeholder="也可填入代码定位结果中的数据库路径"
              @update:value="updateDatabasePath"
            />
            <Button
              :disabled="
                !latestDatabasePath ||
                !codeLocate.inputArchive ||
                assertGeneration.status === 'running'
              "
              @click="selectLatestDatabase"
            >
              使用最近结果（数据库和源码）
            </Button>
          </div>
          <small v-if="latestDatabasePath" class="module-help">
            最近代码定位输出：{{ latestDatabasePath }}
          </small>
        </div>
      </div>
    </Card>

    <Card class="module-card" title="断言插桩运行时">
      <div class="module-input-grid">
        <div class="module-input-field">
          <div class="module-input-label">Agent</div>
          <Select
            v-model:value="assertInputs.agent"
            :disabled="assertGeneration.status === 'running'"
            :options="[{ label: 'Pi', value: 'pi' }]"
          />
        </div>
        <div class="module-input-field">
          <div class="module-input-label">提供商 API</div>
          <Select
            v-model:value="assertInputs.api"
            :disabled="assertGeneration.status === 'running'"
            :options="[
              { label: '使用服务端配置', value: '' },
              { label: 'OpenAI Chat Completions', value: 'openai-completions' },
              { label: 'OpenAI Responses', value: 'openai-responses' },
              { label: 'Anthropic Messages', value: 'anthropic-messages' },
            ]"
          />
        </div>
        <div class="module-input-field">
          <div class="module-input-label">模型</div>
          <Input
            v-model:value="assertInputs.model"
            :disabled="assertGeneration.status === 'running'"
            placeholder="留空使用服务端模型"
          />
        </div>
        <div class="module-input-field">
          <div class="module-input-label">API 端点</div>
          <Input
            v-model:value="assertInputs.baseUrl"
            :disabled="assertGeneration.status === 'running'"
            placeholder="留空使用服务端端点；支持 LLM 缓存地址"
          />
        </div>
        <div class="module-input-field">
          <div class="module-input-label">API Key</div>
          <Input.Password
            v-model:value="assertInputs.apiKey"
            :disabled="assertGeneration.status === 'running'"
            placeholder="留空使用服务端凭据"
            autocomplete="off"
          />
        </div>
      </div>
      <small class="module-help"
        >设置仅用于本次断言插桩任务。Claude 模型可通过 Pi 的 Anthropic Messages
        API 使用。</small
      >
    </Card>

    <div v-if="assertGeneration.error" class="module-error" role="alert">
      <IconifyIcon icon="mdi:alert-circle-outline" />
      <span>{{ assertGeneration.error }}</span>
    </div>

    <div class="module-actions">
      <Button
        type="primary"
        size="large"
        :loading="assertGeneration.status === 'running'"
        :disabled="assertGeneration.status === 'running'"
        @click="runAssertGeneration"
      >
        <template #icon><IconifyIcon icon="mdi:play" /></template>
        开始断言生成
      </Button>
      <Button
        v-if="assertGeneration.result?.artifacts?.zipPath"
        :loading="downloading"
        @click="downloadArtifact('tasks')"
      >
        下载断言任务
      </Button>
      <Button
        v-if="assertGeneration.result?.artifacts?.instrumentedCodeZipPath"
        :loading="downloading"
        @click="downloadArtifact('instrumented-code')"
      >
        下载插桩源码
      </Button>
      <span v-if="assertGeneration.result" class="output-reference">
        输出任务 ID：{{ assertGeneration.result.jobId }}
      </span>
    </div>

    <StageAssertGen
      :events="assertGeneration.job?.events"
      :log-text="assertGeneration.logText"
      :diff-content="assertGeneration.diffContent"
      :result="assertGeneration.result"
      :running="assertGeneration.status === 'running'"
    />
  </div>
</template>

<style scoped>
.analysis-module {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.module-heading {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
}

.module-heading h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}

.module-heading-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.module-heading p,
.module-help {
  margin: 6px 0 0;
  color: var(--ant-text-color-secondary);
}

.module-card {
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
}

.module-input-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.module-input-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.module-input-label {
  font-weight: 600;
}

.database-path-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.module-error {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 12px 16px;
  color: #b42318;
  background: #fef3f2;
  border: 1px solid #fecdca;
  border-radius: 8px;
}

.module-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.output-reference {
  color: var(--ant-text-color-secondary);
  overflow-wrap: anywhere;
}

@media (max-width: 760px) {
  .module-input-grid {
    grid-template-columns: 1fr;
  }

  .database-path-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
