# protocolProject/main.py
import argparse
import subprocess
import sys
from pathlib import Path
import toml


def run_command(cmd: list, cwd: str = None):
    """通用命令执行函数"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
        )
        print(f"[SUCCESS] 命令执行成功: {' '.join(cmd)}")
        if result.stdout:
            print("输出摘要:\n" + "\n".join(result.stdout.splitlines()[:5]))
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 命令执行失败: {' '.join(e.cmd)}")
        print(f"错误信息:\n{e.stdout}")
        sys.exit(1)


def main():
    # 加载全局配置
    config = toml.load("config.toml")
    storage_root = Path(config["storage"]["root"])

    # 参数解析
    parser = argparse.ArgumentParser(
        description="协议分析全流程管理系统",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--apikey", required=True, help="DeepSeek API密钥")
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
    "--apikey", args.apikey,
    "--protocol", args.protocol,
    "--version", args.version,
    "--html-file", str(html_path.absolute()),
    "--store-dir", str(store_dir)
]
    if args.filter_headings:
        doc_cmd.append("--filter-headings")
    # 定义各阶段执行命令
    steps = [
        {
            "name": "文档处理阶段",
            "cmd": doc_cmd,
            "cwd": None  # 在根目录执行
        },
        {
            "name": "关键词处理阶段",
            "cmd": [
                sys.executable, "-m", "keywordProcess",
                "--apikey", args.apikey,
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
                "--apikey", args.apikey,
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
        print(f"⚙️ 执行命令: {' '.join(step['cmd'])}")
        print("=" * 40)

        run_command(
            cmd=step["cmd"],
            cwd=step["cwd"]
        )
        

    print("\n✅ 所有流程执行完成！")
    print(f"\n✅ 所有流程执行完成！结果存储在: {store_dir}")


if __name__ == "__main__":
    main()