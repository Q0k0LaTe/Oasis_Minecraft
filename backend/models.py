"""
Pydantic schemas shared by the FastAPI endpoints.
"""
from typing import Dict, List, Optional, Literal

from pydantic import BaseModel, Field


class ItemPromptRequest(BaseModel):
    """Incoming payload from the frontend when requesting a new mod or batch."""

    prompt: Optional[str] = Field(
        default=None,
        min_length=3,
        description="User text describing the mod idea. Optional when providing a worklist.",
    )
    authorName: Optional[str] = Field(default=None, description="Optional author credit.")
    modName: Optional[str] = Field(
        default=None,
        description="Optional explicit mod name override supplied by the user.",
    )
    worklist: Optional[List['WorklistEntry']] = Field(
        default=None,
        description="Optional curated list of entries divided into items/tools/blocks.",
    )


class WorklistEntry(BaseModel):
    """Single row in the user-managed worklist."""

    id: Optional[str] = Field(
        default=None, description="Client-provided identifier for matching results."
    )
    kind: Literal["ITEM", "TOOL", "BLOCK"] = Field(
        ..., description="Category for this prompt."
    )
    prompt: str = Field(..., min_length=3, description="Description of what to build.")
    modName: Optional[str] = Field(
        default=None, description="Optional mod name override for this entry."
    )
    authorName: Optional[str] = Field(
        default=None, description="Optional author override for this entry."
    )


class ItemProperties(BaseModel):
    """Item tuning parameters returned by the AI analysis step."""

    maxStackSize: int = Field(..., ge=1, le=64)
    rarity: str = Field(..., description="COMMON | UNCOMMON | RARE | EPIC")
    fireproof: bool
    creativeTab: str = Field(..., description="Minecraft creative tab identifier.")
    specialAbility: str = Field(..., description="Short sentence describing the item ability.")


class InteractiveHints(BaseModel):
    """Optional conversational hints for the UI."""

    hooks: List[str] = Field(default_factory=list)
    clarifyingQuestion: Optional[str] = None
    followUpPrompt: Optional[str] = None


class BlockProperties(BaseModel):
    """Block configuration mirrored from the AI spec."""

    material: str
    hardness: float
    resistance: float
    luminance: int
    requiresTool: bool
    creativeTab: str
    soundGroup: str


class ToolProperties(BaseModel):
    """Stats that drive the generated pickaxe implementation."""

    attackDamage: float
    attackSpeed: float
    durability: int
    miningLevel: int
    miningSpeed: float
    enchantability: int


class LegendEntry(BaseModel):
    """Represents the meaning of a crafting symbol."""

    item: str
    label: Optional[str] = None


class RecipeResult(BaseModel):
    """Describes crafting output metadata."""

    item: str
    label: Optional[str] = None
    count: int = 1


class ToolRecipe(BaseModel):
    """Structured forging recipe information for UI + generators."""

    id: str
    type: str
    pattern: List[str]
    legend: Dict[str, LegendEntry]
    result: RecipeResult
    notes: Optional[str] = None
    alternates: List[List[str]] = Field(default_factory=list)


class BlockRecipe(ToolRecipe):
    """Alias for block recipes (same schema as tool recipes)."""


class BlockVariant(BaseModel):
    """Variant breakdown for a generated block."""

    name: str
    description: str
    traits: List[str] = Field(default_factory=list)
    recipe: BlockRecipe


class BlockDecision(BaseModel):
    """Full block description (when the AI decides to generate one)."""

    blockName: str
    blockId: str
    description: str
    dropItemId: str
    gameplayRole: str
    properties: BlockProperties
    variants: List[BlockVariant] = Field(default_factory=list)


class ToolDecision(BaseModel):
    """Optional AI-designed tool that complements the item/block."""

    toolName: str
    toolId: str
    description: str
    toolType: str
    material: str
    creativeTab: str = "TOOLS"
    properties: ToolProperties
    characteristics: List[str] = Field(default_factory=list)
    forgingRecipe: Optional[ToolRecipe] = None


class PackagingPlanModel(BaseModel):
    """High-level packaging/QA notes the AI wants to surface."""

    build_steps: List[str] = Field(default_factory=list, alias="build_steps")
    asset_plan: List[str] = Field(default_factory=list, alias="asset_plan")
    qa_notes: List[str] = Field(default_factory=list, alias="qa_notes")
    release_summary: str = Field(..., alias="release_summary")

    class Config:
        populate_by_name = True


class AIDecisions(BaseModel):
    """Top-level AI analysis summary returned to the client."""

    modName: str
    modId: str
    itemName: str
    itemId: str
    description: str
    author: str
    properties: ItemProperties
    interactive: Optional[InteractiveHints] = None
    block: Optional[BlockDecision] = None
    tool: Optional[ToolDecision] = None
    packagingPlan: Optional[PackagingPlanModel] = None


class GenerateModResponse(BaseModel):
    """Successful response for /api/generate-mod."""

    success: bool
    jobId: str
    aiDecisions: AIDecisions
    downloadUrl: Optional[str] = None
    textureBase64: Optional[str] = None
    blockTextureBase64: Optional[str] = None
    toolTextureBase64: Optional[str] = None
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standardized error envelope for failed requests."""

    success: bool = False
    error: str


# Rebuild models to resolve forward references
ItemPromptRequest.model_rebuild()
WorklistEntry.model_rebuild()


