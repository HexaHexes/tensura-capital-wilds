package org.bitwisemadness.tensuracapitalwilds;

import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Validates the bundled datapack with the rules the datapack-era Python
 * validator enforced, now inside the junit gate:
 *
 * <ol>
 *   <li>every bundled {@code .json} parses;</li>
 *   <li>every structure definition is referenced by a structure_set (a
 *       structure outside any set can never generate or be found);</li>
 *   <li>every structure_set reference resolves to an in-repo structure or an
 *       external namespace;</li>
 *   <li>every jigsaw template_pool element resolves to a bundled template
 *       NBT or an external namespace;</li>
 *   <li>tag files are additive and self-namespace references resolve (vanilla
 *       drops unresolvable tag values silently).</li>
 * </ol>
 *
 * <p>Pure JVM: file and JSON checks only, no Minecraft classes.</p>
 */
class DatapackValidationTest {

    private static final Path DATA = Path.of("src", "main", "resources", "data");
    private static final String OWN_NAMESPACE = "tensura_capital_wilds";
    private static final Set<String> EXTERNAL_NAMESPACES = Set.of("minecraft", "tensura");

    @Test
    void bundledDatapackIsValid() throws IOException {
        List<String> problems = new ArrayList<>();
        assertTrue(Files.isDirectory(DATA), "missing bundled datapack folder: " + DATA);

        Map<Path, JsonElement> documents = new TreeMap<>();
        try (var stream = Files.walk(DATA)) {
            stream.filter(path -> path.toString().endsWith(".json")).sorted().forEach(path -> {
                try {
                    documents.put(path, JsonParser.parseString(Files.readString(path)));
                } catch (Exception e) {
                    problems.add(rel(path) + ": invalid JSON (" + e.getMessage() + ")");
                }
            });
        }

        Map<String, Path> structures = structureIds(documents);
        Set<String> referenced = referencedBySets(documents);

        for (Map.Entry<String, Path> entry : structures.entrySet()) {
            if (!referenced.contains(entry.getKey())) {
                problems.add(rel(entry.getValue()) + ": structure '" + entry.getKey()
                        + "' is not referenced by any structure_set - it can never generate or be found");
            }
        }
        checkSetReferences(documents, structures, problems);
        checkTemplatePools(documents, problems);
        checkTags(documents, structures, referenced, problems);

        assertTrue(problems.isEmpty(), "bundled datapack problems:\n- " + String.join("\n- ", problems));
    }

    private static String rel(Path path) {
        return DATA.relativize(path).toString().replace('\\', '/');
    }

    private static Map<String, Path> structureIds(Map<Path, JsonElement> documents) {
        Map<String, Path> ids = new HashMap<>();
        for (Path path : documents.keySet()) {
            String rel = rel(path);
            if (rel.contains("/tags/")) {
                continue; // tag files live under tags/worldgen/structure/ too - not definitions
            }
            if (rel.contains("/worldgen/structure/") && !rel.contains("/worldgen/structure_set/")) {
                String namespace = rel.split("/")[0];
                String location = rel.substring(rel.indexOf("/worldgen/structure/") + "/worldgen/structure/".length())
                        .replace(".json", "");
                ids.put(namespace + ":" + location, path);
            }
        }
        return ids;
    }

    private static Set<String> referencedBySets(Map<Path, JsonElement> documents) {
        Set<String> referenced = new java.util.HashSet<>();
        for (Map.Entry<Path, JsonElement> entry : documents.entrySet()) {
            String rel = rel(entry.getKey());
            if (rel.contains("/tags/") || !rel.contains("/worldgen/structure_set/")) {
                continue;
            }
            for (JsonElement element : asArrayOrEmpty(entry.getValue(), "structures")) {
                JsonElement id = element.getAsJsonObject().get("structure");
                if (id != null && !id.isJsonNull()) {
                    referenced.add(id.getAsString());
                }
            }
        }
        return referenced;
    }

    private static void checkSetReferences(Map<Path, JsonElement> documents,
                                           Map<String, Path> structures,
                                           List<String> problems) {
        for (Map.Entry<Path, JsonElement> entry : documents.entrySet()) {
            String rel = rel(entry.getKey());
            if (rel.contains("/tags/") || !rel.contains("/worldgen/structure_set/")) {
                continue;
            }
            for (JsonElement element : asArrayOrEmpty(entry.getValue(), "structures")) {
                JsonElement id = element.getAsJsonObject().get("structure");
                if (id == null || id.isJsonNull()) {
                    problems.add(rel + ": structure_set entry without a 'structure' id");
                    continue;
                }
                String namespace = id.getAsString().split(":")[0];
                if (!structures.containsKey(id.getAsString()) && !EXTERNAL_NAMESPACES.contains(namespace)) {
                    problems.add(rel + ": references unknown structure '" + id.getAsString() + "'");
                }
            }
        }
    }

    private static void checkTemplatePools(Map<Path, JsonElement> documents, List<String> problems) {
        for (Map.Entry<Path, JsonElement> entry : documents.entrySet()) {
            String rel = rel(entry.getKey());
            if (rel.contains("/tags/") || !rel.contains("/worldgen/template_pool/")) {
                continue;
            }
            var elements = asArrayOrEmpty(entry.getValue(), "elements");
            for (int i = 0; i < elements.size(); i++) {
                JsonElement inner = elements.get(i).getAsJsonObject().get("element");
                if (inner == null || !inner.isJsonObject() || !inner.getAsJsonObject().has("location")) {
                    continue;
                }
                String location = inner.getAsJsonObject().get("location").getAsString();
                String namespace = location.split(":")[0];
                String templatePath = location.substring(location.indexOf(':') + 1);
                Path template = DATA.resolve(namespace).resolve("structure").resolve(templatePath + ".nbt");
                if (!Files.exists(template) && !EXTERNAL_NAMESPACES.contains(namespace)) {
                    problems.add(rel + ": element " + i + " references missing template '"
                            + location + "' (expected " + template + ")");
                }
            }
        }
    }

    private static void checkTags(Map<Path, JsonElement> documents,
                                  Map<String, Path> structures,
                                  Set<String> referenced,
                                  List<String> problems) {
        for (Map.Entry<Path, JsonElement> entry : documents.entrySet()) {
            String rel = rel(entry.getKey());
            if (!rel.contains("/tags/")) {
                continue;
            }
            JsonElement json = entry.getValue();
            if (json.isJsonObject() && json.getAsJsonObject().get("replace") != null
                    && json.getAsJsonObject().get("replace").getAsBoolean()) {
                problems.add(rel + ": 'replace': true is forbidden - capital tags are a shared additive contract");
            }
            for (JsonElement value : asArrayOrEmpty(json, "values")) {
                if (!value.isJsonPrimitive() || value.getAsString().startsWith("#")) {
                    continue;
                }
                String namespace = value.getAsString().split(":")[0];
                if (namespace.equals(OWN_NAMESPACE) && rel.contains("/worldgen/structure/")) {
                    if (!structures.containsKey(value.getAsString()) && !referenced.contains(value.getAsString())) {
                        problems.add(rel + ": tag references '" + value.getAsString()
                                + "' which is not defined in this repo (vanilla would drop it silently)");
                    }
                }
            }
        }
    }

    private static List<JsonElement> asArrayOrEmpty(JsonElement json, String field) {
        if (json == null || !json.isJsonObject() || !json.getAsJsonObject().has(field)
                || !json.getAsJsonObject().get(field).isJsonArray()) {
            return List.of();
        }
        return json.getAsJsonObject().get(field).getAsJsonArray().asList();
    }
}
