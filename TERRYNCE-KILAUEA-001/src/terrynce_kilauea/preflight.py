from __future__ import annotations

import json
from pathlib import Path

from .author_schema import probe_author_schema
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
    schema = None
    if mat.exists() and any(c["check"] == "md5:Kilauea_training_data.mat" and c["status"] == "PASS" for c in checks):
        inv = write_inventory(mat, artifacts, n_cycles=proto["split"]["n_cycles"])
        # A top-level axis of 39 is NOT required: the released archive uses
        # MATLAB cell arrays. Preserve the flat inventory as a receipt only.
        checks.append({
            "check": "top_level_39_axis",
            "status": "PASS",
            "detail": f"informational only: {len(inv['candidates']['cycle_axis'])} top-level variable(s) expose axis 39; author archive is cell-structured",
        })

        schema = probe_author_schema(mat, artifacts, n_cycles=proto["split"]["n_cycles"])
        checks.append({
            "check": "author_cell_schema_39_cycles",
            "status": "PASS" if schema["status"] == "PASS" else "FAIL",
            "detail": f"X cells={schema.get('x_cell_count', 0)}, Y cells={schema.get('y_cell_count', 0)}; expected cycle axes verified from released indexing",
        })
        channels_ok = bool(schema.get("channel_counts")) and all((n is not None and n >= 7) for n in schema.get("channel_counts", []))
        checks.append({
            "check": "author_channel_map_gps_tilt_seismicity",
            "status": "PASS" if channels_ok else "FAIL",
            "detail": "released training code maps channels 0-4=GPS, 5=tilt, 6=cumulative seismicity",
        })

    scripts = [root / "data" / "raw" / "train_GNN_models.py", root / "data" / "raw" / "make_result_figures.py"]
    scan = write_scan(scripts, artifacts / "author_code_scan.json")
    if "train_GNN_models.py" in scan:
        text = scripts[0].read_text(errors="replace")
        split_ok = "np.arange(29)" in text and "np.arange(29,39)" in text
        fixed_norm_ok = "norm_scale = np.array([80.0, 80.0, 80.0, 80.0, 80.0, 20.0, 300.0])" in text
        checks.append({"check": "author_code_exact_29_10_split", "status": "PASS" if split_ok else "FAIL"})
        checks.append({
            "check": "author_normalization_is_fixed_constant",
            "status": "PASS" if fixed_norm_ok else "REVIEW",
            "detail": "PASS means the released GNN input scale is a literal constant vector, not a statistic fitted on the 39 cycles.",
        })

    psha = protocol_sha256(root)
    (artifacts / "protocol_lock.json").write_text(json.dumps({"sha256": psha, "protocol": proto}, indent=2))

    hard_fail = any(c["status"] in {"FAIL", "BLOCKED"} for c in checks)
    reviews = [c for c in checks if c["status"] == "REVIEW"]
    report = {
        "experiment_id": proto["experiment_id"],
        "status": "BLOCKED" if hard_fail else ("PASS_WITH_REVIEW" if reviews else "PASS"),
        "protocol_sha256": psha,
        "checks": checks,
        "boundary": "No holdout forecast may be scored until this preflight is PASS and the frozen adapter/protocol receipt is committed. The probe may verify shapes and released indexing but must not export holdout values.",
    }
    (artifacts / "preflight_report.json").write_text(json.dumps(report, indent=2))
    return report
