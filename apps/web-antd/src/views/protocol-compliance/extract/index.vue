<script lang="ts" setup>
import { ref, reactive, computed } from 'vue';
import { Page } from '@vben/common-ui';
import { Button, Card, Empty, Form, FormItem, message, Space, Tabs, Tag, Upload, } from 'ant-design-vue';
import type { FormInstance, UploadFile, UploadProps } from 'ant-design-vue';

const activeTab = ref('upload'); // upload | result
const isSubmitting = ref(false);
const formRef = ref<FormInstance>();

// 表单数据模型
const formData = reactive({
  rfc: null as File | null,
  code: null as File | null,
});

// 文件上传列表
const rfcFileList = ref<UploadFile[]>([]);
const codeFileList = ref<UploadFile[]>([]);

// 上传提示
const uploadTip = ref(
  '温馨提示：上传文件后，系统会模拟分析并显示规则与代码。'
);

// 结果数据类型定义
type RuleItem = {
  analysis: string;
  rule: string;
  code?: string;
};

// 分析状态与结果数据
let analysisCompleted = false;
const allData = ref<RuleItem[]>([]);
const analysisGroups = ref<Record<string, RuleItem[]>>({});
const lastFetchError = ref<null | string>(null);

// 分组展开状态管理（核心修改：记录每个分组的展开/收起状态）
const groupExpanded = ref<Record<string, boolean>>({});

// 左侧列表分页
const itemsPerPage = 5;
const currentPage = ref(1);
const totalPages = ref(1);
const currentRules = ref<RuleItem[]>([]);

// 右侧代码查看分页
const currentCodeLines = ref<string[]>([]);
const currentCodePage = ref(1);
const codeLinesPerPage = 32;

// 表单验证规则
const formRules = {
  rfc: [{ required: true, message: '请上传 RFC 文档', trigger: 'change' }],
  code: [{ required: true, message: '请上传源代码文件', trigger: 'change' }],
};

// RFC文档上传控制
const beforeUploadRFC: UploadProps['beforeUpload'] = (file) => {
  rfcFileList.value = [file];
  formData.rfc = (file as UploadFile<File>).originFileObj ?? (file as any as File);
  formRef.value?.clearValidate?.(['rfc']);
  return false;
};

const removeRFC: UploadProps['onRemove'] = () => {
  rfcFileList.value = [];
  formData.rfc = null;
  formRef.value?.validateFields?.(['rfc']);
  return true;
};

// 源代码上传控制
const beforeUploadCode: UploadProps['beforeUpload'] = (file) => {
  codeFileList.value = [file];
  formData.code = (file as UploadFile<File>).originFileObj ?? (file as any as File);
  formRef.value?.clearValidate?.(['code']);
  return false;
};

const removeCode: UploadProps['onRemove'] = () => {
  codeFileList.value = [];
  formData.code = null;
  formRef.value?.validateFields?.(['code']);
  return true;
};

// 模拟分析过程
async function handleAnalyze() {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }

  isSubmitting.value = true;
  try {
    await new Promise(r => setTimeout(r, 1500));
    analysisCompleted = true;
    message.success('分析完成，切换到结果展示');
    activeTab.value = 'result';
    await loadRules();
  } catch (e: any) {
    message.error(`分析失败：${e?.message || e}`);
  } finally {
    isSubmitting.value = false;
  }
}

// 加载规则数据
async function loadRules() {
  if (!analysisCompleted) return;

  lastFetchError.value = null;
  try {
    const res = await fetch('/rule.json');
    const rulesObj = await res.json();
    const data: RuleItem[] = Object.entries(rulesObj).map(([rule, code]) => ({
      analysis: '默认分析组',
      rule,
      code,
    }));

    allData.value = data;

    // 数据分组
    const groups: Record<string, RuleItem[]> = {};
    data.forEach(item => {
      if (!groups[item.analysis]) {
        groups[item.analysis] = [];
        groupExpanded.value[item.analysis] = false; // 初始化所有分组为收起状态
      }
      groups[item.analysis].push(item);
    });

    analysisGroups.value = groups;
  } catch (err: any) {
    lastFetchError.value = String(err);
    message.error(`加载结果失败：${lastFetchError.value}`);
  }
}

// 切换分组展开/收起状态（核心修改：实现切换逻辑）
function toggleAnalysisGroup(key: string) {
  // 切换当前分组的展开状态
  groupExpanded.value[key] = !groupExpanded.value[key];
  
  // 如果是展开状态，初始化分页数据
  if (groupExpanded.value[key]) {
    currentPage.value = 1;
    currentRules.value = analysisGroups.value[key] || [];
    totalPages.value = Math.ceil((currentRules.value.length || 0) / itemsPerPage);
  } else {
    // 收起时清空当前规则列表
    currentRules.value = [];
  }
  
  // 无论展开还是收起，都重置代码显示区域
  currentCodeLines.value = [];
  currentCodePage.value = 1;
}

// 左侧规则列表分页（响应式）
const currentPageSlice = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  return currentRules.value.slice(start, start + itemsPerPage);
});

// 左侧分页控制
function prevPage(e: MouseEvent) {
  e.stopPropagation();
  if (currentPage.value > 1) {
    currentPage.value--;
    currentCodeLines.value = [];
    currentCodePage.value = 1;
  }
}

function nextPage(e: MouseEvent) {
  e.stopPropagation();
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
    currentCodeLines.value = [];
    currentCodePage.value = 1;
  }
}

// 查看规则对应的代码
function openCode(e: MouseEvent, item: RuleItem) {
  e.stopPropagation();
  currentCodeLines.value = (item.code || '(无代码)').split(/\r?\n/);
  currentCodePage.value = 1;
}

// 右侧代码分页（响应式）
const renderCodeLines = computed(() => {
  const start = (currentCodePage.value - 1) * codeLinesPerPage;
  return currentCodeLines.value.slice(start, start + codeLinesPerPage).map((line, idx) => ({
    num: start + idx + 1,
    line
  }));
});

// 右侧代码分页控制
function prevCodePage(e: MouseEvent) {
  e.stopPropagation();
  if (currentCodePage.value > 1) currentCodePage.value--;
}

function nextCodePage(e: MouseEvent) {
  e.stopPropagation();
  const total = Math.ceil(currentCodeLines.value.length / codeLinesPerPage);
  if (currentCodePage.value < total) currentCodePage.value++;
}
</script>

<template>
  <Page title="RFC 规则查看系统" description="上传 RFC 与源代码，分析并查看规则及代码。">
    <div class="flex flex-col gap-4">
      <Card>
        <Space class="w-full justify-between">
          <div class="flex flex-col gap-2">
            <p>将 RFC 与源码交给系统解析后，会提取规则与对应代码。</p>
            <p v-if="lastFetchError" class="text-danger">{{ lastFetchError }}</p>
          </div>
          <Button @click="analysisCompleted ? loadRules() : message.info('请先完成分析')">刷新结果</Button>
        </Space>
      </Card>

      <Card>
        <Tabs v-model:activeKey="activeTab" destroyInactiveTabPane>
          <Tabs.TabPane key="upload" tab="上传 RFC 与源代码">
            <Form ref="formRef" :model="formData" :rules="formRules" layout="vertical">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormItem name="rfc" label="RFC 文档" required>
                  <Upload
                    :file-list="rfcFileList"
                    :before-upload="beforeUploadRFC"
                    :on-remove="removeRFC"
                    :max-count="1"
                  >
                    <Button block>选择 RFC 文档</Button>
                  </Upload>
                </FormItem>
                <FormItem name="code" label="源代码" required>
                  <Upload
                    :file-list="codeFileList"
                    :before-upload="beforeUploadCode"
                    :on-remove="removeCode"
                    :max-count="1"
                  >
                    <Button block>选择源代码文件</Button>
                  </Upload>
                </FormItem>
              </div>
              <p class="upload-hint">{{ uploadTip }}</p>
              <Space class="w-full justify-center mt-4">
                <Button type="primary" :loading="isSubmitting" @click="handleAnalyze">开始分析</Button>
              </Space>
            </Form>
          </Tabs.TabPane>

          <Tabs.TabPane key="result" tab="结果展示">
            <div class="flex flex-col lg:flex-row gap-4">
              <!-- 左侧规则列表 -->
              <Card class="flex-1" title="分析结果列表">
                <template #extra><span>组数 {{ Object.keys(analysisGroups).length }}</span></template>
                
                <div v-if="!analysisCompleted"><Empty description="请先上传文件" /></div>
                <div v-else-if="Object.keys(analysisGroups).length === 0"><Empty description="分析完成，但未找到规则" /></div>
                <div v-else>
                  <div v-for="(rules, groupName, idx) in analysisGroups" :key="groupName" class="item-wrapper">
                    <Card
                      size="small"
                      class="cursor-pointer transition-all duration-200"
                      :class="{ active: groupExpanded[groupName] }"
                      @click="toggleAnalysisGroup(groupName)"
                    >
                      <template #title>
                        <Space>
                          <span>{{ idx + 1 }}. {{ groupName }}</span>
                          <Tag color="processing">{{ rules.length }} 条规则</Tag>
                          <!-- 展开/收起状态图标 -->
                          <span class="expand-icon">{{ groupExpanded[groupName] ? '▼' : '►' }}</span>
                        </Space>
                      </template>

                      <!-- 仅在展开状态显示规则列表 -->
                      <div v-if="groupExpanded[groupName]" class="group-content">
                        <div 
                          v-for="(item, i) in currentPageSlice" 
                          :key="i" 
                          class="rule-item cursor-pointer" 
                          @click="openCode($event, item)"
                        >
                          <span class="rule-number">{{ (currentPage-1)*itemsPerPage + i + 1 }}. </span>
                          <span class="rule-text">{{ item.rule }}</span>
                        </div>

                        <Space class="pagination-controls" @click.stop>
                          <Button 
                            size="small" 
                            :disabled="currentPage === 1" 
                            @click="prevPage($event)"
                          >
                            上一页
                          </Button>
                          <span>第 {{ currentPage }} 页 / 共 {{ totalPages }} 页</span>
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

              <!-- 右侧代码内容 -->
              <Card class="flex-1" title="代码内容">
                <div v-if="currentCodeLines.length === 0"><Empty description="尚未选择规则" /></div>
                <div v-else class="code-display">
                  <pre>
                    <span v-for="(row, i) in renderCodeLines" :key="i" class="code-line">
                      <span class="line-num">{{ row.num }}</span>
                      <span class="line-content">{{ row.line }}</span>
                    </span>
                  </pre>
                  
                  <Space class="code-pagination" @click.stop>
                    <Button 
                      size="small" 
                      :disabled="currentCodePage === 1" 
                      @click="prevCodePage($event)"
                    >
                      上一页
                    </Button>
                    <span>
                      第 {{ currentCodePage }} 页 / 共 {{ Math.ceil((currentCodeLines.length || 0) / codeLinesPerPage) }} 页
                    </span>
                    <Button 
                      size="small" 
                      :disabled="currentCodePage >= Math.ceil((currentCodeLines.length || 0) / codeLinesPerPage)" 
                      @click="nextCodePage($event)"
                    >
                      下一页
                    </Button>
                  </Space>
                </div>
              </Card>
            </div>
          </Tabs.TabPane>
        </Tabs>
      </Card>
    </div>
  </Page>
</template>

<style scoped>
.upload-hint {
  font-size: 13px;
  color: #faad14;
  margin-top: 8px;
}

.item-wrapper {
  margin-bottom: 12px;
}

/* 分组卡片样式 */
.group-content {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e8e8e8;
}

.active {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.15);
}

.expand-icon {
  color: #1890ff;
  font-size: 14px;
  transition: transform 0.2s;
}

/* 规则项样式 */
.rule-item {
  padding: 8px 12px;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  margin-bottom: 6px;
  transition: all 0.2s;
}

.rule-item:hover {
  border-color: #1890ff;
  background-color: #f0f7ff;
}

.rule-number {
  color: #8c8c8c;
  display: inline-block;
  width: 30px;
}

.rule-text {
  word-break: break-word;
}

/* 分页控件样式 */
.pagination-controls {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding: 8px;
}

/* 代码显示样式 */
.code-display {
  line-height: 1.6;
  font-family: "Fira Code", monospace;
  font-size: 13px;
  white-space: pre-wrap;
  max-height: 600px;
  overflow: auto;
}

.code-line {
  display: block;
}

.line-num {
  color: #999;
  display: inline-block;
  width: 45px;
  text-align: right;
  padding-right: 10px;
  border-right: 1px solid #d9d9d9;
  user-select: none;
}

.line-content {
  padding-left: 10px;
}

.code-pagination {
  display: flex;
  justify-content: center;
  margin-top: 12px;
  padding: 8px;
}
</style>
