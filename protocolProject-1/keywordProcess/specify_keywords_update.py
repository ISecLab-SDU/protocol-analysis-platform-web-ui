import re
import json
import argparse
from pathlib import Path
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from tqdm import tqdm
import toml

# 获取当前脚本所在目录
script_dir = Path(__file__).parent.parent
config_path = script_dir / "config.toml"
prompt_path = script_dir / "prompt.toml"
toml_config = toml.load(config_path)
toml_prompt = toml.load(prompt_path)
PROMPT_TEMPLATE = toml_prompt["prompt_specify_keywords_update"]["user"]
this_workers = toml_config["llm"]["max_workers"]
this_url = toml_config["llm"]["base_url"]
this_model = toml_config["llm"]["model1"]
this_temperature = toml_config["llm"]["temperature"]

def process_item(item: tuple, apikey: str, config: Dict, protocol: str, version: str) -> tuple:
    """处理单个章节的线程安全函数"""
    heading, content = item
    client = OpenAI(
        api_key=apikey,
        base_url=this_url
    )

    try:
        # 动态构建提示词
        prompt = PROMPT_TEMPLATE.format(protocol=protocol,version=version,content=content,keywords=config["compact_keywords"])

        response = client.chat.completions.create(
            model=this_model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
        )

        # 验证响应有效性
        result = json.loads(response.choices[0].message.content)
        #print(result)
        if not isinstance(result, dict):
            raise ValueError("Invalid response format")

        return heading, result

    except json.JSONDecodeError:
        return heading, {"error": "Invalid JSON response"}
    except Exception as e:
        return heading, {"error": str(e)}


def main(apikey: str, protocol: str, version: str, config):
    """主处理流程"""
    try:
        # 加载输入数据
        input_path = config["paths"]["paragraph_output"]
        with open(input_path, "r", encoding="utf-8") as f:
            protocol_chapter = json.load(f)

        # 加载关键词列表
        keywords_path = config["paths"]["keyword_list"]
        with open(keywords_path, "r", encoding="utf-8") as f:
            keyword_list = json.load(f)

        # 生成紧凑格式关键词列表（存入config供线程使用）
        config["compact_keywords"] = "[" + ", ".join(f'"{w}"' for w in keyword_list) + "]"

        # 多线程处理
        results = {}
        with ThreadPoolExecutor(
                max_workers=this_workers
        ) as executor:
            futures = {
                executor.submit(process_item, item, apikey, config, protocol, version): item
                for item in protocol_chapter.items()
            }

            # 进度条显示
            with tqdm(
                    total=len(futures),
                    desc="分析协议文档",
                    unit="section",
                    dynamic_ncols=True
            ) as pbar:
                for future in as_completed(futures):
                    heading, result = future.result()
                    results[heading] = result
                    pbar.update(1)
                    pbar.set_postfix_str(f"当前章节: {heading[:15]}...")

        # 保存结果
        output_path = config["paths"]["specify_output"]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n规范关键词扩展完成，结果保存至: {output_path}")

    except Exception as e:
        print(f"处理失败: {str(e)}")
        raise


if __name__ == "__main__":
    #print("开始执行特殊关键词扩充")
    parser = argparse.ArgumentParser()
    parser.add_argument("--apikey", required=True, help="DeepSeek API密钥")
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--config", required=True, help="配置文件路径")
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)
    main(args.apikey, args.protocol, args.version, config)