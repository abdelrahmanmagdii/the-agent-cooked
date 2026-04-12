# the-agent-cooked

Simple:
agent finishes task.
terminal throws party.

Works with Claude Code and Codex directly, plus Cursor through a shared skill.

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

Add the marketplace, then install the plugin to run the celebration on the
main completion event:

```bash
claude plugin marketplace add abdelrahmanmagdii/the-agent-cooked
claude plugin install the-agent-cooked@the-agent-cooked
```

### Codex CLI plugin

Codex plugin packaging lives in `.codex-plugin/`.

To make completion celebrations actually fire in current Codex CLI builds, the
repo also includes:

- `.codex/config.toml` to enable the `codex_hooks` feature
- `.codex/hooks.json` to run the celebration script on `Stop`
- `.agents/plugins/marketplace.json` so the repo can be surfaced as a local
  Codex plugin marketplace entry

## Test

Run the script directly:

```bash
python3 scripts/the-agent-cooked.py
```

If `rich` is unavailable, the script falls back to a plain completion message
and exits cleanly.

## Usage

- Claude Code: the plugin hook runs automatically when the main agent finishes
- Codex CLI: `.codex/hooks.json` runs the celebration when the main agent finishes
- Cursor: install the shared skill and use the `skills/hype/SKILL.md` workflow
- Other CLIs: not guaranteed. `npx skills` only works for agents that support the Skills format

## Files

- `.claude-plugin/hooks.json` wires Claude Code completion hooks to the celebration script
- `.claude-plugin/plugin.json` defines the Claude plugin package
- `.codex/config.toml` enables Codex hooks for this repo
- `.codex/hooks.json` wires Codex `Stop` to the celebration script
- `.codex-plugin/hooks.json` wires Codex completion hooks to the celebration script
- `.codex-plugin/plugin.json` defines the Codex plugin package
- `.agents/plugins/marketplace.json` exposes the repo as a local Codex plugin entry
- `hooks/hooks.json` is the shared source hook definition used by the plugin packages
- `skills/hype/SKILL.md` provides the shared skill instructions
- `scripts/the-agent-cooked.py` does the actual celebration
