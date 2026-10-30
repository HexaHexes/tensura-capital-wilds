# Repo rules — Tensura Capital: Wilds

Repo-specific rules and notes. The org-wide `AGENTS.md` beside this file is
maintained in [`neoforge-mod-template`](https://github.com/HexaHexes/neoforge-mod-template)
and pulled in verbatim — **never hand-edit it.** Everything in this file is this
repo's own and is edited freely; keep it aligned with the org rules rather than
restating them.

**Repo:** `HexaHexes/tensura-capital-mortals` · **Mod ID:** `tensura_capital_wilds` · **Branch:** `main`
**Platform:** Minecraft 1.21.1 / NeoForge 21.1.259 / JDK 21 · **Jar:** `build/libs/tensura_capital_wilds-<version>.jar`

Capital cities for the mortal races - Humans, Elves, Dwarves. The cities ship
as bundled datapack content in this mod's jar and register into the central
`#tensura_faction_spawn:capital/*` tags owned by `tensura-faction-spawn`,
which handles arrival and placement. This mod adds no runtime behaviour of
its own beyond bundling and versioning the capitals.

**Dependencies**
- Required: Minecraft, NeoForge, `tensura` (the Elves structure references
  `tensura:ancient_forest`), `tensura_faction_spawn` (owns the central capital
  tags and the arrival behaviour).

**Test:** `./gradlew runGameTestServer` — `TensuraCapitalWildsGameTests` (2 tests).
`expectedTests = 2` in `build.gradle` must match the `@GameTest` count. JUnit:
`DatapackValidationTest` (the bundled-datapack validator) and `ModIdTest`.

**Gotchas**
- **The capital tags are a shared additive contract.** `"replace": true` is
  forbidden — the JUnit validator enforces it, and vanilla would silently drop
  unresolvable values.
- **Capital IDs are permanent** (spec §18.3/§18.4) — a rename is a migration,
  not a refactor.
- **Every structure needs a structure_set** — `findNearestMapStructure` only
  finds structures that belong to one; the validator enforces the pairing.
- **Templates are generated from committed code**: `python tools/gen_templates.py`
  writes the NBT files under `src/main/resources/data/.../structure/` — edit the
  generator, not the binaries. A single jigsaw structure is capped at
  `max_distance_from_center` 128 (vanilla), so cities grow by expansion, not
  template size.
- **Worldgen placement is biome-constrained** — a "find the city" assertion is
  environmental. Registry and tag wiring is what the GameTests prove headlessly;
  placement is verified in game.
- `tools/gen_templates.py` is Python dev tooling, not shipped content.
