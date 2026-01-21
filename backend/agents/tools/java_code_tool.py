"""
Java Code Generator Tool - Generates Java source code files

This tool creates all Java source files for the mod (main class, items, blocks, etc.).
"""
from pathlib import Path
from typing import Dict, Any, List
from textwrap import dedent


def generate_java_code(
    workspace_path: Path,
    package_name: str,
    mod_id: str,
    main_class_name: str,
    items: List[Dict[str, Any]] = None,
    blocks: List[Dict[str, Any]] = None,
    tools: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate Java source code files

    Args:
        workspace_path: Mod directory path
        package_name: Java package name
        mod_id: Mod identifier
        main_class_name: Main class name
        items: List of item specifications from IR
        blocks: List of block specifications from IR
        tools: List of tool specifications from IR

    Returns:
        Dictionary with paths to generated files
    """
    mod_dir = Path(workspace_path)
    java_path = mod_dir / "src" / "main" / "java" / package_name.replace(".", "/")
    client_path = mod_dir / "src" / "client" / "java" / package_name.replace(".", "/")

    items = items or []
    blocks = blocks or []
    tools = tools or []

    # Generate main mod class
    main_class = dedent(f"""\
        package {package_name};

        import net.fabricmc.api.ModInitializer;
        import org.slf4j.Logger;
        import org.slf4j.LoggerFactory;
        import {package_name}.item.ModItems;
        import {package_name}.block.ModBlocks;
        import {package_name}.item.ModItemGroups;

        public class {main_class_name} implements ModInitializer {{
        \tpublic static final String MOD_ID = "{mod_id}";
        \tpublic static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

        \t@Override
        \tpublic void onInitialize() {{
        \t\tModItems.registerModItems();
        \t\tModBlocks.registerModBlocks();
        \t\tModItemGroups.registerModItemGroups();
        \t\tLOGGER.info("Loaded {{}} mod!", MOD_ID);
        \t}}
        }}
        """)
    main_class_path = java_path / f"{main_class_name}.java"
    main_class_path.write_text(main_class)

    # Generate client class
    client_class = dedent(f"""\
        package {package_name};

        import net.fabricmc.api.ClientModInitializer;

        public class {main_class_name}Client implements ClientModInitializer {{
        \t@Override
        \tpublic void onInitializeClient() {{
        \t\t// Client initialization
        \t}}
        }}
        """)
    client_class_path = client_path / f"{main_class_name}Client.java"
    client_class_path.write_text(client_class)

    # Generate ModItems class
    items_class_path = _generate_mod_items_class(java_path, package_name, mod_id, main_class_name, items)

    # Generate ModBlocks class
    blocks_class_path = _generate_mod_blocks_class(java_path, package_name, mod_id, main_class_name, blocks)

    # Generate ModItemGroups class
    item_groups_class_path = _generate_mod_item_groups_class(java_path, package_name, mod_id, main_class_name, items, blocks)

    return {
        "status": "success",
        "main_class_path": str(main_class_path),
        "client_class_path": str(client_class_path),
        "items_class_path": str(items_class_path),
        "blocks_class_path": str(blocks_class_path),
        "item_groups_class_path": str(item_groups_class_path)
    }


def _generate_mod_items_class(
    java_path: Path,
    package_name: str,
    mod_id: str,
    main_class_name: str,
    items: List[Dict[str, Any]]
) -> Path:
    """Generate ModItems.java with item registrations"""

    # Build item registrations
    item_declarations = []
    item_registrations = []

    for item in items:
        item_id = item.get("item_id", "").split(":")[-1]  # Extract path from namespace:path
        registration_id = item.get("registration_id", item_id.upper())
        rarity = item.get("rarity", "COMMON")
        fireproof = item.get("fireproof", False)
        max_stack = item.get("max_stack_size", 64)

        item_declarations.append(f'\tpublic static Item {registration_id};')

        settings = f"new Item.Settings().registryKey(RegistryKey.of(RegistryKeys.ITEM, Identifier.of({main_class_name}.MOD_ID, \"{item_id}\"))).maxCount({max_stack})"
        if fireproof:
            settings += ".fireproof()"

        item_registrations.append(
            f'\t\t{registration_id} = Registry.register(Registries.ITEM, '
            f'Identifier.of({main_class_name}.MOD_ID, "{item_id}"), '
            f'new Item({settings}));'
        )

    # Generate class
    items_class = dedent(f"""\
        package {package_name}.item;

        import net.minecraft.item.Item;
        import net.minecraft.registry.Registries;
        import net.minecraft.registry.Registry;
        import net.minecraft.registry.RegistryKey;
        import net.minecraft.registry.RegistryKeys;
        import net.minecraft.util.Identifier;
        import {package_name}.{main_class_name};

        public class ModItems {{
        {chr(10).join(item_declarations)}

        \tpublic static void registerModItems() {{
        {chr(10).join(item_registrations)}
        \t}}
        }}
        """)
    items_path = java_path / "item" / "ModItems.java"
    items_path.parent.mkdir(parents=True, exist_ok=True)
    items_path.write_text(items_class)
    return items_path


def _generate_mod_blocks_class(
    java_path: Path,
    package_name: str,
    mod_id: str,
    main_class_name: str,
    blocks: List[Dict[str, Any]]
) -> Path:
    """Generate ModBlocks.java with block registrations"""

    # Build block registrations
    block_declarations = []
    block_registrations = []
    block_item_registrations = []

    for block in blocks:
        block_id = block.get("block_id", "").split(":")[-1]
        registration_id = block.get("registration_id", block_id.upper())
        hardness = block.get("hardness", 3.0)
        resistance = block.get("resistance", 3.0)
        requires_tool = block.get("requires_tool", True)

        block_declarations.append(f'\tpublic static Block {registration_id};')

        settings = f"Block.Settings.create().registryKey(RegistryKey.of(RegistryKeys.BLOCK, Identifier.of({main_class_name}.MOD_ID, \"{block_id}\"))).strength({hardness}f, {resistance}f)"
        if requires_tool:
            settings += ".requiresTool()"

        block_registrations.append(
            f'\t\t{registration_id} = Registry.register(Registries.BLOCK, '
            f'Identifier.of({main_class_name}.MOD_ID, "{block_id}"), '
            f'new Block({settings}));'
        )

        block_item_registrations.append(
            f'\t\tRegistry.register(Registries.ITEM, Identifier.of({main_class_name}.MOD_ID, "{block_id}"), '
            f'new BlockItem({registration_id}, new Item.Settings().registryKey(RegistryKey.of(RegistryKeys.ITEM, Identifier.of({main_class_name}.MOD_ID, \"{block_id}\"))).useBlockPrefixedTranslationKey()));'
        )

    # Generate class
    blocks_class = dedent(f"""\
        package {package_name}.block;

        import net.minecraft.block.Block;
        import net.minecraft.item.BlockItem;
        import net.minecraft.item.Item;
        import net.minecraft.registry.Registries;
        import net.minecraft.registry.Registry;
        import net.minecraft.registry.RegistryKey;
        import net.minecraft.registry.RegistryKeys;
        import net.minecraft.util.Identifier;
        import {package_name}.{main_class_name};

        public class ModBlocks {{
        {chr(10).join(block_declarations)}

        \tpublic static void registerModBlocks() {{
        {chr(10).join(block_registrations)}

        \t\t// Register block items
        {chr(10).join(block_item_registrations)}
        \t}}
        }}
        """)
    blocks_path = java_path / "block" / "ModBlocks.java"
    blocks_path.parent.mkdir(parents=True, exist_ok=True)
    blocks_path.write_text(blocks_class)
    return blocks_path


def _generate_mod_item_groups_class(
    java_path: Path,
    package_name: str,
    mod_id: str,
    main_class_name: str,
    items: List[Dict[str, Any]],
    blocks: List[Dict[str, Any]]
) -> Path:
    """Generate ModItemGroups.java with item group registrations"""
    group_id = f"{mod_id}_group"
    group_const = f"{mod_id.upper()}_GROUP"

    entries = []
    for item in items:
        registration_id = item.get("registration_id", "")
        if registration_id:
            entries.append(f"\t\t\t\tentries.add(ModItems.{registration_id});")
    for block in blocks:
        registration_id = block.get("registration_id", "")
        if registration_id:
            entries.append(f"\t\t\t\tentries.add(ModBlocks.{registration_id});")

    if items:
        icon_item = f"ModItems.{items[0].get('registration_id', '')}"
    elif blocks:
        icon_item = f"ModBlocks.{blocks[0].get('registration_id', '')}"
    else:
        icon_item = "Items.STONE"

    entries_block = "\n".join(entries) if entries else "\t\t\t\t// No items or blocks to add"

    item_groups_class = dedent(f"""\
        package {package_name}.item;

        import net.minecraft.item.ItemGroup;
        import net.minecraft.item.ItemStack;
        import net.minecraft.item.Items;
        import net.minecraft.registry.Registries;
        import net.minecraft.registry.Registry;
        import net.minecraft.registry.RegistryKey;
        import net.minecraft.registry.RegistryKeys;
        import net.minecraft.text.Text;
        import net.minecraft.util.Identifier;
        import {package_name}.{main_class_name};
        import {package_name}.block.ModBlocks;

        public class ModItemGroups {{
        \tprivate static RegistryKey<ItemGroup> register(String id) {{
        \t\treturn RegistryKey.of(RegistryKeys.ITEM_GROUP, Identifier.of({main_class_name}.MOD_ID, id));
        \t}}
        \tpublic static void registerModItemGroups() {{
        \t\tRegistry.register(Registries.ITEM_GROUP, {group_const},
        \t\t\t\tItemGroup.create(ItemGroup.Row.TOP, 7)
        \t\t\t\t\t.displayName(Text.translatable("itemGroup.{group_id}"))
        \t\t\t\t\t.icon(() -> new ItemStack({icon_item}))
        \t\t\t\t\t.entries((displayContext, entries) -> {{
        {entries_block}
        \t\t\t\t\t}}).build());
        \t\t{main_class_name}.LOGGER.info("Registering Mod Item Groups");
        \t}}
        \tpublic static final RegistryKey<ItemGroup> {group_const} = register("{group_id}");
        }}
        """)
    item_groups_path = java_path / "item" / "ModItemGroups.java"
    item_groups_path.parent.mkdir(parents=True, exist_ok=True)
    item_groups_path.write_text(item_groups_class)
    return item_groups_path


def _to_class_name(mod_id: str) -> str:
    """Convert mod-id to ModId class name"""
    return ''.join(word.capitalize() for word in mod_id.replace('_', '-').split('-'))


__all__ = ["generate_java_code"]
