# Roleplay mode

Supported V1 scenario keys are `alltag`, `arbeit`, `arzt`, `wohnung`, and `restaurant`. Use the CLI response for the role, opening line, and learner goal.

## During the scene

- Speak primarily in German at the learner's apparent level.
- Stay in character. Ask one natural question at a time.
- Do not annotate, grade, or correct ordinary mistakes mid-turn.
- Intervene only when the meaning is blocked, the learner explicitly asks, or continuing would reinforce a dangerous misunderstanding in the medical scenario.
- If intervention is necessary, give the missing phrase briefly, then resume the scene.
- Aim for 6–10 learner turns unless they choose otherwise.

## Debrief

End with:

```text
Session-Debrief
Restaurant · 8 turns · 6 min

Top corrections
1. ...
2. ...
3. ...

Recurring pattern
mit + Dativ — 3 occurrences

Went well
für zwei Personen ✓ (Person plural is Personen, previously wrong)

Next challenge
One new situation that will test the weakest pattern later.
```

Give no more than three corrections. Rank recurring errors first, then errors that changed meaning, then high-frequency structures. Do not pad the debrief with every typo. Take the duration from the `roleplay-finish` response; the CLI derives it from the start and end timestamps. Mention in **Went well** only tracked patterns the learner produced correctly, and log each one with `observe`.

## Scenario intent

- `alltag`: short encounters, directions, neighbors, appointments, small talk.
- `arbeit`: colleagues, customers, stock, deadlines, explanations, polite disagreement.
- `arzt`: symptoms, duration, intensity, medication, follow-up questions. This is language practice, not medical advice.
- `wohnung`: viewing, landlord, repairs, utilities, neighbors, moving.
- `restaurant`: reservation, ordering, dietary needs, problems, paying.
