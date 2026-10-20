"""Regression checks for infrastructure failures and Gate 1 result provenance."""
import pathlib
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import cell_dispatch
import cell_run


class Gate1EvidenceTest(unittest.TestCase):
    def setUp(self):
        self.rec = {"run_id": 123, "fp": "0123456789abcdef",
                    "plan": [{"task": "T1", "cell": "target", "variant": "gh-macos"}]}
        self.result = {"task": "T1", "cell": "target", "mode": "naive", "variant": "gh-macos",
                       "run_id": "123", "fp": self.rec["fp"], "accepted": True,
                       "job_conclusion": "success", "pass": False, "verify_rc": 1}

    def flag(self, **updates):
        result = dict(self.result, **updates)
        return cell_dispatch.gate1_flag(result, self.rec, "T1", "target", "naive")

    def test_completed_naive_failure_is_evidence(self):
        self.assertEqual(self.flag(), "F")
        self.assertEqual(self.flag(**{"pass": True, "verify_rc": 0}), "P")

    def test_incomplete_verifier_is_not_a_naive_failure(self):
        for updates in ({"verify_rc": None}, {"verify_timed_out": True}, {"verify_rc": -9},
                        {"invalid": True}, {"pass": None}, {"verify_rc": 0}):
            with self.subTest(updates=updates):
                self.assertEqual(self.flag(**updates), "E")

    def test_stale_or_unattributable_results_are_rejected(self):
        for updates in ({"fp": "different"}, {"run_id": 124}, {"accepted": False},
                        {"job_conclusion": "failure"}, {"task": "T2"}, {"cell": "base"},
                        {"mode": "ref"}, {"variant": "gh-windows"}):
            with self.subTest(updates=updates):
                self.assertEqual(self.flag(**updates), "E")

    def test_fixture_failure_summary_is_not_a_graded_failure(self):
        self.assertEqual(self.flag(verify_summary={"points": 0, "total": 4}), "F")
        for summary in ({"points": None, "total": None}, {"points": 0, "total": 0},
                        {"points": 5, "total": 4}, {"points": True, "total": 4}, None):
            with self.subTest(summary=summary):
                self.assertEqual(self.flag(verify_rc=2, verify_summary=summary), "E")


class RunnerTimeoutTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.args = types.SimpleNamespace(task="T1", cell="target", variant="gh-macos",
                                          how="plain", out=self.tmp.name, model="test", tag="")
        self.run = cell_run.Run(self.args, "ref", "0123456789abcdef",
                                {"task.json": (b'{"id":"T1"}', 0o644)})
        self.ex = types.SimpleNamespace(ws="/workspace", stage="/stage", start=Mock(), reset=Mock(),
                                         stop=Mock(), join=lambda *p: "/".join(p), file_cmd=lambda p: p,
                                         run=Mock(return_value=(None, "private fixture marker", True)))
        self.run.pick = Mock(return_value="setup.py")
        self.run.stage_one = Mock(return_value="/stage/setup.py")
        self.run.stage_files = Mock()
        self.run.facts = Mock()

    def tearDown(self):
        self.tmp.cleanup()

    def test_setup_timeout_stops_before_solution(self):
        self.run.run_solution = Mock()
        with patch.object(cell_run, "make_executor", return_value=self.ex):
            result = self.run.go()
        self.assertTrue(result["invalid"])
        self.assertIsNone(result["pass"])
        self.assertEqual(result["error_kind"], "setup timed out")
        self.run.run_solution.assert_not_called()

    def test_verifier_timeout_is_invalid_and_public_output_stays_private(self):
        def start():
            self.run.ex = self.ex
        self.run.start = start
        self.run.run_solution = Mock()
        result = self.run.go()
        self.assertTrue(result["invalid"])
        self.assertTrue(result["verify_timed_out"])
        self.assertIsNone(result["pass"])
        with patch.dict(cell_run.os.environ, {"CELL_PUBLIC_TAIL": "0"}):
            public = cell_run.public_line(result)
        self.assertNotIn("private fixture marker", public)
        self.assertIn("verifier timed out", public)


if __name__ == "__main__":
    unittest.main()
