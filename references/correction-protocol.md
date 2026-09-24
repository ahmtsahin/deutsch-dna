# Minimal correction protocol

## Output order

Use this compact structure when an actual error exists:

When the learner wants practice, first invite repair of one confirmed error with a small cue, as described in [the learning loop](learning-loop.md), and wait before revealing that correction. For a direct correction request, show the correction immediately. In ordinary conversation, respond to the meaning and continue with one relevant question after feedback; a correction-only request does not need a question.

```text
Dein Satz
Ich möchte morgen mit mein Chef darüber sprechen.

Minimale Korrektur
Ich möchte morgen mit meinem Chef darüber sprechen.

Warum
mit + Dativ: mein → meinem
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

The first example is pinned independently of the recent history. On migrated older data, it may only be the earliest retained example: when `previous.first_example_is_original` is false, do not call it the learner's first-ever mistake or pair it with `first_seen`. Use the example's own date.

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

For a correct, unprompted use, log `observe` and set the last wrong sentence from the response (`last_mistake`) next to the new one. An opener task is prompted: use `grade` when due, or `coach` otherwise, as described in [the learning loop](learning-loop.md). Do not also observe the same answer.

```text
Vor 12 Tagen: „Ich spreche mit mein Chef." · Heute: „Wir haben mit unseren Kunden gesprochen." ✓
```

Keep it to one line and do not explain the rule again; the contrast is the message.

When a new `learning_proof` is returned, prefer its with-help/without-help comparison to a second before-and-after block. Use its real sentences, `at_local` dates, and source. An unaided new task is not spontaneous writing, and one transfer is not mastery.

## Minimality

- Preserve the learner's meaning, register, tense, vocabulary, and information order.
- Change multiple tokens only when one grammatical dependency requires it, such as article plus adjective ending.
- Do not replace a valid word with a preferred synonym.
- Keep punctuation and capitalization changes separate from grammar explanations when that makes the real error easier to see.
- If `record` returns `minimality.status: possible_rewrite`, you changed more than grammar required: reconsider the correction, `undo` the record, or clearly label the larger version as an alternative.

No tool checks the correction itself. Do not call a correction verified or machine-checked; when you are unsure, say so and offer a suggestion instead of recording it.

## What to persist

Persist a mistake only when:

- the learner actually produced it;
- the correction is grammatically necessary, not just more elegant; and
- the root cause can be named stably.

Store what the learner actually wrote. `--original` is the whole sentence, verbatim; `--corrected` is the complete minimal correction of that sentence with every error fixed. When one sentence contains several patterns, record the same pair once per pattern. Keep umlauts and ß; never transliterate them.

Prefer `record --mistake-id` for a pattern that already exists in `list`; otherwise use a key from the pattern catalog. Do not persist typos that the learner immediately identifies, quoted third-party text, or uncertain stylistic preferences unless the learner asks to track them. Never `record` a failed review item; `grade --result fail` already counts the recurrence.
