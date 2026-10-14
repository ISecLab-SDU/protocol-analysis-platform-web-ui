#!/usr/bin/env python3
"""Check or refresh the vendored progress package from a ProtocolGuard checkout."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=root.parent / "ProtocolGuard")
    parser.add_argument(
        "--write", action="store_true", help="Refresh files; default is a parity check"
    )
    args = parser.parse_args()
    canonical = args.source / "dynamic_verification/agent_progress"
    backend = root / "apps/backend-flask"
    sources = {
        backend / "pg_agent_progress" / path.name: path
        for path in (canonical / "src/pg_agent_progress").glob("*.py")
    }
    sources[backend / "tests/test_agent_progress_contract.py"] = (
        canonical / "tests/test_events.py"
    )
    if not (canonical / "pyproject.toml").is_file():
        parser.error("--source must point to the ProtocolGuard checkout")
    different = []
    for target, source in sources.items():
        content = source.read_bytes()
        if args.write:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        elif not target.exists() or target.read_bytes() != content:
            different.append(str(target.relative_to(root)))
    if different:
        print("Vendored progress files differ:\n" + "\n".join(different))
        return 1
    print("Agent progress package and contract tests are synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
