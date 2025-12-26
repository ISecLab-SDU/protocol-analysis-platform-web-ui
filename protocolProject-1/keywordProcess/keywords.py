import json
import re
from pathlib import Path
from typing import Dict, List
import argparse


def extract_quoted_keywords(config: Dict) -> List[str]:
    """
    从JSON文件提取带引号的关键词（支持多级结构和自动修复）

    参数:
        config: 包含路径配置的字典

    返回:
        带引号的关键词列表
    """
    try:
        # 动态解析路径
        json_path = Path(config["paths"]["specify_keywords"])

        if not json_path.exists():
            raise FileNotFoundError(f"JSON关键词文件不存在: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        # JSON解析尝试
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败，尝试修复... (错误位置: {e.pos})")
            content = re.sub(r',\s*}(?=,|\s*$)', '}', content)  # 修复多余逗号
            content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)  # 移除注释
            data = json.loads(content)

        # 递归提取关键词
        keywords = []

        def _extract(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    keywords.append(f'"{k}"')
                    _extract(v)
            elif isinstance(obj, list):
                for item in obj:
                    _extract(item)
            elif isinstance(obj, str):
                keywords.append(f'"{obj}"')

        _extract(data)
        return list(set(keywords))  # 去重

    except Exception as e:
        print(f"❌ JSON关键词提取失败: {str(e)}")
        return []


def extract_txt_keywords(config: Dict) -> List[str]:
    """
    从文本文件提取关键词

    参数:
        config: 包含路径配置的字典

    返回:
        带引号的关键词列表
    """
    try:
        txt_path = Path(config["paths"]["specify_keywords"])

        if not txt_path.exists():
            raise FileNotFoundError(f"文本关键词文件不存在: {txt_path}")

        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
            return [f'"{m}"' for m in re.findall(r'"([^"]*)"', content, re.DOTALL)]  # ✅ 支持跨行
            #return [f'"{line.strip()}"' for line in f if line.strip()]

    except Exception as e:
        print(f"❌ 文本关键词提取失败: {str(e)}")
        return []


def reconstruct_paragraphs(config: Dict) -> None:
    """
    重组段落内容

    参数:
        config: 包含路径配置的字典
    """
    
    try:
        input_path = config["paths"]["input_json"]
        output_path = config["paths"]["paragraph_output"]

        with open(input_path, "r", encoding="utf-8") as f:
            content = json.load(f)

        results = {}
        for heading, data in content.items():
            try:
                # 统一数据结构处理
                if isinstance(data, str):
                    try:
                        data = json.loads(data.replace('\n', ''))
                    except Exception:
                        # 无法解析，直接作为单条文本
                        data = [{"Original": data, "Adjusted": "No change"}]

                #sentences = data.get(heading, data) if isinstance(data, dict) else data
                if isinstance(data, dict):
                    # 取第一个 key 的值作为列表
                    sentences = next(iter(data.values()), [])
                    if not isinstance(sentences, list):
                        sentences = [{"Original": str(sentences), "Adjusted": "No change"}]
                elif isinstance(data, list):
                    sentences = data
                else:
                    # 兜底，转换为单条句子
                    sentences = [{"Original": str(data), "Adjusted": "No change"}]
                #paragraph = ' '.join(
                    #item.get('调整后', item.get('原句', str(item)))
                    #for item in sentences
                #)
                paragraph = ' '.join(
                    item["Original"] if item.get("Adjusted") == "No change" else item.get("Adjusted",item.get("Original", str(item)))
                    for item in sentences
                )
                results[heading] = re.sub(r'\s+', ' ', paragraph).strip()

            except Exception as e:
                print(f"章节处理失败: {heading} - {str(e)}".encode('utf-8', errors='ignore').decode('utf-8'))
                results[heading] = ""

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"已生成段落文件: {output_path}".encode('utf-8', errors='ignore').decode('utf-8'))

    except Exception as e:
        print(f"段落重组失败: {str(e)}".encode('utf-8', errors='ignore').decode('utf-8'))
        raise


def main():
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--protocol", help="协议名称")  # 新增，可选
        parser.add_argument("--version", help="协议版本")   # 新增，可选
        parser.add_argument("--apikey", help="API Key")    # 可选
        parser.add_argument("--config", required=True, help="配置文件路径")
        args = parser.parse_args()

        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 多源关键词合并
        combined_keywords = []

        # JSON源处理
        if "json" in config["processing"]["keyword_sources"]:
            print(">>> 正在处理JSON源")
            json_keywords = extract_quoted_keywords(config)
            combined_keywords.extend(json_keywords)
            print(f"从JSON提取到 {len(json_keywords)} 个关键词")

        # 文本源处理
        if "txt" in config["processing"]["keyword_sources"]:
            print(">>> 正在处理文本源")
            txt_keywords = extract_txt_keywords(config)
            combined_keywords.extend(txt_keywords)
            print(f"从文本提取到 {len(txt_keywords)} 个关键词")
        # 保存关键词
        if combined_keywords:
            output_path = config["paths"]["keyword_list"]
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(list(combined_keywords), f, indent=2)
            print(f"[OK] 合并后关键词数量: {len(combined_keywords)}")
        # 段落重组
        reconstruct_paragraphs(config)

    except FileNotFoundError as e:
        print(f"关键文件缺失: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
    except Exception as e:
        print(f"未捕获错误: {str(e)}")


if __name__ == "__main__":
    main()