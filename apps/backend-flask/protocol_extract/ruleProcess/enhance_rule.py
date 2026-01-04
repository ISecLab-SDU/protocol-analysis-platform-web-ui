import argparse
import pandas as pd
import json
from tqdm import tqdm
from pathlib import Path
import toml
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# ---------- 配置读取 ----------
script_dir = Path(__file__).parent.parent
config_path = script_dir / "config.toml"
prompt_path = script_dir / "prompt.toml"

toml_config = toml.load(config_path)
toml_prompt = toml.load(prompt_path)
PROMPT_TEMPLATE = toml_prompt["prompt_enhance_rule"]["user"]

this_url = toml_config["llm"]["base_url"]
this_model = toml_config["llm"]["model1"]
this_temperature = toml_config["llm"]["temperature"]
this_workers = toml_config["llm"]["max_workers"]

# ---------- 正则与工具函数 ----------
EXPLICIT_REF_RE = re.compile(
    r"(?i)\b(?:table|figure|diagram)\s*(\d+)\b|表\s*(\d+)\b|图\s*(\d+)\b|流程图\s*(\d+)\b"
)
def find_all_explicit_references_with_type(text: str):
    """返回段落中所有 Table/Figure/Flowchart 的引用，列表 [(type, number)]"""
    refs = []
    for m in EXPLICIT_REF_RE.finditer(text):
        if m.group(1):
            refs.append(("table", m.group(1)))
        elif m.group(2):
            refs.append(("table", m.group(2)))
        elif m.group(3):
            refs.append(("figure", m.group(3)))
        elif m.group(4):
            refs.append(("flowchart", m.group(4)))
    return refs

def load_blocks(md_path: Path):
    """
    读取 Markdown 中的图表块信息，返回 {heading: [blocks]}
    blocks = {type, number, title, content}
    """
    HEADING_SECTION_RE = re.compile(r"^##\s+(.*?)\s*$([\s\S]*?)(?=^##\s+|\Z)", re.MULTILINE)
    CODEBLOCK_RE = re.compile(r"[A-Za-z0-9_\-]*\n([\s\S]*?)\n ", re.MULTILINE)

    BLOCK_TITLE_RE = re.compile(
        r"^(?:(Table|Figure|Diagram)|(?:表|图|流程图))\s*(\d+)?\s*[:：]?\s*(.*)$", re.IGNORECASE
    )

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
                    raw, num, tail = m.group(1), m.group(2), m.group(3) or ""
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
                    title = (f"{ttype.capitalize()} {number}: {tail}" if number else f"{ttype.capitalize()}: {tail}") 
                    break
            blocks.append({"type": ttype, "number": number, "title": title, "content": content})
        if blocks:
            sections[heading] = blocks
    return sections

# ---------- 主流程 ----------
def run_enhance_rule(config, api_key, protocol, version):
    """执行增强阶段：生成提示词 + 调用大模型增强句子"""

    # 读取 Excel
    excel_path = Path(config["paths"]["excel_sentences"])
    df = pd.read_excel(excel_path, engine='openpyxl')

    # 读取段落数据
    paragraph_path = Path(config["paths"]["paragraph_output"])
    with open(paragraph_path, "r", encoding="utf-8") as f:
        paragraph_data = json.load(f)

    # 读取图表 Markdown
    table_md_path = Path(config["paths"]["table"])
    blocks_by_heading = load_blocks(table_md_path)

    # 只处理 Conforms 的句子 2025-10-29修改
    #conforms_df = df[df["Second_Filter_Result"] == "Conforms"].copy()
    conforms_df = df[df["Is_Matched"] == True].copy()
    if conforms_df.empty:
        print("没有通过第二阶段筛选的句子，跳过增强阶段。")
        return

    # 初始化提示词列和增强列
    if "Generated_Prompt" not in df.columns:
        df["Generated_Prompt"] = ""
    if "Enhanced_Sentence" not in df.columns:
        df["Enhanced_Sentence"] = ""

    # 初始化 OpenAI 客户端
    client = OpenAI(api_key=api_key, base_url=this_url)

    # 定义增强函数
    def enhance_sentence(heading, sentence):
        paragraph = paragraph_data.get(heading, "")
        
        # 找出段落中所有图表引用
        refs = find_all_explicit_references_with_type(paragraph)
        attached_contents = ""
        for ttype, num in refs:
            for block in blocks_by_heading.get(heading, []):
                if block["type"] == ttype and block["number"] == num:
                    title = block.get("title") or f"{ttype.capitalize()} {num}"
                    attached_contents += f"\n\n{title}\n{block['content']}"

        # 拼接 prompt
        prompt_text = PROMPT_TEMPLATE.format(
            protocol=protocol,
            version=version,
            heading=heading,
            sentence=sentence
        )
        if attached_contents:
            prompt_text += f"\n\n相关图表内容:\n{attached_contents}"

        # 调用模型（重试机制）
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=this_model,
                    messages=[
                        {"role": "system", "content": prompt_text},
                        {"role": "user", "content": f"原始句子：{sentence}\n完整段落：{paragraph}"}
                    ],
                    temperature=this_temperature,
                    stream=False
                )
                enhanced_text = response.choices[0].message.content.strip()
                if "Enhanced Rule:" in enhanced_text:
                    enhanced_rule = enhanced_text.split("Enhanced Rule:", 1)[1].strip()
                else:
                    enhanced_rule = enhanced_text
                return prompt_text, enhanced_rule
            except Exception as e:
                print(f"API Error (attempt {attempt + 1}): {e}")
                time.sleep(2)
        return prompt_text, sentence  # 失败返回原句子

    # 并发处理
    sentences_to_enhance = conforms_df[["Heading", "Sentence"]].values.tolist()
    enhanced_results = []

    with ThreadPoolExecutor(max_workers=this_workers) as executor:
        futures = {
            executor.submit(enhance_sentence, heading, sentence): (heading, sentence)
            for heading, sentence in sentences_to_enhance
        }

        for future in tqdm(as_completed(futures), total=len(futures), desc="Enhancing sentences"):
            heading, sentence = futures[future]
            try:
                prompt_text, enhanced_sentence = future.result()
                # 写回 DataFrame
                df.loc[df["Sentence"] == sentence, "Generated_Prompt"] = prompt_text
                df.loc[df["Sentence"] == sentence, "Enhanced_Sentence"] = enhanced_sentence
                enhanced_results.append({
                    "heading": heading,
                    "sentence": sentence,
                    "enhanced_sentence": enhanced_sentence,
                    "final_prompt": prompt_text
                })
            except Exception as e:
                print(f"Enhancement failed for sentence: {str(e)}")
                df.loc[df["Sentence"] == sentence, "Enhanced_Sentence"] = sentence

    # 保存 Excel
    df.to_excel(excel_path, index=False, engine='openpyxl')

    # 保存 JSON 方便检查
    output_json_path = excel_path.parent / "enhanced_sentences.json"
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(enhanced_results, f, ensure_ascii=False, indent=2)

    print(f"✅ 句子增强完成，共处理 {len(enhanced_results)} 个句子")
    print(f"结果已保存至 {excel_path} 和 {output_json_path}")

# ---------- 入口 ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="增强阶段：生成提示词并调用大模型增强句子")
    parser.add_argument("--apikey", required=True, help="DeepSeek API 密钥")
    parser.add_argument("--protocol", required=True, help="协议名称")
    parser.add_argument("--version", required=True, help="协议版本")
    parser.add_argument("--config", required=True, help="配置文件路径")
    args = parser.parse_args()

    # 读取配置
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    run_enhance_rule(config, args.apikey, args.protocol, args.version)
