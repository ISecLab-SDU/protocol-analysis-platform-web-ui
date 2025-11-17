import re
import json
from openai import OpenAI
from collections import defaultdict
import os


def filter_headings(config):
    print("🔄 Filtering protocol headings...")
    with open(config["paths"]["text_processed"], "r") as f:
        headings = json.load(f)

    # 分组章节
    grouped = defaultdict(list)
    pattern = re.compile(r"^(\d+)[\.\s]")
    for heading in headings:
        match = pattern.match(heading)
        if match:
            grouped[match.group(1)].append(heading)

    # 生成提示词
    headings_str = "\n".join(h for sub in grouped.values() for h in sub)
    with open(config["paths"]["keywords"], "r") as f:
        keywords = f.read()

    prompt = f"""
给定以下{config['protocol']} {config['version']}协议文档的目录，请预测哪些章节下的内容可能包含关于{config['protocol']} {config['version']}消息报文及各个字段的描述。请依据以下标准进行筛选：

1. **消息类型和控制**：若此条目包含关于{config['protocol']} {config['version']}的具体消息报文名称，则此条目是我们所需要的条目,将其筛选出来,{config['protocol']} {config['version']}具体报文名称可以参考如下提供的具体信息。
2. **字段信息**：若此条目包含关于{config['protocol']} {config['version']}的具体消息报文内部各个字段信息的名称，则此条目是我们所需要的条目,将其筛选出来,{config['protocol']} {config['version']}具体报文内部字段信息可以参考如下提供的具体信息。
3. **协议行为影响字段**：若预测此条目下的内容描述了会话管理、消息流转、QoS 机制、订阅管理、流控、错误处理等协议行为，且这些行为可能影响{config['protocol']} {config['version']}消息的字段，则此条目也是我们需要的条目,也需要将其筛选出来。 

以下是关于{config['protocol']} {config['version']}的具体消息类型和消息内部的字段：
{keywords}

这是你要进行筛选的章节目录：
{headings_str}

输出格式：
请最终输出一个 Python 列表，每个列表元素为经过筛选后认为是我们需要的条目，不要输出其他任何多余的内容，如分析过程、解释信息等，输出格式如下：
["条目1","条目2",...]

注意：
(1)在一个大章节出现了符合规定的条目，那么这些条目的平行章节最好要慎重筛选，除非是特别明显不符合我们的要求的，和我们的要求只要有一点关系，那么都要将这个条目加进来。
(2)如果一个条目符合规定，那么它的子条目也需要加入列表。
"""

    # 调用AI筛选
    client = OpenAI(api_key=config["api_key"], base_url="https://api.deepseek.com/v1")
    #print(prompt)
    try:
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": "你是一位协议文档分析专家"},
                {"role": "user", "content": prompt}
            ]
        )
        selected = eval(response.choices[0].message.content)
        with open(config["paths"]["headings"], "w") as f:
            json.dump(selected, f)
        print(f"✅ Selected {len(selected)} headings")
    except Exception as e:
        print(f"❌ Heading selection failed: {str(e)}")