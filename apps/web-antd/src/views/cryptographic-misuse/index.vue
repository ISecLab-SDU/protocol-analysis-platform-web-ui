<script setup lang="ts">
// 导入ECharts相关组件
import type { EchartsUIType } from '@vben/plugins/echarts';

import { computed, onMounted, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

// 导入需要运行时的组件和函数
import { message, Popconfirm } from 'ant-design-vue';
import {
  Badge,
  Button,
  Card,
  Col,
  Divider,
  Layout,
  List,
  Menu,
  Progress,
  Row,
  Tag,
  Tree,
  Typography,
} from 'ant-design-vue';

// 从api导入函数
import {
  analyzeFirmware,
  isValidFirmwareFile,
} from '../../api/firmwareAnalysis';
// 导入requestClient
import { requestClient } from '../../api/request';

// 定义分析结果类型
interface AnalysisResult {
  functionName: string;
  issueType: string;
  severity: string;
  parameters?: string;
  description: string;
  codeSnippet?: string;
}

// 定义历史记录类型
interface HistoryRecord {
  id: string;
  fileName: string;
  fileSize: number;
  analysisTime: Date;
  results: AnalysisResult[];
  treeData: TreeDataNode[];
}

// 自定义树节点类型
interface TreeDataNode {
  title: string;
  key: string;
  isLeaf: boolean;
  children?: TreeDataNode[];
}

// ECharts关系图节点类型
interface GraphNode {
  id: string;
  name: string;
  value?: string;
  symbolSize?: number;
  category?: number;
  itemStyle?: {
    color?: string;
  };
  label?: {
    formatter?: string;
    show?: boolean;
  };
}

// ECharts关系图边类型
interface GraphLink {
  source: string;
  target: string;
  lineStyle?: {
    color?: string;
    curveness?: number;
    width?: number;
  };
}

// 导航栏目
const navItems = [
  { key: 'system-intro', label: '系统介绍' },
  { key: 'upload-analysis', label: '上传分析' },
  { key: 'history-records', label: '历史记录' },
  { key: 'analysis-results', label: '分析结果', disabled: true },
];

// 当前选中的栏目
const currentNav = ref('system-intro');

// 上传的文件
const file = ref<File | null>(null);
// 文件上传输入框引用
const fileInput = ref<HTMLInputElement | null>(null);
// 上传区域引用
const uploadArea = ref<HTMLDivElement | null>(null);

// 分析结果
const analysisResults = ref<AnalysisResult[]>([]);

// 加载状态
const loading = ref<boolean>(false);

// 分析进度
const analysisProgress = ref<number>(0);

// 分析是否完成
const analysisComplete = ref<boolean>(false);

// 导出PDF文件
const exportPDF = async () => {
  try {
    // 检查是否有当前文件或选中的历史记录
    let fileName = '';

    if (file.value) {
      // 如果有当前上传的文件
      fileName = file.value.name;
    } else if (selectedHistoryId.value) {
      // 如果有选中的历史记录
      const record = historyRecords.value.find(
        (r) => r.id === selectedHistoryId.value,
      );
      if (record) {
        fileName = record.fileName;
      }
    }

    if (!fileName) {
      message.error('无法确定要导出的文件名');
      return;
    }

    // 构建API请求URL
    const apiUrl = `/api/firmware/export?filename=${encodeURIComponent(fileName)}`;

    // 设置加载状态
    loading.value = true;

    // 发送请求到后端API
    const response = await fetch(apiUrl);

    if (!response.ok) {
      throw new Error(`API错误: ${response.status}`);
    }

    // 获取PDF文件Blob
    const blob = await response.blob();

    // 构建下载文件名
    const pdfFileName = `${fileName}-dfg.pdf`;

    // 创建下载链接
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = pdfFileName;
    document.body.append(link);
    link.click();

    // 清理
    link.remove();
    URL.revokeObjectURL(link.href);

    message.success('PDF文件下载成功');
  } catch (error) {
    console.error('导出PDF失败:', error);
    message.error('导出PDF文件失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};

// 树状图数据
const treeData = ref<TreeDataNode[]>([]);

// 历史记录列表
const historyRecords = ref<HistoryRecord[]>([]);

// 当前选中的历史记录ID
const selectedHistoryId = ref<null | string>(null);

// 从后端API加载历史记录
const loadHistoryRecords = async () => {
  try {
    const response = await requestClient.get('/firmware/history');
    if (response) {
      historyRecords.value = response.map((record: any) => ({
        ...record,
        analysisTime: new Date(record.analysisTime),
      }));
    }
  } catch (error) {
    console.error('加载历史记录失败:', error);
    message.error('加载历史记录失败');
  }
};

// 保存历史记录到后端API
const saveHistoryRecords = async () => {
  // 这个函数不再需要直接调用，因为saveToHistory和deleteHistoryRecord会直接调用API
};

// 保存当前分析结果到后端API
const saveToHistory = async () => {
  if (!file.value || analysisResults.value.length === 0) return;

  const newRecord: HistoryRecord = {
    id: Date.now().toString(),
    fileName: file.value.name,
    fileSize: file.value.size,
    analysisTime: new Date(),
    results: JSON.parse(JSON.stringify(analysisResults.value)),
    treeData: JSON.parse(JSON.stringify(treeData.value)),
  };

  try {
    await requestClient.post('/firmware/history', newRecord);
    // 重新加载历史记录以确保数据一致
    await loadHistoryRecords();
  } catch (error) {
    console.error('保存历史记录失败:', error);
    message.error('保存历史记录失败');
  }
};

// 从历史记录加载分析结果
const loadFromHistory = async (recordId: string) => {
  try {
    // 先确保历史记录是最新的
    await loadHistoryRecords();
    const record = historyRecords.value.find((r) => r.id === recordId);
    if (record) {
      selectedHistoryId.value = recordId;
      analysisResults.value = JSON.parse(JSON.stringify(record.results));
      treeData.value = JSON.parse(JSON.stringify(record.treeData));
      analysisComplete.value = true;
      navItems[3].disabled = false; // 启用分析结果导航
      handleNavChange('analysis-results');

      // 显式渲染函数调用关系图
      if (treeData.value && treeData.value.length > 0) {
        const { nodes, links } = convertTreeToGraphData(treeData.value);
        renderGraphChart(nodes, links);
      }
    }
  } catch (error) {
    console.error('加载历史记录详情失败:', error);
    message.error('加载历史记录详情失败');
  }
};

// 删除历史记录
const deleteHistoryRecord = async (recordId: string) => {
  try {
    await requestClient.delete(`/firmware/history/${recordId}`);
    // 重新加载历史记录以确保数据一致
    await loadHistoryRecords();
    message.success('历史记录已删除');
  } catch (error) {
    console.error('删除历史记录失败:', error);
    message.error('删除历史记录失败');
  }
};

// ECharts关系图引用
const graphRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(graphRef);

// 组件挂载时执行初始化操作
onMounted(async () => {
  await loadHistoryRecords();
  // 移除对uploadArea的检查，因为它只在特定导航下才会渲染
});

// 处理文件上传
const handleFileUpload = (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    const selectedFile = target.files[0];

    if (selectedFile) {
      // 使用API进行文件验证
      if (!isValidFirmwareFile(selectedFile)) {
        message.error('请上传.so.bin.zip.tar格式的固件文件');
        return;
      }

      file.value = selectedFile;
      message.success(`已选择文件: ${selectedFile.name}`);
    }
  }
};

// 处理上传区域点击
const handleUploadAreaClick = () => {
  if (fileInput.value) {
    try {
      fileInput.value.click();
    } catch (error) {
      console.error('点击上传输入框失败:', error);
      message.error('无法打开文件选择器，请尝试刷新页面');
    }
  } else {
    console.error('文件输入框引用未找到');
    message.error('上传功能未准备好，请刷新页面重试');
  }
};

// 处理拖放事件
const handleDragOver = (e: DragEvent) => {
  e.preventDefault();
  e.stopPropagation();
  if (uploadArea.value) {
    uploadArea.value.classList.add('upload-area-dragging');
  }
};

const handleDragLeave = () => {
  if (uploadArea.value) {
    uploadArea.value.classList.remove('upload-area-dragging');
  }
};

const handleDrop = (e: DragEvent) => {
  e.preventDefault();
  e.stopPropagation();

  if (uploadArea.value) {
    uploadArea.value.classList.remove('upload-area-dragging');
  }

  if (
    e.dataTransfer &&
    e.dataTransfer.files &&
    e.dataTransfer.files.length > 0
  ) {
    const droppedFile = e.dataTransfer.files[0];

    if (droppedFile) {
      if (!isValidFirmwareFile(droppedFile)) {
        message.error('请上传.so.bin.zip.tar格式的固件文件');
        return;
      }

      file.value = droppedFile;
      message.success(`已选择文件: ${droppedFile.name}`);
    }
  }
};

// 生成树状图数据
const generateTreeData = (): TreeDataNode[] => {
  // 确保分析结果存在且是数组
  if (
    !Array.isArray(analysisResults.value) ||
    analysisResults.value.length === 0
  ) {
    return [];
  }

  // 创建根节点，使用上传的文件名作为标题
  const rootNode: TreeDataNode = {
    title: file.value?.name || '固件文件',
    key: 'root',
    isLeaf: false,
    children: [],
  };

  // 按严重性分组
  const severityGroups: Record<string, any[]> = {
    high: [],
    medium: [],
    low: [],
  };

  // 为每个分析结果创建节点
  analysisResults.value.forEach((item, index) => {
    if (!item) return;

    // 创建函数节点
    const functionNode: TreeDataNode = {
      title: `${item.issueType || '未分类问题'} - ${item.functionName || `函数${index + 1}`}`,
      key: `function-${index}`,
      isLeaf: false,
      children: [],
    };

    // 添加描述节点
    if (item.description) {
      functionNode.children.push({
        title: `描述: ${item.description}`,
        key: `desc-${index}`,
        isLeaf: true,
      });
    }

    // 添加参数节点
    if (item.parameters) {
      functionNode.children.push({
        title: `参数: ${item.parameters}`,
        key: `params-${index}`,
        isLeaf: true,
      });
    }

    // 添加代码片段节点
    if (item.codeSnippet) {
      // 截断长的代码片段以避免显示问题
      const shortSnippet =
        item.codeSnippet.length > 50
          ? `${item.codeSnippet.slice(0, 50)}...`
          : item.codeSnippet;
      functionNode.children.push({
        title: `代码: ${shortSnippet}`,
        key: `code-${index}`,
        isLeaf: true,
      });
    }

    // 按严重性将节点添加到相应组中
    const severity = item.severity || 'low';
    if (severityGroups[severity]) {
      severityGroups[severity].push(functionNode);
    } else {
      severityGroups.low.push(functionNode); // 默认低危
    }
  });

  // 创建严重性分组节点
  const severityMap = {
    high: '高危问题',
    medium: '中危问题',
    low: '低危问题',
  };

  Object.keys(severityGroups).forEach((severity) => {
    if (severityGroups[severity].length > 0) {
      const groupNode: TreeDataNode = {
        title: severityMap[severity as keyof typeof severityMap],
        key: `severity-${severity}`,
        isLeaf: false,
        children: severityGroups[severity],
      };
      rootNode.children?.push(groupNode);
    }
  });

  return [rootNode];
};

// 将树形数据转换为ECharts关系图数据
const convertTreeToGraphData = (
  treeData: TreeDataNode[],
): { links: GraphLink[]; nodes: GraphNode[] } => {
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  const visited = new Set<string>();

  // 递归遍历树数据
  const traverseTree = (node: TreeDataNode, parentKey?: string) => {
    if (visited.has(node.key)) return;
    visited.add(node.key);

    // 创建节点
    const shortTitle =
      node.title.length > 30 ? `${node.title.slice(0, 30)}...` : node.title;
    nodes.push({
      id: node.key,
      name: shortTitle,
      value: node.title,
      symbolSize: node.isLeaf ? 20 : 30,
      category: node.isLeaf ? 1 : 0,
      itemStyle: {
        color: node.isLeaf ? '#1890ff' : '#52c41a',
      },
      label: {
        show: true,
        formatter: `{b}`,
      },
    });

    // 创建边
    if (parentKey) {
      links.push({
        source: parentKey,
        target: node.key,
        lineStyle: {
          color: '#999',
          width: 2,
          curveness: 0.3,
        },
      });
    }

    // 递归处理子节点
    if (node.children) {
      node.children.forEach((child) => {
        traverseTree(child, node.key);
      });
    }
  };

  // 遍历所有根节点
  treeData.forEach((node) => {
    traverseTree(node);
  });

  return { nodes, links };
};

// 渲染ECharts关系图
const renderGraphChart = (nodes: GraphNode[], links: GraphLink[]) => {
  renderEcharts({
    tooltip: {
      trigger: 'item',
      formatter: '{b}',
    },
    legend: [
      {
        data: ['函数', '调用点'],
      },
    ],
    animationDurationUpdate: 1500,
    animationEasingUpdate: 'quinticInOut',
    series: [
      {
        type: 'graph',
        layout: 'force',
        force: {
          repulsion: 1000,
          edgeLength: [80, 150],
        },
        roam: true,
        label: {
          show: true,
          position: 'right',
          formatter: '{b}',
          fontSize: 12,
        },
        data: nodes,
        links,
        categories: [
          {
            name: '函数',
          },
          {
            name: '调用点',
          },
        ],
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 4,
          },
        },
        lineStyle: {
          opacity: 0.9,
          width: 2,
          curveness: 0,
          type: 'solid',
        },
      },
    ],
  });
};

// 处理分析按钮点击
const handleAnalyze = async () => {
  if (!file.value) {
    message.error('请先上传固件文件');
    return;
  }

  loading.value = true;
  analysisProgress.value = 0;
  analysisComplete.value = false;
  analysisResults.value = [];
  treeData.value = [];

  try {
    // 模拟进度更新
    const progressInterval = setInterval(() => {
      analysisProgress.value += 5;
      if (analysisProgress.value >= 95) {
        clearInterval(progressInterval);
      }
    }, 150);

    // 调用API进行分析
    const result = await analyzeFirmware({
      fileName: file.value.name,
      fileSize: file.value.size,
      file: file.value,
    });

    clearInterval(progressInterval);
    analysisProgress.value = 100;
    analysisComplete.value = true;

    // 确保正确处理后端返回的数据结构
    // 后端返回的格式是: {code: 0, data: ..., error: null, message: ...}
    // 检查响应对象格式，处理可能的嵌套情况
    const responseData = result?.data || {};

    if (responseData.code === 0 && responseData.data?.functions) {
      // 直接使用后端返回的分析结果
      analysisResults.value = responseData.data.functions;
      console.log('分析结果:', analysisResults.value);

      // 生成树状图数据
      treeData.value = generateTreeData();
      message.success(responseData.message || '固件分析完成');

      // 保存到历史记录
      saveToHistory();

      // 启用分析结果导航
      navItems[3].disabled = false;
    } else {
      const errorMsg =
        responseData.message || result?.message || '分析失败，未返回有效数据';
      message.error(errorMsg);
      console.error('分析失败:', result);
    }
  } catch (error) {
    const errorMsg =
      error instanceof Error ? error.message : '分析过程中发生错误';
    message.error(`分析失败: ${errorMsg}`);
    console.error('Firmware analysis error:', error);
  } finally {
    loading.value = false;
  }
};

// 切换导航栏目
const handleNavChange = (key: string) => {
  // 只有在分析完成后才能访问分析结果页面
  if (
    key === 'analysis-results' &&
    (analysisResults.value.length === 0 || navItems[3].disabled)
  ) {
    message.warning('请先完成固件分析');
    return;
  }
  currentNav.value = key;
  // 滚动到页面顶部
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

// 跳转到分析结果页面
const goToResults = () => {
  handleNavChange('analysis-results');
};

// 根据严重性获取对应的标签颜色
const getSeverityColor = (severity: string): string => {
  const colorMap: Record<string, string> = {
    high: 'red',
    medium: 'orange',
    low: 'blue',
  };
  return colorMap[severity] || 'default';
};

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${Number.parseFloat((bytes / k ** i).toFixed(2))} ${sizes[i]}`;
};

// 格式化日期
const formatDate = (date: Date): string => {
  const d = new Date(date);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}`;
};

// 获取分析进度条的状态
const getProgressStatus = computed(() => {
  if (analysisProgress.value >= 100) {
    return 'success';
  }
  return 'active';
});

// 暴露在模板中使用的函数
defineExpose({
  handleFileUpload,
  handleUploadAreaClick,
  handleAnalyze,
  getSeverityColor,
  getProgressStatus,
  formatFileSize,
  formatDate,
});

// 当treeData更新时重新渲染关系图
watch(
  () => treeData.value,
  (newData) => {
    if (newData && newData.length > 0) {
      const { nodes, links } = convertTreeToGraphData(newData);
      renderGraphChart(nodes, links);
    }
  },
  { immediate: true },
);
</script>

<template>
  <div
    class="firmware-analysis-page min-h-screen bg-gradient-to-br from-gray-50 to-gray-100"
  >
    <!-- 顶部导航栏 - 现代设计 -->
    <Layout.Header
      class="relative overflow-hidden bg-white text-gray-800 shadow-lg"
    >
      <!-- 标题区域 - 白色背景 -->

      <div
        class="container relative z-10 mx-auto flex flex-col items-center justify-between px-4 py-4 md:flex-row"
      >
        <div class="mb-2 flex items-center space-x-3 md:mb-0">
          <IconifyIcon
            icon="ant-design:security-scan-outlined"
            class="text-2xl text-indigo-600"
          />
          <Typography.Title
            :level="3"
            class="m-0 font-light tracking-wide text-gray-800"
          >
            <span class="font-bold text-gray-900">密码算法安全分析</span>
          </Typography.Title>
        </div>
        <!-- 已删除基于数据流的密码规范检测技术 -->
      </div>
    </Layout.Header>

    <!-- 栏目导航 - 现代设计 -->
    <div
      class="sticky top-0 z-10 border-b bg-white bg-opacity-95 shadow-sm backdrop-blur-sm"
    >
      <div class="container mx-auto px-4">
        <Menu
          mode="horizontal"
          :selected-keys="[currentNav]"
          @click="({ key }) => handleNavChange(key)"
          class="border-0"
        >
          <Menu.Item
            v-for="item in navItems"
            :key="item.key"
            :disabled="item.disabled"
            class="cursor-pointer px-6 py-4 text-gray-700 transition-all duration-300 hover:bg-indigo-50 hover:text-indigo-700"
            :class="{ 'font-medium text-indigo-700': currentNav === item.key }"
          >
            {{ item.label }}
          </Menu.Item>
        </Menu>
      </div>
    </div>

    <Layout.Content class="container mx-auto px-4 py-8">
      <!-- 第一栏：系统介绍 - 美化版本 -->
      <section
        id="system-intro"
        class="animate-fadeIn mb-12"
        v-if="currentNav === 'system-intro'"
      >
        <!-- 英雄区域 -->
        <Card class="mb-8 overflow-hidden border-none bg-white shadow-xl">
          <div class="p-8 text-center md:p-12">
            <IconifyIcon
              icon="ant-design:security-scan-outlined"
              class="mb-6 text-5xl text-indigo-600"
            />
            <Typography.Title :level="2" class="mb-4 font-bold text-gray-800">
              密码算法安全分析平台
            </Typography.Title>
            <Typography.Paragraph
              class="mx-auto mb-8 max-w-3xl text-lg text-gray-700"
            >
              本平台基于前沿的数据流分析技术，针对网络设备固件中的密码算法使用规范进行深度检测，
              集成了学术界领先的密码误用分析工具CRYPTODY，能够精准识别固件中密码算法的不安全使用模式。
            </Typography.Paragraph>
            <div class="flex flex-wrap justify-center gap-4">
              <Button
                type="primary"
                size="large"
                @click="handleNavChange('upload-analysis')"
                class="border-none bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
              >
                <IconifyIcon icon="ant-design:upload-outlined" class="mr-2" />
                开始分析
              </Button>
              <Button
                size="large"
                @click="handleNavChange('history-records')"
                class="border-indigo-200 bg-white text-indigo-600 hover:bg-indigo-50"
              >
                <IconifyIcon icon="ant-design:history-outlined" class="mr-2" />
                查看历史
              </Button>
            </div>
          </div>
        </Card>

        <!-- 核心能力 -->
        <Typography.Title :level="3" class="mb-8 text-center text-gray-800">
          平台核心能力
        </Typography.Title>

        <div class="mb-12 space-y-6">
          <Card
            class="group overflow-hidden border-none transition-all duration-300 hover:shadow-xl"
          >
            <div class="relative p-6">
              <div
                class="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-indigo-100 opacity-60 transition-colors duration-300 group-hover:bg-indigo-200"
              ></div>
              <div class="relative z-10">
                <div class="mb-5 text-4xl text-indigo-600">
                  <IconifyIcon icon="ant-design:data-analysis-outlined" />
                </div>
                <div class="mb-5 text-4xl text-indigo-600">
                  <svg
                    class="h-7 w-7 text-indigo-600"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3.586L7.707 9.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 10.586V7z"
                      clip-rule="evenodd"
                    />
                  </svg>
                </div>
                <Typography.Title :level="4" class="mb-3 text-gray-800">
                  数据流驱动分析
                </Typography.Title>
                <Typography.Paragraph class="text-gray-600">
                  通过追踪固件中的数据流向，精准识别密钥生成、加密解密、哈希计算等关键密码操作，
                  实现对密码算法使用全生命周期的安全评估。
                </Typography.Paragraph>
              </div>
            </div>
          </Card>

          <Card
            class="group overflow-hidden border-none transition-all duration-300 hover:shadow-xl"
          >
            <div class="relative p-6">
              <div
                class="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-purple-100 opacity-60 transition-colors duration-300 group-hover:bg-purple-200"
              ></div>
              <div class="relative z-10">
                <div class="mb-5 text-4xl text-purple-600">
                  <IconifyIcon icon="ant-design:algorithm-outlined" />
                </div>
                <div class="mb-3">
                  <svg
                    class="mb-2 h-7 w-7 text-purple-600"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                      clip-rule="evenodd"
                    />
                  </svg>
                </div>
                <Typography.Title :level="4" class="mb-3 text-gray-800">
                  密码规范检测
                </Typography.Title>
                <Typography.Paragraph class="text-gray-600">
                  基于NIST等权威机构的密码标准，检测固件中使用的加密算法、模式和参数是否符合安全规范，
                  识别过时算法、弱密钥、不安全模式等风险点。
                </Typography.Paragraph>
              </div>
            </div>
          </Card>

          <Card
            class="group overflow-hidden border-none transition-all duration-300 hover:shadow-xl"
          >
            <div class="relative p-6">
              <div
                class="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-blue-100 opacity-60 transition-colors duration-300 group-hover:bg-blue-200"
              ></div>
              <div class="relative z-10">
                <div class="mb-5 text-4xl text-blue-600">
                  <IconifyIcon icon="ant-design:bar-chart-outlined" />
                </div>
                <Typography.Title :level="4" class="mb-3 text-gray-800">
                  可视化分析报告
                </Typography.Title>
                <Typography.Paragraph class="text-gray-600">
                  通过函数调用关系图谱、风险热力图等多种可视化方式，直观展示固件中的密码操作分布
                  和安全风险，提供可直接用于修复的详细建议。
                </Typography.Paragraph>
              </div>
            </div>
          </Card>
        </div>

        <!-- 技术优势 -->
        <Card class="mb-12 border-none bg-white shadow-lg">
          <div class="p-8">
            <Typography.Title :level="4" class="mb-6 text-center text-gray-800">
              技术优势
            </Typography.Title>
            <Row :gutter="[24, 16]">
              <Col xs="{24}" sm="{12}" md="{6}">
                <div class="flex items-start rounded-lg bg-gray-50 p-4">
                  <div class="mr-4 mt-1 text-xl text-green-500">
                    <IconifyIcon icon="ant-design:check-circle-outlined" />
                  </div>
                  <div>
                    <Typography.Text strong class="text-gray-800">
                      高精度检测
                    </Typography.Text>
                    <Typography.Paragraph class="mt-1 text-sm text-gray-600">
                      误报率低于5%，有效识别各类密码算法误用问题
                    </Typography.Paragraph>
                  </div>
                </div>
              </Col>
              <Col xs="{24}" sm="{12}" md="{6}">
                <div class="flex items-start rounded-lg bg-gray-50 p-4">
                  <div class="mr-4 mt-1 text-xl text-green-500">
                    <IconifyIcon icon="ant-design:check-circle-outlined" />
                  </div>
                  <div>
                    <Typography.Text strong class="text-gray-800">
                      高性能分析
                    </Typography.Text>
                    <Typography.Paragraph class="mt-1 text-sm text-gray-600">
                      优化的分析算法，支持大型固件文件快速分析
                    </Typography.Paragraph>
                  </div>
                </div>
              </Col>
              <Col xs="{24}" sm="{12}" md="{6}">
                <div class="flex items-start rounded-lg bg-gray-50 p-4">
                  <div class="mr-4 mt-1 text-xl text-green-500">
                    <IconifyIcon icon="ant-design:check-circle-outlined" />
                  </div>
                  <div>
                    <Typography.Text strong class="text-gray-800">
                      全面规范覆盖
                    </Typography.Text>
                    <Typography.Paragraph class="mt-1 text-sm text-gray-600">
                      支持NIST、FIPS等多套密码学安全标准检测
                    </Typography.Paragraph>
                  </div>
                </div>
              </Col>
              <Col xs="{24}" sm="{12}" md="{6}">
                <div class="flex items-start rounded-lg bg-gray-50 p-4">
                  <div class="mr-4 mt-1 text-xl text-green-500">
                    <IconifyIcon icon="ant-design:check-circle-outlined" />
                  </div>
                  <div>
                    <Typography.Text strong class="text-gray-800">
                      开源集成
                    </Typography.Text>
                    <Typography.Paragraph class="mt-1 text-sm text-gray-600">
                      集成CRYPTODY等学术界领先的开源分析工具
                    </Typography.Paragraph>
                  </div>
                </div>
              </Col>
            </Row>
          </div>
        </Card>

        <!-- 应用场景 -->
        <Card
          class="overflow-hidden border-none bg-gradient-to-br from-gray-50 to-gray-100 shadow-lg"
        >
          <div class="p-8">
            <Typography.Title :level="4" class="mb-6 text-center text-gray-800">
              应用场景
            </Typography.Title>
            <div class="space-y-6">
              <div class="rounded-lg bg-white p-6 shadow-sm">
                <IconifyIcon
                  icon="ant-design:laptop-outlined"
                  class="mb-4 text-3xl text-indigo-600"
                />
                <Typography.Title :level="5" class="mb-3 text-gray-800">
                  固件开发安全审计
                </Typography.Title>
                <Typography.Paragraph class="text-gray-600">
                  在固件开发过程中进行安全审计，确保密码算法使用符合最佳实践和安全标准。
                  帮助开发团队在早期发现并修复潜在的密码学安全问题。
                </Typography.Paragraph>
              </div>

              <div class="rounded-lg bg-white p-6 shadow-sm">
                <IconifyIcon
                  icon="ant-design:appstore-outlined"
                  class="mb-4 text-3xl text-indigo-600"
                />
                <Typography.Title :level="5" class="mb-3 text-gray-800">
                  网络设备设备安全评估
                </Typography.Title>
                <Typography.Paragraph class="text-gray-600">
                  对已部署的网络设备设备固件进行安全评估，识别潜在的密码学安全风险。
                  为设备制造商和用户提供全面的安全状态报告。
                </Typography.Paragraph>
              </div>

              <div class="rounded-lg bg-white p-6 shadow-sm">
                <IconifyIcon
                  icon="ant-design:book-outlined"
                  class="mb-4 text-3xl text-indigo-600"
                />
                <Typography.Title :level="5" class="mb-3 text-gray-800">
                  学术研究与教学
                </Typography.Title>
                <Typography.Paragraph class="text-gray-600">
                  为密码学和网络安全研究提供工具支持，用于教学演示和学术研究。
                  帮助研究人员探索网络设备安全领域的新问题和解决方案。
                </Typography.Paragraph>
              </div>
            </div>
          </div>
        </Card>
      </section>

      <!-- 第二栏：上传分析 - 美化版本 -->
      <section
        id="upload-analysis"
        class="animate-fadeIn mb-12"
        v-if="currentNav === 'upload-analysis'"
      >
        <Card class="overflow-hidden border-none bg-white shadow-lg">
          <div class="p-8">
            <Typography.Title
              :level="4"
              class="mb-6 flex items-center text-gray-800"
            >
              <IconifyIcon
                icon="ant-design:cloud-upload-outlined"
                class="mr-3 text-indigo-600"
              />
              固件文件上传
            </Typography.Title>

            <!-- 美化的上传区域 -->
            <div
              ref="uploadArea"
              id="upload-area"
              class="upload-container"
              @dragover.prevent="handleDragOver"
              @dragleave="handleDragLeave"
              @drop.prevent="handleDrop"
            >
              <!-- 隐藏的文件输入框 -->
              <input
                ref="fileInput"
                type="file"
                accept=".so,.bin,.zip,.tar"
                class="file-input"
                @change="handleFileUpload"
              />

              <!-- 上传区域内容 -->
              <div class="upload-content">
                <div class="upload-icon">
                  <IconifyIcon
                    icon="ant-design:cloud-upload-outlined"
                    class="text-5xl"
                  />
                </div>

                <div v-if="file" class="upload-file-selected">
                  <div
                    class="inline-block rounded-lg border border-indigo-200 bg-indigo-50 px-6 py-4"
                  >
                    <div class="mb-2 flex items-center space-x-3">
                      <IconifyIcon
                        icon="ant-design:file-text-outlined"
                        class="text-indigo-600"
                      />
                      <p
                        class="max-w-md break-all text-lg font-medium text-indigo-800"
                      >
                        {{ file.name }}
                      </p>
                    </div>
                    <div class="mb-3 text-sm text-indigo-600">
                      {{ formatFileSize(file.size) }}
                    </div>
                    <div class="flex space-x-3">
                      <Button
                        type="primary"
                        class="border-none bg-indigo-600 hover:bg-indigo-700"
                        @click.prevent="handleAnalyze"
                        :disabled="loading"
                      >
                        <IconifyIcon
                          icon="ant-design:play-circle-outlined"
                          class="mr-1"
                        />
                        开始分析
                      </Button>
                      <Button
                        @click.prevent="file = null"
                        :disabled="loading"
                        class="border-indigo-200 text-indigo-700 hover:bg-indigo-50"
                      >
                        更换文件
                      </Button>
                    </div>
                  </div>
                </div>

                <div v-else class="upload-prompt">
                  <h3 class="mb-4 text-2xl font-bold text-gray-800">
                    固件文件上传
                  </h3>
                  <p class="mx-auto mb-6 max-w-md text-gray-600">
                    点击或拖拽固件文件到此处进行密码规范安全分析
                  </p>
                  <div
                    class="mb-6 inline-block rounded-lg border border-gray-200 bg-gray-50 p-4"
                  >
                    <p class="file-format font-medium text-gray-700">
                      支持格式：.so.bin.zip.tar (网络设备固件文件)
                    </p>
                  </div>
                  <!-- 显式的上传按钮 -->
                  <Button
                    type="primary"
                    size="large"
                    class="border-none bg-gradient-to-r from-indigo-600 to-purple-600 px-8 hover:from-indigo-700 hover:to-purple-700"
                    @click.stop="handleUploadAreaClick"
                  >
                    <IconifyIcon
                      icon="ant-design:upload-outlined"
                      class="mr-2"
                    />
                    选择固件文件
                  </Button>
                </div>
              </div>
            </div>

            <!-- 分析按钮 - 仅在未选择文件时显示 -->
            <div class="mt-8 text-center" v-if="!file">
              <Button
                type="primary"
                @click.stop="handleUploadAreaClick"
                :disabled="loading"
                size="large"
                class="border-none bg-gray-800 hover:bg-gray-900"
              >
                <IconifyIcon icon="ant-design:code-outlined" class="mr-2" />
                开始分析固件
              </Button>
            </div>
          </div>
        </Card>

        <!-- 分析进度 - 美化版本 -->
        <Card
          v-if="loading"
          class="mt-8 overflow-hidden border-none bg-white shadow-lg"
        >
          <div class="p-6">
            <div class="mb-4 flex items-center">
              <IconifyIcon
                icon="ant-design:loading-outlined"
                class="mr-3 animate-spin text-indigo-600"
              />
              <h3 class="text-lg font-medium text-gray-800">
                正在分析固件，请稍候...
              </h3>
            </div>
            <Progress
              :percent="analysisProgress"
              :status="getProgressStatus"
              show-info
              :stroke-width="10"
              class="custom-progress"
              :format="(percent) => `${percent}%`"
            />
            <div class="mt-2 text-center text-sm text-gray-500">
              正在执行深度数据流分析，检测密码算法使用规范...
            </div>
          </div>
        </Card>

        <!-- 分析完成提示 - 美化版本 -->
        <Card
          v-if="analysisComplete && analysisResults.length > 0"
          class="mt-8 border-none bg-gradient-to-br from-green-50 to-emerald-50 shadow-lg"
        >
          <div class="p-8 text-center">
            <div class="mb-6 inline-block rounded-full bg-green-100 p-4">
              <IconifyIcon
                icon="ant-design:check-circle-outlined"
                class="text-5xl text-green-600"
              />
            </div>
            <Typography.Title :level="4" class="mb-2 font-bold text-green-700">
              分析完成！
            </Typography.Title>
            <Typography.Paragraph class="mb-6 text-gray-700">
              发现了
              <span class="font-bold text-indigo-700">{{
                analysisResults.length
              }}</span>
              个潜在的密码规范问题
            </Typography.Paragraph>
            <Button
              type="primary"
              size="large"
              @click="goToResults"
              class="border-none bg-green-600 px-8 hover:bg-green-700"
            >
              <IconifyIcon icon="ant-design:eye-outlined" class="mr-2" />
              查看详细分析结果
            </Button>
          </div>
        </Card>
      </section>

      <!-- 第三栏：历史记录 - 美化版本 -->
      <section
        id="history-records"
        class="animate-fadeIn mb-12"
        v-if="currentNav === 'history-records'"
      >
        <Card class="border-none bg-white shadow-lg">
          <div class="p-8">
            <Typography.Title
              :level="3"
              class="mb-6 flex items-center text-gray-800"
            >
              <IconifyIcon
                icon="ant-design:clock-circle-outlined"
                class="mr-3 text-indigo-600"
              />
              分析历史记录
            </Typography.Title>

            <div
              v-if="historyRecords.length === 0"
              class="rounded-xl bg-gray-50 py-16 text-center"
            >
              <div class="mb-6 inline-block rounded-full bg-gray-100 p-4">
                <IconifyIcon
                  icon="ant-design:clock-circle-outlined"
                  class="text-5xl text-gray-400"
                />
              </div>
              <Typography.Title :level="4" class="mb-3 text-gray-600">
                暂无历史记录
              </Typography.Title>
              <Typography.Paragraph class="mx-auto mb-6 max-w-md text-gray-500">
                上传并分析固件文件后，记录将显示在这里，方便您随时查看和管理
              </Typography.Paragraph>
              <Button
                type="primary"
                size="large"
                @click="handleNavChange('upload-analysis')"
                class="border-none bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
              >
                <IconifyIcon icon="ant-design:upload-outlined" class="mr-2" />
                去上传固件
              </Button>
            </div>

            <div v-else class="space-y-6">
              <Card
                v-for="record in historyRecords"
                :key="record.id"
                class="overflow-hidden border border-gray-100 transition-all duration-300 hover:shadow-xl"
              >
                <div class="flex flex-wrap items-center justify-between p-5">
                  <div class="min-w-[250px] flex-1">
                    <div class="flex items-start">
                      <div class="mr-4 rounded-lg bg-indigo-100 p-3">
                        <IconifyIcon
                          icon="ant-design:file-protect-outlined"
                          class="text-indigo-600"
                        />
                      </div>
                      <div>
                        <Typography.Title
                          :level="5"
                          class="m-0 font-medium text-gray-800"
                        >
                          {{ record.fileName }}
                        </Typography.Title>
                        <div class="mt-1 text-sm text-gray-500">
                          <span class="mr-4 inline-flex items-center">
                            <IconifyIcon
                              icon="ant-design:folder-outlined"
                              class="mr-1"
                            />
                            {{ formatFileSize(record.fileSize) }}
                          </span>
                          <span class="mr-4 inline-flex items-center">
                            <IconifyIcon
                              icon="ant-design:clock-circle-outlined"
                              class="mr-1"
                            />
                            {{ formatDate(record.analysisTime) }}
                          </span>
                          <span
                            v-if="record.results.length > 0"
                            class="inline-flex items-center font-medium text-indigo-600"
                          >
                            <IconifyIcon
                              icon="ant-design:warning-outlined"
                              class="mr-1"
                            />
                            发现 {{ record.results.length }} 个问题
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="mt-4 flex space-x-3 sm:mt-0">
                    <Button
                      type="primary"
                      size="middle"
                      @click="loadFromHistory(record.id)"
                      class="border-none bg-indigo-600 hover:bg-indigo-700"
                    >
                      <IconifyIcon
                        icon="ant-design:eye-outlined"
                        class="mr-1"
                      />
                      查看结果
                    </Button>
                    <Popconfirm
                      title="确定要删除这条历史记录吗？"
                      description="此操作不可撤销"
                      @confirm="deleteHistoryRecord(record.id)"
                      ok-text="确定"
                      cancel-text="取消"
                      class="custom-popconfirm"
                    >
                      <Button danger size="middle" class="hover:bg-red-600">
                        <IconifyIcon
                          icon="ant-design:delete-outlined"
                          class="mr-1"
                        />
                        删除
                      </Button>
                    </Popconfirm>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </Card>
      </section>

      <!-- 第四栏：详细分析结果 - 美化版本 -->
      <section
        id="analysis-results"
        class="animate-fadeIn mb-12"
        v-if="currentNav === 'analysis-results' && analysisResults.length > 0"
      >
        <div class="mb-8 flex flex-wrap items-center justify-between">
          <Typography.Title
            :level="3"
            class="m-0 flex items-center text-gray-800"
          >
            <IconifyIcon
              icon="ant-design:audit-outlined"
              class="mr-3 text-indigo-600"
            />
            详细分析结果
            <Badge
              :count="analysisResults.length"
              class="ml-3"
              :style="{ backgroundColor: '#6366f1' }"
            />
          </Typography.Title>
          <div class="mt-4 flex space-x-3 sm:mt-0">
            <Button
              @click="handleNavChange('upload-analysis')"
              class="border-indigo-200 text-indigo-700 hover:bg-indigo-50"
            >
              <IconifyIcon icon="ant-design:upload-outlined" class="mr-1" />
              上传新固件
            </Button>
            <Button
              @click="handleNavChange('history-records')"
              class="border-none bg-gray-100 text-gray-700 hover:bg-gray-200"
            >
              <IconifyIcon icon="ant-design:history-outlined" class="mr-1" />
              查看历史
            </Button>
            <Button
              @click="exportPDF"
              type="primary"
              class="border-none bg-green-600 hover:bg-green-700"
            >
              <IconifyIcon icon="ant-design:download-outlined" class="mr-1" />
              导出结果
            </Button>
          </div>
        </div>

        <!-- 分析结果统计卡片 -->
        <Row :gutter="[24, 24]" class="mb-8">
          <Col xs="{24}" md="{8}">
            <Card class="border-none bg-white shadow-md">
              <div class="p-6 text-center">
                <Typography.Title :level="3" class="m-0 text-indigo-600">
                  {{ analysisResults.length }}
                </Typography.Title>
                <Typography.Text class="text-gray-600">
                  发现问题总数
                </Typography.Text>
              </div>
            </Card>
          </Col>
          <Col xs="{24}" md="{8}">
            <Card class="border-none bg-white shadow-md">
              <div class="p-6 text-center">
                <Typography.Title :level="3" class="m-0 text-red-600">
                  {{
                    analysisResults.filter((r) => r.severity === 'high').length
                  }}
                </Typography.Title>
                <Typography.Text class="text-gray-600">
                  高危问题
                </Typography.Text>
              </div>
            </Card>
          </Col>
          <Col xs="{24}" md="{8}">
            <Card class="border-none bg-white shadow-md">
              <div class="p-6 text-center">
                <Typography.Title :level="3" class="m-0 text-orange-600">
                  {{
                    analysisResults.filter((r) => r.severity === 'medium')
                      .length
                  }}
                </Typography.Title>
                <Typography.Text class="text-gray-600">
                  中危问题
                </Typography.Text>
              </div>
            </Card>
          </Col>
        </Row>

        <!-- 分析结果列表 -->
        <Card class="mb-8 border-none bg-white shadow-lg">
          <div class="p-6">
            <Typography.Title :level="4" class="mb-6 text-gray-800">
              问题详情
            </Typography.Title>
            <List
              :data-source="analysisResults"
              class="space-y-5"
              :pagination="{ pageSize: 10 }"
            >
              <template #renderItem="{ item }">
                <List.Item>
                  <Card
                    hoverable
                    class="border-none shadow-md transition-shadow hover:shadow-lg"
                    :class="{
                      'border-l-4 border-red-500': item.severity === 'high',
                      'border-l-4 border-orange-500':
                        item.severity === 'medium',
                      'border-l-4 border-blue-500': item.severity === 'low',
                    }"
                  >
                    <div
                      class="mb-3 flex flex-wrap items-start justify-between"
                    >
                      <div class="min-w-[250px] flex-1">
                        <div class="mb-2 flex items-center space-x-3">
                          <span class="text-lg font-bold text-gray-800">{{
                            item.functionName
                          }}</span>
                          <Tag :color="getSeverityColor(item.severity)">
                            {{ item.issueType }}
                          </Tag>
                        </div>
                        <p
                          v-if="item.parameters"
                          class="overflow-x-auto rounded bg-gray-50 p-2 font-mono text-sm text-gray-500"
                        >
                          {{ item.parameters }}
                        </p>
                      </div>
                      <Tag
                        :color="getSeverityColor(item.severity)"
                        class="font-medium"
                      >
                        {{
                          item.severity === 'high'
                            ? '高危'
                            : item.severity === 'medium'
                              ? '中危'
                              : '低危'
                        }}
                      </Tag>
                    </div>
                    <p class="mb-2 text-gray-700">{{ item.description }}</p>
                    <div v-if="item.codeSnippet" class="mt-3">
                      <Typography.Text
                        type="secondary"
                        class="mb-2 block text-sm"
                      >
                        代码片段：
                      </Typography.Text>
                      <pre
                        class="overflow-x-auto rounded bg-gray-50 p-3 text-sm text-gray-700"
                        >{{ item.codeSnippet }}</pre>
                    </div>
                  </Card>
                </List.Item>
              </template>
            </List>
          </div>
        </Card>

        <!-- 分析结果可视化区域 -->
        <div v-if="treeData.length > 0">
          <!-- 可视化分析标题 -->
          <Typography.Title
            :level="4"
            class="mb-6 flex items-center text-gray-800"
          >
            <IconifyIcon
              icon="ant-design:line-chart-outlined"
              class="mr-3 text-indigo-600"
            />
            可视化分析
          </Typography.Title>

          <!-- 树状分析结果图 -->
          <div class="mb-8">
            <Card title="详细调用关系树" class="border-none bg-white shadow-lg">
              <div class="h-[500px] overflow-auto p-4">
                <Tree
                  :tree-data="treeData"
                  :default-expand-all="true"
                  :tree-line="true"
                  :show-icon="true"
                  class="multi-tree-style"
                >
                  <template #title="item">
                    <div class="tree-node-content flex items-center py-1">
                      <span
                        v-if="item.isLeaf"
                        class="node-icon mr-2 text-indigo-500"
                        >📄</span>
                      <span class="node-title flex-1 truncate text-gray-800">{{
                        item.title
                      }}</span>
                    </div>
                  </template>
                </Tree>
              </div>
            </Card>
          </div>

          <!-- ECharts关系图展示区域 -->
          <div>
            <Card
              title="函数调用关系可视化"
              class="border-none bg-white shadow-lg"
            >
              <div class="p-4">
                <EchartsUI ref="graphRef" height="500px" width="100%" />
              </div>
            </Card>
          </div>
        </div>
      </section>
    </Layout.Content>

    <!-- 页脚 - 美化版本 -->
    <Layout.Footer
      class="mt-16 border-t border-gray-200 bg-white py-12 text-gray-800"
    >
      <div class="container mx-auto px-4">
        <div
          class="mb-8 flex flex-col items-center justify-between md:flex-row"
        >
          <div class="mb-6 flex items-center space-x-3 md:mb-0">
            <IconifyIcon
              icon="ant-design:security-scan-outlined"
              class="text-2xl text-indigo-600"
            />
            <Typography.Title :level="4" class="m-0 font-light text-gray-800">
              <span class="font-bold text-gray-900">密码算法安全分析</span>
            </Typography.Title>
          </div>
          <div class="flex space-x-6">
            <a
              href="#"
              class="text-gray-600 transition-colors hover:text-gray-900"
            >
              <IconifyIcon icon="ant-design:github-outlined" class="text-xl" />
            </a>
            <a
              href="#"
              class="text-gray-600 transition-colors hover:text-gray-900"
            >
              <IconifyIcon icon="ant-design:book-outlined" class="text-xl" />
            </a>
            <a
              href="#"
              class="text-gray-600 transition-colors hover:text-gray-900"
            >
              <IconifyIcon
                icon="ant-design:question-circle-outlined"
                class="text-xl"
              />
            </a>
          </div>
        </div>
        <Divider class="my-6 bg-gray-300 opacity-80" />
        <!-- 已删除底栏版权信息 -->
      </div>
    </Layout.Footer>
  </div>
</template>

<style scoped>
@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-10px);
  }
}

/* 添加动画效果 */
@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgb(99 102 241 / 40%);
  }

  70% {
    box-shadow: 0 0 0 15px rgb(99 102 241 / 0%);
  }

  100% {
    box-shadow: 0 0 0 0 rgb(99 102 241 / 0%);
  }
}

@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(20px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式调整 */
@media (max-width: 768px) {
  .upload-container {
    min-height: 250px;
  }

  .upload-prompt h3 {
    font-size: 20px;
  }

  .upload-content {
    padding: 20px 10px;
  }

  .upload-icon {
    font-size: 1.875rem !important;
  }

  .multi-tree-style {
    padding: 12px;
  }
}

@media (max-width: 480px) {
  .upload-container {
    min-height: 200px;
  }

  .upload-prompt h3 {
    font-size: 18px;
  }

  .upload-icon {
    font-size: 1.5rem !important;
  }
}

.firmware-analysis-page {
  font-family:
    -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue',
    Arial, sans-serif;
}

/* 确保上传区域美观的核心样式 */
.upload-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 300px;
  margin: 0 auto;
  overflow: hidden;
  cursor: pointer;
  background-color: #f8fafc;
  border: 3px dashed #6366f1;
  border-radius: 16px;
  transition: all 0.3s ease;
}

.upload-container:hover {
  background-color: #f5f3ff;
  border-color: #4f46e5;
  box-shadow: 0 12px 24px rgb(99 102 241 / 20%);
  transform: translateY(-2px);
}

.upload-area-dragging {
  background-color: #ede9fe;
  border-color: #4338ca;
  box-shadow: 0 12px 24px rgb(99 102 241 / 30%);
  transform: scale(1.01);
}

/* 隐藏的文件输入框 */
.file-input {
  display: none;
}

/* 上传区域内容样式 */
.upload-content {
  width: 100%;
  padding: 30px;
  text-align: center;
}

.upload-icon {
  margin-bottom: 24px;
  color: #6366f1;
  animation: float 3s ease-in-out infinite;
}

.upload-prompt h3 {
  margin-bottom: 16px;
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  background: linear-gradient(to right, #4f46e5, #8b5cf6);
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.upload-file-selected {
  color: #1e293b;
  text-align: center;
}

.upload-file-selected p {
  font-size: 16px;
  font-weight: 500;
  color: #1e293b;
  overflow-wrap: break-word;
}

/* 美化的进度条样式 */
.custom-progress .ant-progress-bg {
  background: linear-gradient(to right, #6366f1, #8b5cf6);
  border-radius: 10px;
  transition: width 0.6s ease;
}

.custom-progress .ant-progress-text {
  font-weight: 600;
  color: #4f46e5;
}

.upload-container::after {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 60px;
  height: 60px;
  margin: -30px 0 0 -30px;
  pointer-events: none;
  content: '';
  border-radius: 50%;
  opacity: 0;
}

.upload-container:hover::after {
  animation: pulse 2s infinite;
}

.upload-prompt p {
  margin: 8px 0;
  font-size: 16px;
  line-height: 1.6;
  color: #64748b;
}

.file-format {
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
}

/* 美化的Popconfirm样式 */
:deep(.custom-popconfirm .ant-popover-inner) {
  border: none;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgb(0 0 0 / 10%);
}

:deep(.custom-popconfirm .ant-popover-inner-content) {
  padding: 20px;
}

/* 其他基础样式 */
.animate-fadeIn {
  animation: fadeIn 0.6s ease forwards;
}

.multi-tree-style {
  height: 100%;
  padding: 24px;
  background-color: #fafafa;
  border-radius: 12px;
}

.tree-node-content {
  transition: all 0.2s ease;
}

.tree-node-content:hover {
  padding: 4px 8px;
  margin: -4px -8px;
  color: #6366f1;
  background-color: #f5f3ff;
  border-radius: 6px;
}

.node-title {
  font-size: 14px;
  line-height: 1.5;
}

/* 滚动条美化 */
:deep(.ant-tree::-webkit-scrollbar) {
  width: 8px;
}

:deep(.ant-tree::-webkit-scrollbar-track) {
  background: #f1f1f1;
  border-radius: 4px;
}

:deep(.ant-tree::-webkit-scrollbar-thumb) {
  background: #cbd5e1;
  border-radius: 4px;
}

:deep(.ant-tree::-webkit-scrollbar-thumb:hover) {
  background: #94a3b8;
}

/* 按钮悬停效果增强 */
:deep(.ant-btn-primary:hover) {
  box-shadow: 0 4px 12px rgb(99 102 241 / 30%);
  transform: translateY(-1px);
  transition: all 0.3s ease;
}

:deep(.ant-card) {
  transition: all 0.3s ease;
}

:deep(.ant-card:hover) {
  transform: translateY(-2px);
}

/* 全局样式 */
</style>
