<script lang="ts">
import type {
  HistoryRecord,
  ProtocolIRItem,
  VerificationResults,
} from '#/api/formal-gpt';

import { computed, onMounted, ref, watch } from 'vue';

import { message } from 'ant-design-vue';

import { fetchFormalGptHistory, uploadProtocolFile } from '#/api/formal-gpt';

const steps = [
  { name: '文档上传', key: 'upload' },
  { name: 'IR提取', key: 'ir' },
  { name: '时序图', key: 'sequence' },
  { name: '安全属性', key: 'properties' },
  { name: 'ProVerif', key: 'proverif' },
  { name: '历史记录', key: 'history' },
];

const securityProperties = [
  {
    id: 'confidentiality',
    name: '保密性',
    description: '确保协议中交换的信息不被未授权方获取',
    icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z',
  },
  {
    id: 'authentication',
    name: '认证性',
    description: '确保通信双方的身份是真实可信的',
    icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
  },
  {
    id: 'integrity',
    name: '完整性',
    description: '确保协议中传输的数据在传输过程中未被篡改',
    icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  {
    id: 'freshness',
    name: '新鲜性',
    description: '确保协议中使用的随机数和密钥是最新生成的',
    icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  {
    id: 'agreement',
    name: '一致性',
    description: '确保通信双方对协议执行结果达成一致',
    icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z',
  },
  {
    id: 'forward_secrecy',
    name: '前向保密',
    description: '确保即使长期密钥泄露，过去的会话密钥也不会泄露',
    icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z',
  },
];

export default {
  name: 'ProtocolVerification',
  setup() {
    const currentStep = ref<number>(0);
    const uploadedFile = ref<File | null | { name: string; size: number }>(
      null,
    );
    const selectedProperties = ref<string[]>([]);
    const isParsing = ref(false);
    const parsingProgress = ref(0);
    const currentFileId = ref<null | string>(null);
    const protocolIR = ref<ProtocolIRItem[]>([]);
    const proverifCode = ref('');
    const verificationResults = ref<null | VerificationResults>(null);
    const uploadHistory = ref<HistoryRecord[]>([]);
    const isVerifying = ref(false);
    const isLoadingHistory = ref(false);

    const stepPositions = computed(() => {
      const positions: Array<{ id: string; index: number; top: number }> = [];
      let currentY = 0;
      const minSpacing = 80; // 操作框之间的最小间距

      protocolIR.value.forEach((step, index) => {
        positions.push({
          id: step.id,
          top: currentY,
          index,
        });

        // 估算这个步骤需要的高度
        let estimatedHeight = 0;

        if (getOperationType(step.id) === 'message') {
          // 消息框基础高度 + 描述文字高度估算
          const descLength = step.desc ? step.desc.length : 0;
          estimatedHeight = 120 + Math.ceil(descLength / 50) * 20; // 每50个字符增加20px
        } else {
          // 计算/验证操作框
          const exprLength = step.expr ? step.expr.length : 0;
          const descLength = step.desc ? step.desc.length : 0;
          // 基础高度80px + 表达式长度 + 描述长度
          estimatedHeight =
            80 +
            Math.ceil(exprLength / 40) * 20 +
            Math.ceil(descLength / 50) * 15;
        }

        // 下一个步骤的起始位置 = 当前位置 + 估算高度 + 最小间距
        currentY += Math.max(estimatedHeight, 60) + minSpacing;
      });

      return positions;
    });

    // 添加一个计算总高度的属性
    const totalHeight = computed<number>(() => {
      if (stepPositions.value.length === 0) return 500;
      const lastPosition = stepPositions.value[stepPositions.value.length - 1]!;
      return lastPosition.top + 200; // 最后一个元素位置 + 额外空间
    });

    // 添加一个辅助函数来获取步骤的垂直位置
    const getStepPosition = (stepId: string) => {
      const position = stepPositions.value.find((p) => p.id === stepId);
      return position ? position.top : 0;
    };

    const participantNames = computed(() => {
      if (protocolIR.value.length === 0) {
        return { partyA: 'A', partyB: 'B' };
      }

      // 收集所有参与方
      const operators = new Set<string>();
      const senders = new Set<string>();
      const receivers = new Set<string>();

      protocolIR.value.forEach((step) => {
        if (step.operator) operators.add(step.operator);
        if (step.sender) senders.add(step.sender);
        if (step.receiver) receivers.add(step.receiver);
      });

      // 合并所有参与方
      const allParties = [...new Set([...operators, ...receivers, ...senders])];

      console.warn('🎭 检测到的参与方:', allParties);

      return {
        partyA: allParties[0] || 'A',
        partyB: allParties[1] || 'B',
      };
    });

    // ✅ 添加：判断是否是某方的操作
    const isPartyAOperation = (step: any) => {
      return step.operator === participantNames.value.partyA;
    };

    const isPartyBOperation = (step: any) => {
      return step.operator === participantNames.value.partyB;
    };

    const irStatistics = computed(() => {
      const total = protocolIR.value.length;
      const message = protocolIR.value.filter(
        (step) => getOperationType(step.id) === 'message',
      ).length;
      const calculate = protocolIR.value.filter(
        (step) => getOperationType(step.id) === 'calculate',
      ).length;
      const validate = protocolIR.value.filter(
        (step) => getOperationType(step.id) === 'validate',
      ).length;
      return [total, message, calculate, validate];
    });

    const handleFileUpload = async (e: Event) => {
      const target = e.target as HTMLInputElement | null;
      const file = target?.files?.[0];

      if (!file) {
        return;
      }

      // 重置所有状态
      resetAllStates();

      // 设置上传中状态
      isParsing.value = true;
      uploadedFile.value = file;

      try {
        console.warn('📤 准备上传文件:', file.name);

        // 调用上传 API
        const uploadResult = await uploadProtocolFile(file);

        console.warn('✅ 文件上传成功:', uploadResult);

        // 保存文件ID，用于后续处理
        currentFileId.value = uploadResult.fileId;

        // 更新上传的文件信息
        uploadedFile.value = {
          name: uploadResult.fileName,
          size: uploadResult.fileSize,
        };

        // 显示成功提示
        message.success(
          `文件上传成功：${uploadResult.fileName}（ID: ${uploadResult.fileId}）`,
        );

        // 可以选择自动跳转到下一步，或者让用户手动点击
        // nextStep();
      } catch (error) {
        console.error('❌ 文件上传失败:', error);
        const err = error as { message?: string };
        message.error(`文件上传失败: ${err?.message || '未知错误'}`);

        // 重置状态
        uploadedFile.value = null;
      } finally {
        isParsing.value = false;
      }
    };

    // ✅ 新增：从后端加载历史记录
    const loadHistoryFromBackend = async () => {
      console.warn('📡 开始加载历史记录...');
      isLoadingHistory.value = true;

      try {
        const data = await fetchFormalGptHistory();
        console.warn('✅ 历史记录加载成功:', data);
        uploadHistory.value = data;
      } catch (error) {
        console.error('❌ 加载历史记录失败:', error);
        uploadHistory.value = [];
      } finally {
        isLoadingHistory.value = false;
      }
    };

    // ✅ 修改：异步加载历史记录详情
    const loadHistoryRecord = async (record: HistoryRecord) => {
      console.warn('========================================');
      console.warn('📄 开始加载协议:', record.id);

      // 重置状态
      resetAllStates();

      // 设置当前选中的协议 ID
      currentFileId.value = record.id;

      // 设置文件信息
      uploadedFile.value = {
        name: record.fileName,
        size: record.fileSize,
      };

      // 设置 protocolIR
      protocolIR.value = record.protocolIR || [];

      // 设置 ProVerif 代码
      proverifCode.value = record.proverifCode || '';

      // 设置验证结果
      verificationResults.value = record.verificationResults;

      // ✅ 关键：根据加载的验证结果设置已选择的安全属性
      selectedProperties.value =
        record.verificationResults &&
        record.verificationResults.security_properties
          ? record.verificationResults.security_properties.map(
              (p) => p.property,
            )
          : record.selectedProperties || [];

      // 跳转到时序图页面（步骤 3，索引为 2），因为IR已经提取好了
      currentStep.value = 2;

      console.warn('📄 跳转到步骤:', currentStep.value);
      console.warn('========================================');
    };

    const resetAllStates = () => {
      protocolIR.value = [];
      selectedProperties.value = [];
      proverifCode.value = '';
      verificationResults.value = null;
      currentStep.value = 0;
      currentFileId.value = null;
    };

    const nextStep = () => {
      if (currentStep.value < 5) {
        currentStep.value = currentStep.value + 1;
      }
    };

    const navigateToStep = (index: number) => {
      if (index === 5 || index <= currentStep.value || uploadedFile.value) {
        currentStep.value = index;
      }
    };

    const getOperationType = (id: string) => {
      if (id.includes('message')) return 'message';
      if (id.includes('validate')) return 'validate';
      return 'calculate';
    };

    const formatFileSize = (bytes: number) => {
      if (bytes < 1024) return `${bytes} B`;
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    };

    const copyIR = () => {
      navigator.clipboard.writeText(JSON.stringify(protocolIR.value, null, 2));
      message.success('IR数据已复制到剪贴板');
    };

    const copyCode = () => {
      navigator.clipboard.writeText(proverifCode.value);
      message.success('ProVerif代码已复制到剪贴板');
    };

    const downloadCode = () => {
      const blob = new Blob([proverifCode.value], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'protocol_verification.pv';
      a.click();
      URL.revokeObjectURL(url);
    };

    const toggleProperty = (propertyId: string) => {
      selectedProperties.value = selectedProperties.value.includes(propertyId)
        ? selectedProperties.value.filter((id) => id !== propertyId)
        : [...selectedProperties.value, propertyId];
    };

    const removeProperty = (propertyId: string) => {
      selectedProperties.value = selectedProperties.value.filter(
        (id) => id !== propertyId,
      );
    };

    const getPropertyName = (propertyId: string) => {
      const property = securityProperties.find((p) => p.id === propertyId);
      return property ? property.name : '';
    };

    const generateProVerifCode = () => {
      // TODO: Implement real ProVerif code generation via backend API
      message.info(
        'ProVerif代码生成功能待实现。代码将由后端根据选择的属性生成。',
      );
      // For now, just move to the next step if properties are selected
      if (selectedProperties.value.length > 0) {
        currentStep.value = 4;
      }
    };

    const runVerification = () => {
      // TODO: Implement real verification run via backend API
      message.info('协议验证功能待实现。将向后端发送请求以运行验证。');
      isVerifying.value = true;
      setTimeout(() => {
        isVerifying.value = false;
        // After real verification, update verificationResults.value
      }, 2000);
    };

    // ✅ 监听步骤变化
    watch(currentStep, (newStep) => {
      console.warn('👀 步骤变化:', newStep);
      if (newStep === 5 && uploadHistory.value.length === 0) {
        // 只有在历史记录为空时才加载
        loadHistoryFromBackend();
      }
    });

    // ✅ 组件挂载时检查
    onMounted(() => {
      console.warn('🚀 组件已挂载');
      // 默认进入历史记录页面
      currentStep.value = 5;
    });

    return {
      steps,
      securityProperties,
      currentStep,
      uploadedFile,
      selectedProperties,
      isParsing,
      parsingProgress,
      currentFileId,
      protocolIR,
      proverifCode,
      verificationResults,
      uploadHistory,
      isVerifying,
      isLoadingHistory, // ✅ 新增
      irStatistics,
      handleFileUpload,
      loadHistoryRecord, // ✅ 已修改为异步
      loadHistoryFromBackend, // ✅ 新增
      nextStep,
      navigateToStep,
      getOperationType,
      formatFileSize,
      copyIR,
      copyCode,
      downloadCode,
      toggleProperty,
      removeProperty,
      getPropertyName,
      generateProVerifCode,
      runVerification,
      participantNames,
      isPartyAOperation,
      isPartyBOperation,
      stepPositions,
      getStepPosition,
      totalHeight,
    };
  },
};
</script>

<template>
  <div class="flex min-h-screen flex-col bg-gray-50">
    <!-- Header -->
    <header class="border-b border-gray-200 bg-white shadow-sm">
      <div class="px-8 py-6">
        <h1 class="mb-2 text-3xl font-semibold text-gray-900">
          Protocol Formal Verification System
        </h1>
        <p class="text-gray-600">基于中间表示的协议形式化验证平台</p>
      </div>
    </header>

    <!-- Top Navigation -->
    <nav class="overflow-x-auto border-b border-gray-200 bg-white px-4">
      <div class="flex">
        <div
          v-for="(step, index) in steps"
          :key="index"
          @click="navigateToStep(index)"
          class="flex cursor-pointer items-center whitespace-nowrap border-b-2 px-6 py-4 transition-all"
          :class="[
            currentStep === index
              ? 'border-blue-500 bg-blue-50 font-medium text-blue-600'
              : currentStep > index
                ? 'border-transparent text-green-600 hover:bg-gray-50'
                : 'border-transparent text-gray-500 hover:bg-gray-50',
          ]"
        >
          <span
            class="mr-3 flex h-7 w-7 items-center justify-center rounded-full text-sm font-semibold"
            :class="[
              currentStep === index
                ? 'bg-blue-500 text-white'
                : currentStep > index
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-200 text-gray-600',
            ]"
          >
            {{ index + 1 }}
          </span>
          <span>{{ step.name }}</span>
        </div>
      </div>
    </nav>

    <!-- Content Area -->
    <main class="flex-1 overflow-y-auto bg-white">
      <!-- Step 1: Upload -->
      <section v-if="currentStep === 0" class="p-8">
        <h2
          class="mb-6 border-b-2 border-blue-500 pb-3 text-2xl font-semibold text-gray-900"
        >
          文档上传
        </h2>
        <p class="mb-6 leading-relaxed text-gray-600">
          请上传RFC格式的协议规范文档。系统将自动解析文档内容，提取协议的关键信息和交互流程。
        </p>
        <div class="my-8">
          <input
            type="file"
            id="file-input"
            class="hidden"
            @change="handleFileUpload"
            accept=".pdf,.doc,.docx,.txt"
            :disabled="isParsing"
          />
          <label
            for="file-input"
            class="flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-16 transition-all"
            :class="[
              isParsing
                ? 'cursor-not-allowed border-gray-300 bg-gray-50 opacity-60'
                : 'cursor-pointer border-gray-300 bg-gray-50 hover:border-blue-500 hover:bg-blue-50',
            ]"
          >
            <svg
              class="mb-4 h-12 w-12 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <span class="mb-2 text-gray-600">
              {{
                isParsing
                  ? '正在解析文件，请稍候...'
                  : '点击选择文件或拖拽到此处'
              }}
            </span>
            <span class="text-sm text-gray-400"
              >支持 PDF, DOC, DOCX, TXT 格式</span
            >
          </label>
        </div>
        <div
          v-if="uploadedFile && !isParsing"
          class="rounded border-l-4 border-green-500 bg-green-50 p-5"
        >
          <p class="mb-2"><strong>已选择：</strong>{{ uploadedFile.name }}</p>
          <p><strong>大小：</strong>{{ formatFileSize(uploadedFile.size) }}</p>
        </div>
        <div v-if="isParsing" class="mt-6">
          <div class="h-2 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              class="h-full bg-blue-500 transition-all duration-300"
              :style="{ width: `${parsingProgress}%` }"
            ></div>
          </div>
          <p class="mt-2 text-center text-gray-600">
            正在解析文档... {{ Math.floor(parsingProgress) }}%
          </p>
        </div>
      </section>

      <!-- Step 2: IR Display -->
      <section v-if="currentStep === 1" class="p-8">
        <h2
          class="mb-6 border-b-2 border-blue-500 pb-3 text-2xl font-semibold text-gray-900"
        >
          中间表示 (Intermediate Representation)
        </h2>
        <p class="mb-6 leading-relaxed text-gray-600">
          以下是从协议文档中提取的中间表示语言(IR)。每个操作包含唯一标识符、操作者和详细描述。
        </p>

        <div class="my-8 grid grid-cols-4 gap-6">
          <div
            v-for="(label, idx) in [
              '总操作数',
              '消息传递',
              '计算操作',
              '验证操作',
            ]"
            :key="idx"
            class="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center"
          >
            <span class="mb-3 block text-sm font-medium text-gray-600">{{
              label
            }}</span>
            <span class="block text-4xl font-semibold text-blue-600">{{
              irStatistics[idx]
            }}</span>
          </div>
        </div>

        <div class="overflow-hidden rounded-lg border border-gray-200">
          <div
            class="flex items-center justify-between border-b border-gray-200 bg-gray-50 p-4"
          >
            <h3 class="font-semibold">IR 数据结构</h3>
            <button
              @click="copyIR"
              class="rounded border border-blue-600 px-4 py-2 text-blue-600 transition-colors hover:bg-blue-50"
            >
              复制JSON
            </button>
          </div>
          <pre
            class="max-h-96 overflow-auto bg-gray-50 p-6 font-mono text-sm text-gray-800"
          >
            {{ JSON.stringify(protocolIR, null, 2) }}
          </pre>
        </div>

        <button
          @click="nextStep"
          class="mt-6 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700"
        >
          继续：生成时序图
        </button>
      </section>

      <!-- Step 3: Improved Sequence Diagram -->
      <section v-if="currentStep === 2" class="p-8">
        <h2
          class="mb-6 border-b-2 border-blue-500 pb-3 text-2xl font-semibold text-gray-900"
        >
          协议时序图
        </h2>

        <p class="mb-6 leading-relaxed text-gray-600">
          可视化展示协议双方的交互过程，包括消息传递、计算和验证步骤。
        </p>

        <div
          class="mb-6 flex gap-8 rounded-lg border border-gray-200 bg-gray-50 p-5"
        >
          <div class="flex items-center gap-3">
            <span
              class="h-6 w-6 rounded border border-gray-300 bg-blue-500"
            ></span>
            <span class="text-sm">消息传递</span>
          </div>
          <div class="flex items-center gap-3">
            <span
              class="h-6 w-6 rounded border border-gray-300 bg-purple-500"
            ></span>
            <span class="text-sm">计算操作</span>
          </div>
          <div class="flex items-center gap-3">
            <span
              class="h-6 w-6 rounded border border-gray-300 bg-green-500"
            ></span>
            <span class="text-sm">验证操作</span>
          </div>
        </div>

        <div
          class="overflow-x-auto rounded-lg border border-gray-200 bg-white p-6"
        >
          <div class="flex min-w-[1400px] justify-between px-12">
            <!-- Party A Column -->
            <div class="flex w-2/5 flex-col items-center">
              <div
                class="mb-8 rounded-lg border-2 border-blue-600 bg-white px-8 py-3 font-semibold text-blue-600 shadow-sm"
              >
                {{ participantNames.partyA }}
              </div>
              <div
                class="relative flex w-full flex-col items-center"
                :style="{ height: `${totalHeight}px` }"
              >
                <!-- Timeline -->
                <div
                  class="absolute left-[50%] w-1 -translate-x-1/2 transform bg-gray-300"
                  :style="{ top: 0, height: '100%' }"
                ></div>

                <!-- Operation Boxes -->
                <div v-for="step in protocolIR" :key="step.id">
                  <!-- Timeline Dot -->
                  <div
                    v-if="
                      isPartyAOperation(step) &&
                      getOperationType(step.id) !== 'message'
                    "
                    class="absolute left-[50%] z-10 h-3 w-3 -translate-x-1/2 transform rounded-full border-2 border-white bg-blue-500 shadow-sm"
                    :style="{ top: `${getStepPosition(step.id)}px` }"
                  ></div>

                  <!-- Operation Box - A的操作框在时间线右侧 -->
                  <div
                    v-if="
                      isPartyAOperation(step) &&
                      getOperationType(step.id) !== 'message'
                    "
                    class="absolute rounded-lg border-l-4 px-5 py-4 text-sm shadow-sm"
                    :class="[
                      getOperationType(step.id) === 'calculate'
                        ? 'border-purple-500 bg-purple-50'
                        : 'border-green-500 bg-green-50',
                    ]"
                    :style="{
                      left: 'calc(50% + 40px)',
                      top: `${getStepPosition(step.id)}px`,
                      maxWidth: '320px',
                      width: 'auto',
                    }"
                  >
                    <div class="flex items-start gap-3">
                      <span
                        class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-xs font-semibold"
                        :class="[
                          getOperationType(step.id) === 'calculate'
                            ? 'bg-purple-500 text-white'
                            : 'bg-green-500 text-white',
                        ]"
                      >
                        {{
                          getOperationType(step.id) === 'calculate' ? 'C' : 'V'
                        }}
                      </span>
                      <div style="flex: 1; min-width: 0">
                        <strong
                          class="mb-1 block font-mono text-xs text-gray-700"
                          >{{ step.id }}</strong
                        >
                        <div
                          class="break-words leading-relaxed text-gray-700"
                          style="word-break: normal; overflow-wrap: anywhere"
                        >
                          <div
                            v-if="step.expr"
                            class="font-mono text-sm text-blue-600"
                            style="word-break: break-all"
                          >
                            {{ step.expr }}
                          </div>
                          <div
                            v-if="step.desc"
                            class="mt-1 text-xs text-gray-500"
                          >
                            {{ step.desc }}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Messages Column -->
            <div class="flex w-1/5 flex-col items-center">
              <div class="mb-8 h-20"></div>
              <div
                class="relative w-full"
                :style="{ height: `${totalHeight}px` }"
              >
                <div v-for="step in protocolIR" :key="step.id">
                  <div
                    v-if="getOperationType(step.id) === 'message'"
                    class="absolute flex w-full flex-col items-center"
                    :style="{ top: `${getStepPosition(step.id)}px` }"
                  >
                    <!-- Message Header with Description -->
                    <div
                      class="mb-6 w-full rounded-lg border-l-4 border-blue-500 bg-gradient-to-r from-blue-50 to-blue-100 px-5 py-4 text-sm shadow-md"
                    >
                      <div class="mb-3 flex items-center justify-between">
                        <span
                          class="font-mono text-xs font-semibold text-gray-700"
                          >{{ step.id }}</span
                        >
                        <span class="text-xs font-semibold text-blue-600">
                          {{ step.sender }} → {{ step.receiver }}
                        </span>
                      </div>
                      <div
                        class="break-words text-sm leading-relaxed text-gray-800"
                      >
                        <span class="font-semibold text-blue-700">{{
                          step.id
                        }}</span>
                        <span class="text-gray-600">（{{ step.desc }}）</span>
                      </div>
                    </div>

                    <!-- Arrow -->
                    <div
                      class="relative flex w-full items-center justify-center px-2"
                    >
                      <div class="relative flex h-8 w-full items-center">
                        <div
                          class="absolute h-1 w-full rounded-full"
                          :style="{
                            background:
                              step.sender === participantNames.partyA
                                ? 'linear-gradient(to right, #60a5fa, #93c5fd)'
                                : 'linear-gradient(to left, #60a5fa, #93c5fd)',
                          }"
                        ></div>

                        <div
                          class="absolute h-0 w-0 border-solid"
                          :class="[
                            step.sender === participantNames.partyA
                              ? 'right-0 border-b-[8px] border-l-[12px] border-t-[8px] border-b-transparent border-l-blue-400 border-t-transparent'
                              : 'left-0 border-b-[8px] border-r-[12px] border-t-[8px] border-b-transparent border-r-blue-400 border-t-transparent',
                          ]"
                          :style="
                            step.sender === participantNames.partyA
                              ? 'right: -1px;'
                              : 'left: -1px;'
                          "
                        ></div>

                        <div
                          class="absolute h-2 w-2 rounded-full bg-blue-500 shadow-sm"
                          :class="[
                            step.sender === participantNames.partyA
                              ? 'left-0'
                              : 'right-0',
                          ]"
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Party B Column -->
            <div class="flex w-2/5 flex-col items-center">
              <div
                class="mb-8 rounded-lg border-2 border-blue-600 bg-white px-8 py-3 font-semibold text-blue-600 shadow-sm"
              >
                {{ participantNames.partyB }}
              </div>
              <div
                class="relative flex w-full flex-col items-center"
                :style="{ height: `${totalHeight}px` }"
              >
                <!-- Timeline -->
                <div
                  class="absolute left-[50%] w-1 -translate-x-1/2 transform bg-gray-300"
                  :style="{ top: 0, height: '100%' }"
                ></div>

                <!-- Operation Boxes -->
                <div v-for="step in protocolIR" :key="step.id">
                  <!-- Timeline Dot -->
                  <div
                    v-if="
                      isPartyBOperation(step) &&
                      getOperationType(step.id) !== 'message'
                    "
                    class="absolute left-[50%] z-10 h-3 w-3 -translate-x-1/2 transform rounded-full border-2 border-white bg-blue-500 shadow-sm"
                    :style="{ top: `${getStepPosition(step.id)}px` }"
                  ></div>

                  <!-- Operation Box - B的操作框在时间线左侧 -->
                  <div
                    v-if="
                      isPartyBOperation(step) &&
                      getOperationType(step.id) !== 'message'
                    "
                    class="absolute rounded-lg border-l-4 px-5 py-4 text-sm shadow-sm"
                    :class="[
                      getOperationType(step.id) === 'calculate'
                        ? 'border-purple-500 bg-purple-50'
                        : 'border-green-500 bg-green-50',
                    ]"
                    :style="{
                      right: 'calc(50% + 40px)',
                      top: `${getStepPosition(step.id)}px`,
                      maxWidth: '320px',
                      width: 'auto',
                    }"
                  >
                    <div class="flex items-start gap-3">
                      <span
                        class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-xs font-semibold"
                        :class="[
                          getOperationType(step.id) === 'calculate'
                            ? 'bg-purple-500 text-white'
                            : 'bg-green-500 text-white',
                        ]"
                      >
                        {{
                          getOperationType(step.id) === 'calculate' ? 'C' : 'V'
                        }}
                      </span>
                      <div style="flex: 1; min-width: 0">
                        <strong
                          class="mb-1 block font-mono text-xs text-gray-700"
                          >{{ step.id }}</strong
                        >
                        <div
                          class="break-words leading-relaxed text-gray-700"
                          style="word-break: normal; overflow-wrap: anywhere"
                        >
                          <div
                            v-if="step.expr"
                            class="font-mono text-sm text-blue-600"
                            style="word-break: break-all"
                          >
                            {{ step.expr }}
                          </div>
                          <div
                            v-if="step.desc"
                            class="mt-1 text-xs text-gray-500"
                          >
                            {{ step.desc }}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Controls -->
        <div class="mt-8 flex items-center justify-between">
          <button
            @click="currentStep = 1"
            class="rounded-lg bg-gray-600 px-6 py-3 font-medium text-white shadow-md transition-colors hover:bg-gray-700 hover:shadow-lg"
          >
            返回：IR显示
          </button>
          <button
            @click="nextStep"
            class="rounded-lg bg-blue-600 px-6 py-3 font-medium text-white shadow-md transition-colors hover:bg-blue-700 hover:shadow-lg"
          >
            继续：选择安全属性
          </button>
        </div>
      </section>

      <!-- Step 4: Security Properties -->
      <section v-if="currentStep === 3" class="p-8">
        <h2
          class="mb-6 border-b-2 border-blue-500 pb-3 text-2xl font-semibold text-gray-900"
        >
          选择安全属性
        </h2>
        <p class="mb-6 leading-relaxed text-gray-600">
          请选择您希望验证的安全属性。系统将根据您的选择生成相应的ProVerif形式化模型。
        </p>

        <div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div
            v-for="property in securityProperties"
            :key="property.id"
            @click="toggleProperty(property.id)"
            class="cursor-pointer rounded-lg border-2 p-6 transition-all"
            :class="[
              selectedProperties.includes(property.id)
                ? '-translate-y-1 transform border-blue-500 bg-blue-50 shadow-md'
                : 'border-gray-200 bg-white hover:border-blue-500 hover:shadow',
            ]"
          >
            <div
              class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-gray-100"
            >
              <svg
                class="h-6 w-6 text-blue-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  :d="property.icon"
                />
              </svg>
            </div>
            <h3 class="mb-3 text-lg font-semibold text-gray-900">
              {{ property.name }}
            </h3>
            <p class="text-sm leading-relaxed text-gray-600">
              {{ property.description }}
            </p>
          </div>
        </div>

        <div
          v-if="selectedProperties.length > 0"
          class="mt-8 rounded-lg border border-gray-200 bg-gray-50 p-6"
        >
          <h3 class="mb-4 text-lg font-semibold">已选择的安全属性</h3>
          <div class="flex flex-wrap gap-3">
            <span
              v-for="propertyId in selectedProperties"
              :key="propertyId"
              class="flex items-center gap-2 rounded-full bg-blue-600 px-4 py-2 font-medium text-white"
            >
              {{ getPropertyName(propertyId) }}
              <button
                @click.stop="removeProperty(propertyId)"
                class="text-lg leading-none hover:text-gray-200"
              >
                ×
              </button>
            </span>
          </div>
        </div>

        <button
          @click="generateProVerifCode"
          :disabled="selectedProperties.length === 0"
          class="mt-6 rounded-lg px-6 py-3 font-medium transition-colors"
          :class="[
            selectedProperties.length === 0
              ? 'cursor-not-allowed bg-gray-400 text-white'
              : 'bg-blue-600 text-white hover:bg-blue-700',
          ]"
        >
          生成ProVerif代码
        </button>
      </section>

      <!-- Step 5: ProVerif Code with Verification -->
      <section v-if="currentStep === 4" class="p-8">
        <h2
          class="mb-6 border-b-2 border-blue-500 pb-3 text-2xl font-semibold text-gray-900"
        >
          ProVerif 形式化模型与验证
        </h2>
        <p class="mb-6 leading-relaxed text-gray-600">
          基于中间表示和您选择的安全属性自动生成的ProVerif形式化验证代码。
        </p>

        <!-- ProVerif Code -->
        <div class="mb-8 overflow-hidden rounded-lg border border-gray-200">
          <div
            class="flex items-center justify-between border-b border-gray-200 bg-gray-50 p-4"
          >
            <h3 class="font-semibold">ProVerif 代码</h3>
            <div class="flex gap-2">
              <button
                @click="copyCode"
                class="rounded border border-blue-600 px-4 py-2 text-blue-600 transition-colors hover:bg-blue-50"
              >
                复制代码
              </button>
              <button
                @click="downloadCode"
                class="rounded border border-blue-600 px-4 py-2 text-blue-600 transition-colors hover:bg-blue-50"
              >
                下载代码
              </button>
            </div>
          </div>
          <pre
            class="max-h-96 overflow-auto bg-gray-50 p-6 font-mono text-sm text-blue-600"
          >
            {{ proverifCode }}
          </pre>
        </div>

        <!-- Verification Section -->
        <div class="rounded-lg border border-gray-200 bg-gray-50 p-6">
          <div class="mb-6 flex items-center justify-between">
            <h3 class="text-xl font-semibold">验证结果</h3>
            <button
              @click="runVerification"
              :disabled="isVerifying"
              class="rounded-lg px-6 py-3 font-medium transition-colors"
              :class="[
                isVerifying
                  ? 'cursor-not-allowed bg-gray-400 text-white'
                  : 'bg-blue-600 text-white hover:bg-blue-700',
              ]"
            >
              {{
                isVerifying
                  ? '验证中...'
                  : verificationResults
                    ? '重新验证'
                    : '运行验证'
              }}
            </button>
          </div>

          <div v-if="verificationResults">
            <div
              class="mb-6 rounded border-l-4 p-4"
              :class="[
                verificationResults.security_properties.every((p) => p.result)
                  ? 'border-green-500 bg-green-50 text-green-900'
                  : 'border-yellow-500 bg-yellow-50 text-yellow-900',
              ]"
            >
              <strong>协议: </strong> {{ verificationResults.protocol }}
              <span class="ml-5 text-sm">
                <strong>状态: </strong>
                {{
                  verificationResults.security_properties.every((p) => p.result)
                    ? '✓ 全部通过'
                    : '⚠ 部分通过'
                }}
              </span>
            </div>

            <div class="space-y-4">
              <div
                v-for="prop in verificationResults.security_properties"
                :key="prop.property"
                class="rounded-lg border border-gray-200 bg-white p-4"
              >
                <div class="mb-2 flex items-center justify-between">
                  <span class="text-lg font-semibold capitalize">{{
                    prop.property
                  }}</span>
                  <span
                    class="rounded-full px-3 py-1 text-sm font-semibold"
                    :class="[
                      prop.result
                        ? 'bg-green-500 text-white'
                        : 'bg-red-500 text-white',
                    ]"
                  >
                    {{ prop.result ? 'VERIFIED' : 'FAILED' }}
                  </span>
                </div>
                <div class="font-mono text-sm text-gray-600">
                  {{ prop.query }}
                </div>
              </div>
            </div>
          </div>
          <div v-else class="py-12 text-center text-gray-500">
            <p>没有可用的验证结果</p>
          </div>
        </div>
      </section>

      <!-- Step 6: History Records -->
      <section v-if="currentStep === 5" class="p-8">
        <h2
          class="mb-6 border-b-2 border-blue-500 pb-3 text-2xl font-semibold text-gray-900"
        >
          历史记录
        </h2>
        <p class="mb-6 leading-relaxed text-gray-600">
          查看所有历史验证记录，点击任意记录可查看详细信息。
        </p>

        <!-- ✅ 新增：加载状态 -->
        <div
          v-if="isLoadingHistory"
          class="flex items-center justify-center py-12"
        >
          <div
            class="h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600"
          ></div>
          <span class="ml-4 text-gray-600">正在加载历史记录...</span>
        </div>

        <!-- ✅ 新增：空状态 -->
        <div v-else-if="uploadHistory.length === 0" class="py-12 text-center">
          <svg
            class="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p class="mt-4 text-gray-600">暂无历史记录</p>
        </div>

        <!-- ✅ 历史记录列表 -->
        <div v-else class="space-y-4">
          <div
            v-for="record in uploadHistory"
            :key="record.id"
            @click="loadHistoryRecord(record)"
            class="flex cursor-pointer items-start justify-between rounded-lg border-2 p-5 transition-all"
            :class="[
              currentFileId === record.id
                ? 'border-blue-500 bg-blue-50 shadow-md'
                : 'border-gray-200 bg-white hover:border-blue-500 hover:shadow',
            ]"
          >
            <div class="flex-1">
              <div class="mb-2 flex items-center">
                <svg
                  class="mr-2 h-5 w-5 text-gray-600"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4z"
                  />
                </svg>
                <span class="text-lg font-semibold text-gray-900">
                  {{ record.fileName }}
                </span>
              </div>
              <div class="mb-3 flex gap-6 text-sm text-gray-600">
                <span>{{ formatFileSize(record.fileSize) }}</span>
                <span>{{ record.uploadTime }}</span>
                <span class="text-blue-600">ID: {{ record.id }}</span>
              </div>

              <!-- ✅ 显示数据状态 -->
              <div class="flex gap-4 text-sm">
                <span
                  v-if="record.protocolIR && record.protocolIR.length > 0"
                  class="rounded bg-green-100 px-2 py-1 text-green-800"
                >
                  ✓ IR数据 ({{ record.protocolIR.length }} 条)
                </span>
                <span
                  v-else
                  class="rounded bg-gray-100 px-2 py-1 text-gray-600"
                >
                  - 无IR数据
                </span>

                <span
                  v-if="record.sequenceData"
                  class="rounded bg-green-100 px-2 py-1 text-green-800"
                >
                  ✓ 时序图
                </span>
                <span
                  v-else
                  class="rounded bg-gray-100 px-2 py-1 text-gray-600"
                >
                  - 无时序图
                </span>

                <span class="rounded bg-gray-100 px-2 py-1 text-gray-600">
                  形式化模型（待开发）
                </span>

                <span
                  v-if="record.verificationResults"
                  class="rounded bg-green-100 px-2 py-1 text-green-800"
                >
                  ✓ 验证结果
                </span>
                <span
                  v-else
                  class="rounded bg-gray-100 px-2 py-1 text-gray-600"
                >
                  - 无验证结果
                </span>
              </div>

              <!-- ✅ 显示验证结果（如果有） -->
              <div
                v-if="
                  record.verificationResults &&
                  record.verificationResults.security_properties
                "
                class="mt-3 space-y-2"
              >
                <div
                  v-for="prop in record.verificationResults.security_properties"
                  :key="prop.property"
                  class="flex items-center gap-2"
                >
                  <span
                    class="rounded px-2 py-1 text-xs font-medium"
                    :class="[
                      prop.result
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800',
                    ]"
                  >
                    {{ prop.result ? '✓' : '✗' }}
                  </span>
                  <span class="text-sm capitalize text-gray-700">{{
                    prop.property
                  }}</span>
                  <span class="text-xs text-gray-500">- {{ prop.query }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
/* 如果需要额外的样式可以在这里添加 */
</style>
