"""
Schemas for the Minecraft Mod Generation Pipeline

These schemas define the contracts between pipeline stages:
- Spec: User intent (human-friendly)
- IR: Intermediate Representation (machine-ready)
- Task: Execution plan (task DAG)
"""
from .spec_schema import (
    ModSpec,
    SpecDelta,
    ItemSpec,
    ItemType,
    BlockSpec,
    ToolSpec,
    Rarity,
    CreativeTab,
    normalize_creative_tab,
    Material,
    SoundGroup,
)
from .ir_schema import ModIR, IRItem, IRBlock, IRTool, IRAsset, IRRecipe
from .task_schema import Task, TaskDAG, TaskStatus, ToolCall

__all__ = [
    # Spec (User Intent)
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
    # IR (Intermediate Representation)
    "ModIR",
    "IRItem",
    "IRBlock",
    "IRTool",
    "IRAsset",
    "IRRecipe",
    # Task (Execution Plan)
    "Task",
    "TaskDAG",
    "TaskStatus",
    "ToolCall",
]
