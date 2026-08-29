#!/usr/bin/env python3
"""Reproduce the public-data feasibility receipt for TERRYNCE-GLACIER-001."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import statistics
import sys
import tempfile
import urllib.request
import zipfile
from datetime import date, datetime
from pathlib import Path, PurePosixPath


HERE = Path(__file__).resolve().parent
REQUIRED_COLUMNS = (
    "X",
    "Y",
    "dx",
    "dy",
    "length",
    "direction",
    "max_corrcoeff",
    "avg_corrcoeff",
)
PATTERNS = {
    "east": re.compile(r"^east_disp/(\d{8})_(\d{8})_disp\.txt$"),
    "west": re.compile(r"^west_disp/(\d{8})_(\d{8})_west_disp\.txt$"),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def md5_file(path: Path) -> str:
    digest = hashlib.md5()  # nosec: source identity, not a security primitive
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "terrynce-glacier-001/1"})
    with urllib.request.urlopen(request, timeout=60) as response:  # nosec: pinned hash follows
        destination.write_bytes(response.read())


def ensure_safe_members(names: list[str]) -> None:
    for name in names:
        member = PurePosixPath(name)
        if member.is_absolute() or ".." in member.parts:
            raise ValueError(f"unsafe ZIP member: {name}")


def parse_date(raw: str) -> date:
    return datetime.strptime(raw, "%Y%m%d").date()


def read_displacement_file(raw: bytes, member: str) -> tuple[tuple[str, ...], int]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text), skipinitialspace=True)
    columns = tuple((field or "").strip() for field in (reader.fieldnames or ()))
    if columns != REQUIRED_COLUMNS:
        raise ValueError(f"unexpected columns in {member}: {columns}")
    count = 0
    for row in reader:
        for column in REQUIRED_COLUMNS:
            float(row[column])
        count += 1
    if count == 0:
        raise ValueError(f"empty displacement file: {member}")
    return columns, count


def density_gate(acquisitions: list[date], minimum: int, multiplier: float) -> dict:
    if len(acquisitions) < minimum:
        return {
            "acquisitions_in_window": len(acquisitions),
            "maximum_gap_days": None,
            "median_gap_days": None,
            "passed": False,
            "reason": "TOO_FEW_ACQUISITIONS",
            "window_rule": f"latest_{minimum}_acquisitions",
        }
    window = acquisitions[-minimum:]
    gaps = [(right - left).days for left, right in zip(window, window[1:])]
    median_gap = float(statistics.median(gaps))
    maximum_gap = max(gaps)
    passed = all(gap < multiplier * median_gap for gap in gaps)
    return {
        "acquisitions_in_window": len(window),
        "maximum_gap_days": maximum_gap,
        "median_gap_days": median_gap,
        "passed": passed,
        "reason": "PASS" if passed else "GAP_LIMIT_EXCEEDED",
        "window_rule": f"latest_{minimum}_acquisitions",
    }


def inspect_archive(archive: Path, expected_md5: str, prereg: dict, sources: dict) -> dict:
    observed_md5 = md5_file(archive)
    if observed_md5 != expected_md5:
        raise ValueError(f"source MD5 mismatch: expected {expected_md5}, got {observed_md5}")

    sides: dict[str, dict] = {}
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        ensure_safe_members(names)
        for side, pattern in PATTERNS.items():
            acquisitions: set[date] = set()
            intervals: list[dict] = []
            total_rows = 0
            columns_seen: set[tuple[str, ...]] = set()
            for name in names:
                match = pattern.match(name)
                if not match:
                    continue
                start, end = map(parse_date, match.groups())
                if end <= start:
                    raise ValueError(f"non-positive interval: {name}")
                columns, rows = read_displacement_file(bundle.read(name), name)
                columns_seen.add(columns)
                total_rows += rows
                acquisitions.update((start, end))
                intervals.append(
                    {
                        "days": (end - start).days,
                        "end": end.isoformat(),
                        "member": name,
                        "rows": rows,
                        "start": start.isoformat(),
                    }
                )
            if not intervals:
                raise ValueError(f"no {side} displacement files")
            ordered = sorted(acquisitions)
            gate = density_gate(
                ordered,
                prereg["critical_slowing_down"]["minimum_acquisitions"],
                prereg["critical_slowing_down"]["maximum_gap_multiplier_of_median"],
            )
            sides[side] = {
                "acquisition_count": len(ordered),
                "acquisitions": [item.isoformat() for item in ordered],
                "columns": list(next(iter(columns_seen))),
                "csd_final_prefix_sampling_gate": gate,
                "first_acquisition": ordered[0].isoformat(),
                "interval_file_count": len(intervals),
                "last_acquisition": ordered[-1].isoformat(),
                "total_vector_rows": total_rows,
            }

    failure_at = datetime.fromisoformat(
        sources["paper_reported_facts_used_by_gate"]["detachment_time_utc_approx"].replace("Z", "+00:00")
    )
    east_last = date.fromisoformat(sides["east"]["last_acquisition"])
    west_first = date.fromisoformat(sides["west"]["first_acquisition"])
    west_last = date.fromisoformat(sides["west"]["last_acquisition"])
    control_years = (west_last - west_first).days / 365.2425
    expected_final_dates = {
        item[key]
        for item in sources["paper_reported_facts_used_by_gate"]["east_final_intervals"]
        for key in ("start", "end")
    }
    east_dates = set(sides["east"]["acquisitions"])
    missing_final_dates = sorted(expected_final_dates - east_dates)

    archive_columns = set(sides["east"]["columns"])
    semantic_fields = {
        "position_m_along_flowline",
        "terminus_position_m",
        "zone",
    }
    semantic_labels_present = semantic_fields.issubset(archive_columns)

    gates = {
        "control_exposure": control_years >= prereg["calibration"]["minimum_control_exposure_glacier_years"],
        "csd_east_final_prefix": sides["east"]["csd_final_prefix_sampling_gate"]["passed"],
        "final_warning_window": not missing_final_dates,
        "frozen_spatial_roles": semantic_labels_present,
        "source_identity": True,
    }
    reason_codes = []
    if not gates["final_warning_window"]:
        reason_codes.append("FINAL_WARNING_WINDOW_ABSENT")
    if not gates["frozen_spatial_roles"]:
        reason_codes.append("FROZEN_SPATIAL_ROLE_METADATA_ABSENT")
    if not gates["control_exposure"]:
        reason_codes.append("CONTROL_EXPOSURE_BELOW_FIVE_GLACIER_YEARS")
    if not gates["csd_east_final_prefix"]:
        reason_codes.append("CSD_SAMPLING_GATE_FAILED")

    ready = all(gates.values())
    return {
        "claim_status": "UNTESTED",
        "experiment_id": prereg["experiment_id"],
        "feasibility_gates": gates,
        "headline_test_ready": ready,
        "observations": {
            "control_exposure_glacier_years_from_open_archive": round(control_years, 6),
            "east_days_from_last_open_acquisition_to_failure": (failure_at.date() - east_last).days,
            "east_missing_paper_reported_final_dates": missing_final_dates,
            "semantic_role_fields_present": semantic_labels_present,
        },
        "reason_codes": reason_codes,
        "sides": sides,
        "source": {
            "archive_md5": observed_md5,
            "doi": sources["dataset"]["doi"],
            "version": sources["dataset"]["version"],
        },
        "status": "READY_FOR_FROZEN_HEADLINE_TEST"
        if ready
        else "PUBLIC_DATA_INSUFFICIENT_FOR_FROZEN_HEADLINE_TEST",
        "version": 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()

    prereg = load_json(HERE / "PREREGISTRATION.json")
    sources = load_json(HERE / "SOURCES.json")
    temporary: tempfile.TemporaryDirectory[str] | None = None
    archive = args.archive
    try:
        if archive is None:
            temporary = tempfile.TemporaryDirectory(prefix="terrynce-glacier-001-")
            archive = Path(temporary.name) / sources["dataset"]["archive_file"]
            download(sources["dataset"]["archive_url"], archive)
        result = inspect_archive(archive, sources["dataset"]["archive_md5"], prereg, sources)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"headline_test_ready": result["headline_test_ready"], "status": result["status"]}))
        if args.require_ready and not result["headline_test_ready"]:
            return 2
        return 0
    finally:
        if temporary is not None:
            temporary.cleanup()


if __name__ == "__main__":
    sys.exit(main())

