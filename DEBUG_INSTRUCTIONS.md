# SOL AFLFUZZ 优化后的清理流程指南

## 🎯 优化说明

已将资源清理逻辑从**停止时**移动到**启动前**，这样可以：
- ✅ 让用户在测试结束后查看完整的输出结果
- ✅ 避免结果被立即清理掉
- ✅ 确保每次启动前环境都是干净的

## 🔄 新的工作流程

### 启动时流程：
1. **启动前清理** - 自动清理之前的容器和输出文件
2. **写入脚本** - 准备测试脚本
3. **启动容器** - 创建新的Docker容器
4. **开始测试** - 运行AFLFUZZ测试

### 停止时流程：
1. **停止容器** - 仅停止Docker容器
2. **保留输出** - 输出文件保留供用户查看

## 🔧 超时问题解决方案

### 已修复的超时问题：
- ✅ **增加Docker操作超时时间**：从10秒增加到60秒
- ✅ **优化后端响应速度**：Docker停止命令使用更短的等待时间
- ✅ **添加超时处理逻辑**：超时时提供友好的用户提示
- ✅ **专用Docker客户端**：为Docker操作创建专门的HTTP客户端

### 如果仍然遇到超时：
1. **检查Docker容器状态**：`docker ps`
2. **手动停止容器**：`docker stop [容器ID]`
3. **强制删除容器**：`docker rm -f [容器ID]`
4. **重新启动测试**：启动前清理会自动处理遗留容器

## 🔍 调试步骤

### 1. 启动测试并观察清理过程
1. 选择 **MQTT协议**
2. 选择 **SOL协议** 实现
3. 点击 **开始测试**
4. 打开浏览器开发者工具的 **Console** 标签
5. 观察启动前清理和容器创建的调试日志

### 2. 停止测试并验证结果保留
1. 点击 **停止测试** 按钮
2. 查看停止流程的调试信息
3. 如果出现超时警告，检查容器是否实际已停止
4. 验证输出文件是否保留

#### 预期的启动调试日志：
```
[DEBUG] ========== startSOLTest 被调用 ==========
[DEBUG] 执行启动前清理...
[DEBUG] ========== preStartCleanupSOL 被调用 ==========
[DEBUG] 发送请求到 /protocol-compliance/pre-start-cleanup
[DEBUG] 启动前清理API响应成功: [清理结果]
[DEBUG] 启动前清理完成: [清理详情]
[DEBUG] 写入脚本文件...
[DEBUG] 启动Docker容器...
[DEBUG] ========== executeSOLCommandWrapper 被调用 ==========
[DEBUG] selectedProtocolImplementation.value: SOL协议
[DEBUG] 调用 executeSOLCommand...
[DEBUG] ========== executeSOLCommand 被调用 ==========
[DEBUG] protocolImplementations: ["SOL协议"]
[DEBUG] 发送请求到 /protocol-compliance/execute-command
[DEBUG] API响应成功: [响应对象]
[DEBUG] responseData: {command: "...", container_id: "[容器ID]", ...}
[DEBUG] 设置 solProcessId.value 为: [容器ID]
[DEBUG] solProcessId.value 设置后的值: [容器ID]
[DEBUG] 开始日志读取...
```

#### 预期的停止调试日志：
```
[DEBUG] ========== handleStopTest 被调用 (停止按钮点击) ==========
[DEBUG] 当前协议类型: MQTT
[DEBUG] 当前协议实现: SOL协议
[DEBUG] 当前运行状态: true
[DEBUG] 当前solProcessId: [容器ID] ← 现在应该有值了
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
[DEBUG] solProcessId.value: [容器ID] ← 现在应该有值了
[DEBUG] isDockerContainer: true
[DEBUG] solProcessId类型: string
[DEBUG] solProcessId长度: [长度]
[DEBUG] 识别为Docker容器，调用 stopAndCleanupSOL
[DEBUG] 传递的容器ID: [容器ID]
[DEBUG] ========== stopSOLContainer 被调用 ==========
[DEBUG] 传入的容器ID: [容器ID]
[DEBUG] 发送请求到 /protocol-compliance/stop-and-cleanup
[DEBUG] 请求数据: {container_id: "[容器ID]", protocol: "RTSP"}
[DEBUG] 停止容器API响应成功: [响应数据]
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
