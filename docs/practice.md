# Practise with DeutschDNA

[Back to the README](../README.md)


Invoke it with `/deutsch-dna` in Claude Code or `$deutsch-dna` in Codex, or write German and ask for feedback. No profile form or commands to memorize: the skill introduces itself in a few lines and gives you one small German task right away. If you already sent a text or requested a scene, it helps with that immediately.

### Your first minute

The welcome is brief. It uses your language when it knows it; after a bare `/deutsch-dna`, it starts in English and switches to the language you answer in:

```text
Hi! I'm DeutschDNA, your German practice partner. I correct what you write,
practise everyday situations with you, and remember the mistakes you repeat
and the hints that helped.

Let's start: what did you do today? Write one sentence in German.
Just starting? Complete: Ich heiße … (My name is …)

You can answer in your own language; I'll explain things in it.
```

There is no level test first. If your sentence has a mistake, you get a small hint instead of the answer, fix it yourself, and then use the same structure in a new situation. A correct first sentence gets a small step up instead, without a fake mistake or score. Your name and goals are optional. If you pause, the next session resumes where you left off. The full progress profile comes when you ask or at a later weekly review.

### Ask naturally

- **Correct my German.** Minimal correction, the reason, and the recurrence callback when a mistake comes back.
- **Let's review.** One due mistake at a time, each in a new situation, then the words due from your scenes.
- **Give me a hint.** Room to repair the sentence yourself; the help and outcome are remembered.
- **I have a meeting tomorrow.** A stated goal can shape a roleplay around a pattern you are practising.
- **Roleplay Restaurant.** Scenes for Alltag, Arbeit, Arzt, Wohnung, and Restaurant. No interruptions; at most three corrections in the debrief.
- **Let's practise words.** Words from your scenes come back after 1, 3, 7, 14, 30, and 60 days, each time in a new sentence you write yourself.
- **How am I doing?** The DeutschDNA profile, the root cause behind your weakest area, and a family drill for it.
- **That wasn't a mistake.** The agent reverts just that correction with `undo`, schedule included, or fixes the entry with `merge`, `rename`, or `forget`. A wrong merge can be undone too.

## Keep talking. Corrections come after.

Start with “Restoranda konuşalım” or `speak restaurant`. With the installed skill, you can use `/deutsch-dna speak restaurant` in Claude Code or `$deutsch-dna speak restaurant` in Codex.

```text
Kellner: Guten Abend. Haben Sie reserviert?
You:     Ja wir haben eine reservierung für zwei person.
Kellner: Auf welchen Namen?
```

The tutor stays in character and waits for your actual answers. Ordinary mistakes do not interrupt the scene. After roughly five minutes, or when you say “bitir”, it leaves the character and puts a short debrief in its reply: scene duration, up to three important corrections, useful vocabulary from the conversation, and any recurring patterns with counts from that scene. Saving the report is not the final step; the reply must show it. New words from the scene go into your word deck and come back in spaced reviews from the next day, each time in a new situation. If a report did not appear, “Son konuşmanın değerlendirmesini göster” retrieves the saved result without counting your mistakes again.

Try the complete scripted example through the real engine:

```bash
python scripts/demo.py --speak
```

The demo produces a 6m 42s scene from recorded timestamps, including four separate occurrences of the `Person → Personen` pattern. That is elapsed scene time, including both participants and pauses. The skill does not measure how long your microphone was active. Text works directly; host-provided speech transcripts can use the same flow, with spelling and punctuation excluded from speech feedback. Audio capture and pronunciation scoring are not included.
