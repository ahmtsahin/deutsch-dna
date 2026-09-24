# Tests and demo assets

[Back to the README](../README.md)

Run the commands below from the repository root. DeutschDNA's runtime uses only Python 3.10+ and the standard library. Pillow is a contributor dependency for rendering the README assets.

## Unit tests

```bash
python -m unittest discover -s tests -v
```

The tests cover the engine. The first-session check exercises the skill in a real agent: a small Claude model plays a learner, and the script checks the transcript and saved records.

```bash
python evals/first_session.py --host claude
python evals/first_session.py --host codex --model gpt-6-astra
```

It uses a copy of the skill called `deutsch-dna-smoke` and isolated state, and fails if `~/.deutschdna` changes. These runs make real model calls through the installed hosts and take a few minutes. `--setup none` checks the experience before permission setup; `--runs 3` repeats the session.

## Render the README stories

```bash
python -m pip install pillow
python scripts/render_demo_gif.py --story learning-loop
python scripts/render_demo_gif.py --story history
python scripts/render_demo_gif.py --story conversation
python scripts/render_demo_gif.py --story board
```

Each story command writes a GIF and a static PNG under `demo/`; `board` writes only `demo/board.png`, a 1600 × 900 image of the four-month learner's session board that also works as a social preview. Its review ladders and comeback markers are drawn, so any monospaced font renders them. Pass `--frames-dir demo-home/frames` to inspect every complete scene at its full size and at the 309 px width used in the mobile review. Text that exceeds the layout raises an error instead of being silently clipped or shrunk.

The learning-loop story opens on the result and lasts 11 seconds. The history story opens on the returning mistake and lasts 9 seconds. Both use scripted learner inputs and actual engine state, with dates anchored to the render day. The conversation replay lasts 16 seconds and reveals each learner message before its tutor reply.

The first full scene is saved as the static alternative. Source images are 720 × 800; the main sentence type is 42 px, which displays at about 18 px when the image is 309 px wide. Auxiliary labels are smaller. Plain text descriptions and the conversation transcript remain available outside the images.

The terminal version of the four-month story can also be rendered with [VHS](https://github.com/charmbracelet/vhs):

```bash
vhs demo/deutschdna.tape
```

It writes `demo/history-terminal.gif`, leaving the README's compact story intact.

## Record a real conversation

The checked-in [capture](../demo/conversation.json) contains actual Claude Code tutor replies and selected saved learning evidence. The learner inputs are scripted. A fresh second chat reads the state written by the first; both happen on the same day. No date is advanced. The GIF is a transcript replay with shortened timing, not a screen capture or a claim of next-day learning evidence.

To capture another run with your existing Claude Code login:

```bash
python evals/record_conversation.py --output demo-home/new-conversation.json
```

This makes three real host calls. It creates a project-local skill copy and an isolated progress folder under the ignored `demo-home/` directory. Global settings and the real learner memory are not edited; the script checks that `~/.deutschdna` stays unchanged. Raw host logs stay local, while the export contains the tutor's complete words and selected evidence. Existing output files are never overwritten.

If interrupted, reuse the printed recording folder:

```bash
python evals/record_conversation.py --resume-run demo-home/conversation-XXXXXXXX --output demo-home/new-conversation.json
```

Completed turns are read from their logs rather than requested again. Review the new recording before publishing it. The renderer verifies every displayed excerpt against its source text; a different tutor response may require selecting new excerpts in `collect_conversation_screens` before rendering:

```bash
python scripts/render_demo_gif.py --story conversation --transcript demo-home/new-conversation.json --output demo-home/new-conversation.gif
```
