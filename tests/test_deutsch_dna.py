from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "deutsch_dna.py"
sys.path.insert(0, str(SCRIPT.parent))
import deutsch_dna as dna  # noqa: E402


BASE_TIME = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
LOCAL_ENDPOINT = "http://localhost:8081/v2/check"


class FakeResponse:
    def __init__(self, value: dict):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.value).encode("utf-8")


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="deutschdna-test-")
        self.home = Path(self._temporary.name)
        self.store = dna.StateStore(self.home)

    def tearDown(self):
        self._temporary.cleanup()

    def record_example(self, at=BASE_TIME, event_id=None, **overrides):
        params = dict(
            original="Ich spreche mit mein Chef.",
            corrected="Ich spreche mit meinem Chef.",
            category="case",
            pattern="mit + dative",
            rule="mit always governs dative",
            verification_status="verified",
            at=at,
            event_id=event_id,
        )
        params.update(overrides)
        return self.store.record(**params)


class ProfileAndRecordingTests(StoreTestCase):
    def test_init_preserves_existing_profile_fields(self):
        first = self.store.init_profile(name="Lena", native_language="tr", at=BASE_TIME)
        second = self.store.init_profile(level="B2", at=BASE_TIME + timedelta(minutes=1))
        self.assertEqual(first["name"], "Lena")
        self.assertEqual(second["name"], "Lena")
        self.assertEqual(second["native_language"], "tr")
        self.assertEqual(second["level"], "B2")
        self.assertEqual(first["created_at"], dna.iso(BASE_TIME))

    def test_recurring_pattern_merges_and_resets_schedule(self):
        first, status, _ = self.record_example(event_id="event-1")
        second, status_again, extra = self.record_example(at=BASE_TIME + timedelta(days=4), event_id="event-2")
        self.assertEqual(status, "recorded")
        self.assertEqual(status_again, "updated")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["occurrences"], 2)
        self.assertEqual(second["review_step"], 0)
        self.assertEqual(second["next_review"], dna.iso(BASE_TIME + timedelta(days=5)))
        self.assertEqual(extra["recent_occurrences"], 2)
        self.assertEqual(extra["previous"]["last_seen"], dna.iso(BASE_TIME))
        self.assertEqual(extra["previous"]["review_step"], 0)
        self.assertEqual(extra["previous"]["occurrences"], 1)

    def test_explicit_event_id_is_idempotent_without_time_limit(self):
        _, status, _ = self.record_example(event_id="same-event")
        repeated, status_again, _ = self.record_example(event_id="same-event", at=BASE_TIME + timedelta(days=10))
        self.assertEqual(status, "recorded")
        self.assertEqual(status_again, "duplicate")
        self.assertEqual(repeated["occurrences"], 1)

    def test_retry_without_event_id_is_deduplicated_within_window(self):
        self.record_example()
        retried, status, _ = self.record_example(at=BASE_TIME + timedelta(minutes=5))
        self.assertEqual(status, "duplicate")
        self.assertEqual(retried["occurrences"], 1)
        later, status_later, _ = self.record_example(at=BASE_TIME + timedelta(days=2))
        self.assertEqual(status_later, "updated")
        self.assertEqual(later["occurrences"], 2)

    def test_german_case_names_and_spacing_resolve_to_one_pattern(self):
        first, _, _ = self.record_example()
        variants = ["mit + Dativ", "mit+dat.", "mit governs the dative", "MIT + DATIVE"]
        for index, variant in enumerate(variants, start=1):
            mistake, status, _ = self.record_example(
                pattern=variant,
                original=f"Satz {index} mit mein Chef.",
                corrected=f"Satz {index} mit meinem Chef.",
                at=BASE_TIME + timedelta(days=index),
            )
            self.assertEqual(mistake["id"], first["id"], variant)
            self.assertEqual(status, "updated", variant)
        self.assertEqual(len(self.store.list(status="all")), 1)

    def test_same_pattern_key_in_another_category_resolves_to_existing(self):
        first, _, _ = self.record_example()
        mistake, status, extra = self.record_example(
            category="preposition",
            original="Ich fahre mit mein Auto.",
            corrected="Ich fahre mit meinem Auto.",
            at=BASE_TIME + timedelta(days=1),
        )
        self.assertEqual(mistake["id"], first["id"])
        self.assertEqual(status, "updated")
        self.assertEqual(extra["resolved_by"], "pattern_key")

    def test_record_by_mistake_id(self):
        first, _, _ = self.record_example()
        mistake, status, extra = self.store.record(
            original="Ich wohne bei mein Bruder.",
            corrected="Ich wohne bei meinem Bruder.",
            mistake_id=first["id"],
            at=BASE_TIME + timedelta(days=1),
        )
        self.assertEqual(status, "updated")
        self.assertEqual(mistake["occurrences"], 2)
        self.assertEqual(extra["resolved_by"], "mistake_id")
        with self.assertRaises(dna.DeutschDNAError):
            self.store.record(original="x", corrected="y", mistake_id="m_missing")

    def test_missing_pattern_fields_are_rejected(self):
        with self.assertRaises(dna.DeutschDNAError):
            self.store.record(original="Ich bin.", corrected="Ich bin.", category="case")

    def test_new_pattern_reports_similar_existing_patterns(self):
        first, _, _ = self.record_example(
            category="agreement",
            pattern="adjective ending after der-word",
            original="den neue Film",
            corrected="den neuen Film",
        )
        second, status, extra = self.record_example(
            category="agreement",
            pattern="adjective ending after ein-word",
            original="einen neue Job",
            corrected="einen neuen Job",
            at=BASE_TIME + timedelta(hours=1),
        )
        self.assertEqual(status, "recorded")
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(extra["similar_patterns"][0]["id"], first["id"])

    def test_pattern_key_normalization(self):
        self.assertEqual(dna.pattern_key("mit + Dativ"), "mit + dative")
        self.assertEqual(dna.pattern_key("Akk. after für"), "accusative after für")
        self.assertEqual(
            dna.pattern_key("obwohl sends the finite verb to the end"),
            "obwohl sends finite verb to end",
        )
        self.assertEqual(dna.pattern_key("helfen takes dative case"), "helfen + dative")
        self.assertEqual(dna.mistake_id("case", "mit + dative"), "m_d90db5d8f27a")


class ReviewTests(StoreTestCase):
    def test_due_and_pass_follow_review_intervals(self):
        mistake, _, _ = self.record_example()
        self.assertEqual(self.store.due(at=BASE_TIME + timedelta(hours=23)), [])
        self.assertEqual(len(self.store.due(at=BASE_TIME + timedelta(days=1))), 1)
        graded, status = self.store.grade(mistake["id"], result="pass", at=BASE_TIME + timedelta(days=1))
        self.assertEqual(status, "graded")
        self.assertEqual(graded["review_step"], 1)
        self.assertEqual(graded["next_review"], dna.iso(BASE_TIME + timedelta(days=4)))
        self.assertEqual(graded["review_history"][-1]["source"], "review")

    def test_fail_records_recurrence_and_restarts_review(self):
        mistake, _, _ = self.record_example()
        failed, _ = self.store.grade(
            mistake["id"],
            result="fail",
            answer="mit mein Freund",
            correction="mit meinem Freund",
            at=BASE_TIME + timedelta(days=1),
        )
        self.assertEqual(failed["occurrences"], 2)
        self.assertEqual(failed["review_failures"], 1)
        self.assertEqual(failed["review_step"], 0)
        self.assertEqual(failed["next_review"], dna.iso(BASE_TIME + timedelta(days=2)))
        self.assertEqual(failed["examples"][-1]["original"], "mit mein Freund")

    def test_fail_without_answer_still_logs_an_example(self):
        mistake, _, _ = self.record_example()
        failed, _ = self.store.grade(mistake["id"], result="fail", at=BASE_TIME + timedelta(days=1))
        self.assertEqual(len(failed["examples"]), 2)
        self.assertIsNone(failed["examples"][-1]["original"])

    def test_duplicate_grade_within_window_is_ignored(self):
        mistake, _, _ = self.record_example()
        review_time = BASE_TIME + timedelta(days=1)
        self.store.grade(mistake["id"], result="fail", at=review_time)
        repeated, status = self.store.grade(mistake["id"], result="fail", at=review_time + timedelta(minutes=1))
        self.assertEqual(status, "duplicate")
        self.assertEqual(repeated["occurrences"], 2)
        self.assertEqual(repeated["review_attempts"], 1)

    def test_mastered_pattern_is_reactivated_by_a_recurrence(self):
        mistake, _, _ = self.record_example()
        review_time = BASE_TIME + timedelta(days=1)
        for step in range(len(dna.REVIEW_INTERVALS)):
            mistake, _ = self.store.grade(mistake["id"], result="pass", at=review_time)
            if step + 1 < len(dna.REVIEW_INTERVALS):
                review_time = dna.parse_moment(mistake["next_review"])
        self.assertEqual(mistake["status"], "mastered")
        self.assertIsNone(mistake["next_review"])
        self.assertEqual(mistake["mastered_at"], dna.iso(review_time))

        recurring, status, _ = self.record_example(at=review_time + timedelta(days=2), event_id="recurrence")
        self.assertEqual(status, "updated")
        self.assertEqual(recurring["status"], "active")
        self.assertEqual(recurring["review_step"], 0)
        self.assertEqual(recurring["mastery_score"], 0.0)
        self.assertIsNone(recurring["mastered_at"])
        self.assertEqual(recurring["reactivated_at"], dna.iso(review_time + timedelta(days=2)))

    def test_observe_counts_correct_use_and_advances_due_pattern(self):
        mistake, _, _ = self.record_example()
        observed_at = BASE_TIME + timedelta(days=2)
        results = self.store.observe([mistake["id"]], context="mit meinem Kunden", at=observed_at)
        self.assertEqual(results[0]["status"], "observed_and_advanced")
        self.assertEqual(results[0]["correct_uses"], 1)
        self.assertEqual(results[0]["review_step"], 1)
        duplicate = self.store.observe([mistake["id"]], context="mit meinem Kunden", at=observed_at + timedelta(minutes=1))
        self.assertEqual(duplicate[0]["status"], "duplicate")
        later = self.store.observe([mistake["id"]], context="mit einer Firma", at=observed_at + timedelta(minutes=10))
        self.assertEqual(later[0]["status"], "observed")
        self.assertEqual(later[0]["correct_uses"], 2)
        stored = self.store.show(mistake["id"])
        self.assertEqual(stored["review_history"][-1]["source"], "observed")
        self.assertEqual(dna.correct_total(stored), 2)


class RepairTests(StoreTestCase):
    def test_list_show_and_forget(self):
        first, _, _ = self.record_example()
        second, _, _ = self.record_example(
            category="preposition",
            pattern="warten auf + accusative",
            original="Ich warte dich.",
            corrected="Ich warte auf dich.",
            at=BASE_TIME + timedelta(hours=1),
        )
        rows = self.store.list(status="active")
        self.assertEqual([row["id"] for row in rows], [first["id"], second["id"]])
        self.assertEqual(self.store.list(category="preposition")[0]["id"], second["id"])
        self.assertEqual(self.store.show(second["id"])["pattern"], "warten auf + accusative")
        removed = self.store.forget(second["id"])
        self.assertEqual(removed["id"], second["id"])
        self.assertEqual(len(self.store.list(status="all")), 1)
        with self.assertRaises(dna.DeutschDNAError):
            self.store.show(second["id"])

    def test_forget_removes_pattern_from_sessions(self):
        mistake, _, _ = self.record_example()
        started = self.store.roleplay_start("arbeit", at=BASE_TIME)
        self.store.roleplay_finish(started["session"]["id"], turns=6, mistake_ids=[mistake["id"]], at=BASE_TIME + timedelta(minutes=5))
        self.store.forget(mistake["id"])
        sessions = json.loads((self.home / "sessions.json").read_text(encoding="utf-8"))["sessions"]
        self.assertEqual(sessions[0]["mistake_ids"], [])

    def test_merge_combines_history_and_future_records_resolve_to_target(self):
        target, _, _ = self.record_example()
        source, _, _ = self.record_example(
            pattern="mit requires dative object",
            original="Ich rede mit mein Bruder.",
            corrected="Ich rede mit meinem Bruder.",
            at=BASE_TIME + timedelta(days=1),
        )
        self.assertNotEqual(source["id"], target["id"])
        merged = self.store.merge(source["id"], target["id"], at=BASE_TIME + timedelta(days=2))
        self.assertEqual(merged["occurrences"], 2)
        self.assertEqual(len(merged["examples"]), 2)
        self.assertEqual(merged["first_seen"], dna.iso(BASE_TIME))
        self.assertEqual(merged["last_seen"], dna.iso(BASE_TIME + timedelta(days=1)))
        self.assertEqual(merged["next_review"], dna.iso(BASE_TIME + timedelta(days=1)))
        self.assertEqual(merged["merged_from"][0]["id"], source["id"])
        self.assertEqual(len(self.store.list(status="all")), 1)
        resolved, status, extra = self.record_example(
            pattern="mit requires dative object",
            original="Ich rede mit mein Vater.",
            corrected="Ich rede mit meinem Vater.",
            at=BASE_TIME + timedelta(days=3),
        )
        self.assertEqual(resolved["id"], target["id"])
        self.assertEqual(status, "updated")
        self.assertEqual(extra["resolved_by"], "alias")
        with self.assertRaises(dna.DeutschDNAError):
            self.store.merge(target["id"], target["id"])

    def test_rename_changes_id_keeps_alias_and_refuses_clashes(self):
        mistake, _, _ = self.record_example()
        other, _, _ = self.record_example(
            category="case",
            pattern="helfen + dative",
            original="Ich helfe dich.",
            corrected="Ich helfe dir.",
            at=BASE_TIME + timedelta(hours=1),
        )
        outcome = self.store.rename(mistake["id"], pattern="mit + Dativobjekt", category="preposition", rule="mit takes dative")
        renamed = outcome["mistake"]
        self.assertEqual(outcome["previous_id"], mistake["id"])
        self.assertNotEqual(renamed["id"], mistake["id"])
        self.assertEqual(renamed["category"], "preposition")
        self.assertEqual(renamed["rule"], "mit takes dative")
        self.assertIn({"category": "case", "pattern_key": "mit + dative"}, renamed["aliases"])
        resolved, status, _ = self.record_example(at=BASE_TIME + timedelta(days=1))
        self.assertEqual(resolved["id"], renamed["id"])
        self.assertEqual(status, "updated")
        with self.assertRaises(dna.DeutschDNAError):
            self.store.rename(renamed["id"], pattern="helfen + Dativ")
        with self.assertRaises(dna.DeutschDNAError):
            self.store.rename(other["id"])


class ReportingTests(StoreTestCase):
    def test_summary_reports_accuracy_clusters_and_streak(self):
        self.store.init_profile(name="Ahmet", level="B2", at=BASE_TIME)
        first, _, _ = self.record_example(
            category="preposition",
            pattern="warten auf + accusative",
            original="Ich warte dich.",
            corrected="Ich warte auf dich.",
        )
        self.record_example(
            category="preposition",
            pattern="denken an + accusative",
            original="Ich denke dich.",
            corrected="Ich denke an dich.",
            at=BASE_TIME + timedelta(hours=1),
        )
        self.record_example(
            category="preposition",
            pattern="denken an + accusative",
            original="Ich denke meine Familie.",
            corrected="Ich denke an meine Familie.",
            at=BASE_TIME + timedelta(days=1),
        )
        summary = self.store.summary(at=BASE_TIME + timedelta(days=1, hours=1))
        bucket = summary["categories"]["preposition"]
        self.assertEqual(bucket["patterns"], 2)
        self.assertEqual(bucket["errors"], 3)
        self.assertEqual(bucket["correct"], 0)
        self.assertEqual(bucket["accuracy_percent"], 20)
        self.assertTrue(bucket["weak"])
        self.assertEqual(summary["clusters"][0]["category"], "preposition")
        self.assertEqual(summary["clusters"][0]["patterns"][0], "denken an + accusative")
        self.assertEqual(summary["streak_days"], 2)
        self.assertEqual(summary["profile"]["name"], "Ahmet")
        self.assertEqual(summary["due_now"], 1)

        self.store.grade(first["id"], result="pass", at=BASE_TIME + timedelta(days=1, hours=2))
        summary = self.store.summary(at=BASE_TIME + timedelta(days=1, hours=3))
        self.assertEqual(summary["categories"]["preposition"]["correct"], 1)
        self.assertEqual(summary["categories"]["preposition"]["accuracy_percent"], 33)
        self.assertEqual(summary["weakest_patterns"][0]["pattern"], "denken an + accusative")

    def test_recap_counts_window_events(self):
        mistake, _, _ = self.record_example(at=BASE_TIME - timedelta(days=20))
        self.store.grade(mistake["id"], result="pass", at=BASE_TIME - timedelta(days=19))
        self.record_example(at=BASE_TIME - timedelta(days=2), event_id="recurrence")
        self.record_example(
            category="preposition",
            pattern="warten auf + accusative",
            original="Ich warte dich.",
            corrected="Ich warte auf dich.",
            at=BASE_TIME - timedelta(days=1),
        )
        self.store.grade(mistake["id"], result="fail", answer="mit mein Chef", correction="mit meinem Chef", at=BASE_TIME - timedelta(hours=12))
        self.store.observe([mistake["id"]], context="mit meinem Team", at=BASE_TIME - timedelta(hours=6))
        started = self.store.roleplay_start("restaurant", at=BASE_TIME - timedelta(hours=3))
        self.store.roleplay_finish(started["session"]["id"], turns=8, at=BASE_TIME - timedelta(hours=2, minutes=54))

        recap = self.store.recap(days=7, at=BASE_TIME)
        self.assertEqual(recap["errors"], {"total": 3, "new_patterns": 1, "recurrences": 2})
        self.assertEqual(recap["new_patterns"], ["warten auf + accusative"])
        self.assertEqual(recap["recurring_patterns"][0]["pattern"], "mit + dative")
        self.assertEqual(recap["reviews"], {"total": 1, "pass": 0, "hard": 0, "fail": 1})
        self.assertEqual(recap["correct_uses"], 1)
        self.assertEqual(recap["roleplays"]["count"], 1)
        self.assertEqual(recap["days_since_last_activity"], 0)
        self.assertEqual(recap["due_now"], 1)
        self.assertEqual(recap["next_focus"]["pattern"], "warten auf + accusative")

    def test_roleplay_duration_is_computed_from_timestamps(self):
        started = self.store.roleplay_start("restaurant", focus="case", at=BASE_TIME)
        session_id = started["session"]["id"]
        finished = self.store.roleplay_finish(session_id, turns=8, notes="Good flow", at=BASE_TIME + timedelta(minutes=6))
        self.assertEqual(finished["status"], "complete")
        self.assertEqual(finished["turns"], 8)
        self.assertEqual(finished["duration_seconds"], 360)
        again = self.store.roleplay_finish(session_id, turns=99, at=BASE_TIME + timedelta(hours=1))
        self.assertEqual(again["turns"], 8)
        other = self.store.roleplay_start("arzt", at=BASE_TIME)
        overridden = self.store.roleplay_finish(other["session"]["id"], turns=4, duration_seconds=100, at=BASE_TIME + timedelta(minutes=6))
        self.assertEqual(overridden["duration_seconds"], 100)


class CorrectionTests(unittest.TestCase):
    def test_small_change_is_minimal(self):
        result = dna.analyze_correction(
            "Ich möchte morgen mit mein Chef sprechen.",
            "Ich möchte morgen mit meinem Chef sprechen.",
        )
        self.assertEqual(result["minimality_status"], "minimal")
        self.assertEqual(result["changes"][0]["original_tokens"], ["mein"])
        self.assertEqual(result["changes"][0]["corrected_tokens"], ["meinem"])

    def test_rewrite_is_flagged(self):
        result = dna.analyze_correction("Ich bin müde.", "Erschöpft sank ich sofort ins Bett.")
        self.assertEqual(result["minimality_status"], "possible_rewrite")

    def test_language_tool_can_verify_correction(self):
        responses = [
            FakeResponse(
                {
                    "matches": [
                        {
                            "message": "Kasus",
                            "offset": 17,
                            "length": 4,
                            "rule": {"id": "GERMAN_CASE"},
                            "replacements": [{"value": "meinem"}],
                        }
                    ]
                }
            ),
            FakeResponse({"matches": []}),
        ]
        with mock.patch("urllib.request.urlopen", side_effect=responses):
            result = dna.verify_correction(
                "Ich spreche mit mein Chef.",
                "Ich spreche mit meinem Chef.",
                endpoint=LOCAL_ENDPOINT,
            )
        self.assertEqual(result["validator_status"], "verified")
        self.assertEqual(result["resolved_rule_ids"], ["GERMAN_CASE"])
        self.assertTrue(result["replacement_supported"])

    def test_unrelated_language_tool_finding_does_not_verify_the_edit(self):
        responses = [
            FakeResponse(
                {
                    "matches": [
                        {
                            "message": "Unrelated",
                            "offset": 0,
                            "length": 3,
                            "rule": {"id": "UNRELATED_RULE"},
                            "replacements": [{"value": "Something else"}],
                        }
                    ]
                }
            ),
            FakeResponse({"matches": []}),
        ]
        with mock.patch("urllib.request.urlopen", side_effect=responses):
            result = dna.verify_correction(
                "Ich spreche mit mein Chef.",
                "Ich spreche mit meinem Chef.",
                endpoint=LOCAL_ENDPOINT,
            )
        self.assertEqual(result["validator_status"], "supported")
        self.assertFalse(result["replacement_supported"])

    def test_unreachable_language_tool_degrades_cleanly(self):
        with mock.patch("urllib.request.urlopen", side_effect=dna.urllib.error.URLError("offline")):
            result = dna.verify_correction("Das ist gut.", "Das ist gut.", endpoint="http://127.0.0.1:8081/v2/check")
        self.assertEqual(result["validator_status"], "unavailable")
        self.assertIn("analysis", result)

    def test_remote_endpoint_is_blocked_unless_allowed(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            result = dna.verify_correction("Das ist gut.", "Das ist gut.", endpoint="https://api.languagetool.org/v2/check")
            urlopen.assert_not_called()
        self.assertEqual(result["validator_status"], "unavailable")
        self.assertIn("--allow-remote", result["reason"])
        with mock.patch("urllib.request.urlopen", side_effect=[FakeResponse({"matches": []}), FakeResponse({"matches": []})]):
            allowed = dna.verify_correction(
                "Das ist gut.", "Das ist gut.", endpoint="https://api.languagetool.org/v2/check", allow_remote=True
            )
        self.assertEqual(allowed["validator_status"], "no_finding")


class CliTests(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="deutschdna-cli-")
        self.home = self._temporary.name

    def tearDown(self):
        self._temporary.cleanup()

    def run_cli(self, *arguments: str) -> str:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = dna.main(["--home", self.home, *arguments])
        self.assertEqual(code, 0, buffer.getvalue())
        return buffer.getvalue()

    def test_cli_prints_utf8_even_on_legacy_console_encoding(self):
        environment = {**os.environ, "PYTHONIOENCODING": "ascii"}
        environment.pop("PYTHONUTF8", None)
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--home",
                self.home,
                "record",
                "--original",
                "Ich möchte mit mein Chef sprechen.",
                "--corrected",
                "Ich möchte mit meinem Chef sprechen.",
                "--category",
                "case",
                "--pattern",
                "mit + dative",
                "--rule",
                "mit + Dativ: mein → meinem",
            ],
            capture_output=True,
            env=environment,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8", "replace"))
        payload = json.loads(completed.stdout.decode("utf-8"))
        self.assertEqual(payload["status"], "recorded")
        self.assertEqual(payload["mistake"]["rule"], "mit + Dativ: mein → meinem")
        error = subprocess.run(
            [sys.executable, str(SCRIPT), "--home", self.home, "show", "m_fehlt_→"],
            capture_output=True,
            env=environment,
            check=False,
        )
        self.assertEqual(error.returncode, 2)
        self.assertIn("m_fehlt_→", error.stderr.decode("utf-8"))

    def test_text_renderers_and_json_commands(self):
        self.run_cli("init", "--name", "Ahmet", "--level", "B2", "--at", "2026-09-01T09:00:00Z")
        recorded = json.loads(
            self.run_cli(
                "record",
                "--original", "Ich spreche mit mein Chef.",
                "--corrected", "Ich spreche mit meinem Chef.",
                "--category", "case",
                "--pattern", "mit + dative",
                "--rule", "mit always governs dative",
                "--at", "2026-09-01T09:00:00Z",
            )
        )
        mistake_id = recorded["mistake"]["id"]
        self.assertEqual(recorded["recent"]["occurrences"], 1)
        summary = self.run_cli("summary", "--format", "text", "--at", "2026-09-02T09:00:00Z")
        self.assertIn("DeutschDNA · Ahmet · B2", summary)
        self.assertIn("Kasus", summary)
        self.assertIn("░", summary)
        recap = self.run_cli("recap", "--format", "text", "--at", "2026-09-02T09:00:00Z")
        self.assertIn("Willkommen zurück, Ahmet.", recap)
        self.assertIn("1 mistake due for review", recap)
        due = self.run_cli("due", "--format", "text", "--at", "2026-09-02T09:00:00Z")
        self.assertIn(mistake_id, due)
        self.assertIn("→", due)
        listing = self.run_cli("list", "--format", "text")
        self.assertIn("mit + dative", listing)
        empty = self.run_cli("list", "--status", "mastered", "--format", "text")
        self.assertEqual(empty.strip(), "No patterns match.")
        graded = json.loads(self.run_cli("grade", mistake_id, "--result", "pass", "--at", "2026-09-02T10:00:00Z"))
        self.assertEqual(graded["mistake"]["review_step"], 1)
        renamed = json.loads(self.run_cli("rename", mistake_id, "--rule", "mit governs the dative"))
        self.assertEqual(renamed["mistake"]["rule"], "mit governs the dative")
        timeline = self.run_cli("show", graded["mistake"]["id"], "--format", "text")
        self.assertIn("✗ wrote    Ich spreche mit mein Chef. → Ich spreche mit meinem Chef.", timeline)
        forgotten = json.loads(self.run_cli("forget", mistake_id))
        self.assertEqual(forgotten["status"], "forgotten")
        empty_summary = self.run_cli("summary", "--format", "text")
        self.assertIn("No mistakes recorded yet", empty_summary)

    def test_roleplay_finish_accepts_plural_and_repeated_mistake_flags(self):
        started = json.loads(self.run_cli("roleplay-start", "--scenario", "wohnung"))
        session_id = started["session"]["id"]
        finished = json.loads(
            self.run_cli("roleplay-finish", session_id, "--turns", "3", "--mistake-ids", "m_a", "m_b", "--mistake-id", "m_c")
        )
        self.assertEqual(finished["session"]["mistake_ids"], ["m_a", "m_b", "m_c"])

    def test_cli_error_returns_exit_code_two(self):
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = dna.main(["--home", self.home, "show", "m_missing"])
        self.assertEqual(code, 2)
        self.assertIn("Unknown mistake ID", buffer.getvalue())


class TimelineAndMigrationTests(StoreTestCase):
    def test_grade_answers_are_kept_and_rendered_in_the_timeline(self):
        mistake, _, _ = self.record_example()
        self.store.grade(mistake["id"], result="pass", answer="Ich fahre mit dem Bus.", at=BASE_TIME + timedelta(days=1))
        self.store.grade(mistake["id"], result="hard", answer="Ich wohne mit meiner Schwester.", at=BASE_TIME + timedelta(days=4))
        self.store.grade(
            mistake["id"],
            result="fail",
            answer="mit mein Freund",
            correction="mit meinem Freund",
            at=BASE_TIME + timedelta(days=5),
        )
        self.store.observe([mistake["id"]], context="mit unseren Kunden", at=BASE_TIME + timedelta(days=5, hours=2))
        stored = self.store.show(mistake["id"])
        self.assertEqual(stored["review_history"][0]["answer"], "Ich fahre mit dem Bus.")
        text = dna.render_show_text({"mistake": stored})
        self.assertIn("✗ wrote    Ich spreche mit mein Chef. → Ich spreche mit meinem Chef.", text)
        self.assertIn("✓ review   Ich fahre mit dem Bus.", text)
        self.assertIn("~ review   Ich wohne mit meiner Schwester. (after a hint)", text)
        self.assertIn("✗ review   mit mein Freund → mit meinem Freund", text)
        self.assertIn("✓ used     mit unseren Kunden", text)
        self.assertEqual(text.count("✗ review"), 1)
        self.assertIn("step 0/6", text)

    def test_timeline_shows_mastery_and_the_comeback(self):
        mistake, _, _ = self.record_example()
        review_time = BASE_TIME + timedelta(days=1)
        for _ in dna.REVIEW_INTERVALS:
            mistake, _ = self.store.grade(mistake["id"], result="pass", at=review_time)
            if mistake["next_review"]:
                review_time = dna.parse_moment(mistake["next_review"])
        mastered_text = dna.render_show_text({"mistake": mistake})
        self.assertIn("· mastered\n", mastered_text.splitlines()[0] + "\n")
        comeback = review_time + timedelta(days=3)
        self.record_example(original="Ich gehe mit mein Hund.", corrected="Ich gehe mit meinem Hund.", at=comeback)
        stored = self.store.show(mistake["id"])
        self.assertEqual(stored["previously_mastered_at"], dna.iso(review_time))
        text = dna.render_show_text({"mistake": stored})
        self.assertIn("★ mastered", text)
        self.assertIn("↺ came back after mastery", text)
        self.assertLess(text.index("★ mastered"), text.index("↺ came back after mastery"))

    def test_schema_one_state_is_migrated_and_resolves_by_pattern_key(self):
        legacy_id = "m_legacy000001"
        document = {
            "schema_version": 1,
            "mistakes": [
                {
                    "id": legacy_id,
                    "pattern": "mit + Dativ",
                    "pattern_key": "mit + dativ",
                    "category": "case",
                    "rule": "mit governs the dative",
                    "status": "active",
                    "occurrences": 1,
                    "review_step": 0,
                    "review_attempts": 0,
                    "review_failures": 0,
                    "consecutive_successes": 0,
                    "mastery_score": 0.0,
                    "first_seen": dna.iso(BASE_TIME),
                    "last_seen": dna.iso(BASE_TIME),
                    "next_review": dna.iso(BASE_TIME + timedelta(days=1)),
                    "examples": [
                        {
                            "original": "mit mein Chef",
                            "corrected": "mit meinem Chef",
                            "context": None,
                            "seen_at": dna.iso(BASE_TIME),
                            "event_id": None,
                        }
                    ],
                    "verification_history": [],
                }
            ],
        }
        self.store.ensure()
        (self.home / "mistakes.json").write_text(json.dumps(document), encoding="utf-8")
        mistake, status, extra = self.record_example(at=BASE_TIME + timedelta(days=2))
        self.assertEqual(mistake["id"], legacy_id)
        self.assertEqual(status, "updated")
        self.assertEqual(extra["resolved_by"], "pattern_key")
        stored = json.loads((self.home / "mistakes.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["schema_version"], dna.SCHEMA_VERSION)
        self.assertEqual(stored["mistakes"][0]["pattern_key"], "mit + dative")
        self.assertEqual(stored["mistakes"][0]["correct_uses"], 0)
        self.assertEqual(self.store.summary(at=BASE_TIME + timedelta(days=2))["total_patterns"], 1)

    def test_clusters_rank_breadth_before_depth(self):
        for index in range(4):
            self.record_example(
                category="agreement",
                pattern="adjective ending after ein-word",
                original=f"ein neue Job {index}",
                corrected=f"ein neuer Job {index}",
                at=BASE_TIME + timedelta(days=index),
            )
        self.record_example(
            category="agreement",
            pattern="adjective ending after der-word",
            original="den neue Film",
            corrected="den neuen Film",
            at=BASE_TIME - timedelta(days=60),
        )
        family = [
            ("warten auf + accusative", "Ich warte dich.", "Ich warte auf dich."),
            ("denken an + accusative", "Ich denke dich.", "Ich denke an dich."),
            ("sich freuen auf + accusative", "Ich freue mich über den Urlaub.", "Ich freue mich auf den Urlaub."),
        ]
        for index, (pattern, original, corrected) in enumerate(family):
            self.record_example(
                category="preposition",
                pattern=pattern,
                original=original,
                corrected=corrected,
                at=BASE_TIME + timedelta(days=index, hours=1),
            )
        summary = self.store.summary(at=BASE_TIME + timedelta(days=5))
        self.assertEqual([cluster["category"] for cluster in summary["clusters"]], ["preposition", "agreement"])
        self.assertEqual(summary["clusters"][0]["recent_patterns"], 3)
        self.assertEqual(summary["clusters"][1]["recent_patterns"], 1)
        text = dna.render_summary_text(summary)
        self.assertIn("Root cause: Präpositionen · 3 of 3 related patterns wrong in the last 30 days", text)
        self.assertIn("  → warten auf + accusative", text)
        self.assertIn("Also: Endungen · 1 of 2 related patterns wrong in the last 30 days", text)

    def test_demo_story_replays_through_the_engine(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import demo  # noqa: E402

        with tempfile.TemporaryDirectory(prefix="deutschdna-demo-test-") as directory:
            home = Path(directory)
            demo.seed(home)
            store = dna.StateStore(home)
            summary = store.summary()
            self.assertEqual(summary["total_patterns"], len(demo.PATTERNS))
            self.assertEqual(summary["clusters"][0]["category"], "preposition")
            mastered = {row["pattern"] for row in store.list(status="mastered")}
            self.assertIn("mit + dative", mastered)
            self.assertGreaterEqual(summary["due_now"], 1)
            recap = store.recap()
            self.assertIn("mit + dative", recap["mastered"])
            self.assertIn("warten auf + accusative", [row["pattern"] for row in store.recap()["recurring_patterns"]])


class UndoTests(StoreTestCase):
    def test_undo_reverts_a_recurrence_exactly(self):
        first, _, _ = self.record_example()
        before = self.store.show(first["id"])
        self.record_example(original="Ich fahre mit mein Auto.", corrected="Ich fahre mit meinem Auto.", at=BASE_TIME + timedelta(days=3))
        outcome = self.store.undo(first["id"])
        self.assertEqual(outcome["status"], "undone")
        self.assertEqual(outcome["undone"], "record")
        after = self.store.show(first["id"])
        self.assertEqual(after, {key: value for key, value in before.items() if key != "undo"})
        self.assertEqual(after["occurrences"], 1)
        self.assertNotIn("undo", after)
        with self.assertRaises(dna.DeutschDNAError):
            self.store.undo(first["id"])

    def test_undo_of_a_new_pattern_removes_it(self):
        first, _, _ = self.record_example()
        outcome = self.store.undo(first["id"])
        self.assertEqual(outcome["status"], "removed")
        self.assertEqual(self.store.list(status="all"), [])

    def test_undo_restores_the_schedule_after_a_disputed_failed_review(self):
        mistake, _, _ = self.record_example()
        passed, _ = self.store.grade(mistake["id"], result="pass", answer="Ich fahre mit dem Bus.", at=BASE_TIME + timedelta(days=1))
        failed, _ = self.store.grade(
            mistake["id"], result="fail", answer="mit mein Freund", correction="mit meinem Freund", at=BASE_TIME + timedelta(days=4)
        )
        self.assertEqual(failed["review_step"], 0)
        self.store.undo(mistake["id"])
        restored = self.store.show(mistake["id"])
        self.assertEqual(restored["review_step"], 1)
        self.assertEqual(restored["occurrences"], 1)
        self.assertEqual(restored["next_review"], passed["next_review"])
        self.assertEqual(len(restored["examples"]), 1)

    def test_undo_reverts_an_observation(self):
        mistake, _, _ = self.record_example()
        self.store.observe([mistake["id"]], context="mit meinem Team", at=BASE_TIME + timedelta(hours=5))
        self.store.undo(mistake["id"])
        self.assertEqual(self.store.show(mistake["id"])["correct_uses"], 0)

    def test_rename_and_merge_clear_the_undo_snapshot(self):
        mistake, _, _ = self.record_example()
        renamed = self.store.rename(mistake["id"], rule="mit governs the dative")["mistake"]
        with self.assertRaises(dna.DeutschDNAError):
            self.store.undo(renamed["id"])

    def test_cli_hides_the_snapshot_but_reports_that_undo_is_available(self):
        mistake, _, _ = self.record_example()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = dna.main(["--home", str(self.home), "show", mistake["id"]])
        self.assertEqual(code, 0)
        shown = json.loads(buffer.getvalue())["mistake"]
        self.assertNotIn("undo", shown)
        self.assertEqual(shown["undo_available"]["action"], "record")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = dna.main(["--home", str(self.home), "undo", mistake["id"]])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buffer.getvalue())["status"], "removed")


if __name__ == "__main__":
    unittest.main()
