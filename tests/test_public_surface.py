import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicSurfaceTests(unittest.TestCase):
    def test_public_receipt_projects_frozen_result(self):
        frozen = json.loads(
            (ROOT / "experiments/terrynce_glacier_001/results/PUBLIC_DATA_FEASIBILITY.json").read_text()
        )
        public = json.loads((ROOT / "docs/receipt.latest.json").read_text())

        self.assertEqual(public["experiment_id"], frozen["experiment_id"])
        self.assertEqual(public["status"], frozen["status"])
        self.assertEqual(public["claim_status"], frozen["claim_status"])
        self.assertEqual(public["headline_test_ready"], frozen["headline_test_ready"])
        self.assertEqual(public["source"], frozen["source"])

    def test_retired_product_claims_stay_off_public_surface(self):
        public_text = "\n".join(
            (ROOT / path).read_text()
            for path in (
                "README.md",
                "docs/index.html",
                "docs/receipt.latest.json",
                "LICENSE",
            )
        )
        retired_claims = (
            "Real-time safety monitoring for AI systems",
            "Real κ/ε math",
            "EMERGENCY SHUTDOWN",
            "OpenLine Hub",
            "SPY likely up tomorrow",
            "[Your Name]",
        )
        for claim in retired_claims:
            with self.subTest(claim=claim):
                self.assertNotIn(claim, public_text)

    def test_legacy_entry_points_are_inert(self):
        for path in (
            "emergence_guard.py",
            "olp_client.py",
            "wire_openline_demo.py",
            "scripts/prebreach_guard.py",
        ):
            with self.subTest(path=path):
                text = (ROOT / path).read_text()
                self.assertIn("Archived", text)
                self.assertNotIn("random.uniform", text)
                self.assertNotIn("write_text", text)

    def test_data_specification_is_public_not_correspondence(self):
        text = (
            ROOT
            / "experiments/terrynce_glacier_001/author_intake/AUTHOR_DATA_REQUEST.md"
        ).read_text()
        self.assertIn("public data specification", text)
        self.assertNotIn("Dear Professor", text)
        self.assertNotIn("@geo.uio.no", text)

    def test_workflow_never_commits_generated_evidence(self):
        workflow = (ROOT / ".github/workflows/update-receipt.yml").read_text()
        self.assertNotIn("git push", workflow)
        self.assertNotIn("python3 wire_openline_demo.py", workflow)
        self.assertNotIn("python wire_openline_demo.py", workflow)


if __name__ == "__main__":
    unittest.main()
