/**
 * SOL协议专用的composable
 * 包含AFLNET相关的数据处理和UI逻辑
 */

import { ref, type Ref } from 'vue';
import type { RTSPStats, LogUIData } from './types';
import { requestClient, dockerRequestClient } from '#/api/request';

export function useSOL() {
  // SOL统计数据
  const solStats: Ref<RTSPStats> = ref({
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

  // 重置SOL统计数据
  function resetSOLStats() {
    solStats.value = {
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

  // 处理SOL协议的AFL-NET日志行
  function processSOLLogLine(line: string, packetCount: Ref<number>, successCount: Ref<number>, failedCount: Ref<number>, crashCount: Ref<number>, currentSpeed: Ref<number>) {
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
        
        // 更新SOL统计信息
        solStats.value = {
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

  // 写入SOL脚本文件
  async function writeSOLScript(scriptContent: string, protocolImplementations?: string[]) {
    try {
      const result = await requestClient.post('/protocol-compliance/write-script', {
        content: scriptContent,
        protocol: 'MQTT',  // SOL协议现在通过MQTT协议实现选择
        protocolImplementations: protocolImplementations || []
      });
      return result;
      
    } catch (error: any) {
      console.error('写入SOL脚本失败:', error);
      throw new Error(`写入脚本文件失败: ${error.message}`);
    }
  }

  // 执行SOL命令
  async function executeSOLCommand(protocolImplementations?: string[]) {
    console.log('[DEBUG] ========== executeSOLCommand 被调用 ==========');
    console.log('[DEBUG] protocolImplementations:', protocolImplementations);
    
    try {
      const requestData = {
        protocol: 'MQTT',  // SOL协议现在通过MQTT协议实现选择
        protocolImplementations: protocolImplementations || []
      };
      
      console.log('[DEBUG] 发送请求到 /protocol-compliance/execute-command');
      console.log('[DEBUG] 请求数据:', requestData);
      
      const result = await dockerRequestClient.post('/protocol-compliance/execute-command', requestData);
      
      console.log('[DEBUG] API响应成功:', result);
      
      // 由于响应拦截器的处理，数据可能直接在result中，也可能在result.data中
      const responseData = result.data || result;
      console.log('[DEBUG] 响应数据结构:', {
        status: result.status,
        data: result.data,
        responseData: responseData,
        hasContainerId: !!responseData?.container_id,
        hasPid: !!responseData?.pid
      });
      
      return result;
      
    } catch (error: any) {
      console.error('[DEBUG] 执行SOL命令失败:', error);
      console.error('[DEBUG] 错误详情:', error.response?.data || error.message);
      throw new Error(`执行启动命令失败: ${error.message}`);
    }
  }

  // 停止SOL进程
  async function stopSOLProcess(processId: string | number) {
    if (!processId) {
      return;
    }
    
    try {
      const result = await requestClient.post('/protocol-compliance/stop-process', {
        pid: processId,
        protocol: 'RTSP'  // 保持协议标识符为RTSP
      });
      return result;
    } catch (error) {
      console.error('停止SOL进程失败:', error);
      throw error;
    }
  }

  // 启动前清理：停止现有容器并清理输出文件
  async function preStartCleanupSOL() {
    console.log('[DEBUG] ========== preStartCleanupSOL 被调用 ==========');
    
    try {
      const requestData = {
        protocol: 'MQTT'  // SOL协议通过MQTT协议实现选择
      };
      
      console.log('[DEBUG] 发送请求到 /protocol-compliance/pre-start-cleanup');
      console.log('[DEBUG] 请求数据:', requestData);
      
      const result = await dockerRequestClient.post('/protocol-compliance/pre-start-cleanup', requestData);
      
      console.log('[DEBUG] 启动前清理API响应成功:', result);
      return result;
    } catch (error) {
      console.error('[DEBUG] 启动前清理失败:', error);
      console.error('[DEBUG] 错误详情:', error.response?.data || error.message);
      throw error;
    }
  }

  // 停止SOL Docker容器（不清理输出文件）
  async function stopSOLContainer(containerId: string) {
    console.log('[DEBUG] ========== stopSOLContainer 被调用 ==========');
    console.log('[DEBUG] 传入的容器ID:', containerId);
    
    if (!containerId) {
      console.log('[DEBUG] 容器ID为空，直接返回');
      return;
    }
    
    try {
      const requestData = {
        container_id: containerId,
        protocol: 'RTSP'  // 保持协议标识符为RTSP
      };
      
      console.log('[DEBUG] 发送请求到 /protocol-compliance/stop-and-cleanup');
      console.log('[DEBUG] 请求数据:', requestData);
      
      const result = await dockerRequestClient.post('/protocol-compliance/stop-and-cleanup', requestData);
      
      console.log('[DEBUG] 停止容器API响应成功:', result);
      return result;
    } catch (error) {
      console.error('[DEBUG] 停止SOL容器失败:', error);
      console.error('[DEBUG] 错误详情:', error.response?.data || error.message);
      throw error;
    }
  }

  // 兼容性函数：保持原有的stopAndCleanupSOL接口
  async function stopAndCleanupSOL(containerId: string) {
    return stopSOLContainer(containerId);
  }

  return {
    solStats,
    resetSOLStats,
    processSOLLogLine,
    writeSOLScript,
    executeSOLCommand,
    stopSOLProcess,
    preStartCleanupSOL,
    stopSOLContainer,
    stopAndCleanupSOL
  };
}
