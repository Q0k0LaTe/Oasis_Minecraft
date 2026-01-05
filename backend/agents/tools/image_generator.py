"""
Image Generator - Creates pixel art textures for Minecraft items using Google Imagen
"""
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from pathlib import Path
from typing import Optional, List, Dict
import numpy as np
import json

from config import GEMINI_API_KEY, IMAGE_MODEL, IMAGE_SIZE, IMAGE_QUALITY, IMAGE_VARIANT_COUNT
from .reference_selector import ReferenceSelector


class ImageGenerator:
    """Generates pixel art textures for Minecraft items"""

    # Minecraft-inspired color palette (common colors used in vanilla Minecraft textures)
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
        # Configure Google Imagen client
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = IMAGE_MODEL

        # Initialize reference selector agent
        self.reference_selector = ReferenceSelector()
        print("✓ ImageGenerator initialized with AI-powered reference selector")

    def _select_reference_textures(
        self,
        item_description: str,
        item_name: str,
        max_refs: int = 3,
        for_block: bool = False
    ) -> List[Path]:
        """
        Use AI agent to select relevant reference textures

        Args:
            item_description: Description of the item to generate
            item_name: Name of the item
            max_refs: Maximum number of reference textures to return
            for_block: If True, search block textures instead of items

        Returns:
            List of paths to relevant reference textures
        """
        return self.reference_selector.select_references(
            item_description=item_description,
            item_name=item_name,
            for_block=for_block,
            max_refs=max_refs
        )

    def generate_item_texture(
        self,
        item_description: str,
        item_name: str,
        count: int = None,
        save_path: Path = None
    ) -> List[bytes]:
        """
        Generate multiple pixel art texture variants for a Minecraft item

        This is the main method that generates IMAGE_VARIANT_COUNT (default: 5) variants
        for user selection.

        Args:
            item_description: Description of the item
            item_name: Name of the item
            count: Number of variants to generate (defaults to IMAGE_VARIANT_COUNT)
            save_path: Optional directory to save variants (saved as {name}_variant_1.png, etc.)

        Returns:
            List of PNG image data as bytes (16x16 pixels), one per variant
        """
        if count is None:
            count = IMAGE_VARIANT_COUNT

        print(f"\n🎨 Generating {count} texture variants for: {item_name}")

        textures = []
        for i in range(count):
            print(f"  [{i+1}/{count}] Generating variant {i+1}...")
            texture = self._generate_single_item_texture(
                item_description=item_description,
                item_name=item_name,
                variant_number=i+1,
                save_path=save_path
            )
            textures.append(texture)
            print(f"  ✓ Variant {i+1} complete")

        print(f"✓ Generated {count} variants successfully\n")
        return textures

    def _generate_single_item_texture(
        self,
        item_description: str,
        item_name: str,
        variant_number: int = 1,
        save_path: Path = None
    ) -> bytes:
        """
        Generate a single pixel art texture variant for a Minecraft item

        Args:
            item_description: Description of the item
            item_name: Name of the item
            variant_number: Which variant this is (for file naming)
            save_path: Optional directory to save the image (will append variant number)

        Returns:
            PNG image data as bytes (16x16 pixels)
        """
        # Create a detailed prompt for pixel art generation
        prompt = self._create_pixel_art_prompt(item_description, item_name)

        # Select reference textures (only once for first variant to save API calls)
        reference_paths = []
        if variant_number == 1:
            reference_paths = self._select_reference_textures(
                item_description, item_name, max_refs=3
            )

        # Build contents list with prompt and reference images
        contents = [prompt]

        # Add reference images if available
        if reference_paths:
            print(f"    Using {len(reference_paths)} reference texture(s) as style guides")
            contents.append("\n\nREFERENCE TEXTURES (use these as style guides):")
            for ref_path in reference_paths:
                ref_image = Image.open(ref_path).convert("RGB")
                contents.append(ref_image)

        # Generate image using Gemini 3 Pro image generation
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
        )

        # Get the image data
        img = None
        for part in response.parts:
            if part.inline_data:
                # Convert inline_data bytes to PIL Image
                img = Image.open(BytesIO(part.inline_data.data))
                break

        if img is None:
            raise ValueError("No image data in response")

        # Convert to 16x16 pixel art (with background removal for items)
        pixelated = self._convert_to_pixel_art(img, size=16, for_block=False)

        # Save to BytesIO
        output = BytesIO()
        pixelated.save(output, format='PNG')
        png_data = output.getvalue()

        # Optionally save to file with variant number
        if save_path:
            if save_path.is_dir():
                # If directory, create file with variant number
                file_path = save_path / f"{item_name}_variant_{variant_number}.png"
            else:
                # If file path, append variant number before extension
                file_path = save_path.parent / f"{save_path.stem}_variant_{variant_number}{save_path.suffix}"

            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(png_data)
            print(f"    Saved to {file_path.name}")

        return png_data

    def _create_pixel_art_prompt(self, item_description: str, item_name: str, rarity: str = "COMMON") -> str:
        """Create an enhanced Imagen prompt optimized for Minecraft-style pixel art"""

        # Rarity-based style guidance
        rarity_styles = {
            "COMMON": "simple, clean design with 3-5 colors. Matte finish, no special effects.",
            "UNCOMMON": "slightly more detailed with 4-6 colors. Subtle highlights and depth.",
            "RARE": "detailed with 5-8 colors. Add shimmer effects, glossy highlights, and rich color depth.",
            "EPIC": "highly detailed with 6-10 colors. Add glowing accents, particle effects, magical aura, vibrant colors."
        }
        style = rarity_styles.get(rarity, rarity_styles["COMMON"])

        # Enhanced color palette guidance
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

        # Specific visual examples based on item type
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
        """Generate contextual examples based on item type"""
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

    def _create_block_prompt(
        self,
        block_name: str,
        description: str,
        gameplay_role: str = "",
        material: str = "",
        luminance: Optional[int] = None
    ) -> str:
        """Enhanced prompt for seamless Minecraft block textures"""
        material_guide = {
            "STONE": "gray base with subtle darker speckles and cracks, similar to cobblestone",
            "METAL": "metallic with horizontal/vertical panel lines, reflective highlights",
            "WOOD": "grain patterns running vertically or horizontally, warm brown tones",
            "GLASS": "semi-transparent look with light reflections, clean edges",
            "PLANT": "organic green tones with texture variation, natural patterns",
            "SAND": "grainy texture with warm beige tones, subtle noise",
            "DEEPSLATE": "dark gray with directional cracks and subtle blue-gray tint",
        }
        material_hint = material_guide.get(material, "textured surface with depth")

        luminance_effects = ""
        if luminance and luminance > 0:
            glow_intensity = "subtle" if luminance < 8 else "bright"
            luminance_effects = f"Add {glow_intensity} glowing effects - brighter center fading to edges."

        prompt = f"""Create a professional seamless tileable Minecraft block texture for: {block_name}
Description: {description}
Purpose: {gameplay_role}
Material style: {material_hint}

VISUAL REQUIREMENTS:
- Pure Minecraft block aesthetic: 16x16 pixel art, sharp pixels, NO blur
- Texture MUST tile seamlessly: edges must connect perfectly when repeated
- Style: {material_hint}
- Use 4-8 solid colors with clear pixel boundaries
- Add depth with subtle shading (light source from top-left)
- {luminance_effects if luminance_effects else 'Natural lighting with subtle shadows'}

REFERENCE EXAMPLES:
- Stone blocks: gray base (#808080) with darker cracks (#505050) and lighter spots (#A0A0A0)
- Ore blocks: stone texture with embedded colored crystals (cyan, gold, emerald)
- Wood planks: parallel grain lines with 3-tone brown palette
- Metal blocks: panel grid pattern with highlights and shadows

TECHNICAL REQUIREMENTS:
- Full 16x16 pixel square, completely opaque (NO transparency)
- Edges must tile: top connects to bottom, left connects to right
- NO 3D perspective, NO depth blur, NO shadows cast outside the tile
- Flat top-down view of the block surface texture
- Border pixels must match opposite side for seamless tiling

NEGATIVE PROMPTS (avoid):
- No hands, tools, or 3D rendered blocks
- No UI elements or text
- No anti-aliasing or gradient blur
- No photos or realistic textures
- No shadows extending beyond the 16x16 boundary"""

        return prompt

    def _convert_to_pixel_art(self, img: Image.Image, size: int = 16, for_block: bool = False) -> Image.Image:
        """
        Convert a high-res image to pixel art with enhanced Minecraft-style processing

        Args:
            img: PIL Image
            size: Target size (default 16x16)
            for_block: If True, keep opaque (no transparency) for tileable blocks

        Returns:
            Enhanced pixelated PIL Image
        """
        # Ensure we're working with RGBA
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        if for_block:
            # Blocks: keep full 16x16 opaque, no background removal
            # Use 2-stage downsampling for better quality
            intermediate_size = size * 2
            medium = img.resize((intermediate_size, intermediate_size), Image.Resampling.LANCZOS)
            small = medium.resize((size, size), Image.Resampling.NEAREST)

            # Apply Minecraft color palette
            quantized = self._quantize_to_minecraft_palette(small, for_block=True)
            return quantized
        else:
            # Items/Tools: enhanced processing pipeline
            # 1. Remove peripheral white background
            img = self._remove_edge_background(img)
            img = self._replace_white_background_with_transparency(img)

            # 2. Auto-crop and pad with consistent margins
            img = self._auto_crop_and_pad(img, target_px=size * 4)

            # 3. Two-stage downsampling for better pixel art quality
            intermediate_size = size * 2
            medium = img.resize((intermediate_size, intermediate_size), Image.Resampling.LANCZOS)
            small = medium.resize((size, size), Image.Resampling.NEAREST)

            # 4. Final white background cleanup
            small = self._replace_white_background_with_transparency(small)

            # 5. Apply Minecraft color palette quantization
            result = self._quantize_to_minecraft_palette(small, for_block=False)

            # 6. Enhanced edge cleanup
            result = self._enhanced_edge_cleanup(result)

        return result

    def _remove_edge_background(self, img: Image.Image, threshold: int = 235) -> Image.Image:
        """
        Remove ONLY peripheral white background using flood-fill from edges.
        Preserves white pixels that are part of the sprite interior.

        Args:
            img: PIL Image in RGBA mode
            threshold: Brightness threshold for white detection (0-255)

        Returns:
            Image with edge background transparent, interior whites preserved
        """
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        width, height = img.size
        pixels = img.load()
        visited = set()
        
        def is_white_bg(x, y):
            """Check if pixel is background white (very bright, low variance)"""
            if (x, y) in visited:
                return False
            r, g, b, a = pixels[x, y]
            brightness = (r + g + b) / 3
            variance = max(r, g, b) - min(r, g, b)
            return brightness >= threshold and variance < 20
        
        def flood_from_edge(start_x, start_y):
            """Flood-fill transparent from edge, stopping at non-white pixels"""
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
                pixels[x, y] = (0, 0, 0, 0)  # Make transparent
                # Check 4-connected neighbors
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    stack.append((x + dx, y + dy))
        
        # Flood from all edges
        for x in range(width):
            flood_from_edge(x, 0)          # Top edge
            flood_from_edge(x, height - 1)  # Bottom edge
        for y in range(height):
            flood_from_edge(0, y)          # Left edge
            flood_from_edge(width - 1, y)   # Right edge
        
        return img

    def _replace_white_background_with_transparency(
        self,
        img: Image.Image,
        tolerance: int = 6
    ) -> Image.Image:
        """
        Convert near-white pixels (intended background) into transparent pixels.
        Assumes the generation prompt keeps item fill colors away from pure white.
        """
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

    def _remove_edge_artifacts(self, img: Image.Image) -> Image.Image:
        """
        Remove light-colored edge artifacts left by anti-aliasing

        Args:
            img: PIL Image in RGBA mode

        Returns:
            Image with cleaned edges
        """
        pixels = img.load()
        width, height = img.size

        # Process each pixel
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]

                # Skip already transparent pixels
                if a == 0:
                    continue

                # Check if this is a light grayish pixel (likely edge artifact)
                brightness = (r + g + b) / 3
                if brightness > 200:
                    # Check surrounding pixels
                    has_solid_neighbor = False
                    transparent_neighbors = 0

                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < width and 0 <= ny < height:
                                nr, ng, nb, na = pixels[nx, ny]
                                neighbor_brightness = (nr + ng + nb) / 3

                                if na == 0:
                                    transparent_neighbors += 1
                                elif neighbor_brightness < 150:
                                    has_solid_neighbor = True

                    # If mostly surrounded by transparent pixels, make this transparent too
                    if transparent_neighbors >= 4 and not has_solid_neighbor:
                        pixels[x, y] = (0, 0, 0, 0)

        return img

    def _clean_edges(self, img: Image.Image) -> Image.Image:
        """
        Clean up semi-transparent edge pixels for crisp pixel art

        Args:
            img: PIL Image in RGBA mode

        Returns:
            Image with cleaned edges
        """
        data = img.getdata()
        new_data = []

        for pixel in data:
            r, g, b, a = pixel
            # If alpha is very low, make it fully transparent
            if a < 30:
                new_data.append((0, 0, 0, 0))
            # If alpha is very high, make it fully opaque
            elif a > 225:
                new_data.append((r, g, b, 255))
            else:
                # Keep as is
                new_data.append(pixel)

        result = Image.new('RGBA', img.size)
        result.putdata(new_data)
        return result

    def _auto_crop_and_pad(
        self,
        img: Image.Image,
        target_px: int = 64,
        padding_ratio: float = 0.18
    ) -> Image.Image:
        """
        Crop out empty borders and add even padding so the sprite sits centered.
        The target_px parameter builds a consistent intermediate canvas (default 4x16)
        before shrinking to the final 16px size which keeps borders uniform.
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
                if pixels[x, y][3] > 10:  # ignore nearly-transparent pixels
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

    def _quantize_to_minecraft_palette(self, img: Image.Image, for_block: bool = False) -> Image.Image:
        """
        Quantize image colors to Minecraft-inspired palette for authentic look

        Args:
            img: PIL Image to quantize
            for_block: If True, return RGB; if False, preserve alpha channel

        Returns:
            Image with colors mapped to Minecraft palette
        """
        # Convert to numpy for faster processing
        if img.mode == 'RGBA':
            img_array = np.array(img)
            alpha = img_array[:, :, 3]
            rgb = img_array[:, :, :3]
        else:
            img_array = np.array(img.convert('RGB'))
            alpha = None
            rgb = img_array

        # Flatten for processing
        original_shape = rgb.shape
        pixels = rgb.reshape(-1, 3)

        # Map each pixel to nearest Minecraft palette color
        palette_array = np.array(self.MINECRAFT_PALETTE)
        quantized = np.zeros_like(pixels)

        for i, pixel in enumerate(pixels):
            # Skip transparent pixels
            if alpha is not None and i < len(alpha.flatten()) and alpha.flatten()[i] < 10:
                quantized[i] = pixel
                continue

            # Find nearest color in Minecraft palette using Euclidean distance
            distances = np.sqrt(np.sum((palette_array - pixel) ** 2, axis=1))
            nearest_idx = np.argmin(distances)
            quantized[i] = palette_array[nearest_idx]

        # Reshape back to image
        quantized = quantized.reshape(original_shape).astype(np.uint8)

        # Create result image
        if for_block:
            result = Image.fromarray(quantized, 'RGB')
        else:
            result_array = np.dstack([quantized, alpha]) if alpha is not None else quantized
            result = Image.fromarray(result_array.astype(np.uint8), 'RGBA' if alpha is not None else 'RGB')

        return result

    def _enhanced_edge_cleanup(self, img: Image.Image) -> Image.Image:
        """
        Enhanced edge cleanup for crisp pixel art with better anti-aliasing removal

        Args:
            img: PIL Image in RGBA mode

        Returns:
            Image with cleaned, crisp edges
        """
        if img.mode != 'RGBA':
            return img

        img_array = np.array(img)
        height, width = img_array.shape[:2]

        # Create output array
        cleaned = img_array.copy()

        for y in range(height):
            for x in range(width):
                r, g, b, a = img_array[y, x]

                # Fully transparent pixels - leave as is
                if a < 10:
                    continue

                # Fully opaque pixels - leave as is
                if a > 245:
                    continue

                # Semi-transparent pixels (potential anti-aliasing artifacts)
                # Check if surrounded by transparent pixels
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

                # If mostly surrounded by transparent, make fully transparent
                if neighbors_transparent >= 5:
                    cleaned[y, x] = [0, 0, 0, 0]
                # If mostly surrounded by opaque, make fully opaque
                elif neighbors_opaque >= 5:
                    cleaned[y, x, 3] = 255
                # Otherwise, threshold to opaque or transparent
                elif a < 128:
                    cleaned[y, x] = [0, 0, 0, 0]
                else:
                    cleaned[y, x, 3] = 255

        return Image.fromarray(cleaned, 'RGBA')

    def generate_texture_from_spec(self, spec: dict) -> bytes:
        """
        Generate texture from mod specification

        Args:
            spec: Mod specification dictionary

        Returns:
            PNG texture data
        """
        description = spec.get('description', '')
        item_name = spec.get('itemName', 'item')

        # Add rarity and properties to enhance the prompt
        rarity = spec.get('properties', {}).get('rarity', 'COMMON')
        fireproof = spec.get('properties', {}).get('fireproof', False)

        # Enhance description with properties
        enhanced_desc = description
        if rarity in ['RARE', 'EPIC']:
            enhanced_desc += f" (glowing, {rarity.lower()} quality)"
        if fireproof:
            enhanced_desc += " (fire-resistant, glowing with heat)"

        # Generate with rarity-aware prompt
        prompt = self._create_pixel_art_prompt(enhanced_desc, item_name, rarity)

        print(f"Generating texture for {item_name} ({rarity})...")

        # Select reference textures
        reference_paths = self._select_reference_textures(
            enhanced_desc, item_name, max_refs=2
        )

        # Build contents list with prompt and reference images
        contents = [prompt]

        # Add reference images if available
        if reference_paths:
            print(f"  Using {len(reference_paths)} reference texture(s)")
            contents.append("\n\nREFERENCE TEXTURES (use these as style guides):")
            for ref_path in reference_paths:
                ref_image = Image.open(ref_path).convert("RGB")
                contents.append(ref_image)

        # Generate image using Gemini image generation
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
        )

        # Get the image data
        img = None
        for part in response.parts:
            if part.inline_data:
                # Convert inline_data bytes to PIL Image
                img = Image.open(BytesIO(part.inline_data.data))
                break

        if img is None:
            raise ValueError("No image data in response")

        # Convert to 16x16 pixel art with enhanced processing
        pixelated = self._convert_to_pixel_art(img, size=16, for_block=False)

        # Save to BytesIO
        output = BytesIO()
        pixelated.save(output, format='PNG')
        return output.getvalue()

    def generate_multiple_block_textures(self, block_spec: dict, count: int = 5) -> list[bytes]:
        """
        Generate multiple block texture variants
        """
        textures = []
        for i in range(count):
            texture = self.generate_block_texture_from_spec(block_spec, save_path=None)
            textures.append(texture)
            print(f"Generated block variant {i+1}/{count}")
        return textures

    def generate_multiple_tool_textures(self, tool_spec: dict, count: int = 5) -> list[bytes]:
        """
        Generate multiple tool texture variants
        """
        textures = []
        for i in range(count):
            texture = self.generate_tool_texture(tool_spec)
            textures.append(texture)
            print(f"Generated tool variant {i+1}/{count}")
        return textures

    def generate_block_texture_from_spec(
        self,
        block_spec: dict,
        count: int = None,
        save_path: Path = None
    ) -> List[bytes]:
        """
        Generate multiple seamless block texture variants using block metadata.

        Args:
            block_spec: Block specification dictionary
            count: Number of variants to generate (defaults to IMAGE_VARIANT_COUNT)
            save_path: Optional directory to save variants

        Returns:
            List of PNG image data as bytes (16x16 pixels), one per variant
        """
        if count is None:
            count = IMAGE_VARIANT_COUNT

        block_name = block_spec.get("blockName", "Mystery Block")
        description = block_spec.get("description", "")
        gameplay = block_spec.get("gameplayRole", "")
        properties = block_spec.get("properties", {})

        print(f"\n🧱 Generating {count} block texture variants for: {block_name}")

        textures = []
        for i in range(count):
            print(f"  [{i+1}/{count}] Generating variant {i+1}...")
            texture = self._generate_single_block_texture(
                block_name=block_name,
                description=description,
                gameplay=gameplay,
                properties=properties,
                variant_number=i+1,
                save_path=save_path
            )
            textures.append(texture)
            print(f"  ✓ Variant {i+1} complete")

        print(f"✓ Generated {count} block variants successfully\n")
        return textures

    def _generate_single_block_texture(
        self,
        block_name: str,
        description: str,
        gameplay: str,
        properties: dict,
        variant_number: int = 1,
        save_path: Path = None
    ) -> bytes:
        """Generate a single seamless block texture variant"""

        prompt = self._create_block_prompt(
            block_name=block_name,
            description=description,
            gameplay_role=gameplay,
            material=properties.get("material"),
            luminance=properties.get("luminance"),
        )

        # Select reference textures (only once for first variant)
        reference_paths = []
        if variant_number == 1:
            reference_paths = self._select_reference_textures(
                description, block_name, max_refs=3, for_block=True
            )

        # Build contents list with prompt and reference images
        contents = [prompt]

        # Add reference images if available
        if reference_paths:
            print(f"    Using {len(reference_paths)} reference block texture(s) as style guides")
            contents.append("\n\nREFERENCE BLOCK TEXTURES (use these as style guides):")
            for ref_path in reference_paths:
                ref_image = Image.open(ref_path).convert("RGB")
                contents.append(ref_image)

        # Generate image using Gemini 3 Pro image generation
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
        )

        # Get the image data
        img = None
        for part in response.parts:
            if part.inline_data:
                img = Image.open(BytesIO(part.inline_data.data))
                break

        if img is None:
            raise ValueError("No image data in response")

        pixelated = self._convert_to_pixel_art(img, size=16, for_block=True)

        output = BytesIO()
        pixelated.save(output, format='PNG')
        png_data = output.getvalue()

        # Optionally save to file with variant number
        if save_path:
            if save_path.is_dir():
                file_path = save_path / f"{block_name}_variant_{variant_number}.png"
            else:
                file_path = save_path.parent / f"{save_path.stem}_variant_{variant_number}{save_path.suffix}"

            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(png_data)
            print(f"    Saved to {file_path.name}")

        return png_data

    def generate_tool_texture(self, tool_spec: dict, count: int = None) -> List[bytes]:
        """
        Generate multiple texture variants for melee tools like pickaxes.

        Args:
            tool_spec: Tool specification dictionary
            count: Number of variants (defaults to IMAGE_VARIANT_COUNT)

        Returns:
            List of PNG image data as bytes (16x16 pixels)
        """
        name = tool_spec.get("toolName", "Custom Pickaxe")
        description = tool_spec.get("description", name)
        return self.generate_item_texture(
            item_description=description,
            item_name=name,
            count=count
        )
