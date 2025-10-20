<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

import {
  Button,
  Card,
  Divider,
  Empty,
  message,
  Space,
  Tag,
} from 'ant-design-vue';

// 类型定义
type RuleItem = {
  analysis: string;
  code?: string;
  rule: string;
};

type RawAnalysisResult = {
  reason: string;
  result: string;
};

// 路由与标题
const route = useRoute();
const title = computed(() => String(route.meta?.title ?? '静态规则分析'));

// 状态管理
const analysisGroups = ref<Record<string, RuleItem[]>>({});
const analysisResults = ref<Record<string, RawAnalysisResult>>({});
const lastFetchError = ref<null | string>(null);
const dataLoaded = ref(false); // 新增：标记数据是否已加载

// 分组展开状态
const groupExpanded = ref<Record<string, boolean>>({}); // 控制分组展开/收起

// 左侧分页
const itemsPerPage = 5;
const currentPage = ref(1);
const totalPages = ref(1);
const currentRules = ref<RuleItem[]>([]);
const activeAnalysisKey = ref<null | string>(null);

// 右侧当前分析结果
const currentResult = ref<null | RawAnalysisResult>(null);
const currentRule = ref<null | string>(null);

// 加载规则与分析结果
async function loadData() {
  try {
    // 1. 加载规则数据
    const rulesRes = await fetch('/rule.json');
    const rulesObj = await rulesRes.json();
    const rulesData: RuleItem[] = Object.entries(rulesObj).map(
      ([rule, code]) => ({
        analysis: '默认规则组',
        rule,
        code: code as string,
      }),
    );

    // 2. 加载分析结果
    const resultsRes = await fetch('/rules.json');
    const rawResults: Record<string, string> = await resultsRes.json();

    // 解析结果
    const parsedResults: Record<string, RawAnalysisResult> = {};
    Object.entries(rawResults).forEach(([rule, resultStr]) => {
      try {
        if (!resultStr.trim()) {
          parsedResults[rule] = { result: '未分析', reason: '无分析结果' };
          return;
        }
        const parsed = JSON.parse(resultStr) as RawAnalysisResult;
        parsedResults[rule] = parsed;
      } catch (error) {
        parsedResults[rule] = {
          result: '解析错误',
          reason: `分析结果格式错误: ${(error as Error).message}`,
        };
      }
    });

    // 3. 分组处理
    const groups: Record<string, RuleItem[]> = {};
    rulesData.forEach((item) => {
      if (!groups[item.analysis]) {
        groups[item.analysis] = [];
        groupExpanded.value[item.analysis] = false; // 初始化为收起状态
      }
      groups[item.analysis].push(item);
    });

    analysisGroups.value = groups;
    analysisResults.value = parsedResults;
    lastFetchError.value = null;
    dataLoaded.value = true; // 标记数据已加载
    message.success('数据加载成功');
  } catch (error: any) {
    lastFetchError.value = `加载数据失败: ${error.message}`;
    message.error(lastFetchError.value);
  }
}

// 初始化不自动加载，保持空状态
onMounted(() => {
  // 不自动调用loadData，等待用户点击刷新
});

// 切换规则组展开/收起
function toggleAnalysisGroup(key: string) {
  // 切换状态
  groupExpanded.value[key] = !groupExpanded.value[key];

  // 处理展开状态
  if (groupExpanded.value[key]) {
    activeAnalysisKey.value = key;
    currentPage.value = 1;
    currentRules.value = analysisGroups.value[key] || [];
    totalPages.value = Math.ceil(
      (currentRules.value.length || 0) / itemsPerPage,
    );
  } else {
    activeAnalysisKey.value = null;
    currentRules.value = [];
    currentResult.value = null;
    currentRule.value = null;
  }
}

// 查看分析结果
function viewAnalysisResult(rule: string) {
  currentRule.value = rule;
  currentResult.value = analysisResults.value[rule] || {
    result: '未找到',
    reason: '未找到对应的分析结果',
  };
}

// 左侧分页控制
function prevPage(e: MouseEvent) {
  e.stopPropagation();
  if (currentPage.value > 1) {
    currentPage.value--;
    currentResult.value = null;
    currentRule.value = null;
  }
}

function nextPage(e: MouseEvent) {
  e.stopPropagation();
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
    currentResult.value = null;
    currentRule.value = null;
  }
}

// 分页数据切片（改为computed确保响应式）
const currentPageSlice = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  return currentRules.value.slice(start, start + itemsPerPage);
});

// 结果状态样式计算
const resultStatusClass = computed(() => {
  if (!currentResult.value) return '';
  const result = currentResult.value.result.toLowerCase();
  if (result.includes('no violation')) return 'text-success';
  if (result.includes('violation')) return 'text-error';
  if (result === '未分析' || result === '') return 'text-gray';
  return 'text-warning';
});

// 结果状态文本
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

        <!-- 初始状态显示空提示 -->
        <div v-if="!dataLoaded">
          <Empty description="请点击刷新按钮加载数据" />
        </div>

        <div v-else-if="Object.keys(analysisGroups).length === 0">
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
              :class="{ 'active-group': groupExpanded[groupName] }"
              @click="toggleAnalysisGroup(groupName)"
            >
              <template #title>
                <Space>
                  <span>{{ idx + 1 }}. {{ groupName }}</span>
                  <Tag color="blue">{{ rules.length }} 条规则</Tag>
                  <!-- 展开/收起图标 -->
                  <span class="expand-icon">{{
                    groupExpanded[groupName] ? '▼' : '►'
                  }}</span>
                </Space>
              </template>

              <!-- 仅在展开状态显示规则列表 -->
              <div v-if="groupExpanded[groupName]" class="group-rules">
                <div
                  v-for="(item, i) in currentPageSlice"
                  :key="i"
                  class="rule-item cursor-pointer"
                  @click.stop="viewAnalysisResult(item.rule)"
                >
                  <div class="rule-header">
                    <span class="rule-index"
                      >{{ (currentPage - 1) * itemsPerPage + i + 1 }}.</span
                    >
                    <span class="rule-content">{{ item.rule }}</span>
                  </div>

                  <Divider orientation="left">对应代码</Divider>
                  <pre class="rule-code">{{ item.code || '无对应代码' }}</pre>
                </div>

                <Space class="pagination-controls" @click.stop>
                  <Button
                    size="small"
                    :disabled="currentPage === 1"
                    @click="prevPage($event)"
                  >
                    上一页
                  </Button>
                  <span>
                    第 {{ currentPage }} 页 / 共 {{ totalPages }} 页
                  </span>
                  <Button
                    size="small"
                    :disabled="currentPage >= totalPages"
                    @click="nextPage($event)"
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
          <Tag
            :color="
              currentResult?.result.includes('no violation')
                ? 'green'
                : currentResult?.result.includes('violation')
                  ? 'red'
                  : 'orange'
            "
          >
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
            <p>{{ currentResult.reason }}</p>
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
  color: rgb(0 0 0 / 65%);
}

.analysis-container {
  display: flex;
  gap: 24px;
  height: calc(100vh - 160px);
}

.analysis-left,
.analysis-right {
  display: flex;
  flex: 1;
  flex-direction: column;
  overflow: auto;
}

.group-wrapper {
  margin-bottom: 16px;
}

.group-card {
  transition: all 0.3s;
}

.group-card.active-group {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgb(24 144 255 / 20%);
}

.expand-icon {
  font-size: 14px;
  color: #1890ff;
  transition: transform 0.2s;
}

.group-rules {
  padding-top: 8px;
  margin-top: 8px;
  border-top: 1px dashed #e8e8e8;
}

.rule-item {
  padding: 12px;
  margin-bottom: 12px;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  transition: all 0.2s;
}

.rule-item:hover {
  background-color: #f0f7ff;
  border-color: #1890ff;
}

.rule-header {
  margin-bottom: 8px;
  word-break: normal;
  overflow-wrap: anywhere;
}

.rule-index {
  display: inline-block;
  width: 30px;
  color: rgb(0 0 0 / 50%);
}

.rule-content {
  font-weight: 500;
}

.rule-code {
  max-height: 200px;
  padding: 8px;
  margin: 0;
  overflow: auto;
  font-family: 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  background: #f5f5f5;
  border-radius: 4px;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  padding: 8px;
  margin-top: 16px;
}

.result-details {
  padding: 8px 0;
}

.result-rule p,
.result-description p {
  margin: 8px 0;
  line-height: 1.6;
  word-break: normal;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.status-text {
  margin: 8px 0;
  font-size: 16px;
  font-weight: 500;
}

/* 状态颜色类 */
.text-success {
  color: #52c41a;
}

.text-error {
  color: #f5222d;
}

.text-warning {
  color: #faad14;
}

.text-gray {
  color: #8c8c8c;
}
</style>
