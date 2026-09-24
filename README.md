# DeutschDNA

> You learn German. Your tutor remembers what helped.

**Yesterday, you needed a hint. Today, you got it right on your own.**

![Four moments with DeutschDNA: your own mistake, a helpful hint, a fresh exercise, and next-day unprompted use](demo/learning-loop.gif)

[View the final moment without animation](demo/learning-loop.png)

**Local JSON · No extra API key · No server · No database**

DeutschDNA is a German coaching skill for Claude Code, Codex, and other agents that read the Agent Skills format. Your existing model teaches. A small Python runtime remembers your mistakes, the help you used, and the sentences that show your progress between sessions.

## The moment you feel it

You write something real. Your tutor gives you room to repair one small mistake. The next day, it notices the same structure in your own writing:

```text
With a hint
„Ich spreche mit meinem Chef.“

Later, unprompted
„Wir haben mit unseren Kunden gesprochen.“ ✓
```

Your old sentence. The hint that helped. A different sentence you produced without it. **Your progress has receipts.**

The demo uses scripted learner inputs. The engine stores the actual attempts and produces the dated comparison only when a later, fresh, unaided use meets its evidence checks. The GIF is rendered from those records.

## You practise. Your tutor adapts.

| You | Your tutor |
| --- | --- |
| Write about your day, a message, or something you need to say. | Responds to the meaning and tracks the root cause of a real mistake. |
| Repair one sentence with a small cue. | Remembers the exact hint and how the attempt went. |
| Try the same structure in a new situation. | Checks whether you can use it without help. |
| Return for another conversation. | Reuses relevant context, keeps useful hints in reserve, and notices your own correct uses. |

Tell it about an upcoming conversation with your boss, and a roleplay can practise that goal using a pattern you are working on. Ask for a direct correction, and it gives you one. During roleplay, ordinary corrections wait until the debrief.

The first session gives you a small, visible win. Spaced reviews follow in new situations. A copied correction or an early practice attempt cannot advance the mastery ladder. The coach remembers observed teaching outcomes; it does not retrain the model or assign you a permanent learning style.

## See it in one command

```bash
python scripts/demo.py --learning-loop
```

This replays the story above in a fresh demo directory. Python 3.10+ is all you need; there are no runtime packages or extra API credentials to configure.

For the longer journey—root causes, spaced reviews, mastery, and an old mistake returning months later—run `python scripts/demo.py`.

<details>
<summary><strong>Watch the four-month memory demo</strong></summary>

![A four-month example of DeutschDNA tracking related errors, reviews, mastery, and a returning mistake](demo/deutschdna.gif)

When a pattern returns, DeutschDNA can recall the pinned first sentence and the progress recorded before the recurrence. It brings the pattern back into practice. The original sentence and important teaching milestones survive the rolling history limits.

Both stories use scripted learner inputs and real engine state. Scores describe tracked patterns, not overall German proficiency. Older history that was already removed before upgrading cannot be recovered.

</details>

## Install

Clone this repository into the skill location for your agent. The directory must contain `SKILL.md`.

```text
# Claude Code, personal (all projects)
~/.claude/skills/deutsch-dna/

# Claude Code, one project
.claude/skills/deutsch-dna/

# Codex, repository-scoped
.agents/skills/deutsch-dna/
```

See the official [Claude Code skill guide](https://code.claude.com/docs/en/skills) and [Codex skill guide](https://developers.openai.com/codex/build-skills) for discovery rules. Python 3.10+ is required; nothing needs to be installed.

## Use it

Invoke it with `/deutsch-dna` in Claude Code or `$deutsch-dna` in Codex, or write German and ask for feedback. No profile form or commands to memorize: the skill explains itself in a familiar language, asks one easy question, and starts a small German task. If you already sent a text or requested a scene, it helps with that immediately.

### Your first minute

The welcome is brief and adapted to your explanation language. For example:

```text
Hi! I'm DeutschDNA, your German practice partner.

We can have short conversations, correct your writing, and practise everyday
situations. I remember recurring mistakes and the hints that helped you.

Just write normally; you don't need to learn commands.

How would you describe your German: just starting, know a little,
or comfortable having a conversation?
```

“Just starting” leads to one tiny phrase with its meaning, such as `Ich heiße …` (“My name is …”), for you to personalize. “Know a little” leads to one or two sentences about your day. “I'm not sure” is welcome too; you do not need a CEFR level to begin. Your name and goals are optional.

After your answer, you get one useful piece of feedback and a natural next question. A correct first sentence completes the introduction without creating a fake mistake or score. If you pause, the next session resumes where you left off. The full progress profile comes when you ask or at a later weekly review.

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

## The CLI

The agent drives the CLI; you can use it directly too. Every command prints JSON, compact when an agent reads it and indented in your terminal; `show` returns a pattern's full history. `recap`, `summary`, `due`, `show`, `vocab-due`, and `vocab-list` also take `--format text` for German cards, and `list --format text` prints a table of the pattern keys.

```bash
python scripts/deutsch_dna.py init --name "Ahmet" --level B2 --native-language tr
python scripts/deutsch_dna.py record --original "Ich spreche mit mein Chef." --corrected "Ich spreche mit meinem Chef." --category case --pattern "mit + dative" --rule "mit always governs the dative"
python scripts/deutsch_dna.py summary --format text
```

| Command | What it does |
| --- | --- |
| `recap` | The session opener; `--format card` prints the German board of patterns in progress |
| `record` | File a mistake under its root cause, or count a recurrence; the reply says whether the correction was minimal |
| `observe` | Count a correct, unprompted use of a tracked pattern |
| `coach` | Remember an actual practice attempt and the hint used, without changing the review schedule |
| `due`, `grade` | Spaced-repetition reviews |
| `summary` | The DeutschDNA profile with root causes |
| `show` | The journey of one pattern |
| `list`, `undo`, `forget`, `merge`, `rename` | Inspect and repair the memory; `undo` also reverts a merge |
| `speak`, `roleplay-start` | Begin a scene with corrections deferred to the end |
| `roleplay-turn`, `roleplay-stop` | Save actual turns and freeze scene duration before feedback |
| `roleplay-vocab`, `roleplay-finish`, `roleplay-show` | Source-backed vocabulary and the session debrief |
| `vocab-due`, `vocab-grade` | Spaced reviews of the words from your scenes |
| `vocab-list`, `vocab-undo`, `vocab-forget` | Your word deck, and repairs to it |

State lives in `~/.deutschdna`; set `DEUTSCHDNA_HOME` or pass `--home` before the command to use another directory. Each command locks that directory, so an agent can run several commands in parallel without losing a write. The full contract, including idempotency and scoring, is in [references/cli-contract.md](references/cli-contract.md).

Reviews require the actual new task and learner answer:

```bash
python scripts/deutsch_dna.py grade m_... --result pass --prompt "Dein Verkehrsmittel ist der Bus. Wie kommst du zur Arbeit?" --answer "Ich fahre mit dem Bus."
```

The engine rejects early reviews, reused prompts, copied answers, and passes with hints. Before the due time, use `coach` for practice. Save a learner-stated goal with `init --goal "Morgen möchte ich einen Termin mit meinem Chef klären."`; roleplay combines a relevant goal with a due or active pattern. See [the learning loop](references/learning-loop.md) for the complete conversation flow.

## Regenerate the demo GIF

Render the opening story and its static final frame from the same learning-loop demo state:

```bash
python -m pip install pillow
python scripts/render_demo_gif.py --story learning-loop
```

This writes `demo/learning-loop.gif` and `demo/learning-loop.png`. Pillow is only needed to render these assets. To regenerate the four-month GIF, run `python scripts/render_demo_gif.py --story history`; [`demo/deutschdna.tape`](demo/deutschdna.tape) also renders that CLI story with [VHS](https://github.com/charmbracelet/vhs):

```bash
vhs demo/deutschdna.tape
```

The two history renderers write `demo/deutschdna.gif`.

## Test

```bash
python -m unittest discover -s tests -v
```

## Roadmap

- Planned: exam modes for Goethe B1/B2, telc B1/B2, and telc Deutsch Beruf
- Exploring: voice practice, pronunciation fingerprint, local dashboard

## License

MIT
