# Terminal Roguelike Dungeon Crawler

A self-contained, dependency-free (Python standard library only) turn-based roguelike. Procedurally generated dungeons, permadeath, five levels deep, one Amulet waiting at the bottom.

```bash
python dungeon.py
```

## How to play

Commands are typed + Enter (no raw terminal mode, so it works identically in any shell — PowerShell, cmd, bash, whatever):

| Key | Action |
|---|---|
| `w` `a` `s` `d` | Move — or attack, if a monster is standing in that direction |
| `i` | Drink a potion (heals 8 HP, capped at max) |
| `q` | Quit |

Walk into gold (`$`), a potion (`!`), or a weapon (`/`) to pick it up automatically. Find the stairs (`>`) to descend. The goal is the Amulet (`A`) waiting at depth 5 — grab it and you win. Die at any point along the way and it's over — no respawns, no save states, just a final stat line.

## What's procedurally generated

Each level is built from scratch: 8 non-overlapping rectangular rooms of random size, connected by L-shaped corridors, populated with monsters and loot that scale with depth. Monster count, monster toughness, gold amounts, and weapon availability all increase the deeper you go. Rooms you've stood in stay lit on the map (explored); corridors only reveal a small radius around you as you walk them — a lightweight version of the "lit rooms, dark corridors" visibility classic roguelikes use.

## Why it's built this way

- **Turn-based, not real-time.** The player acts, then every monster acts once (attack if adjacent, chase if within range, wander otherwise). This keeps the whole thing deterministic and easy to reason about — no timing races, no frame budget, unlike the Wokwi embedded projects in this portfolio where that distinction actually matters for real hardware.
- **No third-party dependencies.** No `curses` (which isn't in the standard Windows Python install), no `colorama` — just `os`, `random`, and a small `ctypes` call to turn on ANSI color in older Windows terminals, wrapped so it degrades to plain text if that fails. Clone it and run it, nothing to `pip install`.
- **Retry-based, exclusion-aware item placement.** Every spawn (monster, gold, potion, weapon) is checked against a running `occupied` set before it's placed, with a bounded number of retries if a random tile is already taken — see "Bugs found and fixed" below for why this matters more than it sounds like it should.

## Bugs found and fixed during testing

This wasn't left to "looks right, ship it" — I wrote a scripted test harness (randomized-input fuzzing across dozens of seeds, plus targeted tests that force specific scenarios like a full descent to depth 5) before calling it done. It caught two real bugs a casual playtest could easily have missed:

1. **Combat crashed the instant the player attacked anything.** The original single `combat()` method picked which defense stat to read (`"def"` for a monster vs. `"defense"` for the player) with a ternary that had the condition backwards. Monster-attacks-player accidentally worked anyway (it was reading the *attacking* monster's own `"def"` key by coincidence, not the player's defense — so damage was being computed wrong even when it didn't crash), but player-attacks-monster raised `KeyError: 'defense'` immediately, every time, because monster dicts don't have that key. A random-move fuzz test alone didn't catch this — the player has to actually land on a monster's tile, which 80 random moves in a big dungeon didn't happen to trigger. A targeted test that forced that exact scenario caught it in one run. Fixed by splitting it into two explicit methods, `player_attacks()` and `monster_attacks()`, each reading the correct stat with no ternary to get backwards.
2. **Loot could spawn on top of a monster — or silently overwrite the depth-5 Amulet.** Gold placement checked an `occupied` set; potion and weapon placement didn't check anything at all. On an unlucky seed, a potion could land on the exact tile already holding the Amulet, and since both are just `self.items[pos] = ...` dict assignments, the second write would erase the first — making that seed's game unwinnable with no error, no warning, just a dungeon with no Amulet in it. Fixed with a single retry-based `place()` helper that all four item types now go through, checked against monsters, the stairs, the player's start tile, and each other. Verified against 300 regenerated levels with zero collisions afterward.

Both are documented here rather than just silently fixed, on the theory that *how* a bug was found is worth as much as the fix itself.
