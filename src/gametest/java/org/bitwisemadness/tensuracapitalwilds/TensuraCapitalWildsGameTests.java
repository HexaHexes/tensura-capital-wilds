package org.bitwisemadness.tensuracapitalwilds.gametest;

import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
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
}