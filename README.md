# Fun Projects

Small, no-agenda builds — no automotive/embedded portfolio angle, just enjoyable things to make and play with. Companion to [embedded-systems-lab](https://github.com/jcs-27/embedded-systems-lab), which *is* the portfolio-building side of this GitHub.

| Project | What it is |
|---|---|
| [Terminal Roguelike Dungeon Crawler](./terminal-roguelike-dungeon) | Turn-based, procedurally generated, permadeath. Pure Python standard library, no dependencies. |
| [Flow Field](./generative-flow-field) | Perlin-noise particle art in a single self-contained HTML file. Open it and watch it run. |
| [Terminal Wordle Clone](./terminal-wordle) | Daily-word or practice mode, colored feedback, on-screen keyboard, shareable emoji grid. Pure Python. |
| [Fractal Explorer](./fractal-explorer) | Interactive Mandelbrot viewer — zoom toward cursor, pan, live Julia-set preview on hover. Single HTML file. |

All four were tested before being pushed, not just written and shipped — see each project's README for exactly what was checked. Real bugs a proper test pass caught along the way: a combat crash and a loot-placement bug in the dungeon crawler that could silently make a run unwinnable, a `UnicodeEncodeError` crash at the very end of a finished Wordle game on non-UTF-8 Windows consoles, and (in the fractal explorer's case) a testing-environment constraint — a hidden preview pane stalling the render's own timer — that was worked around with a standalone Node.js math check plus direct canvas execution, and which also surfaced a real defensive fix worth shipping regardless.
