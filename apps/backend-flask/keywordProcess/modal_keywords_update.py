import json
import argparse
from pathlib import Path
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from tqdm import tqdm
import toml
import re

# 获取当前脚本所在目录
script_dir = Path(__file__).parent.parent
config_path = script_dir / "config.toml"
prompt_path = script_dir / "prompt.toml"
toml_config = toml.load(config_path)
toml_prompt = toml.load(prompt_path)
PROMPT_TEMPLATE = toml_prompt["prompt_modal_keywords_update"]["user"]
this_workers = toml_config["llm"]["max_workers"]
this_url = toml_config["llm"]["base_url"]
this_model = toml_config["llm"]["model1"]
this_temperature = toml_config["llm"]["temperature"]

def process_item(item: tuple, apikey: str) -> tuple:
    """处理单个章节的线程安全函数"""
    heading, content = item
    client = OpenAI(
        api_key=apikey,
        base_url=this_url
    )

    try:
        # 动态构建提示词模板
        prompt_template = PROMPT_TEMPLATE.format(content=content)
        response = client.chat.completions.create(
            model=this_model,
            messages=[
                {"role": "user", "content": prompt_template}
            ],
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content
        match = re.search(r"\{[\s\S]*\}", raw_content)
        if not match:
            return heading, {"warning": "JSON parsed but format unexpected", "data": raw_content}
        clean_json_str = match.group(0)
        # 验证并清理响应
        result = json.loads(clean_json_str)
        #print(result)
        if not all(isinstance(v, list) for v in result.values()):
             return heading, {"warning": "JSON parsed but format unexpected", "data": clean_json_str}

        return heading, result

    except json.JSONDecodeError:
        return heading, {"warning": "JSON parsed but format unexpected", "data": clean_json_str}
    except Exception as e:
        return heading, {"warning": "JSON parsed but format unexpected", "data": clean_json_str}


def main(apikey: str,config):
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
                executor.submit(process_item, item, apikey): item
                for item in protocol_chapter.items()
            }

            # 带进度条处理
            with tqdm(
                    total=len(futures),
                    desc="分析情态关键词",
                    unit="section",
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
            ) as pbar:
                for future in as_completed(futures):
                    heading, result = future.result()
                    results[heading] = result
                    pbar.update(1)
                    pbar.set_postfix(sec=heading[:15])

        # 保存结果
        output_path = config["paths"]["modal_output"]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n情态关键词扩展完成，结果保存至: {output_path}")

    except Exception as e:
        print(f"❌ 处理失败: {str(e)}")
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
    main(args.apikey, config)