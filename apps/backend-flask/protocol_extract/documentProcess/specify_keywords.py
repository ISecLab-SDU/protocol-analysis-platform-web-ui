import json
import os
from pathlib import Path

import toml
from openai import OpenAI

# 获取当前脚本所在目录
script_dir = Path(__file__).parent.parent
config_path = script_dir / "config.toml"
prompt_path = script_dir / "prompt.toml"
toml_config = toml.load(config_path)
toml_prompt = toml.load(prompt_path)
PROMPT_TEMPLATE = toml_prompt["prompt_specify_keywords"]["user"]
this_url = (
    os.environ.get("PROTOCOL_EXTRACT_LLM_BASE_URL")
    or os.environ.get("OPENAI_BASE_URL")
    or toml_config["llm"]["base_url"]
)
this_model = toml_config["llm"]["model2"]


def _build_prompt(config):
    markdown_path = Path(config["paths"]["markdown"])
    document = markdown_path.read_text(encoding="utf-8").strip()
    if not document:
        raise ValueError(f"Protocol document is empty: {markdown_path}")
    return PROMPT_TEMPLATE.format(
        protocol=config["protocol"],
        version=config["version"],
        document=document,
    )


def process_keywords(config):
    client = OpenAI(api_key=config["api_key"], base_url=this_url)

    try:
        prompt = _build_prompt(config)
        response = client.chat.completions.create(
            model=this_model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            response_format={"type": "json_object"},
        )
        keywords = response.choices[0].message.content
        if keywords is None:
            raise ValueError("Empty keyword extraction response")
        payload = json.loads(keywords)
        if not isinstance(payload, dict) or not payload:
            raise ValueError(
                "Keyword extraction response must be a non-empty JSON object"
            )
        Path(config["paths"]["keywords"]).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("✅ Keywords extracted")
    except Exception as e:
        print(f"❌ Keyword extraction failed: {str(e)}")
        raise
