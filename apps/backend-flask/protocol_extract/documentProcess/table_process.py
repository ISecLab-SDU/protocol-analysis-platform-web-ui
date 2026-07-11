import json
from pathlib import Path
import toml

# 获取当前脚本所在目录（保留配置读取，仅用于获取输出路径）
script_dir = Path(__file__).parent.parent
config_path = script_dir / "config.toml"
toml_config = toml.load(config_path)

# 仅保留必要配置（用于获取输出路径）
this_workers = toml_config["llm"]["max_workers"]  # 保留但不使用

def save_markdown(results, output_path):
    """保存空的 Markdown 文件（仅创建文件，无有效内容）"""
    with open(output_path, "w", encoding="utf-8") as f:
        # 写入空内容（或可添加注释说明）
        f.write("\n")

def process_tables(config, max_workers=this_workers):
    """直接生成空的 tables.txt 和 tables.md，跳过所有大模型调用"""
    # 1. 定义输出路径
    tables_path = Path(config["paths"]["tables"])
    markdown_path = tables_path.with_suffix(".md")

    # 2. 生成空的 JSON 格式 tables.txt（符合原代码的字典结构，无有效图表）
    empty_results = {}  # 空字典，符合原代码格式规范
    with open(tables_path, "w", encoding="utf-8") as f:
        json.dump(empty_results, f, ensure_ascii=False, indent=2)

    # 3. 生成空的 Markdown 文件
    save_markdown(empty_results, markdown_path)

    # 4. 打印完成信息
    print(f"\n✅ 已生成空文件：{tables_path}")
    print(f"✅ 已生成空文件：{markdown_path}")
