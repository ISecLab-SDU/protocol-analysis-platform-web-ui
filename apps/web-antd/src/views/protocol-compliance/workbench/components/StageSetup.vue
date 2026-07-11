<script setup lang="ts">
import { computed } from 'vue';

import { Button, Card, Input, InputNumber, Select, SelectOption, Textarea, Upload } from 'ant-design-vue';
import { IconifyIcon } from '@vben/icons';

import type { ProjectConfig } from '../types';
import {
  buildDefaultFuzzScript,
  DEFAULT_TARGET,
  PROTOCOL_IMPLEMENTATIONS,
} from '../types';

interface Props {
  config: ProjectConfig;
  disabled?: boolean;
}

interface Emits {
  (e: 'commit'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const implementationOptions = computed(() => PROTOCOL_IMPLEMENTATIONS[props.config.protocolType]);

function onProtocolChange(val: unknown) {
  if (val !== 'MQTT' && val !== 'SNMP') return;
  props.config.protocolType = val;
  props.config.protocolVersion = val === 'MQTT' ? '3.1.1' : 'v2c/v3';
  props.config.implementation = PROTOCOL_IMPLEMENTATIONS[val][0]!;
  props.config.targetHost = DEFAULT_TARGET[val].host;
  props.config.targetPort = DEFAULT_TARGET[val].port;
  props.config.fuzzScript = buildDefaultFuzzScript(
    props.config.protocolType,
    props.config.implementation,
    props.config.targetHost,
    props.config.targetPort,
  );
}

function onImplementationChange(val: unknown) {
  if (
    typeof val !== 'string' ||
    !PROTOCOL_IMPLEMENTATIONS[props.config.protocolType].includes(
      val as ProjectConfig['implementation'],
    )
  ) {
    return;
  }
  const implementation = val as ProjectConfig['implementation'];
  props.config.implementation = implementation;
  props.config.fuzzScript = buildDefaultFuzzScript(
    props.config.protocolType,
    implementation,
    props.config.targetHost,
    props.config.targetPort,
  );
}

function beforeUpload(
  file: File,
  field: 'archive' | 'rules',
) {
  props.config[field] = file;
  return false;
}

function removeFile(field: 'archive' | 'rules') {
  props.config[field] = null;
}

const canCommit = computed(() => {
  return Boolean(
    props.config.archive &&
    props.config.rules &&
    props.config.buildInstructions.trim()
  );
});
</script>

<template>
  <Card class="stage-card" title="项目设置">
    <div class="setup-grid">
      <div class="setup-section">
        <div class="setup-label">源码压缩包 *</div>
        <Upload
          :file-list="config.archive ? [{ uid: '-1', name: config.archive.name, status: 'done' }] : []"
          :before-upload="(file) => beforeUpload(file, 'archive')"
          :disabled="disabled"
          @remove="() => removeFile('archive')"
        >
          <Button :disabled="disabled">
            <template #icon><IconifyIcon icon="mdi:upload" /></template>
            选择文件
          </Button>
        </Upload>
      </div>

      <div class="setup-section">
        <div class="setup-label">协议规则 JSON *</div>
        <Upload
          :file-list="
            config.rules
              ? [{ uid: '-4', name: config.rules.name, status: 'done' }]
              : []
          "
          :before-upload="(file) => beforeUpload(file, 'rules')"
          :disabled="disabled"
          accept=".json,application/json"
          @remove="() => removeFile('rules')"
        >
          <Button :disabled="disabled">
            <template #icon><IconifyIcon icon="mdi:upload" /></template>
            选择文件
          </Button>
        </Upload>
      </div>

      <div class="setup-section">
        <div class="setup-label">编译命令 *</div>
        <Input
          v-model:value="config.buildInstructions"
          placeholder="例如: make all"
          :disabled="disabled"
        />
      </div>

      <div class="setup-section">
        <div class="setup-label">协议类型</div>
        <Select
          :value="config.protocolType"
          :disabled="disabled"
          @change="onProtocolChange"
        >
          <SelectOption value="MQTT">MQTT</SelectOption>
          <SelectOption value="SNMP">SNMP</SelectOption>
        </Select>
      </div>

      <div class="setup-section">
        <div class="setup-label">协议版本</div>
        <Input
          v-model:value="config.protocolVersion"
          placeholder="3.1.1"
          :disabled="disabled"
        />
      </div>

      <div class="setup-section">
        <div class="setup-label">实现</div>
        <Select
          :value="config.implementation"
          :disabled="disabled"
          @change="onImplementationChange"
        >
          <SelectOption
            v-for="impl in implementationOptions"
            :key="impl"
            :value="impl"
          >
            {{ impl }}
          </SelectOption>
        </Select>
      </div>

      <div class="setup-section">
        <div class="setup-label">目标主机</div>
        <Input
          v-model:value="config.targetHost"
          placeholder="localhost"
          :disabled="disabled"
        />
      </div>

      <div class="setup-section">
        <div class="setup-label">目标端口</div>
        <InputNumber
          v-model:value="config.targetPort"
          :min="1"
          :max="65535"
          :disabled="disabled"
          style="width: 100%"
        />
      </div>

      <div class="setup-section setup-section--full">
        <div class="setup-label">Fuzz 脚本</div>
        <Textarea
          v-model:value="config.fuzzScript"
          :rows="4"
          placeholder="默认 Fuzz 脚本内容"
          :disabled="disabled"
        />
      </div>
    </div>

    <div class="setup-actions">
      <Button
        type="primary"
        size="large"
        :disabled="!canCommit || disabled"
        @click="emit('commit')"
      >
        <template #icon><IconifyIcon icon="mdi:check" /></template>
        保存配置并进入规则确认
      </Button>
    </div>
  </Card>
</template>

<style scoped>
.stage-card {
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
  box-shadow: 0 10px 26px rgb(15 23 42 / 4%);
}

.setup-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px 24px;
}

.setup-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setup-section--full {
  grid-column: 1 / -1;
}

.setup-label {
  font-size: 15px;
  font-weight: 600;
  color: var(--ant-text-color);
}

.stage-card :deep(.ant-card-head-title) {
  font-size: 18px;
}

.stage-card :deep(.ant-btn),
.stage-card :deep(.ant-input),
.stage-card :deep(.ant-input-number-input),
.stage-card :deep(.ant-select-selector),
.stage-card :deep(.ant-upload-list-item-name),
.stage-card :deep(textarea.ant-input) {
  font-size: 14px;
}

.setup-actions {
  padding-top: 24px;
  margin-top: 24px;
  border-top: 1px solid var(--ant-color-border-secondary);
}
</style>
