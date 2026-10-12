#!/usr/bin/env python3
"""Write or verify the tracked, deterministic daily-task fixture definitions."""
from __future__ import annotations

import argparse
from pathlib import Path

from daily_cases import build_cases, js

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "cases/daily")
    parser.add_argument("--check", action="store_true", help="Compare tracked fixtures without writing")
    args = parser.parse_args()
    cases = build_cases()
    if not args.check:
        args.output.mkdir(parents=True, exist_ok=True)
    changed = []
    for case_id, case in cases.items():
        path = args.output / f"{case_id}.json"
        content = js(case)
        if args.check:
            if not path.is_file() or path.read_text() != content:
                changed.append(case_id)
        else:
            path.write_text(content)
    if changed:
        parser.exit(1, f"Fixtures differ: {', '.join(changed)}. Regenerate with scripts/prepare_daily.py.\n")
    print(f"{'Verified' if args.check else 'Prepared'} {len(cases)} cases / {sum(len(c['variants']) for c in cases.values())} variants: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
