"""
Item Image Generator - Creates pixel art textures for Minecraft items and tools

This module handles the generation of item and tool textures using the existing
proven algorithm. Items and tools share the same generation pipeline as they
both require:
- Transparent backgrounds
- Clear outlines
- Centered sprites with padding
- Anti-aliasing removal

Storage: Generated textures are stored under assets/items/
"""
from google import genai
from PIL import Image
from io import BytesIO
from pathlib import Path
from typing import Optional, List

import numpy as np

from config import GEMINI_API_KEY, IMAGE_MODEL, IMAGE_VARIANT_COUNT
from .reference_selector import ReferenceSelector


class ItemImageGenerator:
    """
    Generates pixel art textures for Minecraft items and tools.

    This generator uses the established algorithm optimized for:
    - Items (gems, ingots, food, potions, etc.)
    - Tools (pickaxes, axes, swords, shovels, hoes)

    Key features:
    - Transparent background removal via edge flood-fill
    - Auto-crop and center with consistent padding
    - Two-stage downsampling for quality preservation
    - Minecraft color palette quantization
    - Anti-aliasing artifact cleanup
    """

    # Minecraft-inspired color palette for items
    MINECRAFT_PALETTE = [
        # Grays and blacks
        (0, 0, 0), (64, 64, 64), (127, 127, 127), (191, 191, 191), (255, 255, 255),
        # Browns and tans (wood, dirt)
        (92, 58, 30), (120, 85, 60), (150, 110, 77), (180, 140, 100),
        # Greens (grass, emeralds)
        (34, 139, 34), (60, 179, 113), (102, 255, 102), (0, 128, 0),
        # Blues (diamond, water)
        (92, 219, 213), (79, 193, 255), (0, 0, 255), (30, 144, 255),
        # Reds and oranges
        (255, 0, 0), (255, 69, 0), (220, 20, 60), (178, 34, 34),
        # Purples and magentas
        (147, 112, 219), (186, 85, 211), (255, 0, 255), (138, 43, 226),
        # Yellows and golds
        (255, 215, 0), (255, 255, 0), (255, 200, 124), (218, 165, 32),
        # Stone colors
        (112, 112, 112), (128, 128, 128), (96, 96, 96), (80, 80, 80),
    ]

    def __init__(self):
        """Initialize the item image generator with Gemini API client."""
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = IMAGE_MODEL
        self.reference_selector = ReferenceSelector()
        print("  ItemImageGenerator initialized")

    def generate_item_texture(
        self,
        item_description: str,
        item_name: str,
        count: int = None,
        save_path: Path = None
    ) -> List[bytes]:
        """
        Generate multiple pixel art texture variants for a Minecraft item.

        Args:
            item_description: Description of the item
            item_name: Name of the item
            count: Number of variants to generate (defaults to IMAGE_VARIANT_COUNT)
            save_path: Optional directory to save variants

        Returns:
            List of PNG image data as bytes (16x16 pixels), one per variant
        """
        if count is None:
            count = IMAGE_VARIANT_COUNT

        print(f"\n  Generating {count} item texture variants for: {item_name}")

        textures = []
        for i in range(count):
            print(f"    [{i+1}/{count}] Generating variant {i+1}...")
            texture = self._generate_single_texture(
                item_description=item_description,
                item_name=item_name,
                variant_number=i + 1,
                save_path=save_path
            )
            textures.append(texture)
            print(f"    Variant {i+1} complete")

        print(f"  Generated {count} item variants successfully\n")
        return textures

    def generate_tool_texture(self, tool_spec: dict, count: int = None) -> List[bytes]:
        """
        Generate multiple texture variants for tools (pickaxes, axes, swords, etc.).

        Tools use the same generation algorithm as items since they share
        similar visual requirements (transparent background, held in hand).

        Args:
            tool_spec: Tool specification dictionary
            count: Number of variants (defaults to IMAGE_VARIANT_COUNT)

        Returns:
            List of PNG image data as bytes (16x16 pixels)
        """
        name = tool_spec.get("toolName", "Custom Tool")
        description = tool_spec.get("description", name)
        return self.generate_item_texture(
            item_description=description,
            item_name=name,
            count=count
        )

    def generate_texture_from_spec(self, spec: dict) -> bytes:
        """
        Generate a single texture from mod specification (for final selection).

        Args:
            spec: Mod specification dictionary

        Returns:
            PNG texture data as bytes
        """
        description = spec.get('description', '')
        item_name = spec.get('itemName', 'item')
        rarity = spec.get('properties', {}).get('rarity', 'COMMON')
        fireproof = spec.get('properties', {}).get('fireproof', False)

        # Enhance description with properties
        enhanced_desc = description
        if rarity in ['RARE', 'EPIC']:
            enhanced_desc += f" (glowing, {rarity.lower()} quality)"
        if fireproof:
            enhanced_desc += " (fire-resistant, glowing with heat)"

        prompt = self._create_pixel_art_prompt(enhanced_desc, item_name, rarity)

        print(f"Generating texture for {item_name} ({rarity})...")

        # Select reference textures
        reference_paths = self._select_reference_textures(
            enhanced_desc, item_name, max_refs=2
        )

        contents = [prompt]

        if reference_paths:
            print(f"  Using {len(reference_paths)} reference texture(s)")
            contents.append("\n\nREFERENCE TEXTURES (use these as style guides):")
            for ref_path in reference_paths:
                ref_image = Image.open(ref_path).convert("RGB")
                contents.append(ref_image)

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
            raise ValueError("No image data in response")

        pixelated = self._convert_to_pixel_art(img, size=16)

        output = BytesIO()
        pixelated.save(output, format='PNG')
        return output.getvalue()

    def _generate_single_texture(
        self,
        item_description: str,
        item_name: str,
        variant_number: int = 1,
        save_path: Path = None
    ) -> bytes:
        """Generate a single pixel art texture variant for a Minecraft item."""
        prompt = self._create_pixel_art_prompt(item_description, item_name)

        # Select reference textures (only for first variant to save API calls)
        reference_paths = []
        if variant_number == 1:
            reference_paths = self._select_reference_textures(
                item_description, item_name, max_refs=3
            )

        contents = [prompt]

        if reference_paths:
            print(f"      Using {len(reference_paths)} reference texture(s) as style guides")
            contents.append("\n\nREFERENCE TEXTURES (use these as style guides):")
            for ref_path in reference_paths:
                ref_image = Image.open(ref_path).convert("RGB")
                contents.append(ref_image)

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
            raise ValueError("No image data in response")

        pixelated = self._convert_to_pixel_art(img, size=16)

        output = BytesIO()
        pixelated.save(output, format='PNG')
        png_data = output.getvalue()

        if save_path:
            if save_path.is_dir():
                file_path = save_path / f"{item_name}_variant_{variant_number}.png"
            else:
                file_path = save_path.parent / f"{save_path.stem}_variant_{variant_number}{save_path.suffix}"

            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(png_data)
            print(f"      Saved to {file_path.name}")

        return png_data

    def _select_reference_textures(
        self,
        item_description: str,
        item_name: str,
        max_refs: int = 3
    ) -> List[Path]:
        """Use AI agent to select relevant reference textures for items."""
        return self.reference_selector.select_references(
            item_description=item_description,
            item_name=item_name,
            for_block=False,
            max_refs=max_refs
        )

    def _create_pixel_art_prompt(
        self,
        item_description: str,
        item_name: str,
        rarity: str = "COMMON"
    ) -> str:
        """Create an enhanced prompt optimized for Minecraft-style pixel art items."""
        rarity_styles = {
            "COMMON": "simple, clean design with 3-5 colors. Matte finish, no special effects.",
            "UNCOMMON": "slightly more detailed with 4-6 colors. Subtle highlights and depth.",
            "RARE": "detailed with 5-8 colors. Add shimmer effects, glossy highlights, and rich color depth.",
            "EPIC": "highly detailed with 6-10 colors. Add glowing accents, particle effects, magical aura, vibrant colors."
        }
        style = rarity_styles.get(rarity, rarity_styles["COMMON"])

        color_guide = """
COLOR PALETTE (use colors similar to these Minecraft standards):
- Diamond/Cyan: #5CDBD5, #4FC3F7
- Gold/Yellow: #FFD700, #FFC107
- Iron/Gray: #C0C0C0, #808080
- Emerald/Green: #50C878, #3CB371
- Ruby/Red: #DC143C, #B22222
- Amethyst/Purple: #9370DB, #BA55D3
- Netherite/Dark: #4A4A4A, #2C2C2C
- Wood/Brown: #8B4513, #A0522D"""

        examples = self._get_item_examples(item_name, item_description)

        prompt = f"""Create a professional pixel art item sprite for Minecraft of: {item_name}
Description: {item_description}
Rarity: {rarity} - {style}

{color_guide}

VISUAL STYLE REQUIREMENTS:
- Pure Minecraft aesthetic: sharp pixels, NO anti-aliasing, NO blurriness
- Flat geometric shapes with clear pixel boundaries
- {style}
- Reference style: {examples}
- Use bold outlines (black or very dark color) to define the item's shape
- Add depth with 2-3 shades of each base color (light, medium, dark)
- Keep design simple enough to read clearly at 16x16 pixels

TECHNICAL REQUIREMENTS:
- PURE WHITE background (#FFFFFF / RGB 255,255,255) ONLY
- NO gradients, NO soft shadows on the background
- Center the sprite with generous white margins (at least 20% padding)
- The item sprite MUST have clear dark outlines separating it from white background
- NO white pixels inside the item outline - use off-white (#F0F0F0 or darker) if needed
- Item should occupy roughly 60-70% of the canvas for good scaling

NEGATIVE PROMPTS (DO NOT include these):
- No 3D rendering or smooth shading
- No realistic textures or photographs
- No blurry edges or anti-aliasing
- No gradients spanning multiple pixels
- No hands, UI elements, or text
- No white highlights inside the sprite (use light gray/color instead)"""

        return prompt

    def _get_item_examples(self, item_name: str, description: str) -> str:
        """Generate contextual examples based on item type."""
        text = f"{item_name} {description}".lower()

        if any(word in text for word in ["gem", "crystal", "shard", "stone"]):
            return "diamond (bright cyan geometric gem), emerald (green crystal), ruby (red faceted gem)"
        elif any(word in text for word in ["sword", "blade", "dagger"]):
            return "diamond sword (cyan blade with brown handle), netherite sword (dark blade)"
        elif any(word in text for word in ["pickaxe", "axe", "tool"]):
            return "diamond pickaxe (cyan head with brown stick), iron pickaxe (gray head)"
        elif any(word in text for word in ["apple", "food", "fruit"]):
            return "golden apple (yellow with green leaf), regular apple (red with brown stem)"
        elif any(word in text for word in ["ingot", "bar", "metal"]):
            return "gold ingot (yellow rectangular bar with bevel), iron ingot (gray rectangular)"
        elif any(word in text for word in ["potion", "bottle"]):
            return "potion bottle (glass container with colored liquid inside)"
        else:
            return "diamond (geometric gem), golden apple (simple fruit), iron sword (weapon with handle)"

    def _convert_to_pixel_art(self, img: Image.Image, size: int = 16) -> Image.Image:
        """
        Convert a high-res image to pixel art with Minecraft-style processing.

        Pipeline:
        1. Remove peripheral white background via flood-fill
        2. Replace remaining near-white pixels with transparency
        3. Auto-crop and pad with consistent margins
        4. Two-stage downsampling (Lanczos -> Nearest)
        5. Final white cleanup pass
        6. Minecraft palette quantization
        7. Enhanced edge cleanup for crisp pixels
        """
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # 1. Remove peripheral white background
        img = self._remove_edge_background(img)
        img = self._replace_white_background_with_transparency(img)

        # 2. Auto-crop and pad with consistent margins
        img = self._auto_crop_and_pad(img, target_px=size * 4)

        # 3. Two-stage downsampling for better quality
        intermediate_size = size * 2
        medium = img.resize((intermediate_size, intermediate_size), Image.Resampling.LANCZOS)
        small = medium.resize((size, size), Image.Resampling.NEAREST)

        # 4. Final white background cleanup
        small = self._replace_white_background_with_transparency(small)

        # 5. Apply Minecraft color palette quantization
        result = self._quantize_to_minecraft_palette(small)

        # 6. Enhanced edge cleanup
        result = self._enhanced_edge_cleanup(result)

        return result

    def _remove_edge_background(self, img: Image.Image, threshold: int = 235) -> Image.Image:
        """
        Remove ONLY peripheral white background using flood-fill from edges.
        Preserves white pixels that are part of the sprite interior.
        """
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        width, height = img.size
        pixels = img.load()
        visited = set()

        def is_white_bg(x, y):
            if (x, y) in visited:
                return False
            r, g, b, a = pixels[x, y]
            brightness = (r + g + b) / 3
            variance = max(r, g, b) - min(r, g, b)
            return brightness >= threshold and variance < 20

        def flood_from_edge(start_x, start_y):
            if not is_white_bg(start_x, start_y):
                return
            stack = [(start_x, start_y)]
            while stack:
                x, y = stack.pop()
                if (x, y) in visited or x < 0 or x >= width or y < 0 or y >= height:
                    continue
                if not is_white_bg(x, y):
                    continue
                visited.add((x, y))
                pixels[x, y] = (0, 0, 0, 0)
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    stack.append((x + dx, y + dy))

        for x in range(width):
            flood_from_edge(x, 0)
            flood_from_edge(x, height - 1)
        for y in range(height):
            flood_from_edge(0, y)
            flood_from_edge(width - 1, y)

        return img

    def _replace_white_background_with_transparency(
        self,
        img: Image.Image,
        tolerance: int = 6
    ) -> Image.Image:
        """Convert near-white pixels into transparent pixels."""
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        pixels = img.load()
        width, height = img.size

        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                if a == 0:
                    continue
                if (
                    abs(r - 255) <= tolerance
                    and abs(g - 255) <= tolerance
                    and abs(b - 255) <= tolerance
                ):
                    pixels[x, y] = (r, g, b, 0)

        return img

    def _auto_crop_and_pad(
        self,
        img: Image.Image,
        target_px: int = 64,
        padding_ratio: float = 0.18
    ) -> Image.Image:
        """
        Crop out empty borders and add even padding so the sprite sits centered.
        """
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        width, height = img.size
        pixels = img.load()

        min_x, min_y = width, height
        max_x, max_y = 0, 0
        found = False

        for y in range(height):
            for x in range(width):
                if pixels[x, y][3] > 10:
                    found = True
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if not found:
            return img

        bbox_w = max_x - min_x + 1
        bbox_h = max_y - min_y + 1
        sprite_side = max(bbox_w, bbox_h)
        pad = max(1, int(sprite_side * padding_ratio))

        cropped = img.crop((min_x, min_y, max_x + 1, max_y + 1))
        canvas_side = sprite_side + pad * 2
        canvas = Image.new('RGBA', (canvas_side, canvas_side), (0, 0, 0, 0))

        offset_x = (canvas_side - cropped.width) // 2
        offset_y = (canvas_side - cropped.height) // 2
        canvas.paste(cropped, (offset_x, offset_y))

        if target_px and canvas_side != target_px:
            canvas = canvas.resize((target_px, target_px), Image.Resampling.NEAREST)

        return canvas

    def _quantize_to_minecraft_palette(self, img: Image.Image) -> Image.Image:
        """Quantize image colors to Minecraft-inspired palette."""
        if img.mode == 'RGBA':
            img_array = np.array(img)
            alpha = img_array[:, :, 3]
            rgb = img_array[:, :, :3]
        else:
            img_array = np.array(img.convert('RGB'))
            alpha = None
            rgb = img_array

        original_shape = rgb.shape
        pixels = rgb.reshape(-1, 3)

        palette_array = np.array(self.MINECRAFT_PALETTE)
        quantized = np.zeros_like(pixels)

        for i, pixel in enumerate(pixels):
            if alpha is not None and i < len(alpha.flatten()) and alpha.flatten()[i] < 10:
                quantized[i] = pixel
                continue

            distances = np.sqrt(np.sum((palette_array - pixel) ** 2, axis=1))
            nearest_idx = np.argmin(distances)
            quantized[i] = palette_array[nearest_idx]

        quantized = quantized.reshape(original_shape).astype(np.uint8)

        if alpha is not None:
            result_array = np.dstack([quantized, alpha])
            result = Image.fromarray(result_array.astype(np.uint8), 'RGBA')
        else:
            result = Image.fromarray(quantized, 'RGB')

        return result

    def _enhanced_edge_cleanup(self, img: Image.Image) -> Image.Image:
        """Enhanced edge cleanup for crisp pixel art with anti-aliasing removal."""
        if img.mode != 'RGBA':
            return img

        img_array = np.array(img)
        height, width = img_array.shape[:2]

        cleaned = img_array.copy()

        for y in range(height):
            for x in range(width):
                r, g, b, a = img_array[y, x]

                if a < 10:
                    continue

                if a > 245:
                    continue

                # Semi-transparent pixels (potential anti-aliasing artifacts)
                neighbors_transparent = 0
                neighbors_opaque = 0

                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < height and 0 <= nx < width:
                            neighbor_alpha = img_array[ny, nx, 3]
                            if neighbor_alpha < 10:
                                neighbors_transparent += 1
                            elif neighbor_alpha > 245:
                                neighbors_opaque += 1

                if neighbors_transparent >= 5:
                    cleaned[y, x] = [0, 0, 0, 0]
                elif neighbors_opaque >= 5:
                    cleaned[y, x, 3] = 255
                elif a < 128:
                    cleaned[y, x] = [0, 0, 0, 0]
                else:
                    cleaned[y, x, 3] = 255

        return Image.fromarray(cleaned, 'RGBA')
