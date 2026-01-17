"""
AI Agents for Minecraft Mod Generation

New Architecture (V2):
- pipeline: ModGenerationPipeline - Main pipeline orchestrator
- core: Core pipeline components (Orchestrator, Compiler, Planner, Executor, etc.)
- tools: Tool implementations (code generation, asset generation, image generation)
- schemas: Data schemas (Spec, IR, Task)

Legacy (V1 - for backward compatibility):
- mod_analyzer: ModAnalyzerAgent
- mod_generator: ModGenerator
- langchain_agents: LangChain-based agents
"""

# New Pipeline Architecture (V2)
from .pipeline import ModGenerationPipeline, generate_mod_from_prompt, PipelineError

# Core Components
from .core import (
    Orchestrator,
    SpecManager,
    Compiler,
    Planner,
    Executor,
    Validator,
    Builder,
    ErrorFixer,
)

# Tools
from .tools import (
    ToolRegistry,
    create_tool_registry,
    ImageGenerator,
    ReferenceSelector,
)

# Schemas
from .schemas import (
    ModSpec,
    SpecDelta,
    ItemSpec,
    BlockSpec,
    ToolSpec,
    ModIR,
    IRItem,
    IRBlock,
    IRTool,
    IRAsset,
    IRRecipe,
    Task,
    TaskDAG,
    TaskStatus,
    ToolCall,
)

# Legacy Components (V1 - backward compatibility)
from .langchain_agents import (
    LangChainModOrchestrator,
    InteractiveItemAgent,
    BlockCreationAgent,
    PackagingAgent,
)
from .mod_analyzer import ModAnalyzerAgent
from .mod_generator import ModGenerator

__all__ = [
    # V2 Pipeline
    "ModGenerationPipeline",
    "generate_mod_from_prompt",
    "PipelineError",
    # Core Components
    "Orchestrator",
    "SpecManager",
    "Compiler",
    "Planner",
    "Executor",
    "Validator",
    "Builder",
    "ErrorFixer",
    # Tools
    "ToolRegistry",
    "create_tool_registry",
    "ImageGenerator",
    "ReferenceSelector",
    # Schemas
    "ModSpec",
    "SpecDelta",
    "ItemSpec",
    "BlockSpec",
    "ToolSpec",
    "ModIR",
    "IRItem",
    "IRBlock",
    "IRTool",
    "IRAsset",
    "IRRecipe",
    "Task",
    "TaskDAG",
    "TaskStatus",
    "ToolCall",
    # Legacy (V1)
    "ModAnalyzerAgent",
    "ModGenerator",
    "LangChainModOrchestrator",
    "InteractiveItemAgent",
    "BlockCreationAgent",
    "PackagingAgent",
]
