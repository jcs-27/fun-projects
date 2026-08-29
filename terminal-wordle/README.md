# Terminal Wordle Clone

A dependency-free (Python standard library only) Wordle clone. Six guesses, five letters, colored feedback, an on-screen keyboard that remembers what you've learned, and a shareable emoji result grid at the end.

```bash
python wordle.py
```

## Two modes

1. **Daily** — the same word for everyone who plays on a given calendar date, exactly like the real game. No server, no shared state needed: the date itself deterministically seeds which word gets picked.
2. **Practice** — a fresh random word every run.

## How to play

Type a 5-letter word and press Enter. 🟩 = right letter, right spot. 🟨 = right letter, wrong spot. ⬜ = not in the word. Guesses have to be real words from the built-in list — a guess that isn't recognized doesn't cost you a turn, it just asks again. `q` at any point gives up and reveals the word.

## Why it's built this way

- **The scoring algorithm is the one part of a Wordle clone that's genuinely easy to get subtly wrong**, specifically around duplicate letters (what happens when the guess has two of a letter but the secret only has one, or vice versa, in various position combinations). It's implemented as the standard two-pass algorithm: resolve every exact-position green first, then walk the guess again and hand out yellows only from what's *left over* in the secret after greens are removed — so a repeated letter in your guess can't light up more yellows than the secret actually has left to give. This was verified against five hand-derived test cases (including the classic "secret has 2 of a letter, guess has 2 in the wrong spots" scenario) before being trusted, not just eyeballed.
- **The word list doubles as both the answer pool and the valid-guess pool** — a deliberate simplification versus the real game, which uses a much larger separate dictionary just for accepting guesses (thousands of valid words that are never themselves possible answers). Here, if it's not one of the ~580 curated common words in `WORDS`, it won't be accepted as a guess either. Documented here rather than left as a silent surprise the first time a reasonable word gets rejected.

## Bug found and fixed during testing

A full scripted playthrough (piped input simulating a complete losing game, to exercise the end-of-game share grid) crashed with `UnicodeEncodeError` right at the very last `print()` — after playing all 6 guesses. The cause: Windows consoles frequently default to a legacy codepage (`cp1252` in this case, confirmed from the traceback) rather than UTF-8, and piped/redirected output hits the same limitation, not just interactive terminals. The share grid's emoji characters (🟩🟨⬜) simply don't exist in that codepage, so writing them raised an exception instead of printing anything. Fixed by reconfiguring `stdout`/`stderr` to UTF-8 with `errors="replace"` at the top of the script — worst case, on a genuinely incapable terminal, an unsupported glyph shows as `?` instead of taking the whole program down after a full game's worth of guesses. Re-ran the exact same scripted scenario afterward to confirm it actually completes cleanly now, not just that the exception message changed.
