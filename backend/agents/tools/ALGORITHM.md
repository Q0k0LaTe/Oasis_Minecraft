# Image Generation System Architecture

## Overview

The image generation system has been completely rewritten with a clear separation between **items/tools** and **blocks**. Each type uses a fundamentally different algorithm optimized for its specific requirements.

```
┌─────────────────────────────────────────────────────────────┐
│                     ImageGenerator                          │
│                    (Unified Facade)                         │
├─────────────────────────┬───────────────────────────────────┤
│   ItemImageGenerator    │      BlockImageGenerator          │
│   (Existing Algorithm)  │      (NEW Algorithm)              │
├─────────────────────────┼───────────────────────────────────┤
│ • Items (gems, ingots)  │ • Blocks (stone, ore, wood)       │
│ • Tools (pickaxe, axe)  │                                   │
├─────────────────────────┼───────────────────────────────────┤
│ Output: RGBA w/ alpha   │ Output: RGB (fully opaque)        │
│ Storage: assets/items/  │ Storage: assets/blocks/           │
└─────────────────────────┴───────────────────────────────────┘
```

---

## Item & Tool Generation (Existing Algorithm)

Items and tools use the **established algorithm** that has been proven effective. This algorithm was NOT modified during the rewrite.

### Key Characteristics
- **Transparent backgrounds** - Items float on inventory slots
- **Centered sprites** - Consistent positioning across items
- **Clear outlines** - Sharp edges defining the sprite shape

### Pipeline Steps
1. **Prompt Generation**: Rarity-aware prompts with color palette guidance
2. **Reference Selection**: AI selects similar vanilla textures as style guides
3. **API Generation**: Gemini generates high-resolution base image
4. **Background Removal**: Flood-fill from edges removes white background
5. **Auto-crop & Pad**: Centers sprite with consistent margins
6. **Two-stage Downsampling**: Lanczos → Nearest for quality
7. **Palette Quantization**: Maps to Minecraft color palette
8. **Edge Cleanup**: Removes anti-aliasing artifacts

### Output Specifications
- **Size**: 16×16 pixels
- **Format**: PNG with alpha channel (RGBA)
- **Background**: Transparent
- **Storage**: `assets/{mod_id}/textures/item/{item_id}.png`

---

## Block Generation (NEW Algorithm)

Blocks use a **completely new algorithm** designed for seamless tileable surface textures.

### Why a Different Algorithm?

Block textures have fundamentally different requirements than items:

| Requirement | Items | Blocks |
|-------------|-------|--------|
| Transparency | Yes (floating sprite) | No (solid surface) |
| Tileability | N/A | Critical (must tile seamlessly) |
| View | Isolated sprite | Surface texture |
| Edges | Clear outline | Must match opposite edges |

### NEW Block Algorithm Pipeline

```
┌──────────────────┐
│  1. PROMPT       │  Material-specific prompt emphasizing tileability
└────────┬─────────┘
         ▼
┌──────────────────┐
│  2. REFERENCE    │  Select block textures (not items) as style guides
└────────┬─────────┘
         ▼
┌──────────────────┐
│  3. GENERATE     │  Gemini API produces raw texture
└────────┬─────────┘
         ▼
┌──────────────────┐
│  4. RGB CONVERT  │  Force full opacity (no alpha channel)
└────────┬─────────┘
         ▼
┌──────────────────┐
│  5. DOWNSAMPLE   │  Three-stage quality reduction with sharpening
└────────┬─────────┘
         ▼
┌──────────────────┐
│  6. QUANTIZE     │  Block-specific color palette
└────────┬─────────┘
         ▼
┌──────────────────┐
│  7. EDGE BLEND   │  Improve seamless tiling at boundaries
└────────┬─────────┘
         ▼
┌──────────────────┐
│  8. LUMINANCE    │  Apply glow effect for light-emitting blocks
└────────┬─────────┘
         ▼
┌──────────────────┐
│  OUTPUT: 16×16   │  Fully opaque RGB PNG
│  RGB PNG         │
└──────────────────┘
```

### Block-Specific Features

#### 1. Material-Aware Prompting
Each material type has specific texture guidance:

```python
MATERIAL_CONFIGS = {
    "STONE": {
        "pattern": "irregular cracks and speckles",
        "colors": "gray base with darker cracks and lighter spots"
    },
    "METAL": {
        "pattern": "panel grid with rivets or seams",
        "colors": "metallic silver with darker seams"
    },
    "WOOD": {
        "pattern": "parallel grain lines",
        "colors": "warm brown with darker grain"
    },
    # ... etc
}
```

#### 2. Tileability Requirements
Prompts explicitly require:
- Top edge pixels must match bottom edge
- Left edge pixels must match right edge
- No visible seams when tiled

#### 3. Block Color Palette
Different from item palette, optimized for:
- Stone variations (gray spectrum)
- Deepslate (blue-gray tones)
- Wood (warm browns)
- Metals (cool metallic grays)
- Ore embeddings

#### 4. Edge Blending
Post-processing step that:
- Analyzes color difference between opposite edges
- Blends edges toward average if difference too high
- Preserves texture detail with subtle blend factor

#### 5. Luminance Effects
For light-emitting blocks (luminance > 0):
- Radial brightness gradient (brighter center)
- Preserves texture while adding glow
- Scaled by luminance level (0-15)

### Output Specifications
- **Size**: 16×16 pixels
- **Format**: PNG without alpha (RGB only)
- **Background**: None (fully opaque)
- **Tiling**: Seamless in all directions
- **Storage**: `assets/{mod_id}/textures/block/{block_id}.png`

---

## Storage Rules

**CRITICAL: Items and blocks MUST be stored in separate directories.**

```
assets/
├── items/           ← Item textures ONLY
│   ├── gem.png
│   └── ingot.png
└── blocks/          ← Block textures ONLY
    ├── ore.png
    └── stone.png
```

In the mod structure:
```
src/main/resources/assets/{mod_id}/textures/
├── item/            ← Items and tools
│   ├── magic_gem.png
│   └── magic_pickaxe.png
└── block/           ← Blocks only
    └── magic_ore.png
```

---

## API Usage

### Generate Item Textures
```python
from agents.tools.image_generator import ImageGenerator

generator = ImageGenerator()

# Generate multiple variants for selection
variants = generator.generate_item_texture(
    item_description="A glowing magical gem",
    item_name="magic_gem",
    count=5
)
```

### Generate Tool Textures
```python
# Tools use the SAME algorithm as items
tool_variants = generator.generate_tool_texture(
    tool_spec={
        "toolName": "Magic Pickaxe",
        "description": "A pickaxe made of magical gems"
    },
    count=5
)
```

### Generate Block Textures (NEW Algorithm)
```python
# Blocks use the NEW dedicated algorithm
block_variants = generator.generate_block_texture_from_spec(
    block_spec={
        "blockName": "Magic Ore",
        "description": "Ore containing magical gems",
        "gameplayRole": "Mined for magic gems",
        "properties": {
            "material": "STONE",
            "luminance": 5
        }
    },
    count=5
)
```

### Direct Generator Access
```python
# For advanced usage, access generators directly
item_gen = generator.item_generator
block_gen = generator.block_generator
```

---

## Key Differences Summary

| Aspect | Item/Tool Generator | Block Generator |
|--------|---------------------|-----------------|
| Algorithm | Existing (preserved) | NEW (rewritten) |
| Transparency | RGBA with alpha | RGB only |
| Background | Removed via flood-fill | None (full coverage) |
| Edges | Clear outline required | Must tile seamlessly |
| Palette | Item-focused colors | Block-focused colors |
| Post-processing | Edge cleanup | Edge blending |
| View type | Isolated sprite | Surface texture |
| Storage | textures/item/ | textures/block/ |

---

## Future Extensibility

The modular architecture allows for:
- Adding new material types to block generator
- Supporting multiple block faces (top/side/bottom)
- Adding animation support for textures
- Custom palettes per mod style
