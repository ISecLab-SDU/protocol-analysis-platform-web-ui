"""Static-analysis payload normalization and classification helpers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

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

PROTOCOL_ALIASES = {
    "coap": "CoAP",
    "dhcp": "DHCPv6",
    "dhcpv6": "DHCPv6",
    "ftp": "FTP",
    "mqtt": "MQTT",
    "mqttv3": "MQTT",
    "mqttv5": "MQTT",
    "snmp": "SNMP",
    "ssl": "TLS",
    "tls": "TLS",
    "tlsv1.3": "TLS",
}

RULE_RESULT_PRIORITY = {
    "unknown": 0,
    "no_violation": 1,
    "violation_found": 2,
}


def _parse_llm_response(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, str):
        payload = payload.strip()
        if not payload or payload.lower() == "null":
            return {}
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return {"raw": payload}
        payload = decoded
    if isinstance(payload, dict):
        return payload
    return {}


def _has_structured_violation_payload(llm_payload: Dict[str, Any]) -> bool:
    violations = llm_payload.get("violations")
    if not isinstance(violations, list):
        return False
    return any(isinstance(item, dict) for item in violations)


def _classify_rule_result(llm_payload: Dict[str, Any]) -> tuple[str, str]:
    if _has_structured_violation_payload(llm_payload):
        return "violation_found", "发现违规"

    result_text = str(llm_payload.get("result") or "").lower()
    normalized_result = re.sub(r"[\s_-]+", " ", result_text)
    if "no violation" in normalized_result:
        return "no_violation", "未发现违规"
    if "violation" in normalized_result:
        return "violation_found", "发现违规"
    return "unknown", "未判定"


def _llm_payload_history_time(llm_payload: Dict[str, Any]) -> Optional[str]:
    for key in ("updated_at", "updatedAt", "created_at", "createdAt"):
        value = llm_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize_implementation_from_db(path: Path) -> str:
    name = path.stem
    return name[7:] if name.startswith("sqlite_") else name


def _protocol_for_implementation(implementation_name: str) -> str:
    return PROTOCOL_BY_IMPLEMENTATION.get(implementation_name.lower(), "Other")


def _normalize_protocol_name(
    protocol_name: Optional[str],
    implementation_name: str,
) -> str:
    if isinstance(protocol_name, str) and protocol_name.strip():
        key = re.sub(r"[\s_-]+", "", protocol_name.strip().lower())
        for prefix, normalized in PROTOCOL_ALIASES.items():
            if key.startswith(prefix.replace(".", "")):
                return normalized
    return _protocol_for_implementation(implementation_name)


def _dedupe_key(value: Any) -> str:
    return " ".join(str(value or "").split()).lower()


def _merge_rule_status(
    status_by_rule: Dict[str, str],
    rule_key: str,
    result_status: str,
) -> None:
    current = status_by_rule.get(rule_key)
    if current is None or (
        RULE_RESULT_PRIORITY.get(result_status, 0)
        > RULE_RESULT_PRIORITY.get(current, 0)
    ):
        status_by_rule[rule_key] = result_status


def _violation_location_key(rule_key: str, violation: Dict[str, Any]) -> str:
    code_lines = violation.get("codeLines")
    if isinstance(code_lines, list):
        lines = ",".join(str(item) for item in code_lines)
    else:
        lines = ""
    return "|".join(
        [
            rule_key,
            _dedupe_key(violation.get("filename")),
            _dedupe_key(violation.get("functionName")),
            lines,
        ]
    )


def _parse_violation_details(payload: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    violations_payload = payload.get("violations")
    if not isinstance(violations_payload, list):
        return None

    violations: List[Dict[str, Any]] = []
    for entry in violations_payload:
        if not isinstance(entry, dict):
            continue
        code_lines = entry.get("code_lines") or entry.get("codeLines")
        if isinstance(code_lines, list):
            lines = []
            for item in code_lines:
                try:
                    lines.append(int(item))
                except (TypeError, ValueError):
                    continue
            code_lines = lines or None
        else:
            code_lines = None
        violations.append(
            {
                "filename": entry.get("filename"),
                "functionName": entry.get("function_name") or entry.get("functionName"),
                "codeLines": code_lines,
            }
        )
    return violations or None


def _strip_archive_suffix(filename: str) -> str:
    normalized = filename.strip()
    for suffix in (".tar.gz", ".tar.bz2", ".tar.xz", ".zip", ".tgz", ".tbz2", ".txz"):
        if normalized.lower().endswith(suffix):
            return normalized[: -len(suffix)]
    return Path(normalized).stem or normalized


def _get_static_analysis_verdicts(result: Any) -> List[Dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    model_response = result.get("modelResponse")
    if not isinstance(model_response, dict):
        return []
    verdicts = model_response.get("verdicts")
    if not isinstance(verdicts, list):
        return []
    return [item for item in verdicts if isinstance(item, dict)]


def _analysis_result_inputs(result: Any) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    inputs = result.get("inputs")
    return inputs if isinstance(inputs, dict) else {}


def _analysis_result_artifacts(result: Any) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    artifacts = result.get("artifacts")
    return artifacts if isinstance(artifacts, dict) else {}


def _normalize_implementation_from_analysis_result(
    entry: Dict[str, Any],
    result: Dict[str, Any],
) -> str:
    inputs = _analysis_result_inputs(result)
    raw_name = (
        inputs.get("codeFileName")
        or entry.get("codeFileName")
        or entry.get("databasePath")
        or entry.get("jobId")
        or "analysis-result"
    )
    name = Path(str(raw_name)).name
    return _strip_archive_suffix(name)


def _analysis_result_database_path(
    entry: Dict[str, Any],
    result: Dict[str, Any],
) -> Optional[str]:
    artifacts = _analysis_result_artifacts(result)
    raw_path = artifacts.get("database") or entry.get("databasePath")
    return str(raw_path) if raw_path else None


def _analysis_result_database_name(
    entry: Dict[str, Any],
    result: Dict[str, Any],
) -> str:
    database_path = _analysis_result_database_path(entry, result)
    if database_path:
        return Path(database_path).name
    return "code-locate-consistency"


def _verdict_result_status(verdict: Dict[str, Any]) -> tuple[str, str]:
    compliance = str(verdict.get("compliance") or "").lower()
    if compliance == "non_compliant":
        return "violation_found", "发现违规"
    if compliance == "compliant":
        return "no_violation", "未发现违规"
    return "unknown", "未判定"


def _verdict_rule_desc(verdict: Dict[str, Any]) -> str:
    related_rule = verdict.get("relatedRule")
    if isinstance(related_rule, dict):
        requirement = related_rule.get("requirement")
        if isinstance(requirement, str) and requirement.strip():
            return requirement.strip()
        rule_id = related_rule.get("id")
        if isinstance(rule_id, str) and rule_id.strip():
            return rule_id.strip()
    category = verdict.get("category")
    if isinstance(category, str) and category.strip():
        return category.strip()
    return "未命名规则"


def _verdict_code_lines(verdict: Dict[str, Any]) -> Optional[List[int]]:
    line_range = verdict.get("lineRange")
    if not isinstance(line_range, list) or len(line_range) < 2:
        return None
    try:
        start = int(line_range[0])
        end = int(line_range[1])
    except (TypeError, ValueError):
        return None
    if start <= 0 or end <= 0:
        return None
    if end < start:
        start, end = end, start
    return list(range(start, min(end, start + 199) + 1))


def _verdict_violation_details(
    verdict: Dict[str, Any],
) -> Optional[List[Dict[str, Any]]]:
    location = verdict.get("location")
    location = location if isinstance(location, dict) else {}
    filename = location.get("file")
    function_name = location.get("function")
    code_lines = _verdict_code_lines(verdict)
    if not filename and not function_name and not code_lines:
        return None
    return [
        {
            "filename": filename,
            "functionName": function_name,
            "codeLines": code_lines,
        }
    ]


def _build_analysis_result_history_item_id(
    *,
    entry: Dict[str, Any],
    verdict: Dict[str, Any],
    row_index: int,
) -> str:
    related_rule = verdict.get("relatedRule")
    rule_id = related_rule.get("id") if isinstance(related_rule, dict) else None
    stable_key = "|".join(
        [
            "analysis-result",
            str(entry.get("jobId") or ""),
            str(entry.get("updatedAt") or entry.get("createdAt") or ""),
            str(rule_id or ""),
            _verdict_rule_desc(verdict),
            str(row_index),
        ]
    )
    return hashlib.sha1(stable_key.encode("utf-8")).hexdigest()
