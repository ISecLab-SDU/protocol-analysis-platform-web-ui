import { message } from 'ant-design-vue';

import { baseRequestClient } from './request';

// 分析固件的API函数 - 适配前端传入的参数结构
export async function analyzeFirmware(params: {
  file: File;
  fileName: string;
  fileSize: number;
}): Promise<any> {
  const { fileName, fileSize, file } = params;

  // 调用后端API上传文件并进行分析
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('fileName', fileName);
    formData.append('fileSize', fileSize.toString());

    // 使用baseRequestClient以获取完整的响应对象，而不是只获取data部分
    // 增加timeout设置，适应固件分析的长时间处理
    const response = await baseRequestClient.post(
      '/firmware/analyze',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300_000, // 5分钟超时设置，足够处理大型固件
      },
    );

    return response;
  } catch (error) {
    message.error('文件上传或分析失败');
    console.error('固件分析错误:', error);
    throw error; // 抛出错误让调用者处理
  }
}

// 验证固件文件格式的函数
export const isValidFirmwareFile = (file: File): boolean => {
  const validExtensions = ['.so', '.bin', '.zip', '.tar'];
  const hasValidExtension = validExtensions.some((ext) =>
    file.name.toLowerCase().endsWith(ext),
  );

  if (!hasValidExtension) {
    message.error('请上传.so、.bin、.zip或.tar格式的固件文件');
    return false;
  }

  // 检查文件大小（例如限制为100MB）
  const maxSize = 100 * 1024 * 1024; // 100MB
  if (file.size > maxSize) {
    message.error('文件大小不能超过100MB');
    return false;
  }

  return true;
};
