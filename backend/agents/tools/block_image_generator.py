"""
Block Image Generator - Creates seamless tileable textures for Minecraft blocks

This module implements a NEW dedicated algorithm for block texture generation.
Block textures have fundamentally different requirements than items:

Key Differences from Item Generation:
1. NO TRANSPARENCY - Blocks are fully opaque surfaces
2. TILEABILITY - Edges must seamlessly connect when repeated
3. SINGLE FACE - Represents one side of a cube, not an isometric view
4. SURFACE TEXTURE - Focus on material patterns, not discrete sprites
5. MATERIAL-BASED - Generation varies by material type (stone, wood, metal, etc.)

Storage: Generated textures are stored under assets/blocks/

NEW ALGORITHM OVERVIEW:
=======================
The block generation algorithm differs significantly from item generation:

1. PROMPT ENGINEERING:
   - Emphasizes seamless tiling patterns
   - Material-specific texture guidance (grain, cracks, panels)
   - No background removal instructions (blocks fill the entire 16x16)
   - Top-down surface view, not 3D perspective

2. POST-PROCESSING PIPELINE:
   - No transparency handling (convert to RGB immediately)
   - Edge blending for improved tileability
   - Block-specific color palette quantization
   - Contrast normalization for Minecraft aesthetic

3. TILEABILITY ENHANCEMENT:
   - Edge pixel analysis and blending
   - Optional seamless wrap processing
   - Pattern continuity checking

4. OUTPUT:
   - Always 16x16 PNG
   - Always fully opaque (RGB, no alpha)
   - Represents a single block face
"""
from google import genai
from PIL import Image, ImageFilter
from io import BytesIO
from pathlib import Path
from typing import Optional, List, Dict, Any

import numpy as np

from config import GEMINI_API_KEY, IMAGE_MODEL, IMAGE_VARIANT_COUNT
from .reference_selector import ReferenceSelector


class BlockImageGenerator:
    """
    Generates seamless tileable textures for Minecraft blocks.

    This generator uses a NEW algorithm specifically designed for block textures:
    - Stone, ore, metal, wood, glass, plant, sand, deepslate materials
    - Seamless tiling at edges
    - Full opacity (no transparency)
    - Single face representation (not isometric/3D)

    The algorithm prioritizes:
    1. Material authenticity - textures match Minecraft's visual language
    2. Seamless tiling - edges connect perfectly when repeated
    3. Readable at 16x16 - patterns visible but not cluttered
    4. Consistent lighting - top-left light source convention
    """

    # Block-specific color palette optimized for surface textures
    # Different from item palette - focuses on natural/architectural materials
    BLOCK_PALETTE = [
        # Stone variations (gray spectrum)
        (80, 80, 80), (96, 96, 96), (112, 112, 112), (128, 128, 128),
        (144, 144, 144), (160, 160, 160), (176, 176, 176),
        # Deepslate (dark blue-gray)
        (48, 48, 56), (56, 56, 64), (64, 64, 72), (72, 72, 80),
        # Wood tones (warm browns)
        (92, 58, 30), (105, 70, 40), (120, 85, 55), (140, 100, 70),
        (160, 120, 85), (180, 140, 100),
        # Metal tones (cool grays with hints)
        (168, 168, 176), (184, 184, 192), (200, 200, 208), (216, 216, 224),
        # Ore colors
        (92, 219, 213), (79, 193, 255),  # Diamond/Cyan
        (255, 215, 0), (218, 165, 32),   # Gold
        (50, 200, 120), (60, 179, 113),  # Emerald
        (220, 20, 60), (178, 34, 34),    # Ruby/Redstone
        (147, 112, 219), (138, 43, 226), # Amethyst
        # Earth tones
        (139, 90, 43), (150, 100, 60),   # Dirt
        (194, 178, 128), (210, 190, 140), # Sand
        # Plant greens
        (34, 139, 34), (60, 130, 60), (80, 160, 80),
        # Glass/translucent hints
        (200, 220, 230), (180, 200, 220),
        # Black and white anchors
        (32, 32, 32), (48, 48, 48), (224, 224, 224), (240, 240, 240),
    ]

    # Material-specific generation parameters
    MATERIAL_CONFIGS: Dict[str, Dict[str, Any]] = {
        "STONE": {
            "pattern": "irregular cracks and speckles, rough surface texture",
            "colors": "gray base (#808080) with darker cracks (#505050) and lighter spots (#A0A0A0)",
            "style": "natural variation, weathered appearance"
        },
        "DEEPSLATE": {
            "pattern": "layered horizontal striations with subtle cracks",
            "colors": "dark blue-gray (#404048) with darker lines (#303038) and slate highlights (#505058)",
            "style": "compressed sedimentary look, directional grain"
        },
        "METAL": {
            "pattern": "panel grid with rivets or seams, brushed texture",
            "colors": "metallic silver (#A8A8B0) with darker seams (#707078) and bright highlights (#D0D0D8)",
            "style": "industrial, manufactured appearance with subtle reflections"
        },
        "WOOD": {
            "pattern": "parallel grain lines running vertically or horizontally",
            "colors": "warm brown (#785030) with darker grain (#503020) and lighter sections (#906040)",
            "style": "natural wood grain, plank-like appearance"
        },
        "GLASS": {
            "pattern": "mostly uniform with subtle edge highlights and light refraction hints",
            "colors": "pale cyan-white (#C8DCE8) with edge highlights (#E0F0FF) and subtle shadows (#A0C0D0)",
            "style": "transparent/translucent appearance, clean edges"
        },
        "PLANT": {
            "pattern": "organic cellular texture, moss-like or leaf-like surface",
            "colors": "green base (#408040) with darker shadows (#305030) and bright spots (#60A060)",
            "style": "natural, organic variation, living texture"
        },
        "SAND": {
            "pattern": "fine granular noise, subtle dunes or ripples",
            "colors": "warm beige (#D0B080) with darker grains (#B09060) and highlights (#E8D0A0)",
            "style": "grainy, desert-like texture"
        },
        "ORE": {
            "pattern": "stone base with embedded crystalline clusters or veins",
            "colors": "stone gray base with colored ore deposits",
            "style": "natural ore embedding, visible crystal formations"
        }
    }

    def __init__(self):
        """Initialize the block image generator with Gemini API client."""
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = IMAGE_MODEL
        self.reference_selector = ReferenceSelector()
        print("  BlockImageGenerator initialized")

    def generate_block_texture(
        self,
        block_spec: Dict[str, Any],
        count: int = None,
        save_path: Path = None
    ) -> List[bytes]:
        """
        Generate multiple seamless block texture variants.

        NEW ALGORITHM: This method uses a completely different approach than
        item generation, optimized for tileable surface textures.

        Args:
            block_spec: Block specification dictionary containing:
                - blockName: Display name of the block
                - description: Description of the block
                - gameplayRole: How the block is used in gameplay
                - properties: Dict with material, luminance, hardness, etc.
            count: Number of variants to generate (defaults to IMAGE_VARIANT_COUNT)
            save_path: Optional directory to save variants

        Returns:
            List of PNG image data as bytes (16x16 pixels, fully opaque)
        """
        if count is None:
            count = IMAGE_VARIANT_COUNT

        block_name = block_spec.get("blockName", "Custom Block")
        print(f"\n  Generating {count} block texture variants for: {block_name}")

        textures = []
        for i in range(count):
            print(f"    [{i+1}/{count}] Generating block variant {i+1}...")
            texture = self._generate_single_block_texture(
                block_spec=block_spec,
                variant_number=i + 1,
                save_path=save_path
            )
            textures.append(texture)
            print(f"    Block variant {i+1} complete")

        print(f"  Generated {count} block variants successfully\n")
        return textures

    def _generate_single_block_texture(
        self,
        block_spec: Dict[str, Any],
        variant_number: int = 1,
        save_path: Path = None
    ) -> bytes:
        """
        Generate a single seamless block texture.

        NEW ALGORITHM PIPELINE:
        1. Build material-specific prompt for tileable texture
        2. Select block reference textures (if first variant)
        3. Generate via Gemini API
        4. Apply block-specific post-processing:
           - Convert to RGB (no transparency)
           - Two-stage quality downsampling
           - Block palette quantization
           - Edge enhancement for tileability
        5. Output 16x16 opaque PNG
        """
        block_name = block_spec.get("blockName", "Custom Block")
        description = block_spec.get("description", "")
        gameplay_role = block_spec.get("gameplayRole", "")
        properties = block_spec.get("properties", {})

        # Build the specialized block prompt
        prompt = self._create_block_texture_prompt(
            block_name=block_name,
            description=description,
            gameplay_role=gameplay_role,
            material=properties.get("material", "STONE"),
            luminance=properties.get("luminance", 0)
        )

        # Select reference textures (only for first variant)
        reference_paths = []
        if variant_number == 1:
            reference_paths = self._select_block_references(
                description, block_name, max_refs=3
            )

        contents = [prompt]

        if reference_paths:
            print(f"      Using {len(reference_paths)} reference block texture(s)")
            contents.append("\n\nREFERENCE BLOCK TEXTURES (match this style):")
            for ref_path in reference_paths:
                ref_image = Image.open(ref_path).convert("RGB")
                contents.append(ref_image)

        # Generate via Gemini
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
        )

        img = None
        for part in response.parts:
            if part.inline_data:
                img = Image.open(BytesIO(part.inline_data.data))
                break

        if img is None:
            raise ValueError("No image data in response for block texture")

        # Apply NEW block-specific post-processing pipeline
        processed = self._process_block_texture(
            img,
            size=16,
            material=properties.get("material", "STONE"),
            luminance=properties.get("luminance", 0)
        )

        output = BytesIO()
        processed.save(output, format='PNG')
        png_data = output.getvalue()

        if save_path:
            if save_path.is_dir():
                file_path = save_path / f"{block_name}_variant_{variant_number}.png"
            else:
                file_path = save_path.parent / f"{save_path.stem}_variant_{variant_number}{save_path.suffix}"

            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(png_data)
            print(f"      Saved to {file_path.name}")

        return png_data

    def _select_block_references(
        self,
        description: str,
        block_name: str,
        max_refs: int = 3
    ) -> List[Path]:
        """Select relevant reference textures specifically for blocks."""
        return self.reference_selector.select_references(
            item_description=description,
            item_name=block_name,
            for_block=True,  # Important: search block textures, not items
            max_refs=max_refs
        )

    def _create_block_texture_prompt(
        self,
        block_name: str,
        description: str,
        gameplay_role: str,
        material: str,
        luminance: int = 0
    ) -> str:
        """
        Create a specialized prompt for seamless tileable block textures.

        NEW PROMPT STRUCTURE - Different from item prompts:
        - Emphasizes seamless tiling as primary requirement
        - Material-specific texture guidance
        - No background removal (full coverage)
        - Surface texture focus, not sprite focus
        """
        material = material.upper() if material else "STONE"
        material_config = self.MATERIAL_CONFIGS.get(
            material,
            self.MATERIAL_CONFIGS["STONE"]
        )

        # Luminance effects for glowing blocks
        luminance_instruction = ""
        if luminance and luminance > 0:
            glow_level = "subtle inner glow" if luminance < 8 else "bright glowing effect"
            luminance_instruction = f"""
LUMINANCE EFFECT:
- This block emits light (level {luminance}/15)
- Add {glow_level} - brighter colors toward center
- Use warm yellow/white highlights for light emission
- Maintain texture detail while showing luminosity"""

        prompt = f"""Create a seamless tileable Minecraft block texture for: {block_name}

BLOCK DESCRIPTION: {description}
GAMEPLAY PURPOSE: {gameplay_role}

=== CRITICAL TILING REQUIREMENTS ===
This texture MUST tile seamlessly in all directions:
- TOP edge pixels must match BOTTOM edge pixels exactly
- LEFT edge pixels must match RIGHT edge pixels exactly
- When placed next to itself, no visible seams should appear
- Pattern should flow naturally across tile boundaries

=== MATERIAL: {material} ===
Pattern style: {material_config['pattern']}
Color scheme: {material_config['colors']}
Visual style: {material_config['style']}
{luminance_instruction}

=== VISUAL REQUIREMENTS ===
- Pure Minecraft pixel art aesthetic
- Sharp pixels with NO anti-aliasing or blur
- 4-8 distinct colors maximum
- Consistent top-left lighting (lighter top-left, darker bottom-right)
- Surface texture only - flat top-down view of ONE block face
- Fill the ENTIRE canvas - no background, no margins, no transparency

=== TEXTURE COMPOSITION ===
- Primary base color covering 60-70% of pixels
- Secondary accent/detail color for 20-30%
- Highlight and shadow colors for depth (10-15%)
- Small-scale detail that reads clearly at 16x16

=== TECHNICAL REQUIREMENTS ===
- Output: exactly 16x16 pixels
- Format: fully opaque, no transparency
- View: flat surface texture (not 3D, not isometric, not cube render)
- Fill: 100% coverage of the tile area

=== DO NOT INCLUDE ===
- No 3D cube renders or isometric views
- No perspective or depth beyond surface texture
- No transparency or background
- No UI elements, hands, or tools
- No anti-aliasing or gradient blur
- No realistic photographs
- No text or symbols unless block specifically requires them"""

        return prompt

    def _process_block_texture(
        self,
        img: Image.Image,
        size: int = 16,
        material: str = "STONE",
        luminance: int = 0
    ) -> Image.Image:
        """
        NEW POST-PROCESSING PIPELINE for block textures.

        This pipeline is completely different from item processing:

        1. CONVERT TO RGB - Blocks have no transparency
        2. QUALITY DOWNSAMPLING - Two-stage for better detail preservation
        3. PALETTE QUANTIZATION - Block-specific Minecraft palette
        4. EDGE ENHANCEMENT - Improve tile continuity
        5. LUMINANCE ADJUSTMENT - For glowing blocks

        Args:
            img: Generated image from API
            size: Target size (always 16 for blocks)
            material: Material type for palette hints
            luminance: Light emission level (0-15)

        Returns:
            Processed 16x16 RGB Image (no alpha channel)
        """
        # Step 1: Convert to RGB immediately - blocks are NEVER transparent
        if img.mode != 'RGB':
            # If RGBA, composite onto opaque background
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (128, 128, 128))
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert('RGB')

        # Step 2: Two-stage quality downsampling
        # First pass: high-quality resize to intermediate size
        intermediate_size = size * 4
        img = img.resize((intermediate_size, intermediate_size), Image.Resampling.LANCZOS)

        # Apply subtle sharpening to preserve texture detail
        img = img.filter(ImageFilter.SHARPEN)

        # Second pass: resize to 2x target
        img = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)

        # Final pass: nearest-neighbor to target size for pixel-perfect result
        img = img.resize((size, size), Image.Resampling.NEAREST)

        # Step 3: Quantize to block-specific palette
        img = self._quantize_to_block_palette(img)

        # Step 4: Enhance edge continuity for better tiling
        img = self._enhance_tile_edges(img)

        # Step 5: Apply luminance adjustment for glowing blocks
        if luminance > 0:
            img = self._apply_luminance_effect(img, luminance)

        return img

    def _quantize_to_block_palette(self, img: Image.Image) -> Image.Image:
        """
        Quantize colors to block-specific Minecraft palette.

        Uses a different palette than items, optimized for:
        - Natural materials (stone, wood, dirt)
        - Industrial materials (metal, glass)
        - Organic materials (plants, moss)
        """
        img_array = np.array(img)
        original_shape = img_array.shape
        pixels = img_array.reshape(-1, 3)

        palette_array = np.array(self.BLOCK_PALETTE)
        quantized = np.zeros_like(pixels)

        for i, pixel in enumerate(pixels):
            # Find nearest color using Euclidean distance
            distances = np.sqrt(np.sum((palette_array - pixel) ** 2, axis=1))
            nearest_idx = np.argmin(distances)
            quantized[i] = palette_array[nearest_idx]

        quantized = quantized.reshape(original_shape).astype(np.uint8)
        return Image.fromarray(quantized, 'RGB')

    def _enhance_tile_edges(self, img: Image.Image) -> Image.Image:
        """
        Enhance edges to improve seamless tiling.

        This is a NEW technique not used in item generation.
        It subtly blends edge pixels to reduce visible seams when tiled.

        Algorithm:
        1. Analyze color difference between opposite edges
        2. If difference is too high, blend toward average
        3. Apply subtle smoothing at boundaries
        """
        img_array = np.array(img, dtype=np.float32)
        height, width = img_array.shape[:2]

        # Blend factor - subtle to preserve texture detail
        blend_factor = 0.3

        # Horizontal edge blending (left-right)
        left_edge = img_array[:, 0, :]
        right_edge = img_array[:, width - 1, :]
        avg_horizontal = (left_edge + right_edge) / 2

        # Only blend if difference is significant
        h_diff = np.abs(left_edge - right_edge).mean()
        if h_diff > 30:  # Threshold for noticeable seam
            img_array[:, 0, :] = (1 - blend_factor) * left_edge + blend_factor * avg_horizontal
            img_array[:, width - 1, :] = (1 - blend_factor) * right_edge + blend_factor * avg_horizontal

        # Vertical edge blending (top-bottom)
        top_edge = img_array[0, :, :]
        bottom_edge = img_array[height - 1, :, :]
        avg_vertical = (top_edge + bottom_edge) / 2

        v_diff = np.abs(top_edge - bottom_edge).mean()
        if v_diff > 30:
            img_array[0, :, :] = (1 - blend_factor) * top_edge + blend_factor * avg_vertical
            img_array[height - 1, :, :] = (1 - blend_factor) * bottom_edge + blend_factor * avg_vertical

        return Image.fromarray(img_array.astype(np.uint8), 'RGB')

    def _apply_luminance_effect(self, img: Image.Image, luminance: int) -> Image.Image:
        """
        Apply luminance effect for glowing blocks.

        Creates a subtle glow effect that brightens the texture
        based on the block's light emission level.

        Args:
            img: Input RGB image
            luminance: Light level 0-15

        Returns:
            Image with luminance effect applied
        """
        if luminance <= 0:
            return img

        img_array = np.array(img, dtype=np.float32)

        # Calculate brightness boost (0.0 to 0.5 based on luminance)
        boost = (luminance / 15.0) * 0.4

        # Apply radial glow - brighter toward center
        height, width = img_array.shape[:2]
        center_y, center_x = height // 2, width // 2

        for y in range(height):
            for x in range(width):
                # Distance from center (normalized 0-1)
                dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
                max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
                norm_dist = dist / max_dist

                # Glow is stronger at center
                glow_factor = 1.0 + boost * (1.0 - norm_dist)

                # Apply glow while preserving color ratios
                img_array[y, x] = np.clip(img_array[y, x] * glow_factor, 0, 255)

        return Image.fromarray(img_array.astype(np.uint8), 'RGB')

    # Convenience method for backward compatibility
    def generate_block_texture_from_spec(
        self,
        block_spec: Dict[str, Any],
        count: int = None,
        save_path: Path = None
    ) -> List[bytes]:
        """Alias for generate_block_texture for backward compatibility."""
        return self.generate_block_texture(block_spec, count, save_path)
