"""
Compiler - Spec → IR Transformation

Responsibilities:
- Convert incomplete ModSpec into complete ModIR
- Fill in all optional fields with defaults
- Generate registry IDs from display names
- Resolve version constraints
- Create asset manifests
- Validate everything
- Fail loudly on invalid specs

This is the KEY component that ensures downstream generators
never need to interpret or guess anything.

Rule: If a generator must "figure something out," the IR is incomplete.
"""
import re
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from config import (
    MINECRAFT_VERSION,
    FABRIC_LOADER_VERSION,
    FABRIC_API_VERSION,
    YARN_MAPPINGS,
    JAVA_VERSION,
    RESOURCE_PACK_FORMAT
)
from agents.schemas import (
    ModSpec, ModIR,
    ItemSpec, ItemType, IRItem, IRAsset,
    BlockSpec, IRBlock,
    ToolSpec, IRTool,
    IRRecipe
)


class CompilationError(Exception):
    """Raised when spec cannot be compiled to IR"""
    pass


class Compiler:
    """
    Compiler - Transforms Spec into complete IR

    This component does ALL the "smart" work to create a complete blueprint.
    """

    def __init__(self):
        pass

    def compile(self, spec: ModSpec, spec_version: str = "1") -> ModIR:
        """
        Compile ModSpec into complete ModIR

        Args:
            spec: Mod specification (can be incomplete)
            spec_version: Spec version for provenance

        Returns:
            Complete, deterministic ModIR

        Raises:
            CompilationError: If spec is invalid or incomplete in unresolvable ways
        """
        # Generate mod_id if not provided
        mod_id = spec.mod_id or self._generate_mod_id(spec.mod_name)

        # Generate base package
        base_package = self._generate_base_package(mod_id)

        # Compile all items
        ir_items = [self._compile_item(item, mod_id, base_package) for item in spec.items]

        # Compile all blocks
        ir_blocks = [self._compile_block(block, mod_id, base_package) for block in spec.blocks]

        # Compile all tools
        ir_tools = [self._compile_tool(tool, mod_id, base_package) for tool in spec.tools]

        # Generate recipes for tools
        ir_recipes = []
        for tool in ir_tools:
            recipe = self._generate_tool_recipe(tool, mod_id)
            ir_recipes.append(recipe)

        # Collect all assets
        assets = []
        for item in ir_items:
            assets.extend([item.texture_asset, item.model_asset, item.lang_asset])
        for block in ir_blocks:
            assets.extend([
                block.texture_asset,
                block.blockstate_asset,
                block.model_asset,
                block.item_model_asset,
                block.loot_table_asset,
                block.lang_asset
            ])
        for tool in ir_tools:
            assets.extend([tool.texture_asset, tool.model_asset, tool.lang_asset, tool.recipe_asset])

        # Create complete IR
        ir = ModIR(
            mod_id=mod_id,
            mod_name=spec.mod_name,
            version=spec.version or "1.0.0",
            author=spec.author or "Unknown",
            description=spec.description or f"A mod that adds {spec.mod_name}",

            # Minecraft environment (all required)
            minecraft_version=spec.minecraft_version or MINECRAFT_VERSION,
            fabric_loader_version=spec.fabric_loader_version or FABRIC_LOADER_VERSION,
            fabric_api_version=spec.fabric_api_version or FABRIC_API_VERSION,
            yarn_mappings=YARN_MAPPINGS,
            java_version=JAVA_VERSION,
            resource_pack_format=RESOURCE_PACK_FORMAT,

            # Java structure
            base_package=base_package,
            main_class_name=self._generate_main_class_name(spec.mod_name),

            # Content
            items=ir_items,
            blocks=ir_blocks,
            tools=ir_tools,
            recipes=ir_recipes,
            assets=assets,

            # Gradle config
            gradle_properties=self._generate_gradle_properties(spec, mod_id),
            build_gradle_dependencies=[],

            # Provenance
            compiled_from_spec_version=spec_version,
            compilation_timestamp=datetime.utcnow().isoformat()
        )

        # Validate IR
        self._validate_ir(ir)

        return ir

    def _compile_item(self, item: ItemSpec, mod_id: str, base_package: str) -> IRItem:
        """Compile ItemSpec into complete IRItem"""
        # Generate item_id if not provided
        item_id = item.item_id or self._generate_registry_id(item.item_name)
        full_item_id = f"{mod_id}:{item_id}"

        # Generate Java names
        java_class_name = self._to_pascal_case(item_id) + "Item"
        registration_id = self._to_screaming_snake_case(item_id)

        item_type = self._infer_item_type(item)

        use_method = item.use
        use_on_block_method = item.useOnBlock
        use_on_entity_method = item.useOnEntity
        if item_type == ItemType.ITEM_NEWCLASS and not any(
            self._has_method_body(m) for m in [use_method, use_on_block_method, use_on_entity_method]
        ):
            use_method = self._default_use_stub()

        # Create texture asset
        texture_asset = IRAsset(
            asset_type="texture",
            file_path=f"assets/{mod_id}/textures/item/{item_id}.png",
            texture_generation_prompt=self._create_texture_prompt(item.item_name, item.description, item.texture_description),
            texture_reference_ids=item.texture_references or []
        )

        # Create model asset
        model_asset = IRAsset(
            asset_type="model",
            file_path=f"assets/{mod_id}/models/item/{item_id}.json",
            json_content={
                "parent": "item/generated",
                "textures": {
                    "layer0": f"{mod_id}:item/{item_id}"
                }
            }
        )

        # Create lang asset
        lang_asset = IRAsset(
            asset_type="lang",
            file_path=f"assets/{mod_id}/lang/en_us.json",
            lang_entries={
                f"item.{mod_id}.{item_id}": item.item_name,
                f"item.{mod_id}.{item_id}.tooltip": item.description
            }
        )

        return IRItem(
            item_id=full_item_id,
            display_name=item.item_name,
            description=item.description,
            type=item_type.value,
            maxCount=item.max_stack_size or 64,
            max_stack_size=item.max_stack_size or 64,
            rarity=item.rarity.value if item.rarity else "COMMON",
            fireproof=item.fireproof or False,
            isFood=bool(item.isFood),
            nutrition=item.nutrition,
            saturationModifier=item.saturationModifier,
            isSword=bool(item.isSword),
            swordAttackDamage=item.swordAttackDamage,
            swordAttackSpeed=item.swordAttackSpeed,
            isPickaxe=bool(item.isPickaxe),
            pickaxeAttackDamage=item.pickaxeAttackDamage,
            pickaxeAttackSpeed=item.pickaxeAttackSpeed,
            use=use_method or "",
            useOnBlock=use_on_block_method or "",
            useOnEntity=use_on_entity_method or "",
            creative_tab=item.creative_tab.value if item.creative_tab else "MISC",
            special_ability=item.special_ability or "",
            texture_asset=texture_asset,
            model_asset=model_asset,
            lang_asset=lang_asset,
            java_class_name=java_class_name,
            java_package=f"{base_package}.items",
            registration_id=registration_id
        )

    def _compile_block(self, block: BlockSpec, mod_id: str, base_package: str) -> IRBlock:
        """Compile BlockSpec into complete IRBlock"""
        block_id = block.block_id or self._generate_registry_id(block.block_name)
        full_block_id = f"{mod_id}:{block_id}"

        java_class_name = self._to_pascal_case(block_id) + "Block"
        registration_id = self._to_screaming_snake_case(block_id)

        # Determine drop item
        drop_item_id = block.drop_item_id or full_block_id

        # Create assets
        texture_asset = IRAsset(
            asset_type="texture",
            file_path=f"assets/{mod_id}/textures/block/{block_id}.png",
            texture_generation_prompt=self._create_texture_prompt(block.block_name, block.description, block.texture_description),
            texture_reference_ids=block.texture_references or []
        )

        blockstate_asset = IRAsset(
            asset_type="blockstate",
            file_path=f"assets/{mod_id}/blockstates/{block_id}.json",
            json_content={
                "variants": {
                    "": {"model": f"{mod_id}:block/{block_id}"}
                }
            }
        )

        model_asset = IRAsset(
            asset_type="model",
            file_path=f"assets/{mod_id}/models/block/{block_id}.json",
            json_content={
                "parent": "block/cube_all",
                "textures": {
                    "all": f"{mod_id}:block/{block_id}"
                }
            }
        )

        item_model_asset = IRAsset(
            asset_type="model",
            file_path=f"assets/{mod_id}/models/item/{block_id}.json",
            json_content={
                "parent": f"{mod_id}:block/{block_id}"
            }
        )

        loot_table_asset = IRAsset(
            asset_type="loot_table",
            file_path=f"data/{mod_id}/loot_tables/blocks/{block_id}.json",
            json_content={
                "type": "minecraft:block",
                "pools": [{
                    "rolls": 1,
                    "entries": [{
                        "type": "minecraft:item",
                        "name": drop_item_id
                    }],
                    "conditions": [{
                        "condition": "minecraft:survives_explosion"
                    }]
                }]
            }
        )

        lang_asset = IRAsset(
            asset_type="lang",
            file_path=f"assets/{mod_id}/lang/en_us.json",
            lang_entries={
                f"block.{mod_id}.{block_id}": block.block_name
            }
        )

        return IRBlock(
            block_id=full_block_id,
            display_name=block.block_name,
            description=block.description,
            material=block.material.value if block.material else "STONE",
            hardness=block.hardness or 3.0,
            resistance=block.resistance or 3.0,
            luminance=block.luminance or 0,
            requires_tool=block.requires_tool if block.requires_tool is not None else True,
            creative_tab=block.creative_tab.value if block.creative_tab else "BUILDING_BLOCKS",
            sound_group=block.sound_group.value if block.sound_group else "STONE",
            drop_item_id=drop_item_id,
            drop_count_min=block.drop_count_min or 1,
            drop_count_max=block.drop_count_max or 1,
            texture_asset=texture_asset,
            blockstate_asset=blockstate_asset,
            model_asset=model_asset,
            item_model_asset=item_model_asset,
            loot_table_asset=loot_table_asset,
            lang_asset=lang_asset,
            java_class_name=java_class_name,
            java_package=f"{base_package}.blocks",
            registration_id=registration_id
        )

    def _compile_tool(self, tool: ToolSpec, mod_id: str, base_package: str) -> IRTool:
        """Compile ToolSpec into complete IRTool"""
        tool_id = tool.tool_id or self._generate_registry_id(tool.tool_name)
        full_tool_id = f"{mod_id}:{tool_id}"

        java_class_name = self._to_pascal_case(tool_id) + "Item"
        registration_id = self._to_screaming_snake_case(tool_id)

        # Get tier defaults
        tier_defaults = self._get_tool_tier_defaults(tool.material_tier or "IRON")

        # Create assets
        texture_asset = IRAsset(
            asset_type="texture",
            file_path=f"assets/{mod_id}/textures/item/{tool_id}.png",
            texture_generation_prompt=self._create_texture_prompt(tool.tool_name, tool.description, tool.texture_description),
            texture_reference_ids=tool.texture_references or []
        )

        model_asset = IRAsset(
            asset_type="model",
            file_path=f"assets/{mod_id}/models/item/{tool_id}.json",
            json_content={
                "parent": "item/handheld",
                "textures": {
                    "layer0": f"{mod_id}:item/{tool_id}"
                }
            }
        )

        lang_asset = IRAsset(
            asset_type="lang",
            file_path=f"assets/{mod_id}/lang/en_us.json",
            lang_entries={
                f"item.{mod_id}.{tool_id}": tool.tool_name
            }
        )

        recipe_asset = IRAsset(
            asset_type="recipe",
            file_path=f"data/{mod_id}/recipes/{tool_id}.json",
            json_content={}  # Will be filled by _generate_tool_recipe
        )

        return IRTool(
            tool_id=full_tool_id,
            display_name=tool.tool_name,
            description=tool.description,
            tool_type=tool.tool_type,
            material_tier=tool.material_tier or "IRON",
            durability=tool.durability or tier_defaults["durability"],
            mining_speed=tool.mining_speed or tier_defaults["mining_speed"],
            attack_damage=tool.attack_damage or tier_defaults["attack_damage"],
            rarity=tool.rarity.value if tool.rarity else "COMMON",
            fireproof=tool.fireproof or False,
            creative_tab=tool.creative_tab.value if tool.creative_tab else "TOOLS",
            recipe_asset=recipe_asset,
            texture_asset=texture_asset,
            model_asset=model_asset,
            lang_asset=lang_asset,
            java_class_name=java_class_name,
            java_package=f"{base_package}.items",
            registration_id=registration_id
        )

    def _generate_tool_recipe(self, tool: IRTool, mod_id: str) -> IRRecipe:
        """Generate crafting recipe for a tool"""
        tool_type = tool.tool_type.upper()

        # Default patterns
        patterns = {
            "PICKAXE": (["###", " S ", " S "], {"#": "material", "S": "minecraft:stick"}),
            "AXE": (["##", "#S", " S"], {"#": "material", "S": "minecraft:stick"}),
            "SWORD": (["#", "#", "S"], {"#": "material", "S": "minecraft:stick"}),
            "SHOVEL": (["#", "S", "S"], {"#": "material", "S": "minecraft:stick"}),
            "HOE": (["##", " S", " S"], {"#": "material", "S": "minecraft:stick"})
        }

        pattern, keys = patterns.get(tool_type, patterns["PICKAXE"])

        # TODO: Get crafting ingredient from tool spec
        # For now, use placeholder
        keys["#"] = "minecraft:iron_ingot"

        recipe_id = tool.tool_id.split(":")[1]

        return IRRecipe(
            recipe_id=f"{mod_id}:{recipe_id}_recipe",
            recipe_type="crafting_shaped",
            result_item_id=tool.tool_id,
            result_count=1,
            pattern=pattern,
            keys=keys
        )

    # === Helper Methods ===

    def _infer_item_type(self, item: ItemSpec) -> ItemType:
        """Decide item implementation type based on flags, methods, and name."""
        name_tokens = self._tokenize_name(item.item_name)
        has_methods = any(self._has_method_body(m) for m in [item.use, item.useOnBlock, item.useOnEntity])
        has_special = bool(item.special_ability)

        is_food = bool(item.isFood)
        is_sword = bool(item.isSword) or ("sword" in name_tokens)
        is_pickaxe = bool(item.isPickaxe) or ("pickaxe" in name_tokens)
        is_axe = "axe" in name_tokens and "pickaxe" not in name_tokens
        is_hoe = "hoe" in name_tokens
        is_shovel = "shovel" in name_tokens or "spade" in name_tokens
        has_functionality = has_methods or is_food or is_sword or is_pickaxe or has_special

        if item.type == ItemType.ITEM_SUBCLASS:
            return ItemType.ITEM_SUBCLASS
        if has_methods:
            return ItemType.ITEM_NEWCLASS
        if is_pickaxe or is_sword or is_food:
            return ItemType.ITEM_MAINCLASS
        if not has_functionality and not (is_axe or is_hoe or is_shovel):
            return ItemType.ITEM_MAINCLASS
        if is_axe or is_hoe or is_shovel:
            return ItemType.ITEM_NEWCLASS
        return ItemType.ITEM_NEWCLASS

    @staticmethod
    def _tokenize_name(name: str) -> List[str]:
        return [tok for tok in re.split(r"[^a-z0-9]+", name.lower()) if tok]

    @staticmethod
    def _has_method_body(val: Any) -> bool:
        return isinstance(val, str) and val.strip() != ""

    @staticmethod
    def _default_use_stub() -> str:
        return (
            "@Override\n"
            "public ActionResult use(World world, PlayerEntity player, Hand hand){\n"
            "    if (!world.isClient()) {\n"
            "        // TODO: implement custom behavior\n"
            "        return ActionResult.SUCCESS;\n"
            "    }\n"
            "    return super.use(world, player, hand);\n"
            "}\n"
        )

    def _generate_mod_id(self, mod_name: str) -> str:
        """Generate mod_id from mod_name"""
        # Convert to lowercase, replace spaces with underscores, remove special chars
        mod_id = mod_name.lower()
        mod_id = re.sub(r'[^a-z0-9_]', '_', mod_id)
        mod_id = re.sub(r'_+', '_', mod_id).strip('_')
        return mod_id

    def _generate_registry_id(self, name: str) -> str:
        """Generate registry ID from display name"""
        return self._generate_mod_id(name)

    def _generate_base_package(self, mod_id: str) -> str:
        """Generate base Java package"""
        return f"com.example.{mod_id}"

    def _generate_main_class_name(self, mod_name: str) -> str:
        """Generate main class name"""
        return self._to_pascal_case(mod_name) + "Mod"

    def _to_pascal_case(self, s: str) -> str:
        """Convert string to PascalCase"""
        words = re.split(r'[_\s]+', s)
        return ''.join(word.capitalize() for word in words)

    def _to_screaming_snake_case(self, s: str) -> str:
        """Convert string to SCREAMING_SNAKE_CASE"""
        return s.upper().replace(' ', '_')

    def _create_texture_prompt(self, name: str, description: str, hint: str = None) -> str:
        """Create prompt for texture generation"""
        base = f"{name}: {description}"
        if hint:
            base += f". Visual style: {hint}"
        return base

    def _get_tool_tier_defaults(self, tier: str) -> Dict[str, float]:
        """Get default values for tool tier"""
        tiers = {
            "WOOD": {"durability": 59, "mining_speed": 2.0, "attack_damage": 2.0},
            "STONE": {"durability": 131, "mining_speed": 4.0, "attack_damage": 3.0},
            "IRON": {"durability": 250, "mining_speed": 6.0, "attack_damage": 4.0},
            "GOLD": {"durability": 32, "mining_speed": 12.0, "attack_damage": 2.0},
            "DIAMOND": {"durability": 1561, "mining_speed": 8.0, "attack_damage": 5.0},
            "NETHERITE": {"durability": 2031, "mining_speed": 9.0, "attack_damage": 6.0}
        }
        return tiers.get(tier, tiers["IRON"])

    def _generate_gradle_properties(self, spec: ModSpec, mod_id: str) -> Dict[str, str]:
        """Generate gradle.properties values"""
        return {
            "mod_id": mod_id,
            "mod_name": spec.mod_name,
            "mod_version": spec.version or "1.0.0",
            "maven_group": f"com.example.{mod_id}"
        }

    def _validate_ir(self, ir: ModIR):
        """Validate that IR is complete and valid"""
        # Check all required fields are present
        if not ir.mod_id:
            raise CompilationError("mod_id is required")
        if not ir.base_package:
            raise CompilationError("base_package is required")

        # Check registry ID uniqueness
        all_ids = set()
        for item in ir.items:
            if item.item_id in all_ids:
                raise CompilationError(f"Duplicate registry ID: {item.item_id}")
            all_ids.add(item.item_id)
            item_type = item.type or "ITEM_MAINCLASS"
            if item_type == "ITEM_NEWCLASS":
                if not any(self._has_method_body(m) for m in [item.use, item.useOnBlock, item.useOnEntity]):
                    raise CompilationError(f"ITEM_NEWCLASS item '{item.item_id}' is missing method bodies")
            if item.isFood:
                if item.nutrition is None or item.saturationModifier is None:
                    raise CompilationError(f"isFood set but nutrition/saturationModifier missing for '{item.item_id}'")
            if item.isSword:
                if item.swordAttackDamage is None or item.swordAttackSpeed is None:
                    raise CompilationError(f"isSword set but sword stats missing for '{item.item_id}'")
            if item.isPickaxe:
                if item.pickaxeAttackDamage is None or item.pickaxeAttackSpeed is None:
                    raise CompilationError(f"isPickaxe set but pickaxe stats missing for '{item.item_id}'")
            if item_type == "ITEM_SUBCLASS":
                print(f"⚠ Warning: ITEM_SUBCLASS used for '{item.item_id}' but subclass generation is not implemented")

        # All checks passed
        print(f"✓ IR validation passed: {len(ir.items)} items, {len(ir.blocks)} blocks, {len(ir.tools)} tools")


__all__ = ["Compiler", "CompilationError"]
