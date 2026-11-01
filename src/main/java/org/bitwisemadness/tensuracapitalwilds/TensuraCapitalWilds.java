package org.bitwisemadness.tensuracapitalwilds;

import com.mojang.logging.LogUtils;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import org.slf4j.Logger;

/**
 * The Goblins capital - the Warchief's stronghold in the wild forests.
 *
 * <p>The cities ship as bundled datapack content ({@code data/} in this jar)
 * and register themselves into the central capital tags owned by the
 * {@code tensura_faction_spawn} mod, which handles arrival and placement. This
 * mod adds no runtime behaviour of its own yet; it exists so the capitals
 * install like any mod and version with the rest of the ecosystem.</p>
 */
@Mod(TensuraCapitalWilds.MOD_ID)
public final class TensuraCapitalWilds {

    public static final String MOD_ID = "tensura_capital_wilds";
    public static final Logger LOGGER = LogUtils.getLogger();

    public TensuraCapitalWilds(IEventBus modBus) {
        LOGGER.info("Tensura Capital: Wilds initialized");
    }
}
