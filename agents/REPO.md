# Repo rules - Tensura Capital: Wilds

Repo-specific rules and notes. The org-wide AGENTS.md beside this file is maintained in the neoforge-mod-template repo and pulled in verbatim - never hand-edit it.

**Repo:** `HexaHexes/tensura_capital_wilds` | **Mod ID:** `tensura_capital_wilds` | **Branch:** main
**Platform:** Minecraft 1.21.1 / NeoForge 21.1.259 / JDK 21 | **Jar:** build/libs/tensura_capital_wilds-<version>.jar

Capital cities for the wild races - Goblins, Lizardmen and Aquatic folk - registered into the Tensura Faction Spawn ecosystem. The capital(s) ship as bundled datapack content in this mod's jar and register into the central #tensura_faction_spawn:capital/* tags owned by tensura-faction-spawn, which handles arrival and placement.

**Dependencies**
- Required: Minecraft, NeoForge, tensura (bundled worldgen references Tensura biomes), tensura_faction_spawn (owns the central capital tags and the arrival behaviour; resolved from the org's GitHub Packages).

**Test:** ./gradlew runGameTestServer - smoke test (1 test). expectedTests = 1 in build.gradle must match the @GameTest count. JUnit: DatapackValidationTest (the bundled-datapack validator) and ModIdTest.

**Gotchas**
- The capital tags are a shared additive contract. "replace`: true is forbidden - the JUnit validator enforces it, and vanilla would silently drop unresolvable values.
- Capital IDs are permanent (spec 18.3/18.4) - a rename is a migration, not a refactor.
- Every structure needs a structure_set - enforced by the validator.
- Worldgen placement is biome-constrained - registry/tag wiring is what the GameTests prove headlessly; placement is verified in game.
- The gametest runtime resolves tensura-faction-spawn from the org's GitHub Packages: CI injects PACKAGE_READ_TOKEN on the gametest step; locally supply gpr.user / gpr.key in ~/.gradle/gradle.properties.