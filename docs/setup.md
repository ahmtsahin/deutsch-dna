# Installation and permissions

[Back to the README](../README.md)


Clone the repository into your agent's skill folder. Keep the folder name `deutsch-dna`: it must match the skill's name.

Claude Code, for all your projects:

```bash
git clone https://github.com/ahmtsahin/deutsch-dna.git "$HOME/.claude/skills/deutsch-dna"
```

Codex, for all your projects:

```bash
git clone https://github.com/ahmtsahin/deutsch-dna.git "$HOME/.agents/skills/deutsch-dna"
```

The commands work in macOS and Linux terminals and in PowerShell. For a single project, clone into `.claude/skills/deutsch-dna` (Claude Code) or `.agents/skills/deutsch-dna` (Codex) inside that project instead. To update later, run `git pull` in the skill folder.

See the official [Claude Code skill guide](https://code.claude.com/docs/en/skills) and [Codex skill guide](https://developers.openai.com/codex/skills/) for discovery rules. Python 3.10+ is required; no Python packages are needed for the runtime. On Windows, the `py -3` launcher works where `python` only opens the Microsoft Store.

### Let it save without asking

The skill keeps your progress in `~/.deutschdna` through a small Python helper. Depending on your host permissions, helper calls may ask for approval or the sandbox may block the state folder. One optional setting removes those interruptions.

**Claude Code** asks before helper calls, and “don't ask again” applies only to the current project. To stop the questions everywhere, add these rules to `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(python *deutsch_dna.py*)",
      "PowerShell(python *deutsch_dna.py*)",
      "Read(~/.claude/skills/deutsch-dna/**)"
    ]
  }
}
```

Use `python3` or `py` instead of `python` if that is how your system runs Python. These rules allow Python commands that mention the helper, so keep them only if you trust the skill folder.

**Codex** runs commands in a sandbox that may write only to your project. From the cloned skill folder, create the state directory by running `python scripts/deutsch_dna.py recap` in a normal terminal, and then list it as a writable root in `~/.codex/config.toml`:

```toml
[sandbox_workspace_write]
writable_roots = ["/Users/you/.deutschdna"]   # Windows: ['C:\Users\you\.deutschdna']
```

The folder must exist first; a writable root that does not exist yet cannot be created from inside the sandbox. Without this setting, Codex needs your approval to run the helper outside the sandbox.

## Already installed in an older Codex location?

Some Codex installations also load `~/.codex/skills`. The quick start uses the current documented `~/.agents/skills` location. Keep one copy of the skill to avoid duplicate entries. If the skill does not appear after installation, restart Codex.

## Run the examples from the skill folder

After cloning, change into the location you used before running any `python scripts/...` example:

```bash
# Codex
cd "$HOME/.agents/skills/deutsch-dna"

# Claude Code
cd "$HOME/.claude/skills/deutsch-dna"
```

State is stored in `~/.deutschdna`. To use a different location, set `DEUTSCHDNA_HOME` or place `--home PATH` before the command.
