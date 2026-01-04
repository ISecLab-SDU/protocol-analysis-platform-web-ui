import argparse
import pandas as pd
from openai import OpenAI
from tqdm import tqdm
from pathlib import Path
import toml
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------- 配置读取 ----------
script_dir = Path(__file__).parent.parent
config_path = script_dir / "config.toml"
prompt_path = script_dir / "prompt.toml"
toml_config = toml.load(config_path)
toml_prompt = toml.load(prompt_path)
PROMPT_TEMPLATE = toml_prompt["prompt_second_rule"]["user"]
this_url = toml_config["llm"]["base_url"]
this_model = toml_config["llm"]["model1"]
this_temperature = toml_config["llm"]["temperature"]
this_max_workers = toml_config["llm"]["max_workers"] # 默认5线程

# ---------- 正则与工具函数 ----------
HEADING_SECTION_RE = re.compile(r"^##\s+(.*?)\s*$([\s\S]*?)(?=^##\s+|\Z)", re.MULTILINE)
CODEBLOCK_RE = re.compile(r"```[A-Za-z0-9_\-]*\n([\s\S]*?)\n```", re.MULTILINE)
EXPLICIT_REF_RE = re.compile(
    r"(?i)\b(?:table|figure|diagram)\s*(\d+)\b|表\s*(\d+)\b|图\s*(\d+)\b|流程图\s*(\d+)\b"
)
BLOCK_TITLE_RE = re.compile(r"^(?:(Table|Figure|Diagram)|(?:表|图|流程图))\s*(\d+)?\s*[:：]?\s*(.*)$", re.IGNORECASE)

def load_sections_with_blocks(md_path: Path):
    sections = {}
    text = md_path.read_text(encoding="utf-8")
    for sec in HEADING_SECTION_RE.finditer(text):
        heading = sec.group(1).strip()
        body = sec.group(2)
        blocks = []
        for cb in CODEBLOCK_RE.finditer(body):
            content = cb.group(1).strip()
            ttype = None
            number = None
            title = None
            for line in content.splitlines():
                s = line.strip()
                if not s:
                    continue
                m = BLOCK_TITLE_RE.match(s)
                if m:
                    raw = m.group(1)
                    num = m.group(2)
                    tail = m.group(3) or ""
                    if raw:
                        ttype = raw.lower()
                    else:
                        if s.startswith("表"):
                            ttype = "table"
                        elif s.startswith("图"):
                            ttype = "figure"
                        elif s.startswith("流程图"):
                            ttype = "flowchart"
                    number = num
                    title = (f"{ttype.capitalize()} {number}: {tail}" if number else f"{ttype.capitalize()}: {tail}") if ttype else (tail or None)
                break
            blocks.append({
                "type": ttype,
                "number": number,
                "title": title,
                "content": content
            })
        if blocks:
            sections[heading] = blocks
    return sections

def find_all_explicit_references_with_type(sentence: str):
    refs = []
    for m in EXPLICIT_REF_RE.finditer(sentence):
        if m.group(1):
            refs.append(("table", m.group(1)))
        elif m.group(2):
            refs.append(("table", m.group(2)))
        elif m.group(3):
            refs.append(("figure", m.group(3)))
        elif m.group(4):
            refs.append(("flowchart", m.group(4)))
    return refs

def pick_blocks_by_type_and_number(sections: dict, ttype: str, number: str):
    matched = []
    for blocks in sections.values():
        for b in blocks:
            if b.get("type") == ttype and b.get("number") == number:
                matched.append(b)
    return matched

def process_sentence(client, protocol, version, sentence, heading, sections):
    refs = find_all_explicit_references_with_type(sentence)
    sentence_for_prompt = sentence
    attached_titles = []

    for ttype, num in refs:
        blocks = pick_blocks_by_type_and_number(sections, ttype, num)
        for block in blocks:
            title = block.get("title") or f"{ttype.capitalize()} {num}"
            attached_titles.append(title)
            sentence_for_prompt += f"\n\n相关内容:\n{title}\n{block['content']}"

    prompt_text = PROMPT_TEMPLATE.format(protocol=protocol, version=version, sentence=sentence_for_prompt)

    try:
        response = client.chat.completions.create(
            model=this_model,
            messages=[{"role": "user", "content": prompt_text}],
            temperature=this_temperature,
            stream=False
        )
        model_output = response.choices[0].message.content.strip()
        conforms = "Conforms" in model_output
        result_text = "Conforms" if conforms else "Does not conform"
    except Exception as e:
        model_output = f"Error: {str(e)}"
        result_text = "Error"

    return {
        "heading": heading,
        "sentence": sentence,
        "final_prompt": prompt_text,
        "attached_titles": attached_titles,
        "result": result_text,
        "model_output": model_output
    }

# ---------- 主流程 ----------
def run_second_rule(api_key, protocol, version, config):
    excel_path = Path(config["paths"]["excel_sentences"])
    table_md_path = Path(config["paths"]["table"])

    df = pd.read_excel(excel_path, engine='openpyxl')
    matched_rows = df[df["Is_Matched"] == True]

    sections = load_sections_with_blocks(table_md_path)
    client = OpenAI(api_key=api_key, base_url=this_url)

    prompts = []
    """
    with ThreadPoolExecutor(max_workers=this_max_workers) as executor:
        #2025-10-29修改
        '''
        futures = [
            executor.submit(process_sentence, client, protocol, version, row["Sentence"], row["Heading"].strip(), sections)
            for _, row in matched_rows.iterrows()
        ]
        '''
        # 修改为：
        futures = [
            executor.submit(process_sentence, client, protocol, version, row.get("Enhanced_Sentence") or row["Sentence"], row["Heading"].strip(), sections)
            for _, row in matched_rows.iterrows()
        ]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing Sentences"):
            prompts.append(future.result())
    """
    with ThreadPoolExecutor(max_workers=this_max_workers) as executor:
        # --------------------------
        # 关键修改1：保留原始行索引，用于后续精准匹配
        # --------------------------
        futures = []
        for idx, row in matched_rows.iterrows():  # 遍历带索引的行
            # 使用增强后的句子（若存在）
            sentence = row.get("Enhanced_Sentence") or row["Sentence"]
            # 将future与原始索引绑定，确保结果能对应到正确行
            future = executor.submit(
                process_sentence, 
                client, protocol, version, 
                sentence, 
                row["Heading"].strip(), 
                sections
            )
            futures.append( (future, idx) )  # 存储 (future对象, 原始行索引)

        # --------------------------
        # 关键修改2：移除 as_completed() 的 key 参数，直接迭代处理
        # --------------------------
        for future in tqdm(
            as_completed([f for f, idx in futures]),  # 仅传递future对象列表
            total=len(futures), 
            desc="Processing Sentences"
        ):
            # 找到当前future对应的原始索引
            for f, idx in futures:
                if f == future:
                    result = future.result()
                    prompts.append(result)
                    # 通过索引写入结果
                    df.loc[idx, "Second_Filter_Result"] = result["result"]
                    futures.remove( (f, idx) )  # 移除已处理的项，避免重复匹配
                    break

    df.to_excel(excel_path, index=False, engine='openpyxl')
    # 保存 JSON
    output_path = excel_path.parent / "generated_prompts_with_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)

    print(f"处理完成，结果已写回 Excel")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成提示词并调用大模型（多线程版）")
    parser.add_argument("--apikey", required=True, help="API 密钥")
    parser.add_argument("--protocol", required=True, help="协议名称")
    parser.add_argument("--version", required=True, help="协议版本")
    parser.add_argument("--config", required=True, help="配置文件路径（JSON）")
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    run_second_rule(args.apikey, args.protocol, args.version, config)
