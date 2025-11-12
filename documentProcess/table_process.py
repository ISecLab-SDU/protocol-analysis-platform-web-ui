import json
import time
from openai import OpenAI
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import toml
from pathlib import Path

# 获取当前脚本所在目录
script_dir = Path(__file__).parent.parent
config_path = script_dir / "config.toml"
prompt_path = script_dir / "prompt.toml"
toml_config = toml.load(config_path)
toml_prompt = toml.load(prompt_path)
PROMPT_TEMPLATE = toml_prompt["prompt_table_process"]["user"]
this_workers = toml_config["llm"]["max_workers"]
this_url = toml_config["llm"]["base_url"]
this_model = toml_config["llm"]["model2"]
this_temperature = toml_config["llm"]["temperature"]

def filter_charts(blocks):
    """过滤掉模型输出中明显无效的图表说明"""
    cleaned = []
    for b in blocks:
        if not b.strip():
            continue
        if re.search(r'(no\s+(chart|output|diagram))|(没有图表)|(无图)|(不包含图表)', b, re.I):
            continue
        if re.search(r'after reviewing|purely descriptive text', b, re.I):
            continue
        cleaned.append(b.strip())
    return cleaned

def sanitize_text(text: str, limit: int = 10000) -> str:
    """简单截断，避免超长上下文"""
    if text and len(text) > limit:
        return text[:limit] + "\n...[TRUNCATED]..."
    return text or ""

def try_extract_codeblock(s: str):
    """从模型输出中提取 plaintext 代码块内容"""
    # 匹配 ```plaintext ... ``` 或 ``` ... ```
    matches = re.findall(r"```(?:plaintext)?\s*([\s\S]*?)\s*```", s, re.IGNORECASE)
    if matches:
        return [m.strip() for m in matches]  # 去掉前后空格
    return [s.strip()] if s.strip() else []  # 没代码块时，直接返回原文本（非空）

def process_section(client, title, content):
    """处理单个章节，返回结果"""
    prompt = PROMPT_TEMPLATE.format(
        title=sanitize_text(title, 2000),
        content=sanitize_text(content, 12000)
    )

    try:
        resp = client.chat.completions.create(
            model=this_model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            stream=False,
            temperature=this_temperature
        )
        raw = resp.choices[0].message.content.strip()
        parsed_blocks = try_extract_codeblock(raw)
        parsed_blocks = filter_charts(parsed_blocks)  # 新增过滤
        if parsed_blocks:
            # 统一返回 list，不管多少个表
            return title, {"charts": parsed_blocks}
        else:
            return title, {}
    except Exception as e:
        print(f"  ❌ {title} 调用失败：{e}")
        return title, {}

def save_markdown(results, output_path):
    """保存为 Markdown 格式"""
    with open(output_path, "w", encoding="utf-8") as f:
        for title, data in results.items():
            if not data.get("charts"):
                continue
            f.write(f"## {title}\n\n")
            for chart in data["charts"]:
                f.write("```plaintext\n")
                f.write(chart.strip() + "\n")
                f.write("```\n\n")

def process_tables(config, max_workers=this_workers):
    """多线程提取表格信息"""
    client = OpenAI(api_key=config["api_key"], base_url=this_url)

    with open(config["paths"]["text_processed"], "r", encoding="utf-8") as f:
        sections = json.load(f)

    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_section, client, title, content)
            for title, content in sections.items()
        ]

        for future in tqdm(as_completed(futures), total=len(futures), desc="提取图表信息"):
            title, data = future.result()
            results[title] = data
            time.sleep(0.2)  # 稍微限速，避免API封禁

    with open(config["paths"]["tables"], "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

        # 保存 Markdown
    markdown_path = Path(config["paths"]["tables"]).with_suffix(".md")
    save_markdown(results, markdown_path)

    print(f"\n✅ 已提取图表信息，保存到：{config['paths']['tables']}")
    print(f"✅ Markdown 文件保存到：{markdown_path}")
