#!/usr/bin/env python3
"""
Terminal Wordle Clone
----------------------
A dependency-free (standard library only) Wordle clone. Two modes:
"daily" picks the same word for everyone on a given calendar date (like
the real thing); "practice" picks a fresh random word every run.

Run it:
    python wordle.py

Six guesses, five letters, colored feedback, an on-screen keyboard that
remembers what you've learned, and a shareable emoji result grid at the
end — same shape as the real game.
"""

import os
import sys
import random
import ctypes
from datetime import date

# Windows consoles frequently default to a legacy codepage (cp1252 and
# similar) rather than UTF-8 — piped/redirected output hits this too, not
# just interactive terminals. Without this, printing the emoji share grid
# (\U0001F7E9 etc.) raises UnicodeEncodeError and crashes the program right
# at the end of a finished game. reconfigure() with errors="replace" means
# worst case an unsupported glyph prints as "?" instead of crashing.
def _make_stdout_safe():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


_make_stdout_safe()

# --------------------------------------------------------------------------
# word list — a curated set of common 5-letter English words. Used as both
# the answer pool and the valid-guess pool (see README for why that's a
# deliberate simplification rather than a full dictionary).
# --------------------------------------------------------------------------

WORDS = sorted(set("""
about above abuse actor acute admit adopt adult after again agent agree
ahead alarm album alert alike alive allow alone along alter among anger
angle angry apart apple apply arena argue arise array aside asset avoid
awake award aware badly baker based basic basis beach began begin being
below bench birth black blade blame blank blast blind block blood board
boost booth bound brain brand bread break breed brief bring broad broke
brown build built bunch burst cabin canal candy cargo carry catch cause
chain chair chalk charm chart chase cheap check chess chest chief child
choir chose civil claim class clean clear climb clock close cloud coach
coast could count court cover craft crash crazy cream crime cross crowd
crown crude curve cycle daily dance dealt death debut delay depth diary
diner dirty doubt dozen draft drama drank dream dress drift drill drink
drive drove dying eager early earth eight elite empty enemy enjoy enter
entry equal error event every exact exist extra faith false fault favor
fence fewer fiber field fifth fifty fight final first fixed flame flash
fleet floor fluid focus force forth forty forum found frame fresh front
frost fruit fully funny giant given glass globe glory grace grade grand
grant grape grass great green greet grief grill gross group grown guard
guess guest guide habit happy harsh heart heavy hobby holds honor horse
hotel house human humor hurry ideal image imply index inner input issue
ivory jelly joint judge juice known label labor large laser later laugh
layer learn least leave legal level light limit linen lodge logic loose
lower loyal lucky lunar lunch lying magic major maker march match maybe
mayor medal media melon mercy merit metal meter might minor minus mixed
model moist moral motor mount mouse mouth movie music naval never newly
night noise north noted novel nurse ocean offer often opera orbit order
organ other otter outer owner ozone paint panel panic paper party pause
peace pearl phase phone photo piano pilot pitch pizza place plain plane
plant plate point pound power press price pride prime print prior prize
proof proud prove pulse pupil purse queen query quick quiet quilt quite
radio raise range rapid ratio reach ready realm rebel refer relax renew
reply resin retro rider ridge right rigid rival river robot rocky roman
rough round route royal rural sauce scale scare scarf scene scope score
scout sense serve seven shade shake shall shame shape share sharp shelf
shell shift shine shirt shock shoot short shown sight silly since sixth
sixty skill slate sleep slice slide small smart smile smoke snack solid
sorry sound south space spare speak speed spend spent spine spite split
spoke sport spray squad stack staff stage stake stall stamp stand stark
start state steam steel stern stick stiff still stock stone story strip
study stuff style sugar suite sunny super swear sweet swept swift swing
sword table taste teach thank theft their there thick thing think third
those three throw thumb tiger tight timer title toast today token topic
touch tough tower toxic trace track trade trail train trait treat trend
trial tribe trick truck truly trust truth twice twist ultra uncle under
union unity until upper upset urban usage usual valid value venue video
vinyl viral virus vista vital vivid vocal voice waste watch water weary
wedge weigh weird wheat wheel where which while white whole whose widen
width witty woman world worry worth would wound woven wrist write wrong
yield young youth
""".split()))

WORD_LEN = 5
MAX_GUESSES = 6
assert all(len(w) == WORD_LEN for w in WORDS), "word list contains a non-5-letter entry"

# --------------------------------------------------------------------------
# terminal color setup (same pattern as the roguelike in this repo)
# --------------------------------------------------------------------------

def enable_ansi_on_windows():
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


USE_COLOR = enable_ansi_on_windows()

BG_GREEN = "42"
BG_YELLOW = "43"
BG_GRAY = "100"
FG_BLACK = "30"
FG_WHITE = "97"

EMOJI = {"green": "\U0001F7E9", "yellow": "\U0001F7E8", "gray": "⬜"}


def tile(letter, status):
    if not USE_COLOR:
        return f"[{letter.upper()}]"
    bg = {"green": BG_GREEN, "yellow": BG_YELLOW, "gray": BG_GRAY}[status]
    return f"\033[{bg};{FG_BLACK}m {letter.upper()} \033[0m"


# --------------------------------------------------------------------------
# scoring — the part that's easy to get subtly wrong with duplicate letters
# --------------------------------------------------------------------------

def score_guess(secret, guess):
    """Return a list of 'green' / 'yellow' / 'gray', one per letter of
    `guess`, using the standard two-pass Wordle algorithm: greens are
    resolved first and consumed from the pool of secret letters available
    for yellow-matching, so a repeated letter in the guess only lights up
    yellow as many times as it *actually* appears unmatched in the secret."""
    secret = secret.lower()
    guess = guess.lower()
    result = [None] * WORD_LEN
    remaining = {}

    for i in range(WORD_LEN):
        if guess[i] == secret[i]:
            result[i] = "green"
        else:
            remaining[secret[i]] = remaining.get(secret[i], 0) + 1

    for i in range(WORD_LEN):
        if result[i] is not None:
            continue
        ch = guess[i]
        if remaining.get(ch, 0) > 0:
            result[i] = "yellow"
            remaining[ch] -= 1
        else:
            result[i] = "gray"

    return result


# --------------------------------------------------------------------------
# keyboard state
# --------------------------------------------------------------------------

KEYBOARD_ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
STATUS_RANK = {"gray": 0, "yellow": 1, "green": 2, None: -1}


def update_keyboard(keyboard, guess, result):
    for ch, status in zip(guess.lower(), result):
        if STATUS_RANK[status] > STATUS_RANK.get(keyboard.get(ch), None):
            keyboard[ch] = status


def render_keyboard(keyboard):
    lines = []
    for row in KEYBOARD_ROWS:
        parts = []
        for ch in row:
            status = keyboard.get(ch)
            if status is None:
                parts.append(f" {ch.upper()} " if not USE_COLOR else f"\033[{FG_WHITE}m {ch.upper()} \033[0m")
            else:
                parts.append(tile(ch, status))
        lines.append(" ".join(parts))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# word selection
# --------------------------------------------------------------------------

def pick_daily_word(today=None):
    """Deterministic per calendar date, same idea as the real game's
    word-of-the-day — everyone who plays on the same date gets the same
    word, without needing any server or shared state."""
    d = today or date.today()
    seed = int(d.strftime("%Y%m%d"))
    return random.Random(seed).choice(WORDS)


def pick_practice_word():
    return random.choice(WORDS)


# --------------------------------------------------------------------------
# game loop
# --------------------------------------------------------------------------

def read_guess():
    while True:
        raw = input("> ").strip().lower()
        if raw == "q":
            return None
        if len(raw) != WORD_LEN or not raw.isalpha():
            print(f"Enter a {WORD_LEN}-letter word (or 'q' to quit).")
            continue
        if raw not in WORDS:
            print("Not in word list — try another guess.")
            continue
        return raw


def share_grid(history):
    lines = []
    for _, result in history:
        lines.append("".join(EMOJI[s] for s in result))
    return "\n".join(lines)


def play(secret, mode_label):
    print(f"\nWordle ({mode_label}) — {MAX_GUESSES} guesses, {WORD_LEN} letters. 'q' to quit.\n")
    history = []
    keyboard = {}
    won = False

    while len(history) < MAX_GUESSES:
        guess = read_guess()
        if guess is None:
            print("Gave up. The word was:", secret.upper())
            return
        result = score_guess(secret, guess)
        history.append((guess, result))
        update_keyboard(keyboard, guess, result)

        print()
        for g, r in history:
            print(" ".join(tile(ch, s) for ch, s in zip(g, r)))
        print()
        print(render_keyboard(keyboard))
        print()

        if guess == secret:
            won = True
            break

    if won:
        print(f"Solved in {len(history)}/{MAX_GUESSES}!")
    else:
        print(f"Out of guesses. The word was: {secret.upper()}")

    print("\nShare grid:")
    print(f"Wordle-clone {len(history)}/{MAX_GUESSES}" if won else f"Wordle-clone X/{MAX_GUESSES}")
    print(share_grid(history))


def main():
    print("=== TERMINAL WORDLE CLONE ===")
    print("1) Daily word (same for everyone today)")
    print("2) Practice (random word each run)")
    choice = input("Choose 1 or 2: ").strip()

    if choice == "2":
        play(pick_practice_word(), "practice")
    else:
        play(pick_daily_word(), f"daily, {date.today().isoformat()}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye.")
        sys.exit(0)
