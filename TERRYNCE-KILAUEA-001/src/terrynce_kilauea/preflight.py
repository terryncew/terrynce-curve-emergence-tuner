from __future__ import annotations

import json
from pathlib import Path

from .code_scan import write_scan
from .hashing import digest
from .mat_inventory import write_inventory
from .protocol import load_protocol, protocol_sha256, repo_root


def run_preflight(root: Path | None = None) -> dict:
    root = root or repo_root()
    proto = load_protocol(root)
    artifacts = root / "artifacts"
    artifacts.mkdir(exist_ok=True)
    lock = json.loads((root / "config" / "sources.lock.json").read_text())

    checks = []
    for spec in lock["dataset_record"]["files"]:
        path = root / "data" / "raw" / spec["name"]
        if not path.exists():
            checks.append({"check": f"present:{spec['name']}", "status": "BLOCKED", "detail": "missing; run tk001 acquire"})
            continue
        actual = digest(path, "md5")
        status = "PASS" if actual.lower() == spec["md5"].lower() else "FAIL"
        checks.append({"check": f"md5:{spec['name']}", "status": status, "expected": spec["md5"], "actual": actual})

    mat = root / "data" / "raw" / "Kilauea_training_data.mat"
    inv = None
    if mat.exists() and any(c["check"] == "md5:Kilauea_training_data.mat" and c["status"] == "PASS" for c in checks):
        inv = write_inventory(mat, artifacts, n_cycles=proto["split"]["n_cycles"])
        cycle_candidates = inv["candidates"]["cycle_axis"]
        checks.append({
            "check": "plausible_39_cycle_axis",
            "status": "PASS" if cycle_candidates else "BLOCKED",
            "detail": f"{len(cycle_candidates)} variable(s) contain an axis of length 39",
        })
        for key in ("gps", "tilt", "time", "duration"):
            checks.append({
                "check": f"schema_candidate:{key}",
                "status": "PASS" if inv["candidates"].get(key) else "REVIEW",
                "detail": f"{len(inv['candidates'].get(key, []))} name-matched candidate(s)",
            })

    scripts = [root / "data" / "raw" / "train_GNN_models.py", root / "data" / "raw" / "make_result_figures.py"]
    scan = write_scan(scripts, artifacts / "author_code_scan.json")
    if "train_GNN_models.py" in scan:
        hits = scan["train_GNN_models.py"]["pattern_hits"]
        checks.append({"check": "author_code_mentions_29_split", "status": "PASS" if hits["split_29"] else "REVIEW"})
        checks.append({"check": "author_code_normalization_review", "status": "REVIEW" if hits["normalization_words"] else "PASS", "detail": "REVIEW means inspect whether any statistic is fit before the split; it is not an accusation of leakage."})

    psha = protocol_sha256(root)
    (artifacts / "protocol_lock.json").write_text(json.dumps({"sha256": psha, "protocol": proto}, indent=2))

    hard_fail = any(c["status"] in {"FAIL", "BLOCKED"} for c in checks)
    report = {
        "experiment_id": proto["experiment_id"],
        "status": "BLOCKED" if hard_fail else "PASS_WITH_REVIEW",
        "protocol_sha256": psha,
        "checks": checks,
        "boundary": "No holdout forecast may be scored until schema mapping and any REVIEW items are resolved and the resulting adapter/config are hashed into a new protocol receipt.",
    }
    (artifacts / "preflight_report.json").write_text(json.dumps(report, indent=2))
    return report
