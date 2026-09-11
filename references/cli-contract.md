# CLI contract

All commands print UTF-8 JSON to stdout regardless of the console code page. `recap`, `summary`, `due`, `list`, and `show` also accept `--format text` for a human-readable rendering meant to be shown verbatim, and `recap --format card` prints the German board that opens a session. Errors print JSON to stderr and exit with status 2.

## State

The state directory is selected in this order:

1. global `--home PATH` argument;
2. `DEUTSCHDNA_HOME` environment variable;
3. `~/.deutschdna`.

The CLI creates `profile.json`, `mistakes.json`, and `sessions.json` atomically. They are plain JSON for portability, but integrations must change them only through the CLI (`forget`, `merge`, `rename`), never by hand. State from schema version 1 is upgraded on read; pattern IDs are kept.

Stored times are UTC. Outputs add `*_local` twins such as `seen_at_local`, `next_review_local`, and `last_activity_local` in the machine's time zone, or in `DEUTSCHDNA_UTC_OFFSET` (for example `+02:00`) when it is set. Day-based values follow the local calendar: streaks, today, yesterday, and days since the last activity. Rendering `summary --format text` records `last_full_profile_at` in the profile.

## Commands

| Command | Purpose |
| --- | --- |
| `init` | Create or update the learner profile without clearing history. |
| `record` | Add a new root-cause pattern or add a recurrence to an existing one. Use `--mistake-id` to recur a known pattern, or `--category`, `--pattern`, and `--rule` to name one; `--label` sets its German name. |
| `observe` | Log a correct, unprompted use of one or more tracked patterns (by ID). |
| `due` | Active patterns whose `next_review` is at or before the given time. |
| `grade` | Apply `pass`, `hard`, or `fail` to a reviewed pattern. `--answer` keeps the learner's sentence in the timeline. |
| `list` | Compact rows for `--status active`, `mastered`, or `all`, optionally filtered by `--category`. |
| `show` | One pattern with its full history; `--format text` renders its journey as a timeline. |
| `undo` | Revert the latest `record`, `grade`, or `observe` on one pattern, including its review schedule. One level deep; undoing the record that created a pattern removes it. |
| `forget` | Delete a pattern and its whole history, and drop it from session references. |
| `merge` | Fold the source pattern into the target: counts add up, histories interleave, the source key becomes an alias of the target. |
| `rename` | Change a pattern's key, category, rule, or German `--label`; an old key stays as an alias. Refuses to collide with an existing pattern and points to `merge`. |
| `summary` | The FehlerDNA profile: per-category accuracy, root-cause clusters, weakest and due patterns, streak. |
| `recap` | The session opener: activity in the last `--days` (default 7), totals, `schedule` (due now, later today, next review in local time), `full_profile_due`, `board` (up to five patterns: due first, then by errors) with `board_more`, and `card`, the rendered board. |
| `verify` | Minimality analysis plus a local LanguageTool check. |
| `roleplay-start`, `roleplay-finish` | Store a roleplay session; the duration is derived from the two timestamps unless `--duration-seconds` overrides it. |

Every writing command accepts `--at ISO-8601` for deterministic integrations and tests. Use `python scripts/deutsch_dna.py COMMAND --help` for exact arguments.

## The record response

- `status`: `recorded` (new pattern), `updated` (recurrence), or `duplicate` (nothing changed).
- `resolved_by`: how an existing pattern was found: `mistake_id`, `id`, `pattern_key`, or `alias`.
- `recent.occurrences`: errors on this pattern in the last 7 days, including this one.
- `previous` (recurrences only): the pattern's `last_seen`, `review_step`, `status`, and `occurrences` before this error, plus `first_example` and `last_example`, the earliest and the latest stored wrong sentence. Use them for the recurrence callback in the correction protocol.
- `similar_patterns` and `hint` (new patterns only): existing patterns whose key is at least 72% similar, with a ready `merge` command.

## German labels

Pattern keys stay English and stable; learners see German names. Every row and pattern in the output carries `label` and `label_source`:

- `custom`: set with `record --label` or `rename --label`.
- `catalog`: a built-in name for a catalog key, such as `Verb an Position 2` or `Nomen großschreiben`.
- `rule`: derived from the key, such as `Pizza ist feminin`, `sich treffen (reflexiv)`, `weil: Verb ans Ende`, or `warten auf + Akkusativ`.
- `key`: no German name is known yet; the key itself is shown. Give the pattern a label with `rename --label`.

Labels are at most 60 characters; the board shows up to 36 of them. Text views (`card`, `summary`, `show`, `due`, `recap --format text`) use labels; `list --format text` shows the keys.

## The observe response

Each entry in `results` carries `status` (`observed`, `observed_and_advanced`, or `duplicate`), the new `correct_uses`, the schedule, and `last_mistake`: the latest stored wrong sentence, for the before-and-after line.

## Pattern identity

A pattern's ID is a hash of its category and its *pattern key*. The key is the normalized pattern text: lower-cased, whitespace-collapsed, punctuation removed, with `Dativ`, `Dat`, `dat.` → `dative`; `Akkusativ`, `Akk`, `acc` → `accusative`; `Nominativ` → `nominative`; `Genitiv` → `genitive`; and `governs`, `takes`, `requires`, `needs` → `+`. The tokens `case`, `kasus`, and `the` are dropped. So `mit + Dativ`, `mit+dat.`, and `mit governs the dative` all resolve to `mit + dative`.

Resolution order on `record`: exact ID, then the same key in any category, then any alias created by `merge` or `rename`. A brand-new pattern is created only when nothing matches; the response then lists `similar_patterns`, because the CLI cannot tell `der-word` from `ein-word` on its own.

## Idempotency

- `record` never counts the same `--event-id` twice while that example is stored (the 12 most recent per pattern).
- `record` without `--event-id` derives one from the original and corrected text; an identical call within 30 minutes returns `status: duplicate` and changes nothing. A retry after a crash therefore cannot double-count.
- `grade` ignores a repeat of the same result within 5 minutes.
- `observe` ignores a repeat with the same `--context` within 5 minutes.
- `roleplay-finish` on a completed session returns it unchanged.
- `undo` works once per change: a second `undo` on the same pattern fails, and `merge` or `rename` clear the snapshot. Responses show `undo_available` instead of the stored snapshot.

## Review schedule

The successful review sequence is 1, 3, 7, 14, 30, then 60 days. Recording a recurrence or grading `fail` restarts the sequence at one day. `hard` schedules another one-day attempt without changing the step. Passing the final step marks the pattern `mastered` and sets `mastered_at`; a later recurrence reactivates it and records `reactivated_at` and `previously_mastered_at`.

`observe` on an active pattern that is currently due counts as a pass (`source: observed`): a learner who uses the structure correctly in real writing does not need to be quizzed on it that day. Observations on patterns that are not due only increment `correct_uses`.

## Scoring

- `occurrences` (shown as *wrong*): every recorded error, including review failures.
- *right*: `correct_uses` plus passes from real reviews.
- `accuracy_percent` = round(100 × (right + 1) / (right + wrong + 2)). The smoothing keeps a single error from reading as 0% and a single pass from reading as 100%.
- A pattern or category is `new` until it has at least one graded review or correct use. Text cards show `neu` instead of a percentage, and the weakest-pattern list skips new patterns: a first text is not a score.
- A category is `weak` when it is not new, its accuracy is below 60%, and it has at least two errors.
- A *cluster* (shown as **Root cause**) is a category with at least two active patterns and three errors among them. Clusters are ranked by how many different patterns in the family failed in the last 30 days (`recent_patterns`), then by recent errors, then by total errors. Breadth outranks depth: four different verb-plus-preposition mistakes say more about the rule than one pattern missed four times. The **Root cause** line states the family's share of all mistakes in the same 30 days (`recent_errors` of `recent_errors_total`).
- `mastery_percent` is the average review-ladder position per category (0–100), kept for integrations.
- `streak_days` counts consecutive local days with any recorded activity, ending today or yesterday.
- `full_profile_due` is true when the learner has activity and has never seen the full profile card, or last saw it at least 7 days ago and has been active since.

Percentages describe tracked patterns only. A category with no recorded mistakes does not appear; it is unknown, not 0%. The text profile shows German category names (`Kasus`, `Präpositionen`, `Endungen`, …); JSON keeps the English category IDs.
