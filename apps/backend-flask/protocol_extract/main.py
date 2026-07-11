# protocolProject/main.py
import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, TypedDict

import toml


class PipelineStep(TypedDict):
    name: str
    cmd: list[str]
    cwd: Optional[str]


def format_command(cmd: list[str], secret: str | None = None) -> str:
    safe_parts = []
    for part in cmd:
        text = str(part)
        safe_parts.append("<API_KEY>" if secret and text == secret else text)
    return " ".join(safe_parts)


def run_command(
    cmd: list[str],
    cwd: Optional[str] = None,
    secret: str | None = None,
) -> None:
    """通用命令执行函数"""
    try:
        subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
        )
        print(f"[SUCCESS] 命令执行成功: {format_command(cmd, secret)}")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 命令执行失败: {format_command(e.cmd, secret)}")
        print(f"错误信息:\n{e.stdout}")
        sys.exit(1)


def main():
    # 加载全局配置
    config = toml.load("config.toml")
    storage_root = Path(config["storage"]["root"])

    # 从环境变量读取API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 错误: 未设置环境变量 OPENAI_API_KEY")
        sys.exit(1)

    # 参数解析
    parser = argparse.ArgumentParser(
        description="协议分析全流程管理系统",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--protocol", required=True, help="协议名称（如 MQTT、HTTP）")
    parser.add_argument("--filter_headings", action="store_true", help="是否对目录进行筛选")
    parser.add_argument("--version", required=True, help="协议版本（如 5.0、1.1）")
    parser.add_argument("--html-file", required=True,
                        help="原始HTML文件路径（相对当前目录）")
    args = parser.parse_args()

    # 验证HTML文件存在
    html_path = Path(args.html_file)
    if not html_path.exists():
        print(f"❌ HTML文件不存在: {html_path.absolute()}")
        sys.exit(1)
    
    # 获取协议专属存储目录
    protocol_dir = f"{args.protocol.lower()}_{args.version.replace('.', '_')}"
    store_dir = storage_root / protocol_dir
    store_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 创建/使用协议存储目录: {store_dir}")

    doc_cmd = [
    sys.executable, "-m", "documentProcess",
    "--apikey", api_key,
    "--protocol", args.protocol,
    "--version", args.version,
    "--html-file", str(html_path.absolute()),
    "--store-dir", str(store_dir)
]
    if args.filter_headings:
        doc_cmd.append("--filter-headings")
    # 定义各阶段执行命令
    steps: list[PipelineStep] = [
        {
            "name": "文档处理阶段",
            "cmd": doc_cmd,
            "cwd": None  # 在根目录执行
        },
        {
            "name": "关键词处理阶段",
            "cmd": [
                sys.executable, "-m", "keywordProcess",
                "--apikey", api_key,
                "--protocol", args.protocol,
                "--version", args.version,
                "--store-dir", str(store_dir)
            ],
            "cwd": None
        },
        {
            "name": "规则处理阶段",
            "cmd": [
                sys.executable, "-m", "ruleProcess",
                "--apikey", api_key,
                "--protocol", args.protocol,
                "--version", args.version,
                "--store-dir", str(store_dir)
            ],
            "cwd": None  # 在根目录执行
        }
    ]

    # 按顺序执行各阶段
    for step in steps:
        print(f"\n{'=' * 40}")
        print(f"🚀 开始 {step['name']}")
        print(f"📂 工作目录: {step['cwd'] or '当前目录'}")
        print(f"⚙️ 执行命令: {format_command(step['cmd'], api_key)}")
        print("=" * 40)

        run_command(
            cmd=step["cmd"],
            cwd=step["cwd"],
            secret=api_key,
        )
        

    print("\n✅ 所有流程执行完成！")
    print(f"\n✅ 所有流程执行完成！结果存储在: {store_dir}")


if __name__ == "__main__":
    main()
