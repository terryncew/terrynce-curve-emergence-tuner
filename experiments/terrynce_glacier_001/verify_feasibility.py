#!/usr/bin/env python3
"""Independent, deliberately small verifier for the frozen feasibility receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path, PurePosixPath


EXPECTED_MD5 = "cf418a1dc5f062e2ba2c2f98008f3e40"
FAILURE_DATE = date(2022, 11, 1)
PATTERNS = {
    "east": re.compile(r"^east_disp/(\d{8})_(\d{8})_disp\.txt$"),
    "west": re.compile(r"^west_disp/(\d{8})_(\d{8})_west_disp\.txt$"),
}
REQUIRED_REASONS = {
    "CONTROL_EXPOSURE_BELOW_FIVE_GLACIER_YEARS",
    "CSD_SAMPLING_GATE_FAILED",
    "FINAL_WARNING_WINDOW_ABSENT",
    "FROZEN_SPATIAL_ROLE_METADATA_ABSENT",
}


def fail(message: str) -> int:
    print(json.dumps({"error": message, "verified": False}, sort_keys=True))
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    digest = hashlib.md5(args.archive.read_bytes()).hexdigest()  # nosec: identity check
    if digest != EXPECTED_MD5:
        return fail("archive identity mismatch")

    acquisitions: dict[str, set[date]] = {"east": set(), "west": set()}
    counts = {"east": 0, "west": 0}
    with zipfile.ZipFile(args.archive) as bundle:
        for name in bundle.namelist():
            member = PurePosixPath(name)
            if member.is_absolute() or ".." in member.parts:
                return fail("unsafe archive member")
            for side, pattern in PATTERNS.items():
                match = pattern.match(name)
                if match:
                    counts[side] += 1
                    acquisitions[side].update(
                        datetime.strptime(value, "%Y%m%d").date() for value in match.groups()
                    )

    result = json.loads(args.result.read_text(encoding="utf-8"))
    checks = {
        "claim_unearned": result.get("claim_status") == "UNTESTED",
        "east_acquisitions": len(acquisitions["east"]) == 19,
        "east_gap": (FAILURE_DATE - max(acquisitions["east"])).days == 16,
        "east_intervals": counts["east"] == 30,
        "headline_blocked": result.get("headline_test_ready") is False,
        "reasons_complete": set(result.get("reason_codes", ())) == REQUIRED_REASONS,
        "source_bound": result.get("source", {}).get("archive_md5") == EXPECTED_MD5,
        "status": result.get("status")
        == "PUBLIC_DATA_INSUFFICIENT_FOR_FROZEN_HEADLINE_TEST",
        "west_acquisitions": len(acquisitions["west"]) == 12,
        "west_intervals": counts["west"] == 12,
    }
    if not all(checks.values()):
        return fail("; ".join(name for name, passed in checks.items() if not passed))
    print(json.dumps({"checks": checks, "verified": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

