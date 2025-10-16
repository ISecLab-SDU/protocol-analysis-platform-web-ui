<script lang="ts" setup>
import { ref, reactive } from 'vue';
import { Page } from '@vben/common-ui';
import {
  Button,
  Card,
  Empty,
  Form,
  FormItem,
  message,
  Space,
  Tabs,
  Tag,
  Upload,
} from 'ant-design-vue';
import type { FormInstance, UploadFile, UploadProps } from 'ant-design-vue';

const activeTab = ref('upload'); // upload | result
const isSubmitting = ref(false);
const formRef = ref<FormInstance>();

// 表单数据模型，与Form的name字段绑定
const formData = reactive({
  rfc: null as File | null,
  code: null as File | null,
});

// 双文件上传列表
const rfcFileList = ref<UploadFile[]>([]);
const codeFileList = ref<UploadFile[]>([]);

// 上传提示
const uploadTip = ref(
  '温馨提示：上传文件后，系统会模拟分析并显示规则与代码。'
);

// 结果数据
type RuleItem = { analysis: string; rule: string; code?: string };
let analysisCompleted = false;
const allData = ref<RuleItem[]>([]);
const analysisGroups = ref<Record<string, RuleItem[]>>({});
const lastFetchError = ref<null | string>(null);

// 左侧列表分页
const itemsPerPage = 5;
const currentPage = ref(1);
const totalPages = ref(1);
const currentRules = ref<RuleItem[]>([]);
const activeAnalysisKey = ref<string | null>(null);

// 右侧代码查看分页
const currentCodeLines = ref<string[]>([]);
const currentCodePage = ref(1);
const codeLinesPerPage = 32;

// 表单规则
const formRules = {
  rfc: [{ required: true, message: '请上传 RFC 文档', trigger: 'change' }],
  code: [{ required: true, message: '请上传源代码文件', trigger: 'change' }],
};

// Upload 控制：RFC 文档
const beforeUploadRFC: UploadProps['beforeUpload'] = (file) => {
  rfcFileList.value = [file];
  // 同步到formData，让Form感知文件
  formData.rfc = (file as UploadFile<File>).originFileObj ?? (file as any as File);
  formRef.value?.clearValidate?.(['rfc']);
  return false;
};
const removeRFC: UploadProps['onRemove'] = () => {
  rfcFileList.value = [];
  formData.rfc = null; // 清空formData字段
  formRef.value?.validateFields?.(['rfc']);
  return true;
};

// Upload 控制：源代码
const beforeUploadCode: UploadProps['beforeUpload'] = (file) => {
  codeFileList.value = [file];
  // 同步到formData，让Form感知文件
  formData.code = (file as UploadFile<File>).originFileObj ?? (file as any as File);
  formRef.value?.clearValidate?.(['code']);
  return false;
};
const removeCode: UploadProps['onRemove'] = () => {
  codeFileList.value = [];
  formData.code = null; // 清空formData字段
  formRef.value?.validateFields?.(['code']);
  return true;
};

// 模拟分析
async function handleAnalyze() {
  try {
    // 表单验证通过后执行分析
    await formRef.value?.validate();
  } catch {
    return;
  }

  isSubmitting.value = true;

  try {
    // 模拟上传+分析耗时
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

// 加载规则
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

    // 分组
    const groups: Record<string, RuleItem[]> = {};
    data.forEach(item => {
      if (!groups[item.analysis]) groups[item.analysis] = [];
      groups[item.analysis].push(item);
    });
    analysisGroups.value = groups;
  } catch (err: any) {
    lastFetchError.value = String(err);
    message.error(`加载结果失败：${lastFetchError.value}`);
  }
}

// 展开某组
function openAnalysisGroup(key: string) {
  activeAnalysisKey.value = key;
  currentPage.value = 1;
  currentRules.value = analysisGroups.value[key] || [];
  totalPages.value = Math.ceil((currentRules.value.length || 0) / itemsPerPage);
  currentCodeLines.value = [];
  currentCodePage.value = 1;
}

// 左侧分页
function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--;
    currentCodeLines.value = [];
    currentCodePage.value = 1;
  }
}
function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
    currentCodeLines.value = [];
    currentCodePage.value = 1;
  }
}
function currentPageSlice() {
  const start = (currentPage.value - 1) * itemsPerPage;
  return currentRules.value.slice(start, start + itemsPerPage);
}

// 点击规则显示代码
function openCode(item: RuleItem) {
  currentCodeLines.value = (item.code || '(无代码)').split(/\r?\n/);
  currentCodePage.value = 1;
}

// 右侧代码分页
function renderCodeLines() {
  const start = (currentCodePage.value - 1) * codeLinesPerPage;
  return currentCodeLines.value.slice(start, start + codeLinesPerPage).map((line, idx) => ({
    num: start + idx + 1,
    line
  }));
}
function prevCodePage() { if (currentCodePage.value > 1) currentCodePage.value--; }
function nextCodePage() {
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
            <!-- 绑定formData到Form -->
            <Form ref="formRef" :model="formData" :rules="formRules" layout="vertical">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormItem name="rfc" label="RFC 文档" required>
                  <Upload :file-list="rfcFileList" :before-upload="beforeUploadRFC" :on-remove="removeRFC" :max-count="1">
                    <Button block>选择 RFC 文档</Button>
                  </Upload>
                </FormItem>
                <FormItem name="code" label="源代码" required>
                  <Upload :file-list="codeFileList" :before-upload="beforeUploadCode" :on-remove="removeCode" :max-count="1">
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
                    <Card size="small" class="cursor-pointer" :class="{ active: activeAnalysisKey === groupName }" @click="openAnalysisGroup(groupName)">
                      <template #title>
                        <Space>
                          <span>{{ idx + 1 }}. {{ groupName }}</span>
                          <Tag color="processing">{{ rules.length }} 条规则</Tag>
                        </Space>
                      </template>
                      <div v-if="activeAnalysisKey === groupName">
                        <div v-for="(item, i) in currentPageSlice()" :key="i" class="rule-item" @click.stop="openCode(item)">
                          <span>{{ (currentPage-1)*itemsPerPage + i + 1 }}. </span>
                          <span>{{ item.rule }}</span>
                        </div>
                        <Space class="justify-center mt-2">
                          <Button size="small" :disabled="currentPage===1" @click="prevPage">上一页</Button>
                          <span>第 {{ currentPage }} 页 / 共 {{ totalPages }} 页</span>
                          <Button size="small" :disabled="currentPage>=totalPages" @click="nextPage">下一页</Button>
                        </Space>
                      </div>
                    </Card>
                  </div>
                </div>
              </Card>

              <!-- 右侧代码 -->
              <Card class="flex-1" title="代码内容">
                <div v-if="currentCodeLines.length === 0"><Empty description="尚未选择规则" /></div>
                <div v-else class="code-display">
                  <pre>
<span v-for="(row, i) in renderCodeLines()" :key="i">
  <span class="line-num">{{ row.num }}</span> {{ row.line }}
</span>
                  </pre>
                  <Space class="justify-center mt-2">
                    <Button size="small" :disabled="currentCodePage===1" @click="prevCodePage">上一页</Button>
                    <span>第 {{ currentCodePage }} 页 / 共 {{ Math.ceil((currentCodeLines.length||0)/codeLinesPerPage) }} 页</span>
                    <Button size="small" :disabled="currentCodePage>=Math.ceil((currentCodeLines.length||0)/codeLinesPerPage)" @click="nextCodePage">下一页</Button>
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
.upload-hint { font-size: 13px; color: #faad14; margin-top: 8px; }
.item-wrapper { margin-bottom: 8px; }
.rule-item { padding: 6px 10px; border: 1px solid #d9d9d9; margin-bottom: 4px; cursor: pointer; }
.rule-item:hover { border-color: #1890ff; }
.code-display { line-height: 1.6; font-family: "Fira Code", monospace; font-size: 13px; white-space: pre-wrap; }
.line-num { color: #999; display: inline-block; width: 40px; text-align: right; padding-right: 8px; border-right: 1px solid #d9d9d9; user-select: none; }
</style>
