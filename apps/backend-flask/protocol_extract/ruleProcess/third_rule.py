import argparse
import pandas as pd
import json
import time
from tqdm import tqdm
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import toml

# 获取当前脚本所在目录
script_dir = Path(__file__).parent.parent
config_path = script_dir / "config.toml"
prompt_path = script_dir / "prompt.toml"
toml_config = toml.load(config_path)
toml_prompt = toml.load(prompt_path)
PROMPT_TEMPLATE = toml_prompt["prompt_third_rule"]["user"]
this_url = toml_config["llm"]["base_url"]
this_model = toml_config["llm"]["model1"]
this_temperature = toml_config["llm"]["temperature"]
this_workers = toml_config["llm"]["max_workers"]

def run_third_rule(api_key, protocol, version, config):
    # 读取Excel文件
    excel_path=Path(config["paths"]["excel_sentences"])
    df = pd.read_excel(excel_path, engine='openpyxl')

    # 只筛选通过第二阶段的句子
    df = df[df["Second_Filter_Result"] == "Conforms"]

    # 处理缺失的 Heading 列
    if "Heading" not in df.columns:
        df["Heading"] = ""

    # 准备处理数据（优先使用增强后的句子）
    sentences_to_process = []
    for _, row in df.iterrows():
        heading = row["Heading"]
        # 优先使用 Enhanced_Sentence，如果不存在则使用原始 Sentence
        sentence = row.get("Enhanced_Sentence") or row["Sentence"]
        sentences_to_process.append([heading, sentence])

    # 初始化 OpenAI 客户端，使用配置文件中的设置
    client = OpenAI(api_key=api_key, base_url=this_url)

    def process_sentence(heading, sentence):
        """调用大模型处理句子"""
        prompt = PROMPT_TEMPLATE.format(protocol=protocol, version=version, heading=heading, sentence=sentence)

        for _ in range(3):  # 失败重试机制
            try:
                response = client.chat.completions.create(
                    model=this_model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    response_format={'type': 'json_object'},
                    temperature=this_temperature,
                    stream=False
                )

                model_output = response.choices[0].message.content.strip()
                return json.loads(model_output)

            except Exception as e:
                print(f"API Error: {e}, Retrying...")
                time.sleep(2)

        return {  # 默认返回结构
            "rule": sentence,
            "req_type": "",
            "req_fields": [],
            "res_type": "",
            "res_fields": []
        }

    # 并发处理
    results = []
    with ThreadPoolExecutor(max_workers=this_workers) as executor:
        futures = {
            executor.submit(process_sentence, h, s): (h, s)
            for h, s in sentences_to_process
        }

        # 进度条显示
        progress = tqdm(
            as_completed(futures),
            total=len(futures),
            desc=f"Analyzing {protocol} {version}"
        )

        for future in progress:
            try:
                results.append(future.result())
            except Exception as e:
                print(f"Processing failed: {str(e)}")

    # 保存结果
    processed_file=config["paths"]["processed"]
    with open(processed_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"\n[OK] {protocol} {version} 协议分析完成，结果已保存至processed_results.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="通用协议字段解析器")
    parser.add_argument("--apikey", required=True, help="DeepSeek API 密钥")
    parser.add_argument("--protocol", required=True, help="目标协议名称（如 HTTP/MQTT）")
    parser.add_argument("--version", required=True, help="协议版本号（如 1.1/5.0）")
    parser.add_argument("--config", required=True, help="配置文件路径")
    args = parser.parse_args()

    # 读取配置文件
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    run_third_rule(
        api_key=args.apikey,
        protocol=args.protocol,
        version=args.version,
        config=config
    )