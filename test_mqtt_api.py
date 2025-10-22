#!/usr/bin/env python3
"""
简单的测试脚本，用于验证MQTT协议的后端API是否正常工作
"""

import requests
import json

# 测试读取MQTT日志文件的API
def test_mqtt_log_api():
    url = "http://localhost:5000/api/protocol-compliance/read-log"
    
    payload = {
        "protocol": "MQTT",
        "lastPosition": 0
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API调用成功!")
            print(f"📄 读取内容长度: {len(result.get('data', {}).get('content', ''))}")
            print(f"📍 当前位置: {result.get('data', {}).get('position', 0)}")
            
            # 显示前几行内容
            content = result.get('data', {}).get('content', '')
            if content:
                lines = content.split('\n')[:10]  # 显示前10行
                print("\n📋 日志内容预览:")
                for i, line in enumerate(lines, 1):
                    if line.strip():
                        print(f"  {i:2d}: {line}")
            
            return True
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务器，请确保Flask服务器正在运行")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 测试MQTT协议后端API...")
    print("=" * 50)
    
    success = test_mqtt_log_api()
    
    print("=" * 50)
    if success:
        print("✅ 所有测试通过!")
        print("\n💡 提示:")
        print("  - 现在可以在前端界面选择MQTT协议进行测试")
        print("  - 日志文件位置: apps/backend-flask/protocol_compliance/mbfuzzer_logs/fuzzing_report.txt")
    else:
        print("❌ 测试失败，请检查:")
        print("  1. Flask后端服务器是否正在运行")
        print("  2. 日志文件是否存在")
        print("  3. API路由是否正确配置")
