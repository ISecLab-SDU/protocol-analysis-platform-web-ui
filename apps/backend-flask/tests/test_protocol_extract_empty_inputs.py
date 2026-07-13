from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = BACKEND_ROOT / "protocol_extract"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


text_process = _load_module(
    "protocol_extract_text_process",
    PIPELINE_ROOT / "documentProcess" / "text_process.py",
)
index_filtering = _load_module(
    "protocol_extract_index_filtering",
    PIPELINE_ROOT / "documentProcess" / "index_filtering.py",
)
third_rule = _load_module(
    "protocol_extract_third_rule",
    PIPELINE_ROOT / "ruleProcess" / "third_rule.py",
)
second_rule = _load_module(
    "protocol_extract_second_rule",
    PIPELINE_ROOT / "ruleProcess" / "second_rule.py",
)


def test_indented_markdown_headings_are_extracted_and_filtered(tmp_path: Path) -> None:
    markdown_path = tmp_path / "protocol.md"
    markdown_path.write_text(
        "    ## [1](https://example.test/section-1). INTRODUCTION\n\n"
        "    First section content.\n\n"
        "## [2](https://example.test/section-2). COMMANDS\n\n"
        "Second section content.\n",
        encoding="utf-8",
    )

    headings = text_process.extract_markdown_hierarchy(markdown_path)
    filtered = text_process.filter_headings_content(headings)

    assert list(filtered) == ["1. INTRODUCTION", "2. COMMANDS"]
    assert filtered["1. INTRODUCTION"] == "First section content."


def test_heading_selection_restores_omitted_section_numbers() -> None:
    headings = {
        "1.  INTRODUCTION": "Introduction",
        "2.  OVERVIEW": "Overview",
        "3. DATA TRANSFER FUNCTIONS": "Data transfer",
    }

    selected = index_filtering._resolve_selected_headings(
        ["OVERVIEW", "DATA TRANSFER FUNCTIONS"],
        headings,
    )

    assert selected == ["2.  OVERVIEW", "3. DATA TRANSFER FUNCTIONS"]


def test_heading_selection_parses_fenced_json_response() -> None:
    selected = index_filtering._parse_selected_headings(
        '```json\n["1. INTRODUCTION", "2. COMMANDS"]\n```'
    )

    assert selected == ["1. INTRODUCTION", "2. COMMANDS"]


def test_heading_selection_rejects_non_string_items() -> None:
    try:
        index_filtering._parse_selected_headings('["1. INTRODUCTION", 2]')
    except ValueError as exc:
        assert str(exc) == "Heading selection response must be a list of strings"
    else:
        raise AssertionError("Expected a non-string heading to be rejected")


def test_third_rule_accepts_an_empty_stage_two_workbook(tmp_path: Path) -> None:
    excel_path = tmp_path / "filtered_sentences.xlsx"
    processed_path = tmp_path / "processed_results.json"
    pd.DataFrame(columns=["Heading", "Sentence", "Is_Matched"]).to_excel(
        excel_path,
        index=False,
        engine="openpyxl",
    )

    third_rule.run_third_rule(
        api_key="unused",
        protocol="FTP",
        version="5",
        config={
            "paths": {
                "excel_sentences": str(excel_path),
                "processed": str(processed_path),
            }
        },
    )

    assert json.loads(processed_path.read_text(encoding="utf-8")) == []


def test_second_rule_writes_result_schema_when_no_sentences_match(
    tmp_path: Path,
) -> None:
    excel_path = tmp_path / "filtered_sentences.xlsx"
    table_path = tmp_path / "tables.md"
    processed_path = tmp_path / "processed_results.json"
    pd.DataFrame(
        [
            {
                "Heading": "FTP COMMANDS",
                "Sentence": "The server listens on the control connection.",
                "Is_Matched": False,
            }
        ]
    ).to_excel(excel_path, index=False, engine="openpyxl")

    second_rule.run_second_rule(
        api_key="unused",
        protocol="FTP",
        version="5",
        config={
            "paths": {
                "excel_sentences": str(excel_path),
                "processed": str(processed_path),
                "table": str(table_path),
            }
        },
    )

    result = pd.read_excel(excel_path, engine="openpyxl")
    assert result["Second_Filter_Result"].tolist() == ["Not evaluated"]
    prompts_path = tmp_path / "generated_prompts_with_results.json"
    assert json.loads(prompts_path.read_text(encoding="utf-8")) == []

    third_rule.run_third_rule(
        api_key="unused",
        protocol="FTP",
        version="5",
        config={
            "paths": {
                "excel_sentences": str(excel_path),
                "processed": str(processed_path),
            }
        },
    )
    assert json.loads(processed_path.read_text(encoding="utf-8")) == []
