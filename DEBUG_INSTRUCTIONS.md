# SOL AFLFUZZ 停止测试调试指南

## 🔍 问题诊断

根据之前的调试日志，发现 `solProcessId.value` 为 `null`，这说明启动时容器ID没有被正确设置。

## 🔍 新的调试步骤

现在我已经在启动和停止流程的关键位置添加了详细的调试日志。请按照以下步骤进行调试：

### 1. 启动测试并观察容器ID设置
1. 选择 **MQTT协议**
2. 选择 **SOL协议** 实现
3. 点击 **开始测试**
4. 打开浏览器开发者工具的 **Console** 标签
5. 观察启动时的调试日志

### 2. 停止测试并观察调试日志
1. 点击 **停止测试** 按钮
2. 查看停止流程的调试信息

#### 预期的启动调试日志：
```
[DEBUG] ========== executeSOLCommandWrapper 被调用 ==========
[DEBUG] selectedProtocolImplementation.value: SOL协议
[DEBUG] 调用 executeSOLCommand...
[DEBUG] ========== executeSOLCommand 被调用 ==========
[DEBUG] protocolImplementations: ["SOL协议"]
[DEBUG] 发送请求到 /protocol-compliance/execute-command
[DEBUG] 请求数据: {protocol: "MQTT", protocolImplementations: ["SOL协议"]}
[DEBUG] API响应成功: [响应对象]
[DEBUG] 响应数据结构: {status: 200, data: {...}, hasContainerId: true, hasPid: false}
[DEBUG] executeSOLCommand 返回结果: [完整响应]
[DEBUG] result.data: [数据对象]
[DEBUG] result.data.container_id: [容器ID]
[DEBUG] result.data.pid: null
[DEBUG] 设置 solProcessId.value 为: [容器ID]
[DEBUG] solProcessId.value 设置后的值: [容器ID]
```

#### 预期的停止调试日志：
```
[DEBUG] ========== handleStopTest 被调用 (停止按钮点击) ==========
[DEBUG] 当前协议类型: MQTT
[DEBUG] 当前协议实现: SOL协议
[DEBUG] 当前运行状态: true
[DEBUG] 当前solProcessId: [容器ID] ← 这里应该有值，不是null
[DEBUG] 停止所有实时流...
[DEBUG] 更新协议状态...
[DEBUG] 检测到MQTT协议，调用 stopMQTTTest
[DEBUG] ========== stopMQTTTest 被调用 ==========
[DEBUG] selectedProtocolImplementation.value: SOL协议
[DEBUG] 开始安全停止MQTT测试...
[DEBUG] 检查是否需要停止SOL Docker容器...
[DEBUG] selectedProtocolImplementation.value === SOL协议: true
[DEBUG] 检测到SOL协议实现，调用 stopSOLProcessWrapper
[DEBUG] ========== stopSOLProcessWrapper 被调用 ==========
[DEBUG] solProcessId.value: [容器ID] ← 这里应该有值，不是null
[DEBUG] isDockerContainer: true
[DEBUG] solProcessId类型: string
[DEBUG] solProcessId长度: [长度]
[DEBUG] 识别为Docker容器，调用 stopAndCleanupSOL
[DEBUG] 传递的容器ID: [容器ID]
[DEBUG] ========== stopAndCleanupSOL 被调用 ==========
[DEBUG] 传入的容器ID: [容器ID]
[DEBUG] 发送请求到 /protocol-compliance/stop-and-cleanup
[DEBUG] 请求数据: {container_id: "[容器ID]", protocol: "RTSP"}
[DEBUG] API响应成功: [响应数据]
```

#### 后端调试日志（Flask控制台）：
```
[DEBUG] ========== 停止和清理API被调用 ==========
[DEBUG] 接收到的请求数据: {'container_id': '[容器ID]', 'protocol': 'RTSP'}
[DEBUG] 解析参数 - 容器ID: [容器ID], 协议: RTSP
[DEBUG] 开始停止和清理RTSP容器: [容器ID]
[DEBUG] 找到容器: [容器ID]
[DEBUG] 容器正在运行，需要停止: [容器ID]
[DEBUG] 容器停止成功: [容器ID]
[DEBUG] 容器删除成功: [容器ID]
```

### 3. 验证Docker容器状态
在终端中运行以下命令验证容器是否被正确停止：

```bash
# 查看正在运行的容器
docker ps

# 查看所有容器（包括已停止的）
docker ps -a

# 如果看到protocolguard容器仍在运行，记录容器ID
```

### 4. 问题排查

#### 如果没有看到调试日志：
- 检查浏览器控制台是否正确打开
- 确认选择的是MQTT协议 + SOL协议实现
- 检查是否有JavaScript错误阻止了执行

#### 如果调试日志显示容器ID为空：
- 检查启动时是否成功获取了容器ID
- 查看启动时的控制台日志

#### 如果API调用失败：
- 检查网络请求是否成功发送
- 查看Flask后端是否收到请求
- 检查后端日志中的错误信息

#### 如果Docker容器仍在运行：
- 记录容器ID
- 手动执行停止命令：`docker stop [容器ID]`
- 检查后端日志中的Docker命令执行结果

### 5. 报告问题
请将以下信息提供给开发者：

1. **浏览器控制台的完整调试日志**
2. **Flask后端控制台的调试日志**
3. **Docker容器状态**（`docker ps` 和 `docker ps -a` 的输出）
4. **任何错误信息**

## 🛠️ 手动清理命令

如果容器仍在运行，可以手动清理：

```bash
# 查找protocolguard容器
docker ps | grep protocolguard

# 停止容器
docker stop [容器ID]

# 删除容器
docker rm [容器ID]

# 或者强制删除
docker rm -f [容器ID]
```

## 📝 预期修复效果

修复成功后，调试日志应该显示完整的停止流程，并且：
1. Docker容器被正确识别和停止
2. 容器被从系统中删除
3. `docker ps` 不再显示protocolguard容器
