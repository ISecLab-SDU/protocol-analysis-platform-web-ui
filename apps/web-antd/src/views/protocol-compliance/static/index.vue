<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import {
  Card,
  Empty,
  Space,
  Button,
  Tag,
  message,
  Divider
} from 'ant-design-vue';

// 类型定义（适配 rules.json 的特殊结构）
type RuleItem = {
  analysis: string;
  rule: string;
  code?: string;
};

// 分析结果的原始结构（值是 JSON 字符串）
type RawAnalysisResult = {
  result: string; // 可能是 "no violation found!" 等字符串
  reason: string;
};

// 路由与标题
const route = useRoute();
const title = computed(() =>
  String(route.meta?.title ?? '静态规则分析' ?? '功能建设中'),
);

// 状态管理
const analysisGroups = ref<Record<string, RuleItem[]>>({});
// 存储解析后的分析结果（规则内容 → 分析结果）
const analysisResults = ref<Record<string, RawAnalysisResult>>({});
const lastFetchError = ref<null | string>(null);

// 左侧分页
const itemsPerPage = 5;
const currentPage = ref(1);
const totalPages = ref(1);
const currentRules = ref<RuleItem[]>([]);
const activeAnalysisKey = ref<string | null>(null);

// 右侧当前分析结果
const currentResult = ref<RawAnalysisResult | null>(null);
const currentRule = ref<string | null>(null);

// 加载规则与分析结果（适配 rules.json 的特殊格式）
async function loadData() {
  try {
    // 1. 加载规则数据（rule.json）
    const rulesRes = await fetch('/rule.json');
    const rulesObj = await rulesRes.json();
    const rulesData: RuleItem[] = Object.entries(rulesObj).map(([rule, code]) => ({
      analysis: '默认规则组',
      rule,
      code: code as string,
    }));

    // 2. 加载分析结果（rules.json）- 重点处理：值是 JSON 字符串
    const resultsRes = await fetch('/rules.json');
    const rawResults: Record<string, string> = await resultsRes.json(); // 值是字符串

    // 解析每个值（JSON 字符串 → 对象）
    const parsedResults: Record<string, RawAnalysisResult> = {};
    Object.entries(rawResults).forEach(([rule, resultStr]) => {
      try {
        // 处理空值或无效字符串
        if (!resultStr.trim()) {
          parsedResults[rule] = { result: '未分析', reason: '无分析结果' };
          return;
        }
        // 解析 JSON 字符串
        const parsed = JSON.parse(resultStr) as RawAnalysisResult;
        parsedResults[rule] = parsed;
      } catch (e) {
        // 解析失败时的容错处理
        parsedResults[rule] = {
          result: '解析错误',
          reason: `分析结果格式错误: ${(e as Error).message}`
        };
      }
    });

    // 3. 分组处理规则
    const groups: Record<string, RuleItem[]> = {};
    rulesData.forEach(item => {
      if (!groups[item.analysis]) groups[item.analysis] = [];
      groups[item.analysis].push(item);
    });

    analysisGroups.value = groups;
    analysisResults.value = parsedResults;
    lastFetchError.value = null;
  } catch (err: any) {
    lastFetchError.value = `加载数据失败: ${err.message}`;
    message.error(lastFetchError.value);
  }
}

// 初始化加载
onMounted(() => {
  loadData();
});

// 展开规则组
function openAnalysisGroup(key: string) {
  activeAnalysisKey.value = key;
  currentPage.value = 1;
  currentRules.value = analysisGroups.value[key] || [];
  totalPages.value = Math.ceil((currentRules.value.length || 0) / itemsPerPage);
  currentResult.value = null;
  currentRule.value = null;
}

// 查看分析结果（核心：用规则内容作为键匹配）
function viewAnalysisResult(rule: string) {
  currentRule.value = rule;
  // 从解析后的结果中查找，无结果时显示默认值
  currentResult.value = analysisResults.value[rule] || {
    result: '未找到',
    reason: '未找到对应的分析结果'
  };
}

// 左侧分页控制
function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--;
    currentResult.value = null;
    currentRule.value = null;
  }
}

function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
    currentResult.value = null;
    currentRule.value = null;
  }
}

// 分页数据切片
function currentPageSlice() {
  const start = (currentPage.value - 1) * itemsPerPage;
  return currentRules.value.slice(start, start + itemsPerPage);
}

// 结果状态样式计算（适配实际 result 字符串）
const resultStatusClass = computed(() => {
  if (!currentResult.value) return '';
  const result = currentResult.value.result.toLowerCase();
  if (result.includes('no violation')) return 'text-success'; // 符合规则
  if (result.includes('violation')) return 'text-error'; // 违反规则
  if (result === '未分析' || result === '') return 'text-gray'; // 未分析
  return 'text-warning'; // 其他情况（解析错误等）
});

// 结果状态文本（中文显示）
const resultStatusText = computed(() => {
  if (!currentResult.value) return '';
  const result = currentResult.value.result.toLowerCase();
  if (result.includes('no violation')) return '符合规则';
  if (result.includes('violation')) return '违反规则';
  if (result === '未分析' || result === '') return '未分析';
  return '需要注意';
});
</script>

<template>
  <div class="static-analysis-page">
    <div class="page-header">
      <h1>{{ title }}</h1>
      <p>静态规则分析结果展示，左侧为规则与代码，右侧为对应分析结果</p>
      <Space v-if="lastFetchError" class="error提示">
        <span class="text-danger">{{ lastFetchError }}</span>
        <Button size="small" @click="loadData">重新加载</Button>
      </Space>
    </div>

    <div class="analysis-container">
      <!-- 左侧：规则与代码 -->
      <Card class="analysis-left" title="规则与代码列表">
        <template #extra>
          <Space>
            <span>规则组数: {{ Object.keys(analysisGroups).length }}</span>
            <Button size="small" @click="loadData">刷新</Button>
          </Space>
        </template>

        <div v-if="Object.keys(analysisGroups).length === 0">
          <Empty description="未加载到规则数据" />
        </div>

        <div v-else>
          <div 
            v-for="(rules, groupName, idx) in analysisGroups" 
            :key="groupName" 
            class="group-wrapper"
          >
            <Card 
              size="small" 
              class="group-card cursor-pointer"
              :class="{ 'active-group': activeAnalysisKey === groupName }"
              @click="openAnalysisGroup(groupName)"
            >
              <template #title>
                <Space>
                  <span>{{ idx + 1 }}. {{ groupName }}</span>
                  <Tag color="blue">{{ rules.length }} 条规则</Tag>
                </Space>
              </template>

              <div v-if="activeAnalysisKey === groupName" class="group-rules">
                <div 
                  v-for="(item, i) in currentPageSlice()" 
                  :key="i" 
                  class="rule-item cursor-pointer"
                  @click.stop="viewAnalysisResult(item.rule)"
                >
                  <div class="rule-header">
                    <span class="rule-index">{{ (currentPage - 1) * itemsPerPage + i + 1 }}.</span>
                    <span class="rule-content">{{ item.rule }}</span>
                  </div>
                  
                  <Divider orientation="left">对应代码</Divider>
                  <pre class="rule-code">{{ item.code || '无对应代码' }}</pre>
                </div>

                <Space class="pagination-controls">
                  <Button 
                    size="small" 
                    :disabled="currentPage === 1" 
                    @click="prevPage"
                  >
                    上一页
                  </Button>
                  <span>
                    第 {{ currentPage }} 页 / 共 {{ totalPages }} 页
                  </span>
                  <Button 
                    size="small" 
                    :disabled="currentPage >= totalPages" 
                    @click="nextPage"
                  >
                    下一页
                  </Button>
                </Space>
              </div>
            </Card>
          </div>
        </div>
      </Card>

      <!-- 右侧：分析结果 -->
      <Card class="analysis-right" title="分析结果详情">
        <template #extra>
          <Tag :color="currentResult?.result.includes('no violation') ? 'green' : 
                         currentResult?.result.includes('violation') ? 'red' : 'orange'">
            {{ currentResult ? resultStatusText : '未选择规则' }}
          </Tag>
        </template>

        <div v-if="!currentResult">
          <Empty description="请从左侧选择规则查看分析结果" />
        </div>

        <div v-else class="result-details">
          <div class="result-rule">
            <h3>规则内容:</h3>
            <p>{{ currentRule }}</p>
          </div>

          <Divider />

          <div class="result-status">
            <h3>分析结果:</h3>
            <p class="status-text" :class="resultStatusClass">
              {{ resultStatusText }}
            </p>
          </div>

          <Divider />

          <div class="result-description">
            <h3>详细说明:</h3>
            <p>{{ currentResult.reason }}</p> <!-- 显示 reason 字段 -->
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.static-analysis-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.page-header p {
  margin: 8px 0 0;
  color: rgba(0, 0, 0, 0.65);
}

.analysis-container {
  display: flex;
  gap: 24px;
  height: calc(100vh - 160px);
}

.analysis-left, .analysis-right {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
}

.group-wrapper {
  margin-bottom: 16px;
}

.group-card {
  transition: all 0.3s;
}

.group-card.active-group {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2);
}

.group-rules {
  margin-top: 8px;
}

.rule-item {
  padding: 12px;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  margin-bottom: 12px;
  transition: all 0.2s;
}

.rule-item:hover {
  border-color: #1890ff;
}

.rule-header {
  margin-bottom: 8px;
  word-break: break-word; /* 长规则自动换行 */
}

.rule-index {
  display: inline-block;
  width: 30px;
  color: rgba(0, 0, 0, 0.5);
}

.rule-content {
  font-weight: 500;
}

.rule-code {
  margin: 0;
  padding: 8px;
  background: #f5f5f5;
  border-radius: 4px;
  font-family: "Fira Code", monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  max-height: 200px;
  overflow: auto;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.result-details {
  padding: 8px 0;
}

.result-rule p, .result-description p {
  margin: 8px 0;
  line-height: 1.6;
  white-space: pre-wrap; /* 长文本自动换行 */
  word-break: break-word;
}

.status-text {
  margin: 8px 0;
  font-size: 16px;
  font-weight: 500;
}

/* 状态颜色类 */
.text-success { color: #52c41a; }
.text-error { color: #f5222d; }
.text-warning { color: #faad14; }
.text-gray { color: #8c8c8c; }
</style>
