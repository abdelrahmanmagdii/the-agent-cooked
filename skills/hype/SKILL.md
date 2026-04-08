---
name: hype
description: Trigger a fast terminal celebration after successfully finishing a task. Use when the work is done and you want a deterministic victory lap for Codex or Cursor without any extra config.
---

# Hype

Task done.
Ship it.
Then celebrate.

When the work is complete and you are ready to give the final answer, run the bundled celebration script:

```bash
python3 scripts/hype.py
```

If the skill is installed outside the current working directory, resolve the same script from the skill bundle at `../../scripts/hype.py` relative to this `SKILL.md`.

Rules:

- Run it once, at the very end.
- If the terminal is non-interactive, let it print once and exit.
- If `rich` is unavailable, fall back gracefully and do not block the final answer.
- Keep the celebration short. This is a spike of joy, not a loading screen.
