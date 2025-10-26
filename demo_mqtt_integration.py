#!/usr/bin/env python3
"""
MQTT协议集成演示脚本
展示MBFuzzer日志文件的解析和处理流程
"""

import os
import json
from typing import Dict, List, Any

def parse_mqtt_log_file(file_path: str) -> Dict[str, Any]:
    """
    解析MBFuzzer日志文件
    """
    if not os.path.exists(file_path):
        print(f"❌ 日志文件不存在: {file_path}")
        return {}
    
    print(f"📄 开始解析日志文件: {file_path}")
    
    stats = {
        'basic_info': {},
        'client_messages': {},
        'broker_messages': {},
        'duplicate_diffs': {},
        'differential_reports': [],
        'q_table_states': []
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
        
        print(f"📊 日志文件总行数: {len(lines)}")
        
        current_section = None
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # 解析基本统计信息
            if line.startswith('Fuzzing Start Time:'):
                stats['basic_info']['start_time'] = line.split(':', 1)[1].strip()
            elif line.startswith('Fuzzing End Time:'):
                stats['basic_info']['end_time'] = line.split(':', 1)[1].strip()
            elif line.startswith('Fuzzing request number (client):'):
                stats['basic_info']['client_requests'] = int(line.split(':')[1].strip())
            elif line.startswith('Fuzzing request number (broker):'):
                stats['basic_info']['broker_requests'] = int(line.split(':')[1].strip())
            elif line.startswith('Crash Number:'):
                stats['basic_info']['crashes'] = int(line.split(':')[1].strip())
            elif line.startswith('Diff Number:'):
                stats['basic_info']['diffs'] = int(line.split(':')[1].strip())
            elif line.startswith('Duplicate Diff Number:'):
                stats['basic_info']['duplicate_diffs'] = int(line.split(':')[1].strip())
            elif line.startswith('Valid Connect Number:'):
                stats['basic_info']['valid_connects'] = int(line.split(':')[1].strip())
            
            # 识别段落
            elif line == 'Fuzzing requests (client):':
                current_section = 'client_messages'
            elif line == 'Fuzzing requests (broker):':
                current_section = 'broker_messages'
            elif line == 'Differential Report:':
                current_section = 'differential_reports'
            elif line == 'Q Table:':
                current_section = 'q_table'
            
            # 解析消息类型统计
            elif current_section in ['client_messages', 'broker_messages'] and ':' in line and line.startswith('\t'):
                parts = line.strip().split(':')
                if len(parts) == 2:
                    msg_type = parts[0].strip()
                    count = int(parts[1].strip())
                    stats[current_section][msg_type] = count
            
            # 解析差异报告
            elif current_section == 'differential_reports' and 'protocol_version:' in line:
                # 简单解析差异报告行
                stats['differential_reports'].append(line)
            
            # 解析Q表格
            elif current_section == 'q_table' and '{' in line and '}' in line:
                # 简单解析Q表格行
                stats['q_table_states'].append(line)
        
        print("✅ 日志文件解析完成")
        return stats
        
    except Exception as e:
        print(f"❌ 解析日志文件时出错: {str(e)}")
        return {}

def display_stats(stats: Dict[str, Any]):
    """
    显示解析后的统计信息
    """
    if not stats:
        print("❌ 没有可显示的统计信息")
        return
    
    print("\n" + "="*60)
    print("📊 MBFuzzer 统计信息")
    print("="*60)
    
    # 基本信息
    basic = stats.get('basic_info', {})
    if basic:
        print("\n🕒 基本信息:")
        for key, value in basic.items():
            print(f"  {key}: {value}")
    
    # 客户端消息统计
    client_msgs = stats.get('client_messages', {})
    if client_msgs:
        print(f"\n📤 客户端消息统计 (共{len(client_msgs)}种类型):")
        sorted_msgs = sorted(client_msgs.items(), key=lambda x: x[1], reverse=True)
        for msg_type, count in sorted_msgs[:10]:  # 显示前10个
            print(f"  {msg_type:12}: {count:>8,}")
        if len(sorted_msgs) > 10:
            print(f"  ... 还有 {len(sorted_msgs) - 10} 种消息类型")
    
    # 代理端消息统计
    broker_msgs = stats.get('broker_messages', {})
    if broker_msgs:
        print(f"\n📥 代理端消息统计 (共{len(broker_msgs)}种类型):")
        sorted_msgs = sorted(broker_msgs.items(), key=lambda x: x[1], reverse=True)
        for msg_type, count in sorted_msgs[:10]:  # 显示前10个
            print(f"  {msg_type:12}: {count:>8,}")
        if len(sorted_msgs) > 10:
            print(f"  ... 还有 {len(sorted_msgs) - 10} 种消息类型")
    
    # 差异报告
    diff_reports = stats.get('differential_reports', [])
    if diff_reports:
        print(f"\n⚠️  差异报告 (共{len(diff_reports)}条):")
        for i, report in enumerate(diff_reports[:5], 1):  # 显示前5条
            print(f"  {i}. {report[:80]}...")
        if len(diff_reports) > 5:
            print(f"  ... 还有 {len(diff_reports) - 5} 条差异报告")
    
    # Q表格状态
    q_states = stats.get('q_table_states', [])
    if q_states:
        print(f"\n🧠 Q-Learning状态 (共{len(q_states)}个状态):")
        for i, state in enumerate(q_states[:3], 1):  # 显示前3个
            print(f"  {i}. {state[:80]}...")
        if len(q_states) > 3:
            print(f"  ... 还有 {len(q_states) - 3} 个状态")

def main():
    """
    主函数
    """
    print("🚀 MQTT协议集成演示")
    print("="*60)
    
    # 日志文件路径
    log_file_paths = [
        "apps/backend-flask/protocol_compliance/mbfuzzer_logs/fuzzing_report.txt",
        "mbfuzzer_artifact/mbfuzzer_artifact/fuzzing_report.txt"
    ]
    
    log_file = None
    for path in log_file_paths:
        if os.path.exists(path):
            log_file = path
            break
    
    if not log_file:
        print("❌ 找不到MBFuzzer日志文件")
        print("请确保以下路径之一存在日志文件:")
        for path in log_file_paths:
            print(f"  - {path}")
        return
    
    # 解析日志文件
    stats = parse_mqtt_log_file(log_file)
    
    # 显示统计信息
    display_stats(stats)
    
    # 保存解析结果
    output_file = "mqtt_parsed_stats.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"\n💾 解析结果已保存到: {output_file}")
    except Exception as e:
        print(f"❌ 保存解析结果失败: {str(e)}")
    
    print("\n✅ 演示完成!")
    print("\n💡 下一步:")
    print("  1. 启动Flask后端服务器: cd apps/backend-flask && python main.py")
    print("  2. 启动前端开发服务器: cd apps/web-antd && pnpm dev")
    print("  3. 在浏览器中选择MQTT协议进行测试")

if __name__ == "__main__":
    main()
