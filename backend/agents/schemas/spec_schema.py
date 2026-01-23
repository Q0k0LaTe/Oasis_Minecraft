"""
Spec Schema - User Intent Format

This defines the human-friendly specification that captures user intent.
The Orchestrator produces this from conversations.
The Compiler transforms this into IR.

Key principle: Specs can be incomplete or ambiguous.
The Compiler's job is to fill in defaults and resolve ambiguity.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from enum import Enum


class Rarity(str, Enum):
    """Minecraft item rarity levels"""
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    EPIC = "EPIC"


class CreativeTab(str, Enum):
    """Minecraft creative inventory tabs"""
    BUILDING_BLOCKS = "BUILDING_BLOCKS"
    COLORED_BLOCKS = "COLORED_BLOCKS"
    NATURAL = "NATURAL"
    FUNCTIONAL = "FUNCTIONAL"
    REDSTONE = "REDSTONE"
    TOOLS = "TOOLS"
    COMBAT = "COMBAT"
    FOOD_AND_DRINK = "FOOD_AND_DRINK"
    INGREDIENTS = "INGREDIENTS"
    SPAWN_EGGS = "SPAWN_EGGS"
    MISC = "MISC"


class ItemType(str, Enum):
    """Item implementation strategy"""
    ITEM_MAINCLASS = "ITEM_MAINCLASS"
    ITEM_SUBCLASS = "ITEM_SUBCLASS"
    ITEM_NEWCLASS = "ITEM_NEWCLASS"


def normalize_creative_tab(value: Any, default: "CreativeTab" = None) -> "CreativeTab":
    """
    Safely convert arbitrary creative tab strings to a CreativeTab enum.

    Unknown or misspelled values fall back to the provided default (MISC if omitted).
    """
    default = default or CreativeTab.MISC
    if value is None:
        return default
    if isinstance(value, CreativeTab):
        return value

    normalized = str(value).strip().upper().replace(" ", "_").replace("-", "_")
    normalized = normalized.strip(" '\"")
    alias_map = {
        "MATERIALS": CreativeTab.INGREDIENTS.value,
        "MATERIAL": CreativeTab.INGREDIENTS.value,
        "INGREDIENT": CreativeTab.INGREDIENTS.value,
        "FOOD": CreativeTab.FOOD_AND_DRINK.value,
        "FOODS": CreativeTab.FOOD_AND_DRINK.value,
    }
    normalized = alias_map.get(normalized, normalized)

    try:
        return CreativeTab(normalized)
    except ValueError:
        return default


class Material(str, Enum):
    """Block material types"""
    STONE = "STONE"
    METAL = "METAL"
    WOOD = "WOOD"
    GLASS = "GLASS"
    PLANT = "PLANT"
    SAND = "SAND"
    DEEPSLATE = "DEEPSLATE"
    DIRT = "DIRT"
    ORGANIC = "ORGANIC"


class SoundGroup(str, Enum):
    """Block sound types"""
    WOOD = "WOOD"
    METAL = "METAL"
    GLASS = "GLASS"
    STONE = "STONE"
    GRASS = "GRASS"
    GRAVEL = "GRAVEL"
    SAND = "SAND"
    SNOW = "SNOW"
    WOOL = "WOOL"


class ItemSpec(BaseModel):
    """Specification for a custom item"""
    item_name: str = Field(..., description="Display name (e.g., 'Ruby Gem')")
    item_id: Optional[str] = Field(None, description="Registry ID (e.g., 'ruby_gem'). Compiler will generate if missing.")
    description: str = Field(..., description="Lore/purpose of the item")

    # Implementation strategy and custom behaviors
    type: ItemType = Field(ItemType.ITEM_MAINCLASS, description="ITEM_MAINCLASS, ITEM_SUBCLASS, or ITEM_NEWCLASS")
    use: Optional[str] = Field(None, description="Full method body for use(World, PlayerEntity, Hand)")
    useOnBlock: Optional[str] = Field(None, description="Full method body for useOnBlock(ItemUsageContext)")
    useOnEntity: Optional[str] = Field(None, description="Full method body for useOnEntity(ItemStack, PlayerEntity, LivingEntity, Hand)")

    # Properties (can be partial)
    max_stack_size: Optional[int] = Field(64, ge=1, le=64)
    rarity: Optional[Rarity] = Field(Rarity.COMMON)
    fireproof: Optional[bool] = Field(False)
    creative_tab: Optional[CreativeTab] = Field(CreativeTab.MISC)
    special_ability: Optional[str] = Field(None, description="What the item does when used")

    # Food and tool flags/stats
    isFood: bool = Field(False, description="True if the item acts as food")
    nutrition: Optional[int] = Field(None, ge=0, description="Hunger restored (half-shanks)")
    saturationModifier: Optional[float] = Field(None, ge=0.0, description="Saturation multiplier applied to nutrition")
    isSword: bool = Field(False, description="True if the item behaves as a sword")
    swordAttackDamage: Optional[float] = Field(None, description="Attack damage bonus for sword behavior")
    swordAttackSpeed: Optional[float] = Field(None, description="Attack speed modifier for sword behavior")
    isPickaxe: bool = Field(False, description="True if the item behaves as a pickaxe")
    pickaxeAttackDamage: Optional[float] = Field(None, description="Attack damage bonus for pickaxe behavior")
    pickaxeAttackSpeed: Optional[float] = Field(None, description="Attack speed modifier for pickaxe behavior")

    # Texture hints (optional - Compiler will use AI if missing)
    texture_description: Optional[str] = Field(None, description="How the texture should look")
    texture_references: Optional[List[str]] = Field(None, description="Vanilla items to reference")

    @field_validator("creative_tab", mode="before")
    @classmethod
    def _coerce_creative_tab(cls, v):
        return normalize_creative_tab(v)

    @model_validator(mode="after")
    def _validate_behavior_consistency(self):
        """Ensure behavior flags align with provided stats and method bodies."""
        # Food validation
        if self.isFood:
            if self.nutrition is None or self.saturationModifier is None:
                raise ValueError("isFood is True but nutrition/saturationModifier are missing")
        else:
            if self.nutrition is not None or self.saturationModifier is not None:
                raise ValueError("Food stats provided but isFood is False")

        # Sword validation
        if self.isSword:
            if self.swordAttackDamage is None or self.swordAttackSpeed is None:
                raise ValueError("isSword is True but swordAttackDamage/swordAttackSpeed are missing")
        else:
            if self.swordAttackDamage is not None or self.swordAttackSpeed is not None:
                raise ValueError("Sword stats provided but isSword is False")

        # Pickaxe validation
        if self.isPickaxe:
            if self.pickaxeAttackDamage is None or self.pickaxeAttackSpeed is None:
                raise ValueError("isPickaxe is True but pickaxeAttackDamage/pickaxeAttackSpeed are missing")
        else:
            if self.pickaxeAttackDamage is not None or self.pickaxeAttackSpeed is not None:
                raise ValueError("Pickaxe stats provided but isPickaxe is False")

        # Custom class validation
        if self.type == ItemType.ITEM_NEWCLASS:
            if not self._has_method_body(self.use) and not self._has_method_body(self.useOnBlock) and not self._has_method_body(self.useOnEntity):
                raise ValueError("ITEM_NEWCLASS requires at least one method body (use/useOnBlock/useOnEntity)")

        # Validate provided method bodies look complete
        for field_name, body in [
            ("use", self.use),
            ("useOnBlock", self.useOnBlock),
            ("useOnEntity", self.useOnEntity),
        ]:
            if self._has_method_body(body) and not self._looks_like_method(body):
                raise ValueError(f"{field_name} must be a complete method body (include signature and braces)")

        return self

    @staticmethod
    def _has_method_body(value: Optional[str]) -> bool:
        return value is not None and value.strip() != ""

    @staticmethod
    def _looks_like_method(value: str) -> bool:
        stripped = value.strip()
        return "(" in stripped and "{" in stripped and ("public" in stripped or "@Override" in stripped)


class BlockSpec(BaseModel):
    """Specification for a custom block"""
    block_name: str = Field(..., description="Display name (e.g., 'Ruby Ore')")
    block_id: Optional[str] = Field(None, description="Registry ID. Compiler generates if missing.")
    description: str = Field(..., description="What the block is/does")

    # Properties (can be partial)
    material: Optional[Material] = Field(Material.STONE)
    hardness: Optional[float] = Field(3.0, ge=0.1, le=100.0)
    resistance: Optional[float] = Field(3.0, ge=0.1, le=1200.0)
    luminance: Optional[int] = Field(0, ge=0, le=15, description="Light level 0-15")
    requires_tool: Optional[bool] = Field(True)
    creative_tab: Optional[CreativeTab] = Field(CreativeTab.BUILDING_BLOCKS)
    sound_group: Optional[SoundGroup] = Field(SoundGroup.STONE)

    # Drops (optional)
    drop_item_id: Optional[str] = Field(None, description="What item drops when broken")
    drop_count_min: Optional[int] = Field(1, ge=0)
    drop_count_max: Optional[int] = Field(1, ge=0)

    # Texture hints
    texture_description: Optional[str] = Field(None)
    texture_references: Optional[List[str]] = Field(None)

    @field_validator("creative_tab", mode="before")
    @classmethod
    def _coerce_creative_tab(cls, v):
        return normalize_creative_tab(v, CreativeTab.BUILDING_BLOCKS)


class ToolSpec(BaseModel):
    """Specification for a tool (pickaxe, axe, shovel, hoe, sword)"""
    tool_name: str = Field(..., description="Display name (e.g., 'Ruby Pickaxe')")
    tool_id: Optional[str] = Field(None)
    tool_type: str = Field(..., description="PICKAXE, AXE, SHOVEL, HOE, or SWORD")
    description: str = Field(..., description="What makes this tool special")

    # Tool properties
    material_tier: Optional[str] = Field("IRON", description="WOOD, STONE, IRON, GOLD, DIAMOND, NETHERITE, or custom")
    durability: Optional[int] = Field(None, description="Uses before breaking. Compiler sets default based on tier.")
    mining_speed: Optional[float] = Field(None, description="Mining speed multiplier")
    attack_damage: Optional[float] = Field(None, description="Damage dealt")

    # Crafting
    crafting_ingredient_id: Optional[str] = Field(None, description="Material used in recipe (e.g., 'ruby_gem')")

    # Other properties
    rarity: Optional[Rarity] = Field(Rarity.COMMON)
    fireproof: Optional[bool] = Field(False)
    creative_tab: Optional[CreativeTab] = Field(CreativeTab.TOOLS)

    # Texture hints
    texture_description: Optional[str] = Field(None)
    texture_references: Optional[List[str]] = Field(None)

    @field_validator("creative_tab", mode="before")
    @classmethod
    def _coerce_creative_tab(cls, v):
        return normalize_creative_tab(v, CreativeTab.TOOLS)


class ModSpec(BaseModel):
    """
    Complete Mod Specification - User Intent

    This is the canonical source of what the user wants.
    It can be incomplete or ambiguous - the Compiler resolves this.
    """
    # Metadata
    mod_name: str = Field(..., description="Human-friendly mod name")
    mod_id: Optional[str] = Field(None, description="Namespace ID. Compiler generates if missing.")
    version: Optional[str] = Field("1.0.0")
    author: Optional[str] = Field("Unknown")
    description: Optional[str] = Field("A custom Minecraft mod")

    # Minecraft environment
    minecraft_version: Optional[str] = Field(None, description="Target MC version. Uses config default if missing.")
    fabric_loader_version: Optional[str] = Field(None)
    fabric_api_version: Optional[str] = Field(None)

    # Content
    items: List[ItemSpec] = Field(default_factory=list)
    blocks: List[BlockSpec] = Field(default_factory=list)
    tools: List[ToolSpec] = Field(default_factory=list)

    # Free-form metadata
    extra: Dict[str, Any] = Field(default_factory=dict, description="Additional user-provided context")


class SpecDelta(BaseModel):
    """
    Incremental change to ModSpec

    Supports both structured JSON-path updates (operation/path/value) and
    higher-level create/update deltas used by SpecManager tests.
    """
    # Structured JSON patch style (used by Orchestrator)
    operation: Optional[str] = Field(None, description="add, update, remove")
    path: Optional[str] = Field(None, description="JSON path to modify (e.g., 'items[0].rarity')")
    value: Optional[Any] = Field(None, description="New value to set (for add/update)")
    reason: Optional[str] = Field(None, description="Why this change was made")

    # Semantic delta style (used by SpecManager tests/legacy flow)
    delta_type: Optional[str] = Field(None, description="create or update delta")
    mod_name: Optional[str] = None
    mod_id: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    minecraft_version: Optional[str] = None
    fabric_loader_version: Optional[str] = None
    fabric_api_version: Optional[str] = None
    items_to_add: List[ItemSpec] = Field(default_factory=list)
    blocks_to_add: List[BlockSpec] = Field(default_factory=list)
    tools_to_add: List[ToolSpec] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")

    def is_structured(self) -> bool:
        """Return True when using operation/path/value style deltas."""
        return self.operation is not None and self.path is not None


# Export for convenience
__all__ = [
    "ModSpec",
    "SpecDelta",
    "ItemSpec",
    "ItemType",
    "BlockSpec",
    "ToolSpec",
    "Rarity",
    "CreativeTab",
    "normalize_creative_tab",
    "Material",
    "SoundGroup",
]
