/**
 * RTSP协议专用的composable
 * 包含AFLNET相关的数据处理和UI逻辑
 */

import { ref, type Ref } from 'vue';
import type { RTSPStats, LogUIData } from './types';

export function useRTSP() {
  // RTSP统计数据
  const rtspStats: Ref<RTSPStats> = ref({
    cycles_done: 0,
    paths_total: 0,
    cur_path: 0,
    pending_total: 0,
    pending_favs: 0,
    map_size: '0%',
    unique_crashes: 0,
    unique_hangs: 0,
    max_depth: 0,
    execs_per_sec: 0,
    n_nodes: 0,
    n_edges: 0
  });

  // 重置RTSP统计数据
  function resetRTSPStats() {
    rtspStats.value = {
      cycles_done: 0,
      paths_total: 0,
      cur_path: 0,
      pending_total: 0,
      pending_favs: 0,
      map_size: '0%',
      unique_crashes: 0,
      unique_hangs: 0,
      max_depth: 0,
      execs_per_sec: 0,
      n_nodes: 0,
      n_edges: 0
    };
  }

  // 处理RTSP协议的AFL-NET日志行
  function processRTSPLogLine(line: string, packetCount: Ref<number>, successCount: Ref<number>, failedCount: Ref<number>, crashCount: Ref<number>, currentSpeed: Ref<number>) {
    const timestamp = new Date().toLocaleTimeString();
    
    // 处理注释行（参数说明）
    if (line.startsWith('#')) {
      return {
        timestamp,
        type: 'HEADER',
        content: line.replace('#', '').trim(),
        isHeader: true
      } as LogUIData;
    }
    
    // 处理数据行
    if (line.includes(',')) {
      const parts = line.split(',').map(part => part.trim());
      if (parts.length >= 13) {
        const [
          unix_time, cycles_done, cur_path, paths_total, pending_total, 
          pending_favs, map_size, unique_crashes, unique_hangs, max_depth, 
          execs_per_sec, n_nodes, n_edges
        ] = parts;
        
        // 格式化显示AFL-NET统计信息
        const formattedContent = `Cycles: ${cycles_done} | Paths: ${cur_path}/${paths_total} | Pending: ${pending_total}(${pending_favs} favs) | Coverage: ${map_size} | Crashes: ${unique_crashes} | Hangs: ${unique_hangs} | Speed: ${execs_per_sec}/sec | Nodes: ${n_nodes} | Edges: ${n_edges}`;
        
        // 更新RTSP统计信息
        rtspStats.value = {
          cycles_done: parseInt(cycles_done),
          paths_total: parseInt(paths_total),
          cur_path: parseInt(cur_path),
          pending_total: parseInt(pending_total),
          pending_favs: parseInt(pending_favs),
          map_size: map_size,
          unique_crashes: parseInt(unique_crashes),
          unique_hangs: parseInt(unique_hangs),
          max_depth: parseInt(max_depth),
          execs_per_sec: parseFloat(execs_per_sec),
          n_nodes: parseInt(n_nodes),
          n_edges: parseInt(n_edges)
        };
        
        // 更新通用统计信息
        packetCount.value = parseInt(cur_path);
        successCount.value = parseInt(paths_total) - parseInt(pending_total);
        failedCount.value = parseInt(unique_crashes);
        crashCount.value = parseInt(unique_crashes);
        currentSpeed.value = Math.round(parseFloat(execs_per_sec));
        
        return {
          timestamp,
          type: 'STATS',
          content: formattedContent,
          rawData: {
            cycles_done: parseInt(cycles_done),
            paths_total: parseInt(paths_total),
            cur_path: parseInt(cur_path),
            pending_total: parseInt(pending_total),
            unique_crashes: parseInt(unique_crashes),
            execs_per_sec: parseFloat(execs_per_sec)
          }
        } as LogUIData;
      }
    } else {
      // 处理其他类型的日志行
      return {
        timestamp,
        type: 'INFO',
        content: line
      } as LogUIData;
    }
    
    return null;
  }

  // 写入RTSP脚本文件
  async function writeRTSPScript(scriptContent: string) {
    try {
      const response = await fetch('/api/protocol-compliance/write-script', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: scriptContent,
          protocol: 'RTSP'
        }),
      });
      
      if (!response.ok) {
        throw new Error(`写入脚本文件失败: ${response.statusText}`);
      }
      
      const result = await response.json();
      return result;
      
    } catch (error: any) {
      console.error('写入RTSP脚本失败:', error);
      throw new Error(`写入脚本文件失败: ${error.message}`);
    }
  }

  // 执行RTSP命令
  async function executeRTSPCommand() {
    try {
      const response = await fetch('/api/protocol-compliance/execute-command', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          protocol: 'RTSP'
        }),
      });
      
      if (!response.ok) {
        throw new Error(`执行命令失败: ${response.statusText}`);
      }
      
      const result = await response.json();
      return result;
      
    } catch (error: any) {
      console.error('执行RTSP命令失败:', error);
      throw new Error(`执行启动命令失败: ${error.message}`);
    }
  }

  // 停止RTSP进程
  async function stopRTSPProcess(processId: string | number) {
    if (!processId) {
      return;
    }
    
    try {
      const response = await fetch('/api/protocol-compliance/stop-process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          pid: processId,
          protocol: 'RTSP'
        }),
      });
      
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('停止RTSP进程失败:', error);
      throw error;
    }
  }

  return {
    rtspStats,
    resetRTSPStats,
    processRTSPLogLine,
    writeRTSPScript,
    executeRTSPCommand,
    stopRTSPProcess
  };
}
