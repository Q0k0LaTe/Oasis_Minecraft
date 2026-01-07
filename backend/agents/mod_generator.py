"""
Mod Generator - Creates complete Fabric mod structure with AI-generated textures
"""
import base64
import json
import shutil
import subprocess
from zipfile import ZipFile
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional, List

from PIL import Image

from config import (
    GENERATED_DIR,
    DOWNLOADS_DIR,
    MINECRAFT_VERSION,
    FABRIC_LOADER_VERSION,
    FABRIC_API_VERSION,
    YARN_MAPPINGS,
    JAVA_VERSION,
    RESOURCE_PACK_FORMAT
)
from agents.tools.image_generator import ImageGenerator


class ModGenerator:
    """Generates complete Fabric mod structure and compiles it"""

    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent / "templates"
        self.image_generator = ImageGenerator()

    def generate_mod(self, spec: Dict[str, Any], job_id: str, progress_callback=None) -> Dict[str, Any]:
        """
        Generate complete mod structure and compile it

        Args:
            spec: Mod specification from AI agent
            job_id: Unique job ID
            progress_callback: Optional function to report progress (msg: str) -> None

        Returns:
            Dictionary with generation results
        """
        mod_id = spec["modId"]
        mod_dir = GENERATED_DIR / job_id / mod_id

        texture_info = None

        def log(msg):
            if progress_callback:
                progress_callback(msg)
            print(f"[Job {job_id}] {msg}")

        try:
            # Create mod directory structure
            log(f"Creating directory structure for {mod_id}...")
            self._create_directory_structure(mod_dir, spec)

            # Generate all files
            log("Generating Gradle build files...")
            self._generate_gradle_files(mod_dir, spec)
            
            log("Generating fabric.mod.json...")
            self._generate_fabric_mod_json(mod_dir, spec)
            
            log("Generating Java source code...")
            self._generate_java_files(mod_dir, spec)
            
            log("Generating assets and textures (this may take a moment)...")
            texture_info = self._generate_assets(mod_dir, spec)
            
            log("Generating mixins configuration...")
            self._generate_mixins_json(mod_dir, spec)

            # Copy gradle wrapper
            log("Setting up Gradle wrapper...")
            self._copy_gradle_wrapper(mod_dir)

            # Compile the mod
            log("Compiling mod with Gradle (this can take 1-2 minutes)...")
            jar_path = self._compile_mod(mod_dir, spec, progress_callback)

            if jar_path:
                log("Compilation successful! verifying resources...")
                # Double-check that essential resource pack files made it into the jar
                self._ensure_resource_pack_metadata(
                    jar_path=jar_path,
                    mod_dir=mod_dir,
                    spec=spec,
                    texture_info=texture_info
                )

                # Move to downloads directory
                final_jar = DOWNLOADS_DIR / f"{mod_id}.jar"
                shutil.copy(jar_path, final_jar)
                
                log(f"Mod packaged successfully: {final_jar.name}")

                return {
                    "success": True,
                    "jarPath": str(final_jar),
                    "downloadUrl": f"/downloads/{mod_id}.jar",
                    "textureBase64": texture_info.get("texture_base64") if texture_info else None,
                    "blockTextureBase64": texture_info.get("block_texture_base64") if texture_info else None,
                    "toolTextureBase64": texture_info.get("tool_texture_base64") if texture_info else None
                }
            else:
                log("Compilation failed.")
                return {
                    "success": False,
                    "error": "Compilation failed"
                }

        except Exception as e:
            print(f"Error generating mod: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def generate_mod_with_selected_images(
        self,
        spec: Dict[str, Any],
        job_id: str,
        selected_images: Dict[str, str],
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Generate complete mod structure with user-selected textures

        Args:
            spec: Mod specification from AI agent
            job_id: Unique job ID
            selected_images: Dict with "item", "block", "tool" base64 images
            progress_callback: Optional function to report progress (msg: str) -> None

        Returns:
            Dictionary with generation results
        """
        mod_id = spec["modId"]
        mod_dir = GENERATED_DIR / job_id / mod_id

        def log(msg):
            if progress_callback:
                progress_callback(msg)
            print(f"[Job {job_id}] {msg}")

        try:
            # Create mod directory structure
            log(f"Creating directory structure for {mod_id}...")
            self._create_directory_structure(mod_dir, spec)

            # Generate all files
            log("Generating Gradle build files...")
            self._generate_gradle_files(mod_dir, spec)

            log("Generating fabric.mod.json...")
            self._generate_fabric_mod_json(mod_dir, spec)

            log("Generating Java source code...")
            self._generate_java_files(mod_dir, spec)

            log("Generating assets with your selected textures...")
            texture_info = self._generate_assets_with_selected_images(mod_dir, spec, selected_images)

            log("Generating mixins configuration...")
            self._generate_mixins_json(mod_dir, spec)

            # Copy gradle wrapper
            log("Setting up Gradle wrapper...")
            self._copy_gradle_wrapper(mod_dir)

            # Compile the mod
            log("Compiling mod with Gradle (this can take 1-2 minutes)...")
            jar_path = self._compile_mod(mod_dir, spec, progress_callback)

            if jar_path:
                log("Compilation successful! verifying resources...")
                self._ensure_resource_pack_metadata(
                    jar_path=jar_path,
                    mod_dir=mod_dir,
                    spec=spec,
                    texture_info=texture_info
                )

                # Move to downloads directory
                final_jar = DOWNLOADS_DIR / f"{mod_id}.jar"
                shutil.copy(jar_path, final_jar)

                log(f"Mod packaged successfully: {final_jar.name}")

                return {
                    "success": True,
                    "jarPath": str(final_jar),
                    "downloadUrl": f"/downloads/{mod_id}.jar"
                }
            else:
                log("Compilation failed.")
                return {
                    "success": False,
                    "error": "Compilation failed"
                }

        except Exception as e:
            print(f"Error generating mod with selected images: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def _create_directory_structure(self, mod_dir: Path, spec: Dict[str, Any]):
        """Create the mod directory structure"""
        mod_id = spec["modId"]
        package_path = "com/example/" + mod_id.replace("-", "")

        # Main directories
        (mod_dir / "gradle" / "wrapper").mkdir(parents=True, exist_ok=True)
        (mod_dir / "src" / "main" / "java" / package_path / "item").mkdir(parents=True, exist_ok=True)
        (mod_dir / "src" / "main" / "java" / package_path / "block").mkdir(parents=True, exist_ok=True)
        (mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "lang").mkdir(parents=True, exist_ok=True)
        (mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "items").mkdir(parents=True, exist_ok=True)
        (mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "models" / "item").mkdir(parents=True, exist_ok=True)
        (mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "models" / "block").mkdir(parents=True, exist_ok=True)
        (mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "textures" / "item").mkdir(parents=True, exist_ok=True)
        (mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "textures" / "block").mkdir(parents=True, exist_ok=True)
        (mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "blockstates").mkdir(parents=True, exist_ok=True)
        (mod_dir / "src" / "client" / "java" / package_path).mkdir(parents=True, exist_ok=True)

    def _generate_gradle_files(self, mod_dir: Path, spec: Dict[str, Any]):
        """Generate Gradle build files"""
        mod_id = spec["modId"]

        # gradle.properties
        gradle_props = f"""# Fabric Properties
minecraft_version={MINECRAFT_VERSION}
yarn_mappings={YARN_MAPPINGS}
loader_version={FABRIC_LOADER_VERSION}

# Mod Properties
mod_version=1.0.0
maven_group=com.example.{mod_id.replace('-', '')}
archives_base_name={mod_id}

# Dependencies
fabric_version={FABRIC_API_VERSION}

# Build Configuration
org.gradle.jvmargs=-Xmx2G
org.gradle.parallel=true
"""
        (mod_dir / "gradle.properties").write_text(gradle_props)

        # build.gradle
        build_gradle = """plugins {
\tid 'fabric-loom' version '1.6-SNAPSHOT'
\tid 'maven-publish'
}

version = project.mod_version
group = project.maven_group

repositories {
\tmavenCentral()
}

dependencies {
\tminecraft "com.mojang:minecraft:${project.minecraft_version}"
\tmappings "net.fabricmc:yarn:${project.yarn_mappings}:v2"
\tmodImplementation "net.fabricmc:fabric-loader:${project.loader_version}"
\tmodImplementation "net.fabricmc.fabric-api:fabric-api:${project.fabric_version}"
}

loom {
\tsplitEnvironmentSourceSets()
}

processResources {
\tinputs.property "version", project.version
\tfilteringCharset "UTF-8"

\tfilesMatching("fabric.mod.json") {
\t\texpand "version": project.version
\t}
}

java {
\tsourceCompatibility = JavaVersion.VERSION_21
\ttargetCompatibility = JavaVersion.VERSION_21
\twithSourcesJar()
}

tasks.withType(JavaCompile).configureEach {
\tit.options.release = 21
}

jar {
\tfrom("LICENSE") {
\t\trename { "${it}_${project.archives_base_name}"}
\t}
}
"""
        (mod_dir / "build.gradle").write_text(build_gradle)

        # settings.gradle
        settings_gradle = """pluginManagement {
\trepositories {
\t\tmaven {
\t\t\tname = 'Fabric'
\t\t\turl = 'https://maven.fabricmc.net/'
\t\t}
\t\tmavenCentral()
\t\tgradlePluginPortal()
\t}
}
"""
        (mod_dir / "settings.gradle").write_text(settings_gradle)

        # Create a simple LICENSE file
        (mod_dir / "LICENSE").write_text("MIT License\n\nGenerated by AI Mod Generator")

    def _generate_fabric_mod_json(self, mod_dir: Path, spec: Dict[str, Any]):
        """Generate fabric.mod.json"""
        mod_id = spec["modId"]
        mod_name = spec["modName"]
        author = spec.get("author", "AI Generator")
        package_name = f"com.example.{mod_id.replace('-', '')}"

        fabric_mod = {
            "schemaVersion": 1,
            "id": mod_id,
            "version": "${version}",
            "name": mod_name,
            "description": spec.get("description", "AI generated mod"),
            "authors": [author],
            "contact": {},
            "license": "MIT",
            "icon": f"assets/{mod_id}/icon.png",
            "environment": "*",
            "entrypoints": {
                "main": [f"{package_name}.{self._to_class_name(mod_id)}"],
                "client": [f"{package_name}.{self._to_class_name(mod_id)}Client"]
            },
            "mixins": [f"{mod_id}.mixins.json"],
            "depends": {
                "fabricloader": f">={FABRIC_LOADER_VERSION}",
                "minecraft": f"~{MINECRAFT_VERSION}",
                "java": f">={JAVA_VERSION}",
                "fabric-api": "*"
            }
        }

        fabric_mod_path = mod_dir / "src" / "main" / "resources" / "fabric.mod.json"
        fabric_mod_path.write_text(json.dumps(fabric_mod, indent=2))

    def _generate_java_files(self, mod_dir: Path, spec: Dict[str, Any]):
        """Generate Java source files"""
        mod_id = spec["modId"]
        package_name = f"com.example.{mod_id.replace('-', '')}"
        class_name = self._to_class_name(mod_id)

        # Main mod class
        main_class = f"""package {package_name};

import net.fabricmc.api.ModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import {package_name}.item.ModItems;
import {package_name}.block.ModBlocks;

public class {class_name} implements ModInitializer {{
\tpublic static final String MOD_ID = "{mod_id}";
\tpublic static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

\t@Override
\tpublic void onInitialize() {{
\t\tModItems.registerModItems();
\t\tModBlocks.registerModBlocks();
\t\tLOGGER.info("Loaded {{}} mod!", MOD_ID);
\t}}
}}
"""
        java_path = mod_dir / "src" / "main" / "java" / package_name.replace(".", "/")
        (java_path / f"{class_name}.java").write_text(main_class)

        # Client class
        client_class = f"""package {package_name};

import net.fabricmc.api.ClientModInitializer;

public class {class_name}Client implements ClientModInitializer {{
\t@Override
\tpublic void onInitializeClient() {{
\t\t// Client initialization
\t}}
}}
"""
        client_path = mod_dir / "src" / "client" / "java" / package_name.replace(".", "/")
        (client_path / f"{class_name}Client.java").write_text(client_class)

        # ModItems class
        self._generate_mod_items_class(mod_dir, spec, package_name)
        # ModBlocks class
        self._generate_mod_blocks_class(mod_dir, spec, package_name)

    def _generate_mod_items_class(self, mod_dir: Path, spec: Dict[str, Any], package_name: str):
        """Generate ModItems.java"""
        mod_id = spec["modId"]
        class_name = self._to_class_name(mod_id)
        item_id = spec["itemId"]
        item_var_name = item_id.upper()

        props = spec["properties"]
        max_stack = props["maxStackSize"]
        fireproof = props["fireproof"]
        rarity = props["rarity"]
        creative_tab = props["creativeTab"]
        tool_spec = spec.get("tool")

        # Build item settings
        settings = []
        if max_stack != 64:
            settings.append(f".maxCount({max_stack})")
        if fireproof:
            settings.append(".fireproof()")
        if rarity != "COMMON":
            settings.append(f".rarity(Rarity.{rarity})")

        settings_str = "".join(settings) if settings else ""

        tool_decl = ""
        creative_entries = [(creative_tab.upper(), item_var_name)]

        if tool_spec:
            tool_id = tool_spec["toolId"]
            tool_var = tool_id.upper()
            tool_props = tool_spec.get("properties", {})
            tool_decl = f"""
\tpublic static final Item {tool_var} = registerItem(
\t\t"{tool_id}",
\t\tnew Settings().maxCount(1)
\t);
"""
            creative_entries.append(
                (tool_spec.get("creativeTab", "TOOLS").upper(), tool_var)
            )

        creative_lines = "\n".join(
            f'\t\tItemGroupEvents.modifyEntriesEvent(ItemGroups.{group}).register(entries -> entries.add({var}));'
            for group, var in creative_entries
        )

        mod_items = f"""package {package_name}.item;

import {package_name}.{class_name};
import net.fabricmc.fabric.api.itemgroup.v1.ItemGroupEvents;
import net.minecraft.item.Item;
import net.minecraft.item.Item.Settings;
import net.minecraft.item.ItemGroups;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.registry.RegistryKey;
import net.minecraft.registry.RegistryKeys;
import net.minecraft.util.Identifier;
import net.minecraft.util.Rarity;

public class ModItems {{

\tpublic static final Item {item_var_name} = registerItem("{item_id}",
\t\tnew Settings(){settings_str});
{tool_decl}
\tprivate static Item registerItem(String name, Item.Settings settings) {{
\t\tIdentifier id = Identifier.of({class_name}.MOD_ID, name);
\t\tRegistryKey<Item> itemKey = RegistryKey.of(RegistryKeys.ITEM, id);
\t\tsettings.registryKey(itemKey);

\t\t{class_name}.LOGGER.info("Registering item: {{}}", id);
\t\treturn Registry.register(Registries.ITEM, id, new Item(settings));
\t}}
\tpublic static void registerModItems() {{
\t\t{class_name}.LOGGER.info("Registering items for {{}}", {class_name}.MOD_ID);
\t\t
\t\t// Add to creative tabs
{creative_lines}
\t}}
}}
"""
        items_path = mod_dir / "src" / "main" / "java" / package_name.replace(".", "/") / "item"
        (items_path / "ModItems.java").write_text(mod_items)

    def _generate_mod_blocks_class(self, mod_dir: Path, spec: Dict[str, Any], package_name: str):
        """Generate ModBlocks.java with optional block registration."""
        mod_id = spec["modId"]
        class_name = self._to_class_name(mod_id)
        block_spec = spec.get("block")
        blocks_path = mod_dir / "src" / "main" / "java" / package_name.replace(".", "/") / "block"

        if not block_spec:
            stub = f"""package {package_name}.block;

import {package_name}.{class_name};

public class ModBlocks {{
\tpublic static void registerModBlocks() {{
\t\t{class_name}.LOGGER.info("No custom blocks declared for {{}}", {class_name}.MOD_ID);
\t}}
}}
"""
            (blocks_path / "ModBlocks.java").write_text(stub)
            return

        block_id = block_spec["blockId"]
        block_name = block_spec["blockName"]
        block_var = block_id.upper().replace("-", "_")
        props = block_spec.get("properties", {})
        material = props.get("material", "STONE").upper()
        sound_group = props.get("soundGroup", "STONE").upper()
        hardness = float(props.get("hardness", 1.5))
        resistance = float(props.get("resistance", 6.0))
        luminance = int(props.get("luminance", 0))
        requires_tool = props.get("requiresTool", False)
        creative_tab = props.get("creativeTab", "BUILDING_BLOCKS").upper()

        base_block_lookup = {
            "STONE": "STONE",
            "METAL": "IRON_BLOCK",
            "WOOD": "OAK_PLANKS",
            "GLASS": "GLASS",
            "PLANT": "MOSS_BLOCK",
            "SAND": "SANDSTONE",
            "ORGANIC": "MOSS_BLOCK",
            "DEEPSLATE": "DEEPSLATE",
        }
        base_block = base_block_lookup.get(material, "STONE")

        hardness_str = f"{hardness:.1f}f"
        resistance_str = f"{resistance:.1f}f"
        settings_chain = [
            f"AbstractBlock.Settings.copy(Blocks.{base_block})",
            f".strength({hardness_str}, {resistance_str})",
            f".sounds(BlockSoundGroup.{sound_group})"
        ]
        if luminance > 0:
            settings_chain.append(f".luminance(state -> {min(luminance, 15)})")
        if requires_tool:
            settings_chain.append(".requiresTool()")
        settings_expr = "".join(settings_chain)

        drop_item = block_spec.get("dropItemId", block_id)
        block_template = f"""package {package_name}.block;

import {package_name}.{class_name};
import net.fabricmc.fabric.api.itemgroup.v1.ItemGroupEvents;
import net.minecraft.block.AbstractBlock;
import net.minecraft.block.Block;
import net.minecraft.block.Blocks;
import net.minecraft.item.BlockItem;
import net.minecraft.item.Item;
import net.minecraft.item.ItemGroups;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.registry.RegistryKey;
import net.minecraft.registry.RegistryKeys;
import net.minecraft.sound.BlockSoundGroup;
import net.minecraft.util.Identifier;

public class ModBlocks {{

\tpublic static final Block {block_var} = registerBlock(
\t\t"{block_id}",
\t\t{settings_expr},
\t\tItemGroups.{creative_tab}
\t);

\tprivate static Block registerBlock(String name, AbstractBlock.Settings settings, RegistryKey<net.minecraft.item.ItemGroup> group) {{
\t\tRegistryKey<Block> blockKey = RegistryKey.of(RegistryKeys.BLOCK, Identifier.of({class_name}.MOD_ID, name));
\t\tsettings.registryKey(blockKey);
\t\tBlock block = new Block(settings);
\t\tregisterBlockItem(name, block, group);
\t\treturn Registry.register(Registries.BLOCK, blockKey, block);
\t}}

\tprivate static void registerBlockItem(String name, Block block, RegistryKey<net.minecraft.item.ItemGroup> group) {{
\t\tRegistryKey<Item> itemKey = RegistryKey.of(RegistryKeys.ITEM, Identifier.of({class_name}.MOD_ID, name));
\t\tBlockItem blockItem = new BlockItem(block, new Item.Settings().registryKey(itemKey));
\t\tItem registered = Registry.register(Registries.ITEM, itemKey, blockItem);
\t\tItemGroupEvents.modifyEntriesEvent(group).register(entries -> entries.add(registered));
\t}}

\tpublic static void registerModBlocks() {{
\t\t{class_name}.LOGGER.info("Registering block: {{}} ({block_name}) drops {drop_item}", {class_name}.MOD_ID);
\t}}
}}
"""
        (blocks_path / "ModBlocks.java").write_text(block_template)

    def _generate_assets(self, mod_dir: Path, spec: Dict[str, Any]):
        """Generate asset files (lang, models, textures) with AI-generated images"""
        mod_id = spec["modId"]
        item_id = spec["itemId"]
        item_name = spec["itemName"]
        block_spec = spec.get("block")
        tool_spec = spec.get("tool")

        assets_dir = mod_dir / "src" / "main" / "resources" / "assets" / mod_id
        resources_root = mod_dir / "src" / "main" / "resources"

        # Language file
        lang = {
            f"item.{mod_id}.{item_id}": item_name,
        }
        if block_spec:
            block_name = block_spec["blockName"]
            block_id = block_spec["blockId"]
            lang[f"block.{mod_id}.{block_id}"] = block_name
            lang[f"item.{mod_id}.{block_id}"] = block_name
        if tool_spec:
            lang[f"item.{mod_id}.{tool_spec['toolId']}"] = tool_spec["toolName"]
        (assets_dir / "lang" / "en_us.json").write_text(json.dumps(lang, indent=2))

        # Item model definition (required since Minecraft 1.21.4+)
        (assets_dir / "items").mkdir(exist_ok=True)
        item_definition = {
            "model": {
                "type": "model",
                "model": f"{mod_id}:item/{item_id}"
            }
        }
        (assets_dir / "items" / f"{item_id}.json").write_text(json.dumps(item_definition, indent=2))

        # Item model
        model = {
            "parent": "minecraft:item/generated",
            "textures": {
                "layer0": f"{mod_id}:item/{item_id}"
            }
        }
        (assets_dir / "models" / "item" / f"{item_id}.json").write_text(json.dumps(model, indent=2))

        # Generate AI texture using DALL-E
        texture_path = assets_dir / "textures" / "item" / f"{item_id}.png"
        icon_path = assets_dir / "icon.png"

        png_data = self.image_generator.generate_texture_from_spec(spec)
        texture_path.write_bytes(png_data)
        texture_base64 = base64.b64encode(png_data).decode("utf-8")

        block_texture_base64 = None
        block_texture_path = None
        tool_texture_base64 = None
        if block_spec:
            block_id = block_spec["blockId"]
            blockstates_dir = assets_dir / "blockstates"
            blockstate = {
                "variants": {
                    "": {
                        "model": f"{mod_id}:block/{block_id}"
                    }
                }
            }
            (blockstates_dir / f"{block_id}.json").write_text(json.dumps(blockstate, indent=2))

            block_model = {
                "parent": "minecraft:block/cube_all",
                "textures": {
                    "all": f"{mod_id}:block/{block_id}"
                }
            }
            (assets_dir / "models" / "block" / f"{block_id}.json").write_text(json.dumps(block_model, indent=2))

            # Block item definition
            block_item_definition = {
                "model": {
                    "type": "model",
                    "model": f"{mod_id}:block/{block_id}"
                }
            }
            (assets_dir / "items" / f"{block_id}.json").write_text(json.dumps(block_item_definition, indent=2))

            block_item_model = {
                "parent": f"{mod_id}:block/{block_id}"
            }
            (assets_dir / "models" / "item" / f"{block_id}.json").write_text(json.dumps(block_item_model, indent=2))

            block_texture_path = assets_dir / "textures" / "block" / f"{block_id}.png"
            block_png = self.image_generator.generate_block_texture_from_spec(block_spec)

            block_texture_path.write_bytes(block_png)
            block_texture_base64 = base64.b64encode(block_png).decode("utf-8")
            self._write_block_data(resources_root, mod_id, block_spec, spec.get("itemId"))
            self._write_block_recipes(resources_root, mod_id, block_spec, spec.get("itemId"))

        if tool_spec:
            tool_id = tool_spec["toolId"]
            tool_name = tool_spec["toolName"]
            
            # Tool item definition
            tool_definition = {
                "model": {
                    "type": "model",
                    "model": f"{mod_id}:item/{tool_id}"
                }
            }
            (assets_dir / "items" / f"{tool_id}.json").write_text(json.dumps(tool_definition, indent=2))

            handheld_model = {
                "parent": "minecraft:item/handheld",
                "textures": {
                    "layer0": f"{mod_id}:item/{tool_id}"
                }
            }
            (assets_dir / "models" / "item" / f"{tool_id}.json").write_text(json.dumps(handheld_model, indent=2))

            tool_texture_path = assets_dir / "textures" / "item" / f"{tool_id}.png"
            tool_png = self.image_generator.generate_tool_texture(tool_spec)
            tool_texture_path.write_bytes(tool_png)
            tool_texture_base64 = base64.b64encode(tool_png).decode("utf-8")
            self._write_tool_recipe(resources_root, mod_id, tool_spec, item_id)
            self._write_tool_item_file(
                resources_root,
                mod_id,
                tool_spec,
                spec.get("properties", {}),
            )

        # Create a Fabric-friendly icon by upscaling the generated texture
        self._create_icon_from_texture(png_data, icon_path)

        # pack.mcmeta helps Minecraft treat the bundled resources as a proper resource pack
        pack_meta = {
            "pack": {
                "pack_format": RESOURCE_PACK_FORMAT,
                "description": f"{spec['modName']} assets generated by AI"
            }
        }
        (resources_root / "pack.mcmeta").write_text(json.dumps(pack_meta, indent=2))
        # Marker file used by Minecraft to treat this jar as a resource pack
        (assets_dir / ".mcassetsroot").write_text("")

        return {
            "texture_path": texture_path,
            "icon_path": icon_path,
            "texture_base64": texture_base64,
            "block_texture_base64": block_texture_base64,
            "block_texture_path": block_texture_path,
            "tool_texture_base64": tool_texture_base64
        }

    def _generate_assets_with_selected_images(
        self,
        mod_dir: Path,
        spec: Dict[str, Any],
        selected_images: Dict[str, str]
    ):
        """Generate asset files using user-selected textures"""
        mod_id = spec["modId"]
        item_id = spec["itemId"]
        item_name = spec["itemName"]
        block_spec = spec.get("block")
        tool_spec = spec.get("tool")

        assets_dir = mod_dir / "src" / "main" / "resources" / "assets" / mod_id
        resources_root = mod_dir / "src" / "main" / "resources"

        # Language file
        lang = {
            f"item.{mod_id}.{item_id}": item_name,
        }
        if block_spec:
            block_name = block_spec["blockName"]
            block_id = block_spec["blockId"]
            lang[f"block.{mod_id}.{block_id}"] = block_name
            lang[f"item.{mod_id}.{block_id}"] = block_name
        if tool_spec:
            lang[f"item.{mod_id}.{tool_spec['toolId']}"] = tool_spec["toolName"]
        (assets_dir / "lang" / "en_us.json").write_text(json.dumps(lang, indent=2))

        # Item model definition
        (assets_dir / "items").mkdir(exist_ok=True)
        item_definition = {
            "model": {
                "type": "model",
                "model": f"{mod_id}:item/{item_id}"
            }
        }
        (assets_dir / "items" / f"{item_id}.json").write_text(json.dumps(item_definition, indent=2))

        # Item model
        model = {
            "parent": "minecraft:item/generated",
            "textures": {
                "layer0": f"{mod_id}:item/{item_id}"
            }
        }
        (assets_dir / "models" / "item" / f"{item_id}.json").write_text(json.dumps(model, indent=2))

        # Use selected item texture
        texture_path = assets_dir / "textures" / "item" / f"{item_id}.png"
        icon_path = assets_dir / "icon.png"

        png_data = base64.b64decode(selected_images["item"])
        texture_path.write_bytes(png_data)

        block_texture_path = None
        if block_spec and "block" in selected_images:
            block_id = block_spec["blockId"]
            blockstates_dir = assets_dir / "blockstates"
            blockstate = {
                "variants": {
                    "": {
                        "model": f"{mod_id}:block/{block_id}"
                    }
                }
            }
            (blockstates_dir / f"{block_id}.json").write_text(json.dumps(blockstate, indent=2))

            block_model = {
                "parent": "minecraft:block/cube_all",
                "textures": {
                    "all": f"{mod_id}:block/{block_id}"
                }
            }
            (assets_dir / "models" / "block" / f"{block_id}.json").write_text(json.dumps(block_model, indent=2))

            # Block item definition
            block_item_definition = {
                "model": {
                    "type": "model",
                    "model": f"{mod_id}:block/{block_id}"
                }
            }
            (assets_dir / "items" / f"{block_id}.json").write_text(json.dumps(block_item_definition, indent=2))

            block_item_model = {
                "parent": f"{mod_id}:block/{block_id}"
            }
            (assets_dir / "models" / "item" / f"{block_id}.json").write_text(json.dumps(block_item_model, indent=2))

            # Use selected block texture
            block_texture_path = assets_dir / "textures" / "block" / f"{block_id}.png"
            block_png = base64.b64decode(selected_images["block"])
            block_texture_path.write_bytes(block_png)

            self._write_block_data(resources_root, mod_id, block_spec, item_id)
            self._write_block_recipes(resources_root, mod_id, block_spec, item_id)

        if tool_spec and "tool" in selected_images:
            tool_id = tool_spec["toolId"]
            tool_name = tool_spec["toolName"]

            # Tool item definition
            tool_definition = {
                "model": {
                    "type": "model",
                    "model": f"{mod_id}:item/{tool_id}"
                }
            }
            (assets_dir / "items" / f"{tool_id}.json").write_text(json.dumps(tool_definition, indent=2))

            handheld_model = {
                "parent": "minecraft:item/handheld",
                "textures": {
                    "layer0": f"{mod_id}:item/{tool_id}"
                }
            }
            (assets_dir / "models" / "item" / f"{tool_id}.json").write_text(json.dumps(handheld_model, indent=2))

            # Use selected tool texture
            tool_texture_path = assets_dir / "textures" / "item" / f"{tool_id}.png"
            tool_png = base64.b64decode(selected_images["tool"])
            tool_texture_path.write_bytes(tool_png)

            self._write_tool_recipe(resources_root, mod_id, tool_spec, item_id)
            self._write_tool_item_file(
                resources_root,
                mod_id,
                tool_spec,
                spec.get("properties", {}),
            )

        # Create icon from item texture
        self._create_icon_from_texture(png_data, icon_path)

        # pack.mcmeta
        pack_meta = {
            "pack": {
                "pack_format": RESOURCE_PACK_FORMAT,
                "description": f"{spec['modName']} assets generated by AI"
            }
        }
        (resources_root / "pack.mcmeta").write_text(json.dumps(pack_meta, indent=2))
        (assets_dir / ".mcassetsroot").write_text("")

        return {
            "texture_path": texture_path,
            "icon_path": icon_path,
            "block_texture_path": block_texture_path,
        }

    def _write_block_data(self, resources_root: Path, mod_id: str, block_spec: Dict[str, Any], default_drop: str):
        """Create loot table and mining tags so the block behaves like an ore."""
        block_id = block_spec["blockId"]
        drop_id = block_spec.get("dropItemId") or default_drop
        data_root = resources_root / "data"

        loot_dir = data_root / mod_id / "loot_tables" / "blocks"
        loot_dir.mkdir(parents=True, exist_ok=True)
        loot_table = {
            "type": "minecraft:block",
            "pools": [
                {
                    "rolls": 1,
                    "entries": [
                        {
                            "type": "minecraft:item",
                            "name": f"{mod_id}:{drop_id}"
                        }
                    ],
                    "conditions": [
                        {"condition": "minecraft:survives_explosion"}
                    ]
                }
            ]
        }
        (loot_dir / f"{block_id}.json").write_text(json.dumps(loot_table, indent=2))

        # Mining tags so only proper pickaxes can harvest it
        tags_root = data_root / "minecraft" / "tags" / "blocks"
        pickaxe_dir = tags_root / "mineable"
        pickaxe_dir.mkdir(parents=True, exist_ok=True)
        (pickaxe_dir / "pickaxe.json").write_text(json.dumps({
            "replace": False,
            "values": [f"{mod_id}:{block_id}"]
        }, indent=2))

        needs_tool_file = tags_root / "needs_iron_tool.json"
        needs_tool_file.parent.mkdir(parents=True, exist_ok=True)
        needs_tool_file.write_text(json.dumps({
            "replace": False,
            "values": [f"{mod_id}:{block_id}"]
        }, indent=2))

    def _write_block_recipes(
        self,
        resources_root: Path,
        mod_id: str,
        block_spec: Dict[str, Any],
        primary_item_id: Optional[str],
    ):
        """Create compression/decompression recipes for the custom block."""
        if not primary_item_id:
            return

        variants = block_spec.get("variants", [])
        if not variants:
            variants = [
                {
                    "recipe": {
                        "id": f"{block_spec['blockId']}_compression",
                        "type": "minecraft:crafting_shaped",
                        "pattern": ["###", "###", "###"],
                        "legend": {
                            "#": {
                                "item": f"{mod_id}:{primary_item_id}"
                            }
                        },
                        "result": {
                            "item": f"{mod_id}:{block_spec['blockId']}"
                        }
                    }
                },
                {
                    "recipe": {
                        "id": f"{block_spec['blockId']}_reclaim",
                        "type": "minecraft:crafting_shaped",
                        "pattern": ["#"],
                        "legend": {
                            "#": {
                                "item": f"{mod_id}:{block_spec['blockId']}"
                            }
                        },
                        "result": {
                            "item": f"{mod_id}:{primary_item_id}",
                            "count": 9
                        }
                    }
                }
            ]

        recipes_dir = resources_root / "data" / mod_id / "recipes"
        recipes_dir.mkdir(parents=True, exist_ok=True)

        for variant in variants:
            recipe = variant.get("recipe")
            if not recipe:
                continue

            base_pattern = recipe.get("pattern") or []
            if not base_pattern:
                continue

            legend = recipe.get("legend", {})
            result = recipe.get("result", {})
            recipe_type = recipe.get("type", "minecraft:crafting_shaped")

            def _write_recipe_file(pattern: List[str], suffix: str = ""):
                shaped = {
                    "type": recipe_type,
                    "pattern": pattern,
                    "key": {
                        symbol: {"item": entry.get("item")}
                        for symbol, entry in legend.items()
                        if entry.get("item")
                    },
                    "result": {
                        "item": result.get("item", f"{mod_id}:{block_spec['blockId']}")
                    }
                }
                count = result.get("count")
                if count and count != 1:
                    shaped["result"]["count"] = count
                file_stem = recipe.get("id") or f"{block_spec['blockId']}_recipe"
                file_name = f"{file_stem}{suffix}.json"
                (recipes_dir / file_name).write_text(json.dumps(shaped, indent=2))

            _write_recipe_file(base_pattern)
            for idx, alt_pattern in enumerate(recipe.get("alternates", []), start=1):
                _write_recipe_file(alt_pattern, suffix=f"_alt{idx}")

    def _write_tool_recipe(self, resources_root: Path, mod_id: str, tool_spec: Dict[str, Any], primary_item_id: str):
        """Create crafting recipes that match the requested tool type."""
        recipes_dir = resources_root / "data" / mod_id / "recipes"
        recipes_dir.mkdir(parents=True, exist_ok=True)
        config = self._get_tool_type_config(tool_spec.get("toolType"))
        forging_recipe = tool_spec.get("forgingRecipe") or {}

        def _write_recipe_file(pattern: List[str], suffix: str = ""):
            recipe = {
                "type": forging_recipe.get("type", "minecraft:crafting_shaped"),
                "pattern": pattern,
                "key": {
                    symbol: {"item": entry}
                    for symbol, entry in _legend_map.items()
                },
                "result": {
                    "item": result_item
                }
            }
            if result_count != 1:
                recipe["result"]["count"] = result_count
            file_name = f"{tool_spec['toolId']}{suffix}.json"
            (recipes_dir / file_name).write_text(json.dumps(recipe, indent=2))

        legend_entries = forging_recipe.get("legend")
        if legend_entries:
            _legend_map = {
                symbol: entry.get("item")
                for symbol, entry in legend_entries.items()
                if entry.get("item")
            }
        else:
            _legend_map = {
                "#": f"{mod_id}:{primary_item_id}",
                "S": "minecraft:stick"
            }

        result_info = forging_recipe.get("result", {})
        result_item = result_info.get("item", f"{mod_id}:{tool_spec['toolId']}")
        result_count = result_info.get("count", 1)

        primary_pattern = forging_recipe.get("pattern") or config["recipe"]
        _write_recipe_file(primary_pattern)

        alt_patterns = forging_recipe.get("alternates") or config.get("alt_recipes", [])
        for idx, alt in enumerate(alt_patterns, start=1):
            _write_recipe_file(alt, suffix=f"_alt{idx}")

    def _write_tool_item_file(
        self,
        resources_root: Path,
        mod_id: str,
        tool_spec: Dict[str, Any],
        item_properties: Dict[str, Any],
    ):
        """Define tool behavior using the new item component JSON schema."""
        items_dir = resources_root / "data" / mod_id / "items"
        items_dir.mkdir(parents=True, exist_ok=True)

        props = tool_spec.get("properties", {})
        config = self._get_tool_type_config(tool_spec.get("toolType"))

        attack_damage = float(props.get("attackDamage", 3))
        attack_speed = float(props.get("attackSpeed", -2.8))
        durability = int(props.get("durability", 400))
        mining_speed = float(props.get("miningSpeed", 6.0))
        mining_level = int(props.get("miningLevel", 2))
        enchantability = int(props.get("enchantability", 14))

        components = {
            "minecraft:durability": {
                "max_durability": durability
            },
            "minecraft:enchantable": {
                "value": enchantability,
                "slots": config["enchant_slots"],
            },
            "minecraft:attribute_modifiers": {
                "modifiers": [
                    {
                        "type": "minecraft:generic.attack_damage",
                        "amount": attack_damage,
                        "operation": "add_value",
                        "slot": "mainhand"
                    },
                    {
                        "type": "minecraft:generic.attack_speed",
                        "amount": attack_speed,
                        "operation": "add_value",
                        "slot": "mainhand"
                    }
                ],
                "show_in_tooltip": True
            }
        }

        tag = config.get("tag")
        if tag:
            components["minecraft:tool"] = {
                "default_mining_speed": 1.0,
                "damage_per_block": 1,
                "rules": [
                    {
                        "blocks": tag,
                        "speed": mining_speed,
                        "correct_for_drops": True,
                        "mining_level": mining_level
                    }
                ]
            }

        special_ability = item_properties.get("specialAbility")
        if special_ability:
            components["minecraft:lore"] = [
                {
                    "text": special_ability,
                    "italic": False
                }
            ]

        item_data = {
            "components": components
        }
        (items_dir / f"{tool_spec['toolId']}.json").write_text(json.dumps(item_data, indent=2))

    def _get_tool_type_config(self, tool_type: Optional[str]) -> Dict[str, Any]:
        tool_type = (tool_type or "PICKAXE").upper()
        configs = {
            "PICKAXE": {
                "tag": "#minecraft:mineable/pickaxe",
                "recipe": ["###", " S ", " S "],
                "enchant_slots": ["digging"]
            },
            "AXE": {
                "tag": "#minecraft:mineable/axe",
                "recipe": ["##", "S#", " S"],
                "alt_recipes": [["##", "#S", " S"]],
                "enchant_slots": ["digging"]
            },
            "SHOVEL": {
                "tag": "#minecraft:mineable/shovel",
                "recipe": ["#", "S", "S"],
                "enchant_slots": ["digging"]
            },
            "HOE": {
                "tag": "#minecraft:mineable/hoe",
                "recipe": ["##", " S", " S"],
                "alt_recipes": [["##", "S ", "S "]],
                "enchant_slots": ["digging"]
            },
            "SWORD": {
                "tag": None,
                "recipe": ["#", "#", "S"],
                "enchant_slots": ["weapon"]
            }
        }
        return configs.get(tool_type, configs["PICKAXE"])

    def _create_icon_from_texture(self, png_data: bytes, icon_path: Path):
        """Upscale the generated texture so Fabric's icon reference always exists"""
        img = Image.open(BytesIO(png_data))
        upscale = img.resize((128, 128), Image.Resampling.NEAREST)
        buffer = BytesIO()
        upscale.save(buffer, format="PNG")
        icon_path.write_bytes(buffer.getvalue())
        print(f"✓ Mod icon saved to {icon_path}")

    def _generate_mixins_json(self, mod_dir: Path, spec: Dict[str, Any]):
        """Generate mixins JSON (empty but required)"""
        mod_id = spec["modId"]
        package_name = f"com.example.{mod_id.replace('-', '')}.mixin"

        mixins = {
            "required": True,
            "package": package_name,
            "compatibilityLevel": "JAVA_21",
            "mixins": [],
            "injectors": {
                "defaultRequire": 1
            }
        }

        mixins_path = mod_dir / "src" / "main" / "resources" / f"{mod_id}.mixins.json"
        mixins_path.write_text(json.dumps(mixins, indent=2))

    def _copy_gradle_wrapper(self, mod_dir: Path):
        """Copy a full Gradle wrapper so we control the Gradle version"""
        template_dir = self.templates_dir / "gradle_wrapper_template"
        if not template_dir.exists():
            raise RuntimeError("Gradle wrapper template is missing. Re-run setup.")

        # Copy wrapper directory (contains gradle-wrapper.jar + properties pinned to 8.5)
        shutil.copytree(
            template_dir / "gradle" / "wrapper",
            mod_dir / "gradle" / "wrapper",
            dirs_exist_ok=True
        )

        # Copy launch scripts
        shutil.copy(template_dir / "gradlew", mod_dir / "gradlew")
        shutil.copy(template_dir / "gradlew.bat", mod_dir / "gradlew.bat")

        # Ensure Unix wrapper is executable
        (mod_dir / "gradlew").chmod(0o755)

    def _compile_mod(self, mod_dir: Path, spec: Dict[str, Any], progress_callback=None) -> Optional[Path]:
        """
        Compile the mod using Gradle

        Returns:
            Path to compiled JAR file, or None if compilation failed
        """
        try:
            print(f"Compiling mod at {mod_dir}")
            if progress_callback:
                progress_callback(f"Starting Gradle build in {mod_dir.name}...")

            # Run gradle build with Popen to capture output real-time
            process = subprocess.Popen(
                ["./gradlew", "build", "--no-daemon"],
                cwd=mod_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Stream output
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                
                # Log significant lines
                is_significant = any(k in line for k in [
                    "Compiling", "Building", "Processing", "Task :", "BUILD SUCCESSFUL", "FAILED"
                ])
                
                if is_significant and progress_callback:
                    # clean up the log message a bit
                    clean_line = line.replace("Task :", "Task: ")
                    progress_callback(f"> {clean_line}")
            
            process.wait(timeout=300)

            if process.returncode == 0:
                # Find the built JAR
                build_libs = mod_dir / "build" / "libs"
                if build_libs.exists():
                    jar_files = list(build_libs.glob("*.jar"))
                    # Filter out sources jar
                    jar_files = [j for j in jar_files if "-sources" not in j.name]
                    if jar_files:
                        return jar_files[0]
            else:
                if progress_callback:
                    progress_callback("Gradle build failed. Check server logs.")
                print(f"Gradle build failed with code {process.returncode}")

            return None

        except subprocess.TimeoutExpired:
            print("Gradle build timed out")
            if progress_callback:
                progress_callback("Error: Gradle build timed out")
            return None
        except Exception as e:
            print(f"Error compiling mod: {e}")
            if progress_callback:
                progress_callback(f"Error compiling mod: {e}")
            return None

    def _to_class_name(self, mod_id: str) -> str:
        """Convert mod ID to Java class name"""
        # Remove hyphens and underscores, capitalize each word
        parts = mod_id.replace("-", " ").replace("_", " ").split()
        return "".join(word.capitalize() for word in parts) + "Mod"

    def _ensure_resource_pack_metadata(
        self,
        jar_path: Path,
        mod_dir: Path,
        spec: Dict[str, Any],
        texture_info: Optional[Dict[str, Any]]
    ):
        """
        Make sure pack.mcmeta, .mcassetsroot, and textures exist inside the built jar.
        Some Minecraft versions ignore mod assets without these markers, which results
        in purple/black missing-texture placeholders.
        """
        try:
            mod_id = spec["modId"]
            item_id = spec["itemId"]
            resources_root = mod_dir / "src" / "main" / "resources"
            assets_dir = resources_root / "assets" / mod_id

            # Ensure pack.mcmeta exists on disk (create if a previous run skipped it)
            pack_meta_path = resources_root / "pack.mcmeta"
            if not pack_meta_path.exists():
                pack_meta = {
                    "pack": {
                        "pack_format": RESOURCE_PACK_FORMAT,
                        "description": f"{spec['modName']} assets generated by AI"
                    }
                }
                resources_root.mkdir(parents=True, exist_ok=True)
                pack_meta_path.write_text(json.dumps(pack_meta, indent=2))

            # Ensure the mod namespace has a .mcassetsroot marker
            mcassetsroot_path = assets_dir / ".mcassetsroot"
            if not mcassetsroot_path.exists():
                assets_dir.mkdir(parents=True, exist_ok=True)
                mcassetsroot_path.write_text("")

            # Optional: texture/icon/item definition paths (may have been generated earlier)
            texture_path = assets_dir / "textures" / "item" / f"{item_id}.png"
            icon_path = assets_dir / "icon.png"
            item_def_path = assets_dir / "items" / f"{item_id}.json"
            block_spec = spec.get("block")
            block_id = block_spec["blockId"] if block_spec else None
            block_texture_path = assets_dir / "textures" / "block" / f"{block_id}.png" if block_spec else None
            blockstate_path = assets_dir / "blockstates" / f"{block_id}.json" if block_spec else None
            block_model_path = assets_dir / "models" / "block" / f"{block_id}.json" if block_spec else None
            block_item_model_path = assets_dir / "models" / "item" / f"{block_id}.json" if block_spec else None
            if texture_info:
                texture_path = Path(texture_info.get("texture_path", texture_path))
                icon_path = Path(texture_info.get("icon_path", icon_path))
                if block_spec and texture_info.get("block_texture_path"):
                    block_texture_path = Path(texture_info["block_texture_path"])

            # Create item definition if missing (required for 1.21.4+)
            if not item_def_path.exists():
                (assets_dir / "items").mkdir(parents=True, exist_ok=True)
                item_definition = {
                    "model": {
                        "type": "model",
                        "model": f"{mod_id}:item/{item_id}"
                    }
                }
                item_def_path.write_text(json.dumps(item_definition, indent=2))

            with ZipFile(jar_path, "a") as jar:
                jar_contents = set(jar.namelist())

                def add_file(path: Path, arcname: str):
                    if not path.exists():
                        return
                    if arcname in jar_contents:
                        return
                    jar.write(path, arcname=arcname)
                    jar_contents.add(arcname)

                add_file(pack_meta_path, "pack.mcmeta")
                add_file(mcassetsroot_path, f"assets/{mod_id}/.mcassetsroot")
                
                # Add items definition if it exists (base item)
                if item_def_path and item_def_path.exists():
                    add_file(item_def_path, f"assets/{mod_id}/items/{item_id}.json")
                
                # Add tool item definition if tool exists
                tool_spec = spec.get("tool")
                if tool_spec:
                    tool_id = tool_spec["toolId"]
                    tool_item_def = assets_dir / "items" / f"{tool_id}.json"
                    if tool_item_def.exists():
                        add_file(tool_item_def, f"assets/{mod_id}/items/{tool_id}.json")
                    
                    # Add tool texture
                    tool_texture_path = assets_dir / "textures" / "item" / f"{tool_id}.png"
                    if tool_texture_path.exists():
                        add_file(tool_texture_path, f"assets/{mod_id}/textures/item/{tool_id}.png")

                add_file(texture_path, f"assets/{mod_id}/textures/item/{item_id}.png")
                add_file(icon_path, f"assets/{mod_id}/icon.png")
                
                if block_spec:
                    add_file(blockstate_path, f"assets/{mod_id}/blockstates/{block_id}.json")
                    add_file(block_model_path, f"assets/{mod_id}/models/block/{block_id}.json")
                    add_file(block_item_model_path, f"assets/{mod_id}/models/item/{block_id}.json")
                    add_file(block_texture_path, f"assets/{mod_id}/textures/block/{block_id}.png")
                    
                    # Also ensure block item definition is included
                    block_item_def = assets_dir / "items" / f"{block_id}.json"
                    if block_item_def.exists():
                        add_file(block_item_def, f"assets/{mod_id}/items/{block_id}.json")

        except Exception as e:
            print(f"Warning: could not verify jar resources: {e}")
