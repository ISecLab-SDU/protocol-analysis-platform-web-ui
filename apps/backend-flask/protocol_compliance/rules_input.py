"""Validate the rules passed to the compiler and preserve protocol identity."""

from __future__ import annotations

import re
from typing import Any, cast

METADATA_KEYS = {
    "protocol",
    "protocolName",
    "protocolVersion",
    "protocol_version",
    "version",
    "title",
    "name",
    "summary",
    "description",
}


def canonical_protocol(value: str) -> str:
    key = value.strip().lower()
    aliases = {
        "mqtt": "MQTT",
        "ftp": "FTP",
        "coap": "CoAP",
        "dhcp": "DHCP",
        "dhcpv4": "DHCP",
        "dhcpv6": "DHCP",
        "tls1.3": "TLS1.3",
        "tls": "TLS1.3",
    }
    if key not in aliases:
        raise ValueError(
            f"Unsupported protocol {value!r}; expected MQTT, FTP, CoAP, DHCP or TLS1.3"
        )
    return aliases[key]


def rule_metadata(document: dict[str, Any]) -> tuple[str | None, str | None]:
    protocols: set[str] = set()
    versions: set[str] = set()
    for key in ("protocol", "protocolName"):
        value = document.get(key)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a string")
            if value.strip().lower() not in {"", "auto", "unknown"}:
                protocols.add(canonical_protocol(value))
                if value.strip().lower() in {"dhcpv4", "dhcpv6"}:
                    versions.add(value.strip()[-1])
    for key in ("protocolVersion", "protocol_version", "version"):
        value = document.get(key)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a string")
            if value.strip():
                versions.add(value.strip())
    groups = document.get("rules", document)
    if isinstance(groups, dict):
        for name in groups:
            match = re.fullmatch(
                r"(MQTT|FTP|CoAP|DHCP|TLS1\.3)(?:[-_ ]v?(\d+(?:\.\d+)*))?(?:[-_ ]rules)?",
                name,
                re.IGNORECASE,
            )
            if match:
                protocols.add(canonical_protocol(match[1]))
                if match[2]:
                    versions.add(match[2])
    if len(protocols) > 1 or len(versions) > 1:
        raise ValueError("Conflicting protocol or version metadata in rules JSON")
    return next(iter(protocols), None), next(iter(versions), None)


def validate_rules(document: object) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(document, dict):
        raise ValueError("Rules JSON root must be an object of rule arrays")
    document = cast(dict[str, Any], document)
    groups = document.get("rules", document)
    if isinstance(groups, list):
        groups = {"rules": groups}
    if not isinstance(groups, dict):
        raise ValueError("rules must be an object of rule arrays or an array")
    result: dict[str, list[dict[str, Any]]] = {}
    for group, entries in groups.items():
        if groups is document and group in METADATA_KEYS:
            continue
        if group == "UNKNOWN":
            raise ValueError(
                "UNKNOWN rules are skipped by the matcher; assign a concrete message category"
            )
        if not isinstance(entries, list):
            raise ValueError(f"{group}: expected an array of rules")
        for index, entry in enumerate(entries):
            location = f"{group}[{index}]"
            if not isinstance(entry, dict):
                raise ValueError(f"{location}: rule must be an object")
            entry = cast(dict[str, Any], entry)
            clean: dict[str, Any] = {}
            for key in ("rule", "req_type", "res_type"):
                value = entry.get(key)
                if not isinstance(value, str):
                    raise ValueError(f"{location}.{key}: required string")
                clean[key] = value.strip()
            for key in ("rule", "req_type"):
                if not clean[key]:
                    raise ValueError(
                        f"{location}.{key}: must not be empty; assign the rule's incoming message type"
                    )
            for key in ("req_fields", "res_fields"):
                value = entry.get(key)
                if not isinstance(value, list) or any(
                    not isinstance(field, str) or not field.strip() for field in value
                ):
                    raise ValueError(
                        f"{location}.{key}: required array of nonempty strings (use [] when absent)"
                    )
                clean[key] = [field.strip() for field in value]
            if clean["res_fields"] and not clean["res_type"]:
                raise ValueError(
                    f"{location}.res_fields: response fields require res_type"
                )
            result.setdefault(group, []).append(clean)
    if not result:
        raise ValueError("Rules JSON contains no analyzable rules")
    return result
