# agent-hype

Simple:
agent finishes task.
terminal throws party.

Works with Claude Code, Codex, and Cursor.

## Requirements

Need `python3`.
Need `rich`.

```bash
python3 -m pip install rich
```

## Install

### Shared skill

Install the shared `hype` skill from this repo:

```bash
npx skills add abdelrahmanmagdii/the-agent-cooked --skill hype
```

You can also test from a local checkout:

```bash
npx skills add /the-agent-cooked --skill hype
```

### Claude Code plugin

Install the Claude plugin from this repo to run the celebration on
`TaskCompleted`:

```bash
claude plugin install the-agent-cooked@abdelrahmanmagdii
```

## Test

Run the script directly:

```bash
python3 scripts/hype.py
```

If `rich` is unavailable, the script falls back to a plain completion message
and exits cleanly.

## Usage

- Claude Code: the plugin hook runs automatically when a task completes
- Codex and Cursor: use the shared skill/script setup in `skills/hype/SKILL.md`

## Files

- `.claude-plugin/hooks.json` wires Claude Code `TaskCompleted` to the celebration script
- `.claude-plugin/plugin.json` defines the Claude plugin package
- `skills/hype/SKILL.md` provides the shared skill instructions
- `scripts/hype.py` does the actual hype
