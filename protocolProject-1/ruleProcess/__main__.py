# main.py
import argparse
import subprocess
import sys
from pathlib import Path
import json


def get_module_path(script_name: str) -> str:
    """获取模块内脚本的绝对路径"""
    current_dir = Path(__file__).parent  # main.py所在目录
    script_path = current_dir / f"{script_name}.py"

    if not script_path.exists():
        print(f"❌ 错误：找不到 {script_name}.py 文件")
        print(f"请确认文件存在于: {script_path}")
        sys.exit(1)

    return str(script_path)

def create_default_config(store_dir: Path) -> dict:
    """生成默认配置，并返回 dict"""
    # 创建 ruleDir 子目录
    rule_dir = store_dir / "ruleDir"
    document_dir = store_dir / "documentDir"
    rule_dir.mkdir(parents=True, exist_ok=True)
    
    paths = {
        "paragraph_output": str(store_dir / "keywordDir" / "paragraphs_output.json"),  # 从keywordDir读取
        "final_output": str(store_dir / "keywordDir" / "keywords_final.json"),  # 从keywordDir读取
        "json_sentences": str(rule_dir / "filtered_sentences.json"),
        "txt_sentences": str(rule_dir / "matched_sentences.txt"),
        "excel_sentences": str(rule_dir / "filtered_sentences.xlsx"),
        "table": str(document_dir / "tables.md"),
        "processed": str(rule_dir / "processed_results.json"),
    }

    config = {
        "paths": paths
    }
    config_file = rule_dir / "rule_config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"[OK] 已生成默认配置文件: {config_file}")
    return config

def main():
    parser = argparse.ArgumentParser(description="通用协议规则分析系统",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--apikey", help="DeepSeek API 密钥（第二、三阶段需要）")
    parser.add_argument("--protocol", required=True, help="目标协议名称（如 HTTP、MQTT）")
    parser.add_argument("--version", required=True, help="协议版本号（如 1.1、5.0）")
    parser.add_argument("--store-dir", required=True, help="协议专属存储目录")
    # 修改步骤选项参数，添加 "enhance" 步骤
    parser.add_argument("--steps", nargs="+",
                        choices=["all", "first", "second", "enhance", "third"],
                        default=["all"],
                        help="选择要执行的步骤（默认：all）")
    args = parser.parse_args()

    store_dir = Path(args.store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建 ruleDir 子目录
    rule_dir = store_dir / "ruleDir"
    rule_dir.mkdir(parents=True, exist_ok=True)
    
    config = create_default_config(store_dir)
    config_file = rule_dir / "rule_config.json"

    # 步骤处理逻辑
    steps = args.steps
    # 修改默认步骤顺序（当选择 all 时）
    if "all" in steps:
        steps = ["first",  "enhance", "second", "third"]  # 添加 enhance 步骤
    # 执行第一阶段
    if "first" in steps:
        print("\n[Stage 1] 执行第一阶段：基础规则过滤")
        first_script = get_module_path("first_rule")
        subprocess.run([
            sys.executable, first_script,
            "--config", config_file
            ], check=True)
    # 执行增强阶段（位于 second 和 third 之间）
    if "enhance" in steps:
        if not args.apikey:
            raise ValueError("增强阶段需要提供 API 密钥！")
        print("\n[Enhance] 执行增强阶段：句子上下文补充")
        enhance_script = get_module_path("enhance_rule")
        subprocess.run([
            sys.executable, enhance_script,
            "--apikey", args.apikey,
            "--protocol", args.protocol,
            "--version", args.version,
            "--config", config_file
        ], check=True)
        # 执行第二阶段
    if "second" in steps:
        if not args.apikey:
            raise ValueError("第二阶段需要提供 API 密钥！")
        print("\n[Stage 2] 执行第二阶段：AI 规则验证")
        second_script = get_module_path("second_rule")
        subprocess.run([
            sys.executable, second_script,
            "--apikey", args.apikey,
            "--protocol", args.protocol,
            "--version", args.version,
            "--config", config_file
        ], check=True)
    # 执行第三阶段
    if "third" in steps:
        if not args.apikey:
            raise ValueError("第三阶段需要提供 API 密钥！")
        print("\n[Stage 3] 执行第三阶段：协议字段解析")
        third_script = get_module_path("third_rule")
        subprocess.run([
            sys.executable, third_script,
            "--apikey", args.apikey,
            "--protocol", args.protocol,
            "--version", args.version,
            "--config", config_file
        ], check=True)

if __name__ == "__main__":
    main()