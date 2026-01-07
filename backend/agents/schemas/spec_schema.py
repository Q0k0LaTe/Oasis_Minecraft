"""
Spec Schema - User Intent Format

This defines the human-friendly specification that captures user intent.
The Orchestrator produces this from conversations.
The Compiler transforms this into IR.

Key principle: Specs can be incomplete or ambiguous.
The Compiler's job is to fill in defaults and resolve ambiguity.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
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

    # Properties (can be partial)
    max_stack_size: Optional[int] = Field(64, ge=1, le=64)
    rarity: Optional[Rarity] = Field(Rarity.COMMON)
    fireproof: Optional[bool] = Field(False)
    creative_tab: Optional[CreativeTab] = Field(CreativeTab.MISC)
    special_ability: Optional[str] = Field(None, description="What the item does when used")

    # Texture hints (optional - Compiler will use AI if missing)
    texture_description: Optional[str] = Field(None, description="How the texture should look")
    texture_references: Optional[List[str]] = Field(None, description="Vanilla items to reference")

    @field_validator("creative_tab", mode="before")
    @classmethod
    def _coerce_creative_tab(cls, v):
        return normalize_creative_tab(v)


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
    "BlockSpec",
    "ToolSpec",
    "Rarity",
    "CreativeTab",
    "normalize_creative_tab",
    "Material",
    "SoundGroup",
]
