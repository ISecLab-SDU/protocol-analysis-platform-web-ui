import json
import re
from pathlib import Path
from typing import List, Dict, Set
from openai import OpenAI
import toml
import argparse

# ========== 全局配置 ==========
script_dir = Path(__file__).parent.parent
config_path = script_dir / "config.toml"
prompt_path = script_dir / "prompt.toml"
toml_config = toml.load(config_path)
toml_prompt = toml.load(prompt_path)
this_url = toml_config["llm"]["base_url"]
this_model = toml_config["llm"]["model1"]

# 完整 RFC 2119 + RFC 8174 核心情态关键词
RFC2119_CORE = {
    "MUST", "MUST NOT",
    "REQUIRED",
    "SHALL", "SHALL NOT",
    "SHOULD", "SHOULD NOT",
    "RECOMMENDED", "NOT RECOMMENDED"
}

# ========== 数据加载 ==========
def load_processed_data(config: Dict, data_type: str) -> Dict:
    """加载中间结果数据"""
    data_path = config["paths"][f"{data_type}_output"]
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] {data_type} 数据加载失败: {str(e)}")
        raise


def extract_keywords(data: Dict) -> List[str]:
    """从处理结果中提取关键词（不过滤）"""
    keywords = []

    for section, content in data.items():
        try:
            if not content or content == "{}":
                continue

            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    continue

            if isinstance(content, dict):
                for key, values in content.items():
                    if isinstance(values, list):
                        keywords.extend(values)
                    elif isinstance(values, dict):
                        keywords.extend(values.keys())
                        for v in values.values():
                            if isinstance(v, list):
                                keywords.extend(v)
                            elif isinstance(v, str):
                                keywords.append(v)

        except Exception as e:
            print(f"[WARNING] 章节处理异常 [{section[:15]}]: {str(e)}")

    return list(set(keywords))


# ========== LLM 调用 ==========
def classify_keywords_with_llm(keywords_by_type: Dict[str, List[str]], apikey: str, base_url: str, model: str, protocol_name: str) -> Dict[str, List[str]]:
    client = OpenAI(api_key=apikey, base_url=base_url)
    result = {}

    prompts = {
        "specify": toml_prompt["prompt_classify_keywords_specify"]["user"].format(
            keywords=keywords_by_type["specify"],
            protocol=protocol_name
        ),
        "modal": toml_prompt["prompt_classify_keywords_modal"]["user"].format(
            keywords=keywords_by_type["modal"],
            core_modals=list(RFC2119_CORE)
        ),
        "comparative": toml_prompt["prompt_classify_keywords_comparative"]["user"].format(
            keywords=keywords_by_type["comparative"],
            core_comparatives = [
            # 优劣比较
            "better", "worse", "superior", "inferior", "improved", "degraded",
            "more reliable", "less reliable",
             "stronger", "weaker", "higher quality", "lower quality",

            # 速度/性能
            "faster", "slower", "more efficient", "less efficient",
            "more optimal", "less optimal", "higher performance", "lower performance",

            # 概率/可能性
            "more likely", "less likely", "more probable", "less probable",
            "more certain", "less certain",

            # 差异/比较
            "different", "similar", "greater than", "less than", "equal to",
            "more than", "fewer than", "increase", "decrease",
            ]
    
        )
    }
    
    for cat, prompt in prompts.items():
        try:
            print(f"[INFO] 正在处理 {cat} 类别...")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            response_content = response.choices[0].message.content
            print(f"[DEBUG] {cat} 响应长度: {len(response_content)} 字符")
            
            # 尝试解析JSON
            try:
                parsed_response = json.loads(response_content)
                if cat in parsed_response:
                    result[cat] = parsed_response[cat]
                else:
                    print(f"[WARNING] 响应中缺少 '{cat}' 键，使用空列表")
                    result[cat] = []
            except json.JSONDecodeError as e:
                print(f"[ERROR] {cat} JSON解析失败: {str(e)}")
                print(f"[DEBUG] 响应内容前500字符: {response_content[:500]}")
                print(f"[DEBUG] 响应内容后500字符: {response_content[-500:]}")
                
                # 尝试修复常见的JSON问题
                try:
                    # 移除可能的控制字符
                    cleaned_content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', response_content)
                    # 尝试修复未转义的引号
                    cleaned_content = re.sub(r'(?<!\\)"(?=\w)', '\\"', cleaned_content)
                    parsed_response = json.loads(cleaned_content)
                    if cat in parsed_response:
                        result[cat] = parsed_response[cat]
                        print(f"[INFO] {cat} JSON修复成功")
                    else:
                        result[cat] = []
                except:
                    print(f"[ERROR] {cat} JSON修复失败，使用空列表")
                    result[cat] = []
                    
        except Exception as e:
            print(f"[ERROR] {cat} 处理失败: {str(e)}")
            result[cat] = []

    return result   


# ========== 主流程 ==========
def main(apikey, config, protocol):
    try:
        all_keywords = {"specify": [], "modal": [], "comparative": []}

        for data_type in ["specify", "modal", "comparative"]:
            data = load_processed_data(config, data_type)
            extracted = extract_keywords(data)
            all_keywords[data_type] = list(set(extracted))

        # 用 LLM 过滤
        classified = classify_keywords_with_llm(all_keywords, apikey, this_url, this_model, protocol)

        # 保存
        output_path = config["paths"]["final_output"]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(classified, f, ensure_ascii=False, indent=2)

        print("\n关键词分类完成")
        for cat, kws in classified.items():
            print(f"{cat}: {len(kws)} 条")
        print(f"结果文件: {output_path}")

    except Exception as e:
        print(f"[ERROR] 最终结果生成失败: {str(e)}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apikey", required=True, help="DeepSeek API密钥")
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--config", required=True, help="配置文件路径")
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    main(args.apikey, config, args.protocol)
