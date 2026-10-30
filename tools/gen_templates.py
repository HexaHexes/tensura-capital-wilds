#!/usr/bin/env python3
"""Generates the jigsaw structure templates for the mortals capitals.

Committed tooling, not a one-off: the templates are code so the cities are
regeneratable and reviewable. Run from the repository root:

    python tools/gen_templates.py

Writes gzip NBT structure files under datapack/data/<ns>/structure/humans/.

Design constraints (see SPIKE-CAPITAL-GEN-01): a single jigsaw structure is
capped at 128 blocks from its center (`max_distance_from_center`), so each
template stays small and the town grows by jigsaw expansion, not by template
size. All connections use a uniform name/target pair ("road"), horizontal
`orientation` values, and `joint: "roll"` - the scheme vanilla villages prove
works. Blocks are full cubes only; v1 avoids stairs/slab properties.
"""

from __future__ import annotations

import gzip
import struct
from pathlib import Path

TAG_BYTE = 1
TAG_INT = 3
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10

DATA_VERSION = 3955  # 1.21.1
NAMESPACE = "tensura_capital_mortals"
OUT = Path(__file__).resolve().parent.parent / "src" / "main" / "resources" / "data" / NAMESPACE / "structure"

STREETS_POOL = f"{NAMESPACE}:humans/streets"
BUILDINGS_POOL = f"{NAMESPACE}:humans/buildings"
STREETS_POOL_ELVES = f"{NAMESPACE}:elves/streets"
BUILDINGS_POOL_ELVES = f"{NAMESPACE}:elves/buildings"
STREETS_POOL_DWARVES = f"{NAMESPACE}:dwarves/streets"
BUILDINGS_POOL_DWARVES = f"{NAMESPACE}:dwarves/buildings"
ANDESITE = "minecraft:andesite"


# --- minimal NBT writer -----------------------------------------------------


def _string(value: str) -> bytes:
    raw = value.encode("utf-8")
    return struct.pack(">H", len(raw)) + raw


def _payload(tag: int, value):
    if tag == TAG_BYTE:
        return struct.pack(">b", value)
    if tag == TAG_INT:
        return struct.pack(">i", value)
    if tag == TAG_STRING:
        return _string(value)
    if tag == TAG_LIST:
        element_type, items = value
        out = bytes([element_type]) + struct.pack(">i", len(items))
        for item in items:
            out += _payload(element_type, item)
        return out
    if tag == TAG_COMPOUND:
        out = b""
        for name, item_tag, item_value in value:
            out += bytes([item_tag]) + _string(name) + _payload(item_tag, item_value)
        return out + b"\x00"
    raise ValueError(f"unsupported tag {tag}")


def compound(fields) -> tuple[int, tuple]:
    """(TAG_COMPOUND, [(name, tag, value), ...])"""
    return (TAG_COMPOUND, list(fields))


def int_list(values) -> tuple[int, list]:
    return (TAG_INT, list(values))


def encode_root(body) -> bytes:
    # mtime=0 keeps regeneration byte-deterministic (no phantom diffs on rebuild).
    return gzip.compress(bytes([TAG_COMPOUND]) + _string("") + _payload(TAG_COMPOUND, body), mtime=0)


# --- template builder -------------------------------------------------------


class Template:
    def __init__(self, width: int, height: int, depth: int):
        self.size = (width, height, depth)
        self.palette: list[tuple[str, dict]] = []
        self.palette_index: dict[tuple, int] = {}
        self.blocks: dict[tuple[int, int, int], int] = {}
        self.jigsaws: list[dict] = []

    def state(self, name: str, **props) -> int:
        key = (name, tuple(sorted(props.items())))
        if key not in self.palette_index:
            self.palette_index[key] = len(self.palette)
            self.palette.append((name, props))
        return self.palette_index[key]

    def set(self, x: int, y: int, z: int, name: str, **props) -> None:
        if 0 <= x < self.size[0] and 0 <= y < self.size[1] and 0 <= z < self.size[2]:
            self.blocks[(x, y, z)] = self.state(name, **props)

    def fill(self, x0, y0, z0, x1, y1, z1, name: str, **props) -> None:
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, name, **props)

    def walls(self, x0, z0, x1, z1, y0, y1, name: str, **props) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, z0, name, **props)
                self.set(x, y, z1, name, **props)
            for z in range(z0, z1 + 1):
                self.set(x0, y, z, name, **props)
                self.set(x1, y, z, name, **props)

    def jigsaw(self, x: int, y: int, z: int, orientation: str, pool: str) -> None:
        """Places a jigsaw block with the uniform road connection."""
        state = self.state("minecraft:jigsaw", orientation=orientation)
        self.blocks[(x, y, z)] = state
        self.jigsaws.append({
            "pos": [x, y, z],
            "pool": pool,
        })

    def to_nbt(self) -> bytes:
        blocks = []
        for (x, y, z) in sorted(self.blocks):
            fields = [("pos", TAG_LIST, int_list([x, y, z])),
                      ("state", TAG_INT, self.blocks[(x, y, z)])]
            jigsaw = next((j for j in self.jigsaws if j["pos"] == [x, y, z]), None)
            if jigsaw:
                fields.append(("nbt", TAG_COMPOUND, [
                    ("name", TAG_STRING, "road"),
                    ("target", TAG_STRING, "road"),
                    ("pool", TAG_STRING, jigsaw["pool"]),
                    ("final_state", TAG_STRING, "minecraft:air"),
                    ("joint", TAG_STRING, "roll"),
                ]))
            blocks.append(fields)  # list elements are payload-only compounds

        palette = []
        for name, props in self.palette:
            fields = [("Name", TAG_STRING, name)]
            if props:
                fields.append(("Properties", TAG_COMPOUND,
                               [(k, TAG_STRING, v) for k, v in sorted(props.items())]))
            palette.append(fields)

        body = [
            ("size", TAG_LIST, int_list(list(self.size))),
            ("entities", TAG_LIST, (TAG_COMPOUND, [])),
            ("blocks", TAG_LIST, (TAG_COMPOUND, blocks)),
            ("palette", TAG_LIST, (TAG_COMPOUND, palette)),
            ("DataVersion", TAG_INT, DATA_VERSION),
        ]
        return encode_root(body)


# --- the Humans capital pieces ----------------------------------------------

BRICK = "minecraft:stone_bricks"
COBBLE = "minecraft:cobblestone"
PLANKS = "minecraft:oak_planks"
LOG = "minecraft:oak_log"
GLASS = "minecraft:glass"


def build_start() -> Template:
    """Gate + plaza: the structure's origin piece. Four road connections."""
    t = Template(16, 8, 16)
    t.fill(0, 0, 0, 15, 0, 15, COBBLE)                    # plaza floor
    # stone-brick border ring
    for i in range(16):
        t.set(i, 0, 0, BRICK)
        t.set(i, 0, 15, BRICK)
        t.set(0, 0, i, BRICK)
        t.set(15, 0, i, BRICK)
    # gate wall along z=0 with an arch opening (x 6..9, y 1..4)
    t.fill(0, 1, 0, 15, 5, 0, BRICK)
    t.fill(6, 1, 0, 9, 4, 0, "minecraft:air")
    t.fill(5, 5, 0, 10, 5, 0, BRICK)                      # arch top
    # corner towers
    t.fill(0, 1, 0, 1, 7, 1, BRICK)
    t.fill(14, 1, 0, 15, 7, 1, BRICK)
    # road exits through the arch and around the other three faces
    t.jigsaw(7, 1, 0, "south_up", STREETS_POOL)
    t.jigsaw(8, 1, 15, "north_up", STREETS_POOL)
    t.jigsaw(15, 1, 8, "east_up", STREETS_POOL)
    t.jigsaw(0, 1, 8, "west_up", STREETS_POOL)
    return t


def build_street() -> Template:
    """Straight street: continues roads at both ends, pulls buildings at the sides."""
    t = Template(16, 4, 16)
    t.fill(6, 0, 0, 9, 0, 15, COBBLE)                     # 4-wide path
    t.jigsaw(7, 1, 0, "south_up", STREETS_POOL)
    t.jigsaw(7, 1, 15, "north_up", STREETS_POOL)
    t.jigsaw(0, 1, 7, "west_up", BUILDINGS_POOL)
    t.jigsaw(15, 1, 7, "east_up", BUILDINGS_POOL)
    return t


def build_house() -> Template:
    """Small cottage: floor, log-cornered plank walls, glass, flat roof."""
    t = Template(9, 7, 9)
    t.fill(0, 0, 0, 8, 0, 8, PLANKS)
    t.walls(0, 0, 8, 8, 1, 3, PLANKS)
    for x, z in ((0, 0), (8, 0), (0, 8), (8, 8)):
        t.fill(x, 1, z, x, 3, z, LOG)
    t.set(4, 2, 8, GLASS)                                  # north window
    t.set(0, 2, 4, GLASS)
    t.set(8, 2, 4, GLASS)
    t.fill(4, 1, 0, 4, 2, 0, "minecraft:air")              # door gap (south)
    t.fill(0, 4, 0, 8, 4, 8, PLANKS)                       # roof
    t.jigsaw(4, 1, 0, "south_up", BUILDINGS_POOL)          # consumed on attach; sits in the door gap
    return t


def build_keep() -> Template:
    """Stone keep: tall walls, glass band, battlements."""
    t = Template(11, 16, 11)
    t.fill(0, 0, 0, 10, 0, 10, COBBLE)
    t.walls(0, 0, 10, 10, 1, 9, BRICK)
    for z in range(1, 10):
        if z % 2 == 0:
            t.set(0, 4, z, GLASS)
            t.set(10, 4, z, GLASS)
    for x in range(1, 10):
        if x % 2 == 0:
            t.set(x, 4, 0, GLASS)
            t.set(x, 4, 10, GLASS)
    t.fill(5, 1, 0, 5, 2, 0, "minecraft:air")              # door gap (south)
    t.fill(0, 10, 0, 10, 10, 10, BRICK)                    # roof
    for x in range(0, 11):
        for z in range(0, 11):
            if (x in (0, 10) or z in (0, 10)) and (x + z) % 2 == 0:
                t.set(x, 11, z, BRICK)                     # battlements
    t.jigsaw(5, 1, 0, "south_up", BUILDINGS_POOL)
    return t


# --- the Elves capital pieces -----------------------------------------------

MOSS = "minecraft:moss_block"
LEAVES = "minecraft:oak_leaves"


def build_elves_start() -> Template:
    """Forest clearing with a giant ancient tree: the elves' origin piece."""
    t = Template(16, 13, 16)
    t.fill(0, 0, 0, 15, 0, 15, MOSS)                       # clearing floor
    # giant ancient tree: 3x3 trunk, wide canopy
    t.fill(7, 1, 7, 9, 9, 9, LOG)
    for y in range(6, 13):
        radius = 6 - (y - 6) // 2
        for x in range(8 - radius, 9 + radius):
            for z in range(8 - radius, 9 + radius):
                if t.blocks.get((x, y, z)) is None and not (x == 8 and z == 8 and y <= 9):
                    t.set(x, y, z, LEAVES, persistent="true")
    # mossy stone ring
    for i in range(16):
        t.set(i, 0, 0, BRICK)
        t.set(i, 0, 15, BRICK)
        t.set(0, 0, i, BRICK)
        t.set(15, 0, i, BRICK)
    t.jigsaw(7, 1, 0, "south_up", STREETS_POOL_ELVES)
    t.jigsaw(8, 1, 15, "north_up", STREETS_POOL_ELVES)
    t.jigsaw(15, 1, 8, "east_up", STREETS_POOL_ELVES)
    t.jigsaw(0, 1, 8, "west_up", STREETS_POOL_ELVES)
    return t


def build_elves_street() -> Template:
    """Mossy walkway: continues paths, pulls elven buildings at the sides."""
    t = Template(16, 4, 16)
    t.fill(6, 0, 0, 9, 0, 15, MOSS)
    t.jigsaw(7, 1, 0, "south_up", STREETS_POOL_ELVES)
    t.jigsaw(7, 1, 15, "north_up", STREETS_POOL_ELVES)
    t.jigsaw(0, 1, 7, "west_up", BUILDINGS_POOL_ELVES)
    t.jigsaw(15, 1, 7, "east_up", BUILDINGS_POOL_ELVES)
    return t


def build_elves_treetop() -> Template:
    """Hut on a trunk: the elves' elevated dwelling."""
    t = Template(9, 13, 9)
    t.fill(4, 0, 4, 4, 6, 4, LOG)                          # trunk
    t.fill(2, 7, 2, 6, 7, 6, PLANKS)                       # platform
    t.walls(2, 2, 6, 6, 8, 9, PLANKS)
    t.fill(4, 8, 2, 4, 9, 2, "minecraft:air")              # doorway (south)
    t.set(2, 9, 4, GLASS)
    t.set(6, 9, 4, GLASS)
    t.fill(1, 10, 1, 7, 10, 7, LEAVES, persistent="true")  # leaf roof
    t.fill(3, 11, 3, 5, 11, 5, LEAVES, persistent="true")
    t.jigsaw(4, 1, 3, "south_up", BUILDINGS_POOL_ELVES)    # consumed on attach; in front of the trunk
    return t


def build_elves_hut() -> Template:
    """Ground hut with a leaf roof."""
    t = Template(7, 6, 7)
    t.fill(0, 0, 0, 6, 0, 6, MOSS)
    t.walls(0, 0, 6, 6, 1, 2, PLANKS)
    for x, z in ((0, 0), (6, 0), (0, 6), (6, 6)):
        t.fill(x, 1, z, x, 2, z, LOG)
    t.fill(3, 1, 0, 3, 2, 0, "minecraft:air")              # door gap (south)
    t.fill(0, 3, 0, 6, 3, 6, LEAVES, persistent="true")    # leaf roof
    t.fill(1, 4, 1, 5, 4, 5, LEAVES, persistent="true")
    t.jigsaw(3, 1, 0, "south_up", BUILDINGS_POOL_ELVES)
    return t


# --- the Dwarves capital pieces ---------------------------------------------

def _rock(x: int, z: int) -> str:
    mix = (x + z) % 3
    return ANDESITE if mix == 0 else (COBBLE if mix == 1 else BRICK)


def build_dwarves_start() -> Template:
    """Mountain gatehouse: gate and plaza in front, the massif rising behind,
    with a carved tunnel exit through the rock."""
    t = Template(20, 16, 16)
    t.fill(0, 0, 0, 19, 0, 15, COBBLE)                     # plaza floor
    t.fill(0, 1, 0, 19, 6, 0, BRICK)                       # gate wall
    t.fill(8, 1, 0, 11, 4, 0, "minecraft:air")             # arch opening
    t.fill(8, 5, 0, 11, 6, 0, BRICK)                       # arch top
    for x, z in ((0, 0), (1, 0), (18, 0), (19, 0)):        # gate towers
        t.fill(x, 1, z, x, 8, z, BRICK)
    t.walls(0, 0, 19, 8, 1, 5, BRICK)                      # courtyard side walls
    # the massif rising behind the gate (tallest at the back)
    for z in range(8, 16):
        top = 5 + (z - 8)
        for x in range(0, 20):
            for y in range(1, top + 1):
                t.set(x, y, z, _rock(x, z))
    # carved tunnel exit through the rock
    t.fill(9, 1, 12, 10, 3, 15, "minecraft:air")
    t.jigsaw(9, 1, 0, "south_up", STREETS_POOL_DWARVES)
    t.jigsaw(9, 1, 15, "north_up", STREETS_POOL_DWARVES)
    t.jigsaw(19, 1, 8, "east_up", STREETS_POOL_DWARVES)
    t.jigsaw(0, 1, 8, "west_up", STREETS_POOL_DWARVES)
    return t


def build_dwarves_street() -> Template:
    """Stone-brick road: continues roads, pulls halls and keeps at the sides."""
    t = Template(16, 4, 16)
    t.fill(6, 0, 0, 9, 0, 15, BRICK)
    t.jigsaw(7, 1, 0, "south_up", STREETS_POOL_DWARVES)
    t.jigsaw(7, 1, 15, "north_up", STREETS_POOL_DWARVES)
    t.jigsaw(0, 1, 7, "west_up", BUILDINGS_POOL_DWARVES)
    t.jigsaw(15, 1, 7, "east_up", BUILDINGS_POOL_DWARVES)
    return t


def build_dwarves_hall() -> Template:
    """Stone hall with a glass slit band."""
    t = Template(13, 8, 13)
    t.fill(0, 0, 0, 12, 0, 12, COBBLE)
    t.walls(0, 0, 12, 12, 1, 5, BRICK)
    for z in range(1, 12):
        if z % 2 == 0:
            t.set(0, 4, z, GLASS)
            t.set(12, 4, z, GLASS)
    t.fill(6, 1, 0, 6, 2, 0, "minecraft:air")              # door gap (south)
    t.fill(0, 6, 0, 12, 6, 12, BRICK)                      # roof
    t.walls(0, 0, 12, 12, 7, 7, BRICK)                     # roof rim
    t.jigsaw(6, 1, 0, "south_up", BUILDINGS_POOL_DWARVES)
    return t


def build_dwarves_keep() -> Template:
    """Tall stone keep with a battlemented roof."""
    t = Template(13, 18, 13)
    t.fill(0, 0, 0, 12, 0, 12, COBBLE)
    t.walls(0, 0, 12, 12, 1, 11, BRICK)
    for z in range(1, 12):
        if z % 2 == 0:
            t.set(0, 5, z, GLASS)
            t.set(12, 5, z, GLASS)
    for x in range(1, 12):
        if x % 2 == 0:
            t.set(x, 5, 0, GLASS)
            t.set(x, 5, 12, GLASS)
    t.fill(6, 1, 0, 6, 2, 0, "minecraft:air")              # door gap (south)
    t.fill(0, 12, 0, 12, 12, 12, BRICK)                    # roof
    for x in range(0, 13):
        for z in range(0, 13):
            if (x in (0, 12) or z in (0, 12)) and (x + z) % 2 == 0:
                t.set(x, 13, z, BRICK)                     # battlements
    t.jigsaw(6, 1, 0, "south_up", BUILDINGS_POOL_DWARVES)
    return t


PIECES = {
    "humans/start": build_start,
    "humans/street": build_street,
    "humans/house": build_house,
    "humans/keep": build_keep,
    "elves/start": build_elves_start,
    "elves/street": build_elves_street,
    "elves/treetop": build_elves_treetop,
    "elves/hut": build_elves_hut,
    "dwarves/start": build_dwarves_start,
    "dwarves/street": build_dwarves_street,
    "dwarves/hall": build_dwarves_hall,
    "dwarves/keep": build_dwarves_keep,
}


def main() -> None:
    for name, builder in PIECES.items():
        template = builder()
        path = OUT / f"{name}.nbt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(template.to_nbt())
        print(f"wrote data/{NAMESPACE}/structure/{name}.nbt "
              f"({len(template.blocks)} blocks, {len(template.palette)} palette entries)")


if __name__ == "__main__":
    main()
