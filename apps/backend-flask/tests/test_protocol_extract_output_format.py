from __future__ import annotations

import sys
from pathlib import Path


RULE_PROCESS_ROOT = (
    Path(__file__).resolve().parents[1] / "protocol_extract" / "ruleProcess"
)
if str(RULE_PROCESS_ROOT) not in sys.path:
    sys.path.insert(0, str(RULE_PROCESS_ROOT))

from output_format import build_legacy_rules_payload  # noqa: E402


def test_build_legacy_rules_payload_groups_rules_and_keeps_scalar_types() -> None:
    payload = build_legacy_rules_payload(
        [
            {
                "rule": "STOR must replace an existing file.",
                "req_type": "STOR",
                "req_fields": ["command", "filename"],
                "res_type": "",
                "res_fields": [],
            },
            {
                "rule": "PASS can receive reply 332.",
                "req_type": ["PASS"],
                "req_fields": [],
                "res_type": ["332"],
                "res_fields": [],
            },
        ]
    )

    assert list(payload) == ["STOR", "PASS"]
    assert payload["STOR"][0]["req_type"] == "STOR"
    assert payload["STOR"][0]["res_type"] == ""
    assert payload["PASS"][0]["req_type"] == "PASS"
    assert payload["PASS"][0]["res_type"] == "332"


def test_build_legacy_rules_payload_splits_multiple_types_without_losing_them() -> None:
    payload = build_legacy_rules_payload(
        [
            {
                "rule": "Commands share reply behavior.",
                "req_type": ["APPE", "STOR"],
                "req_fields": [],
                "res_type": ["150", "250"],
                "res_fields": [],
            }
        ]
    )

    assert [(item["req_type"], item["res_type"]) for item in payload["APPE"]] == [
        ("APPE", "150"),
        ("APPE", "250"),
    ]
    assert [(item["req_type"], item["res_type"]) for item in payload["STOR"]] == [
        ("STOR", "150"),
        ("STOR", "250"),
    ]


def test_build_legacy_rules_payload_uses_response_or_default_group() -> None:
    payload = build_legacy_rules_payload(
        [
            {
                "rule": "The server sends 220.",
                "req_type": "",
                "req_fields": [],
                "res_type": "220",
                "res_fields": [],
            },
            {
                "rule": "The data connection closes immediately.",
                "req_type": "",
                "req_fields": [],
                "res_type": "",
                "res_fields": [],
            },
        ]
    )

    assert payload["220"][0]["res_type"] == "220"
    assert payload["DEFAULT"][0]["req_type"] == ""
    assert payload["DEFAULT"][0]["res_type"] == ""
