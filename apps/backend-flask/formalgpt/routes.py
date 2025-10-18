"""Routes for formal verification system."""

from flask import Blueprint, jsonify
import os
import json
from datetime import datetime

bp = Blueprint('formal_gpt', __name__, url_prefix='/api/formal-gpt')

# 配置路径
CASE_FOLDER = '/amax/bxy/formalgpt/case'

def get_proverif_code(protocol_path):
    """读取 ProVerif 形式化验证代码"""
    protocol_txt_path = os.path.join(protocol_path, 'formalmodel', 'turn1', 'protocol.txt')
    if os.path.exists(protocol_txt_path):
        try:
            with open(protocol_txt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading protocol.txt: {e}")
    return None


def get_verification_results(protocol_path):
    """读取验证结果"""
    verification_json_path = os.path.join(protocol_path, 'verification_out.json')
    if os.path.exists(verification_json_path):
        return read_json_file(verification_json_path)
    return None


def read_json_file(filepath):
    """安全地读取JSON文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None


def get_file_size_and_time(protocol_path, protocol_name):
    """获取文件大小和上传时间"""
    extensions = ['pdf', 'doc', 'docx', 'txt']
    for ext in extensions:
        file_path = os.path.join(protocol_path, f"{protocol_name}.{ext}")
        if os.path.exists(file_path):
            return {
                'fileName': f"{protocol_name}.{ext}",
                'fileSize': os.path.getsize(file_path),
                'uploadTime': datetime.fromtimestamp(
                    os.path.getctime(file_path)
                ).strftime('%Y-%m-%d %H:%M:%S')
            }
    
    return {
        'fileName': f"{protocol_name}.pdf",
        'fileSize': 0,
        'uploadTime': datetime.fromtimestamp(
            os.path.getctime(protocol_path)
        ).strftime('%Y-%m-%d %H:%M:%S')
    }


@bp.route('/history', methods=['GET'])
def get_history():
    """获取所有协议的历史记录列表"""
    try:
        if not os.path.exists(CASE_FOLDER):
            return jsonify({
                'code': 1,
                'success': False,
                'error': f'案例目录不存在: {CASE_FOLDER}'
            }), 404
        
        protocols = []
        
        for protocol_name in os.listdir(CASE_FOLDER):
            protocol_path = os.path.join(CASE_FOLDER, protocol_name)
            
            if not os.path.isdir(protocol_path):
                continue
            
            file_info = get_file_size_and_time(protocol_path, protocol_name)

            # 添加读取 ProVerif 代码
            proverif_code = get_proverif_code(protocol_path)
            
            # 添加读取验证结果
            verification_results = get_verification_results(protocol_path)
            
            # 读取 formalir/turn1/Model.json
            formalir_dir = os.path.join(protocol_path, 'formalir', 'turn1')
            ir_data = None
            if os.path.exists(formalir_dir):
                model_json = os.path.join(formalir_dir, 'Model.json')
                if os.path.exists(model_json):
                    ir_data = read_json_file(model_json)
            
            # ✅ 读取 formalmodel/turn1/Model.json 和 protocol.json
            formalmodel_dir = os.path.join(protocol_path, 'formalmodel', 'turn1')
            model_data = None
            sequence_data = None
            
            if os.path.exists(formalmodel_dir):
                # 读取 Model.json（时序图用）
                model_json = os.path.join(formalmodel_dir, 'Model.json')
                if os.path.exists(model_json):
                    model_data = read_json_file(model_json)
                
                # 读取 protocol.json（协议定义）
                protocol_json = os.path.join(formalmodel_dir, 'protocol.json')
                if os.path.exists(protocol_json):
                    sequence_data = read_json_file(protocol_json)
            
            protocol_info = {
                'id': protocol_name,
                'fileName': file_info['fileName'],
                'fileSize': file_info['fileSize'],
                'uploadTime': file_info['uploadTime'],
                'irData': ir_data,
                'modelData': model_data,
                'sequenceData': sequence_data,
                'proverifCode': proverif_code,  # 新增
                'verificationResults': verification_results,  # 修改
                'selectedProperties': []  # 可能需要从验证结果中提取
            }
            # 如果有验证结果，从 'security_properties' 提取属性名称
            if verification_results and 'security_properties' in verification_results:
                protocol_info['selectedProperties'] = [
                    prop.get('property', '') for prop in verification_results.get('security_properties', []) if prop.get('property')
                ]
            
            protocols.append(protocol_info)
        
        protocols.sort(key=lambda x: x['uploadTime'], reverse=True)
        
        return jsonify({
            'code': 0,
            'success': True,
            'data': protocols
        })
        
    except Exception as e:
        print(f"Error in get_history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'code': 1,
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/protocol/<protocol_id>', methods=['GET'])
def get_protocol_detail(protocol_id):
    """获取单个协议的详细信息"""
    try:
        protocol_path = os.path.join(CASE_FOLDER, protocol_id)
        
        if not os.path.exists(protocol_path):
            return jsonify({
                'code': 1,
                'success': False,
                'error': '协议不存在'
            }), 404
        
        # 读取 formalir/turn1/Model.json
        formalir_dir = os.path.join(protocol_path, 'formalir', 'turn1')
        ir_data = None
        if os.path.exists(formalir_dir):
            model_json = os.path.join(formalir_dir, 'Model.json')
            if os.path.exists(model_json):
                ir_data = read_json_file(model_json)
        
        # ✅ 读取 formalmodel/turn1/Model.json 和 protocol.json
        formalmodel_dir = os.path.join(protocol_path, 'formalmodel', 'turn1')
        model_data = None
        sequence_data = None
        
        if os.path.exists(formalmodel_dir):
            model_json = os.path.join(formalmodel_dir, 'Model.json')
            if os.path.exists(model_json):
                model_data = read_json_file(model_json)
            
            protocol_json = os.path.join(formalmodel_dir, 'protocol.json')
            if os.path.exists(protocol_json):
                sequence_data = read_json_file(protocol_json)

         # 添加读取
        proverif_code = get_proverif_code(protocol_path)
        verification_results = get_verification_results(protocol_path)


        
        return jsonify({
            'code': 0,
            'success': True,
            'data': {
                'irData': ir_data,
                'modelData': model_data,
                'sequenceData': sequence_data,
                'proverifCode': proverif_code,  # 新增
                'verificationResults': verification_results,  # 修改
            }
        })
        
    except Exception as e:
        print(f"Error in get_protocol_detail: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'code': 1,
            'success': False,
            'error': str(e)
        }), 500
