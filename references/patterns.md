# Pattern catalog

Canonical keys for the most frequent root causes. Use these exact keys with `record --pattern`. The CLI maps `Dativ`, `Akk.`, `takes`, `governs`, and similar variants onto the same key, but a catalog key keeps the FehlerDNA clean. When a real error fits none of these, coin a key in the same style: the reusable rule, in English, lowercase, with `+` for government (`<word> + <case>`).

Naming rules:

- Name the rule, not the sentence: `mit + dative`, not `mit meinem Chef`.
- One remediation per key. `warten auf + accusative` and `helfen + dative` are separate.
- Individual items: `<Noun> is masculine|feminine|neuter`, `<Noun> plural is <form>`, `<verb> past participle is <form>`, `<verb> is reflexive`, `<verb> + <case>`.
- Prefer the deepest useful cause. For `mit meine Kunde`, track `mit + dative` and mention the n-declension in the rule; add `n-declension nouns take -n/-en` only when it recurs on its own.

## article

| Key | Rule | Example |
| --- | --- | --- |
| `-ung nouns are feminine` | Nouns in -ung are feminine | ein Reservierung → eine Reservierung |
| `-heit/-keit nouns are feminine` | -heit, -keit, -schaft, -ion, -tät, -ik, -ie are feminine | der Möglichkeit → die Möglichkeit |
| `-chen/-lein nouns are neuter` | Diminutives are neuter | die Mädchen → das Mädchen |
| `-ment/-um nouns are neuter` | Usually neuter | der Dokument → das Dokument |
| `-ismus nouns are masculine` | | das Tourismus → der Tourismus |
| `nominalized infinitives are neuter` | | der Essen → das Essen |
| `no article before profession or nationality` | | Ich bin ein Lehrer → Ich bin Lehrer |
| `country names with article` | die Türkei, die Schweiz, der Irak, die USA keep their article and change case | in Türkei → in der Türkei |
| `<Noun> is masculine/feminine/neuter` | Per-noun gender with no rule | das Tisch → der Tisch (`Tisch is masculine`) |

## case

| Key | Rule | Example |
| --- | --- | --- |
| `mit + dative` | mit always governs the dative | mit mein Chef → mit meinem Chef |
| `bei + dative` | also: nach, von, zu, aus, seit, außer, gegenüber (`<prep> + dative`) | bei meine Oma → bei meiner Oma |
| `für + accusative` | also: ohne, gegen, um, durch, bis (`<prep> + accusative`) | für mein Bruder → für meinen Bruder |
| `two-way preposition: location takes dative` | Wo? in, an, auf, über, unter, vor, hinter, neben, zwischen + dative | Ich bin in die Küche → in der Küche |
| `two-way preposition: direction takes accusative` | Wohin? the same prepositions + accusative | Ich gehe in der Küche → in die Küche |
| `helfen + dative` | Dative-object verbs: helfen, danken, gefallen, gehören, folgen, antworten, gratulieren, passen, schmecken, fehlen, vertrauen, zuhören (`<verb> + dative`) | Ich helfe meinen Bruder → meinem Bruder |
| `anrufen + accusative` | Accusative-object verbs where other languages use a dative: anrufen, fragen, besuchen, treffen, brauchen, stören (`<verb> + accusative`) | Ich rufe dir an → Ich rufe dich an |
| `masculine accusative -en` | ein, kein, mein, der become einen, keinen, meinen, den before a masculine direct object | Ich habe ein Hund → einen Hund |
| `n-declension nouns take -n/-en` | Kunde, Kollege, Student, Herr, Name, Junge take -n/-en outside the nominative | mit dem Kunde → mit dem Kunden |
| `dative plural -n` | Plural nouns add -n in the dative | mit den Kinder → mit den Kindern |
| `wegen/trotz/während + genitive` | Standard German uses the genitive; colloquial dative exists | wegen dem Regen → wegen des Regens |
| `predicate noun after sein takes nominative` | | Das ist einen Fehler → Das ist ein Fehler |
| `es gibt + accusative` | | Es gibt ein Grund → einen Grund |
| `pronoun case after preposition` | mir, dir, ihm after dative prepositions; mich, dich, ihn after accusative ones | mit mich → mit mir |

## preposition

Verb, adjective, or expression plus fixed preposition, and preposition choice.

| Key | Rule | Example |
| --- | --- | --- |
| `warten auf + accusative` | | Ich warte dich → Ich warte auf dich |
| `denken an + accusative` | | Ich denke dich → Ich denke an dich |
| `sich erinnern an + accusative` | | Ich erinnere mich von → an |
| `sich interessieren für + accusative` | | Ich interessiere mich an Fußball → für Fußball |
| `sich freuen auf + accusative` | For something ahead | Ich freue mich über das Wochenende → auf das Wochenende |
| `sich freuen über + accusative` | For something present or past | Ich freue mich auf dein Geschenk (already received) → über dein Geschenk |
| `teilnehmen an + dative` | | teilnehmen bei → an der Besprechung |
| `sich kümmern um + accusative` | | |
| `sich bewerben um + accusative` | | |
| `sprechen über + accusative` | Topics take über; people you talk with take mit | Wir sprechen von das Projekt → über das Projekt |
| `Angst haben vor + dative` | | Angst von Hunden → vor Hunden |
| `sich ärgern über + accusative` | | |
| `sich vorbereiten auf + accusative` | | |
| `sich gewöhnen an + accusative` | | |
| `abhängen von + dative` | | |
| `bitten um + accusative` | | |
| `sich bedanken bei + dative` | bei the person, für the thing | |
| `zufrieden mit + dative` | | |
| `stolz auf + accusative` | | |
| `verantwortlich für + accusative` | | |
| `nach vs zu for destinations` | nach with cities and article-less countries; zu with people, shops, institutions | Ich gehe nach dem Arzt → zum Arzt |
| `in vs nach for countries` | nach Deutschland, but in die Türkei, in die Schweiz | Ich fliege nach der Türkei → in die Türkei |
| `seit vs vor` | seit: ongoing since; vor: ago | Ich wohne hier vor zwei Jahren → seit zwei Jahren |
| `am/um/im for time expressions` | am Montag, um 8 Uhr, im Mai | in Montag → am Montag |
| `bei for at a person or company` | | Ich arbeite in Siemens → bei Siemens |
| `zu Hause vs nach Hause` | Location vs direction | Ich gehe zu Hause → nach Hause |

## word-order

| Key | Rule | Example |
| --- | --- | --- |
| `finite verb in second position` | Main clause: one element, then the verb | Morgen ich gehe → Morgen gehe ich |
| `weil sends finite verb to end` | weil, obwohl, dass, wenn, ob, damit, als, bevor, nachdem send the finite verb to the end (`<conj> sends finite verb to end`) | weil ich bin krank → weil ich krank bin |
| `relative clause verb to end` | | der Mann, der wohnt hier → der hier wohnt |
| `separable prefix goes to clause end` | | Ich anrufe dich → Ich rufe dich an |
| `past participle at clause end` | | Ich habe gesprochen mit ihm → mit ihm gesprochen |
| `infinitive after modal at clause end` | | Ich möchte sprechen mit dir → mit dir sprechen |
| `time-manner-place order` | | Ich fahre nach Berlin morgen → morgen nach Berlin |
| `nicht position` | nicht before the negated element, or at the end for the whole clause | Ich nicht komme → Ich komme nicht |
| `coordinating conjunctions keep word order` | und, aber, denn, oder, sondern do not move the verb | denn bin ich müde → denn ich bin müde |
| `adverb connectors trigger inversion` | deshalb, dann, trotzdem, danach start the clause and the verb follows | deshalb ich bleibe → deshalb bleibe ich |
| `dative before accusative noun objects` | Two noun objects: dative first; a pronoun object goes first | Ich gebe das Buch meinem Bruder → meinem Bruder das Buch |
| `yes/no question verb first` | | Du kommst morgen? (as a question) → Kommst du morgen? |

## verb

| Key | Rule | Example |
| --- | --- | --- |
| `sein as perfect auxiliary for motion and change` | fahren, gehen, kommen, aufstehen, einschlafen, bleiben, sein, werden use sein | Ich habe gefahren → Ich bin gefahren |
| `-ieren verbs take no ge-` | | gestudiert → studiert |
| `inseparable prefix verbs take no ge-` | be-, ge-, er-, ver-, zer-, ent-, emp-, miss- | geverstanden → verstanden |
| `<verb> past participle is <form>` | Irregular participles | gesprecht → gesprochen |
| `<verb> is reflexive` | sich erinnern, sich freuen, sich beeilen | Ich erinnere an → Ich erinnere mich an |
| `stem vowel change in du/er forms` | fahren → fährst, lesen → liest, sehen → sieht, nehmen → nimmt | er fahrt → er fährt |
| `modal verbs have no -t in 3rd person` | er kann, muss, will, darf, soll, mag | er kannt → er kann |
| `infinitive with zu after non-modal verbs` | versuchen, hoffen, vergessen, anfangen + zu; modals without zu | Ich versuche kommen → zu kommen |
| `Präteritum for sein/haben/modals` | Spoken German prefers war, hatte, konnte | Ich bin müde gewesen → Ich war müde |
| `werden for future and passive` | | Das Haus ist gebaut (being built now) → wird gebaut |
| `hätte/wäre/würde for polite and unreal` | | Ich habe gern einen Kaffee → Ich hätte gern einen Kaffee |

## agreement

| Key | Rule | Example |
| --- | --- | --- |
| `adjective ending after der-word` | der, die, das, dieser, jeder, welcher + adjective: -e in the nominative singular and the feminine or neuter accusative, -en everywhere else | den neue Film → den neuen Film |
| `adjective ending after ein-word` | ein, kein, mein, dein, unser + adjective: the adjective shows the gender where the article cannot (ein neuer Job, ein neues Auto), otherwise -e or -en | einen neue Job → einen neuen Job |
| `adjective ending without article` | Strong endings: guter Wein, kaltes Wasser, frische Brötchen | gut Wein → guter Wein |
| `possessive agrees with the possessed noun` | mein Vater, meine Mutter, mein Kind: the ending follows the noun's gender, not the owner's | meine Chef → mein Chef |
| `subject-verb agreement` | | Die Kinder spielt → spielen |
| `der-word endings` | dieser, jeder, welcher follow der/die/das endings | diese Mann → dieser Mann |

## plural

| Key | Rule | Example |
| --- | --- | --- |
| `Person plural is Personen` | | zwei Person → zwei Personen |
| `-ung plural adds -en` | | Wohnungs → Wohnungen |
| `feminine -e plural adds -n` | | die Blume → die Blumen |
| `-in plural is -innen` | | Lehrerins → Lehrerinnen |
| `umlaut plural` | Vater → Väter, Stadt → Städte | die Stadts → die Städte |
| `-s plural for loanwords` | | Autos, Handys, Hotels |
| `plural after numbers above one` | | zwei Kind → zwei Kinder |

## spelling

| Key | Rule | Example |
| --- | --- | --- |
| `German nouns are capitalized` | | die wohnung → die Wohnung |
| `dass vs das` | Conjunction dass; article or pronoun das | Ich weiß, das → dass |
| `ß after long vowel, ss after short` | | Strasse → Straße; dass keeps ss |
| `compound nouns are one word` | | Kunden Service → Kundenservice |
| `formal Sie is capitalized` | | Können sie mir helfen? → Können Sie mir helfen? |
| `umlauts are written` | mochte and möchte differ in meaning | Ich mochte einen Kaffee → Ich möchte einen Kaffee |

## vocabulary

| Key | Rule | Example |
| --- | --- | --- |
| `kennen vs wissen` | kennen a person, place, or thing; wissen a fact or clause | Ich weiß ihn → Ich kenne ihn |
| `wenn vs als vs wann` | als: single past event; wenn: repeated or conditional; wann: question | Wenn ich Kind war → Als ich Kind war |
| `möchten vs mögen vs gern` | | Ich mag einen Kaffee (ordering) → Ich möchte einen Kaffee |
| `bekommen means receive` | False friend with become | Ich bekomme müde → Ich werde müde |
| `eine Entscheidung treffen` | Fixed collocation | eine Entscheidung machen → treffen |
| `einen Termin vereinbaren` | | einen Termin machen → vereinbaren |
| `lernen vs studieren` | studieren only at university | Ich studiere Deutsch (in a course) → Ich lerne Deutsch |
| `also means therefore` | False friend with English also | Ich also gehe (meaning too) → Ich gehe auch |

## register

| Key | Rule | Example |
| --- | --- | --- |
| `Sie in formal exchanges` | Customers, officials, strangers, doctors | Kannst du mir helfen? (to a waiter) → Können Sie mir helfen? |
| `du/Sie consistency` | Do not switch within one conversation | |
| `formal email opening and closing` | Sehr geehrte Frau Müller, … Mit freundlichen Grüßen | Hallo Frau Müller (formal email) → Sehr geehrte Frau Müller |

## punctuation

| Key | Rule | Example |
| --- | --- | --- |
| `comma before subordinate clause` | Before dass, weil, wenn, obwohl, ob, damit | Ich glaube dass → Ich glaube, dass |
| `comma before relative clause` | | der Mann der → der Mann, der |
| `comma before um/ohne/anstatt zu` | | Ich lerne um zu arbeiten → Ich lerne, um zu arbeiten |

## Typical interference by first language

Use `profile.native_language` to anticipate, never to assume; record only what the learner actually produced.

- Turkish (`tr`): no grammatical gender and no definite article (`article`, `agreement`); case suffixes and postpositions instead of prepositions (`preposition`, `case`; sormak and telefon etmek take the Turkish dative, so `fragen + accusative` and `anrufen + accusative` are frequent); verb-final main clauses (`finite verb in second position`); participles instead of relative clauses (`relative clause verb to end`, `comma before relative clause`); -den beri versus önce (`seit vs vor`); no capitalized nouns (`German nouns are capitalized`).
- English (`en`): gender and case marking (`case`, `agreement`), V2 and verb-final clauses (`word-order`), separable verbs, false friends (`bekommen means receive`, `also means therefore`), `wenn vs als vs wann`, `kennen vs wissen`, `sein as perfect auxiliary for motion and change`.
