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
The Lizardman theme: the Marsh Court - packed-mud lodges with mangrove
timber and sea-lantern glow, raised in the swamps and jungles. The Aquatic
theme: the Coral Throne - a prismarine palace with dark-prismarine bands
and gold hoard trim, built solid on the ocean floor.
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


# --- the Lizardman capital pieces --------------------------------------------
# Writes to structure/lizardman/ (subdir pool layout: template_pool/lizardman/*).

LIZARDMAN_STREETS_POOL = f"{NAMESPACE}:lizardman/streets"
LIZARDMAN_BUILDINGS_POOL = f"{NAMESPACE}:lizardman/buildings"

LEARTH = "minecraft:packed_mud"
LWALL = "minecraft:mud_bricks"
LTIMBER = "minecraft:mangrove_log"
LMOSS = "minecraft:mossy_stone_bricks"
LCOPPER = "minecraft:copper_block"
LLIGHT = "minecraft:sea_lantern"


def build_lizardman_start() -> Template:
    """Marsh court + mound: the Lizardman capital's origin, with a court mound."""
    t = Template(16, 12, 16)
    t.fill(0, 0, 0, 15, 0, 15, LEARTH)                     # packed-mud court
    for i in range(16):                                    # mossy stone border
        t.set(i, 0, 0, LMOSS)
        t.set(i, 0, 15, LMOSS)
        t.set(0, 0, i, LMOSS)
        t.set(15, 0, i, LMOSS)
    for x, z in ((4, 4), (11, 4), (4, 11), (11, 11)):      # mangrove posts
        t.fill(x, 1, z, x, 3, z, LTIMBER)
        t.set(x, 4, z, LLIGHT)
    # central court mound (the court rises from here)
    t.fill(6, 1, 6, 9, 8, 9, LWALL)
    t.fill(7, 1, 7, 8, 8, 8, LEARTH)
    t.fill(6, 4, 6, 9, 4, 9, LTIMBER)                      # timber band
    t.fill(6, 9, 6, 9, 9, 9, LCOPPER)
    # low wall along z=0 with a gate opening (x 6..9, y 1..4)
    t.fill(0, 1, 0, 15, 4, 0, LWALL)
    t.fill(6, 1, 0, 9, 4, 0, "minecraft:air")
    t.fill(5, 5, 0, 10, 5, 0, LTIMBER)
    t.set(5, 1, 0, LLIGHT)
    t.set(10, 1, 0, LLIGHT)
    t.jigsaw(7, 1, 0, "south_up", LIZARDMAN_STREETS_POOL)
    t.jigsaw(8, 1, 15, "north_up", LIZARDMAN_STREETS_POOL)
    t.jigsaw(15, 1, 8, "east_up", LIZARDMAN_BUILDINGS_POOL)
    t.jigsaw(0, 1, 8, "west_up", LIZARDMAN_BUILDINGS_POOL)
    return t


def build_lizardman_street() -> Template:
    """Packed-mud way with mossy inlays and sea-lantern lamps."""
    t = Template(16, 4, 16)
    t.fill(6, 0, 0, 9, 0, 15, LEARTH)
    for z in range(0, 16):                                 # mossy inlays
        if z % 5 == 2:
            t.set(6, 0, z, LMOSS)
            t.set(9, 0, z, LMOSS)
    for z in range(3, 16, 6):                              # sea-lantern lamps
        t.set(5, 1, z, LLIGHT)
        t.set(10, 1, z, LLIGHT)
    t.jigsaw(7, 1, 0, "south_up", LIZARDMAN_STREETS_POOL)
    t.jigsaw(7, 1, 15, "north_up", LIZARDMAN_STREETS_POOL)
    t.jigsaw(0, 1, 7, "west_up", LIZARDMAN_BUILDINGS_POOL)
    t.jigsaw(15, 1, 7, "east_up", LIZARDMAN_BUILDINGS_POOL)
    return t


def build_lizardman_spire() -> Template:
    """Marsh watch: mud-brick tower with timber bands and a copper crown."""
    t = Template(9, 16, 9)
    t.fill(0, 0, 0, 8, 0, 8, LEARTH)
    t.fill(3, 1, 3, 5, 10, 5, LWALL)
    t.fill(4, 1, 4, 4, 10, 4, LMOSS)
    t.fill(3, 4, 3, 5, 4, 5, LTIMBER)                      # timber band
    t.fill(3, 7, 3, 5, 7, 5, LEARTH)                       # mud band
    t.set(4, 11, 4, LLIGHT)                                # glowing crown
    t.set(4, 12, 4, LCOPPER)
    t.jigsaw(4, 1, 2, "south_up", LIZARDMAN_BUILDINGS_POOL)
    return t


def build_lizardman_hall() -> Template:
    """Court hall: mud-brick walls, mangrove posts, copper roof trim."""
    t = Template(11, 8, 11)
    t.fill(0, 0, 0, 10, 0, 10, LEARTH)
    t.walls(0, 0, 10, 10, 1, 4, LWALL)
    for z in range(1, 10):
        if z % 3 == 1:
            t.set(0, 3, z, LMOSS)
            t.set(10, 3, z, LMOSS)
    for x, z in ((0, 0), (10, 0), (0, 10), (10, 10)):
        t.fill(x, 1, z, x, 4, z, LTIMBER)
    t.fill(5, 1, 0, 5, 2, 0, "minecraft:air")              # door gap (south)
    t.fill(4, 1, 5, 6, 1, 6, LLIGHT)                       # hearth glow
    t.fill(0, 5, 0, 10, 5, 10, LWALL)                      # roof
    for x in range(0, 11):
        t.set(x, 6, 0, LCOPPER)
        t.set(x, 6, 10, LCOPPER)
    for z in range(0, 11):
        t.set(0, 6, z, LCOPPER)
        t.set(10, 6, z, LCOPPER)
    t.jigsaw(5, 1, 0, "south_up", LIZARDMAN_BUILDINGS_POOL)
    return t


LIZARDMAN_PIECES = {
    "start": build_lizardman_start,
    "street": build_lizardman_street,
    "spire": build_lizardman_spire,
    "hall": build_lizardman_hall,
}


# --- the Aquatic capital pieces ----------------------------------------------
# Writes to structure/aquatic/ (subdir pool layout: template_pool/aquatic/*).
# The palace builds SOLID (no interior voids) so it does not carve air pockets
# into the ocean floor.

AQUATIC_STREETS_POOL = f"{NAMESPACE}:aquatic/streets"
AQUATIC_BUILDINGS_POOL = f"{NAMESPACE}:aquatic/buildings"

ASTONE = "minecraft:prismarine"
ABRICK = "minecraft:prismarine_bricks"
ADARK = "minecraft:dark_prismarine"
AGOLD = "minecraft:gold_block"
ALIGHT = "minecraft:sea_lantern"


def build_aquatic_start() -> Template:
    """Palace terrace: the Coral Throne's origin, solid on the seafloor."""
    t = Template(16, 12, 16)
    t.fill(0, 0, 0, 15, 0, 15, ABRICK)                     # terrace floor
    for i in range(16):                                    # dark prismarine border
        t.set(i, 0, 0, ADARK)
        t.set(i, 0, 15, ADARK)
        t.set(0, 0, i, ADARK)
        t.set(15, 0, i, ADARK)
    # central throne mass (solid)
    t.fill(6, 1, 6, 9, 8, 9, ASTONE)
    t.fill(7, 1, 7, 8, 8, 8, ABRICK)
    t.fill(6, 4, 6, 9, 4, 9, ADARK)                        # dark band
    t.fill(6, 9, 6, 9, 9, 9, AGOLD)
    for x, z in ((3, 3), (12, 3), (3, 12), (12, 12)):      # sea-lantern pylons
        t.fill(x, 1, z, x, 2, z, ALIGHT)
    # gate wall along z=0 with an arch opening (x 6..9, y 1..4)
    t.fill(0, 1, 0, 15, 4, 0, ASTONE)
    t.fill(6, 1, 0, 9, 4, 0, "minecraft:air")
    t.fill(5, 5, 0, 10, 5, 0, ADARK)
    t.jigsaw(7, 1, 0, "south_up", AQUATIC_STREETS_POOL)
    t.jigsaw(8, 1, 15, "north_up", AQUATIC_STREETS_POOL)
    t.jigsaw(15, 1, 8, "east_up", AQUATIC_STREETS_POOL)
    t.jigsaw(0, 1, 8, "west_up", AQUATIC_STREETS_POOL)
    return t


def build_aquatic_street() -> Template:
    """Prismarine causeway with dark-prismarine joints and lantern rows."""
    t = Template(16, 4, 16)
    t.fill(6, 0, 0, 9, 0, 15, ABRICK)
    for z in range(0, 16):                                 # dark joints
        if z % 4 == 2:
            t.set(7, 0, z, ADARK)
            t.set(8, 0, z, ADARK)
    for z in range(3, 16, 6):                              # lantern rows
        t.set(5, 1, z, ALIGHT)
        t.set(10, 1, z, ALIGHT)
    t.jigsaw(7, 1, 0, "south_up", AQUATIC_STREETS_POOL)
    t.jigsaw(7, 1, 15, "north_up", AQUATIC_STREETS_POOL)
    t.jigsaw(0, 1, 7, "west_up", AQUATIC_BUILDINGS_POOL)
    t.jigsaw(15, 1, 7, "east_up", AQUATIC_BUILDINGS_POOL)
    return t


def build_aquatic_spire() -> Template:
    """Solid coral spire: prismarine shaft, dark bands, lantern crown."""
    t = Template(9, 16, 9)
    t.fill(0, 0, 0, 8, 0, 8, ABRICK)
    t.fill(3, 1, 3, 5, 10, 5, ASTONE)
    t.fill(4, 1, 4, 4, 10, 4, ABRICK)
    t.fill(3, 4, 3, 5, 4, 5, ADARK)                        # dark band
    t.fill(3, 7, 3, 5, 7, 5, ADARK)                        # dark band
    t.set(4, 11, 4, ALIGHT)                                # glowing crown
    t.set(4, 12, 4, AGOLD)
    t.jigsaw(4, 1, 2, "south_up", AQUATIC_BUILDINGS_POOL)
    return t


def build_aquatic_hall() -> Template:
    """Solid palace hall: prismarine mass, dark bands, gold hoard cap."""
    t = Template(11, 8, 11)
    t.fill(0, 0, 0, 10, 0, 10, ABRICK)
    t.fill(0, 1, 0, 10, 4, 10, ASTONE)                     # solid mass
    for z in range(0, 11):
        t.set(0, 3, z, ADARK)
        t.set(10, 3, z, ADARK)
    for x in range(0, 11):
        t.set(x, 3, 0, ADARK)
        t.set(x, 3, 10, ADARK)
    t.fill(0, 5, 0, 10, 5, 10, ABRICK)                     # roof
    for x in range(0, 11):
        t.set(x, 6, 0, AGOLD)
        t.set(x, 6, 10, AGOLD)
    for z in range(0, 11):
        t.set(0, 6, z, AGOLD)
        t.set(10, 6, z, AGOLD)
    t.jigsaw(5, 1, 0, "south_up", AQUATIC_BUILDINGS_POOL)
    return t


AQUATIC_PIECES = {
    "start": build_aquatic_start,
    "street": build_aquatic_street,
    "spire": build_aquatic_spire,
    "hall": build_aquatic_hall,
}


def write_set(pieces: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, builder in pieces.items():
        template = builder()
        path = out_dir / f"{name}.nbt"
        path.write_bytes(template.to_nbt())
        rel = path.relative_to(OUT.parent.parent)
        print(f"wrote {rel} ({len(template.blocks)} blocks, {len(template.palette)} palette entries)")


def main() -> None:
    # Goblins keeps its merged top-level layout (pools reference the bare names);
    # Lizardman and Aquatic use subdirectories with their own pool namespaces.
    write_set(PIECES, OUT)
    write_set(LIZARDMAN_PIECES, OUT / "lizardman")
    write_set(AQUATIC_PIECES, OUT / "aquatic")


if __name__ == "__main__":
    main()
