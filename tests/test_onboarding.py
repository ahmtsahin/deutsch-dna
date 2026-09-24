from __future__ import annotations

import contextlib
import io
import json
from datetime import timedelta

from test_deutsch_dna import BASE_TIME, StoreTestCase, dna


class OnboardingTests(StoreTestCase):
    def test_empty_state_starts_with_welcome_without_requiring_profile_fields(self):
        recap = self.store.recap(at=BASE_TIME)
        self.assertEqual(recap["onboarding"]["stage"], "welcome")
        self.assertIsNone(recap["onboarding"]["explanation_language"])
        self.assertIsNone(recap["profile"]["name"])
        self.assertEqual(recap["profile"]["level"], "unspecified")
        self.assertEqual(recap["board"], [])
        self.assertFalse(recap["full_profile_due"])

    def test_welcome_and_starting_point_resume_without_counting_as_practice(self):
        self.store.init_profile(explanation_language="tr", welcome_shown=True, at=BASE_TIME)
        self.store = dna.StateStore(self.home)
        recap = self.store.recap(at=BASE_TIME + timedelta(minutes=1))
        self.assertEqual(recap["onboarding"]["stage"], "choose_start")
        self.assertEqual(recap["onboarding"]["explanation_language"], "tr")
        self.assertIsNone(recap["profile"]["native_language"])
        self.assertIsNone(recap["last_activity_at"])
        self.assertEqual(recap["streak_days"], 0)
        self.store.init_profile(starting_point="beginner", at=BASE_TIME + timedelta(minutes=2))
        self.store = dna.StateStore(self.home)
        resumed = self.store.recap(at=BASE_TIME + timedelta(days=1))
        self.assertEqual(resumed["onboarding"]["stage"], "first_practice")
        self.assertEqual(resumed["onboarding"]["starting_point"], "beginner")
        self.assertIsNone(resumed["last_activity_at"])

    def test_starting_preferences_never_become_cefr_scores(self):
        for preference in ("beginner", "some", "comfortable", "unsure"):
            with self.subTest(preference=preference):
                self.store.init_profile(starting_point=preference, at=BASE_TIME)
                recap = self.store.recap(at=BASE_TIME)
                self.assertEqual(recap["onboarding"]["stage"], "first_practice")
                self.assertEqual(recap["profile"]["level"], "unspecified")
                self.assertEqual(self.store.summary(at=BASE_TIME)["categories"], {})
        with self.assertRaises(dna.DeutschDNAError):
            self.store.init_profile(starting_point="B2", at=BASE_TIME)

    def test_explicit_cefr_level_skips_starting_point_question(self):
        self.store.init_profile(level="B2", at=BASE_TIME)
        recap = self.store.recap(at=BASE_TIME)
        self.assertEqual(recap["onboarding"]["stage"], "first_practice")
        self.assertIsNone(recap["profile"]["starting_point"])
        self.assertIsNone(recap["profile"]["name"])

    def test_a_correct_first_sentence_finishes_setup_without_a_fake_mistake(self):
        # The learner supplies a name using the starter; this is practice,
        # but not a reviewed pattern or an unaided mastery claim.
        self.store.init_profile(name="Mira", starting_point="beginner", onboarding_complete=True, at=BASE_TIME)
        self.store = dna.StateStore(self.home)
        recap = self.store.recap(at=BASE_TIME + timedelta(minutes=1))
        self.assertEqual(recap["onboarding"]["stage"], "complete")
        self.assertEqual(recap["last_activity_at"], dna.iso(BASE_TIME))
        self.assertEqual(recap["streak_days"], 1)
        self.assertEqual(recap["active_patterns"], 0)
        self.assertEqual(recap["mastered_total"], 0)
        self.assertEqual(recap["correct_uses"], 0)
        self.assertEqual(recap["reviews"]["total"], 0)
        self.assertEqual(self.store.list(), [])
        self.assertEqual(self.store.summary(at=BASE_TIME)["categories"], {})
        self.assertEqual(self.store.summary(at=BASE_TIME)["streak_days"], 1)
        self.assertFalse(self.store.recap(at=BASE_TIME + timedelta(days=10))["full_profile_due"])

    def test_flag_retries_preserve_timestamps_and_do_not_inflate_activity(self):
        first = self.store.init_profile(welcome_shown=True, explanation_language="tr", starting_point="some", at=BASE_TIME)
        completion = self.store.init_profile(onboarding_complete=True, at=BASE_TIME + timedelta(minutes=5))
        repeated = self.store.init_profile(welcome_shown=True, onboarding_complete=True, name="Lena", at=BASE_TIME + timedelta(days=3))
        self.assertEqual(repeated["welcome_shown_at"], first["welcome_shown_at"])
        self.assertEqual(repeated["onboarding_completed_at"], completion["onboarding_completed_at"])
        self.assertEqual(repeated["explanation_language"], "tr")
        self.assertEqual(repeated["starting_point"], "some")
        recap = self.store.recap(at=BASE_TIME + timedelta(days=3))
        self.assertEqual(recap["last_activity_at"], completion["onboarding_completed_at"])
        self.assertEqual(recap["streak_days"], 0)

    def test_explanation_preference_is_separate_from_native_language(self):
        self.store.init_profile(native_language="tr", at=BASE_TIME)
        self.assertEqual(self.store.recap(at=BASE_TIME)["onboarding"]["explanation_language"], "tr")
        self.store.init_profile(explanation_language="de", at=BASE_TIME)
        recap = self.store.recap(at=BASE_TIME)
        self.assertEqual(recap["onboarding"]["explanation_language"], "de")
        self.assertEqual(recap["profile"]["native_language"], "tr")
        self.store.init_profile(explanation_language="", at=BASE_TIME)
        self.assertEqual(self.store.recap(at=BASE_TIME)["onboarding"]["explanation_language"], "tr")

    def test_existing_history_is_not_forced_through_the_new_intro(self):
        self.record_example()
        recap = self.store.recap(at=BASE_TIME + timedelta(minutes=1))
        self.assertEqual(recap["onboarding"]["stage"], "complete")
        self.assertIsNone(recap["onboarding"]["completed_at_local"])
        self.assertTrue(recap["full_profile_due"])

    def test_first_automatic_profile_waits_for_a_week_and_further_activity(self):
        self.record_example()
        completed = BASE_TIME + timedelta(minutes=5)
        self.store.init_profile(onboarding_complete=True, at=completed)
        self.assertFalse(self.store.recap(at=BASE_TIME + timedelta(hours=1))["full_profile_due"])
        self.assertFalse(self.store.recap(at=BASE_TIME + timedelta(days=8))["full_profile_due"])
        self.record_example(original="Ich fahre mit mein Auto.", corrected="Ich fahre mit meinem Auto.", at=BASE_TIME + timedelta(days=8))
        self.assertTrue(self.store.recap(at=BASE_TIME + timedelta(days=8, minutes=1))["full_profile_due"])

    def test_cli_roundtrip_can_resume_and_complete_without_personal_setup(self):
        def cli(*args):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = dna.main(["--home", str(self.home), *args])
            self.assertEqual(code, 0)
            return json.loads(output.getvalue())

        cli("init", "--explanation-language", "tr", "--welcome-shown", "--at", "2026-09-10T12:00:00Z")
        cli("init", "--starting-point", "unsure", "--at", "2026-09-10T12:01:00Z")
        recap = cli("recap", "--at", "2026-09-10T12:02:00Z")
        self.assertEqual(recap["onboarding"]["stage"], "first_practice")
        self.assertIsNone(recap["profile"]["name"])
        cli("init", "--onboarding-complete", "--at", "2026-09-10T12:03:00Z")
        recap = cli("recap", "--at", "2026-09-10T12:04:00Z")
        self.assertEqual(recap["onboarding"]["stage"], "complete")
        self.assertEqual(recap["onboarding"]["completed_at_local"], "2026-09-10T12:03:00+00:00")
