import { message } from 'ant-design-vue';

// 分析固件的API函数 - 适配前端传入的参数结构
export const analyzeFirmware = async (params: {
  fileName: string;
  fileSize: number;
}): Promise<any> => {
  // 模拟API调用
  return new Promise((resolve) => {
    setTimeout(() => {
      // 返回模拟的分析结果，使用functions字段以匹配前端期望
      resolve({
        success: true,
        data: {
          functions: [
            {
              functionName: 's_ecb DES_ecb_encrypt',
              issueType: 'ECB模式使用',
              severity: 'high', // 使用英文以匹配getSeverityColor函数
              parameters:
                'const_DES_cblock *input, DES_cblock *output, DES_key_schedule *ks, int enc',
              description:
                '使用了不安全的ECB加密模式，该模式在加密相同明文时会产生相同密文',
              codeSnippet: 'DES_ecb_encrypt(input, output, ks, enc);',
            },
            {
              functionName: 's_func DES_ecb_encrypt',
              issueType: 'ECB模式使用',
              severity: 'high',
              parameters:
                'const_DES_cblock *input, DES_cblock *output, DES_key_schedule *ks, int enc',
              description:
                '使用了不安全的ECB加密模式，该模式在加密相同明文时会产生相同密文',
              codeSnippet: 'DES_ecb_encrypt(input, output, ks, enc);',
            },
            {
              functionName: 'const_key DES_key_sched',
              issueType: '弱密钥使用',
              severity: 'medium',
              parameters: 'const_DES_cblock *key, DES_key_schedule *schedule',
              description: '使用了可能较弱的DES密钥长度（56位）和固定密钥值',
              codeSnippet: 'DES_key_sched(key, schedule);',
            },
            {
              functionName: 's_func DES_key_sched',
              issueType: '弱密钥使用',
              severity: 'medium',
              parameters: 'const_DES_cblock *key, DES_key_schedule *schedule',
              description: '使用了可能较弱的DES密钥长度（56位）',
              codeSnippet: 'DES_key_sched(key, schedule);',
            },
          ],
        },
      });
    }, 2000);
  });
};

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
