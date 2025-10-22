/**
 * 共享的日志处理composable
 * 包含日志读取、UI显示等通用逻辑
 */

import { ref, nextTick, type Ref } from 'vue';
import type { LogUIData, ProtocolType } from './types';

export function useLogReader() {
  // 日志读取状态
  const isReadingLog = ref(false);
  const logReadingInterval = ref<number | null>(null);
  const logReadPosition = ref(0);
  const logContainer = ref<HTMLDivElement | null>(null);

  // 开始实时日志读取
  async function startLogReading(protocol: ProtocolType, processLogLine: (line: string) => LogUIData | null) {
    isReadingLog.value = true;
    
    if (logReadingInterval.value) {
      clearInterval(logReadingInterval.value);
    }
    
    logReadingInterval.value = window.setInterval(async () => {
      if (!isReadingLog.value) {
        if (logReadingInterval.value) {
          clearInterval(logReadingInterval.value);
          logReadingInterval.value = null;
        }
        return;
      }
      
      try {
        // 调用后端API读取日志文件
        const response = await fetch('/api/protocol-compliance/read-log', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            protocol: protocol,
            lastPosition: logReadPosition.value
          }),
        });
        
        if (response.ok) {
          const result = await response.json();
          if (result.data && result.data.content && result.data.content.trim()) {
            // 更新读取位置
            logReadPosition.value = result.data.position || logReadPosition.value;
            
            // 处理日志内容
            const logLines = result.data.content.split('\n').filter((line: string) => line.trim());
            logLines.forEach((line: string) => {
              const logData = processLogLine(line);
              if (logData) {
                // 根据协议类型使用不同的UI显示函数
                if (protocol === 'MQTT') {
                  addMQTTLogToUI(logData);
                } else if (protocol === 'RTSP') {
                  addRTSPLogToUI(logData);
                } else {
                  addLogToUI(logData);
                }
              }
            });
          }
        }
      } catch (error) {
        console.error(`读取${protocol}日志失败:`, error);
      }
    }, 2000); // 每2秒读取一次日志
  }

  // 停止日志读取
  function stopLogReading() {
    isReadingLog.value = false;
    if (logReadingInterval.value) {
      clearInterval(logReadingInterval.value);
      logReadingInterval.value = null;
    }
  }

  // 重置日志读取状态
  function resetLogReader() {
    stopLogReading();
    logReadPosition.value = 0;
  }

  // 通用的日志UI显示函数
  function addLogToUI(logData: LogUIData) {
    if (!logContainer.value) return;
    
    nextTick(() => {
      try {
        if (!logContainer.value || !logContainer.value.appendChild) {
          return;
        }
        
        const div = document.createElement('div');
        
        // 根据日志类型设置样式和内容
        switch (logData.type) {
          case 'HEADER':
            div.className = 'log-header-line';
            div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-info font-medium">参数说明:</span> <span class="text-dark/70 text-xs">${logData.content}</span>`;
            break;
          case 'STATS':
            div.className = 'log-stats-line';
            div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-dark font-mono text-xs">${logData.content}</span>`;
            break;
          case 'ERROR':
            div.className = 'log-error-line';
            div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-danger font-medium">ERROR:</span> <span class="text-danger">${logData.content}</span>`;
            break;
          case 'WARNING':
            div.className = 'log-warning-line';
            div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-warning font-medium">WARNING:</span> <span class="text-warning">${logData.content}</span>`;
            break;
          case 'SUCCESS':
            div.className = 'log-success-line';
            div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-success font-medium">SUCCESS:</span> <span class="text-success">${logData.content}</span>`;
            break;
          default:
            div.className = 'log-info-line';
            div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-primary">INFO:</span> <span class="text-dark/70">${logData.content}</span>`;
        }
        
        logContainer.value.appendChild(div);
        
        // 自动滚动到底部
        if (logContainer.value.scrollTop !== undefined) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight;
        }
        
        // 限制日志条目数量，保持性能
        if (logContainer.value.children && logContainer.value.children.length > 200) {
          const firstChild = logContainer.value.firstChild;
          if (firstChild && logContainer.value.removeChild) {
            logContainer.value.removeChild(firstChild);
          }
        }
      } catch (error) {
        console.warn('添加日志到UI失败:', error);
      }
    });
  }

  // MQTT专用的日志显示函数
  function addMQTTLogToUI(logData: LogUIData) {
    if (!logContainer.value) return;
    
    // 使用 nextTick 确保 DOM 稳定后再操作
    nextTick(() => {
      try {
        // 双重检查 DOM 元素是否仍然存在
        if (!logContainer.value || !logContainer.value.appendChild) {
          return;
        }
        
        const div = document.createElement('div');
        
        if (logData.isDetailedDiff && logData.diffInfo) {
          // 差异报告专用样式 - 更突出和详细
          div.className = 'mqtt-diff-line';
          const severityClass = logData.type === 'ERROR' ? 'border-red-400 bg-red-50' : 
                               logData.type === 'WARNING' ? 'border-yellow-400 bg-yellow-50' : 
                               'border-blue-400 bg-blue-50';
          
          div.innerHTML = `
            <div class="p-3 rounded-lg border-l-4 ${severityClass} mb-2">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-gray-500">[${logData.timestamp}]</span>
                <span class="text-xs px-2 py-1 rounded-full ${logData.type === 'ERROR' ? 'bg-red-100 text-red-700' : 
                                                             logData.type === 'WARNING' ? 'bg-yellow-100 text-yellow-700' : 
                                                             'bg-blue-100 text-blue-700'}">${logData.diffInfo.type}</span>
              </div>
              <div class="text-sm font-medium text-gray-800">${logData.content}</div>
              <div class="text-xs text-gray-600 mt-1">
                文件: ${logData.diffInfo.file_path?.split('/').pop() || 'N/A'} | 
                时间: ${logData.diffInfo.capture_time}
              </div>
            </div>
          `;
        } else if (logData.isHeader) {
          // 标题行
          div.className = 'mqtt-header-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-info font-medium">MBFuzzer:</span> <span class="text-dark/70 text-sm">${logData.content}</span>`;
        } else if (logData.type === 'STATS') {
          // 统计数据行
          div.className = 'mqtt-stats-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-success font-mono text-sm">${logData.content}</span>`;
        } else if (logData.type === 'ERROR') {
          // 错误信息行
          div.className = 'mqtt-error-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-danger font-medium">ERROR:</span> <span class="text-danger">${logData.content}</span>`;
        } else if (logData.type === 'WARNING') {
          // 警告信息行
          div.className = 'mqtt-warning-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-warning font-medium">WARNING:</span> <span class="text-warning">${logData.content}</span>`;
        } else if (logData.type === 'SUCCESS') {
          // 成功信息行
          div.className = 'mqtt-success-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-success font-medium">SUCCESS:</span> <span class="text-success">${logData.content}</span>`;
        } else {
          // 普通信息行
          div.className = 'mqtt-info-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-primary">MQTT:</span> <span class="text-dark/70">${logData.content}</span>`;
        }
        
        // 再次检查容器是否存在再添加元素
        if (logContainer.value && logContainer.value.appendChild) {
          logContainer.value.appendChild(div);
          
          // 自动滚动到底部
          if (logContainer.value.scrollTop !== undefined) {
            logContainer.value.scrollTop = logContainer.value.scrollHeight;
          }
          
          // 限制日志条目数量，保持性能
          if (logContainer.value.children && logContainer.value.children.length > 200) {
            const firstChild = logContainer.value.firstChild;
            if (firstChild && logContainer.value.removeChild) {
              logContainer.value.removeChild(firstChild);
            }
          }
        }
      } catch (error) {
        console.warn('添加MQTT日志到UI失败:', error);
      }
    });
  }

  // RTSP专用的日志显示函数
  function addRTSPLogToUI(logData: LogUIData) {
    if (!logContainer.value) return;
    
    // 使用 nextTick 确保 DOM 稳定后再操作
    nextTick(() => {
      try {
        // 双重检查 DOM 元素是否仍然存在
        if (!logContainer.value || !logContainer.value.appendChild) {
          return;
        }
        
        const div = document.createElement('div');
        
        if (logData.isHeader) {
          // 参数说明行
          div.className = 'rtsp-header-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-info font-medium">AFL-NET参数说明:</span> <span class="text-dark/70 text-xs">${logData.content}</span>`;
        } else if (logData.type === 'STATS') {
          // 统计数据行
          div.className = 'rtsp-stats-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-dark font-mono text-xs">${logData.content}</span>`;
        } else {
          // 普通信息行
          div.className = 'rtsp-info-line';
          div.innerHTML = `<span class="text-dark/50">[${logData.timestamp}]</span> <span class="text-primary">RTSP-AFL:</span> <span class="text-dark/70">${logData.content}</span>`;
        }
        
        // 再次检查容器是否存在再添加元素
        if (logContainer.value && logContainer.value.appendChild) {
          logContainer.value.appendChild(div);
          
          // 自动滚动到底部
          if (logContainer.value.scrollTop !== undefined) {
            logContainer.value.scrollTop = logContainer.value.scrollHeight;
          }
          
          // 限制日志条目数量，保持性能
          if (logContainer.value.children && logContainer.value.children.length > 200) {
            const firstChild = logContainer.value.firstChild;
            if (firstChild && logContainer.value.removeChild) {
              logContainer.value.removeChild(firstChild);
            }
          }
        }
      } catch (error) {
        console.warn('添加RTSP日志到UI失败:', error);
      }
    });
  }

  // 清空日志
  function clearLog() {
    try {
      nextTick(() => {
        try {
          if (logContainer.value && logContainer.value.innerHTML !== undefined) {
            logContainer.value.innerHTML = '<div class="text-dark/50 italic">测试未开始，请配置参数并点击"开始测试"</div>';
          }
        } catch (error) {
          console.warn('清空日志容器失败:', error);
        }
      });
    } catch (error) {
      console.warn('清空日志失败:', error);
    }
  }

  return {
    isReadingLog,
    logReadingInterval,
    logReadPosition,
    logContainer,
    startLogReading,
    stopLogReading,
    resetLogReader,
    addLogToUI,
    addMQTTLogToUI,
    addRTSPLogToUI,
    clearLog
  };
}
