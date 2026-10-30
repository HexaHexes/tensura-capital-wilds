package org.bitwisemadness.tensuracapitalwilds.gametest;

import net.minecraft.core.Holder;
import net.minecraft.core.HolderSet;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.bitwisemadness.tensuracapitalwilds.TensuraCapitalWilds;

import java.util.List;
import java.util.Optional;

/**
 * Registry-level coverage: the three capitals are registered structures and
 * their central capital tags resolve. Worldgen placement itself is
 * biome-environmental and is verified in game.
 */
@GameTestHolder(TensuraCapitalWilds.MOD_ID)
@PrefixGameTestTemplate(false)
public final class TensuraCapitalWildsGameTests {

    private TensuraCapitalWildsGameTests() {
    }

    /** The mod is loaded and the empty structure template resolves. */
    @GameTest(template = "empty")
    public static void mod_loads(GameTestHelper helper) {
        helper.succeed();
    }

    /** Humans, Elves and Dwarves capitals are registered and tagged. */
    @GameTest(template = "empty")
    public static void capitals_registered_and_tagged(GameTestHelper helper) {
        var registry = helper.getLevel().registryAccess().registryOrThrow(Registries.STRUCTURE);
        for (String faction : List.of("humans", "elves", "dwarves")) {
            ResourceKey<net.minecraft.world.level.levelgen.structure.Structure> key =
                    ResourceKey.create(Registries.STRUCTURE,
                            ResourceLocation.fromNamespaceAndPath(TensuraCapitalWilds.MOD_ID, faction));
            helper.assertTrue(registry.getHolder(key).isPresent(),
                    "capital structure not registered: " + key.location());

            TagKey<net.minecraft.world.level.levelgen.structure.Structure> tag = TagKey.create(Registries.STRUCTURE,
                    ResourceLocation.fromNamespaceAndPath("tensura_faction_spawn", "capital/" + faction));
            var holders = registry.getTag(tag);
            helper.assertTrue(holders.isPresent() && holders.get().size() > 0,
                    "capital tag does not resolve: " + tag.location());
            boolean containsOwn = holders.orElseThrow().stream().anyMatch(h -> containsFaction(h, faction));
            helper.assertTrue(containsOwn, "capital tag " + tag.location() + " is missing the " + faction + " capital");
        }
        helper.succeed();
    }

    private static boolean containsFaction(Holder<net.minecraft.world.level.levelgen.structure.Structure> holder,
                                           String faction) {
        return holder.unwrapKey()
                .map(k -> k.location().getNamespace().equals(TensuraCapitalWilds.MOD_ID)
                        && k.location().getPath().equals(faction))
                .orElse(false);
    }
}
