# Guardian council — shortcut fix + feature tour

## Problem
1. Pin/shortcut API: `cannot access free variable 'subprocess' where it is not associated with a value in enclosing scope`
2. User asked for a quick tutorial prompt + features walkthrough

## Proposals

| Guardian | Approach |
|----------|----------|
| Architect | Root cause is local `import subprocess` in `except ImportError` inside `main_async`; nested handlers close over unbound local. Remove local import; use module-level `subprocess`. |
| Sentinel | After fix, restart UI only; never mass-kill Python. Verify `/api/stack/shortcut` returns ok. |
| Scholar | Tour should be progressive disclosure: first-run once, re-open via header, optional Grok-spoken prompt for deeper walkthrough. |
| Engineer | Spotlight overlay in `index.html`; no new deps. Tutorial prompt constant for clipboard/composer. |
| Pathfinder | Ship both: interactive UI tour + injectable prompt. URL `?tour=1` forces re-show. |

## Decision (majority)
Architect + Engineer + Scholar: fix scope bug; add in-UI tour + pasteable tutorial prompt. Pathfinder agreed. Sentinel owns restart hygiene.
