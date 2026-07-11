/**
 * Formal GPT API - 协议形式化验证相关接口
 */

// ==================== 类型定义 ====================

export interface UploadFileResponse {
  fileId: string;
  fileName: string;
  fileSize: number;
  filePath: string;
  uploadTime: string;
}

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
  expr?: string; // ✅ 添加这一行
  id: string;
  operator?: string;
  receiver?: string;
  sender?: string;
}

export interface PropertyResult {
  property: string;
  query: string;
  result: boolean;
  // 兼容旧版或未来扩展
  id?: string;
  name?: string;
  message?: string;
}

export interface VerificationResults {
  protocol: string;
  security_properties: PropertyResult[];
  // 兼容旧版或未来扩展
  executionTime?: string;
  status?: 'failed' | 'partial' | 'success';
  properties?: PropertyResult[];
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
  verificationResults: null | VerificationResults;
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
      expr: item.expr || '', // ✅ 添加这一行：保留 expr
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

// ==================== 文件上传接口 ====================

/**
 * 上传协议文件
 * @param file - 要上传的文件对象
 * @returns 上传结果，包含文件ID等信息
 */
export async function uploadProtocolFile(
  file: File,
): Promise<UploadFileResponse> {
  try {
    console.warn('📤 开始上传文件:', file.name);

    // 创建 FormData 对象
    const formData = new FormData();
    formData.append('file', file);

    // 发送请求
    const response = await fetch(`${BASE_PATH}/upload`, {
      method: 'POST',
      body: formData,
      // 注意：不要设置 Content-Type，让浏览器自动设置
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result: ApiResponse<UploadFileResponse> = await response.json();

    console.warn('📦 上传响应:', result);

    if (result.code === 0 && result.data) {
      console.warn('✅ 文件上传成功:', result.data);
      return result.data;
    }

    throw new Error(result.error || '文件上传失败');
  } catch (error: any) {
    console.error('❌ uploadProtocolFile 错误:', error);
    throw error;
  }
}

const BASE_PATH = '/api/formal-gpt';

export async function fetchFormalGptHistory(): Promise<HistoryRecord[]> {
  try {
    console.warn('📡 调用 API:', `${BASE_PATH}/history`);

    const response = await fetch(`${BASE_PATH}/history`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result: ApiResponse<any[]> = await response.json();

    console.warn('📦 API 响应:', result);
    console.warn('📦 code:', result.code);
    console.warn('📦 data 条数:', result.data?.length);

    if (result.code === 0 && result.data) {
      console.warn('✅ 解析成功，数据条数:', result.data.length);

      return result.data.map((protocol: any) => ({
        fileName: protocol.fileName,
        fileSize: protocol.fileSize,
        id: protocol.id,
        // ✅ 优先使用 modelData（时序图数据），否则使用 irData
        protocolIR: transformIRDataForSequence(
          protocol.modelData || protocol.irData,
        ),
        proverifCode: protocol.proverifCode, // 新增：从后端获取 ProVerif 代码
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
    console.warn('📡 调用 API:', `${BASE_PATH}/protocol/${protocolId}`);

    const response = await fetch(`${BASE_PATH}/protocol/${protocolId}`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result: ApiResponse<any> = await response.json();

    console.warn('📦 协议详情响应:', result);

    if (result.code === 0 && result.data) {
      console.warn('✅ 协议详情解析成功');
      return result.data;
    }

    throw new Error(result.error || '获取协议详情失败');
  } catch (error: any) {
    console.error('❌ fetchFormalGptProtocolDetail 错误:', error);
    throw error;
  }
}

/**
 * 执行协议安全验证
 */
export async function runProtocolVerification(
  protocolId: string,
  selectedProperties: string[],
): Promise<VerificationResults> {
  const response = await fetch(`${BASE_PATH}/verify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      protocolId,
      selectedProperties,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const result: ApiResponse<VerificationResults> = await response.json();

  if (result.code === 0 && result.data) {
    return result.data;
  }

  throw new Error(result.error || '验证失败');
}
