import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

def create_default_config(store_dir: Path) -> dict:
    """生成默认配置，并返回 dict"""
    # 创建 keywordDir 子目录
    keyword_dir = store_dir / "keywordDir"
    keyword_dir.mkdir(parents=True, exist_ok=True)
    
    paths = {
        "specify_keywords": str(store_dir / "documentDir" / "specify_keywords.txt"),  # 从documentDir读取
        "input_json": str(store_dir / "documentDir" / "filtered_headings.json"),  # 从documentDir读取
        "keyword_list": str(keyword_dir / "keyword_list.json"),
        "paragraph_output": str(keyword_dir / "paragraphs_output.json"),
        "specify_output": str(keyword_dir / "specify_keywords_update_r1.json"),
        "modal_output": str(keyword_dir / "modal_keywords_update_r1.json"),
        "comparative_output": str(keyword_dir / "comparative_keywords_update_r1.json"),
        "final_output": str(keyword_dir / "keywords_final.json")
    }

    config = {
        "processing": {
            "keyword_sources": ["txt"]
        },
        "paths": paths
    }
    config_file = keyword_dir / "keywords_config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"✅ 已生成默认配置文件: {config_file}")
    return config

def run_subprocess(script_name: str, config_file: Path, protocol: str, version: str, apikey: Optional[str] = None) -> None:
    """执行子脚本"""
    script_path = Path(__file__).parent / f"{script_name}.py"
    if not script_path.exists():
        print(f"❌ 找不到处理脚本: {script_path.name}")
        sys.exit(1)

    cmd = [
        sys.executable,
        str(script_path),
        "--protocol", protocol,
        "--version", version,
        "--config", str(config_file)
    ]
    if apikey:
        cmd += ["--apikey", apikey]

    print(f"\n🚀 正在执行 {script_name.upper()}...")
    try:
        # 使用 Popen 实时读取子进程输出
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

        # 按行实时输出
        output_lines = []
        if proc.stdout is not None:
            for line in proc.stdout:
                print(line, end='')   # 直接输出到控制台
                output_lines.append(line)

        proc.wait()
        if proc.returncode != 0:
            print(f"❌ {script_name} 执行失败 (code={proc.returncode})")
            sys.exit(proc.returncode)

        print(f"✅ {script_name} 执行成功")
        if output_lines:
            print("输出摘要:\n", "".join(output_lines[:200]), "...")

    except Exception as e:
        print(f"❌ {script_name} 执行异常: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="通用协议关键词处理系统")
    parser.add_argument("--apikey", required=True, help="DeepSeek API key")
    parser.add_argument("--protocol", required=True, help="协议名称（如 HTTP/MQTT）")
    parser.add_argument("--version", required=True, help="协议版本号（如 1.1/5.0）")
    parser.add_argument("--store-dir", required=True, help="协议专属存储目录")
    args = parser.parse_args()

    store_dir = Path(args.store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建 keywordDir 子目录
    keyword_dir = store_dir / "keywordDir"
    keyword_dir.mkdir(parents=True, exist_ok=True)

    # 创建默认 config
    config = create_default_config(store_dir)
    config_file = keyword_dir / "keywords_config.json"

    # 检查必要文件
    required_files = [Path(config["paths"]["input_json"]), Path(config["paths"]["specify_keywords"])]
    missing = [str(p) for p in required_files if not p.exists()]
    if missing:
        print("❌ 缺失必要输入文件:")
        print("\n".join(missing))
        sys.exit(1)

    # 执行处理流程
    processing_steps = [
        ("keywords", False),
        ("specify_keywords_update", True),
        ("modal_keywords_update", True),
        ("comparative_keywords_updates", True),
        ("keywords_final", True)
    ]

    for step, needs_key in processing_steps:
        run_subprocess(step, config_file, args.protocol, args.version, args.apikey if needs_key else None)

    print("\n🎉 处理完成！结果文件:")
    print(f" - 关键词列表: {config['paths']['keyword_list']}")
    print(f" - 重组段落: {config['paths']['paragraph_output']}")

if __name__ == "__main__":
    main()
