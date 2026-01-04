#!/usr/bin/env python3
"""
import os
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="Universal Protocol Document Processor")
    parser.add_argument("--api-key", required=True, help="DeepSeek API key")
    parser.add_argument("--protocol", required=True, help="Protocol name (e.g. mqtt)")
    parser.add_argument("--version", required=True, help="Protocol version (e.g. 5.0)")
    parser.add_argument("--html-file", required=True, help="Path to protocol HTML document")
    parser.add_argument("--filter-headings", action="store_true", help="是否对目录进行筛选")

    args = parser.parse_args()

    # 创建存储目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    store_dir = os.path.join(base_dir, "directoryStore")
    os.makedirs(store_dir, exist_ok=True)

    # 生成配置字典
    config = {
        "api_key": args.api_key,
        "protocol": args.protocol.lower(),
        "version": args.version,
        "paths": {
            "directoryStore": os.path.abspath(store_dir),
            "html_input": os.path.join(store_dir,args.html_file),
            "cleaned_html": os.path.join(store_dir, f"{args.protocol}_cleaned.html"),
            "markdown": os.path.join(store_dir, f"final_{args.protocol}.md"),
            "keywords": os.path.join(store_dir, "specify_keywords.txt"),
            "headings": os.path.join(store_dir, "headings.json"),
            "output_json": os.path.join(store_dir, "filtered_headings.json"),
            "output_excel": os.path.join(store_dir, "sentences_analysis.xlsx"),
            "text_processed": os.path.join(store_dir, "text_processed.json"),
            "dissector": os.path.join(store_dir, f"packet-{args.protocol}.c"),
            "tables": os.path.join(store_dir, "tables.json")
        }
    }

    # 保存配置文件
    with open(os.path.join(store_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=2)

    # 执行处理流程
    from .html_process import process_html
    from .text_process import process_text
    #from .specify_keywords import fetch_dissector
    from .index_filtering import filter_headings
    from .separate_sentences import process_sentences

    process_html(config)
    process_text(config)
    #fetch_dissector(config)
    if args.filter_headings:
        filter_headings(config)
    #process_sentences(config)

    # 检查 tables.json 是否为空，为空则自动处理表格
    tables_path = config["paths"]["tables"]
    need_process_table = False
    if not os.path.exists(tables_path):
        need_process_table = True
    else:
        with open(tables_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if not data:  # 空dict或空list
                    need_process_table = True
            except Exception:
                need_process_table = True

    if need_process_table:
        from .table_process import process_tables
        process_tables(config)


if __name__ == "__main__":
    main()
"""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Universal Protocol Document Processor")
    parser.add_argument("--apikey", required=True, help="DeepSeek API key")
    parser.add_argument("--protocol", required=True, help="Protocol name (e.g. mqtt)")
    parser.add_argument("--version", required=True, help="Protocol version (e.g. 5.0)")
    parser.add_argument("--html-file", required=True, help="Path to protocol HTML document")
    parser.add_argument("--filter-headings", action="store_true", help="是否对目录进行筛选")
    parser.add_argument("--store-dir", required=True, help="协议专属存储目录")
    args = parser.parse_args()

    # 设置存储目录
    store_dir = Path(args.store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建 documentDir 子目录
    document_dir = store_dir / "documentDir"
    document_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成路径配置
    paths = {
        "html_input": args.html_file,
        "cleaned_html": document_dir / f"{args.protocol.lower()}_cleaned.html",
        "markdown": document_dir / f"final_{args.protocol.lower()}.md",
        "keywords": document_dir / "specify_keywords.txt",
        "headings": document_dir / "headings.json",
        "output_json": document_dir / "filtered_headings.json",
        "output_excel": document_dir / "sentences_analysis.xlsx",
        "text_processed": document_dir / "text_processed.json",
        "dissector": document_dir / f"packet-{args.protocol.lower()}.c",
        "tables": document_dir / "tables.txt"
    }

    # 转换为字符串路径
    str_paths = {k: str(v) for k, v in paths.items()}

    # 生成配置字典
    config = {
        "api_key": args.apikey,
        "protocol": args.protocol.lower(),
        "version": args.version,
        "paths": str_paths
    }
    
    # 执行处理流程
    from .html_process import process_html
    from .text_process import process_text
    from .index_filtering import filter_headings
    from .table_process import process_tables
    from .specify_keywords import process_keywords
    from .separate_sentences import process_sentences

    print("执行到节点1")
    process_html(config)
    
    print("执行到节点2")
    process_text(config)

    print("执行到节点3")
    process_keywords(config)
    
    if args.filter_headings:
        filter_headings(config)

    print("执行到节点4")
    process_sentences(config)
    
    
    
    tables_path = paths["tables"]
    need_process_table = False

    if not tables_path.exists():
        need_process_table = True
    else:
        with open(tables_path, "r", encoding="utf-8") as f:
            try:
                content = f.read().strip()
                if not content:
                    # 文件为空
                    need_process_table = True
                else:
                    # 尝试解析 JSON，如果失败就按纯文本处理
                    try:
                        data = json.loads(content)
                        if not data:
                            need_process_table = True
                    except json.JSONDecodeError:
                        # 是纯文本，不为空就认为不需要重新处理
                        need_process_table = False
            except Exception:
                need_process_table = True

    if need_process_table:
        print("执行到节点5")
        process_tables(config)


if __name__ == "__main__":
    main()
