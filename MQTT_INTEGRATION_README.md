# MQTT协议集成说明

## 概述

本项目已成功集成MBFuzzer工具，用于MQTT协议的模糊测试。MBFuzzer是一个专门针对MQTT代理的多方黑盒模糊测试工具。

## 文件结构

```
protocol-analysis-platform-web-ui/
├── mbfuzzer_artifact/                    # MBFuzzer工具和日志文件
│   └── mbfuzzer_artifact/
│       ├── fuzzing_report.txt           # 原始MBFuzzer日志文件
│       └── mbfuzzer/                    # MBFuzzer源代码
├── apps/
│   ├── backend-flask/
│   │   └── protocol_compliance/
│   │       ├── mbfuzzer_logs/           # 后端日志文件目录
│   │       │   └── fuzzing_report.txt   # 复制的日志文件
│   │       └── routes.py                # 更新的API路由
│   └── web-antd/
│       └── src/views/protocol-compliance/fuzz/
│           └── index.vue                # 更新的前端界面
└── test_mqtt_api.py                     # API测试脚本
```

## 功能特性

### 1. MBFuzzer日志解析
- ✅ 解析基本统计信息（开始/结束时间、请求数量等）
- ✅ 解析客户端和代理端消息类型统计
- ✅ 解析崩溃和差异统计
- ✅ 解析重复差异统计
- 🔄 差异报告解析（待实现）
- 🔄 Q-Learning表格解析（待实现）

### 2. 前端界面
- ✅ MQTT协议选择和MBFuzzer引擎选择
- ✅ 实时日志显示和解析
- ✅ MQTT专用的统计界面
- ✅ 客户端vs代理端消息分布可视化
- ✅ 协议差异分析界面

### 3. 后端API
- ✅ 支持MQTT协议的日志读取API
- ✅ 增量日志读取（避免重复处理）
- ✅ 错误处理和回退机制

## 使用方法

### 1. 启动后端服务器

```bash
cd apps/backend-flask
python main.py
```

### 2. 启动前端开发服务器

```bash
cd apps/web-antd
pnpm dev
```

### 3. 测试API连接

```bash
python test_mqtt_api.py
```

### 4. 使用界面

1. 打开浏览器访问前端界面
2. 在协议类型中选择"MQTT"
3. Fuzz引擎会自动选择为"MBFuzzer"
4. 配置目标主机和端口（默认1883）
5. 点击"开始测试"

## 日志文件格式

MBFuzzer生成的日志文件包含以下部分：

### 基本统计信息
```
Fuzzing Start Time: 2024-07-06 00:39:14
Fuzzing End Time: 2024-07-07 10:15:23
Fuzzing request number (client): 851051
Fuzzing request number (broker): 523790
Crash Number: 0
Diff Number: 5841
Duplicate Diff Number: 118563
Valid Connect Number: 1362
```

### 消息类型统计
```
Fuzzing requests (client):
	CONNECT: 176742
	CONNACK: 2018
	PUBLISH: 648530
	...

Fuzzing requests (broker):
	CONNECT: 7174
	CONNACK: 6029
	PUBLISH: 418336
	...
```

### 差异报告
```
Differential Report:
protocol_version: 5, type: {Message Unexpected}, diff_range_broker: ['flashmq'], msg_type: PUBREL, direction: broker, file_path: /path/to/diff.raw, capture_time: 2024-07-06 00:39:14.355007
```

### Q-Learning表格
```
Q Table:
24604fbefebdf98b1a6c3042284285a4 {'CONNECT': 0.49596472797307095, 'CONNACK': 0.2571241946947465, ...}
	[0.04106915 0.02547191 0.58996318 ...]
```

## 字段含义

### 统计字段
- **Fuzzing Start/End Time**: 模糊测试的开始和结束时间
- **Client/Broker Request Number**: 客户端和代理端的总请求数
- **Crash Number**: 检测到的崩溃数量
- **Diff Number**: 发现的协议差异数量
- **Duplicate Diff Number**: 重复的差异数量
- **Valid Connect Number**: 有效的连接数量

### 消息类型
- **CONNECT/CONNACK**: 连接请求/响应
- **PUBLISH/PUBACK/PUBREC/PUBREL/PUBCOMP**: 发布消息相关
- **SUBSCRIBE/SUBACK**: 订阅相关
- **UNSUBSCRIBE/UNSUBACK**: 取消订阅相关
- **PINGREQ/PINGRESP**: 心跳相关
- **DISCONNECT**: 断开连接
- **AUTH**: 认证相关

## 待实现功能

### 1. 差异报告解析 (mqtt_diff_parser)
- 解析协议不一致性信息
- 按代理类型分类差异
- 可视化差异分布

### 2. Q-Learning表格解析 (mqtt_q_table_parser)
- 解析强化学习状态
- 可视化Q值分布
- 显示状态转换概率

### 3. 实时日志读取 (mqtt_real_time)
- 实现真正的实时日志监控
- 支持日志文件轮转
- 优化性能和内存使用

## 故障排除

### 1. API连接失败
- 确保Flask后端服务器正在运行
- 检查端口是否被占用
- 验证API路由配置

### 2. 日志文件读取失败
- 检查日志文件是否存在
- 验证文件权限
- 确认文件路径配置正确

### 3. 前端显示异常
- 检查浏览器控制台错误
- 验证API响应格式
- 确认Vue组件状态更新

## 开发说明

### 添加新的日志解析功能

1. 在`processMQTTLogLine`函数中添加新的解析逻辑
2. 更新`mqttStats`数据结构
3. 在UI模板中添加相应的显示组件
4. 测试解析功能的正确性

### 修改日志文件路径

在`apps/backend-flask/protocol_compliance/routes.py`中修改`MQTT_CONFIG`：

```python
MQTT_CONFIG = {
    "log_file_path": "/path/to/your/fuzzing_report.txt",
    # ...
}
```

## 联系信息

如有问题或建议，请联系开发团队。
