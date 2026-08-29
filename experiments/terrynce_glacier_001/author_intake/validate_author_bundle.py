#!/usr/bin/env python3
"""Validate author-derived TERRYNCE-GLACIER-001 measurements, fail closed."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
VELOCITY_COLUMNS = (
    "glacier_id",
    "interval_start_utc",
    "interval_end_utc",
    "profile_point_id",
    "position_m_along_flowline",
    "zone",
    "along_flow_displacement_m",
    "along_flow_velocity_m_per_day",
    "source_product",
)
TERMINUS_COLUMNS = (
    "glacier_id",
    "observed_at",
    "terminus_position_m",
    "source_product",
)
CONTROL_COLUMNS = (
    "glacier_id",
    "latitude",
    "longitude",
    "detached",
    "control_source",
)


class BundleError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_utc(raw: str) -> datetime:
    if not raw.endswith("Z"):
        raise BundleError(f"timestamp must end in Z: {raw}")
    try:
        parsed = datetime.fromisoformat(raw[:-1] + "+00:00")
    except ValueError as exc:
        raise BundleError(f"invalid timestamp: {raw}") from exc
    if parsed.tzinfo != timezone.utc:
        raise BundleError(f"timestamp must be UTC: {raw}")
    return parsed


def finite_float(raw: str, field: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise BundleError(f"invalid {field}: {raw}") from exc
    if not math.isfinite(value):
        raise BundleError(f"non-finite {field}: {raw}")
    return value


def read_csv(path: Path, expected: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        if columns != expected:
            raise BundleError(f"unexpected columns in {path.name}: {columns}")
        rows = list(reader)
    if not rows:
        raise BundleError(f"empty required file: {path.name}")
    return rows


def union_days(intervals: list[tuple[datetime, datetime]]) -> float:
    if not intervals:
        return 0.0
    merged: list[list[datetime]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        elif end > merged[-1][1]:
            merged[-1][1] = end
    return sum((end - start).total_seconds() for start, end in merged) / 86400.0


def density_gate(acquisitions: set[datetime], minimum: int, multiplier: float) -> dict:
    ordered = sorted(acquisitions)
    if len(ordered) < minimum:
        return {
            "acquisitions": len(ordered),
            "passed": False,
            "reason": "TOO_FEW_ACQUISITIONS",
        }
    window = ordered[-minimum:]
    gaps = [(right - left).total_seconds() / 86400.0 for left, right in zip(window, window[1:])]
    median_gap = statistics.median(gaps)
    maximum_gap = max(gaps)
    passed = all(gap < multiplier * median_gap for gap in gaps)
    return {
        "acquisitions": len(window),
        "maximum_gap_days": round(maximum_gap, 6),
        "median_gap_days": round(median_gap, 6),
        "passed": passed,
        "reason": "PASS" if passed else "GAP_LIMIT_EXCEEDED",
    }


def validate(bundle: Path, contract: dict) -> dict:
    manifest_path = bundle / "bundle_manifest.json"
    if not manifest_path.is_file():
        raise BundleError("missing bundle_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != contract["schema_version"]:
        raise BundleError("schema version mismatch")
    if manifest.get("source_doi") != contract["source_doi"]:
        raise BundleError("source DOI mismatch")
    if manifest.get("raw_imagery_included") is not False:
        raise BundleError("raw imagery is outside this intake contract")
    if not str(manifest.get("license_or_permission", "")).strip():
        raise BundleError("license_or_permission is required")

    filenames = (
        contract["bundle_files"]["velocity_observations"],
        contract["bundle_files"]["terminus_observations"],
        contract["bundle_files"]["control_registry"],
    )
    declared = manifest.get("files")
    if not isinstance(declared, dict) or set(declared) != set(filenames):
        raise BundleError("manifest must declare exactly the three contract data files")
    for filename in filenames:
        path = bundle / filename
        if not path.is_file():
            raise BundleError(f"missing {filename}")
        expected_hash = declared[filename].get("sha256") if isinstance(declared[filename], dict) else None
        if expected_hash != sha256(path):
            raise BundleError(f"SHA-256 mismatch: {filename}")

    velocity_rows = read_csv(bundle / filenames[0], VELOCITY_COLUMNS)
    terminus_rows = read_csv(bundle / filenames[1], TERMINUS_COLUMNS)
    control_rows = read_csv(bundle / filenames[2], CONTROL_COLUMNS)
    allowed_products = set(contract["allowed_source_products"])
    zones = {"UPSTREAM", "TERMINUS"}

    velocity_keys: set[tuple[str, str, str, str]] = set()
    intervals_by_glacier: dict[str, set[tuple[datetime, datetime]]] = defaultdict(set)
    acquisitions_by_glacier: dict[str, set[datetime]] = defaultdict(set)
    east_final_zones: set[str] = set()
    latest_required = parse_utc(contract["east_final_interval"]["latest_required_end_utc"])
    tolerance = contract["velocity_tolerance_m_per_day"]
    for row in velocity_rows:
        key = (
            row["glacier_id"],
            row["interval_start_utc"],
            row["interval_end_utc"],
            row["profile_point_id"],
        )
        if key in velocity_keys:
            raise BundleError(f"duplicate velocity observation: {key}")
        velocity_keys.add(key)
        start = parse_utc(row["interval_start_utc"])
        end = parse_utc(row["interval_end_utc"])
        if end <= start:
            raise BundleError(f"non-positive velocity interval: {key}")
        zone = row["zone"]
        if zone not in zones:
            raise BundleError(f"invalid zone: {zone}")
        if row["source_product"] not in allowed_products:
            raise BundleError(f"invalid source_product: {row['source_product']}")
        position = finite_float(row["position_m_along_flowline"], "position_m_along_flowline")
        displacement = finite_float(row["along_flow_displacement_m"], "along_flow_displacement_m")
        velocity = finite_float(row["along_flow_velocity_m_per_day"], "along_flow_velocity_m_per_day")
        if position < 0 or velocity < 0:
            raise BundleError("flowline position and velocity must be nonnegative")
        duration_days = (end - start).total_seconds() / 86400.0
        if abs(displacement / duration_days - velocity) > tolerance:
            raise BundleError(f"velocity/displacement mismatch: {key}")
        intervals_by_glacier[row["glacier_id"]].add((start, end))
        acquisitions_by_glacier[row["glacier_id"]].update((start, end))
        if row["glacier_id"] == "BUKADABAN_EAST" and end >= latest_required:
            east_final_zones.add(zone)

    terminus_by_glacier: dict[str, set[datetime]] = defaultdict(set)
    terminus_keys: set[tuple[str, str]] = set()
    for row in terminus_rows:
        key = (row["glacier_id"], row["observed_at"])
        if key in terminus_keys:
            raise BundleError(f"duplicate terminus observation: {key}")
        terminus_keys.add(key)
        observed_at = parse_utc(row["observed_at"])
        position = finite_float(row["terminus_position_m"], "terminus_position_m")
        if position < 0:
            raise BundleError("terminus position must be nonnegative")
        if row["source_product"] not in allowed_products:
            raise BundleError(f"invalid source_product: {row['source_product']}")
        terminus_by_glacier[row["glacier_id"]].add(observed_at)

    control_ids: set[str] = set()
    for row in control_rows:
        glacier_id = row["glacier_id"]
        if glacier_id in control_ids:
            raise BundleError(f"duplicate control glacier: {glacier_id}")
        control_ids.add(glacier_id)
        latitude = finite_float(row["latitude"], "latitude")
        longitude = finite_float(row["longitude"], "longitude")
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise BundleError(f"invalid coordinates: {glacier_id}")
        if row["detached"].lower() != "false":
            raise BundleError(f"control must be non-detaching: {glacier_id}")
        if not row["control_source"].strip():
            raise BundleError(f"control_source required: {glacier_id}")

    missing_control_series = sorted(control_ids - set(intervals_by_glacier))
    control_days = sum(union_days(list(intervals_by_glacier[item])) for item in control_ids)
    control_years = control_days / 365.2425
    final_terminus = sorted(
        stamp for stamp in terminus_by_glacier["BUKADABAN_EAST"] if stamp >= datetime(2022, 10, 16, tzinfo=timezone.utc)
    )
    csd = density_gate(
        acquisitions_by_glacier["BUKADABAN_EAST"],
        contract["critical_slowing_down_gate"]["minimum_acquisitions"],
        contract["critical_slowing_down_gate"]["maximum_gap_multiplier_of_median"],
    )

    gates = {
        "control_exposure": control_years >= contract["minimum_control_exposure_glacier_years"],
        "control_series_complete": not missing_control_series,
        "csd_sampling": csd["passed"],
        "east_final_interval": set(contract["east_final_interval"]["required_zones"]).issubset(east_final_zones),
        "east_final_terminus_series": len(final_terminus) >= 2,
        "manifest_provenance": True,
    }
    reasons = [name.upper() + "_FAILED" for name, passed in gates.items() if not passed]
    ready = all(gates.values())
    return {
        "bundle_id": manifest.get("bundle_id"),
        "experiment_id": contract["experiment_id"],
        "gates": gates,
        "headline_test_ready": ready,
        "measurements": {
            "control_exposure_glacier_years": round(control_years, 6),
            "control_glacier_count": len(control_ids),
            "csd_sampling": csd,
            "east_final_zones": sorted(east_final_zones),
            "east_terminus_observations_since_2022_10_16": len(final_terminus),
            "terminus_observation_count": len(terminus_rows),
            "velocity_observation_count": len(velocity_rows),
        },
        "reason_codes": reasons,
        "source_doi": manifest["source_doi"],
        "status": "VALID_AND_READY" if ready else "VALID_BUT_NOT_READY",
        "version": 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    contract = json.loads((HERE / "BUNDLE_CONTRACT.json").read_text(encoding="utf-8"))
    try:
        result = validate(args.bundle, contract)
    except (BundleError, json.JSONDecodeError, OSError) as exc:
        print(json.dumps({"error": str(exc), "status": "INVALID_BUNDLE"}, sort_keys=True))
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"headline_test_ready": result["headline_test_ready"], "status": result["status"]}))
    if args.require_ready and not result["headline_test_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

