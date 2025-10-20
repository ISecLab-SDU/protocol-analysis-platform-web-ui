<script lang="ts" setup>  
import { ref, reactive, computed } from 'vue';  
import { useRoute } from 'vue-router';  
import type { UploadFile, UploadProps } from 'ant-design-vue';  
import {  
  Card,  
  Tabs,  
  TabPane,  
  Form,  
  FormItem,  
  Input,  
  Button,  
  Table,  
  Tag,  
  Space,  
  message,  
  Divider,  
  Empty,  
  Upload  
} from 'ant-design-vue';  
import { getDetectionResults, addAnalysisHistory, getAnalysisHistory } from '#/api/protocol-compliance';  
  
// 类型定义  
interface DetectionResult {  
  id: number;  
  rule_desc: string;  
  code_snippet: string;  
  llm_response: {  
    result: string;  
    reason: string;  
  };  
}  
  
interface HistoryRecord {  
  id: string;  
  implementationName: string;  
  protocolName: string;  
  statistics: {  
    total: number;  
    violations: number;  
    noViolations: number;  
    noResult: number;  
  };  
  createdAt: string;  
}  
  
// 路由与标题  
const route = useRoute();  
const title = computed(() => String(route.meta?.title ?? '静态规则分析'));  
  
// 标签页状态  
const activeTab = ref('input');  
  
// 文件列表状态  
const rulesFileList = ref<UploadFile[]>([]);  
const sourceCodeFileList = ref<UploadFile[]>([]);  
  
// 第一个标签页:输入表单  
const formData = reactive({  
  protocolName: '',  
  implementationName: '',  
  rulesFile: null as File | null,  
  sourceCodeFile: null as File | null  
});  
const formLoading = ref(false);  
  
// 第二个标签页:检测结果  
const detectionResults = ref<DetectionResult[]>([]);  
const detectionLoading = ref(false);  
  
// 第三个标签页:历史记录  
const historyRecords = ref<HistoryRecord[]>([]);  
const historyLoading = ref(false);  
  
// 规则文件上传控制  
const beforeUploadRules: UploadProps['beforeUpload'] = (file) => {  
  rulesFileList.value = [file];  
  formData.rulesFile = (file as UploadFile<File>).originFileObj ?? (file as any as File);  
  return false; // 阻止自动上传  
};  
  
const removeRules: UploadProps['onRemove'] = () => {  
  rulesFileList.value = [];  
  formData.rulesFile = null;  
  return true;  
};  
  
// 源代码文件上传控制  
const beforeUploadSourceCode: UploadProps['beforeUpload'] = (file) => {  
  sourceCodeFileList.value = [file];  
  formData.sourceCodeFile = (file as UploadFile<File>).originFileObj ?? (file as any as File);  
  return false; // 阻止自动上传  
};  
  
const removeSourceCode: UploadProps['onRemove'] = () => {  
  sourceCodeFileList.value = [];  
  formData.sourceCodeFile = null;  
  return true;  
};  
  
// 检查是否可以开始分析  
const canStartAnalysis = computed(() => {  
  return !!(  
    formData.protocolName &&   
    formData.implementationName &&   
    formData.rulesFile &&   
    formData.sourceCodeFile  
  );  
});  
  
// 表格列定义 - 检测结果  
const detectionColumns = [  
  {  
    title: '原始规则',  
    dataIndex: 'rule_desc',  
    key: 'rule_desc',  
    width: '25%',  
    ellipsis: true  
  },  
  {  
    title: '代码切片',  
    dataIndex: 'code_snippet',  
    key: 'code_snippet',  
    width: '35%'  
  },  
  {  
    title: '分析结果',  
    dataIndex: 'llm_response',  
    key: 'llm_response',  
    width: '40%'  
  }  
];  
  
// 表格列定义 - 历史记录  
const historyColumns = [  
  {  
    title: '协议实现',  
    dataIndex: 'implementationName',  
    key: 'implementationName',  
    width: '25%'  
  },  
  {  
    title: '协议类型',  
    dataIndex: 'protocolName',  
    key: 'protocolName',  
    width: '20%'  
  },  
  {  
    title: '分析结果',  
    key: 'statistics',  
    width: '55%'  
  }  
];  
  
// 开始分析  
async function handleStartAnalysis() {  
  if (!formData.protocolName || !formData.implementationName) {  
    message.error('请填写协议名称和协议实现名称');  
    return;  
  }  
  
  if (!formData.rulesFile || !formData.sourceCodeFile) {  
    message.error('请上传规则文件和源代码文件');  
    return;  
  }  
  
  formLoading.value = true;  
    
  try {  
    // 显示分析中的提示  
    message.loading('正在分析结果，请稍候...', 0);  
      
    // 模拟分析过程，等待5秒  
    await new Promise(resolve => setTimeout(resolve, 5000));  
      
    // 关闭加载提示  
    message.destroy();  
      
    // 从数据库读取检测结果  
    const response = await getDetectionResults(formData.implementationName);  
    detectionResults.value = response.items;  
      
    // 添加到历史记录  
    await addAnalysisHistory({  
      implementationName: formData.implementationName,  
      protocolName: formData.protocolName  
    });  
      
    // 切换到检测结果标签页  
    activeTab.value = 'detection';  
    message.success('分析完成');  
  } catch (error: any) {  
    message.destroy();  
    message.error(error.message || '加载失败');  
  } finally {  
    formLoading.value = false;  
  }  
}  
  
// 加载历史记录  
async function loadHistory() {  
  historyLoading.value = true;  
  try {  
    const response = await getAnalysisHistory();  
    historyRecords.value = response.items;  
  } catch (error: any) {  
    message.error('加载历史记录失败');  
  } finally {  
    historyLoading.value = false;  
  }  
}  
  
// 查看历史记录详情  
async function viewHistoryDetail(record: HistoryRecord) {  
  formData.implementationName = record.implementationName;  
  formData.protocolName = record.protocolName;  
    
  detectionLoading.value = true;  
  try {  
    const response = await getDetectionResults(record.implementationName);  
    detectionResults.value = response.items;  
    activeTab.value = 'detection';  
  } catch (error: any) {  
    message.error('加载失败');  
  } finally {  
    detectionLoading.value = false;  
  }  
}  
  
// 结果状态颜色  
function getResultColor(result: string): string {  
  const lowerResult = result.toLowerCase();  
  if (lowerResult.includes('no violation')) return 'green';  
  if (lowerResult.includes('violation')) return 'red';  
  return 'orange';  
}  
  
// 结果状态文本  
function getResultText(result: string): string {  
  const lowerResult = result.toLowerCase();  
  if (lowerResult.includes('no violation')) return '✓ 符合规则';  
  if (lowerResult.includes('violation')) return '✗ 违反规则';  
  return '⚠ 需要审查';  
}  
  
// 标签页切换时加载历史记录  
function handleTabChange(key: string) {  
  if (key === 'history') {  
    loadHistory();  
  }  
}  
</script>  
  
<template>  
  <div class="static-analysis-page">  
    <div class="page-header">  
      <h1>{{ title }}</h1>  
      <p>协议合规性静态分析 - 上传文件并输入协议信息查看分析结果</p>  
    </div>  
  
    <Card>  
      <Tabs v-model:activeKey="activeTab" @change="handleTabChange">  
        <!-- 第一个标签页:输入 -->  
        <TabPane key="input" tab="输入协议信息">  
          <Form :model="formData" layout="vertical" style="max-width: 600px; margin: 0 auto;">  
            <!-- 规则文件上传 -->  
            <FormItem label="规则文件">  
              <Upload  
                :file-list="rulesFileList"  
                :before-upload="beforeUploadRules"  
                :on-remove="removeRules"  
                :max-count="1"  
              >  
                <Button block>选择规则文件</Button>  
              </Upload>  
            </FormItem>  
              
            <!-- 源代码文件上传 -->  
            <FormItem label="协议源代码实现">  
              <Upload  
                :file-list="sourceCodeFileList"  
                :before-upload="beforeUploadSourceCode"  
                :on-remove="removeSourceCode"  
                :max-count="1"  
              >  
                <Button block>选择源代码文件</Button>  
              </Upload>  
            </FormItem>  
              
            <Divider />  
              
            <!-- 协议信息输入 -->  
            <FormItem label="协议名称" required>  
              <Input   
                v-model:value="formData.protocolName"   
                placeholder="例如: MQTT"  
              />  
            </FormItem>  
              
            <FormItem label="协议实现名称" required>  
              <Input   
                v-model:value="formData.implementationName"   
                placeholder="例如: mosquitto"  
              />  
            </FormItem>  
              
            <FormItem>  
              <Button   
                type="primary"   
                :loading="formLoading"  
                :disabled="!canStartAnalysis"  
                @click="handleStartAnalysis"  
                block  
              >  
                开始分析  
              </Button>  
            </FormItem>  
          </Form>  
        </TabPane>  
  
        <!-- 第二个标签页:检测结果 -->  
        <TabPane key="detection" tab="代码切片与检测">  
          <div v-if="detectionResults.length === 0">  
            <Empty description="暂无检测结果,请先输入协议信息" />  
          </div>  
            
          <Table  
            v-else  
            :columns="detectionColumns"  
            :data-source="detectionResults"  
            :loading="detectionLoading"  
            :pagination="{  
              pageSize: 10,  
              showSizeChanger: true,  
              showTotal: (total) => `共 ${total} 条记录`  
            }"  
            :scroll="{ x: 1200 }"  
          >  
            <template #bodyCell="{ column, record }">  
              <!-- 代码切片列 -->  
              <template v-if="column.key === 'code_snippet'">  
                <pre class="code-snippet">{{ record.code_snippet }}</pre>  
              </template>  
                
              <!-- 分析结果列 -->  
              <template v-if="column.key === 'llm_response'">  
                <div class="analysis-result">  
                  <Tag :color="getResultColor(record.llm_response.result)">  
                    {{ getResultText(record.llm_response.result) }}  
                  </Tag>  
                  <Divider style="margin: 8px 0;" />  
                  <div class="reason-text">  
                    <strong>详细说明:</strong>  
                    <p>{{ record.llm_response.reason }}</p>  
                  </div>  
                </div>  
              </template>  
            </template>  
          </Table>  
        </TabPane>  
  
        <!-- 第三个标签页:历史记录 -->  
        <TabPane key="history" tab="历史记录">  
          <Table  
            :columns="historyColumns"  
            :data-source="historyRecords"  
            :loading="historyLoading"  
            :pagination="{  
              pageSize: 10,  
              showTotal: (total) => `共 ${total} 条记录`  
            }"  
          >  
            <template #bodyCell="{ column, record }">  
              <!-- 协议实现列 - 可点击 -->  
              <template v-if="column.key === 'implementationName'">  
                <a @click="viewHistoryDetail(record)">{{ record.implementationName }}</a>  
              </template>  
                
              <!-- 统计信息列 -->  
              <template v-if="column.key === 'statistics'">  
                <Space>  
                  <span>总数: {{ record.statistics.total }}</span>  
                  <Tag color="red">违规: {{ record.statistics.violations }}</Tag>  
                  <Tag color="green">符合: {{ record.statistics.noViolations }}</Tag>  
                  <Tag color="orange">待定: {{ record.statistics.noResult }}</Tag>  
                </Space>  
              </template>  
            </template>  
          </Table>  
        </TabPane>  
      </Tabs>  
    </Card>  
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
  
.code-snippet {  
  margin: 0;  
  padding: 8px;  
  background: #f5f5f5;  
  border-radius: 4px;  
  font-family: "Fira Code", "Consolas", monospace;  
  font-size: 12px;  
  line-height: 1.6;  
  white-space: pre-wrap;  
  word-break: break-all;  
  max-height: 200px;  
  overflow-y: auto;  
}  
  
.analysis-result {  
  padding: 8px 0;  
}  
  
.reason-text {  
  margin-top: 8px;  
}  
  
.reason-text p {  
  margin: 4px 0;  
  line-height: 1.6;  
  white-space: pre-wrap;  
  word-break: break-word;  
}  
</style>
