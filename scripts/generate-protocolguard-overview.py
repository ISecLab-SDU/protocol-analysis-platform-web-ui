#!/usr/bin/env python3
"""Generate ProtocolGuard overview statistics from database/*.db files."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
DATABASE_DIR = ROOT_DIR / "database"
OUTPUT_PATH = ROOT_DIR / "apps/web-antd/public/protocolguard-overview.json"

PROTOCOL_BY_IMPLEMENTATION = {
    "freecoap": "CoAP",
    "libcoap": "CoAP",
    "dhcp": "DHCPv6",
    "dnsmasq": "DHCPv6",
    "ndhs": "DHCPv6",
    "mosquitto": "MQTT",
    "sol": "MQTT",
    "tinymqtt": "MQTT",
    "pure-ftpd": "FTP",
    "uftpd": "FTP",
    "tlse": "TLS",
    "wolfssl": "TLS",
}

EXCLUDED_IMPLEMENTATIONS = {"dhcp"}


def normalize_implementation(path: Path) -> str:
    name = path.stem
    return name[7:] if name.startswith("sqlite_") else name


def parse_llm_response(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", "ignore")
    if isinstance(payload, str):
        text = payload.strip()
        if not text or text.lower() == "null":
            return {}
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}
        return decoded if isinstance(decoded, dict) else {}
    return payload if isinstance(payload, dict) else {}


def classify_rule_result(payload: dict[str, Any]) -> str:
    result_text = str(payload.get("result") or "").lower()
    if "violation" in result_text and "no violation" not in result_text:
        return "violation_found"
    if "no violation" in result_text:
        return "no_violation"
    return "unknown"


def truncate(value: Any, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[:limit - 1]}…"


def count_rows(connection: sqlite3.Connection, table: str) -> int:
    quoted = '"' + table.replace('"', '""') + '"'
    return int(connection.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0])


def build_stats() -> dict[str, Any]:
    if not DATABASE_DIR.is_dir():
        raise FileNotFoundError(f"Database directory not found: {DATABASE_DIR}")

    database_files = sorted(DATABASE_DIR.glob("sqlite_*.db"))
    summary = defaultdict(int)
    table_totals = defaultdict(int)
    protocol_totals: dict[str, defaultdict[str, int]] = {}
    implementations: list[dict[str, Any]] = []
    top_findings: list[dict[str, Any]] = []

    for db_path in database_files:
        implementation = normalize_implementation(db_path)
        if implementation.lower() in EXCLUDED_IMPLEMENTATIONS:
            continue

        protocol = PROTOCOL_BY_IMPLEMENTATION.get(implementation.lower(), "Other")
        protocol_bucket = protocol_totals.setdefault(protocol, defaultdict(int))

        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        tables = [
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        ]

        table_counts = {table: count_rows(connection, table) for table in tables}
        for table, count in table_counts.items():
            table_totals[table] += count

        if "rule_code_snippet" in tables:
            rule_rows = connection.execute(
                "SELECT rule_desc, code_snippet, llm_response FROM rule_code_snippet"
            ).fetchall()
        else:
            rule_rows = []

        result_counts = defaultdict(int)
        violation_locations = 0
        code_snippets = 0

        for row in rule_rows:
            llm_payload = parse_llm_response(row["llm_response"])
            result = classify_rule_result(llm_payload)
            result_counts[result] += 1

            if row["code_snippet"]:
                code_snippets += 1

            violations = llm_payload.get("violations")
            if isinstance(violations, list):
                violation_locations += len(violations)

            if result == "violation_found":
                top_findings.append(
                    {
                        "implementation": implementation,
                        "protocol": protocol,
                        "rule": truncate(row["rule_desc"], 160),
                        "reason": truncate(llm_payload.get("reason"), 220),
                    }
                )

        analysis_records = sum(table_counts.values())
        item = {
            "name": implementation,
            "protocol": protocol,
            "database": db_path.name,
            "analysisRecords": analysis_records,
            "ruleResults": len(rule_rows),
            "violationRules": result_counts["violation_found"],
            "noViolationRules": result_counts["no_violation"],
            "unknownRules": result_counts["unknown"],
            "violationLocations": violation_locations,
            "codeSnippets": code_snippets,
        }
        implementations.append(item)

        for key in (
            "analysisRecords",
            "ruleResults",
            "violationRules",
            "noViolationRules",
            "unknownRules",
            "violationLocations",
            "codeSnippets",
        ):
            summary[key] += item[key]
            protocol_bucket[key] += item[key]
        protocol_bucket["implementations"] += 1

        connection.close()

    implementations.sort(key=lambda item: item["violationRules"], reverse=True)
    top_findings = sorted(
        top_findings,
        key=lambda item: (
            item["protocol"],
            item["implementation"].lower(),
            item["rule"] or "",
        ),
    )[:6]

    protocols = [
        {
            "name": name,
            **dict(values),
        }
        for name, values in sorted(protocol_totals.items())
    ]

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceDirectory": "database",
        "summary": {
            "databaseFiles": len(implementations),
            "implementations": len(implementations),
            **dict(summary),
        },
        "tableTotals": dict(sorted(table_totals.items())),
        "protocols": protocols,
        "implementations": implementations,
        "topFindings": top_findings,
    }


def main() -> None:
    stats = build_stats()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
