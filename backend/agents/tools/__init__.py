"""
Tools for Mod Generation

These tools are invoked by the Executor to perform specific tasks:
- Image generation (textures)
- Reference texture selection
- Code generation
- Asset generation
- Workspace setup
- etc.

All tools are deterministic: same inputs → same outputs.

IMAGE GENERATION ARCHITECTURE:
=============================
The image generation system uses specialized generators:
- ItemImageGenerator: Items and tools (transparent backgrounds, sprites)
- BlockImageGenerator: Blocks (opaque, seamless tileable textures)
- ImageGenerator: Unified facade that delegates to specialized generators

See ALGORITHM.md for detailed documentation of each algorithm.
"""
from .workspace_tool import setup_workspace
from .gradle_tool import generate_gradle_files
from .fabric_json_tool import generate_fabric_mod_json
from .java_code_tool import generate_java_code
from .asset_tool import generate_assets
from .mixins_tool import generate_mixins_json
from .gradle_wrapper_tool import setup_gradle_wrapper
from .build_tool import build_mod
from .image_generator import ImageGenerator
from .item_image_generator import ItemImageGenerator
from .block_image_generator import BlockImageGenerator
from .reference_selector import ReferenceSelector
from .tool_registry import ToolRegistry, create_tool_registry

__all__ = [
    "setup_workspace",
    "generate_gradle_files",
    "generate_fabric_mod_json",
    "generate_java_code",
    "generate_assets",
    "generate_mixins_json",
    "setup_gradle_wrapper",
    "build_mod",
    "ImageGenerator",
    "ItemImageGenerator",
    "BlockImageGenerator",
    "ReferenceSelector",
    "ToolRegistry",
    "create_tool_registry",
]
