"""
Tool Registry - Central registry for all available tools

This module defines all tools available to the Executor.
Each tool is a callable function that receives parameters from the Task DAG.

Tool Design Principles:
1. Tools must be deterministic - same input always produces same output
2. Tools receive complete specifications - no ambiguity
3. Tools are dumb - no AI/reasoning, just mechanical execution
4. Tools report what they did - return file paths, status, etc.
"""
from typing import Dict, Callable, Any
from pathlib import Path

# Import all tool implementations
from .workspace_tool import setup_workspace
from .gradle_tool import generate_gradle_files
from .fabric_json_tool import generate_fabric_mod_json
from .java_code_tool import generate_java_code
from .asset_tool import generate_assets
from .mixins_tool import generate_mixins_json
from .gradle_wrapper_tool import setup_gradle_wrapper
from .build_tool import build_mod
from .image_generator import ImageGenerator


class ToolRegistry:
    """
    Central registry for all available tools

    The Planner uses this to understand what tools are available.
    The Executor uses this to invoke tools.
    """

    def __init__(self, workspace_dir: Path):
        """
        Initialize tool registry

        Args:
            workspace_dir: Base directory for mod generation
        """
        self.workspace_dir = Path(workspace_dir)
        self.image_generator = ImageGenerator()

        # Build registry
        self._registry: Dict[str, Callable] = {}
        self._register_tools()

    def _register_tools(self):
        """Register all available tools"""

        # Workspace setup
        self._registry["setup_workspace"] = self._wrap_tool(
            setup_workspace,
            description="Create mod directory structure",
            inputs=["workspace_dir", "mod_id", "package_name"],
            outputs=["workspace_path"]
        )

        # Build configuration
        self._registry["generate_gradle_files"] = self._wrap_tool(
            generate_gradle_files,
            description="Generate Gradle build files (build.gradle, settings.gradle, gradle.properties)",
            inputs=["workspace_path", "mod_id", "mod_name", "version", "minecraft_version", "dependencies"],
            outputs=["build_gradle_path", "settings_gradle_path", "gradle_properties_path"]
        )

        self._registry["generate_fabric_mod_json"] = self._wrap_tool(
            generate_fabric_mod_json,
            description="Generate fabric.mod.json metadata file",
            inputs=[
                "workspace_path",
                "mod_id",
                "mod_name",
                "version",
                "description",
                "authors",
                "license",
                "package_name",
                "main_class_name",
            ],
            outputs=["fabric_mod_json_path"]
        )

        # Code generation
        self._registry["generate_java_code"] = self._wrap_tool(
            generate_java_code,
            description="Generate Java source code for mod classes",
            inputs=["workspace_path", "package_name", "mod_id", "main_class_name", "items", "blocks", "tools"],
            outputs=["main_class_path", "items_class_path", "blocks_class_path"]
        )

        # Asset generation
        self._registry["generate_assets"] = self._wrap_tool(
            generate_assets,
            description="Generate all resource files (models, textures, recipes, lang files)",
            inputs=["workspace_path", "mod_id", "items", "blocks", "tools", "textures"],
            outputs=["assets_path", "data_path"]
        )

        # Texture generation (AI-powered)
        # Routes to ItemImageGenerator for items/tools, BlockImageGenerator for blocks
        self._registry["generate_texture"] = self._wrap_tool(
            self._generate_texture_wrapper,
            description="Generate pixel art texture using AI",
            inputs=["item_name", "description", "variant_count", "entity_type", "material", "luminance", "gameplay_role"],
            outputs=["texture_variants"]
        )

        # Configuration
        self._registry["generate_mixins_json"] = self._wrap_tool(
            generate_mixins_json,
            description="Generate mixins configuration file",
            inputs=["workspace_path", "mod_id", "package_name"],
            outputs=["mixins_json_path"]
        )

        self._registry["setup_gradle_wrapper"] = self._wrap_tool(
            setup_gradle_wrapper,
            description="Copy Gradle wrapper files to project",
            inputs=["workspace_path"],
            outputs=["gradle_wrapper_path"]
        )

        # Build
        self._registry["build_mod"] = self._wrap_tool(
            build_mod,
            description="Compile mod using Gradle and produce JAR file",
            inputs=["workspace_path", "mod_id"],
            outputs=["jar_path"]
        )

    def _wrap_tool(self, func: Callable, description: str, inputs: list, outputs: list) -> Callable:
        """
        Wrap tool function with metadata

        This allows us to query tool capabilities.
        """
        def wrapper(**kwargs):
            # Provide sensible workspace defaults
            if func.__name__ == "setup_workspace":
                kwargs.setdefault("workspace_dir", self.workspace_dir)
            else:
                kwargs.setdefault("workspace_path", self.workspace_dir)
            return func(**kwargs)

        # Attach metadata
        wrapper.__doc__ = description
        wrapper.__tool_inputs__ = inputs
        wrapper.__tool_outputs__ = outputs
        wrapper.__wrapped__ = func

        return wrapper

    def _generate_texture_wrapper(self, **kwargs):
        """
        Wrapper for image generator - routes to appropriate generator based on entity type.

        For items/tools: Uses ItemImageGenerator (transparent backgrounds, sprites)
        For blocks: Uses BlockImageGenerator (opaque, seamless tileable textures)
        """
        item_name = kwargs.get("item_name")
        description = kwargs.get("description")
        variant_count = kwargs.get("variant_count", 5)
        entity_type = kwargs.get("entity_type", "item")

        # Route to appropriate generator based on entity type
        if entity_type == "block":
            # Use NEW block generation algorithm for blocks
            block_spec = {
                "blockName": item_name,
                "description": description or item_name,
                "gameplayRole": kwargs.get("gameplay_role", ""),
                "properties": {
                    "material": kwargs.get("material", "STONE"),
                    "luminance": kwargs.get("luminance", 0)
                }
            }
            variants = self.image_generator.generate_block_texture_from_spec(
                block_spec=block_spec,
                count=variant_count
            )
        else:
            # Use existing item/tool generation algorithm
            variants = self.image_generator.generate_item_texture(
                item_name=item_name,
                item_description=description or item_name,
                count=variant_count
            )

        return {"texture_variants": variants}

    def get_tool(self, tool_name: str) -> Callable:
        """Get tool by name"""
        if tool_name not in self._registry:
            available = ", ".join(self._registry.keys())
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {available}")
        return self._registry[tool_name]

    def get_all_tools(self) -> Dict[str, Callable]:
        """Get all registered tools"""
        return self._registry.copy()

    def list_tools(self) -> list:
        """List all available tool names"""
        return list(self._registry.keys())

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get metadata about a tool"""
        tool = self.get_tool(tool_name)
        return {
            "name": tool_name,
            "description": tool.__doc__,
            "inputs": getattr(tool, "__tool_inputs__", []),
            "outputs": getattr(tool, "__tool_outputs__", [])
        }


def create_tool_registry(workspace_dir: Path) -> Dict[str, Callable]:
    """
    Factory function to create a tool registry

    This is the main entry point for the Executor.

    Args:
        workspace_dir: Base directory for mod generation

    Returns:
        Dictionary mapping tool names to callable functions
    """
    registry = ToolRegistry(workspace_dir)
    return registry.get_all_tools()


__all__ = ["ToolRegistry", "create_tool_registry"]
