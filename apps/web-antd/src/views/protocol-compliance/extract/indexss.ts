<script lang="ts" setup>
import { ref, reactive, computed, h } from 'vue';
import { Card, Empty, Space, Button, Tag, message, Input, Upload, Spin, Table, Typography, Divider, Modal } from 'ant-design-vue';
import type { UploadFile, UploadProps, TableColumnType } from 'ant-design-vue';

// 类型定义
type RuleItem = {
  rule: string;
  req_type: string;
  req_fields: string[];
  res_type: string;
  res_fields: string[];
};

// 状态管理
const activeMenuKey = ref('upload');
const isAnalyzing = ref(false);
const analysisCompleted = ref(false);
const stagedResults = ref<RuleItem[]>([]);

// 上传相关
const rfcFileList = ref<UploadFile[]>([]);
const formData = reactive({
  protocol: '',
});
const supportedProtocols = [
  'TLSv1_3', 'CoAP', 
  'DHCPv6', 'FTP', 'MQTTv3_1_1', 'MQTTv5'
];

// 表格分页
const currentPage = ref(1);
const pageSize = ref(10);
const totalItems = ref(0);

// 上传控制
const beforeUploadRFC: UploadProps['beforeUpload'] = (file) => {
  const allowedTypes = ['application/pdf', 'text/plain', 'application/json'];
  const isAllowed = allowedTypes.includes(file.type);
  const isAllowedExt = ['.pdf', '.txt', '.json'].some(ext =>
    file.name.toLowerCase().endsWith(ext)
  );

  if (!isAllowed && !isAllowedExt) {
    message.error('仅支持上传 PDF、TXT 或 JSON 格式的 RFC 文件');
    return false;
  }

  rfcFileList.value = [file];
  return false;
};

const removeRFC: UploadProps['onRemove'] = () => {
  rfcFileList.value = [];
  return true;
};

// ✅ 协议名标准化函数
function normalizeProtocolName(input: string) {
  return input
    .trim()
    .replace(/\s+/g, '')
    .replace(/[._]+/g, '-')
    .replace(/[^a-zA-Z0-9\-\/]/g, '')
    .toLowerCase();
}

// 开始分析
async function startAnalysis() {
  console.log('当前协议输入值:', formData.protocol);

  if (rfcFileList.value.length === 0) {
    message.warning('请先上传 RFC 文件');
    return;
  }

  if (!formData.protocol.replace(/\s/g, '')) {
    message.warning('请输入协议类型');
    return;
  }

  isAnalyzing.value = true;
  analysisCompleted.value = false;
  stagedResults.value = [];

  try {
    await new Promise(resolve => setTimeout(resolve, 1500));

    const normalizedProtocol = normalizeProtocolName(formData.protocol);
    const fileName = `ruleConfig_${normalizedProtocol}.json`;
    const response = await fetch(`/${fileName}`);

    if (!response.ok) {
      throw new Error(`未找到 ${formData.protocol} 对应的规则文件`);
    }

    const rawData = await response.json();

    console.log('读取到的规则原始数据:', rawData);

    let rules: RuleItem[] = [];

    // ✅ 自动兼容对象或数组结构
    if (Array.isArray(rawData)) {
      rules = rawData;
    } else if (typeof rawData === 'object' && rawData !== null) {
      Object.keys(rawData).forEach(key => {
        const arr = rawData[key];
        if (Array.isArray(arr)) {
          rules.push(...arr);
        }
      });
    } else {
      throw new Error('规则文件格式不正确，应为数组或对象类型');
    }

    if (rules.length === 0) {
      throw new Error('未在规则文件中找到任何规则数据');
    }

    stagedResults.value = rules;
    totalItems.value = rules.length;
    analysisCompleted.value = true;

    activeMenuKey.value = 'result';
    message.success(`成功加载 ${rules.length} 条规则`);
  } catch (err: any) {
    message.error(`分析失败: ${err.message}`);
  } finally {
    isAnalyzing.value = false;
  }
}

// 规则详情
const currentRule = ref<RuleItem | null>(null);
const showDetailModal = ref(false);

function showRuleDetails(rule: RuleItem) {
  currentRule.value = rule;
  showDetailModal.value = true;
}

// 表格列定义
const columns: TableColumnType<RuleItem>[] = [
  {
    title: '序号',
    dataIndex: 'index',
    key: 'index',
    width: 80,
    render: (_, __, index) => (currentPage.value - 1) * pageSize.value + index + 1,
  },
  { title: '规则描述', dataIndex: 'rule', key: 'rule', ellipsis: { showTitle: true } },
  { title: '协议消息类型', dataIndex: 'req_type', key: 'req_type' },
  {
    title: '操作',
    key: 'action',
    width: 120,
    render: (_, record) =>
      h(Button, { type: 'text', size: 'small', onClick: () => showRuleDetails(record) }, { default: () => '查看详情' }),
  },
];

// 分页变更
function handleTableChange(pagination: any) {
  currentPage.value = pagination.current;
  pageSize.value = pagination.pageSize;
}

// 当前页数据
const currentPageData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return stagedResults.value.slice(start, start + pageSize.value);
});
</script>

<template>
  <div class="page-container">
    <Typography.Title level="2">RFC 规则提取系统</Typography.Title>
    <Typography.Paragraph>上传 RFC 文件并提取协议规则</Typography.Paragraph>

    <div class="main-container">
      <div class="menu-bar">
        <Button 
          type="primary" 
          :ghost="activeMenuKey !== 'upload'"
          @click="activeMenuKey = 'upload'"
          style="margin-right: 8px;"
        >
          上传 RFC 文件
        </Button>
        <Button 
          type="primary" 
          :ghost="activeMenuKey !== 'result'"
          @click="activeMenuKey = 'result'"
          :disabled="!analysisCompleted"
        >
          结果展示
        </Button>
      </div>

      <Divider style="margin: 16px 0;" />

      <!-- 上传页面 -->
      <Card v-if="activeMenuKey === 'upload'">
        <div class="upload-container">
          <div class="upload-info">
            <Typography.Title level="4">上传 RFC 文件并指定协议</Typography.Title>
            <Typography.Paragraph>
              上传 RFC 文档后，系统将分析并提取其中的协议规则。
            </Typography.Paragraph>

            <div class="protocol-hint">
              <Typography.Text strong>支持的协议类型：</Typography.Text>
              <Space size="small" wrap>
                <Tag v-for="proto in supportedProtocols" :key="proto" color="blue">{{ proto }}</Tag>
              </Space>
            </div>
          </div>

          <div class="upload-form">
            <div class="form-item">
              <Typography.Text strong>协议类型：</Typography.Text>
              <Input
                v-model:value.trim="formData.protocol"
                placeholder="请输入协议类型（如 TLS、MQTTv5）"
                style="width: 300px; margin-left: 8px;"
              />
            </div>

            <div class="form-item">
              <Typography.Text strong>RFC 文件：</Typography.Text>
              <Upload
                :file-list="rfcFileList"
                :before-upload="beforeUploadRFC"
                :on-remove="removeRFC"
                :max-count="1"
                style="margin-left: 8px;"
              >
                <Button>选择文件</Button>
              </Upload>
            </div>

            <div class="analysis-btn">
              <Button type="primary" :loading="isAnalyzing" @click="startAnalysis" :disabled="isAnalyzing">
                开始分析
              </Button>
            </div>
          </div>

          <div v-if="isAnalyzing" class="analyzing-state">
            <Spin size="large" tip="正在分析 RFC 文件，提取规则中...">
              <div class="spin-content"></div>
            </Spin>
          </div>
        </div>
      </Card>

      <!-- 结果展示页面 -->
      <Card v-if="activeMenuKey === 'result'">
        <div class="result-header">
          <Typography.Title level="4">{{ formData.protocol }} 协议规则提取结果</Typography.Title>
          <Typography.Text>共提取到 {{ totalItems }} 条规则</Typography.Text>
        </div>

        <div v-if="stagedResults.length === 0">
          <Empty description="未找到规则数据" />
        </div>
        <div v-else>
          <Table
            :columns="columns"
            :data-source="currentPageData"
            :pagination="{
              current: currentPage,
              pageSize: pageSize,
              total: totalItems,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条规则`
            }"
            :row-key="(record, index) => index"
            @change="handleTableChange"
            bordered
          />
        </div>
      </Card>
    </div>

    <!-- 规则详情 -->
    <Modal v-model:visible="showDetailModal" title="规则详情" :width="700" destroy-on-close>
      <template v-if="currentRule">
        <div class="rule-detail">
          <Typography.Title level="5">规则描述</Typography.Title>
          <Typography.Paragraph>{{ currentRule.rule }}</Typography.Paragraph>
          <Divider />
          <Typography.Title level="5">发送消息信息</Typography.Title>
          <p><strong>消息类型：</strong>{{ currentRule.req_type }}</p>
          <p><strong>涉及字段：</strong></p>
          <Tag v-for="f in currentRule.req_fields" :key="f" color="blue">{{ f }}</Tag>
          <Divider />
          <Typography.Title level="5">返回消息信息</Typography.Title>
          <p><strong>消息类型：</strong>{{ currentRule.res_type }}</p>
          <Tag v-for="f in currentRule.res_fields" :key="f" color="green">{{ f }}</Tag>
        </div>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.page-container { padding: 24px; }
.main-container { max-width: 1200px; margin: 0 auto; }
.menu-bar { margin-bottom: 16px; }
.upload-container { padding: 24px; }
.upload-info { margin-bottom: 24px; }
.protocol-hint { margin: 16px 0; padding: 12px; background-color: #f5f7fa; border-radius: 4px; }
.upload-form { display: flex; flex-direction: column; gap: 24px; align-items: flex-start; }
.form-item { display: flex; align-items: center; width: 100%; }
.analysis-btn { margin-top: 16px; align-self: flex-start; }
.analyzing-state { margin-top: 32px; display: flex; justify-content: center; align-items: center; padding: 40px 0; }
.spin-content { height: 100px; }
.result-header { margin-bottom: 24px; }
.rule-detail { padding: 8px 0; }
</style>
