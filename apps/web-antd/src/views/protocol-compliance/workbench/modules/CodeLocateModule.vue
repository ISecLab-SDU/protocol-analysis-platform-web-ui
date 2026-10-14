<script setup lang="ts">
import { computed } from 'vue';

import { IconifyIcon } from '@vben/icons';

import { Button, Card, Tag, Upload } from 'ant-design-vue';

import StageCodeLocate from '../components/StageCodeLocate.vue';
import StageRuleConfirm from '../components/StageRuleConfirm.vue';
import { useAnalysisModules } from '../useAnalysisModules';

const {
  codeLocate,
  codeLocateInputs,
  resetCodeLocateOutput,
  runCodeLocate,
  stopCodeLocate,
} = useAnalysisModules();

const archiveFileList = computed(() =>
  codeLocateInputs.codeArchive
    ? [
        {
          name: codeLocateInputs.codeArchive.name,
          status: 'done' as const,
          uid: 'code-archive',
        },
      ]
    : [],
);

const rulesFileList = computed(() =>
  codeLocateInputs.rulesFile
    ? [
        {
          name: codeLocateInputs.rulesFile.name,
          status: 'done' as const,
          uid: 'rules-file',
        },
      ]
    : [],
);

function beforeUploadArchive(file: File) {
  resetCodeLocateOutput();
  codeLocateInputs.codeArchive = file;
  return false;
}

function beforeUploadRules(file: File) {
  resetCodeLocateOutput();
  codeLocateInputs.rulesFile = file;
  return false;
}

function removeArchive() {
  resetCodeLocateOutput();
  codeLocateInputs.codeArchive = null;
  return true;
}

function removeRules() {
  resetCodeLocateOutput();
  codeLocateInputs.rulesFile = null;
  return true;
}
</script>

<template>
  <div class="analysis-module">
    <header class="module-heading">
      <div>
        <h1>代码定位与一致性分析</h1>
        <p>上传源码包和规则文件，选择一条规则后单独运行分析。</p>
      </div>
      <div class="module-heading-actions">
        <Button
          v-if="codeLocate.status === 'running'"
          danger
          size="small"
          @click="stopCodeLocate"
        >
          <template #icon><IconifyIcon icon="mdi:stop" /></template>
          停止
        </Button>
        <Tag
          :color="codeLocate.status === 'running' ? 'processing' : 'default'"
        >
          {{
            codeLocate.status === 'running'
              ? '进行中'
              : codeLocate.status === 'done'
                ? '已完成'
                : codeLocate.status === 'stopped'
                  ? '已停止'
                  : codeLocate.status === 'error'
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
            :disabled="codeLocate.status === 'running'"
            :file-list="archiveFileList"
            @remove="removeArchive"
          >
            <Button :disabled="codeLocate.status === 'running'">
              <template #icon><IconifyIcon icon="mdi:upload" /></template>
              选择源码压缩包
            </Button>
          </Upload>
        </div>
        <div class="module-input-field">
          <div class="module-input-label">协议规则 JSON *</div>
          <Upload
            accept=".json,application/json"
            :before-upload="beforeUploadRules"
            :disabled="codeLocate.status === 'running'"
            :file-list="rulesFileList"
            @remove="removeRules"
          >
            <Button :disabled="codeLocate.status === 'running'">
              <template #icon><IconifyIcon icon="mdi:upload" /></template>
              选择规则文件
            </Button>
          </Upload>
        </div>
      </div>
      <p class="module-help">
        规则确认沿用规则提取和规则文件中的字段；此模块只提交已选中的规则。
      </p>
    </Card>

    <StageRuleConfirm
      v-if="codeLocateInputs.rulesFile"
      :disabled="codeLocate.status === 'running'"
      :rules-file="codeLocateInputs.rulesFile"
      :show-back="false"
      start-label="开始代码定位与一致性分析"
      title="确认分析规则"
      @start="runCodeLocate"
    />

    <div v-if="codeLocate.error" class="module-error" role="alert">
      <IconifyIcon icon="mdi:alert-circle-outline" />
      <span>{{ codeLocate.error }}</span>
    </div>

    <StageCodeLocate
      :evidence="codeLocate.evidence"
      :events="codeLocate.events"
      :log-html="codeLocate.logHtml"
      :log-text="codeLocate.logText"
      :result="codeLocate.result"
      :rule="codeLocate.rule"
      :running="codeLocate.status === 'running'"
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
}

.module-input-label {
  font-weight: 600;
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

@media (max-width: 760px) {
  .module-input-grid {
    grid-template-columns: 1fr;
  }
}
</style>
