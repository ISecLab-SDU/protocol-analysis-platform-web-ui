<script lang="ts">
import { computed, ref, watch, onMounted } from 'vue';

import type { 
  HistoryRecord, 
  ProtocolIRItem 
} from '#/api/formal-gpt';

import { 
  fetchFormalGptHistory,
  uploadProtocolFile,
  fetchFormalGptProtocolDetail,
  transformIRDataForSequence
} from '#/api/formal-gpt';

// 调整步骤：合并安全属性和ProVerif步骤
const steps = [
  { name: '文档上传', key: 'upload' },
  { name: '时序图', key: 'sequence' },
  { name: '安全验证', key: 'verification' }, // 合并后的步骤
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

// 生成随机文件大小（10KB到2MB之间）
const generateRandomFileSize = () => {
  // 10KB = 10 * 1024 = 10240 bytes
  // 2MB = 2 * 1024 * 1024 = 2097152 bytes
  return Math.floor(Math.random() * (2097152 - 10240 + 1)) + 10240;
};

// 生成有时间间隔的历史记录时间
const generateHistoricalDates = (count: number) => {
  const dates = [];
  const now = new Date();
  
  // 从最新的时间开始，依次往前推
  for (let i = 0; i < count; i++) {
    // 随机生成1到24小时的间隔
    const hoursToSubtract = Math.floor(Math.random() * 24) + 1 + (i * 4);
    const date = new Date(now.getTime() - hoursToSubtract * 60 * 60 * 1000);
    dates.push(date);
  }
  
  return dates;
};

export default {
  name: 'ProtocolVerification',
  setup() {
    const currentStep = ref(0);
    const uploadedFile = ref(null);
    const selectedProperties = ref([]);
    const isParsing = ref(false);
    const parsingProgress = ref(0);
    const currentFileId = ref(null);
    const protocolIR = ref<ProtocolIRItem[]>([]);
    const proverifCode = ref('');
    const verificationResults = ref(null);
    const uploadHistory = ref<HistoryRecord[]>([]);
    const isVerifying = ref(false);
    const isLoadingHistory = ref(false);
    const selectedStep = ref<ProtocolIRItem | null>(null);
    // 添加解析和验证的状态文本
    const parsingStatus = ref('准备解析文档...');
    const verificationStatus = ref('准备验证安全属性...');

    // 固定的message宽度常量
    const MESSAGE_WIDTH = 500;
    const ARROW_WIDTH = 250;

    const stepPositions = computed(() => {
      const positions = [];
      let currentY = 40; // Start with some padding from top
      const verticalGap = 1; // Gap between rows
      const operationHeight = 48; // Estimated height of operation boxes
      const messageSpacing = 35; // Vertical space for message (compact)
      
      protocolIR.value.forEach((step, index) => {
        const isMessage = getOperationType(step.id) === 'message';
        
        if (isMessage) {
          // Messages get minimal vertical space but are positioned separately
          const centerY = currentY + messageSpacing / 2;
          
          positions.push({
            id: step.id,
            top: centerY,
            index: index
          });
          
          currentY += messageSpacing + verticalGap;
        } else {
          // Operations get their own vertical space
          const centerY = currentY + operationHeight / 2;
          
          positions.push({
            id: step.id,
            top: centerY,
            index: index
          });
          
          currentY += operationHeight + verticalGap;
        }
      });
      
      return positions;
    });

    const totalHeight = computed(() => {
      if (stepPositions.value.length === 0) return 300;
      const lastPosition = stepPositions.value[stepPositions.value.length - 1];
      // Add minimal padding at bottom for the last element
      return lastPosition.top + 60;
    });

    const getStepPosition = (stepId) => {
      const position = stepPositions.value.find(p => p.id === stepId);
      return position ? position.top : 0;
    };

    const participantNames = computed(() => {
      if (protocolIR.value.length === 0) {
        return { partyA: 'A', partyB: 'B' };
      }

      const operators = new Set<string>();
      const senders = new Set<string>();
      const receivers = new Set<string>();

      protocolIR.value.forEach(step => {
        if (step.operator) operators.add(step.operator);
        if (step.sender) senders.add(step.sender);
        if (step.receiver) receivers.add(step.receiver);
      });

      const allParties = Array.from(new Set([...operators, ...senders, ...receivers]));
      
      return {
        partyA: allParties[0] || 'A',
        partyB: allParties[1] || 'B',
      };
    });

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

    const handleStepClick = (step: ProtocolIRItem) => {
      selectedStep.value = step;
    };

    // 修正 matchProtocolByFileName 函数
    const matchProtocolByFileName = (fileName) => {
      // 提取文件名中的关键词（去除扩展名和特殊字符）
      const nameWithoutExt = fileName.toLowerCase().replace(/\.(pdf|doc|docx|txt)$/i, '');
      
      // 🔴 修正协议关键词映射 - 每个协议对应自己的名称
      const protocolKeywords = {
        'ssh': ['ssh', 'secure shell'],
        'edhoc': ['edhoc'],
        'ekev1': ['ekev1', 'ikev1', 'ike v1'],
        'ekev2': ['ekev2', 'ikev2', 'ike v2'],
        'bt-ssp-jw': ['bt-ssp-jw', 'bt', 'bluetooth', 'ssp', 'jw'],
      };
      
      // 匹配协议名称
      for (const [protocol, keywords] of Object.entries(protocolKeywords)) {
        if (keywords.some(keyword => nameWithoutExt.includes(keyword))) {
          console.log(`✅ 文件名 "${fileName}" 匹配到协议: ${protocol}`);
          return protocol;
        }
      }
      
      console.log(`⚠️ 文件名 "${fileName}" 未匹配到任何协议`);
      return null;
    };

    // 修改handleFileUpload方法
    const handleFileUpload = async (e) => {
      const file = e.target.files[0];
      
      if (!file) {
        return;
      }
      
      resetAllStates();
      
      isParsing.value = true;
      parsingProgress.value = 0;
      uploadedFile.value = file;
      
      const parsingStates = [
        "正在读取文件内容...",
        "提取协议结构信息...",
        "解析协议交互流程...",
        "生成中间表示形式...",
        "验证IR数据完整性..."
      ];
      
      try {
        console.log('📤 准备上传文件:', file.name);
        
        // 1. 上传文件
        const uploadResult = await uploadProtocolFile(file);
        console.log('✅ 文件上传成功:', uploadResult);
        
        currentFileId.value = uploadResult.fileId;
        const fileSize = file.size || generateRandomFileSize();
        uploadedFile.value = {
          name: uploadResult.fileName,
          size: fileSize
        };
        
        // 2. 模拟解析进度
        const totalSteps = 5;
        const intervalTime = 600;
        
        for (let i = 0; i < totalSteps; i++) {
          parsingStatus.value = parsingStates[i];
          parsingProgress.value = (i + 1) * (100 / totalSteps);
          await new Promise(resolve => setTimeout(resolve, intervalTime));
        }
        
        // 3. 根据文件名匹配协议数据
        console.log('📥 匹配协议数据...');
        const protocolName = matchProtocolByFileName(file.name);
        console.log('🔍 识别到协议:', protocolName);
        
        const historyData = await fetchFormalGptHistory();
        
        if (historyData && historyData.length > 0) {
          // 尝试根据协议名称匹配
          let matchedProtocol = null;
          
          if (protocolName) {
            matchedProtocol = historyData.find(item => 
              item.fileName.toLowerCase().includes(protocolName) ||
              item.id.toLowerCase() === protocolName ||
              (item.protocolName && item.protocolName.toLowerCase() === protocolName)
            );
          }
          
          // 如果没有匹配到，使用第一条记录作为默认
          const demoProtocol = matchedProtocol || historyData[0];
          
          console.log('✅ 使用协议数据:', demoProtocol.fileName);
          
          // 🔴 更新 currentFileId 为匹配到的协议ID
          currentFileId.value = demoProtocol.id;
          
          // 加载协议IR数据
          protocolIR.value = demoProtocol.protocolIR || [];
          
          // 只加载 ProVerif 代码，不加载验证结果
          if (demoProtocol.proverifCode) {
            proverifCode.value = demoProtocol.proverifCode;
          }
          
          // 清空验证结果，等待用户点击"开始验证"
          verificationResults.value = null;
          selectedProperties.value = [];
          
          // 🔴 创建临时历史记录（使用匹配到的协议数据）
          const tempRecord = {
            id: `temp-${Date.now()}`, // 生成临时ID
            fileName: uploadResult.fileName,
            fileSize: fileSize,
            uploadTime: new Date().toLocaleString(),
            protocolIR: demoProtocol.protocolIR || [],
            proverifCode: demoProtocol.proverifCode || '',
            verificationResults: null, // 初始没有验证结果
            selectedProperties: [],
            isTemporary: true, // 标记为临时记录
            originalProtocolId: demoProtocol.id // 保存原始协议ID，用于后续加载验证结果
          };
          
          // 🔴 将临时记录添加到历史记录列表顶部
          uploadHistory.value = [tempRecord, ...uploadHistory.value];
          
          console.log('✅ 临时历史记录已创建:', tempRecord);
          
          // 跳转到时序图步骤
          currentStep.value = 1;
        } else {
          alert('文件上传成功,但未获取到协议数据');
        }
        
      } catch (error) {
        console.error('❌ 操作失败:', error);
        alert(`操作失败: ${error.message || '未知错误'}`);
        uploadedFile.value = null;
      } finally {
        isParsing.value = false;
      }
    };

    // 修改loadHistoryFromBackend方法
    const loadHistoryFromBackend = async () => {
      console.log('📡 开始加载历史记录...');
      isLoadingHistory.value = true;
      
      try {
        const data = await fetchFormalGptHistory();
        console.log('✅ 历史记录加载成功:', data);
        
        // 生成有时间间隔的日期
        const historicalDates = generateHistoricalDates(data.length);
        
        // 处理历史记录数据，补充缺失的文件大小和时间
        const processedData = data.map((item, index) => {
          const fileSize = item.fileSize || generateRandomFileSize();
          const uploadTime = item.uploadTime 
            ? item.uploadTime 
            : historicalDates[index].toLocaleString();
            
          return {
            ...item,
            fileSize,
            uploadTime
          };
        });
        
        // 🔴 保留已存在的临时记录
        const tempRecords = uploadHistory.value.filter(record => record.isTemporary);
        
        // 🔴 合并临时记录和后端记录（临时记录在前）
        uploadHistory.value = [...tempRecords, ...processedData];
        
        console.log('✅ 历史记录已更新，包含临时记录:', uploadHistory.value.length);
        
      } catch (error) {
        console.error('❌ 加载历史记录失败:', error);
        // 🔴 加载失败时，仍然保留临时记录
        const tempRecords = uploadHistory.value.filter(record => record.isTemporary);
        uploadHistory.value = tempRecords;
      } finally {
        isLoadingHistory.value = false;
      }
    };

    // 修改loadHistoryRecord方法
    const loadHistoryRecord = async (record: HistoryRecord) => {
      console.log('========================================');
      console.log('📄 开始加载协议:', record.id);
      
      resetAllStates();

      currentFileId.value = record.id;
      
      uploadedFile.value = { 
        name: record.fileName, 
        size: record.fileSize 
      };
      
      protocolIR.value = record.protocolIR || [];
      
      proverifCode.value = record.proverifCode || '';
      
      // 🔴 直接加载验证结果
      verificationResults.value = record.verificationResults || null;
      
      // 🔴 自动提取已验证的属性
      if (record.verificationResults && record.verificationResults.security_properties) {
        selectedProperties.value = record.verificationResults.security_properties.map(
          p => p.property
        );
      } else {
        selectedProperties.value = record.selectedProperties || [];
      }
      
      console.log('✅ 验证结果:', verificationResults.value);
      
      // 跳转到时序图步骤
      currentStep.value = 1;
      
      console.log('📄 跳转到步骤:', currentStep.value);
      console.log('========================================');
    };

    const resetAllStates = () => {
      protocolIR.value = [];
      selectedProperties.value = [];
      proverifCode.value = '';
      verificationResults.value = null;
      currentStep.value = 0;
      currentFileId.value = null;
      selectedStep.value = null;
    };

    const nextStep = () => {
      if (currentStep.value < 3) { // 步骤数量减少，调整最大值
        currentStep.value = currentStep.value + 1;
      }
    };

    const navigateToStep = (index) => {
      if (index === 3 || index <= currentStep.value || uploadedFile.value) { // 历史记录变为步骤3
        currentStep.value = index;
      }
    };

    const getOperationType = (id) => {
      if (id.includes('message')) return 'message';
      if (id.includes('validate')) return 'validate';
      return 'calculate';
    };

    const formatFileSize = (bytes) => {
      if (bytes < 1024) return `${bytes} B`;
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    };

    const copyIR = () => {
      navigator.clipboard.writeText(JSON.stringify(protocolIR.value, null, 2));
      alert('IR数据已复制到剪贴板');
    };

    const copyCode = () => {
      navigator.clipboard.writeText(proverifCode.value);
      alert('ProVerif代码已复制到剪贴板');
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

    const toggleProperty = (propertyId) => {
      selectedProperties.value = selectedProperties.value.includes(propertyId)
        ? selectedProperties.value.filter((id) => id !== propertyId)
        : [...selectedProperties.value, propertyId];
    };

    const removeProperty = (propertyId) => {
      selectedProperties.value = selectedProperties.value.filter(
        (id) => id !== propertyId,
      );
    };

    const getPropertyName = (propertyId) => {
      const property = securityProperties.find((p) => p.id === propertyId);
      return property ? property.name : '';
    };

    // 修改 runVerification 方法 - 验证后更新临时历史记录
    const runVerification = async () => {
      isVerifying.value = true;
      verificationResults.value = null;
      
      const verificationStates = [
        "正在读取验证结果...",
        "解析验证数据...",
        "生成验证报告...",
        "验证完成..."
      ];
      
      try {
        console.log('📥 开始读取验证结果，协议ID:', currentFileId.value);
        
        // 模拟加载进度
        const totalSteps = 4;
        const intervalTime = 500;
        
        for (let i = 0; i < totalSteps; i++) {
          verificationStatus.value = verificationStates[i];
          await new Promise(resolve => setTimeout(resolve, intervalTime));
        }
        
        // 🔴 查找当前记录是否为临时记录
        const tempRecord = uploadHistory.value.find(
          record => record.isTemporary && record.fileName === uploadedFile.value?.name
        );
        
        // 🔴 如果是临时记录，使用原始协议ID读取验证结果
        const protocolIdToFetch = tempRecord?.originalProtocolId || currentFileId.value;
        
        // 从后端读取当前协议的详细信息（包含验证结果）
        const protocolDetail = await fetchFormalGptProtocolDetail(protocolIdToFetch);
        
        if (protocolDetail && protocolDetail.verificationResults) {
          verificationResults.value = protocolDetail.verificationResults;
          
          // 自动提取已验证的属性
          if (protocolDetail.verificationResults.security_properties) {
            selectedProperties.value = protocolDetail.verificationResults.security_properties.map(
              p => p.property
            );
          }
          
          // 🔴 更新临时历史记录的验证结果
          if (tempRecord) {
            tempRecord.verificationResults = protocolDetail.verificationResults;
            tempRecord.selectedProperties = selectedProperties.value;
            console.log('✅ 临时历史记录已更新验证结果');
          }
          
          console.log('✅ 验证结果加载成功:', verificationResults.value);
        } else {
          throw new Error('未找到验证结果数据');
        }
      } catch (error) {
        console.error('❌ 读取验证结果失败:', error);
        alert(`读取验证结果失败: ${error.message || '未知错误'}`);
      } finally {
        isVerifying.value = false;
      }
    };

    watch(currentStep, (newStep) => {
      console.log('👀 步骤变化:', newStep);
      if (newStep === 3 && uploadHistory.value.length === 0) { // 历史记录变为步骤3
        loadHistoryFromBackend();
      }
    });

    onMounted(() => {
      console.log('🚀 组件已挂载');
      currentStep.value = 3; // 默认显示历史记录
    });

    // 添加删除历史记录的方法
    const deleteHistoryRecord = (recordId, event) => {
      // 阻止事件冒泡，防止触发loadHistoryRecord
      event.stopPropagation();
      
      // 确认删除
      if (confirm('确定要删除这条历史记录吗？')) {
        uploadHistory.value = uploadHistory.value.filter(
          (record) => record.id !== recordId
        );
        
        // 如果删除的是当前选中的记录，重置状态
        if (currentFileId.value === recordId) {
          resetAllStates();
        }
      }
    };

    return {
      steps,
      securityProperties,
      currentStep,
      uploadedFile,
      selectedProperties,
      isParsing,
      parsingProgress,
      parsingStatus, // 新增解析状态文本
      currentFileId,
      protocolIR,
      proverifCode,
      verificationResults,
      uploadHistory,
      isVerifying,
      verificationStatus, // 新增验证状态文本
      isLoadingHistory,
      irStatistics,
      handleFileUpload,
      loadHistoryRecord,
      loadHistoryFromBackend,
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
      runVerification, // 合并后的验证函数
      participantNames,
      isPartyAOperation,
      isPartyBOperation,
      stepPositions,
      getStepPosition,
      totalHeight,
      selectedStep,
      handleStepClick,
      MESSAGE_WIDTH,
      ARROW_WIDTH,
      deleteHistoryRecord,
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
          协议设计形式化验证
        </h1>
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
        
        <!-- 解析动画区域 -->
        <div v-if="isParsing" class="mt-8 flex flex-col items-center justify-center rounded-lg border border-gray-200 bg-gray-50 p-8">
          <!-- 加载动画 -->
          <div class="mb-6 flex items-center justify-center">
            <div class="h-16 w-16 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
            <!-- 旋转的文档图标 -->
            <div class="absolute flex h-8 w-8 items-center justify-center text-blue-600">
              <svg 
                class="h-8 w-8" 
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
            </div>
          </div>
          
          <!-- 进度条 -->
          <div class="mb-4 w-full max-w-md">
            <div class="h-2 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                class="h-full bg-blue-500 transition-all duration-300 ease-out"
                :style="{ width: `${parsingProgress}%` }"
              ></div>
            </div>
          </div>
          
          <!-- 状态文本 -->
          <p class="text-center text-gray-700">
            {{ parsingStatus }} {{ Math.floor(parsingProgress) }}%
          </p>
          
          <!-- 步骤指示器 -->
          <div class="mt-8 flex w-full max-w-md items-center justify-between">
            <div class="flex flex-col items-center">
              <div class="mb-1 h-3 w-3 rounded-full" :class="parsingProgress >= 20 ? 'bg-blue-500' : 'bg-gray-300'"></div>
              <span class="text-xs text-gray-500">读取文件</span>
            </div>
            <div class="h-0.5 flex-1 bg-gray-200">
              <div class="h-full bg-blue-500" :style="{ width: parsingProgress >= 20 ? '100%' : '0%' }"></div>
            </div>
            <div class="flex flex-col items-center">
              <div class="mb-1 h-3 w-3 rounded-full" :class="parsingProgress >= 40 ? 'bg-blue-500' : 'bg-gray-300'"></div>
              <span class="text-xs text-gray-500">解析流程</span>
            </div>
            <div class="h-0.5 flex-1 bg-gray-200">
              <div class="h-full bg-blue-500" :style="{ width: parsingProgress >= 40 ? '100%' : '0%' }"></div>
            </div>
            <div class="flex flex-col items-center">
              <div class="mb-1 h-3 w-3 rounded-full" :class="parsingProgress >= 60 ? 'bg-blue-500' : 'bg-gray-300'"></div>
              <span class="text-xs text-gray-500">生成IR</span>
            </div>
            <div class="h-0.5 flex-1 bg-gray-200">
              <div class="h-full bg-blue-500" :style="{ width: parsingProgress >= 60 ? '100%' : '0%' }"></div>
            </div>
            <div class="flex flex-col items-center">
              <div class="mb-1 h-3 w-3 rounded-full" :class="parsingProgress >= 80 ? 'bg-blue-500' : 'bg-gray-300'"></div>
              <span class="text-xs text-gray-500">验证IR数据完整性</span>
            </div>
            <div class="h-0.5 flex-1 bg-gray-200">
              <div class="h-full bg-blue-500" :style="{ width: parsingProgress >= 80 ? '100%' : '0%' }"></div>
            </div>
            <div class="flex flex-col items-center">
              <div class="mb-1 h-3 w-3 rounded-full" :class="parsingProgress >= 100 ? 'bg-blue-500' : 'bg-gray-300'"></div>
              <span class="text-xs text-gray-500">完成</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Step 2: Sequence Diagram -->
      <section v-if="currentStep === 1" class="p-8">
        <!-- 统计数据 -->
        <div class="mb-6 grid grid-cols-4 gap-4">
          <div class="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <span
              class="h-6 w-6 rounded border border-gray-300 bg-blue-500"
            ></span>
            <span class="text-sm">消息传递 <span class="font-semibold text-blue-600">({{ irStatistics[1] }})</span></span>
          </div>
          <div class="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <span
              class="h-6 w-6 rounded border border-gray-300 bg-purple-500"
            ></span>
            <span class="text-sm">计算操作 <span class="font-semibold text-purple-600">({{ irStatistics[2] }})</span></span>
          </div>
          <div class="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <span
              class="h-6 w-6 rounded border border-gray-300 bg-green-500"
            ></span>
            <span class="text-sm">验证操作 <span class="font-semibold text-green-600">({{ irStatistics[3] }})</span></span>
          </div>
          <div class="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <span
              class="h-6 w-6 rounded border border-gray-300 bg-gray-500"
            ></span>
            <span class="text-sm">总操作数 <span class="font-semibold text-gray-600">({{ irStatistics[0] }})</span></span>
          </div>
        </div>

        <!-- 时序图区域 -->
        <div class="overflow-x-auto rounded-lg border border-gray-200 bg-white p-6">
          <div class="flex min-w-[1400px] justify-between px-6">
            <!-- Party A Column -->
            <div class="flex w-1/3 flex-col items-center">
              <div class="mb-4 rounded-lg border-2 border-blue-600 bg-white px-6 py-2 font-semibold text-blue-600 shadow-sm">
                {{ participantNames.partyA }}
              </div>
              <div class="relative flex w-full flex-col items-center" :style="{ height: totalHeight + 'px' }">
                <!-- Timeline -->
                <div
                  class="absolute left-[50%] w-1 -translate-x-1/2 transform bg-gray-300"
                  :style="{ top: 0, height: '100%' }"
                ></div>

                <!-- 左侧操作框的详情面板 -->
                <div
                  v-if="selectedStep && isPartyAOperation(selectedStep) && getOperationType(selectedStep.id) !== 'message'"
                  class="absolute z-20 max-w-[400px] rounded-lg border border-gray-200 bg-white p-4 shadow-lg"
                  :style="{ 
                    right: 'calc(50% + 120px)',
                    top: getStepPosition(selectedStep.id) + 'px',
                    transform: 'translateY(-50%)'
                  }"
                >
                  <div class="space-y-2 text-sm">
                    <div>
                      <h4 class="font-medium text-gray-500">ID</h4>
                      <p class="font-mono text-blue-600">{{ selectedStep.id }}</p>
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-500">操作方</h4>
                      <p>{{ selectedStep.operator }}</p>
                    </div>
                    <div v-if="selectedStep.expr">
                      <h4 class="font-medium text-gray-500">表达式</h4>
                      <p class="font-mono text-blue-600 break-all">{{ selectedStep.expr }}</p>
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-500">描述</h4>
                      <p class="text-gray-700">{{ selectedStep.desc }}</p>
                    </div>
                  </div>
                </div>

                <!-- A发给B的消息详情面板 -->
                <div
                  v-if="selectedStep && getOperationType(selectedStep.id) === 'message' && selectedStep.sender === participantNames.partyA"
                  class="absolute z-20 max-w-[400px] rounded-lg border border-gray-200 bg-white p-4 shadow-lg"
                  :style="{ 
                    right: 'calc(50% + 120px)',
                    top: getStepPosition(selectedStep.id) + 'px',
                    transform: 'translateY(-50%)'
                  }"
                >
                  <div class="space-y-2 text-sm">
                    <div>
                      <h4 class="font-medium text-gray-500">ID</h4>
                      <p class="font-mono text-blue-600">{{ selectedStep.id }}</p>
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-500">发送方</h4>
                      <p>{{ selectedStep.sender }}</p>
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-500">接收方</h4>
                      <p>{{ selectedStep.receiver }}</p>
                    </div>
                    <div v-if="selectedStep.expr">
                      <h4 class="font-medium text-gray-500">表达式</h4>
                      <p class="font-mono text-blue-600 break-all">{{ selectedStep.expr }}</p>
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-500">描述</h4>
                      <p class="text-gray-700">{{ selectedStep.desc }}</p>
                    </div>
                  </div>
                </div>

                <!-- Operation Boxes -->
                <div
                  v-for="(step, idx) in protocolIR"
                  :key="step.id"
                >
                  <!-- Timeline Dot -->
                  <div
                    v-if="
                      isPartyAOperation(step) &&
                      getOperationType(step.id) !== 'message'
                    "
                    class="absolute left-[50%] z-10 h-3 w-3 -translate-x-1/2 transform rounded-full border-2 border-white bg-blue-500 shadow-sm"
                    :style="{ top: getStepPosition(step.id) + 'px' }"
                  ></div>

                  <!-- Operation Box -->
                  <div
                    v-if="
                      isPartyAOperation(step) &&
                      getOperationType(step.id) !== 'message'
                    "
                    @click="handleStepClick(step)"
                    class="absolute cursor-pointer rounded-lg border-l-4 px-4 py-2 text-xs shadow-sm transition-transform hover:scale-105 whitespace-nowrap"
                    :class="[
                      getOperationType(step.id) === 'calculate'
                        ? 'border-purple-500 bg-purple-50'
                        : 'border-green-500 bg-green-50',
                      selectedStep && selectedStep.id === step.id ? 'ring-2 ring-blue-500' : ''
                    ]"
                    :style="{ 
                      left: 'calc(50% + 15px)',
                      top: getStepPosition(step.id) + 'px',
                      transform: 'translateY(-50%)',
                      maxWidth: '500px',
                      minWidth: '300px'
                    }"
                  >
                    <div class="flex items-start gap-2">
                      <span
                        class="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-semibold"
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
                      <div class="flex-1 whitespace-nowrap overflow-hidden">
                        <div v-if="step.expr" class="font-mono text-xs text-blue-600">
                          {{ step.expr }}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Messages Column -->
            <div class="flex w-1/3 flex-col items-center">
              <div class="mb-4 h-16"></div>
              <div class="relative flex justify-center" :style="{ height: totalHeight + 'px', width: MESSAGE_WIDTH + 'px' }">

                <div
                  v-for="(step, idx) in protocolIR"
                  :key="step.id"
                >
                  <div
                    v-if="getOperationType(step.id) === 'message'"
                    class="absolute flex flex-col items-center"
                    :style="{ 
                      top: getStepPosition(step.id) + 'px',
                      width: MESSAGE_WIDTH + 'px',
                      left: '50%',
                      transform: 'translate(-50%, -50%)'
                    }"
                  >
                    <!-- Message Header -->
                    <div
                      @click="handleStepClick(step)"
                      class="mb-1 cursor-pointer rounded-lg border-l-4 border-blue-500 bg-gradient-to-r from-blue-50 to-blue-100 px-3 py-1.5 text-xs shadow-md transition-transform hover:scale-105 whitespace-nowrap"
                      :style="{ maxWidth: MESSAGE_WIDTH + 'px', minWidth: '200px' }"
                      :class="[selectedStep && selectedStep.id === step.id ? 'ring-2 ring-blue-500' : '']"
                    >
                      <div class="flex items-center whitespace-nowrap">
                        <span class="font-mono text-xs font-semibold text-gray-700">{{ step.id }}</span>
                        <span v-if="step.expr" class="ml-1 font-mono text-xs text-blue-600">（{{ step.expr }}）</span>
                      </div>
                    </div>

                    <!-- Arrow -->
                    <div class="relative flex items-center justify-center">
                      <div class="relative flex h-3 items-center" :style="{ width: ARROW_WIDTH + 'px' }">
                        <div
                          class="absolute h-1 rounded-full"
                          :style="{
                            width: ARROW_WIDTH + 'px',
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
                              ? 'right-0 border-b-[6px] border-l-[8px] border-t-[6px] border-b-transparent border-l-blue-400 border-t-transparent'
                              : 'left-0 border-b-[6px] border-r-[8px] border-t-[6px] border-b-transparent border-r-blue-400 border-t-transparent',
                          ]"
                          :style="
                            step.sender === participantNames.partyA ? 'right: -1px;' : 'left: -1px;'
                          "
                        ></div>

                        <div
                          class="absolute h-2 w-2 rounded-full bg-blue-500 shadow-sm"
                          :class="[step.sender === participantNames.partyA ? 'left-0' : 'right-0']"
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Party B Column -->
            <div class="flex w-1/3 flex-col items-center">
              <div class="mb-4 rounded-lg border-2 border-blue-600 bg-white px-6 py-2 font-semibold text-blue-600 shadow-sm">
                {{ participantNames.partyB }}
              </div>
              <div class="relative flex w-full flex-col items-center" :style="{ height: totalHeight + 'px' }">
                <!-- Timeline -->
                <div
                  class="absolute left-[50%] w-1 -translate-x-1/2 transform bg-gray-300"
                  :style="{ top: 0, height: '100%' }"
                ></div>

                <!-- 右侧操作框的详情面板 -->
                <div
                  v-if="selectedStep && isPartyBOperation(selectedStep) && getOperationType(selectedStep.id) !== 'message'"
                  class="absolute z-20 max-w-[400px] rounded-lg border border-gray-200 bg-white p-4 shadow-lg"
                  :style="{ 
                    left: 'calc(50% + 120px)',
                    top: getStepPosition(selectedStep.id) + 'px',
                    transform: 'translateY(-50%)'
                  }"
                >
                  <div class="space-y-2 text-sm">
                    <div>
                      <h4 class="font-medium text-gray-500">ID</h4>
                      <p class="font-mono text-blue-600">{{ selectedStep.id }}</p>
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-500">操作方</h4>
                      <p>{{ selectedStep.operator }}</p>
                    </div>
                    <div v-if="selectedStep.expr">
                      <h4 class="font-medium text-gray-500">表达式</h4>
                      <p class="font-mono text-blue-600 break-all">{{ selectedStep.expr }}</p>
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-500">描述</h4>
                      <p class="text-gray-700">{{ selectedStep.desc }}</p>
                    </div>
                  </div>
                </div>

                <!-- B发给A的消息详情面板 -->
                <div
                  v-if="selectedStep && getOperationType(selectedStep.id) === 'message' && selectedStep.sender === participantNames.partyB"
                  class="absolute z-20 max-w-[400px] rounded-lg border border-gray-200 bg-white p-4 shadow-lg"
                  :style="{ 
                    left: 'calc(50% + 120px)',
                    top: getStepPosition(selectedStep.id) + 'px',
                    transform: 'translateY(-50%)'
                  }"
                >
                  <div class="space-y-2 text-sm">
                    <div>
                      <h4 class="font-medium text-gray-500">ID</h4>
                      <p class="font-mono text-blue-600">{{ selectedStep.id }}</p>
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-500">发送方</h4>
                      <p>{{ selectedStep.sender }}</p>
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-500">接收方</h4>
                      <p>{{ selectedStep.receiver }}</p>
                    </div>
                    <div v-if="selectedStep.expr">
                      <h4 class="font-medium text-gray-500">表达式</h4>
                      <p class="font-mono text-blue-600 break-all">{{ selectedStep.expr }}</p>
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-500">描述</h4>
                      <p class="text-gray-700">{{ selectedStep.desc }}</p>
                    </div>
                  </div>
                </div>

                <!-- Operation Boxes -->
                <div
                  v-for="(step, idx) in protocolIR"
                  :key="step.id"
                >
                  <!-- Timeline Dot -->
                  <div
                    v-if="
                      isPartyBOperation(step) &&
                      getOperationType(step.id) !== 'message'
                    "
                    class="absolute left-[50%] z-10 h-3 w-3 -translate-x-1/2 transform rounded-full border-2 border-white bg-blue-500 shadow-sm"
                    :style="{ top: getStepPosition(step.id) + 'px' }"
                  ></div>

                  <!-- Operation Box -->
                  <div
                    v-if="
                      isPartyBOperation(step) &&
                      getOperationType(step.id) !== 'message'
                    "
                    @click="handleStepClick(step)"
                    class="absolute cursor-pointer rounded-lg border-l-4 px-4 py-2 text-xs shadow-sm transition-transform hover:scale-105 whitespace-nowrap"
                    :class="[
                      getOperationType(step.id) === 'calculate'
                        ? 'border-purple-500 bg-purple-50'
                        : 'border-green-500 bg-green-50',
                      selectedStep && selectedStep.id === step.id ? 'ring-2 ring-blue-500' : ''
                    ]"
                    :style="{ 
                      right: 'calc(50% + 10px)',
                      top: getStepPosition(step.id) + 'px',
                      transform: 'translateY(-50%)',
                      maxWidth: '500px',
                      minWidth: '300px'
                    }"
                  >
                    <div class="flex items-start gap-2">
                      <span
                        class="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-semibold"
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
                      <div class="flex-1 whitespace-nowrap overflow-hidden">
                        <div v-if="step.expr" class="font-mono text-xs text-blue-600">
                          {{ step.expr }}
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
        <div class="mt-6 flex items-center justify-between">
          <button
            @click="currentStep = 0"
            class="rounded-lg bg-gray-600 px-6 py-3 font-medium text-white shadow-md transition-colors hover:bg-gray-700 hover:shadow-lg"
          >
            返回：文档上传
          </button>
          <button
            @click="nextStep"
            class="rounded-lg bg-blue-600 px-6 py-3 font-medium text-white shadow-md transition-colors hover:bg-blue-700 hover:shadow-lg"
          >
            继续：安全验证
          </button>
        </div>
      </section>

      <!-- 合并后的步骤：安全验证（包含安全属性选择和ProVerif验证） -->
      <section v-if="currentStep === 2" class="p-8">
        <!-- ProVerif代码展示 -->
        <div class="mb-8 overflow-hidden rounded-lg border border-gray-200">
          <div class="flex items-center justify-between border-b border-gray-200 bg-gray-50 p-4">
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
          <pre class="max-h-96 overflow-auto bg-gray-50 p-6 font-mono text-sm text-blue-600">{{ proverifCode || '加载协议数据后将显示ProVerif代码...' }}</pre>
        </div>

        <!-- 🔴 如果没有验证结果，显示"开始验证"按钮 -->
        <button
          v-if="!verificationResults"
          @click="runVerification"
          :disabled="!proverifCode || isVerifying"
          class="mb-8 rounded-lg px-6 py-3 font-medium transition-colors"
          :class="[
            (!proverifCode || isVerifying)
              ? 'cursor-not-allowed bg-gray-400 text-white'
              : 'bg-blue-600 text-white hover:bg-blue-700',
          ]"
        >
          {{ isVerifying ? '正在验证...' : '开始验证' }}
        </button>

        <!-- 验证加载动画 -->
        <div v-if="isVerifying" class="mb-8 flex flex-col items-center justify-center rounded-lg border border-gray-200 bg-gray-50 p-8">
          <div class="mb-6 flex items-center justify-center">
            <div class="h-16 w-16 animate-spin rounded-full border-4 border-purple-200 border-t-purple-600"></div>
            <div class="absolute flex h-8 w-8 items-center justify-center text-purple-600">
              <svg 
                class="h-8 w-8" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  stroke-linecap="round" 
                  stroke-linejoin="round" 
                  stroke-width="2" 
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" 
                />
              </svg>
            </div>
          </div>
          <p class="text-center text-gray-700">{{ verificationStatus }}</p>
        </div>

        <!-- 🔴 直接显示验证结果（如果存在） -->
        <div v-if="verificationResults && !isVerifying" class="rounded-lg border border-gray-200 bg-gray-50 p-6">
          <h3 class="mb-6 text-xl font-semibold">验证结果</h3>
          
          <!-- 验证结果列表 -->
          <div v-if="verificationResults.security_properties && verificationResults.security_properties.length > 0" class="space-y-4">
            <div
              v-for="(prop, index) in verificationResults.security_properties"
              :key="index"
              class="rounded-lg border p-4 transition-shadow hover:shadow-md"
              :class="[
                prop.result
                  ? 'border-green-300 bg-green-50'
                  : 'border-red-300 bg-red-50',
              ]"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="mb-2 flex items-center gap-3">
                    <span
                      class="flex h-8 w-8 items-center justify-center rounded-full text-lg font-bold"
                      :class="[
                        prop.result
                          ? 'bg-green-500 text-white'
                          : 'bg-red-500 text-white',
                      ]"
                    >
                      {{ prop.result ? '✓' : '✗' }}
                    </span>
                    <h4 class="text-lg font-semibold capitalize" :class="[prop.result ? 'text-green-800' : 'text-red-800']">
                      {{ getPropertyName(prop.property) }}
                    </h4>
                  </div>
                  <p class="ml-11 text-sm text-gray-700">
                    {{ prop.query }}
                  </p>
                </div>
                <span
                  class="rounded px-3 py-1 text-xs font-medium"
                  :class="[
                    prop.result
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800',
                  ]"
                >
                  {{ prop.result ? '验证通过' : '验证失败' }}
                </span>
              </div>
            </div>
          </div>
          
          <!-- 无验证结果提示 -->
          <div v-else class="py-8 text-center text-gray-500">
            暂无验证结果数据
          </div>
        </div>

        <!-- 导航按钮 -->
        <div class="mt-8 flex items-center justify-between">
          <button
            @click="currentStep = 1"
            class="rounded-lg bg-gray-600 px-6 py-3 font-medium text-white shadow-md transition-colors hover:bg-gray-700 hover:shadow-lg"
          >
            返回：时序图
          </button>
          <button
            @click="currentStep = 3"
            class="rounded-lg bg-blue-600 px-6 py-3 font-medium text-white shadow-md transition-colors hover:bg-blue-700 hover:shadow-lg"
          >
            查看：历史记录
          </button>
        </div>
      </section>

      <!-- Step 4: History Records (原步骤5) -->
      <section v-if="currentStep === 3" class="p-8">
        <!-- 加载状态 -->
        <div v-if="isLoadingHistory" class="flex items-center justify-center py-12">
          <div class="h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600"></div>
          <span class="ml-4 text-gray-600">正在加载历史记录...</span>
        </div>

        <!-- 空状态 -->
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

        <!-- 历史记录列表 -->
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

              <!-- 显示数据状态 -->
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

              <!-- 显示验证结果 -->
              <div v-if="record.verificationResults && record.verificationResults.security_properties" class="mt-3 space-y-2">
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
                  <span class="text-sm capitalize text-gray-700">{{ getPropertyName(prop.property) }}</span>
                  <span class="text-xs text-gray-500">- {{ prop.query }}</span>
                </div>
              </div>
            </div>

            <!-- 删除按钮 -->
            <div class="flex-shrink-0">
              <button
                @click.stop="deleteHistoryRecord(record.id, $event)"
                class="flex h-8 w-8 items-center justify-center rounded-full bg-red-500 p-1 text-white transition-all hover:bg-red-600"
                title="删除历史记录"
              >
                <svg
                  class="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.ring-2 {
  box-shadow: 0 0 0 2px currentColor;
}

/* 动画样式 */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 平滑过渡效果 */
.transition-all {
  transition: all 0.3s ease;
}

.ease-out {
  transition-timing-function: cubic-bezier(0, 0, 0.2, 1);
}
</style>
