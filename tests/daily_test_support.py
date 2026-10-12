"""Reference artifacts for harness tests, never supplied to the real agent."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

from daily_checks import expand


def reference_artifacts(case, variant, root, base_url="http://fixture.invalid", *, inputs=True, snapshots=None):
    root = Path(root)
    data = expand(case["variants"][variant], base_url)
    if inputs:
        for name, content in data["files"].items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    for spec in data["checks"]:
        if spec["kind"] == "retrieval":
            continue
        target = root / spec["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if spec["kind"] == "json":
            target.write_text(json.dumps(spec["expected"]))
        elif spec["kind"] == "text":
            target.write_text("Reference artifact for an automated harness self-test. " * 8 + "\n" + "\n".join(spec.get("contains", [])))
        elif spec["kind"] in {"meals", "itinerary"}:
            target.write_text(json.dumps(data["reference_output"]))
        elif spec["kind"] == "organize":
            moves = []
            for i, original in enumerate(spec["rules"]["original_sha256"]):
                destination = "organized/" + spec["rules"]["categories"][original] + f"/file-{i}.txt"
                (root / destination).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(root / original), root / destination)
                moves.append({"from": original, "to": destination})
            target.write_text(json.dumps({"moves": moves}))
        if spec.get("phase") and snapshots:
            saved = Path(snapshots) / f"phase-{spec['phase']:02d}" / spec["path"]
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(target, saved)
    if inputs:
        for p in data["phases"]:
            for name in p["remove_before"]:
                (root / name).unlink(missing_ok=True)
    requests = [{"path": path, "status": status} for spec in data["checks"] if spec["kind"] == "retrieval"
                for path, status in spec["required"].items()]
    return requests
