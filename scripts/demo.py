#!/usr/bin/env python3
"""Replay a four-month learner story through the real DeutschDNA engine.

The story only scripts what the learner wrote and how each review went. When a
review happens is decided by the engine's own schedule, and every number in the
output is computed from the stored events. Nothing on screen is hard-coded.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deutsch_dna as dna  # noqa: E402


STORY_DAYS = 120
TICK = timedelta(minutes=3)

PATTERNS = {
    "mit": ("case", "mit + dative", "mit always governs the dative"),
    "warten": ("preposition", "warten auf + accusative", "warten takes auf + accusative"),
    "ung": ("article", "-ung nouns are feminine", "Nouns ending in -ung are feminine"),
    "interessieren": ("preposition", "sich interessieren für + accusative", "sich interessieren takes für + accusative"),
    "obwohl": ("word-order", "obwohl sends finite verb to end", "In an obwohl clause the finite verb goes last"),
    "helfen": ("case", "helfen + dative", "helfen takes a dative object"),
    "hund": ("case", "masculine accusative -en", "A masculine direct object needs -en: einen, keinen, meinen, den"),
    "freuen": ("preposition", "sich freuen auf + accusative", "sich freuen auf for something ahead, über for something here"),
    "adj": ("agreement", "adjective ending after ein-word", "After ein, kein, mein the adjective shows the gender: ein wichtiger Termin"),
    "personen": ("plural", "Person plural is Personen", "die Person, die Personen"),
    "anrufen": ("case", "anrufen + accusative", "anrufen takes an accusative object: Ich rufe dich an"),
    "adjdef": ("agreement", "adjective ending after der-word", "After der, die, das the adjective ends in -e or -en: den neuen Film"),
    "angst": ("preposition", "Angst haben vor + dative", "Angst haben takes vor + dative"),
    "weil": ("word-order", "weil sends finite verb to end", "In a weil clause the finite verb goes last"),
}

# What the learner wrote and its minimal correction: (days ago, pattern, sentence, correction).
WRITING = [
    (120, "mit", "Ich spreche mit mein Chef.", "Ich spreche mit meinem Chef."),
    (120, "warten", "Ich warte dich.", "Ich warte auf dich."),
    (118, "ung", "Ich habe ein Reservierung für zwei Personen.", "Ich habe eine Reservierung für zwei Personen."),
    (100, "interessieren", "Ich interessiere mich an Fußball.", "Ich interessiere mich für Fußball."),
    (80, "obwohl", "Obwohl ich bin müde, arbeite ich weiter.", "Obwohl ich müde bin, arbeite ich weiter."),
    (80, "helfen", "Ich helfe meinen Bruder.", "Ich helfe meinem Bruder."),
    (45, "hund", "Ich habe ein Hund.", "Ich habe einen Hund."),
    (45, "freuen", "Ich freue mich über das Wochenende.", "Ich freue mich auf das Wochenende."),
    (45, "adj", "Ich habe einen neue Job.", "Ich habe einen neuen Job."),
    (20, "interessieren", "Ich interessiere mich an Geschichte.", "Ich interessiere mich für Geschichte."),
    (15, "anrufen", "Ich rufe dir morgen an.", "Ich rufe dich morgen an."),
    (14, "personen", "Wir sind vier Person.", "Wir sind vier Personen."),
    (12, "freuen", "Ich freue mich über meinen Urlaub nächste Woche.", "Ich freue mich auf meinen Urlaub nächste Woche."),
    (10, "adjdef", "Ich mag den neue Film.", "Ich mag den neuen Film."),
    (4, "angst", "Ich habe Angst von Hunden.", "Ich habe Angst vor Hunden."),
    (2, "weil", "Ich bleibe zu Hause, weil ich bin krank.", "Ich bleibe zu Hause, weil ich krank bin."),
    (0, "warten", "Ich warte meine Freundin.", "Ich warte auf meine Freundin."),
    (0, "weil", "Ich nehme den Bus, weil es regnet stark.", "Ich nehme den Bus, weil es stark regnet."),
]

# How each review went, in order: ("pass", answer), ("hard", answer), ("fail", answer, correction).
# Reviews beyond the end of a list pass. Every review uses a new sentence.
REVIEWS = {
    "mit": [
        ("pass", "Ich arbeite mit meinem Kollegen."),
        ("pass", "Ich fahre mit dem Bus zur Arbeit."),
        ("pass", "Ich telefoniere mit meiner Mutter."),
        ("pass", "Wir essen mit unseren Nachbarn."),
        ("pass", "Ich spreche mit einem Kunden."),
        ("pass", "Ich bin mit dem Projekt zufrieden."),
    ],
    "warten": [
        ("pass", "Ich warte auf meinen Bruder."),
        ("fail", "Ich warte den Zug.", "Ich warte auf den Zug."),
        ("pass", "Wir warten auf das Paket."),
        ("hard", "Ich warte auf deine Antwort."),
        ("pass", "Sie wartet auf ihren Termin."),
        ("fail", "Wir warten den Bus.", "Wir warten auf den Bus."),
        ("pass", "Ich warte auf eine E-Mail."),
        ("pass", "Warte bitte auf mich!"),
        ("pass", "Er wartet auf den Arzt."),
        ("pass", "Wie lange wartest du schon auf mich?"),
        ("pass", "Wir warten auf besseres Wetter."),
    ],
    "helfen": [("pass", None), ("fail", "Ich helfe dich gern.", "Ich helfe dir gern.")],
    "freuen": [("pass", None)] * 5
    + [("fail", "Ich freue mich über die Party am Samstag.", "Ich freue mich auf die Party am Samstag.")],
    "adj": [
        ("pass", None),
        ("fail", "mit meinem neue Kollegen", "mit meinem neuen Kollegen"),
        ("pass", None),
        ("fail", "ein interessante Buch", "ein interessantes Buch"),
        ("pass", None),
        ("pass", None),
        ("fail", "Ich trinke einen kalte Kaffee.", "Ich trinke einen kalten Kaffee."),
        ("pass", None),
        ("pass", None),
        ("pass", None),
        ("fail", "Das ist ein wichtige Termin.", "Das ist ein wichtiger Termin."),
    ],
    "adjdef": [
        ("fail", "die neue Filme", "die neuen Filme"),
        ("pass", None),
        ("fail", "mit dem neue Auto", "mit dem neuen Auto"),
    ],
    "anrufen": [("pass", None), ("fail", "Ruf mir bitte an.", "Ruf mich bitte an.")],
}

# Correct, unprompted uses of tracked patterns in later writing.
OBSERVATIONS = [
    (6, "hund", "Wir haben einen Hund und eine Katze."),
    (4, "helfen", "Ich helfe dir gern beim Umzug."),
    (1, "mit", "mit unseren Kunden"),
]
ROLEPLAYS = [(2, "restaurant", 8, timedelta(minutes=6, seconds=42))]


class Clock:
    """Hands out increasing moments inside one story day."""

    def __init__(self, day_start: datetime):
        self.moment = day_start

    def next(self) -> datetime:
        current = self.moment
        self.moment += TICK
        return current


def seed(home: Path) -> None:
    store = dna.StateStore(home)
    anchor = dna.utc_now() - timedelta(hours=1)
    ids: dict[str, str] = {}
    keys_by_id: dict[str, str] = {}
    queues = {key: list(outcomes) for key, outcomes in REVIEWS.items()}
    store.init_profile(name="Ahmet", level="B2", native_language="tr", at=anchor - timedelta(days=STORY_DAYS, minutes=10))

    for days_ago in range(STORY_DAYS, -1, -1):
        day_start = anchor - timedelta(days=days_ago)
        clock = Clock(day_start)
        # Morning: whatever the engine says is due. Nothing is reviewed on the last day,
        # so the demo ends with reviews waiting, exactly as a learner would find it.
        if days_ago > 0:
            for mistake in store.due(at=day_start + timedelta(hours=1), limit=100):
                key = keys_by_id[mistake["id"]]
                outcome = queues[key].pop(0) if queues.get(key) else ("pass", None)
                if outcome[0] == "fail":
                    store.grade(mistake["id"], result="fail", answer=outcome[1], correction=outcome[2], at=clock.next())
                else:
                    store.grade(mistake["id"], result=outcome[0], answer=outcome[1], at=clock.next())
        for day, key, original, corrected in WRITING:
            if day != days_ago:
                continue
            category, pattern, rule = PATTERNS[key]
            mistake, _, _ = store.record(
                original=original,
                corrected=corrected,
                category=category,
                pattern=pattern,
                rule=rule,
                verification_status="verified",
                at=clock.next(),
            )
            ids[key] = mistake["id"]
            keys_by_id[mistake["id"]] = key
        for day, key, context in OBSERVATIONS:
            if day == days_ago:
                store.observe([ids[key]], context=context, at=clock.next())
        for day, scenario, turns, duration in ROLEPLAYS:
            if day == days_ago:
                started_at = clock.next()
                started = store.roleplay_start(scenario, at=started_at)
                store.roleplay_finish(
                    started["session"]["id"],
                    turns=turns,
                    notes="Reservation, order, one complaint, payment.",
                    at=started_at + duration,
                )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed and show a DeutschDNA demo profile")
    parser.add_argument("--home", help="State directory to seed (default: a fresh temporary directory)")
    parser.add_argument("--quiet", action="store_true", help="Only seed; print nothing but the state path")
    arguments = parser.parse_args(argv)
    dna._configure_streams()

    home = Path(arguments.home).expanduser() if arguments.home else Path(tempfile.mkdtemp(prefix="deutschdna-demo-"))
    if any(home.glob("*.json")):
        print(f"Refusing to seed a non-empty state directory: {home}", file=sys.stderr)
        return 2
    seed(home)
    if arguments.quiet:
        print(str(home))
        return 0

    mit_id = dna.mistake_id("case", "mit + dative")
    warten_id = dna.mistake_id("preposition", "warten auf + accusative")
    print("DeutschDNA demo: four months of one learner, replayed through the real engine.")
    print(f"State directory: {home}")
    screens = (
        ["recap", "--format", "card"],
        ["summary", "--format", "text"],
        ["show", mit_id, "--format", "text"],
        ["show", warten_id, "--format", "text"],
        ["due", "--format", "text"],
    )
    for command in screens:
        print()
        print(f"$ python scripts/deutsch_dna.py {' '.join(command)}")
        dna.main(["--home", str(home), *command])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
