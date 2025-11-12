from openai import OpenAI
import toml
from pathlib import Path
import httpx

# 获取当前脚本所在目录
script_dir = Path(__file__).parent.parent
config_path = script_dir / "config.toml"
prompt_path = script_dir / "prompt.toml"
toml_config = toml.load(config_path)
toml_prompt = toml.load(prompt_path)
PROMPT_TEMPLATE = toml_prompt["prompt_specify_keywords"]["user"]
this_url = toml_config["llm"]["base_url"]
this_model = toml_config["llm"]["model2"]

def process_keywords(config):
    http_client = httpx.Client(proxies=None)  # 强制禁用所有代理
    client = OpenAI(api_key=config["api_key"], base_url=this_url, http_client=http_client)

    prompt = PROMPT_TEMPLATE.format(protocol=config["protocol"],version=config["version"])

    try:
        response = client.chat.completions.create(
            # 指定使用的模型为deepseek-chat
            model=this_model,
            # 定义对话消息列表
            messages=[
                {"role": "user", "content": prompt},
            ],
            # 设置非流式响应（等待完整响应返回）
            stream=False,
            response_format={
            'type': 'json_object'
            }
        )
        keywords = response.choices[0].message.content
        with open(config["paths"]["keywords"], "w", encoding="utf-8") as f:
            f.write(keywords)
        print("✅ Keywords extracted")
    except Exception as e:
        print(f"❌ Keyword extraction failed: {str(e)}")
