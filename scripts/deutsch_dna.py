#!/usr/bin/env python3
"""DeutschDNA's dependency-free local mistake memory and review engine.

All learner state is plain JSON under one directory. Nothing leaves the machine
unless a remote validator endpoint is explicitly allowed.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


SCHEMA_VERSION = 2
REVIEW_INTERVALS = (1, 3, 7, 14, 30, 60)
RECENT_DAYS = 7
EXAMPLE_LIMIT = 12
HISTORY_LIMIT = 30
DUPLICATE_RECORD_WINDOW = timedelta(minutes=30)
DUPLICATE_EVENT_WINDOW = timedelta(minutes=5)
SIMILARITY_HINT_THRESHOLD = 0.72
CLUSTER_MIN_PATTERNS = 2
CLUSTER_MIN_OCCURRENCES = 3
WEAK_ACCURACY_THRESHOLD = 60
CLUSTER_WINDOW = timedelta(days=30)
TIMELINE_LIMIT = 16
FULL_PROFILE_INTERVAL_DAYS = 7
BOARD_ROWS = 5
LABEL_WIDTH = 36
LABEL_MAX_LENGTH = 60
WEEKDAYS_DE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
REVIEW_CONTEXT = "spaced-repetition review"
DEFAULT_LANGUAGETOOL_URL = "http://localhost:8081/v2/check"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

CATEGORY_ORDER = (
    "article",
    "case",
    "preposition",
    "word-order",
    "verb",
    "agreement",
    "plural",
    "spelling",
    "vocabulary",
    "register",
    "punctuation",
    "other",
)
CATEGORIES = frozenset(CATEGORY_ORDER)
# German display names for the human-readable profile; JSON keeps the English IDs.
CATEGORY_LABELS = {
    "article": "Artikel",
    "case": "Kasus",
    "preposition": "Präpositionen",
    "word-order": "Wortstellung",
    "verb": "Verben",
    "agreement": "Endungen",
    "plural": "Plural",
    "spelling": "Rechtschreibung",
    "vocabulary": "Wortschatz",
    "register": "Register",
    "punctuation": "Zeichensetzung",
    "other": "Sonstiges",
}
VERIFICATION_STATUSES = frozenset(
    {"verified", "supported", "no_finding", "uncertain", "unavailable", "not_checked"}
)
# Pattern keys are normalized so that German and English case names, common
# abbreviations, and "governs/takes" phrasings all land on the same key.
PATTERN_ALIASES = {
    "dativ": "dative",
    "dat": "dative",
    "akkusativ": "accusative",
    "akk": "accusative",
    "acc": "accusative",
    "accusativ": "accusative",
    "nominativ": "nominative",
    "nom": "nominative",
    "genitiv": "genitive",
    "gen": "genitive",
    "governs": "+",
    "takes": "+",
    "requires": "+",
    "needs": "+",
    "verlangt": "+",
    "regiert": "+",
}
DROPPED_PATTERN_TOKENS = frozenset({"case", "kasus", "the"})
SCENARIOS: dict[str, dict[str, Any]] = {
    "alltag": {
        "assistant_role": "a helpful neighbor",
        "setting": "A short everyday encounter in Germany",
        "opening": "Hallo! Wir haben uns lange nicht gesehen. Wie geht es dir?",
        "learner_goal": "Keep a natural everyday exchange going and ask one follow-up question.",
        "suggested_turns": 8,
    },
    "arbeit": {
        "assistant_role": "a colleague who needs a clear update",
        "setting": "A German workplace conversation",
        "opening": "Guten Morgen. Kannst du mir kurz sagen, wie der aktuelle Stand ist?",
        "learner_goal": "Explain a status, a problem, and the next step politely.",
        "suggested_turns": 8,
    },
    "arzt": {
        "assistant_role": "a doctor asking language-practice questions",
        "setting": "A fictional doctor's appointment for language practice only",
        "opening": "Guten Tag. Was kann ich heute für Sie tun?",
        "learner_goal": "Describe symptoms, duration, and intensity, then answer follow-up questions.",
        "suggested_turns": 8,
        "safety_note": "This is language practice, not medical advice or diagnosis.",
    },
    "wohnung": {
        "assistant_role": "a landlord or property manager",
        "setting": "A flat viewing or repair conversation",
        "opening": "Guten Tag. Möchten Sie zuerst die Wohnung besichtigen oder haben Sie eine Frage?",
        "learner_goal": "Ask precise questions and explain one housing need or problem.",
        "suggested_turns": 8,
    },
    "restaurant": {
        "assistant_role": "a waiter in a busy restaurant",
        "setting": "A restaurant visit from arrival to payment",
        "opening": "Guten Abend. Haben Sie reserviert?",
        "learner_goal": "Handle the reservation, order, one special request, and payment.",
        "suggested_turns": 8,
    },
}


class DeutschDNAError(Exception):
    """A user-facing CLI error."""


# --------------------------------------------------------------------------- time


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def parse_moment(value: str | None) -> datetime:
    if not value:
        return utc_now()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DeutschDNAError(f"Invalid ISO-8601 time: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def local_zone() -> timezone | None:
    """The learner's time zone: DEUTSCHDNA_UTC_OFFSET such as +02:00, or the system zone by default."""
    configured = os.environ.get("DEUTSCHDNA_UTC_OFFSET", "").strip()
    if not configured:
        return None
    match = re.fullmatch(r"([+-])(\d{1,2}):?(\d{2})", configured)
    if not match:
        raise DeutschDNAError(f"Invalid DEUTSCHDNA_UTC_OFFSET '{configured}'; use a form like +02:00")
    offset = timedelta(hours=int(match.group(2)), minutes=int(match.group(3)))
    return timezone(offset if match.group(1) == "+" else -offset)


def to_local(moment: datetime) -> datetime:
    """Stored times are UTC; everything shown to the learner is local."""
    zone = local_zone()
    return moment.astimezone(zone) if zone else moment.astimezone()


def local_date(moment: datetime) -> date:
    return to_local(moment).date()


def local_iso(stamp: str | None) -> str | None:
    parsed = _safe_moment(stamp)
    return to_local(parsed).isoformat() if parsed else None


def _safe_moment(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parse_moment(value)
    except DeutschDNAError:
        return None


def within(stamp: str | None, moment: datetime, window: timedelta) -> bool:
    parsed = _safe_moment(stamp)
    return parsed is not None and abs(parsed - moment) <= window


def streak_days(days: set[date], today: date) -> int:
    cursor = today if today in days else today - timedelta(days=1)
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


# --------------------------------------------------------------------------- keys


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).strip().lower())


def pattern_key(pattern: str) -> str:
    """Canonical key for a root-cause pattern; tolerant of casing, spacing, and German case names."""
    text = normalized(pattern)
    text = re.sub(r"\s*\+\s*", " + ", text)
    text = re.sub(r"[^\w+\s/-]", " ", text)
    tokens: list[str] = []
    for token in text.split():
        token = PATTERN_ALIASES.get(token, token)
        if not token or token in DROPPED_PATTERN_TOKENS:
            continue
        if token == "+" and tokens and tokens[-1] == "+":
            continue
        tokens.append(token)
    return " ".join(tokens).strip("+ ")


def compact_key(key: str) -> str:
    return re.sub(r"[^\w]", "", key)


def mistake_id_for(category: str, key: str) -> str:
    digest = hashlib.sha256(f"{category}\0{key}".encode("utf-8")).hexdigest()[:12]
    return f"m_{digest}"


def mistake_id(category: str, pattern: str) -> str:
    return mistake_id_for(category, pattern_key(pattern))


def auto_event_id(original: str, corrected: str) -> str:
    digest = hashlib.sha256(f"{normalized(original)}\0{normalized(corrected)}".encode("utf-8")).hexdigest()[:16]
    return f"auto_{digest}"


def category_rank(category: str) -> int:
    return CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else len(CATEGORY_ORDER)


# --------------------------------------------------------------------------- German labels

# German names for catalog keys that are not a plain "<word> + <case>" rule. Keys are
# normalized with pattern_key, so spelling variants of a key share one label.
_CATALOG_LABELS_RAW = {
    "-ung nouns are feminine": "-ung-Wörter sind feminin",
    "-heit/-keit nouns are feminine": "-heit/-keit sind feminin",
    "-chen/-lein nouns are neuter": "-chen/-lein sind neutral",
    "-ment/-um nouns are neuter": "-ment/-um sind meist neutral",
    "-ismus nouns are masculine": "-ismus ist maskulin",
    "nominalized infinitives are neuter": "das Essen, das Lernen",
    "no article before profession or nationality": "kein Artikel vor Berufen",
    "country names with article": "Länder mit Artikel",
    "two-way preposition: location takes dative": "Wo? → Dativ",
    "two-way preposition: direction takes accusative": "Wohin? → Akkusativ",
    "masculine accusative -en": "den/einen im Akkusativ",
    "n-declension nouns take -n/-en": "n-Deklination: dem Kunden",
    "dative plural -n": "Dativ Plural: -n",
    "predicate noun after sein takes nominative": "sein + Nominativ",
    "pronoun case after preposition": "mir/mich nach Präposition",
    "nach vs zu for destinations": "nach oder zu?",
    "in vs nach for countries": "in die Türkei, nach Deutschland",
    "seit vs vor": "seit oder vor?",
    "am/um/im for time expressions": "am/um/im bei Zeitangaben",
    "bei for at a person or company": "bei + Firma oder Person",
    "zu Hause vs nach Hause": "zu Hause oder nach Hause?",
    "finite verb in second position": "Verb an Position 2",
    "relative clause verb to end": "Relativsatz: Verb ans Ende",
    "separable prefix goes to clause end": "trennbares Präfix ans Ende",
    "past participle at clause end": "Partizip ans Satzende",
    "infinitive after modal at clause end": "Infinitiv ans Satzende",
    "time-manner-place order": "Zeit, Art, Ort",
    "nicht position": "Position von nicht",
    "coordinating conjunctions keep word order": "und/aber/denn: Verb bleibt",
    "adverb connectors trigger inversion": "deshalb/dann: Verb zuerst",
    "dative before accusative noun objects": "Dativ vor Akkusativ",
    "yes/no question verb first": "Ja/Nein-Frage: Verb zuerst",
    "sein as perfect auxiliary for motion and change": "Perfekt mit sein",
    "-ieren verbs take no ge-": "-ieren ohne ge-",
    "inseparable prefix verbs take no ge-": "be-/ver-/er- ohne ge-",
    "stem vowel change in du/er forms": "Vokalwechsel: du fährst",
    "modal verbs have no -t in 3rd person": "er kann, er muss",
    "infinitive with zu after non-modal verbs": "zu + Infinitiv",
    "Präteritum for sein/haben/modals": "war, hatte, konnte",
    "werden for future and passive": "werden: Futur und Passiv",
    "hätte/wäre/würde for polite and unreal": "hätte, wäre, würde",
    "adjective ending after der-word": "Adjektiv nach der/die/das",
    "adjective ending after ein-word": "Adjektiv nach ein/kein/mein",
    "adjective ending without article": "Adjektiv ohne Artikel",
    "possessive agrees with the possessed noun": "mein/meine: das Nomen zählt",
    "subject-verb agreement": "Subjekt und Verb",
    "der-word endings": "dieser, jeder, welcher",
    "-ung plural adds -en": "-ung → -ungen",
    "feminine -e plural adds -n": "-e → -en im Plural",
    "-in plural is -innen": "-in → -innen",
    "umlaut plural": "Plural mit Umlaut",
    "-s plural for loanwords": "-s-Plural: die Autos",
    "plural after numbers above one": "Plural nach Zahlen",
    "German nouns are capitalized": "Nomen großschreiben",
    "dass vs das": "dass oder das?",
    "ß after long vowel, ss after short": "ß oder ss?",
    "compound nouns are one word": "Komposita zusammenschreiben",
    "formal Sie is capitalized": "Sie großschreiben",
    "umlauts are written": "Umlaute schreiben",
    "kennen vs wissen": "kennen oder wissen?",
    "wenn vs als vs wann": "wenn, als oder wann?",
    "möchten vs mögen vs gern": "möchte, mag oder gern?",
    "bekommen means receive": "bekommen heißt erhalten",
    "eine Entscheidung treffen": "eine Entscheidung treffen",
    "einen Termin vereinbaren": "einen Termin vereinbaren",
    "lernen vs studieren": "lernen oder studieren?",
    "also means therefore": "also heißt deshalb",
    "Sie in formal exchanges": "Sie im formellen Kontext",
    "du/Sie consistency": "du und Sie nicht mischen",
    "formal email opening and closing": "formelle E-Mail",
    "comma before subordinate clause": "Komma vor Nebensatz",
    "comma before relative clause": "Komma vor Relativsatz",
    "comma before um/ohne/anstatt zu": "Komma vor um … zu",
}
CATALOG_LABELS = {pattern_key(key): label for key, label in _CATALOG_LABELS_RAW.items()}
CASE_NAMES_DE = {
    "dative": "Dativ", "dativ": "Dativ", "dat": "Dativ",
    "accusative": "Akkusativ", "akkusativ": "Akkusativ", "akk": "Akkusativ", "acc": "Akkusativ",
    "genitive": "Genitiv", "genitiv": "Genitiv", "gen": "Genitiv",
    "nominative": "Nominativ", "nominativ": "Nominativ", "nom": "Nominativ",
}
GENDERS_DE = {"masculine": "maskulin", "feminine": "feminin", "neuter": "neutral"}
_CASE_WORD = re.compile(r"\b(" + "|".join(CASE_NAMES_DE) + r")\b\.?", re.IGNORECASE)
_LABEL_RULES: tuple[tuple[re.Pattern[str], Callable[[re.Match[str]], str]], ...] = (
    (
        re.compile(r"^(?P<noun>.+?) is (?P<gender>masculine|feminine|neuter)$", re.IGNORECASE),
        lambda match: f"{match['noun']} ist {GENDERS_DE[match['gender'].lower()]}",
    ),
    (
        re.compile(r"^(?P<noun>.+?) plural is (?P<form>.+)$", re.IGNORECASE),
        lambda match: f"Plural von {match['noun']}: {match['form']}",
    ),
    (
        re.compile(r"^(?P<verb>.+?) past participle is (?P<form>.+)$", re.IGNORECASE),
        lambda match: f"{match['verb']}: Partizip {match['form']}",
    ),
    (
        re.compile(r"^(?P<verb>.+?) is reflexive$", re.IGNORECASE),
        lambda match: f"{match['verb']} (reflexiv)",
    ),
    (
        re.compile(r"^(?P<conj>\S+) sends (?:the )?finite verb to (?:the )?end$", re.IGNORECASE),
        lambda match: f"{match['conj']}: Verb ans Ende",
    ),
)


def _german_case_names(value: str) -> tuple[str, int]:
    return _CASE_WORD.subn(lambda match: CASE_NAMES_DE[match.group(1).lower()], value)


def display_label(mistake: dict[str, Any]) -> tuple[str, str]:
    """The German name shown to the learner, and its source: custom, catalog, rule, or key."""
    custom = (mistake.get("label") or "").strip()
    if custom:
        return custom, "custom"
    raw = (mistake.get("pattern") or "").strip()
    catalog = CATALOG_LABELS.get(mistake.get("pattern_key") or pattern_key(raw))
    if catalog:
        return catalog, "catalog"
    for rule, build in _LABEL_RULES:
        match = rule.match(raw)
        if match:
            return _german_case_names(build(match))[0], "rule"
    translated, found = _german_case_names(raw)
    return (translated, "rule") if found else (raw, "key")


def clean_label(label: str | None) -> str | None:
    if label is None:
        return None
    value = label.strip()
    if not value:
        raise DeutschDNAError("label must not be empty")
    if len(value) > LABEL_MAX_LENGTH:
        raise DeutschDNAError(f"label must be at most {LABEL_MAX_LENGTH} characters")
    return value


# --------------------------------------------------------------------------- scoring


def review_passes(mistake: dict[str, Any]) -> int:
    return sum(
        1
        for entry in mistake.get("review_history", [])
        if entry.get("result") == "pass" and entry.get("source", "review") == "review"
    )


def correct_total(mistake: dict[str, Any]) -> int:
    return int(mistake.get("correct_uses", 0)) + review_passes(mistake)


def evidence(mistake: dict[str, Any]) -> int:
    """How often the learner had a chance to show progress: graded reviews plus correct uses."""
    return int(mistake.get("review_attempts", 0)) + int(mistake.get("correct_uses", 0))


def example_view(example: dict[str, Any] | None) -> dict[str, Any] | None:
    if not example:
        return None
    return {
        "original": example.get("original"),
        "corrected": example.get("corrected"),
        "seen_at": example.get("seen_at"),
        "seen_at_local": local_iso(example.get("seen_at")),
        "context": example.get("context"),
    }


def accuracy_percent(correct: int, errors: int) -> int:
    """Laplace-smoothed share of correct productions among all tracked productions."""
    return round(100 * (correct + 1) / (correct + errors + 2))


def compact(mistake: dict[str, Any]) -> dict[str, Any]:
    occurrences = int(mistake.get("occurrences", 0))
    examples = mistake.get("examples") or []
    label, label_source = display_label(mistake)
    return {
        "id": mistake["id"],
        "pattern": mistake["pattern"],
        "label": label,
        "label_source": label_source,
        "category": mistake["category"],
        "status": mistake.get("status"),
        "rule": mistake.get("rule"),
        "occurrences": occurrences,
        "correct_uses": int(mistake.get("correct_uses", 0)),
        "right": correct_total(mistake),
        "accuracy_percent": accuracy_percent(correct_total(mistake), occurrences),
        "new": evidence(mistake) == 0,
        "review_step": int(mistake.get("review_step", 0)),
        "review_steps_total": len(REVIEW_INTERVALS),
        "next_review": mistake.get("next_review"),
        "next_review_local": local_iso(mistake.get("next_review")),
        "last_seen": mistake.get("last_seen"),
        "last_example": example_view(examples[-1]) if examples else None,
    }


def errors_between(mistake: dict[str, Any], start: datetime, end: datetime) -> int:
    count = 0
    for example in mistake.get("examples", []):
        seen = _safe_moment(example.get("seen_at"))
        if seen is not None and start < seen <= end:
            count += 1
    return count


def public(mistake: dict[str, Any]) -> dict[str, Any]:
    """The pattern as shown to callers: the undo snapshot is summarized, not dumped."""
    view = {key: value for key, value in mistake.items() if key != "undo"}
    view["label"], view["label_source"] = display_label(mistake)
    snapshot = mistake.get("undo")
    if snapshot:
        view["undo_available"] = {"action": snapshot.get("action"), "at": snapshot.get("at")}
    return view


def _snapshot(mistake: dict[str, Any], action: str, moment: datetime) -> None:
    """Keep one level of undo: the pattern exactly as it was before this change."""
    state = copy.deepcopy({key: value for key, value in mistake.items() if key != "undo"})
    mistake["undo"] = {"action": action, "at": iso(moment), "state": state}


def profile_view(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": profile.get("name"),
        "level": profile.get("level"),
        "native_language": profile.get("native_language"),
    }


def _event_moments(mistakes: list[dict[str, Any]], sessions: list[dict[str, Any]]) -> list[datetime]:
    stamps: list[str | None] = []
    for mistake in mistakes:
        stamps.extend(example.get("seen_at") for example in mistake.get("examples", []))
        stamps.extend(entry.get("reviewed_at") for entry in mistake.get("review_history", []))
        stamps.extend(entry.get("observed_at") for entry in mistake.get("correct_use_history", []))
    for session in sessions:
        stamps.append(session.get("started_at"))
        stamps.append(session.get("ended_at"))
    moments = []
    for stamp in stamps:
        parsed = _safe_moment(stamp)
        if parsed is not None:
            moments.append(parsed)
    return moments


def similar_patterns(mistakes: list[dict[str, Any]], key: str, *, exclude_id: str | None = None) -> list[dict[str, Any]]:
    target = compact_key(key)
    hits = []
    for mistake in mistakes:
        if mistake.get("id") == exclude_id:
            continue
        ratio = difflib.SequenceMatcher(None, target, compact_key(mistake.get("pattern_key", "")), autojunk=False).ratio()
        if ratio >= SIMILARITY_HINT_THRESHOLD:
            hits.append(
                {
                    "id": mistake["id"],
                    "pattern": mistake["pattern"],
                    "category": mistake["category"],
                    "similarity": round(ratio, 3),
                }
            )
    hits.sort(key=lambda item: (-item["similarity"], item["pattern"]))
    return hits[:3]


# --------------------------------------------------------------------------- storage


def default_home(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    configured = os.environ.get("DEUTSCHDNA_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".deutschdna"


def _read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return fallback
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeutschDNAError(f"Could not read valid JSON from {path}") from exc
    if not isinstance(value, dict):
        raise DeutschDNAError(f"Expected a JSON object in {path}")
    return value


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise DeutschDNAError(f"Could not create the state directory {path.parent}: {exc}") from exc
    temporary_path = path.parent / f"{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary_path.open("x", encoding="utf-8", newline="\n") as temporary:
            json.dump(value, temporary, ensure_ascii=False, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    except Exception as exc:
        try:
            temporary_path.unlink()
        except OSError:
            pass
        if isinstance(exc, DeutschDNAError):
            raise
        if isinstance(exc, OSError):
            raise DeutschDNAError(f"Could not write state file {path}: {exc}") from exc
        raise


def _migrate_mistakes(document: dict[str, Any]) -> dict[str, Any]:
    """Upgrade schema-1 state in memory; the next write persists it. IDs are kept."""
    try:
        version = int(document.get("schema_version") or 1)
    except (TypeError, ValueError):
        version = 1
    if version >= SCHEMA_VERSION:
        return document
    for mistake in document["mistakes"]:
        if isinstance(mistake.get("pattern"), str):
            mistake["pattern_key"] = pattern_key(mistake["pattern"]) or mistake.get("pattern_key", "")
        mistake.setdefault("correct_uses", 0)
        mistake.setdefault("last_correct_use", None)
        mistake.setdefault("mastered_at", None)
        for field in ("examples", "verification_history", "review_history", "correct_use_history", "aliases", "merged_from"):
            mistake.setdefault(field, [])
    document["schema_version"] = SCHEMA_VERSION
    return document


class StateStore:
    def __init__(self, home: Path):
        self.home = home
        self.profile_path = home / "profile.json"
        self.mistakes_path = home / "mistakes.json"
        self.sessions_path = home / "sessions.json"

    # ---- documents

    def ensure(self) -> None:
        try:
            self.home.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DeutschDNAError(f"Could not create the state directory {self.home}: {exc}") from exc
        if not self.profile_path.exists():
            _atomic_write(
                self.profile_path,
                {
                    "schema_version": SCHEMA_VERSION,
                    "name": None,
                    "native_language": None,
                    "level": "unspecified",
                    "created_at": iso(utc_now()),
                    "updated_at": iso(utc_now()),
                },
            )
        if not self.mistakes_path.exists():
            _atomic_write(self.mistakes_path, {"schema_version": SCHEMA_VERSION, "mistakes": []})
        if not self.sessions_path.exists():
            _atomic_write(self.sessions_path, {"schema_version": SCHEMA_VERSION, "sessions": []})

    def _profile(self) -> dict[str, Any]:
        self.ensure()
        return _read_json(self.profile_path, {})

    def _mistake_document(self) -> dict[str, Any]:
        self.ensure()
        document = _read_json(self.mistakes_path, {"schema_version": SCHEMA_VERSION, "mistakes": []})
        if not isinstance(document.get("mistakes"), list):
            raise DeutschDNAError(f"Expected a mistakes list in {self.mistakes_path}")
        return _migrate_mistakes(document)

    def _session_document(self) -> dict[str, Any]:
        self.ensure()
        document = _read_json(self.sessions_path, {"schema_version": SCHEMA_VERSION, "sessions": []})
        if not isinstance(document.get("sessions"), list):
            raise DeutschDNAError(f"Expected a sessions list in {self.sessions_path}")
        return document

    @staticmethod
    def _find(mistakes: list[dict[str, Any]], identifier: str) -> dict[str, Any] | None:
        return next((item for item in mistakes if item.get("id") == identifier), None)

    def _require(self, mistakes: list[dict[str, Any]], identifier: str) -> dict[str, Any]:
        mistake = self._find(mistakes, identifier)
        if not mistake:
            raise DeutschDNAError(f"Unknown mistake ID: {identifier}")
        return mistake

    @staticmethod
    def _resolve(
        mistakes: list[dict[str, Any]], category: str, pattern: str
    ) -> tuple[dict[str, Any] | None, str | None]:
        key = pattern_key(pattern)
        if not key:
            raise DeutschDNAError("pattern must contain letters or digits")
        exact = StateStore._find(mistakes, mistake_id_for(category, key))
        if exact:
            return exact, "id"
        for mistake in mistakes:
            if mistake.get("pattern_key") == key:
                return mistake, "pattern_key"
        for mistake in mistakes:
            for alias in mistake.get("aliases", []):
                if alias.get("pattern_key") == key:
                    return mistake, "alias"
        return None, None

    def _replace_session_ids(self, old_id: str, new_id: str | None) -> None:
        document = self._session_document()
        changed = False
        for session in document["sessions"]:
            ids = session.get("mistake_ids") or []
            if old_id not in ids:
                continue
            replaced = [new_id if item == old_id else item for item in ids]
            session["mistake_ids"] = list(dict.fromkeys(item for item in replaced if item))
            changed = True
        if changed:
            _atomic_write(self.sessions_path, document)

    # ---- profile

    def init_profile(
        self,
        *,
        name: str | None = None,
        native_language: str | None = None,
        level: str | None = None,
        at: datetime | None = None,
    ) -> dict[str, Any]:
        moment = at or utc_now()
        profile_was_missing = not self.profile_path.exists()
        self.ensure()
        profile = _read_json(self.profile_path, {})
        if profile_was_missing:
            profile["created_at"] = iso(moment)
        for key, value in (("name", name), ("native_language", native_language), ("level", level)):
            if value is not None:
                profile[key] = value
        profile["updated_at"] = iso(moment)
        _atomic_write(self.profile_path, profile)
        return profile

    def mark_profile_shown(self, *, at: datetime | None = None) -> None:
        """Remember when the learner last saw the full profile card, for the weekly Wochenbilanz."""
        profile = self._profile()
        profile["last_full_profile_at"] = iso(at or utc_now())
        _atomic_write(self.profile_path, profile)

    # ---- recording

    def record(
        self,
        *,
        original: str,
        corrected: str,
        category: str | None = None,
        pattern: str | None = None,
        rule: str | None = None,
        mistake_id: str | None = None,
        context: str | None = None,
        verification_status: str = "not_checked",
        at: datetime | None = None,
        event_id: str | None = None,
        label: str | None = None,
    ) -> tuple[dict[str, Any], str, dict[str, Any]]:
        label = clean_label(label)
        if verification_status not in VERIFICATION_STATUSES:
            raise DeutschDNAError(f"Unknown verification status '{verification_status}'")
        if not original.strip() or not corrected.strip():
            raise DeutschDNAError("original and corrected must not be empty")
        moment = at or utc_now()
        document = self._mistake_document()
        mistakes = document["mistakes"]
        resolved_by: str | None = None

        if mistake_id:
            existing: dict[str, Any] | None = self._require(mistakes, mistake_id)
            resolved_by = "mistake_id"
        else:
            if not (category and pattern and rule) or not pattern.strip() or not rule.strip():
                raise DeutschDNAError("Provide --mistake-id, or --category, --pattern, and --rule")
            if category not in CATEGORIES:
                raise DeutschDNAError(f"Unknown category '{category}'. Choose from: {', '.join(CATEGORY_ORDER)}")
            existing, resolved_by = self._resolve(mistakes, category, pattern)

        effective_event_id = event_id or auto_event_id(original, corrected)
        if existing:
            for example in existing.get("examples", []):
                if example.get("event_id") != effective_event_id:
                    continue
                if event_id or within(example.get("seen_at"), moment, DUPLICATE_RECORD_WINDOW):
                    return existing, "duplicate", {"resolved_by": resolved_by}

        example = {
            "original": original.strip(),
            "corrected": corrected.strip(),
            "context": context,
            "seen_at": iso(moment),
            "event_id": effective_event_id,
        }
        verification_event = {"status": verification_status, "checked_at": iso(moment)}
        extra: dict[str, Any] = {"resolved_by": resolved_by}

        if existing:
            earlier = existing.get("examples") or []
            extra["previous"] = {
                "last_seen": existing.get("last_seen"),
                "review_step": int(existing.get("review_step", 0)),
                "status": existing.get("status"),
                "occurrences": int(existing.get("occurrences", 0)),
                "first_example": example_view(earlier[0] if earlier else None),
                "last_example": example_view(earlier[-1] if earlier else None),
            }
            was_mastered = existing.get("status") == "mastered"
            _snapshot(existing, "record", moment)
            existing["occurrences"] = int(existing.get("occurrences", 1)) + 1
            existing["last_seen"] = iso(moment)
            if rule and rule.strip():
                existing["rule"] = rule.strip()
            if label:
                existing["label"] = label
            existing["status"] = "active"
            existing["review_step"] = 0
            existing["consecutive_successes"] = 0
            existing["mastery_score"] = 0.0
            existing["next_review"] = iso(moment + timedelta(days=REVIEW_INTERVALS[0]))
            if was_mastered:
                existing["reactivated_at"] = iso(moment)
                existing["previously_mastered_at"] = existing.get("mastered_at")
                existing["mastered_at"] = None
            existing.setdefault("examples", []).append(example)
            existing["examples"] = existing["examples"][-EXAMPLE_LIMIT:]
            existing.setdefault("verification_history", []).append(verification_event)
            existing["verification_history"] = existing["verification_history"][-HISTORY_LIMIT:]
            status = "updated"
            mistake = existing
        else:
            assert category and pattern and rule
            key = pattern_key(pattern)
            mistake = {
                "id": mistake_id_for(category, key),
                "pattern": pattern.strip(),
                "pattern_key": key,
                "category": category,
                "rule": rule.strip(),
                "status": "active",
                "occurrences": 1,
                "correct_uses": 0,
                "review_step": 0,
                "review_attempts": 0,
                "review_failures": 0,
                "consecutive_successes": 0,
                "mastery_score": 0.0,
                "first_seen": iso(moment),
                "last_seen": iso(moment),
                "last_reviewed": None,
                "last_correct_use": None,
                "next_review": iso(moment + timedelta(days=REVIEW_INTERVALS[0])),
                "mastered_at": None,
                "examples": [example],
                "verification_history": [verification_event],
                "review_history": [],
                "correct_use_history": [],
                "aliases": [],
                "merged_from": [],
                "undo": {"action": "record", "at": iso(moment), "state": None},
                "label": label,
            }
            mistakes.append(mistake)
            status = "recorded"
            extra["similar_patterns"] = similar_patterns(mistakes, key, exclude_id=mistake["id"])

        extra["recent_occurrences"] = sum(
            1 for item in mistake.get("examples", []) if within(item.get("seen_at"), moment, timedelta(days=RECENT_DAYS))
        )
        _atomic_write(self.mistakes_path, document)
        return mistake, status, extra

    def observe(
        self,
        identifiers: list[str],
        *,
        context: str | None = None,
        at: datetime | None = None,
    ) -> list[dict[str, Any]]:
        moment = at or utc_now()
        document = self._mistake_document()
        mistakes = document["mistakes"]
        results = []
        for identifier in dict.fromkeys(identifiers):
            mistake = self._require(mistakes, identifier)
            history = mistake.setdefault("correct_use_history", [])
            duplicate = any(
                entry.get("context") == context and within(entry.get("observed_at"), moment, DUPLICATE_EVENT_WINDOW)
                for entry in history
            )
            if duplicate:
                results.append({"id": mistake["id"], "pattern": mistake["pattern"], "status": "duplicate"})
                continue
            _snapshot(mistake, "observe", moment)
            mistake["correct_uses"] = int(mistake.get("correct_uses", 0)) + 1
            history.append({"observed_at": iso(moment), "context": context})
            mistake["correct_use_history"] = history[-HISTORY_LIMIT:]
            mistake["last_correct_use"] = iso(moment)
            status = "observed"
            next_review = _safe_moment(mistake.get("next_review"))
            if mistake.get("status") == "active" and next_review is not None and next_review <= moment:
                self._apply_pass(mistake, moment, source="observed")
                status = "observed_and_advanced"
            results.append(
                {
                    "id": mistake["id"],
                    "pattern": mistake["pattern"],
                    "status": status,
                    "correct_uses": mistake["correct_uses"],
                    "review_step": mistake.get("review_step", 0),
                    "next_review": mistake.get("next_review"),
                    "mastered": mistake.get("status") == "mastered",
                    "last_mistake": example_view((mistake.get("examples") or [None])[-1]),
                }
            )
        _atomic_write(self.mistakes_path, document)
        return results

    # ---- reviewing

    def due(self, *, at: datetime | None = None, limit: int = 5) -> list[dict[str, Any]]:
        moment = at or utc_now()
        document = self._mistake_document()
        due_items = []
        for mistake in document["mistakes"]:
            next_review = mistake.get("next_review")
            if mistake.get("status") != "active" or not next_review:
                continue
            if parse_moment(next_review) <= moment:
                due_items.append(mistake)
        due_items.sort(key=lambda item: (item.get("next_review", ""), -int(item.get("occurrences", 0))))
        return due_items[: max(0, limit)]

    @staticmethod
    def _apply_pass(mistake: dict[str, Any], moment: datetime, *, source: str, answer: str | None = None) -> None:
        step = int(mistake.get("review_step", 0)) + 1
        mistake["review_step"] = step
        mistake["consecutive_successes"] = int(mistake.get("consecutive_successes", 0)) + 1
        mistake["mastery_score"] = round(min(1.0, step / len(REVIEW_INTERVALS)), 3)
        if step >= len(REVIEW_INTERVALS):
            mistake["status"] = "mastered"
            mistake["next_review"] = None
            mistake["mastered_at"] = iso(moment)
        else:
            mistake["status"] = "active"
            mistake["next_review"] = iso(moment + timedelta(days=REVIEW_INTERVALS[step]))
        mistake["last_reviewed"] = iso(moment)
        entry = {"result": "pass", "reviewed_at": iso(moment), "source": source}
        if answer:
            entry["answer"] = answer
        mistake.setdefault("review_history", []).append(entry)
        mistake["review_history"] = mistake["review_history"][-HISTORY_LIMIT:]

    def grade(
        self,
        identifier: str,
        *,
        result: str,
        answer: str | None = None,
        correction: str | None = None,
        at: datetime | None = None,
    ) -> tuple[dict[str, Any], str]:
        if result not in {"pass", "hard", "fail"}:
            raise DeutschDNAError("result must be pass, hard, or fail")
        moment = at or utc_now()
        document = self._mistake_document()
        mistake = self._require(document["mistakes"], identifier)

        history = mistake.get("review_history") or []
        last = history[-1] if history else None
        if (
            last
            and last.get("result") == result
            and last.get("source", "review") == "review"
            and within(last.get("reviewed_at"), moment, DUPLICATE_EVENT_WINDOW)
        ):
            return mistake, "duplicate"

        _snapshot(mistake, "grade", moment)
        mistake["review_attempts"] = int(mistake.get("review_attempts", 0)) + 1
        clean_answer = answer.strip() if answer and answer.strip() else None
        if result == "pass":
            self._apply_pass(mistake, moment, source="review", answer=clean_answer)
        else:
            if result == "hard":
                mistake["status"] = "active"
                mistake["consecutive_successes"] = 0
                mistake["next_review"] = iso(moment + timedelta(days=1))
            else:
                if mistake.get("status") == "mastered":
                    mistake["reactivated_at"] = iso(moment)
                    mistake["previously_mastered_at"] = mistake.get("mastered_at")
                    mistake["mastered_at"] = None
                mistake["occurrences"] = int(mistake.get("occurrences", 1)) + 1
                mistake["review_failures"] = int(mistake.get("review_failures", 0)) + 1
                mistake["review_step"] = 0
                mistake["consecutive_successes"] = 0
                mistake["mastery_score"] = 0.0
                mistake["status"] = "active"
                mistake["last_seen"] = iso(moment)
                mistake["next_review"] = iso(moment + timedelta(days=REVIEW_INTERVALS[0]))
                mistake.setdefault("examples", []).append(
                    {
                        "original": clean_answer,
                        "corrected": correction.strip() if correction else None,
                        "context": REVIEW_CONTEXT,
                        "seen_at": iso(moment),
                        "event_id": None,
                    }
                )
                mistake["examples"] = mistake["examples"][-EXAMPLE_LIMIT:]
            mistake["last_reviewed"] = iso(moment)
            entry = {"result": result, "reviewed_at": iso(moment), "source": "review"}
            if clean_answer:
                entry["answer"] = clean_answer
            mistake.setdefault("review_history", []).append(entry)
            mistake["review_history"] = mistake["review_history"][-HISTORY_LIMIT:]

        _atomic_write(self.mistakes_path, document)
        return mistake, "graded"

    # ---- inspection and repair

    def list(self, *, status: str = "active", category: str | None = None) -> list[dict[str, Any]]:
        if status not in {"active", "mastered", "all"}:
            raise DeutschDNAError("status must be active, mastered, or all")
        if category is not None and category not in CATEGORIES:
            raise DeutschDNAError(f"Unknown category '{category}'. Choose from: {', '.join(CATEGORY_ORDER)}")
        rows = [
            compact(mistake)
            for mistake in self._mistake_document()["mistakes"]
            if (status == "all" or mistake.get("status") == status)
            and (category is None or mistake.get("category") == category)
        ]
        rows.sort(key=lambda row: (category_rank(row["category"]), -row["occurrences"], row["pattern"]))
        return rows

    def show(self, identifier: str) -> dict[str, Any]:
        return self._require(self._mistake_document()["mistakes"], identifier)

    def forget(self, identifier: str) -> dict[str, Any]:
        document = self._mistake_document()
        mistake = self._require(document["mistakes"], identifier)
        document["mistakes"] = [item for item in document["mistakes"] if item.get("id") != identifier]
        _atomic_write(self.mistakes_path, document)
        self._replace_session_ids(identifier, None)
        return mistake

    def undo(self, identifier: str) -> dict[str, Any]:
        """Revert the most recent record, grade, or observe on one pattern. One level deep."""
        document = self._mistake_document()
        mistakes = document["mistakes"]
        mistake = self._require(mistakes, identifier)
        snapshot = mistake.get("undo")
        if not snapshot:
            raise DeutschDNAError(
                f"Nothing to undo for {identifier}: only the latest record, grade, or observe can be undone"
            )
        undone = {"undone": snapshot.get("action"), "undone_at": snapshot.get("at")}
        if snapshot.get("state") is None:
            document["mistakes"] = [item for item in mistakes if item.get("id") != identifier]
            _atomic_write(self.mistakes_path, document)
            self._replace_session_ids(identifier, None)
            return {"status": "removed", **undone, "mistake": public(mistake)}
        restored = snapshot["state"]
        mistakes[mistakes.index(mistake)] = restored
        _atomic_write(self.mistakes_path, document)
        return {"status": "undone", **undone, "mistake": public(restored)}

    def merge(self, source_id: str, target_id: str, *, at: datetime | None = None) -> dict[str, Any]:
        if source_id == target_id:
            raise DeutschDNAError("source and target must be different mistake IDs")
        moment = at or utc_now()
        document = self._mistake_document()
        mistakes = document["mistakes"]
        source = self._require(mistakes, source_id)
        target = self._require(mistakes, target_id)

        target["occurrences"] = int(target.get("occurrences", 0)) + int(source.get("occurrences", 0))
        for field in ("correct_uses", "review_attempts", "review_failures"):
            target[field] = int(target.get(field, 0)) + int(source.get(field, 0))
        for field, stamp, limit in (
            ("examples", "seen_at", EXAMPLE_LIMIT),
            ("verification_history", "checked_at", HISTORY_LIMIT),
            ("review_history", "reviewed_at", HISTORY_LIMIT),
            ("correct_use_history", "observed_at", HISTORY_LIMIT),
        ):
            combined = list(target.get(field, [])) + list(source.get(field, []))
            combined.sort(key=lambda item: item.get(stamp) or "")
            target[field] = combined[-limit:]
        first_seen = [value for value in (target.get("first_seen"), source.get("first_seen")) if value]
        last_seen = [value for value in (target.get("last_seen"), source.get("last_seen")) if value]
        if first_seen:
            target["first_seen"] = min(first_seen)
        if last_seen:
            target["last_seen"] = max(last_seen)
        if "active" in (target.get("status"), source.get("status")):
            step = min(int(target.get("review_step", 0)), int(source.get("review_step", 0)))
            target["status"] = "active"
            target["review_step"] = step
            target["consecutive_successes"] = min(
                int(target.get("consecutive_successes", 0)), int(source.get("consecutive_successes", 0))
            )
            target["mastery_score"] = round(min(1.0, step / len(REVIEW_INTERVALS)), 3)
            candidates = [value for value in (target.get("next_review"), source.get("next_review")) if value]
            target["next_review"] = min(candidates) if candidates else iso(moment + timedelta(days=REVIEW_INTERVALS[0]))
            target["mastered_at"] = None
        aliases = list(target.get("aliases", []))
        for alias in [{"category": source["category"], "pattern_key": source["pattern_key"]}] + list(source.get("aliases", [])):
            if alias not in aliases:
                aliases.append(alias)
        target["aliases"] = aliases
        target.pop("undo", None)
        target.setdefault("merged_from", []).append(
            {"id": source["id"], "pattern": source["pattern"], "category": source["category"], "merged_at": iso(moment)}
        )
        document["mistakes"] = [item for item in mistakes if item.get("id") != source_id]
        _atomic_write(self.mistakes_path, document)
        self._replace_session_ids(source_id, target_id)
        return target

    def rename(
        self,
        identifier: str,
        *,
        pattern: str | None = None,
        category: str | None = None,
        rule: str | None = None,
        label: str | None = None,
    ) -> dict[str, Any]:
        if pattern is None and category is None and rule is None and label is None:
            raise DeutschDNAError("Provide --pattern, --category, --rule, or --label")
        label = clean_label(label)
        document = self._mistake_document()
        mistakes = document["mistakes"]
        mistake = self._require(mistakes, identifier)
        if category is not None and category not in CATEGORIES:
            raise DeutschDNAError(f"Unknown category '{category}'. Choose from: {', '.join(CATEGORY_ORDER)}")
        if pattern is not None and not pattern.strip():
            raise DeutschDNAError("pattern must not be empty")
        if rule is not None and not rule.strip():
            raise DeutschDNAError("rule must not be empty")

        new_category = category or mistake["category"]
        new_pattern = pattern.strip() if pattern else mistake["pattern"]
        new_key = pattern_key(new_pattern)
        if not new_key:
            raise DeutschDNAError("pattern must contain letters or digits")
        new_id = mistake_id_for(new_category, new_key)
        previous_id = mistake["id"]
        if new_id != previous_id:
            clash = self._find(mistakes, new_id) or next(
                (item for item in mistakes if item is not mistake and item.get("pattern_key") == new_key), None
            )
            if clash:
                raise DeutschDNAError(
                    f"'{new_pattern}' already exists as {clash['id']}; run: merge {previous_id} {clash['id']}"
                )
        if (new_category, new_key) != (mistake["category"], mistake.get("pattern_key")):
            aliases = [
                alias
                for alias in mistake.get("aliases", [])
                if not (alias.get("category") == new_category and alias.get("pattern_key") == new_key)
            ]
            old_alias = {"category": mistake["category"], "pattern_key": mistake.get("pattern_key")}
            if old_alias not in aliases:
                aliases.append(old_alias)
            mistake["aliases"] = aliases
        mistake.update({"id": new_id, "pattern": new_pattern, "pattern_key": new_key, "category": new_category})
        mistake.pop("undo", None)
        if rule is not None:
            mistake["rule"] = rule.strip()
        if label is not None:
            mistake["label"] = label
        _atomic_write(self.mistakes_path, document)
        if new_id != previous_id:
            self._replace_session_ids(previous_id, new_id)
        return {"previous_id": previous_id, "mistake": mistake}

    # ---- reporting

    def summary(self, *, at: datetime | None = None) -> dict[str, Any]:
        moment = at or utc_now()
        profile = self._profile()
        mistakes = self._mistake_document()["mistakes"]
        sessions = self._session_document()["sessions"]

        categories: dict[str, dict[str, Any]] = {}
        for mistake in mistakes:
            bucket = categories.setdefault(
                mistake["category"],
                {
                    "patterns": 0,
                    "active": 0,
                    "mastered": 0,
                    "errors": 0,
                    "correct": 0,
                    "evidence": 0,
                    "due": 0,
                    "mastery_total": 0.0,
                },
            )
            is_active = mistake.get("status") == "active"
            next_review = _safe_moment(mistake.get("next_review"))
            bucket["patterns"] += 1
            bucket["active"] += int(is_active)
            bucket["mastered"] += int(mistake.get("status") == "mastered")
            bucket["errors"] += int(mistake.get("occurrences", 0))
            bucket["correct"] += correct_total(mistake)
            bucket["evidence"] += evidence(mistake)
            bucket["due"] += int(is_active and next_review is not None and next_review <= moment)
            bucket["mastery_total"] += float(mistake.get("mastery_score", 0.0))
        for bucket in categories.values():
            bucket["accuracy_percent"] = accuracy_percent(bucket["correct"], bucket["errors"])
            bucket["mastery_percent"] = round(100 * bucket.pop("mastery_total") / max(1, bucket["patterns"]))
            # Without a single review or correct use there is nothing to measure yet.
            bucket["new"] = bucket["evidence"] == 0
            bucket["weak"] = (
                not bucket["new"] and bucket["accuracy_percent"] < WEAK_ACCURACY_THRESHOLD and bucket["errors"] >= 2
            )

        # A cluster is a family of related patterns that keep failing. Breadth (how many
        # different members failed recently) outranks depth: many members failing means the
        # learner is missing the rule, not one word.
        window_start = moment - CLUSTER_WINDOW
        clusters = []
        for category in categories:
            active = [item for item in mistakes if item["category"] == category and item.get("status") == "active"]
            occurrences = sum(int(item.get("occurrences", 0)) for item in active)
            if len(active) < CLUSTER_MIN_PATTERNS or occurrences < CLUSTER_MIN_OCCURRENCES:
                continue
            recent = {item["id"]: errors_between(item, window_start, moment) for item in active}
            active.sort(key=lambda item: (-recent[item["id"]], -int(item.get("occurrences", 0)), item["pattern"]))
            clusters.append(
                {
                    "category": category,
                    "patterns": [item["pattern"] for item in active],
                    "labels": [display_label(item)[0] for item in active],
                    "pattern_ids": [item["id"] for item in active],
                    "occurrences": occurrences,
                    "recent_errors": sum(recent.values()),
                    "recent_patterns": sum(1 for value in recent.values() if value),
                }
            )
        clusters.sort(
            key=lambda cluster: (
                -cluster["recent_patterns"],
                -cluster["recent_errors"],
                -cluster["occurrences"],
                category_rank(cluster["category"]),
            )
        )

        active_rows = [compact(item) for item in mistakes if item.get("status") == "active"]
        weakest = sorted(active_rows, key=lambda row: (row["accuracy_percent"], -row["occurrences"], row["pattern"]))[:5]
        due_rows = [compact(item) for item in self.due(at=moment, limit=len(mistakes))]
        moments = [value for value in _event_moments(mistakes, sessions) if value <= moment]
        days = {local_date(value) for value in moments}
        today = local_date(moment)
        return {
            "as_of": iso(moment),
            "profile": profile_view(profile),
            "total_patterns": len(mistakes),
            "active_patterns": len(active_rows),
            "mastered_patterns": sum(item.get("status") == "mastered" for item in mistakes),
            "errors_total": sum(int(item.get("occurrences", 0)) for item in mistakes),
            "correct_total": sum(correct_total(item) for item in mistakes),
            "due_now": len(due_rows),
            "streak_days": streak_days(days, today),
            "active_days_last_30": sum(1 for day in days if 0 <= (today - day).days < 30),
            "last_activity_at": iso(max(moments)) if moments else None,
            "categories": categories,
            "clusters": clusters,
            "cluster_window_days": CLUSTER_WINDOW.days,
            "recent_errors_total": sum(errors_between(item, window_start, moment) for item in mistakes),
            "weakest_patterns": weakest,
            "due_patterns": due_rows[:5],
        }

    def recap(self, *, days: int = RECENT_DAYS, at: datetime | None = None) -> dict[str, Any]:
        moment = at or utc_now()
        window = max(1, days)
        since = moment - timedelta(days=window)
        profile = self._profile()
        mistakes = self._mistake_document()["mistakes"]
        sessions = self._session_document()["sessions"]

        def in_window(stamp: str | None) -> bool:
            parsed = _safe_moment(stamp)
            return parsed is not None and since < parsed <= moment

        new_patterns: list[str] = []
        recurring: list[dict[str, Any]] = []
        errors_total = 0
        recurrences = 0
        reviews = {"total": 0, "pass": 0, "hard": 0, "fail": 0}
        observed = 0
        mastered: list[str] = []
        mastered_labels: list[str] = []
        for mistake in mistakes:
            examples_in = sum(1 for example in mistake.get("examples", []) if in_window(example.get("seen_at")))
            is_new = in_window(mistake.get("first_seen"))
            if is_new:
                new_patterns.append(mistake["pattern"])
            errors_total += examples_in
            repeat_count = examples_in - (1 if is_new and examples_in else 0)
            recurrences += repeat_count
            if repeat_count:
                recurring.append(
                    {
                        "id": mistake["id"],
                        "pattern": mistake["pattern"],
                        "label": display_label(mistake)[0],
                        "category": mistake["category"],
                        "count": examples_in,
                        "last_seen": mistake.get("last_seen"),
                    }
                )
            for entry in mistake.get("review_history", []):
                if entry.get("source", "review") != "review" or not in_window(entry.get("reviewed_at")):
                    continue
                reviews["total"] += 1
                reviews[entry.get("result", "pass")] = reviews.get(entry.get("result", "pass"), 0) + 1
            observed += sum(1 for entry in mistake.get("correct_use_history", []) if in_window(entry.get("observed_at")))
            if mistake.get("status") == "mastered" and in_window(mistake.get("mastered_at")):
                mastered.append(mistake["pattern"])
                mastered_labels.append(display_label(mistake)[0])
        recurring.sort(key=lambda row: row["last_seen"] or "", reverse=True)
        recurring.sort(key=lambda row: -row["count"])

        roleplays = [
            session
            for session in sessions
            if session.get("type", "roleplay") == "roleplay" and in_window(session.get("started_at"))
        ]
        due_rows = [compact(item) for item in self.due(at=moment, limit=len(mistakes))]
        moments = [value for value in _event_moments(mistakes, sessions) if value <= moment]
        last = max(moments) if moments else None
        day_set = {local_date(value) for value in moments}
        active_rows = [compact(item) for item in mistakes if item.get("status") == "active"]
        weakest = sorted(active_rows, key=lambda row: (row["accuracy_percent"], -row["occurrences"], row["pattern"]))
        next_focus = due_rows[0] if due_rows else (weakest[0] if weakest else None)
        upcoming = sorted(
            parsed
            for parsed in (_safe_moment(item.get("next_review")) for item in mistakes if item.get("status") == "active")
            if parsed is not None and parsed > moment
        )
        later_today = [value for value in upcoming if local_date(value) == local_date(moment)]
        schedule = {
            "due_now": len(due_rows),
            "later_today": len(later_today),
            "later_today_first_local": to_local(later_today[0]).isoformat() if later_today else None,
            "next_local": to_local(upcoming[0]).isoformat() if upcoming else None,
        }
        shown = _safe_moment(profile.get("last_full_profile_at"))
        full_profile_due = last is not None and (
            shown is None
            or (moment - shown >= timedelta(days=FULL_PROFILE_INTERVAL_DAYS) and last > shown)
        )
        recurring_ids = {row["id"] for row in recurring}
        due_ids = {row["id"] for row in due_rows}
        ranked = sorted(
            active_rows,
            key=lambda row: (row["id"] not in due_ids, -row["occurrences"], row["next_review"] or "~", row["label"]),
        )
        board = [
            {**row, "due": row["id"] in due_ids, "came_back": row["id"] in recurring_ids}
            for row in ranked[:BOARD_ROWS]
        ]
        result = {
            "as_of": iso(moment),
            "window_days": window,
            "since": iso(since),
            "profile": profile_view(profile),
            "last_activity_at": iso(last) if last else None,
            "last_activity_local": to_local(last).isoformat() if last else None,
            "days_since_last_activity": (local_date(moment) - local_date(last)).days if last else None,
            "streak_days": streak_days(day_set, local_date(moment)),
            "errors": {"total": errors_total, "new_patterns": len(new_patterns), "recurrences": recurrences},
            "new_patterns": new_patterns,
            "recurring_patterns": recurring[:5],
            "recurring_total": len(recurring),
            "reviews": reviews,
            "correct_uses": observed,
            "mastered": mastered,
            "mastered_labels": mastered_labels,
            "roleplays": {"count": len(roleplays), "scenarios": [session.get("scenario") for session in roleplays]},
            "due_now": len(due_rows),
            "due_patterns": due_rows[:5],
            "next_focus": next_focus,
            "active_patterns": len(active_rows),
            "mastered_total": sum(item.get("status") == "mastered" for item in mistakes),
            "schedule": schedule,
            "full_profile_due": full_profile_due,
            "board": board,
            "board_more": max(0, len(ranked) - len(board)),
        }
        result["card"] = render_recap_card(result)
        return result

    # ---- roleplay

    def roleplay_start(
        self,
        scenario: str,
        *,
        focus: str | None = None,
        at: datetime | None = None,
    ) -> dict[str, Any]:
        if scenario not in SCENARIOS:
            raise DeutschDNAError(f"Unknown scenario '{scenario}'. Choose from: {', '.join(sorted(SCENARIOS))}")
        moment = at or utc_now()
        document = self._session_document()
        session = {
            "id": f"s_{uuid.uuid4().hex[:12]}",
            "type": "roleplay",
            "scenario": scenario,
            "focus": focus,
            "status": "active",
            "started_at": iso(moment),
            "ended_at": None,
            "turns": None,
            "duration_seconds": None,
            "mistake_ids": [],
            "notes": None,
        }
        document["sessions"].append(session)
        _atomic_write(self.sessions_path, document)
        return {
            "session": session,
            "contract": {
                **SCENARIOS[scenario],
                "feedback_policy": "Stay in character; defer ordinary corrections; give at most three in the debrief.",
                "focus": focus,
            },
        }

    def roleplay_finish(
        self,
        identifier: str,
        *,
        turns: int,
        duration_seconds: int | None = None,
        mistake_ids: list[str] | None = None,
        notes: str | None = None,
        at: datetime | None = None,
    ) -> dict[str, Any]:
        moment = at or utc_now()
        document = self._session_document()
        session = next((item for item in document["sessions"] if item.get("id") == identifier), None)
        if not session:
            raise DeutschDNAError(f"Unknown session ID: {identifier}")
        if session.get("status") == "complete":
            return session
        started = _safe_moment(session.get("started_at"))
        if duration_seconds is None and started is not None:
            duration_seconds = max(0, int((moment - started).total_seconds()))
        session.update(
            {
                "status": "complete",
                "ended_at": iso(moment),
                "turns": max(0, turns),
                "duration_seconds": max(0, duration_seconds) if duration_seconds is not None else None,
                "mistake_ids": list(dict.fromkeys(mistake_ids or [])),
                "notes": notes,
            }
        )
        _atomic_write(self.sessions_path, document)
        return session


# --------------------------------------------------------------------------- correction analysis


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)


def analyze_correction(original: str, corrected: str) -> dict[str, Any]:
    before = tokenize(original)
    after = tokenize(corrected)
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    changes = []
    changed_before = 0
    changed_after = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        changed_before += i2 - i1
        changed_after += j2 - j1
        changes.append(
            {
                "operation": tag,
                "original_tokens": before[i1:i2],
                "corrected_tokens": after[j1:j2],
            }
        )
    denominator = max(1, len(before), len(after))
    edit_ratio = round(max(changed_before, changed_after) / denominator, 3)
    similarity = round(matcher.ratio(), 3)
    minimality_status = "minimal" if edit_ratio <= 0.35 and similarity >= 0.65 else "possible_rewrite"
    return {
        "original_tokens": len(before),
        "corrected_tokens": len(after),
        "changed_token_ratio": edit_ratio,
        "similarity": similarity,
        "minimality_status": minimality_status,
        "changes": changes,
    }


def is_local_endpoint(endpoint: str) -> bool:
    try:
        host = urllib.parse.urlparse(endpoint).hostname
    except ValueError:
        return False
    return bool(host) and (host in LOCAL_HOSTS or host.endswith(".localhost"))


def _language_tool_check(endpoint: str, text: str, language: str, timeout: float) -> dict[str, Any]:
    payload = urllib.parse.urlencode({"text": text, "language": language}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "DeutschDNA/1.1"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
    matches = result.get("matches", [])
    if not isinstance(matches, list):
        raise DeutschDNAError("LanguageTool returned an invalid matches value")
    return {
        "count": len(matches),
        "matches": [
            {
                "message": item.get("message"),
                "offset": item.get("offset"),
                "length": item.get("length"),
                "rule_id": (item.get("rule") or {}).get("id"),
                "replacements": [replacement.get("value") for replacement in item.get("replacements", [])[:3]],
            }
            for item in matches
        ],
    }


def verify_correction(
    original: str,
    corrected: str,
    *,
    endpoint: str,
    language: str = "de-DE",
    timeout: float = 2.5,
    allow_remote: bool = False,
) -> dict[str, Any]:
    analysis = analyze_correction(original, corrected)
    if not is_local_endpoint(endpoint) and not allow_remote:
        return {
            "validator_status": "unavailable",
            "validator": "LanguageTool",
            "endpoint": endpoint,
            "reason": (
                "Remote validator endpoint blocked so learner text stays on this machine. "
                "Pass --allow-remote or set DEUTSCHDNA_ALLOW_REMOTE_VALIDATOR=1 to opt in."
            ),
            "analysis": analysis,
        }
    try:
        original_check = _language_tool_check(endpoint, original, language, timeout)
        corrected_check = _language_tool_check(endpoint, corrected, language, timeout)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError, DeutschDNAError) as exc:
        return {
            "validator_status": "unavailable",
            "validator": "LanguageTool",
            "endpoint": endpoint,
            "reason": str(exc),
            "analysis": analysis,
        }

    original_rules = {match["rule_id"] for match in original_check["matches"] if match["rule_id"]}
    corrected_rules = {match["rule_id"] for match in corrected_check["matches"] if match["rule_id"]}
    new_rules = sorted(corrected_rules - original_rules)
    resolved_rules = sorted(original_rules - corrected_rules)
    changed_fragments = {
        normalized(" ".join(change["corrected_tokens"]))
        for change in analysis["changes"]
        if change["corrected_tokens"]
    }
    suggested_replacements = {
        normalized(replacement)
        for match in original_check["matches"]
        for replacement in match["replacements"]
        if replacement
    }
    replacement_supported = any(
        suggestion == fragment or suggestion in fragment or fragment in suggestion
        for suggestion in suggested_replacements
        for fragment in changed_fragments
    )
    if original_check["count"] > 0 and corrected_check["count"] == 0 and replacement_supported:
        status = "verified"
    elif original_check["count"] > corrected_check["count"] and not new_rules:
        status = "supported"
    elif original_check["count"] == 0:
        status = "no_finding"
    else:
        status = "uncertain"
    return {
        "validator_status": status,
        "validator": "LanguageTool",
        "endpoint": endpoint,
        "original": original_check,
        "corrected": corrected_check,
        "resolved_rule_ids": resolved_rules,
        "new_rule_ids": new_rules,
        "replacement_supported": replacement_supported,
        "analysis": analysis,
    }


# --------------------------------------------------------------------------- text rendering


def render_bar(percent: int, width: int = 10) -> str:
    filled = max(0, min(width, round(width * percent / 100)))
    return "█" * filled + "░" * (width - filled)


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    return f"{count} {singular if count == 1 else (plural or singular + 's')}"


def _display_name(profile: dict[str, Any]) -> str:
    return profile.get("name") or "Learner"


def _label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category)


def _join_limited(items: list[str], limit: int, total: int | None = None) -> str:
    shown = " · ".join(items[:limit])
    hidden = (len(items) if total is None else total) - min(limit, len(items))
    if hidden > 0:
        shown += f" · +{hidden} more"
    return shown


def _cluster_detail(cluster: dict[str, Any], recent_total: int) -> str:
    recent_errors = cluster.get("recent_errors", 0)
    if recent_errors and recent_total:
        return (
            f"{recent_errors} of your {recent_total} mistakes in {CLUSTER_WINDOW.days} days · "
            f"{_plural(cluster.get('recent_patterns', 0), 'related pattern')}"
        )
    return f"{_plural(len(cluster['patterns']), 'related pattern')} · {_plural(cluster['occurrences'], 'error')}"


def _score(accuracy: int, is_new: bool) -> str:
    """Fixed-width score column: a bar with a percentage, or "neu" when nothing is measured yet."""
    return "neu".ljust(15) if is_new else f"{render_bar(accuracy)} {accuracy:>3}%"


def render_summary_text(summary: dict[str, Any]) -> str:
    profile = summary["profile"]
    level = profile.get("level")
    title = f"DeutschDNA · {_display_name(profile)}"
    if level and level != "unspecified":
        title += f" · {level}"
    lines = [
        title,
        (
            f"{_plural(summary['total_patterns'], 'pattern')} · {summary['mastered_patterns']} mastered · "
            f"{summary['errors_total']} wrong · {summary['correct_total']} right · "
            f"streak {_plural(summary['streak_days'], 'day')} · {summary['due_now']} due"
        ),
        "",
    ]
    categories = summary["categories"]
    if not categories:
        lines.append("No mistakes recorded yet. Your DNA forms as you write.")
        return "\n".join(lines)
    for category in sorted(categories, key=category_rank):
        bucket = categories[category]
        line = (
            f"{_label(category):<16}{_score(bucket['accuracy_percent'], bucket.get('new', False))}   "
            f"{_plural(bucket['patterns'], 'pattern'):<10} · {bucket['mastered']} mastered · "
            f"{bucket['errors']} wrong · {bucket['correct']} right"
        )
        if bucket["weak"]:
            line += "   ← weak"
        lines.append(line)
    clusters = summary["clusters"]
    recent_total = summary.get("recent_errors_total", 0)
    if clusters:
        top = clusters[0]
        lines.append("")
        lines.append(f"Root cause: {_label(top['category'])} · {_cluster_detail(top, recent_total)}")
        for name in top.get("labels", top["patterns"])[:4]:
            lines.append(f"  → {name}")
        if len(top["patterns"]) > 4:
            lines.append(f"  → +{len(top['patterns']) - 4} more")
        for cluster in clusters[1:2]:
            lines.append(f"Also: {_label(cluster['category'])} · {_cluster_detail(cluster, recent_total)}")
    weakest = [row for row in summary["weakest_patterns"] if not row.get("new")][:3]
    if weakest:
        lines.append("")
        lines.append("Weakest patterns")
        width = max(len(row["label"]) for row in weakest)
        for row in weakest:
            lines.append(
                f"  {row['label']:<{width}}  {row['accuracy_percent']:>3}%  "
                f"{row['occurrences']} wrong · {row['right']} right · step {row['review_step']}/{row['review_steps_total']}"
            )
    if summary["due_patterns"]:
        names = [row["label"] for row in summary["due_patterns"]]
        lines.append("")
        lines.append("Due now: " + _join_limited(names, 3, summary["due_now"]))
    return "\n".join(lines)


def render_recap_text(recap: dict[str, Any]) -> str:
    name = _display_name(recap["profile"])
    gap = recap["days_since_last_activity"]
    if gap is None:
        return f"Willkommen, {name}.\nNo history yet. Write a few sentences in German and your DeutschDNA starts forming."
    when = "today" if gap == 0 else ("yesterday" if gap == 1 else f"{gap} days ago")
    errors = recap["errors"]
    reviews = recap["reviews"]
    lines = [
        f"Willkommen zurück, {name}.",
        f"Last practice: {when} · streak {_plural(recap['streak_days'], 'day')}",
        (
            f"Last {recap['window_days']} days: {_plural(errors['total'], 'mistake')} "
            f"({errors['new_patterns']} new, {errors['recurrences']} repeated) · "
            f"{_plural(reviews['total'], 'review')} ({reviews['pass']} passed) · "
            f"{_plural(recap['correct_uses'], 'correct use')} · {_plural(recap['roleplays']['count'], 'roleplay')}"
        ),
    ]
    if recap["recurring_patterns"]:
        names = [
            row.get("label", row["pattern"]) + (f" ×{row['count']}" if row["count"] > 1 else "")
            for row in recap["recurring_patterns"]
        ]
        lines.append("Came back: " + _join_limited(names, 2, recap.get("recurring_total")))
    if recap["mastered"]:
        lines.append("Mastered: " + _join_limited(recap.get("mastered_labels") or recap["mastered"], 3))
    if recap["due_now"]:
        lines.append(f"{_plural(recap['due_now'], 'mistake')} due for review · 5-minute challenge?")
    elif recap["next_focus"]:
        lines.append(f"Nothing due. Weakest right now: {recap['next_focus']['label']}")
    return "\n".join(lines)


def _fit(value: str, width: int) -> str:
    return value if len(value) <= width else value[: width - 1] + "…"


def _ladder(step: int) -> str:
    filled = max(0, min(step, len(REVIEW_INTERVALS)))
    return "▰" * filled + "▱" * (len(REVIEW_INTERVALS) - filled)


def _when_due(row: dict[str, Any], now_local: datetime) -> str:
    if row.get("due"):
        return "jetzt fällig"
    stamp = row.get("next_review_local")
    if not stamp:
        return "-"
    moment = datetime.fromisoformat(stamp)
    days = (moment.date() - now_local.date()).days
    if days <= 0:
        return f"heute {moment:%H:%M}"
    if days == 1:
        return f"morgen {moment:%H:%M}"
    if days < 7:
        return f"{WEEKDAYS_DE[moment.weekday()]} {moment:%H:%M}"
    return f"{moment:%d.%m.}"


def render_recap_card(recap: dict[str, Any]) -> str:
    """The session header and a board of the patterns in progress. Every value comes from the recap."""
    profile = recap["profile"]
    head = ["DeutschDNA", _display_name(profile)]
    level = profile.get("level")
    if level and level != "unspecified":
        head.append(level)
    if recap.get("last_activity_at") is None:
        return " · ".join(head) + "\nNoch keine Einträge. Schreib ein paar Sätze auf Deutsch, dann entsteht deine DNA."
    streak = recap["streak_days"]
    if streak:
        head.append(f"{streak} {'Tag' if streak == 1 else 'Tage'} in Folge")
    else:
        head.append(f"zuletzt vor {recap['days_since_last_activity']} Tagen")
    total = recap["active_patterns"] + recap["mastered_total"]
    head.append(f"{recap['mastered_total']} von {total} gemeistert")
    lines = [" · ".join(head)]
    board = recap.get("board") or []
    if board:
        now_local = to_local(parse_moment(recap["as_of"]))
        width = min(LABEL_WIDTH, max(len(row["label"]) for row in board))
        lines.append("")
        for row in board:
            wrong = f"{row['occurrences']}× falsch" + (" ↺" if row.get("came_back") else "")
            lines.append(
                f"{_fit(row['label'], width):<{width}}  {_ladder(row['review_step'])} "
                f"{row['review_step']}/{row['review_steps_total']}   {wrong:<11}   {_when_due(row, now_local)}"
            )
        if recap.get("board_more"):
            lines.append(f"+{recap['board_more']} weitere")
    elif recap["mastered_total"]:
        lines.append("")
        lines.append("Alles gemeistert ★ Schreib etwas Neues, dann suche ich die nächste Baustelle.")
    return "\n".join(lines)


def render_due_text(result: dict[str, Any]) -> str:
    if not result["mistakes"]:
        return "Nothing due right now."
    lines = [f"Due now: {result['count']}"]
    for index, mistake in enumerate(result["mistakes"], start=1):
        row = compact(mistake)
        lines.append(f"{index}. {row['label']}  [{row['category']}]  {row['id']}")
        lines.append(f"   Rule: {row['rule']}")
        example = row["last_example"]
        if example and example.get("original"):
            lines.append(f"   Last: {example['original']} → {example.get('corrected') or '?'}")
        lines.append(
            f"   {row['occurrences']} wrong · {row['right']} right · step {row['review_step']}/{row['review_steps_total']}"
        )
    return "\n".join(lines)


def render_list_text(result: dict[str, Any]) -> str:
    rows = result["mistakes"]
    if not rows:
        return "No patterns match."
    header = f"{'ID':<15}{'STATUS':<10}{'CATEGORY':<13}{'PATTERN':<42}{'WRONG':>6}{'RIGHT':>6}  {'STEP':<5} {'NEXT':<10}"
    lines = [header]
    for row in rows:
        pattern = row["pattern"] if len(row["pattern"]) <= 40 else row["pattern"][:39] + "…"
        next_review = (row.get("next_review_local") or "")[:10] or "-"
        lines.append(
            f"{row['id']:<15}{row['status']:<10}{row['category']:<13}{pattern:<42}"
            f"{row['occurrences']:>6}{row['right']:>6}  {row['review_step']}/{row['review_steps_total']:<3} {next_review:<10}"
        )
    return "\n".join(lines)


def render_show_text(result: dict[str, Any]) -> str:
    """The journey of one pattern: first mistake, every review, real-life use, mastery."""
    mistake = result["mistake"]
    row = compact(mistake)
    mastered = mistake.get("status") == "mastered"
    lines = [
        f"{row['label']} · {_label(mistake['category'])} · {'mastered' if mastered else 'learning'}",
        f"Rule: {mistake.get('rule')}",
        "",
    ]
    events: list[tuple[str, int, str]] = []
    failed_review_stamps = set()
    for example in mistake.get("examples", []):
        stamp = example.get("seen_at") or ""
        original, corrected = example.get("original"), example.get("corrected")
        pair = f"{original} → {corrected or '?'}" if original else ""
        if example.get("context") == REVIEW_CONTEXT:
            failed_review_stamps.add(stamp)
            events.append((stamp, 0, f"✗ review   {pair}".rstrip()))
        else:
            events.append((stamp, 0, f"✗ wrote    {pair}".rstrip()))
    for entry in mistake.get("review_history", []):
        if entry.get("source", "review") != "review":
            continue
        stamp = entry.get("reviewed_at") or ""
        answer = entry.get("answer") or ""
        outcome = entry.get("result")
        if outcome == "pass":
            events.append((stamp, 1, f"✓ review   {answer or 'passed'}"))
        elif outcome == "hard":
            events.append((stamp, 1, f"~ review   {answer + ' ' if answer else ''}(after a hint)"))
        elif outcome == "fail" and stamp not in failed_review_stamps:
            events.append((stamp, 1, "✗ review   failed"))
    for entry in mistake.get("correct_use_history", []):
        events.append((entry.get("observed_at") or "", 2, f"✓ used     {entry.get('context') or 'correctly, unprompted'}"))
    for field, marker in (
        ("previously_mastered_at", "★ mastered"),
        ("mastered_at", "★ mastered"),
        ("reactivated_at", "↺ came back after mastery"),
    ):
        if mistake.get(field):
            events.append((mistake[field], 3, marker))
    events.sort(key=lambda item: (item[0], item[1]))
    hidden = max(0, len(events) - TIMELINE_LIMIT)
    if hidden:
        lines.append(f"… {_plural(hidden, 'earlier event')}")
    for stamp, _, text in events[hidden:]:
        lines.append(f"{(local_iso(stamp) or stamp)[:10]}  {text}")
    progress = "mastered" if mastered else f"step {row['review_step']}/{row['review_steps_total']}"
    score = "neu" if row["new"] else f"{render_bar(row['accuracy_percent'])} {row['accuracy_percent']}%"
    lines.append("")
    lines.append(f"{score} · {row['occurrences']} wrong · {row['right']} right · {progress}")
    return "\n".join(lines)


TEXT_RENDERERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "summary": render_summary_text,
    "recap": render_recap_text,
    "due": render_due_text,
    "list": render_list_text,
    "show": render_show_text,
}
CARD_RENDERERS: dict[str, Callable[[dict[str, Any]], str]] = {"recap": render_recap_card}


# --------------------------------------------------------------------------- CLI


def _configure_streams() -> None:
    """Force UTF-8 output so JSON never crashes on legacy Windows console code pages."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


def _print_json(value: Any, *, stream: Any = None) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), file=stream or sys.stdout)


def _add_format(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("json", "text"), default="json", help="json for agents, text for humans")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DeutschDNA local mistake memory and review engine")
    parser.add_argument("--home", help="State directory; overrides DEUTSCHDNA_HOME")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create or update the learner profile")
    init_parser.add_argument("--name")
    init_parser.add_argument("--native-language")
    init_parser.add_argument("--level")
    init_parser.add_argument("--at", help="ISO-8601 time, primarily for deterministic integrations")

    record_parser = subparsers.add_parser("record", help="Record or recur a root-cause mistake pattern")
    record_parser.add_argument("--original", required=True)
    record_parser.add_argument("--corrected", required=True)
    record_parser.add_argument("--mistake-id", help="Recur an existing pattern by ID instead of naming it")
    record_parser.add_argument("--category", choices=CATEGORY_ORDER)
    record_parser.add_argument("--pattern", help="Stable root-cause key, e.g. 'mit + dative'")
    record_parser.add_argument("--rule", help="One-line rule the learner should remember")
    record_parser.add_argument("--label", help="Short German name shown to the learner, e.g. 'hätte gern (höflich)'")
    record_parser.add_argument("--context")
    record_parser.add_argument("--verification-status", default="not_checked", choices=sorted(VERIFICATION_STATUSES))
    record_parser.add_argument("--event-id", help="Idempotency key; identical calls without one are deduplicated for 30 minutes")
    record_parser.add_argument("--at", help="ISO-8601 event time")

    observe_parser = subparsers.add_parser("observe", help="Log a correct, unprompted use of tracked patterns")
    observe_parser.add_argument("mistake_ids", nargs="+")
    observe_parser.add_argument("--context", help="The learner's phrase; also used to deduplicate retries")
    observe_parser.add_argument("--at", help="ISO-8601 event time")

    due_parser = subparsers.add_parser("due", help="List mistake patterns due for review")
    due_parser.add_argument("--limit", type=int, default=5)
    due_parser.add_argument("--at", help="ISO-8601 comparison time")
    _add_format(due_parser)

    grade_parser = subparsers.add_parser("grade", help="Grade a mistake review")
    grade_parser.add_argument("mistake_id")
    grade_parser.add_argument("--result", required=True, choices=("pass", "hard", "fail"))
    grade_parser.add_argument("--answer", help="The learner's answer; kept in the pattern's timeline")
    grade_parser.add_argument("--correction", help="Minimal correction of a failed answer")
    grade_parser.add_argument("--at", help="ISO-8601 review time")

    list_parser = subparsers.add_parser("list", help="List tracked patterns compactly")
    list_parser.add_argument("--status", choices=("active", "mastered", "all"), default="active")
    list_parser.add_argument("--category", choices=CATEGORY_ORDER)
    _add_format(list_parser)

    show_parser = subparsers.add_parser("show", help="Show one pattern with its full history")
    show_parser.add_argument("mistake_id")
    _add_format(show_parser)

    forget_parser = subparsers.add_parser("forget", help="Delete a wrongly recorded pattern")
    forget_parser.add_argument("mistake_id")

    undo_parser = subparsers.add_parser("undo", help="Revert the latest record, grade, or observe on one pattern")
    undo_parser.add_argument("mistake_id")

    merge_parser = subparsers.add_parser("merge", help="Fold one pattern into another (source into target)")
    merge_parser.add_argument("source_id")
    merge_parser.add_argument("target_id")
    merge_parser.add_argument("--at", help="ISO-8601 merge time")

    rename_parser = subparsers.add_parser("rename", help="Rename or recategorize a pattern")
    rename_parser.add_argument("mistake_id")
    rename_parser.add_argument("--pattern")
    rename_parser.add_argument("--category", choices=CATEGORY_ORDER)
    rename_parser.add_argument("--rule")
    rename_parser.add_argument("--label", help="Short German name shown to the learner")

    summary_parser = subparsers.add_parser("summary", help="Show the learner's FehlerDNA profile")
    summary_parser.add_argument("--at", help="ISO-8601 summary time")
    _add_format(summary_parser)

    recap_parser = subparsers.add_parser("recap", help="Summarize recent activity for a session opener")
    recap_parser.add_argument("--days", type=int, default=RECENT_DAYS)
    recap_parser.add_argument("--at", help="ISO-8601 recap time")
    recap_parser.add_argument(
        "--format",
        choices=("json", "text", "card"),
        default="json",
        help="json for agents, text for a summary, card for the two-line German session header",
    )

    verify_parser = subparsers.add_parser("verify", help="Check minimality and query a local LanguageTool server")
    verify_parser.add_argument("--original", required=True)
    verify_parser.add_argument("--corrected", required=True)
    verify_parser.add_argument("--endpoint", default=os.environ.get("LANGUAGETOOL_URL", DEFAULT_LANGUAGETOOL_URL))
    verify_parser.add_argument("--language", default="de-DE")
    verify_parser.add_argument("--timeout", type=float, default=2.5)
    verify_parser.add_argument(
        "--allow-remote",
        action="store_true",
        default=os.environ.get("DEUTSCHDNA_ALLOW_REMOTE_VALIDATOR") == "1",
        help="Permit a non-localhost endpoint (sends learner text off this machine)",
    )

    roleplay_start_parser = subparsers.add_parser("roleplay-start", help="Start a delayed-feedback roleplay session")
    roleplay_start_parser.add_argument("--scenario", required=True, choices=sorted(SCENARIOS))
    roleplay_start_parser.add_argument("--focus")
    roleplay_start_parser.add_argument("--at", help="ISO-8601 start time")

    roleplay_finish_parser = subparsers.add_parser("roleplay-finish", help="Finish a roleplay session")
    roleplay_finish_parser.add_argument("session_id")
    roleplay_finish_parser.add_argument("--turns", required=True, type=int)
    roleplay_finish_parser.add_argument("--duration-seconds", type=int, help="Override the timestamp-derived duration")
    roleplay_finish_parser.add_argument(
        "--mistake-id", "--mistake-ids", dest="mistake_id", action="extend", nargs="+", default=[],
        help="IDs recorded in this session; repeat the flag or list several",
    )
    roleplay_finish_parser.add_argument("--notes")
    roleplay_finish_parser.add_argument("--at", help="ISO-8601 finish time")
    return parser


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    store = StateStore(default_home(arguments.home))
    command = arguments.command
    if command == "init":
        profile = store.init_profile(
            name=arguments.name,
            native_language=arguments.native_language,
            level=arguments.level,
            at=parse_moment(arguments.at),
        )
        return {"status": "ready", "home": str(store.home.resolve()), "profile": profile}
    if command == "record":
        mistake, status, extra = store.record(
            original=arguments.original,
            corrected=arguments.corrected,
            category=arguments.category,
            pattern=arguments.pattern,
            rule=arguments.rule,
            mistake_id=arguments.mistake_id,
            context=arguments.context,
            verification_status=arguments.verification_status,
            event_id=arguments.event_id,
            label=arguments.label,
            at=parse_moment(arguments.at),
        )
        result: dict[str, Any] = {
            "status": status,
            "mistake": public(mistake),
            "resolved_by": extra.get("resolved_by"),
            "recent": {"days": RECENT_DAYS, "occurrences": extra.get("recent_occurrences", 0)},
        }
        if extra.get("previous"):
            result["previous"] = extra["previous"]
        similar = extra.get("similar_patterns") or []
        if similar:
            result["similar_patterns"] = similar
            result["hint"] = (
                f"Similar patterns already exist. If this is the same root cause, run: "
                f"merge {mistake['id']} {similar[0]['id']}"
            )
        return result
    if command == "observe":
        results = store.observe(arguments.mistake_ids, context=arguments.context, at=parse_moment(arguments.at))
        return {"status": "observed", "results": results}
    if command == "due":
        moment = parse_moment(arguments.at)
        items = store.due(at=moment, limit=arguments.limit)
        return {"as_of": iso(moment), "count": len(items), "mistakes": [public(item) for item in items]}
    if command == "grade":
        mistake, status = store.grade(
            arguments.mistake_id,
            result=arguments.result,
            answer=arguments.answer,
            correction=arguments.correction,
            at=parse_moment(arguments.at),
        )
        return {"status": status, "mistake": public(mistake)}
    if command == "list":
        rows = store.list(status=arguments.status, category=arguments.category)
        return {"count": len(rows), "status_filter": arguments.status, "mistakes": rows}
    if command == "show":
        return {"mistake": public(store.show(arguments.mistake_id))}
    if command == "forget":
        return {"status": "forgotten", "mistake": public(store.forget(arguments.mistake_id))}
    if command == "undo":
        return store.undo(arguments.mistake_id)
    if command == "merge":
        merged = store.merge(arguments.source_id, arguments.target_id, at=parse_moment(arguments.at))
        return {"status": "merged", "mistake": public(merged)}
    if command == "rename":
        outcome = store.rename(
            arguments.mistake_id,
            pattern=arguments.pattern,
            category=arguments.category,
            rule=arguments.rule,
            label=arguments.label,
        )
        return {"status": "renamed", "previous_id": outcome["previous_id"], "mistake": public(outcome["mistake"])}
    if command == "summary":
        moment = parse_moment(arguments.at)
        result = store.summary(at=moment)
        if arguments.format == "text":
            store.mark_profile_shown(at=moment)
        return result
    if command == "recap":
        return store.recap(days=arguments.days, at=parse_moment(arguments.at))
    if command == "verify":
        return verify_correction(
            arguments.original,
            arguments.corrected,
            endpoint=arguments.endpoint,
            language=arguments.language,
            timeout=arguments.timeout,
            allow_remote=arguments.allow_remote,
        )
    if command == "roleplay-start":
        return store.roleplay_start(arguments.scenario, focus=arguments.focus, at=parse_moment(arguments.at))
    if command == "roleplay-finish":
        session = store.roleplay_finish(
            arguments.session_id,
            turns=arguments.turns,
            duration_seconds=arguments.duration_seconds,
            mistake_ids=arguments.mistake_id,
            notes=arguments.notes,
            at=parse_moment(arguments.at),
        )
        return {"status": "finished", "session": session}
    raise DeutschDNAError(f"Unsupported command: {command}")


def main(argv: list[str] | None = None) -> int:
    _configure_streams()
    parser = build_parser()
    try:
        arguments = parser.parse_args(argv)
        result = run(arguments)
        output_format = getattr(arguments, "format", "json")
        renderers = {"text": TEXT_RENDERERS, "card": CARD_RENDERERS}.get(output_format, {})
        renderer = renderers.get(arguments.command)
        if renderer:
            print(renderer(result))
        else:
            _print_json(result)
        return 0
    except DeutschDNAError as exc:
        _print_json({"error": str(exc)}, stream=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
