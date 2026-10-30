package org.bitwisemadness.tensuracapitalwilds;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Placeholder-style identity check so the CI junit check cannot pass vacuously;
 * grows alongside the mod's pure-JVM logic.
 */
class ModIdTest {

    @Test
    void modIdIsALowercasePathSegment() {
        assertTrue(TensuraCapitalWilds.MOD_ID.matches("[a-z][a-z0-9_]{2,63}"),
                "mod id must be a lowercase resource location path segment");
    }
}
