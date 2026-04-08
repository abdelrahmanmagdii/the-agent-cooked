# the-agent-cooked

Simple:
agent finishes task.
terminal throws party.

Works with Claude Code directly, plus Codex and Cursor through a shared skill.

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

### Claude Code plugin

Add the marketplace, then install the plugin to run the celebration when
Claude finishes a response:

```bash
claude plugin marketplace add abdelrahmanmagdii/the-agent-cooked
claude plugin install the-agent-cooked@the-agent-cooked
```

## Test

Run the script directly:

```bash
python3 scripts/the-agent-cooked.py
```

If `rich` is unavailable, the script falls back to a plain completion message
and exits cleanly.

## Usage

- Claude Code: the plugin hook runs automatically when Claude stops after a response
- Codex and Cursor: install the shared skill and use the `skills/hype/SKILL.md` workflow
- Other CLIs: not guaranteed. `npx skills` only works for agents that support the Skills format

## Files

- `.claude-plugin/hooks.json` wires Claude Code stop events to the celebration script
- `.claude-plugin/plugin.json` defines the Claude plugin package
- `skills/hype/SKILL.md` provides the shared skill instructions
- `scripts/the-agent-cooked.py` does the actual celebration
