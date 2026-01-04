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
PROMPT_TEMPLATE = toml_prompt["prompt_comparative_keywords_update"]["user"]
this_workers = toml_config["llm"]["max_workers"]
this_url = toml_config["llm"]["base_url"]
this_model = toml_config["llm"]["model1"]
this_temperature = toml_config["llm"]["temperature"]

def process_item(item: tuple, apikey: str, protocol: str, version: str) -> tuple:
    """处理单个章节"""
    heading, content = item
    client = OpenAI(
        api_key=apikey,
        base_url=this_url
    )

    try:
        prompt = PROMPT_TEMPLATE.format(protocol=protocol,version=version,content=content)
        response = client.chat.completions.create(
            model=this_model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
        )

        # 验证响应格式
        result = json.loads(response.choices[0].message.content)
        if not all(isinstance(v, list) for v in result.values()):
            raise ValueError("无效的响应格式")

        return heading, result

    except json.JSONDecodeError:
        return heading, {"error": "无效的JSON响应"}
    except Exception as e:
        return heading, {"error": str(e)}


def main(apikey: str, protocol: str, version: str, config):
    """主处理流程"""
    try:
        # 加载输入数据
        input_path = config["paths"]["paragraph_output"]
        with open(input_path, "r", encoding="utf-8") as f:
            protocol_chapter = json.load(f)

        # 多线程处理
        results = {}
        with ThreadPoolExecutor(
                max_workers=this_workers
        ) as executor:
            futures = {
                executor.submit(process_item, item, apikey, protocol, version): item
                for item in protocol_chapter.items()
            }

            # 进度条显示
            with tqdm(
                    total=len(futures),
                    desc="分析比较关系",
                    unit="section",
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
            ) as pbar:
                for future in as_completed(futures):
                    heading, result = future.result()
                    results[heading] = result
                    pbar.update(1)
                    pbar.set_postfix(sec=heading[:15])

        # 保存结果
        output_path = config["paths"]["comparative_output"]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n比较关系分析完成，结果保存至: {output_path}")

    except Exception as e:
        print(f"处理失败: {str(e)}")
        raise


if __name__ == "__main__":
    #print("开始执行比较关键词扩充")
    parser = argparse.ArgumentParser()
    parser.add_argument("--apikey", required=True, help="DeepSeek API密钥")
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--config", required=True, help="配置文件路径")
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)
    main(args.apikey, args.protocol, args.version, config)