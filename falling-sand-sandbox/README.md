# Falling Sand Sandbox

A classic falling-sand cellular automaton — sand piles up at its angle of repose, water finds its level and flows around obstacles, fire spreads through wood and burns out, sand sinks through water. Self-contained single HTML file, no dependencies.

```bash
start sandbox.html      # Windows
open sandbox.html       # macOS
xdg-open sandbox.html   # Linux
```

## Controls

Pick a material, then click and drag on the canvas to place it. Brush size is adjustable. Pause freezes the simulation without clearing it; Clear wipes the grid.

| Material | Behavior |
|---|---|
| Sand | Falls straight down; slides diagonally off a peak; sinks through water |
| Water | Falls, then flows sideways to find its level |
| Wall | Static, blocks everything |
| Wood | Static until adjacent to fire, then has a small per-tick chance to ignite |
| Fire | Spreads to adjacent wood, burns out after a fixed lifespan into smoke or nothing |

## How it works

The simulation is a grid of material IDs updated once per frame. Each cell's next state is decided by simple local rules — sand and water check the cell below (and diagonals) before moving; fire has a countdown and a chance to ignite orthogonal wood neighbors each tick. Rows are processed **bottom-to-top** specifically so a particle that falls into the row below (already handled this tick) never gets processed twice in the same frame — a classic bug in naive falling-sand implementations where a particle could fall multiple rows in a single step, or where a whole tick's worth of sand collapses at once instead of settling gradually. The left/right scan direction alternates by tick parity, and diagonal tie-breaks are randomized per-particle, both to avoid a visible directional bias (sand piles that always lean one way, water that always flows right first).

## Why it's built this way

The simulation core (`step()` and its per-material helper functions) is a pure function of the grid — no canvas or DOM references inside it at all. That's what made it possible to test the actual physics rigorously: the exact `<script>` block from this HTML file gets extracted verbatim and loaded into Node for testing (see below), so there's no separate "test version" of the logic that could quietly drift out of sync with what actually ships. Rendering and mouse/touch input are a thin layer on top that only exists in the browser half of the file.

## Testing

Before this was ever loaded in a browser, the extracted simulation core went through a Node.js test suite covering:

- **No double-falling**: a single sand particle moves exactly one row per tick in free fall — the specific thing bottom-to-top row processing exists to guarantee.
- **Conservation**: total sand/water count stays exactly constant across hundreds of ticks when no fire is involved (materials only move, they don't get created or silently deleted by a stray write).
- **Water spreads, sand piles**: a narrow stack of water dropped onto a floor ends up spread across many columns; sand does not.
- **Sand is denser than water**: in a walled-off vertical shaft (so water can't just flow away sideways instead), sand dropped above water ends up below it after settling — they swap through each other.
- **Fire ignites wood and burns out**: forced-deterministic ignition test (an RNG stub that always "succeeds") confirms wood adjacent to fire converts to fire; a separate test confirms fire started with a finite lifespan doesn't burn forever.
- **Fuzz test**: a randomized mixed-material 40×30 grid run for 150 ticks with every material value checked to stay in the valid range the whole time — catches stray out-of-bounds writes or index math errors that a hand-picked scenario might not exercise.

**One test design mistake worth mentioning, not just the passes:** the first version of the "sand sinks through water" test placed sand above water in an *open* 5-column grid and asserted sand would end up below water. It failed — but dumping the actual grid showed why: water reached the floor first (it started lower) and flowed sideways before sand ever got close enough to force a vertical collision, so they settled in the same row but different columns. That's correct simulation behavior, not a bug — the test's setup just didn't isolate the mechanic it was meant to check. Fixed by confining both materials to a one-column-wide walled shaft so water has nowhere to escape sideways, which properly forces the vertical interaction and confirmed the density-swap logic is correct.

All of the above was then re-confirmed live in-browser: painting sand produces the expected pyramidal piles with correct angle-of-repose sliding, water poured across the same area pools and levels around the sand, and fire placed next to a wood block measurably reduces the wood count over a few seconds as it burns — exercised with real mouse events, not just inspected in isolation.
