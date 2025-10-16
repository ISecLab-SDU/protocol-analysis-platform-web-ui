<script lang="ts" setup>
import { onMounted, onBeforeUnmount, reactive, ref } from 'vue';
import { Page } from '@vben/common-ui';
import {
  Button,
  Card,
  Empty,
  Form,
  FormItem,
  Input,
  message,
  Modal,
  Progress,
  Space,
  Tabs,
  Tag,
  Upload,
} from 'ant-design-vue';
import type { FormInstance, UploadFile, UploadProps } from 'ant-design-vue';

const activeTab = ref('upload'); // upload | result
const isSubmitting = ref(false);
const isModalOpen = ref(false); // 若未来需要扩展，可保留
const formRef = ref<FormInstance>();

// 双文件上传
const rfcFileList = ref<UploadFile[]>([]);
const codeFileList = ref<UploadFile[]>([]);
const rfcFile = ref<File | null>(null);
const codeFile = ref<File | null>(null);

// 上传面板提示
const uploadTip = ref(
  '温馨提示：由于网络环境和设备性能差异，文件上传可能需要多次尝试才能成功。如遇上传失败，请检查网络连接后重试。'
);

// 结果数据
type RuleItem = { analysis: string; rule: string; code?: string };
let analysisCompleted = false;
const allData = ref<RuleItem[]>([]);
const analysisGroups = ref<Record<string, RuleItem[]>>({});
const lastFetchError = ref<null | string>(null);

// 左侧列表分页（按分组内规则分页）
const itemsPerPage = 5;
const currentPage = ref(1);
const totalPages = ref(1);
const currentRules = ref<RuleItem[]>([]);
const activeAnalysisKey = ref<string | null>(null);

// 右侧代码查看分页
const currentCodeLines = ref<string[]>([]);
const currentCodePage = ref(1);
const codeLinesPerPage = 32;

// 规则状态元数据（借鉴“新建文本文档.vue”的状态展示风格）
const statusMeta = {
  completed: { color: 'success', label: '解析完成' },
  failed: { color: 'error', label: '解析失败' },
  processing: { color: 'processing', label: '解析中' },
  queued: { color: 'default', label: '等待中' },
} as const;

// 表单简单校验（必须选择两文件）
const formRules = {
  rfc: [{ required: true, message: '请上传 RFC 文档', trigger: 'change' }],
  code: [{ required: true, message: '请上传源代码文件', trigger: 'change' }],
};

// Upload 受控处理
const beforeUploadRFC: UploadProps['beforeUpload'] = (file) => {
  rfcFileList.value = [file];
  const actual = (file as UploadFile<File>).originFileObj ?? (file as any as File);
  rfcFile.value = actual;
  formRef.value?.clearValidate?.(['rfc']);
  return false;
};
const beforeUploadCode: UploadProps['beforeUpload'] = (file) => {
  codeFileList.value = [file];
  const actual = (file as UploadFile<File>).originFileObj ?? (file as any as File);
  codeFile.value = actual;
  formRef.value?.clearValidate?.(['code']);
  return false;
};
const removeRFC: UploadProps['onRemove'] = () => {
  rfcFileList.value = [];
  rfcFile.value = null;
  formRef.value?.validateFields?.(['rfc']);
  return true;
};
const removeCode: UploadProps['onRemove'] = () => {
  codeFileList.value = [];
  codeFile.value = null;
  formRef.value?.validateFields?.(['code']);
  return true;
};

// 提交分析（调用你现有后端 /api/upload 成功后，再加载 /api/rules）
async function handleAnalyze() {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }
  if (!rfcFile.value || !codeFile.value) {
    message.error('请先选择 RFC 与源代码文件');
    return;
  }

  isSubmitting.value = true;
  const formData = new FormData();
  formData.append('rfc', rfcFile.value);
  formData.append('code', codeFile.value);

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    const result = await res.json();
    if (!result?.success) {
      throw new Error(result?.message || '上传失败');
    }
    // 可选：模拟分析过程进度
    await new Promise((r) => setTimeout(r, 1000));
    analysisCompleted = true;
    message.success('分析成功，切换到结果展示');
    activeTab.value = 'result';
    await loadRules();
  } catch (e: any) {
    message.error(`上传/分析失败：${e?.message || e}`);
  } finally {
    isSubmitting.value = false;
  }
}

async function loadRules() {
  if (!analysisCompleted) return;
  lastFetchError.value = null;
  try {
    const res = await fetch('/api/rules');
    if (!res.ok) throw new Error(`服务器错误 ${res.status}`);
    const data = (await res.json()) as RuleItem[];
    allData.value = data;
    // 分组
    const groups: Record<string, RuleItem[]> = {};
    data.forEach((item) => {
      if (!groups[item.analysis]) groups[item.analysis] = [];
      groups[item.analysis].push(item);
    });
    analysisGroups.value = groups;
  } catch (err: any) {
    lastFetchError.value = err?.message || String(err);
    message.error(`加载结果失败：${lastFetchError.value}`);
  }
}

// 展开某个分析组
function openAnalysisGroup(key: string) {
  activeAnalysisKey.value = key;
  currentPage.value = 1;
  currentRules.value = analysisGroups.value[key] || [];
  totalPages.value = Math.ceil((currentRules.value.length || 0) / itemsPerPage);
  // 重置右侧代码
  currentCodeLines.value = [];
  currentCodePage.value = 1;
}

// 左侧分页切换
function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--;
    // 切页时重置代码
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
  const end = start + itemsPerPage;
  return currentRules.value.slice(start, end);
}

// 点击规则，右侧显示代码
function openCode(item: RuleItem) {
  const text = item.code || '(无代码)';
  currentCodeLines.value = text.split(/\r?\n/);
  currentCodePage.value = 1;
}

// 右侧代码分页
function renderCodeLines() {
  const start = (currentCodePage.value - 1) * codeLinesPerPage;
  const end = start + codeLinesPerPage;
  return currentCodeLines.value.slice(start, end).map((line, idx) => {
    const num = start + idx + 1;
    return { num, line };
  });
}
function prevCodePage() {
  if (currentCodePage.value > 1) currentCodePage.value--;
}
function nextCodePage() {
  const total = Math.ceil((currentCodeLines.value.length || 0) / codeLinesPerPage);
  if (currentCodePage.value < total) currentCodePage.value++;
}

onMounted(() => {
  // 可根据需要做初始化提醒
});
onBeforeUnmount(() => {
  // 清理轮询等
});
</script>

<template>
  <Page title="RFC 规则查看系统" description="上传 RFC 与源代码，分析并查看匹配的规则及关联代码片段。">
    <div class="flex flex-col gap-4">
      <Card>
        <Space class="w-full justify-between" direction="horizontal">
          <div class="flex flex-col gap-2">
            <p class="intro-text">
              将 RFC 与源码交给系统解析后，我们会提取关键规则与对应代码片段，并支持分页查看与下载。
            </p>
            <p class="intro-helper">
              当前使用：<Tag color="blue">本地接口</Tag>
            </p>
            <p v-if="lastFetchError" class="intro-helper text-danger">
              {{ lastFetchError }}
            </p>
          </div>
          <Space>
            <Button @click="analysisCompleted ? loadRules() : message.info('请先完成分析')">
              刷新结果
            </Button>
          </Space>
        </Space>
      </Card>

      <Card>
        <Tabs v-model:activeKey="activeTab" destroyInactiveTabPane>
          <Tabs.TabPane key="upload" tab="上传 RFC 与源代码">
            <Form ref="formRef" :rules="formRules" layout="vertical">
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
                  <p class="upload-helper">支持 .txt / .pdf / .doc 等格式。</p>
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
                  <p class="upload-helper">支持多种语言代码文件。</p>
                </FormItem>
              </div>

              <div class="upload-hint">
                <span>{{ uploadTip }}</span>
              </div>

              <Space class="w-full justify-center mt-4">
                <Button
                  type="primary"
                  :loading="isSubmitting"
                  :disabled="!rfcFile || !codeFile"
                  @click="handleAnalyze"
                >
                  开始分析
                </Button>
              </Space>
            </Form>
          </Tabs.TabPane>

          <Tabs.TabPane key="result" tab="结果展示">
            <div class="flex flex-col lg:flex-row gap-4">
              <!-- 左侧分析结果与规则列表 -->
              <Card class="flex-1" title="分析结果列表" :body-style="{ padding: '16px' }">
                <template #extra>
                  <span class="text-secondary">
                    组数 {{ Object.keys(analysisGroups).length }}
                  </span>
                </template>

                <div v-if="!analysisCompleted">
                  <Empty description="请先上传文件并点击“开始分析”生成结果" />
                </div>

                <div v-else-if="Object.keys(analysisGroups).length === 0">
                  <Empty description="分析完成，但未找到匹配的规则" />
                </div>

                <div v-else class="flex flex-col gap-3">
                  <div
                    v-for="(rules, groupName, idx) in analysisGroups"
                    :key="groupName"
                    class="item-wrapper"
                  >
                    <Card
                      size="small"
                      class="cursor-pointer"
                      :class="{ active: activeAnalysisKey === groupName }"
                      @click="openAnalysisGroup(groupName)"
                    >
                      <template #title>
                        <Space>
                          <span class="analysis-number">{{ idx + 1 }}</span>
                          <span class="analysis-title">{{ groupName }}</span>
                          <Tag color="processing">{{ rules.length }} 条规则</Tag>
                        </Space>
                      </template>

                      <div v-if="activeAnalysisKey === groupName" class="flex flex-col gap-2 mt-2">
                        <div v-for="(item, i) in currentPageSlice()" :key="i" class="rule-item" @click.stop="openCode(item)">
                          <Space align="start">
                            <span class="rule-index">{{ (currentPage - 1) * itemsPerPage + i + 1 }}</span>
                            <span v-html="(item.rule || '').replace(/\b(?=\w*[A-Z])\w{2,}\b/g,'&lt;span class=&quot;rule-highlight&quot;&gt;$&amp;&lt;/span&gt;')"></span>
                          </Space>
                        </div>

                        <Space class="justify-center mt-2">
                          <Button size="small" :disabled="currentPage === 1" @click="prevPage">上一页</Button>
                          <span class="text-secondary">第 {{ currentPage }} 页 / 共 {{ totalPages }} 页</span>
                          <Button size="small" :disabled="currentPage >= totalPages" @click="nextPage">下一页</Button>
                        </Space>
                      </div>
                    </Card>
                  </div>
                </div>
              </Card>

              <!-- 右侧代码内容 -->
              <Card class="flex-1" title="代码内容" :body-style="{ padding: '16px' }">
                <div v-if="currentCodeLines.length === 0" class="py-12">
                  <Empty description="(尚未选择规则)" />
                </div>
                <div v-else id="codeDisplay" class="code-display">
                  <pre>
<span v-for="(row, i) in renderCodeLines()" :key="i">
  <span class="line-num">{{ row.num }}</span> <span>{{ row.line }}</span>
</span>
                  </pre>
                </div>
                <Space class="justify-center mt-2">
                  <Button size="small" :disabled="currentCodePage === 1" @click="prevCodePage">上一页</Button>
                  <span class="text-secondary">
                    第 {{ currentCodePage }} 页 / 共 {{ Math.ceil((currentCodeLines.length||0)/codeLinesPerPage) }} 页
                  </span>
                  <Button
                    size="small"
                    :disabled="currentCodePage >= Math.ceil((currentCodeLines.length||0)/codeLinesPerPage)"
                    @click="nextCodePage"
                  >
                    下一页
                  </Button>
                </Space>
              </Card>
            </div>
          </Tabs.TabPane>
        </Tabs>
      </Card>
    </div>

    <!-- 预留：如需弹窗创建任务，可复用 Modal -->
    <Modal v-model:open="isModalOpen" title="创建任务" :footer="null">
      <p>此弹窗占位，用于未来扩展。</p>
    </Modal>
  </Page>
</template>

<style scoped>
.intro-text {
  margin: 0;
  line-height: 1.6;
  color: var(--ant-text-color);
}
.intro-helper {
  margin: 0;
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}
.upload-helper {
  margin-top: 8px;
  margin-bottom: 0;
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}
.upload-hint {
  margin-top: 8px;
  font-size: 13px;
  color: var(--ant-text-color-secondary);
  background-color: #FFF8E6;
  border-left: 3px solid var(--ant-color-warning);
  padding: 12px 16px;
  border-radius: 0 4px 4px 0;
}
.item-wrapper { margin-bottom: 8px; }
.analysis-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--ant-color-primary);
  color: #fff;
  font-weight: 600;
  font-size: 12px;
}
.analysis-title { font-weight: 600; }
.rule-item {
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border);
  border-radius: 6px;
  padding: 10px 12px;
  cursor: pointer;
}
.rule-item:hover {
  border-color: var(--ant-color-primary);
  box-shadow: 0 0 0 2px rgba(22,93,255,0.15);
}
.rule-index {
  min-width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--ant-color-primary-bg);
  color: var(--ant-color-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 12px;
}
.rule-highlight {
  background-color: #FFF8E6;
  border-radius: 3px;
  padding: 0 3px;
  color: #E67700;
  font-weight: 500;
}
.code-display {
  line-height: 1.6;
  font-family: "Fira Code", "Consolas", monospace;
  font-size: 13px;
  white-space: pre-wrap;
}
.line-num {
  color: var(--ant-color-text-tertiary);
  display: inline-block;
  width: 40px;
  text-align: right;
  padding-right: 10px;
  border-right: 1px solid var(--ant-color-border);
  user-select: none;
}
.text-secondary {
  font-size: 13px;
  color: var(--ant-text-color-secondary);
}
.text-danger { color: var(--ant-color-error); }
</style>
