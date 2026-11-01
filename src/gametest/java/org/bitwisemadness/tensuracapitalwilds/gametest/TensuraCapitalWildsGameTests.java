package org.bitwisemadness.tensuracapitalwilds.gametest;

import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.bitwisemadness.tensuracapitalwilds.TensuraCapitalWilds;

/** Smoke test: the mod loads and the gametest harness runs. */
@GameTestHolder(TensuraCapitalWilds.MOD_ID)
@PrefixGameTestTemplate(false)
public final class TensuraCapitalWildsGameTests {

    private TensuraCapitalWildsGameTests() {
    }

    @GameTest(template = "empty")
    public static void mod_loads(GameTestHelper helper) {
        helper.succeed();
    }

    /** The Goblins capital is a registered structure and its central tag resolves. */
    @GameTest(template = "empty")
    public static void capital_registered_and_tagged(GameTestHelper helper) {
        var registry = helper.getLevel().registryAccess().registryOrThrow(Registries.STRUCTURE);
        var key = net.minecraft.resources.ResourceKey.create(Registries.STRUCTURE,
                ResourceLocation.fromNamespaceAndPath(TensuraCapitalWilds.MOD_ID, "goblins"));
        helper.assertTrue(registry.getHolder(key).isPresent(), "the Goblins capital structure is not registered");
        var tag = net.minecraft.tags.TagKey.create(Registries.STRUCTURE,
                ResourceLocation.fromNamespaceAndPath("tensura_faction_spawn", "capital/goblins"));
        var holders = registry.getTag(tag);
        helper.assertTrue(holders.isPresent() && holders.get().size() > 0, "the Goblins capital tag does not resolve");
        helper.succeed();
    }

    /** The Lizardman capital is a registered structure and its central tag resolves. */
    @GameTest(template = "empty")
    public static void lizardman_registered_and_tagged(GameTestHelper helper) {
        var registry = helper.getLevel().registryAccess().registryOrThrow(Registries.STRUCTURE);
        var key = net.minecraft.resources.ResourceKey.create(Registries.STRUCTURE,
                ResourceLocation.fromNamespaceAndPath(TensuraCapitalWilds.MOD_ID, "lizardman"));
        helper.assertTrue(registry.getHolder(key).isPresent(), "the Lizardman capital structure is not registered");
        var tag = net.minecraft.tags.TagKey.create(Registries.STRUCTURE,
                ResourceLocation.fromNamespaceAndPath("tensura_faction_spawn", "capital/lizardman"));
        var holders = registry.getTag(tag);
        helper.assertTrue(holders.isPresent() && holders.get().size() > 0, "the Lizardman capital tag does not resolve");
        helper.succeed();
    }

    /** The Aquatic capital is a registered structure and its central tag resolves. */
    @GameTest(template = "empty")
    public static void aquatic_registered_and_tagged(GameTestHelper helper) {
        var registry = helper.getLevel().registryAccess().registryOrThrow(Registries.STRUCTURE);
        var key = net.minecraft.resources.ResourceKey.create(Registries.STRUCTURE,
                ResourceLocation.fromNamespaceAndPath(TensuraCapitalWilds.MOD_ID, "aquatic"));
        helper.assertTrue(registry.getHolder(key).isPresent(), "the Aquatic capital structure is not registered");
        var tag = net.minecraft.tags.TagKey.create(Registries.STRUCTURE,
                ResourceLocation.fromNamespaceAndPath("tensura_faction_spawn", "capital/aquatic"));
        var holders = registry.getTag(tag);
        helper.assertTrue(holders.isPresent() && holders.get().size() > 0, "the Aquatic capital tag does not resolve");
        helper.succeed();
    }
}