# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

No build step — open `index.html` directly in a browser:

```powershell
Start-Process index.html
```

## Architecture

Single-file project: all HTML, CSS, and JS lives in `index.html`. No dependencies, no bundler, no framework.

**Game state** (plain JS variables in `index.html`):
- `board` — flat 9-element array (`null | 'X' | 'O'`), indexed 0–8 left-to-right, top-to-bottom
- `current` — whose turn (`'X'` or `'O'`)
- `gameOver` — boolean
- `scores` — `{ X, O, D }` object, persists across "New Game" restarts

**Rendering** is a single `render()` call that rebuilds the entire DOM state from the `board` array. There is no partial update pattern — always call `render()` after mutating state.

**Win detection** checks `board` against the 8 hardcoded winning index triples in `WINS`.

## Color palette

| Token | Hex | Used for |
|---|---|---|
| Background | `#1a1a2e` | Page background |
| Cell | `#16213e` | Cell / score box background |
| Hover/win | `#0f3460` | Cell hover and win highlight |
| X / accent | `#e94560` | X player, heading, button |
| O / secondary | `#a8dadc` | O player, status text |
| Draw | `#f4a261` | Draw score |

## Git / GitHub — always commit and push

**Every session, every change — commit and push. No exceptions.**

- After every code change, run `git add -A`, commit with a descriptive message, and push to `origin master`
- A `Stop` hook in `.claude/settings.json` does this automatically after each Claude response
- If the hook hasn't fired or a manual commit is needed: `git add -A && git commit -m "<description>" && git push origin master`
- Never leave a session with uncommitted changes — the goal is that GitHub always reflects the current state

Remote: `https://github.com/abeshkc/abeshkc.git` — branch `master`.
