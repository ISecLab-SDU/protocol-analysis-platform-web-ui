from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[1] / "protocol_extract"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_specify_keyword_prompt_contains_current_document(tmp_path: Path) -> None:
    module = _load_module(
        "protocol_extract_specify_keywords",
        PIPELINE_ROOT / "documentProcess" / "specify_keywords.py",
    )
    markdown = tmp_path / "protocol.md"
    markdown.write_text("FTP TEST DOCUMENT SENTINEL", encoding="utf-8")

    prompt = module._build_prompt(
        {
            "protocol": "FTP",
            "version": "RFC 959",
            "paths": {"markdown": str(markdown)},
        }
    )

    assert "FTP TEST DOCUMENT SENTINEL" in prompt
    assert "VarBindList" not in prompt
    assert "coldStart" not in prompt


def test_text_keyword_extraction_does_not_preserve_json_quotes(tmp_path: Path) -> None:
    module = _load_module(
        "protocol_extract_keywords",
        PIPELINE_ROOT / "keywordProcess" / "keywords.py",
    )
    keywords = tmp_path / "specify_keywords.txt"
    keywords.write_text(
        '{"USER": {"username": {}, "password": {}}}',
        encoding="utf-8",
    )

    result = module.extract_txt_keywords({"paths": {"specify_keywords": str(keywords)}})

    assert result == ["USER", "username", "password"]
