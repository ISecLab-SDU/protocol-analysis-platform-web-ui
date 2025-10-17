/**
 * Formal GPT API - 协议形式化验证相关接口
 */

// ==================== 类型定义 ====================

export interface IRDataItem {
  desc: string;
  direction?: string;
  expr?: string;
  id: string;
  label?: 'calculate' | 'generate' | 'message' | 'validate';
  operator?: string;
  receiver?: string;
  sender?: string;
}

export interface ProtocolIRItem {
  desc: string;
  expr?: string;  // ✅ 添加这一行
  id: string;
  operator?: string;
  receiver?: string;
  sender?: string;
}

export interface PropertyResult {
  id: string;
  message: string;
  name: string;
  result: 'FAILED' | 'UNKNOWN' | 'VERIFIED';
}

export interface VerificationResults {
  executionTime: string;
  properties: PropertyResult[];
  status: 'failed' | 'partial' | 'success';
}

export interface HistoryRecord {
  fileName: string;
  fileSize: number;
  id: string;
  protocolIR: ProtocolIRItem[];
  proverifCode?: string;
  selectedProperties: string[];
  sequenceData: any;
  uploadTime: string;
  verificationResults: VerificationResults | null;
}

export interface ApiResponse<T = any> {
  code?: number;
  data?: T;
  error?: string;
  message?: string;
  success?: boolean;
}

// ==================== 工具函数 ====================

export function transformIRDataForSequence(
  irData: IRDataItem[] | null,
): ProtocolIRItem[] {
  if (!irData || !Array.isArray(irData)) return [];

  return irData.map((item) => {
    const baseItem: ProtocolIRItem = {
      desc: item.desc || '',
      expr: item.expr || '',  // ✅ 添加这一行：保留 expr
      id: item.id,
    };

    if (item.sender && item.receiver) {
      return {
        ...baseItem,
        sender: item.sender,
        receiver: item.receiver,
      };
    }

    if (item.label === 'message') {
      const [sender, receiver] = (item.direction || '').split(' -> ');
      return {
        ...baseItem,
        receiver: receiver?.trim() || '',
        sender: sender?.trim() || '',
      };
    } else if (
      item.label === 'calculate' ||
      item.label === 'generate' ||
      item.label === 'validate'
    ) {
      return {
        ...baseItem,
        operator: item.operator || '',
      };
    }

    if (item.direction) {
      const [sender, receiver] = item.direction.split(' -> ');
      return {
        ...baseItem,
        receiver: receiver?.trim() || '',
        sender: sender?.trim() || '',
      };
    }

    if (item.operator) {
      return {
        ...baseItem,
        operator: item.operator,
      };
    }

    return baseItem;
  });
}

// ==================== API 接口 ====================

const BASE_PATH = '/api/formal-gpt';

export async function fetchFormalGptHistory(): Promise<HistoryRecord[]> {
  try {
    console.log('📡 调用 API:', `${BASE_PATH}/history`);
    
    const response = await fetch(`${BASE_PATH}/history`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const result: ApiResponse<any[]> = await response.json();
    
    console.log('📦 API 响应:', result);
    console.log('📦 code:', result.code);
    console.log('📦 data 条数:', result.data?.length);

    if (result.code === 0 && result.data) {
      console.log('✅ 解析成功，数据条数:', result.data.length);
      
      return result.data.map((protocol: any) => ({
        fileName: protocol.fileName,
        fileSize: protocol.fileSize,
        id: protocol.id,
        // ✅ 优先使用 modelData（时序图数据），否则使用 irData
        protocolIR: transformIRDataForSequence(protocol.modelData || protocol.irData),
        selectedProperties: protocol.selectedProperties || [],
        sequenceData: protocol.sequenceData,
        uploadTime: protocol.uploadTime,
        verificationResults: protocol.verificationResults,
      }));
    }

    throw new Error(result.error || '获取历史记录失败');
  } catch (error: any) {
    console.error('❌ fetchFormalGptHistory 错误:', error);
    throw error;
  }
}

export async function fetchFormalGptProtocolDetail(protocolId: string) {
  try {
    console.log('📡 调用 API:', `${BASE_PATH}/protocol/${protocolId}`);
    
    const response = await fetch(`${BASE_PATH}/protocol/${protocolId}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const result: ApiResponse<any> = await response.json();
    
    console.log('📦 协议详情响应:', result);

    if (result.code === 0 && result.data) {
      console.log('✅ 协议详情解析成功');
      return result.data;
    }

    throw new Error(result.error || '获取协议详情失败');
  } catch (error: any) {
    console.error('❌ fetchFormalGptProtocolDetail 错误:', error);
    throw error;
  }
}