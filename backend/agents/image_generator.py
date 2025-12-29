"""
Image Generator - Creates pixel art textures for Minecraft items using Google Imagen
"""
import hashlib
import google.generativeai as genai
from PIL import Image, ImageDraw
import requests
from io import BytesIO
from pathlib import Path
from typing import Callable, Optional

from config import GEMINI_API_KEY, IMAGE_MODEL, IMAGE_SIZE, IMAGE_QUALITY


class ImageGenerator:
    """Generates pixel art textures for Minecraft items"""

    def __init__(self):
        # Configure Gemini for image generation
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(IMAGE_MODEL)

    def generate_multiple_item_textures(
        self,
        item_description: str,
        item_name: str,
        count: int = 5,
        placeholder_factory: Optional[Callable[[], bytes]] = None
    ) -> list[bytes]:
        """
        Generate multiple pixel art texture variants for a Minecraft item

        Args:
            item_description: Description of the item
            item_name: Name of the item
            count: Number of variants to generate
            placeholder_factory: Optional function to create placeholder

        Returns:
            List of PNG image data as bytes (16x16 pixels)
        """
        textures = []
        for i in range(count):
            try:
                texture = self.generate_item_texture(
                    item_description=item_description,
                    item_name=item_name,
                    save_path=None,
                    placeholder_factory=placeholder_factory
                )
                textures.append(texture)
                print(f"Generated variant {i+1}/{count} for {item_name}")
            except Exception as e:
                print(f"Error generating variant {i+1}: {e}")
                if placeholder_factory:
                    textures.append(placeholder_factory())
                else:
                    textures.append(self._create_item_placeholder_texture(item_name))
        return textures

    def generate_item_texture(
        self,
        item_description: str,
        item_name: str,
        save_path: Path = None,
        placeholder_factory: Optional[Callable[[], bytes]] = None
    ) -> bytes:
        """
        Generate a pixel art texture for a Minecraft item

        Args:
            item_description: Description of the item
            item_name: Name of the item
            save_path: Optional path to save the image

        Returns:
            PNG image data as bytes (16x16 pixels)
        """
        try:
            # Create a detailed prompt for pixel art generation
            prompt = self._create_pixel_art_prompt(item_description, item_name)

            print(f"Generating texture for {item_name}...")

            # Generate image using Google Imagen
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    # Imagen configuration
                    response_mime_type="image/png"
                )
            )

            # Get the image data
            if hasattr(response, 'parts') and len(response.parts) > 0:
                # Extract image data from response
                image_data = response.parts[0].inline_data.data
                img = Image.open(BytesIO(image_data))
            else:
                raise ValueError("No image data in response")

            # Convert to 16x16 pixel art (with background removal for items)
            pixelated = self._convert_to_pixel_art(img, size=16, for_block=False)

            # Save to BytesIO
            output = BytesIO()
            pixelated.save(output, format='PNG')
            png_data = output.getvalue()

            # Optionally save to file
            if save_path:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(png_data)
                print(f"Texture saved to {save_path}")

            return png_data

        except Exception as e:
            print(f"Error generating texture: {e}")
            if placeholder_factory:
                return placeholder_factory()
            return self._create_item_placeholder_texture(item_name)

    def _create_pixel_art_prompt(self, item_description: str, item_name: str) -> str:
        """Create an Imagen prompt optimized for Minecraft-style pixel art"""

        prompt = f"""Create a pixel art item sprite for Minecraft of: {item_name}
Description: {item_description}

CRITICAL REQUIREMENTS:
- Draw the item exactly as it appears in Minecraft's inventory
- Use a PURE WHITE background (#FFFFFF / RGB 255,255,255) with NO gradients or shadows
- Center the {item_name} sprite with generous white margins on all sides
- The sprite itself should have bold black or dark outlines separating it from the white background
- Use 4-8 solid colors maximum (no gradients within the item)
- Minecraft's iconic style: sharp pixels, flat colors, simple geometric shapes
- Think diamond sword (bright blue blade, brown handle), golden apple (yellow with green leaf spot), or ruby gem (deep red crystal with dark facets)
- The item should be clearly separated from the white background by its outline
- Scale appropriately for 16x16 pixels - keep it simple and recognizable
- DO NOT place pure white pixels inside the item sprite—reserve white exclusively for the background so it can be keyed out later

The white background should be completely uniform and only surround the item - do not put white pixels inside the item's outline."""

        return prompt

    def _create_block_prompt(
        self,
        block_name: str,
        description: str,
        gameplay_role: str = "",
        material: str = "",
        luminance: Optional[int] = None
    ) -> str:
        """Prompt tailored for seamless Minecraft block textures."""
        material_line = f"Material inspiration: {material}." if material else ""
        luminance_line = ""
        if luminance is not None and luminance > 0:
            luminance_line = "Add subtle glow/emission effects."

        prompt = f"""Create a seamless tileable 16x16 Minecraft block texture for: {block_name}
Description: {description}
Gameplay role: {gameplay_role}
{material_line}

CRITICAL REQUIREMENTS:
- Full 16x16 pixel square texture (NO transparency, NO alpha channel, NO background)
- The texture must tile seamlessly on all edges (left connects to right, top connects to bottom)
- Use Minecraft's blocky pixel art style with 4-8 solid colors
- Add subtle shading/depth but keep edges tileable
- Think of vanilla blocks: stone (gray with noise), iron ore (stone with brown-orange spots), diamond ore (stone with cyan crystals)
- {luminance_line if luminance_line else 'Subtle lighting variations to show depth'}
- NO hands, UI, or 3D perspective - just a flat tileable texture face
- Keep border pixels compatible for seamless tiling"""
        return prompt

    def _convert_to_pixel_art(self, img: Image.Image, size: int = 16, for_block: bool = False) -> Image.Image:
        """
        Convert a high-res image to pixel art with smart background removal

        Args:
            img: PIL Image
            size: Target size (default 16x16)
            for_block: If True, keep opaque (no transparency) for tileable blocks

        Returns:
            Pixelated PIL Image
        """
        # Ensure we're working with RGBA
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        if for_block:
            # Blocks: keep full 16x16 opaque, no background removal
            small = img.resize((size, size), Image.Resampling.NEAREST)
            quantized = small.quantize(colors=32).convert('RGB')
            return quantized
        else:
            # Items/Tools: remove peripheral white background only
            img = self._remove_edge_background(img)
            img = self._replace_white_background_with_transparency(img)
        img = self._auto_crop_and_pad(img, target_px=size * 4)

            # Resize to target size
        small = img.resize((size, size), Image.Resampling.NEAREST)
        small = self._replace_white_background_with_transparency(small)

        # Separate alpha channel before quantization
        alpha = small.split()[3] if small.mode == 'RGBA' else None

        # Quantize only the RGB channels
        if alpha:
            rgb = small.convert('RGB')
            quantized_rgb = rgb.quantize(colors=64).convert('RGB')
            result = quantized_rgb.copy()
            result.putalpha(alpha)
        else:
            quantized = small.quantize(colors=64)
            result = quantized.convert('RGBA')

            # Clean up semi-transparent edge pixels
        result = self._clean_edges(result)

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

    def _create_placeholder_texture(self, label: str = "Placeholder") -> bytes:
        """Backwards-compatible placeholder that uses the item tint logic."""
        return self._create_item_placeholder_texture(label)

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

        return self.generate_item_texture(
            enhanced_desc,
            item_name,
            placeholder_factory=lambda: self._create_item_placeholder_texture(item_name)
        )

    def generate_multiple_block_textures(self, block_spec: dict, count: int = 5) -> list[bytes]:
        """
        Generate multiple block texture variants
        """
        textures = []
        for i in range(count):
            try:
                texture = self.generate_block_texture_from_spec(block_spec, save_path=None)
                textures.append(texture)
                print(f"Generated block variant {i+1}/{count}")
            except Exception as e:
                print(f"Error generating block variant {i+1}: {e}")
                textures.append(self._create_block_placeholder_texture(block_spec))
        return textures

    def generate_multiple_tool_textures(self, tool_spec: dict, count: int = 5) -> list[bytes]:
        """
        Generate multiple tool texture variants
        """
        textures = []
        for i in range(count):
            try:
                texture = self.generate_tool_texture(tool_spec)
                textures.append(texture)
                print(f"Generated tool variant {i+1}/{count}")
            except Exception as e:
                print(f"Error generating tool variant {i+1}: {e}")
                textures.append(self._create_tool_placeholder_texture(tool_spec.get("toolName", "Tool")))
        return textures

    def generate_block_texture_from_spec(self, block_spec: dict, save_path: Path = None) -> bytes:
        """
        Generate a seamless block texture using LangChain block metadata.
        """
        block_name = block_spec.get("blockName", "Mystery Block")
        description = block_spec.get("description", "")
        gameplay = block_spec.get("gameplayRole", "")
        properties = block_spec.get("properties", {})

        prompt = self._create_block_prompt(
            block_name=block_name,
            description=description,
            gameplay_role=gameplay,
            material=properties.get("material"),
            luminance=properties.get("luminance"),
        )

        try:
            # Generate image using Google Imagen
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="image/png"
                )
            )

            # Get the image data
            if hasattr(response, 'parts') and len(response.parts) > 0:
                image_data = response.parts[0].inline_data.data
                img = Image.open(BytesIO(image_data))
            else:
                raise ValueError("No image data in response")
            pixelated = self._convert_to_pixel_art(img, size=16, for_block=True)

            output = BytesIO()
            pixelated.save(output, format='PNG')
            png_data = output.getvalue()

            if save_path:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_bytes(png_data)

            return png_data
        except Exception as e:
            print(f"Error generating block texture: {e}")
            return self._create_block_placeholder_texture(block_spec)

    def generate_tool_texture(self, tool_spec: dict) -> bytes:
        """
        Generate a texture for melee tools like pickaxes. Falls back to a stylized
        placeholder so debugging in-game never shows the magenta checkerboard.
        """
        name = tool_spec.get("toolName", "Custom Pickaxe")
        description = tool_spec.get("description", name)
        return self.generate_item_texture(
            item_description=description,
            item_name=name,
            placeholder_factory=lambda: self._create_tool_placeholder_texture(name)
        )

    # -------------------------------------------------------------------------
    # Placeholder helpers
    # -------------------------------------------------------------------------

    def _color_from_name(self, text: str) -> tuple[int, int, int]:
        digest = hashlib.sha1(text.encode("utf-8")).digest()
        return tuple(80 + digest[i] % 140 for i in range(3))

    def _create_item_placeholder_texture(self, name: str) -> bytes:
        base = self._color_from_name(name)
        highlight = tuple(min(255, channel + 40) for channel in base)
        shade = tuple(max(0, channel - 35) for channel in base)

        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        diamond = [
            (8, 2), (12, 6), (8, 14), (4, 6)
        ]
        draw.polygon(diamond, fill=highlight, outline=shade)
        draw.line([(8, 2), (8, 14)], fill=shade)
        draw.line([(4, 6), (12, 6)], fill=shade)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def _create_block_placeholder_texture(self, block_spec: dict | None) -> bytes:
        block_name = (block_spec or {}).get("blockName", "Ore Block")
        accent = self._color_from_name(block_name)
        accent_dark = tuple(max(0, c - 30) for c in accent)
        stone = (70, 70, 70, 255)

        img = Image.new("RGBA", (16, 16), stone)
        pixels = img.load()

        digest = hashlib.sha1(block_name.encode("utf-8")).digest()
        for i in range(0, len(digest), 2):
            x = digest[i] % 16
            y = digest[i + 1] % 16
            pixels[x, y] = accent + (255,)
            if x + 1 < 16:
                pixels[x + 1, y] = accent_dark + (255,)
            if y + 1 < 16:
                pixels[x, y + 1] = accent_dark + (255,)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def _create_tool_placeholder_texture(self, name: str) -> bytes:
        head = self._color_from_name(name)
        handle = (96, 61, 26)
        shadow = tuple(max(0, c - 40) for c in head)

        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Handle
        draw.line([(7, 4), (4, 13)], fill=handle, width=2)
        draw.line([(9, 4), (6, 13)], fill=handle, width=1)

        # Pickaxe head
        draw.polygon([(8, 3), (13, 3), (15, 5), (14, 6), (9, 6)], fill=head)
        draw.polygon([(8, 3), (3, 3), (1, 5), (2, 6), (7, 6)], fill=head)
        draw.line([(8, 3), (8, 6)], fill=shadow, width=1)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
