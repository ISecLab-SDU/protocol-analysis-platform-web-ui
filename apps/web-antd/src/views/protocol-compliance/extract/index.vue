<script lang="ts" setup>
import type { TableColumnType, UploadFile, UploadProps } from 'ant-design-vue';
import { computed, h, onMounted, reactive, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import {
  Button,
  Card,
  Empty,
  Form,
  FormItem,
  Input,
  message,
  Select,
  Space,
  Spin,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
  Progress,
  AutoComplete,
  Popconfirm,
  Divider,
} from 'ant-design-vue';
import type { ProtocolExtractRuleItem } from '@/api/protocol-compliance';
import { runProtocolExtract } from '@/api/protocol-compliance';

type RuleItem = ProtocolExtractRuleItem & {
  group?: string | null;
  msgType?: string; // 存储消息类型（如 CONNECT）
};

type HistoryItem = {
  id: string; // 唯一ID，用于删除定位
  analysisTime: string;
  categories: string[];
  protocol: string;
  version?: string;
  ruleCount: number;
  rules: RuleItem[];
  storeDir?: string;
  resultPath?: string;
};

const HISTORY_KEY = 'protocol_analysis_history';

// 全局状态
const activeMenuKey = ref('analyze');
const isAnalyzing = ref(false);
const isLoadingResult = ref(false);
const isUploadingResult = ref(false);
const analysisCompleted = ref(false);
const stagedResults = ref<RuleItem[]>([]);
const rfcFileList = ref<UploadFile[]>([]);
const resultFileList = ref<UploadFile[]>([]);
const selectedResultFile = ref<File | null>(null);
const selectedFile = ref<File | null>(null); // 协议文档上传文件对象
const formData = reactive({
  protocol: '',
  version: '',
  apiKey: '',
  filterHeadings: false,
});
const currentPage = ref(1);
const pageSize = ref(10);
const totalItems = ref(0);
const historyData = ref<HistoryItem[]>([]);
const lastResultMeta = ref<{ storeDir?: string; resultPath?: string } | null>(null);
const analysisProgress = ref(0);
const progressText = ref('准备分析...');
const selectedGroup = ref<null | string>(null);

// 组件别名
const TypographyParagraph = Typography.Paragraph;
const TypographyText = Typography.Text;

// 规则分类列表
const ruleCategories = [
  '安全',
  '性能',
  '兼容',
  '基础',
  '高级',
  '加密',
  '认证',
  '会话管理',
  '可靠性',
  '优化',
  '错误处理',
  '日志',
  '扩展性',
  'QoS',
  '协议约束',
];

// 分隔符正则
const SPLIT_PATTERN = /[,;/]|\s+(?:or|and)\s+/gi;

// 生成唯一ID
function generateUniqueId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
}

// 标准化协议名称
function normalizeProtocolName(input: string) {
  return input
    .trim()
    .replaceAll(/\s+/g, '')
    .replaceAll(/[^\w./-]/g, '')
    .toLowerCase();
}

// 标准化版本名称
function normalizeVersionName(input: string) {
  return normalizeProtocolName(input);
}

// 随机生成分类
function randomCategories(): string[] {
  const shuffled = [...ruleCategories].sort(() => Math.random() - 0.5);
  const count = Math.floor(Math.random() * 2) + 3;
  return shuffled.slice(0, count);
}

// 转换为数组
function toArray(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item ?? '').trim())
      .filter((item) => Boolean(item));
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return [];
    const segments = trimmed.split(SPLIT_PATTERN).map(s => s.trim()).filter(Boolean);
    return [...new Set(segments)];
  }
  return [];
}

// 标准化规则项
function normalizeRuleItem(raw: any, msgType?: string): RuleItem {
  const ruleText = typeof raw?.rule === 'string' ? raw.rule.trim() : String(raw?.rule ?? '').trim();
  return {
    rule: ruleText,
    group: raw?.group ?? null,
    msgType: msgType || raw?.req_type?.[0] || '',
    req_type: toArray(raw?.req_type),
    req_fields: toArray(raw?.req_fields),
    res_type: toArray(raw?.res_type),
    res_fields: toArray(raw?.res_fields),
  };
}

// 协议文档上传前校验
const beforeUploadRFC: UploadProps['beforeUpload'] = (file) => {
  const allowedTypes = ['text/html', 'application/pdf', 'text/plain', 'application/json'];
  const isAllowed = allowedTypes.includes(file.type);
  const isAllowedExt = ['.html', '.pdf', '.txt', '.json'].some((ext) =>
    file.name.toLowerCase().endsWith(ext),
  );
  if (!isAllowed && !isAllowedExt) {
    message.error('仅支持上传 HTML、PDF、TXT、JSON 格式的协议文档');
    return false;
  }
  const originalFile = (file as UploadFile & { originFileObj?: File }).originFileObj || (file as unknown as File);
  selectedFile.value = originalFile;
  rfcFileList.value = [file];
  return false;
};

// 结果文件上传前校验
const beforeUploadResultFile: UploadProps['beforeUpload'] = (file) => {
  const isJson = file.type === 'application/json' || file.name.toLowerCase().endsWith('.json');
  if (!isJson) {
    message.error('请上传 JSON 格式的分析结果文件');
    return false;
  }
  const originalFile = (file as UploadFile & { originFileObj?: File }).originFileObj || (file as unknown as File);
  selectedResultFile.value = originalFile;
  resultFileList.value = [file];
  return false;
};

// 移除协议文档
const removeRFC: UploadProps['onRemove'] = () => {
  selectedFile.value = null;
  rfcFileList.value = [];
  return true;
};

// 移除结果文件
const removeResultFile: UploadProps['onRemove'] = () => {
  selectedResultFile.value = null;
  resultFileList.value = [];
  return true;
};

// 保存历史记录到本地存储
function saveHistoryToStorage() {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(historyData.value));
}

// 加载历史记录
function loadHistoryFromStorage() {
  try {
    const saved = localStorage.getItem(HISTORY_KEY);
    const parsed = saved ? JSON.parse(saved) : [];
    if (!Array.isArray(parsed)) {
      historyData.value = [];
      return;
    }
    historyData.value = parsed
      .map((item: any) => {
        const rules = Array.isArray(item?.rules)
          ? item.rules
              .map((rule: any) => normalizeRuleItem(rule, rule.msgType))
              .filter((rule: RuleItem) => rule.rule)
          : [];
        return {
          id: item.id || generateUniqueId(), // 为旧数据补全ID
          analysisTime: String(item?.analysisTime ?? ''),
          categories: Array.isArray(item?.categories) ? item.categories : [],
          protocol: String(item?.protocol ?? ''),
          version: item?.version ? String(item.version) : undefined,
          ruleCount: typeof item?.ruleCount === 'number' ? item.ruleCount : rules.length,
          rules,
          storeDir: item?.storeDir ? String(item.storeDir) : undefined,
          resultPath: item?.resultPath ? String(item.resultPath) : undefined,
        } as HistoryItem;
      })
      .filter((item: HistoryItem) => item.protocol && item.rules.length > 0);
  } catch {
    historyData.value = [];
  }
}

// 单条删除历史记录
function deleteHistoryItem(id: string) {
  historyData.value = historyData.value.filter(item => item.id !== id);
  saveHistoryToStorage();
  message.success('历史记录删除成功');
}

// 清空全部历史记录
function clearAllHistory() {
  historyData.value = [];
  localStorage.removeItem(HISTORY_KEY);
  message.success('全部历史记录已清空');
}

// 开始分析协议文档
async function startAnalysis() {
  const uploadFile = selectedFile.value;
  const protocol = formData.protocol.trim();
  const version = formData.version.trim();
  const apiKey = formData.apiKey.trim();

  if (!uploadFile) {
    message.warning('请先上传协议文档 (HTML/PDF/TXT/JSON)');
    return;
  }
  if (!protocol) {
    message.warning('请输入或选择协议类型');
    return;
  }
  if (!version) {
    message.warning('请输入协议版本');
    return;
  }
  if (!apiKey) {
    message.warning('请输入 DeepSeek API 密钥');
    return;
  }

  isAnalyzing.value = true;
  analysisCompleted.value = false;
  stagedResults.value = [];
  selectedGroup.value = null;
  currentPage.value = 1;
  lastResultMeta.value = null;
  analysisProgress.value = 0;
  progressText.value = '准备分析...';

  const progressInterval = setInterval(() => {
    if (analysisProgress.value < 90) {
      analysisProgress.value += Math.floor(Math.random() * 10) + 5;
      if (analysisProgress.value > 30 && analysisProgress.value < 60) {
        progressText.value = '正在提取协议规则...';
      } else if (analysisProgress.value >= 60) {
        progressText.value = '正在整理规则数据...';
      }
    }
  }, 500);

  try {
    const response = await runProtocolExtract({
      apiKey,
      protocol,
      version,
      htmlFile: uploadFile,
      filterHeadings: formData.filterHeadings,
    });

    clearInterval(progressInterval);
    analysisProgress.value = 100;
    progressText.value = '分析完成！';

    const rulesData = response.rules || response.data?.rules || [];
    const rules = Array.isArray(rulesData)
      ? rulesData.map(normalizeRuleItem).filter((rule) => rule.rule)
      : [];

    if (rules.length === 0) {
      throw new Error('分析流程完成，但未生成任何规则');
    }

    stagedResults.value = rules;
    totalItems.value = rules.length;
    analysisCompleted.value = true;
    lastResultMeta.value = {
      storeDir: response.storeDir || response.data?.storeDir || `project_store/${normalizeProtocolName(protocol)}_${normalizeVersionName(version)}`,
      resultPath: response.resultPath || response.data?.resultPath || `project_store/${normalizeProtocolName(protocol)}_${normalizeVersionName(version)}/rules.json`,
    };

    addToHistory(rules, protocol, version);
    message.success(`分析成功，提取到 ${rules.length} 条规则`);
  } catch (error: any) {
    clearInterval(progressInterval);
    analysisProgress.value = 0;
    progressText.value = '分析失败';

    const details = error?.response?.data?.details;
    let detailMessage = error?.response?.data?.message || error?.message || '未知错误';
    if (details) {
      if (typeof details === 'string') {
        detailMessage = details;
      } else if (typeof details === 'object') {
        if (typeof details.message === 'string' && details.message.trim()) {
          detailMessage = details.message;
        } else if (Array.isArray(details.stderr) && details.stderr.length) {
          detailMessage = details.stderr.join('\n');
        } else if (Array.isArray(details.stdout) && details.stdout.length) {
          detailMessage = details.stdout.join('\n');
        } else {
          detailMessage = JSON.stringify(details);
        }
      }
    }
    console.error('分析失败', error);
    message.error(`分析失败: ${detailMessage}`);
  } finally {
    isAnalyzing.value = false;
  }
}

// 导入结果文件
async function uploadAndSaveResult() {
  const protocol = formData.protocol.trim();
  const version = formData.version.trim();
  const resultFile = selectedResultFile.value;

  if (!resultFile) {
    message.warning('请先上传 JSON 格式的分析结果文件');
    return;
  }
  if (!protocol) {
    message.warning('请输入或选择协议类型');
    return;
  }
  if (!version) {
    message.warning('请输入协议版本');
    return;
  }

  isUploadingResult.value = true;
  analysisCompleted.value = false;
  stagedResults.value = [];
  selectedGroup.value = null;
  currentPage.value = 1;
  lastResultMeta.value = null;

  try {
    // 读取文件
    const reader = new FileReader();
    const fileContent = await new Promise<string>((resolve, reject) => {
      reader.onload = (e) => {
        const result = e.target?.result;
        if (typeof result === 'string') {
          resolve(result);
        } else {
          reject(new Error('文件读取结果不是字符串'));
        }
      };
      reader.onerror = (err) => reject(new Error(`文件读取失败：${err.message}`));
      reader.onabort = () => reject(new Error('文件读取被中止'));
      reader.readAsText(resultFile);
    });

    // 解析JSON
    let rawData: any;
    try {
      rawData = JSON.parse(fileContent);
    } catch (jsonErr) {
      const cleanedText = fileContent.replace(/^\uFEFF/, '').trim();
      try {
        rawData = JSON.parse(cleanedText);
      } catch (err) {
        throw new Error(`JSON格式错误：${(err as Error).message}`);
      }
    }

    // 处理3种格式
    let rules: RuleItem[] = [];
    if (Array.isArray(rawData)) {
      rules = rawData.map(normalizeRuleItem).filter((rule) => rule.rule);
      console.log('识别到直接数组格式，共解析', rules.length, '条规则');
    } else if (typeof rawData === 'object' && Array.isArray(rawData.rules)) {
      rules = rawData.rules.map(normalizeRuleItem).filter((rule) => rule.rule);
      console.log('识别到 rules 嵌套格式，共解析', rules.length, '条规则');
    } else if (typeof rawData === 'object' && rawData !== null) {
      Object.entries(rawData).forEach(([msgType, ruleArray]) => {
        if (Array.isArray(ruleArray)) {
          const groupRules = ruleArray
            .map((rawRule: any) => normalizeRuleItem(rawRule, msgType))
            .filter((rule: RuleItem) => rule.rule);
          rules = [...rules, ...groupRules];
        }
      });
      console.log('识别到按消息类型分组格式，共解析', rules.length, '条规则');
    }

    if (rules.length === 0) {
      throw new Error('上传的文件中未包含有效规则（请检查JSON格式是否正确）');
    }

    // 显示结果
    stagedResults.value = rules;
    totalItems.value = rules.length;
    analysisCompleted.value = true;
    lastResultMeta.value = {
      storeDir: `uploaded_results/${normalizeProtocolName(protocol)}_${normalizeVersionName(version)}`,
      resultPath: `${normalizeProtocolName(protocol)}_${normalizeVersionName(version)}_uploaded.json`,
    };

    // 去重添加历史
    const isDuplicate = historyData.value.some(
      item => item.protocol === protocol && item.version === version
    );
    if (!isDuplicate) {
      addToHistory(rules, protocol, version);
    }

    // 清空上传状态
    resultFileList.value = [];
    selectedResultFile.value = null;

    message.success(`成功导入 ${protocol} ${version} 的分析结果，共 ${rules.length} 条规则（已存入历史记录）`);
  } catch (error: any) {
    let errorMsg = '';
    if (error.message.includes('JSON格式错误')) {
      errorMsg = `JSON文件格式错误，请检查文件内容`;
    } else if (error.message.includes('未包含有效规则')) {
      errorMsg = `上传的文件中未找到有效规则（支持格式：直接数组、{rules:[]}、{消息类型:[]}）`;
    } else if (error.message.includes('文件读取')) {
      errorMsg = `文件读取失败：${error.message}`;
    } else {
      errorMsg = `导入失败：${error.message}`;
    }
    message.error(errorMsg);
    console.error('导入分析结果失败：', error);
  } finally {
    isUploadingResult.value = false;
  }
}

// 加载本地结果文件
async function loadExistingResult() {
  const protocol = formData.protocol.trim();
  const version = formData.version.trim();

  if (!protocol) {
    message.warning('请输入或选择协议类型');
    return;
  }
  if (!version) {
    message.warning('请输入协议版本');
    return;
  }

  isLoadingResult.value = true;
  analysisCompleted.value = false;
  stagedResults.value = [];
  selectedGroup.value = null;
  currentPage.value = 1;
  lastResultMeta.value = null;

  try {
    const normalizedProtocol = normalizeProtocolName(protocol);
    const normalizedVersion = normalizeVersionName(version);

    const possiblePaths = [
      `project_store/${normalizedProtocol}_${normalizedVersion}/rules.json`,
      `project_store/${normalizedProtocol}/${normalizedVersion}/rules.json`,
      `results/${normalizedProtocol}_${normalizedVersion}.json`,
      `static/results/${normalizedProtocol}_${normalizedVersion}.json`,
      `${normalizedProtocol}_${normalizedVersion}_rules.json`
    ];

    let rawResponseText = '';
    let successPath = '';
    let response: Response | null = null;

    // 尝试所有路径
    for (const path of possiblePaths) {
      try {
        response = await fetch(path);
        if (response.ok) {
          successPath = path;
          rawResponseText = await response.text();
          break;
        }
      } catch (err) {
        continue;
      }
    }

    if (!successPath) {
      throw new Error(`未找到 ${protocol} ${version} 的结果文件`);
    }

    // 解析JSON
    let rawData: any;
    try {
      rawData = JSON.parse(rawResponseText);
    } catch (jsonErr) {
      const cleanedText = rawResponseText.replace(/^\uFEFF/, '').trim();
      try {
        rawData = JSON.parse(cleanedText);
      } catch (err) {
        throw new Error(`JSON格式错误：${(err as Error).message}`);
      }
    }

    // 处理3种格式
    let rules: RuleItem[] = [];
    if (Array.isArray(rawData)) {
      rules = rawData.map(normalizeRuleItem).filter((rule) => rule.rule);
    } else if (typeof rawData === 'object' && Array.isArray(rawData.rules)) {
      rules = rawData.rules.map(normalizeRuleItem).filter((rule) => rule.rule);
    } else if (typeof rawData === 'object' && rawData !== null) {
      Object.entries(rawData).forEach(([msgType, ruleArray]) => {
        if (Array.isArray(ruleArray)) {
          const groupRules = ruleArray
            .map((rawRule: any) => normalizeRuleItem(rawRule, msgType))
            .filter((rule: RuleItem) => rule.rule);
          rules = [...rules, ...groupRules];
        }
      });
    }

    if (rules.length === 0) {
      throw new Error(`文件 ${successPath} 中未包含有效规则`);
    }

    // 显示结果
    stagedResults.value = rules;
    totalItems.value = rules.length;
    analysisCompleted.value = true;
    lastResultMeta.value = {
      storeDir: successPath.substring(0, successPath.lastIndexOf('/')),
      resultPath: successPath,
    };

    // 去重添加历史
    const isDuplicate = historyData.value.some(
      item => item.protocol === protocol && item.version === version
    );
    if (!isDuplicate) {
      addToHistory(rules, protocol, version);
    }

    message.success(`成功加载 ${protocol} ${version} 的本地结果，共 ${rules.length} 条规则`);
  } catch (error: any) {
    let errorMsg = '';
    if (error.message.includes('未找到')) {
      errorMsg = `未找到 ${protocol} ${version} 的分析结果，请先上传文件或导入结果`;
    } else if (error.message.includes('未包含有效规则')) {
      errorMsg = `结果文件中未找到有效规则`;
    } else if (error.message.includes('JSON格式错误')) {
      errorMsg = `JSON文件格式错误，请检查文件内容`;
    } else {
      errorMsg = `加载失败：${error.message}`;
    }
    message.error(errorMsg);
    console.error('加载本地结果失败：', error);
  } finally {
    isLoadingResult.value = false;
  }
}

// 添加到历史记录
function addToHistory(rules: RuleItem[], protocol: string, version: string) {
  const now = new Date().toLocaleString();
  const newHistory: HistoryItem = {
    id: generateUniqueId(),
    protocol,
    version,
    ruleCount: rules.length,
    analysisTime: now,
    categories: randomCategories(),
    rules,
    storeDir: lastResultMeta.value?.storeDir,
    resultPath: lastResultMeta.value?.resultPath,
  };

  // 去重
  historyData.value = historyData.value.filter(
    item => !(item.protocol === protocol && item.version === version)
  );
  historyData.value.unshift(newHistory);
  historyData.value = historyData.value.slice(0, 20); // 最多保留20条
  saveHistoryToStorage();
}

// 下载结果
function downloadAnalysisResult() {
  if (!analysisCompleted.value || stagedResults.value.length === 0) {
    message.warning('暂无分析结果可下载');
    return;
  }
  const normalizedProtocol = normalizeProtocolName(formData.protocol || 'protocol');
  const normalizedVersion = normalizeVersionName(formData.version || 'v');
  const fileName = `ruleConfig_${normalizedProtocol}_${normalizedVersion}.json`;
  
  // 按消息类型分组
  const groupedRules: Record<string, RuleItem[]> = {};
  stagedResults.value.forEach(rule => {
    const msgType = rule.msgType || 'default';
    if (!groupedRules[msgType]) {
      groupedRules[msgType] = [];
    }
    const { msgType: _, ...ruleWithoutMsgType } = rule;
    groupedRules[msgType].push(ruleWithoutMsgType);
  });
  
  const jsonStr = JSON.stringify(groupedRules, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
  message.success(`分析结果已下载：${fileName}`);
}

// 从历史记录打开
function openFromHistory(item: HistoryItem) {
  formData.protocol = item.protocol;
  formData.version = item.version ?? '';
  stagedResults.value = item.rules ?? [];
  totalItems.value = stagedResults.value.length;
  analysisCompleted.value = stagedResults.value.length > 0;
  selectedGroup.value = null;
  currentPage.value = 1;
  activeMenuKey.value = 'analyze';
  lastResultMeta.value = {
    storeDir: item.storeDir,
    resultPath: item.resultPath,
  };
}

// 计算属性：分组列表（按消息类型）
const groupList = computed(() => {
  const groups = new Set(
    stagedResults.value.map((r) => r.msgType).filter((group): group is string => Boolean(group)),
  );
  return [...groups];
});

// 计算属性：筛选后的结果
const filteredResults = computed(() => {
  if (!selectedGroup.value) return stagedResults.value;
  return stagedResults.value.filter((r) => r.msgType === selectedGroup.value);
});

// 计算属性：当前页数据
const currentPageData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredResults.value.slice(start, start + pageSize.value);
});

// 渲染标签列表
const renderTagList = (value: unknown, color: string) => {
  const items = toArray(value);
  if (!items.length) {
    return h('span', { class: 'table-empty' }, '-');
  }
  return h(
    Space,
    { size: 'small', wrap: true },
    items.map((item, index) =>
      h(
        Tag,
        {
          color: color,
          key: `tag-${index}`,
          style: { margin: '2px' }
        },
        () => item.trim()
      )
    )
  );
};

// 结果表格列定义
const columns: TableColumnType<RuleItem>[] = [
  {
    title: '序号',
    key: 'index',
    width: 60,
    customRender: ({ index }) =>
      (currentPage.value - 1) * pageSize.value + index + 1,
  },
  {
    title: '消息类型',
    dataIndex: 'msgType',
    key: 'msgType',
    width: 120,
    customRender: ({ text }) => {
      const validText = String(text ?? '未知').trim();
      return h(Tag, { color: 'blue' }, validText);
    },
  },
  {
    title: '规则描述',
    dataIndex: 'rule',
    key: 'rule',
    width: 420,
    customRender: ({ text }) => {
      const validText = String(text ?? '').trim();
      return h('div', { 
        style: 'white-space: pre-wrap; word-break: break-word; line-height: 1.5;' 
      }, validText);
    },
  },
  {
    title: '协议消息类型',
    dataIndex: 'req_type',
    key: 'req_type',
    width: 180,
    customRender: ({ text }) => renderTagList(text, 'purple'),
  },
  {
    title: '请求字段',
    dataIndex: 'req_fields',
    key: 'req_fields',
    width: 220,
    customRender: ({ text }) => renderTagList(text, 'blue'),
  },
  {
    title: '响应类型',
    dataIndex: 'res_type',
    key: 'res_type',
    width: 180,
    customRender: ({ text }) => renderTagList(text, 'orange'),
  },
  {
    title: '响应字段',
    dataIndex: 'res_fields',
    key: 'res_fields',
    width: 220,
    customRender: ({ text }) => renderTagList(text, 'green'),
  },
];

// 表格分页变化
function handleTableChange(pagination: any) {
  currentPage.value = pagination.current;
  pageSize.value = pagination.pageSize;
}

// 历史记录表格列定义
const historyColumns = computed<TableColumnType<HistoryItem>[]>(() => [
  {
    title: '协议',
    dataIndex: 'protocol',
    key: 'protocol',
    customRender: ({ record }) => {
      const item = record as HistoryItem;
      const protocolLabel = item.protocol ?? '';
      const versionLabel = item.version ? `(${item.version})` : '';
      return h(Tag, { color: 'cyan' }, `${protocolLabel}${versionLabel}`);
    },
  },
  {
    title: '规则数量',
    dataIndex: 'ruleCount',
    key: 'ruleCount',
    customRender: ({ text }) => h(Tag, { color: 'green' }, String(text ?? '0')),
  },
  {
    title: '分析时间',
    dataIndex: 'analysisTime',
    key: 'analysisTime',
  },
  {
    title: '操作',
    key: 'action',
    width: 120,
    align: 'center',
    customRender: ({ record }) => {
      const item = record as HistoryItem;
      return h(
        Popconfirm,
        {
          title: '确定要删除这条记录吗？',
          okText: '确定',
          cancelText: '取消',
          onConfirm: () => deleteHistoryItem(item.id),
          placement: 'top',
        },
        {
          default: () => h(Button, { type: 'text', danger: true, size: 'small' }, '删除'),
        }
      );
    },
  },
]);

// 挂载时加载历史记录
onMounted(() => {
  loadHistoryFromStorage();
});
</script>

<template>
  <Page title="协议规则提取">
    <div class="protocol-extract">
      <Tabs v-model:active-key="activeMenuKey" class="extract-tabs">
        <!-- 规则提取标签页 -->
        <Tabs.TabPane key="analyze" tab="规则提取">
          <div class="analyze-layout">
            <Card class="form-card">
              <template #title>
                <Space>
                  <IconifyIcon icon="ant-design:cloud-upload-outlined" class="text-lg" />
                  <span>协议分析 / 结果导入</span>
                </Space>
              </template>
              <Spin :spinning="isAnalyzing || isLoadingResult || isUploadingResult" 
                    :tip="isAnalyzing ? '正在执行协议分析...' : isLoadingResult ? '正在读取本地结果...' : '正在导入结果文件...'">
                <Form class="extract-form" layout="vertical">
                  <!-- 基础信息 -->
                  <FormItem label="协议类型">
                    <AutoComplete
                      v-model:value="formData.protocol"
                      allow-clear
                      class="input-protocol"
                      placeholder="选择或输入协议类型（如 MQTTv5）"
                      :options="[
                        { value: 'CoAP' },
                        { value: 'DHCPv6' },
                        { value: 'MQTTv3_1_1' },
                        { value: 'MQTTv5' },
                        { value: 'TLSv1_3' },
                        { value: 'FTP' }
                      ]"
                    />
                  </FormItem>
                  <FormItem label="协议版本">
                    <Input
                      v-model:value="formData.version"
                      placeholder="请输入协议版本（如 1.0）"
                    />
                  </FormItem>

                  <!-- 功能一：上传协议文档分析 -->
                  <div style="margin: 16px 0; padding: 16px; border: 1px dashed #e8e8e8; border-radius: 4px;">
                    <TypographyText strong>功能一：上传协议文档，自动分析</TypographyText>
                    <FormItem label="DeepSeek API 密钥" style="margin-top: 8px;">
                      <Input.Password
                        v-model:value="formData.apiKey"
                        autocomplete="off"
                        placeholder="分析需要调用API，必填"
                      />
                    </FormItem>
                    <FormItem label="上传协议文档">
                      <Upload
                        :file-list="rfcFileList"
                        :before-upload="beforeUploadRFC"
                        :on-remove="removeRFC"
                        accept=".html,.pdf,.txt,.json"
                        style="width: 100%;"
                      >
                        <Button block type="dashed">
                          <IconifyIcon icon="ant-design:file-add-outlined" class="mr-1" />
                          选择协议文档（支持 HTML/PDF/TXT/JSON）
                        </Button>
                      </Upload>
                    </FormItem>
                    <FormItem label="启用目录筛选" value-prop-name="checked">
                      <Switch v-model:checked="formData.filterHeadings" />
                    </FormItem>
                    <Button
                      type="primary"
                      :loading="isAnalyzing"
                      @click="startAnalysis"
                      style="margin-top: 8px;"
                    >
                      <IconifyIcon icon="ant-design:play-circle-outlined" class="mr-1" />
                      开始分析（生成结果并存储）
                    </Button>
                  </div>

                  <!-- 功能二：上传结果文件导入 -->
                  <div style="margin: 16px 0; padding: 16px; border: 1px dashed #e8e8e8; border-radius: 4px;">
                    <TypographyText strong>功能二：上传已有结果文件，直接导入</TypographyText>
                    <TypographyParagraph type="secondary" style="margin: 8px 0;">
                      已提前生成分析结果JSON文件？直接上传导入，无需重复分析（无需API密钥）
                      <br/>支持3种JSON格式：1. 直接数组 [{...}] 2. { "rules": [...] } 3. 按消息类型分组 { "CONNECT": [...], ... }
                    </TypographyParagraph>
                    <FormItem label="上传分析结果文件">
                      <Upload
                        :file-list="resultFileList"
                        :before-upload="beforeUploadResultFile"
                        :on-remove="removeResultFile"
                        accept=".json"
                        style="width: 100%;"
                      >
                        <Button block type="dashed">
                          <IconifyIcon icon="ant-design:upload-outlined" class="mr-1" />
                          选择JSON格式的结果文件
                        </Button>
                      </Upload>
                      <TypographyText type="secondary" style="font-size: 12px; margin-top: 8px; display: block;">
                        已选文件：{{ resultFileList[0]?.name || '无' }}
                      </TypographyText>
                    </FormItem>
                    <Button
                      type="default"
                      :loading="isUploadingResult"
                      @click="uploadAndSaveResult"
                      style="margin-top: 8px; background: #1890ff; color: white;"
                    >
                      <IconifyIcon icon="ant-design:save-outlined" class="mr-1" />
                      导入结果并存储到历史记录
                    </Button>
                  </div>

                  <!-- 功能三：加载本地结果 -->
                  <div style="margin: 16px 0; padding: 16px; border: 1px dashed #e8e8e8; border-radius: 4px;">
                    <TypographyText strong>功能三：加载本地已存结果，快速查看</TypographyText>
                    <TypographyParagraph type="secondary" style="margin: 8px 0;">
                      项目中已存在结果文件？直接输入协议名和版本，快速加载（无需上传文件）
                    </TypographyParagraph>
                    <Button
                      type="default"
                      :loading="isLoadingResult"
                      @click="loadExistingResult"
                      style="margin-top: 8px;"
                    >
                      <IconifyIcon icon="ant-design:folder-open-outlined" class="mr-1" />
                      加载本地结果（自动查找文件）
                    </Button>
                  </div>

                  <TypographyParagraph class="form-tip" type="secondary">
                    提示：所有生成/导入的结果都会自动存入历史记录，可在「历史记录」标签页查看。
                    <br/>如果操作失败，请打开浏览器控制台（F12）查看具体错误信息。
                  </TypographyParagraph>
                </Form>
              </Spin>
            </Card>

            <!-- 结果预览卡片 -->
            <Card class="result-card">
              <template #title>
                <Space>
                  <IconifyIcon icon="ant-design:profile-outlined" class="text-lg" />
                  <span>规则预览</span>
                </Space>
              </template>
              <div class="result-toolbar">
                <TypographyText type="secondary">
                  共 {{ totalItems }} 条规则
                  <span v-if="selectedGroup">· 已筛选 {{ filteredResults.length }} 条</span>
                </TypographyText>
                <Space size="small" wrap>
                  <Select
                    v-model:value="selectedGroup"
                    allow-clear
                    class="select-group"
                    :disabled="!analysisCompleted || !groupList.length"
                    placeholder="按消息类型筛选（如 CONNECT）"
                  >
                    <Select.Option v-for="g in groupList" :key="`group-${g}`" :value="g">
                      {{ g }}
                    </Select.Option>
                  </Select>
                  <Button
                    :disabled="!analysisCompleted || !stagedResults.length"
                    @click="downloadAnalysisResult"
                  >
                    <IconifyIcon icon="ant-design:download-outlined" class="mr-1" />
                    下载 JSON（按消息类型分组）
                  </Button>
                </Space>
              </div>
              <TypographyParagraph
                v-if="analysisCompleted && lastResultMeta"
                class="result-meta"
                type="secondary"
              >
                结果来源：{{ lastResultMeta.resultPath || '未知' }}
                <span v-if="lastResultMeta.storeDir">（存储目录：{{ lastResultMeta.storeDir }}）</span>
              </TypographyParagraph>
              <div
                v-if="analysisCompleted && filteredResults.length"
                class="table-wrapper"
              >
                <Table
                  :columns="columns"
                  :data-source="currentPageData"
                  :pagination="{
                    current: currentPage,
                    pageSize,
                    total: filteredResults.length,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 条规则`,
                  }"
                  :row-key="(record, index) => `row-${index}`"
                  :scroll="{ x: 'max-content', y: 400 }"
                  bordered
                  @change="handleTableChange"
                />
              </div>
              <Empty
                v-else-if="analysisCompleted"
                description="未找到规则数据"
              />
              <TypographyParagraph
                v-else
                class="result-placeholder"
                type="secondary"
              >
                请选择功能生成/导入规则，或加载本地已有结果。
              </TypographyParagraph>
            </Card>
          </div>
        </Tabs.TabPane>

        <!-- 历史记录标签页 -->
        <Tabs.TabPane key="history" tab="历史记录">
          <Card class="history-card">
            <template #title>
              <Space style="width: 100%; justify-content: space-between; align-items: center;">
                <Space>
                  <IconifyIcon icon="ant-design:calendar-outlined" class="text-lg" />
                  <span>历史记录（自动存储所有结果）</span>
                </Space>
                <!-- 清空全部按钮 -->
                <Popconfirm
                  title="确定要清空全部历史记录吗？此操作不可恢复！"
                  okText="确定"
                  cancelText="取消"
                  onConfirm="clearAllHistory"
                  placement="right"
                  okType="danger"
                >
                  <Button type="danger" size="small">
                    <IconifyIcon icon="ant-design:delete-outlined" class="mr-1" />
                    清空全部
                  </Button>
                </Popconfirm>
              </Space>
            </template>
            
            <Divider />

            <div v-if="historyData.length" class="history-header">
              <TypographyText type="secondary">已存储的分析结果：</TypographyText>
              <Space size="small" wrap class="history-protocols">
                <Tag
                  v-for="(item, index) in historyData"
                  :key="`history-tag-${index}`"
                  color="blue"
                  :style="{ cursor: 'pointer' }"
                  @click="openFromHistory(item)"
                >
                  {{ item.protocol }}({{ item.version }}) - {{ item.ruleCount }}条
                </Tag>
              </Space>
            </div>
            
            <TypographyParagraph class="history-tip" type="secondary">
              包含：上传文档分析、导入结果文件、加载本地结果的所有记录，点击标签可快速查看。
            </TypographyParagraph>
            
            <div class="history-table-wrapper" v-if="historyData.length">
              <Table
                :columns="historyColumns"
                :data-source="historyData"
                :pagination="{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total) => `共 ${total} 条记录`,
                }"
                :row-key="item => item.id"
                bordered
                :scroll="{ x: 'max-content' }"
                @row-click="openFromHistory"
              />
            </div>
            
            <Empty v-else description="暂无历史记录" style="margin: 32px 0;" />
          </Card>
        </Tabs.TabPane>
      </Tabs>
    </div>
  </Page>
</template>

<style scoped>
:deep(.mb-2.flex.text-lg.font-semibold) {
  font-size: 2.25rem;
}

.protocol-extract {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100vh;
  height: auto;
  overflow-y: auto;
  padding-bottom: 24px;
}

.extract-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 16px;
}

.analyze-layout {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 16px;
  align-items: start;
}

.form-card,
.result-card {
  display: flex;
  flex-direction: column;
  height: auto;
}

.extract-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-protocol {
  width: 100%;
}

.form-tip {
  margin: 8px 0;
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.result-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 16px 0;
}

.select-group {
  min-width: 180px;
}

.table-wrapper {
  flex: 1;
  min-height: 400px;
}

.result-placeholder {
  margin: 32px 0;
  font-size: 13px;
  text-align: center;
}

.result-meta {
  margin: 8px 0;
  font-size: 12px;
}

.history-card :deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  flex-wrap: wrap;
}

.history-protocols {
  display: inline-flex;
  flex-wrap: wrap;
  width: 100%;
  gap: 8px;
}

.history-tip {
  margin: 8px 0;
  font-size: 12px;
  color: var(--ant-text-color-secondary);
}

.history-table-wrapper {
  width: 100%;
  margin-top: 8px;
}

:deep(.ant-table-cell) {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
}

.table-empty {
  color: var(--ant-text-color-secondary);
}

/* 适配移动端 */
@media (max-width: 1200px) {
  .analyze-layout {
    grid-template-columns: 1fr;
  }
}
</style>
