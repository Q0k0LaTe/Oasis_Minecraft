"""
IR Schema - Intermediate Representation

This defines the COMPLETE, DETERMINISTIC blueprint for mod generation.

Key principles:
- NO optional fields (everything must be specified)
- NO ambiguity (generators can execute mechanically)
- NO English descriptions that require interpretation
- COMPLETE (all registry IDs, all file paths, all values)

If a generator needs to "figure something out," the IR is incomplete.
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class IRRecipe(BaseModel):
    """Fully specified crafting recipe"""
    recipe_id: str = Field(..., description="Unique ID (e.g., 'ruby_pickaxe_recipe')")
    recipe_type: str = Field(..., description="crafting_shaped, crafting_shapeless, smelting, etc.")
    result_item_id: str = Field(..., description="Fully qualified ID (e.g., 'modid:ruby_pickaxe')")
    result_count: int = Field(1, ge=1)

    # For shaped crafting
    pattern: Optional[List[str]] = Field(None, description="3x3 pattern, e.g., ['###', ' S ', ' S ']")
    keys: Optional[Dict[str, str]] = Field(None, description="Symbol → item mapping, e.g., {'#': 'modid:ruby_gem'}")

    # For shapeless crafting
    ingredients: Optional[List[str]] = Field(None, description="List of item IDs")

    # For smelting
    input_item_id: Optional[str] = Field(None)
    experience: Optional[float] = Field(None)
    cooking_time: Optional[int] = Field(None, description="Ticks (200 = 10 seconds)")


class IRAsset(BaseModel):
    """Fully specified asset file"""
    asset_type: str = Field(..., description="texture, model, lang, blockstate, recipe, loot_table")
    file_path: str = Field(..., description="Relative path in resources (e.g., 'assets/modid/textures/item/ruby.png')")

    # For textures
    texture_data: Optional[bytes] = Field(None, description="PNG bytes (base64 encoded when serialized)")
    texture_generation_prompt: Optional[str] = Field(None, description="If texture needs generation")
    texture_reference_ids: Optional[List[str]] = Field(None, description="Vanilla textures to reference")

    # For JSON files (models, blockstates, recipes, etc.)
    json_content: Optional[Dict] = Field(None, description="Exact JSON to write")

    # For lang files
    lang_entries: Optional[Dict[str, str]] = Field(None, description="Translation key → value")


class IRItem(BaseModel):
    """Fully specified item registration"""
    item_id: str = Field(..., description="Registry ID (namespace:path format)")
    display_name: str = Field(..., description="English name for lang file")
    description: str = Field(..., description="Tooltip/lore")
    
    type: Optional[str] = Field(None, description="ITEM_MAINCLASS, ITEM_SUBCLASS, ITEM_NEWCLASS")

    # for All:
    maxCount: Optional[int] = Field(None, ge=1, le=64)
    rarity: Optional[str] = Field(None, description="COMMON, UNCOMMON, RARE, EPIC")
    fireproof: Optional[bool] = Field(None, description="True if lava/fire safe")
    
    # for ITEM_MAINCLASS:

    # for ITEM_SUBCLASS:

    # for ITEM_NEWCLASS:
    use: Optional[str] = Field(None, description="Entire code for the method use")
    useOnBlock: Optional[str] = Field(None, description="Entire code for the method useOnBlock")
    useOnEntity: Optional[str] = Field(None, description="Entire code for the method useOnEntity")
    

    # Properties (all required, no optionals)
    max_stack_size: int = Field(..., ge=1, le=64)
    creative_tab: str = Field(..., description="Creative tab constant name")
    special_ability: str = Field("", description="Empty if no special ability")

    # Assets
    texture_asset: IRAsset = Field(..., description="Item texture asset")
    model_asset: IRAsset = Field(..., description="Item model JSON")
    lang_asset: IRAsset = Field(..., description="Language entries")

    # Java generation hints
    java_class_name: str = Field(..., description="Java class name (e.g., 'RubyGemItem')")
    java_package: str = Field(..., description="Package path (e.g., 'com.example.mod.items')")
    registration_id: str = Field(..., description="Identifier constant (e.g., 'RUBY_GEM')")


class IRBlock(BaseModel):
    """Fully specified block registration"""
    block_id: str = Field(..., description="Registry ID (namespace:path)")
    display_name: str = Field(..., description="English name")
    description: str = Field(...)

    # Properties (all required)
    material: str = Field(..., description="Material enum value")
    hardness: float = Field(..., ge=0.1)
    resistance: float = Field(..., ge=0.1)
    luminance: int = Field(..., ge=0, le=15)
    requires_tool: bool = Field(...)
    creative_tab: str = Field(...)
    sound_group: str = Field(...)

    # Drops
    drop_item_id: str = Field(..., description="Fully qualified item ID that drops")
    drop_count_min: int = Field(..., ge=0)
    drop_count_max: int = Field(..., ge=0)

    # Assets
    texture_asset: IRAsset = Field(..., description="Block texture")
    blockstate_asset: IRAsset = Field(..., description="Blockstate JSON")
    model_asset: IRAsset = Field(..., description="Block model JSON")
    item_model_asset: IRAsset = Field(..., description="Block item model JSON")
    loot_table_asset: IRAsset = Field(..., description="Loot table JSON")
    lang_asset: IRAsset = Field(...)

    # Java generation hints
    java_class_name: str = Field(...)
    java_package: str = Field(...)
    registration_id: str = Field(...)


class IRTool(BaseModel):
    """Fully specified tool registration"""
    tool_id: str = Field(..., description="Registry ID")
    display_name: str = Field(...)
    description: str = Field(...)
    tool_type: str = Field(..., description="PICKAXE, AXE, SHOVEL, HOE, SWORD")

    # Properties
    material_tier: str = Field(..., description="Material tier constant")
    durability: int = Field(..., ge=1)
    mining_speed: float = Field(..., ge=0.0)
    attack_damage: float = Field(..., ge=0.0)
    rarity: str = Field(...)
    fireproof: bool = Field(...)
    creative_tab: str = Field(...)

    # Recipe
    recipe_asset: IRAsset = Field(..., description="Crafting recipe JSON")

    # Assets
    texture_asset: IRAsset = Field(...)
    model_asset: IRAsset = Field(...)
    lang_asset: IRAsset = Field(...)

    # Java generation hints
    java_class_name: str = Field(...)
    java_package: str = Field(...)
    registration_id: str = Field(...)


class ModIR(BaseModel):
    """
    Complete Intermediate Representation

    This is the COMPLETE, DETERMINISTIC blueprint for generation.
    Every field is required. No ambiguity allowed.
    """
    # Metadata (all required)
    mod_id: str = Field(..., description="Namespace ID (lowercase, underscores only)")
    mod_name: str = Field(...)
    version: str = Field(...)
    author: str = Field(...)
    description: str = Field(...)

    # Minecraft environment (fully specified)
    minecraft_version: str = Field(...)
    fabric_loader_version: str = Field(...)
    fabric_api_version: str = Field(...)
    yarn_mappings: str = Field(...)
    java_version: str = Field(...)
    resource_pack_format: int = Field(...)

    # Java structure
    base_package: str = Field(..., description="Base Java package (e.g., 'com.example.mod')")
    main_class_name: str = Field(..., description="Main mod class (e.g., 'ExampleMod')")

    # Content (fully specified)
    items: List[IRItem] = Field(default_factory=list)
    blocks: List[IRBlock] = Field(default_factory=list)
    tools: List[IRTool] = Field(default_factory=list)
    recipes: List[IRRecipe] = Field(default_factory=list)

    # All assets collected
    assets: List[IRAsset] = Field(default_factory=list)

    # Gradle/build config
    gradle_properties: Dict[str, str] = Field(default_factory=dict)
    build_gradle_dependencies: List[str] = Field(default_factory=list)

    # Metadata for provenance
    compiled_from_spec_version: Optional[str] = Field(None)
    compilation_timestamp: Optional[str] = Field(None)


# Export
__all__ = [
    "ModIR",
    "IRItem",
    "IRBlock",
    "IRTool",
    "IRAsset",
    "IRRecipe",
]
