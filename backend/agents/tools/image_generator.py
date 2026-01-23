"""
Image Generator - Unified facade for Minecraft texture generation

This module provides a clean API for generating both item/tool and block textures
by delegating to specialized generators:

- ItemImageGenerator: Handles items and tools (transparent backgrounds, sprites)
- BlockImageGenerator: Handles blocks (opaque, tileable surface textures)

ARCHITECTURE OVERVIEW:
======================
The image generation system is split into two completely separate pipelines:

1. ITEMS & TOOLS (ItemImageGenerator):
   - Transparent backgrounds (RGBA with alpha channel)
   - Centered sprites with padding
   - Edge flood-fill background removal
   - Anti-aliasing cleanup
   - Stored in: assets/items/ (or textures/item/ in mod structure)

2. BLOCKS (BlockImageGenerator - NEW ALGORITHM):
   - Fully opaque (RGB, no transparency)
   - Seamless tileable surface textures
   - Material-specific generation (stone, wood, metal, etc.)
   - Edge blending for better tiling
   - Stored in: assets/blocks/ (or textures/block/ in mod structure)

The two generators use DIFFERENT:
- Prompt structures
- Post-processing pipelines
- Color palettes
- Output formats

This separation ensures each texture type is optimized for its specific use case.
"""
from pathlib import Path
from typing import List, Dict, Any

from .item_image_generator import ItemImageGenerator
from .block_image_generator import BlockImageGenerator


class ImageGenerator:
    """
    Unified facade for Minecraft texture generation.

    This class delegates to specialized generators based on texture type:
    - Items and tools -> ItemImageGenerator
    - Blocks -> BlockImageGenerator

    Usage:
        generator = ImageGenerator()

        # Generate item textures
        item_textures = generator.generate_item_texture("A magical gem", "magic_gem", count=3)

        # Generate tool textures
        tool_textures = generator.generate_tool_texture(tool_spec, count=3)

        # Generate block textures (uses NEW algorithm)
        block_textures = generator.generate_block_texture_from_spec(block_spec, count=3)
    """

    def __init__(self):
        """Initialize both specialized generators."""
        print("Initializing ImageGenerator with specialized sub-generators...")
        self._item_generator = ItemImageGenerator()
        self._block_generator = BlockImageGenerator()
        print("ImageGenerator initialized successfully")

    # =========================================================================
    # ITEM GENERATION METHODS (delegates to ItemImageGenerator)
    # =========================================================================

    def generate_item_texture(
        self,
        item_description: str,
        item_name: str,
        count: int = None,
        save_path: Path = None
    ) -> List[bytes]:
        """
        Generate multiple pixel art texture variants for a Minecraft item.

        Uses the EXISTING proven algorithm for item sprites with:
        - Transparent background removal
        - Auto-crop and centering
        - Minecraft palette quantization

        Args:
            item_description: Description of the item
            item_name: Name of the item
            count: Number of variants to generate
            save_path: Optional directory to save variants

        Returns:
            List of PNG image data as bytes (16x16 RGBA with transparency)
        """
        return self._item_generator.generate_item_texture(
            item_description=item_description,
            item_name=item_name,
            count=count,
            save_path=save_path
        )

    def generate_texture_from_spec(self, spec: dict) -> bytes:
        """
        Generate a single item texture from mod specification.

        Args:
            spec: Mod specification dictionary

        Returns:
            PNG texture data as bytes
        """
        return self._item_generator.generate_texture_from_spec(spec)

    def generate_tool_texture(self, tool_spec: dict, count: int = None) -> List[bytes]:
        """
        Generate multiple texture variants for tools.

        Tools use the same algorithm as items (transparent background, sprite format).

        Args:
            tool_spec: Tool specification dictionary
            count: Number of variants

        Returns:
            List of PNG image data as bytes (16x16 RGBA)
        """
        return self._item_generator.generate_tool_texture(tool_spec, count)

    def generate_multiple_item_textures(
        self,
        item_description: str,
        item_name: str,
        count: int = 5
    ) -> List[bytes]:
        """
        Backward compatibility wrapper for V1 API.

        Args:
            item_description: Description of the item
            item_name: Name of the item
            count: Number of variants to generate

        Returns:
            List of PNG image data as bytes (16x16 pixels)
        """
        return self._item_generator.generate_item_texture(
            item_description=item_description,
            item_name=item_name,
            count=count
        )

    def generate_multiple_tool_textures(self, tool_spec: dict, count: int = 5) -> List[bytes]:
        """
        Generate multiple tool texture variants.

        Args:
            tool_spec: Tool specification dictionary
            count: Number of variants

        Returns:
            List of PNG image data as bytes
        """
        return self._item_generator.generate_tool_texture(tool_spec, count)

    # =========================================================================
    # BLOCK GENERATION METHODS (delegates to BlockImageGenerator - NEW ALGORITHM)
    # =========================================================================

    def generate_block_texture_from_spec(
        self,
        block_spec: dict,
        count: int = None,
        save_path: Path = None
    ) -> List[bytes]:
        """
        Generate multiple seamless block texture variants.

        *** USES NEW DEDICATED BLOCK ALGORITHM ***

        This method uses a completely different generation pipeline than items:
        - No transparency (fully opaque RGB)
        - Seamless tileable textures
        - Material-specific generation
        - Edge blending for better tiling

        Args:
            block_spec: Block specification dictionary containing:
                - blockName: Display name of the block
                - description: Description of the block
                - gameplayRole: How the block is used
                - properties: Dict with material, luminance, etc.
            count: Number of variants to generate
            save_path: Optional directory to save variants

        Returns:
            List of PNG image data as bytes (16x16 fully opaque RGB)
        """
        return self._block_generator.generate_block_texture(
            block_spec=block_spec,
            count=count,
            save_path=save_path
        )

    def generate_multiple_block_textures(self, block_spec: dict, count: int = 5) -> List[bytes]:
        """
        Generate multiple block texture variants.

        *** USES NEW DEDICATED BLOCK ALGORITHM ***

        Args:
            block_spec: Block specification dictionary
            count: Number of variants

        Returns:
            List of PNG image data as bytes (16x16 opaque)
        """
        return self._block_generator.generate_block_texture(block_spec, count)

    # =========================================================================
    # UTILITY PROPERTIES
    # =========================================================================

    @property
    def item_generator(self) -> ItemImageGenerator:
        """Direct access to item generator for advanced usage."""
        return self._item_generator

    @property
    def block_generator(self) -> BlockImageGenerator:
        """Direct access to block generator for advanced usage."""
        return self._block_generator
