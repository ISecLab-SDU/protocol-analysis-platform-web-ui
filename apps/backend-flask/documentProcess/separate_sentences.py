import re
import json
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_random_exponential
from openai import OpenAI
import concurrent.futures
from typing import Any

from tqdm import tqdm
import toml
from pathlib import Path

script_dir = Path(__file__).parent.parent
config_path = script_dir / "config.toml"
prompt_path = script_dir / "prompt.toml"
toml_config = toml.load(config_path)
toml_prompt = toml.load(prompt_path)
this_workers = toml_config["llm"]["max_workers"]
this_url = toml_config["llm"]["base_url"]
PROMPT_TEMPLATE = toml_prompt["prompt_separate_sentences"]["user"]
this_model = toml_config["llm"]["model1"]

def sanitize_text(text: str, limit: int = 10000) -> str:
    if text and len(text) > limit:
        return text[:limit] + "\n...[TRUNCATED]..."
    return text or ""

@retry(stop=stop_after_attempt(3), wait=wait_random_exponential(min=1, max=10))
def process_sentence(client, heading, sentence):
    prompt = PROMPT_TEMPLATE.format(heading=sanitize_text(heading, 2000), sentence=sanitize_text(sentence, 12000)) 
    response = client.chat.completions.create(
        model=this_model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        response_format={
            'type': 'json_object'
        }
    )
    return response.choices[0].message.content.strip()


def process_sentences(config):
    print("🔄 Processing sentences...")

    # 加载数据
    with open(config["paths"]["text_processed"], "r") as f:
        headings = json.load(f)
    with open(config["paths"]["headings"], "r") as f:
        selected = json.load(f)

    client = OpenAI(api_key=config["api_key"], base_url=this_url)
    results = {}
    df_data: list[list[Any]] = []

    # 使用tqdm进度条
    with tqdm(total=len(selected), desc="处理章节") as pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=this_workers) as executor:  # 减少并发数避免超限
            futures = {}

            # 提交章节级任务
            print(f"[DEBUG] selected章节数: {len(selected)}")
            print(f"[DEBUG] headings章节数: {len(headings)}")
            print(f"[DEBUG] selected章节示例: {list(selected)[:5]}")
            print(f"[DEBUG] headings章节示例: {list(headings)[:5]}")
            for heading in selected:
                if heading in headings:
                    if not headings[heading].strip():
                        print(f"[WARN] {heading} 在headings中但内容为空，跳过")
                        continue
                    sentences = [s for s in re.split(r'(?<=[.!?])\s+', headings[heading]) if s.strip()]
                    if not sentences:
                        print(f"[WARN] {heading} 内容分句后为空，跳过")
                        continue
                    futures[executor.submit(process_sentence, client, heading, sentences)] = heading
                else:
                    print(f"[WARN] {heading} 不在headings中，跳过")

            # 处理结果
            for future in concurrent.futures.as_completed(futures):
                heading = futures[future]
                try:
                    optimized_text = future.result()
                    results[heading] = optimized_text

                    # 记录到DataFrame
                    original_sentences = re.split(r'(?<=[.!?])\s+', headings[heading])
                    optimized_sentences = re.split(r'(?<=[.!?])\s+', optimized_text)
                    for orig, opt in zip(original_sentences, optimized_sentences):
                        df_data.append([heading, orig, opt])

                except Exception as e:
                    print(f"❌ 章节处理失败: {heading} - {str(e)}")
                    results[heading] = headings[heading]  # 保留原始内容
                finally:
                    pbar.update(1)

    # 保存结果
    df = pd.DataFrame(df_data)
    df.columns = ["章节", "原句", "修正"]
    df.to_excel(config["paths"]["output_excel"], index=False)

    with open(config["paths"]["output_json"], "w", encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
