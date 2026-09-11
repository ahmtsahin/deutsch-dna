# Minimal correction protocol

## Output order

Use this compact structure when an actual error exists:

```text
Dein Satz
Ich möchte morgen mit mein Chef darüber sprechen.

Minimale Korrektur
Ich möchte morgen mit meinem Chef darüber sprechen.

Warum
mit + Dativ: mein → meinem

Prüfung
LanguageTool supports this correction.
```

Show only the changed fragment in **Warum**. If the learner asks for a natural rewrite, add:

```text
Native alternative — not a correction
Morgen würde ich das gern mit meinem Chef besprechen.
```

If the sentence is already correct, say so. Do not manufacture a correction in order to teach something. If the sentence correctly uses a pattern the learner used to get wrong, log it with `observe` and add the before-and-after line.

## The recurrence callback

When `record` answers `status: updated`, the learner has made this mistake before. Add a **Muster** block; it is the moment the tutor proves it remembers. Build it only from the CLI response.

The first line names the pattern and the numbers:

- Several times this week (`recent.occurrences` of 2 or more): say how often.
- Back after a long pause (`previous.last_seen` weeks ago): say how long it stayed away and how far it had climbed (`previous.review_step` of 6), or that it had been mastered (`previous.status`).

The second line quotes the earliest stored sentence for this pattern (`previous.first_example`) with its date, next to the sentence from today. Seeing their own old sentence is what makes the learner feel remembered.

```text
Muster
mit + Dativ · 3. Mal in 7 Tagen
Am 9. September: „Ich spreche mit mein Chef." · heute: „Ich gehe mit meine Kollegin essen."
```

```text
Muster
warten auf + Akkusativ · nach 104 Tagen zurück · du warst schon bei Stufe 5 von 6
Am 14. Mai: „Ich warte dich." · heute: „Ich warte meine Freundin."
```

Then say in one sentence that it will come back tomorrow in a new sentence. Never invent a count, a date, or a quote that the CLI did not return.

## The before-and-after line

When the learner gets a tracked pattern right, unprompted or in an opener task, log it with `observe` and set the last wrong sentence from the response (`last_mistake`) next to the new one:

```text
Vor 12 Tagen: „Ich spreche mit mein Chef." · Heute: „Wir haben mit unseren Kunden gesprochen." ✓
```

Keep it to one line and do not explain the rule again; the contrast is the message.

## Minimality

- Preserve the learner's meaning, register, tense, vocabulary, and information order.
- Change multiple tokens only when one grammatical dependency requires it, such as article plus adjective ending.
- Do not replace a valid word with a preferred synonym.
- Keep punctuation and capitalization changes separate from grammar explanations when that makes the real error easier to see.
- If the CLI returns `minimality_status: possible_rewrite`, reconsider the correction or clearly label the larger version as an alternative.

## Validator labels

Use the CLI result without upgrading its certainty:

- `verified`: LanguageTool found an issue in the original, suggested the changed fragment, and found no issue in the correction. Say **LanguageTool supports this correction**.
- `supported`: LanguageTool reports fewer issues and no new rule IDs, but some findings remain. Say **LanguageTool partially supports this correction**.
- `no_finding`: LanguageTool did not detect the proposed error. Say **LanguageTool did not verify this change**.
- `uncertain`: findings remain or new rule IDs appear. Show the disagreement briefly and call the change a suggestion.
- `unavailable`: the local server could not be reached, or the endpoint is remote and not allowed. Say **Not LanguageTool-verified**.

These labels mean machine-checked, not linguistically proven. Semantic and register judgments remain model-only.

## What to persist

Persist a mistake only when:

- the learner actually produced it;
- the correction is grammatically necessary, not just more elegant; and
- the root cause can be named stably.

Store what the learner actually wrote. `--original` is the whole sentence, verbatim; `--corrected` is the complete minimal correction of that sentence with every error fixed. When one sentence contains several patterns, record the same pair once per pattern. Keep umlauts and ß; never transliterate them.

Prefer `record --mistake-id` for a pattern that already exists in `list`; otherwise use a key from the pattern catalog. Do not persist typos that the learner immediately identifies, quoted third-party text, or uncertain stylistic preferences unless the learner asks to track them. Never `record` a failed review item; `grade --result fail` already counts the recurrence.
