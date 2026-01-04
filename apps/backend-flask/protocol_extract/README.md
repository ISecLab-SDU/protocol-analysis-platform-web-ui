# Protocol Analyzer 

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)

智能协议规范分析系统，支持多协议版本的自动化规则提取与验证

## 🌟 功能特性

- **三阶段处理流程**
  - 📄 文档处理：原始协议文档解析与结构化
  - 🔑 关键词处理：智能提取协议关键要素
  - ⚖️ 规则处理：深度分析协议逻辑与验证

- **核心能力**
  - 支持 MQTT/HTTP/DHCP 等主流协议
  - 基于大模型的语义规则验证
  - 多格式输出支持 (JSON/Excel/TXT)

## 🚀 快速开始

### 1.环境要求
- Python 3.10+
- DeepSeek API Key ([获取地址](https://platform.deepseek.com/))

### 2.安装步骤

#### （1）克隆仓库
git clone https://github.com/peter-pe/protocolProject.git

#### （2）安装依赖
pip install -r requirements.txt

## 🛠️ 使用指南

### 1.输入文件要求
- HTML格式的协议规范文件
- DeepSeek 平台申请的访问密钥

### 2.运行示例
python main.py  --apikey sk-xxx --protocol MQTT --version 5.0 --html-file samples/mqtt_v5_spec.html

### 3.参数说明
- protocol    协议类型 (必填，如 MQTT/HTTP)
- version     协议版本 (必填，如 5.0/1.1)
- html-file   输入文件路径 (必填)
- apikey      DeepSeek API密钥 (必填)
