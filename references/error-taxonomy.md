# FehlerDNA taxonomy

Choose one primary category. Put cross-cutting detail in the `pattern` and `rule` fields rather than duplicating the same event in several categories. Canonical pattern keys for each category are in [patterns.md](patterns.md).

| Category | Use for | Pattern-key examples |
| --- | --- | --- |
| `article` | noun gender and article selection | `-ung nouns are feminine`, `Tisch is masculine`, `no article before profession or nationality` |
| `case` | case marking after prepositions, verbs, and in noun phrases | `mit + dative`, `helfen + dative`, `masculine accusative -en` |
| `preposition` | which preposition a verb, adjective, or expression takes, and preposition choice | `warten auf + accusative`, `seit vs vor`, `nach vs zu for destinations` |
| `word-order` | verb position, clause order, sentence fields | `weil sends finite verb to end`, `finite verb in second position` |
| `verb` | conjugation, tense, auxiliary, participle, separable or reflexive form | `sein as perfect auxiliary for motion and change`, `sich erinnern is reflexive` |
| `agreement` | adjective, determiner, or subject-verb agreement | `adjective ending after ein-word`, `possessive agrees with the possessed noun` |
| `plural` | plural formation | `Person plural is Personen`, `-ung plural adds -en` |
| `spelling` | spelling, capitalization, compound boundaries | `German nouns are capitalized`, `dass vs das` |
| `vocabulary` | wrong lexical item, false friend, or fixed collocation | `kennen vs wissen`, `eine Entscheidung treffen` |
| `register` | situationally inappropriate formality | `Sie in formal exchanges` |
| `punctuation` | commas and punctuation that affect correctness | `comma before subordinate clause` |
| `other` | genuine errors that fit none of the above | keep the pattern precise |

## Deciding between `case` and `preposition`

- The learner chose the right preposition but the wrong case after it: `case` (`mit mein Chef` → `mit + dative`).
- The learner omitted or chose the wrong preposition that a verb or adjective requires: `preposition` (`Ich warte dich` → `warten auf + accusative`).
- The learner used the right verb-preposition pair with the wrong case: still `preposition`, because the key already carries the case (`warten auf + accusative`).

## Stable pattern keys

- Name the reusable rule: `mit + dative`, not `mit meinem Chef`.
- Keep the same wording for the same root cause; the CLI normalizes case names, spacing, and `takes/governs` phrasings, but a catalog key keeps the record clean.
- Separate patterns when their remediation differs. `warten auf + accusative` and `helfen + dative` are not one pattern, even though both involve government.
- Prefer the deepest useful cause. For `mit meine Kunde`, track `mit + dative` and mention the n-declension in the rule; add `n-declension nouns take -n/-en` only when it recurs on its own.
- When `record` reports `similar_patterns`, read them before continuing. Merge only when the remediation is identical; `der-word` and `ein-word` adjective endings are similar strings but different lessons.
