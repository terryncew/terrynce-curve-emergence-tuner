from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "experiments" / "terrynce_glacier_001" / "run_feasibility.py"
SPEC = importlib.util.spec_from_file_location("terrynce_glacier_001", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FeasibilityContractTests(unittest.TestCase):
    def test_frozen_boundaries(self) -> None:
        prereg = json.loads(
            (ROOT / "experiments" / "terrynce_glacier_001" / "PREREGISTRATION.json").read_text()
        )
        self.assertEqual(prereg["boundaries"]["bridge_equation_status"], "RETIRED")
        self.assertEqual(prereg["boundaries"]["nepal_2026_role"], "MOTIVATION_ONLY")
        self.assertFalse(prereg["boundaries"]["universal_tipping_claim"])
        self.assertTrue(prereg["walk_forward"]["prefix_only"])
        self.assertFalse(prereg["walk_forward"]["future_aware_smoothing"])

    def test_density_gate_passes_regular_latest_window(self) -> None:
        observations = [date(2020, 1, 1) + timedelta(days=10 * index) for index in range(15)]
        result = MODULE.density_gate(observations, minimum=15, multiplier=2.0)
        self.assertTrue(result["passed"])
        self.assertEqual(result["reason"], "PASS")

    def test_density_gate_blocks_large_gap(self) -> None:
        observations = [date(2020, 1, 1) + timedelta(days=10 * index) for index in range(14)]
        observations.append(observations[-1] + timedelta(days=25))
        result = MODULE.density_gate(observations, minimum=15, multiplier=2.0)
        self.assertFalse(result["passed"])
        self.assertEqual(result["reason"], "GAP_LIMIT_EXCEEDED")

    def test_density_gate_blocks_too_few_acquisitions(self) -> None:
        observations = [date(2020, 1, 1) + timedelta(days=10 * index) for index in range(14)]
        result = MODULE.density_gate(observations, minimum=15, multiplier=2.0)
        self.assertFalse(result["passed"])
        self.assertEqual(result["reason"], "TOO_FEW_ACQUISITIONS")

    def test_zip_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../escape.txt", "no")
            with zipfile.ZipFile(archive) as bundle:
                with self.assertRaisesRegex(ValueError, "unsafe ZIP member"):
                    MODULE.ensure_safe_members(bundle.namelist())

    def test_wrong_source_identity_fails_closed(self) -> None:
        prereg = json.loads(
            (ROOT / "experiments" / "terrynce_glacier_001" / "PREREGISTRATION.json").read_text()
        )
        sources = json.loads(
            (ROOT / "experiments" / "terrynce_glacier_001" / "SOURCES.json").read_text()
        )
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "wrong.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("east_disp/example.txt", "wrong")
            with self.assertRaisesRegex(ValueError, "source MD5 mismatch"):
                MODULE.inspect_archive(archive, sources["dataset"]["archive_md5"], prereg, sources)


if __name__ == "__main__":
    unittest.main()

