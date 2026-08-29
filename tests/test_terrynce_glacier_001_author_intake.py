from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTAKE = ROOT / "experiments" / "terrynce_glacier_001" / "author_intake"
SPEC = importlib.util.spec_from_file_location("author_intake", INTAKE / "validate_author_bundle.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CONTRACT = json.loads((INTAKE / "BUNDLE_CONTRACT.json").read_text())


def iso(stamp: datetime) -> str:
    return stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def make_bundle(root: Path, *, complete: bool = True) -> None:
    velocity: list[dict[str, object]] = []
    start = datetime(2017, 1, 1, tzinfo=timezone.utc)
    for index in range(16):
        left = start + timedelta(days=120 * index)
        right = left + timedelta(days=120)
        for zone, point, position in (("UPSTREAM", "u1", 100.0), ("TERMINUS", "t1", 900.0)):
            velocity.append(
                {
                    "glacier_id": "CONTROL_ONE",
                    "interval_start_utc": iso(left),
                    "interval_end_utc": iso(right),
                    "profile_point_id": f"{point}-{index}",
                    "position_m_along_flowline": position,
                    "zone": zone,
                    "along_flow_displacement_m": 12.0,
                    "along_flow_velocity_m_per_day": 0.1,
                    "source_product": "SENTINEL_2_DERIVED",
                }
            )
    control_two_start = start
    control_two_end = start + timedelta(days=2 * 365)
    velocity.append(
        {
            "glacier_id": "CONTROL_TWO",
            "interval_start_utc": iso(control_two_start),
            "interval_end_utc": iso(control_two_end),
            "profile_point_id": "u1",
            "position_m_along_flowline": 100.0,
            "zone": "UPSTREAM",
            "along_flow_displacement_m": 73.0,
            "along_flow_velocity_m_per_day": 0.1,
            "source_product": "SENTINEL_2_DERIVED",
        }
    )

    east_start = datetime(2022, 10, 17, 3, 42, tzinfo=timezone.utc)
    for index in range(15):
        left = east_start + timedelta(days=index)
        right = left + timedelta(days=1)
        for zone, point, position, speed in (
            ("UPSTREAM", "u1", 100.0, 20.0),
            ("TERMINUS", "t1", 900.0, 0.01),
        ):
            if not complete and index == 14 and zone == "TERMINUS":
                continue
            velocity.append(
                {
                    "glacier_id": "BUKADABAN_EAST",
                    "interval_start_utc": iso(left),
                    "interval_end_utc": iso(right),
                    "profile_point_id": f"{point}-{index}",
                    "position_m_along_flowline": position,
                    "zone": zone,
                    "along_flow_displacement_m": speed,
                    "along_flow_velocity_m_per_day": speed,
                    "source_product": "PLANETSCOPE_DERIVED",
                }
            )

    terminus = [
        {
            "glacier_id": "BUKADABAN_EAST",
            "observed_at": "2022-10-16T00:00:00Z",
            "terminus_position_m": 1000.0,
            "source_product": "PLANETSCOPE_DERIVED",
        },
        {
            "glacier_id": "BUKADABAN_EAST",
            "observed_at": "2022-11-01T03:42:00Z",
            "terminus_position_m": 1000.5,
            "source_product": "PLANETSCOPE_DERIVED",
        },
    ]
    controls = [
        {
            "glacier_id": "CONTROL_ONE",
            "latitude": 35.97,
            "longitude": 90.80,
            "detached": "false",
            "control_source": "published inventory A",
        },
        {
            "glacier_id": "CONTROL_TWO",
            "latitude": 35.98,
            "longitude": 90.82,
            "detached": "false",
            "control_source": "published inventory B",
        },
    ]

    files = {
        "velocity_observations.csv": (MODULE.VELOCITY_COLUMNS, velocity),
        "terminus_observations.csv": (MODULE.TERMINUS_COLUMNS, terminus),
        "control_registry.csv": (MODULE.CONTROL_COLUMNS, controls),
    }
    for filename, (columns, rows) in files.items():
        write_csv(root / filename, columns, rows)
    manifest_files = {
        filename: {"sha256": hashlib.sha256((root / filename).read_bytes()).hexdigest()}
        for filename in files
    }
    (root / "bundle_manifest.json").write_text(
        json.dumps(
            {
                "bundle_id": "synthetic-contract-fixture",
                "files": manifest_files,
                "license_or_permission": "synthetic test data",
                "raw_imagery_included": False,
                "schema_version": 1,
                "source_doi": CONTRACT["source_doi"],
            }
        ),
        encoding="utf-8",
    )


class AuthorIntakeTests(unittest.TestCase):
    def test_complete_bundle_clears_every_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_bundle(root)
            result = MODULE.validate(root, CONTRACT)
        self.assertEqual(result["status"], "VALID_AND_READY")
        self.assertTrue(result["headline_test_ready"])
        self.assertTrue(all(result["gates"].values()))

    def test_missing_final_zone_stays_valid_but_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_bundle(root, complete=False)
            result = MODULE.validate(root, CONTRACT)
        self.assertEqual(result["status"], "VALID_BUT_NOT_READY")
        self.assertFalse(result["gates"]["east_final_interval"])

    def test_manifest_hash_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_bundle(root)
            with (root / "velocity_observations.csv").open("a", encoding="utf-8") as handle:
                handle.write("tamper\n")
            with self.assertRaisesRegex(MODULE.BundleError, "SHA-256 mismatch"):
                MODULE.validate(root, CONTRACT)

    def test_raw_imagery_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_bundle(root)
            manifest_path = root / "bundle_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["raw_imagery_included"] = True
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.BundleError, "raw imagery"):
                MODULE.validate(root, CONTRACT)

    def test_control_exposure_uses_interval_union(self) -> None:
        first = datetime(2020, 1, 1, tzinfo=timezone.utc)
        intervals = [
            (first, first + timedelta(days=100)),
            (first + timedelta(days=50), first + timedelta(days=150)),
        ]
        self.assertEqual(MODULE.union_days(intervals), 150.0)


if __name__ == "__main__":
    unittest.main()
