#!/usr/bin/env python3
"""Generates the jigsaw structure templates for the Goblins capital.

Committed tooling, not a one-off: the templates are code so the city is
regeneratable and reviewable. Run from the repository root:

    python tools/gen_templates.py

Writes gzip NBT structure files under src/main/resources/data/
<ns>/structure/ (the mod-bundled datapack).

Design constraints (SPIKE-CAPITAL-GEN-01): a single jigsaw structure is capped
at 128 blocks from its center (`max_distance_from_center`), so each template
stays small and the stronghold grows by jigsaw expansion. All connections use
a uniform name/target pair ("road"), horizontal `orientation` values, and
`joint: "roll"`. Blocks are full cubes only.

The Goblins theme: the Warchief's stronghold - rough cobblestone and mossy
stone mass, spruce timber framing, glowstone torchlight and gold loot trim.
The races (goblin through orc disaster, kobold) range across Tensura's
forest-family villages, so the stronghold generates in the vanilla forest
family.
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
NAMESPACE = "tensura_capital_wilds"
OUT = Path(__file__).resolve().parent.parent / "src" / "main" / "resources" / "data" / NAMESPACE / "structure"

STREETS_POOL = f"{NAMESPACE}:streets"
BUILDINGS_POOL = f"{NAMESPACE}:buildings"


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
        state = self.state("minecraft:jigsaw", orientation=orientation)
        self.blocks[(x, y, z)] = state
        self.jigsaws.append({"pos": [x, y, z], "pool": pool})

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


# --- the Goblins capital pieces ---------------------------------------------

STONE = "minecraft:cobblestone"
MOSS = "minecraft:mossy_cobblestone"
TIMBER = "minecraft:spruce_log"
WOOD = "minecraft:spruce_planks"
GOLD = "minecraft:gold_block"
LIGHT = "minecraft:glowstone"


def build_start() -> Template:
    """Gate + plaza: the stronghold's origin piece, with a central keep base."""
    t = Template(16, 12, 16)
    t.fill(0, 0, 0, 15, 0, 15, STONE)                      # plaza floor
    for x, z in ((3, 3), (12, 3), (3, 12), (12, 12)):      # mossy patches
        t.set(x, 0, z, MOSS)
        t.set(x + 1, 0, z, MOSS)
        t.set(x, 0, z + 1, MOSS)
    for i in range(16):                                    # gold loot ring at the gate
        t.set(i, 0, 0, GOLD)
    # central keep base (the stronghold rises from here)
    t.fill(6, 1, 6, 9, 8, 9, STONE)
    t.fill(7, 1, 7, 8, 8, 8, WOOD)
    t.fill(6, 4, 6, 9, 4, 9, MOSS)                         # mossy band
    t.fill(6, 9, 6, 9, 9, 9, GOLD)
    # gate wall along z=0 with an arch opening (x 6..9, y 1..4)
    t.fill(0, 1, 0, 15, 4, 0, STONE)
    t.fill(6, 1, 0, 9, 4, 0, "minecraft:air")
    t.fill(5, 5, 0, 10, 5, 0, TIMBER)
    t.set(5, 1, 0, LIGHT)
    t.set(10, 1, 0, LIGHT)
    t.jigsaw(7, 1, 0, "south_up", STREETS_POOL)
    t.jigsaw(8, 1, 15, "north_up", STREETS_POOL)
    t.jigsaw(15, 1, 8, "east_up", STREETS_POOL)
    t.jigsaw(0, 1, 8, "west_up", STREETS_POOL)
    return t


def build_street() -> Template:
    """Cobble walkway with mossy inlays and glowstone lamps."""
    t = Template(16, 4, 16)
    t.fill(6, 0, 0, 9, 0, 15, STONE)
    for z in range(0, 16):                                 # mossy inlays
        if z % 5 == 2:
            t.set(6, 0, z, MOSS)
            t.set(9, 0, z, MOSS)
    for z in range(3, 16, 6):                              # glowstone lamps
        t.set(5, 1, z, LIGHT)
        t.set(10, 1, z, LIGHT)
    t.jigsaw(7, 1, 0, "south_up", STREETS_POOL)
    t.jigsaw(7, 1, 15, "north_up", STREETS_POOL)
    t.jigsaw(0, 1, 7, "west_up", BUILDINGS_POOL)
    t.jigsaw(15, 1, 7, "east_up", BUILDINGS_POOL)
    return t


def build_spire() -> Template:
    """Watchtower: cobble mass, timber bands, mossy patches, glowing crown."""
    t = Template(9, 16, 9)
    t.fill(0, 0, 0, 8, 0, 8, STONE)
    t.fill(3, 1, 3, 5, 10, 5, STONE)
    t.fill(4, 1, 4, 4, 10, 4, WOOD)
    t.fill(3, 4, 3, 5, 4, 5, TIMBER)                       # timber band
    t.fill(2, 8, 2, 6, 8, 6, MOSS)                         # mossy band
    t.set(4, 11, 4, LIGHT)                                 # glowing crown
    t.set(4, 12, 4, GOLD)
    t.jigsaw(4, 1, 2, "south_up", BUILDINGS_POOL)
    return t


def build_hall() -> Template:
    """War longhouse: timber corner posts, mossy walls, gold roof trim."""
    t = Template(11, 8, 11)
    t.fill(0, 0, 0, 10, 0, 10, WOOD)
    t.walls(0, 0, 10, 10, 1, 4, STONE)
    for z in range(1, 10):
        if z % 3 == 1:
            t.set(0, 2, z, MOSS)
            t.set(10, 2, z, MOSS)
    for x, z in ((0, 0), (10, 0), (0, 10), (10, 10)):
        t.fill(x, 1, z, x, 4, z, TIMBER)
    t.fill(5, 1, 0, 5, 2, 0, "minecraft:air")              # door gap (south)
    t.fill(4, 1, 5, 6, 1, 6, LIGHT)                        # hearth glow
    t.fill(0, 5, 0, 10, 5, 10, STONE)                      # roof
    for x in range(0, 11):
        t.set(x, 6, 0, GOLD)
        t.set(x, 6, 10, GOLD)
    for z in range(0, 11):
        t.set(0, 6, z, GOLD)
        t.set(10, 6, z, GOLD)
    t.jigsaw(5, 1, 0, "south_up", BUILDINGS_POOL)
    return t


PIECES = {
    "start": build_start,
    "street": build_street,
    "spire": build_spire,
    "hall": build_hall,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, builder in PIECES.items():
        template = builder()
        path = OUT / f"{name}.nbt"
        path.write_bytes(template.to_nbt())
        print(f"wrote data/{NAMESPACE}/structure/{name}.nbt "
              f"({len(template.blocks)} blocks, {len(template.palette)} palette entries)")


if __name__ == "__main__":
    main()
