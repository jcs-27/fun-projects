#!/usr/bin/env python3
"""
Terminal Roguelike Dungeon Crawler
-----------------------------------
A self-contained, dependency-free (standard library only) turn-based
roguelike. Procedurally generated dungeons, permadeath, five levels deep,
one Amulet waiting at the bottom.

Run it:
    python dungeon.py

Controls (typed + Enter, so it works in any terminal, no raw input mode):
    w / a / s / d   move / attack (walk into a monster to hit it)
    i               inventory — drink a potion
    q               quit

Goal: survive to depth 5 and grab the Amulet. Good luck.
"""

import os
import sys
import random
import ctypes

# --------------------------------------------------------------------------
# terminal setup
# --------------------------------------------------------------------------

def enable_ansi_on_windows():
    """Modern Windows terminals support ANSI color, but cmd.exe needs the
    virtual-terminal-processing flag turned on first. Best-effort only —
    if this fails (older Windows, redirected output), we just fall back to
    plain text further down via USE_COLOR."""
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        return bool(kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING))
    except Exception:
        return False


USE_COLOR = enable_ansi_on_windows()


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def c(text, code):
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


COLOR = {
    "wall": "90", "floor": "37", "player": "1;96", "monster": "1;31",
    "gold": "1;33", "potion": "1;35", "weapon": "1;36", "stairs": "1;32",
    "amulet": "1;95;5", "hud": "1;37", "log": "37", "dim": "2;37",
}

# --------------------------------------------------------------------------
# map / dungeon generation
# --------------------------------------------------------------------------

MAP_W, MAP_H = 58, 18
MAX_DEPTH = 5
WALL, FLOOR = "#", "."


class Room:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    def center(self):
        return (self.x + self.w // 2, self.y + self.h // 2)

    def intersects(self, other, padding=1):
        return (self.x - padding < other.x + other.w and
                self.x + self.w + padding > other.x and
                self.y - padding < other.y + other.h and
                self.y + self.h + padding > other.y)


class Level:
    def __init__(self, depth):
        self.depth = depth
        self.grid = [[WALL for _ in range(MAP_W)] for _ in range(MAP_H)]
        self.seen = [[False for _ in range(MAP_W)] for _ in range(MAP_H)]
        self.rooms = []
        self.monsters = []
        self.items = {}       # (x, y) -> item dict
        self.stairs_down = None
        self.amulet_pos = None
        self.player_start = (1, 1)
        self._generate()

    def _carve_room(self, room):
        for y in range(room.y, room.y + room.h):
            for x in range(room.x, room.x + room.w):
                self.grid[y][x] = FLOOR

    def _carve_corridor(self, x1, y1, x2, y2):
        if random.random() < 0.5:
            for x in range(min(x1, x2), max(x1, x2) + 1):
                self.grid[y1][x] = FLOOR
            for y in range(min(y1, y2), max(y1, y2) + 1):
                self.grid[y][x2] = FLOOR
        else:
            for y in range(min(y1, y2), max(y1, y2) + 1):
                self.grid[y][x1] = FLOOR
            for x in range(min(x1, x2), max(x1, x2) + 1):
                self.grid[y2][x] = FLOOR

    def _generate(self):
        attempts = 0
        while len(self.rooms) < 8 and attempts < 100:
            attempts += 1
            w, h = random.randint(4, 9), random.randint(3, 6)
            x, y = random.randint(1, MAP_W - w - 2), random.randint(1, MAP_H - h - 2)
            new_room = Room(x, y, w, h)
            if any(new_room.intersects(r) for r in self.rooms):
                continue
            self._carve_room(new_room)
            if self.rooms:
                px, py = self.rooms[-1].center()
                nx, ny = new_room.center()
                self._carve_corridor(px, py, nx, ny)
            self.rooms.append(new_room)

        self.player_start = self.rooms[0].center()

        last_room_center = self.rooms[-1].center()
        if self.depth == MAX_DEPTH:
            self.amulet_pos = last_room_center
            self.items[last_room_center] = {"symbol": "A", "name": "Amulet", "kind": "amulet"}
        else:
            self.stairs_down = last_room_center

        self._populate_monsters()
        self._populate_items()

    def _random_floor_tile(self, exclude_room_index=0):
        room = random.choice(self.rooms[1:] if len(self.rooms) > 1 else self.rooms)
        x = random.randint(room.x, room.x + room.w - 1)
        y = random.randint(room.y, room.y + room.h - 1)
        return (x, y)

    def _populate_monsters(self):
        templates = [
            {"symbol": "g", "name": "goblin", "hp": 6, "atk": 2, "def": 0},
            {"symbol": "o", "name": "orc",    "hp": 10, "atk": 3, "def": 1},
            {"symbol": "t", "name": "troll",  "hp": 16, "atk": 5, "def": 2},
        ]
        count = 3 + self.depth
        scale = 1.0 + 0.25 * (self.depth - 1)
        occupied = set(self.items.keys()) | {self.player_start}
        for _ in range(count):
            tpl = random.choice(templates[: min(1 + self.depth // 2, 3)])
            pos = self._random_floor_tile()
            if pos in occupied or pos == self.player_start:
                continue
            occupied.add(pos)
            self.monsters.append({
                "x": pos[0], "y": pos[1], "symbol": tpl["symbol"], "name": tpl["name"],
                "hp": int(tpl["hp"] * scale), "max_hp": int(tpl["hp"] * scale),
                "atk": int(tpl["atk"] * scale), "def": tpl["def"], "alive": True,
            })

    def _populate_items(self):
        # note: must be (m["x"], m["y"]) unconditionally — an `x and (...)`
        # shortcut here would collapse to the bare int 0 whenever a monster's
        # x-coordinate happened to be 0, silently breaking the exclusion.
        occupied = set(self.items.keys()) | {(m["x"], m["y"]) for m in self.monsters}
        occupied.add(self.player_start)
        if self.stairs_down:
            occupied.add(self.stairs_down)
        # amulet_pos is already a key in self.items at this point (set earlier
        # in _generate), so it's covered by the first term above — but every
        # placement below still goes through `occupied`, so nothing placed
        # here can ever silently overwrite it in the dict.

        def place(build_entry, chance=1.0):
            if random.random() > chance:
                return
            for _ in range(10):  # a few retries against a crowded map; give up quietly if unlucky
                pos = self._random_floor_tile()
                if pos in occupied:
                    continue
                occupied.add(pos)
                self.items[pos] = build_entry()
                return

        for _ in range(2 + self.depth // 2):
            place(lambda: {"symbol": "$", "name": "gold", "kind": "gold", "amount": random.randint(5, 20) * self.depth})
        place(lambda: {"symbol": "!", "name": "potion", "kind": "potion"}, chance=0.7)
        if self.depth >= 2:
            place(lambda: {"symbol": "/", "name": "blade", "kind": "weapon", "atk_bonus": 1 + self.depth // 2}, chance=0.5)

    def is_walkable(self, x, y):
        if not (0 <= x < MAP_W and 0 <= y < MAP_H):
            return False
        return self.grid[y][x] == FLOOR

    def room_containing(self, x, y):
        for r in self.rooms:
            if r.x <= x < r.x + r.w and r.y <= y < r.y + r.h:
                return r
        return None


# --------------------------------------------------------------------------
# player + game state
# --------------------------------------------------------------------------

class Player:
    def __init__(self):
        self.x, self.y = 1, 1
        self.hp = self.max_hp = 20
        self.atk = 4
        self.defense = 1
        self.gold = 0
        self.potions = 1
        self.kills = 0


class Game:
    def __init__(self):
        self.player = Player()
        self.depth = 1
        self.level = Level(self.depth)
        self.player.x, self.player.y = self.level.player_start
        self.log = []
        self.won = False
        self.game_over = False

    def msg(self, text):
        self.log.append(text)
        self.log = self.log[-4:]

    # -- visibility ---------------------------------------------------
    def update_visibility(self):
        lvl = self.level
        room = lvl.room_containing(self.player.x, self.player.y)
        if room:
            for y in range(room.y, room.y + room.h):
                for x in range(room.x, room.x + room.w):
                    lvl.seen[y][x] = True
        radius = 2
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                x, y = self.player.x + dx, self.player.y + dy
                if 0 <= x < MAP_W and 0 <= y < MAP_H and dx * dx + dy * dy <= radius * radius:
                    if lvl.grid[y][x] != WALL:
                        lvl.seen[y][x] = True

    def visible_now(self, x, y):
        p = self.player
        return abs(p.x - x) <= 6 and abs(p.y - y) <= 6 and self.level.room_containing(x, y) == self.level.room_containing(p.x, p.y) \
            or (abs(p.x - x) <= 2 and abs(p.y - y) <= 2)

    # -- rendering ------------------------------------------------------
    def render(self):
        lvl = self.level
        lines = []
        for y in range(MAP_H):
            row = []
            for x in range(MAP_W):
                if not lvl.seen[y][x]:
                    row.append(" ")
                    continue
                ch = lvl.grid[y][x]
                visible = self.visible_now(x, y)
                if ch == WALL:
                    row.append(c(WALL, COLOR["wall"]) if visible else c(WALL, COLOR["dim"]))
                else:
                    row.append(c(".", COLOR["floor"]) if visible else c(".", COLOR["dim"]))
            lines.append(row)

        if lvl.stairs_down:
            sx, sy = lvl.stairs_down
            if lvl.seen[sy][sx]:
                lines[sy][sx] = c(">", COLOR["stairs"])

        for pos, item in lvl.items.items():
            x, y = pos
            if lvl.seen[y][x] and self.visible_now(x, y):
                color = COLOR["amulet"] if item["kind"] == "amulet" else COLOR.get(item["kind"], COLOR["gold"])
                lines[y][x] = c(item["symbol"], color)

        for m in lvl.monsters:
            if m["alive"] and lvl.seen[m["y"]][m["x"]] and self.visible_now(m["x"], m["y"]):
                lines[m["y"]][m["x"]] = c(m["symbol"], COLOR["monster"])

        lines[self.player.y][self.player.x] = c("@", COLOR["player"])

        out = ["".join(row) for row in lines]
        return "\n".join(out)

    def render_hud(self):
        p = self.player
        hp_bar = "#" * max(0, int(20 * p.hp / p.max_hp)) + "-" * (20 - max(0, int(20 * p.hp / p.max_hp)))
        hud = (f"Depth {self.depth}/{MAX_DEPTH}  HP [{hp_bar}] {p.hp}/{p.max_hp}  "
               f"ATK {p.atk}  DEF {p.defense}  Gold {p.gold}  Potions {p.potions}")
        return c(hud, COLOR["hud"])

    def render_log(self):
        return "\n".join(c("- " + line, COLOR["log"]) for line in self.log)

    def draw(self):
        clear_screen()
        print(self.render_hud())
        print()
        print(self.render())
        print()
        print(self.render_log())
        print()

    # -- turn logic -------------------------------------------------------
    def monster_at(self, x, y):
        for m in self.level.monsters:
            if m["alive"] and m["x"] == x and m["y"] == y:
                return m
        return None

    def player_attacks(self, monster):
        dmg = max(1, self.player.atk - monster["def"] + random.randint(-1, 1))
        monster["hp"] -= dmg
        self.msg(f"You hit the {monster['name']} for {dmg}.")
        if monster["hp"] <= 0:
            monster["alive"] = False
            self.player.kills += 1
            self.msg(f"The {monster['name']} dies!")

    def monster_attacks(self, monster):
        dmg = max(1, monster["atk"] - self.player.defense + random.randint(-1, 1))
        self.player.hp -= dmg
        self.msg(f"The {monster['name']} hits you for {dmg}.")

    def try_move_player(self, dx, dy):
        nx, ny = self.player.x + dx, self.player.y + dy
        target_monster = self.monster_at(nx, ny)
        if target_monster:
            self.player_attacks(target_monster)
            return True
        if not self.level.is_walkable(nx, ny):
            self.msg("You bump into a wall.")
            return False
        self.player.x, self.player.y = nx, ny
        pos = (nx, ny)
        if pos in self.level.items:
            self.pickup(pos)
        if self.level.stairs_down == pos:
            self.descend()
        return True

    def pickup(self, pos):
        item = self.level.items.pop(pos)
        p = self.player
        if item["kind"] == "gold":
            p.gold += item["amount"]
            self.msg(f"You pick up {item['amount']} gold.")
        elif item["kind"] == "potion":
            p.potions += 1
            self.msg("You pick up a potion.")
        elif item["kind"] == "weapon":
            p.atk += item["atk_bonus"]
            self.msg(f"You find a {item['name']}! ATK +{item['atk_bonus']}.")
        elif item["kind"] == "amulet":
            self.won = True
            self.msg("You grasp the Amulet. The dungeon trembles...")

    def descend(self):
        self.depth += 1
        self.level = Level(self.depth)
        self.player.x, self.player.y = self.level.player_start
        self.msg(f"You descend to depth {self.depth}.")

    def drink_potion(self):
        p = self.player
        if p.potions <= 0:
            self.msg("No potions left.")
            return
        p.potions -= 1
        healed = min(8, p.max_hp - p.hp)
        p.hp += healed
        self.msg(f"You drink a potion, healing {healed} HP.")

    def monster_turn(self):
        p = self.player
        for m in self.level.monsters:
            if not m["alive"]:
                continue
            dx, dy = p.x - m["x"], p.y - m["y"]
            dist = max(abs(dx), abs(dy))
            if dist <= 1:
                self.monster_attacks(m)
                continue
            if dist <= 6:
                step_x = (dx > 0) - (dx < 0)
                step_y = (dy > 0) - (dy < 0)
                nx, ny = m["x"] + step_x, m["y"]
                if self.level.is_walkable(nx, ny) and not self.monster_at(nx, ny) and (nx, ny) != (p.x, p.y):
                    m["x"] = nx
                else:
                    ny2 = m["y"] + step_y
                    if self.level.is_walkable(m["x"], ny2) and not self.monster_at(m["x"], ny2) and (m["x"], ny2) != (p.x, p.y):
                        m["y"] = ny2
            elif random.random() < 0.3:
                dx2, dy2 = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
                nx, ny = m["x"] + dx2, m["y"] + dy2
                if self.level.is_walkable(nx, ny) and not self.monster_at(nx, ny):
                    m["x"], m["y"] = nx, ny

    def take_turn(self, cmd):
        cmd = cmd.strip().lower()
        moved_or_acted = False
        if cmd == "w":
            moved_or_acted = self.try_move_player(0, -1)
        elif cmd == "s":
            moved_or_acted = self.try_move_player(0, 1)
        elif cmd == "a":
            moved_or_acted = self.try_move_player(-1, 0)
        elif cmd == "d":
            moved_or_acted = self.try_move_player(1, 0)
        elif cmd == "i":
            self.drink_potion()
            moved_or_acted = True
        elif cmd == "q":
            self.game_over = True
            return
        else:
            self.msg("Unknown command. w/a/s/d to move, i for potion, q to quit.")

        if moved_or_acted and self.player.hp > 0 and not self.won:
            self.monster_turn()
        if self.player.hp <= 0:
            self.game_over = True

    def run(self):
        title()
        while not self.game_over and not self.won:
            self.update_visibility()
            self.draw()
            cmd = input("> ")
            self.take_turn(cmd)
        self.update_visibility()
        self.draw()
        if self.won:
            print(c("*** YOU ESCAPED WITH THE AMULET. VICTORY! ***", "1;92"))
        else:
            print(c("*** YOU HAVE DIED ***", "1;91"))
        p = self.player
        print(f"Depth reached: {self.depth}   Gold: {p.gold}   Kills: {p.kills}")


def title():
    clear_screen()
    print(c(r"""
  ______                                     ______           _
 |  ____|                                   |  ____|         | |
 | |__  ___ ___  __ _ _ __   ___ _ __       | |__   __ _  ___| |
 |  __|/ __/ __|/ _` | '_ \ / _ \ '__|      |  __| / _` |/ __| |
 | |___\__ \__ \ (_| | |_) |  __/ |         | |___| (_| | (__|_|
 |______|___/___/\__,_| .__/ \___|_|         |______\__,_|\___(_)
                       | |
                       |_|          -- Dungeon Crawler --
""", "1;93"))
    print("Find the Amulet at depth 5. Permadeath. w/a/s/d to move, i for potion, q to quit.")
    input("Press Enter to descend...")


if __name__ == "__main__":
    random.seed()
    try:
        Game().run()
    except KeyboardInterrupt:
        print("\nFled the dungeon.")
        sys.exit(0)
